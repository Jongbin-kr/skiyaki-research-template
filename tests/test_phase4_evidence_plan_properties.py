"""Property validation for Phase 4 evidence closure and plan reviewability."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import Any

from hypothesis import given, settings, strategies as st
import yaml


WORKSPACE = Path(__file__).resolve().parents[1]
HELPERS = WORKSPACE / "tests" / "helpers"
if str(HELPERS) not in sys.path:
    sys.path.insert(0, str(HELPERS))

# The helpers intentionally live under tests/ without package marker files.
# Register a test-local namespace so the evidence validator's relative model
# import works without changing repository manifests or package structure.
HELPER_PACKAGE = ModuleType("phase4_test_helpers")
HELPER_PACKAGE.__path__ = [str(HELPERS)]  # type: ignore[attr-defined]
sys.modules.setdefault("phase4_test_helpers", HELPER_PACKAGE)

from phase4_test_helpers.phase4_evidence_validator import (  # noqa: E402
    classify_duplication,
    validate_discovery_report,
)
from phase4_artifact_validator import validate_plan  # noqa: E402


GOLDEN_PLAN = (
    WORKSPACE
    / "tests"
    / "fixtures"
    / "phase4-planning-golden-path"
    / "golden"
    / "expected"
    / "experiments"
    / "lora-rank-ablation"
    / "plan.md"
).read_text(encoding="utf-8")

OVERLAP_FACTS = {
    "exact_duplicate": {
        "objective": "exact",
        "model": "exact",
        "dataset": "exact",
        "technique": "exact",
        "parameter_range": "exact",
        "metrics": "exact",
        "controls": "exact",
    },
    "near_duplicate": {
        "objective": "exact",
        "model": "exact",
        "dataset": "exact",
        "technique": "exact",
        "parameter_range": "overlap",
        "metrics": "exact",
        "controls": "different",
    },
    "related_work": {
        "objective": "similar",
        "model": "different",
        "dataset": "different",
        "technique": "exact",
        "parameter_range": "different",
        "metrics": "different",
        "controls": "different",
    },
    "novel_work": {
        "objective": "different",
        "model": "different",
        "dataset": "different",
        "technique": "different",
        "parameter_range": "different",
        "metrics": "different",
        "controls": "different",
    },
}
DUPLICATION_LEVELS = tuple(OVERLAP_FACTS)
REQUIRED_HEADINGS = (
    "Purpose",
    "Hypothesis",
    "Evidence-Backed Baseline",
    "Variables",
    "Controls",
    "Rationale",
    "Risks and Limitations",
    "Expected Outcomes",
    "If Hypothesis Supported",
    "If Hypothesis Refuted",
)
PLACEHOLDERS = ("<metric-name>", "[Describe objective]", "TODO")


def _write_evidence_workspace(root: Path, metric_value: float, project_log: bool) -> None:
    """Create one isolated, minimal evidence inventory for a generated example."""
    files: dict[str, str] = {
        "project-plan.md": "# Project Plan\n",
        "experiments/prior/plan.md": "# Prior experiment\n",
        "experiments/prior/journal.md": f"Accuracy was {metric_value}.\n",
        "experiments/prior/results.yaml": yaml.safe_dump(
            {"primary_metric": {"name": "accuracy", "value": metric_value}}
        ),
        "experiments/prior/jobs/train.yaml": "job_id: prior-train\ntype: train\n",
        "git-evidence.yaml": yaml.safe_dump({"entries": [{"commit": "abcdef1"}]}),
    }
    if project_log:
        files["project-log.md"] = "# Project Log\n"
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _inventory(project_log: bool) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    inspected = [
        {"source_type": "project_plan", "status": "inspected", "source_ref": "project-plan.md"},
        {
            "source_type": "project_log",
            "status": "inspected" if project_log else "missing",
            "source_ref": "project-log.md",
        },
        {"source_type": "experiment_plan", "status": "inspected", "source_ref": "experiments/prior/plan.md"},
        {"source_type": "experiment_journal", "status": "inspected", "source_ref": "experiments/prior/journal.md"},
        {"source_type": "structured_results", "status": "inspected", "source_ref": "experiments/prior/results.yaml"},
        {"source_type": "job_configuration", "status": "inspected", "source_ref": "experiments/prior/jobs/train.yaml"},
        {"source_type": "git_history", "status": "inspected", "source_ref": "git-evidence.yaml#abcdef1"},
    ]
    missing = [] if project_log else [
        {"source_type": "project_log", "source_ref": "project-log.md", "reason": "No populated root project log exists."}
    ]
    return inspected, missing


def _discovery_report(
    *,
    metric_value: float,
    project_log: bool,
    inventory_complete: bool,
    claim_supported: bool,
    conflict: bool,
    conflict_recorded: bool,
    baseline_mode: str,
    overlap_level: str,
    report_overlap_correctly: bool,
) -> dict[str, Any]:
    inspected, missing = _inventory(project_log)
    if not inventory_complete:
        inspected = [item for item in inspected if item["source_type"] != "experiment_plan"]

    narrative_value = metric_value + 0.01 if conflict else metric_value
    facts = deepcopy(OVERLAP_FACTS[overlap_level])
    reported_level = overlap_level
    if not report_overlap_correctly:
        reported_level = next(level for level in DUPLICATION_LEVELS if level != overlap_level)

    if baseline_mode == "supported":
        baseline = {
            "status": "supported",
            "model": "roberta-base LoRA rank 16",
            "dataset": "glue/sst2",
            "split": "validation",
            "metric": {"name": "accuracy", "value": metric_value, "direction": "maximize"},
            "source_evidence_id": "results",
        }
    elif baseline_mode == "unresolved":
        baseline = {
            "status": "unresolved",
            "missing_support": "No repository evidence supports a numeric baseline.",
        }
    else:
        baseline = {
            "status": "supported",
            "model": "roberta-base LoRA rank 16",
            "dataset": "glue/sst2",
            "split": "validation",
            "metric": {"name": "accuracy", "value": metric_value, "direction": "maximize"},
            "source_evidence_id": "not-declared",
        }

    report: dict[str, Any] = {
        "inspected": inspected,
        "missing_sources": missing,
        "evidence": [
            {
                "evidence_id": "results",
                "source_type": "structured_results",
                "source_ref": "experiments/prior/results.yaml",
                "claims": [f"Validation accuracy was {metric_value}."],
            },
            {
                "evidence_id": "journal",
                "source_type": "experiment_journal",
                "source_ref": "experiments/prior/journal.md",
                "claims": [f"Narrative accuracy was {narrative_value}."],
            },
        ],
        "findings": [
            {
                "finding_id": "generated-finding",
                "statement": f"Prior validation accuracy was {metric_value}.",
                "evidence_ids": ["results"] if claim_supported else [],
            }
        ],
        "metric_comparisons": [
            {
                "metric": "accuracy",
                "structured": {
                    "value": metric_value,
                    "source_ref": "experiments/prior/results.yaml",
                },
                "narrative": {
                    "value": narrative_value,
                    "source_ref": "experiments/prior/journal.md",
                },
                "comparison_value": metric_value,
            }
        ],
        "baselines": [baseline],
        "duplication": {
            "level": reported_level,
            "overlap_facts": facts,
            "evidence_ids": ["journal"],
            "differences": [] if reported_level == "exact_duplicate" else ["Generated material difference"],
        },
        "conflicts": [],
    }
    if conflict_recorded:
        report["conflicts"] = [
            {
                "metric": "accuracy",
                "structured": {
                    "value": metric_value,
                    "source_ref": "experiments/prior/results.yaml",
                },
                "narrative": {
                    "value": narrative_value,
                    "source_ref": "experiments/prior/journal.md",
                },
            }
        ]
    return report


def _move_defaults_after_design(plan: str) -> str:
    start = plan.index("## Agent-Determined Defaults")
    end = plan.index("## Decision Provenance", start)
    block = plan[start:end]
    without = plan[:start] + plan[end:]
    insertion = without.index("## Risks and Limitations")
    return without[:insertion] + block + without[insertion:]


def _remove_repository_evidence_references(plan: str) -> str:
    return re.sub(r"experiments/[A-Za-z0-9_./-]+", "prior-artifact", plan)


def _insert_placeholder(plan: str, placeholder: str) -> str:
    if placeholder == "TODO":
        return plan.replace("experiment_id: lora-rank-ablation", "experiment_id: TODO", 1)
    return plan.replace("Determine whether LoRA", f"{placeholder} Determine whether LoRA", 1)


@settings(max_examples=100, deadline=None)
@given(
    metric_value=st.floats(min_value=0.1, max_value=0.99, allow_nan=False, allow_infinity=False),
    project_log=st.booleans(),
    inventory_complete=st.booleans(),
    claim_supported=st.booleans(),
    conflict=st.booleans(),
    conflict_recorded=st.booleans(),
    baseline_mode=st.sampled_from(("supported", "unresolved", "invented")),
    overlap_level=st.sampled_from(DUPLICATION_LEVELS),
    report_overlap_correctly=st.booleans(),
)
def test_property_3_evidence_closure_and_baseline_integrity(
    metric_value: float,
    project_log: bool,
    inventory_complete: bool,
    claim_supported: bool,
    conflict: bool,
    conflict_recorded: bool,
    baseline_mode: str,
    overlap_level: str,
    report_overlap_correctly: bool,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 3: Evidence closure and baseline integrity.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.3, 5.4**
    """
    with TemporaryDirectory() as temporary_directory:
        source_workspace = Path(temporary_directory) / "source-workspace"
        source_workspace.mkdir()
        _write_evidence_workspace(source_workspace, metric_value, project_log)
        report = _discovery_report(
            metric_value=metric_value,
            project_log=project_log,
            inventory_complete=inventory_complete,
            claim_supported=claim_supported,
            conflict=conflict,
            conflict_recorded=conflict_recorded,
            baseline_mode=baseline_mode,
            overlap_level=overlap_level,
            report_overlap_correctly=report_overlap_correctly,
        )

        result = validate_discovery_report(
            "generated-evidence",
            report,
            source_workspace,
        )
        codes = {diagnostic.code for diagnostic in result.diagnostics}

        assert classify_duplication(OVERLAP_FACTS[overlap_level]) == overlap_level
        assert ("EVIDENCE_SOURCE_CLASS_UNACCOUNTED" in codes) is (not inventory_complete)
        assert ("EVIDENCE_UNSUPPORTED_CLAIM" in codes) is (not claim_supported)
        assert ("EVIDENCE_CONFLICT_UNRECORDED" in codes) is (
            conflict and not conflict_recorded
        )
        assert ("EVIDENCE_BASELINE_UNSUPPORTED" in codes) is (baseline_mode == "invented")
        assert ("EVIDENCE_DUPLICATION_CLASS_MISMATCH" in codes) is (
            not report_overlap_correctly
        )

        should_be_valid = (
            inventory_complete
            and claim_supported
            and (not conflict or conflict_recorded)
            and baseline_mode != "invented"
            and report_overlap_correctly
        )
        assert result.valid is should_be_valid
        assert all(diagnostic.scenario_id == "generated-evidence" for diagnostic in result.diagnostics)


@settings(max_examples=100, deadline=None)
@given(
    mutation=st.sampled_from(
        ("valid", "heading_missing", "defaults_after_design", "evidence_missing", "placeholder")
    ),
    required_heading=st.sampled_from(REQUIRED_HEADINGS),
    placeholder=st.sampled_from(PLACEHOLDERS),
)
def test_property_6_plan_validity_and_review_order(
    mutation: str,
    required_heading: str,
    placeholder: str,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 6: Plan validity and review order.

    **Validates: Requirements 4.3, 5.1, 5.2, 5.3, 5.5**
    """
    plan = GOLDEN_PLAN
    expected_code: str | None = None
    if mutation == "heading_missing":
        plan = plan.replace(f"## {required_heading}", f"**{required_heading}**", 1)
        expected_code = "PLAN_SECTION_MISSING"
    elif mutation == "defaults_after_design":
        plan = _move_defaults_after_design(plan)
        expected_code = "PLAN_DEFAULTS_ORDER_INVALID"
    elif mutation == "evidence_missing":
        plan = _remove_repository_evidence_references(plan)
        expected_code = "PLAN_EVIDENCE_REFERENCE_MISSING"
    elif mutation == "placeholder":
        plan = _insert_placeholder(plan, placeholder)
        expected_code = "PLAN_PLACEHOLDER_UNRESOLVED"

    result = validate_plan(plan, scenario_id="generated-plan", location="plan.md")
    codes = {diagnostic.code for diagnostic in result.diagnostics}

    if expected_code is None:
        assert result.valid, result.diagnostics
    else:
        assert not result.valid
        assert expected_code in codes
    assert all(diagnostic.scenario_id == "generated-plan" for diagnostic in result.diagnostics)
    assert all(not Path(diagnostic.location).is_absolute() for diagnostic in result.diagnostics)
