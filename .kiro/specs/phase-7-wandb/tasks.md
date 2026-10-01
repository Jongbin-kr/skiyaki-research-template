# Implementation Plan: Phase 7 — Weights & Biases Integration

## Overview

Implement `track_wandb.py` in `.agents/skills/train-llm/scripts/` as a deterministic helper that adds the W&B experiment-tracking layer on top of the Phase 5 local executor (`run_local.py`) and the Phase 6 Slurm submitter (`submit_slurm.py`). The language is Python (the design uses Python throughout, so no language selection is required). Each task builds incrementally: the module skeleton, data models, and the injected `WandbClient` boundary first; then the pure logic (settings/mode resolution, group/tag derivation, config redaction, path construction, URL parsing, status mapping, gating, git-sha mapping, safety filters); then the thin orchestration (create, resume, config, group/tag assignment, sync check, comparison, run.yaml linkage); then the CLI entrypoint with boundary enforcement. Property tests reference design properties and run with `pytest` + `PyYAML` + `Hypothesis` through a disposable `uv` environment. All test writes stay under `tmp_path`; the example experiment stays read-only; no task performs a real W&B API call, sync, or network I/O.

## Tasks

- [x] 1. Set up module skeleton, data models, and the injected W&B boundary
  - [x] 1.1 Create `track_wandb.py` scaffolding and core data models
    - Add module docstring, JSON-envelope helper `_result(status, message, data, errors, warnings)`, exit-code contract (0/1/2), and the `WandbStatus`, `EffectiveMode`, and `ActionDecision` enums
    - Define `WandbSettings`, `ModeDecision`, `CreatedRun`, `RunMetrics`, and the orchestration result dataclasses (`RunResult`, `ResumeResult`, `ConfigResult`, `GroupResult`, `SyncResult`, `CompareResult`); define `PLACEHOLDER_ENTITY`, `VALID_MODES`, and `UNKNOWN_SHA` constants
    - _Requirements: 15.1, 13.1_
  - [x] 1.2 Define the `WandbClient` protocol and both implementations
    - Add the `WandbClient` protocol (`create_run`, `resume_run`, `update_config`, `finish_run`, `sync_state`, `fetch_group_metrics`), `RealWandbClient` (production, wraps the `wandb` SDK, constructed only in `main()`), and `FakeWandbClient` (scripted results, records calls, raises on unscripted operations)
    - _Requirements: 12.1, 12.2, 12.3_
  - [x] 1.3 Implement `load_wandb_settings` from project-plan.md frontmatter
    - Parse YAML frontmatter into `WandbSettings` (entity, project, mode, keep_local_data); never prompt for stable settings
    - _Requirements: 1.1_
  - [x]* 1.4 Write unit tests for settings loading and the fake-client guard
    - Example test parsing a `project-plan.md` fixture into `WandbSettings`; guard test asserting `RealWandbClient` / the `wandb` SDK is never constructed in tests
    - _Requirements: 1.1, 12.2, 12.3_
  - [x]* 1.5 Write property test for settings loading
    - **Feature: phase-7-wandb, Property 1: Settings loading reflects the project plan**
    - **Property 1: Settings loading reflects the project plan**
    - **Validates: Requirements 1.1**

- [x] 2. Implement mode resolution and placeholder tolerance
  - [x] 2.1 Implement `is_placeholder_entity` and `resolve_mode`
    - Detect the `TODO-set-before-phase-7` placeholder; map declared mode to an `EffectiveMode` with `config_error` for invalid modes and `placeholder_online_declined` plus offline downgrade for the placeholder in online mode; `disabled` short-circuits
    - _Requirements: 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4_
  - [x]* 2.2 Write property test for invalid-mode configuration error
    - **Feature: phase-7-wandb, Property 2: Invalid mode is a configuration error with no run created**
    - **Property 2: Invalid mode is a configuration error with no run created**
    - **Validates: Requirements 1.2**
  - [x]* 2.3 Write property test for disabled-mode no-op
    - **Feature: phase-7-wandb, Property 3: Disabled mode performs no mutating action**
    - **Property 3: Disabled mode performs no mutating action**
    - **Validates: Requirements 1.3**
  - [x]* 2.4 Write property test for placeholder-entity tolerance
    - **Feature: phase-7-wandb, Property 4: Placeholder-entity tolerance**
    - **Property 4: Placeholder-entity tolerance**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

- [x] 3. Implement pure group, tag, config, and path logic
  - [x] 3.1 Implement `resolve_group` and `resolve_tags`
    - Group resolves to the experiment id (with an optional job-level override) so every Run of an experiment shares one group; tags derive deterministically and de-duplicated from declared and config-derived values
    - _Requirements: 5.1, 5.2, 5.4_
  - [x]* 3.2 Write property test for shared experiment group
    - **Feature: phase-7-wandb, Property 7: Runs of one experiment share a group**
    - **Property 7: Runs of one experiment share a group**
    - **Validates: Requirements 5.1, 5.4**
  - [x]* 3.3 Write property test for deterministic tag derivation
    - **Feature: phase-7-wandb, Property 8: Tag derivation is deterministic**
    - **Property 8: Tag derivation is deterministic**
    - **Validates: Requirements 5.2**
  - [x] 3.4 Implement `redact_config`, `build_run_config`, and `redact_secrets`
    - Drop every credential-like value from config (recursively), surface only non-credential env key names, and redact credential values from text (reuse Phase 5/6 names-only approach)
    - _Requirements: 6.1, 6.3, 14.1, 14.2, 14.3_
  - [x]* 3.5 Write property test for config redaction through the client
    - **Feature: phase-7-wandb, Property 9: Resolved config is recorded through the client with credentials dropped**
    - **Property 9: Resolved config is recorded through the client with credentials dropped**
    - **Validates: Requirements 6.1, 6.3**
  - [x] 3.6 Implement `local_wandb_dir` and `filter_commit_candidates`
    - Path rule `experiments/<experiment-id>/runs/<run-id>/wandb`; exclude `.out`/`.err` logs and `checkpoints`/`wandb` directories from commit candidates
    - _Requirements: 7.1, 16.3_
  - [x]* 3.7 Write property test for the local W&B directory path rule
    - **Feature: phase-7-wandb, Property 11: Local W&B directory path rule**
    - **Property 11: Local W&B directory path rule**
    - **Validates: Requirements 7.1**
  - [x]* 3.8 Write property test for commit-candidate exclusion
    - **Feature: phase-7-wandb, Property 23: Commit candidates exclude logs, checkpoints, and caches**
    - **Property 23: Commit candidates exclude logs, checkpoints, and caches**
    - **Validates: Requirements 16.3**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement pure parsing, status mapping, gating, and git-sha logic
  - [x] 5.1 Implement `parse_wandb_url` and `extract_run_id_from_url`
    - Match a `wandb.ai/.../runs/<id>` URL in surrounding log text and extract the run id; return None when absent (read-only, ungated)
    - _Requirements: 10.1, 10.2, 10.3_
  - [x]* 5.2 Write property test for the URL parse/extract round-trip
    - **Feature: phase-7-wandb, Property 16: W&B URL parse/extract round-trip**
    - **Property 16: W&B URL parse/extract round-trip**
    - **Validates: Requirements 10.2, 10.3**
  - [x] 5.3 Implement `map_sync_state`
    - Mode-aware total mapping: `offline` when offline, `not_started` when disabled, `synced` for completed uploads, `running` for in-progress, `sync_failed` for failed or unrecognized states
    - _Requirements: 9.2, 9.4_
  - [x]* 5.4 Write property test for sync-state mapping
    - **Feature: phase-7-wandb, Property 14: Sync-state mapping is total and mode-aware**
    - **Property 14: Sync-state mapping is total and mode-aware**
    - **Validates: Requirements 9.2, 9.4**
  - [x] 5.5 Implement `decide_mutating_action` and `record_git_sha`
    - Approval decision (`proceed` only when approval equals `approved`) for the mutating kinds (create, resume, config, finish, sync); pure mapping of a `git rev-parse HEAD` result to `(sha, warnings)` with the `unknown` fallback
    - _Requirements: 6.2, 6.4, 11.1, 11.2, 11.3, 11.4_
  - [x]* 5.6 Write property test for git-sha mapping with unknown fallback
    - **Feature: phase-7-wandb, Property 10: Git SHA mapping with unknown fallback**
    - **Property 10: Git SHA mapping with unknown fallback**
    - **Validates: Requirements 6.2, 6.4**
  - [x]* 5.7 Write property test for approval gating of mutating actions
    - **Feature: phase-7-wandb, Property 17: Mutating actions execute if and only if approved**
    - **Property 17: Mutating actions execute if and only if approved**
    - **Validates: Requirements 3.1, 3.4, 11.1, 11.2, 11.3**
  - [x]* 5.8 Write property test for ungated read-only actions
    - **Feature: phase-7-wandb, Property 18: Read-only actions are ungated**
    - **Property 18: Read-only actions are ungated**
    - **Validates: Requirements 10.1, 11.4**

- [x] 6. Implement run creation, resume, config, and group/tag orchestration
  - [x] 6.1 Implement `create_run` with approval gate and identity recording
    - Gate on approval and non-placeholder entity; create the Run through the client with the configured entity/project; record `wandb_run_id`, `wandb_url`, and `wandb_status = running`; create the `Local_Wandb_Dir` before local writes
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 7.2_
  - [x]* 6.2 Write property test for run-creation identity recording
    - **Feature: phase-7-wandb, Property 5: Run creation records identity and sets running status**
    - **Property 5: Run creation records identity and sets running status**
    - **Validates: Requirements 3.2, 3.3**
  - [x] 6.3 Implement `resume_run`
    - Resume a recorded `wandb_run_id` through the client without creating a new Run and preserve the recorded id/url; report resume-not-possible when no id is recorded
    - _Requirements: 4.1, 4.2, 4.3_
  - [x]* 6.4 Write property test for resume reuse
    - **Feature: phase-7-wandb, Property 6: Resume reuses the recorded run id without creating a new run**
    - **Property 6: Resume reuses the recorded run id without creating a new run**
    - **Validates: Requirements 4.1, 4.2, 4.3**
  - [x] 6.5 Implement `record_config` and `assign_group_tags`
    - Route the redacted resolved config through the client (approval-gated); write `wandb_group` and `wandb_tags` into the Run_Record and apply tags to the Run
    - _Requirements: 5.3, 6.1_
  - [x]* 6.6 Write unit tests for placeholder decline, resume-not-possible, and invalid mode
    - Assert online placeholder declines with exit 1 and no Run; resume with no recorded id reports resume-not-possible with no new Run; invalid mode reports a configuration error with no Run
    - _Requirements: 1.2, 2.2, 4.2_

- [x] 7. Implement sync check, comparison, and run.yaml linkage orchestration
  - [x] 7.1 Implement `check_sync`
    - Query the sync state through the client, map it with `map_sync_state`, and write `wandb_status` to the Run_Record without changing the training `status`; offline mode yields `offline`
    - _Requirements: 9.1, 9.3, 9.5_
  - [x]* 7.2 Write property test for distinct W&B status recording
    - **Feature: phase-7-wandb, Property 15: W&B status is recorded distinctly and never changes training status**
    - **Property 15: W&B status is recorded distinctly and never changes training status**
    - **Validates: Requirements 9.3, 9.5, 13.2**
  - [x] 7.3 Implement `compare_runs`
    - Fetch metrics for a single group through the client and place each Run's `wandb_run_id` and metric values in the envelope `data`; report an empty-comparison outcome when the group has no comparable Runs
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x]* 7.4 Write property test for group-scoped comparison
    - **Feature: phase-7-wandb, Property 13: Comparison is scoped to one group and reports every run**
    - **Property 13: Comparison is scoped to one group and reports every run**
    - **Validates: Requirements 8.1, 8.2**
  - [x] 7.5 Implement `write_wandb_linkage` into run.yaml
    - Write `wandb_run_id`, `wandb_url`, `wandb_group`, `wandb_tags`, `wandb_status`, `wandb_mode`, and `git_sha`; confine the write to the targeted Run's `run.yaml`; never write secrets; retain the `Local_Wandb_Dir` when `keep_local_data` is true
    - _Requirements: 7.3, 7.4, 13.1, 13.2, 13.3, 13.4_
  - [x]* 7.6 Write property test for run.yaml linkage completeness
    - **Feature: phase-7-wandb, Property 20: run.yaml linkage completeness**
    - **Property 20: run.yaml linkage completeness**
    - **Validates: Requirements 1.4, 5.3, 13.1**
  - [x]* 7.7 Write property test for write confinement to the run directory
    - **Feature: phase-7-wandb, Property 12: W&B writes are confined to the run directory**
    - **Property 12: W&B writes are confined to the run directory**
    - **Validates: Requirements 7.4, 13.4**
  - [x]* 7.8 Write property test for no-secret-in-artifacts
    - **Feature: phase-7-wandb, Property 21: Artifacts contain no secrets**
    - **Property 21: Artifacts contain no secrets**
    - **Validates: Requirements 13.3, 14.1, 14.2, 14.3**
  - [x]* 7.9 Write a unit test for the run.yaml linkage round-trip
    - Assert all linkage fields present after create/sync and no credential values written; confirm the training `status` is untouched
    - _Requirements: 13.1, 13.2, 13.3_

- [x] 8. Wire the CLI entrypoint and boundary enforcement
  - [x] 8.1 Implement `parse_args`, `main`, and command dispatch
    - Subcommands for `create`, `resume`, `config`, `sync`, `compare`; construct `RealWandbClient` only here; load settings and resolve mode (config error exits 1 with no Run); compose pure logic with the client; emit the JSON envelope and map exit codes (0/1/2); assert no Hugging Face upload and no Git commit occur
    - _Requirements: 12.2, 15.1, 15.2, 15.3, 15.4, 16.1, 16.2_
  - [x]* 8.2 Write property test for the output envelope and exit-code mapping
    - **Feature: phase-7-wandb, Property 22: Output envelope and exit-code mapping**
    - **Property 22: Output envelope and exit-code mapping**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.4**
  - [x]* 8.3 Write property test for injected-boundary discipline
    - **Feature: phase-7-wandb, Property 19: Injected-boundary discipline**
    - **Property 19: Injected-boundary discipline**
    - **Validates: Requirements 8.4, 9.1, 12.1, 12.3**
  - [x]* 8.4 Write an integration test for the end-to-end CLI flow with a FakeWandbClient
    - Drive create → config → sync → compare with an injected `FakeWandbClient`; assert envelope shape, exit codes, approval gating, no real W&B/network I/O, and tmp_path-only writes
    - _Requirements: 12.3, 15.1_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for a faster MVP; core implementation tasks are never optional.
- Each task references specific requirement sub-clauses for traceability.
- Property test tasks each name a design property and run a minimum of 100 iterations with the tag `**Feature: phase-7-wandb, Property N: ...**`.
- All W&B API, network, and filesystem-mutating W&B I/O passes through the injected `WandbClient`; tests use `FakeWandbClient` only and never touch the real W&B API or network.
- All test writes are confined to `tmp_path`; the example experiment stays read-only.
- Mutating W&B actions (create, resume, config update, finish, sync) require explicit user approval (`approval.status == approved`) and are never exercised against real W&B by tests; the placeholder entity in online mode is declined (exit 1) and never crashes.
- Phase 8 Hugging Face Hub uploads are out of scope and no Git commit occurs in Phase 7.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "1.5", "2.1", "3.1", "3.4", "3.6", "5.1", "5.3", "5.5"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "3.2", "3.3", "3.5", "3.7", "3.8", "5.2", "5.4", "5.6", "5.7", "5.8"] },
    { "id": 3, "tasks": ["6.1", "6.3", "6.5", "7.1", "7.3", "7.5"] },
    { "id": 4, "tasks": ["6.2", "6.4", "6.6", "7.2", "7.4", "7.6", "7.7", "7.8", "7.9"] },
    { "id": 5, "tasks": ["8.1"] },
    { "id": 6, "tasks": ["8.2", "8.3", "8.4"] }
  ]
}
```
