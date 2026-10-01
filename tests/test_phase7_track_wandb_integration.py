"""Integration tests for the Phase 7 W&B tracking helper (track_wandb.py).

Feature: phase-7-wandb

Exercises orchestration wiring (create, resume, config, sync, compare, run.yaml
linkage) with a FakeWandbClient. No real W&B API call, sync, or network I/O ever
occurs. All writes are confined to tmp_path; the example experiment stays
read-only. Covers design Properties 5, 6, 12, 13, 15, 18, 19, 20, 22 and the
injection guard.
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
    WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts" / "track_wandb.py"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("track_wandb", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.modules["track_wandb"] = module
    spec.loader.exec_module(module)
    return module


TW = _load_module()


def _settings(entity="my-lab", mode="online"):
    return TW.WandbSettings(entity=entity, project="proj", mode=mode, keep_local_data=True)


def _run_dir(tmp_path: Path, record=None) -> Path:
    d = tmp_path / "experiments" / "exp1" / "runs" / "run-001"
    d.mkdir(parents=True)
    (d / "run.yaml").write_text(yaml.safe_dump(record or {"status": "succeeded"}),
                                encoding="utf-8")
    return d


# --- injection guard ----------------------------------------------------- #
def test_fake_client_raises_on_unscripted() -> None:
    c = TW.FakeWandbClient({})
    with pytest.raises(AssertionError):
        c.create_run(entity="e", project="p", group="g", tags=[], config={},
                     mode="online", dir="/x")


def test_real_client_not_constructed_in_tests() -> None:
    """Property 19: Injected-boundary discipline.

    **Feature: phase-7-wandb, Property 19: Injected-boundary discipline**
    **Validates: Requirements 8.4, 9.1, 12.1, 12.3**
    """
    assert hasattr(TW, "RealWandbClient")
    assert TW._build_client.__name__ == "_build_client"
    # The wandb SDK is imported lazily inside RealWandbClient methods only.
    import sys
    assert "wandb" not in sys.modules


# --- Property 5: create records identity + running ----------------------- #
def test_property_5_create_records_identity(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 5: Run creation records identity and running status.

    **Validates: Requirements 3.2, 3.3**
    """
    run_dir = _run_dir(tmp_path)
    (run_dir / "resolved-job.yaml").write_text(
        yaml.safe_dump({"method": "lora", "lora_rank": 16}), encoding="utf-8")
    client = TW.FakeWandbClient({
        "create_run": TW.CreatedRun(run_id="abc123", url="https://wandb.ai/my-lab/proj/runs/abc123"),
    })
    result = TW.create_run(client, run_dir, _settings(), {"method": "lora"},
                           approval_status="approved", experiment_id="exp1")
    assert result.ok and result.run_id == "abc123"
    assert result.wandb_status == TW.WandbStatus.RUNNING
    assert (run_dir / "wandb").is_dir()


def test_property_5_create_declined_without_approval(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 5 / Property 17.

    **Validates: Requirements 3.1, 3.4, 11.2**
    """
    run_dir = _run_dir(tmp_path)
    client = TW.FakeWandbClient({})  # any call raises
    result = TW.create_run(client, run_dir, _settings(), {},
                           approval_status="pending", experiment_id="exp1")
    assert not result.ok and result.decision == "approval_required"
    assert client.calls == []


def test_create_declined_on_placeholder_online(tmp_path: Path) -> None:
    """**Validates: Requirements 2.2, 3.1**"""
    run_dir = _run_dir(tmp_path)
    client = TW.FakeWandbClient({})
    s = _settings(entity=TW.PLACEHOLDER_ENTITY, mode="online")
    result = TW.create_run(client, run_dir, s, {}, approval_status="approved",
                           experiment_id="exp1")
    assert not result.ok and result.decision == "placeholder_entity"
    assert client.calls == []


# --- Property 6: resume reuses recorded id ------------------------------- #
def test_property_6_resume_reuses_id(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 6: Resume reuses recorded id without new run.

    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    run_dir = _run_dir(tmp_path, {"status": "failed", "wandb_run_id": "r42",
                                   "wandb_url": "https://wandb.ai/my-lab/proj/runs/r42"})
    client = TW.FakeWandbClient({
        "resume_run": TW.CreatedRun(run_id="r42", url="https://wandb.ai/my-lab/proj/runs/r42"),
    })
    result = TW.resume_run(client, run_dir, _settings(), approval_status="approved",
                           experiment_id="exp1")
    assert result.ok and result.run_id == "r42"
    assert all(c["op"] != "create_run" for c in client.calls)


def test_property_6_resume_not_possible(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 6: Resume reuses recorded id without new run.

    **Validates: Requirements 4.2**
    """
    run_dir = _run_dir(tmp_path, {"status": "failed"})
    client = TW.FakeWandbClient({})
    result = TW.resume_run(client, run_dir, _settings(), approval_status="approved",
                           experiment_id="exp1")
    assert not result.ok and result.decision == "resume_not_possible"
    assert client.calls == []


# --- Property 13: group-scoped comparison -------------------------------- #
def test_property_13_compare_group(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 13: Comparison scoped to one group.

    **Validates: Requirements 8.1, 8.2**
    """
    client = TW.FakeWandbClient({
        "fetch_group_metrics": [
            TW.RunMetrics(run_id="a", summary={"acc": 0.9}),
            TW.RunMetrics(run_id="b", summary={"acc": 0.8}),
        ],
    })
    result = TW.compare_runs(client, _settings(), "exp1")
    assert result.ok and not result.empty
    ids = {r["wandb_run_id"] for r in result.runs}
    assert ids == {"a", "b"}
    assert result.runs[0]["metrics"]["acc"] == 0.9


def test_property_13_empty_comparison(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 13: Comparison scoped to one group.

    **Validates: Requirements 8.3**
    """
    client = TW.FakeWandbClient({"fetch_group_metrics": []})
    result = TW.compare_runs(client, _settings(), "exp1")
    assert result.ok and result.empty and result.runs == []


# --- Property 15: wandb_status distinct, never changes run status -------- #
def test_property_15_sync_failure_preserves_status(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 15: W&B status distinct from training status.

    **Validates: Requirements 9.3, 9.5, 13.2**
    """
    run_dir = _run_dir(tmp_path, {"status": "succeeded", "wandb_run_id": "r1"})
    client = TW.FakeWandbClient({"sync_state": "failed"})
    result = TW.check_sync(client, run_dir, _settings(), mode_decision=None)
    assert result.wandb_status == TW.WandbStatus.SYNC_FAILED
    TW.write_wandb_linkage(run_dir, {"wandb_status": result.wandb_status.value})
    loaded = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    assert loaded["status"] == "succeeded"  # training status untouched
    assert loaded["wandb_status"] == "sync_failed"


def test_sync_offline_mode(tmp_path: Path) -> None:
    """**Validates: Requirements 9.4**"""
    run_dir = _run_dir(tmp_path, {"status": "succeeded"})
    client = TW.FakeWandbClient({})  # offline => no client call
    s = _settings(mode="offline")
    result = TW.check_sync(client, run_dir, s, mode_decision=TW.resolve_mode(s, s.entity))
    assert result.wandb_status == TW.WandbStatus.OFFLINE
    assert client.calls == []


# --- Property 18: read-only actions ungated ------------------------------ #
def test_property_18_url_parse_ungated(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 18: Read-only actions are ungated.

    **Validates: Requirements 10.1, 11.4**
    """
    # parse/extract need no client and no approval
    url = "https://wandb.ai/my-lab/proj/runs/zzz"
    assert TW.extract_run_id_from_url(TW.parse_wandb_url(f"see {url}")) == "zzz"


# --- Property 12: writes confined to run dir ----------------------------- #
def test_property_12_linkage_confined(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 12: W&B writes confined to run dir.

    **Validates: Requirements 7.4, 13.4**
    """
    run_dir = _run_dir(tmp_path)
    other = tmp_path / "experiments" / "exp1" / "runs" / "run-002"
    other.mkdir(parents=True)
    (other / "run.yaml").write_text(yaml.safe_dump({"status": "x"}), encoding="utf-8")
    before = (other / "run.yaml").read_text(encoding="utf-8")
    TW.write_wandb_linkage(run_dir, {"wandb_status": "running"})
    assert (other / "run.yaml").read_text(encoding="utf-8") == before


# --- Property 20: run.yaml linkage completeness -------------------------- #
def test_property_20_linkage_completeness(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 20: run.yaml linkage completeness.

    **Validates: Requirements 1.4, 5.3, 13.1**
    """
    run_dir = _run_dir(tmp_path)
    TW.write_wandb_linkage(run_dir, {
        "wandb_run_id": "r1", "wandb_url": "u", "wandb_group": "exp1",
        "wandb_tags": ["method:lora"], "wandb_status": "running",
        "wandb_mode": "online", "git_sha": "abc",
    })
    loaded = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    for key in ("wandb_run_id", "wandb_url", "wandb_group", "wandb_tags",
                "wandb_status", "wandb_mode", "git_sha"):
        assert key in loaded


def test_linkage_drops_credentials(tmp_path: Path) -> None:
    """**Validates: Requirements 13.3, 14.2**"""
    run_dir = _run_dir(tmp_path)
    TW.write_wandb_linkage(run_dir, {"wandb_run_id": "r1",
                                      "WANDB_API_KEY": "supersecret"})
    text = (run_dir / "run.yaml").read_text(encoding="utf-8")
    assert "supersecret" not in text and "WANDB_API_KEY" not in text


# --- Property 22: end-to-end CLI create flow ----------------------------- #
def _plan(tmp_path: Path, entity="my-lab", mode="online") -> Path:
    p = tmp_path / "project-plan.md"
    p.write_text(
        f"---\nwandb:\n  entity: {entity}\n  project: proj\n  mode: {mode}\n"
        f"  keep_local_data: true\n---\n# plan\n", encoding="utf-8")
    return p


def test_property_22_cli_create_envelope(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 22: Output envelope and exit-code mapping.

    **Validates: Requirements 15.1, 15.2**
    """
    plan = _plan(tmp_path)
    run_dir = _run_dir(tmp_path, {"status": "succeeded"})
    (run_dir / "resolved-job.yaml").write_text(
        yaml.safe_dump({"method": "lora", "lora_rank": 8}), encoding="utf-8")
    exp_plan = tmp_path / "experiments" / "exp1" / "plan.md"
    exp_plan.write_text("---\napproval:\n  status: approved\n---\n", encoding="utf-8")

    client = TW.FakeWandbClient({
        "create_run": TW.CreatedRun(run_id="xyz", url="https://wandb.ai/my-lab/proj/runs/xyz"),
    })
    args = argparse.Namespace(command="create", plan_file=str(plan),
                              run_dir=str(run_dir), experiment_plan=str(exp_plan),
                              experiment_id="exp1", workspace=str(tmp_path), group=None)
    result = TW.run_cli(args, client_factory=lambda s: client)
    for key in ("status", "message", "data", "errors", "warnings"):
        assert key in result
    assert result["status"] == "success"
    assert result["data"]["wandb_run_id"] == "xyz"
    loaded = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    assert loaded["wandb_run_id"] == "xyz"
    assert loaded["wandb_status"] == "running"
    assert loaded["status"] == "succeeded"  # training status untouched


def test_cli_invalid_mode_declines(tmp_path: Path) -> None:
    """Feature: phase-7-wandb, Property 22: Output envelope and exit-code mapping.

    **Validates: Requirements 1.2, 15.3**
    """
    plan = _plan(tmp_path, mode="bogus")
    run_dir = _run_dir(tmp_path)
    args = argparse.Namespace(command="create", plan_file=str(plan),
                              run_dir=str(run_dir), experiment_plan=None,
                              experiment_id="exp1", workspace=str(tmp_path), group=None)
    result = TW.run_cli(args, client_factory=lambda s: TW.FakeWandbClient({}))
    assert result["status"] == "error"
    assert result["data"]["decision"] == "config_error"
