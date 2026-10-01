# Implementation Plan: Phase 6 — SSH and Slurm Integration

## Overview

Implement `submit_slurm.py` in `.agents/skills/train-llm/scripts/` as a deterministic helper that extends the Phase 5 Slurm deferral into a real submission path. The language is Python (the design uses Python throughout, so no language selection is required). Each task builds incrementally: plan/job parsing and the injected `CommandRunner` boundary first, then the pure generation/mapping/validation logic, then orchestration (verify, submit, poll, cancel, retry/resume, linkage), then end-to-end wiring with a `FakeCommandRunner`. Property tests reference design properties and run with `pytest` + `PyYAML` + `Hypothesis` through a disposable `uv` environment. All test writes stay under `tmp_path`; the example experiment stays read-only; no task performs real SSH, Slurm, or network I/O.

## Tasks

- [x] 1. Set up module skeleton, data models, and the injected I/O boundary
  - [x] 1.1 Create `submit_slurm.py` scaffolding and core data models
    - Add module docstring, JSON-envelope helper `_result(status, message, data, errors, warnings)`, exit-code contract (0/1/2), and the `RunStatus` enum
    - Define `QoSCaps`, `PlanSettings`, `CommandResult`, and result dataclasses (`VerifyResult`, `SubmitResult`, `CancelResult`, `QuotaResult`)
    - _Requirements: 7.1, 13.1_
  - [x] 1.2 Define the `CommandRunner` protocol and both implementations
    - Add `CommandRunner` protocol, `SSHCommandRunner` (production, constructed only in `main()`), and `FakeCommandRunner` (scripted results, records calls, raises on unscripted commands)
    - _Requirements: 14.4_
  - [x] 1.3 Implement `load_plan_settings` from project-plan.md frontmatter
    - Parse YAML frontmatter into `PlanSettings` (ssh_host, remote_project_root, remote_conda_root, partition, account, qos, caps, cuda ceiling); never prompt for stable settings
    - _Requirements: 1.1, 2.1, 3.1, 4.1_
  - [x]* 1.4 Write unit tests for plan parsing and the fake runner guard
    - Example test parsing a `project-plan.md` fixture; guard test asserting `SSHCommandRunner` is never constructed in tests
    - _Requirements: 1.1, 14.4_

- [x] 2. Implement pure sbatch-generation logic
  - [x] 2.1 Implement `build_gres` and `map_resources_to_sbatch`
    - GRES from gpus and optional gpu_type; `--partition/--account/--qos` from plan; `--cpus-per-task/--mem/--time` from resources
    - _Requirements: 4.1, 4.2, 4.3_
  - [x]* 2.2 Write property test for GRES mapping
    - **Property 3: GRES mapping**
    - **Validates: Requirements 4.3**
  - [x]* 2.3 Write property test for resource-to-SBATCH mapping
    - **Property 4: Resource-to-SBATCH mapping**
    - **Validates: Requirements 4.1, 4.2**
  - [x] 2.4 Implement log directives and name resolution
    - `build_log_directives` (regular `%A_%x`, array `%A_%a_%x`, fixed Date_Prefix) and `resolve_log_name`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 9.2_
  - [x]* 2.5 Write property test for log-name construction
    - **Property 10: Log-name construction follows the mandated rule**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 9.2**
  - [x] 2.6 Implement `generate_sbatch_script` with activation, run command, array/dependency, and CUDA note
    - Compose directives + conda activation (source profile under Remote_Conda_Root, activate env) before the project-declared run command; conditional `--array`/`--dependency`; CUDA/12.4 conda-toolkit comment; reuse Phase 5 `config_style` serialization and framework-free check
    - _Requirements: 4.4, 4.5, 4.6, 9.1, 10.1, 10.2_
  - [x]* 2.7 Write property test for conda activation ordering
    - **Property 5: Conda activation precedes the run command**
    - **Validates: Requirements 4.4**
  - [x]* 2.8 Write property test for framework-free run command
    - **Property 6: Run command is framework-free and uses the declared entrypoint**
    - **Validates: Requirements 4.5**
  - [x]* 2.9 Write property test for array/dependency conditional inclusion
    - **Property 11: Dependency directive conditional inclusion**
    - **Validates: Requirements 9.1, 10.1, 10.2**
  - [x]* 2.10 Write unit test for the CUDA toolkit comment
    - Assert the generated script contains the CUDA/12.4 conda-toolkit note
    - _Requirements: 4.6_

- [x] 3. Implement pure validation, parsing, mapping, and safety logic
  - [x] 3.1 Implement `validate_quota` against QoS caps
    - Reject when gpus>4, cpus>8, mem_gb>80, or wall time>2 days; return every violation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  - [x]* 3.2 Write property test for quota pre-check
    - **Property 7: Quota pre-check accepts exactly the within-cap jobs**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**
  - [x] 3.9 Implement `parse_slurm_job_id`
    - Extract the id from `Submitted batch job N`; return None when absent
    - _Requirements: 6.2, 6.3, 9.3_
  - [x]* 3.3 Write property test for job-id parsing round-trip
    - **Property 8: Slurm job-id parsing round-trip**
    - **Validates: Requirements 6.2, 6.3, 9.3**
  - [x] 3.4 Implement `map_slurm_state`
    - Total mapping over the 8 Slurm states with normalization; FAILED and OUT_OF_MEMORY to `failed` while retaining the raw state
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  - [x]* 3.5 Write property test for Slurm-to-Harness status mapping
    - **Property 9: Slurm-to-Harness status mapping is total and correct**
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8**
  - [x] 3.6 Implement `decide_mutating_action`, `filter_commit_candidates`, and secret redaction
    - Approval decision for mutating actions; exclude `.out`/`.err`/checkpoints/wandb from commit candidates; redact credential-like values (reuse Phase 5 approach)
    - _Requirements: 14.1, 14.2, 14.3, 15.3, 4.7, 13.4_
  - [x]* 3.7 Write property test for commit-candidate exclusion
    - **Property 17: Commit candidates exclude logs, checkpoints, and caches**
    - **Validates: Requirements 15.3**
  - [x]* 3.8 Write property test for no-secret-in-artifacts
    - **Property 18: Generated artifacts contain no secrets**
    - **Validates: Requirements 4.7, 13.4**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement remote verification orchestration (read-only probes)
  - [x] 5.1 Implement `verify_remote` (host, path, env) via the Command_Runner
    - Reachability probe, remote-path existence probe, conda-env membership check; each read-only and routed through the injected runner; no mutating action on failure
    - _Requirements: 1.2, 1.3, 1.4, 2.2, 2.3, 2.4, 3.2, 3.3, 3.4, 15.2_
  - [x]* 5.2 Write property test for the pre-submit verification gate
    - **Property 1: Pre-submit gate on read-only verification**
    - **Validates: Requirements 1.3, 1.4, 2.3, 2.4**
  - [x]* 5.3 Write property test for conda-env membership verification
    - **Property 2: Conda environment verification is membership**
    - **Validates: Requirements 3.3, 3.4**
  - [x]* 5.4 Write property test for read-only probe membership
    - **Property 16: Login-node probes are non-mutating**
    - **Validates: Requirements 15.2**

- [x] 6. Implement submission, polling, and cancellation orchestration
  - [x] 6.1 Implement `submit` with approval gate, quota pre-check, and job-id capture
    - Gate on approval; run `validate_quota` before any `sbatch`; invoke `sbatch` via runner over SSH; parse id; record id + `submitted` status; route all heavy jobs through sbatch (never login node)
    - _Requirements: 6.1, 6.3, 6.4, 5.1, 14.1, 15.1_
  - [x]* 6.2 Write property test for approval gating of mutating actions
    - **Property 14: Mutating actions execute if and only if approved**
    - **Validates: Requirements 6.1, 8.1, 8.2, 8.4, 14.1, 14.2, 14.3**
  - [x]* 6.3 Write property test for heavy-job sbatch routing
    - **Property 15: Heavy jobs always route through sbatch**
    - **Validates: Requirements 15.1**
  - [x] 6.4 Implement `poll` using squeue/sacct and status mapping
    - Query active jobs via `squeue`, completed via `sacct`; map state; capture node assignment
    - _Requirements: 7.1, 13.2_
  - [x] 6.5 Implement `cancel` with approval gate
    - Gate on approval; invoke `scancel`; set `cancelled` on exit 0; decline without approval
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x]* 6.6 Write integration test for submit/poll/cancel with a FakeCommandRunner
    - Script runner results for sbatch, squeue, sacct, scancel; assert wiring, no real I/O, writes under tmp_path
    - _Requirements: 6.1, 7.1, 8.2_

- [x] 7. Implement retry/resume and run.yaml linkage
  - [x] 7.1 Implement retry and resume
    - Retry creates a new Run_Record preserving the prior; resume polls a recorded `slurm_job_id` without resubmitting; resume-not-possible when no id
    - _Requirements: 11.1, 11.2, 11.3_
  - [x]* 7.2 Write property test for retry preservation
    - **Property 12: Retry preserves the prior run**
    - **Validates: Requirements 11.1**
  - [x]* 7.3 Write property test for resume behavior
    - **Property 13: Resume reuses the recorded job id without resubmitting**
    - **Validates: Requirements 11.2, 11.3**
  - [x] 7.4 Implement `write_run_linkage` into run.yaml
    - Write slurm_job_id, slurm_state, mapped status, submitted/queued time, node_list, and array_job_id; never write secrets
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  - [x]* 7.5 Write unit test for run.yaml linkage fields
    - Assert all linkage fields present after submit/poll; assert no credential values written
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [x] 8. Wire the CLI entrypoint and boundary enforcement
  - [x] 8.1 Implement `parse_arguments`, `main`, and command dispatch
    - Subcommands/flags for verify, submit, poll, cancel, retry, resume; construct `SSHCommandRunner` only here; emit the JSON envelope and exit codes; assert W&B and HF are not invoked
    - _Requirements: 6.1, 7.1, 8.1, 14.4, 15.4_
  - [x]* 8.2 Write integration test for the end-to-end CLI flow
    - Drive verify → submit → poll → linkage with an injected FakeCommandRunner; assert envelope shape, exit codes, and tmp_path-only writes
    - _Requirements: 14.4, 15.4_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for a faster MVP; core implementation tasks are never optional.
- Each task references specific requirement sub-clauses for traceability.
- Property test tasks each name a design property and run a minimum of 100 iterations with the tag `**Feature: phase-6-ssh-slurm, Property N: ...**`.
- All SSH and Slurm I/O passes through the injected `CommandRunner`; tests use `FakeCommandRunner` only and never touch the network.
- All test writes are confined to `tmp_path`; the example experiment stays read-only.
- Real mutating remote actions (sbatch, scancel, transfer/clone, env creation) require explicit user approval and are never exercised by tests.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "2.1", "2.4", "3.1", "3.9", "3.4", "3.6"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.5", "3.2", "3.3", "3.5", "3.7", "3.8"] },
    { "id": 3, "tasks": ["2.6"] },
    { "id": 4, "tasks": ["2.7", "2.8", "2.9", "2.10", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "6.1", "6.4", "6.5"] },
    { "id": 6, "tasks": ["6.2", "6.3", "6.6", "7.1", "7.4"] },
    { "id": 7, "tasks": ["7.2", "7.3", "7.5", "8.1"] },
    { "id": 8, "tasks": ["8.2"] }
  ]
}
```
