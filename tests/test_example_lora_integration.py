"""Integration coverage for the example LoRA rank-ablation experiment.

Validates: Requirements 8.1, 8.2, 8.3, 10.1
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml


WORKSPACE = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = WORKSPACE / "experiments" / "example-lora-rank-ablation"
TRAIN_JOB = EXPERIMENT_DIR / "jobs" / "train.yaml"
VALIDATE_SCRIPT = (
    WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts" / "validate_job.py"
)
INITIALIZE_SCRIPT = (
    WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts" / "initialize_run.py"
)
RUN_ID_PATTERN = re.compile(
    r"^train-train-lora-rank__\d{8}T\d{6}$"
)


def run_script(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run a helper script with the active test interpreter."""
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        check=False,
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO-8601 value emitted by the helper scripts."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_existing_train_job_is_schema_valid_except_for_missing_example_entrypoint() -> None:
    """Validate the tracked job and preserve its real missing-entrypoint result."""
    completed = run_script(
        VALIDATE_SCRIPT,
        "--job-file",
        str(TRAIN_JOB),
        "--workspace",
        str(WORKSPACE),
    )

    assert completed.returncode == 1, completed.stderr
    result = json.loads(completed.stdout)

    assert result["valid"] is False
    assert result["warnings"] == []
    assert result["checked"] == {
        "required_fields": True,
        "entrypoint_exists": False,
        "quota_compliance": False,
    }
    assert result["errors"] == [
        f"Entrypoint file not found: {(WORKSPACE / 'src' / 'train_lora.py').absolute()}",
        "  (looking for 'src/train_lora.py' relative to workspace "
        f"{WORKSPACE.absolute()})",
    ]

    job = yaml.safe_load(TRAIN_JOB.read_text(encoding="utf-8"))
    assert set(("job_id", "type", "entrypoint", "parameters", "resources")) <= job.keys()
    assert job["type"] == "train"
    assert job["matrix"] == {"lora_rank": [4, 8, 16, 32]}
    assert job["resources"]["backend"] == "slurm"
    assert set(job["wandb"]) >= {"enabled", "group", "tags"}
    assert set(job["huggingface"]) >= {"push", "repo"}


def test_initialize_run_in_temporary_experiment_matches_run_schemas(tmp_path: Path) -> None:
    """Initialize real artifacts in isolation and verify their documented schemas."""
    source_runs_before = sorted(path.name for path in (EXPERIMENT_DIR / "runs").iterdir())
    isolated_experiment = tmp_path / EXPERIMENT_DIR.name
    shutil.copytree(EXPERIMENT_DIR, isolated_experiment)
    shutil.rmtree(isolated_experiment / "runs")
    (isolated_experiment / "runs").mkdir()
    isolated_job = isolated_experiment / "jobs" / "train.yaml"

    completed = run_script(
        INITIALIZE_SCRIPT,
        "--job-file",
        str(isolated_job),
        "--experiment-dir",
        str(isolated_experiment),
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["status"] == "success"
    assert output["errors"] == []
    assert output["warnings"] == [
        "Matrix parameter detected but not resolved "
        "(matrix resolution is planned for future phases)"
    ]

    data = output["data"]
    assert RUN_ID_PATTERN.fullmatch(data["run_id"])
    assert data["status"] == "initialized"
    assert data.get("dry_run") is None
    parse_iso8601(data["timestamp"])

    run_dir = Path(data["run_dir"])
    logs_dir = run_dir / "logs"
    run_yaml_path = run_dir / "run.yaml"
    resolved_job_path = run_dir / "resolved-job.yaml"
    assert run_dir.parent == isolated_experiment / "runs"
    assert run_dir.is_dir()
    assert logs_dir.is_dir()
    assert run_yaml_path.is_file()
    assert resolved_job_path.is_file()
    assert set(map(Path, data["created_files"])) == {
        run_dir,
        logs_dir,
        run_yaml_path,
        resolved_job_path,
    }

    run_metadata = yaml.safe_load(run_yaml_path.read_text(encoding="utf-8"))
    assert set(("run_id", "job_file", "experiment_id", "status", "created_at")) <= run_metadata.keys()
    assert run_metadata["run_id"] == data["run_id"]
    assert run_metadata["job_file"] == str(isolated_job.resolve())
    assert run_metadata["experiment_id"] == "example-lora-rank-ablation"
    assert run_metadata["status"] == "initialized"
    parse_iso8601(run_metadata["created_at"])
    assert run_metadata["started_at"] is None
    assert run_metadata["completed_at"] is None
    assert run_metadata["exit_code"] is None
    assert run_metadata["metrics"] == {}
    assert run_metadata["wandb_run_id"] is None
    assert run_metadata["checkpoint_path"] is None

    source_job = yaml.safe_load(isolated_job.read_text(encoding="utf-8"))
    resolved_job = yaml.safe_load(resolved_job_path.read_text(encoding="utf-8"))
    assert resolved_job == source_job
    assert set(("job_id", "type", "entrypoint", "parameters", "resources")) <= resolved_job.keys()
    assert sorted(path.name for path in (EXPERIMENT_DIR / "runs").iterdir()) == source_runs_before
