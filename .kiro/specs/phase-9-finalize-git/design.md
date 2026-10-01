# Design Document

## Overview

Phase 9 adds the Finalize and Git layer on top of the Phase 5 local-execution helper (`run_local.py`), the Phase 6 Slurm submission helper (`submit_slurm.py`), the Phase 7 W&B tracking helper (`track_wandb.py`), and the Phase 8 Hugging Face Hub publication helper (`publish_hf.py`). It is delivered as a deterministic Python helper, `finalize_experiment.py`, in `.agents/skills/train-llm/scripts/`, alongside the existing `initialize_run.py`, `run_local.py`, `submit_slurm.py`, `track_wandb.py`, and `publish_hf.py`. It implements the `verify_completion.py` idea that the `finalize-experiment` skill's `completion-checklist.md` defers to a future script, realizing that checklist as a deterministic helper.

The central design decision is the same strict separation between **pure logic** and **impure I/O** that Phases 6, 7, and 8 established:

- **Pure logic** functions take plain data (dicts parsed from YAML, strings, enums, paths-present flags) and return plain data (strings, enums, dataclasses, dicts). They perform no Git operation, no subprocess call, no network, and no filesystem mutation. These functions carry the property-based and unit tests.
- **Impure I/O** passes exclusively through a single injected `GitClient` interface. Production uses a `RealGitClient` that wraps `git` via subprocess; tests inject a `FakeGitClient`. No real Git commit, no push, and no network access ever occurs in tests.

All stable settings (for example the W&B entity and project, the Hugging Face namespace) continue to be read from `project-plan.md` frontmatter and are never re-asked. Mutating Git actions — staging files, creating a commit, and pushing — require `approval.status == approved` in the experiment `plan.md`, the same approval gate used in Phases 5, 6, 7, and 8. Read-only and local-only actions — reading `run.yaml`, `results.yaml`, `plan.md`, `history.md`, `journal.md`, and `project-log.md`; validating documentation; assembling the result file; drafting the commit message; and selecting the commit candidate — are non-mutating and ungated. The helper proposes the Commit_Candidate without creating a commit until the Approval_Status equals `approved`.

A failed or partial experiment is finalized honestly. A required run with a `failed` Run_Status is confirmed documented in `history.md` and `journal.md`, success criteria are not reported as met, and if a required Hub upload is not verified (Phase 8 `hf_status` other than `verified`) the Experiment is not marked complete. The Finalizer never changes any training Run_Status; it writes only a Finalized_Marker to `plan.md` (a `status` of `completed` or a `finalized` flag) to record experiment-level completion. Generated artifacts never contain secrets, tokens, or credential values, reusing the Phase 5/6/7/8 names-only redaction approach, and the commit security review refuses to stage credential-bearing files (for example `.env`, `*.token`, `credentials.json`). The commit candidate reuses the Phase 6/7/8 exclusion of model checkpoints (`*.pt`, `*.bin`, `*.safetensors`, `*.ckpt`), W&B caches (`wandb/`), raw Slurm logs (`*.out`, `*.err`), and other large artifacts.

The helper follows the Phase 5/6/7/8 output contract: a JSON envelope `{status, message, data, errors, warnings}` printed to stdout, with exit codes `0` (verified, finalized, proposal-ready, or committed after approval), `1` (declined: verification failure, missing approval, incomplete experiment, blocked finalization, or credential-file refusal), and `2` (runtime error: filesystem/parse). Phase 9 does not run training, submit Slurm jobs, call W&B, or upload to the Hub.

## Architecture

```text
                   project-plan.md (frontmatter)          experiment plan.md (approval)
                               │                                      │
                               ▼                                      ▼
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                         finalize_experiment.py                            │
        │                                                                           │
        │   PURE LOGIC (no I/O, fully testable)                                     │
        │   ├─ verify_completeness(loaded) -> CompletenessResult                    │
        │   ├─ validate_results(results, run_dirs) -> ResultsValidation             │
        │   ├─ verify_references(results, linkage) -> ReferenceResult               │
        │   ├─ assemble_results(plan, runs, linkage) -> dict                        │
        │   ├─ format_history_entry(fields) -> str                                  │
        │   ├─ validate_journal(journal_text) -> JournalValidation                  │
        │   ├─ build_project_log_entry(fields) -> str                               │
        │   ├─ insert_project_log_entry(existing, entry, exp_id) -> str             │
        │   ├─ select_commit_candidate(experiment_dir, produced) -> list[str]       │
        │   ├─ filter_commit_candidates(paths) -> list[str]                         │
        │   ├─ scan_for_credential_files(paths) -> list[str]                        │
        │   ├─ build_commit_message(fields) -> str                                  │
        │   ├─ decide_mutating_action(approval, kind) -> ActionDecision             │
        │   ├─ assess_honesty(runs, hf_statuses) -> HonestyResult                   │
        │   ├─ map_finalize_status(signals) -> FinalizeStatus                       │
        │   ├─ redact_config(config) -> dict                                        │
        │   └─ redact_secrets(text, env) -> str                                     │
        │                                                                           │
        │   IMPURE BOUNDARY (single injection point)                                │
        │   └─ GitClient.<op>(...)                                                   │
        │        ├─ RealGitClient  (production; wraps git via subprocess)           │
        │        └─ FakeGitClient  (tests; scripted results, records calls)         │
        │                                                                           │
        │   ORCHESTRATION (thin; composes pure logic + GitClient)                   │
        │   ├─ verify(exp_dir) -> VerifyResult               (read-only)            │
        │   ├─ finalize_docs(exp_dir, plan, runs) -> DocsResult   (local writes)    │
        │   ├─ propose_commit(exp_dir, produced) -> ProposalResult (read-only)      │
        │   ├─ commit(client, candidate, approval) -> CommitResult (approval-gated) │
        │   └─ write_finalized_marker(plan_file, status) -> None  (never Run_Status)│
        └─────────────────────────────────────────────────────────────────────────┘
                               │                                   │
                               ▼                                   ▼
   experiments/<exp>/results.yaml, history.md, journal.md     git stage/commit/push
   experiments/<exp>/plan.md (Finalized_Marker)               (via RealGitClient only)
   project-log.md (reverse-chronological entry)
```

### Why this split

- Property tests exercise completeness verification, results validation, reference checking, result assembly, history-entry formatting, journal validation, project-log insertion and dedup, commit-candidate selection and exclusion filtering, credential-file scanning, commit-message assembly, approval gating, honest-finalization assessment, status mapping, and redaction across hundreds of inputs with zero Git or network risk.
- Integration tests use `FakeGitClient` to assert orchestration wiring and approval gating without any real staging, commit, or push.
- The only code that can touch `git` or the network is `RealGitClient`, which is never constructed in tests.

## Components and Interfaces

### GitClient (injected boundary)

Every Git operation, network call, and filesystem-mutating Git action passes through one protocol. The orchestration never shells out to `git` directly.

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class StageOutcome:
    staged: tuple[str, ...]      # paths actually staged

@dataclass(frozen=True)
class CommitOutcome:
    commit_sha: str
    staged: tuple[str, ...]

@dataclass(frozen=True)
class PushOutcome:
    pushed: bool
    remote: str
    branch: str

class GitClient(Protocol):
    def status(self) -> tuple[str, ...]:
        """Return the working-tree status. Read-only."""
        ...

    def stage(self, *, paths: tuple[str, ...]) -> StageOutcome:
        """Stage the given paths. Mutating; approval-gated."""
        ...

    def commit(self, *, message: str) -> CommitOutcome:
        """Create a commit from staged content. Mutating; approval-gated."""
        ...

    def push(self, *, remote: str, branch: str) -> PushOutcome:
        """Push the branch to a remote. Mutating; network; approval-gated."""
        ...
```

- `RealGitClient()` wraps `git` via `subprocess` (`git status --porcelain`, `git add -- <paths>`, `git commit -m`, `git push -u <remote> <branch>`) and is constructed **only** in `main()`. It stages specific files by name rather than `git add -A`, preserves hooks, and never modifies Git config.
- `FakeGitClient(scripted)` returns pre-seeded results keyed by operation and records every call for assertions. It raises on any unscripted operation, guaranteeing tests never leak to real Git or the network.

### Loaded-document bundle

The orchestration reads every document once, then hands plain data to the pure logic. No pure function performs I/O.

```python
@dataclass(frozen=True)
class LoadedDocs:
    plan_present: bool
    job_files_present: bool
    run_dirs: tuple[str, ...]          # run directory names found under runs/
    results_present: bool
    history_present: bool
    journal_present: bool
    project_log_present: bool
    approval_status: str | None        # plan.md approval.status
    plan: dict                         # plan.md frontmatter
    results: dict                      # parsed results.yaml (may be empty)
    linkage: dict                      # run_id -> Linkage_Fields
    journal_text: str
    project_log_text: str
```

### Completeness verification

```python
@dataclass(frozen=True)
class CompletenessResult:
    complete: bool
    approved: bool
    missing: tuple[str, ...]           # names of missing required artifacts

_REQUIRED = ("plan", "job_files", "runs", "results", "history", "journal", "project_log")

def verify_completeness(loaded: LoadedDocs) -> CompletenessResult:
    """Pure: derive the verification result from already-loaded presence flags.
    Performs no I/O."""
    missing: list[str] = []
    if not loaded.plan_present:
        missing.append("plan.md")
    if not loaded.job_files_present:
        missing.append("jobs/*.yaml")
    if not loaded.run_dirs:
        missing.append("runs/")
    if not loaded.results_present:
        missing.append("results.yaml")
    if not loaded.history_present:
        missing.append("history.md")
    if not loaded.journal_present:
        missing.append("journal.md")
    if not loaded.project_log_present:
        missing.append("project-log.md")
    approved = bool(loaded.approval_status
                    and loaded.approval_status.strip().lower() == "approved")
    return CompletenessResult(complete=not missing, approved=approved,
                              missing=tuple(missing))
```

When a required file is missing the orchestration reports a blocked-finalization outcome identifying the missing file and exits `1`. The approval status is surfaced here but gates only Mutating_Git_Actions, not read-only verification.

### Results validation

```python
import numbers

@dataclass(frozen=True)
class ResultsValidation:
    best_run_exists: bool
    metric_numeric: bool
    best_run_id: str | None
    primary_metric_value: object

def _is_numeric(value) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool)

def validate_results(results: dict, run_dirs: tuple[str, ...]) -> ResultsValidation:
    """Pure: confirm best_run.run_id references an existing run directory and
    the primary metric value is numeric. Performs no I/O."""
    best = (results or {}).get("best_run", {}) or {}
    run_id = best.get("run_id")
    metric = ((results or {}).get("primary_metric", {}) or {}).get("value")
    return ResultsValidation(
        best_run_exists=bool(run_id) and run_id in run_dirs,
        metric_numeric=_is_numeric(metric),
        best_run_id=run_id,
        primary_metric_value=metric,
    )
```

If `best_run.run_id` does not reference an existing run directory the orchestration reports an invalid-reference outcome and exits `1`. If the Primary_Metric value is missing or not numeric it reports an incomplete-results outcome and exits `1`.

### Reference verification

```python
@dataclass(frozen=True)
class ReferenceResult:
    all_metrics_backed: bool
    all_artifacts_exist: bool
    verified_artifact_refs: tuple[str, ...]
    success_claimable: bool            # >=1 verified artifact AND verified numeric metric
    unverified: tuple[str, ...]

def verify_references(results: dict, linkage: dict,
                      metric_numeric: bool) -> ReferenceResult:
    """Pure: every claimed metric must be backed by a recorded value, and every
    artifact reference must exist in the linkage fields or on the filesystem
    (presence flags). No success without >=1 verified artifact ref and a verified
    numeric metric. Performs no I/O."""
    ...
```

A conclusion that references a metric or artifact that cannot be verified yields an unverified-reference outcome and the experiment is **not** marked successful. The Finalizer never claims success without at least one verified Artifact_Reference and a verified numeric Primary_Metric value.

### Results assembly

```python
def assemble_results(plan: dict, runs: dict, linkage: dict) -> dict:
    """Pure: assemble results.yaml content from already-loaded data. No network I/O.
    Populates best_run, primary_metric, success (criteria_met + rationale derived
    from the plan success criteria), and completed_at, and surfaces the Linkage_Fields
    from each referenced run."""
    ...
```

The assembled Results_File confirms the presence of `best_run`, `primary_metric`, `success`, and `completed_at`; populates the Success_Assessment with a `criteria_met` boolean and a `rationale` derived from the Plan's success criteria; and surfaces each referenced Run_Record's Linkage_Fields. A partial experiment records its partial status in the Results_File and the Success_Assessment rationale.

### History entry formatting

```python
def format_history_entry(fields: dict) -> str:
    """Pure: build a completion entry containing a timestamp, the best run
    reference, the Primary_Metric value, and the Success_Assessment determination.
    The entry is a summary record, never full stdout/stderr logs."""
    lines = [
        f"## [{fields['timestamp']}] — Experiment {fields['completion_label']}",
        "",
        f"- **Status**: {fields['status']}",
        f"- **Best Run**: {fields['best_run_id']}",
        f"- **Primary Metric**: {fields['metric_name']} = {fields['metric_value']}",
        f"- **Success Criteria**: {fields['criteria_met_label']}",
    ]
    return "\n".join(lines)
```

The orchestration appends this entry to the History_File without modifying prior entries, and the entry contains summary records rather than full logs.

### Journal validation

```python
@dataclass(frozen=True)
class JournalValidation:
    has_hypothesis_assessment: bool
    has_key_findings: bool
    has_interpretation: bool
    has_next_experiments: bool
    is_interpretive: bool              # not merely an execution log
    warnings: tuple[str, ...]

def validate_journal(journal_text: str) -> JournalValidation:
    """Pure: confirm the journal contains a hypothesis assessment, key findings,
    interpretation, and recommended next experiments. Warn (not block) if the
    recommended-next-experiments section is absent. Performs no I/O."""
    ...
```

A missing recommended-next-experiments section produces a documentation warning in the Output_Envelope rather than a block. The Journal_File must contain interpretive analysis rather than only an execution log.

### Project-log entry assembly and insertion

```python
def build_project_log_entry(fields: dict) -> str:
    """Pure: a concise, project-level conclusion — a one-line conclusion, the best
    run reference, a link to the Experiment_Dir, and key metric values — that does
    NOT duplicate the per-run detail in results.yaml, history.md, or journal.md.
    A section/length constraint keeps the entry project-level."""
    ...

def insert_project_log_entry(existing: str, entry: str, experiment_id: str) -> str:
    """Pure: insert the entry at the TOP of the project log in reverse-chronological
    order. If an entry for the same experiment_id already exists, UPDATE it in place
    rather than adding a duplicate. Performs no I/O."""
    ...
```

The Project_Log_Entry is added at the top in reverse-chronological order and constrained to a project-level conclusion. When an entry for the same experiment already exists, `insert_project_log_entry` updates the existing entry rather than appending a duplicate.

### Commit-candidate selection, filtering, and security scan

```python
def select_commit_candidate(experiment_dir: str, produced_paths: list[str]) -> list[str]:
    """Pure: build the candidate file list — plan.md, jobs/*.yaml, runs/*/run.yaml,
    results.yaml, history.md, journal.md, and project-log.md. No I/O beyond reading
    already-loaded path data."""
    ...

_EXCLUDED_SUFFIX = (".pt", ".bin", ".safetensors", ".ckpt", ".out", ".err")
_EXCLUDED_DIRS = ("wandb", "checkpoints")

def filter_commit_candidates(paths: list[str]) -> list[str]:
    """Pure: exclude model checkpoints (*.pt, *.bin, *.safetensors, *.ckpt),
    the wandb/ cache, raw .out/.err logs, and other large artifacts. No I/O."""
    return [p for p in paths
            if not p.endswith(_EXCLUDED_SUFFIX)
            and not any(d in p.split("/") for d in _EXCLUDED_DIRS)]

_CREDENTIAL_FILE_PATTERNS = (".env", ".token", "credentials.json")

def scan_for_credential_files(paths: list[str]) -> list[str]:
    """Pure: return every candidate path matching a Credential_File pattern
    (.env, *.token, credentials.json). No I/O."""
    hits = []
    for p in paths:
        name = p.split("/")[-1]
        if (name == ".env" or name.endswith(".env")
                or name.endswith(".token") or name == "credentials.json"):
            hits.append(p)
    return hits
```

If `scan_for_credential_files` returns any path, the Finalizer refuses to stage it, reports a security-review outcome, declines the Mutating_Git_Action, and exits `1`. Checkpoints and caches are kept out of the candidate by `filter_commit_candidates`, which reuses the Phase 6/7/8 exclusion set.

### Commit-message assembly

```python
def build_commit_message(fields: dict) -> str:
    """Pure: assemble the commit message including the experiment identifier,
    the Primary_Metric value, the Success_Assessment determination, and the surfaced
    Linkage_Fields. Every Credential_Key value is dropped before rendering."""
    ...
```

### Approval gating for mutating Git actions

```python
from enum import Enum

class ActionDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"

MUTATING_KINDS = ("stage", "commit", "push")

def decide_mutating_action(approval_status: str | None, kind: str) -> ActionDecision:
    if approval_status and approval_status.strip().lower() == "approved":
        return ActionDecision.PROCEED
    return ActionDecision.DECLINE_APPROVAL
```

Every Mutating_Git_Action (stage, commit, push) calls `decide_mutating_action` first; on `DECLINE_APPROVAL` the orchestration returns without touching the `GitClient`, presents the Commit_Candidate as a proposal, and exits `1`. Read-only and local-only actions (reading the documents, validating docs, assembling results, drafting the message, selecting the candidate) skip the gate entirely.

### Honest finalization

```python
@dataclass(frozen=True)
class HonestyResult:
    required_failure_documented: bool
    success_criteria_met: bool
    experiment_complete: bool
    partial: bool

def assess_honesty(runs: dict, hf_statuses: tuple[str, ...],
                   failure_documented: bool,
                   references: "ReferenceResult") -> HonestyResult:
    """Pure: a required run with status 'failed' must be documented and success
    must NOT be reported met; any required Hub upload with hf_status other than
    'verified' blocks experiment completion. Performs no I/O."""
    any_failed = any((r.get("status") == "failed") for r in runs.values())
    hub_verified = all(s == "verified" for s in hf_statuses) if hf_statuses else True
    success = (not any_failed) and references.success_claimable
    complete = (not any_failed) and hub_verified and references.success_claimable
    return HonestyResult(
        required_failure_documented=(not any_failed) or failure_documented,
        success_criteria_met=success,
        experiment_complete=complete,
        partial=any_failed or (not hub_verified),
    )
```

### Status model

```python
class FinalizeStatus(str, Enum):
    VERIFIED = "verified"            # completeness/results/references all pass
    FINALIZED = "finalized"          # docs assembled and marker written
    PROPOSAL_READY = "proposal_ready"  # candidate selected, awaiting approval
    COMMITTED = "committed"          # commit created after approval
    BLOCKED = "blocked"              # missing file / invalid reference / incomplete
    DECLINED = "declined"            # approval missing / credential file / unverified

def map_finalize_status(signals: dict) -> FinalizeStatus:
    """Pure: map the accumulated verification/finalization signals to a status."""
    ...
```

The Finalized_Marker (a `status` of `completed` or a `finalized` flag) is written only to the Plan, and the Finalizer leaves every training Run_Status unchanged.

### Config assembly and redaction

```python
import re

_CREDENTIAL_KEY_PATTERN = re.compile(
    r"(TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.IGNORECASE
)

def _is_credential_key(key: str) -> bool:
    return bool(_CREDENTIAL_KEY_PATTERN.search(key or ""))

def redact_config(config: dict) -> dict:
    """Drop every credential-like value; retain only non-credential entries.
    Where a name must be surfaced, the key name is kept but the value is removed."""
    out = {}
    for k, v in (config or {}).items():
        if _is_credential_key(k):
            continue
        out[k] = redact_config(v) if isinstance(v, dict) else v
    return out

def redact_secrets(text: str, env: dict) -> str:
    out = text or ""
    for k, v in (env or {}).items():
        if _is_credential_key(k) and v:
            out = out.replace(str(v), f"<{k}>")
    return out
```

`redact_config` and `redact_secrets` reuse the Phase 5/6/7/8 names-only approach: `HF_TOKEN`, `WANDB_API_KEY`, and any other `Credential_Key` value never reach the Results_File, History_File, Journal_File, Project_Log, commit message, or output envelope, including error and warning text.

### CLI (orchestration entry point)

`main()` parses subcommands (`verify`, `finalize`, `propose`, `commit`), constructs the `RealGitClient` **only there**, composes the pure logic with the client, writes the finalization artifacts and Finalized_Marker, and prints the output envelope with the mapped exit code.

- `verify` runs completeness + results validation + reference verification (read-only).
- `finalize` assembles `results.yaml`, appends the `history.md` entry, validates `journal.md`, and updates `project-log.md`, then writes the Finalized_Marker (local writes; no Git).
- `propose` selects + filters + security-scans the candidate and drafts the message, presenting a proposal only (read-only; no Git).
- `commit` executes the approval-gated Mutating_Git_Action through the `GitClient`.

```python
def main(argv: list[str]) -> int:
    args = parse_args(argv)
    loaded = load_documents(args.experiment_dir)          # the only I/O boundary for reads
    comp = verify_completeness(loaded)
    if not comp.complete:
        return emit(blocked_envelope("missing required file", comp.missing), code=1)
    client = RealGitClient()  # only here; subprocess git used only in the real client
    ...
```

## Data Models

- **LoadedDocs**: presence flags and parsed content read once by the orchestration and handed to the pure logic.
- **CompletenessResult**: pure result of `verify_completeness` — completeness, approval, and the missing-file list.
- **ResultsValidation**: pure result of `validate_results` — best-run existence and metric numericness.
- **ReferenceResult**: pure result of `verify_references` — metric backing, artifact existence, and whether success is claimable.
- **HonestyResult**: pure result of `assess_honesty` — failure-documented, success-met, experiment-complete, partial.
- **FinalizeStatus**: the finalization outcome enum (`verified`, `finalized`, `proposal_ready`, `committed`, `blocked`, `declined`).
- **StageOutcome / CommitOutcome / PushOutcome**: the only Git values crossing the injected boundary.
- **Linkage_Fields**: the Phase 5–8 fields surfaced from each Run_Record (`status`, `slurm_job_id`, `wandb_run_id`, `wandb_url`, `wandb_status`, `hf_repo_id`, `hf_revision`, `hf_status`), surfaced into `results.yaml` and the commit message.
- **Commit_Candidate**: the filtered file list plus the drafted commit message, presented for approval and never committed automatically.
- **Finalized_Marker**: the experiment-level completion marker written to `plan.md`; it never changes any Run_Status.

### plan.md Finalized_Marker

Phase 9 writes the Finalized_Marker only to the experiment Plan:

```yaml
status: completed        # experiment-level completion marker (or a `finalized: true` flag)
# Run_Status values in each run.yaml are owned by Phase 5/6 and are never changed here.
```

### results.yaml surfaced linkage

```yaml
best_run:
  run_id: train-r16__20250115T142530
  checkpoint: my-namespace/llama2-7b-wikitext-lora-r16   # surfaced from hf_repo_id
primary_metric:
  name: perplexity
  value: 27.1
success:
  criteria_met: true
  rationale: "improvement 4.2% exceeds 2% threshold from plan success criteria"
completed_at: 2025-01-15T18:30:00Z
linkage:
  train-r16__20250115T142530:
    status: succeeded
    wandb_run_id: 2a3b4c5d
    hf_status: verified
```

No secret, token, password, or credential value is ever written; reporting reuses the Phase 5/6/7/8 redaction approach (names only, credential-like keys dropped).

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Completeness verification is pure and reports missing files

*For any* bundle of already-loaded presence flags and approval status, `verify_completeness` reports the experiment complete if and only if the Plan, the job configuration files, at least one run directory, the Results_File, the History_File, the Journal_File, and the Project_Log are all present; it lists every missing required file; it reports approval as granted if and only if the Approval_Status equals `approved`; and it performs no I/O.

**Validates: Requirements 1.1, 1.2, 1.4**

### Property 2: Missing required file blocks finalization

*For any* completeness result with at least one missing required file, the orchestration reports a blocked-finalization outcome identifying the missing file and exits with code `1`.

**Validates: Requirements 1.3**

### Property 3: Results reference an existing run

*For any* Results_File and set of run directory names, `validate_results` reports the best run as existing if and only if `best_run.run_id` is present and matches an existing run directory; when it does not match, the orchestration reports an invalid-reference outcome and exits `1`.

**Validates: Requirements 2.1, 2.2**

### Property 4: Primary metric must be numeric

*For any* Results_File, `validate_results` reports the Primary_Metric numeric if and only if its value is a real number (and not a boolean); when the value is missing or non-numeric, the orchestration reports an incomplete-results outcome and exits `1`.

**Validates: Requirements 2.3, 2.4**

### Property 5: Conclusions reference only verified metrics and artifacts

*For any* Results_File and recorded Linkage_Fields, `verify_references` reports every claimed metric backed if and only if it has an actual recorded value, and every Artifact_Reference verified if and only if it exists in the Linkage_Fields or on the filesystem; whenever any referenced metric or artifact cannot be verified, the experiment is not marked successful.

**Validates: Requirements 3.1, 3.2, 3.3**

### Property 6: No success without a verified artifact and a verified metric

*For any* reference-verification result, success is claimable if and only if there is at least one verified Artifact_Reference and a verified numeric Primary_Metric value.

**Validates: Requirements 3.4**

### Property 7: Results assembly populates required fields with a plan-derived rationale

*For any* Plan, runs, and Linkage_Fields, `assemble_results` produces content that confirms the presence of `best_run`, `primary_metric`, `success`, and `completed_at`; populates the Success_Assessment with a `criteria_met` boolean and a `rationale` derived from the Plan's success criteria; surfaces each referenced Run_Record's Linkage_Fields; and performs no network I/O.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 8: History completion entry is a summary appended without mutation

*For any* completion fields, `format_history_entry` produces an entry containing a timestamp, the best run reference, the Primary_Metric value, and the Success_Assessment determination, as summary records rather than full stdout/stderr logs; and the orchestration appends it to the History_File without modifying prior entries.

**Validates: Requirements 5.1, 5.2, 5.3**

### Property 9: Journal validation confirms interpretive sections and warns on missing next steps

*For any* journal text, `validate_journal` reports whether the journal contains a hypothesis assessment, key findings, interpretation, and recommended next experiments, and whether it is interpretive rather than only an execution log; when the recommended-next-experiments section is absent, it emits a documentation warning in the Output_Envelope rather than blocking.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 10: Project-log entry is inserted at the top in reverse-chronological order

*For any* existing project log and new entry, `insert_project_log_entry` places the entry at the top of the Project_Log in reverse-chronological order, and the entry includes a one-line conclusion, the best run reference, a link to the Experiment_Dir, and key metric values.

**Validates: Requirements 7.1, 7.2**

### Property 11: Project-log entry is concise and does not duplicate per-run detail

*For any* composed Project_Log_Entry, the entry is constrained to a project-level conclusion that does not duplicate the per-run detail recorded in the Results_File, the History_File, or the Journal_File (enforced by the section/length constraint).

**Validates: Requirements 7.3**

### Property 12: An existing project-log entry is updated rather than duplicated

*For any* project log that already contains an entry for the same experiment identifier, `insert_project_log_entry` updates the existing entry in place rather than adding a duplicate entry.

**Validates: Requirements 7.4**

### Property 13: Commit-candidate selection is pure and complete

*For any* experiment directory and set of produced paths, `select_commit_candidate` builds the file list from already-loaded data with no additional I/O and includes the Plan, the job configuration files, the Run_Record summaries, the Results_File, the History_File, the Journal_File, and the Project_Log.

**Validates: Requirements 8.1, 8.3**

### Property 14: Commit message surfaces experiment identity, metric, success, and linkage

*For any* commit fields, `build_commit_message` includes the experiment identifier, the Primary_Metric value, the Success_Assessment determination, and the surfaced Linkage_Fields.

**Validates: Requirements 8.2**

### Property 15: Commit candidate excludes checkpoints, caches, and raw logs

*For any* set of produced paths, `filter_commit_candidates` returns no path matching `*.pt`, `*.bin`, `*.safetensors`, or `*.ckpt`, no path within a `wandb/` cache directory, no raw `.out` or `.err` log, and no other Excluded_Artifact; and the exclusion is derived by pure logic performing no I/O.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

### Property 16: Credential files are refused and decline the mutating action

*For any* candidate file list, `scan_for_credential_files` returns every path matching a Credential_File pattern (`.env`, `*.token`, `credentials.json`); whenever any such file is present, the Finalizer refuses to stage it, reports a security-review outcome, declines the Mutating_Git_Action, and exits `1`.

**Validates: Requirements 10.1, 10.2, 10.3**

### Property 17: Mutating Git actions execute if and only if approved, proposing otherwise

*For any* Mutating_Git_Action kind (stage, commit, push) and approval status, the action reaches the `GitClient` if and only if the Approval_Status equals `approved`; otherwise the client is not invoked, the Commit_Candidate is presented as a proposal, and the task exits `1`. The Finalizer never creates a commit until the Approval_Status equals `approved`.

**Validates: Requirements 11.1, 11.2, 11.3, 11.5**

### Property 18: Read-only and local-only actions are ungated

*For any* approval status, a read-only or local-only action (reading `run.yaml`, `results.yaml`, `plan.md`, `history.md`, `journal.md`, and `project-log.md`; validating documentation; assembling results; drafting the commit message; selecting the candidate) proceeds without consulting the approval gate.

**Validates: Requirements 11.4**

### Property 19: Injected-boundary discipline

*For any* orchestration task, every Git operation, network call, and filesystem-mutating Git action passes through the single injected `GitClient`, and the pure logic performs no I/O; the `RealGitClient` is constructed only within `main()`; and under test the `FakeGitClient` performs no real Git commit, no push, and no network access, raising on any unscripted operation.

**Validates: Requirements 12.1, 12.2, 12.3, 12.4**

### Property 20: A required failed run is documented and success is not reported met

*For any* set of runs where a required run has a Run_Status of `failed`, `assess_honesty` requires the failure to be documented in the History_File and the Journal_File before finalizing and does not report the success criteria as met.

**Validates: Requirements 13.1, 13.2**

### Property 21: Unverified Hub upload blocks completion

*For any* set of Hub statuses, when a required Hub upload has an Hf_Status other than `verified`, `assess_honesty` does not mark the experiment complete and the orchestration reports an incomplete-experiment outcome.

**Validates: Requirements 13.3**

### Property 22: Partial experiments are finalized honestly

*For any* partial experiment, the Finalizer records the partial status in the Results_File and in the Success_Assessment rationale.

**Validates: Requirements 13.4**

### Property 23: Linkage is surfaced and the finalized marker never changes run status

*For any* Run_Record read during finalization, the Finalizer surfaces the Phase 5–8 Linkage_Fields in the Results_File and the commit message; on completion it writes the Finalized_Marker to the Plan; and every training Run_Status is left unchanged.

**Validates: Requirements 14.1, 14.2, 14.3**

### Property 24: Artifacts contain no secrets

*For any* configuration and environment map that include credential-like keys and values, `redact_config` drops every Credential_Key value while retaining non-credential entries, `redact_secrets` masks credential values in reported text, and none of the Results_File, the History_File, the Journal_File, the Project_Log, the commit message, or the Output_Envelope (including its error and warning text) contains any of those credential values; where a name is required, only the key name is retained.

**Validates: Requirements 15.1, 15.2, 15.3**

### Property 25: Output envelope and exit-code mapping

*For any* completed task, the stdout envelope contains the fields `status`, `message`, `data`, `errors`, and `warnings`; a verified, finalized, proposal-ready, or committed-after-approval outcome exits `0`; a decline (verification failure, missing approval, incomplete experiment, blocked finalization, or credential-file refusal) exits `1`; and a filesystem or parse error exits `2`.

**Validates: Requirements 16.1, 16.2, 16.3, 16.4**

### Property 26: Phase boundaries are respected

*For any* finalization task, the Finalizer runs no training job, submits no Slurm job, creates or finishes no W&B Run, and uploads no checkpoint to the Hugging Face Hub, confining its mutating actions to finalizing documentation, writing the Finalized_Marker, and proposing or executing an approved Commit_Candidate.

**Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5**

## Error Handling

- **Missing required file**: blocked-finalization outcome (exit `1`) identifying the missing file; no Mutating_Git_Action attempted.
- **Approval not granted**: the Commit_Candidate is presented as a proposal; the `GitClient` is never invoked for a Mutating_Git_Action (exit `1`).
- **Invalid best-run reference**: invalid-reference outcome (exit `1`); no finalization.
- **Missing or non-numeric primary metric**: incomplete-results outcome (exit `1`).
- **Unverified metric or artifact reference**: unverified-reference outcome; the experiment is not marked successful (exit `1`).
- **Credential file in the candidate**: security-review outcome; the file is refused and the Mutating_Git_Action is declined (exit `1`); the `GitClient` is never invoked.
- **Required run failed**: finalization confirms the failure is documented in `history.md` and `journal.md`; success criteria are not reported met; the experiment is finalized as partial.
- **Required Hub upload not verified** (`hf_status != verified`): incomplete-experiment outcome; the experiment is not marked complete (exit `1`).
- **Missing recommended-next-experiments section**: documentation warning in the Output_Envelope (not a block).
- **Filesystem/parse errors**: caught at the top level and returned as a structured error (exit `2`); the helper never crashes with a traceback.

## Testing Strategy

**Dual approach.** Property tests cover the pure logic across many generated inputs; unit/integration tests cover specific examples, edge cases, and orchestration wiring with a `FakeGitClient`. All test writes are confined to `tmp_path`; the example experiment under `experiments/example-lora-rank-ablation/` stays read-only; no test performs a real Git commit, push, or network I/O.

- **Tooling**: `pytest` with `PyYAML` and `Hypothesis`, run through a disposable `uv` environment per Phase 2 conventions. The target language is Python, so property tests use the Hypothesis library rather than a hand-rolled generator; the helper never implements property-based testing from scratch.
- **Property tests**: minimum 100 iterations each; each references its design property with the tag `**Feature: phase-9-finalize-git, Property N: <text>**`. Each correctness property is implemented by a single property-based test.
- **Unit/integration tests**: concrete examples (missing-file block, invalid best-run reference, non-numeric metric decline, unverified-reference decline, credential-file refusal, approval-gated commit through the `FakeGitClient`, propose-only when not approved, project-log update-not-duplicate round-trip, history append preserves prior entries, failed-run honest finalization, unverified-Hub incompleteness, `results.yaml` linkage round-trip) and orchestration wiring asserted against the `FakeGitClient`.
- **Phase-boundary examples**: a guard test asserts `finalize_experiment.py` runs no training, submits no Slurm job, creates no W&B Run, and performs no Hub upload, and that `git` via subprocess and the `RealGitClient` are reachable only within `main()`'s real-client path, so no real client is reachable without explicit injection.
