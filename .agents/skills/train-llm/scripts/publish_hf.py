#!/usr/bin/env python3
"""
Publish a checkpoint to the Hugging Face Hub and record the linkage (Phase 8).

This helper adds the Hugging Face Hub publication layer on top of the Phase 5
local executor (run_local.py), the Phase 6 Slurm submitter (submit_slurm.py),
and the Phase 7 W&B tracker (track_wandb.py). It verifies the Hub repository,
decides push eligibility, uploads checkpoints, records revisions, drafts a model
card, verifies the upload by revision, applies the private/public policy, and
links the publication back into run.yaml.

Design discipline (Phase 8):
  - PURE LOGIC functions take plain data and return plain data. They perform no
    Hub API call, no network, and no filesystem mutation.
  - IMPURE I/O passes exclusively through an injected HfClient. Production uses
    RealHfClient (constructed only in main(), wrapping huggingface_hub lazily);
    tests inject a FakeHfClient. No real Hub API or network ever occurs in tests.
  - Mutating Hub actions (create/ensure repo, set visibility, upload, revision)
    require approval.status == approved in the experiment plan.md. Read-only/
    local-only actions (checking a local checkpoint path, drafting a model card,
    reading run.yaml, locating content by revision) are non-mutating.
  - A Hub failure is recorded distinctly from a training failure: run.yaml
    carries a separate hf_status field so a failed upload never flips the
    training status, while still signaling the experiment must not be marked
    complete.
  - No secrets (HF_TOKEN / HUGGINGFACEHUB_API_TOKEN etc.) are ever written.
  - Checkpoints are uploaded to the Hub, never added to Git.

Output (JSON envelope): {status, message, data, errors, warnings}
Exit Codes:
  0 - Completed, recorded, or verified
  1 - Declined (approval / placeholder namespace / policy skip / not verified / missing prereq)
  2 - Runtime error (filesystem/parse)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

__version__ = "0.1.0"

PLACEHOLDER_NAMESPACE = "TODO-set-before-phase-8"
VALID_POLICIES = ("never", "final_only", "milestone", "final_and_milestone", "every_save")
MUTATING_KINDS = ("create_repo", "set_visibility", "upload", "revision")

_CREDENTIAL_KEY_PATTERN = re.compile(
    r"(TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.IGNORECASE
)
_EXCLUDED_SUFFIX = (".out", ".err")
_EXCLUDED_DIRS = ("checkpoints", "wandb")


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class CheckpointKind(str, Enum):
    FINAL = "final"
    MILESTONE = "milestone"
    INTERMEDIATE = "intermediate"


class Visibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class VisDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"
    DECLINE_SILENT_PUBLIC = "silent_public_blocked"


class HfStatus(str, Enum):
    NOT_STARTED = "not_started"
    SKIPPED_BY_POLICY = "skipped_by_policy"
    UPLOADED = "uploaded"
    VERIFIED = "verified"
    UPLOAD_FAILED = "upload_failed"


class ActionDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HfSettings:
    namespace: str
    private: bool
    push_policy: str


@dataclass(frozen=True)
class PushDecision:
    eligible: bool
    config_error: bool = False


@dataclass(frozen=True)
class UploadOutcome:
    revision: str
    repo_id: str


@dataclass(frozen=True)
class RepoInfo:
    exists: bool
    private: bool = True


@dataclass(frozen=True)
class CheckpointResult:
    ok: bool
    path: Optional[str] = None
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepoResult:
    ok: bool
    decision: str
    repo_id: str
    created: bool = False
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class UploadResult:
    ok: bool
    decision: str
    hf_status: HfStatus
    revision: Optional[str] = None
    repo_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    hf_status: HfStatus
    experiment_incomplete: bool = False
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CardResult:
    ok: bool
    path: str


# --------------------------------------------------------------------------- #
# HfClient — the single injected I/O boundary
# --------------------------------------------------------------------------- #
class HfClient(Protocol):
    def repo_exists(self, *, repo_id: str) -> RepoInfo: ...

    def create_repo(self, *, repo_id: str, private: bool) -> RepoInfo: ...

    def set_visibility(self, *, repo_id: str, private: bool) -> RepoInfo: ...

    def upload_checkpoint(self, *, repo_id: str, local_path: str) -> UploadOutcome: ...

    def file_exists_at_revision(self, *, repo_id: str, revision: str) -> bool: ...


class RealHfClient:
    """Production client wrapping huggingface_hub. Constructed ONLY in main()."""

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token
        self._api = None

    def _hf(self):
        if self._api is None:
            from huggingface_hub import HfApi  # lazy; never in tests

            self._api = HfApi(token=self._token)
        return self._api

    def repo_exists(self, *, repo_id):
        from huggingface_hub.utils import RepositoryNotFoundError

        try:
            info = self._hf().repo_info(repo_id=repo_id, repo_type="model")
            return RepoInfo(exists=True, private=bool(getattr(info, "private", True)))
        except RepositoryNotFoundError:
            return RepoInfo(exists=False)

    def create_repo(self, *, repo_id, private):
        self._hf().create_repo(repo_id=repo_id, private=private, exist_ok=True)
        return RepoInfo(exists=True, private=private)

    def set_visibility(self, *, repo_id, private):
        self._hf().update_repo_settings(repo_id=repo_id, private=private)
        return RepoInfo(exists=True, private=private)

    def upload_checkpoint(self, *, repo_id, local_path):
        commit = self._hf().upload_folder(repo_id=repo_id, folder_path=local_path)
        revision = getattr(commit, "oid", "") or ""
        return UploadOutcome(revision=revision, repo_id=repo_id)

    def file_exists_at_revision(self, *, repo_id, revision):
        try:
            files = self._hf().list_repo_files(repo_id=repo_id, revision=revision)
            return len(files) > 0
        except Exception:  # noqa: BLE001
            return False


class FakeHfClient:
    """Test client. Returns pre-seeded results keyed by operation and records
    every call. Raises on any unscripted operation so tests never leak to real
    Hub or network I/O.
    """

    def __init__(self, scripted: Optional[Mapping[str, Any]] = None) -> None:
        self._scripted: Dict[str, Any] = dict(scripted or {})
        self.calls: List[Dict[str, Any]] = []

    def _result(self, op: str, **kwargs):
        self.calls.append({"op": op, **kwargs})
        if op not in self._scripted:
            raise AssertionError(f"FakeHfClient received unscripted op: {op!r}")
        value = self._scripted[op]
        return value(**kwargs) if callable(value) else value

    def repo_exists(self, **kwargs) -> RepoInfo:
        return self._result("repo_exists", **kwargs)

    def create_repo(self, **kwargs) -> RepoInfo:
        return self._result("create_repo", **kwargs)

    def set_visibility(self, **kwargs) -> RepoInfo:
        return self._result("set_visibility", **kwargs)

    def upload_checkpoint(self, **kwargs) -> UploadOutcome:
        return self._result("upload_checkpoint", **kwargs)

    def file_exists_at_revision(self, **kwargs) -> bool:
        return self._result("file_exists_at_revision", **kwargs)


# --------------------------------------------------------------------------- #
# Pure logic: settings
# --------------------------------------------------------------------------- #
def load_hf_settings(frontmatter: Dict[str, Any]) -> HfSettings:
    hf = (frontmatter or {}).get("huggingface", {}) or {}
    private = hf.get("private", True)
    return HfSettings(
        namespace=str(hf.get("namespace", "")),
        private=bool(private) if private is not None else True,
        push_policy=str(hf.get("push_policy", "")),
    )


def is_placeholder_namespace(namespace: str) -> bool:
    return (namespace or "").strip() == PLACEHOLDER_NAMESPACE


# --------------------------------------------------------------------------- #
# Pure logic: push eligibility
# --------------------------------------------------------------------------- #
_ELIGIBLE_KINDS = {
    "never": set(),
    "final_only": {CheckpointKind.FINAL},
    "final_and_milestone": {CheckpointKind.FINAL, CheckpointKind.MILESTONE},
    "milestone": {CheckpointKind.MILESTONE, CheckpointKind.FINAL},
    "every_save": {CheckpointKind.FINAL, CheckpointKind.MILESTONE, CheckpointKind.INTERMEDIATE},
}


def decide_push(policy: str, checkpoint_kind: CheckpointKind) -> PushDecision:
    if policy not in VALID_POLICIES:
        return PushDecision(eligible=False, config_error=True)
    return PushDecision(eligible=checkpoint_kind in _ELIGIBLE_KINDS[policy])


# --------------------------------------------------------------------------- #
# Pure logic: repo id / url
# --------------------------------------------------------------------------- #
def build_repo_id(namespace: str, repo_name: str) -> str:
    return f"{namespace}/{repo_name}"


def build_hf_url(repo_id: str, revision: Optional[str] = None) -> str:
    base = f"https://huggingface.co/{repo_id}"
    return f"{base}/tree/{revision}" if revision else base


# --------------------------------------------------------------------------- #
# Pure logic: visibility
# --------------------------------------------------------------------------- #
def resolve_visibility(private: bool) -> Visibility:
    return Visibility.PRIVATE if private else Visibility.PUBLIC


def guard_visibility_change(current: Visibility, requested: Visibility,
                            approval_status: Optional[str]) -> VisDecision:
    approved = bool(approval_status and str(approval_status).strip().lower() == "approved")
    if current == Visibility.PRIVATE and requested == Visibility.PUBLIC:
        return VisDecision.PROCEED if approved else VisDecision.DECLINE_SILENT_PUBLIC
    return VisDecision.PROCEED if approved else VisDecision.DECLINE_APPROVAL


# --------------------------------------------------------------------------- #
# Pure logic: status mapping + gating
# --------------------------------------------------------------------------- #
_RAW_MAP = {
    "uploaded": HfStatus.UPLOADED,
    "completed": HfStatus.UPLOADED,
    "verified": HfStatus.VERIFIED,
    "located": HfStatus.VERIFIED,
    "failed": HfStatus.UPLOAD_FAILED,
    "error": HfStatus.UPLOAD_FAILED,
}


def map_hf_status(raw_state: str) -> HfStatus:
    token = ""
    if raw_state and str(raw_state).strip():
        token = str(raw_state).strip().split()[0].lower()
    return _RAW_MAP.get(token, HfStatus.UPLOAD_FAILED)


def decide_mutating_action(approval_status: Optional[str], kind: str) -> ActionDecision:
    if approval_status and str(approval_status).strip().lower() == "approved":
        return ActionDecision.PROCEED
    return ActionDecision.DECLINE_APPROVAL


# --------------------------------------------------------------------------- #
# Pure logic: redaction + model card
# --------------------------------------------------------------------------- #
def _is_credential_key(key: str) -> bool:
    return bool(_CREDENTIAL_KEY_PATTERN.search(key or ""))


def redact_config(config: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (config or {}).items():
        if _is_credential_key(str(k)):
            continue
        out[k] = redact_config(v) if isinstance(v, dict) else v
    return out


def redact_secrets(text: str, env: Dict[str, Any]) -> str:
    out = text or ""
    for k, v in (env or {}).items():
        if _is_credential_key(str(k)) and v:
            out = out.replace(str(v), f"<{k}>")
    return out


def _render_yaml(data: Dict[str, Any]) -> str:
    import yaml

    return yaml.safe_dump(data, sort_keys=False).strip()


def build_model_card(repo_id: str, checkpoint_kind: str, resolved_config: Dict[str, Any]) -> str:
    safe_config = redact_config(resolved_config or {})
    lines = [
        "---",
        "library_name: transformers",
        "---",
        f"# {repo_id}",
        "",
        f"- **Checkpoint kind:** {checkpoint_kind}",
        "",
        "## Training configuration",
        "",
        "```yaml",
        _render_yaml(safe_config) if safe_config else "{}",
        "```",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Pure logic: commit filter
# --------------------------------------------------------------------------- #
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
# run.yaml linkage (impure: local file only)
# --------------------------------------------------------------------------- #
def write_hf_linkage(run_dir: Path, fields: Dict[str, Any]) -> None:
    """Merge Hub linkage fields into run.yaml. Never writes secret values and
    never changes the training `status` (callers never pass it)."""
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
# Orchestration (thin; composes pure logic + HfClient)
# --------------------------------------------------------------------------- #
def verify_checkpoint(checkpoint_path: str) -> CheckpointResult:
    p = Path(checkpoint_path)
    if not p.exists():
        return CheckpointResult(ok=False, errors=[f"checkpoint not found: {checkpoint_path}"])
    return CheckpointResult(ok=True, path=str(p))


def ensure_repo(client: HfClient, repo_id: str, private: bool,
                approval_status: Optional[str]) -> RepoResult:
    info = client.repo_exists(repo_id=repo_id)
    if info.exists:
        return RepoResult(ok=True, decision="exists", repo_id=repo_id)
    decision = decide_mutating_action(approval_status, "create_repo")
    if decision != ActionDecision.PROCEED:
        return RepoResult(ok=False, decision=decision.value, repo_id=repo_id,
                          errors=["approval required to create repository"])
    client.create_repo(repo_id=repo_id, private=private)
    return RepoResult(ok=True, decision=ActionDecision.PROCEED.value,
                      repo_id=repo_id, created=True)


def upload_checkpoint(
    client: HfClient, repo_id: str, checkpoint_path: str,
    settings: HfSettings, checkpoint_kind: CheckpointKind,
    approval_status: Optional[str],
) -> UploadResult:
    if is_placeholder_namespace(settings.namespace):
        return UploadResult(ok=False, decision="placeholder_namespace",
                            hf_status=HfStatus.NOT_STARTED,
                            errors=["namespace is a placeholder; set it before uploading"])
    push = decide_push(settings.push_policy, checkpoint_kind)
    if push.config_error:
        return UploadResult(ok=False, decision="config_error",
                            hf_status=HfStatus.NOT_STARTED,
                            errors=[f"invalid push_policy: {settings.push_policy}"])
    if not push.eligible:
        return UploadResult(ok=False, decision="skipped_by_policy",
                            hf_status=HfStatus.SKIPPED_BY_POLICY,
                            errors=[f"{checkpoint_kind.value} not eligible under {settings.push_policy}"])
    decision = decide_mutating_action(approval_status, "upload")
    if decision != ActionDecision.PROCEED:
        return UploadResult(ok=False, decision=decision.value,
                            hf_status=HfStatus.NOT_STARTED,
                            errors=["approval required for upload"])
    try:
        outcome = client.upload_checkpoint(repo_id=repo_id, local_path=checkpoint_path)
    except Exception as exc:  # noqa: BLE001 - treated as upload failure, not a crash
        return UploadResult(ok=False, decision="upload_error",
                            hf_status=HfStatus.UPLOAD_FAILED,
                            errors=[f"upload failed: {exc}"])
    if not outcome.revision:
        return UploadResult(ok=False, decision="revision_unavailable",
                            hf_status=HfStatus.UPLOAD_FAILED, repo_id=repo_id,
                            errors=["upload completed without a parseable revision"])
    return UploadResult(ok=True, decision=ActionDecision.PROCEED.value,
                        hf_status=HfStatus.UPLOADED, revision=outcome.revision,
                        repo_id=repo_id)


def verify_upload(client: HfClient, repo_id: str, revision: str) -> VerifyResult:
    located = client.file_exists_at_revision(repo_id=repo_id, revision=revision)
    if located:
        return VerifyResult(ok=True, hf_status=HfStatus.VERIFIED)
    return VerifyResult(ok=False, hf_status=HfStatus.UPLOAD_FAILED,
                        experiment_incomplete=True,
                        errors=[f"checkpoint not locatable at revision {revision}"])


def draft_model_card(run_dir: Path, repo_id: str, checkpoint_kind: str,
                     resolved_config: Dict[str, Any]) -> CardResult:
    card = build_model_card(repo_id, checkpoint_kind, resolved_config)
    path = run_dir / "MODEL_CARD.md"
    path.write_text(card, encoding="utf-8")
    return CardResult(ok=True, path=str(path))


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
        description="Publish a checkpoint to the Hugging Face Hub (Phase 8).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    def _common(p):
        p.add_argument("--plan-file", help="Path to project-plan.md")
        p.add_argument("--run-dir", help="Existing run directory")
        p.add_argument("--experiment-plan", help="Path to the experiment plan.md (approval)")
        p.add_argument("--checkpoint", help="Local checkpoint path")
        p.add_argument("--repo-name", help="Hub repository name (without namespace)")
        p.add_argument("--kind", choices=[k.value for k in CheckpointKind],
                       default="final", help="Checkpoint kind")

    for name in ("verify", "ensure-repo", "upload", "verify-upload", "card", "publish"):
        _common(sub.add_parser(name))

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _build_client(settings: HfSettings) -> HfClient:
    # The ONLY place RealHfClient is constructed.
    return RealHfClient(token=None)


def run_cli(args: argparse.Namespace, client_factory=_build_client) -> Dict[str, Any]:
    if not args.command:
        return _result("error", "No command given", errors=["command required"])

    plan_path = Path(args.plan_file).resolve() if args.plan_file else Path("project-plan.md").resolve()
    frontmatter = _read_frontmatter(plan_path)
    if frontmatter is None:
        return _result("error", f"project-plan.md not found or unparseable: {plan_path}",
                       errors=["Missing/invalid project-plan.md"])
    settings = load_hf_settings(frontmatter)
    if settings.push_policy not in VALID_POLICIES:
        return _result("error", f"huggingface.push_policy invalid: {settings.push_policy!r}",
                       data={"decision": "config_error"},
                       errors=["push_policy must be never, final_only, milestone, final_and_milestone, or every_save"])

    client = client_factory(settings)
    run_dir = Path(args.run_dir).resolve() if args.run_dir else None
    experiment_id = (run_dir.parent.parent.name if run_dir else "")
    repo_name = args.repo_name or experiment_id or "model"
    repo_id = build_repo_id(settings.namespace, repo_name)
    exp_plan = (Path(args.experiment_plan).resolve() if args.experiment_plan
                else (run_dir.parent.parent / "plan.md" if run_dir else None))
    approval_status = read_approval_status(exp_plan) if exp_plan else None
    kind = CheckpointKind(args.kind)

    if args.command == "verify":
        result = verify_checkpoint(args.checkpoint or "")
        status = "success" if result.ok else "error"
        return _result(status, "checkpoint verification", data={"path": result.path},
                       errors=result.errors)

    if run_dir is None:
        return _result("error", "--run-dir is required", errors=["Missing --run-dir"])

    if args.command == "card":
        job = _load_yaml_file(run_dir / "resolved-job.yaml") if (run_dir / "resolved-job.yaml").exists() else {}
        card = draft_model_card(run_dir, repo_id, kind.value, job)
        write_hf_linkage(run_dir, {"model_card_path": card.path})
        return _result("success", "model card drafted", data={"model_card_path": card.path})

    if args.command == "ensure-repo":
        result = ensure_repo(client, repo_id, settings.private, approval_status)
        if not result.ok:
            return _result("error", f"ensure-repo declined: {result.decision}",
                           data={"decision": result.decision}, errors=result.errors)
        write_hf_linkage(run_dir, {"hf_repo_id": repo_id, "hf_private": settings.private})
        return _result("success", f"repo ready: {repo_id}",
                       data={"hf_repo_id": repo_id, "created": result.created})

    if args.command == "upload":
        if not args.checkpoint:
            return _result("error", "--checkpoint is required", errors=["Missing --checkpoint"])
        cp = verify_checkpoint(args.checkpoint)
        if not cp.ok:
            return _result("error", "missing checkpoint", data={"decision": "missing_checkpoint"},
                           errors=cp.errors)
        result = upload_checkpoint(client, repo_id, args.checkpoint, settings, kind, approval_status)
        write_hf_linkage(run_dir, {"hf_status": result.hf_status.value})
        if not result.ok:
            return _result("error", f"upload declined/failed: {result.decision}",
                           data={"decision": result.decision, "hf_status": result.hf_status.value},
                           errors=result.errors)
        write_hf_linkage(run_dir, {
            "hf_repo_id": repo_id, "hf_revision": result.revision,
            "hf_url": build_hf_url(repo_id, result.revision),
            "hf_status": result.hf_status.value, "hf_private": settings.private,
        })
        return _result("success", f"uploaded to {repo_id}@{result.revision}",
                       data={"hf_repo_id": repo_id, "hf_revision": result.revision,
                             "hf_status": result.hf_status.value})

    if args.command == "verify-upload":
        revision = read_run_field(run_dir, "hf_revision")
        if not revision:
            return _result("error", "no recorded hf_revision to verify",
                           errors=["Missing hf_revision"])
        result = verify_upload(client, repo_id, str(revision))
        write_hf_linkage(run_dir, {"hf_status": result.hf_status.value})
        if not result.ok:
            return _result("error", "upload not verified; experiment must not be marked complete",
                           data={"decision": "not_verified", "hf_status": result.hf_status.value,
                                 "experiment_incomplete": result.experiment_incomplete},
                           errors=result.errors)
        return _result("success", f"verified {repo_id}@{revision}",
                       data={"hf_status": result.hf_status.value})

    if args.command == "publish":
        if not args.checkpoint:
            return _result("error", "--checkpoint is required", errors=["Missing --checkpoint"])
        cp = verify_checkpoint(args.checkpoint)
        if not cp.ok:
            return _result("error", "missing checkpoint", data={"decision": "missing_checkpoint"},
                           errors=cp.errors)
        repo = ensure_repo(client, repo_id, settings.private, approval_status)
        if not repo.ok:
            return _result("error", f"ensure-repo declined: {repo.decision}",
                           data={"decision": repo.decision}, errors=repo.errors)
        up = upload_checkpoint(client, repo_id, args.checkpoint, settings, kind, approval_status)
        write_hf_linkage(run_dir, {"hf_status": up.hf_status.value})
        if not up.ok:
            return _result("error", f"upload declined/failed: {up.decision}",
                           data={"decision": up.decision, "hf_status": up.hf_status.value},
                           errors=up.errors)
        ver = verify_upload(client, repo_id, up.revision)
        job = _load_yaml_file(run_dir / "resolved-job.yaml") if (run_dir / "resolved-job.yaml").exists() else {}
        card = draft_model_card(run_dir, repo_id, kind.value, job)
        write_hf_linkage(run_dir, {
            "hf_repo_id": repo_id, "hf_revision": up.revision,
            "hf_url": build_hf_url(repo_id, up.revision),
            "hf_status": ver.hf_status.value, "hf_private": settings.private,
            "model_card_path": card.path,
        })
        if not ver.ok:
            return _result("error", "upload not verified; experiment must not be marked complete",
                           data={"decision": "not_verified", "hf_status": ver.hf_status.value,
                                 "experiment_incomplete": ver.experiment_incomplete},
                           errors=ver.errors)
        return _result("success", f"published {repo_id}@{up.revision}",
                       data={"hf_repo_id": repo_id, "hf_revision": up.revision,
                             "hf_status": ver.hf_status.value, "model_card_path": card.path})

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
    declined = {"approval_required", "placeholder_namespace", "skipped_by_policy",
                "not_verified", "missing_checkpoint", "config_error",
                "revision_unavailable", "upload_error"}
    if decision in declined or any(
        kw in " ".join(result.get("errors", [])).lower()
        for kw in ("approval", "placeholder", "not eligible", "not locatable",
                   "not found", "push_policy", "hf_revision", "not verified")
    ):
        sys.exit(1)
    sys.exit(2)


if __name__ == "__main__":
    main()
