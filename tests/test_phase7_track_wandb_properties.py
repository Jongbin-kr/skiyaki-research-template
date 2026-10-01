"""Property tests for the Phase 7 W&B tracking helper (track_wandb.py).

Feature: phase-7-wandb

Pure-logic properties (settings loading, mode resolution, placeholder tolerance,
group/tag derivation, config redaction, local-dir path rule, URL parse/extract,
sync-state mapping, approval gating, git-sha fallback, commit-candidate
exclusion, secret safety) are exercised with Hypothesis. The module is loaded by
path, matching the Phase 5/6 suites. No test performs a real W&B API call, sync,
or network I/O.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

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


def _settings(entity="my-lab", mode="online", project="proj", keep=True):
    return TW.WandbSettings(entity=entity, project=project, mode=mode, keep_local_data=keep)


# Property 1 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    entity=st.text(max_size=20), project=st.text(max_size=20),
    mode=st.sampled_from(["online", "offline", "disabled", "weird"]),
    keep=st.booleans(),
)
def test_property_1_settings_loading(entity, project, mode, keep) -> None:
    """Feature: phase-7-wandb, Property 1: Settings loading reflects the project plan.

    **Validates: Requirements 1.1**
    """
    fm = {"wandb": {"entity": entity, "project": project, "mode": mode,
                    "keep_local_data": keep}}
    s = TW.load_wandb_settings(fm)
    assert s.entity == entity and s.project == project
    assert s.mode == mode and s.keep_local_data == keep


# Property 2 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(mode=st.text(max_size=12))
def test_property_2_invalid_mode(mode) -> None:
    """Feature: phase-7-wandb, Property 2: Invalid mode is a configuration error.

    **Validates: Requirements 1.2**
    """
    md = TW.resolve_mode(_settings(mode=mode), "my-lab")
    assert md.config_error == (mode not in TW.VALID_MODES)


# Property 3 -------------------------------------------------------------- #
@settings(max_examples=60, deadline=None)
@given(entity=st.sampled_from(["my-lab", TW.PLACEHOLDER_ENTITY]))
def test_property_3_disabled_no_mutation(entity) -> None:
    """Feature: phase-7-wandb, Property 3: Disabled mode performs no mutating action.

    **Validates: Requirements 1.3**
    """
    md = TW.resolve_mode(_settings(entity=entity, mode="disabled"), entity)
    assert md.effective == TW.EffectiveMode.DISABLED
    assert TW.map_sync_state("running", md.effective) == TW.WandbStatus.NOT_STARTED


# Property 4 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(mode=st.sampled_from(["online", "offline", "disabled"]))
def test_property_4_placeholder_tolerance(mode) -> None:
    """Feature: phase-7-wandb, Property 4: Placeholder-entity tolerance.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    assert TW.is_placeholder_entity(TW.PLACEHOLDER_ENTITY)
    md = TW.resolve_mode(_settings(entity=TW.PLACEHOLDER_ENTITY, mode=mode),
                         TW.PLACEHOLDER_ENTITY)
    if mode == "online":
        assert md.placeholder_online_declined and md.effective == TW.EffectiveMode.OFFLINE
    elif mode == "offline":
        assert md.effective == TW.EffectiveMode.OFFLINE
    else:
        assert md.effective == TW.EffectiveMode.DISABLED


# Property 7 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    exp=st.from_regex(r"[a-z0-9-]{1,20}", fullmatch=True),
    override=st.one_of(st.none(), st.from_regex(r"[a-z0-9-]{1,20}", fullmatch=True)),
)
def test_property_7_shared_group(exp, override) -> None:
    """Feature: phase-7-wandb, Property 7: Runs of one experiment share a group.

    **Validates: Requirements 5.1, 5.4**
    """
    job = {"wandb": {"group": override}} if override else {}
    g1 = TW.resolve_group(exp, job)
    g2 = TW.resolve_group(exp, dict(job))
    assert g1 == g2
    assert g1 == (override if override else exp)


# Property 8 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    tags=st.lists(st.from_regex(r"[a-z]{1,8}", fullmatch=True), max_size=5),
    method=st.one_of(st.none(), st.sampled_from(["lora", "full"])),
)
def test_property_8_deterministic_tags(tags, method) -> None:
    """Feature: phase-7-wandb, Property 8: Tag derivation is deterministic.

    **Validates: Requirements 5.2**
    """
    job = {"wandb": {"tags": tags}}
    if method:
        job["method"] = method
    t1 = TW.resolve_tags(job)
    t2 = TW.resolve_tags(dict(job))
    assert t1 == t2
    assert len(t1) == len(set(t1))  # de-duplicated


# Property 9 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(secret=st.text(alphabet="ABCDEF0123456789", min_size=4, max_size=20))
def test_property_9_config_credentials_dropped(secret) -> None:
    """Feature: phase-7-wandb, Property 9: Resolved config recorded with credentials dropped.

    **Validates: Requirements 6.1, 6.3**
    """
    job = {"learning_rate": 0.01, "HF_TOKEN": secret,
           "nested": {"WANDB_API_KEY": secret, "epochs": 3}}
    env = {"WANDB_API_KEY": secret, "PATH": "/usr/bin"}
    config = TW.build_run_config(job, env)
    flat = str(config)
    assert secret not in flat
    assert "HF_TOKEN" not in config
    assert "WANDB_API_KEY" not in config.get("nested", {})
    assert config["nested"]["epochs"] == 3
    assert "WANDB_API_KEY" not in config["_env_names"]
    assert "PATH" in config["_env_names"]


# Property 10 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(
    ok=st.booleans(),
    sha=st.from_regex(r"[0-9a-f]{40}", fullmatch=True),
    empty=st.booleans(),
)
def test_property_10_git_sha_fallback(ok, sha, empty) -> None:
    """Feature: phase-7-wandb, Property 10: Git SHA mapping with unknown fallback.

    **Validates: Requirements 6.2, 6.4**
    """
    stdout = "" if empty else sha
    result = TW.GitResult(0 if ok else 1, stdout)
    out_sha, warnings = TW.record_git_sha(result)
    if ok and not empty:
        assert out_sha == sha and warnings == []
    else:
        assert out_sha == TW.UNKNOWN_SHA and warnings


# Property 11 ------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    exp=st.from_regex(r"[a-z0-9-]{1,15}", fullmatch=True),
    run=st.from_regex(r"[a-z0-9_-]{1,25}", fullmatch=True),
)
def test_property_11_local_dir(exp, run) -> None:
    """Feature: phase-7-wandb, Property 11: Local W&B directory path rule.

    **Validates: Requirements 7.1**
    """
    assert TW.local_wandb_dir(exp, run) == f"experiments/{exp}/runs/{run}/wandb"


# Property 14 ------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    raw=st.sampled_from(["synced", "finished", "uploaded", "failed", "error",
                         "running", "offline", "weird", ""]),
    mode=st.sampled_from(list(TW.EffectiveMode)),
)
def test_property_14_sync_mapping(raw, mode) -> None:
    """Feature: phase-7-wandb, Property 14: Sync-state mapping is total and mode-aware.

    **Validates: Requirements 9.2, 9.4**
    """
    status = TW.map_sync_state(raw, mode)
    assert isinstance(status, TW.WandbStatus)
    if mode == TW.EffectiveMode.OFFLINE:
        assert status == TW.WandbStatus.OFFLINE
    elif mode == TW.EffectiveMode.DISABLED:
        assert status == TW.WandbStatus.NOT_STARTED
    elif raw in ("synced", "finished", "uploaded"):
        assert status == TW.WandbStatus.SYNCED
    elif raw == "running":
        assert status == TW.WandbStatus.RUNNING
    elif raw == "offline":
        # a run reporting an "offline" state maps to OFFLINE even in online mode
        assert status == TW.WandbStatus.OFFLINE
    else:
        assert status == TW.WandbStatus.SYNC_FAILED


# Property 16 ------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    run_id=st.from_regex(r"[a-z0-9]{4,12}", fullmatch=True),
    entity=st.from_regex(r"[a-z-]{1,10}", fullmatch=True),
    project=st.from_regex(r"[a-z-]{1,10}", fullmatch=True),
    pre=st.text(alphabet="abc \n", max_size=8),
)
def test_property_16_url_roundtrip(run_id, entity, project, pre) -> None:
    """Feature: phase-7-wandb, Property 16: W&B URL parse/extract round-trip.

    **Validates: Requirements 10.2, 10.3**
    """
    url = f"https://wandb.ai/{entity}/{project}/runs/{run_id}"
    text = f"{pre}View run at {url} more"
    parsed = TW.parse_wandb_url(text)
    assert parsed is not None
    assert TW.extract_run_id_from_url(parsed) == run_id


@settings(max_examples=80, deadline=None)
@given(text=st.text(max_size=50).filter(lambda t: "wandb.ai" not in t))
def test_property_16_url_absent(text) -> None:
    """Feature: phase-7-wandb, Property 16: W&B URL parse/extract round-trip.

    **Validates: Requirements 10.2, 10.3**
    """
    assert TW.parse_wandb_url(text) is None


# Property 17 ------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    approval=st.one_of(st.none(), st.just("approved"), st.just("pending"), st.text(max_size=8)),
    kind=st.sampled_from(list(TW.MUTATING_KINDS)),
)
def test_property_17_approval_gating(approval, kind) -> None:
    """Feature: phase-7-wandb, Property 17: Mutating actions iff approved.

    **Validates: Requirements 3.1, 3.4, 11.1, 11.2, 11.3**
    """
    decision = TW.decide_mutating_action(approval, kind)
    if approval and str(approval).strip().lower() == "approved":
        assert decision == TW.ActionDecision.PROCEED
    else:
        assert decision == TW.ActionDecision.DECLINE_APPROVAL


# Property 23 ------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(paths=st.lists(st.from_regex(
    r"[a-z/]{1,8}(/(checkpoints|wandb))?/[a-z]{1,6}\.(out|err|yaml|json|md|png)",
    fullmatch=True), max_size=12))
def test_property_23_commit_filter(paths) -> None:
    """Feature: phase-7-wandb, Property 23: Commit candidates exclude logs, checkpoints, caches.

    **Validates: Requirements 16.3**
    """
    for p in TW.filter_commit_candidates(paths):
        assert not p.endswith((".out", ".err"))
        assert "checkpoints" not in p.split("/")
        assert "wandb" not in p.split("/")


# Property 21 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(secret=st.text(alphabet="ABCDEF0123456789", min_size=6, max_size=24))
def test_property_21_no_secrets_in_text(secret) -> None:
    """Feature: phase-7-wandb, Property 21: Artifacts contain no secrets.

    **Validates: Requirements 13.3, 14.1, 14.2, 14.3**
    """
    env = {"WANDB_API_KEY": secret, "HF_TOKEN": secret, "PATH": "/usr/bin"}
    text = f"configuring run with key={secret} and path=/usr/bin"
    redacted = TW.redact_secrets(text, env)
    assert secret not in redacted
    assert "/usr/bin" in redacted  # non-credential value preserved
