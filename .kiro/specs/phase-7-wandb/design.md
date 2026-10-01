# Design Document

## Overview

Phase 7 adds the Weights & Biases (W&B) experiment-tracking layer on top of the Phase 5 local-execution helper (`run_local.py`) and the Phase 6 Slurm submission helper (`submit_slurm.py`). It is delivered as a deterministic Python helper, `track_wandb.py`, in `.agents/skills/train-llm/scripts/`, alongside the existing `initialize_run.py`, `run_local.py`, and `submit_slurm.py`.

The central design decision is the same strict separation between **pure logic** and **impure I/O** that Phase 6 established:

- **Pure logic** functions take plain data (dicts parsed from YAML, strings, enums) and return plain data (strings, enums, dataclasses). They perform no W&B API call, no network, and no filesystem mutation. These functions carry the property-based and unit tests.
- **Impure I/O** passes exclusively through a single injected `WandbClient` interface. Production uses a `RealWandbClient` that wraps the real `wandb` SDK; tests inject a `FakeWandbClient`. No real W&B API call or network access ever occurs in tests.

All stable settings (`wandb.entity`, `wandb.project`, `wandb.mode`, `wandb.keep_local_data`) come from `project-plan.md` frontmatter and are never re-asked. The `wandb.entity` value is currently the placeholder `TODO-set-before-phase-7`; the helper tolerates it by declining the online mutating action (exit `1`) or by downgrading to offline operation, and never crashes. Mutating W&B actions (creating a W&B Run, finishing a W&B Run, syncing a local Run to the web) require `approval.status == approved` in the experiment `plan.md`; read-only and local-only actions (reading `run.yaml`, parsing a W&B URL from log text, inspecting the local W&B directory) are non-mutating and ungated.

A W&B failure is recorded distinctly from a training/run failure: `run.yaml` carries a separate `wandb_status` field so a failed sync never flips the training `status`. Generated artifacts never contain secrets, tokens, or credential values (for example `WANDB_API_KEY`), reusing the Phase 5/6 names-only redaction approach.

The helper follows the Phase 5/6 output contract: a JSON envelope `{status, message, data, errors, warnings}` printed to stdout, with exit codes `0` (completed or recorded), `1` (declined: approval, placeholder entity in online mode, missing prerequisite), and `2` (runtime error: filesystem/parse). Phase 8 Hugging Face Hub uploads are out of scope, and no Git commits occur in Phase 7.

## Architecture

```text
                   project-plan.md (frontmatter)          experiment plan.md (approval)
                               │                                      │
                               ▼                                      ▼
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                            track_wandb.py                                 │
        │                                                                           │
        │   PURE LOGIC (no I/O, fully testable)                                     │
        │   ├─ load_wandb_settings(frontmatter) -> WandbSettings                    │
        │   ├─ is_placeholder_entity(entity) -> bool                                │
        │   ├─ resolve_mode(settings, entity) -> ModeDecision                       │
        │   ├─ resolve_group(experiment_id, job) -> str                            │
        │   ├─ resolve_tags(job) -> list[str]                                       │
        │   ├─ build_run_config(resolved_job, env) -> dict  (credentials dropped)   │
        │   ├─ local_wandb_dir(experiment_id, run_id) -> str                        │
        │   ├─ parse_wandb_url(log_text) -> str | None                              │
        │   ├─ extract_run_id_from_url(url) -> str | None                           │
        │   ├─ map_sync_state(raw_state, mode) -> WandbStatus                       │
        │   ├─ decide_mutating_action(approval, kind) -> ActionDecision             │
        │   ├─ redact_secrets(text, env) -> str                                     │
        │   ├─ redact_config(config) -> dict                                        │
        │   └─ filter_commit_candidates(paths) -> list[str]                         │
        │                                                                           │
        │   IMPURE BOUNDARY (single injection point)                                │
        │   └─ WandbClient.<op>(...)                                                 │
        │        ├─ RealWandbClient  (production; wraps the wandb SDK)              │
        │        └─ FakeWandbClient  (tests; scripted results, records calls)       │
        │                                                                           │
        │   ORCHESTRATION (thin; composes pure logic + WandbClient)                 │
        │   ├─ create_run(client, run_dir, settings, job, approval) -> RunResult    │
        │   ├─ resume_run(client, run_dir, settings) -> ResumeResult                │
        │   ├─ record_config(client, run_dir, job, env) -> ConfigResult             │
        │   ├─ assign_group_tags(client, run_dir, exp_id, job) -> GroupResult       │
        │   ├─ check_sync(client, run_dir, settings) -> SyncResult                  │
        │   ├─ compare_runs(client, group) -> CompareResult                         │
        │   └─ write_wandb_linkage(run_dir, fields) -> None                         │
        └─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
             experiments/<exp>/runs/<run-id>/run.yaml   (W&B linkage fields)
             experiments/<exp>/runs/<run-id>/wandb/      (Local_Wandb_Dir)
```

### Why this split

- Property tests exercise settings loading, mode resolution, group/tag derivation, config redaction, URL parsing, status mapping, and gating across hundreds of inputs with zero network risk.
- Integration tests use `FakeWandbClient` to assert orchestration wiring and approval gating without any real W&B Run creation or sync.
- The only code that can touch the W&B API or network is `RealWandbClient`, which is never constructed in tests.

## Components and Interfaces

### WandbClient (injected boundary)

Every W&B API call, network call, and filesystem-mutating W&B operation passes through one protocol. The orchestration never imports `wandb` directly.

```python
from dataclasses import dataclass
from typing import Protocol, Mapping, Sequence

@dataclass(frozen=True)
class CreatedRun:
    run_id: str
    url: str

@dataclass(frozen=True)
class RunMetrics:
    run_id: str
    summary: Mapping[str, float]

class WandbClient(Protocol):
    def create_run(self, *, entity: str, project: str, group: str,
                   tags: Sequence[str], config: Mapping[str, object],
                   mode: str, dir: str) -> CreatedRun:
        """Create a W&B Run. Mutating; approval-gated."""
        ...

    def resume_run(self, *, run_id: str, project: str, entity: str,
                   mode: str, dir: str) -> CreatedRun:
        """Resume an existing W&B Run by id. Mutating; approval-gated."""
        ...

    def update_config(self, *, run_id: str, config: Mapping[str, object]) -> None:
        """Record resolved config onto the Run. Mutating; approval-gated."""
        ...

    def finish_run(self, *, run_id: str) -> None:
        """Finish a W&B Run. Mutating; approval-gated."""
        ...

    def sync_state(self, *, run_id: str, dir: str) -> str:
        """Return the raw sync state for the Run. Mutating when it triggers
        an upload; approval-gated."""
        ...

    def fetch_group_metrics(self, *, entity: str, project: str,
                            group: str) -> list[RunMetrics]:
        """Read metrics for every Run in a group. Read-only."""
        ...
```

- `RealWandbClient(entity, project)` wraps `wandb.init`, `run.config.update`, `run.finish`, the W&B sync/public API, and is constructed **only** in `main()`.
- `FakeWandbClient(scripted)` returns pre-seeded results keyed by operation and records every call for assertions. It raises on any unscripted operation, guaranteeing tests never leak to real I/O.

### W&B settings

```python
@dataclass(frozen=True)
class WandbSettings:
    entity: str
    project: str
    mode: str            # "online" | "offline" | "disabled"
    keep_local_data: bool

PLACEHOLDER_ENTITY = "TODO-set-before-phase-7"
VALID_MODES = ("online", "offline", "disabled")

def load_wandb_settings(frontmatter: dict) -> WandbSettings:
    w = frontmatter.get("wandb", {}) or {}
    return WandbSettings(
        entity=str(w.get("entity", "")),
        project=str(w.get("project", "")),
        mode=str(w.get("mode", "")),
        keep_local_data=bool(w.get("keep_local_data", False)),
    )

def is_placeholder_entity(entity: str) -> bool:
    return (entity or "").strip() == PLACEHOLDER_ENTITY
```

Settings are read from `project-plan.md` frontmatter at the start of every task and never prompted for. An invalid `mode` is a configuration error reported before any Run is created.

### Mode resolution and placeholder tolerance

```python
from enum import Enum

class EffectiveMode(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DISABLED = "disabled"

@dataclass(frozen=True)
class ModeDecision:
    effective: EffectiveMode
    config_error: bool = False      # invalid declared mode
    placeholder_online_declined: bool = False  # placeholder + online => decline

def resolve_mode(settings: WandbSettings, entity: str) -> ModeDecision:
    if settings.mode not in VALID_MODES:
        return ModeDecision(EffectiveMode.DISABLED, config_error=True)
    if settings.mode == "disabled":
        return ModeDecision(EffectiveMode.DISABLED)
    if is_placeholder_entity(entity):
        # Online cannot proceed with an unconfigured entity; the orchestration
        # declines (exit 1). Offline/local operation downgrades gracefully.
        if settings.mode == "online":
            return ModeDecision(EffectiveMode.OFFLINE,
                                placeholder_online_declined=True)
        return ModeDecision(EffectiveMode.OFFLINE)
    return ModeDecision(EffectiveMode(settings.mode))
```

- `disabled` short-circuits every mutating action and yields `wandb_status = not_started`.
- An invalid declared mode is a configuration error (no Run created).
- A placeholder entity in `online` mode causes the online mutating action to be declined with exit `1`; where offline/local operation is possible, the mode is downgraded to offline and `wandb_status = offline`. The helper never raises on the placeholder.

### Group and tag resolution

```python
def resolve_group(experiment_id: str, job: dict) -> str:
    # All Runs of one experiment share one group so they are comparable in a
    # single W&B view. An explicit job-level group override wins when present.
    declared = (job.get("wandb") or {}).get("group")
    return str(declared) if declared else str(experiment_id)

def resolve_tags(job: dict) -> list[str]:
    tags: list[str] = []
    for t in (job.get("wandb") or {}).get("tags", []) or []:
        tags.append(str(t))
    # Derive stable tags from the job config (e.g. method, rank) for sweeps.
    for key in ("method", "lora_rank", "model"):
        if key in job:
            tags.append(f"{key}:{job[key]}")
    # Deterministic, de-duplicated order.
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
```

Group resolution is a pure function of the experiment id (with an optional declared override), so every Run of the same experiment resolves to the same group value regardless of order.

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
        if isinstance(v, dict):
            out[k] = redact_config(v)
        else:
            out[k] = v
    return out

def build_run_config(resolved_job: dict, env: dict) -> dict:
    merged = dict(resolved_job or {})
    # Only non-credential environment hints are surfaced, by name.
    merged["_env_keys"] = [k for k in (env or {}) if not _is_credential_key(k)]
    return redact_config(merged)

def redact_secrets(text: str, env: dict) -> str:
    out = text or ""
    for k, v in (env or {}).items():
        if _is_credential_key(k) and v:
            out = out.replace(str(v), f"<{k}>")
    return out
```

`build_run_config` reuses the Phase 5/6 names-only approach: the W&B Run config carries resolved job parameters with every credential value stripped. `WANDB_API_KEY` and any other `Credential_Key` value never reach the Run config, `run.yaml`, or the output envelope.

### Local W&B directory

```python
def local_wandb_dir(experiment_id: str, run_id: str) -> str:
    return f"experiments/{experiment_id}/runs/{run_id}/wandb"
```

The directory is created before the Run writes local data. When `keep_local_data` is true, the directory is retained after a sync. All local W&B writes are confined to this directory and to `run.yaml`.

### Status model

```python
class WandbStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    SYNCED = "synced"
    SYNC_FAILED = "sync_failed"
    OFFLINE = "offline"

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
    token = (raw_state or "").strip().split()[0].lower() if raw_state and raw_state.strip() else ""
    return _SYNC_MAP.get(token, WandbStatus.SYNC_FAILED)
```

`WandbStatus` is written to `run.yaml` as `wandb_status`, a field **separate** from the training `status` (owned by Phase 5/6). A `sync_failed` outcome never changes the training `status`, so a failed sync stays distinguishable from a training failure.

### W&B URL parsing from logs

```python
_WANDB_URL_PATTERN = re.compile(r"https?://(?:[\w.-]*\.)?wandb\.ai/[^\s'\"<>]+")
_RUN_ID_PATTERN = re.compile(r"/runs/([^/?#\s]+)")

def parse_wandb_url(log_text: str) -> str | None:
    m = _WANDB_URL_PATTERN.search(log_text or "")
    return m.group(0) if m else None

def extract_run_id_from_url(url: str) -> str | None:
    m = _RUN_ID_PATTERN.search(url or "")
    return m.group(1) if m else None
```

Parsing is a read-only action requiring no approval. When no URL is present, the recorded `wandb_run_id` and `wandb_url` fields are left unchanged.

### Approval gating for mutating actions

```python
class ActionDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"

MUTATING_KINDS = ("create", "resume", "config", "finish", "sync")

def decide_mutating_action(approval_status: str | None, kind: str) -> ActionDecision:
    if approval_status and approval_status.strip().lower() == "approved":
        return ActionDecision.PROCEED
    return ActionDecision.DECLINE_APPROVAL
```

Every `Mutating_Wandb_Action` (create, resume, config update, finish, sync) calls `decide_mutating_action` first; on `DECLINE_APPROVAL` the orchestration returns without touching the `WandbClient`. Read-only and local-only actions (reading `run.yaml`, parsing a URL, inspecting the local directory, comparing already-recorded metrics) skip the gate entirely.

### Git SHA recording

```python
UNKNOWN_SHA = "unknown"

def record_git_sha(runner_result: CommandResult | None) -> tuple[str, list[str]]:
    """Pure mapping of a `git rev-parse HEAD` result to (sha, warnings).
    The subprocess itself is the one small impurity, done in the orchestration."""
    if runner_result and runner_result.exit_code == 0 and runner_result.stdout.strip():
        return runner_result.stdout.strip(), []
    return UNKNOWN_SHA, ["git_sha_unknown: could not determine current commit"]
```

The current `git_sha` is written to `run.yaml`. If it cannot be determined, the `unknown` marker is recorded and a warning is added to the output envelope.

### Safety filters

```python
_EXCLUDED_SUFFIX = (".out", ".err")        # raw Slurm logs
_EXCLUDED_DIRS = ("checkpoints", "wandb")  # caches and checkpoints

def filter_commit_candidates(paths: list[str]) -> list[str]:
    return [p for p in paths
            if not p.endswith(_EXCLUDED_SUFFIX)
            and not any(d in p.split("/") for d in _EXCLUDED_DIRS)]
```

### CLI (orchestration entry point)

`main()` parses subcommands (`create`, `resume`, `config`, `sync`, `compare`), constructs the `RealWandbClient` **only there**, composes the pure logic with the client, writes the W&B linkage fields to `run.yaml`, and prints the output envelope with the mapped exit code.

```python
def main(argv: list[str]) -> int:
    args = parse_args(argv)
    settings = load_wandb_settings(read_frontmatter(args.plan_file))
    mode = resolve_mode(settings, settings.entity)
    if mode.config_error:
        return emit(declined_envelope("wandb.mode invalid"), code=1)
    client = RealWandbClient(settings.entity, settings.project)  # only here
    ...
```

## Data Models

- **WandbSettings**: parsed once from `project-plan.md` frontmatter (`entity`, `project`, `mode`, `keep_local_data`).
- **ModeDecision**: pure result of `resolve_mode` — the effective mode plus `config_error` / `placeholder_online_declined` flags.
- **Job_Config**: parsed from `resolved-job.yaml` (preferred) or the source job YAML; supplies group/tag hints and the resolved parameters that become the Run config.
- **CreatedRun / RunMetrics**: the only W&B values crossing the injected boundary.
- **RunResult / ResumeResult / ConfigResult / GroupResult / SyncResult / CompareResult**: pure dataclasses summarizing each orchestration step for the JSON envelope.
- **Run_Record**: `run.yaml`, extended in Phase 7 with the W&B linkage fields below.

### run.yaml linkage fields

Phase 7 extends the Run_Record with W&B linkage, written only to the targeted Harness Run:

```yaml
wandb_run_id: 3kf9a2bq         # from create/resume, or parsed from logs
wandb_url: https://wandb.ai/<entity>/<project>/runs/3kf9a2bq
wandb_group: example-lora-rank-ablation
wandb_tags: [method:lora, lora_rank:16]
wandb_status: running          # not_started | running | synced | sync_failed | offline
wandb_mode: online             # resolved mode recorded for provenance
git_sha: 1a2b3c4d...           # or "unknown" when it cannot be determined
status: succeeded              # training status — owned by Phase 5/6, never changed here
```

No secret, token, password, or credential value is ever written; environment reporting reuses the Phase 5/6 redaction approach (names only, credential-like keys dropped).

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Settings loading reflects the project plan

*For any* `project-plan.md` frontmatter containing a `wandb` block, the loaded `WandbSettings` carry the entity, project, mode, and `keep_local_data` values exactly as declared, and no prompt is issued.

**Validates: Requirements 1.1**

### Property 2: Invalid mode is a configuration error with no run created

*For any* declared mode string, `resolve_mode` reports a configuration error if and only if the mode is not one of `online`, `offline`, or `disabled`; whenever the configuration error is reported, no W&B Run is created through the client.

**Validates: Requirements 1.2**

### Property 3: Disabled mode performs no mutating action

*For any* task invoked while the resolved mode is `disabled`, the `wandb_status` is `not_started` and the client records zero mutating W&B operations.

**Validates: Requirements 1.3**

### Property 4: Placeholder-entity tolerance

*For any* run with the placeholder entity `TODO-set-before-phase-7`, `is_placeholder_entity` returns true; when the declared mode is `online` the online mutating action is declined (exit `1`) and no Run is created; when offline or local operation is possible the mode downgrades to offline with `wandb_status = offline`; and in every case the task completes with a structured envelope rather than raising an unhandled exception.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 5: Run creation records identity and sets running status

*For any* created W&B Run returned by the client when the approval status equals `approved` and the entity is not the placeholder, the orchestration invokes `create_run` with the configured entity and project, records the returned `wandb_run_id` and `wandb_url` in `run.yaml`, and sets `wandb_status` to `running`.

**Validates: Requirements 3.2, 3.3**

### Property 6: Resume reuses the recorded run id without creating a new run

*For any* Run that records a `wandb_run_id`, a resume calls the client to resume exactly that id, creates no new Run, and leaves the recorded `wandb_run_id` and `wandb_url` unchanged; *for any* Run with no recorded id, a resume reports resume-not-possible and creates no Run.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 7: Runs of one experiment share a group

*For any* two Runs resolved for the same experiment id, `resolve_group` returns the same group value regardless of order, so the Runs are comparable within a single W&B group.

**Validates: Requirements 5.1, 5.4**

### Property 8: Tag derivation is deterministic

*For any* job configuration, `resolve_tags` produces the same de-duplicated tag list on repeated evaluation, reflecting the declared and config-derived tags that are then applied to the W&B Run.

**Validates: Requirements 5.2**

### Property 9: Resolved config is recorded through the client with credentials dropped

*For any* resolved job and environment map containing credential-like keys, the config recorded through the client contains none of those credential values, and the config update is routed through the injected client.

**Validates: Requirements 6.1, 6.3**

### Property 10: Git SHA mapping with unknown fallback

*For any* `git rev-parse` result, a successful non-empty result yields that SHA with no warning, and any failing or empty result yields the `unknown` marker together with a non-empty warning in the output envelope.

**Validates: Requirements 6.2, 6.4**

### Property 11: Local W&B directory path rule

*For any* experiment id and run id, `local_wandb_dir` equals `experiments/<experiment-id>/runs/<run-id>/wandb`.

**Validates: Requirements 7.1**

### Property 12: W&B writes are confined to the run directory

*For any* W&B linkage write the helper performs, every written path is either within the Run's `Local_Wandb_Dir` or is that Run's `run.yaml`, and no write targets another Run's directory.

**Validates: Requirements 7.4, 13.4**

### Property 13: Comparison is scoped to one group and reports every run

*For any* group whose metrics the client returns, the comparison fetches metrics for that single group through the client, and the `data` section of the envelope contains each compared Run's `wandb_run_id` together with its metric values.

**Validates: Requirements 8.1, 8.2**

### Property 14: Sync-state mapping is total and mode-aware

*For any* raw sync state and resolved mode, `map_sync_state` returns `offline` when the mode is offline, `not_started` when disabled, `synced` for a completed-upload state, `running` for an in-progress state, and `sync_failed` for a failed or unrecognized state — always a defined `WandbStatus`.

**Validates: Requirements 9.2, 9.4**

### Property 15: W&B status is recorded distinctly and never changes training status

*For any* W&B outcome, `wandb_status` is written to `run.yaml` as a field separate from the training `status`; when the sync state indicates failure, `wandb_status` is set to `sync_failed` while the training `status` retains its prior value.

**Validates: Requirements 9.3, 9.5, 13.2**

### Property 16: W&B URL parse/extract round-trip

*For any* run id embedded in a `wandb.ai/.../runs/<id>` URL within surrounding log text, parsing the URL and extracting the run id recovers that id; *for any* log text containing no W&B URL, parsing yields no URL and the recorded `wandb_run_id` and `wandb_url` fields are left unchanged.

**Validates: Requirements 10.2, 10.3**

### Property 17: Mutating actions execute if and only if approved

*For any* Mutating_Wandb_Action kind (create, resume, config, finish, sync) and approval status, the action reaches the client if and only if the approval status equals `approved`; otherwise the client is not invoked for that action and an approval-required outcome is reported.

**Validates: Requirements 3.1, 3.4, 11.1, 11.2, 11.3**

### Property 18: Read-only actions are ungated

*For any* approval status, a read-only or local-only action (reading `run.yaml`, parsing a W&B URL from logs, inspecting the local W&B directory) proceeds without consulting the approval gate.

**Validates: Requirements 10.1, 11.4**

### Property 19: Injected-boundary discipline

*For any* orchestration task, every W&B API call, network call, filesystem-mutating W&B operation, and metric read passes through the single injected client; under test the `FakeWandbClient` performs no real W&B API call and no network access, raising on any unscripted operation.

**Validates: Requirements 8.4, 9.1, 12.1, 12.3**

### Property 20: run.yaml linkage completeness

*For any* create or resume outcome, the Run_Record contains the `wandb_run_id`, `wandb_url`, `wandb_group`, `wandb_tags`, `wandb_status`, `git_sha`, and `wandb_mode` fields.

**Validates: Requirements 1.4, 5.3, 13.1**

### Property 21: Artifacts contain no secrets

*For any* environment map and configuration that include credential-like keys and values, neither the written `run.yaml` nor the output envelope (including its error and warning text) contains any of those credential values.

**Validates: Requirements 13.3, 14.1, 14.2, 14.3**

### Property 22: Output envelope and exit-code mapping

*For any* completed task, the stdout envelope contains the fields `status`, `message`, `data`, `errors`, and `warnings`; a successful or recorded outcome exits `0`, a decline (missing approval, placeholder entity in online mode, or missing prerequisite) exits `1`, and a filesystem or parse error exits `2`.

**Validates: Requirements 15.1, 15.2, 15.3, 15.4**

### Property 23: Commit candidates exclude logs, checkpoints, and caches

*For any* set of produced paths, the filtered commit candidates contain no path ending in `.out` or `.err` and no path within a `checkpoints` or `wandb` directory.

**Validates: Requirements 16.3**

## Error Handling

- **Invalid W&B mode**: configuration-error outcome (exit `1`); no Run created.
- **Placeholder entity in online mode**: declined placeholder-entity outcome (exit `1`); no Run created.
- **Placeholder entity, offline/local possible**: downgraded to offline, `wandb_status = offline`, exit `0`; never raises.
- **Missing approval for a mutating action**: declined approval-required outcome (exit `1`); the `WandbClient` is never invoked for that action.
- **Resume with no recorded `wandb_run_id`**: resume-not-possible outcome (exit `1`); no new Run created.
- **Git SHA undeterminable**: `unknown` marker recorded, warning added; the task still completes.
- **Sync failure**: `wandb_status = sync_failed` recorded; the training `status` is left unchanged (exit `0`, the sync outcome is reported, not treated as a crash).
- **Empty comparison group**: empty-comparison outcome reported in the envelope (exit `0`).
- **Filesystem/parse errors**: caught at the top level and returned as a structured error (exit `2`); the helper never crashes with a traceback.

## Testing Strategy

**Dual approach.** Property tests cover the pure logic across many generated inputs; unit/integration tests cover specific examples, edge cases, and orchestration wiring with a `FakeWandbClient`. All test writes are confined to `tmp_path`; the example experiment under `experiments/example-lora-rank-ablation/` stays read-only; no test performs a real W&B API call, sync, or network I/O.

- **Tooling**: `pytest` with `PyYAML` and `Hypothesis`, run through a disposable `uv` environment per Phase 2 conventions. The target language is Python, so property tests use the Hypothesis library rather than a hand-rolled generator.
- **Property tests**: minimum 100 iterations each; each references its design property with the tag `**Feature: phase-7-wandb, Property N: <text>**`. Each correctness property is implemented by a single property-based test.
- **Unit/integration tests**: concrete examples (placeholder decline, resume-not-possible, empty comparison, invalid mode), the `run.yaml` round-trip, and orchestration wiring asserted against the `FakeWandbClient`.
- **Injection discipline**: unit and property tests never construct `RealWandbClient`; a guard test asserts the `wandb` SDK is only imported/constructed within `main()`'s real-client path, so no real client is reachable without explicit injection.
