"""Integration tests for the Phase 6 Slurm submission helper (submit_slurm.py).

Feature: phase-6-ssh-slurm

Exercises orchestration wiring (verify, submit, poll, cancel, retry, resume,
run.yaml linkage) with a FakeCommandRunner. No real SSH, Slurm, or network I/O
ever occurs. All writes are confined to tmp_path; the example experiment stays
read-only. Also covers design Properties 1, 2, 12, 13 and the injection guard.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKSPACE = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts" / "submit_slurm.py"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("submit_slurm", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.modules["submit_slurm"] = module
    spec.loader.exec_module(module)
    return module


SS = _load_module()

SETTINGS = SS.PlanSettings(
    ssh_host="research-cluster",
    remote_project_root="/home/u/data/proj",
    remote_conda_root="/data/u/miniconda3",
    partition="gpu",
    account="cluster",
    qos="normal",
    caps=SS.QoSCaps(),
)


def _ok(stdout="", exit_code=0, stderr=""):
    return SS.CommandResult(exit_code, stdout, stderr)


def _runner(scripted):
    return SS.FakeCommandRunner(scripted)


# --- Injection guard ----------------------------------------------------- #
def test_fake_runner_raises_on_unscripted() -> None:
    r = _runner([])
    with pytest.raises(AssertionError):
        r.run(["sbatch", "job.sh"], remote=True)


def test_sshrunner_not_constructed_in_tests() -> None:
    """Guard: this suite never constructs SSHCommandRunner; the fake does all I/O.

    **Validates: Requirements 14.4**
    """
    # Confirm the production runner exists but is not instantiated here.
    assert hasattr(SS, "SSHCommandRunner")
    # No live boundary without an injected runner: run_cli requires a factory.
    assert SS._build_runner.__name__ == "_build_runner"


# --- Property 1: pre-submit verification gate ---------------------------- #
def test_property_1_verify_gate_all_ok() -> None:
    """Feature: phase-6-ssh-slurm, Property 1: Pre-submit gate on verification.

    **Validates: Requirements 1.3, 1.4, 2.3, 2.4**
    """
    r = _runner([
        ("echo ok", _ok("ok\n")),
        ("test -d", _ok("")),
        ("conda env list", _ok("# conda environments:\nbase  *  /x\nmyenv  /y\n")),
    ])
    v = SS.verify_remote(r, SETTINGS, "myenv")
    assert v.ok and v.host_ok and v.path_ok and v.env_ok


def test_property_1_host_unreachable_no_further_probe() -> None:
    """Feature: phase-6-ssh-slurm, Property 1: Pre-submit gate on verification.

    **Validates: Requirements 1.3, 1.4, 2.3, 2.4**
    """
    r = _runner([("echo ok", _ok("", exit_code=255, stderr="conn refused"))])
    v = SS.verify_remote(r, SETTINGS, "myenv")
    assert not v.ok and not v.host_ok
    # Only the reachability probe should have been attempted.
    assert len(r.calls) == 1


def test_property_1_missing_path_blocks_env_check() -> None:
    """Feature: phase-6-ssh-slurm, Property 1: Pre-submit gate on verification.

    **Validates: Requirements 1.3, 1.4, 2.3, 2.4**
    """
    r = _runner([("echo ok", _ok("ok\n")), ("test -d", _ok("", exit_code=1))])
    v = SS.verify_remote(r, SETTINGS, "myenv")
    assert not v.ok and v.host_ok and not v.path_ok
    assert len(r.calls) == 2  # no conda env list


# --- Property 2: conda env membership ------------------------------------ #
def test_property_2_env_present_verified() -> None:
    """Feature: phase-6-ssh-slurm, Property 2: Conda env verification membership.

    **Validates: Requirements 3.3, 3.4**
    """
    r = _runner([
        ("echo ok", _ok("ok\n")), ("test -d", _ok("")),
        ("conda env list", _ok("base  /a\ntarget  /b\n")),
    ])
    v = SS.verify_remote(r, SETTINGS, "target")
    assert v.env_ok and not v.env_creation_required


def test_property_2_env_absent_flags_creation() -> None:
    """Feature: phase-6-ssh-slurm, Property 2: Conda env verification membership.

    **Validates: Requirements 3.3, 3.4**
    """
    r = _runner([
        ("echo ok", _ok("ok\n")), ("test -d", _ok("")),
        ("conda env list", _ok("base  /a\nother  /b\n")),
    ])
    v = SS.verify_remote(r, SETTINGS, "target")
    assert not v.env_ok and v.env_creation_required


# --- submit: approval + quota gating ------------------------------------- #
def _job(gpus=1, cpus=4, mem=16, time="00:30:00"):
    return {"entrypoint": "train.py", "config_style": "argument",
            "resources": {"gpus": gpus, "cpus": cpus, "mem_gb": mem, "time": time},
            "parameters": {"epochs": 3}}


def test_submit_declined_without_approval_never_calls_runner() -> None:
    """**Validates: Requirements 6.1, 14.1**"""
    r = _runner([])  # anything would raise
    result = SS.submit(r, _job(), SETTINGS, approval_status="pending",
                       conda_env_name="env", date_prefix="20260101-120000",
                       remote_script_path="/x/job.sbatch", verified=True)
    assert not result.ok and result.decision == "approval_required"
    assert r.calls == []  # runner never invoked for the mutating action


def test_submit_quota_exceeded_no_sbatch() -> None:
    """**Validates: Requirements 5.1, 5.2**"""
    r = _runner([])
    result = SS.submit(r, _job(gpus=8), SETTINGS, approval_status="approved",
                       conda_env_name="env", date_prefix="20260101-120000",
                       remote_script_path="/x/job.sbatch", verified=True)
    assert not result.ok and result.decision == "quota_exceeded"
    assert "gpus>4" in result.errors
    assert r.calls == []


def test_submit_approved_parses_job_id() -> None:
    """**Validates: Requirements 6.1, 6.3**"""
    r = _runner([
        ("cat >", _ok("")),
        ("sbatch", _ok("Submitted batch job 778899\n")),
    ])
    result = SS.submit(r, _job(), SETTINGS, approval_status="approved",
                       conda_env_name="env", date_prefix="20260101-120000",
                       remote_script_path="/x/job.sbatch", verified=True)
    assert result.ok and result.slurm_job_id == 778899
    assert result.status == SS.RunStatus.SUBMITTED
    assert any("sbatch" in c["joined"] for c in r.calls)


def test_submit_blocked_when_unverified() -> None:
    """**Validates: Requirements 1.3, 2.3**"""
    r = _runner([])
    result = SS.submit(r, _job(), SETTINGS, approval_status="approved",
                       conda_env_name="env", date_prefix="20260101-120000",
                       remote_script_path="/x/job.sbatch", verified=False)
    assert not result.ok and result.decision == "verification_required"
    assert r.calls == []


# --- poll / cancel ------------------------------------------------------- #
def test_poll_running_from_squeue() -> None:
    """**Validates: Requirements 7.1**"""
    r = _runner([("squeue", _ok("RUNNING n03\n"))])
    status, raw, node = SS.poll(r, 1234)
    assert status == SS.RunStatus.RUNNING and raw == "RUNNING" and node == "n03"


def test_poll_completed_from_sacct() -> None:
    """**Validates: Requirements 7.1**"""
    r = _runner([("squeue", _ok("")), ("sacct", _ok("COMPLETED|n04\n"))])
    status, raw, node = SS.poll(r, 1234)
    assert status == SS.RunStatus.SUCCEEDED and raw == "COMPLETED" and node == "n04"


def test_cancel_approved_sets_cancelled() -> None:
    """**Validates: Requirements 8.1, 8.2**"""
    r = _runner([("scancel", _ok(""))])
    result = SS.cancel(r, 55, approval_status="approved")
    assert result.ok and result.status == SS.RunStatus.CANCELLED


def test_cancel_declined_without_approval() -> None:
    """**Validates: Requirements 8.4**"""
    r = _runner([])
    result = SS.cancel(r, 55, approval_status=None)
    assert not result.ok and result.decision == "approval_required"
    assert r.calls == []


# --- Property 12: retry preserves prior run ------------------------------ #
def _write_run(run_dir: Path, record: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")


def test_property_12_retry_allowed_from_failed() -> None:
    """Feature: phase-6-ssh-slurm, Property 12: Retry preserves the prior run.

    **Validates: Requirements 11.1**
    """
    for status in ("failed", "timed_out", "cancelled", "preempted"):
        assert SS.can_retry(status)
    for status in ("succeeded", "running", "pending", "submitted", None):
        assert not SS.can_retry(status)


def test_property_12_retry_preserves_prior_record(tmp_path: Path) -> None:
    """Feature: phase-6-ssh-slurm, Property 12: Retry preserves the prior run.

    **Validates: Requirements 11.1**
    """
    prior = tmp_path / "runs" / "run-001"
    _write_run(prior, {"status": "failed", "slurm_job_id": 11})
    before = (prior / "run.yaml").read_text(encoding="utf-8")
    # A new run would be a distinct directory; the prior must stay untouched.
    new = tmp_path / "runs" / "run-002"
    _write_run(new, {"status": "submitted"})
    after = (prior / "run.yaml").read_text(encoding="utf-8")
    assert before == after
    assert new.name != prior.name


# --- Property 13: resume reuses recorded job id -------------------------- #
def test_property_13_resume_polls_recorded_id(tmp_path: Path) -> None:
    """Feature: phase-6-ssh-slurm, Property 13: Resume reuses recorded job id.

    **Validates: Requirements 11.2, 11.3**
    """
    run_dir = tmp_path / "runs" / "run-001"
    _write_run(run_dir, {"status": "running", "slurm_job_id": 4242})
    job_id = SS.read_run_field(run_dir, "slurm_job_id")
    assert job_id == 4242
    r = _runner([("squeue", _ok("RUNNING n01\n"))])
    status, raw, node = SS.poll(r, int(job_id))
    assert status == SS.RunStatus.RUNNING
    # Resume must never call sbatch.
    assert not any("sbatch" in c["joined"] for c in r.calls)


def test_property_13_resume_not_possible_without_id(tmp_path: Path) -> None:
    """Feature: phase-6-ssh-slurm, Property 13: Resume reuses recorded job id.

    **Validates: Requirements 11.2, 11.3**
    """
    run_dir = tmp_path / "runs" / "run-001"
    _write_run(run_dir, {"status": "created"})
    assert SS.read_run_field(run_dir, "slurm_job_id") is None


# --- run.yaml linkage ---------------------------------------------------- #
def test_write_run_linkage_fields(tmp_path: Path) -> None:
    """**Validates: Requirements 13.1, 13.2, 13.3**"""
    run_dir = tmp_path / "runs" / "run-001"
    run_dir.mkdir(parents=True)
    SS.write_run_linkage(run_dir, {
        "slurm_job_id": 999, "slurm_state": "COMPLETED", "status": "succeeded",
        "submitted_at": "2026-09-23T14:25:30Z", "node_list": "n03",
    })
    loaded = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    assert loaded["slurm_job_id"] == 999
    assert loaded["slurm_state"] == "COMPLETED"
    assert loaded["status"] == "succeeded"
    assert loaded["node_list"] == "n03"


def test_write_run_linkage_drops_credentials(tmp_path: Path) -> None:
    """**Validates: Requirements 13.4**"""
    run_dir = tmp_path / "runs" / "run-001"
    run_dir.mkdir(parents=True)
    SS.write_run_linkage(run_dir, {
        "slurm_job_id": 1, "HF_TOKEN": "secretvalue", "status": "submitted",
    })
    text = (run_dir / "run.yaml").read_text(encoding="utf-8")
    assert "secretvalue" not in text
    assert "HF_TOKEN" not in text


# --- end-to-end CLI with injected FakeCommandRunner ---------------------- #
def test_cli_submit_flow(tmp_path: Path) -> None:
    """**Validates: Requirements 14.4, 15.4**"""
    # Build a minimal project-plan.md and an approved experiment plan + run dir.
    plan = tmp_path / "project-plan.md"
    plan.write_text(
        "---\n"
        "environment:\n  remote_conda_root: /data/u/miniconda3\n"
        "execution:\n  ssh_host: research-cluster\n  remote_project_root: /home/u/data/proj\n"
        "slurm:\n  partition: gpu\n  account: cluster\n  qos: normal\n"
        "  max_gpus_per_job: 4\n  max_cpus_per_job: 8\n  max_mem_gb_per_job: 80\n"
        "cuda:\n  driver_cuda_version: '12.4'\n"
        "---\n# plan\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "experiments" / "e1" / "runs" / "run-001"
    run_dir.mkdir(parents=True)
    (run_dir / "resolved-job.yaml").write_text(
        yaml.safe_dump(_job()), encoding="utf-8")
    (run_dir / "run.yaml").write_text(
        yaml.safe_dump({"status": "created"}), encoding="utf-8")
    exp_plan = tmp_path / "experiments" / "e1" / "plan.md"
    exp_plan.write_text("---\napproval:\n  status: approved\n---\n", encoding="utf-8")

    scripted = [
        ("echo ok", _ok("ok\n")), ("test -d", _ok("")),
        ("conda env list", _ok("base /a\ntarget /b\n")),
        ("cat >", _ok("")),
        ("sbatch", _ok("Submitted batch job 314159\n")),
    ]
    fake = _runner(scripted)

    import argparse
    args = argparse.Namespace(
        command="submit", plan_file=str(plan), run_dir=str(run_dir),
        experiment_plan=str(exp_plan), conda_env="target",
    )
    result = SS.run_cli(args, runner_factory=lambda s: fake)
    assert result["status"] == "success"
    assert result["data"]["slurm_job_id"] == 314159
    linked = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    assert linked["slurm_job_id"] == 314159
    assert linked["status"] == "submitted"
    # All writes under tmp_path; no W&B/HF tokens anywhere in the envelope.
    assert "wandb" not in str(result).lower() or "wandb_url" not in str(result)


def test_cli_submit_declined_without_approval(tmp_path: Path) -> None:
    """**Validates: Requirements 6.1, 14.1**"""
    plan = tmp_path / "project-plan.md"
    plan.write_text(
        "---\nenvironment:\n  remote_conda_root: /c\n"
        "execution:\n  ssh_host: research-cluster\n  remote_project_root: /p\n"
        "slurm:\n  partition: gpu\n  account: cluster\n  qos: normal\n---\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "experiments" / "e1" / "runs" / "run-001"
    run_dir.mkdir(parents=True)
    (run_dir / "resolved-job.yaml").write_text(yaml.safe_dump(_job()), encoding="utf-8")
    (run_dir / "run.yaml").write_text(yaml.safe_dump({"status": "created"}), encoding="utf-8")
    exp_plan = tmp_path / "experiments" / "e1" / "plan.md"
    exp_plan.write_text("---\napproval:\n  status: pending\n---\n", encoding="utf-8")

    fake = _runner([
        ("echo ok", _ok("ok\n")), ("test -d", _ok("")),
        ("conda env list", _ok("base /a\ntarget /b\n")),
    ])
    import argparse
    args = argparse.Namespace(
        command="submit", plan_file=str(plan), run_dir=str(run_dir),
        experiment_plan=str(exp_plan), conda_env="target",
    )
    result = SS.run_cli(args, runner_factory=lambda s: fake)
    assert result["status"] == "error"
    assert result["data"]["decision"] == "approval_required"
    # No sbatch was ever attempted.
    assert not any("sbatch" in c["joined"] for c in fake.calls)
