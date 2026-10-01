# Requirements Document

## Introduction

Phase 7 of the Codex-native AI/ML Research Workspace roadmap adds the **Weights & Biases (W&B) experiment tracking** layer on top of the Phase 5 local-execution helper (`run_local.py`) and the Phase 6 SSH/Slurm submission helper (`submit_slurm.py`). Phase 7 implements W&B Run creation and resume; group and tag assignment so that related Runs (for example a LoRA-rank ablation sweep) are comparable within a single W&B group; recording of the resolved job config and the current Git SHA; placement of the local W&B directory under `experiments/<experiment-id>/runs/<run-id>/wandb/`; comparison of Runs within a group; and a sync-status check. The resulting W&B Run identity (id and URL) and sync state are linked back to the Harness Run by writing them into `run.yaml`.

Phase 7 is deliberately bounded. All stable W&B settings are read from the repository `project-plan.md` frontmatter (`wandb.entity`, `wandb.project`, `wandb.mode`, `wandb.keep_local_data`) and are never re-asked. The `wandb.entity` value is currently the placeholder `TODO-set-before-phase-7`; the helper must tolerate the placeholder gracefully by declining or falling back to local-only/offline behavior and never crashing. Real mutating W&B actions — creating or finishing a W&B Run and syncing a local run to the web — require explicit user approval (the experiment `plan.md` `approval.status` must equal `approved`), the same approval gate used in Phase 5 and Phase 6. Read-only and local-only actions — reading `run.yaml`, parsing a W&B URL from log text, and inspecting the local W&B directory — are non-mutating and do not require approval.

The design separates pure logic (no I/O: group and tag resolution, config and Git-SHA assembly, Slurm/log URL parsing, status mapping, redaction, local-directory path construction, output-envelope assembly) from a single injected impure boundary. All W&B API, network, and filesystem-mutating calls pass through one `WandbClient` protocol, with a `RealWandbClient` constructed only in `main()` for production and a `FakeWandbClient` used in tests, so that no real W&B API call or network access ever occurs during automated tests. A W&B failure is recorded distinctly from a training/run failure: `run.yaml` carries a separate `wandb_status` field so that a failed sync never marks the training Run itself as failed. Generated `run.yaml` records and any artifact never contain secrets, tokens, or credential values (for example `WANDB_API_KEY`), reusing the Phase 5/6 names-only redaction approach. The helper follows the Phase 5/6 output contract: a JSON envelope `{status, message, data, errors, warnings}` on stdout with exit code 0 (completed/recorded), 1 (declined), or 2 (runtime error). Phase 8 Hugging Face Hub uploads are out of scope, and no Git commits occur in Phase 7.

This document specifies the behavior of the Phase 7 tracking layer, implemented as a deterministic helper (`track_wandb.py`) in `.agents/skills/train-llm/scripts/` alongside `initialize_run.py`, `run_local.py`, and `submit_slurm.py`, with pure logic separated from a single injected W&B client boundary.

## Glossary

- **Wandb_Tracker**: The Phase 7 component (`track_wandb.py`) that creates and resumes W&B Runs, assigns groups and tags, records config and Git SHA, manages the local W&B directory, compares Runs, checks sync status, and links the W&B Run to the Harness Run.
- **Wandb_Client**: The single injected interface through which every W&B API, network, and filesystem-mutating action passes. The production implementation is `RealWandbClient`, constructed only in `main()`; the test implementation is `FakeWandbClient`.
- **Real_Wandb_Client**: The production `Wandb_Client` implementation that performs real W&B API and network operations and is instantiated only within `main()`.
- **Fake_Wandb_Client**: The test `Wandb_Client` implementation that simulates W&B behavior in memory so that no real W&B API call or network access occurs during tests.
- **Local_Executor**: The existing Phase 5 component (`run_local.py`) that runs eligible local jobs and records their outcomes.
- **Slurm_Submitter**: The existing Phase 6 component (`submit_slurm.py`) that submits jobs to Slurm and links them to the Harness Run.
- **Project_Plan**: The repository-root `project-plan.md` file whose YAML frontmatter supplies the stable W&B settings.
- **Wandb_Entity**: The W&B entity recorded as `wandb.entity` in the Project_Plan.
- **Wandb_Project**: The W&B project recorded as `wandb.project` in the Project_Plan.
- **Wandb_Mode**: The W&B operating mode recorded as `wandb.mode` in the Project_Plan, one of `online`, `offline`, or `disabled`.
- **Keep_Local_Data**: The `wandb.keep_local_data` boolean in the Project_Plan indicating whether local W&B data is retained after sync.
- **Placeholder_Entity**: The sentinel Wandb_Entity value `TODO-set-before-phase-7` indicating the entity has not yet been configured.
- **Run_Record**: The `run.yaml` metadata file inside the Harness Run directory, extended in Phase 7 with W&B linkage fields.
- **Run_Status**: The Harness Run lifecycle state recorded in `run.yaml` (for example `succeeded`, `failed`), owned by Phase 5 and Phase 6 and never changed by a W&B outcome.
- **Wandb_Status**: The W&B linkage state recorded in `run.yaml`, one of `not_started`, `running`, `synced`, `sync_failed`, or `offline`.
- **Wandb_Run_Id**: The W&B Run identifier returned by the Wandb_Client when a Run is created or resumed.
- **Wandb_Url**: The W&B Run web URL associated with the Wandb_Run_Id.
- **Wandb_Group**: The W&B group name under which related Runs are grouped so they are comparable in a single view.
- **Wandb_Tags**: The list of W&B tag strings assigned to a W&B Run.
- **Local_Wandb_Dir**: The local W&B directory for a Run located at `experiments/<experiment-id>/runs/<run-id>/wandb/`.
- **Resolved_Config**: The resolved job configuration (job parameters and resolved settings) recorded as the W&B Run config.
- **Git_Sha**: The current repository Git commit SHA recorded with the W&B Run and in the Run_Record.
- **Mutating_Wandb_Action**: Any action that changes W&B remote state or finalizes a Run: creating a W&B Run, finishing a W&B Run, and syncing a local Run to the web.
- **Approval_Status**: The `approval.status` field in the experiment `plan.md`; a Mutating_Wandb_Action proceeds only when the value equals `approved`.
- **Output_Envelope**: The JSON object `{status, message, data, errors, warnings}` the Wandb_Tracker writes to stdout.
- **Credential_Key**: A configuration or environment key whose name matches a credential-like pattern (for example `WANDB_API_KEY`, `token`, `password`, `secret`), whose value is excluded from all written artifacts.

## Requirements

### Requirement 1: Stable W&B settings from the project plan

**User Story:** As an AI/ML researcher, I want W&B settings read from the project plan, so that the entity, project, mode, and local-data policy are consistent and never re-asked.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker begins any task, THE Wandb_Tracker SHALL read the Wandb_Entity, Wandb_Project, Wandb_Mode, and Keep_Local_Data from the Project_Plan rather than prompting for them.
2. IF the Wandb_Mode read from the Project_Plan is not one of `online`, `offline`, or `disabled`, THEN THE Wandb_Tracker SHALL report a configuration-error outcome and SHALL NOT create a W&B Run.
3. WHILE the Wandb_Mode equals `disabled`, THE Wandb_Tracker SHALL set the Wandb_Status to `not_started` and SHALL NOT invoke any Mutating_Wandb_Action.
4. THE Wandb_Tracker SHALL record the resolved Wandb_Mode in the Run_Record as the `wandb_mode` field.

### Requirement 2: Placeholder entity tolerance

**User Story:** As an AI/ML researcher, I want the helper to handle an unconfigured entity gracefully, so that running before the entity is set never crashes the workflow.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker reads the Wandb_Entity, THE Wandb_Tracker SHALL detect whether the value equals the Placeholder_Entity.
2. IF the Wandb_Entity equals the Placeholder_Entity AND the Wandb_Mode equals `online`, THEN THE Wandb_Tracker SHALL decline the online Mutating_Wandb_Action, SHALL report a placeholder-entity outcome, and SHALL exit with code 1.
3. WHERE the Wandb_Entity equals the Placeholder_Entity AND local-only or offline operation is possible, THE Wandb_Tracker SHALL fall back to offline operation and SHALL set the Wandb_Status to `offline`.
4. WHEN the Wandb_Entity equals the Placeholder_Entity, THE Wandb_Tracker SHALL complete without raising an unhandled exception.

### Requirement 3: W&B Run creation

**User Story:** As an AI/ML researcher, I want a W&B Run created for a training run, so that metrics and config are tracked against a real experiment identity.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker creates a W&B Run, THE Wandb_Tracker SHALL treat the creation as a Mutating_Wandb_Action requiring the Approval_Status to equal `approved`.
2. WHILE the Approval_Status equals `approved` AND the Wandb_Entity is not the Placeholder_Entity, THE Wandb_Tracker SHALL create the W&B Run through the Wandb_Client using the Wandb_Entity and Wandb_Project.
3. WHEN the Wandb_Client returns a created Run, THE Wandb_Tracker SHALL record the Wandb_Run_Id and the Wandb_Url in the Run_Record and SHALL set the Wandb_Status to `running`.
4. IF the Approval_Status does not equal `approved`, THEN THE Wandb_Tracker SHALL decline the creation, SHALL report an approval-required outcome, and SHALL exit with code 1.

### Requirement 4: W&B Run resume

**User Story:** As an AI/ML researcher, I want to resume an existing W&B Run, so that a retried or continued training run reuses its tracked identity instead of creating a duplicate.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker is asked to resume a Run that already records a Wandb_Run_Id in the Run_Record, THE Wandb_Tracker SHALL resume the recorded Wandb_Run_Id through the Wandb_Client without creating a new W&B Run.
2. IF a resume target has no recorded Wandb_Run_Id, THEN THE Wandb_Tracker SHALL report a resume-not-possible outcome and SHALL NOT create a new W&B Run.
3. WHEN the Wandb_Tracker resumes a Wandb_Run_Id, THE Wandb_Tracker SHALL preserve the previously recorded Wandb_Run_Id and Wandb_Url in the Run_Record.

### Requirement 5: Group and tag assignment

**User Story:** As an AI/ML researcher, I want related Runs assigned to a shared group with tags, so that a LoRA-rank ablation sweep is comparable within a single W&B group.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker assigns grouping, THE Wandb_Tracker SHALL set the Wandb_Group so that Runs belonging to the same experiment share one Wandb_Group value.
2. WHEN the Wandb_Tracker assigns tags, THE Wandb_Tracker SHALL apply the Wandb_Tags derived from the job configuration to the W&B Run.
3. WHEN the Wandb_Tracker records grouping metadata, THE Wandb_Tracker SHALL write the Wandb_Group and the Wandb_Tags into the Run_Record.
4. WHERE multiple Runs of one experiment are created, THE Wandb_Tracker SHALL assign each Run the same Wandb_Group so that the Runs are comparable within a single W&B group.

### Requirement 6: Config and Git SHA recording

**User Story:** As an AI/ML researcher, I want the resolved config and the Git SHA recorded with the W&B Run, so that each tracked Run is reproducible and traceable to source.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker creates or resumes a W&B Run, THE Wandb_Tracker SHALL record the Resolved_Config as the W&B Run config through the Wandb_Client.
2. WHEN the Wandb_Tracker records provenance, THE Wandb_Tracker SHALL determine the current Git_Sha and SHALL write the Git_Sha into the Run_Record as the `git_sha` field.
3. WHEN the Wandb_Tracker records the Resolved_Config, THE Wandb_Tracker SHALL exclude every Credential_Key value from the recorded config.
4. IF the current Git_Sha cannot be determined, THEN THE Wandb_Tracker SHALL record an unknown Git_Sha marker in the Run_Record and SHALL add a warning to the Output_Envelope.

### Requirement 7: Local W&B directory management

**User Story:** As an AI/ML researcher, I want the local W&B data placed under the run directory, so that W&B artifacts live beside their Harness Run and follow the retention policy.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker configures local storage, THE Wandb_Tracker SHALL set the Local_Wandb_Dir to `experiments/<experiment-id>/runs/<run-id>/wandb/`.
2. WHEN the Local_Wandb_Dir does not exist and a Run is created, THE Wandb_Tracker SHALL create the Local_Wandb_Dir before the W&B Run writes local data.
3. WHILE Keep_Local_Data equals true, THE Wandb_Tracker SHALL retain the Local_Wandb_Dir after a sync completes.
4. THE Wandb_Tracker SHALL confine all local W&B writes to the Local_Wandb_Dir and the Run_Record.

### Requirement 8: Run comparison

**User Story:** As an AI/ML researcher, I want to compare Runs within a group, so that I can assess which configuration performed best.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker compares Runs, THE Wandb_Tracker SHALL compare Runs that share a single Wandb_Group.
2. WHEN the Wandb_Tracker produces a comparison, THE Wandb_Tracker SHALL include each compared Run's Wandb_Run_Id and the compared metric values in the `data` section of the Output_Envelope.
3. IF the requested Wandb_Group contains no comparable Runs, THEN THE Wandb_Tracker SHALL report an empty-comparison outcome in the Output_Envelope.
4. WHEN the Wandb_Tracker reads Run metrics for comparison, THE Wandb_Tracker SHALL obtain the metrics through the Wandb_Client.

### Requirement 9: Sync status check and failure distinction

**User Story:** As an AI/ML researcher, I want W&B sync failures recorded separately from the training outcome, so that a failed sync does not mark the training run as failed.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker checks sync status, THE Wandb_Tracker SHALL query the W&B sync state through the Wandb_Client.
2. WHEN the sync state indicates a completed upload, THE Wandb_Tracker SHALL set the Wandb_Status to `synced` in the Run_Record.
3. IF the sync state indicates a failed upload, THEN THE Wandb_Tracker SHALL set the Wandb_Status to `sync_failed` in the Run_Record and SHALL NOT change the Run_Status.
4. WHILE the Wandb_Mode equals `offline`, THE Wandb_Tracker SHALL set the Wandb_Status to `offline` in the Run_Record.
5. THE Wandb_Tracker SHALL record the Wandb_Status as a field distinct from the Run_Status so that a W&B failure is distinguishable from a training failure.

### Requirement 10: W&B URL parsing from logs

**User Story:** As an AI/ML researcher, I want the W&B URL recovered from log text when needed, so that a Run started outside the helper can still be linked.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker parses a Wandb_Url from log text, THE Wandb_Tracker SHALL treat the parsing as a read-only action that requires no approval.
2. WHEN a Wandb_Url is parsed from log text, THE Wandb_Tracker SHALL extract the Wandb_Run_Id from the parsed Wandb_Url.
3. IF no Wandb_Url is present in the log text, THEN THE Wandb_Tracker SHALL leave the Wandb_Run_Id and Wandb_Url fields in the Run_Record unchanged.

### Requirement 11: Approval gating for mutating W&B actions

**User Story:** As an AI/ML researcher, I want every W&B action that changes remote state to require my approval, so that no Run creation, finish, or sync happens without my consent.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker prepares a Mutating_Wandb_Action, THE Wandb_Tracker SHALL read the Approval_Status from the experiment `plan.md` before executing the action.
2. IF the Approval_Status does not equal `approved`, THEN THE Wandb_Tracker SHALL decline the Mutating_Wandb_Action and SHALL report an approval-required outcome.
3. WHILE the Approval_Status equals `approved`, THE Wandb_Tracker SHALL permit the Mutating_Wandb_Action to execute through the Wandb_Client.
4. WHEN the Wandb_Tracker performs a read-only or local-only action, THE Wandb_Tracker SHALL execute the action without requiring the Approval_Status.

### Requirement 12: Injected W&B client boundary

**User Story:** As an AI/ML researcher, I want all W&B I/O routed through one injected boundary, so that logic is testable and tests never touch the real W&B API or network.

#### Acceptance Criteria

1. THE Wandb_Tracker SHALL route every W&B API call, network call, and filesystem-mutating W&B operation through a single Wandb_Client.
2. WHEN the Wandb_Tracker runs in production, THE Wandb_Tracker SHALL construct the Real_Wandb_Client only within `main()`.
3. WHEN the Wandb_Tracker runs under test with the Fake_Wandb_Client, THE Wandb_Tracker SHALL perform no real W&B API call and no network access.
4. THE Wandb_Tracker SHALL separate pure logic that performs no I/O from the impure operations that pass through the Wandb_Client.

### Requirement 13: Run-to-W&B linkage in run.yaml

**User Story:** As an AI/ML researcher, I want the W&B Run linked to its Harness Run, so that `run.yaml` captures the W&B identity, grouping, and sync state.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker links a W&B Run, THE Wandb_Tracker SHALL write the Wandb_Run_Id, Wandb_Url, Wandb_Group, Wandb_Tags, Wandb_Status, Git_Sha, and Wandb_Mode into the Run_Record.
2. WHEN the Wandb_Tracker updates the Wandb_Status, THE Wandb_Tracker SHALL write the updated Wandb_Status into the Run_Record without modifying the Run_Status.
3. THE Run_Record SHALL NOT contain any secret, token, password, or Credential_Key value.
4. WHEN the Wandb_Tracker writes W&B linkage fields, THE Wandb_Tracker SHALL confine the write to the Run_Record of the targeted Harness Run.

### Requirement 14: Secret safety and redaction

**User Story:** As an AI/ML researcher, I want W&B credentials kept out of every artifact, so that no token or key is committed or recorded.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker records config or metadata, THE Wandb_Tracker SHALL drop every Credential_Key value and SHALL retain only the key names where a name is required.
2. THE Wandb_Tracker SHALL exclude the W&B API key and any other Credential_Key value from the Run_Record and from the Output_Envelope.
3. WHEN the Wandb_Tracker reports an error that references configuration, THE Wandb_Tracker SHALL redact every Credential_Key value from the reported message.

### Requirement 15: Output envelope and exit codes

**User Story:** As an AI/ML researcher, I want a consistent JSON result and exit code, so that the Phase 7 helper composes with the Phase 5 and Phase 6 helpers.

#### Acceptance Criteria

1. WHEN the Wandb_Tracker completes any task, THE Wandb_Tracker SHALL write an Output_Envelope with the fields `status`, `message`, `data`, `errors`, and `warnings` to stdout.
2. WHEN the Wandb_Tracker completes or records an outcome successfully, THE Wandb_Tracker SHALL exit with code 0.
3. WHEN the Wandb_Tracker declines due to a missing approval, a Placeholder_Entity in online mode, or a missing prerequisite, THE Wandb_Tracker SHALL exit with code 1.
4. IF the Wandb_Tracker encounters a filesystem or parse error, THEN THE Wandb_Tracker SHALL exit with code 2.

### Requirement 16: Phase boundaries

**User Story:** As an AI/ML researcher, I want Phase 7 limited to W&B tracking, so that Hugging Face uploads and Git commits remain in their own phases.

#### Acceptance Criteria

1. THE Wandb_Tracker SHALL NOT upload any checkpoint or artifact to the Hugging Face Hub, deferring that work to Phase 8.
2. THE Wandb_Tracker SHALL NOT create any Git commit.
3. THE Wandb_Tracker SHALL exclude W&B cache directories, raw `.out` and `.err` logs, and checkpoints from any content it marks as commit candidates.
