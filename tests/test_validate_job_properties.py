"""Property tests for the train-llm job configuration validator."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml
from hypothesis import given, settings, strategies as st


VALIDATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "train-llm"
    / "scripts"
    / "validate_job.py"
)


def _load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("validate_job", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_job = _load_validator().validate_job

REQUIRED_FIELDS = {"job_id", "type", "entrypoint", "parameters", "resources"}

RESOURCE_CASES = {
    "valid": {
        "backend": "local",
        "gpus": 0,
        "cpus": 1,
        "memory_gb": 1,
        "time": "00:00:00",
    },
    "negative_gpus": {"gpus": -1},
    "zero_cpus": {"cpus": 0},
    "low_memory": {"memory_gb": 0.5},
    "invalid_time": {"time": "1:60:00"},
    "invalid_backend": {"backend": "remote"},
}


@settings(max_examples=100, deadline=None)
@given(
    missing_fields=st.sets(st.sampled_from(sorted(REQUIRED_FIELDS))),
    entrypoint_exists=st.booleans(),
    resource_case=st.sampled_from(sorted(RESOURCE_CASES)),
    quota_provided=st.booleans(),
)
def test_property_job_validation_completeness(
    missing_fields: set[str],
    entrypoint_exists: bool,
    resource_case: str,
    quota_provided: bool,
) -> None:
    """Property 1: every validation concern is checked and reported as JSON.

    **Validates: Requirements 4.14, 4.15, 4.16, 4.17**
    """
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        entrypoint = workspace / "src" / "train.py"
        if entrypoint_exists:
            entrypoint.parent.mkdir()
            entrypoint.write_text("# generated entrypoint\n", encoding="utf-8")

        resources = dict(RESOURCE_CASES["valid"])
        resources.update(RESOURCE_CASES[resource_case])
        job: dict[str, Any] = {
            "job_id": "generated-job",
            "type": "train",
            "entrypoint": "src/train.py",
            "parameters": {},
            "resources": resources,
        }
        for field in missing_fields:
            job.pop(field)

        job_file = tmp_path / "job.yaml"
        job_file.write_text(yaml.safe_dump(job), encoding="utf-8")

        quota_file = None
        if quota_provided:
            quota_file = tmp_path / "project-plan.md"
            quota_file.write_text("resource_limits:\n  gpus: 8\n", encoding="utf-8")

        result = validate_job(job_file, workspace, quota_file)

        # Requirement 4.17: results always have a stable, JSON-serializable shape.
        assert set(result) == {"valid", "errors", "warnings", "checked"}
        assert isinstance(result["valid"], bool)
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
        assert set(result["checked"]) == {
            "required_fields",
            "entrypoint_exists",
            "quota_compliance",
        }
        assert all(isinstance(value, bool) for value in result["checked"].values())
        assert json.loads(json.dumps(result)) == result

        # Requirement 4.14: every omitted required field is reported together.
        assert result["checked"]["required_fields"] is (not missing_fields)
        if missing_fields:
            missing_error = next(
                error for error in result["errors"] if error.startswith("Missing required fields:")
            )
            assert all(field in missing_error for field in missing_fields)

        # Requirement 4.15: an included entrypoint is resolved against the workspace.
        expected_entrypoint_check = "entrypoint" not in missing_fields and entrypoint_exists
        assert result["checked"]["entrypoint_exists"] is expected_entrypoint_check
        if "entrypoint" not in missing_fields and not entrypoint_exists:
            assert any("Entrypoint file not found:" in error for error in result["errors"])

        # Requirement 4.16: generated resource specifications are validated, and an
        # optional quota file is either checked or accompanied by an explicit warning.
        if "resources" not in missing_fields and resource_case != "valid":
            assert any(error.startswith("resources.") for error in result["errors"])
        if quota_provided:
            quota_was_handled = result["checked"]["quota_compliance"] or any(
                "skipping quota validation" in warning for warning in result["warnings"]
            )
            assert quota_was_handled
        else:
            assert result["checked"]["quota_compliance"] is False

        has_validation_error = bool(missing_fields)
        has_validation_error |= "entrypoint" not in missing_fields and not entrypoint_exists
        has_validation_error |= "resources" not in missing_fields and resource_case != "valid"
        assert result["valid"] is (not has_validation_error)
