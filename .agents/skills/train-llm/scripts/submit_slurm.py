#!/usr/bin/env python3
"""
Submit an approved job to Slurm over SSH and record the linkage (Phase 6).

This helper extends the Phase 5 Slurm deferral (run_local.py) into a real
submission path. It composes with initialize_run.py / run_local.py: those create
the run directory, run.yaml, and resolved-job.yaml. submit_slurm.py reads the
stable settings from project-plan.md, the job from resolved-job.yaml, and the
experiment plan's approval status, then generates an sbatch script, submits it
over SSH, polls status, cancels, retries, resumes, and writes Slurm linkage
fields into run.yaml.

Design discipline (Phase 6):
  - PURE LOGIC functions take plain data and return plain data. They perform no
    SSH, no subprocess, no network, and no filesystem mutation.
  - IMPURE I/O passes exclusively through an injected CommandRunner. Production
    uses SSHCommandRunner (constructed only in main()); tests inject a
    FakeCommandRunner. No real SSH or network ever occurs in tests.
  - Mutating remote actions (sbatch, scancel, transfer/clone, env creation)
    require approval.status == approved in the experiment plan.md. Read-only
    probes (ssh echo, test -d, conda env list, sinfo, squeue, sacct,
    scontrol show) are non-mutating and still routed through the CommandRunner.

Output (JSON envelope): {status, message, data, errors, warnings}
Exit Codes:
  0 - Action completed or recorded
  1 - Declined (approval / quota / verification / resume)
  2 - Runtime error
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

__version__ = "0.1.0"

VALID_CONFIG_STYLES = ("argument", "hydra", "json", "yaml")
_FRAMEWORK_SUBSTRINGS = ("torch", "jax", "accelerate", "lightning", "tensorflow", "keras")
_CREDENTIAL_KEY_PATTERN = re.compile(
    r"(TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.IGNORECASE
)
_GPU_TYPES = ("A6000", "PRO6000", "4090")
_SBATCH_ID = re.compile(r"Submitted batch job (\d+)")
_EXCLUDED_SUFFIXES = (".out", ".err")
_EXCLUDED_DIRS = ("checkpoints", "wandb")
CUDA_COMMENT = (
    "# CUDA toolkit is provided by the conda environment and pinned at or below "
    "the\n# NVIDIA driver CUDA ceiling (12.4). No system nvcc, no lmod on this "
    "cluster."
)


# --------------------------------------------------------------------------- #
# Status model
# --------------------------------------------------------------------------- #
class RunStatus(str, Enum):
    SUBMITTED = "submitted"
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    PREEMPTED = "preempted"


class ActionDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class QoSCaps:
    max_gpus: int = 4
    max_cpus: int = 8
    max_mem_gb: int = 80
    max_wall_seconds: int = 2 * 24 * 3600  # 2 days


@dataclass(frozen=True)
class PlanSettings:
    ssh_host: str
    remote_project_root: str
    remote_conda_root: str
    partition: str
    account: str
    qos: str
    caps: QoSCaps = field(default_factory=QoSCaps)
    cuda_ceiling: str = "12.4"


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class QuotaResult:
    ok: bool
    violations: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    host_ok: bool
    path_ok: bool
    env_ok: bool
    env_creation_required: bool = False
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SubmitResult:
    ok: bool
    decision: str
    slurm_job_id: Optional[int] = None
    status: Optional[RunStatus] = None
    errors: List[str] = field(default_factory=list)
    quota: Optional[QuotaResult] = None


@dataclass(frozen=True)
class CancelResult:
    ok: bool
    decision: str
    status: Optional[RunStatus] = None
    errors: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# CommandRunner — the single injected I/O boundary
# --------------------------------------------------------------------------- #
class CommandRunner(Protocol):
    def run(self, argv: Sequence[str], *, remote: bool) -> CommandResult:
        """Execute argv locally or over SSH. The ONLY I/O boundary."""
        ...


class SSHCommandRunner:
    """Production runner. Wraps `ssh <SSH_Host> ...` for remote commands.

    Constructed ONLY in main(); never in tests.
    """

    def __init__(self, ssh_host: str, timeout_seconds: int = 120) -> None:
        self._ssh_host = ssh_host
        self._timeout = timeout_seconds

    def run(self, argv: Sequence[str], *, remote: bool) -> CommandResult:
        if remote:
            command = ["ssh", self._ssh_host, *argv]
        else:
            command = list(argv)
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self._timeout,
                check=False,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(124, "", "command timed out")
        except FileNotFoundError as exc:
            return CommandResult(127, "", f"command not found: {exc}")
        except OSError as exc:
            return CommandResult(126, "", f"spawn error: {exc}")
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


class FakeCommandRunner:
    """Test runner. Returns pre-seeded CommandResults keyed by a substring
    matcher and records every call. Raises on unscripted commands so tests can
    never leak to real I/O.

    scripted: list of (matcher_substring, CommandResult). The first matcher that
    is contained in the joined argv wins.
    """

    def __init__(self, scripted: Optional[Sequence[Tuple[str, CommandResult]]] = None) -> None:
        self._scripted: List[Tuple[str, CommandResult]] = list(scripted or [])
        self.calls: List[Dict[str, Any]] = []

    def run(self, argv: Sequence[str], *, remote: bool) -> CommandResult:
        joined = " ".join(argv)
        self.calls.append({"argv": list(argv), "remote": remote, "joined": joined})
        for matcher, result in self._scripted:
            if matcher in joined:
                return result
        raise AssertionError(
            f"FakeCommandRunner received an unscripted command: {joined!r}"
        )


# --------------------------------------------------------------------------- #
# Pure logic: plan parsing
# --------------------------------------------------------------------------- #
def load_plan_settings(frontmatter: Dict[str, Any]) -> PlanSettings:
    """Build PlanSettings from parsed project-plan.md frontmatter.

    Never prompts for stable settings; reads them from the plan.
    """
    frontmatter = frontmatter or {}
    execution = frontmatter.get("execution") or {}
    environment = frontmatter.get("environment") or {}
    slurm = frontmatter.get("slurm") or {}
    cuda = frontmatter.get("cuda") or {}

    caps = QoSCaps(
        max_gpus=int(slurm.get("max_gpus_per_job", 4)),
        max_cpus=int(slurm.get("max_cpus_per_job", 8)),
        max_mem_gb=int(slurm.get("max_mem_gb_per_job", 80)),
    )
    return PlanSettings(
        ssh_host=str(execution.get("ssh_host", "")),
        remote_project_root=str(execution.get("remote_project_root", "")),
        remote_conda_root=str(environment.get("remote_conda_root", "")),
        partition=str(slurm.get("partition", "")),
        account=str(slurm.get("account", "")),
        qos=str(slurm.get("qos", "")),
        caps=caps,
        cuda_ceiling=str(cuda.get("driver_cuda_version", "12.4")),
    )


# --------------------------------------------------------------------------- #
# Pure logic: time parsing
# --------------------------------------------------------------------------- #
def parse_time_to_seconds(time_str: Optional[str]) -> int:
    """Parse a Slurm walltime into seconds. Accepts D-HH:MM:SS, HH:MM:SS,
    MM:SS, and plain minutes. Returns 0 when absent/invalid."""
    if time_str is None:
        return 0
    text = str(time_str).strip()
    if not text:
        return 0
    days = 0
    if "-" in text:
        day_part, _, text = text.partition("-")
        try:
            days = int(day_part)
        except ValueError:
            return 0
    parts = text.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return 0
    if len(nums) == 3:
        hours, minutes, seconds = nums
    elif len(nums) == 2:
        hours, minutes, seconds = 0, nums[0], nums[1]
    elif len(nums) == 1:
        hours, minutes, seconds = 0, nums[0], 0
    else:
        return 0
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


# --------------------------------------------------------------------------- #
# Pure logic: quota validation
# --------------------------------------------------------------------------- #
def validate_quota(resources: Dict[str, Any], caps: QoSCaps) -> QuotaResult:
    resources = resources or {}

    def _int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    violations: List[str] = []
    if _int(resources.get("gpus", 0), 0) > caps.max_gpus:
        violations.append(f"gpus>{caps.max_gpus}")
    if _int(resources.get("cpus", 1), 1) > caps.max_cpus:
        violations.append(f"cpus>{caps.max_cpus}")
    mem = resources.get("mem_gb", resources.get("memory_gb", 0))
    if _int(mem, 0) > caps.max_mem_gb:
        violations.append(f"mem_gb>{caps.max_mem_gb}")
    if parse_time_to_seconds(resources.get("time")) > caps.max_wall_seconds:
        violations.append("time>2-00:00:00")
    return QuotaResult(ok=not violations, violations=violations)


# --------------------------------------------------------------------------- #
# Pure logic: GRES
# --------------------------------------------------------------------------- #
def build_gres(gpus: int, gpu_type: Optional[str]) -> str:
    if gpu_type and gpu_type in _GPU_TYPES:
        return f"gpu:{gpu_type}:{gpus}"
    return f"gpu:{gpus}"


# --------------------------------------------------------------------------- #
# Pure logic: resource -> sbatch directives
# --------------------------------------------------------------------------- #
def map_resources_to_sbatch(resources: Dict[str, Any], settings: PlanSettings) -> List[str]:
    """Return the directive lines (without the leading `#SBATCH `) for the plan
    and resource values. GRES is only included when gpus > 0."""
    resources = resources or {}

    def _int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    gpus = _int(resources.get("gpus", 0), 0)
    cpus = _int(resources.get("cpus", 1), 1)
    mem_gb = _int(resources.get("mem_gb", resources.get("memory_gb", 0)), 0)
    time_str = str(resources.get("time", "00:30:00"))

    directives = [
        f"--partition={settings.partition}",
        f"--account={settings.account}",
        f"--qos={settings.qos}",
        f"--cpus-per-task={cpus}",
        f"--mem={mem_gb}G",
        f"--time={time_str}",
    ]
    if gpus > 0:
        directives.append(f"--gres={build_gres(gpus, resources.get('gpu_type'))}")
    return directives


# --------------------------------------------------------------------------- #
# Pure logic: log directives and name resolution
# --------------------------------------------------------------------------- #
def build_log_directives(date_prefix: str, is_array: bool) -> Tuple[str, str]:
    stem = f"{date_prefix}_%A_%a_%x" if is_array else f"{date_prefix}_%A_%x"
    return f"{stem}.out", f"{stem}.err"


def resolve_log_name(
    date_prefix: str, job_id: int, task_id: Optional[int], job_name: str
) -> str:
    if task_id is None:
        return f"{date_prefix}_{job_id}_{job_name}"
    return f"{date_prefix}_{job_id}_{task_id}_{job_name}"


# --------------------------------------------------------------------------- #
# Pure logic: parameter serialization (reuses Phase 5 config_style conventions)
# --------------------------------------------------------------------------- #
class UnsupportedConfigStyle(ValueError):
    """Raised when a job declares a config_style outside the supported set."""


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def serialize_parameters(
    params: Optional[Dict[str, Any]],
    config_style: Optional[str],
    param_file_path: Optional[str] = None,
) -> List[str]:
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
    if param_file_path is None:
        raise ValueError("param_file_path required for json/yaml config styles")
    return ["--config", param_file_path]


def command_is_framework_free(tokens: List[str], entrypoint: str) -> bool:
    for token in tokens:
        if token == entrypoint:
            continue
        lowered = token.lower()
        if any(fw in lowered for fw in _FRAMEWORK_SUBSTRINGS):
            return False
    return True


# --------------------------------------------------------------------------- #
# Pure logic: sbatch script generation
# --------------------------------------------------------------------------- #
def generate_sbatch_script(
    job: Dict[str, Any],
    settings: PlanSettings,
    date_prefix: str,
    *,
    conda_env_name: str,
    log_dir: Optional[str] = None,
    param_file_path: Optional[str] = None,
) -> str:
    """Generate the full sbatch script. Pure: no I/O.

    Conda activation lines always appear before the run-command line. The run
    command uses the project-declared entrypoint and introduces no training
    framework token of its own.
    """
    job = job or {}
    job_id_name = str(job.get("job_id") or job.get("name") or "job")
    resources = job.get("resources") or {}
    array_spec = job.get("array")
    dependency_spec = job.get("dependency")
    is_array = array_spec is not None

    lines: List[str] = ["#!/bin/bash"]
    lines.append(f"#SBATCH --job-name={job_id_name}")
    for directive in map_resources_to_sbatch(resources, settings):
        lines.append(f"#SBATCH {directive}")
    if is_array:
        lines.append(f"#SBATCH --array={array_spec}")
    if dependency_spec is not None:
        lines.append(f"#SBATCH --dependency={dependency_spec}")

    out_name, err_name = build_log_directives(date_prefix, is_array)
    base = (log_dir or f"{settings.remote_project_root}/logs").rstrip("/")
    lines.append(f"#SBATCH --output={base}/{out_name}")
    lines.append(f"#SBATCH --error={base}/{err_name}")

    lines.append("")
    lines.append(CUDA_COMMENT)
    lines.append(f"source {settings.remote_conda_root}/etc/profile.d/conda.sh")
    lines.append(f"conda activate {conda_env_name}")
    lines.append("")
    lines.append(f"cd {settings.remote_project_root}")

    entrypoint = str(job.get("entrypoint", ""))
    config_style = str(job.get("config_style", "argument")).strip().lower()
    param_tokens = serialize_parameters(
        job.get("parameters"), config_style, param_file_path
    )
    run_tokens = ["python", entrypoint, *param_tokens]
    lines.append(" ".join(run_tokens))
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Pure logic: job-id parsing
# --------------------------------------------------------------------------- #
def parse_slurm_job_id(sbatch_stdout: str) -> Optional[int]:
    match = _SBATCH_ID.search(sbatch_stdout or "")
    return int(match.group(1)) if match else None


# --------------------------------------------------------------------------- #
# Pure logic: Slurm -> Harness status mapping
# --------------------------------------------------------------------------- #
_STATE_MAP = {
    "PENDING": RunStatus.PENDING,
    "RUNNING": RunStatus.RUNNING,
    "COMPLETED": RunStatus.SUCCEEDED,
    "FAILED": RunStatus.FAILED,
    "OUT_OF_MEMORY": RunStatus.FAILED,
    "CANCELLED": RunStatus.CANCELLED,
    "TIMEOUT": RunStatus.TIMED_OUT,
    "PREEMPTED": RunStatus.PREEMPTED,
}


def map_slurm_state(state: str) -> RunStatus:
    """Map a Slurm state (any case, with trailing annotations like
    'CANCELLED by 1234') to a Harness RunStatus. Unknown states map to PENDING."""
    if not state or not str(state).strip():
        return RunStatus.PENDING
    token = str(state).strip().split()[0].upper()
    return _STATE_MAP.get(token, RunStatus.PENDING)


# --------------------------------------------------------------------------- #
# Pure logic: approval gating
# --------------------------------------------------------------------------- #
def decide_mutating_action(approval_status: Optional[str], kind: str) -> ActionDecision:
    """Mutating remote actions proceed only when approval is 'approved'."""
    if approval_status and str(approval_status).strip().lower() == "approved":
        return ActionDecision.PROCEED
    return ActionDecision.DECLINE_APPROVAL


# --------------------------------------------------------------------------- #
# Pure logic: safety filters
# --------------------------------------------------------------------------- #
def filter_commit_candidates(paths: List[str]) -> List[str]:
    """Exclude raw Slurm logs (.out/.err) and checkpoints/wandb directories."""
    result: List[str] = []
    for path in paths or []:
        if path.endswith(_EXCLUDED_SUFFIXES):
            continue
        if any(part in _EXCLUDED_DIRS for part in path.split("/")):
            continue
        result.append(path)
    return result


def redact_secrets(text: str, env: Dict[str, Any]) -> str:
    """Replace any credential-like env value appearing in text with a redaction
    marker. Only values of credential-like keys are redacted."""
    redacted = text or ""
    for key, value in (env or {}).items():
        if value is None:
            continue
        if _CREDENTIAL_KEY_PATTERN.search(str(key)) and str(value):
            redacted = redacted.replace(str(value), "***REDACTED***")
    return redacted


def redact_environment(env_map: Dict[str, Any]) -> Dict[str, Any]:
    """Names-only report; drop values for credential-like keys."""
    present_names = sorted(env_map.keys())
    safe = {
        key: value
        for key, value in env_map.items()
        if not _CREDENTIAL_KEY_PATTERN.search(str(key))
    }
    return {"env_names_present": present_names, "safe_values": safe}


# --------------------------------------------------------------------------- #
# Pure logic: heavy-job routing
# --------------------------------------------------------------------------- #
CPU_HEAVY_THRESHOLD_HOURS = 4.0


def is_heavy_job(resources: Dict[str, Any]) -> bool:
    """A job is heavy (sbatch-only) when it requests GPUs or exceeds the
    CPU-heavy threshold (cpus * walltime hours)."""
    resources = resources or {}
    try:
        gpus = int(resources.get("gpus", 0) or 0)
    except (TypeError, ValueError):
        gpus = 0
    if gpus > 0:
        return True
    try:
        cpus = int(resources.get("cpus", 1) or 1)
    except (TypeError, ValueError):
        cpus = 1
    hours = parse_time_to_seconds(resources.get("time")) / 3600.0
    if hours <= 0:
        hours = 1.0
    return (cpus * hours) > CPU_HEAVY_THRESHOLD_HOURS


# --------------------------------------------------------------------------- #
# Read-only probe allow-list
# --------------------------------------------------------------------------- #
_READONLY_PREFIXES = ("echo", "test", "conda env list", "sinfo", "squeue", "sacct", "scontrol show")


def is_readonly_probe(argv: Sequence[str]) -> bool:
    joined = " ".join(argv).strip()
    return any(joined.startswith(prefix) for prefix in _READONLY_PREFIXES)


# --------------------------------------------------------------------------- #
# Orchestration (thin; composes pure logic + CommandRunner)
# --------------------------------------------------------------------------- #
def verify_remote(
    runner: CommandRunner, settings: PlanSettings, conda_env_name: str
) -> VerifyResult:
    """Read-only verification: host reachability, remote-path existence, conda
    env membership. All probes route through the injected runner."""
    errors: List[str] = []

    host = runner.run(["echo", "ok"], remote=True)
    host_ok = host.exit_code == 0 and "ok" in host.stdout
    if not host_ok:
        errors.append("host unreachable")

    path_ok = False
    if host_ok:
        probe = runner.run(["test", "-d", settings.remote_project_root], remote=True)
        path_ok = probe.exit_code == 0
        if not path_ok:
            errors.append(f"remote path missing: {settings.remote_project_root}")

    env_ok = False
    env_creation_required = False
    if host_ok and path_ok:
        listing = runner.run(["conda", "env", "list"], remote=True)
        env_ok = _env_in_listing(listing.stdout, conda_env_name)
        if not env_ok:
            env_creation_required = True
            errors.append(f"conda env not found: {conda_env_name}")

    return VerifyResult(
        ok=host_ok and path_ok and env_ok,
        host_ok=host_ok,
        path_ok=path_ok,
        env_ok=env_ok,
        env_creation_required=env_creation_required,
        errors=errors,
    )


def _env_in_listing(listing: str, conda_env_name: str) -> bool:
    """Membership check against `conda env list` output. The env name is the
    first whitespace-delimited token on a non-comment line."""
    if not conda_env_name:
        return False
    for line in (listing or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name = stripped.split()[0]
        if name == conda_env_name:
            return True
    return False


def submit(
    runner: CommandRunner,
    job: Dict[str, Any],
    settings: PlanSettings,
    approval_status: Optional[str],
    *,
    conda_env_name: str,
    date_prefix: str,
    remote_script_path: str,
    verified: bool = True,
) -> SubmitResult:
    """Submit a job to Slurm. Gated on approval; quota pre-checked before any
    sbatch. Heavy jobs always route through sbatch (never the login node)."""
    if not verified:
        return SubmitResult(
            ok=False, decision="verification_required",
            errors=["remote verification did not pass"],
        )

    decision = decide_mutating_action(approval_status, "submit")
    if decision != ActionDecision.PROCEED:
        return SubmitResult(ok=False, decision=decision.value,
                            errors=["approval required for submit"])

    resources = job.get("resources") or {}
    quota = validate_quota(resources, settings.caps)
    if not quota.ok:
        return SubmitResult(ok=False, decision="quota_exceeded",
                            errors=list(quota.violations), quota=quota)

    # Generate the script (pure) and write it remotely, then sbatch it. Both are
    # mutating remote actions and only reach the runner after the approval gate.
    script = generate_sbatch_script(
        job, settings, date_prefix, conda_env_name=conda_env_name,
    )
    # Write via a heredoc on the remote host.
    write_cmd = f"cat > {remote_script_path} << 'KIRO_SBATCH_EOF'\n{script}KIRO_SBATCH_EOF"
    runner.run(["bash", "-lc", write_cmd], remote=True)
    result = runner.run(["sbatch", remote_script_path], remote=True)
    job_id = parse_slurm_job_id(result.stdout)
    if job_id is None:
        return SubmitResult(ok=False, decision="submission_failed",
                            errors=["could not parse Slurm job id from sbatch output"],
                            quota=quota)
    return SubmitResult(ok=True, decision=ActionDecision.PROCEED.value,
                        slurm_job_id=job_id, status=RunStatus.SUBMITTED, quota=quota)


def poll(runner: CommandRunner, slurm_job_id: int) -> Tuple[RunStatus, str, Optional[str]]:
    """Poll a job's state. Active jobs via squeue; completed via sacct.
    Returns (mapped_status, raw_slurm_state, node_list)."""
    active = runner.run(
        ["squeue", "-j", str(slurm_job_id), "-h", "-o", "%T %N"], remote=True
    )
    text = (active.stdout or "").strip()
    if active.exit_code == 0 and text:
        parts = text.split()
        raw_state = parts[0]
        node = parts[1] if len(parts) > 1 else None
        return map_slurm_state(raw_state), raw_state, node

    done = runner.run(
        ["sacct", "-j", str(slurm_job_id), "-n", "-P", "-o", "State,NodeList"],
        remote=True,
    )
    for line in (done.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        fields = line.split("|")
        raw_state = fields[0] if fields else ""
        node = fields[1] if len(fields) > 1 and fields[1] else None
        return map_slurm_state(raw_state), raw_state, node
    return RunStatus.PENDING, "", None


def cancel(
    runner: CommandRunner, slurm_job_id: int, approval_status: Optional[str]
) -> CancelResult:
    """Cancel a job. Gated on approval."""
    decision = decide_mutating_action(approval_status, "cancel")
    if decision != ActionDecision.PROCEED:
        return CancelResult(ok=False, decision=decision.value,
                            errors=["approval required for cancel"])
    result = runner.run(["scancel", str(slurm_job_id)], remote=True)
    if result.exit_code == 0:
        return CancelResult(ok=True, decision=ActionDecision.PROCEED.value,
                            status=RunStatus.CANCELLED)
    return CancelResult(ok=False, decision=ActionDecision.PROCEED.value,
                        errors=[f"scancel failed: {result.stderr}"])


# --------------------------------------------------------------------------- #
# run.yaml linkage
# --------------------------------------------------------------------------- #
_RETRYABLE = {RunStatus.FAILED, RunStatus.TIMED_OUT, RunStatus.CANCELLED, RunStatus.PREEMPTED}


def can_retry(prior_status: Optional[str]) -> bool:
    if prior_status is None:
        return False
    key = str(prior_status).strip().lower()
    return key in {s.value for s in _RETRYABLE}


def write_run_linkage(run_dir: Path, fields: Dict[str, Any]) -> None:
    """Merge Slurm linkage fields into run.yaml. Never writes secret values."""
    import yaml

    run_yaml = run_dir / "run.yaml"
    record: Dict[str, Any] = {}
    if run_yaml.exists():
        loaded = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            record = loaded
    safe_fields = {
        key: value
        for key, value in fields.items()
        if not _CREDENTIAL_KEY_PATTERN.search(str(key))
    }
    record.update(safe_fields)
    run_yaml.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")


def read_run_field(run_dir: Path, key: str) -> Any:
    import yaml

    run_yaml = run_dir / "run.yaml"
    if not run_yaml.exists():
        return None
    loaded = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return loaded.get(key)
    return None


# --------------------------------------------------------------------------- #
# Plan / approval reading (impure: local file reads only)
# --------------------------------------------------------------------------- #
def _read_frontmatter(path: Path) -> Optional[Dict[str, Any]]:
    import yaml

    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    frontmatter = text[text.index("\n") + 1 : end]
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def read_approval_status(plan_path: Path) -> Optional[str]:
    data = _read_frontmatter(plan_path)
    if not data:
        return None
    approval = data.get("approval")
    if not isinstance(approval, dict) or "status" not in approval:
        return None
    status = approval.get("status")
    return None if status is None else str(status)


# --------------------------------------------------------------------------- #
# JSON envelope + helpers
# --------------------------------------------------------------------------- #
def _result(status, message, data=None, errors=None, warnings=None):
    return {
        "status": status,
        "message": message,
        "data": data or {},
        "errors": errors or [],
        "warnings": warnings or [],
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_prefix() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    import yaml

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit an approved job to Slurm over SSH (Phase 6).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    def _common(p):
        p.add_argument("--plan-file", help="Path to project-plan.md")
        p.add_argument("--run-dir", help="Existing run directory")
        p.add_argument("--experiment-plan", help="Path to the experiment plan.md (approval)")
        p.add_argument("--conda-env", default="base", help="Conda environment name")

    for name in ("verify", "submit", "poll", "cancel", "retry", "resume"):
        p = sub.add_parser(name)
        _common(p)

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _build_runner(settings: PlanSettings) -> CommandRunner:
    # The ONLY place SSHCommandRunner is constructed.
    return SSHCommandRunner(settings.ssh_host)


def run_cli(args: argparse.Namespace, runner_factory=_build_runner) -> Dict[str, Any]:
    """Dispatch a CLI command. runner_factory is injectable for tests."""
    if not args.command:
        return _result("error", "No command given", errors=["command required"])

    plan_path = Path(args.plan_file).resolve() if args.plan_file else Path("project-plan.md").resolve()
    frontmatter = _read_frontmatter(plan_path)
    if not frontmatter:
        return _result("error", f"project-plan.md not found or unparseable: {plan_path}",
                       errors=["Missing/invalid project-plan.md"])
    settings = load_plan_settings(frontmatter)
    conda_env = args.conda_env

    runner = runner_factory(settings)

    if args.command == "verify":
        v = verify_remote(runner, settings, conda_env)
        status = "success" if v.ok else "error"
        return _result(status, "verification complete",
                       data={"host_ok": v.host_ok, "path_ok": v.path_ok,
                             "env_ok": v.env_ok,
                             "env_creation_required": v.env_creation_required},
                       errors=v.errors)

    # Commands below need the run directory and job.
    if not args.run_dir:
        return _result("error", "--run-dir is required", errors=["Missing --run-dir"])
    run_dir = Path(args.run_dir).resolve()
    exp_plan = Path(args.experiment_plan).resolve() if args.experiment_plan else (run_dir.parent.parent / "plan.md")
    approval_status = read_approval_status(exp_plan)

    if args.command in ("submit", "retry"):
        resolved = run_dir / "resolved-job.yaml"
        if not resolved.exists():
            return _result("error", "resolved-job.yaml not found",
                           errors=["Run initialize_run.py first"])
        job = _load_yaml_file(resolved)
        if args.command == "retry":
            prior = read_run_field(run_dir, "status")
            if not can_retry(prior):
                return _result("error", f"retry not allowed from status: {prior}",
                               errors=["prior run is not in a retryable state"])
        v = verify_remote(runner, settings, conda_env)
        result = submit(
            runner, job, settings, approval_status,
            conda_env_name=conda_env, date_prefix=_date_prefix(),
            remote_script_path=f"{settings.remote_project_root}/.kiro_job.sbatch",
            verified=v.ok,
        )
        if result.ok:
            write_run_linkage(run_dir, {
                "slurm_job_id": result.slurm_job_id,
                "status": result.status.value,
                "submitted_at": _now_iso(),
            })
            return _result("success", f"submitted job {result.slurm_job_id}",
                           data={"slurm_job_id": result.slurm_job_id,
                                 "status": result.status.value})
        return _result("error", f"submit declined: {result.decision}",
                       data={"decision": result.decision}, errors=result.errors)

    if args.command in ("poll", "resume"):
        job_id = read_run_field(run_dir, "slurm_job_id")
        if job_id is None:
            msg = ("resume not possible: no recorded slurm_job_id"
                   if args.command == "resume" else "no recorded slurm_job_id to poll")
            return _result("error", msg, errors=["Missing slurm_job_id"])
        status, raw_state, node = poll(runner, int(job_id))
        write_run_linkage(run_dir, {
            "slurm_job_id": int(job_id), "slurm_state": raw_state,
            "status": status.value, "node_list": node, "polled_at": _now_iso(),
        })
        return _result("success", f"polled job {job_id}: {status.value}",
                       data={"slurm_job_id": int(job_id), "status": status.value,
                             "slurm_state": raw_state, "node_list": node})

    if args.command == "cancel":
        job_id = read_run_field(run_dir, "slurm_job_id")
        if job_id is None:
            return _result("error", "no recorded slurm_job_id to cancel",
                           errors=["Missing slurm_job_id"])
        result = cancel(runner, int(job_id), approval_status)
        if result.ok:
            write_run_linkage(run_dir, {"status": result.status.value,
                                         "cancelled_at": _now_iso()})
            return _result("success", f"cancelled job {job_id}",
                           data={"status": result.status.value})
        return _result("error", f"cancel declined: {result.decision}",
                       data={"decision": result.decision}, errors=result.errors)

    return _result("error", f"unknown command: {args.command}", errors=["unknown command"])


def main() -> None:
    try:
        import yaml  # noqa: F401
    except ImportError:
        print(json.dumps(_result("error", "PyYAML is required but not installed.",
                                   errors=["Missing dependency: PyYAML"]), indent=2))
        sys.exit(2)

    args = parse_arguments()
    try:
        result = run_cli(args)
    except UnsupportedConfigStyle as exc:
        result = _result("error", f"Unsupported config_style: {exc}",
                         errors=[f"Unsupported config_style: {exc}"])
    except Exception as exc:  # noqa: BLE001 - structured error, never crash
        result = _result("error", f"Unexpected error: {exc}",
                         errors=[f"Runtime error: {exc}"])

    print(json.dumps(result, indent=2))
    if result["status"] == "success":
        sys.exit(0)
    decision = result.get("data", {}).get("decision")
    declined = {"approval_required", "quota_exceeded", "verification_required",
                "submission_failed"}
    if decision in declined or any(
        kw in " ".join(result.get("errors", [])).lower()
        for kw in ("approval", "quota", "verification", "resume not possible",
                   "not in a retryable", "slurm_job_id")
    ):
        sys.exit(1)
    sys.exit(2)


if __name__ == "__main__":
    main()
