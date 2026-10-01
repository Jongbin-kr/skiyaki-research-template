"""Property tests for train-llm helper-script interface compliance."""

from __future__ import annotations

import ast
import json
import random
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import pytest
import yaml


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts"
SCRIPT_PATHS = tuple(sorted(SCRIPTS_DIR.glob("*.py")))
EXPECTED_SCRIPTS = {"initialize_run.py", "validate_job.py", "run_local.py", "submit_slurm.py", "track_wandb.py", "publish_hf.py", "finalize_experiment.py"}
RUN_TIMESTAMP = re.compile(r"(?<=__)\d{8}T\d{6}")


@dataclass(frozen=True)
class ScriptCase:
    """Describe one helper script's explicit-path and state-change interface."""

    path: Path
    modifies_state: bool


SCRIPT_CASES = (
    ScriptCase(SCRIPTS_DIR / "validate_job.py", modifies_state=False),
    ScriptCase(SCRIPTS_DIR / "initialize_run.py", modifies_state=True),
)


def _generated_directory_names(
    seed: int = 20250308, count: int = 8
) -> Iterable[Tuple[int, str]]:
    """Generate reproducible working-directory names with varied path characters."""
    rng = random.Random(seed)
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    for case_number in range(count):
        suffix = "".join(rng.choice(alphabet) for _ in range(rng.randint(3, 16)))
        separator = " " if case_number % 2 else "-"
        yield case_number, f"cwd{separator}{case_number}-{suffix}"


GENERATED_DIRECTORIES = tuple(_generated_directory_names())


def _write_valid_job(root: Path) -> Tuple[Path, Path]:
    """Create a valid job and its workspace using only explicit absolute paths."""
    workspace = root / "explicit workspace"
    entrypoint = workspace / "src" / "train.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("# property-test entrypoint\n", encoding="utf-8")

    job_file = root / "job inputs" / "train.yaml"
    job_file.parent.mkdir(parents=True)
    job_file.write_text(
        yaml.safe_dump(
            {
                "job_id": "interface-property",
                "type": "train",
                "entrypoint": "src/train.py",
                "parameters": {"seed": 17},
                "resources": {
                    "backend": "local",
                    "gpus": 0,
                    "cpus": 1,
                    "memory_gb": 2,
                    "time": "00:05:00",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return job_file.resolve(), workspace.resolve()


def _arguments_for(
    script_case: ScriptCase,
    job_file: Path,
    workspace: Path,
    experiment_dir: Path,
) -> List[str]:
    """Build each script's CLI using explicit absolute path arguments."""
    if script_case.path.name == "validate_job.py":
        return [
            "--job-file",
            str(job_file),
            "--workspace",
            str(workspace),
        ]
    if script_case.path.name == "initialize_run.py":
        return [
            "--job-file",
            str(job_file),
            "--experiment-dir",
            str(experiment_dir.resolve()),
            "--dry-run",
        ]
    raise AssertionError(f"Unhandled helper script: {script_case.path}")


def _run_script(script: Path, arguments: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Execute a helper script and capture its machine-readable interface."""
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _parse_json_stdout(completed: subprocess.CompletedProcess[str]) -> Dict[str, Any]:
    """Assert stdout is one structured JSON document and return it."""
    assert completed.stdout.strip(), f"script emitted no stdout; stderr={completed.stderr!r}"
    parsed = json.loads(completed.stdout)
    assert isinstance(parsed, dict), "script output must be a JSON object"
    return parsed


def _without_volatile_timestamps(value: Any) -> Any:
    """Normalize only time-derived output fields before cwd comparisons."""
    if isinstance(value, dict):
        return {
            key: "<timestamp>" if key == "timestamp" else _without_volatile_timestamps(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_without_volatile_timestamps(item) for item in value]
    if isinstance(value, str):
        return RUN_TIMESTAMP.sub("<timestamp>", value)
    return value


def _imported_modules(script: Path) -> Iterable[str]:
    """Yield modules imported by a helper script's Python syntax tree."""
    tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


@pytest.mark.parametrize(
    ("case_number", "directory_name"),
    GENERATED_DIRECTORIES,
    ids=[f"generated-cwds-{case_number}" for case_number, _ in GENERATED_DIRECTORIES],
)
@pytest.mark.parametrize("script_case", SCRIPT_CASES, ids=lambda case: case.path.stem)
def test_property_3_scripts_are_cwd_independent_json_interfaces(
    tmp_path: Path,
    script_case: ScriptCase,
    case_number: int,
    directory_name: str,
) -> None:
    """Property 3: explicit paths produce equivalent JSON from arbitrary cwd paths.

    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    """
    inputs_root = tmp_path / f"inputs-{case_number}"
    job_file, workspace = _write_valid_job(inputs_root)
    experiment_dir = inputs_root / "experiment"
    experiment_dir.mkdir()

    cwd_one = tmp_path / directory_name / "first"
    cwd_two = tmp_path / f"other-{directory_name}" / "nested" / "second"
    cwd_one.mkdir(parents=True)
    cwd_two.mkdir(parents=True)
    arguments = _arguments_for(
        script_case, job_file, workspace, experiment_dir
    )

    first = _run_script(script_case.path, arguments, cwd_one)
    second = _run_script(script_case.path, arguments, cwd_two)

    assert first.returncode == second.returncode == 0
    first_json = _parse_json_stdout(first)
    second_json = _parse_json_stdout(second)
    assert _without_volatile_timestamps(first_json) == _without_volatile_timestamps(
        second_json
    )

    if script_case.modifies_state:
        assert "--dry-run" in arguments
        assert first_json["status"] == "success"
        assert first_json["data"]["dry_run"] is True
        assert first_json["data"]["status"] == "preview"
        assert not (experiment_dir / "runs").exists()
    else:
        assert first_json["valid"] is True


@pytest.mark.parametrize("script_case", SCRIPT_CASES, ids=lambda case: case.path.stem)
@pytest.mark.parametrize("cwd_label", ("outside-one", "outside two"))
def test_property_3_missing_files_are_clear_json_errors(
    tmp_path: Path,
    script_case: ScriptCase,
    cwd_label: str,
) -> None:
    """Property 3: every helper reports missing explicit inputs as JSON.

    **Validates: Requirements 7.2, 7.3, 7.7**
    """
    cwd = tmp_path / cwd_label
    cwd.mkdir()
    missing_job = (tmp_path / "missing inputs" / "absent-job.yaml").resolve()
    existing_root = tmp_path / "existing-root"
    existing_root.mkdir()

    if script_case.path.name == "validate_job.py":
        arguments = [
            "--job-file",
            str(missing_job),
            "--workspace",
            str(existing_root.resolve()),
        ]
    else:
        arguments = [
            "--job-file",
            str(missing_job),
            "--experiment-dir",
            str(existing_root.resolve()),
            "--dry-run",
        ]

    completed = _run_script(script_case.path, arguments, cwd)
    output = _parse_json_stdout(completed)

    assert completed.returncode != 0
    errors = output.get("errors")
    assert isinstance(errors, list) and errors
    combined_message = " ".join(
        [str(output.get("message", "")), *(str(error) for error in errors)]
    ).lower()
    assert str(missing_job).lower() in combined_message
    assert "not found" in combined_message or "does not exist" in combined_message


def test_property_3_all_helper_scripts_avoid_project_src_imports() -> None:
    """Property 3: helper scripts remain self-contained outside project src/.

    **Validates: Requirements 7.6**
    """
    assert {path.name for path in SCRIPT_PATHS} == EXPECTED_SCRIPTS

    imports_by_script: Mapping[str, List[str]] = {
        script.name: list(_imported_modules(script)) for script in SCRIPT_PATHS
    }
    forbidden = {
        script: [module for module in modules if module == "src" or module.startswith("src.")]
        for script, modules in imports_by_script.items()
    }
    assert not any(forbidden.values()), f"project src imports found: {forbidden}"
