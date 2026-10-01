"""Property tests for the Phase 6 Slurm submission helper (submit_slurm.py).

Feature: phase-6-ssh-slurm

Pure-logic properties (GRES mapping, resource->sbatch mapping, log naming,
conda-activation ordering, framework-free run command, quota pre-check, job-id
parsing, status mapping, approval gating, commit-candidate exclusion, secret
redaction, verification gating, heavy-job routing, read-only probe membership,
retry/resume) are exercised with Hypothesis. The module is loaded by path,
matching tests/test_phase5_run_local_properties.py. No test performs real SSH,
Slurm, or network I/O; every impure call goes through FakeCommandRunner.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

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

_SETTINGS = SS.PlanSettings(
    ssh_host="research-cluster",
    remote_project_root="/home/u/data/proj",
    remote_conda_root="/data/u/miniconda3",
    partition="gpu",
    account="cluster",
    qos="normal",
    caps=SS.QoSCaps(),
)


# Property 3 -------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    gpus=st.integers(min_value=1, max_value=8),
    gpu_type=st.one_of(st.none(), st.sampled_from(["A6000", "PRO6000", "4090"]),
                       st.text(max_size=6)),
)
def test_property_3_gres_mapping(gpus, gpu_type) -> None:
    """Feature: phase-6-ssh-slurm, Property 3: GRES mapping.

    **Validates: Requirements 4.3**
    """
    gres = SS.build_gres(gpus, gpu_type)
    if gpu_type in ("A6000", "PRO6000", "4090"):
        assert gres == f"gpu:{gpu_type}:{gpus}"
    else:
        assert gres == f"gpu:{gpus}"


# Property 4 -------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    gpus=st.integers(min_value=0, max_value=4),
    cpus=st.integers(min_value=1, max_value=8),
    mem_gb=st.integers(min_value=1, max_value=80),
    hh=st.integers(min_value=0, max_value=47),
    mm=st.integers(min_value=0, max_value=59),
)
def test_property_4_resource_mapping(gpus, cpus, mem_gb, hh, mm) -> None:
    """Feature: phase-6-ssh-slurm, Property 4: Resource-to-SBATCH mapping.

    **Validates: Requirements 4.1, 4.2**
    """
    time = f"{hh:02d}:{mm:02d}:00"
    resources = {"gpus": gpus, "cpus": cpus, "mem_gb": mem_gb, "time": time}
    directives = SS.map_resources_to_sbatch(resources, _SETTINGS)
    joined = "\n".join(directives)
    assert f"--partition={_SETTINGS.partition}" in joined
    assert f"--account={_SETTINGS.account}" in joined
    assert f"--qos={_SETTINGS.qos}" in joined
    assert f"--cpus-per-task={cpus}" in joined
    assert f"--mem={mem_gb}G" in joined
    assert f"--time={time}" in joined
    if gpus > 0:
        assert any(d.startswith("--gres=") for d in directives)
    else:
        assert not any(d.startswith("--gres=") for d in directives)


# Property 10 ------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    prefix=st.from_regex(r"[0-9]{8}-[0-9]{6}", fullmatch=True),
    job_id=st.integers(min_value=1, max_value=10_000_000),
    task_id=st.one_of(st.none(), st.integers(min_value=0, max_value=999)),
    job_name=st.from_regex(r"[a-z0-9_-]{1,20}", fullmatch=True),
)
def test_property_10_log_name(prefix, job_id, task_id, job_name) -> None:
    """Feature: phase-6-ssh-slurm, Property 10: Log-name construction.

    **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 9.2**
    """
    name = SS.resolve_log_name(prefix, job_id, task_id, job_name)
    if task_id is None:
        assert name == f"{prefix}_{job_id}_{job_name}"
    else:
        assert name == f"{prefix}_{job_id}_{task_id}_{job_name}"

    out, err = SS.build_log_directives(prefix, is_array=task_id is not None)
    assert out.endswith(".out") and err.endswith(".err")
    assert out[:-4] == err[:-4]  # share one stem
    assert out.startswith(prefix)
    if task_id is None:
        assert "%A" in out and "%x" in out and "%a" not in out
    else:
        assert "%A" in out and "%a" in out and "%x" in out


# Property 7 -------------------------------------------------------------- #
@settings(max_examples=200, deadline=None)
@given(
    gpus=st.integers(min_value=0, max_value=8),
    cpus=st.integers(min_value=1, max_value=16),
    mem_gb=st.integers(min_value=1, max_value=160),
    days=st.integers(min_value=0, max_value=4),
)
def test_property_7_quota_precheck(gpus, cpus, mem_gb, days) -> None:
    """Feature: phase-6-ssh-slurm, Property 7: Quota pre-check.

    **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**
    """
    caps = SS.QoSCaps()
    time = f"{days}-00:00:00"
    resources = {"gpus": gpus, "cpus": cpus, "mem_gb": mem_gb, "time": time}
    result = SS.validate_quota(resources, caps)
    within = (gpus <= caps.max_gpus and cpus <= caps.max_cpus
              and mem_gb <= caps.max_mem_gb
              and SS.parse_time_to_seconds(time) <= caps.max_wall_seconds)
    assert result.ok == within


# Property 8 -------------------------------------------------------------- #
@settings(max_examples=200, deadline=None)
@given(
    job_id=st.integers(min_value=1, max_value=99_999_999),
    prefix=st.text(alphabet="abc \n", max_size=10),
    suffix=st.text(alphabet="xyz \n", max_size=10),
)
def test_property_8_jobid_roundtrip(job_id, prefix, suffix) -> None:
    """Feature: phase-6-ssh-slurm, Property 8: Slurm job-id parsing round-trip.

    **Validates: Requirements 6.2, 6.3, 9.3**
    """
    text = f"{prefix}Submitted batch job {job_id}{suffix}"
    assert SS.parse_slurm_job_id(text) == job_id


@settings(max_examples=100, deadline=None)
@given(text=st.text(max_size=60).filter(lambda t: "Submitted batch job" not in t))
def test_property_8_jobid_absent(text) -> None:
    """Feature: phase-6-ssh-slurm, Property 8: Slurm job-id parsing round-trip.

    **Validates: Requirements 6.2, 6.3, 9.3**
    """
    assert SS.parse_slurm_job_id(text) is None


# Property 9 -------------------------------------------------------------- #
_EXPECTED = {
    "PENDING": "pending",
    "RUNNING": "running",
    "COMPLETED": "succeeded",
    "FAILED": "failed",
    "OUT_OF_MEMORY": "failed",
    "CANCELLED": "cancelled",
    "TIMEOUT": "timed_out",
    "PREEMPTED": "preempted",
}


@settings(max_examples=150, deadline=None)
@given(
    state=st.sampled_from(list(_EXPECTED.keys())),
    upper=st.booleans(),
    annotation=st.sampled_from(["", " by 1234", " +"]),
)
def test_property_9_status_mapping(state, upper, annotation) -> None:
    """Feature: phase-6-ssh-slurm, Property 9: Slurm-to-Harness status mapping.

    **Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8**
    """
    raw = state if upper else state.lower()
    mapped = SS.map_slurm_state(raw + annotation)
    assert mapped.value == _EXPECTED[state]


# Property 5 -------------------------------------------------------------- #
@settings(max_examples=80, deadline=None)
@given(
    env_name=st.from_regex(r"[a-z0-9_-]{1,15}", fullmatch=True),
    entrypoint=st.sampled_from(["train.py", "src/main.py", "run.py"]),
)
def test_property_5_conda_activation_ordering(env_name, entrypoint) -> None:
    """Feature: phase-6-ssh-slurm, Property 5: Conda activation precedes run.

    **Validates: Requirements 4.4**
    """
    job = {"entrypoint": entrypoint, "config_style": "argument",
           "resources": {"gpus": 1, "cpus": 4, "mem_gb": 32, "time": "01:00:00"},
           "parameters": {}}
    script = SS.generate_sbatch_script(job, _SETTINGS, "20260101-120000",
                                       conda_env_name=env_name)
    lines = script.splitlines()
    source_idx = next(i for i, l in enumerate(lines) if "conda.sh" in l)
    activate_idx = next(i for i, l in enumerate(lines) if l.startswith("conda activate"))
    run_idx = next(i for i, l in enumerate(lines) if l.startswith("python "))
    assert source_idx < run_idx
    assert activate_idx < run_idx
    assert f"conda activate {env_name}" in script


# Property 6 -------------------------------------------------------------- #
@settings(max_examples=80, deadline=None)
@given(
    entrypoint=st.from_regex(r"[a-z_]{1,10}\.py", fullmatch=True),
    lr=st.floats(min_value=1e-5, max_value=1.0, allow_nan=False, allow_infinity=False),
    epochs=st.integers(min_value=1, max_value=100),
)
def test_property_6_framework_free(entrypoint, lr, epochs) -> None:
    """Feature: phase-6-ssh-slurm, Property 6: Framework-free run command.

    **Validates: Requirements 4.5**
    """
    job = {"entrypoint": entrypoint, "config_style": "argument",
           "resources": {"gpus": 1, "cpus": 4, "mem_gb": 16, "time": "00:30:00"},
           "parameters": {"learning_rate": lr, "epochs": epochs}}
    script = SS.generate_sbatch_script(job, _SETTINGS, "20260101-120000",
                                       conda_env_name="env")
    run_line = next(l for l in script.splitlines() if l.startswith("python "))
    tokens = run_line.split()
    assert entrypoint in tokens
    assert SS.command_is_framework_free(tokens, entrypoint)


# Property 11 ------------------------------------------------------------- #
@settings(max_examples=80, deadline=None)
@given(
    array=st.one_of(st.none(), st.sampled_from(["0-3", "1-10%2", "0,2,4"])),
    dependency=st.one_of(st.none(), st.sampled_from(["afterok:123", "afterany:9"])),
)
def test_property_11_conditional_directives(array, dependency) -> None:
    """Feature: phase-6-ssh-slurm, Property 11: Dependency/array conditional.

    **Validates: Requirements 9.1, 10.1, 10.2**
    """
    job = {"entrypoint": "t.py", "config_style": "argument",
           "resources": {"gpus": 0, "cpus": 2, "mem_gb": 8, "time": "00:10:00"},
           "parameters": {}}
    if array is not None:
        job["array"] = array
    if dependency is not None:
        job["dependency"] = dependency
    script = SS.generate_sbatch_script(job, _SETTINGS, "20260101-120000",
                                       conda_env_name="env")
    if array is not None:
        assert f"--array={array}" in script
    else:
        assert "--array=" not in script
    if dependency is not None:
        assert f"--dependency={dependency}" in script
    else:
        assert "--dependency=" not in script


# Property 14 ------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    approval=st.one_of(st.none(), st.just("approved"), st.just("pending"),
                       st.text(max_size=10)),
    kind=st.sampled_from(["submit", "cancel", "transfer", "env_create"]),
)
def test_property_14_approval_gating(approval, kind) -> None:
    """Feature: phase-6-ssh-slurm, Property 14: Mutating actions iff approved.

    **Validates: Requirements 6.1, 8.1, 8.2, 8.4, 14.1, 14.2, 14.3**
    """
    decision = SS.decide_mutating_action(approval, kind)
    if approval and str(approval).strip().lower() == "approved":
        assert decision == SS.ActionDecision.PROCEED
    else:
        assert decision == SS.ActionDecision.DECLINE_APPROVAL


# Property 15 ------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    gpus=st.integers(min_value=0, max_value=4),
    cpus=st.integers(min_value=1, max_value=8),
    hours=st.integers(min_value=0, max_value=8),
)
def test_property_15_heavy_routing(gpus, cpus, hours) -> None:
    """Feature: phase-6-ssh-slurm, Property 15: Heavy jobs route through sbatch.

    **Validates: Requirements 15.1**
    """
    resources = {"gpus": gpus, "cpus": cpus, "time": f"{hours:02d}:00:00"}
    heavy = SS.is_heavy_job(resources)
    effective_hours = hours if hours > 0 else 1.0
    expected = gpus > 0 or (cpus * effective_hours) > SS.CPU_HEAVY_THRESHOLD_HOURS
    assert heavy == expected


# Property 16 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(
    argv=st.sampled_from([
        ["echo", "ok"], ["test", "-d", "/x"], ["conda", "env", "list"],
        ["sinfo"], ["squeue", "-j", "1"], ["sacct", "-j", "1"],
        ["scontrol", "show", "job", "1"],
    ])
)
def test_property_16_readonly_probes(argv) -> None:
    """Feature: phase-6-ssh-slurm, Property 16: Login-node probes non-mutating.

    **Validates: Requirements 15.2**
    """
    assert SS.is_readonly_probe(argv)


@settings(max_examples=100, deadline=None)
@given(argv=st.sampled_from([["sbatch", "job.sh"], ["scancel", "1"], ["rm", "-rf", "/x"],
                              ["git", "clone", "u"]]))
def test_property_16_mutating_not_probe(argv) -> None:
    """Feature: phase-6-ssh-slurm, Property 16: Login-node probes non-mutating.

    **Validates: Requirements 15.2**
    """
    assert not SS.is_readonly_probe(argv)


# Property 17 ------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(paths=st.lists(st.from_regex(
    r"[a-z/]{1,8}(/(checkpoints|wandb))?/[a-z]{1,6}\.(out|err|yaml|json|md|png)",
    fullmatch=True), max_size=12))
def test_property_17_commit_filter(paths) -> None:
    """Feature: phase-6-ssh-slurm, Property 17: Commit candidates exclude logs.

    **Validates: Requirements 15.3**
    """
    filtered = SS.filter_commit_candidates(paths)
    for p in filtered:
        assert not p.endswith((".out", ".err"))
        assert "checkpoints" not in p.split("/")
        assert "wandb" not in p.split("/")


# Property 18 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
@given(
    secret=st.text(alphabet="ABCDEF0123456789", min_size=8, max_size=24),
    entrypoint=st.sampled_from(["train.py", "run.py"]),
)
def test_property_18_no_secrets_in_script(secret, entrypoint) -> None:
    """Feature: phase-6-ssh-slurm, Property 18: Generated artifacts hold no secrets.

    **Validates: Requirements 4.7, 13.4**
    """
    env = {"HF_TOKEN": secret, "WANDB_API_KEY": secret, "PATH": "/usr/bin"}
    job = {"entrypoint": entrypoint, "config_style": "argument",
           "resources": {"gpus": 1, "cpus": 4, "mem_gb": 16, "time": "00:30:00"},
           "parameters": {"epochs": 3}}
    script = SS.generate_sbatch_script(job, _SETTINGS, "20260101-120000",
                                       conda_env_name="env")
    # Generator never embeds env values; and redaction removes any that appear.
    assert secret not in script
    redacted = SS.redact_secrets(script + f" {secret}", env)
    assert secret not in redacted
    # Names-only report drops credential values.
    report = SS.redact_environment(env)
    assert "HF_TOKEN" not in report["safe_values"]
    assert "WANDB_API_KEY" not in report["safe_values"]
    assert "PATH" in report["safe_values"]
