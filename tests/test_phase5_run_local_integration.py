"""Integration tests for Phase 5 local execution (run_local.py).

Feature: phase-5-local-execution

These tests build an isolated experiment under tmp_path, call initialize_run.py
to create the run directory, then run_local.py to execute a tiny CPU entrypoint.
The repository example experiment is never touched.

Validates: Requirements 2.5, 3.6, 6.3, 7.1, 7.2, 7.4, 8.1, 9.3, 10.2, 10.3, 11.2
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPTS = WORKSPACE / ".agents" / "skills" / "train-llm" / "scripts"
INIT = SCRIPTS / "initialize_run.py"
RUN_LOCAL = SCRIPTS / "run_local.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_experiment(ws: Path, *, approved: bool = True) -> Path:
    exp = ws / "experiments" / "demo"
    _write(exp / "plan.md", (
        "---\n"
        "schema_version: 1\n"
        "experiment_id: demo\n"
        f"status: {'approved' if approved else 'awaiting_approval'}\n"
        "approval:\n"
        f"  status: {'approved' if approved else 'pending'}\n"
        "  approved_by: tester\n"
        "  approved_at: \"2025-01-01T00:00:00Z\"\n"
        "  approved_commit: abc\n"
        "---\n# Demo\n"
    ))
    return exp


def _job(entrypoint: str, *, gpus: int = 0, time: str = "00:01:00", params=None) -> str:
    data = {
        "job_id": "demo",
        "type": "train",
        "entrypoint": entrypoint,
        "config_style": "argument",
        "parameters": params or {"epochs": 1},
        "resources": {"backend": "local", "gpus": gpus, "cpus": 1,
                      "memory_gb": 1, "time": time},
    }
    return yaml.safe_dump(data, sort_keys=False)


def _init_run(ws: Path, exp: Path, job_name: str) -> Path:
    completed = subprocess.run(
        [sys.executable, str(INIT), "--job-file", str(exp / "jobs" / job_name),
         "--experiment-dir", str(exp)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(completed.stdout)
    return Path(data["data"]["run_dir"])


def _run_local(ws: Path, run_dir: Path, default_timeout: int = 600):
    completed = subprocess.run(
        [sys.executable, str(RUN_LOCAL), "--run-dir", str(run_dir),
         "--workspace", str(ws), "--default-timeout", str(default_timeout)],
        capture_output=True, text=True, check=False,
    )
    return completed, json.loads(completed.stdout)


def test_successful_local_run(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    exp = _make_experiment(ws)
    _write(ws / "src" / "ok.py", (
        "import sys\n"
        "print('run ok; https://wandb.ai/lab/proj/runs/zzz')\n"
        "print('argv', sys.argv[1:])\n"
    ))
    _write(exp / "jobs" / "train.yaml", _job("src/ok.py"))
    run_dir = _init_run(ws, exp, "train.yaml")
    completed, result = _run_local(ws, run_dir)

    assert completed.returncode == 0
    assert result["data"]["run_status"] == "succeeded"
    assert result["data"]["exit_code"] == 0

    record = yaml.safe_load((run_dir / "run.yaml").read_text())
    assert record["status"] == "succeeded"
    assert record["started_at"] and record["completed_at"]
    assert record["wandb_url"] == "https://wandb.ai/lab/proj/runs/zzz"

    assert (run_dir / "logs" / "stdout.log").exists()
    assert (run_dir / "logs" / "stderr.log").exists()
    assert "run ok" in (run_dir / "logs" / "stdout.log").read_text()

    history = (exp / "history.md").read_text()
    assert "succeeded" in history and run_dir.name in history


def test_nonzero_exit_is_recorded_failure(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    exp = _make_experiment(ws)
    _write(ws / "src" / "bad.py", "import sys\nsys.exit(5)\n")
    _write(exp / "jobs" / "train.yaml", _job("src/bad.py"))
    run_dir = _init_run(ws, exp, "train.yaml")
    completed, result = _run_local(ws, run_dir)

    assert result["data"]["run_status"] == "failed"
    assert result["data"]["exit_code"] == 5
    record = yaml.safe_load((run_dir / "run.yaml").read_text())
    assert record["status"] == "failed"
    assert record["exit_code"] == 5


def test_missing_entrypoint_records_failure_without_spawn(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    exp = _make_experiment(ws)
    _write(exp / "jobs" / "train.yaml", _job("src/missing.py"))
    run_dir = _init_run(ws, exp, "train.yaml")
    completed, result = _run_local(ws, run_dir)

    assert completed.returncode == 1
    assert result["data"]["run_status"] == "failed"
    # No process started -> no stdout.log written by run_process
    assert not (run_dir / "logs" / "stdout.log").exists()
    history = (exp / "history.md").read_text()
    assert "failed" in history


def test_gpu_job_defers_to_slurm(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    exp = _make_experiment(ws)
    _write(ws / "src" / "ok.py", "print('x')\n")
    _write(exp / "jobs" / "train.yaml", _job("src/ok.py", gpus=1))
    run_dir = _init_run(ws, exp, "train.yaml")
    completed, result = _run_local(ws, run_dir)

    assert completed.returncode == 1
    assert result["data"]["decision"] == "deferred"
    history = (exp / "history.md").read_text()
    assert "Deferred" in history or "deferred" in history


def test_unapproved_experiment_is_declined(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    exp = _make_experiment(ws, approved=False)
    _write(ws / "src" / "ok.py", "print('x')\n")
    _write(exp / "jobs" / "train.yaml", _job("src/ok.py"))
    run_dir = _init_run(ws, exp, "train.yaml")
    completed, result = _run_local(ws, run_dir)

    assert completed.returncode == 1
    assert result["data"]["decision"] == "approval_required"


def test_timeout_is_recorded(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    exp = _make_experiment(ws)
    _write(ws / "src" / "slow.py", "import time\ntime.sleep(10)\n")
    _write(exp / "jobs" / "train.yaml", _job("src/slow.py", time="00:00:01"))
    run_dir = _init_run(ws, exp, "train.yaml")
    completed, result = _run_local(ws, run_dir, default_timeout=1)

    assert result["data"]["run_status"] == "timed_out"
    record = yaml.safe_load((run_dir / "run.yaml").read_text())
    assert record["status"] == "timed_out"
    assert record["timeout_seconds"] == 1


def test_writes_confined_to_run_directory(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    exp = _make_experiment(ws)
    _write(ws / "src" / "ok.py", "print('x')\n")
    _write(exp / "jobs" / "train.yaml", _job("src/ok.py"))
    # snapshot src/ before run
    before = {p.name for p in (ws / "src").iterdir()}
    run_dir = _init_run(ws, exp, "train.yaml")
    _run_local(ws, run_dir)
    after = {p.name for p in (ws / "src").iterdir()}
    assert before == after  # execution did not write into src/
    # all run outputs under the run dir
    assert (run_dir / "run.yaml").exists()
    assert (run_dir / "logs").is_dir()
