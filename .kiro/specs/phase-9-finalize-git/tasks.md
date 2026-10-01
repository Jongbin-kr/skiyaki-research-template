# Implementation Plan: Phase 9 — Finalize and Git

## Overview

Implement `finalize_experiment.py` in `.agents/skills/train-llm/scripts/` as a deterministic helper that adds the Finalize and Git layer on top of the Phase 5 local executor (`run_local.py`), the Phase 6 Slurm submitter (`submit_slurm.py`), the Phase 7 W&B tracker (`track_wandb.py`), and the Phase 8 Hugging Face Hub publisher (`publish_hf.py`). The language is Python (the design uses Python throughout, so no language selection is required). Each task builds incrementally: the module skeleton, data models, and the injected `GitClient` boundary first; then the pure verification logic (completeness verification, results validation, reference verification, honest-finalization assessment); then the pure documentation-assembly logic (results assembly, history-entry formatting, journal validation, project-log entry assembly and insertion); then the pure commit logic (candidate selection, exclusion filtering, credential-file scanning, commit-message assembly, approval gating, status mapping, config/secret redaction); then the thin orchestration (verify, finalize docs, propose commit, commit, write finalized marker); then the CLI entrypoint with the `verify`/`finalize`/`propose`/`commit` subcommands and boundary enforcement. Property tests reference design properties and run with `pytest` + `PyYAML` + `Hypothesis` through a disposable `uv` environment. All test writes stay under `tmp_path`; the example experiment stays read-only; no task performs a real Git commit, push, or network I/O; mutating Git actions require explicit user approval and are never exercised against a real repository by tests; checkpoints, W&B caches, and raw Slurm logs are never added to Git.

## Tasks

- [x] 1. Set up module skeleton, data models, and the injected Git boundary
  - [x] 1.1 Create `finalize_experiment.py` scaffolding and core data models
    - Add module docstring, JSON-envelope helper `_result(status, message, data, errors, warnings)`, exit-code contract (0/1/2), and the `FinalizeStatus` and `ActionDecision` enums
    - Define `LoadedDocs`, `CompletenessResult`, `ResultsValidation`, `ReferenceResult`, `HonestyResult`, `JournalValidation`, `StageOutcome`, `CommitOutcome`, and `PushOutcome` dataclasses; define `_REQUIRED`, `MUTATING_KINDS`, `_EXCLUDED_SUFFIX`, `_EXCLUDED_DIRS`, and `_CREDENTIAL_FILE_PATTERNS` constants
    - _Requirements: 16.1, 14.2_
  - [x] 1.2 Define the `GitClient` protocol and both implementations
    - Add the `GitClient` protocol (`status`, `stage`, `commit`, `push`), `RealGitClient` (production, wraps `git` via subprocess with `git status --porcelain`, `git add -- <paths>`, `git commit -m`, `git push -u <remote> <branch>`, stages specific files by name, preserves hooks, never modifies Git config, constructed only in `main()`), and `FakeGitClient` (scripted results, records every call, raises on unscripted operations)
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  - [x] 1.3 Implement `load_documents` for the experiment directory
    - Read `plan.md`, `jobs/*.yaml`, `runs/*/run.yaml`, `results.yaml`, `history.md`, `journal.md`, and `project-log.md` once into a `LoadedDocs` bundle (presence flags, parsed frontmatter, approval status, parsed results, run-id-keyed linkage, journal text, project-log text); never re-ask stable settings; read-only
    - _Requirements: 1.1, 14.1_
  - [x]* 1.4 Write unit tests for document loading and the fake-client guard
    - Example test loading a fixture experiment directory into `LoadedDocs`; guard test asserting `RealGitClient` and `git` via subprocess are never constructed or invoked in tests
    - _Requirements: 1.1, 12.2, 12.3_

- [x] 2. Implement pure verification logic
  - [x] 2.1 Implement `verify_completeness`
    - Derive the completeness result from already-loaded presence flags: require the Plan, job configuration files, at least one run directory, the Results_File, the History_File, the Journal_File, and the Project_Log; list every missing required file; report approval granted if and only if the Approval_Status equals `approved`; perform no I/O
    - _Requirements: 1.1, 1.2, 1.4_
  - [x] 2.2 Implement `validate_results` with numeric-metric check
    - Report the best run as existing if and only if `best_run.run_id` matches an existing run directory; report the Primary_Metric numeric if and only if its value is a real number and not a boolean; perform no I/O
    - _Requirements: 2.1, 2.3_
  - [x] 2.3 Implement `verify_references`
    - Report every claimed metric backed if and only if it has a recorded value, and every Artifact_Reference verified if and only if it exists in the Linkage_Fields or on the filesystem (presence flags); report success claimable only when there is at least one verified Artifact_Reference and a verified numeric Primary_Metric value; perform no I/O
    - _Requirements: 3.1, 3.2, 3.4_
  - [x] 2.4 Implement `assess_honesty`
    - A required run with Run_Status `failed` requires documentation and never reports success criteria met; any required Hub upload with `hf_status` other than `verified` blocks experiment completion; record the partial status; perform no I/O
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  - [x]* 2.5 Write property test for pure completeness verification
    - **Feature: phase-9-finalize-git, Property 1: Completeness verification is pure and reports missing files**
    - **Property 1: Completeness verification is pure and reports missing files**
    - **Validates: Requirements 1.1, 1.2, 1.4**
  - [x]* 2.6 Write property test for results referencing an existing run
    - **Feature: phase-9-finalize-git, Property 3: Results reference an existing run**
    - **Property 3: Results reference an existing run**
    - **Validates: Requirements 2.1, 2.2**
  - [x]* 2.7 Write property test for the numeric primary metric
    - **Feature: phase-9-finalize-git, Property 4: Primary metric must be numeric**
    - **Property 4: Primary metric must be numeric**
    - **Validates: Requirements 2.3, 2.4**
  - [x]* 2.8 Write property test for conclusions referencing only verified metrics and artifacts
    - **Feature: phase-9-finalize-git, Property 5: Conclusions reference only verified metrics and artifacts**
    - **Property 5: Conclusions reference only verified metrics and artifacts**
    - **Validates: Requirements 3.1, 3.2, 3.3**
  - [x]* 2.9 Write property test for no success without a verified artifact and metric
    - **Feature: phase-9-finalize-git, Property 6: No success without a verified artifact and a verified metric**
    - **Property 6: No success without a verified artifact and a verified metric**
    - **Validates: Requirements 3.4**
  - [x]* 2.10 Write property test for a documented failed run not reporting success
    - **Feature: phase-9-finalize-git, Property 20: A required failed run is documented and success is not reported met**
    - **Property 20: A required failed run is documented and success is not reported met**
    - **Validates: Requirements 13.1, 13.2**
  - [x]* 2.11 Write property test for unverified Hub upload blocking completion
    - **Feature: phase-9-finalize-git, Property 21: Unverified Hub upload blocks completion**
    - **Property 21: Unverified Hub upload blocks completion**
    - **Validates: Requirements 13.3**
  - [x]* 2.12 Write property test for partial experiments finalized honestly
    - **Feature: phase-9-finalize-git, Property 22: Partial experiments are finalized honestly**
    - **Property 22: Partial experiments are finalized honestly**
    - **Validates: Requirements 13.4**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement pure documentation-assembly logic
  - [x] 4.1 Implement `assemble_results`
    - Assemble the Results_File content from already-loaded data: confirm `best_run`, `primary_metric`, `success`, and `completed_at`; populate the Success_Assessment with a `criteria_met` boolean and a `rationale` derived from the Plan's success criteria; surface each referenced Run_Record's Linkage_Fields; record partial status in the rationale; perform no network I/O
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 4.2 Implement `format_history_entry`
    - Build a completion entry containing a timestamp, the best run reference, the Primary_Metric value, and the Success_Assessment determination as summary records rather than full stdout/stderr logs; perform no I/O
    - _Requirements: 5.1, 5.3_
  - [x] 4.3 Implement `validate_journal`
    - Report whether the Journal_File contains a hypothesis assessment, key findings, interpretation, and recommended next experiments, and whether it is interpretive rather than only an execution log; emit a documentation warning (not a block) when the recommended-next-experiments section is absent; perform no I/O
    - _Requirements: 6.1, 6.2, 6.3_
  - [x] 4.4 Implement `build_project_log_entry` and `insert_project_log_entry`
    - Compose a concise project-level conclusion (one-line conclusion, best run reference, link to the Experiment_Dir, key metric values) constrained by a section/length limit so it does not duplicate per-run detail; insert the entry at the top in reverse-chronological order and update an existing entry for the same experiment in place rather than duplicating; perform no I/O
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [x]* 4.5 Write property test for results assembly populating required fields
    - **Feature: phase-9-finalize-git, Property 7: Results assembly populates required fields with a plan-derived rationale**
    - **Property 7: Results assembly populates required fields with a plan-derived rationale**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
  - [x]* 4.6 Write property test for the history completion entry
    - **Feature: phase-9-finalize-git, Property 8: History completion entry is a summary appended without mutation**
    - **Property 8: History completion entry is a summary appended without mutation**
    - **Validates: Requirements 5.1, 5.2, 5.3**
  - [x]* 4.7 Write property test for journal validation and the missing-next-steps warning
    - **Feature: phase-9-finalize-git, Property 9: Journal validation confirms interpretive sections and warns on missing next steps**
    - **Property 9: Journal validation confirms interpretive sections and warns on missing next steps**
    - **Validates: Requirements 6.1, 6.2, 6.3**
  - [x]* 4.8 Write property test for reverse-chronological project-log insertion
    - **Feature: phase-9-finalize-git, Property 10: Project-log entry is inserted at the top in reverse-chronological order**
    - **Property 10: Project-log entry is inserted at the top in reverse-chronological order**
    - **Validates: Requirements 7.1, 7.2**
  - [x]* 4.9 Write property test for the concise, non-duplicating project-log entry
    - **Feature: phase-9-finalize-git, Property 11: Project-log entry is concise and does not duplicate per-run detail**
    - **Property 11: Project-log entry is concise and does not duplicate per-run detail**
    - **Validates: Requirements 7.3**
  - [x]* 4.10 Write property test for updating an existing project-log entry
    - **Feature: phase-9-finalize-git, Property 12: An existing project-log entry is updated rather than duplicated**
    - **Property 12: An existing project-log entry is updated rather than duplicated**
    - **Validates: Requirements 7.4**

- [x] 5. Implement pure commit logic, gating, and redaction
  - [x] 5.1 Implement `select_commit_candidate`
    - Build the candidate file list from already-loaded path data — the Plan, the job configuration files, the Run_Record summaries, the Results_File, the History_File, the Journal_File, and the Project_Log; perform no I/O beyond reading already-loaded data
    - _Requirements: 8.1, 8.3_
  - [x] 5.2 Implement `filter_commit_candidates`
    - Exclude model checkpoints (`*.pt`, `*.bin`, `*.safetensors`, `*.ckpt`), the `wandb/` cache directory, raw `.out` and `.err` logs, and other Excluded_Artifacts; derive the exclusion purely with no I/O
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x] 5.3 Implement `scan_for_credential_files`
    - Return every candidate path matching a Credential_File pattern (`.env`, `*.token`, `credentials.json`); perform no I/O
    - _Requirements: 10.1, 10.2, 10.3_
  - [x] 5.4 Implement `build_commit_message`
    - Assemble the commit message including the experiment identifier, the Primary_Metric value, the Success_Assessment determination, and the surfaced Linkage_Fields; drop every Credential_Key value before rendering
    - _Requirements: 8.2_
  - [x] 5.5 Implement `decide_mutating_action` and `map_finalize_status`
    - Return `PROCEED` only when the Approval_Status equals `approved`, otherwise `DECLINE_APPROVAL`, for the mutating kinds (stage, commit, push); map accumulated verification and finalization signals to a `FinalizeStatus`; perform no I/O
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  - [x] 5.6 Implement `redact_config` and `redact_secrets`
    - Drop every Credential_Key value from config recursively while retaining non-credential entries and key names where required; mask credential values in reported text (reuse the Phase 5/6/7/8 names-only approach); perform no I/O
    - _Requirements: 15.1, 15.2, 15.3_
  - [x]* 5.7 Write property test for pure, complete commit-candidate selection
    - **Feature: phase-9-finalize-git, Property 13: Commit-candidate selection is pure and complete**
    - **Property 13: Commit-candidate selection is pure and complete**
    - **Validates: Requirements 8.1, 8.3**
  - [x]* 5.8 Write property test for the commit message surfacing identity, metric, success, and linkage
    - **Feature: phase-9-finalize-git, Property 14: Commit message surfaces experiment identity, metric, success, and linkage**
    - **Property 14: Commit message surfaces experiment identity, metric, success, and linkage**
    - **Validates: Requirements 8.2**
  - [x]* 5.9 Write property test for the commit-candidate exclusions
    - **Feature: phase-9-finalize-git, Property 15: Commit candidate excludes checkpoints, caches, and raw logs**
    - **Property 15: Commit candidate excludes checkpoints, caches, and raw logs**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
  - [x]* 5.10 Write property test for credential-file refusal declining the mutating action
    - **Feature: phase-9-finalize-git, Property 16: Credential files are refused and decline the mutating action**
    - **Property 16: Credential files are refused and decline the mutating action**
    - **Validates: Requirements 10.1, 10.2, 10.3**
  - [x]* 5.11 Write property test for approval-gated mutating actions proposing otherwise
    - **Feature: phase-9-finalize-git, Property 17: Mutating Git actions execute if and only if approved, proposing otherwise**
    - **Property 17: Mutating Git actions execute if and only if approved, proposing otherwise**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.5**
  - [x]* 5.12 Write property test for ungated read-only and local-only actions
    - **Feature: phase-9-finalize-git, Property 18: Read-only and local-only actions are ungated**
    - **Property 18: Read-only and local-only actions are ungated**
    - **Validates: Requirements 11.4**
  - [x]* 5.13 Write property test for no-secret-in-artifacts redaction
    - **Feature: phase-9-finalize-git, Property 24: Artifacts contain no secrets**
    - **Property 24: Artifacts contain no secrets**
    - **Validates: Requirements 15.1, 15.2, 15.3**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement orchestration composing pure logic with the Git client
  - [x] 7.1 Implement `verify` orchestration
    - Compose `verify_completeness`, `validate_results`, and `verify_references` over the loaded documents; report a blocked-finalization outcome identifying the missing file (exit 1) when a required file is missing, an invalid-reference outcome (exit 1) when the best run does not exist, an incomplete-results outcome (exit 1) when the metric is missing or non-numeric, and an unverified-reference outcome (exit 1) when a reference cannot be verified; read-only
    - _Requirements: 1.3, 2.2, 2.4, 3.3_
  - [x] 7.2 Implement `finalize_docs` and `write_finalized_marker`
    - Assemble `results.yaml`, append the `history.md` completion entry without modifying prior entries, validate `journal.md`, update `project-log.md`, and write the Finalized_Marker to the Plan while leaving every training Run_Status unchanged; surface the Phase 5–8 Linkage_Fields; local writes only, no Git
    - _Requirements: 5.2, 14.1, 14.2, 14.3_
  - [x] 7.3 Implement `propose_commit`
    - Select, filter, and credential-scan the candidate and draft the commit message; refuse to stage and report a security-review outcome declining the Mutating_Git_Action (exit 1) when a Credential_File is present; present the Commit_Candidate as a proposal without invoking the `GitClient`; read-only
    - _Requirements: 10.2, 10.3, 11.5_
  - [x] 7.4 Implement `commit` orchestration through the Git client
    - Call `decide_mutating_action` before any stage, commit, or push; on `DECLINE_APPROVAL` present the proposal and exit 1 without touching the `GitClient`; on `PROCEED` stage the filtered candidate, create the commit, and optionally push through the injected `GitClient`
    - _Requirements: 11.1, 11.2, 11.3, 12.1_
  - [x]* 7.5 Write property test for injected-boundary discipline
    - **Feature: phase-9-finalize-git, Property 19: Injected-boundary discipline**
    - **Property 19: Injected-boundary discipline**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4**
  - [x]* 7.6 Write property test for linkage surfacing and the finalized marker leaving run status unchanged
    - **Feature: phase-9-finalize-git, Property 23: Linkage is surfaced and the finalized marker never changes run status**
    - **Property 23: Linkage is surfaced and the finalized marker never changes run status**
    - **Validates: Requirements 14.1, 14.2, 14.3**
  - [x]* 7.7 Write unit tests for blocked finalization, invalid reference, unverified reference, and credential-file refusal
    - Assert a missing required file reports blocked-finalization and exits 1; an invalid `best_run.run_id` reports invalid-reference and exits 1; an unverified metric or artifact reference does not mark the experiment successful and exits 1; a Credential_File in the candidate is refused with a security-review outcome, declines the Mutating_Git_Action, and exits 1 with no `GitClient` call
    - _Requirements: 1.3, 2.2, 3.3, 10.2, 10.3_
  - [x]* 7.8 Write unit tests for honest partial finalization and project-log dedup
    - Assert a required run with Run_Status `failed` is confirmed documented, success criteria are not reported met, and an unverified `hf_status` leaves the experiment not complete with an incomplete-experiment outcome; assert `insert_project_log_entry` updates an existing entry for the same experiment rather than duplicating; assert the `history.md` append preserves prior entries
    - _Requirements: 13.1, 13.2, 13.3, 5.2, 7.4_

- [x] 8. Wire the CLI entrypoint and boundary enforcement
  - [x] 8.1 Implement `parse_args`, `main`, and command dispatch
    - Subcommands for `verify`, `finalize`, `propose`, and `commit`; construct `RealGitClient` only here; load documents, compose the pure logic with the client, write the finalization artifacts and Finalized_Marker, present or execute the approval-gated Commit_Candidate, emit the JSON envelope, and map exit codes (0 verified/finalized/proposal-ready/committed, 1 declined, 2 runtime); assert no training job, Slurm submission, W&B Run, or Hub upload occurs
    - _Requirements: 12.2, 16.1, 16.2, 16.3, 16.4, 17.1, 17.2, 17.3, 17.4, 17.5_
  - [x]* 8.2 Write property test for the output envelope and exit-code mapping
    - **Feature: phase-9-finalize-git, Property 25: Output envelope and exit-code mapping**
    - **Property 25: Output envelope and exit-code mapping**
    - **Validates: Requirements 16.1, 16.2, 16.3, 16.4**
  - [x]* 8.3 Write property test for respected phase boundaries
    - **Feature: phase-9-finalize-git, Property 26: Phase boundaries are respected**
    - **Property 26: Phase boundaries are respected**
    - **Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5**
  - [x]* 8.4 Write property test for blocked finalization on a missing file
    - **Feature: phase-9-finalize-git, Property 2: Missing required file blocks finalization**
    - **Property 2: Missing required file blocks finalization**
    - **Validates: Requirements 1.3**
  - [x]* 8.5 Write an integration test for the end-to-end verify → finalize → propose → commit flow with a FakeGitClient
    - Drive verify → finalize → propose → commit with an injected `FakeGitClient`; assert envelope shape, exit codes, approval gating (propose-only when not approved vs committed after approval), no real Git commit/push or network I/O, and tmp_path-only writes; include an injection guard asserting `git` via subprocess and `RealGitClient` are reachable only within `main()`'s real-client path
    - _Requirements: 11.2, 11.3, 12.2, 12.3, 16.1_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for a faster MVP; core implementation tasks are never optional.
- Each task references specific requirement sub-clauses for traceability.
- Property test tasks each name a design property and run a minimum of 100 iterations with the tag `**Feature: phase-9-finalize-git, Property N: ...**`; there is one property-based test per design property (26 total).
- All Git operations, network calls, and filesystem-mutating Git actions pass through the injected `GitClient`; tests use `FakeGitClient` only and never touch real `git` or the network.
- All test writes are confined to `tmp_path`; the example experiment under `experiments/example-lora-rank-ablation/` stays read-only.
- Mutating Git actions (stage, commit, push) require explicit user approval (`approval.status == approved`) and are never exercised against a real repository by tests; without approval the Commit_Candidate is presented as a proposal and the task exits 1.
- The Finalized_Marker is written only to the Plan and never changes any training Run_Status, which is owned by Phase 5/6.
- Checkpoints (`*.pt`, `*.bin`, `*.safetensors`, `*.ckpt`), the `wandb/` cache, and raw `.out`/`.err` logs are excluded from the commit candidate; credential-bearing files (`.env`, `*.token`, `credentials.json`) are refused; no secret, token, or credential value is ever written to any artifact.
- Phase 9 runs no training, submits no Slurm job, creates no W&B Run, and uploads no checkpoint to the Hub.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "2.1", "2.2", "2.3", "2.4"] },
    { "id": 2, "tasks": ["2.5", "2.6", "2.7", "2.8", "2.9", "2.10", "2.11", "2.12"] },
    { "id": 3, "tasks": ["4.1", "4.2", "4.3", "4.4"] },
    { "id": 4, "tasks": ["4.5", "4.6", "4.7", "4.8", "4.9", "4.10"] },
    { "id": 5, "tasks": ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6"] },
    { "id": 6, "tasks": ["5.7", "5.8", "5.9", "5.10", "5.11", "5.12", "5.13"] },
    { "id": 7, "tasks": ["7.1", "7.2", "7.3", "7.4"] },
    { "id": 8, "tasks": ["7.5", "7.6", "7.7", "7.8"] },
    { "id": 9, "tasks": ["8.1"] },
    { "id": 10, "tasks": ["8.2", "8.3", "8.4", "8.5"] }
  ]
}
```
