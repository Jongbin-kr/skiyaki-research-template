# Requirements Document

## Introduction

Phase 9 of the Codex-native AI/ML Research Workspace roadmap adds the **Finalize and Git** layer on top of the Phase 5 local-execution helper (`run_local.py`), the Phase 6 SSH/Slurm submission helper (`submit_slurm.py`), the Phase 7 W&B tracking helper (`track_wandb.py`), and the Phase 8 Hugging Face Hub publication helper (`publish_hf.py`). Phase 9 is the finalize layer that aggregates the `run.yaml` linkage data produced by Phases 5 through 8 and completes experiment documentation: it assembles and validates `results.yaml`, appends a final completion entry to `history.md`, writes or validates `journal.md` (interpretive analysis and next steps), and adds a reverse-chronological project-level conclusion to `project-log.md`. Phase 9 then selects a Git commit candidate — the list of files to commit and the commit message — and proposes it, but never creates a commit or pushes without explicit user approval. Per the roadmap completion criteria, conclusions reference actual recorded metrics and verified artifacts (no success is claimed without a verified artifact or metric reference), the project log does not duplicate experiment detail, and no commit is created before explicit user approval.

Phase 9 is deliberately bounded. It is governed by the existing `finalize-experiment` skill (`.agents/skills/finalize-experiment/SKILL.md`) and its `completion-checklist.md`, which are the behavioral source of truth; Phase 9 implements their verification as a deterministic helper, realizing the `verify_completion.py` idea that the checklist defers to a future script. All stable settings (for example the W&B entity and project, the Hugging Face namespace) continue to be read from the repository `project-plan.md` frontmatter and are never re-asked. Real mutating Git actions — staging files, creating a commit, and pushing — require explicit user approval (the experiment `plan.md` `approval.status` must equal `approved`), the same approval gate used in Phase 5, Phase 6, Phase 7, and Phase 8. Read-only and local-only actions — reading `run.yaml`, `results.yaml`, `plan.md`, `history.md`, `journal.md`, and `project-log.md`; validating documentation; drafting the commit message; and selecting the commit candidate — are non-mutating and do not require approval.

The design separates pure logic (no I/O: completeness verification over already-loaded data, metric and artifact reference checks, commit-candidate selection and exclusion filtering, project-log dedup and length enforcement, commit-message assembly, status mapping, redaction, output-envelope assembly) from a single injected impure boundary. All Git operations and any filesystem-mutating or network action pass through one `Git_Client` protocol, with a `Real_Git_Client` wrapping `git` via subprocess, constructed only in `main()` for production, and a `Fake_Git_Client` used in tests, so that no real Git commit, no push, and no network access ever occurs during automated tests. A failed or partial experiment is finalized honestly: a required run that failed is documented in `history.md` and `journal.md`, success criteria are not reported as met, and if a required Hub upload is not verified (Phase 8 `hf_status` not equal to `verified`) the Experiment is not marked complete. Generated artifacts never contain secrets, tokens, or credential values, reusing the Phase 5/6/7/8 names-only redaction approach, and the commit security review refuses to stage credential-bearing files (for example `.env`, `*.token`, `credentials.json`). The commit candidate reuses the Phase 6/7/8 exclusion of model checkpoints (`*.pt`, `*.bin`, `*.safetensors`, `*.ckpt`), W&B caches (`wandb/`), raw Slurm logs (`*.out`, `*.err`), and other large artifacts. The helper follows the Phase 5/6/7/8 output contract: a JSON envelope `{status, message, data, errors, warnings}` on stdout with exit code 0 (verified/finalized/proposal-ready, or committed after approval), 1 (declined), or 2 (runtime error). Phase 9 does not run training, submit Slurm jobs, call W&B, or upload to the Hub.

This document specifies the behavior of the Phase 9 finalize layer, implemented as a deterministic helper (`finalize_experiment.py`) in `.agents/skills/train-llm/scripts/` alongside `initialize_run.py`, `run_local.py`, `submit_slurm.py`, `track_wandb.py`, and `publish_hf.py`, with pure logic separated from a single injected Git client boundary.

## Glossary

- **Finalizer**: The Phase 9 component (`finalize_experiment.py`) that verifies experiment completeness, assembles and validates documentation, selects a Git commit candidate, and proposes a commit without creating it.
- **Git_Client**: The single injected interface through which every Git operation, network call, and filesystem-mutating Git action passes. The production implementation is `Real_Git_Client`, constructed only in `main()`; the test implementation is `Fake_Git_Client`.
- **Real_Git_Client**: The production `Git_Client` implementation that wraps `git` via subprocess, performs real Git and network operations, and is instantiated only within `main()`.
- **Fake_Git_Client**: The test `Git_Client` implementation that simulates Git behavior in memory so that no real Git commit, push, or network access occurs during tests.
- **Local_Executor**: The existing Phase 5 component (`run_local.py`) that runs eligible local jobs and records their outcomes.
- **Slurm_Submitter**: The existing Phase 6 component (`submit_slurm.py`) that submits jobs to Slurm and links them to the Harness Run.
- **Wandb_Tracker**: The existing Phase 7 component (`track_wandb.py`) that tracks W&B Runs and links them to the Harness Run.
- **Hf_Publisher**: The existing Phase 8 component (`publish_hf.py`) that publishes checkpoints to the Hugging Face Hub and links them to the Harness Run.
- **Completion_Checklist**: The verification requirements defined in `.agents/skills/finalize-experiment/references/completion-checklist.md`, treated as the behavioral source of truth for finalization.
- **Experiment_Dir**: The experiment directory `experiments/<experiment-id>/` containing the plan, jobs, runs, and documentation.
- **Plan**: The experiment `plan.md` file whose YAML frontmatter supplies experiment metadata, success criteria, and the approval status.
- **Approval_Status**: The `approval.status` field in the experiment `plan.md`; a Mutating_Git_Action proceeds only when the value equals `approved`.
- **Run_Record**: A `run.yaml` metadata file inside a Harness Run directory, carrying the Phase 5 through Phase 8 linkage fields.
- **Run_Status**: The Harness Run lifecycle state recorded in a Run_Record (for example `succeeded`, `failed`), owned by Phases 5 and 6 and never changed by the Finalizer.
- **Linkage_Fields**: The Phase 5 through Phase 8 fields surfaced from each Run_Record, including `status`, `slurm_job_id`, `wandb_run_id`, `wandb_url`, `wandb_status`, `hf_repo_id`, `hf_revision`, and `hf_status`.
- **Hf_Status**: The Hugging Face publication state recorded in a Run_Record by Phase 8, one of `not_started`, `skipped_by_policy`, `uploaded`, `verified`, or `upload_failed`.
- **Results_File**: The `results.yaml` file in the Experiment_Dir that records the best run, primary metric, success assessment, and artifact references.
- **Primary_Metric**: The experiment's primary metric, recorded in the Results_File with a name, a numeric value, and a direction.
- **Success_Assessment**: The documented determination of whether the experiment's success criteria were met, with a rationale.
- **Artifact_Reference**: A reference in the Results_File or documentation to a checkpoint, a W&B Run, a Hub revision, or another produced artifact.
- **History_File**: The `history.md` file in the Experiment_Dir containing chronological execution records.
- **Journal_File**: The `journal.md` file in the Experiment_Dir containing interpretive analysis and recommended next experiments.
- **Project_Log**: The repository-root `project-log.md` file containing reverse-chronological, project-level conclusions.
- **Project_Log_Entry**: A single concise, project-level conclusion added to the Project_Log for the finalized experiment.
- **Commit_Candidate**: The proposed set of files to commit together with the drafted commit message, presented for approval and never committed automatically.
- **Mutating_Git_Action**: Any action that changes Git state: staging files, creating a commit, and pushing.
- **Excluded_Artifact**: Any path excluded from the Commit_Candidate, including model checkpoints (`*.pt`, `*.bin`, `*.safetensors`, `*.ckpt`), W&B caches (`wandb/`), raw Slurm logs (`*.out`, `*.err`), and other large artifacts.
- **Credential_File**: A file whose name or content matches a credential-bearing pattern (for example `.env`, `*.token`, `credentials.json`).
- **Credential_Key**: A configuration or environment key whose name matches a credential-like pattern (for example `HF_TOKEN`, `WANDB_API_KEY`, `token`, `password`, `secret`), whose value is excluded from all written artifacts.
- **Finalized_Marker**: The experiment-level completion marker the Finalizer writes to the Plan (for example a `status` of `completed` or a `finalized` flag) to indicate finalization, which never changes any Run_Status.
- **Output_Envelope**: The JSON object `{status, message, data, errors, warnings}` the Finalizer writes to stdout.

## Requirements

### Requirement 1: Experiment completeness verification

**User Story:** As an AI/ML researcher, I want the helper to verify my experiment is complete before finalizing, so that incomplete experiments are never documented as finished.

#### Acceptance Criteria

1. WHEN the Finalizer begins finalization, THE Finalizer SHALL verify that the Plan, the job configuration files, at least one run directory, the Results_File, the History_File, the Journal_File, and the Project_Log exist in the expected locations.
2. WHEN the Finalizer reads the Plan, THE Finalizer SHALL confirm that the Approval_Status equals `approved`.
3. IF a required file is missing, THEN THE Finalizer SHALL report a blocked-finalization outcome identifying the missing file and SHALL exit with code 1.
4. WHEN the Finalizer verifies completeness, THE Finalizer SHALL derive the verification result from already-loaded data using pure logic that performs no I/O.

### Requirement 2: Results reference an existing run

**User Story:** As an AI/ML researcher, I want results to reference a run that actually exists, so that the best run is traceable to real recorded data.

#### Acceptance Criteria

1. WHEN the Finalizer validates the Results_File, THE Finalizer SHALL confirm that the `best_run.run_id` references an existing run directory in the Experiment_Dir.
2. IF the `best_run.run_id` does not reference an existing run directory, THEN THE Finalizer SHALL report an invalid-reference outcome and SHALL exit with code 1.
3. WHEN the Finalizer validates the Primary_Metric, THE Finalizer SHALL confirm that the Primary_Metric value is a numeric value.
4. IF the Primary_Metric value is missing or is not numeric, THEN THE Finalizer SHALL report an incomplete-results outcome and SHALL exit with code 1.

### Requirement 3: Conclusions reference verified metrics and artifacts

**User Story:** As an AI/ML researcher, I want every success claim backed by verified evidence, so that no conclusion asserts a result without a recorded metric or an existing artifact.

#### Acceptance Criteria

1. WHEN the Finalizer records the Success_Assessment, THE Finalizer SHALL require every claimed metric to be backed by an actual recorded value in the Results_File or a Run_Record.
2. WHEN the Finalizer records an Artifact_Reference, THE Finalizer SHALL verify that the referenced artifact exists in the recorded Linkage_Fields or on the local filesystem before including the reference in a conclusion.
3. IF a conclusion references a metric or an artifact that cannot be verified, THEN THE Finalizer SHALL report an unverified-reference outcome and SHALL NOT mark the experiment as successful.
4. THE Finalizer SHALL NOT claim experiment success without at least one verified Artifact_Reference and a verified Primary_Metric value.

### Requirement 4: Assemble and validate results.yaml

**User Story:** As an AI/ML researcher, I want results.yaml assembled and validated, so that the result file is complete and internally consistent.

#### Acceptance Criteria

1. WHEN the Finalizer finalizes the Results_File, THE Finalizer SHALL confirm the presence of the `best_run`, `primary_metric`, `success`, and `completed_at` fields.
2. WHEN the Finalizer assembles the Results_File, THE Finalizer SHALL populate the Success_Assessment with a `criteria_met` boolean and a `rationale` derived from the success criteria in the Plan.
3. WHEN the Finalizer records artifacts in the Results_File, THE Finalizer SHALL surface the Linkage_Fields from each referenced Run_Record.
4. WHEN the Finalizer assembles the Results_File, THE Finalizer SHALL derive the assembled content from already-loaded data using pure logic that performs no network I/O.

### Requirement 5: Append final history entry

**User Story:** As an AI/ML researcher, I want a final completion entry appended to history.md, so that the chronological record ends with the experiment outcome.

#### Acceptance Criteria

1. WHEN the Finalizer finalizes documentation, THE Finalizer SHALL append a completion entry to the History_File that includes a timestamp, the best run reference, the Primary_Metric value, and the Success_Assessment determination.
2. THE Finalizer SHALL append to the History_File without modifying prior History_File entries.
3. THE History_File completion entry SHALL contain summary records rather than full standard-output or standard-error logs.

### Requirement 6: Write and validate journal.md

**User Story:** As an AI/ml researcher, I want journal.md to carry interpretive analysis and next steps, so that the experiment's meaning and follow-up work are captured.

#### Acceptance Criteria

1. WHEN the Finalizer finalizes the Journal_File, THE Finalizer SHALL confirm that the Journal_File contains a hypothesis assessment, key findings, interpretation, and recommended next experiments.
2. IF the Journal_File lacks a recommended-next-experiments section, THEN THE Finalizer SHALL report a documentation warning in the Output_Envelope.
3. THE Journal_File SHALL contain interpretive analysis rather than only an execution log.

### Requirement 7: Reverse-chronological project log without duplication

**User Story:** As an AI/ML researcher, I want a concise project-log entry, so that the project log summarizes conclusions without duplicating experiment detail.

#### Acceptance Criteria

1. WHEN the Finalizer updates the Project_Log, THE Finalizer SHALL add the Project_Log_Entry at the top of the Project_Log in reverse-chronological order.
2. WHEN the Finalizer composes the Project_Log_Entry, THE Finalizer SHALL include a one-line conclusion, the best run reference, a link to the Experiment_Dir, and key metric values.
3. THE Finalizer SHALL constrain the Project_Log_Entry to a project-level conclusion that does not duplicate the per-run detail recorded in the Results_File, the History_File, or the Journal_File.
4. WHILE a Project_Log_Entry for the same experiment already exists, THE Finalizer SHALL update the existing entry rather than adding a duplicate entry.

### Requirement 8: Commit candidate selection

**User Story:** As an AI/ML researcher, I want the helper to build the list of files to commit and a commit message, so that I can review a complete commit candidate.

#### Acceptance Criteria

1. WHEN the Finalizer selects the Commit_Candidate, THE Finalizer SHALL build the list of files to commit and the commit message using pure logic that performs no I/O beyond reading already-loaded data.
2. WHEN the Finalizer assembles the commit message, THE Finalizer SHALL include the experiment identifier, the Primary_Metric value, the Success_Assessment determination, and the surfaced Linkage_Fields.
3. WHEN the Finalizer builds the Commit_Candidate file list, THE Finalizer SHALL include the Plan, the job configuration files, the Run_Record summaries, the Results_File, the History_File, the Journal_File, and the Project_Log.

### Requirement 9: Commit candidate exclusions

**User Story:** As an AI/ML researcher, I want large artifacts kept out of the commit candidate, so that checkpoints, caches, and raw logs never enter Git.

#### Acceptance Criteria

1. WHEN the Finalizer builds the Commit_Candidate, THE Finalizer SHALL exclude model checkpoints matching `*.pt`, `*.bin`, `*.safetensors`, and `*.ckpt`.
2. WHEN the Finalizer builds the Commit_Candidate, THE Finalizer SHALL exclude the `wandb/` cache directory and raw `.out` and `.err` logs.
3. WHEN the Finalizer builds the Commit_Candidate, THE Finalizer SHALL exclude any Excluded_Artifact identified as a large artifact.
4. THE Finalizer SHALL derive the exclusion result using pure logic that performs no I/O.

### Requirement 10: Commit security review

**User Story:** As an AI/ML researcher, I want the helper to refuse credential-bearing files, so that no secret is ever staged for commit.

#### Acceptance Criteria

1. WHEN the Finalizer builds the Commit_Candidate, THE Finalizer SHALL scan the candidate file list for Credential_File patterns including `.env`, `*.token`, and `credentials.json`.
2. IF the Commit_Candidate contains a Credential_File, THEN THE Finalizer SHALL refuse to stage the Credential_File and SHALL report a security-review outcome.
3. WHEN the Finalizer detects a Credential_File in the Commit_Candidate, THE Finalizer SHALL decline the Mutating_Git_Action and SHALL exit with code 1.

### Requirement 11: Approval gating for mutating Git actions

**User Story:** As an AI/ML researcher, I want every Git action that changes state to require my approval, so that no commit or push happens without my consent.

#### Acceptance Criteria

1. WHEN the Finalizer prepares a Mutating_Git_Action, THE Finalizer SHALL read the Approval_Status from the Plan before executing the action.
2. IF the Approval_Status does not equal `approved`, THEN THE Finalizer SHALL decline the Mutating_Git_Action, SHALL present the Commit_Candidate as a proposal, and SHALL exit with code 1.
3. WHILE the Approval_Status equals `approved`, THE Finalizer SHALL permit the Mutating_Git_Action to execute through the Git_Client.
4. WHEN the Finalizer performs a read-only or local-only action, THE Finalizer SHALL execute the action without requiring the Approval_Status.
5. THE Finalizer SHALL propose the Commit_Candidate without creating a commit until the Approval_Status equals `approved`.

### Requirement 12: Injected Git client boundary

**User Story:** As an AI/ML researcher, I want all Git I/O routed through one injected boundary, so that logic is testable and tests never run real Git or network operations.

#### Acceptance Criteria

1. THE Finalizer SHALL route every Git operation, network call, and filesystem-mutating Git action through a single Git_Client.
2. WHEN the Finalizer runs in production, THE Finalizer SHALL construct the Real_Git_Client only within `main()`.
3. WHEN the Finalizer runs under test with the Fake_Git_Client, THE Finalizer SHALL perform no real Git commit, no push, and no network access.
4. THE Finalizer SHALL separate pure logic that performs no I/O from the impure operations that pass through the Git_Client.

### Requirement 13: Honest finalization of failed or partial experiments

**User Story:** As an AI/ML researcher, I want failures finalized honestly, so that a failed or partial experiment is never reported as successful.

#### Acceptance Criteria

1. IF a required run has a Run_Status of `failed`, THEN THE Finalizer SHALL confirm the failure is documented in the History_File and the Journal_File before finalizing.
2. IF a required run failed, THEN THE Finalizer SHALL NOT report the success criteria as met.
3. IF a required Hub upload has an Hf_Status other than `verified`, THEN THE Finalizer SHALL NOT mark the experiment as complete and SHALL report an incomplete-experiment outcome.
4. WHEN the Finalizer finalizes a partial experiment, THE Finalizer SHALL record the partial status in the Results_File and the Success_Assessment rationale.

### Requirement 14: Run-to-experiment linkage and completion marker

**User Story:** As an AI/ML researcher, I want the finalizer to surface prior-phase linkage and mark the experiment finalized, so that the completion state is recorded without altering any run's status.

#### Acceptance Criteria

1. WHEN the Finalizer reads a Run_Record, THE Finalizer SHALL read the Linkage_Fields produced by Phases 5 through 8 and surface them in the Results_File and the commit message.
2. WHEN the Finalizer completes finalization, THE Finalizer SHALL write the Finalized_Marker to the Plan.
3. THE Finalizer SHALL leave every Run_Status unchanged when writing the Finalized_Marker.

### Requirement 15: Secret safety and redaction

**User Story:** As an AI/ML researcher, I want credentials kept out of every artifact, so that no token or key is written or committed.

#### Acceptance Criteria

1. WHEN the Finalizer records config or metadata, THE Finalizer SHALL drop every Credential_Key value and SHALL retain only the key names where a name is required.
2. THE Finalizer SHALL exclude every Credential_Key value from the Results_File, the History_File, the Journal_File, the Project_Log, the commit message, and the Output_Envelope.
3. WHEN the Finalizer reports an error that references configuration, THE Finalizer SHALL redact every Credential_Key value from the reported message.

### Requirement 16: Output envelope and exit codes

**User Story:** As an AI/ML researcher, I want a consistent JSON result and exit code, so that the Phase 9 helper composes with the Phase 5, Phase 6, Phase 7, and Phase 8 helpers.

#### Acceptance Criteria

1. WHEN the Finalizer completes any task, THE Finalizer SHALL write an Output_Envelope with the fields `status`, `message`, `data`, `errors`, and `warnings` to stdout.
2. WHEN the Finalizer verifies completeness, finalizes documentation, prepares a proposal, or commits after approval, THE Finalizer SHALL exit with code 0.
3. WHEN the Finalizer declines due to a verification failure, a missing approval, an incomplete experiment, or a blocked finalization, THE Finalizer SHALL exit with code 1.
4. IF the Finalizer encounters a filesystem or parse error, THEN THE Finalizer SHALL exit with code 2.

### Requirement 17: Phase boundaries

**User Story:** As an AI/ML researcher, I want Phase 9 limited to finalization and commit proposal, so that execution, submission, tracking, and publication remain in their own phases.

#### Acceptance Criteria

1. THE Finalizer SHALL NOT run any training job, deferring local execution to Phase 5.
2. THE Finalizer SHALL NOT submit any Slurm job, deferring Slurm submission to Phase 6.
3. THE Finalizer SHALL NOT create or finish any W&B Run, deferring W&B tracking to Phase 7.
4. THE Finalizer SHALL NOT upload any checkpoint to the Hugging Face Hub, deferring Hub publication to Phase 8.
5. THE Finalizer SHALL confine its mutating actions to finalizing documentation, writing the Finalized_Marker, and proposing or executing an approved Commit_Candidate.
