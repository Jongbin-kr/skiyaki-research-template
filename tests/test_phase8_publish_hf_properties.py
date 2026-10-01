"""Property tests for the Phase 8 Hugging Face Hub publisher (publish_hf.py).

Feature: phase-8-huggingface

Pure-logic properties (settings loading, placeholder tolerance, push eligibility,
repo-id/url construction, visibility guard, status mapping, approval gating,
redaction, model card, commit-candidate exclusion) are exercised with Hypothesis.
The module is loaded by path, matching the Phase 5/6/7 suites. No test performs a
real Hub API call, upload, verification, or network I/O.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from hypothesis import given, settings, strategies as st
import pytest

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


# Property 1 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    namespace=st.text(max_size=20),
    policy=st.sampled_from(list(PH.VALID_POLICIES)),
    private=st.one_of(st.none(), st.booleans()),
)
def test_property_1_settings_private_default(namespace, policy, private) -> None:
    """Feature: phase-8-huggingface, Property 1: Settings loading, private defaults true.

    **Validates: Requirements 1.1, 1.4**
    """
    hf: dict = {"namespace": namespace, "push_policy": policy}
    if private is not None:
        hf["private"] = private
    s = PH.load_hf_settings({"huggingface": hf})
    assert s.namespace == namespace and s.push_policy == policy
    assert s.private == (True if private is None else private)


# Property 2 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(policy=st.text(max_size=15), kind=st.sampled_from(list(PH.CheckpointKind)))
def test_property_2_invalid_policy(policy, kind) -> None:
    """Feature: phase-8-huggingface, Property 2: Invalid push policy is a config error.

    **Validates: Requirements 1.2**
    """
    d = PH.decide_push(policy, kind)
    assert d.config_error == (policy not in PH.VALID_POLICIES)
    if d.config_error:
        assert not d.eligible


# Property 3 -------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(ns=st.text(max_size=24))
def test_property_3_placeholder(ns) -> None:
    """Feature: phase-8-huggingface, Property 3: Placeholder-namespace tolerance.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    assert PH.is_placeholder_namespace(ns) == (ns.strip() == PH.PLACEHOLDER_NAMESPACE)


# Property 4 -------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(policy=st.sampled_from(list(PH.VALID_POLICIES)),
       kind=st.sampled_from(list(PH.CheckpointKind)))
def test_property_4_push_matrix(policy, kind) -> None:
    """Feature: phase-8-huggingface, Property 4: Push eligibility across policy×kind.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
    """
    d = PH.decide_push(policy, kind)
    expected = {
        "never": set(),
        "final_only": {PH.CheckpointKind.FINAL},
        "final_and_milestone": {PH.CheckpointKind.FINAL, PH.CheckpointKind.MILESTONE},
        "milestone": {PH.CheckpointKind.MILESTONE, PH.CheckpointKind.FINAL},
        "every_save": set(PH.CheckpointKind),
    }[policy]
    assert d.eligible == (kind in expected)
    # intermediate eligible only under every_save
    if kind == PH.CheckpointKind.INTERMEDIATE:
        assert d.eligible == (policy == "every_save")


# Property 7 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(ns=st.from_regex(r"[a-z0-9-]{1,15}", fullmatch=True),
       name=st.from_regex(r"[a-z0-9-]{1,15}", fullmatch=True))
def test_property_7_repo_id(ns, name) -> None:
    """Feature: phase-8-huggingface, Property 7: Repository id construction.

    **Validates: Requirements 5.1**
    """
    assert PH.build_repo_id(ns, name) == f"{ns}/{name}"


# Property 9 -------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    private=st.booleans(),
    requested=st.sampled_from(list(PH.Visibility)),
    approval=st.one_of(st.none(), st.just("approved"), st.text(max_size=8)),
)
def test_property_9_visibility_guard(private, requested, approval) -> None:
    """Feature: phase-8-huggingface, Property 9: Visibility never silently public.

    **Validates: Requirements 6.1, 6.2, 6.3**
    """
    current = PH.resolve_visibility(private)
    assert current == (PH.Visibility.PRIVATE if private else PH.Visibility.PUBLIC)
    decision = PH.guard_visibility_change(current, requested, approval)
    approved = bool(approval and str(approval).strip().lower() == "approved")
    if current == PH.Visibility.PRIVATE and requested == PH.Visibility.PUBLIC and not approved:
        assert decision == PH.VisDecision.DECLINE_SILENT_PUBLIC
    elif approved:
        assert decision == PH.VisDecision.PROCEED
    else:
        assert decision == PH.VisDecision.DECLINE_APPROVAL


# Property 10 ------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(approval=st.one_of(st.none(), st.just("approved"), st.just("pending"), st.text(max_size=8)),
       kind=st.sampled_from(list(PH.MUTATING_KINDS)))
def test_property_10_approval_gating(approval, kind) -> None:
    """Feature: phase-8-huggingface, Property 10: Mutating actions iff approved.

    **Validates: Requirements 7.1, 7.2, 7.5, 11.1, 11.2, 11.3**
    """
    d = PH.decide_mutating_action(approval, kind)
    if approval and str(approval).strip().lower() == "approved":
        assert d == PH.ActionDecision.PROCEED
    else:
        assert d == PH.ActionDecision.DECLINE_APPROVAL


# Status mapping (supports Properties 12/14) ------------------------------ #
@settings(max_examples=120, deadline=None)
@given(raw=st.sampled_from(["uploaded", "completed", "verified", "located",
                            "failed", "error", "weird", ""]))
def test_hf_status_mapping(raw) -> None:
    """Feature: phase-8-huggingface, Property 14 (status mapping helper).

    **Validates: Requirements 9.2, 9.3**
    """
    status = PH.map_hf_status(raw)
    assert isinstance(status, PH.HfStatus)
    if raw in ("uploaded", "completed"):
        assert status == PH.HfStatus.UPLOADED
    elif raw in ("verified", "located"):
        assert status == PH.HfStatus.VERIFIED
    else:
        assert status == PH.HfStatus.UPLOAD_FAILED


# Property 15 ------------------------------------------------------------- #
@settings(max_examples=80, deadline=None)
@given(
    ns=st.from_regex(r"[a-z-]{1,10}", fullmatch=True),
    name=st.from_regex(r"[a-z-]{1,10}", fullmatch=True),
    kind=st.sampled_from(list(PH.CheckpointKind)),
    secret=st.text(alphabet="ABCDEF0123456789", min_size=6, max_size=16),
)
def test_property_15_model_card(ns, name, kind, secret) -> None:
    """Feature: phase-8-huggingface, Property 15: Model card assembled locally.

    **Validates: Requirements 10.1, 10.2, 10.3**
    """
    repo_id = PH.build_repo_id(ns, name)
    config = {"learning_rate": 0.01, "HF_TOKEN": secret}
    card = PH.build_model_card(repo_id, kind.value, config)
    assert repo_id in card
    assert kind.value in card
    assert secret not in card  # credential dropped
    assert "learning_rate" in card


# Property 19 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(secret=st.text(alphabet="ABCDEF0123456789", min_size=6, max_size=20))
def test_property_19_no_secrets(secret) -> None:
    """Feature: phase-8-huggingface, Property 19: Artifacts contain no secrets.

    **Validates: Requirements 10.4, 13.3, 14.1, 14.2, 14.3**
    """
    config = {"HF_TOKEN": secret, "HUGGINGFACEHUB_API_TOKEN": secret,
              "lr": 0.1, "nested": {"SECRET_KEY": secret, "epochs": 2}}
    red = PH.redact_config(config)
    assert secret not in str(red)
    assert "HF_TOKEN" not in red and "HUGGINGFACEHUB_API_TOKEN" not in red
    assert "SECRET_KEY" not in red["nested"]
    assert red["nested"]["epochs"] == 2
    text = PH.redact_secrets(f"token={secret} lr=0.1", {"HF_TOKEN": secret})
    assert secret not in text


# Property 21 ------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(paths=st.lists(st.from_regex(
    r"[a-z/]{1,8}(/(checkpoints|wandb))?/[a-z]{1,6}\.(out|err|yaml|json|md|safetensors)",
    fullmatch=True), max_size=12))
def test_property_21_commit_filter(paths) -> None:
    """Feature: phase-8-huggingface, Property 21: Commit candidates exclude logs/ckpts/caches.

    **Validates: Requirements 16.3, 16.4**
    """
    for p in PH.filter_commit_candidates(paths):
        assert not p.endswith((".out", ".err"))
        assert "checkpoints" not in p.split("/")
        assert "wandb" not in p.split("/")
