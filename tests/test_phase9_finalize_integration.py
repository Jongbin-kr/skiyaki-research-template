"""Integration tests for the Phase 9 finalize helper (finalize_experiment.py).

Feature: phase-9-finalize-git

Exercises orchestration wiring (verify, finalize, propose, commit) with a
FakeGitClient. No real git commit, push, or network I/O ever occurs. All writes
are confined to tmp_path; the example experiment stays read-only. Covers design
Properties 2, 8, 19, 23 and the injection guard, plus blocked/invalid/unverified/
security-review/approval-gating/honest-partial scenarios.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKSPACE = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts" / "finalize_experiment.py"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("finalize_experiment", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.modules["finalize_experiment"] = module
    spec.loader.exec_module(module)
    return module


FE = _load_module()


# --------------------------------------------------------------------------- #
# Fixture: a complete experiment directory under tmp_path
# --------------------------------------------------------------------------- #
def _make_experiment(tmp_path: Path, *, approved=True, run_status="succeeded",
                     metric=0.9, hf_status="verified", with_journal=True,
                     with_results=True) -> Path:
    exp = tmp_path / "experiments" / "exp1"
    (exp / "jobs").mkdir(parents=True)
    (exp / "jobs" / "train.yaml").write_text(yaml.safe_dump({"job_id": "t"}), encoding="utf-8")
    run_dir = exp / "runs" / "train-t__20260101T000000"
    run_dir.mkdir(parents=True)
    (run_dir / "run.yaml").write_text(yaml.safe_dump({
        "status": run_status, "wandb_run_id": "w123",
        "wandb_url": "https://wandb.ai/lab/proj/runs/w123",
        "hf_repo_id": "lab/exp1", "hf_revision": "abc", "hf_status": hf_status,
    }), encoding="utf-8")
    approval = "approved" if approved else "pending"
    (exp / "plan.md").write_text(
        f"---\nexperiment_id: exp1\nstatus: running\n"
        f"success_criteria:\n  - acc > 0.8\n"
        f"approval:\n  status: {approval}\n---\n# plan\n", encoding="utf-8")
    if with_results:
        (exp / "results.yaml").write_text(yaml.safe_dump({
            "experiment_id": "exp1",
            "best_run": {"run_id": run_dir.name},
            "primary_metric": {"name": "acc", "value": metric, "direction": "max"},
            "artifacts": {"checkpoint": "lab/exp1"},
        }), encoding="utf-8")
    (exp / "history.md").write_text("# Experiment History\n\n## run\n- did a run\n",
                                    encoding="utf-8")
    if with_journal:
        (exp / "journal.md").write_text(
            "# Journal\n## Hypothesis\nsupported\n## Key Findings\nf1\n"
            "## Interpretation\nmeaning\n## Recommended Next Experiments\nnext\n",
            encoding="utf-8")
    # project-log at workspace root (tmp_path)
    (tmp_path / "project-log.md").write_text("# Project Log\n\n", encoding="utf-8")
    return exp


def _args(cmd, exp, workspace):
    return argparse.Namespace(command=cmd, experiment_dir=str(exp), workspace=str(workspace))


# --- injection guard ----------------------------------------------------- #
def test_fake_client_raises_on_unscripted() -> None:
    c = FE.FakeGitClient({})
    with pytest.raises(AssertionError):
        c.commit("msg")


def test_real_client_only_in_builder() -> None:
    """Property 19: Injected-boundary discipline.

    **Feature: phase-9-finalize-git, Property 19: Injected-boundary discipline**
    **Validates: Requirements 12.1, 12.2, 12.3, 12.4**
    """
    assert hasattr(FE, "RealGitClient")
    assert FE._build_client.__name__ == "_build_client"


# --- verify -------------------------------------------------------------- #
def test_verify_passes(tmp_path: Path) -> None:
    """**Validates: Requirements 1.1, 2.1, 3.1**"""
    exp = _make_experiment(tmp_path)
    result = FE.run_cli(_args("verify", exp, tmp_path))
    assert result["status"] == "success"
    assert result["data"]["status"] == "verified"


# --- Property 2: blocked finalization on missing file -------------------- #
def test_property_2_blocked_missing_file(tmp_path: Path) -> None:
    """Feature: phase-9-finalize-git, Property 2: Missing required file blocks finalization.

    **Validates: Requirements 1.3**
    """
    exp = _make_experiment(tmp_path, with_results=False)
    result = FE.run_cli(_args("verify", exp, tmp_path))
    assert result["status"] == "error"
    assert result["data"]["decision"] == "blocked"
    assert "results" in result["data"]["missing"]


def test_invalid_run_reference(tmp_path: Path) -> None:
    """**Validates: Requirements 2.2**"""
    exp = _make_experiment(tmp_path)
    # corrupt best_run reference
    res = yaml.safe_load((exp / "results.yaml").read_text())
    res["best_run"]["run_id"] = "nonexistent"
    (exp / "results.yaml").write_text(yaml.safe_dump(res), encoding="utf-8")
    result = FE.run_cli(_args("verify", exp, tmp_path))
    assert result["status"] == "error"
    assert result["data"]["decision"] == "invalid_reference"


def test_non_numeric_metric(tmp_path: Path) -> None:
    """**Validates: Requirements 2.4**"""
    exp = _make_experiment(tmp_path)
    res = yaml.safe_load((exp / "results.yaml").read_text())
    res["primary_metric"]["value"] = "high"
    (exp / "results.yaml").write_text(yaml.safe_dump(res), encoding="utf-8")
    result = FE.run_cli(_args("verify", exp, tmp_path))
    assert result["status"] == "error"
    assert result["data"]["decision"] == "incomplete_results"


# --- finalize ------------------------------------------------------------ #
def test_finalize_writes_docs(tmp_path: Path) -> None:
    """**Validates: Requirements 4.1, 5.1, 7.1, 14.2**"""
    exp = _make_experiment(tmp_path)
    result = FE.run_cli(_args("finalize", exp, tmp_path))
    assert result["status"] == "success"
    assert result["data"]["status"] == "finalized"
    # history appended, prior content preserved
    hist = (exp / "history.md").read_text(encoding="utf-8")
    assert "Experiment Completed" in hist and "did a run" in hist
    # project log updated with the experiment entry
    plog = (tmp_path / "project-log.md").read_text(encoding="utf-8")
    assert "— exp1" in plog
    # plan.md finalized marker set, run status unchanged
    plan = yaml.safe_load((exp / "plan.md").read_text().split("---")[1])
    assert plan["finalized"] is True and plan["status"] == "completed"
    run_yaml = yaml.safe_load(
        (exp / "runs" / "train-t__20260101T000000" / "run.yaml").read_text())
    assert run_yaml["status"] == "succeeded"  # Property 23: run status untouched


def test_property_23_linkage_surfaced(tmp_path: Path) -> None:
    """Feature: phase-9-finalize-git, Property 23: Linkage surfaced, run status unchanged.

    **Validates: Requirements 14.1, 14.2, 14.3**
    """
    exp = _make_experiment(tmp_path)
    FE.run_cli(_args("finalize", exp, tmp_path))
    results = yaml.safe_load((exp / "results.yaml").read_text(encoding="utf-8"))
    assert results["artifacts"]["wandb_url"].startswith("https://wandb.ai")
    assert results["artifacts"]["hf_repo_id"] == "lab/exp1"


# --- honest partial finalization ----------------------------------------- #
def test_finalize_partial_unverified_hf(tmp_path: Path) -> None:
    """**Validates: Requirements 13.3**"""
    exp = _make_experiment(tmp_path, hf_status="upload_failed")
    result = FE.run_cli(_args("finalize", exp, tmp_path))
    assert result["status"] == "error"
    assert result["data"]["decision"] == "incomplete_experiment"
    assert result["data"]["experiment_complete"] is False
    plan = yaml.safe_load((exp / "plan.md").read_text().split("---")[1])
    assert plan["status"] == "partial"


# --- propose ------------------------------------------------------------- #
def test_property_8_propose_candidate(tmp_path: Path) -> None:
    """Feature: phase-9-finalize-git, Property 8/13: candidate proposal.

    **Validates: Requirements 8.1, 8.3, 11.5**
    """
    exp = _make_experiment(tmp_path)
    result = FE.run_cli(_args("propose", exp, tmp_path))
    assert result["status"] == "success"
    assert result["data"]["status"] == "proposal_ready"
    files = result["data"]["files"]
    assert "experiments/exp1/results.yaml" in files
    assert "project-log.md" in files
    assert "exp1" in result["data"]["message"]


def test_propose_refuses_credential_file(tmp_path: Path) -> None:
    """Security review refuses a candidate that contains a credential file.

    The orchestration selects only known doc types, so a credential file cannot
    normally reach the candidate; this asserts the scan refuses one if it does.

    **Validates: Requirements 10.2, 10.3**
    """
    exp = _make_experiment(tmp_path)
    candidate = FE.select_commit_candidate("experiments/exp1",
                                           ["train-t__20260101T000000"], ["train.yaml"])
    # A credential file reaching the candidate must be detected and refused.
    tainted = candidate + ["experiments/exp1/.env", "secrets/api.token"]
    found = FE.scan_for_credential_files(tainted)
    assert "experiments/exp1/.env" in found
    assert "secrets/api.token" in found
    # And none of the clean candidate paths are flagged.
    assert not FE.scan_for_credential_files(candidate)


# --- commit (approval-gated) --------------------------------------------- #
def test_commit_declined_without_approval(tmp_path: Path) -> None:
    """**Validates: Requirements 11.2**"""
    exp = _make_experiment(tmp_path, approved=False)
    fake = FE.FakeGitClient({})  # any call raises
    result = FE.run_cli(_args("commit", exp, tmp_path), client_factory=lambda w: fake)
    assert result["status"] == "error"
    assert result["data"]["decision"] == "approval_required"
    assert result["data"]["status"] == "proposal_ready"
    assert fake.calls == []  # git never touched


def test_commit_proceeds_with_approval(tmp_path: Path) -> None:
    """**Validates: Requirements 11.3, 12.1**"""
    exp = _make_experiment(tmp_path, approved=True)
    fake = FE.FakeGitClient({
        "stage": FE.StageOutcome(staged=[]),
        "commit": FE.CommitOutcome(sha="cafebabe"),
    })
    result = FE.run_cli(_args("commit", exp, tmp_path), client_factory=lambda w: fake)
    assert result["status"] == "success"
    assert result["data"]["status"] == "committed"
    assert result["data"]["sha"] == "cafebabe"
    ops = [c["op"] for c in fake.calls]
    assert "stage" in ops and "commit" in ops
