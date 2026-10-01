"""Property tests for Phase 4 job artifacts and approval handoff."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys
from typing import Any

from hypothesis import given, settings, strategies as st
import yaml


WORKSPACE = Path(__file__).resolve().parents[1]
HELPERS = WORKSPACE / "tests" / "helpers"
if str(HELPERS) not in sys.path:
    sys.path.insert(0, str(HELPERS))

from phase4_artifact_validator import (  # noqa: E402
    calculate_resource_estimate,
    validate_approval_summary,
    validate_jobs,
)

GOLDEN = (
    WORKSPACE
    / "tests"
    / "fixtures"
    / "phase4-planning-golden-path"
    / "golden"
    / "expected"
)
GOLDEN_PLAN = (GOLDEN / "experiments/lora-rank-ablation/plan.md").read_text(
    encoding="utf-8"
)
GOLDEN_TRAIN = yaml.safe_load(
    (GOLDEN / "experiments/lora-rank-ablation/jobs/train.yaml").read_text(
        encoding="utf-8"
    )
)
GOLDEN_EVALUATE = yaml.safe_load(
    (GOLDEN / "experiments/lora-rank-ablation/jobs/evaluate.yaml").read_text(
        encoding="utf-8"
    )
)
GOLDEN_SUMMARY = (GOLDEN / "approval-summary.md").read_text(encoding="utf-8")

RANKS = st.lists(
    st.integers(min_value=1, max_value=256),
    min_size=1,
    max_size=5,
    unique=True,
).map(sorted)
SEEDS = st.lists(
    st.integers(min_value=0, max_value=2**16),
    min_size=1,
    max_size=4,
    unique=True,
).map(sorted)
DESTINATION = st.sampled_from(
    (
        ("fixture-nlp-lab", "sentiment-lora", "fixture-nlp-lab/lora-rank-ablation"),
        ("research-team", "rank-study", "research-team/rank-study"),
        ("offline-lab", "lora-validation", "offline-lab/lora-validation"),
    )
)
PROJECT_SETTINGS = {"execution": {"default_target": "ssh"}}


def _jobs(
    ranks: list[int], seeds: list[int], destination: tuple[str, str, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    train = deepcopy(GOLDEN_TRAIN)
    evaluate = deepcopy(GOLDEN_EVALUATE)
    train["matrix"] = {"lora_rank": ranks, "seed": seeds}
    train["planning"]["configuration_count"] = len(ranks) * len(seeds)
    evaluate["planning"]["checkpoints_to_evaluate"] = len(ranks) * len(seeds)

    entity, project, repo = destination
    for document in (train, evaluate):
        document["wandb"].update(entity=entity, project=project)
        document["huggingface"].update(namespace=entity, repo=repo)
    return train, evaluate


def _diagnostic_codes(result: Any) -> set[str]:
    return {diagnostic.code for diagnostic in result.diagnostics}


def _assert_secret_redacted(result: Any, secret: str) -> None:
    secret_diagnostics = [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "JOB_SECRET_DETECTED"
    ]
    assert secret_diagnostics
    for diagnostic in secret_diagnostics:
        assert "<redacted>" in diagnostic.message
        assert secret not in diagnostic.message
        assert secret not in diagnostic.location


def _replace_summary_matrix(
    summary: str,
    ranks: list[int],
    seeds: list[int],
    train: dict[str, Any],
    evaluate: dict[str, Any],
) -> str:
    estimate = calculate_resource_estimate(train, evaluate)
    summary = summary.replace("[8, 16, 32]", str(ranks))
    summary = summary.replace("[17, 42, 73]", str(seeds))
    summary = re.sub(
        r"\*\*Estimated count\*\*:.*",
        (
            f"**Estimated count**: {estimate.train_runs} training configurations plus "
            f"{estimate.evaluate_runs} aggregate evaluation job, for "
            f"{estimate.total_runs} planned job invocations and "
            f"{estimate.train_runs} evaluated checkpoints."
        ),
        summary,
    )
    summary = re.sub(
        r"\*\*Requested upper bound\*\*:.*",
        f"**Requested upper bound**: {estimate.total_gpu_hours:g} GPU-hours from configured limits.",
        summary,
    )
    return summary


def _replace_destinations(
    summary: str, destination: tuple[str, str, str]
) -> str:
    entity, project, repo = destination
    summary = summary.replace("fixture-nlp-lab/sentiment-lora", f"{entity}/{project}")
    summary = summary.replace("fixture-nlp-lab/lora-rank-ablation", repo)
    return summary


def _move_heading_block_after(summary: str, heading: str, after_heading: str) -> str:
    start = summary.index(f"## {heading}")
    next_heading = summary.find("\n## ", start + 4)
    end = len(summary) if next_heading < 0 else next_heading + 1
    block = summary[start:end]
    without = summary[:start] + summary[end:]
    insertion_start = without.index(f"## {after_heading}")
    insertion_next = without.find("\n## ", insertion_start + 4)
    insertion = len(without) if insertion_next < 0 else insertion_next + 1
    return without[:insertion] + block + without[insertion:]


@settings(max_examples=100, deadline=None)
@given(
    ranks=RANKS,
    seeds=SEEDS,
    destination=DESTINATION,
    mutation=st.sampled_from(
        (
            "valid",
            "metric_mismatch",
            "dataset_mismatch",
            "split_mismatch",
            "group_mismatch",
            "phase6_marker",
            "phase7_marker",
            "phase8_marker",
            "missing_required_key",
            "placeholder",
            "secret_key",
            "secret_value",
        )
    ),
)
def test_property_7_reproducible_and_phase_bounded_jobs(
    ranks: list[int],
    seeds: list[int],
    destination: tuple[str, str, str],
    mutation: str,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 7: Reproducible and phase-bounded jobs.

    **Validates: Requirements 4.2, 4.4, 5.1, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7**
    """
    train, evaluate = _jobs(ranks, seeds, destination)
    expected_code: str | None = None
    secret: str | None = None

    if mutation == "metric_mismatch":
        evaluate["parameters"]["primary_metric"] = "loss"
        expected_code = "JOB_METRIC_MISMATCH"
    elif mutation == "dataset_mismatch":
        evaluate["parameters"]["dataset_config"] = "mnli"
        expected_code = "JOB_DATASET_MISMATCH"
    elif mutation == "split_mismatch":
        evaluate["parameters"]["dataset_split"] = "test"
        expected_code = "JOB_SPLIT_MISMATCH"
    elif mutation == "group_mismatch":
        evaluate["wandb"]["group"] = "different-experiment"
        expected_code = "JOB_GROUP_MISMATCH"
    elif mutation == "phase6_marker":
        train["resources"]["available_phase"] = 5
        expected_code = "JOB_PHASE_LABEL_INVALID"
    elif mutation == "phase7_marker":
        evaluate["wandb"]["status"] = "verified"
        expected_code = "JOB_PHASE_LABEL_INVALID"
    elif mutation == "phase8_marker":
        train["huggingface"]["available_phase"] = 7
        expected_code = "JOB_PHASE_LABEL_INVALID"
    elif mutation == "missing_required_key":
        del evaluate["entrypoint"]
        expected_code = "JOB_REQUIRED_KEY_MISSING"
    elif mutation == "placeholder":
        train["parameters"]["model_name"] = "<model-name>"
        expected_code = "JOB_PLACEHOLDER_UNRESOLVED"
    elif mutation == "secret_key":
        secret = "should-never-appear"
        train["wandb"]["api_key"] = secret
        expected_code = "JOB_SECRET_DETECTED"
    elif mutation == "secret_value":
        secret = "hf_1234567890abcdef"
        evaluate["huggingface"]["repo"] = secret
        expected_code = "JOB_SECRET_DETECTED"

    result = validate_jobs(
        train,
        evaluate,
        plan=GOLDEN_PLAN,
        scenario_id="generated-artifacts-property-7",
        train_location="jobs/train.yaml",
        evaluate_location="jobs/evaluate.yaml",
        project_settings=PROJECT_SETTINGS,
    )
    codes = _diagnostic_codes(result)

    assert train["matrix"]["lora_rank"] == ranks
    assert train["matrix"]["seed"] == seeds
    estimate = calculate_resource_estimate(train, evaluate)
    assert estimate.train_runs == len(ranks) * len(seeds)
    assert estimate.total_runs == len(ranks) * len(seeds) + 1
    assert estimate.train_gpu_hours == len(ranks) * len(seeds) * 8
    assert estimate.evaluate_gpu_hours == 2
    assert estimate.total_gpu_hours == len(ranks) * len(seeds) * 8 + 2

    if expected_code is None:
        assert result.valid, result.diagnostics
    else:
        assert not result.valid
        assert expected_code in codes
    if secret is not None:
        _assert_secret_redacted(result, secret)
    assert all(
        diagnostic.scenario_id == "generated-artifacts-property-7"
        for diagnostic in result.diagnostics
    )


@settings(max_examples=100, deadline=None)
@given(
    ranks=RANKS,
    seeds=SEEDS,
    destination=DESTINATION,
    mutation=st.sampled_from(
        (
            "valid",
            "defaults_order",
            "duplicated_value",
            "run_count",
            "gpu_hours",
            "wandb_phase",
            "huggingface_phase",
            "artifact_path",
            "approval_ending",
        )
    ),
)
def test_property_8_approval_summary_consistency(
    ranks: list[int],
    seeds: list[int],
    destination: tuple[str, str, str],
    mutation: str,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 8: Approval summary consistency.

    **Validates: Requirements 4.3, 5.2, 5.5, 7.2, 7.3, 7.4, 7.5**
    """
    train, evaluate = _jobs(ranks, seeds, destination)
    summary = _replace_summary_matrix(GOLDEN_SUMMARY, ranks, seeds, train, evaluate)
    summary = _replace_destinations(summary, destination)
    expected_code: str | None = None

    if mutation == "defaults_order":
        summary = _move_heading_block_after(
            summary, "Agent-Determined Defaults", "Objective and Hypothesis"
        )
        expected_code = "APPROVAL_SUMMARY_ORDER_INVALID"
    elif mutation == "duplicated_value":
        summary = summary.replace("0.874", "0.873")
        expected_code = "APPROVAL_VALUE_MISMATCH"
    elif mutation == "run_count":
        estimate = calculate_resource_estimate(train, evaluate)
        summary = summary.replace(
            f"{estimate.total_runs} planned job invocations",
            f"{estimate.total_runs + 1} planned job invocations",
        )
        expected_code = "APPROVAL_RUN_COUNT_MISMATCH"
    elif mutation == "gpu_hours":
        estimate = calculate_resource_estimate(train, evaluate)
        summary = summary.replace(
            f"{estimate.total_gpu_hours:g} GPU-hours", "0.5 GPU-hours"
        )
        expected_code = "APPROVAL_RESOURCE_ARITHMETIC_MISMATCH"
    elif mutation == "wandb_phase":
        summary = summary.replace("W&B, Phase 7", "W&B destination")
        expected_code = "APPROVAL_PHASE_LABEL_MISSING"
    elif mutation == "huggingface_phase":
        summary = summary.replace("Hugging Face, Phase 8", "Hugging Face destination")
        expected_code = "APPROVAL_PHASE_LABEL_MISSING"
    elif mutation == "artifact_path":
        summary = summary.replace(
            "experiments/lora-rank-ablation/jobs/evaluate.yaml", "evaluation artifact"
        )
        expected_code = "APPROVAL_ARTIFACT_PATH_MISSING"
    elif mutation == "approval_ending":
        summary = summary.replace(
            "Please approve this plan or request modifications. No experiment execution, Run creation, credential use, external operation, or Git commit has occurred.",
            "Planning details end here.",
        )
        expected_code = "APPROVAL_REQUEST_MISSING"

    result = validate_approval_summary(
        summary,
        plan=GOLDEN_PLAN,
        train_job=train,
        evaluate_job=evaluate,
        scenario_id="generated-artifacts-property-8",
        location="approval-summary.md",
    )
    codes = _diagnostic_codes(result)

    estimate = calculate_resource_estimate(train, evaluate)
    assert estimate.total_runs == len(ranks) * len(seeds) + 1
    assert estimate.total_gpu_hours == len(ranks) * len(seeds) * 8 + 2
    if expected_code is None:
        assert result.valid, result.diagnostics
    else:
        assert not result.valid
        assert expected_code in codes
    assert all(
        diagnostic.scenario_id == "generated-artifacts-property-8"
        for diagnostic in result.diagnostics
    )
    assert all(not Path(diagnostic.location).is_absolute() for diagnostic in result.diagnostics)
