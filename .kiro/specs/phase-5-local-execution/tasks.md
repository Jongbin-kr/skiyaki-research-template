# Implementation Plan: Phase 5 — Local Lightweight Job Execution

## Overview

Implement a new deterministic helper `run_local.py` in `.agents/skills/train-llm/scripts/` that composes with `initialize_run.py` to run short local CPU smoke-test jobs after approval. Pure decision logic is built first and property-tested; the single impure subprocess step is wired last and integration-tested with a tiny CPU entrypoint fixture under `tmp_path`. All work is in Python, matches the existing script contract (explicit paths, JSON output, no `src/` imports), and keeps the example experiment read-only.

Each prompt builds on the previous one and ends by wiring the orchestration and skill documentation together, leaving no orphaned code.

## Tasks

- [x] 1. Scaffold the helper module and shared data types
  - Create `.agents/skills/train-llm/scripts/run_local.py` with the module docstring, `argparse` CLI (`--run-dir`, `--workspace`, `--plan-file`, `--default-timeout`, `--version`), and the JSON output contract matching sibling scripts
  - Define `RunStatus`, `ExecDecision`, `EnvManager`, `EnvMarkers`, and `ProcessOutcome` from the design
  - Add a disposable-`uv` test module `tests/test_phase5_run_local_properties.py` skeleton importing the module via `importlib` (same loader pattern as `tests/test_initialize_run_properties.py`)
  - _Requirements: 5.1, 8.7_

- [x] 2. Implement approval gating and Slurm classification
  - [x] 2.1 Implement `decide_approval` and the `plan.md` approval reader
    - Return `PROCEED`/`DECLINE_APPROVAL`/`DECLINE_MISSING_APPROVAL`; never spawn on decline
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x]* 2.2 Write property test for the approval gate
    - **Property 1: Approval gate is a total decision over approval status**
    - **Validates: Requirements 1.2, 1.3, 1.4**
  - [x] 2.3 Implement `estimate_cpu_hours` and `classify_execution`
    - Hard-reject GPU (`gpus>0`) and CPU-heavy (`cpu_hours>4`) as `DEFER_SLURM`; else `PROCEED`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x]* 2.4 Write property test for Slurm classification
    - **Property 2: Slurm classification refuses GPU and CPU-heavy jobs**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

- [x] 3. Implement environment detection
  - [x] 3.1 Implement `detect_environment` and `activation_prefix`
    - Priority conda → uv → venv → system; build the matching activation prefix tokens
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x]* 3.2 Write property test for detection priority
    - **Property 3: Environment detection follows the fixed priority order**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

- [x] 4. Implement command construction and config-style serialization
  - [x] 4.1 Implement `serialize_parameters` and `build_command`
    - Support `argument` (default), `hydra`, `json`, `yaml`; write JSON/YAML param files inside the run dir; decline unknown styles; use the entrypoint path verbatim; keep whitespace values as single tokens
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.1, 5.2, 5.3_
  - [x]* 4.2 Write property test for argument-style serialization
    - **Property 4: Argument-style serialization emits a flag and value for every parameter**
    - **Validates: Requirements 4.1, 4.2, 4.6, 5.3**
  - [x]* 4.3 Write property test for hydra-style serialization
    - **Property 5: Hydra-style serialization emits a key=value override for every parameter**
    - **Validates: Requirements 4.3**
  - [x]* 4.4 Write property test for file-based config-style round-trip
    - **Property 6: File-based config styles round-trip the parameters inside the run directory**
    - **Validates: Requirements 4.4, 4.5, 7.3**
  - [x]* 4.5 Write property test for whitespace token safety
    - **Property 7: Whitespace-bearing values remain single argument tokens**
    - **Validates: Requirements 4.8**
  - [x]* 4.6 Write property test for unsupported config styles
    - **Property 8: Unsupported config styles are declined**
    - **Validates: Requirements 4.7**
  - [x]* 4.7 Write property test for framework independence
    - **Property 9: Constructed commands reference no named framework**
    - **Validates: Requirements 5.1, 5.2**

- [x] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement preparation checks and write planning
  - [x] 6.1 Implement entrypoint existence check and `plan_writes`
    - Missing entrypoint → `failed` with reason and non-null exit code, no spawn; `plan_writes` returns only paths under the run dir
    - _Requirements: 6.1, 6.2, 7.3_
  - [x]* 6.2 Write property test for missing-entrypoint failure
    - **Property 10: Missing entrypoint produces a recorded failure with no spawn**
    - **Validates: Requirements 6.1, 6.2**
  - [x]* 6.3 Write property test for write confinement
    - **Property 11: Planned writes are confined to the run directory**
    - **Validates: Requirements 7.3**

- [x] 7. Implement status mapping, timeout parsing, and log parsing
  - [x] 7.1 Implement `map_status`, `normalize_status`, and `parse_timeout`
    - Map outcomes to the roadmap lifecycle; normalize `initialized`→`created`, `completed`→`succeeded`; parse `HH:MM:SS` to seconds with default fallback
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.1, 10.2_
  - [x]* 7.2 Write property test for status mapping and normalization
    - **Property 13: Status mapping is total and lands in the allowed lifecycle set**
    - **Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.2**
  - [x]* 7.3 Write property test for timeout parsing
    - **Property 15: Timeout seconds parse correctly from the time field**
    - **Validates: Requirements 10.1**
  - [x] 7.4 Implement `parse_wandb_url`
    - Extract a wandb.ai run URL from log text as plain text; return `None` when absent; no network
    - _Requirements: 7.5_
  - [x]* 7.5 Write property test for W&B URL extraction
    - **Property 12: W&B URL extraction round-trips present URLs and reports absence**
    - **Validates: Requirements 7.5**

- [x] 8. Implement run-record finalization, history formatting, and redaction
  - [x] 8.1 Implement `redact_environment`
    - Strip values for credential-like keys; keep names-only form
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  - [x]* 8.2 Write property test for credential redaction
    - **Property 17: Recorded environment details never contain credential values**
    - **Validates: Requirements 12.1, 12.2**
  - [x] 8.3 Implement `format_history_entry` and the run-record update writer
    - Entry contains run id and status; adds exit code and W&B URL for succeeded runs; record update sets status, started_at, completed_at, exit_code; preserve initializer fields
    - _Requirements: 8.1, 9.1, 9.2, 9.3, 11.1, 11.2, 11.3, 11.4_
  - [x]* 8.4 Write property test for history entry formatting and append preservation
    - **Property 16: History entries include identity and status and preserve prior content**
    - **Validates: Requirements 11.1, 11.3, 11.4**
  - [x]* 8.5 Write property test for terminal run-record completeness
    - **Property 14: Terminal outcomes produce a complete run record**
    - **Validates: Requirements 8.1, 9.1**

- [x] 9. Implement the impure subprocess shell and top-level orchestration
  - [x] 9.1 Implement `run_process`
    - Spawn via subprocess from the workspace root, capture stdout→`logs/stdout.log` and stderr→`logs/stderr.log`, enforce the timeout, map SIGINT/SIGTERM to a cancelled outcome, never raise on child failure
    - _Requirements: 7.1, 7.2, 7.4, 8.1, 10.2, 10.3_
  - [x] 9.2 Implement `execute` orchestration and wire the CLI `main`
    - Load `resolved-job.yaml` and approval; run approval gate → Slurm gate → entrypoint check → env detection → command build → timeout → `run_process` → finalize record + history; emit JSON and exit codes (0/1/2); set credential env on the child only
    - _Requirements: 1.1, 2.5, 3.6, 6.3, 7.3, 8.1, 9.1, 9.2, 9.3, 11.2, 12.2, 12.4_
  - [x]* 9.3 Write integration tests for the execution shell
    - Use a tiny CPU entrypoint fixture under `tmp_path` (success exit 0, non-zero exit, sleeping process for timeout); assert stdout/stderr capture, status lifecycle, deferral and missing-entrypoint history appends, and that writes stay under the run dir; keep the example experiment read-only
    - _Requirements: 2.5, 3.6, 6.3, 7.1, 7.2, 7.4, 8.1, 9.3, 10.2, 10.3, 11.2_

- [x] 10. Wire documentation and update the skill contract
  - [x] 10.1 Document `run_local.py` in the scripts README and update `train-llm/SKILL.md`
    - Add usage, arguments, JSON output, exit codes, and the composition note (status normalization `initialized→created`, `completed→succeeded`); update SKILL.md Execution/Track steps to call `run_local.py` and record the Slurm hard-reject and Phase 6/7/8 boundaries
    - _Requirements: 2.2, 8.6, 12.4_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for a faster MVP.
- Each task references specific requirement sub-clauses for traceability.
- All test writes use `tmp_path`; `experiments/example-lora-rank-ablation` stays read-only.
- Tests run via a disposable `uv` environment with pytest + PyYAML + Hypothesis, matching Phase 2 conventions.
- Property tests use a minimum of 100 iterations and are tagged `Feature: phase-5-local-execution, Property N: <text>`.
- Checkpoints provide incremental validation points.

## Task Dependency Graph

Implementation sub-tasks all edit the single new module `run_local.py`, so they are serialized across waves to avoid write conflicts on that file. Test sub-tasks (marked `*`) each write their own `tests/test_phase5_*` file and run in parallel once the code they cover exists.

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1"] },
    { "id": 1, "tasks": ["2.3"] },
    { "id": 2, "tasks": ["3.1"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["6.1"] },
    { "id": 5, "tasks": ["7.1"] },
    { "id": 6, "tasks": ["7.4"] },
    { "id": 7, "tasks": ["8.1"] },
    { "id": 8, "tasks": ["8.3"] },
    { "id": 9, "tasks": ["9.1"] },
    { "id": 10, "tasks": ["9.2"] },
    { "id": 11, "tasks": ["2.2", "2.4", "3.2", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "6.2", "6.3", "7.2", "7.3", "7.5", "8.2", "8.4", "8.5", "9.3", "10.1"] }
  ]
}
```
