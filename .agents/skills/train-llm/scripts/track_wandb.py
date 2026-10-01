#!/usr/bin/env python3
"""
Track a run with Weights & Biases and record the linkage (Phase 7).

This helper adds the W&B experiment-tracking layer on top of the Phase 5 local
executor (run_local.py) and the Phase 6 Slurm submitter (submit_slurm.py). It
creates/resumes W&B runs, assigns groups and tags, records the resolved config
and Git SHA, manages the local W&B directory, compares runs within a group,
checks sync status, and links the W&B run identity back into run.yaml.

Design discipline (Phase 7):
  - PURE LOGIC functions take plain data and return plain data. They perform no
    W&B API call, no network, and no filesystem mutation.
  - IMPURE I/O passes exclusively through an injected WandbClient. Production
    uses RealWandbClient (constructed only in main(), wrapping the wandb SDK);
    tests inject a FakeWandbClient. No real W&B API or network ever occurs in
    tests.
  - Mutating W&B actions (create, resume, config update, finish, sync) require
    approval.status == approved in the experiment plan.md. Read-only/local-only
    actions (reading run.yaml, parsing a W&B URL from logs, inspecting the local
    wandb dir) are non-mutating.
  - A W&B failure is recorded distinctly from a training failure: run.yaml
    carries a separate wandb_status field so a failed sync never flips the
    training status.
  - No secrets (WANDB_API_KEY etc.) are ever written to run.yaml or artifacts.

Output (JSON envelope): {status, message, data, errors, warnings}
Exit Codes:
  0 - Completed or recorded
  1 - Declined (approval / placeholder entity in online mode / missing prereq)
  2 - Runtime error (filesystem/parse)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

__version__ = "0.1.0"

PLACEHOLDER_ENTITY = "TODO-set-before-phase-7"
VALID_MODES = ("online", "offline", "disabled")
UNKNOWN_SHA = "unknown"
MUTATING_KINDS = ("create", "resume", "config", "finish", "sync")

_CREDENTIAL_KEY_PATTERN = re.compile(
    r"(TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.IGNORECASE
)
_WANDB_URL_PATTERN = re.compile(r"https?://(?:[\w.-]*\.)?wandb\.ai/[^\s'\"<>]+")
_RUN_ID_PATTERN = re.compile(r"/runs/([^/?#\s]+)")
_EXCLUDED_SUFFIX = (".out", ".err")
_EXCLUDED_DIRS = ("checkpoints", "wandb")


# --------------------------------------------------------------------------- #
# Status + decision models
# --------------------------------------------------------------------------- #
class WandbStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    SYNCED = "synced"
    SYNC_FAILED = "sync_failed"
    OFFLINE = "offline"


class EffectiveMode(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DISABLED = "disabled"


class ActionDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WandbSettings:
    entity: str
    project: str
    mode: str
    keep_local_data: bool = False


@dataclass(frozen=True)
class ModeDecision:
    effective: EffectiveMode
    config_error: bool = False
    placeholder_online_declined: bool = False


@dataclass(frozen=True)
class CreatedRun:
    run_id: str
    url: str


@dataclass(frozen=True)
class RunMetrics:
    run_id: str
    summary: Mapping[str, float]


@dataclass(frozen=True)
class RunResult:
    ok: bool
    decision: str
    run_id: Optional[str] = None
    url: Optional[str] = None
    wandb_status: Optional[WandbStatus] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResumeResult:
    ok: bool
    decision: str
    run_id: Optional[str] = None
    url: Optional[str] = None
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConfigResult:
    ok: bool
    decision: str
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class GroupResult:
    ok: bool
    group: str
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncResult:
    ok: bool
    wandb_status: WandbStatus
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompareResult:
    ok: bool
    group: str
    runs: List[Dict[str, Any]] = field(default_factory=list)
    empty: bool = False


# --------------------------------------------------------------------------- #
# WandbClient — the single injected I/O boundary
# --------------------------------------------------------------------------- #
class WandbClient(Protocol):
    def create_run(self, *, entity: str, project: str, group: str,
                   tags: Sequence[str], config: Mapping[str, object],
                   mode: str, dir: str) -> CreatedRun: ...

    def resume_run(self, *, run_id: str, project: str, entity: str,
                   mode: str, dir: str) -> CreatedRun: ...

    def update_config(self, *, run_id: str, config: Mapping[str, object]) -> None: ...

    def finish_run(self, *, run_id: str) -> None: ...

    def sync_state(self, *, run_id: str, dir: str) -> str: ...

    def fetch_group_metrics(self, *, entity: str, project: str,
                            group: str) -> List[RunMetrics]: ...


class RealWandbClient:
    """Production client wrapping the wandb SDK. Constructed ONLY in main()."""

    def __init__(self, entity: str, project: str) -> None:
        self._entity = entity
        self._project = project
        self._run = None

    def create_run(self, *, entity, project, group, tags, config, mode, dir):
        import wandb  # imported lazily; never in tests

        self._run = wandb.init(
            entity=entity, project=project, group=group, tags=list(tags),
            config=dict(config), mode=mode, dir=dir,
        )
        return CreatedRun(run_id=self._run.id, url=self._run.get_url() or "")

    def resume_run(self, *, run_id, project, entity, mode, dir):
        import wandb

        self._run = wandb.init(
            id=run_id, entity=entity, project=project, resume="must",
            mode=mode, dir=dir,
        )
        return CreatedRun(run_id=self._run.id, url=self._run.get_url() or "")

    def update_config(self, *, run_id, config):
        if self._run is not None:
            self._run.config.update(dict(config), allow_val_change=True)

    def finish_run(self, *, run_id):
        if self._run is not None:
            self._run.finish()

    def sync_state(self, *, run_id, dir):
        if self._run is not None:
            return str(getattr(self._run, "state", "running"))
        return "running"

    def fetch_group_metrics(self, *, entity, project, group):
        import wandb

        api = wandb.Api()
        runs = api.runs(f"{entity}/{project}", filters={"group": group})
        return [RunMetrics(run_id=r.id, summary=dict(r.summary)) for r in runs]


class FakeWandbClient:
    """Test client. Returns pre-seeded results keyed by operation and records
    every call. Raises on any unscripted operation so tests never leak to real
    W&B or network I/O.

    scripted: dict mapping operation name to a value or callable.
    """

    def __init__(self, scripted: Optional[Mapping[str, Any]] = None) -> None:
        self._scripted: Dict[str, Any] = dict(scripted or {})
        self.calls: List[Dict[str, Any]] = []

    def _result(self, op: str, **kwargs):
        self.calls.append({"op": op, **kwargs})
        if op not in self._scripted:
            raise AssertionError(f"FakeWandbClient received unscripted op: {op!r}")
        value = self._scripted[op]
        return value(**kwargs) if callable(value) else value

    def create_run(self, **kwargs) -> CreatedRun:
        return self._result("create_run", **kwargs)

    def resume_run(self, **kwargs) -> CreatedRun:
        return self._result("resume_run", **kwargs)

    def update_config(self, **kwargs) -> None:
        self._result("update_config", **kwargs)

    def finish_run(self, **kwargs) -> None:
        self._result("finish_run", **kwargs)

    def sync_state(self, **kwargs) -> str:
        return self._result("sync_state", **kwargs)

    def fetch_group_metrics(self, **kwargs) -> List[RunMetrics]:
        return self._result("fetch_group_metrics", **kwargs)


# --------------------------------------------------------------------------- #
# Pure logic: settings + mode resolution
# --------------------------------------------------------------------------- #
def load_wandb_settings(frontmatter: Dict[str, Any]) -> WandbSettings:
    w = (frontmatter or {}).get("wandb", {}) or {}
    return WandbSettings(
        entity=str(w.get("entity", "")),
        project=str(w.get("project", "")),
        mode=str(w.get("mode", "")),
        keep_local_data=bool(w.get("keep_local_data", False)),
    )


def is_placeholder_entity(entity: str) -> bool:
    return (entity or "").strip() == PLACEHOLDER_ENTITY


def resolve_mode(settings: WandbSettings, entity: str) -> ModeDecision:
    if settings.mode not in VALID_MODES:
        return ModeDecision(EffectiveMode.DISABLED, config_error=True)
    if settings.mode == "disabled":
        return ModeDecision(EffectiveMode.DISABLED)
    if is_placeholder_entity(entity):
        if settings.mode == "online":
            return ModeDecision(EffectiveMode.OFFLINE,
                                placeholder_online_declined=True)
        return ModeDecision(EffectiveMode.OFFLINE)
    return ModeDecision(EffectiveMode(settings.mode))


# --------------------------------------------------------------------------- #
# Pure logic: group + tags
# --------------------------------------------------------------------------- #
def resolve_group(experiment_id: str, job: Dict[str, Any]) -> str:
    declared = (job.get("wandb") or {}).get("group") if job else None
    return str(declared) if declared else str(experiment_id)


def resolve_tags(job: Dict[str, Any]) -> List[str]:
    job = job or {}
    tags: List[str] = []
    for t in (job.get("wandb") or {}).get("tags", []) or []:
        tags.append(str(t))
    for key in ("method", "lora_rank", "model"):
        if key in job:
            tags.append(f"{key}:{job[key]}")
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


# --------------------------------------------------------------------------- #
# Pure logic: config assembly + redaction
# --------------------------------------------------------------------------- #
def _is_credential_key(key: str) -> bool:
    return bool(_CREDENTIAL_KEY_PATTERN.search(key or ""))


def redact_config(config: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (config or {}).items():
        if _is_credential_key(str(k)):
            continue
        if isinstance(v, dict):
            out[k] = redact_config(v)
        else:
            out[k] = v
    return out


def build_run_config(resolved_job: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(resolved_job or {})
    merged["_env_names"] = [k for k in (env or {}) if not _is_credential_key(str(k))]
    return redact_config(merged)


def redact_secrets(text: str, env: Dict[str, Any]) -> str:
    out = text or ""
    for k, v in (env or {}).items():
        if _is_credential_key(str(k)) and v:
            out = out.replace(str(v), f"<{k}>")
    return out


# --------------------------------------------------------------------------- #
# Pure logic: local dir + commit filter
# --------------------------------------------------------------------------- #
def local_wandb_dir(experiment_id: str, run_id: str) -> str:
    return f"experiments/{experiment_id}/runs/{run_id}/wandb"


def filter_commit_candidates(paths: List[str]) -> List[str]:
    result: List[str] = []
    for p in paths or []:
        if p.endswith(_EXCLUDED_SUFFIX):
            continue
        if any(d in p.split("/") for d in _EXCLUDED_DIRS):
            continue
        result.append(p)
    return result


# --------------------------------------------------------------------------- #
# Pure logic: URL parsing
# --------------------------------------------------------------------------- #
def parse_wandb_url(log_text: str) -> Optional[str]:
    m = _WANDB_URL_PATTERN.search(log_text or "")
    return m.group(0) if m else None


def extract_run_id_from_url(url: str) -> Optional[str]:
    m = _RUN_ID_PATTERN.search(url or "")
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
# Pure logic: sync-state mapping
# --------------------------------------------------------------------------- #
_SYNC_MAP = {
    "synced": WandbStatus.SYNCED,
    "finished": WandbStatus.SYNCED,
    "uploaded": WandbStatus.SYNCED,
    "failed": WandbStatus.SYNC_FAILED,
    "error": WandbStatus.SYNC_FAILED,
    "running": WandbStatus.RUNNING,
    "offline": WandbStatus.OFFLINE,
}


def map_sync_state(raw_state: str, mode: EffectiveMode) -> WandbStatus:
    if mode == EffectiveMode.OFFLINE:
        return WandbStatus.OFFLINE
    if mode == EffectiveMode.DISABLED:
        return WandbStatus.NOT_STARTED
    token = ""
    if raw_state and str(raw_state).strip():
        token = str(raw_state).strip().split()[0].lower()
    return _SYNC_MAP.get(token, WandbStatus.SYNC_FAILED)


# --------------------------------------------------------------------------- #
# Pure logic: approval gating + git sha
# --------------------------------------------------------------------------- #
def decide_mutating_action(approval_status: Optional[str], kind: str) -> ActionDecision:
    if approval_status and str(approval_status).strip().lower() == "approved":
        return ActionDecision.PROCEED
    return ActionDecision.DECLINE_APPROVAL


@dataclass(frozen=True)
class GitResult:
    exit_code: int
    stdout: str


def record_git_sha(result: Optional[GitResult]) -> "tuple[str, List[str]]":
    if result and result.exit_code == 0 and result.stdout.strip():
        return result.stdout.strip(), []
    return UNKNOWN_SHA, ["git_sha_unknown: could not determine current commit"]


# --------------------------------------------------------------------------- #
# run.yaml linkage (impure: local file only)
# --------------------------------------------------------------------------- #
def write_wandb_linkage(run_dir: Path, fields: Dict[str, Any]) -> None:
    """Merge W&B linkage fields into run.yaml. Never writes secret values and
    never changes the training `status` unless explicitly provided (callers do
    not pass `status`)."""
    import yaml

    run_yaml = run_dir / "run.yaml"
    record: Dict[str, Any] = {}
    if run_yaml.exists():
        loaded = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            record = loaded
    safe = {k: v for k, v in fields.items() if not _is_credential_key(str(k))}
    record.update(safe)
    run_yaml.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")


def read_run_field(run_dir: Path, key: str) -> Any:
    import yaml

    run_yaml = run_dir / "run.yaml"
    if not run_yaml.exists():
        return None
    loaded = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))
    return loaded.get(key) if isinstance(loaded, dict) else None


# --------------------------------------------------------------------------- #
# Orchestration (thin; composes pure logic + WandbClient)
# --------------------------------------------------------------------------- #
def create_run(
    client: WandbClient,
    run_dir: Path,
    settings: WandbSettings,
    job: Dict[str, Any],
    approval_status: Optional[str],
    *,
    experiment_id: str,
    env: Optional[Dict[str, Any]] = None,
    mode_decision: Optional[ModeDecision] = None,
) -> RunResult:
    env = env or {}
    md = mode_decision or resolve_mode(settings, settings.entity)
    if md.placeholder_online_declined:
        return RunResult(ok=False, decision="placeholder_entity",
                         errors=["wandb.entity is a placeholder; set it before online runs"])
    decision = decide_mutating_action(approval_status, "create")
    if decision != ActionDecision.PROCEED:
        return RunResult(ok=False, decision=decision.value,
                         errors=["approval required for W&B run creation"])

    group = resolve_group(experiment_id, job)
    tags = resolve_tags(job)
    config = build_run_config(job, env)
    wdir = local_wandb_dir(experiment_id, run_dir.name)
    Path(wdir)  # path is pure; actual mkdir below is confined to run_dir
    (run_dir / "wandb").mkdir(parents=True, exist_ok=True)
    created = client.create_run(
        entity=settings.entity, project=settings.project, group=group,
        tags=tags, config=config, mode=md.effective.value, dir=str(run_dir / "wandb"),
    )
    return RunResult(ok=True, decision=ActionDecision.PROCEED.value,
                     run_id=created.run_id, url=created.url,
                     wandb_status=WandbStatus.RUNNING)


def resume_run(
    client: WandbClient,
    run_dir: Path,
    settings: WandbSettings,
    approval_status: Optional[str],
    *,
    experiment_id: str,
    mode_decision: Optional[ModeDecision] = None,
) -> ResumeResult:
    run_id = read_run_field(run_dir, "wandb_run_id")
    if not run_id:
        return ResumeResult(ok=False, decision="resume_not_possible",
                            errors=["no recorded wandb_run_id to resume"])
    decision = decide_mutating_action(approval_status, "resume")
    if decision != ActionDecision.PROCEED:
        return ResumeResult(ok=False, decision=decision.value,
                            errors=["approval required for W&B resume"])
    md = mode_decision or resolve_mode(settings, settings.entity)
    url = read_run_field(run_dir, "wandb_url")
    client.resume_run(run_id=str(run_id), project=settings.project,
                      entity=settings.entity, mode=md.effective.value,
                      dir=str(run_dir / "wandb"))
    return ResumeResult(ok=True, decision=ActionDecision.PROCEED.value,
                        run_id=str(run_id), url=url)


def record_config(
    client: WandbClient, run_id: str, job: Dict[str, Any],
    env: Dict[str, Any], approval_status: Optional[str],
) -> ConfigResult:
    decision = decide_mutating_action(approval_status, "config")
    if decision != ActionDecision.PROCEED:
        return ConfigResult(ok=False, decision=decision.value,
                            errors=["approval required for W&B config update"])
    client.update_config(run_id=run_id, config=build_run_config(job, env))
    return ConfigResult(ok=True, decision=ActionDecision.PROCEED.value)


def assign_group_tags(experiment_id: str, job: Dict[str, Any]) -> GroupResult:
    return GroupResult(ok=True, group=resolve_group(experiment_id, job),
                       tags=resolve_tags(job))


def check_sync(
    client: WandbClient, run_dir: Path, settings: WandbSettings,
    *, mode_decision: Optional[ModeDecision] = None,
) -> SyncResult:
    md = mode_decision or resolve_mode(settings, settings.entity)
    if md.effective in (EffectiveMode.OFFLINE, EffectiveMode.DISABLED):
        status = map_sync_state("", md.effective)
        return SyncResult(ok=True, wandb_status=status)
    run_id = read_run_field(run_dir, "wandb_run_id")
    raw = client.sync_state(run_id=str(run_id), dir=str(run_dir / "wandb"))
    status = map_sync_state(raw, md.effective)
    return SyncResult(ok=status != WandbStatus.SYNC_FAILED, wandb_status=status)


def compare_runs(client: WandbClient, settings: WandbSettings, group: str) -> CompareResult:
    metrics = client.fetch_group_metrics(
        entity=settings.entity, project=settings.project, group=group)
    if not metrics:
        return CompareResult(ok=True, group=group, runs=[], empty=True)
    runs = [{"wandb_run_id": m.run_id, "metrics": dict(m.summary)} for m in metrics]
    return CompareResult(ok=True, group=group, runs=runs)


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


def current_git_sha(workspace: Path) -> GitResult:
    try:
        completed = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "HEAD"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
            check=False, text=True,
        )
        return GitResult(completed.returncode, completed.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return GitResult(1, "")


# --------------------------------------------------------------------------- #
# JSON envelope + CLI
# --------------------------------------------------------------------------- #
def _result(status, message, data=None, errors=None, warnings=None):
    return {
        "status": status,
        "message": message,
        "data": data or {},
        "errors": errors or [],
        "warnings": warnings or [],
    }


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    import yaml

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track a run with Weights & Biases (Phase 7).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    def _common(p):
        p.add_argument("--plan-file", help="Path to project-plan.md")
        p.add_argument("--run-dir", help="Existing run directory")
        p.add_argument("--experiment-plan", help="Path to the experiment plan.md (approval)")
        p.add_argument("--experiment-id", help="Experiment id for group/local-dir")
        p.add_argument("--workspace", help="Workspace root (for git sha)")
        p.add_argument("--group", help="W&B group (compare)")

    for name in ("create", "resume", "config", "sync", "compare"):
        _common(sub.add_parser(name))

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _build_client(settings: WandbSettings) -> WandbClient:
    # The ONLY place RealWandbClient is constructed.
    return RealWandbClient(settings.entity, settings.project)


def run_cli(args: argparse.Namespace, client_factory=_build_client) -> Dict[str, Any]:
    if not args.command:
        return _result("error", "No command given", errors=["command required"])

    plan_path = Path(args.plan_file).resolve() if args.plan_file else Path("project-plan.md").resolve()
    frontmatter = _read_frontmatter(plan_path)
    if frontmatter is None:
        return _result("error", f"project-plan.md not found or unparseable: {plan_path}",
                       errors=["Missing/invalid project-plan.md"])
    settings = load_wandb_settings(frontmatter)
    md = resolve_mode(settings, settings.entity)
    if md.config_error:
        return _result("error", f"wandb.mode invalid: {settings.mode!r}",
                       data={"decision": "config_error"},
                       errors=["wandb.mode must be online, offline, or disabled"])

    client = client_factory(settings)
    warnings: List[str] = []

    run_dir = Path(args.run_dir).resolve() if args.run_dir else None
    experiment_id = args.experiment_id or (run_dir.parent.parent.name if run_dir else "")
    exp_plan = (Path(args.experiment_plan).resolve() if args.experiment_plan
                else (run_dir.parent.parent / "plan.md" if run_dir else None))
    approval_status = read_approval_status(exp_plan) if exp_plan else None

    if args.command == "compare":
        group = args.group or experiment_id
        result = compare_runs(client, settings, group)
        return _result("success", f"compared group {group}",
                       data={"group": result.group, "runs": result.runs,
                             "empty": result.empty})

    if run_dir is None:
        return _result("error", "--run-dir is required", errors=["Missing --run-dir"])

    if args.command == "create":
        resolved = run_dir / "resolved-job.yaml"
        job = _load_yaml_file(resolved) if resolved.exists() else {}
        workspace = Path(args.workspace).resolve() if args.workspace else run_dir
        sha, sha_warn = record_git_sha(current_git_sha(workspace))
        warnings.extend(sha_warn)
        result = create_run(client, run_dir, settings, job, approval_status,
                            experiment_id=experiment_id, mode_decision=md)
        if not result.ok:
            return _result("error", f"create declined: {result.decision}",
                           data={"decision": result.decision}, errors=result.errors)
        gr = assign_group_tags(experiment_id, job)
        write_wandb_linkage(run_dir, {
            "wandb_run_id": result.run_id, "wandb_url": result.url,
            "wandb_group": gr.group, "wandb_tags": gr.tags,
            "wandb_status": result.wandb_status.value, "wandb_mode": md.effective.value,
            "git_sha": sha,
        })
        return _result("success", f"created W&B run {result.run_id}",
                       data={"wandb_run_id": result.run_id, "wandb_url": result.url,
                             "wandb_group": gr.group, "wandb_status": result.wandb_status.value},
                       warnings=warnings)

    if args.command == "resume":
        result = resume_run(client, run_dir, settings, approval_status,
                            experiment_id=experiment_id, mode_decision=md)
        if not result.ok:
            return _result("error", f"resume declined: {result.decision}",
                           data={"decision": result.decision}, errors=result.errors)
        return _result("success", f"resumed W&B run {result.run_id}",
                       data={"wandb_run_id": result.run_id})

    if args.command == "config":
        resolved = run_dir / "resolved-job.yaml"
        job = _load_yaml_file(resolved) if resolved.exists() else {}
        run_id = read_run_field(run_dir, "wandb_run_id")
        if not run_id:
            return _result("error", "no recorded wandb_run_id for config update",
                           errors=["Missing wandb_run_id"])
        result = record_config(client, str(run_id), job, {}, approval_status)
        if not result.ok:
            return _result("error", f"config declined: {result.decision}",
                           data={"decision": result.decision}, errors=result.errors)
        return _result("success", f"recorded config for {run_id}", data={"wandb_run_id": run_id})

    if args.command == "sync":
        result = check_sync(client, run_dir, settings, mode_decision=md)
        write_wandb_linkage(run_dir, {"wandb_status": result.wandb_status.value})
        return _result("success", f"sync status: {result.wandb_status.value}",
                       data={"wandb_status": result.wandb_status.value})

    return _result("error", f"unknown command: {args.command}", errors=["unknown command"])


def main() -> None:
    try:
        import yaml  # noqa: F401
    except ImportError:
        print(json.dumps(_result("error", "PyYAML is required but not installed.",
                                   errors=["Missing dependency: PyYAML"]), indent=2))
        sys.exit(2)

    args = parse_args()
    try:
        result = run_cli(args)
    except Exception as exc:  # noqa: BLE001 - structured error, never crash
        result = _result("error", f"Unexpected error: {exc}",
                         errors=[f"Runtime error: {exc}"])

    print(json.dumps(result, indent=2))
    if result["status"] == "success":
        sys.exit(0)
    decision = result.get("data", {}).get("decision")
    declined = {"approval_required", "placeholder_entity", "resume_not_possible",
                "config_error"}
    if decision in declined or any(
        kw in " ".join(result.get("errors", [])).lower()
        for kw in ("approval", "placeholder", "resume", "missing wandb_run_id",
                   "wandb.mode")
    ):
        sys.exit(1)
    sys.exit(2)


if __name__ == "__main__":
    main()
