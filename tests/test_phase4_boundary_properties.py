"""Property tests for Phase 4 safety, isolation, and diagnostic boundaries."""

from __future__ import annotations

from pathlib import Path
import random
import tempfile
from typing import Any

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest
import yaml

from helpers.phase4_boundary_validator import (
    compare_protected_snapshots,
    snapshot_protected_paths,
    validate_command_texts,
    validate_observed_actions,
)
from helpers.phase4_fixture_loader import FixtureLoadError, load_scenario
from helpers.phase4_models import (
    Diagnostic,
    EXTERNAL_PHASES,
    ObservedAction,
    ValidationResult,
)


WORKSPACE = Path(__file__).resolve().parents[1]
REAL_EXAMPLE = "experiments/example-lora-rank-ablation"
MAX_EXAMPLES = 100

_SAFE_SEGMENT = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=16
).filter(lambda value: value not in {".", ".."})

_COMMAND_CASES = (
    ("execution", "python src/train.py --epochs 1", "8.4", "BOUNDARY_EXECUTION_ATTEMPT"),
    ("execution", "uv run src/evaluate.py --split test", "8.4", "BOUNDARY_EXECUTION_ATTEMPT"),
    ("execution", "accelerate launch scripts/training_job.py", "8.4", "BOUNDARY_EXECUTION_ATTEMPT"),
    ("execution", "torchrun src/evaluation.py", "8.4", "BOUNDARY_EXECUTION_ATTEMPT"),
    ("run", "python scripts/initialize_run.py", "8.1", "BOUNDARY_RUN_CREATED"),
    ("run", "mkdir -p experiments/demo/runs/new-run", "8.1", "BOUNDARY_RUN_CREATED"),
    ("ssh", "ssh cluster.example", "8.4", "BOUNDARY_EXTERNAL_OPERATION"),
    ("ssh", "scp plan.md cluster.example:/tmp/", "8.4", "BOUNDARY_EXTERNAL_OPERATION"),
    ("slurm", "sbatch jobs/train.sh", "8.4", "BOUNDARY_EXTERNAL_OPERATION"),
    ("slurm", "squeue --me", "8.4", "BOUNDARY_EXTERNAL_OPERATION"),
    ("wandb", "wandb sync ./wandb/offline-run", "8.4", "BOUNDARY_EXTERNAL_OPERATION"),
    ("huggingface", "hf upload org/model checkpoint.bin", "8.4", "BOUNDARY_EXTERNAL_OPERATION"),
    ("huggingface", "huggingface-cli upload org/model checkpoint.bin", "8.4", "BOUNDARY_EXTERNAL_OPERATION"),
    ("git", "git commit -m planned", "8.3", "BOUNDARY_GIT_COMMIT"),
)

_EXTERNAL_ACTION_KINDS = {
    "ssh": ("ssh", "scp", "sftp", "remote_access"),
    "slurm": ("slurm", "sbatch", "srun"),
    "wandb": ("wandb", "wandb_api", "wandb_cli"),
    "huggingface": ("huggingface", "hugging_face", "huggingface_hub", "hf_hub"),
}

_FORBIDDEN_DEPENDENCIES = (
    "clock",
    "credential",
    "credentials",
    "external_service",
    "mutable_external_data",
    "network",
    "network_state",
    "remote_service",
    "wall_clock",
    "wall_clock_time",
)


def _assert_single_traceable_diagnostic(
    result: ValidationResult,
    *,
    scenario_id: str,
    requirement: str,
    code: str,
    location_prefix: str,
) -> Diagnostic:
    assert not result.valid
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.scenario_id == scenario_id
    assert diagnostic.requirement == requirement
    assert diagnostic.code == code
    assert diagnostic.location.startswith(location_prefix)
    return diagnostic


@settings(
    max_examples=MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(
    case=st.sampled_from(_COMMAND_CASES),
    wrapper=st.sampled_from(("inline", "bash", "sh", "zsh", "console")),
    leading_space=st.integers(min_value=0, max_value=3),
    trailing_space=st.integers(min_value=0, max_value=3),
)
def test_property_2_rejects_forbidden_command_variants(
    case: tuple[str, str, str, str],
    wrapper: str,
    leading_space: int,
    trailing_space: int,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 2: Pre-approval safety invariant.

    **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5**
    """
    _, command, requirement, code = case
    padded = f"{' ' * leading_space}{command}{' ' * trailing_space}"
    text = f"`{padded}`" if wrapper == "inline" else f"```{wrapper}\n{padded}\n```"

    result = validate_command_texts(
        {"approval-summary.md": text}, scenario_id="property-2-command"
    )

    _assert_single_traceable_diagnostic(
        result,
        scenario_id="property-2-command",
        requirement=requirement,
        code=code,
        location_prefix="approval-summary.md:",
    )


@settings(
    max_examples=MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(
    family=st.sampled_from(tuple(_EXTERNAL_ACTION_KINDS)),
    variant_index=st.integers(min_value=0, max_value=3),
    classification=st.sampled_from(("kind", "metadata")),
)
def test_property_2_rejects_every_external_action_family(
    tmp_path: Path,
    family: str,
    variant_index: int,
    classification: str,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 2: Pre-approval safety invariant.

    **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5**
    """
    kinds = _EXTERNAL_ACTION_KINDS[family]
    kind = kinds[variant_index % len(kinds)] if classification == "kind" else "local_read"
    metadata = {} if classification == "kind" else {"integration": family}
    action = ObservedAction(kind, "planned-destination", metadata=metadata)

    result = validate_observed_actions(
        (action,), fixture_workspace=tmp_path, scenario_id="property-2-external"
    )

    diagnostic = _assert_single_traceable_diagnostic(
        result,
        scenario_id="property-2-external",
        requirement="8.2",
        code="BOUNDARY_EXTERNAL_OPERATION",
        location_prefix="action-manifest.actions[0]",
    )
    assert f"Phase {EXTERNAL_PHASES[family]}" in diagnostic.message


@settings(
    max_examples=MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(parts=st.lists(_SAFE_SEGMENT, min_size=1, max_size=4, unique=True))
def test_property_9_confines_relative_writes_to_fixture_workspace(
    tmp_path: Path, parts: list[str]
) -> None:
    """Feature: phase-4-planning-golden-path, Property 9: Fixture write confinement and preservation.

    **Validates: Requirements 9.4, 9.5, 10.5**
    """
    relative_target = "/".join(parts) + "/plan.md"
    result = validate_observed_actions(
        (ObservedAction("local_write", relative_target),),
        fixture_workspace=tmp_path,
        scenario_id="property-9-relative-write",
    )

    assert result == ValidationResult(valid=True)
    assert not (tmp_path / relative_target).exists(), "validation must not perform writes"


@settings(
    max_examples=MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(
    segment=_SAFE_SEGMENT,
    escape_kind=st.sampled_from(("parent", "absolute", "windows-parent", "windows-absolute")),
)
def test_property_9_rejects_escaping_write_variants(
    tmp_path: Path, segment: str, escape_kind: str
) -> None:
    """Feature: phase-4-planning-golden-path, Property 9: Fixture write confinement and preservation.

    **Validates: Requirements 9.4, 9.5, 10.5**
    """
    targets = {
        "parent": f"../{segment}/plan.md",
        "absolute": str(tmp_path.parent / segment / "plan.md"),
        "windows-parent": f"..\\{segment}\\plan.md",
        "windows-absolute": f"C:\\{segment}\\plan.md",
    }
    result = validate_observed_actions(
        (ObservedAction("planning_write", targets[escape_kind]),),
        fixture_workspace=tmp_path,
        scenario_id="property-9-escaped-write",
    )

    _assert_single_traceable_diagnostic(
        result,
        scenario_id="property-9-escaped-write",
        requirement="9.4",
        code="FIXTURE_WRITE_ESCAPED",
        location_prefix="action-manifest.actions[0]",
    )


@settings(
    max_examples=MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(
    files=st.dictionaries(
        keys=_SAFE_SEGMENT.map(lambda value: f"{value}.txt"),
        values=st.binary(min_size=0, max_size=64),
        min_size=1,
        max_size=5,
    ),
    replacement=st.binary(min_size=1, max_size=64),
)
def test_property_9_detects_protected_content_mutation_without_touching_real_example(
    tmp_path: Path, files: dict[str, bytes], replacement: bytes
) -> None:
    """Feature: phase-4-planning-golden-path, Property 9: Fixture write confinement and preservation.

    **Validates: Requirements 9.4, 9.5, 10.5**
    """
    real_before = snapshot_protected_paths(
        WORKSPACE, (REAL_EXAMPLE,), include_defaults=False
    )
    with tempfile.TemporaryDirectory(dir=tmp_path) as case_dir:
        repository = Path(case_dir) / "repository"
        protected = repository / "protected"
        protected.mkdir(parents=True)
        for name, content in files.items():
            (protected / name).write_bytes(content)

        before = snapshot_protected_paths(
            repository, ("protected",), include_defaults=False
        )
        changed_name = sorted(files)[0]
        original = (protected / changed_name).read_bytes()
        changed = replacement if replacement != original else replacement + b"!"
        (protected / changed_name).write_bytes(changed)
        after = snapshot_protected_paths(
            repository, ("protected",), include_defaults=False
        )

        result = compare_protected_snapshots(
            before, after, scenario_id="property-9-preservation"
        )
        assert any(
            diagnostic.code == "PROTECTED_CONTENT_CHANGED"
            and diagnostic.requirement == "9.5"
            and diagnostic.location == f"protected/{changed_name}"
            for diagnostic in result.diagnostics
        )
    real_after = snapshot_protected_paths(
        WORKSPACE, (REAL_EXAMPLE,), include_defaults=False
    )
    assert compare_protected_snapshots(
        real_before, real_after, scenario_id="property-9-real-example"
    ).valid


@settings(
    max_examples=MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(
    kinds=st.lists(
        st.sampled_from(("training", "run_create", "git_commit", "unknown_action")),
        min_size=1,
        max_size=8,
    )
)
def test_property_10_repeated_validation_has_stable_order_and_normalization(
    tmp_path: Path, kinds: list[str]
) -> None:
    """Feature: phase-4-planning-golden-path, Property 10: Deterministic validation.

    **Validates: Requirements 9.1, 9.6, 9.7**
    """
    actions = tuple(ObservedAction(kind, "artifact") for kind in kinds)
    first = validate_observed_actions(
        actions, fixture_workspace=tmp_path, scenario_id="property-10-repeat"
    )
    second = validate_observed_actions(
        actions, fixture_workspace=tmp_path, scenario_id="property-10-repeat"
    )
    assert first == second
    assert first.diagnostics == tuple(
        sorted(first.diagnostics, key=lambda diagnostic: diagnostic.sort_key)
    )

    volatile = [
        Diagnostic(
            "property-10-repeat",
            "9.6",
            f"NORMALIZED_{index % 3}",
            f"tmp\\artifact[{index}]",
            f"At 2025-01-02T03:04:05Z in /tmp/case-{index}, token=hf_abcdefghijk",
        )
        for index in range(len(kinds))
    ]
    shuffled = list(volatile)
    random.Random(len(kinds)).shuffle(shuffled)
    normalized_first = ValidationResult.from_diagnostics(volatile)
    normalized_second = ValidationResult.from_diagnostics(shuffled)
    assert normalized_first == normalized_second
    for diagnostic in normalized_first.diagnostics:
        assert diagnostic.location.startswith("tmp/artifact[")
        assert "<timestamp>" in diagnostic.message
        assert "<tmp_path>" in diagnostic.message
        assert "<redacted>" in diagnostic.message
        assert "hf_abcdefghijk" not in diagnostic.message


@settings(
    max_examples=MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(
    dependency=st.sampled_from(_FORBIDDEN_DEPENDENCIES),
    dependency_key=st.sampled_from(
        ("dependencies", "dependency", "fixture_dependencies", "requires")
    ),
    shape=st.sampled_from(("scalar", "list", "mapping", "nested")),
)
def test_property_10_rejects_nondeterministic_dependency_declarations(
    tmp_path: Path, dependency: str, dependency_key: str, shape: str
) -> None:
    """Feature: phase-4-planning-golden-path, Property 10: Deterministic validation.

    **Validates: Requirements 9.1, 9.6, 9.7**
    """
    fixture = tmp_path / "dependency-fixture"
    fixture.mkdir(exist_ok=True)
    values: dict[str, Any] = {
        "scalar": dependency,
        "list": [dependency],
        "mapping": {"kind": dependency},
        "nested": {"items": [{"source": dependency}]},
    }
    scenario = {
        "schema_version": 1,
        "scenario_id": "property-10-dependency",
        "phase": 4,
        dependency_key: values[shape],
    }
    (fixture / "scenario.yaml").write_text(
        yaml.safe_dump(scenario, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(FixtureLoadError) as error:
        load_scenario(fixture)

    assert error.value.code == "FIXTURE_NONDETERMINISTIC_DEPENDENCY"
    assert error.value.location == f"scenario.{dependency_key}"
    assert dependency in error.value.detail


_TRACEABLE_GUARDS = (
    (ObservedAction("training", "src/train.py"), "8.4", "BOUNDARY_EXECUTION_ATTEMPT"),
    (ObservedAction("run_create", "experiments/demo/runs/one"), "8.1", "BOUNDARY_RUN_CREATED"),
    (ObservedAction("git_commit", "HEAD"), "8.3", "BOUNDARY_GIT_COMMIT"),
    (ObservedAction("ssh", "cluster"), "8.2", "BOUNDARY_EXTERNAL_OPERATION"),
    (ObservedAction("slurm", "gpu"), "8.2", "BOUNDARY_EXTERNAL_OPERATION"),
    (ObservedAction("wandb_api", "entity/project"), "8.2", "BOUNDARY_EXTERNAL_OPERATION"),
    (ObservedAction("huggingface_hub", "org/model"), "8.2", "BOUNDARY_EXTERNAL_OPERATION"),
    (ObservedAction("local_write", "../escape"), "9.4", "FIXTURE_WRITE_ESCAPED"),
)


@settings(
    max_examples=MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(
    guard=st.sampled_from(_TRACEABLE_GUARDS),
    scenario_suffix=_SAFE_SEGMENT,
)
def test_property_11_guard_diagnostics_are_fully_traceable(
    tmp_path: Path,
    guard: tuple[ObservedAction, str, str],
    scenario_suffix: str,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 11: Guard diagnostic traceability.

    **Validates: Requirements 9.3, 10.3**
    """
    action, requirement, code = guard
    scenario_id = f"guard-{scenario_suffix}"

    first = validate_observed_actions(
        (action,), fixture_workspace=tmp_path, scenario_id=scenario_id
    )
    second = validate_observed_actions(
        (action,), fixture_workspace=tmp_path, scenario_id=scenario_id
    )

    diagnostic = _assert_single_traceable_diagnostic(
        first,
        scenario_id=scenario_id,
        requirement=requirement,
        code=code,
        location_prefix="action-manifest.actions[0]",
    )
    assert diagnostic.message
    assert first == second
