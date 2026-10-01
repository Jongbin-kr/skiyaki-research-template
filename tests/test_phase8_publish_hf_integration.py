"""Integration tests for the Phase 8 Hugging Face Hub publisher (publish_hf.py).

Feature: phase-8-huggingface

Exercises orchestration wiring (verify checkpoint, ensure repo, upload, verify
upload, model card, run.yaml linkage, publish) with a FakeHfClient. No real Hub
API call, upload, verification, or network I/O ever occurs. All writes are
confined to tmp_path; the example experiment stays read-only. Covers design
Properties 5, 6, 8, 12, 13, 14, 16, 17, 18, 20 and the injection guard.
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
    WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts" / "publish_hf.py"
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("publish_hf", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.modules["publish_hf"] = module
    spec.loader.exec_module(module)
    return module


PH = _load_module()


def _settings(ns="my-lab", private=True, policy="final_and_milestone"):
    return PH.HfSettings(namespace=ns, private=private, push_policy=policy)


def _run_dir(tmp_path: Path, record=None) -> Path:
    d = tmp_path / "experiments" / "exp1" / "runs" / "run-001"
    d.mkdir(parents=True)
    (d / "run.yaml").write_text(yaml.safe_dump(record or {"status": "succeeded"}),
                                encoding="utf-8")
    return d


# --- injection guard ----------------------------------------------------- #
def test_fake_client_raises_on_unscripted() -> None:
    c = PH.FakeHfClient({})
    with pytest.raises(AssertionError):
        c.repo_exists(repo_id="x/y")


def test_real_client_not_imported_in_tests() -> None:
    """Property 16: Injected-boundary discipline.

    **Feature: phase-8-huggingface, Property 16: Injected-boundary discipline**
    **Validates: Requirements 12.1, 12.3, 12.4**
    """
    assert hasattr(PH, "RealHfClient")
    assert PH._build_client.__name__ == "_build_client"
    import sys
    assert "huggingface_hub" not in sys.modules


# --- Property 6: checkpoint verification gating -------------------------- #
def test_property_6_missing_checkpoint(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 6: Local checkpoint verification gates upload.

    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    result = PH.verify_checkpoint(str(tmp_path / "nope"))
    assert not result.ok and result.errors


def test_property_6_present_checkpoint(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 6: Local checkpoint verification gates upload.

    **Validates: Requirements 4.1, 4.3**
    """
    cp = tmp_path / "ckpt"
    cp.mkdir()
    result = PH.verify_checkpoint(str(cp))
    assert result.ok and result.path


# --- Property 8: repo existence + approval-gated create ------------------ #
def test_property_8_repo_exists(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 8: Repo existence check + approval-gated create.

    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    client = PH.FakeHfClient({"repo_exists": PH.RepoInfo(exists=True, private=True)})
    result = PH.ensure_repo(client, "my-lab/r", private=True, approval_status="approved")
    assert result.ok and not result.created
    assert all(c["op"] != "create_repo" for c in client.calls)


def test_property_8_repo_missing_creates_when_approved(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 8: Repo existence check + approval-gated create.

    **Validates: Requirements 5.3**
    """
    client = PH.FakeHfClient({
        "repo_exists": PH.RepoInfo(exists=False),
        "create_repo": PH.RepoInfo(exists=True, private=True),
    })
    result = PH.ensure_repo(client, "my-lab/r", private=True, approval_status="approved")
    assert result.ok and result.created
    assert any(c["op"] == "create_repo" for c in client.calls)


def test_property_8_repo_missing_declines_without_approval(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 8: Repo existence check + approval-gated create.

    **Validates: Requirements 5.4**
    """
    client = PH.FakeHfClient({"repo_exists": PH.RepoInfo(exists=False)})
    result = PH.ensure_repo(client, "my-lab/r", private=True, approval_status="pending")
    assert not result.ok and result.decision == "approval_required"
    assert all(c["op"] != "create_repo" for c in client.calls)


# --- Property 5: skip by policy ------------------------------------------ #
def test_property_5_skip_by_policy(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 5: Ineligible checkpoints skipped by policy.

    **Validates: Requirements 3.7**
    """
    client = PH.FakeHfClient({})  # any call raises
    result = PH.upload_checkpoint(client, "my-lab/r", str(tmp_path),
                                  _settings(policy="final_only"),
                                  PH.CheckpointKind.INTERMEDIATE, approval_status="approved")
    assert not result.ok and result.decision == "skipped_by_policy"
    assert result.hf_status == PH.HfStatus.SKIPPED_BY_POLICY
    assert client.calls == []


# --- Property 12: completed upload records revision ---------------------- #
def test_property_12_upload_records_revision(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 12: Completed upload records identity + revision.

    **Validates: Requirements 7.3, 8.1, 8.2**
    """
    client = PH.FakeHfClient({
        "upload_checkpoint": PH.UploadOutcome(revision="9c1f2a0b", repo_id="my-lab/r"),
    })
    result = PH.upload_checkpoint(client, "my-lab/r", str(tmp_path), _settings(),
                                  PH.CheckpointKind.FINAL, approval_status="approved")
    assert result.ok and result.revision == "9c1f2a0b"
    assert result.hf_status == PH.HfStatus.UPLOADED


# --- Property 13: upload failure keeps training status ------------------- #
def test_property_13_upload_failure_preserves_status(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 13: Upload failure keeps training status.

    **Validates: Requirements 7.4, 8.3, 9.4, 13.2, 16.5**
    """
    def _raise(**kwargs):
        raise RuntimeError("network down")

    run_dir = _run_dir(tmp_path, {"status": "succeeded"})
    client = PH.FakeHfClient({"upload_checkpoint": _raise})
    result = PH.upload_checkpoint(client, "my-lab/r", str(tmp_path), _settings(),
                                  PH.CheckpointKind.FINAL, approval_status="approved")
    assert not result.ok and result.hf_status == PH.HfStatus.UPLOAD_FAILED
    PH.write_hf_linkage(run_dir, {"hf_status": result.hf_status.value})
    loaded = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    assert loaded["status"] == "succeeded"  # training status untouched
    assert loaded["hf_status"] == "upload_failed"


def test_upload_declined_without_approval(tmp_path: Path) -> None:
    """**Validates: Requirements 7.5**"""
    client = PH.FakeHfClient({})
    result = PH.upload_checkpoint(client, "my-lab/r", str(tmp_path), _settings(),
                                  PH.CheckpointKind.FINAL, approval_status="pending")
    assert not result.ok and result.decision == "approval_required"
    assert client.calls == []


def test_upload_declined_on_placeholder(tmp_path: Path) -> None:
    """**Validates: Requirements 2.2**"""
    client = PH.FakeHfClient({})
    result = PH.upload_checkpoint(client, "x/r", str(tmp_path),
                                  _settings(ns=PH.PLACEHOLDER_NAMESPACE),
                                  PH.CheckpointKind.FINAL, approval_status="approved")
    assert not result.ok and result.decision == "placeholder_namespace"
    assert client.calls == []


# --- Property 14: verify-by-revision ------------------------------------- #
def test_property_14_verify_located(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 14: Verify-by-revision located => verified.

    **Validates: Requirements 9.1, 9.2**
    """
    client = PH.FakeHfClient({"file_exists_at_revision": True})
    result = PH.verify_upload(client, "my-lab/r", "9c1f2a0b")
    assert result.ok and result.hf_status == PH.HfStatus.VERIFIED
    assert not result.experiment_incomplete


def test_property_14_verify_unlocatable(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 14: Verify-by-revision unlocatable => failed.

    **Validates: Requirements 9.3**
    """
    client = PH.FakeHfClient({"file_exists_at_revision": False})
    result = PH.verify_upload(client, "my-lab/r", "9c1f2a0b")
    assert not result.ok and result.hf_status == PH.HfStatus.UPLOAD_FAILED
    assert result.experiment_incomplete


# --- Property 17/18: linkage completeness + confinement ------------------ #
def test_property_17_linkage_completeness(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 17: run.yaml linkage completeness.

    **Validates: Requirements 1.3, 6.4, 10.3, 13.1**
    """
    run_dir = _run_dir(tmp_path)
    PH.write_hf_linkage(run_dir, {
        "hf_repo_id": "my-lab/r", "hf_revision": "abc", "hf_url": "u",
        "hf_status": "verified", "hf_private": True, "model_card_path": "p",
    })
    loaded = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    for key in ("hf_repo_id", "hf_revision", "hf_url", "hf_status", "hf_private",
                "model_card_path"):
        assert key in loaded


def test_property_18_linkage_confined(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 18: Hub linkage writes confined to run.

    **Validates: Requirements 13.4**
    """
    run_dir = _run_dir(tmp_path)
    other = tmp_path / "experiments" / "exp1" / "runs" / "run-002"
    other.mkdir(parents=True)
    (other / "run.yaml").write_text(yaml.safe_dump({"status": "x"}), encoding="utf-8")
    before = (other / "run.yaml").read_text(encoding="utf-8")
    PH.write_hf_linkage(run_dir, {"hf_status": "uploaded"})
    assert (other / "run.yaml").read_text(encoding="utf-8") == before


def test_linkage_drops_credentials(tmp_path: Path) -> None:
    """**Validates: Requirements 13.3, 14.2**"""
    run_dir = _run_dir(tmp_path)
    PH.write_hf_linkage(run_dir, {"hf_repo_id": "r", "HF_TOKEN": "supersecret"})
    text = (run_dir / "run.yaml").read_text(encoding="utf-8")
    assert "supersecret" not in text and "HF_TOKEN" not in text


# --- Property 20: end-to-end publish via CLI ----------------------------- #
def _plan(tmp_path: Path, ns="my-lab", policy="final_and_milestone") -> Path:
    p = tmp_path / "project-plan.md"
    p.write_text(
        f"---\nhuggingface:\n  namespace: {ns}\n  private: true\n"
        f"  push_policy: {policy}\n---\n# plan\n", encoding="utf-8")
    return p


def test_property_20_publish_cli(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 20: Output envelope and exit-code mapping.

    **Validates: Requirements 15.1, 15.2**
    """
    plan = _plan(tmp_path)
    run_dir = _run_dir(tmp_path, {"status": "succeeded"})
    (run_dir / "resolved-job.yaml").write_text(
        yaml.safe_dump({"method": "lora", "HF_TOKEN": "sekret"}), encoding="utf-8")
    ckpt = run_dir / "checkpoints" / "final"
    ckpt.mkdir(parents=True)
    (ckpt / "model.safetensors").write_text("weights", encoding="utf-8")
    exp_plan = tmp_path / "experiments" / "exp1" / "plan.md"
    exp_plan.write_text("---\napproval:\n  status: approved\n---\n", encoding="utf-8")

    client = PH.FakeHfClient({
        "repo_exists": PH.RepoInfo(exists=False),
        "create_repo": PH.RepoInfo(exists=True, private=True),
        "upload_checkpoint": PH.UploadOutcome(revision="deadbeef", repo_id="my-lab/exp1"),
        "file_exists_at_revision": True,
    })
    args = argparse.Namespace(command="publish", plan_file=str(plan),
                              run_dir=str(run_dir), experiment_plan=str(exp_plan),
                              checkpoint=str(ckpt), repo_name=None, kind="final")
    result = PH.run_cli(args, client_factory=lambda s: client)
    for key in ("status", "message", "data", "errors", "warnings"):
        assert key in result
    assert result["status"] == "success"
    assert result["data"]["hf_revision"] == "deadbeef"
    assert result["data"]["hf_status"] == "verified"
    loaded = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    assert loaded["hf_status"] == "verified"
    assert loaded["status"] == "succeeded"  # training status untouched
    card = (run_dir / "MODEL_CARD.md").read_text(encoding="utf-8")
    assert "sekret" not in card  # credential dropped from model card


def test_cli_invalid_policy_declines(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 20: Output envelope and exit-code mapping.

    **Validates: Requirements 1.2, 15.3**
    """
    plan = _plan(tmp_path, policy="bogus")
    run_dir = _run_dir(tmp_path)
    args = argparse.Namespace(command="publish", plan_file=str(plan),
                              run_dir=str(run_dir), experiment_plan=None,
                              checkpoint=str(tmp_path), repo_name=None, kind="final")
    result = PH.run_cli(args, client_factory=lambda s: PH.FakeHfClient({}))
    assert result["status"] == "error"
    assert result["data"]["decision"] == "config_error"


def test_cli_publish_unverified_experiment_incomplete(tmp_path: Path) -> None:
    """Feature: phase-8-huggingface, Property 14/20: unverified => experiment incomplete.

    **Validates: Requirements 9.3, 15.3**
    """
    plan = _plan(tmp_path)
    run_dir = _run_dir(tmp_path, {"status": "succeeded"})
    ckpt = run_dir / "ckpt"
    ckpt.mkdir()
    exp_plan = tmp_path / "experiments" / "exp1" / "plan.md"
    exp_plan.write_text("---\napproval:\n  status: approved\n---\n", encoding="utf-8")
    client = PH.FakeHfClient({
        "repo_exists": PH.RepoInfo(exists=True, private=True),
        "upload_checkpoint": PH.UploadOutcome(revision="rev1", repo_id="my-lab/exp1"),
        "file_exists_at_revision": False,  # not locatable
    })
    args = argparse.Namespace(command="publish", plan_file=str(plan),
                              run_dir=str(run_dir), experiment_plan=str(exp_plan),
                              checkpoint=str(ckpt), repo_name=None, kind="final")
    result = PH.run_cli(args, client_factory=lambda s: client)
    assert result["status"] == "error"
    assert result["data"]["experiment_incomplete"] is True
    loaded = yaml.safe_load((run_dir / "run.yaml").read_text(encoding="utf-8"))
    assert loaded["hf_status"] == "upload_failed"
    assert loaded["status"] == "succeeded"
