# Requirements Document

## Introduction

This document specifies Phase 3 of the AI/ML Research Workspace: strengthening the five existing specialist agent descriptions and adding bounded Main Agent routing. Phase 3 preserves every existing description filename, standardizes delegation contracts, and documents future external capabilities without implementing W&B, Hugging Face Hub, SSH, or Slurm integrations.

Phase 3 is documentation-only. Conformance is established through structured documentation review rather than a new automated contract validator.

## Glossary

- **Phase_3_Documentation**: The root `AGENTS.md`, five files in `agent-descriptions/`, and relevant `README.md` sections modified during Phase 3.
- **`AGENTS.md`**: The root Markdown policy document that governs Main_Agent routing and workflow behavior.
- **`README.md`**: The root user guide that documents specialist discoverability and roadmap availability.
- **W&B**: Weights & Biases, the external experiment-tracking service whose live integration is assigned to Phase 7.
- **Hugging Face Hub**: The external model repository service whose live integration is assigned to Phase 8.
- **SSH**: Secure Shell access to remote infrastructure, assigned with Slurm execution support to Phase 6.
- **Slurm**: The external cluster workload manager whose live integration is assigned to Phase 6.
- **Main_Agent**: The primary agent governed by the root `AGENTS.md`.
- **Specialist_Description**: A Markdown contract in `agent-descriptions/` that defines one specialist's mission, invocation criteria, inputs, actions, boundaries, and outputs.
- **Bounded_Delegation**: Delegation of one explicit task with a defined scope, inputs, expected outputs, and approval constraints.
- **Selective_Loading**: Reading only the Specialist_Description required for the selected delegation.
- **External_Capability**: A capability that communicates with W&B, Hugging Face Hub, SSH infrastructure, or Slurm infrastructure.
- **Roadmap_Gate**: A phase boundary that prevents an External_Capability from being presented as currently operational before its implementation phase.
- **Documentation_Review**: A manual, checklist-based inspection of headings, routing mappings, filenames, phase gates, cross-references, and safety boundaries.
- **Research_Journal_Git_Specialist**: The specialist defined by `agent-descriptions/research-journal-git.md`.
- **WandB_Analyst**: The specialist defined by `agent-descriptions/wandb-analyst.md`.
- **Hugging_Face_Curator**: The routing name for the specialist defined by `agent-descriptions/huggingface-managing-specialist.md`.
- **Visualization_Specialist**: The specialist defined by `agent-descriptions/visualization-specialist.md`.
- **Slurm_Debugger**: The routing name for the specialist defined by `agent-descriptions/slurm-managing-specialist.md`.

## Requirements

### Requirement 1: Preserve and Identify Specialist Descriptions

**User Story:** As a template maintainer, I want stable specialist description paths, so that existing links and workflows remain compatible.

#### Acceptance Criteria

1. THE Phase_3_Documentation SHALL preserve the filenames `research-journal-git.md`, `wandb-analyst.md`, `huggingface-managing-specialist.md`, `visualization-specialist.md`, and `slurm-managing-specialist.md`.
2. THE Phase_3_Documentation SHALL map Hugging_Face_Curator to `agent-descriptions/huggingface-managing-specialist.md`.
3. THE Phase_3_Documentation SHALL map Slurm_Debugger to `agent-descriptions/slurm-managing-specialist.md`.
4. THE Phase_3_Documentation SHALL use one canonical routing name for each Specialist_Description in `AGENTS.md`.
5. WHEN a display name differs from a preserved filename, THE Phase_3_Documentation SHALL state the display-name-to-file mapping explicitly.

### Requirement 2: Standardize Specialist Contracts

**User Story:** As the Main_Agent, I want complete specialist contracts, so that each delegation has explicit boundaries and predictable results.

#### Acceptance Criteria

1. THE Specialist_Description SHALL define Mission, When to Invoke, Required Inputs, Allowed Actions, Prohibited Actions, Required Output, and Escalation sections.
2. THE Specialist_Description SHALL define the artifacts or evidence that the specialist may read.
3. THE Specialist_Description SHALL define the files or artifacts that the specialist may create or modify.
4. THE Specialist_Description SHALL define approval-gated actions applicable to the specialist.
5. WHEN required input is absent, THE Specialist_Description SHALL direct the specialist to report the missing input to the Main_Agent.
6. WHEN a requested action exceeds the specialist boundary, THE Specialist_Description SHALL direct the specialist to stop and return the out-of-scope action to the Main_Agent.
7. THE Specialist_Description SHALL require outputs to identify evidence sources, completed work, unresolved risks, and recommended next actions.

### Requirement 3: Route Bounded Delegations from AGENTS.md

**User Story:** As the Main_Agent, I want deterministic routing guidance, so that I delegate only when specialist expertise adds value.

#### Acceptance Criteria

1. THE `AGENTS.md` SHALL define the routing trigger and Specialist_Description path for each of the five specialists.
2. WHEN one specialist matches a bounded task, THE Main_Agent SHALL load only the matching Specialist_Description before delegation.
3. WHEN multiple specialists could match a task, THE Main_Agent SHALL select the narrowest specialist that can complete the bounded task.
4. WHEN a workflow needs multiple specialists, THE Main_Agent SHALL delegate separate bounded tasks and load each Specialist_Description only before the corresponding delegation.
5. WHEN no specialist matches a task, THE Main_Agent SHALL retain the task instead of loading every Specialist_Description.
6. WHEN delegating a task, THE Main_Agent SHALL provide the task objective, permitted scope, relevant file paths or evidence, expected output, and applicable approval constraints.
7. THE `AGENTS.md` SHALL prohibit loading all Specialist_Descriptions by default.

### Requirement 4: Enforce Roadmap Gates

**User Story:** As a researcher, I want current capabilities distinguished from roadmap capabilities, so that documentation does not promise unavailable integrations.

#### Acceptance Criteria

1. WHILE Phase 6 is incomplete, THE Phase_3_Documentation SHALL describe SSH and Slurm External_Capabilities as unavailable for execution and live cluster diagnosis.
2. WHILE Phase 7 is incomplete, THE Phase_3_Documentation SHALL describe W&B API External_Capabilities as unavailable.
3. WHILE Phase 8 is incomplete, THE Phase_3_Documentation SHALL describe Hugging Face Hub External_Capabilities as unavailable.
4. WHERE an External_Capability is roadmap-gated, THE Specialist_Description SHALL distinguish currently permitted local documentation or artifact analysis from the future External_Capability.
5. IF a request requires a roadmap-gated External_Capability, THEN THE Specialist_Description SHALL return the phase dependency and a non-executing next step to the Main_Agent.
6. THE Phase_3_Documentation SHALL preserve Phase 3 as documentation and routing work without adding network clients, command wrappers, credentials, or execution automation.

### Requirement 5: Preserve Safety and Approval Boundaries

**User Story:** As a researcher, I want specialist actions constrained by existing safety rules, so that delegation cannot bypass approvals or alter evidence improperly.

#### Acceptance Criteria

1. THE Specialist_Description SHALL preserve explicit user approval before Git commits, job execution, job resubmission, configuration changes, artifact uploads, or destructive remote actions applicable to the specialist.
2. THE Specialist_Description SHALL prohibit committing or exposing secrets, tokens, credentials, model checkpoints, W&B caches, and raw Slurm logs.
3. THE Research_Journal_Git_Specialist SHALL separate discovery responsibilities from finalization responsibilities.
4. THE WandB_Analyst SHALL preserve source metric values.
5. THE WandB_Analyst SHALL identify unavailable live W&B access as a Phase 7 dependency.
6. THE Hugging_Face_Curator SHALL preserve project privacy and push-policy constraints.
7. THE Hugging_Face_Curator SHALL identify Hugging Face Hub operations as a Phase 8 dependency.
8. THE Visualization_Specialist SHALL preserve source data values.
9. THE Visualization_Specialist SHALL disclose transformations used to produce figures.
10. THE Slurm_Debugger SHALL avoid job submission, cancellation, resubmission, and configuration mutation.
11. THE Slurm_Debugger SHALL identify live Slurm access as a Phase 6 dependency.

### Requirement 6: Maintain Human-Facing Documentation Consistency

**User Story:** As a template user, I want the README and routing rules to agree, so that specialist names, paths, and availability are unambiguous.

#### Acceptance Criteria

1. THE `README.md` SHALL list all five specialist routing names with their preserved Specialist_Description paths.
2. THE `README.md` SHALL identify Slurm External_Capabilities as Phase 6, W&B External_Capabilities as Phase 7, and Hugging Face Hub External_Capabilities as Phase 8.
3. THE `README.md` SHALL describe selective specialist loading and bounded delegation consistently with `AGENTS.md`.
4. WHEN Phase_3_Documentation references a Specialist_Description, THE Phase_3_Documentation SHALL use an existing relative path.
5. THE Phase_3_Documentation SHALL avoid claiming that roadmap-gated External_Capabilities are operational in Phase 3.

### Requirement 7: Validate Through Documentation Review

**User Story:** As a maintainer, I want reviewable Phase 3 checks, so that contract quality can be verified without introducing a validator program.

#### Acceptance Criteria

1. THE Documentation_Review SHALL verify the seven required contract sections in every Specialist_Description.
2. THE Documentation_Review SHALL verify all five canonical routing-name-to-file mappings in `AGENTS.md` and `README.md`.
3. THE Documentation_Review SHALL verify Phase 6, Phase 7, and Phase 8 Roadmap_Gates across relevant Specialist_Descriptions, `AGENTS.md`, and `README.md`.
4. THE Documentation_Review SHALL verify that relative links and preserved filenames resolve within the repository.
5. THE Documentation_Review SHALL verify that each prohibited or approval-gated action has an explicit boundary in the applicable Specialist_Description.
6. THE Documentation_Review SHALL record findings as a checklist in the implementation change or pull-request review without adding a new automated contract validator.
7. IF the Documentation_Review finds a conflict, THEN THE Phase_3_Documentation SHALL resolve the conflict before Phase 3 is considered complete.

### Requirement 8: Limit Phase 3 Scope

**User Story:** As a template maintainer, I want Phase 3 narrowly scoped, so that later roadmap phases retain clear ownership of integrations and execution behavior.

#### Acceptance Criteria

1. THE Phase_3_Documentation SHALL modify only documentation needed for specialist contracts, Main_Agent routing, specialist discoverability, and Phase 3 review.
2. THE Phase_3_Documentation SHALL retain existing skill filenames and existing specialist filenames.
3. THE Phase_3_Documentation SHALL exclude implementation of SSH, Slurm, W&B API, and Hugging Face Hub operations.
4. THE Phase_3_Documentation SHALL exclude a new executable contract-validation utility.
5. THE Phase_3_Documentation SHALL exclude changes to experiment execution, evaluation, run tracking, and artifact upload code.
