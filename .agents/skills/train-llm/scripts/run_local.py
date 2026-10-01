#!/usr/bin/env python3
"""
Run an approved job locally and record the outcome (Phase 5).

This helper composes with initialize_run.py: that script creates the run
directory, run.yaml (status: initialized), and resolved-job.yaml. run_local.py
consumes an existing run directory, reads resolved-job.yaml and the experiment
plan's approval status, runs a short local CPU job, captures stdout/stderr,
tracks the run lifecycle, and appends a history.md entry.

Hard boundaries (Phase 5):
  - GPU jobs and CPU-heavy jobs are hard-rejected (deferred to Slurm / Phase 6);
    no local process is ever spawned for them.
  - No live W&B API calls (Phase 7); a W&B URL is only parsed from log text.
  - No Hugging Face Hub uploads (Phase 8), no Git operations, no network calls.
  - All writes are confined to the run directory plus the experiment history.md.

Usage:
  run_local.py --run-dir PATH --workspace PATH [--plan-file PATH]
               [--default-timeout SECONDS] [--version]

Output (JSON):
  {
    "status": "success" | "error",
    "message": "...",
    "data": {
      "run_id": "...", "decision": "...", "run_status": "...",
      "exit_code": 0, "created_files": [...], "timestamp": "..."
    },
    "errors": [...], "warnings": [...]
  }

Exit Codes:
  0 - Local run executed and recorded (succeeded or recorded failure/timeout)
  1 - Declined (approval required, deferred to Slurm, unsupported style, prep failure)
  2 - Runtime error (filesystem/parse error)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

__version__ = "0.1.0"

DEFAULT_TIMEOUT_SECONDS = 600
LOCAL_CPU_HOURS_THRESHOLD = 4.0
VALID_CONFIG_STYLES = ("argument", "hydra", "json", "yaml")
_FRAMEWORK_SUBSTRINGS = ("torch", "jax", "accelerate", "lightning", "tensorflow", "keras")
_CREDENTIAL_KEY_PATTERN = re.compile(
    r"(TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.IGNORECASE
)
_WANDB_URL_PATTERN = re.compile(r"https?://(?:[\w.-]*\.)?wandb\.ai/[^\s'\"<>]+")


# --------------------------------------------------------------------------- #
# Decision records
# --------------------------------------------------------------------------- #
class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ExecDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"
    DECLINE_MISSING_APPROVAL = "missing_approval"
    DEFER_SLURM = "deferred"
    DECLINE_CONFIG_STYLE = "unsupported_config_style"


class EnvManager(str, Enum):
    CONDA = "conda"
    UV = "uv"
    VENV = "venv"
    SYSTEM = "system"


@dataclass
class EnvMarkers:
    conda_active: bool = False
    conda_manifest: bool = False
    conda_env_name: Optional[str] = None
    uv_project: bool = False
    uv_available: bool = False
    virtual_env: Optional[str] = None


@dataclass
class ProcessOutcome:
    kind: str  # "exited" | "timeout" | "cancelled" | "prep_error"
    exit_code: Optional[int]
    elapsed_seconds: float = 0.0
    reason: Optional[str] = None


class UnsupportedConfigStyle(ValueError):
    """Raised when a job declares a config_style outside the supported set."""


# --------------------------------------------------------------------------- #
# Requirement 1 — Approval gating
# --------------------------------------------------------------------------- #
def decide_approval(approval_status: Optional[str]) -> ExecDecision:
    """approved -> PROCEED; present non-approved -> DECLINE_APPROVAL;
    missing/None -> DECLINE_MISSING_APPROVAL."""
    if approval_status is None:
        return ExecDecision.DECLINE_MISSING_APPROVAL
    if str(approval_status).strip().lower() == "approved":
        return ExecDecision.PROCEED
    return ExecDecision.DECLINE_APPROVAL


def read_approval_status(plan_path: Path) -> Optional[str]:
    """Read approval.status from a plan.md with YAML frontmatter. Returns None
    when the plan is missing or has no approval.status field."""
    if not plan_path.exists() or not plan_path.is_file():
        return None
    text = plan_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    frontmatter = text[text.index("\n") + 1 : end]
    try:
        import yaml
    except ImportError:  # pragma: no cover - exercised only without PyYAML
        return None
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    approval = data.get("approval")
    if not isinstance(approval, dict) or "status" not in approval:
        return None
    status = approval.get("status")
    return None if status is None else str(status)


# --------------------------------------------------------------------------- #
# Requirement 2 — Slurm deferral
# --------------------------------------------------------------------------- #
def parse_time_to_hours(time_str: Optional[str]) -> float:
    """Convert HH:MM:SS to fractional hours; default 1.0 hour when absent/invalid."""
    if not time_str or not isinstance(time_str, str):
        return 1.0
    parts = time_str.strip().split(":")
    if len(parts) != 3:
        return 1.0
    try:
        hours, minutes, seconds = (int(p) for p in parts)
    except ValueError:
        return 1.0
    return hours + minutes / 60.0 + seconds / 3600.0


def estimate_cpu_hours(cpus: int, time_str: Optional[str]) -> float:
    """cpus * hours derived from HH:MM:SS."""
    try:
        cpu_count = int(cpus)
    except (TypeError, ValueError):
        cpu_count = 1
    if cpu_count < 1:
        cpu_count = 1
    return cpu_count * parse_time_to_hours(time_str)


def classify_execution(resources: Optional[Dict[str, Any]]) -> ExecDecision:
    """gpus>0 OR cpu_hours>4 -> DEFER_SLURM; else PROCEED."""
    resources = resources or {}
    try:
        gpus = int(resources.get("gpus", 0) or 0)
    except (TypeError, ValueError):
        gpus = 0
    if gpus > 0:
        return ExecDecision.DEFER_SLURM
    cpu_hours = estimate_cpu_hours(resources.get("cpus", 1), resources.get("time"))
    if cpu_hours > LOCAL_CPU_HOURS_THRESHOLD:
        return ExecDecision.DEFER_SLURM
    return ExecDecision.PROCEED


# --------------------------------------------------------------------------- #
# Requirement 3 — Environment detection
# --------------------------------------------------------------------------- #
def detect_environment(markers: EnvMarkers) -> EnvManager:
    """Priority conda > uv > venv > system."""
    if markers.conda_active or markers.conda_manifest:
        return EnvManager.CONDA
    if markers.uv_project and markers.uv_available:
        return EnvManager.UV
    if markers.virtual_env:
        return EnvManager.VENV
    return EnvManager.SYSTEM


def activation_prefix(manager: EnvManager, markers: EnvMarkers) -> List[str]:
    """Build the activation prefix tokens for the detected manager."""
    if manager == EnvManager.CONDA:
        name = markers.conda_env_name or os.environ.get("CONDA_DEFAULT_ENV")
        if name:
            return ["conda", "run", "-n", name]
        return ["conda", "run"]
    if manager == EnvManager.UV:
        return ["uv", "run"]
    if manager == EnvManager.VENV and markers.virtual_env:
        return [str(Path(markers.virtual_env) / "bin" / "python")]
    return []


def detect_markers(workspace: Path) -> EnvMarkers:
    """Inspect the workspace for environment markers (local reads only)."""
    import shutil

    conda_manifest = (workspace / "environment.yaml").exists() or (
        workspace / "environment.yml"
    ).exists()
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if not virtual_env:
        for candidate in (".venv", "venv"):
            if (workspace / candidate / "bin" / "python").exists():
                virtual_env = str(workspace / candidate)
                break
    return EnvMarkers(
        conda_active=bool(os.environ.get("CONDA_DEFAULT_ENV")),
        conda_manifest=conda_manifest,
        conda_env_name=os.environ.get("CONDA_DEFAULT_ENV"),
        uv_project=(workspace / "pyproject.toml").exists()
        and (workspace / "uv.lock").exists(),
        uv_available=shutil.which("uv") is not None,
        virtual_env=virtual_env,
    )


# --------------------------------------------------------------------------- #
# Requirement 4/5 — Command construction
# --------------------------------------------------------------------------- #
def serialize_parameters(
    params: Optional[Dict[str, Any]],
    config_style: Optional[str],
    param_file_path: Optional[str],
) -> List[str]:
    """Return argv tokens per config_style. Raises UnsupportedConfigStyle for
    unknown styles. json/yaml write a param file (caller provides the path)."""
    params = params or {}
    style = (config_style or "argument").strip().lower()
    if style not in VALID_CONFIG_STYLES:
        raise UnsupportedConfigStyle(style)

    if style == "argument":
        tokens: List[str] = []
        for key, value in params.items():
            tokens.append(f"--{str(key).replace('_', '-')}")
            tokens.append(_scalar(value))
        return tokens
    if style == "hydra":
        return [f"{key}={_scalar(value)}" for key, value in params.items()]
    # json / yaml -> file reference (file written by caller via write_param_file)
    if param_file_path is None:
        raise ValueError("param_file_path required for json/yaml config styles")
    return ["--config", param_file_path]


def _scalar(value: Any) -> str:
    """Render a parameter value as a single token, preserving whitespace."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def write_param_file(params: Dict[str, Any], config_style: str, run_dir: Path) -> Path:
    """Write a json/yaml param file inside the run directory and return its path."""
    style = config_style.strip().lower()
    if style == "json":
        path = run_dir / "params.json"
        path.write_text(json.dumps(params, indent=2), encoding="utf-8")
        return path
    if style == "yaml":
        import yaml

        path = run_dir / "params.yaml"
        path.write_text(yaml.safe_dump(params, sort_keys=False), encoding="utf-8")
        return path
    raise ValueError(f"write_param_file called for non-file style: {config_style}")


def build_command(
    env_prefix: List[str], entrypoint: str, param_tokens: List[str]
) -> List[str]:
    """[*env_prefix, "python", entrypoint, *param_tokens]."""
    return [*env_prefix, "python", str(entrypoint), *param_tokens]


def command_is_framework_free(command: List[str], entrypoint: str) -> bool:
    """True when no forbidden framework substring appears outside the entrypoint."""
    for token in command:
        if token == entrypoint:
            continue
        lowered = token.lower()
        if any(fw in lowered for fw in _FRAMEWORK_SUBSTRINGS):
            return False
    return True


# --------------------------------------------------------------------------- #
# Requirement 7.3 — Write planning
# --------------------------------------------------------------------------- #
def plan_writes(job_config: Dict[str, Any], run_dir: Path) -> List[str]:
    """All paths run_local may write, each under run_dir."""
    logs = run_dir / "logs"
    writes = [
        str((logs / "stdout.log")),
        str((logs / "stderr.log")),
        str((run_dir / "run.yaml")),
    ]
    style = str(job_config.get("config_style", "argument")).strip().lower()
    if style == "json":
        writes.append(str(run_dir / "params.json"))
    elif style == "yaml":
        writes.append(str(run_dir / "params.yaml"))
    return writes


# --------------------------------------------------------------------------- #
# Requirement 10 — Timeout parsing
# --------------------------------------------------------------------------- #
def parse_timeout(resources: Optional[Dict[str, Any]], default_seconds: int) -> int:
    """HH:MM:SS -> seconds, or default when absent/invalid."""
    resources = resources or {}
    time_str = resources.get("time")
    if not time_str or not isinstance(time_str, str):
        return default_seconds
    parts = time_str.strip().split(":")
    if len(parts) != 3:
        return default_seconds
    try:
        hours, minutes, seconds = (int(p) for p in parts)
    except ValueError:
        return default_seconds
    total = hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else default_seconds


# --------------------------------------------------------------------------- #
# Requirement 8 — Status mapping
# --------------------------------------------------------------------------- #
def map_status(outcome: ProcessOutcome) -> RunStatus:
    if outcome.kind == "timeout":
        return RunStatus.TIMED_OUT
    if outcome.kind == "cancelled":
        return RunStatus.CANCELLED
    if outcome.kind == "prep_error":
        return RunStatus.FAILED
    # exited
    return RunStatus.SUCCEEDED if outcome.exit_code == 0 else RunStatus.FAILED


def normalize_status(on_disk_status: str) -> RunStatus:
    mapping = {"initialized": RunStatus.CREATED, "completed": RunStatus.SUCCEEDED}
    key = str(on_disk_status).strip().lower()
    if key in mapping:
        return mapping[key]
    for status in RunStatus:
        if status.value == key:
            return status
    return RunStatus.CREATED


# --------------------------------------------------------------------------- #
# Requirement 7.5 — W&B URL parsing
# --------------------------------------------------------------------------- #
def parse_wandb_url(log_text: str) -> Optional[str]:
    match = _WANDB_URL_PATTERN.search(log_text or "")
    return match.group(0) if match else None


# --------------------------------------------------------------------------- #
# Requirement 11 — History formatting
# --------------------------------------------------------------------------- #
def format_history_entry(
    run_id: str,
    job_ref: str,
    status: RunStatus,
    timestamp: str,
    exit_code: Optional[int],
    wandb_url: Optional[str],
) -> str:
    lines = [
        f"## {timestamp} — Local Run {status.value.capitalize()}",
        "",
        f"- Run ID: {run_id}",
        f"- Job: {job_ref}",
        f"- Status: {status.value}",
    ]
    if status == RunStatus.SUCCEEDED:
        if exit_code is not None:
            lines.append(f"- Exit code: {exit_code}")
        if wandb_url:
            lines.append(f"- W&B: {wandb_url}")
    elif exit_code is not None:
        lines.append(f"- Exit code: {exit_code}")
    lines.append("")
    return "\n".join(lines) + "\n"


def append_history(history_path: Path, entry: str) -> None:
    """Create history.md if absent and append entry, preserving prior content."""
    existing = ""
    if history_path.exists():
        existing = history_path.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            existing += "\n"
    header = "" if existing else "# Experiment History\n\n"
    history_path.write_text(existing + header + entry, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Requirement 12 — Redaction
# --------------------------------------------------------------------------- #
def redact_environment(env_map: Dict[str, Any]) -> Dict[str, Any]:
    """Drop values for credential-like keys; keep names only form."""
    present_names = sorted(env_map.keys())
    safe = {
        key: value
        for key, value in env_map.items()
        if not _CREDENTIAL_KEY_PATTERN.search(str(key))
    }
    return {"env_names_present": present_names, "safe_values": safe}


# --------------------------------------------------------------------------- #
# Requirement 7/8/10 — Impure subprocess shell
# --------------------------------------------------------------------------- #
def run_process(
    command: List[str],
    run_dir: Path,
    timeout_seconds: int,
    child_env: Dict[str, str],
    cwd: Path,
) -> ProcessOutcome:
    """The ONLY impure execution step. Captures stdout/stderr to logs,
    enforces the timeout, maps SIGINT/SIGTERM to cancelled, never raises on
    child failure."""
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_dir / "stdout.log"
    stderr_path = logs_dir / "stderr.log"
    start = datetime.now()
    try:
        with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(cwd),
                    env=child_env,
                    stdout=out,
                    stderr=err,
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                elapsed = (datetime.now() - start).total_seconds()
                return ProcessOutcome("timeout", None, elapsed, "timeout exceeded")
            except KeyboardInterrupt:
                elapsed = (datetime.now() - start).total_seconds()
                return ProcessOutcome("cancelled", None, elapsed, "interrupted")
    except FileNotFoundError as exc:
        elapsed = (datetime.now() - start).total_seconds()
        return ProcessOutcome("prep_error", 127, elapsed, f"command not found: {exc}")
    except OSError as exc:
        elapsed = (datetime.now() - start).total_seconds()
        return ProcessOutcome("prep_error", 126, elapsed, f"spawn error: {exc}")
    elapsed = (datetime.now() - start).total_seconds()
    return ProcessOutcome("exited", completed.returncode, elapsed, None)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _result(status, message, data=None, errors=None, warnings=None):
    return {
        "status": status,
        "message": message,
        "data": data or {},
        "errors": errors or [],
        "warnings": warnings or [],
    }


def _load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_run_record(run_dir: Path, updates: Dict[str, Any]) -> None:
    import yaml

    run_yaml = run_dir / "run.yaml"
    record: Dict[str, Any] = {}
    if run_yaml.exists():
        loaded = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            record = loaded
    record.update(updates)
    run_yaml.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")


def execute(
    run_dir: Path,
    plan_path: Path,
    workspace_root: Path,
    default_timeout: int,
) -> Dict[str, Any]:
    """Top-level orchestration. Returns the JSON-shaped result dict."""
    warnings: List[str] = []
    resolved_job = run_dir / "resolved-job.yaml"
    if not resolved_job.exists():
        return _result(
            "error",
            f"resolved-job.yaml not found in run dir: {run_dir}",
            errors=["Missing resolved-job.yaml; run initialize_run.py first"],
        )
    job = _load_yaml(resolved_job) or {}
    run_id = run_dir.name
    job_ref = job.get("job_file") or "resolved-job.yaml"
    now = datetime.now().isoformat()

    # 1. Approval gate
    approval_status = read_approval_status(plan_path)
    approval = decide_approval(approval_status)
    if approval != ExecDecision.PROCEED:
        _write_run_record(run_dir, {"decision": approval.value})
        return _result(
            "error",
            f"Execution declined: {approval.value}",
            data={"run_id": run_id, "decision": approval.value},
            errors=[f"Approval gate: {approval.value}"],
        )

    # 2. Slurm classification
    classification = classify_execution(job.get("resources"))
    if classification == ExecDecision.DEFER_SLURM:
        _write_run_record(
            run_dir,
            {
                "decision": classification.value,
                "error_summary": "GPU or CPU-heavy job deferred to Slurm (Phase 6)",
            },
        )
        append_history(
            plan_path.parent / "history.md",
            format_history_entry(run_id, job_ref, RunStatus.CREATED, now, None, None).replace(
                "Local Run Created", "Local Run Deferred (Slurm, Phase 6)"
            ),
        )
        return _result(
            "error",
            "Job deferred to Slurm (Phase 6): GPU or CPU-heavy",
            data={"run_id": run_id, "decision": classification.value},
            errors=["GPU/CPU-heavy jobs require Slurm (Phase 6)"],
        )

    # 3. Entrypoint check
    entrypoint = str(job.get("entrypoint", ""))
    entrypoint_path = (workspace_root / entrypoint).resolve()
    if not entrypoint or not entrypoint_path.exists():
        _write_run_record(
            run_dir,
            {
                "status": RunStatus.FAILED.value,
                "exit_code": 2,
                "started_at": now,
                "completed_at": datetime.now().isoformat(),
                "error_summary": f"Entrypoint not found: {entrypoint}",
                "decision": ExecDecision.PROCEED.value,
            },
        )
        append_history(
            plan_path.parent / "history.md",
            format_history_entry(run_id, job_ref, RunStatus.FAILED, now, 2, None),
        )
        return _result(
            "error",
            f"Entrypoint not found: {entrypoint}",
            data={"run_id": run_id, "run_status": RunStatus.FAILED.value},
            errors=[f"Missing entrypoint: {entrypoint}"],
        )

    # 4. Config style
    config_style = str(job.get("config_style", "argument")).strip().lower()
    if config_style not in VALID_CONFIG_STYLES:
        _write_run_record(run_dir, {"decision": ExecDecision.DECLINE_CONFIG_STYLE.value})
        return _result(
            "error",
            f"Unsupported config_style: {config_style}",
            data={"run_id": run_id, "decision": ExecDecision.DECLINE_CONFIG_STYLE.value},
            errors=[f"Unsupported config_style: {config_style}"],
        )

    # 5. Environment detection
    markers = detect_markers(workspace_root)
    manager = detect_environment(markers)
    if manager == EnvManager.SYSTEM:
        warnings.append("No project environment detected; using system Python")
    env_prefix = activation_prefix(manager, markers)

    # 6. Command construction
    params = job.get("parameters") or {}
    param_file = None
    if config_style in ("json", "yaml"):
        param_file = str(write_param_file(params, config_style, run_dir))
    param_tokens = serialize_parameters(params, config_style, param_file)
    command = build_command(env_prefix, entrypoint, param_tokens)

    # 7. Timeout + child env
    timeout_seconds = parse_timeout(job.get("resources"), default_timeout)
    child_env = dict(os.environ)

    # 8. Execute
    started = datetime.now().isoformat()
    _write_run_record(
        run_dir,
        {
            "status": RunStatus.RUNNING.value,
            "started_at": started,
            "command": " ".join(command),
            "decision": ExecDecision.PROCEED.value,
        },
    )
    outcome = run_process(command, run_dir, timeout_seconds, child_env, workspace_root)

    # 9. Finalize
    final_status = map_status(outcome)
    log_text = ""
    stdout_log = run_dir / "logs" / "stdout.log"
    if stdout_log.exists():
        log_text = stdout_log.read_text(encoding="utf-8", errors="replace")
    wandb_url = parse_wandb_url(log_text)
    completed = datetime.now().isoformat()
    _write_run_record(
        run_dir,
        {
            "status": final_status.value,
            "completed_at": completed,
            "exit_code": outcome.exit_code,
            "elapsed_seconds": round(outcome.elapsed_seconds, 2),
            "timeout_seconds": timeout_seconds,
            "wandb_url": wandb_url,
            "environment": {
                "manager": manager.value,
                "env_names_present": redact_environment(child_env)["env_names_present"][:50],
            },
            "error_summary": outcome.reason,
        },
    )
    append_history(
        plan_path.parent / "history.md",
        format_history_entry(run_id, job_ref, final_status, started, outcome.exit_code, wandb_url),
    )
    return _result(
        "success",
        f"Local run {final_status.value}: {run_id}",
        data={
            "run_id": run_id,
            "decision": ExecDecision.PROCEED.value,
            "run_status": final_status.value,
            "exit_code": outcome.exit_code,
            "timestamp": completed,
        },
        warnings=warnings,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an approved job locally and record the outcome (Phase 5).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    needs_required = "--version" not in sys.argv and "--help" not in sys.argv
    parser.add_argument("--run-dir", required=needs_required, help="Existing run directory")
    parser.add_argument("--workspace", required=needs_required, help="Workspace root")
    parser.add_argument("--plan-file", help="Path to experiment plan.md (default: run-dir/../../plan.md)")
    parser.add_argument("--default-timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()


def main() -> None:
    try:
        import yaml  # noqa: F401
    except ImportError:
        print(json.dumps(_result("error", "PyYAML is required but not installed.",
                                   errors=["Missing dependency: PyYAML"]), indent=2))
        sys.exit(2)

    args = parse_arguments()
    run_dir = Path(args.run_dir).resolve()
    workspace = Path(args.workspace).resolve()
    if args.plan_file:
        plan_path = Path(args.plan_file).resolve()
    else:
        plan_path = (run_dir.parent.parent / "plan.md").resolve()

    if not run_dir.exists() or not run_dir.is_dir():
        print(json.dumps(_result("error", f"Run directory not found: {run_dir}",
                                   errors=["Missing run directory"]), indent=2))
        sys.exit(2)

    try:
        result = execute(run_dir, plan_path, workspace, args.default_timeout)
    except UnsupportedConfigStyle as exc:
        result = _result("error", f"Unsupported config_style: {exc}",
                         errors=[f"Unsupported config_style: {exc}"])
    except Exception as exc:  # noqa: BLE001 - produce structured error, never crash
        result = _result("error", f"Unexpected error: {exc}", errors=[f"Runtime error: {exc}"])

    print(json.dumps(result, indent=2))
    if result["status"] == "success":
        sys.exit(0)
    # Declined decisions and recorded prep failures exit 1; runtime errors exit 2.
    decision = result.get("data", {}).get("decision")
    if decision in {d.value for d in ExecDecision if d != ExecDecision.PROCEED} or \
       result.get("data", {}).get("run_status") == RunStatus.FAILED.value:
        sys.exit(1)
    sys.exit(2)


if __name__ == "__main__":
    main()
