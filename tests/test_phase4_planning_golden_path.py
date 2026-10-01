"""Successful Phase 4 planning Golden Path integration and preservation tests.

Validates: Requirements 6.1, 7.1, 7.5, 8.1, 8.2, 8.3, 9.2, 9.4, 9.5, 10.5
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping


WORKSPACE = Path(__file__).resolve().parents[1]
TESTS_ROOT = Path(__file__).resolve().parent
HELPERS_ROOT = TESTS_ROOT / "helpers"
FIXTURE_ROOT = TESTS_ROOT / "fixtures" / "phase4-planning-golden-path" / "golden"

# ``helpers`` is intentionally a test-only namespace package.  Adding both
# roots supports its package-relative imports and the artifact validator's
# historical top-level phase4_models import under pytest and direct loaders.
for import_root in (TESTS_ROOT, HELPERS_ROOT):
    import_path = str(import_root)
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from helpers.phase4_artifact_validator import validate_artifacts
from helpers.phase4_boundary_validator import (
    compare_protected_snapshots,
    snapshot_protected_paths,
    validate_boundary,
)
from helpers.phase4_evidence_validator import validate_scenario_evidence
from helpers.phase4_fixture_loader import (
    load_markdown_frontmatter,
    load_scenario,
    load_yaml,
    materialize_source_workspace,
)
from helpers.phase4_models import PHASE4_WORKFLOW_STATES
from helpers.phase4_workflow_validator import derive_workflow_states, validate_workflow


def _require_mapping(value: Any) -> Mapping[str, Any]:
    """Return a fixture mapping or fail with a useful integration-test error."""
    assert isinstance(value, Mapping)
    return value


def _materialize_expected_artifacts(
    expected_artifacts: Mapping[str, Path], fixture_workspace: Path
) -> dict[str, Path]:
    """Copy generated planning outputs into the disposable fixture workspace."""
    destinations = {
        "discovery_report": fixture_workspace / "discovery-report.yaml",
        "plan": fixture_workspace / "experiments/lora-rank-ablation/plan.md",
        "train_job": fixture_workspace
        / "experiments/lora-rank-ablation/jobs/train.yaml",
        "evaluate_job": fixture_workspace
        / "experiments/lora-rank-ablation/jobs/evaluate.yaml",
        "approval_summary": fixture_workspace / "approval-summary.md",
    }
    assert set(expected_artifacts) == set(destinations)
    for name, destination in destinations.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(expected_artifacts[name], destination)
    return destinations


def _run_paths(root: Path) -> tuple[str, ...]:
    """Return a stable inventory of all Run directories and metadata files."""
    return tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.name == "runs" or "runs" in path.relative_to(root).parts
        )
    )


def test_successful_planning_scenario_is_consistent_and_preserves_repository(
    tmp_path: Path,
) -> None:
    """Validate the full ordered planning flow without execution side effects."""
    scenario = load_scenario(FIXTURE_ROOT)
    scenario_document = _require_mapping(load_yaml(FIXTURE_ROOT / "scenario.yaml"))
    action_manifest = _require_mapping(load_yaml(FIXTURE_ROOT / "action-manifest.yaml"))
    protected_paths = tuple(scenario_document.get("protected_paths", ()))
    protected_before = snapshot_protected_paths(WORKSPACE, protected_paths)

    fixture_workspace = materialize_source_workspace(FIXTURE_ROOT, tmp_path)
    runs_before = _run_paths(fixture_workspace)

    # Discovery observes only the source workspace that existed at discovery
    # time; generated plan/job outputs are materialized only after it passes.
    evidence_result = validate_scenario_evidence(scenario, fixture_workspace)
    materialized_artifacts = _materialize_expected_artifacts(
        scenario.expected_artifacts, fixture_workspace
    )
    materialized_scenario = replace(
        scenario, expected_artifacts=materialized_artifacts
    )

    workflow_result = validate_workflow(materialized_scenario)
    artifact_result = validate_artifacts(
        materialized_artifacts["plan"],
        materialized_artifacts["train_job"],
        materialized_artifacts["evaluate_job"],
        materialized_artifacts["approval_summary"],
        scenario_id=scenario.scenario_id,
        project_settings=scenario.stable_settings,
    )
    boundary_result = validate_boundary(
        materialized_scenario, fixture_workspace=fixture_workspace
    )

    results = {
        "workflow": workflow_result,
        "evidence": evidence_result,
        "artifacts": artifact_result,
        "boundary": boundary_result,
    }
    assert {
        name: result.diagnostics for name, result in results.items() if not result.valid
    } == {}

    assert derive_workflow_states(materialized_scenario) == PHASE4_WORKFLOW_STATES
    assert action_manifest["terminal_state"] == "awaiting_approval"
    assert action_manifest["approval_status"] == "pending"

    plan, _ = load_markdown_frontmatter(materialized_artifacts["plan"])
    train_job = _require_mapping(load_yaml(materialized_artifacts["train_job"]))
    evaluate_job = _require_mapping(load_yaml(materialized_artifacts["evaluate_job"]))
    assert plan["jobs"] == ["jobs/train.yaml", "jobs/evaluate.yaml"]
    assert plan["primary_metric"]["name"] == evaluate_job["parameters"]["primary_metric"]
    assert plan["baseline"]["evaluation"]["split"] == evaluate_job["parameters"]["dataset_split"]
    assert train_job["matrix"] == {"lora_rank": [8, 16, 32], "seed": [17, 42, 73]}
    assert train_job["wandb"]["group"] == evaluate_job["wandb"]["group"] == plan["experiment_id"]
    assert train_job["planning"]["configuration_count"] == 9
    assert evaluate_job["planning"]["checkpoints_to_evaluate"] == 9

    assert runs_before == _run_paths(fixture_workspace) == ()
    assert action_manifest["run_artifacts_created"] == []
    assert action_manifest["commands_generated"] == []
    assert action_manifest["credentials_used"] == []
    assert action_manifest["external_operations"] == []
    assert action_manifest["git_commits_created"] == []

    protected_after = snapshot_protected_paths(WORKSPACE, protected_paths)
    preservation_result = compare_protected_snapshots(
        protected_before, protected_after, scenario_id=scenario.scenario_id
    )
    assert preservation_result.valid, preservation_result.diagnostics
    assert protected_after.inventory == protected_before.inventory
    assert dict(protected_after.digests) == dict(protected_before.digests)
