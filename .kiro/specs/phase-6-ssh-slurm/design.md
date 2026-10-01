# Design Document

## Overview

Phase 6 implements the Slurm execution path that Phase 5 (`run_local.py`) hard-defers for GPU and CPU-heavy jobs. It is delivered as a deterministic Python helper, `submit_slurm.py`, in `.agents/skills/train-llm/scripts/`, alongside the existing `initialize_run.py` and `run_local.py`.

The central design decision is a strict separation between **pure logic** and **impure I/O**:

- **Pure logic** functions take plain data (dicts parsed from YAML, strings, enums) and return plain data (strings, enums, dataclasses). They perform no SSH, no subprocess, no network, and no filesystem mutation. These functions are covered by property-based and unit tests.
- **Impure I/O** passes exclusively through an injected `CommandRunner` interface that executes a command and returns `(exit_code, stdout, stderr)`. Production uses an `SSHCommandRunner`; tests inject a `FakeCommandRunner`. No real SSH or network ever occurs in tests.

All stable settings come from `project-plan.md` and are never re-asked. Mutating remote actions (`sbatch`, `scancel`, remote transfer/clone, remote env creation) require `approval.status == approved` in the experiment `plan.md`; read-only probes (`ssh echo`, `test -d`, `conda env list`, `sinfo`, `squeue`, `sacct`, `scontrol show`) are non-mutating and still routed through the `CommandRunner`.

The helper follows the Phase 5 output contract: a JSON envelope `{status, message, data, errors, warnings}` printed to stdout, with exit codes `0` (action completed or recorded), `1` (declined: approval/quota/verification/resume), and `2` (runtime error).

## Architecture

```text
                      project-plan.md (frontmatter)         experiment plan.md (approval)
                                 │                                     │
                                 ▼                                     ▼
          ┌───────────────────────────────────────────────────────────────────┐
          │                         submit_slurm.py                             │
          │                                                                     │
          │   PURE LOGIC (no I/O, fully testable)                               │
          │   ├─ load_plan_settings(frontmatter) -> PlanSettings                │
          │   ├─ validate_quota(resources, caps) -> QuotaResult                 │
          │   ├─ build_gres(gpus, gpu_type) -> str                              │
          │   ├─ map_resources_to_sbatch(resources, settings) -> list[str]      │
          │   ├─ build_log_directives(prefix, is_array) -> (out, err)           │
          │   ├─ resolve_log_name(prefix, jobid, taskid, name) -> str           │
          │   ├─ generate_sbatch_script(job, settings, prefix) -> str           │
          │   ├─ parse_slurm_job_id(sbatch_stdout) -> int | None                │
          │   ├─ map_slurm_state(state) -> RunStatus                            │
          │   ├─ decide_mutating_action(approval, kind) -> ActionDecision       │
          │   ├─ filter_commit_candidates(paths) -> list[str]                   │
          │   └─ redact_secrets(text, env) -> str                               │
          │                                                                     │
          │   IMPURE BOUNDARY (single injection point)                          │
          │   └─ CommandRunner.run(argv, *, remote: bool) -> CommandResult      │
          │        ├─ SSHCommandRunner  (production; wraps ssh <SSH_Host> ...)  │
          │        └─ FakeCommandRunner (tests; scripted results, records calls)│
          │                                                                     │
          │   ORCHESTRATION (thin; composes pure logic + CommandRunner)         │
          │   ├─ verify_remote(runner, settings) -> VerifyResult                │
          │   ├─ submit(runner, job, settings, approval) -> SubmitResult        │
          │   ├─ poll(runner, slurm_job_id) -> RunStatus                        │
          │   ├─ cancel(runner, slurm_job_id, approval) -> CancelResult         │
          │   └─ write_run_linkage(run_dir, fields) -> None                     │
          └───────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                 experiments/<exp>/runs/<run-id>/run.yaml  (Slurm linkage fields)
```

### Why this split

- Property tests exercise generation, mapping, parsing, and validation across hundreds of inputs with zero network risk.
- Integration tests use `FakeCommandRunner` to assert orchestration wiring and gating without any real `sbatch`/`scancel`.
- The only code that can touch the cluster is `SSHCommandRunner`, which is never constructed in tests.

## Components and Interfaces

### CommandRunner (injected boundary)

```python
from dataclasses import dataclass
from typing import Protocol, Sequence

@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

class CommandRunner(Protocol):
    def run(self, argv: Sequence[str], *, remote: bool) -> CommandResult:
        """Execute argv locally or over SSH. The ONLY I/O boundary."""
        ...
```

- `SSHCommandRunner(ssh_host)` builds `["ssh", ssh_host, *argv]` for `remote=True` and runs via `subprocess`. Constructed only in `main()`.
- `FakeCommandRunner(scripted)` returns pre-seeded `CommandResult`s keyed by a command matcher and records every call for assertions. It raises if asked to run anything not scripted, guaranteeing tests never leak to real I/O.

### Plan and job data

```python
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
    caps: QoSCaps
    cuda_ceiling: str = "12.4"
```

### Status model

```python
from enum import Enum

class RunStatus(str, Enum):
    SUBMITTED = "submitted"
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    PREEMPTED = "preempted"
```

### Slurm-to-Harness status mapping

```python
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
    # sacct may append codes like "CANCELLED by 1234"; normalize to the leading token.
    token = (state or "").strip().split()[0].upper() if state and state.strip() else ""
    return _STATE_MAP.get(token, RunStatus.PENDING)
```

`FAILED` and `OUT_OF_MEMORY` both map to `failed`; the originating Slurm state is recorded separately in `run.yaml` as `slurm_state` so an out-of-memory failure stays distinguishable.

### GRES construction

```python
_GPU_TYPES = {"A6000", "PRO6000", "4090"}

def build_gres(gpus: int, gpu_type: str | None) -> str:
    if gpu_type and gpu_type in _GPU_TYPES:
        return f"gpu:{gpu_type}:{gpus}"
    return f"gpu:{gpus}"
```

### Quota validation

```python
@dataclass(frozen=True)
class QuotaResult:
    ok: bool
    violations: list[str]

def validate_quota(resources: dict, caps: QoSCaps) -> QuotaResult:
    violations = []
    if int(resources.get("gpus", 0)) > caps.max_gpus:
        violations.append(f"gpus>{caps.max_gpus}")
    if int(resources.get("cpus", 1)) > caps.max_cpus:
        violations.append(f"cpus>{caps.max_cpus}")
    if int(resources.get("mem_gb", resources.get("memory_gb", 0))) > caps.max_mem_gb:
        violations.append(f"mem_gb>{caps.max_mem_gb}")
    if parse_time_to_seconds(resources.get("time")) > caps.max_wall_seconds:
        violations.append("time>2-00:00:00")
    return QuotaResult(ok=not violations, violations=violations)
```

Submission proceeds only when `QuotaResult.ok` is true.

### Log naming

Log names follow roadmap section 6 exactly. The `Date_Prefix` is a single `YYYYMMDD-HHMMSS` timestamp fixed at submit time and embedded literally; Slurm placeholders `%A` (array/job id), `%a` (array task id), and `%x` (job name) fill the rest.

```python
def build_log_directives(date_prefix: str, is_array: bool) -> tuple[str, str]:
    stem = f"{date_prefix}_%A_%a_%x" if is_array else f"{date_prefix}_%A_%x"
    return f"{stem}.out", f"{stem}.err"

def resolve_log_name(date_prefix: str, job_id: int,
                     task_id: int | None, job_name: str) -> str:
    if task_id is None:
        return f"{date_prefix}_{job_id}_{job_name}"
    return f"{date_prefix}_{job_id}_{task_id}_{job_name}"
```

### Job-id parsing

```python
_SBATCH_ID = re.compile(r"Submitted batch job (\d+)")

def parse_slurm_job_id(sbatch_stdout: str) -> int | None:
    m = _SBATCH_ID.search(sbatch_stdout or "")
    return int(m.group(1)) if m else None
```

### sbatch script generation (shape)

```text
#!/bin/bash
#SBATCH --job-name=<job_id>
#SBATCH --partition=<plan.partition>
#SBATCH --account=<plan.account>
#SBATCH --qos=<plan.qos>
#SBATCH --cpus-per-task=<resources.cpus>
#SBATCH --mem=<resources.mem_gb>G
#SBATCH --time=<resources.time>
#SBATCH --gres=<gres>                 # only when gpus > 0
#SBATCH --array=<array>               # only when array declared
#SBATCH --dependency=<dependency>     # only when dependency declared
#SBATCH --output=<remote_root>/.../logs/<prefix>_%A[_%a]_%x.out
#SBATCH --error=<remote_root>/.../logs/<prefix>_%A[_%a]_%x.err

# CUDA toolkit is provided by the conda environment and pinned at or below the
# NVIDIA driver CUDA ceiling (12.4). No system nvcc, no lmod on this cluster.
source <remote_conda_root>/etc/profile.d/conda.sh
conda activate <conda_env_name>

cd <remote_project_root>
python <entrypoint> <serialized parameters>
```

Parameter serialization reuses the Phase 5 `config_style` conventions (`argument`, `hydra`, `json`, `yaml`). The generator never injects a training-framework name of its own choosing; it only emits the project-declared entrypoint and parameters.

### Approval gating for mutating actions

```python
class ActionDecision(str, Enum):
    PROCEED = "proceed"
    DECLINE_APPROVAL = "approval_required"

def decide_mutating_action(approval_status: str | None, kind: str) -> ActionDecision:
    if approval_status and approval_status.strip().lower() == "approved":
        return ActionDecision.PROCEED
    return ActionDecision.DECLINE_APPROVAL
```

Every `Mutating_Remote_Action` (submit, cancel, transfer/clone, env creation) calls `decide_mutating_action` first; on `DECLINE_APPROVAL` the orchestration returns without touching the `CommandRunner`.

### run.yaml linkage fields

Phase 6 extends the Run_Record with:

```yaml
slurm_job_id: 123456
slurm_state: COMPLETED        # raw Slurm state, keeps OOM distinct from plain failure
status: succeeded             # mapped Harness Run status
submitted_at: 2026-09-23T14:25:30Z
queued_at: 2026-09-23T14:25:31Z
node_list: n03                # from squeue/sacct when assigned
array_job_id: 123456          # present only for array jobs
```

No secret, token, password, or credential value is ever written; environment reporting reuses the Phase 5 redaction approach (names only, credential-like keys dropped).

### Safety filters

```python
_EXCLUDED = (".out", ".err")          # raw Slurm logs
_EXCLUDED_DIRS = ("checkpoints", "wandb")

def filter_commit_candidates(paths: list[str]) -> list[str]:
    return [p for p in paths
            if not p.endswith(_EXCLUDED)
            and not any(d in p.split("/") for d in _EXCLUDED_DIRS)]
```

## Data Models

- **PlanSettings / QoSCaps**: parsed once from `project-plan.md` frontmatter.
- **Job_Config**: parsed from `resolved-job.yaml` (preferred) or the source job YAML; includes `resources`, optional `array`, optional `dependency`.
- **CommandResult**: `(exit_code, stdout, stderr)` — the only value crossing the I/O boundary.
- **SubmitResult / VerifyResult / CancelResult / QuotaResult**: pure dataclasses summarizing each orchestration step for the JSON envelope.
- **Run_Record**: `run.yaml`, extended with the Slurm linkage fields above.

## Error Handling

- **Unreachable host / missing remote path / missing env**: orchestration returns a declined result (exit `1`) with a specific `errors` entry; no mutating action is attempted.
- **Quota violation**: declined (exit `1`) listing every violated cap; no `sbatch`.
- **Unparseable sbatch stdout**: submission-failure result; no `slurm_job_id` written.
- **Missing approval**: declined (exit `1`); the `CommandRunner` is never invoked for the mutating action.
- **Resume with no recorded job id**: resume-not-possible result (exit `1`); no new submission.
- **Runtime/parse errors**: caught at the top level and returned as a structured error (exit `2`); the helper never crashes with a traceback.
- **FAILED vs OUT_OF_MEMORY**: both map to `failed`, but `slurm_state` preserves the distinction for debugging.

## Testing Strategy

**Dual approach.** Property tests cover the pure logic across many generated inputs; unit/integration tests cover specific examples, edge cases, and orchestration wiring with a `FakeCommandRunner`. All test writes are confined to `tmp_path`; the example experiment under `experiments/example-lora-rank-ablation/` stays read-only; no test performs real SSH, Slurm, or network I/O.

- **Tooling**: `pytest` with `PyYAML` and `Hypothesis`, run through a disposable `uv` environment per Phase 2 conventions.
- **Property tests**: minimum 100 iterations each; each references its design property with the tag `**Feature: phase-6-ssh-slurm, Property N: <text>**`.
- **Injection discipline**: unit and property tests never construct `SSHCommandRunner`; a guard test asserts the default I/O path is not reachable without an injected runner.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Pre-submit gate on read-only verification

*For any* sequence of read-only probe results for host reachability and remote-path existence, the Slurm_Submitter attempts a job submission only when both the reachability probe and the remote-path probe returned exit code zero; if either probe failed, no `sbatch` call is made.

**Validates: Requirements 1.3, 1.4, 2.3, 2.4**

### Property 2: Conda environment verification is membership

*For any* conda environment listing and target Conda_Env_Name, the environment is reported verified if and only if the Conda_Env_Name appears in the listing; when absent, the reported outcome flags remote environment creation as an approval-gated mutating action.

**Validates: Requirements 3.3, 3.4**

### Property 3: GRES mapping

*For any* GPU count greater than zero and optional GPU type, the generated `--gres` value equals `gpu:<type>:<N>` when the type is one of `A6000`, `PRO6000`, or `4090`, and equals `gpu:<N>` otherwise.

**Validates: Requirements 4.3**

### Property 4: Resource-to-SBATCH mapping

*For any* valid Resources and PlanSettings, the generated script contains `--partition`, `--account`, and `--qos` equal to the plan values and `--cpus-per-task`, `--mem` (in gigabytes), and `--time` equal to the requested resource values.

**Validates: Requirements 4.1, 4.2**

### Property 5: Conda activation precedes the run command

*For any* PlanSettings and Conda_Env_Name, the generated script sources the conda profile under the Remote_Conda_Root and activates the Conda_Env_Name on lines that appear before the run-command line.

**Validates: Requirements 4.4**

### Property 6: Run command is framework-free and uses the declared entrypoint

*For any* Job_Config, the generated run command contains the project-declared entrypoint and contains no training-framework token introduced by the generator.

**Validates: Requirements 4.5**

### Property 7: Quota pre-check accepts exactly the within-cap jobs

*For any* Resources, the quota check passes if and only if `gpus` is at most 4, `cpus` is at most 8, `mem_gb` is at most 80, and the wall time is at most 2 days; whenever the check fails, no submission is attempted.

**Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**

### Property 8: Slurm job-id parsing round-trip

*For any* numeric job id embedded in `sbatch`-style output (including surrounding text), the parser recovers exactly that id; and *for any* output containing no submitted-batch-job pattern, the parser returns no id.

**Validates: Requirements 6.2, 6.3, 9.3**

### Property 9: Slurm-to-Harness status mapping is total and correct

*For any* Slurm_State in `{PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, TIMEOUT, OUT_OF_MEMORY, PREEMPTED}` (in any case and with trailing annotations), the mapped Run_Status equals the specified target, with `FAILED` and `OUT_OF_MEMORY` mapping to `failed` while the originating Slurm_State is retained.

**Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8**

### Property 10: Log-name construction follows the mandated rule

*For any* Date_Prefix, job id, optional task id, and job name, the resolved log name equals `<Date_Prefix>_<jobid>_<jobname>` for a regular job and `<Date_Prefix>_<jobid>_<taskid>_<jobname>` for an array task; and the generated `--output` and `--error` directives share one stem differing only by the `.out`/`.err` suffix, embedding `%A`/`%x` for a regular job and `%A`/`%a`/`%x` for an array job with the Date_Prefix fixed.

**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 9.2**

### Property 11: Dependency directive conditional inclusion

*For any* Job_Config, the script contains a `--dependency` directive equal to the declared Dependency_Spec if and only if a Dependency_Spec is declared, and the same conditional inclusion holds for the `--array` directive and its declared value.

**Validates: Requirements 9.1, 10.1, 10.2**

### Property 12: Retry preserves the prior run

*For any* prior Run_Record whose status is `failed`, `timed_out`, `cancelled`, or `preempted`, a retry produces a new Run_Record with a distinct run id while the prior Run_Record remains unchanged.

**Validates: Requirements 11.1**

### Property 13: Resume reuses the recorded job id without resubmitting

*For any* Run that records a Slurm_Job_Id, a resume polls that recorded id and performs no `sbatch` submission; *for any* Run with no recorded id, a resume reports resume-not-possible and performs no submission.

**Validates: Requirements 11.2, 11.3**

### Property 14: Mutating actions execute if and only if approved

*For any* Mutating_Remote_Action kind (submit, cancel, transfer/clone, env creation) and Approval_Status, the action reaches the Command_Runner if and only if the Approval_Status equals `approved`; otherwise the Command_Runner is not invoked for that action.

**Validates: Requirements 6.1, 8.1, 8.2, 8.4, 14.1, 14.2, 14.3**

### Property 15: Heavy jobs always route through sbatch

*For any* Job_Config that requests one or more GPUs or exceeds the CPU-heavy threshold, the selected execution path is `sbatch` submission and no direct login-node run command is issued.

**Validates: Requirements 15.1**

### Property 16: Login-node probes are non-mutating

*For any* probe the Slurm_Submitter issues directly on the login node, the probe command belongs to the allowed read-only set (`ssh echo`, `test -d`, `conda env list`, `sinfo`, `squeue`, `sacct`, `scontrol show`).

**Validates: Requirements 15.2**

### Property 17: Commit candidates exclude logs, checkpoints, and caches

*For any* set of produced paths, the filtered commit candidates contain no path ending in `.out` or `.err` and no path within a `checkpoints` or `wandb` directory.

**Validates: Requirements 15.3**

### Property 18: Generated artifacts contain no secrets

*For any* Job_Config and environment map that includes credential-like keys and values, neither the generated sbatch script nor the written Run_Record contains any of those secret values.

**Validates: Requirements 4.7, 13.4**
