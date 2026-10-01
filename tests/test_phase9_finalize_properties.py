"""Property tests for the Phase 9 finalize helper (finalize_experiment.py).

Feature: phase-9-finalize-git

Pure-logic properties (completeness verification, results validation, reference
verification, honesty assessment, results assembly, history/journal/project-log
assembly, commit-candidate selection/filtering, credential scan, commit message,
approval gating, redaction) are exercised with Hypothesis. The module is loaded
by path, matching the Phase 5-8 suites. No test performs a real git commit,
push, or network I/O.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from hypothesis import given, settings, strategies as st
import pytest

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


# Property 1 -------------------------------------------------------------- #
@settings(max_examples=150, deadline=None)
@given(
    present=st.dictionaries(st.sampled_from(list(FE._REQUIRED)), st.booleans()),
    approval=st.one_of(st.none(), st.just("approved"), st.text(max_size=8)),
)
def test_property_1_completeness(present, approval) -> None:
    """Feature: phase-9-finalize-git, Property 1: Completeness verification is pure.

    **Validates: Requirements 1.1, 1.2, 1.4**
    """
    result = FE.verify_completeness(present, approval)
    missing = [k for k in FE._REQUIRED if not present.get(k, False)]
    approved = bool(approval and str(approval).strip().lower() == "approved")
    assert result.missing == missing
    assert result.approval_granted == approved
    assert result.ok == (not missing and approved)


# Property 3 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    run_ids=st.lists(st.from_regex(r"[a-z0-9-]{1,10}", fullmatch=True), min_size=1, max_size=5),
    pick_existing=st.booleans(),
)
def test_property_3_results_reference(run_ids, pick_existing) -> None:
    """Feature: phase-9-finalize-git, Property 3: Results reference an existing run.

    **Validates: Requirements 2.1, 2.2**
    """
    best = run_ids[0] if pick_existing else "nonexistent-xyz"
    results = {"best_run": {"run_id": best}, "primary_metric": {"value": 0.9}}
    v = FE.validate_results(results, run_ids)
    assert v.best_run_exists == (best in set(run_ids))


# Property 4 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(value=st.one_of(st.floats(allow_nan=False, allow_infinity=False),
                       st.integers(), st.booleans(), st.text(max_size=5), st.none()))
def test_property_4_numeric_metric(value) -> None:
    """Feature: phase-9-finalize-git, Property 4: Primary metric must be numeric.

    **Validates: Requirements 2.3, 2.4**
    """
    results = {"best_run": {"run_id": "r"}, "primary_metric": {"value": value}}
    v = FE.validate_results(results, ["r"])
    is_num = isinstance(value, (int, float)) and not isinstance(value, bool)
    assert v.metric_numeric == is_num


# Property 6 -------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    metric=st.one_of(st.floats(allow_nan=False, allow_infinity=False), st.none()),
    has_artifact=st.booleans(),
)
def test_property_6_no_success_without_evidence(metric, has_artifact) -> None:
    """Feature: phase-9-finalize-git, Property 6: No success without verified artifact and metric.

    **Validates: Requirements 3.4**
    """
    artifacts = {"checkpoint": "my-lab/r"} if has_artifact else {}
    linkage = {"hf_repo_id": "my-lab/r"} if has_artifact else {}
    results = {"primary_metric": {"value": metric}, "artifacts": artifacts}
    ref = FE.verify_references(results, linkage, {})
    metric_ok = isinstance(metric, (int, float)) and not isinstance(metric, bool)
    assert ref.success_claimable == (metric_ok and has_artifact)


# Property 20 ------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(
    failed=st.booleans(), documented=st.booleans(),
)
def test_property_20_failed_run_honesty(failed, documented) -> None:
    """Feature: phase-9-finalize-git, Property 20: Failed run documented, success not met.

    **Validates: Requirements 13.1, 13.2**
    """
    statuses = {"r1": "failed" if failed else "succeeded"}
    h = FE.assess_honesty(statuses, documented=documented, hf_statuses=["verified"])
    if failed:
        assert not h.success_allowed
        assert h.ok == documented
    else:
        assert h.success_allowed


# Property 21 ------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(hf=st.sampled_from(["verified", "uploaded", "upload_failed", "skipped_by_policy",
                           "not_started"]))
def test_property_21_hf_unverified_blocks(hf) -> None:
    """Feature: phase-9-finalize-git, Property 21: Unverified Hub upload blocks completion.

    **Validates: Requirements 13.3**
    """
    h = FE.assess_honesty({"r1": "succeeded"}, documented=True, hf_statuses=[hf])
    blocking = hf not in ("verified", "skipped_by_policy", "not_started")
    assert h.experiment_complete == (not blocking)


# Property 10 + 12 -------------------------------------------------------- #
@settings(max_examples=80, deadline=None)
@given(exp=st.from_regex(r"[a-z0-9-]{1,12}", fullmatch=True))
def test_property_10_project_log_top_insert(exp) -> None:
    """Feature: phase-9-finalize-git, Property 10: Project-log entry inserted at top.

    **Validates: Requirements 7.1, 7.2**
    """
    existing = ("# Project Log\n\n## [2026-01-01] — older-exp\n\n- old\n\n---\n")
    entry = FE.build_project_log_entry(exp, "concl", "run-1", {"acc": 0.9})
    out = FE.insert_project_log_entry(existing, entry, exp)
    # new entry's header must appear before the older one
    assert out.index(f"— {exp}") < out.index("— older-exp")


@settings(max_examples=60, deadline=None)
@given(exp=st.from_regex(r"[a-z]{3,10}", fullmatch=True))
def test_property_12_project_log_update_existing(exp) -> None:
    """Feature: phase-9-finalize-git, Property 12: Existing entry updated not duplicated.

    **Validates: Requirements 7.4**
    """
    first = FE.build_project_log_entry(exp, "first", "run-1", {"acc": 0.5})
    existing = "# Project Log\n\n" + first
    second = FE.build_project_log_entry(exp, "second", "run-2", {"acc": 0.9})
    out = FE.insert_project_log_entry(existing, second, exp)
    # Only one header for this experiment.
    assert out.count(f"— {exp}") == 1
    assert "second" in out and "first" not in out


# Property 11 ------------------------------------------------------------- #
@settings(max_examples=80, deadline=None)
@given(exp=st.from_regex(r"[a-z-]{1,12}", fullmatch=True))
def test_property_11_project_log_concise(exp) -> None:
    """Feature: phase-9-finalize-git, Property 11: Project-log entry is concise.

    **Validates: Requirements 7.3**
    """
    entry = FE.build_project_log_entry(exp, "one-line", "run-1",
                                       {"acc": 0.9, "f1": 0.8})
    non_empty = [l for l in entry.splitlines() if l.strip()]
    assert len(non_empty) <= FE.PROJECT_LOG_ENTRY_MAX_LINES


# Property 15 ------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(paths=st.lists(st.from_regex(
    r"[a-z/]{1,8}(/(checkpoints|wandb))?/[a-z]{1,6}\.(out|err|yaml|md|pt|bin|safetensors|ckpt)",
    fullmatch=True), max_size=12))
def test_property_15_commit_exclusions(paths) -> None:
    """Feature: phase-9-finalize-git, Property 15: Commit candidate excludes ckpts/caches/logs.

    **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    """
    for p in FE.filter_commit_candidates(paths):
        assert not p.endswith((".out", ".err", ".pt", ".bin", ".safetensors", ".ckpt"))
        assert "checkpoints" not in p.split("/")
        assert "wandb" not in p.split("/")


# Property 16 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(extra=st.lists(st.sampled_from([".env", "a.token", "credentials.json",
                                       "key.pem", "normal.yaml", "run.yaml"]), max_size=6))
def test_property_16_credential_scan(extra) -> None:
    """Feature: phase-9-finalize-git, Property 16: Credential files are detected.

    **Validates: Requirements 10.1, 10.2, 10.3**
    """
    paths = [f"experiments/e/{name}" for name in extra]
    found = FE.scan_for_credential_files(paths)
    for p in paths:
        name = p.split("/")[-1]
        cred = (name in (".env", "credentials.json") or name.endswith(".token")
                or name.endswith(".pem") or name.endswith(".key"))
        assert (p in found) == cred


# Property 17 ------------------------------------------------------------- #
@settings(max_examples=120, deadline=None)
@given(approval=st.one_of(st.none(), st.just("approved"), st.text(max_size=8)),
       kind=st.sampled_from(list(FE.MUTATING_KINDS)))
def test_property_17_approval_gating(approval, kind) -> None:
    """Feature: phase-9-finalize-git, Property 17: Mutating git actions iff approved.

    **Validates: Requirements 11.1, 11.2, 11.3, 11.5**
    """
    d = FE.decide_mutating_action(approval, kind)
    if approval and str(approval).strip().lower() == "approved":
        assert d == FE.ActionDecision.PROCEED
    else:
        assert d == FE.ActionDecision.DECLINE_APPROVAL


# Property 14 ------------------------------------------------------------- #
@settings(max_examples=80, deadline=None)
@given(
    exp=st.from_regex(r"[a-z-]{1,12}", fullmatch=True),
    value=st.floats(allow_nan=False, allow_infinity=False),
    met=st.booleans(),
)
def test_property_14_commit_message(exp, value, met) -> None:
    """Feature: phase-9-finalize-git, Property 14: Commit message surfaces identity/metric/success/linkage.

    **Validates: Requirements 8.2**
    """
    linkage = {"wandb_url": "https://wandb.ai/x", "hf_repo_id": "lab/r",
               "HF_TOKEN": "secret"}
    msg = FE.build_commit_message(exp, "acc", value, met, linkage)
    assert exp in msg
    assert "acc = " in msg
    assert ("Met" in msg)
    assert "secret" not in msg  # credential dropped
    assert "lab/r" in msg


# Property 24 ------------------------------------------------------------- #
@settings(max_examples=100, deadline=None)
@given(secret=st.text(alphabet="ABCDEF0123456789", min_size=6, max_size=20))
def test_property_24_no_secrets(secret) -> None:
    """Feature: phase-9-finalize-git, Property 24: Artifacts contain no secrets.

    **Validates: Requirements 15.1, 15.2, 15.3**
    """
    config = {"HF_TOKEN": secret, "lr": 0.1, "nested": {"API_KEY": secret, "n": 2}}
    red = FE.redact_config(config)
    assert secret not in str(red)
    assert "HF_TOKEN" not in red and "API_KEY" not in red["nested"]
    assert red["nested"]["n"] == 2
    text = FE.redact_secrets(f"tok={secret}", {"HF_TOKEN": secret})
    assert secret not in text


# Property 13 ------------------------------------------------------------- #
@settings(max_examples=80, deadline=None)
@given(
    run_ids=st.lists(st.from_regex(r"[a-z0-9-]{1,8}", fullmatch=True), min_size=1, max_size=3),
    job_files=st.lists(st.from_regex(r"[a-z]{1,6}\.yaml", fullmatch=True), min_size=1, max_size=3),
)
def test_property_13_candidate_selection(run_ids, job_files) -> None:
    """Feature: phase-9-finalize-git, Property 13: Commit-candidate selection is pure and complete.

    **Validates: Requirements 8.1, 8.3**
    """
    cand = FE.select_commit_candidate("experiments/exp1", run_ids, job_files)
    assert "experiments/exp1/plan.md" in cand
    assert "experiments/exp1/results.yaml" in cand
    assert "experiments/exp1/history.md" in cand
    assert "experiments/exp1/journal.md" in cand
    assert "project-log.md" in cand
    for rid in run_ids:
        assert f"experiments/exp1/runs/{rid}/run.yaml" in cand
    for jf in job_files:
        assert f"experiments/exp1/jobs/{jf}" in cand
