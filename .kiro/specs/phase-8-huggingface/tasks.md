# Implementation Plan: Phase 8 — Hugging Face Hub Publication

## Overview

Implement `publish_hf.py` in `.agents/skills/train-llm/scripts/` as a deterministic helper that adds the Hugging Face Hub publication layer on top of the Phase 5 local executor (`run_local.py`), the Phase 6 Slurm submitter (`submit_slurm.py`), and the Phase 7 W&B tracker (`track_wandb.py`). The language is Python (the design uses Python throughout, so no language selection is required). Each task builds incrementally: the module skeleton, data models, and the injected `HfClient` boundary first; then the pure logic (settings loading, placeholder detection, push-eligibility decision, repo-id/URL construction, visibility resolution and guard, model-card assembly, status mapping, approval gating, config/secret redaction, commit-candidate filtering); then the thin orchestration (verify checkpoint, ensure repo, upload, record revision, verify upload, draft model card, write run.yaml linkage); then the CLI entrypoint with the `verify`/`ensure-repo`/`upload`/`verify-upload`/`card`/`publish` subcommands and boundary enforcement. Property tests reference design properties and run with `pytest` + `PyYAML` + `Hypothesis` through a disposable `uv` environment. All test writes stay under `tmp_path`; the example experiment stays read-only; no task performs a real Hugging Face Hub API call, upload, verification, or network I/O; mutating Hub actions require explicit user approval and are never exercised against the real Hub by tests; checkpoints are never added to Git.

## Tasks

- [x] 1. Set up module skeleton, data models, and the injected Hub boundary
  - [x] 1.1 Create `publish_hf.py` scaffolding and core data models
    - Add module docstring, JSON-envelope helper `_result(status, message, data, errors, warnings)`, exit-code contract (0/1/2), and the `CheckpointKind`, `Visibility`, `VisDecision`, `HfStatus`, and `ActionDecision` enums
    - Define `HfSettings`, `PushDecision`, `UploadOutcome`, `RepoInfo`, and the orchestration result dataclasses (`CheckpointResult`, `RepoResult`, `UploadResult`, `RevisionResult`, `VerifyResult`, `CardResult`); define `PLACEHOLDER_NAMESPACE`, `VALID_POLICIES`, and `MUTATING_KINDS` constants
    - _Requirements: 15.1, 13.1_
  - [x] 1.2 Define the `HfClient` protocol and both implementations
    - Add the `HfClient` protocol (`repo_exists`, `create_repo`, `set_visibility`, `upload_checkpoint`, `file_exists_at_revision`), `RealHfClient` (production, wraps `huggingface_hub` with a lazy import, constructed only in `main()`), and `FakeHfClient` (scripted results, records calls, raises on unscripted operations)
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  - [x] 1.3 Implement `load_hf_settings` from project-plan.md frontmatter
    - Parse YAML frontmatter into `HfSettings` (namespace, private, push_policy); default `private` to `true` when absent; never prompt for stable settings
    - _Requirements: 1.1, 1.4_
  - [x]* 1.4 Write unit tests for settings loading and the fake-client guard
    - Example test parsing a `project-plan.md` fixture into `HfSettings`; guard test asserting `RealHfClient` / the `huggingface_hub` SDK is never constructed or imported in tests
    - _Requirements: 1.1, 1.4, 12.2, 12.3_
  - [x]* 1.5 Write property test for settings loading
    - **Feature: phase-8-huggingface, Property 1: Settings loading reflects the project plan with private defaulting true**
    - **Property 1: Settings loading reflects the project plan with private defaulting true**
    - **Validates: Requirements 1.1, 1.4**

- [x] 2. Implement placeholder tolerance and push-eligibility logic
  - [x] 2.1 Implement `is_placeholder_namespace` and `decide_push`
    - Detect the `TODO-set-before-phase-8` placeholder; derive push eligibility purely from the policy and checkpoint kind, returning a `config_error` for an unknown policy and the full policy×kind matrix otherwise (`never`→none; `final_only`→final; `final_and_milestone`→final/milestone; `milestone`→milestone/final; `every_save`→all), so `intermediate` is eligible only under `every_save`
    - _Requirements: 1.2, 2.1, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - [x]* 2.2 Write property test for invalid-push-policy configuration error
    - **Feature: phase-8-huggingface, Property 2: Invalid push policy is a configuration error with no mutating action**
    - **Property 2: Invalid push policy is a configuration error with no mutating action**
    - **Validates: Requirements 1.2**
  - [x]* 2.3 Write property test for placeholder-namespace tolerance
    - **Feature: phase-8-huggingface, Property 3: Placeholder-namespace tolerance**
    - **Property 3: Placeholder-namespace tolerance**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
  - [x]* 2.4 Write property test for push eligibility across the policy × kind matrix
    - **Feature: phase-8-huggingface, Property 4: Push eligibility across the full policy × kind matrix**
    - **Property 4: Push eligibility across the full policy × kind matrix**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

- [x] 3. Implement pure repo-id, URL, and visibility logic
  - [x] 3.1 Implement `build_repo_id` and `build_hf_url`
    - Construct the `Hf_Repo_Id` as `<namespace>/<repo-name>` and the `Hf_Url` from the repo id with an optional revision suffix
    - _Requirements: 5.1_
  - [x]* 3.2 Write property test for repository id construction
    - **Feature: phase-8-huggingface, Property 7: Repository id construction**
    - **Property 7: Repository id construction**
    - **Validates: Requirements 5.1**
  - [x] 3.3 Implement `resolve_visibility` and `guard_visibility_change`
    - Resolve visibility from `Hf_Private`; permit a private→public change only when it is an explicit request whose approval status equals `approved`, declining a silent public change otherwise, so a private repo is never silently made public
    - _Requirements: 6.1, 6.2, 6.3_
  - [x]* 3.4 Write property test for the never-silently-public visibility guard
    - **Feature: phase-8-huggingface, Property 9: Visibility policy never silently makes a private repo public**
    - **Property 9: Visibility policy never silently makes a private repo public**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 4. Implement pure status mapping, gating, redaction, and safety filters
  - [x] 4.1 Implement `map_hf_status` and `decide_mutating_action`
    - Total mapping of a raw Hub state to an `HfStatus` (`uploaded`/`completed`→uploaded, `verified`/`located`→verified, `failed`/`error`/unrecognized→upload_failed); approval decision (`proceed` only when approval equals `approved`) for the mutating kinds (create_repo, set_visibility, upload, revision)
    - _Requirements: 7.1, 7.2, 7.5, 11.1, 11.2, 11.3_
  - [x]* 4.2 Write property test for approval gating of mutating Hub actions
    - **Feature: phase-8-huggingface, Property 10: Mutating Hub actions execute if and only if approved**
    - **Property 10: Mutating Hub actions execute if and only if approved**
    - **Validates: Requirements 7.1, 7.2, 7.5, 11.1, 11.2, 11.3**
  - [x]* 4.3 Write property test for ungated read-only and local-only actions
    - **Feature: phase-8-huggingface, Property 11: Read-only and local-only actions are ungated**
    - **Property 11: Read-only and local-only actions are ungated**
    - **Validates: Requirements 11.4**
  - [x] 4.4 Implement `redact_config`, `redact_secrets`, and `build_model_card`
    - Drop every credential-like value from config (recursively) and mask credential values in reported text (reuse Phase 5/6/7 names-only approach); assemble the model-card markdown purely from the `Hf_Repo_Id`, `Checkpoint_Kind`, and redacted resolved config with no network I/O and no `Credential_Key` value
    - _Requirements: 10.1, 10.2, 10.4, 14.1, 14.2, 14.3_
  - [x]* 4.5 Write property test for model-card local assembly
    - **Feature: phase-8-huggingface, Property 15: Model card contents are assembled locally without approval**
    - **Property 15: Model card contents are assembled locally without approval**
    - **Validates: Requirements 10.1, 10.2, 10.3**
  - [x]* 4.6 Write property test for no-secret-in-artifacts
    - **Feature: phase-8-huggingface, Property 19: Artifacts contain no secrets**
    - **Property 19: Artifacts contain no secrets**
    - **Validates: Requirements 10.4, 13.3, 14.1, 14.2, 14.3**
  - [x] 4.7 Implement `filter_commit_candidates`
    - Exclude `.out`/`.err` logs and `checkpoints`/`wandb` directories from commit candidates, keeping checkpoints routed to the Hub rather than Git
    - _Requirements: 16.3, 16.4_
  - [x]* 4.8 Write property test for commit-candidate exclusion
    - **Feature: phase-8-huggingface, Property 21: Commit candidates exclude logs, checkpoints, and caches, and checkpoints go to the Hub**
    - **Property 21: Commit candidates exclude logs, checkpoints, and caches, and checkpoints go to the Hub**
    - **Validates: Requirements 16.3, 16.4**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement checkpoint verification, repository, and upload orchestration
  - [x] 6.1 Implement `verify_checkpoint`
    - Verify the `Checkpoint_Path` exists on the local filesystem as a read-only, ungated action; report a missing-checkpoint outcome and invoke no `Mutating_Hub_Action` when absent; record the path as verified and proceed when present
    - _Requirements: 4.1, 4.2, 4.3_
  - [x]* 6.2 Write property test for local checkpoint verification gating the upload
    - **Feature: phase-8-huggingface, Property 6: Local checkpoint verification gates the upload**
    - **Property 6: Local checkpoint verification gates the upload**
    - **Validates: Requirements 4.1, 4.2, 4.3**
  - [x] 6.3 Implement `ensure_repo` with approval gate and visibility
    - Query the Hub for the `Hf_Repo_Id` through the client; create the repository (with visibility set from `resolve_visibility`) only when it is missing and approval equals `approved`; decline creation with an approval-required outcome when it is missing and not approved
    - _Requirements: 5.2, 5.3, 5.4_
  - [x]* 6.4 Write property test for repository existence check and approval-gated create
    - **Feature: phase-8-huggingface, Property 8: Repository existence check and approval-gated create**
    - **Property 8: Repository existence check and approval-gated create**
    - **Validates: Requirements 5.2, 5.3, 5.4**
  - [x] 6.5 Implement `upload_checkpoint` with approval gate and skip-by-policy handling
    - Gate the upload on approval, non-placeholder namespace, and push eligibility; set `hf_status = skipped_by_policy` with no mutating action and exit 1 when ineligible; upload the `Checkpoint_Path` to the `Hf_Repo_Id` through the client and set `hf_status = uploaded` on completion; set `hf_status = upload_failed` without changing the training `status` on an upload error; decline with an approval-required outcome (exit 1) when not approved
    - _Requirements: 3.7, 7.1, 7.2, 7.3, 7.4, 7.5_
  - [x]* 6.6 Write property test for policy-skipped checkpoints
    - **Feature: phase-8-huggingface, Property 5: Ineligible checkpoints are skipped by policy**
    - **Property 5: Ineligible checkpoints are skipped by policy**
    - **Validates: Requirements 3.7**
  - [x]* 6.7 Write unit tests for placeholder decline, policy skip, missing checkpoint, and repo-missing-not-approved decline
    - Assert the mutating path declines with exit 1 and no client call for the placeholder namespace; an ineligible checkpoint sets `skipped_by_policy` with no upload; a missing checkpoint reports missing-checkpoint with no mutating action; a missing repo without approval declines creation
    - _Requirements: 2.2, 3.7, 4.2, 5.4_

- [x] 7. Implement revision recording, upload verification, model-card draft, and run.yaml linkage
  - [x] 7.1 Implement `record_revision`
    - Obtain the `Hf_Revision` for a completed upload through the client, record the `Hf_Repo_Id`, `Hf_Revision`, and `Hf_Url` in `run.yaml`, and set `hf_status = upload_failed` with a revision-unavailable outcome when no parseable revision is returned
    - _Requirements: 8.1, 8.2, 8.3_
  - [x]* 7.2 Write property test for completed-upload identity and revision recording
    - **Feature: phase-8-huggingface, Property 12: Completed upload records repository identity and revision**
    - **Property 12: Completed upload records repository identity and revision**
    - **Validates: Requirements 7.3, 8.1, 8.2**
  - [x]* 7.3 Write property test for upload/revision failure keeping the training status
    - **Feature: phase-8-huggingface, Property 13: Upload or revision failure sets upload_failed and never changes the training status**
    - **Property 13: Upload or revision failure sets upload_failed and never changes the training status**
    - **Validates: Requirements 7.4, 8.3, 9.4, 13.2, 16.5**
  - [x] 7.4 Implement `verify_upload`
    - Confirm through the client that the uploaded checkpoint is locatable at the recorded `Hf_Revision` in the `Hf_Repo_Id`; set `hf_status = verified` when located; set `hf_status = upload_failed`, signal the Experiment must not be marked complete, and exit 1 when not located
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x]* 7.5 Write property test for verify-by-revision located/unlocatable mapping
    - **Feature: phase-8-huggingface, Property 14: Verify-by-revision maps located to verified and unlocatable to upload_failed**
    - **Property 14: Verify-by-revision maps located to verified and unlocatable to upload_failed**
    - **Validates: Requirements 9.1, 9.2, 9.3**
  - [x] 7.6 Implement `draft_model_card` and `write_hf_linkage`
    - Write the assembled model card to the `Model_Card_Path` (local-only, ungated) and record the path; write `hf_repo_id`, `hf_revision`, `hf_url`, `hf_status`, `hf_private`, and `model_card_path` into the targeted Run's `run.yaml` without changing the training `status` and without writing any credential value; confine every write to the targeted Run's directory
    - _Requirements: 10.3, 13.1, 13.2, 13.3, 13.4_
  - [x]* 7.7 Write property test for run.yaml linkage completeness
    - **Feature: phase-8-huggingface, Property 17: run.yaml linkage completeness**
    - **Property 17: run.yaml linkage completeness**
    - **Validates: Requirements 1.3, 6.4, 10.3, 13.1**
  - [x]* 7.8 Write property test for write confinement to the targeted run
    - **Feature: phase-8-huggingface, Property 18: Hub linkage writes are confined to the targeted run**
    - **Property 18: Hub linkage writes are confined to the targeted run**
    - **Validates: Requirements 13.4**
  - [x]* 7.9 Write unit tests for verify-upload failure and the run.yaml linkage round-trip
    - Assert an unlocatable revision sets `upload_failed`, signals experiment-not-complete, and exits 1 while leaving the training `status` untouched; assert all linkage fields present after publish with no credential values written
    - _Requirements: 9.3, 9.4, 13.1, 13.2, 13.3_

- [x] 8. Wire the CLI entrypoint and boundary enforcement
  - [x] 8.1 Implement `parse_args`, `main`, and command dispatch
    - Subcommands for `verify`, `ensure-repo`, `upload`, `verify-upload`, `card`, and `publish` (the full sequence verify → ensure-repo → upload → record revision → verify-upload → card); construct `RealHfClient` only here with a lazy `huggingface_hub` import; load settings, reject an invalid push policy (exit 1, no mutating action), and decline a placeholder namespace for mutating actions (exit 1); compose pure logic with the client; emit the JSON envelope and map exit codes (0/1/2); assert no W&B Run is created and no Git commit occurs
    - _Requirements: 12.2, 15.1, 15.2, 15.3, 15.4, 16.1, 16.2_
  - [x]* 8.2 Write property test for the output envelope and exit-code mapping
    - **Feature: phase-8-huggingface, Property 20: Output envelope and exit-code mapping**
    - **Property 20: Output envelope and exit-code mapping**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.4**
  - [x]* 8.3 Write property test for injected-boundary discipline
    - **Feature: phase-8-huggingface, Property 16: Injected-boundary discipline**
    - **Property 16: Injected-boundary discipline**
    - **Validates: Requirements 12.1, 12.3, 12.4**
  - [x]* 8.4 Write an integration test for the end-to-end publish flow with a FakeHfClient
    - Drive verify → ensure-repo → upload → verify-upload → card with an injected `FakeHfClient`; assert envelope shape, exit codes, approval gating, no real Hub/network I/O, and tmp_path-only writes; include an injection guard asserting the `huggingface_hub` SDK is imported and `RealHfClient` constructed only within `main()`'s real-client path
    - _Requirements: 12.2, 12.3, 15.1_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for a faster MVP; core implementation tasks are never optional.
- Each task references specific requirement sub-clauses for traceability.
- Property test tasks each name a design property and run a minimum of 100 iterations with the tag `**Feature: phase-8-huggingface, Property N: ...**`.
- All Hugging Face Hub API, network, and filesystem-mutating Hub I/O passes through the injected `HfClient`; tests use `FakeHfClient` only and never touch the real Hub API or network.
- All test writes are confined to `tmp_path`; the example experiment stays read-only.
- Mutating Hub actions (create/ensure repository, set visibility, upload, create revision) require explicit user approval (`approval.status == approved`) and are never exercised against the real Hub by tests; the placeholder namespace declines mutating actions (exit 1) and never crashes.
- A Hub failure is recorded in `hf_status` distinctly from the training `status`, which is owned by Phase 5/6 and never changed here.
- Checkpoints are uploaded to the Hub through the `HfClient` and are never added to Git; W&B tracking stays in Phase 7 and no Git commit occurs in Phase 8.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "1.5", "2.1", "3.1", "3.3", "4.1", "4.4", "4.7"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "3.2", "3.4", "4.2", "4.3", "4.5", "4.6", "4.8"] },
    { "id": 3, "tasks": ["6.1", "6.3", "6.5"] },
    { "id": 4, "tasks": ["6.2", "6.4", "6.6", "6.7", "7.1", "7.4", "7.6"] },
    { "id": 5, "tasks": ["7.2", "7.3", "7.5", "7.7", "7.8", "7.9"] },
    { "id": 6, "tasks": ["8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3", "8.4"] }
  ]
}
```
