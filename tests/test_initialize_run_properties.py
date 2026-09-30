"""Property tests for train-llm run initialization."""

from __future__ import annotations

import importlib.util
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import pytest
import yaml


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    WORKSPACE
    / ".agents"
    / "skills"
    / "train-llm"
    / "scripts"
    / "initialize_run.py"
)
RUN_ID_PATTERN = re.compile(
    r"^(train|evaluate|custom)-([a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?)__"
    r"(\d{8}T\d{6})$"
)


def _load_initialize_run_module() -> Any:
    """Load the helper script without requiring its directory to be a package."""
    spec = importlib.util.spec_from_file_location("initialize_run", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INITIALIZE_RUN = _load_initialize_run_module()


def _generated_job_configs(seed: int = 20250214, count: int = 36) -> Iterable[Tuple[int, Dict[str, Any]]]:
    """Generate reproducible, varied valid job configurations."""
    rng = random.Random(seed)
    job_types = ("train", "evaluate", "custom")

    for case_number in range(count):
        job_type = job_types[case_number % len(job_types)]
        suffix = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(rng.randint(1, 18)))
        job_id = f"case-{case_number}-{suffix}"
        config: Dict[str, Any] = {
            "job_id": job_id,
            "type": job_type,
            "entrypoint": f"src/{job_type}.py",
            "config_style": rng.choice(("argument", "yaml", "json")),
            "parameters": {
                "learning_rate": rng.choice((1e-5, 2e-5, 5e-4)),
                "epochs": rng.randint(1, 20),
                "gradient_checkpointing": rng.choice((True, False)),
                "tags": [f"generated-{case_number}", job_type],
                "nested": {"seed": rng.randint(0, 2**31 - 1)},
            },
            "resources": {
                "backend": "local",
                "gpus": rng.randint(0, 4),
                "cpus": rng.randint(1, 32),
                "memory_gb": rng.choice((4, 8, 16, 32, 64)),
                "time": f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00",
            },
            "wandb": {
                "enabled": rng.choice((True, False)),
                "group": f"property-{case_number}",
                "tags": [job_type],
            },
            "huggingface": {"push": "never", "repo": None},
        }
        if case_number % 4 == 0:
            config["matrix"] = {
                "learning_rate": [1e-5, 2e-5],
                "batch_size": [1, 8],
            }
        yield case_number, config


GENERATED_JOBS = tuple(_generated_job_configs())


@pytest.mark.parametrize(
    ("case_number", "job_config"),
    GENERATED_JOBS,
    ids=[f"generated-job-{case_number}" for case_number, _ in GENERATED_JOBS],
)
def test_property_2_run_initialization_consistency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    case_number: int,
    job_config: Dict[str, Any],
) -> None:
    """Property 2: every valid generated job initializes a consistent run.

    **Validates: Requirements 4.18, 4.19, 4.20, 4.21, 4.22**
    """
    experiment_dir = tmp_path / f"experiment-{case_number}"
    jobs_dir = experiment_dir / "jobs"
    jobs_dir.mkdir(parents=True)
    job_file = jobs_dir / "job.yaml"
    job_file.write_text(yaml.safe_dump(job_config, sort_keys=False), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "--job-file",
            str(job_file),
            "--experiment-dir",
            str(experiment_dir),
        ],
    )

    with pytest.raises(SystemExit) as exit_info:
        INITIALIZE_RUN.main()

    assert exit_info.value.code == 0
    stdout = capsys.readouterr().out
    output = json.loads(stdout)
    assert output["status"] == "success"
    assert output["errors"] == []

    data = output["data"]
    match = RUN_ID_PATTERN.fullmatch(data["run_id"])
    assert match is not None
    assert match.group(1) == job_config["type"]
    assert match.group(2) == job_config["job_id"]
    datetime.strptime(match.group(3), "%Y%m%dT%H%M%S")
    datetime.fromisoformat(data["timestamp"])

    run_dir = Path(data["run_dir"])
    logs_dir = run_dir / "logs"
    run_yaml_path = run_dir / "run.yaml"
    resolved_job_path = run_dir / "resolved-job.yaml"
    expected_paths = {
        str(run_dir.resolve()),
        str(logs_dir.resolve()),
        str(run_yaml_path.resolve()),
        str(resolved_job_path.resolve()),
    }

    assert data["status"] == "initialized"
    assert run_dir == experiment_dir / "runs" / data["run_id"]
    assert run_dir.is_dir()
    assert logs_dir.is_dir()
    assert run_yaml_path.is_file()
    assert resolved_job_path.is_file()
    assert len(data["created_files"]) == 4
    assert set(data["created_files"]) == expected_paths

    run_metadata = yaml.safe_load(run_yaml_path.read_text(encoding="utf-8"))
    assert run_metadata == {
        "run_id": data["run_id"],
        "job_file": str(job_file.resolve()),
        "experiment_id": experiment_dir.name,
        "status": "initialized",
        "created_at": run_metadata["created_at"],
        "started_at": None,
        "completed_at": None,
        "exit_code": None,
        "metrics": {},
        "wandb_run_id": None,
        "checkpoint_path": None,
    }
    datetime.fromisoformat(run_metadata["created_at"])

    resolved_job = yaml.safe_load(resolved_job_path.read_text(encoding="utf-8"))
    assert resolved_job == job_config
