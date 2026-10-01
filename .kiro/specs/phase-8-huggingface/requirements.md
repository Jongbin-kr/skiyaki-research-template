# Requirements Document

## Introduction

Phase 8 of the Codex-native AI/ML Research Workspace roadmap adds the **Hugging Face Hub publication** layer on top of the Phase 5 local-execution helper (`run_local.py`), the Phase 6 SSH/Slurm submission helper (`submit_slurm.py`), and the Phase 7 W&B tracking helper (`track_wandb.py`). Phase 8 implements Hub repository existence and verification checks; checkpoint upload; revision recording; a local model-card draft; upload-result verification; and the private/public visibility policy. The resulting Hub repository identity (repository id, revision, and URL) and publication status are linked back to the Harness Run by writing them into `run.yaml`. Per the roadmap completion criteria, an uploaded checkpoint can be located by its revision, and if a required Hub upload fails, the Experiment is NOT marked complete.

Phase 8 is deliberately bounded. All stable Hub settings are read from the repository `project-plan.md` frontmatter (`huggingface.namespace`, `huggingface.private`, `huggingface.push_policy`) and are never re-asked. The `huggingface.namespace` value is currently the placeholder `TODO-set-before-phase-8`; the helper must tolerate the placeholder gracefully by declining the upload with a clear outcome, exiting with code 1, and never crashing. Real mutating Hub actions — creating or ensuring a repository, uploading a checkpoint or file, creating a commit or revision on the Hub, and setting repository visibility — require explicit user approval (the experiment `plan.md` `approval.status` must equal `approved`), the same approval gate used in Phase 5, Phase 6, and Phase 7. Read-only and local-only actions — reading `run.yaml`, checking a local checkpoint path, drafting a model card locally, and parsing settings — are non-mutating and do not require approval.

The design separates pure logic (no I/O: push-eligibility decision from policy and checkpoint kind, model-card draft assembly, revision and URL construction, status mapping, redaction, output-envelope assembly) from a single injected impure boundary. All Hugging Face Hub API, network, and filesystem-mutating calls pass through one `HfClient` protocol, with a `RealHfClient` wrapping `huggingface_hub` constructed only in `main()` for production and a `FakeHfClient` used in tests, so that no real Hub API call or network access ever occurs during automated tests. A Hub failure is recorded distinctly from a training/run failure: `run.yaml` carries a separate `hf_status` field so that a failed upload never marks the training Run itself as failed, while still signaling that the Experiment must not be marked complete. Generated `run.yaml` records and any artifact never contain secrets, tokens, or credential values (for example `HF_TOKEN` or `HUGGINGFACEHUB_API_TOKEN`), reusing the Phase 5/6/7 names-only redaction approach. Checkpoints are large artifacts uploaded to the Hub and are never added to Git; the helper reuses the Phase 6/7 commit-candidate exclusion (`checkpoints/`, `wandb/`, `.out`/`.err`). The helper follows the Phase 5/6/7 output contract: a JSON envelope `{status, message, data, errors, warnings}` on stdout with exit code 0 (completed/recorded/verified), 1 (declined), or 2 (runtime error). W&B tracking remains in Phase 7, and no Git commits occur in Phase 8.

This document specifies the behavior of the Phase 8 publication layer, implemented as a deterministic helper (`publish_hf.py`) in `.agents/skills/train-llm/scripts/` alongside `initialize_run.py`, `run_local.py`, `submit_slurm.py`, and `track_wandb.py`, with pure logic separated from a single injected Hub client boundary.

## Glossary

- **Hf_Publisher**: The Phase 8 component (`publish_hf.py`) that verifies the Hub repository, decides push eligibility, uploads checkpoints, records revisions, drafts the model card, verifies the upload, applies the visibility policy, and links the Hub publication to the Harness Run.
- **Hf_Client**: The single injected interface through which every Hugging Face Hub API call, network call, and filesystem-mutating Hub operation passes. The production implementation is `Real_Hf_Client`, constructed only in `main()`; the test implementation is `Fake_Hf_Client`.
- **Real_Hf_Client**: The production `Hf_Client` implementation that wraps `huggingface_hub`, performs real Hub API and network operations, and is instantiated only within `main()`.
- **Fake_Hf_Client**: The test `Hf_Client` implementation that simulates Hub behavior in memory so that no real Hub API call or network access occurs during tests.
- **Local_Executor**: The existing Phase 5 component (`run_local.py`) that runs eligible local jobs and records their outcomes.
- **Slurm_Submitter**: The existing Phase 6 component (`submit_slurm.py`) that submits jobs to Slurm and links them to the Harness Run.
- **Wandb_Tracker**: The existing Phase 7 component (`track_wandb.py`) that tracks W&B Runs and links them to the Harness Run.
- **Project_Plan**: The repository-root `project-plan.md` file whose YAML frontmatter supplies the stable Hub settings.
- **Hf_Namespace**: The Hugging Face namespace (user or organization) recorded as `huggingface.namespace` in the Project_Plan.
- **Hf_Private**: The `huggingface.private` boolean in the Project_Plan indicating whether created repositories default to private.
- **Push_Policy**: The `huggingface.push_policy` value in the Project_Plan governing which checkpoints are eligible to push, one of `never`, `final_only`, `milestone`, `final_and_milestone`, or `every_save`.
- **Placeholder_Namespace**: The sentinel Hf_Namespace value `TODO-set-before-phase-8` indicating the namespace has not yet been configured.
- **Checkpoint_Kind**: The classification of a checkpoint, one of `final`, `milestone`, or `intermediate`.
- **Checkpoint_Path**: The local filesystem path to the checkpoint artifact to be uploaded.
- **Hf_Repo_Id**: The Hub repository identifier in the form `<Hf_Namespace>/<repo-name>`.
- **Hf_Revision**: The Hub revision (commit SHA or tag) at which a checkpoint upload is recorded and later located.
- **Hf_Url**: The Hub web URL associated with the Hf_Repo_Id and Hf_Revision.
- **Model_Card**: The locally drafted model-card document describing the uploaded model.
- **Model_Card_Path**: The local filesystem path of the drafted Model_Card.
- **Run_Record**: The `run.yaml` metadata file inside the Harness Run directory, extended in Phase 8 with Hub linkage fields.
- **Run_Status**: The Harness Run lifecycle state recorded in `run.yaml` (for example `succeeded`, `failed`), owned by Phase 5 and Phase 6 and never changed by a Hub outcome.
- **Hf_Status**: The Hub publication state recorded in `run.yaml`, one of `not_started`, `skipped_by_policy`, `uploaded`, `verified`, or `upload_failed`.
- **Mutating_Hub_Action**: Any action that changes Hub remote state: creating or ensuring a repository, uploading a checkpoint or file, creating a commit or revision on the Hub, and setting repository visibility.
- **Approval_Status**: The `approval.status` field in the experiment `plan.md`; a Mutating_Hub_Action proceeds only when the value equals `approved`.
- **Output_Envelope**: The JSON object `{status, message, data, errors, warnings}` the Hf_Publisher writes to stdout.
- **Credential_Key**: A configuration or environment key whose name matches a credential-like pattern (for example `HF_TOKEN`, `HUGGINGFACEHUB_API_TOKEN`, `token`, `password`, `secret`), whose value is excluded from all written artifacts.

## Requirements

### Requirement 1: Stable Hub settings from the project plan

**User Story:** As an AI/ML researcher, I want Hub settings read from the project plan, so that the namespace, visibility, and push policy are consistent and never re-asked.

#### Acceptance Criteria

1. WHEN the Hf_Publisher begins any task, THE Hf_Publisher SHALL read the Hf_Namespace, Hf_Private, and Push_Policy from the Project_Plan rather than prompting for them.
2. IF the Push_Policy read from the Project_Plan is not one of `never`, `final_only`, `milestone`, `final_and_milestone`, or `every_save`, THEN THE Hf_Publisher SHALL report a configuration-error outcome and SHALL NOT invoke any Mutating_Hub_Action.
3. WHEN the Hf_Publisher resolves the Hub settings, THE Hf_Publisher SHALL record the resolved Hf_Private value in the Run_Record as the `hf_private` field.
4. THE Hf_Publisher SHALL treat Hf_Private as `true` when the Project_Plan does not declare the `huggingface.private` value.

### Requirement 2: Placeholder namespace tolerance

**User Story:** As an AI/ML researcher, I want the helper to handle an unconfigured namespace gracefully, so that running before the namespace is set never crashes the workflow.

#### Acceptance Criteria

1. WHEN the Hf_Publisher reads the Hf_Namespace, THE Hf_Publisher SHALL detect whether the value equals the Placeholder_Namespace.
2. IF the Hf_Namespace equals the Placeholder_Namespace, THEN THE Hf_Publisher SHALL decline the Mutating_Hub_Action, SHALL report a placeholder-namespace outcome, and SHALL exit with code 1.
3. WHEN the Hf_Namespace equals the Placeholder_Namespace, THE Hf_Publisher SHALL complete without raising an unhandled exception.
4. WHERE the Hf_Namespace equals the Placeholder_Namespace, THE Hf_Publisher SHALL permit read-only and local-only actions to proceed.

### Requirement 3: Push-eligibility decision from policy

**User Story:** As an AI/ML researcher, I want the push policy to decide which checkpoints are eligible, so that only the intended checkpoints are published to the Hub.

#### Acceptance Criteria

1. WHEN the Hf_Publisher evaluates push eligibility, THE Hf_Publisher SHALL derive eligibility from the Push_Policy and the Checkpoint_Kind using pure logic that performs no I/O.
2. WHILE the Push_Policy equals `never`, THE Hf_Publisher SHALL mark every Checkpoint_Kind as ineligible.
3. WHILE the Push_Policy equals `final_only`, THE Hf_Publisher SHALL mark a Checkpoint_Kind of `final` as eligible and all other Checkpoint_Kind values as ineligible.
4. WHILE the Push_Policy equals `final_and_milestone`, THE Hf_Publisher SHALL mark a Checkpoint_Kind of `final` or `milestone` as eligible and a Checkpoint_Kind of `intermediate` as ineligible.
5. WHILE the Push_Policy equals `milestone`, THE Hf_Publisher SHALL mark a Checkpoint_Kind of `milestone` or `final` as eligible and a Checkpoint_Kind of `intermediate` as ineligible.
6. WHILE the Push_Policy equals `every_save`, THE Hf_Publisher SHALL mark every Checkpoint_Kind as eligible.
7. IF the Checkpoint_Kind is ineligible under the Push_Policy, THEN THE Hf_Publisher SHALL set the Hf_Status to `skipped_by_policy`, SHALL NOT invoke any Mutating_Hub_Action, and SHALL exit with code 1.

### Requirement 4: Local checkpoint verification

**User Story:** As an AI/ML researcher, I want the helper to confirm the checkpoint exists locally before upload, so that an upload does not run against a missing or wrong path.

#### Acceptance Criteria

1. WHEN the Hf_Publisher prepares an upload, THE Hf_Publisher SHALL verify that the Checkpoint_Path exists on the local filesystem as a read-only action requiring no approval.
2. IF the Checkpoint_Path does not exist, THEN THE Hf_Publisher SHALL report a missing-checkpoint outcome and SHALL NOT invoke any Mutating_Hub_Action.
3. WHILE the Checkpoint_Path exists, THE Hf_Publisher SHALL record the Checkpoint_Path as verified and proceed to repository verification.

### Requirement 5: Repository existence and verification

**User Story:** As an AI/ML researcher, I want the helper to check and ensure the Hub repository, so that the checkpoint uploads to a known repository under the correct namespace.

#### Acceptance Criteria

1. WHEN the Hf_Publisher resolves the target repository, THE Hf_Publisher SHALL construct the Hf_Repo_Id from the Hf_Namespace and the repository name.
2. WHEN the Hf_Publisher checks repository existence, THE Hf_Publisher SHALL query the Hub for the Hf_Repo_Id through the Hf_Client.
3. WHERE the Hf_Repo_Id does not exist AND the Approval_Status equals `approved`, THE Hf_Publisher SHALL create the repository through the Hf_Client with visibility set according to Hf_Private.
4. IF the Hf_Repo_Id does not exist AND the Approval_Status does not equal `approved`, THEN THE Hf_Publisher SHALL decline repository creation and SHALL report an approval-required outcome.

### Requirement 6: Private and public visibility policy

**User Story:** As an AI/ML researcher, I want repositories created according to the configured visibility, so that a private repository is never silently made public.

#### Acceptance Criteria

1. WHEN the Hf_Publisher creates a repository, THE Hf_Publisher SHALL set the repository visibility to private WHERE Hf_Private equals `true`.
2. IF a visibility change would make a private repository public, THEN THE Hf_Publisher SHALL require the Approval_Status to equal `approved` before applying the change.
3. WHILE Hf_Private equals `true`, THE Hf_Publisher SHALL NOT set the repository visibility to public without an explicit visibility-change request whose Approval_Status equals `approved`.
4. WHEN the Hf_Publisher records visibility, THE Hf_Publisher SHALL write the resolved repository visibility into the Run_Record as the `hf_private` field.

### Requirement 7: Checkpoint upload

**User Story:** As an AI/ML researcher, I want eligible checkpoints uploaded to the Hub, so that trained models are published and retrievable.

#### Acceptance Criteria

1. WHEN the Hf_Publisher uploads a checkpoint, THE Hf_Publisher SHALL treat the upload as a Mutating_Hub_Action requiring the Approval_Status to equal `approved`.
2. WHILE the Approval_Status equals `approved` AND the Hf_Namespace is not the Placeholder_Namespace AND the Checkpoint_Kind is eligible under the Push_Policy, THE Hf_Publisher SHALL upload the Checkpoint_Path to the Hf_Repo_Id through the Hf_Client.
3. WHEN the Hf_Client returns a completed upload, THE Hf_Publisher SHALL set the Hf_Status to `uploaded` in the Run_Record.
4. IF the upload returns an error from the Hf_Client, THEN THE Hf_Publisher SHALL set the Hf_Status to `upload_failed` in the Run_Record and SHALL NOT change the Run_Status.
5. IF the Approval_Status does not equal `approved`, THEN THE Hf_Publisher SHALL decline the upload, SHALL report an approval-required outcome, and SHALL exit with code 1.

### Requirement 8: Revision recording

**User Story:** As an AI/ML researcher, I want the uploaded checkpoint's revision recorded, so that each published checkpoint is traceable to a specific Hub revision.

#### Acceptance Criteria

1. WHEN the Hf_Client returns a completed upload, THE Hf_Publisher SHALL obtain the Hf_Revision associated with the upload through the Hf_Client.
2. WHEN the Hf_Publisher records the publication, THE Hf_Publisher SHALL write the Hf_Repo_Id, the Hf_Revision, and the Hf_Url into the Run_Record.
3. IF the upload completes without a parseable Hf_Revision, THEN THE Hf_Publisher SHALL set the Hf_Status to `upload_failed` and SHALL report a revision-unavailable outcome.

### Requirement 9: Upload-result verification

**User Story:** As an AI/ML researcher, I want the uploaded checkpoint located by its recorded revision, so that a required publication is confirmed before the Experiment is considered complete.

#### Acceptance Criteria

1. WHEN the Hf_Publisher verifies an upload, THE Hf_Publisher SHALL confirm through the Hf_Client that the uploaded checkpoint can be located at the recorded Hf_Revision in the Hf_Repo_Id.
2. WHEN the verification confirms the checkpoint is locatable by the recorded Hf_Revision, THE Hf_Publisher SHALL set the Hf_Status to `verified` in the Run_Record.
3. IF the verification cannot locate the checkpoint by the recorded Hf_Revision, THEN THE Hf_Publisher SHALL set the Hf_Status to `upload_failed`, SHALL signal that the Experiment must not be marked complete, and SHALL exit with code 1.
4. WHEN a required Hub upload is not verified, THE Hf_Publisher SHALL record the Hf_Status distinctly from the Run_Status so that a Hub failure is distinguishable from a training failure.

### Requirement 10: Model card draft

**User Story:** As an AI/ML researcher, I want a model card drafted locally for the uploaded model, so that the published repository can carry documentation.

#### Acceptance Criteria

1. WHEN the Hf_Publisher drafts a Model_Card, THE Hf_Publisher SHALL treat the draft as a local-only action requiring no approval.
2. WHEN the Hf_Publisher assembles the Model_Card, THE Hf_Publisher SHALL include the Hf_Repo_Id, the Checkpoint_Kind, and the recorded Resolved_Config using pure logic that performs no network I/O.
3. WHEN the Hf_Publisher writes the Model_Card, THE Hf_Publisher SHALL write the Model_Card to the Model_Card_Path and SHALL record the Model_Card_Path in the Run_Record.
4. THE Model_Card SHALL NOT contain any Credential_Key value.

### Requirement 11: Approval gating for mutating Hub actions

**User Story:** As an AI/ML researcher, I want every Hub action that changes remote state to require my approval, so that no repository creation, upload, revision, or visibility change happens without my consent.

#### Acceptance Criteria

1. WHEN the Hf_Publisher prepares a Mutating_Hub_Action, THE Hf_Publisher SHALL read the Approval_Status from the experiment `plan.md` before executing the action.
2. IF the Approval_Status does not equal `approved`, THEN THE Hf_Publisher SHALL decline the Mutating_Hub_Action and SHALL report an approval-required outcome.
3. WHILE the Approval_Status equals `approved`, THE Hf_Publisher SHALL permit the Mutating_Hub_Action to execute through the Hf_Client.
4. WHEN the Hf_Publisher performs a read-only or local-only action, THE Hf_Publisher SHALL execute the action without requiring the Approval_Status.

### Requirement 12: Injected Hub client boundary

**User Story:** As an AI/ML researcher, I want all Hub I/O routed through one injected boundary, so that logic is testable and tests never touch the real Hub API or network.

#### Acceptance Criteria

1. THE Hf_Publisher SHALL route every Hugging Face Hub API call, network call, and filesystem-mutating Hub operation through a single Hf_Client.
2. WHEN the Hf_Publisher runs in production, THE Hf_Publisher SHALL construct the Real_Hf_Client only within `main()`.
3. WHEN the Hf_Publisher runs under test with the Fake_Hf_Client, THE Hf_Publisher SHALL perform no real Hub API call and no network access.
4. THE Hf_Publisher SHALL separate pure logic that performs no I/O from the impure operations that pass through the Hf_Client.

### Requirement 13: Run-to-Hub linkage in run.yaml

**User Story:** As an AI/ML researcher, I want the Hub publication linked to its Harness Run, so that `run.yaml` captures the repository identity, revision, and publication state.

#### Acceptance Criteria

1. WHEN the Hf_Publisher links a Hub publication, THE Hf_Publisher SHALL write the Hf_Repo_Id, Hf_Revision, Hf_Url, Hf_Status, Hf_Private, and Model_Card_Path into the Run_Record.
2. WHEN the Hf_Publisher updates the Hf_Status, THE Hf_Publisher SHALL write the updated Hf_Status into the Run_Record without modifying the Run_Status.
3. THE Run_Record SHALL NOT contain any secret, token, password, or Credential_Key value.
4. WHEN the Hf_Publisher writes Hub linkage fields, THE Hf_Publisher SHALL confine the write to the Run_Record of the targeted Harness Run.

### Requirement 14: Secret safety and redaction

**User Story:** As an AI/ML researcher, I want Hub credentials kept out of every artifact, so that no token or key is committed or recorded.

#### Acceptance Criteria

1. WHEN the Hf_Publisher records config or metadata, THE Hf_Publisher SHALL drop every Credential_Key value and SHALL retain only the key names where a name is required.
2. THE Hf_Publisher SHALL exclude the Hub token and any other Credential_Key value from the Run_Record, the Model_Card, and the Output_Envelope.
3. WHEN the Hf_Publisher reports an error that references configuration, THE Hf_Publisher SHALL redact every Credential_Key value from the reported message.

### Requirement 15: Output envelope and exit codes

**User Story:** As an AI/ML researcher, I want a consistent JSON result and exit code, so that the Phase 8 helper composes with the Phase 5, Phase 6, and Phase 7 helpers.

#### Acceptance Criteria

1. WHEN the Hf_Publisher completes any task, THE Hf_Publisher SHALL write an Output_Envelope with the fields `status`, `message`, `data`, `errors`, and `warnings` to stdout.
2. WHEN the Hf_Publisher completes, records, or verifies an outcome successfully, THE Hf_Publisher SHALL exit with code 0.
3. WHEN the Hf_Publisher declines due to a missing approval, a Placeholder_Namespace, a policy skip, an unverified upload, or a missing prerequisite, THE Hf_Publisher SHALL exit with code 1.
4. IF the Hf_Publisher encounters a filesystem or parse error, THEN THE Hf_Publisher SHALL exit with code 2.

### Requirement 16: Phase boundaries and commit-candidate exclusion

**User Story:** As an AI/ML researcher, I want Phase 8 limited to Hub publication, so that W&B tracking and Git commits remain in their own phases and large artifacts stay out of Git.

#### Acceptance Criteria

1. THE Hf_Publisher SHALL NOT create or finish any W&B Run, deferring W&B tracking to Phase 7.
2. THE Hf_Publisher SHALL NOT create any Git commit.
3. THE Hf_Publisher SHALL exclude `checkpoints/`, `wandb/`, and raw `.out` and `.err` logs from any content it marks as commit candidates.
4. THE Hf_Publisher SHALL upload checkpoints to the Hub through the Hf_Client and SHALL NOT add checkpoints to Git.
5. WHEN a Hub outcome is recorded, THE Hf_Publisher SHALL leave the Run_Status owned by Phase 5 and Phase 6 unchanged.
