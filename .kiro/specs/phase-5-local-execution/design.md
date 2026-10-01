# Design Document — Phase 5: Local Lightweight Job Execution

## Overview

Phase 5 adds a local execution layer on top of the existing `initialize_run.py` helper. It is implemented as a single new deterministic helper, `run_local.py`, placed alongside `validate_job.py` and `initialize_run.py` in `.agents/skills/train-llm/scripts/`. The helper follows the established script contract: it accepts explicit paths, emits structured JSON, never imports project `src/`, and confines all writes to a provided run directory.

The design separates **pure decision logic** (approval gating, Slurm classification, environment detection, command construction, status mapping, timeout parsing, history formatting, redaction, write-path planning) from a **single thin impure step** that spawns the subprocess, captures output, and enforces the timeout. This split lets property-based tests cover the logic exhaustively while a small number of integration tests exercise the one subprocess path with a tiny CPU entrypoint fixture under `tmp_path`.

### Composition with `initialize_run.py`

`run_local.py` does not create the run directory, `run.yaml`, or `resolved-job.yaml`. Those are produced by `initialize_run.py`, which writes `status: initialized`. `run_local.py` consumes an existing run directory, reads `resolved-job.yaml` for the configuration, and updates `run.yaml` through the Phase 5 lifecycle. Because the roadmap (section 18) vocabulary differs from the initializer's, Phase 5 normalizes the on-disk `initialized` to the lifecycle state `created` when it reads, and writes the roadmap statuses (`running`, `succeeded`, `failed`, `timed_out`, `cancelled`) on update. The initializer stays untouched.

### Scope boundaries (hard)

- GPU jobs and CPU-heavy jobs are **hard-rejected**: classified as Slurm-required, recorded as a `deferred` outcome pointing to Phase 6, and **never** spawned locally.
- No live W&B API calls; W&B URLs are only parsed from captured log text.
- No Hugging Face Hub uploads, no Git operations, no network calls.
- All filesystem writes are confined to the provided run directory (plus the experiment `history.md` append).

## Architecture

```
                     plan.md (approval.status)
                              │
                              ▼
          ┌───────────────────────────────────────┐
          │             run_local.py               │
          │                                         │
          │  ┌───────────── PURE LOGIC ──────────┐  │
          │  │ decide_approval(approval_status)  │  │  Req 1
          │  │ classify_execution(resources)     │  │  Req 2
          │  │ detect_environment(markers)       │  │  Req 3
          │  │ build_command(env, job, run_dir)  │  │  Req 4,5
          │  │ plan_writes(job, run_dir)         │  │  Req 7.3
          │  │ parse_timeout(resources.time)     │  │  Req 10.1
          │  │ map_status(outcome, exit_code)    │  │  Req 8
          │  │ normalize_status(on_disk_status)  │  │  Req 8.6
          │  │ parse_wandb_url(log_text)         │  │  Req 7.5
          │  │ format_history_entry(fields)      │  │  Req 11
          │  │ redact_environment(env_map)       │  │  Req 12
          │  └───────────────────────────────────┘  │
          │                   │                      │
          │                   ▼                      │
          │  ┌────────── IMPURE SHELL ───────────┐   │
          │  │ run_process(command, run_dir,     │   │  Req 7,8,10
          │  │   timeout) → stdout.log/stderr.log│   │
          │  └───────────────────────────────────┘   │
          │                   │                      │
          │                   ▼                      │
          │  update run.yaml  +  append history.md   │  Req 8,9,11
          └───────────────────────────────────────┘
```

### Control flow

1. **Load**: Read `resolved-job.yaml` from the run directory and `approval.status` from the experiment `plan.md`.
2. **Approval gate** (`decide_approval`): if not `approved`, decline without spawning.
3. **Slurm classification** (`classify_execution`): if Slurm-required, record `deferred`, append history, stop.
4. **Entrypoint check**: if entrypoint missing, record `failed` with reason, append history, stop.
5. **Environment detection** (`detect_environment`): choose conda → uv → venv → system.
6. **Command construction** (`build_command`): serialize parameters per `config_style`; write JSON/YAML param files inside the run directory when needed.
7. **Timeout** (`parse_timeout`): derive seconds from `resources.time` or default.
8. **Execute** (`run_process`): set status `running` + `started_at`, spawn, capture streams, enforce timeout.
9. **Finalize** (`map_status`): map outcome to terminal status, parse W&B URL, redact env, update `run.yaml`, append `history.md`.

## Components and Interfaces

All functions below are expressed in Python. Pure functions take plain data (dicts, strings) and return plain data, with no I/O.

### Decision records

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ExecDecision(str, Enum):
    PROCEED = "proceed"          # eligible local job
    DECLINE_APPROVAL = "approval_required"
    DECLINE_MISSING_APPROVAL = "missing_approval"
    DEFER_SLURM = "deferred"     # GPU / CPU-heavy -> Phase 6
    DECLINE_CONFIG_STYLE = "unsupported_config_style"


class EnvManager(str, Enum):
    CONDA = "conda"
    UV = "uv"
    VENV = "venv"
    SYSTEM = "system"


@dataclass
class EnvMarkers:
    """Filesystem facts used for deterministic environment detection."""
    conda_active: bool = False
    conda_manifest: bool = False     # environment.yaml / .yml present
    conda_env_name: Optional[str] = None
    uv_project: bool = False         # pyproject.toml + uv.lock present
    uv_available: bool = False       # `uv` on PATH
    virtual_env: Optional[str] = None  # VIRTUAL_ENV or detected venv dir


@dataclass
class ProcessOutcome:
    kind: str          # "exited" | "timeout" | "cancelled" | "prep_error"
    exit_code: Optional[int]
    elapsed_seconds: float = 0.0
    reason: Optional[str] = None
```

### Pure logic interfaces

```python
def decide_approval(approval_status: Optional[str]) -> ExecDecision:
    """Req 1. approved -> PROCEED; a present-but-not-approved -> DECLINE_APPROVAL;
    None/missing -> DECLINE_MISSING_APPROVAL."""


def estimate_cpu_hours(cpus: int, time_str: Optional[str]) -> float:
    """Req 2. cpus * hours derived from HH:MM:SS (default when absent)."""


def classify_execution(resources: dict) -> ExecDecision:
    """Req 2. gpus>0 OR cpu_hours>4 -> DEFER_SLURM; else PROCEED."""


def detect_environment(markers: EnvMarkers) -> EnvManager:
    """Req 3. Priority conda > uv > venv > system."""


def activation_prefix(manager: EnvManager, markers: EnvMarkers) -> list[str]:
    """Req 3. e.g. ["conda", "run", "-n", name], ["uv", "run"], venv python, or []."""


def serialize_parameters(params: dict, config_style: str,
                         param_file_path: Optional[str]) -> list[str]:
    """Req 4,5,8. Returns argv tokens for argument/hydra, or ["--config", path]
    for json/yaml. Raises UnsupportedConfigStyle for unknown styles."""


def build_command(env_prefix: list[str], entrypoint: str,
                  param_tokens: list[str]) -> list[str]:
    """Req 4.1,5. [*env_prefix, "python", entrypoint, *param_tokens]."""


def plan_writes(job_config: dict, run_dir: str) -> list[str]:
    """Req 7.3. All paths run_local will write (logs + optional param file),
    each guaranteed under run_dir."""


def parse_timeout(resources: dict, default_seconds: int) -> int:
    """Req 10.1. HH:MM:SS -> seconds, or default when absent."""


def map_status(outcome: ProcessOutcome) -> RunStatus:
    """Req 8. exited/0 -> SUCCEEDED; exited/nonzero -> FAILED;
    timeout -> TIMED_OUT; cancelled -> CANCELLED; prep_error -> FAILED."""


def normalize_status(on_disk_status: str) -> RunStatus:
    """Req 8.6. 'initialized' -> CREATED; 'completed' -> SUCCEEDED; else pass-through
    when already a valid RunStatus."""


def parse_wandb_url(log_text: str) -> Optional[str]:
    """Req 7.5. Extract a wandb.ai run URL from text, else None. No network."""


def format_history_entry(run_id: str, job_ref: str, status: RunStatus,
                         timestamp: str, exit_code: Optional[int],
                         wandb_url: Optional[str]) -> str:
    """Req 11. Markdown entry including run_id and status; adds exit_code and
    wandb_url for succeeded runs when present."""


def redact_environment(env_map: dict) -> dict:
    """Req 12. Drop values for credential-like keys (TOKEN/KEY/SECRET/PASSWORD/
    WANDB_API_KEY/HF_TOKEN...), keeping only safe names/values."""
```

### Impure shell interface

```python
def run_process(command: list[str], run_dir: str, timeout_seconds: int,
                child_env: dict, cwd: str) -> ProcessOutcome:
    """Req 7,8,10. The ONLY impure execution step. Spawns the command with
    subprocess, streams stdout -> run_dir/logs/stdout.log and stderr ->
    run_dir/logs/stderr.log, enforces timeout_seconds, returns a ProcessOutcome.
    Never raises on child failure; maps SIGINT/SIGTERM to a cancelled outcome
    and timeout to a timeout outcome."""


def execute(run_dir: str, plan_path: str, workspace_root: str,
            default_timeout: int) -> dict:
    """Top-level orchestration. Returns the JSON result (status, decision,
    run_status, created_files, errors, warnings). Writes run.yaml + history.md."""
```

## Data Models

### `run.yaml` fields written by Phase 5

Phase 5 updates the record created by `initialize_run.py`. It preserves the initializer's fields and adds/updates:

```yaml
status: running | succeeded | failed | timed_out | cancelled   # roadmap lifecycle
started_at: 2025-01-15T14:25:45          # set at execution start
completed_at: 2025-01-15T14:26:03        # set at terminal outcome
exit_code: 0                              # process exit code (null for prep errors with set reason)
command: "conda run -n ml python src/smoke.py --epochs 1"   # reproducibility
error_summary: "Entrypoint not found: src/missing.py"       # failed/deferred reasons
wandb_url: https://wandb.ai/lab/proj/runs/abc123            # parsed from logs, optional
decision: proceed | deferred | approval_required | ...       # Phase 5 decision tag
environment:
  manager: conda | uv | venv | system
  env_names_present: ["WANDB_PROJECT", "HF_TOKEN"]           # names only, no values
timeout_seconds: 600
elapsed_seconds: 18.4
```

Credential **values** are never written. Checkpoints and W&B cache remain on disk under `outputs/` or `wandb/`, never embedded in `run.yaml`.

### Config-style serialization table

| config_style | Serialization | Example token(s) |
|---|---|---|
| `argument` (default) | `--key value` pairs | `--learning-rate 0.0002` |
| `hydra` | `key=value` overrides | `training.lr=0.0002` |
| `json` | write `params.json` in run dir | `--config <run_dir>/params.json` |
| `yaml` | write `params.yaml` in run dir | `--config <run_dir>/params.yaml` |
| other | decline (`unsupported_config_style`) | — |

## Error Handling

- **Not approved / missing approval** → decline, no spawn, JSON reports the decision; no `run.yaml` lifecycle change beyond recording the decline reason.
- **Slurm-required** → `deferred` outcome with a Phase 6 pointer in `error_summary`; history entry appended; no spawn.
- **Unsupported config_style** → decline with `unsupported_config_style`; no spawn.
- **Missing entrypoint** → `failed` with reason, non-null preparation exit code, history failure entry.
- **Non-zero exit** → `failed`, exit code recorded, logs preserved.
- **Timeout** → process terminated, `timed_out`, elapsed + threshold recorded.
- **Cancellation (SIGINT/SIGTERM)** → `cancelled`, `completed_at` recorded.
- **Environment activation failure** → surfaces as a non-zero child exit → `failed` with the activation reason captured from `stderr.log`.

Every terminal outcome retains the run directory and its logs. The helper never raises uncaught on child failure; it always produces a structured JSON result and the appropriate exit code (0 success, 1 declined/validation, 2 runtime error), matching the sibling scripts.

## Testing Strategy

**Dual approach.** Pure logic is covered by property-based tests (Hypothesis), run via a disposable `uv` environment with pytest + PyYAML, matching the Phase 2 test conventions in `tests/`. The single impure `run_process` path is covered by integration tests that spawn a tiny CPU entrypoint fixture (a few-line Python script) created under `tmp_path`. The example experiment at `experiments/example-lora-rank-ablation` is treated as **read-only**; integration tests build isolated experiment/run directories under `tmp_path` and may invoke `initialize_run.py` there to compose realistically.

- **Property tests**: minimum 100 iterations each; tagged `Feature: phase-5-local-execution, Property N: <text>`; each references its design property.
- **Unit/example tests**: approval read ordering, entrypoint precheck, framework-free command, no-network import surface.
- **Integration tests**: success exit 0, non-zero exit, timeout (sleeping fixture), stdout/stderr capture to the right files, deferral append, missing-entrypoint append, write confinement on a real run dir.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Approval gate is a total decision over approval status

For any approval-status input (the string `approved`, any other present string, or an absent/`None` value), `decide_approval` returns `PROCEED` if and only if the status equals `approved`; a present non-`approved` status returns `DECLINE_APPROVAL`; an absent/`None` status returns `DECLINE_MISSING_APPROVAL`; and no process is planned for either decline.

**Validates: Requirements 1.2, 1.3, 1.4**

### Property 2: Slurm classification refuses GPU and CPU-heavy jobs

For any resources specification, `classify_execution` returns `DEFER_SLURM` exactly when `gpus > 0` or when the estimated CPU-hours (`cpus` × hours parsed from `time`) exceed 4, and returns `PROCEED` otherwise; whenever the result is `DEFER_SLURM` no local process is planned.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 3: Environment detection follows the fixed priority order

For any combination of environment markers, `detect_environment` selects conda when a conda marker is present, otherwise uv when a uv project with an available `uv` command is present, otherwise venv when a virtual-environment marker is present, otherwise system; and the returned manager is always one of `conda`, `uv`, `venv`, `system`.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

### Property 4: Argument-style serialization emits a flag and value for every parameter

For any parameter mapping, `serialize_parameters` with the `argument` style (including when `config_style` is absent) produces, for each key, a double-dashed flag token immediately followed by that parameter's value token.

**Validates: Requirements 4.1, 4.2, 4.6, 5.3**

### Property 5: Hydra-style serialization emits a key=value override for every parameter

For any parameter mapping, `serialize_parameters` with the `hydra` style produces exactly one `key=value` override token per parameter.

**Validates: Requirements 4.3**

### Property 6: File-based config styles round-trip the parameters inside the run directory

For any parameter mapping and for the `json` or `yaml` style, the written parameter file lies within the run directory and reading it back yields a mapping equal to the original parameters, and the serialized tokens reference that file path.

**Validates: Requirements 4.4, 4.5, 7.3**

### Property 7: Whitespace-bearing values remain single argument tokens

For any parameter value that contains whitespace, the serialized command token list keeps that value as a single token rather than splitting it across multiple tokens.

**Validates: Requirements 4.8**

### Property 8: Unsupported config styles are declined

For any `config_style` value that is not one of `argument`, `hydra`, `json`, or `yaml`, command construction yields a `DECLINE_CONFIG_STYLE` decision and plans no process.

**Validates: Requirements 4.7**

### Property 9: Constructed commands reference no named framework

For any job configuration, the tokens of the constructed command contain none of the forbidden framework substrings (such as `torch`, `jax`, `accelerate`, `lightning`) except where they appear verbatim inside the user-declared entrypoint path.

**Validates: Requirements 5.1, 5.2**

### Property 10: Missing entrypoint produces a recorded failure with no spawn

For any job whose entrypoint path does not resolve to an existing workspace file, preparation yields a `failed` run status with a non-null exit code and a recorded missing-entrypoint reason, and no process is planned.

**Validates: Requirements 6.1, 6.2**

### Property 11: Planned writes are confined to the run directory

For any job configuration and run directory, every path returned by `plan_writes` is located within that run directory.

**Validates: Requirements 7.3**

### Property 12: W&B URL extraction round-trips present URLs and reports absence

For any log text that embeds a W&B run URL, `parse_wandb_url` returns exactly that URL as plain text; for any text containing no W&B URL, it returns `None`; and in all cases it performs no external call.

**Validates: Requirements 7.5**

### Property 13: Status mapping is total and lands in the allowed lifecycle set

For any process outcome, `map_status` returns `succeeded` for a zero exit, `failed` for a non-zero exit or preparation error, `timed_out` for a timeout outcome, and `cancelled` for a cancellation outcome; and `normalize_status` maps an on-disk `initialized` to `created` and `completed` to `succeeded`; every result is a member of the allowed status set.

**Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.2**

### Property 14: Terminal outcomes produce a complete run record

For any terminal process outcome, the finalized run record carries a non-null terminal status, a `started_at` timestamp, a `completed_at` timestamp, and an exit code field consistent with the outcome kind.

**Validates: Requirements 8.1, 9.1**

### Property 15: Timeout seconds parse correctly from the time field

For any valid `HH:MM:SS` time string, `parse_timeout` returns `hours×3600 + minutes×60 + seconds`; when `resources.time` is absent, it returns the configured default.

**Validates: Requirements 10.1**

### Property 16: History entries include identity and status and preserve prior content

For any set of entry fields, `format_history_entry` produces text containing the run identifier and the status, and includes the exit code and the W&B URL when the status is `succeeded` and a URL is present; and for any pre-existing history content, appending a new entry yields content that starts with the original content and contains the new entry.

**Validates: Requirements 11.1, 11.3, 11.4**

### Property 17: Recorded environment details never contain credential values

For any environment mapping that includes credential-like keys, `redact_environment` produces a mapping whose values exclude every credential value, while retaining the credential key names in a names-only form.

**Validates: Requirements 12.1, 12.2**
