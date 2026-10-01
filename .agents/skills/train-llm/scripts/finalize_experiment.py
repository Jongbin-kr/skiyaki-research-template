#!/usr/bin/env python3
"""
Finalize an experiment and propose a Git commit (Phase 9).

This helper adds the Finalize-and-Git layer on top of the Phase 5 local executor
(run_local.py), the Phase 6 Slurm submitter (submit_slurm.py), the Phase 7 W&B
tracker (track_wandb.py), and the Phase 8 Hugging Face Hub publisher
(publish_hf.py). It verifies experiment completeness per the finalize-experiment
checklist, assembles/validates results.yaml, appends a final history.md entry,
validates journal.md, adds a reverse-chronological project-log.md conclusion,
writes an experiment finalized marker, and selects a Git commit candidate — but
PROPOSES only, never committing or pushing without explicit user approval.

Design discipline (Phase 9):
  - PURE LOGIC functions take plain data and return plain data. They perform no
    Git operation, no network, and no filesystem mutation.
  - IMPURE I/O (Git) passes exclusively through an injected GitClient.
    Production uses RealGitClient (constructed only in main(), wrapping git via
    subprocess); tests inject a FakeGitClient. No real git commit/push and no
    network ever occurs in tests. Reading/writing local experiment docs is
    non-mutating-to-Git and done directly by the orchestration.
  - Mutating Git actions (stage, commit, push) require approval.status ==
    approved in the experiment plan.md. Reading docs, validating, drafting the
    message, and selecting/filtering the candidate are non-mutating.
  - Conclusions reference verified metrics and artifacts; no success is claimed
    without a verified artifact reference AND a verified numeric metric.
  - A failed/partial experiment is finalized honestly; an unverified required
    Hub upload (hf_status != verified) blocks completion.
  - No secrets ever written; credential-bearing files are refused for staging.

Output (JSON envelope): {status, message, data, errors, warnings}
Exit Codes:
  0 - Verified / finalized / proposal-ready / committed after approval
  1 - Declined (verification failure / missing approval / incomplete / blocked)
  2 - Runtime error (filesystem/parse)
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
from typing import Any, Dict, List, Optional, Protocol, Sequence

__version__ = "0.1.0"

MUTATING_KINDS = ("stage", "commit", "push")
_CHECKPOINT_SUFFIX = (".pt", ".bin", ".safetensors", ".ckpt")
_EXCLUDED_SUFFIX = (".out", ".err")
_EXCLUDED_DIRS = ("checkpoints", "wandb")
_CREDENTIAL_FILE_PATTERNS = (".env", ".token", "credentials.json", "secrets.yaml",
                             "secrets.yml")
_CREDENTIAL_KEY_PATTERN = re.compile(
    r"(TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.IGNORECASE
)
_RETRYABLE_FAIL = {"failed", "timed_out", "cancelled", "preempted"}
PROJECT_LOG_ENTRY_MAX_LINES = 12


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class FinalizeStatus(str, Enum):
    VERIFIED = "verified"
    FINALIZED = "finalized"
    PROPOSAL_READY = "proposal_ready"
    COMMITTED = "committed"
    BLOCKED = "blocked"
    DECLINED = "declined"


class ActionDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CompletenessResult:
    ok: bool
    missing: List[str] = field(default_factory=list)
    approval_granted: bool = False


@dataclass(frozen=True)
class ResultsValidation:
    best_run_exists: bool
    metric_numeric: bool
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReferenceResult:
    all_verified: bool
    success_claimable: bool
    unverified: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class HonestyResult:
    ok: bool
    success_allowed: bool
    experiment_complete: bool
    partial: bool
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class JournalValidation:
    has_sections: bool
    interpretive: bool
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class StageOutcome:
    staged: List[str]


@dataclass(frozen=True)
class CommitOutcome:
    sha: str


@dataclass(frozen=True)
class PushOutcome:
    ok: bool


# --------------------------------------------------------------------------- #
# GitClient — the single injected I/O boundary
# --------------------------------------------------------------------------- #
class GitClient(Protocol):
    def status(self) -> List[str]: ...

    def stage(self, paths: Sequence[str]) -> StageOutcome: ...

    def commit(self, message: str) -> CommitOutcome: ...

    def push(self, *, remote: str, branch: str) -> PushOutcome: ...


class RealGitClient:
    """Production client wrapping git via subprocess. Constructed ONLY in main().

    Stages specific files by name, preserves hooks, never modifies git config.
    """

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    def _run(self, argv: Sequence[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self._workspace), *argv],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=120, check=False,
        )

    def status(self) -> List[str]:
        out = self._run(["status", "--porcelain=v1"])
        return [line for line in out.stdout.splitlines() if line.strip()]

    def stage(self, paths):
        self._run(["add", "--", *paths])
        return StageOutcome(staged=list(paths))

    def commit(self, message):
        self._run(["commit", "-m", message])
        rev = self._run(["rev-parse", "HEAD"])
        return CommitOutcome(sha=rev.stdout.strip())

    def push(self, *, remote, branch):
        out = self._run(["push", "-u", remote, branch])
        return PushOutcome(ok=out.returncode == 0)


class FakeGitClient:
    """Test client. Returns pre-seeded results keyed by operation and records
    every call. Raises on any unscripted operation so tests never leak to real
    git or network I/O.
    """

    def __init__(self, scripted: Optional[Dict[str, Any]] = None) -> None:
        self._scripted: Dict[str, Any] = dict(scripted or {})
        self.calls: List[Dict[str, Any]] = []

    def _result(self, op: str, **kwargs):
        self.calls.append({"op": op, **kwargs})
        if op not in self._scripted:
            raise AssertionError(f"FakeGitClient received unscripted op: {op!r}")
        value = self._scripted[op]
        return value(**kwargs) if callable(value) else value

    def status(self) -> List[str]:
        return self._result("status")

    def stage(self, paths) -> StageOutcome:
        return self._result("stage", paths=list(paths))

    def commit(self, message) -> CommitOutcome:
        return self._result("commit", message=message)

    def push(self, *, remote, branch) -> PushOutcome:
        return self._result("push", remote=remote, branch=branch)


# --------------------------------------------------------------------------- #
# Pure logic: completeness verification
# --------------------------------------------------------------------------- #
_REQUIRED = ("plan", "jobs", "runs", "results", "history", "journal", "project_log")


def verify_completeness(present: Dict[str, bool], approval_status: Optional[str]) -> CompletenessResult:
    """present maps each required artifact key to a boolean. Pure."""
    missing = [key for key in _REQUIRED if not present.get(key, False)]
    approved = bool(approval_status and str(approval_status).strip().lower() == "approved")
    return CompletenessResult(ok=not missing and approved, missing=missing,
                              approval_granted=approved)


def validate_results(results: Dict[str, Any], run_ids: Sequence[str]) -> ResultsValidation:
    results = results or {}
    best = (results.get("best_run") or {}).get("run_id")
    best_exists = bool(best) and best in set(run_ids)
    metric = (results.get("primary_metric") or {}).get("value")
    metric_numeric = isinstance(metric, (int, float)) and not isinstance(metric, bool)
    errors: List[str] = []
    if not best_exists:
        errors.append(f"best_run.run_id does not reference an existing run: {best!r}")
    if not metric_numeric:
        errors.append("primary_metric.value is missing or not numeric")
    return ResultsValidation(best_run_exists=best_exists, metric_numeric=metric_numeric,
                             errors=errors)


def verify_references(results: Dict[str, Any], linkage: Dict[str, Any],
                      artifact_present: Dict[str, bool]) -> ReferenceResult:
    """Every claimed metric must have a recorded value; every artifact reference
    must exist in linkage or on the filesystem (artifact_present flags). Pure."""
    results = results or {}
    unverified: List[str] = []

    metric = (results.get("primary_metric") or {}).get("value")
    metric_ok = isinstance(metric, (int, float)) and not isinstance(metric, bool)
    if not metric_ok:
        unverified.append("primary_metric")

    verified_artifact = False
    for ref_key, ref_val in (results.get("artifacts") or {}).items():
        if ref_val is None or ref_val == "":
            continue
        in_linkage = any(str(ref_val) == str(v) for v in (linkage or {}).values())
        on_fs = artifact_present.get(str(ref_val), False)
        if in_linkage or on_fs:
            verified_artifact = True
        else:
            unverified.append(f"artifact:{ref_key}")

    all_verified = not unverified
    success_claimable = metric_ok and verified_artifact
    return ReferenceResult(all_verified=all_verified,
                           success_claimable=success_claimable, unverified=unverified)


def assess_honesty(run_statuses: Dict[str, str], documented: bool,
                   hf_statuses: Sequence[str]) -> HonestyResult:
    """Pure honesty assessment over run statuses and hf statuses."""
    failed = {rid: st for rid, st in (run_statuses or {}).items()
              if str(st).strip().lower() in _RETRYABLE_FAIL}
    errors: List[str] = []
    success_allowed = True
    if failed:
        success_allowed = False
        if not documented:
            errors.append("failed run(s) not documented in history/journal")
    hf_required_unverified = any(
        str(s).strip().lower() not in ("verified", "skipped_by_policy", "not_started")
        for s in (hf_statuses or [])
    )
    experiment_complete = not hf_required_unverified and (not failed or documented)
    if hf_required_unverified:
        errors.append("required Hub upload not verified")
    partial = bool(failed) or hf_required_unverified
    ok = (not failed or documented)
    return HonestyResult(ok=ok, success_allowed=success_allowed,
                         experiment_complete=experiment_complete, partial=partial,
                         errors=errors)


# --------------------------------------------------------------------------- #
# Pure logic: documentation assembly
# --------------------------------------------------------------------------- #
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def assemble_results(plan: Dict[str, Any], results: Dict[str, Any],
                     linkage: Dict[str, Any], *, criteria_met: bool,
                     partial: bool) -> Dict[str, Any]:
    """Assemble/complete results.yaml content from already-loaded data. Pure."""
    out = dict(results or {})
    out.setdefault("best_run", results.get("best_run", {}))
    out.setdefault("primary_metric", results.get("primary_metric", {}))
    criteria = (plan or {}).get("success_criteria", [])
    rationale = ("criteria met" if criteria_met else "criteria not met")
    if partial:
        rationale = "partial experiment; " + rationale
    out["success"] = {"criteria_met": bool(criteria_met), "rationale": rationale,
                      "criteria": criteria}
    out["completed_at"] = _now_iso()
    # Surface prior-phase linkage, redacted.
    out["artifacts"] = redact_config({**(results.get("artifacts") or {}), **(linkage or {})})
    return out


def format_history_entry(best_run: str, metric_name: str, metric_value: Any,
                         criteria_met: bool) -> str:
    determination = "Met" if criteria_met else "Not Met"
    lines = [
        f"## [{_now_iso()}] — Experiment Completed",
        "",
        "- **Status**: Completed",
        f"- **Best Run**: {best_run}",
        f"- **Primary Metric**: {metric_name} = {metric_value}",
        f"- **Success Criteria**: {determination}",
        "",
    ]
    return "\n".join(lines) + "\n"


def validate_journal(journal_text: str) -> JournalValidation:
    text = (journal_text or "").lower()
    has_hypothesis = "hypothesis" in text
    has_findings = "finding" in text
    has_interpretation = "interpret" in text
    has_next = "next experiment" in text or "next steps" in text or "recommend" in text
    warnings: List[str] = []
    if not has_next:
        warnings.append("journal.md missing a recommended-next-experiments section")
    interpretive = has_hypothesis or has_interpretation or has_findings
    return JournalValidation(
        has_sections=has_hypothesis and has_findings and has_interpretation and has_next,
        interpretive=interpretive, warnings=warnings,
    )


def build_project_log_entry(experiment_id: str, conclusion: str, best_run: str,
                            metrics: Dict[str, Any]) -> str:
    lines = [
        f"## [{_today()}] — {experiment_id}",
        "",
        f"- **Conclusion**: {conclusion}",
        f"- **Best Run**: `{best_run}`",
        f"- **Experiment**: `experiments/{experiment_id}/`",
        "- **Key Metrics**:",
    ]
    for name, value in (metrics or {}).items():
        lines.append(f"  - {name}: {value}")
    lines.append("")
    lines.append("---")
    lines.append("")
    entry = "\n".join(lines) + "\n"
    return entry


_ENTRY_HEADER = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] — (.+)$", re.MULTILINE)


def insert_project_log_entry(existing: str, entry: str, experiment_id: str) -> str:
    """Insert the entry at the top (reverse-chronological). If an entry for the
    same experiment already exists, replace it in place rather than duplicating.
    Pure string transform."""
    existing = existing or ""
    header_prefix = "# Project Log"
    body = existing
    header = ""
    if existing.lstrip().startswith(header_prefix):
        # keep the top-level header, insert entries after it
        idx = existing.find("\n", existing.find(header_prefix))
        if idx >= 0:
            header = existing[: idx + 1]
            body = existing[idx + 1 :]
    # Does an entry for this experiment already exist? Replace its block.
    blocks = _split_entry_blocks(body)
    replaced = False
    new_blocks: List[str] = []
    for block in blocks:
        m = _ENTRY_HEADER.search(block)
        if m and m.group(1).strip() == experiment_id:
            new_blocks.append(entry)
            replaced = True
        else:
            new_blocks.append(block)
    if replaced:
        rebuilt = "".join(new_blocks)
        return (header + rebuilt) if header else rebuilt
    # Prepend as newest.
    if header:
        sep = "" if header.endswith("\n") else "\n"
        return header + sep + entry + body.lstrip("\n")
    return entry + body


def _split_entry_blocks(body: str) -> List[str]:
    """Split a project-log body into entry blocks, each starting at a '## [date]'
    header and including everything up to the next header."""
    if not body.strip():
        return []
    positions = [m.start() for m in _ENTRY_HEADER.finditer(body)]
    if not positions:
        return [body]
    blocks: List[str] = []
    if positions[0] > 0:
        blocks.append(body[: positions[0]])
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(body)
        blocks.append(body[start:end])
    return blocks


# --------------------------------------------------------------------------- #
# Pure logic: commit candidate
# --------------------------------------------------------------------------- #
def select_commit_candidate(experiment_rel: str, run_ids: Sequence[str],
                            job_files: Sequence[str]) -> List[str]:
    base = experiment_rel.rstrip("/")
    paths = [f"{base}/plan.md"]
    paths.extend(f"{base}/jobs/{jf}" for jf in job_files)
    paths.extend(f"{base}/runs/{rid}/run.yaml" for rid in run_ids)
    paths.extend([f"{base}/results.yaml", f"{base}/history.md", f"{base}/journal.md"])
    paths.append("project-log.md")
    return paths


def filter_commit_candidates(paths: List[str]) -> List[str]:
    result: List[str] = []
    for p in paths or []:
        if p.endswith(_CHECKPOINT_SUFFIX) or p.endswith(_EXCLUDED_SUFFIX):
            continue
        if any(d in p.split("/") for d in _EXCLUDED_DIRS):
            continue
        result.append(p)
    return result


def scan_for_credential_files(paths: List[str]) -> List[str]:
    found: List[str] = []
    for p in paths or []:
        name = p.split("/")[-1]
        if name in _CREDENTIAL_FILE_PATTERNS or name.endswith(".token") or name == ".env" \
           or name.endswith(".key") or name.endswith(".pem"):
            found.append(p)
    return found


def build_commit_message(experiment_id: str, metric_name: str, metric_value: Any,
                         criteria_met: bool, linkage: Dict[str, Any]) -> str:
    determination = "Met" if criteria_met else "Not Met"
    safe_linkage = redact_config(linkage or {})
    lines = [
        f"feat({experiment_id}): finalize experiment",
        "",
        f"Complete {experiment_id} experiment.",
        "",
        "Results:",
        f"- Primary Metric: {metric_name} = {metric_value}",
        f"- Success Criteria: {determination}",
    ]
    for key in ("wandb_url", "wandb_run_id", "hf_repo_id", "hf_revision",
                "hf_status", "slurm_job_id"):
        if key in safe_linkage and safe_linkage[key] not in (None, ""):
            lines.append(f"- {key}: {safe_linkage[key]}")
    return "\n".join(lines) + "\n"


def decide_mutating_action(approval_status: Optional[str], kind: str) -> ActionDecision:
    if approval_status and str(approval_status).strip().lower() == "approved":
        return ActionDecision.PROCEED
    return ActionDecision.DECLINE_APPROVAL


# --------------------------------------------------------------------------- #
# Pure logic: redaction
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


# --------------------------------------------------------------------------- #
# Impure: local document loading + writing (not Git)
# --------------------------------------------------------------------------- #
@dataclass
class LoadedDocs:
    experiment_dir: Path
    present: Dict[str, bool]
    plan: Dict[str, Any]
    approval_status: Optional[str]
    results: Dict[str, Any]
    run_ids: List[str]
    run_statuses: Dict[str, str]
    linkage: Dict[str, Any]
    hf_statuses: List[str]
    job_files: List[str]
    journal_text: str
    project_log_text: str


def _read_frontmatter_file(path: Path) -> Optional[Dict[str, Any]]:
    import yaml

    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    try:
        data = yaml.safe_load(text[text.index("\n") + 1 : end])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _load_yaml(path: Path) -> Dict[str, Any]:
    import yaml

    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def load_documents(experiment_dir: Path, workspace: Path) -> LoadedDocs:
    plan_path = experiment_dir / "plan.md"
    jobs_dir = experiment_dir / "jobs"
    runs_dir = experiment_dir / "runs"
    results_path = experiment_dir / "results.yaml"
    history_path = experiment_dir / "history.md"
    journal_path = experiment_dir / "journal.md"
    project_log_path = workspace / "project-log.md"

    plan = _read_frontmatter_file(plan_path) or {}
    approval = plan.get("approval") if isinstance(plan.get("approval"), dict) else {}
    approval_status = str(approval.get("status")) if approval and approval.get("status") is not None else None

    run_ids: List[str] = []
    run_statuses: Dict[str, str] = {}
    linkage: Dict[str, Any] = {}
    hf_statuses: List[str] = []
    if runs_dir.exists():
        for rd in sorted(runs_dir.iterdir()):
            if not rd.is_dir():
                continue
            run_ids.append(rd.name)
            rec = _load_yaml(rd / "run.yaml")
            run_statuses[rd.name] = str(rec.get("status", ""))
            for key in ("slurm_job_id", "wandb_run_id", "wandb_url", "wandb_status",
                        "hf_repo_id", "hf_revision", "hf_status"):
                if key in rec and rec[key] not in (None, ""):
                    linkage[key] = rec[key]
            if "hf_status" in rec and rec["hf_status"] not in (None, ""):
                hf_statuses.append(str(rec["hf_status"]))

    job_files = ([p.name for p in sorted(jobs_dir.glob("*.yaml"))] if jobs_dir.exists() else [])

    present = {
        "plan": plan_path.exists(),
        "jobs": bool(job_files),
        "runs": bool(run_ids),
        "results": results_path.exists(),
        "history": history_path.exists(),
        "journal": journal_path.exists(),
        "project_log": project_log_path.exists(),
    }
    return LoadedDocs(
        experiment_dir=experiment_dir, present=present, plan=plan,
        approval_status=approval_status, results=_load_yaml(results_path),
        run_ids=run_ids, run_statuses=run_statuses, linkage=linkage,
        hf_statuses=hf_statuses, job_files=job_files,
        journal_text=(journal_path.read_text(encoding="utf-8") if journal_path.exists() else ""),
        project_log_text=(project_log_path.read_text(encoding="utf-8") if project_log_path.exists() else ""),
    )


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


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalize an experiment and propose a Git commit (Phase 9).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    def _common(p):
        p.add_argument("--experiment-dir", help="Experiment directory")
        p.add_argument("--workspace", help="Workspace root")

    for name in ("verify", "finalize", "propose", "commit"):
        _common(sub.add_parser(name))

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _build_client(workspace: Path) -> GitClient:
    # The ONLY place RealGitClient is constructed.
    return RealGitClient(workspace)


def _verify(docs: LoadedDocs) -> Dict[str, Any]:
    comp = verify_completeness(docs.present, docs.approval_status)
    if comp.missing:
        return _result("error", "blocked finalization: missing required files",
                       data={"decision": "blocked", "missing": comp.missing},
                       errors=[f"missing: {m}" for m in comp.missing])
    rv = validate_results(docs.results, docs.run_ids)
    if not rv.best_run_exists:
        return _result("error", "invalid reference: best_run.run_id",
                       data={"decision": "invalid_reference"}, errors=rv.errors)
    if not rv.metric_numeric:
        return _result("error", "incomplete results: primary_metric not numeric",
                       data={"decision": "incomplete_results"}, errors=rv.errors)
    artifact_present: Dict[str, bool] = {}
    ref = verify_references(docs.results, docs.linkage, artifact_present)
    if not ref.all_verified:
        return _result("error", "unverified reference(s) in results",
                       data={"decision": "unverified_reference",
                             "unverified": ref.unverified},
                       errors=[f"unverified: {u}" for u in ref.unverified])
    return _result("success", "experiment verification passed",
                   data={"status": FinalizeStatus.VERIFIED.value,
                         "success_claimable": ref.success_claimable,
                         "approval_granted": comp.approval_granted})


def run_cli(args: argparse.Namespace, client_factory=_build_client) -> Dict[str, Any]:
    if not args.command:
        return _result("error", "No command given", errors=["command required"])
    if not args.experiment_dir:
        return _result("error", "--experiment-dir is required", errors=["Missing --experiment-dir"])

    experiment_dir = Path(args.experiment_dir).resolve()
    workspace = Path(args.workspace).resolve() if args.workspace else experiment_dir.parent.parent
    docs = load_documents(experiment_dir, workspace)
    experiment_id = experiment_dir.name

    if args.command == "verify":
        return _verify(docs)

    # Both finalize/propose/commit require a passing verification first.
    verified = _verify(docs)
    if verified["status"] != "success":
        return verified

    honesty = assess_honesty(docs.run_statuses, documented=True, hf_statuses=docs.hf_statuses)
    rv = validate_results(docs.results, docs.run_ids)
    ref = verify_references(docs.results, docs.linkage, {})
    criteria_met = ref.success_claimable and honesty.success_allowed and honesty.experiment_complete
    best_run = (docs.results.get("best_run") or {}).get("run_id", "")
    pm = docs.results.get("primary_metric") or {}
    metric_name = pm.get("name", "metric")
    metric_value = pm.get("value")

    if args.command == "finalize":
        import yaml

        assembled = assemble_results(docs.plan, docs.results, docs.linkage,
                                     criteria_met=criteria_met, partial=honesty.partial)
        (experiment_dir / "results.yaml").write_text(
            yaml.safe_dump(assembled, sort_keys=False), encoding="utf-8")
        # append history
        hist = experiment_dir / "history.md"
        entry = format_history_entry(best_run, metric_name, metric_value, criteria_met)
        prior = hist.read_text(encoding="utf-8") if hist.exists() else "# Experiment History\n\n"
        if prior and not prior.endswith("\n"):
            prior += "\n"
        hist.write_text(prior + entry, encoding="utf-8")
        jv = validate_journal(docs.journal_text)
        # project log
        conclusion = f"{metric_name}={metric_value}; criteria {'met' if criteria_met else 'not met'}"
        pl_entry = build_project_log_entry(experiment_id, conclusion, best_run,
                                           {metric_name: metric_value})
        plog = workspace / "project-log.md"
        updated = insert_project_log_entry(docs.project_log_text, pl_entry, experiment_id)
        plog.write_text(updated, encoding="utf-8")
        # finalized marker (plan.md status) — never touches run status
        _write_finalized_marker(experiment_dir / "plan.md", honesty.experiment_complete)
        status = FinalizeStatus.FINALIZED.value
        if not honesty.experiment_complete:
            return _result("error", "experiment incomplete; finalized as partial",
                           data={"decision": "incomplete_experiment", "status": status,
                                 "experiment_complete": False},
                           errors=honesty.errors, warnings=jv.warnings)
        return _result("success", f"finalized {experiment_id}",
                       data={"status": status, "criteria_met": criteria_met,
                             "experiment_complete": honesty.experiment_complete},
                       warnings=jv.warnings)

    # propose / commit share candidate building
    candidate = filter_commit_candidates(
        select_commit_candidate(f"experiments/{experiment_id}", docs.run_ids, docs.job_files))
    cred = scan_for_credential_files(candidate)
    if cred:
        return _result("error", "security review: credential file in candidate",
                       data={"decision": "security_review", "credential_files": cred},
                       errors=[f"refused credential file: {c}" for c in cred])
    message = build_commit_message(experiment_id, metric_name, metric_value,
                                   criteria_met, docs.linkage)

    if args.command == "propose":
        return _result("success", "commit candidate proposed",
                       data={"status": FinalizeStatus.PROPOSAL_READY.value,
                             "files": candidate, "message": message})

    # commit — approval-gated
    decision = decide_mutating_action(docs.approval_status, "commit")
    if decision != ActionDecision.PROCEED:
        return _result("error", "commit requires approval; presented as proposal",
                       data={"decision": "approval_required",
                             "status": FinalizeStatus.PROPOSAL_READY.value,
                             "files": candidate, "message": message},
                       errors=["approval.status is not approved"])
    client = client_factory(workspace)
    client.stage(candidate)
    outcome = client.commit(message)
    return _result("success", f"committed {experiment_id}",
                   data={"status": FinalizeStatus.COMMITTED.value,
                         "sha": outcome.sha, "files": candidate})


def _write_finalized_marker(plan_path: Path, complete: bool) -> None:
    """Set plan.md frontmatter status without changing any run status."""
    import yaml

    if not plan_path.exists():
        return
    text = plan_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return
    end = text.find("\n---", 3)
    if end < 0:
        return
    fm_text = text[text.index("\n") + 1 : end]
    body = text[end + 4 :]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return
    if not isinstance(fm, dict):
        return
    fm["status"] = "completed" if complete else "partial"
    fm["finalized"] = True
    plan_path.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False) + "---" + body,
                         encoding="utf-8")


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
    declined = {"blocked", "invalid_reference", "incomplete_results",
                "unverified_reference", "approval_required", "security_review",
                "incomplete_experiment"}
    if decision in declined or any(
        kw in " ".join(result.get("errors", [])).lower()
        for kw in ("missing", "approval", "unverified", "credential", "not numeric",
                   "incomplete", "invalid")
    ):
        sys.exit(1)
    sys.exit(2)


if __name__ == "__main__":
    main()
