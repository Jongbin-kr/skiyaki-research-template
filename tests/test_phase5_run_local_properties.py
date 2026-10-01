"""Property tests for the Phase 5 local execution helper (run_local.py).

Feature: phase-5-local-execution

Pure-logic properties (approval gating, Slurm classification, environment
detection, command construction, status mapping, timeout parsing, W&B URL
parsing, history formatting, redaction) are exercised with Hypothesis. The
module is loaded by path, matching tests/test_initialize_run_properties.py.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts" / "run_local.py"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("run_local", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.modules["run_local"] = module
    spec.loader.exec_module(module)
    return module


RL = _load_module()
STATUS_VALUES = {s.value for s in RL.RunStatus}


# Property 1 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(status=st.one_of(st.none(), st.text(max_size=20), st.just("approved")))
def test_property_1_approval_gate_total(status) -> None:
    """Feature: phase-5-local-execution, Property 1: Approval gate is total.

    **Validates: Requirements 1.2, 1.3, 1.4**
    """
    decision = RL.decide_approval(status)
    if status is None:
        assert decision == RL.ExecDecision.DECLINE_MISSING_APPROVAL
    elif str(status).strip().lower() == "approved":
        assert decision == RL.ExecDecision.PROCEED
    else:
        assert decision == RL.ExecDecision.DECLINE_APPROVAL


# Property 2 -------------------------------------------------------------- #
@settings(max_examples=200, deadline=None)
@given(
    gpus=st.integers(min_value=0, max_value=8),
    cpus=st.integers(min_value=1, max_value=64),
    hours=st.integers(min_value=0, max_value=12),
    minutes=st.integers(min_value=0, max_value=59),
)
def test_property_2_slurm_classification(gpus, cpus, hours, minutes) -> None:
    """Feature: phase-5-local-execution, Property 2: Slurm classification.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    time_str = f"{hours:02d}:{minutes:02d}:00"
    resources = {"gpus": gpus, "cpus": cpus, "time": time_str}
    decision = RL.classify_execution(resources)
    cpu_hours = RL.estimate_cpu_hours(cpus, time_str)
    expected_defer = gpus > 0 or cpu_hours > RL.LOCAL_CPU_HOURS_THRESHOLD
    if expected_defer:
        assert decision == RL.ExecDecision.DEFER_SLURM
    else:
        assert decision == RL.ExecDecision.PROCEED


# Property 3 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(
    conda=st.booleans(),
    uv_project=st.booleans(),
    uv_available=st.booleans(),
    venv=st.booleans(),
)
def test_property_3_env_detection_priority(conda, uv_project, uv_available, venv) -> None:
    """Feature: phase-5-local-execution, Property 3: Env detection priority.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    """
    markers = RL.EnvMarkers(
        conda_active=conda,
        conda_manifest=False,
        uv_project=uv_project,
        uv_available=uv_available,
        virtual_env="/x/.venv" if venv else None,
    )
    manager = RL.detect_environment(markers)
    assert manager in set(RL.EnvManager)
    if conda:
        assert manager == RL.EnvManager.CONDA
    elif uv_project and uv_available:
        assert manager == RL.EnvManager.UV
    elif venv:
        assert manager == RL.EnvManager.VENV
    else:
        assert manager == RL.EnvManager.SYSTEM


# Property 4 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(params=st.dictionaries(
    st.text(alphabet="abcdefghijklmnop_", min_size=1, max_size=8),
    st.integers() | st.text(max_size=12),
    min_size=0, max_size=6,
))
def test_property_4_argument_style(params) -> None:
    """Feature: phase-5-local-execution, Property 4: Argument-style serialization.

    **Validates: Requirements 4.1, 4.2, 4.6, 5.3**
    """
    tokens = RL.serialize_parameters(params, None, None)  # None -> default argument
    assert len(tokens) == 2 * len(params)
    for i, (key, value) in enumerate(params.items()):
        assert tokens[2 * i] == f"--{key.replace('_', '-')}"
        assert tokens[2 * i + 1] == RL._scalar(value)


# Property 5 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(params=st.dictionaries(
    st.text(alphabet="abcdefghij._", min_size=1, max_size=8),
    st.integers() | st.floats(allow_nan=False, allow_infinity=False),
    min_size=0, max_size=6,
))
def test_property_5_hydra_style(params) -> None:
    """Feature: phase-5-local-execution, Property 5: Hydra-style serialization.

    **Validates: Requirements 4.3**
    """
    tokens = RL.serialize_parameters(params, "hydra", None)
    assert len(tokens) == len(params)
    for token in tokens:
        assert "=" in token


# Property 6 -------------------------------------------------------------- #
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    style=st.sampled_from(["json", "yaml"]),
    params=st.dictionaries(
        st.text(alphabet="abcdef_", min_size=1, max_size=6),
        st.integers() | st.text(max_size=10),
        min_size=0, max_size=5,
    ),
)
def test_property_6_file_style_roundtrip(tmp_path, style, params) -> None:
    """Feature: phase-5-local-execution, Property 6: File config round-trip.

    **Validates: Requirements 4.4, 4.5, 7.3**
    """
    import yaml
    path = RL.write_param_file(params, style, tmp_path)
    rp, rt = path.resolve(), tmp_path.resolve()
    assert rt in rp.parents or rp.parent == rt
    if style == "json":
        loaded = json.loads(path.read_text())
    else:
        loaded = yaml.safe_load(path.read_text())
    assert loaded == params
    tokens = RL.serialize_parameters(params, style, str(path))
    assert tokens == ["--config", str(path)]


# Property 7 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(value=st.text(min_size=1, max_size=20).filter(lambda s: " " in s or True))
def test_property_7_whitespace_single_token(value) -> None:
    """Feature: phase-5-local-execution, Property 7: Whitespace single token.

    **Validates: Requirements 4.8**
    """
    tokens = RL.serialize_parameters({"note": value}, "argument", None)
    assert tokens == ["--note", RL._scalar(value)]
    assert tokens[1] == str(value)


# Property 8 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(style=st.text(min_size=1, max_size=12).filter(
    lambda s: s.strip().lower() not in RL.VALID_CONFIG_STYLES))
def test_property_8_unsupported_style(style) -> None:
    """Feature: phase-5-local-execution, Property 8: Unsupported styles declined.

    **Validates: Requirements 4.7**
    """
    with pytest.raises(RL.UnsupportedConfigStyle):
        RL.serialize_parameters({"a": 1}, style, None)


# Property 9 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(entry=st.sampled_from(["src/train.py", "src/torch_entry.py", "run.py"]))
def test_property_9_framework_free(entry) -> None:
    """Feature: phase-5-local-execution, Property 9: Framework-free command.

    **Validates: Requirements 5.1, 5.2**
    """
    command = RL.build_command(["conda", "run", "-n", "env"], entry, ["--epochs", "1"])
    assert RL.command_is_framework_free(command, entry) is True


# Property 11 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    style=st.sampled_from(["argument", "hydra", "json", "yaml"]),
    name=st.text(alphabet="abcde", min_size=1, max_size=5),
)
def test_property_11_write_confinement(tmp_path, style, name) -> None:
    """Feature: phase-5-local-execution, Property 11: Writes confined to run dir.

    **Validates: Requirements 7.3**
    """
    job = {"config_style": style, "parameters": {name: 1}}
    root = tmp_path.resolve()
    for raw in RL.plan_writes(job, tmp_path):
        resolved = Path(raw).resolve()
        assert root in resolved.parents or resolved.parent == root


# Property 12 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(
    present=st.booleans(),
    run_id=st.text(alphabet="abc123", min_size=1, max_size=8),
)
def test_property_12_wandb_url(present, run_id) -> None:
    """Feature: phase-5-local-execution, Property 12: W&B URL extraction.

    **Validates: Requirements 7.5**
    """
    if present:
        url = f"https://wandb.ai/lab/proj/runs/{run_id}"
        text = f"training...\nview run at {url}\ndone"
        assert RL.parse_wandb_url(text) == url
    else:
        assert RL.parse_wandb_url("no url here\njust logs") is None


# Property 13 ------------------------------------------------------------- #
@settings(max_examples=200, deadline=None)
@given(
    kind=st.sampled_from(["exited", "timeout", "cancelled", "prep_error"]),
    exit_code=st.one_of(st.none(), st.integers(min_value=0, max_value=255)),
    on_disk=st.sampled_from(["initialized", "completed", "running", "failed"]),
)
def test_property_13_status_mapping_total(kind, exit_code, on_disk) -> None:
    """Feature: phase-5-local-execution, Property 13: Status mapping is total.

    **Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.2**
    """
    outcome = RL.ProcessOutcome(kind=kind, exit_code=exit_code)
    status = RL.map_status(outcome)
    assert status.value in STATUS_VALUES
    if kind == "timeout":
        assert status == RL.RunStatus.TIMED_OUT
    elif kind == "cancelled":
        assert status == RL.RunStatus.CANCELLED
    elif kind == "prep_error":
        assert status == RL.RunStatus.FAILED
    else:
        assert status == (RL.RunStatus.SUCCEEDED if exit_code == 0 else RL.RunStatus.FAILED)
    norm = RL.normalize_status(on_disk)
    assert norm.value in STATUS_VALUES
    if on_disk == "initialized":
        assert norm == RL.RunStatus.CREATED
    elif on_disk == "completed":
        assert norm == RL.RunStatus.SUCCEEDED


# Property 15 ------------------------------------------------------------- #
@settings(max_examples=200, deadline=None)
@given(
    hours=st.integers(min_value=0, max_value=99),
    minutes=st.integers(min_value=0, max_value=59),
    seconds=st.integers(min_value=0, max_value=59),
    absent=st.booleans(),
)
def test_property_15_timeout_parsing(hours, minutes, seconds, absent) -> None:
    """Feature: phase-5-local-execution, Property 15: Timeout parsing.

    **Validates: Requirements 10.1**
    """
    default = 600
    if absent:
        assert RL.parse_timeout({}, default) == default
    else:
        total = hours * 3600 + minutes * 60 + seconds
        resources = {"time": f"{hours:02d}:{minutes:02d}:{seconds:02d}"}
        expected = total if total > 0 else default
        assert RL.parse_timeout(resources, default) == expected


# Property 16 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    run_id=st.text(alphabet="abc123-_", min_size=1, max_size=12),
    prior=st.text(alphabet="abcdefghij \n#-", max_size=40),
)
def test_property_16_history_entry(tmp_path, run_id, prior) -> None:
    """Feature: phase-5-local-execution, Property 16: History entries.

    **Validates: Requirements 11.1, 11.3, 11.4**
    """
    entry = RL.format_history_entry(
        run_id, "jobs/train.yaml", RL.RunStatus.SUCCEEDED,
        "2025-01-01T00:00:00", 0, "https://wandb.ai/l/p/runs/x",
    )
    assert run_id in entry
    assert "succeeded" in entry
    assert "https://wandb.ai/l/p/runs/x" in entry

    history = tmp_path / "history.md"
    if prior.strip():
        history.write_text(prior, encoding="utf-8")
    RL.append_history(history, entry)
    content = history.read_text(encoding="utf-8")
    if prior.strip():
        assert prior.strip() in content
    assert entry.strip() in content


# Property 17 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(
    extra=st.dictionaries(
        st.sampled_from(["WANDB_API_KEY", "HF_TOKEN", "MY_SECRET", "DB_PASSWORD"]),
        st.text(min_size=1, max_size=20),
        min_size=1, max_size=4,
    ),
    safe=st.dictionaries(
        st.sampled_from(["WANDB_PROJECT", "PATH", "HOME"]),
        st.text(min_size=1, max_size=10),
        min_size=0, max_size=3,
    ),
)
def test_property_17_redaction(extra, safe) -> None:
    """Feature: phase-5-local-execution, Property 17: Credential redaction.

    **Validates: Requirements 12.1, 12.2**
    """
    env = {**extra, **safe}
    result = RL.redact_environment(env)
    for key in extra:
        assert key not in result["safe_values"]
    for key in safe:
        assert key in result["safe_values"]
    for key in env:
        assert key in result["env_names_present"]