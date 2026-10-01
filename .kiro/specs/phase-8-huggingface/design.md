# Design Document

## Overview

Phase 8 adds the Hugging Face Hub publication layer on top of the Phase 5 local-execution helper (`run_local.py`), the Phase 6 Slurm submission helper (`submit_slurm.py`), and the Phase 7 W&B tracking helper (`track_wandb.py`). It is delivered as a deterministic Python helper, `publish_hf.py`, in `.agents/skills/train-llm/scripts/`, alongside the existing `initialize_run.py`, `run_local.py`, `submit_slurm.py`, and `track_wandb.py`.

The central design decision is the same strict separation between **pure logic** and **impure I/O** that Phase 6 and Phase 7 established:

- **Pure logic** functions take plain data (dicts parsed from YAML, strings, enums) and return plain data (strings, enums, dataclasses). They perform no Hugging Face Hub API call, no network, and no filesystem mutation. These functions carry the property-based and unit tests.
- **Impure I/O** passes exclusively through a single injected `HfClient` interface. Production uses a `RealHfClient` that wraps `huggingface_hub` (imported lazily); tests inject a `FakeHfClient`. No real Hub API call or network access ever occurs in tests.

All stable settings (`huggingface.namespace`, `huggingface.private`, `huggingface.push_policy`) come from `project-plan.md` frontmatter and are never re-asked. The `huggingface.namespace` value is currently the placeholder `TODO-set-before-phase-8`; the helper tolerates it by declining every mutating Hub action (exit `1`) with a clear outcome, while allowing read-only and local-only actions to proceed, and never crashes. Mutating Hub actions — creating or ensuring a repository, uploading a checkpoint or file, creating a commit or revision on the Hub, and setting repository visibility — require `approval.status == approved` in the experiment `plan.md`, the same approval gate used in Phases 5, 6, and 7. Read-only and local-only actions (reading `run.yaml`, checking a local checkpoint path, drafting a model card locally, parsing settings) are non-mutating and ungated.

A Hub failure is recorded distinctly from a training/run failure: `run.yaml` carries a separate `hf_status` field so a failed upload never flips the training `status`, while still signaling that the Experiment must not be marked complete. Generated artifacts never contain secrets, tokens, or credential values (for example `HF_TOKEN` or `HUGGINGFACEHUB_API_TOKEN`), reusing the Phase 5/6/7 names-only redaction approach. Checkpoints are large artifacts uploaded to the Hub and are never added to Git; the helper reuses the Phase 6/7 commit-candidate exclusion (`checkpoints/`, `wandb/`, `.out`/`.err`).

The helper follows the Phase 5/6/7 output contract: a JSON envelope `{status, message, data, errors, warnings}` printed to stdout, with exit codes `0` (completed, recorded, or verified), `1` (declined: approval, placeholder namespace, policy skip, unverified upload, missing prerequisite), and `2` (runtime error: filesystem/parse). W&B tracking remains in Phase 7, and no Git commits occur in Phase 8.

## Architecture

```text
                   project-plan.md (frontmatter)          experiment plan.md (approval)
                               │                                      │
                               ▼                                      ▼
        ┌─────────────────────────────────────────────────────────────────────────┐
        │                             publish_hf.py                                 │
        │                                                                           │
        │   PURE LOGIC (no I/O, fully testable)                                     │
        │   ├─ load_hf_settings(frontmatter) -> HfSettings                          │
        │   ├─ is_placeholder_namespace(namespace) -> bool                          │
        │   ├─ decide_push(policy, checkpoint_kind) -> PushDecision                 │
        │   ├─ build_repo_id(namespace, repo_name) -> str                           │
        │   ├─ build_hf_url(repo_id, revision) -> str                               │
        │   ├─ resolve_visibility(private) -> Visibility                            │
        │   ├─ guard_visibility_change(current, requested, approval) -> VisDecision │
        │   ├─ build_model_card(repo_id, kind, resolved_config) -> str              │
        │   ├─ map_hf_status(raw_state) -> HfStatus                                 │
        │   ├─ decide_mutating_action(approval, kind) -> ActionDecision             │
        │   ├─ redact_config(config) -> dict                                        │
        │   ├─ redact_secrets(text, env) -> str                                     │
        │   └─ filter_commit_candidates(paths) -> list[str]                         │
        │                                                                           │
        │   IMPURE BOUNDARY (single injection point)                                │
        │   └─ HfClient.<op>(...)                                                    │
        │        ├─ RealHfClient  (production; wraps huggingface_hub, lazy import)  │
        │        └─ FakeHfClient  (tests; scripted results, records calls)          │
        │                                                                           │
        │   ORCHESTRATION (thin; composes pure logic + HfClient)                    │
        │   ├─ verify_checkpoint(path) -> CheckpointResult        (local, read-only)│
        │   ├─ ensure_repo(client, repo_id, private, approval) -> RepoResult        │
        │   ├─ upload_checkpoint(client, repo_id, path, approval) -> UploadResult   │
        │   ├─ record_revision(client, upload) -> RevisionResult                    │
        │   ├─ verify_upload(client, repo_id, revision) -> VerifyResult             │
        │   ├─ draft_model_card(run_dir, repo_id, kind, cfg) -> CardResult  (local) │
        │   └─ write_hf_linkage(run_dir, fields) -> None                            │
        └─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
             experiments/<exp>/runs/<run-id>/run.yaml       (Hub linkage fields)
             experiments/<exp>/runs/<run-id>/MODEL_CARD.md  (Model_Card_Path)
```

### Why this split

- Property tests exercise settings loading, push-eligibility decisions, repo-id and URL construction, visibility resolution, model-card assembly, status mapping, redaction, and gating across hundreds of inputs with zero network risk.
- Integration tests use `FakeHfClient` to assert orchestration wiring and approval gating without any real repository creation, upload, or verification.
- The only code that can touch the Hub API or network is `RealHfClient`, which is never constructed in tests.

## Components and Interfaces

### HfClient (injected boundary)

Every Hugging Face Hub API call, network call, and filesystem-mutating Hub operation passes through one protocol. The orchestration never imports `huggingface_hub` directly.

```python
from dataclasses import dataclass
from typing import Protocol, Mapping

@dataclass(frozen=True)
class UploadOutcome:
    revision: str          # commit SHA or tag at which the upload landed
    repo_id: str

@dataclass(frozen=True)
class RepoInfo:
    exists: bool
    private: bool

class HfClient(Protocol):
    def repo_exists(self, *, repo_id: str) -> RepoInfo:
        """Query the Hub for a repository. Read-only."""
        ...

    def create_repo(self, *, repo_id: str, private: bool) -> RepoInfo:
        """Create/ensure a repository with the given visibility. Mutating; approval-gated."""
        ...

    def set_visibility(self, *, repo_id: str, private: bool) -> RepoInfo:
        """Change repository visibility. Mutating; approval-gated."""
        ...

    def upload_checkpoint(self, *, repo_id: str, local_path: str) -> UploadOutcome:
        """Upload a checkpoint folder/file and create a revision. Mutating; approval-gated."""
        ...

    def file_exists_at_revision(self, *, repo_id: str, revision: str) -> bool:
        """Confirm the uploaded content is locatable at the revision. Read-only."""
        ...
```

- `RealHfClient(token=None)` wraps `huggingface_hub` (`HfApi.repo_info`, `create_repo`, `update_repo_settings`/`update_repo_visibility`, `upload_folder`/`upload_file`) and is constructed **only** in `main()`. The `huggingface_hub` import is lazy so that unit and property tests never import the SDK.
- `FakeHfClient(scripted)` returns pre-seeded results keyed by operation and records every call for assertions. It raises on any unscripted operation, guaranteeing tests never leak to real I/O.

### Hugging Face settings

```python
@dataclass(frozen=True)
class HfSettings:
    namespace: str
    private: bool
    push_policy: str   # never | final_only | milestone | final_and_milestone | every_save

PLACEHOLDER_NAMESPACE = "TODO-set-before-phase-8"
VALID_POLICIES = ("never", "final_only", "milestone", "final_and_milestone", "every_save")

def load_hf_settings(frontmatter: dict) -> HfSettings:
    hf = frontmatter.get("huggingface", {}) or {}
    # private defaults to True when not declared.
    private = hf.get("private", True)
    return HfSettings(
        namespace=str(hf.get("namespace", "")),
        private=bool(private) if private is not None else True,
        push_policy=str(hf.get("push_policy", "")),
    )

def is_placeholder_namespace(namespace: str) -> bool:
    return (namespace or "").strip() == PLACEHOLDER_NAMESPACE
```

Settings are read from `project-plan.md` frontmatter at the start of every task and never prompted for. `private` defaults to `true` whenever `huggingface.private` is absent. An invalid `push_policy` is a configuration error reported before any mutating action.

### Push-eligibility decision

```python
from enum import Enum

class CheckpointKind(str, Enum):
    FINAL = "final"
    MILESTONE = "milestone"
    INTERMEDIATE = "intermediate"

@dataclass(frozen=True)
class PushDecision:
    eligible: bool
    config_error: bool = False   # unknown policy string

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
```

`decide_push` is pure and performs no I/O. An `intermediate` checkpoint is eligible only under `every_save`. When a checkpoint is ineligible, the orchestration sets `hf_status = skipped_by_policy`, invokes no mutating action, and exits `1`.

### Repository id and URL construction

```python
def build_repo_id(namespace: str, repo_name: str) -> str:
    return f"{namespace}/{repo_name}"

def build_hf_url(repo_id: str, revision: str | None = None) -> str:
    base = f"https://huggingface.co/{repo_id}"
    return f"{base}/tree/{revision}" if revision else base
```

### Visibility policy

```python
class Visibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"

class VisDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"
    DECLINE_SILENT_PUBLIC = "silent_public_blocked"

def resolve_visibility(private: bool) -> Visibility:
    return Visibility.PRIVATE if private else Visibility.PUBLIC

def guard_visibility_change(current: Visibility, requested: Visibility,
                            approval_status: str | None) -> VisDecision:
    """A private repo is never silently made public. A private->public change
    requires an explicit request whose approval status equals `approved`."""
    approved = bool(approval_status and approval_status.strip().lower() == "approved")
    if current == Visibility.PRIVATE and requested == Visibility.PUBLIC:
        return VisDecision.PROCEED if approved else VisDecision.DECLINE_SILENT_PUBLIC
    return VisDecision.PROCEED if approved else VisDecision.DECLINE_APPROVAL
```

On repository creation the visibility is set from `resolve_visibility(private)`. A private repository is never silently turned public: a public visibility change requires an explicit, approved request, otherwise it is declined.

### Status model

```python
class HfStatus(str, Enum):
    NOT_STARTED = "not_started"
    SKIPPED_BY_POLICY = "skipped_by_policy"
    UPLOADED = "uploaded"
    VERIFIED = "verified"
    UPLOAD_FAILED = "upload_failed"

_RAW_MAP = {
    "uploaded": HfStatus.UPLOADED,
    "completed": HfStatus.UPLOADED,
    "verified": HfStatus.VERIFIED,
    "located": HfStatus.VERIFIED,
    "failed": HfStatus.UPLOAD_FAILED,
    "error": HfStatus.UPLOAD_FAILED,
}

def map_hf_status(raw_state: str) -> HfStatus:
    token = (raw_state or "").strip().split()[0].lower() if raw_state and raw_state.strip() else ""
    return _RAW_MAP.get(token, HfStatus.UPLOAD_FAILED)
```

`HfStatus` is written to `run.yaml` as `hf_status`, a field **separate** from the training `status` (owned by Phase 5/6). An `upload_failed` outcome never changes the training `status`, so a failed or unverified upload stays distinguishable from a training failure, while still signaling that the Experiment must not be marked complete.

### Model card assembly

```python
def build_model_card(repo_id: str, checkpoint_kind: str, resolved_config: dict) -> str:
    """Pure assembly of a model-card markdown string. No network I/O.
    Every credential-like value is dropped before rendering."""
    safe_config = redact_config(resolved_config or {})
    lines = [
        "---",
        f"library_name: transformers",
        "---",
        f"# {repo_id}",
        "",
        f"- **Checkpoint kind:** {checkpoint_kind}",
        "",
        "## Training configuration",
        "",
        "```yaml",
        _render_yaml(safe_config),
        "```",
    ]
    return "\n".join(lines)
```

The model card includes the `Hf_Repo_Id`, the `Checkpoint_Kind`, and the redacted resolved config. It is a local-only action requiring no approval, written to the `Model_Card_Path` under the Run directory, and never contains a `Credential_Key` value.

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

`redact_config` and `redact_secrets` reuse the Phase 5/6/7 names-only approach: `HF_TOKEN`, `HUGGINGFACEHUB_API_TOKEN`, and any other `Credential_Key` value never reach the model card, `run.yaml`, or the output envelope.

### Approval gating for mutating actions

```python
class ActionDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"

MUTATING_KINDS = ("create_repo", "set_visibility", "upload", "revision")

def decide_mutating_action(approval_status: str | None, kind: str) -> ActionDecision:
    if approval_status and approval_status.strip().lower() == "approved":
        return ActionDecision.PROCEED
    return ActionDecision.DECLINE_APPROVAL
```

Every `Mutating_Hub_Action` (create/ensure repository, set visibility, upload, create revision) calls `decide_mutating_action` first; on `DECLINE_APPROVAL` the orchestration returns without touching the `HfClient`. Read-only and local-only actions (reading `run.yaml`, checking a local checkpoint path, drafting the model card, parsing settings, locating content by revision) skip the gate entirely.

### Safety filters

```python
_EXCLUDED_SUFFIX = (".out", ".err")        # raw Slurm logs
_EXCLUDED_DIRS = ("checkpoints", "wandb")  # checkpoints and caches

def filter_commit_candidates(paths: list[str]) -> list[str]:
    return [p for p in paths
            if not p.endswith(_EXCLUDED_SUFFIX)
            and not any(d in p.split("/") for d in _EXCLUDED_DIRS)]
```

Checkpoints are uploaded to the Hub through the `HfClient` and are never added to Git; `filter_commit_candidates` keeps `checkpoints/`, `wandb/`, and raw `.out`/`.err` logs out of any content marked as a commit candidate.

### CLI (orchestration entry point)

`main()` parses subcommands (`verify`, `ensure-repo`, `upload`, `verify-upload`, `card`, `publish`), constructs the `RealHfClient` **only there**, composes the pure logic with the client, writes the Hub linkage fields to `run.yaml`, and prints the output envelope with the mapped exit code. The `publish` subcommand runs the full sequence: verify checkpoint → ensure repo → upload → record revision → verify upload → draft card.

```python
def main(argv: list[str]) -> int:
    args = parse_args(argv)
    settings = load_hf_settings(read_frontmatter(args.plan_file))
    if settings.push_policy not in VALID_POLICIES:
        return emit(declined_envelope("huggingface.push_policy invalid"), code=1)
    if is_placeholder_namespace(settings.namespace) and args.is_mutating:
        return emit(declined_envelope("namespace is placeholder"), code=1)
    client = RealHfClient(token=None)  # only here; huggingface_hub imported lazily
    ...
```

## Data Models

- **HfSettings**: parsed once from `project-plan.md` frontmatter (`namespace`, `private`, `push_policy`); `private` defaults to `true`.
- **PushDecision**: pure result of `decide_push` — eligibility plus a `config_error` flag for an unknown policy.
- **CheckpointKind**: `final | milestone | intermediate`.
- **Visibility / VisDecision**: pure visibility resolution and the never-silently-public guard outcome.
- **Job_Config / Resolved_Config**: parsed from `resolved-job.yaml` (preferred) or the source job YAML; supplies the resolved parameters surfaced (redacted) in the model card.
- **RepoInfo / UploadOutcome**: the only Hub values crossing the injected boundary.
- **RepoResult / UploadResult / RevisionResult / VerifyResult / CardResult / CheckpointResult**: pure dataclasses summarizing each orchestration step for the JSON envelope.
- **Run_Record**: `run.yaml`, extended in Phase 8 with the Hub linkage fields below.

### run.yaml linkage fields

Phase 8 extends the Run_Record with Hub linkage, written only to the targeted Harness Run:

```yaml
hf_repo_id: my-namespace/skiyaki-emo-lora      # <namespace>/<repo-name>
hf_revision: 9c1f2a0b...                        # commit SHA or tag of the upload
hf_url: https://huggingface.co/my-namespace/skiyaki-emo-lora/tree/9c1f2a0b
hf_status: verified          # not_started | skipped_by_policy | uploaded | verified | upload_failed
hf_private: true             # resolved repository visibility
model_card_path: experiments/<exp>/runs/<run-id>/MODEL_CARD.md
status: succeeded            # training status — owned by Phase 5/6, never changed here
```

No secret, token, password, or credential value is ever written; environment reporting reuses the Phase 5/6/7 redaction approach (names only, credential-like keys dropped).

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Settings loading reflects the project plan with private defaulting true

*For any* `project-plan.md` frontmatter containing a `huggingface` block, the loaded `HfSettings` carry the namespace and push policy exactly as declared and issue no prompt; and `private` resolves to `true` whenever `huggingface.private` is absent and to the declared boolean otherwise.

**Validates: Requirements 1.1, 1.4**

### Property 2: Invalid push policy is a configuration error with no mutating action

*For any* push-policy string, `decide_push` reports a configuration error if and only if the policy is not one of `never`, `final_only`, `milestone`, `final_and_milestone`, or `every_save`; whenever the configuration error is reported, no `Mutating_Hub_Action` is invoked through the client.

**Validates: Requirements 1.2**

### Property 3: Placeholder-namespace tolerance

*For any* namespace value, `is_placeholder_namespace` returns true if and only if the value equals `TODO-set-before-phase-8`; when the namespace is the placeholder, every `Mutating_Hub_Action` is declined with a structured outcome and exit `1`, read-only and local-only actions still proceed, and the task completes without raising an unhandled exception.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 4: Push eligibility across the full policy × kind matrix

*For any* valid push policy and checkpoint kind, `decide_push` reports the checkpoint eligible if and only if the kind is permitted by the policy — `never` permits none; `final_only` permits only `final`; `final_and_milestone` permits `final` and `milestone`; `milestone` permits `milestone` and `final`; `every_save` permits all three — so `intermediate` is eligible only under `every_save`; and the decision performs no I/O.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

### Property 5: Ineligible checkpoints are skipped by policy

*For any* checkpoint kind that is ineligible under the resolved push policy, the orchestration sets `hf_status` to `skipped_by_policy`, invokes no `Mutating_Hub_Action` through the client, and exits `1`.

**Validates: Requirements 3.7**

### Property 6: Local checkpoint verification gates the upload

*For any* checkpoint path, verifying its existence is a read-only action that consults no approval; when the path is missing the orchestration reports a missing-checkpoint outcome and invokes no `Mutating_Hub_Action`, and when the path exists it records the path as verified and proceeds to repository verification.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 7: Repository id construction

*For any* namespace and repository name, `build_repo_id` returns `<namespace>/<repo-name>`.

**Validates: Requirements 5.1**

### Property 8: Repository existence check and approval-gated create

*For any* repository-existence result and approval status, the orchestration queries the Hub for the `Hf_Repo_Id` through the client, creates the repository through the client (with visibility set according to `Hf_Private`) if and only if the repository does not exist and the approval status equals `approved`, and otherwise — when the repository is missing and approval is not `approved` — declines creation with an approval-required outcome.

**Validates: Requirements 5.2, 5.3, 5.4**

### Property 9: Visibility policy never silently makes a private repo public

*For any* resolved visibility, a created repository is private when `Hf_Private` is `true`; and `guard_visibility_change` permits a private→public change only when it is an explicit request whose approval status equals `approved`, declining it as silent-public-blocked otherwise, so a private repository is never silently made public.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 10: Mutating Hub actions execute if and only if approved

*For any* `Mutating_Hub_Action` kind (create/ensure repository, set visibility, upload, create revision) and approval status, the action reaches the client if and only if the approval status equals `approved`; otherwise the client is not invoked for that action, an approval-required outcome is reported, and the task exits `1`.

**Validates: Requirements 7.1, 7.2, 7.5, 11.1, 11.2, 11.3**

### Property 11: Read-only and local-only actions are ungated

*For any* approval status, a read-only or local-only action (reading `run.yaml`, checking a local checkpoint path, drafting the model card, parsing settings, locating content by revision) proceeds without consulting the approval gate.

**Validates: Requirements 11.4**

### Property 12: Completed upload records repository identity and revision

*For any* completed upload returned by the client when approval equals `approved`, the namespace is not the placeholder, and the checkpoint kind is eligible, the orchestration uploads the checkpoint to the `Hf_Repo_Id` through the client, obtains the `Hf_Revision`, sets `hf_status` to `uploaded`, and records the `Hf_Repo_Id`, `Hf_Revision`, and `Hf_Url` in `run.yaml`.

**Validates: Requirements 7.3, 8.1, 8.2**

### Property 13: Upload or revision failure sets upload_failed and never changes the training status

*For any* upload that returns an error from the client or completes without a parseable revision, `hf_status` is set to `upload_failed`, the appropriate failure outcome (upload-error or revision-unavailable) is reported, and the training `status` (owned by Phase 5/6) retains its prior value, keeping a Hub failure distinct from a training failure.

**Validates: Requirements 7.4, 8.3, 9.4, 13.2, 16.5**

### Property 14: Verify-by-revision maps located to verified and unlocatable to upload_failed

*For any* recorded revision, the orchestration confirms through the client whether the uploaded checkpoint is locatable at that revision in the `Hf_Repo_Id`; when it is locatable `hf_status` is set to `verified`, and when it is not locatable `hf_status` is set to `upload_failed`, the Experiment-must-not-be-marked-complete signal is raised, and the task exits `1`.

**Validates: Requirements 9.1, 9.2, 9.3**

### Property 15: Model card contents are assembled locally without approval

*For any* repository id, checkpoint kind, and resolved config, drafting the model card is a local-only ungated action whose output contains the `Hf_Repo_Id`, the `Checkpoint_Kind`, and the resolved config, is assembled by pure logic performing no network I/O, is written to the `Model_Card_Path`, and whose path is recorded in `run.yaml`.

**Validates: Requirements 10.1, 10.2, 10.3**

### Property 16: Injected-boundary discipline

*For any* orchestration task, every Hugging Face Hub API call, network call, and filesystem-mutating Hub operation passes through the single injected client, and the pure logic performs no I/O; under test the `FakeHfClient` performs no real Hub API call and no network access, raising on any unscripted operation.

**Validates: Requirements 12.1, 12.3, 12.4**

### Property 17: run.yaml linkage completeness

*For any* publication outcome, the Run_Record contains the `hf_repo_id`, `hf_revision`, `hf_url`, `hf_status`, `hf_private`, and `model_card_path` fields, with `hf_private` equal to the resolved visibility.

**Validates: Requirements 1.3, 6.4, 10.3, 13.1**

### Property 18: Hub linkage writes are confined to the targeted run

*For any* Hub linkage write the helper performs, every written path is within the targeted Harness Run's directory (its `run.yaml` or its `Model_Card_Path`) and no write targets another Run's directory.

**Validates: Requirements 13.4**

### Property 19: Artifacts contain no secrets

*For any* configuration and environment map that include credential-like keys and values, `redact_config` drops every credential value while retaining non-credential entries, `redact_secrets` masks credential values in reported text, and none of the `run.yaml`, the model card, or the output envelope (including its error and warning text) contains any of those credential values.

**Validates: Requirements 10.4, 13.3, 14.1, 14.2, 14.3**

### Property 20: Output envelope and exit-code mapping

*For any* completed task, the stdout envelope contains the fields `status`, `message`, `data`, `errors`, and `warnings`; a successful, recorded, or verified outcome exits `0`, a decline (missing approval, placeholder namespace, policy skip, unverified upload, or missing prerequisite) exits `1`, and a filesystem or parse error exits `2`.

**Validates: Requirements 15.1, 15.2, 15.3, 15.4**

### Property 21: Commit candidates exclude logs, checkpoints, and caches, and checkpoints go to the Hub

*For any* set of produced paths, the filtered commit candidates contain no path ending in `.out` or `.err` and no path within a `checkpoints` or `wandb` directory; and a checkpoint selected for publication is routed to the Hub through the client rather than added to the commit candidates.

**Validates: Requirements 16.3, 16.4**

## Error Handling

- **Invalid push policy**: configuration-error outcome (exit `1`); no `Mutating_Hub_Action` attempted.
- **Placeholder namespace, mutating action**: declined placeholder-namespace outcome (exit `1`); the `HfClient` is never invoked for the mutating action; the helper never raises.
- **Placeholder namespace, read-only/local action**: proceeds normally (checkpoint check, model-card draft, settings read), exit `0`.
- **Ineligible checkpoint under policy**: `hf_status = skipped_by_policy`, no upload, exit `1`.
- **Missing checkpoint path**: missing-checkpoint outcome (exit `1`); no `Mutating_Hub_Action`.
- **Repository missing, not approved**: approval-required outcome (exit `1`); the repository is not created.
- **Visibility change toward public without an approved explicit request**: declined silent-public-blocked outcome (exit `1`); visibility is left unchanged.
- **Missing approval for any mutating action**: declined approval-required outcome (exit `1`); the `HfClient` is never invoked for that action.
- **Upload error from the client**: `hf_status = upload_failed`; the training `status` is left unchanged; the outcome is reported (exit `1`), not treated as a crash.
- **Upload without a parseable revision**: `hf_status = upload_failed`, revision-unavailable outcome (exit `1`).
- **Verification cannot locate the checkpoint by its revision**: `hf_status = upload_failed`, Experiment-must-not-be-marked-complete signaled (exit `1`).
- **Filesystem/parse errors**: caught at the top level and returned as a structured error (exit `2`); the helper never crashes with a traceback.

## Testing Strategy

**Dual approach.** Property tests cover the pure logic across many generated inputs; unit/integration tests cover specific examples, edge cases, and orchestration wiring with a `FakeHfClient`. All test writes are confined to `tmp_path`; the example experiment under `experiments/example-lora-rank-ablation/` stays read-only; no test performs a real Hugging Face Hub API call, upload, verification, or network I/O.

- **Tooling**: `pytest` with `PyYAML` and `Hypothesis`, run through a disposable `uv` environment per Phase 2 conventions. The target language is Python, so property tests use the Hypothesis library rather than a hand-rolled generator; the helper never implements property-based testing from scratch.
- **Property tests**: minimum 100 iterations each; each references its design property with the tag `**Feature: phase-8-huggingface, Property N: <text>**`. Each correctness property is implemented by a single property-based test.
- **Unit/integration tests**: concrete examples (placeholder decline, policy skip, repository query through the `FakeHfClient`, approval-gated create, upload-success, upload-failure keeps training status, verify-by-revision located/unlocatable, model-card round-trip, `run.yaml` linkage round-trip) and orchestration wiring asserted against the `FakeHfClient`.
- **Phase-boundary examples**: a guard test asserts `publish_hf.py` creates no W&B Run and issues no Git commit, and that the `huggingface_hub` SDK is imported and the `RealHfClient` constructed only within `main()`'s real-client path, so no real client is reachable without explicit injection.
