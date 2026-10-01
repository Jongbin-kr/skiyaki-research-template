# Requirements Document

## Introduction

Phase 4 validates the planning-only Golden Path for an AI/ML research request without executing an experiment. The validated flow begins with a LoRA rank-ablation request, discovers repository-backed prior research, resolves material scientific decisions through one-question-at-a-time grilling, generates a reviewable experiment plan and reproducible training/evaluation job YAML, presents a concise approval summary, and stops while awaiting explicit user approval. Validation uses deterministic local fixtures and Python tests; Phase 4 does not create a real Run or contact SSH, Slurm, Weights & Biases, or Hugging Face Hub.

## Glossary

- **Planning_Golden_Path**: The repository workflow that converts a LoRA rank-ablation request into local planning artifacts and an approval request without experiment execution.
- **Planning_Session**: One ordered interaction from the initial research request through the awaiting-approval response.
- **Project_Settings**: Stable environment, execution, Slurm, W&B, Hugging Face, quota, and artifact-policy values recorded in `project-plan.md`.
- **Prior_Research_Evidence**: A repository path and supported finding obtained from `project-log.md`, experiment plans, experiment journals, structured results, job YAML, or relevant Git history.
- **Discovery_Report**: The structured synthesis of inspected sources, comparable baselines, reusable settings, duplication level, gaps, and recommendation.
- **Material_Decision**: A decision about research objective, baseline, primary metric, success criterion, experimental scope, or another parameter that changes experimental meaning.
- **Research_Grill**: The interactive clarification stage that resolves Material_Decisions.
- **Agent_Default**: A value selected by the Planning_Golden_Path rather than explicitly selected by the user or copied from Project_Settings.
- **Experiment_Plan**: `experiments/<experiment-id>/plan.md`, containing structured frontmatter and reviewable research rationale.
- **Job_Configuration**: A reproducible YAML document under `experiments/<experiment-id>/jobs/` describing a planned training or evaluation job.
- **Approval_Summary**: The concise user-facing summary that requests approval after planning artifacts pass validation.
- **Explicit_Approval**: An unambiguous user response authorizing the proposed experiment plan for a later execution phase.
- **Run**: A recorded attempt to execute a Job_Configuration under an experiment `runs/` directory.
- **External_Integration**: SSH access, Slurm submission or query, live W&B access, or Hugging Face Hub access.
- **Scenario_Fixture**: Dedicated test data representing project records, prior research, user turns, expected responses, and expected artifacts.
- **Golden_Path_Validator**: Local Python validation code that checks Scenario_Fixtures and generated planning artifacts deterministically.
- **Guard_Scenario**: A focused negative Scenario_Fixture that demonstrates rejection of prohibited or incomplete behavior.
- **Fixture_Workspace**: A temporary or dedicated fixture path that isolates test writes from user-owned project and experiment data.

## Requirements

### Requirement 1: Planning-only workflow boundary

**User Story:** As a researcher, I want the Phase 4 workflow to produce a complete proposal without side effects, so that I can review scientific and resource decisions before any execution occurs.

#### Acceptance Criteria

1. WHEN a user requests a LoRA rank ablation, THE Planning_Golden_Path SHALL start a Planning_Session with prior-research discovery before Research_Grill or artifact generation.
2. WHILE a Planning_Session lacks Explicit_Approval, THE Planning_Golden_Path SHALL keep the experiment status `awaiting_approval` and the approval status `pending`.
3. WHILE Phase 4 validation is active, THE Planning_Golden_Path SHALL limit operations to local repository reads and local planning-document writes.
4. IF a Planning_Session requests experiment execution before Explicit_Approval, THEN THE Planning_Golden_Path SHALL return an approval-required response without starting execution.
5. IF a Planning_Session requests an External_Integration, THEN THE Planning_Golden_Path SHALL identify the applicable later roadmap phase and preserve the awaiting-approval state.

### Requirement 2: Evidence-backed prior research

**User Story:** As a researcher, I want experiment planning grounded in repository evidence, so that proposed baselines and defaults reflect prior work rather than unsupported assumptions.

#### Acceptance Criteria

1. WHEN prior-research discovery begins, THE Planning_Golden_Path SHALL inspect each available project log, relevant experiment plan, relevant experiment journal, relevant structured result, relevant Job_Configuration, and relevant Git-history entry.
2. WHEN the Planning_Golden_Path reports a prior finding, THE Discovery_Report SHALL associate the finding with at least one repository path or Git commit identifier.
3. WHEN structured results and narrative conclusions describe the same metric, THE Planning_Golden_Path SHALL compare the values and identify any inconsistency in the Discovery_Report.
4. WHEN prior experiments overlap the requested model, dataset, technique, objective, or parameter range, THE Discovery_Report SHALL classify the overlap as exact duplicate, near duplicate, related work, or novel work.
5. IF no populated root project log exists, THEN THE Discovery_Report SHALL record the missing source without treating a template file as project evidence.
6. IF available evidence does not support a baseline value, THEN THE Planning_Golden_Path SHALL mark the baseline value unresolved for Research_Grill rather than inventing a value.

### Requirement 3: Focused Research Grill

**User Story:** As a researcher, I want concise clarification that asks only consequential questions, so that planning reaches scientific completeness without repeating known configuration.

#### Acceptance Criteria

1. WHEN the Research_Grill has multiple unresolved Material_Decisions, THE Planning_Golden_Path SHALL present exactly one question in the current assistant turn.
2. WHEN the user answers a Research_Grill question, THE Planning_Golden_Path SHALL resolve or refine that Material_Decision before presenting the next question.
3. WHILE Project_Settings contain a stable setting, THE Planning_Golden_Path SHALL consume the recorded value without asking the user to restate the value.
4. WHEN a user answer is insufficient to determine a measurable decision, THE Planning_Golden_Path SHALL ask one focused follow-up question or propose a labeled Agent_Default.
5. WHEN the baseline, primary metric, and success criterion are resolved, THE Planning_Golden_Path SHALL stop asking questions that concern implementation details or recorded Project_Settings.
6. IF a user answer conflicts with Prior_Research_Evidence, THEN THE Planning_Golden_Path SHALL ask one focused question that distinguishes intentional deviation from misunderstanding.

### Requirement 4: Complete decision record and defaults

**User Story:** As a reviewer, I want user choices, inherited settings, and agent-selected defaults distinguished, so that I can audit the origin of every material plan value.

#### Acceptance Criteria

1. WHEN Research_Grill completes, THE Planning_Golden_Path SHALL record the research objective, baseline, primary metric, success criterion, ablation scope, and key controlled parameters.
2. WHEN the Planning_Golden_Path selects an Agent_Default, THE Experiment_Plan SHALL record the value, rationale, and evidence source or explicit assumption.
3. WHEN the Experiment_Plan contains Agent_Default entries, THE Experiment_Plan SHALL place an Agent-Determined Defaults summary before detailed design and risk sections.
4. WHEN Project_Settings supply a value, THE Experiment_Plan SHALL distinguish the inherited Project_Settings value from Agent_Default entries.
5. IF a required baseline, primary metric, or success criterion remains unresolved, THEN THE Planning_Golden_Path SHALL keep the Planning_Session in Research_Grill and defer approval-request generation.

### Requirement 5: Reviewable experiment plan

**User Story:** As a researcher, I want a complete experiment plan, so that I can assess purpose, comparison validity, and expected outcomes before approval.

#### Acceptance Criteria

1. WHEN all required Material_Decisions are resolved, THE Planning_Golden_Path SHALL create an Experiment_Plan with schema version, kebab-case experiment identifier, `awaiting_approval` status, primary metric name and direction, measurable success criteria, Job_Configuration paths, and pending approval metadata.
2. WHEN the Experiment_Plan is created, THE Planning_Golden_Path SHALL include the objective, testable hypothesis, evidence-backed baseline, Agent_Default summary, variables, controls, design rationale, risks, limitations, and supported/refuted outcome interpretations.
3. WHEN the Experiment_Plan references Prior_Research_Evidence, THE Experiment_Plan SHALL include repository paths or Git commit identifiers for the referenced evidence.
4. WHEN a planned comparison uses a baseline metric, THE Experiment_Plan SHALL specify the baseline value, metric direction, evaluation dataset split, and source.
5. IF a generated Experiment_Plan contains an unresolved placeholder, THEN THE Golden_Path_Validator SHALL reject the Experiment_Plan before approval-request generation.

### Requirement 6: Reproducible training and evaluation jobs

**User Story:** As a researcher, I want reproducible YAML job definitions, so that approved work can be executed consistently in a later phase.

#### Acceptance Criteria

1. WHEN the Experiment_Plan is created, THE Planning_Golden_Path SHALL create one training Job_Configuration and one evaluation Job_Configuration referenced by the Experiment_Plan.
2. WHEN the training Job_Configuration is created, THE Planning_Golden_Path SHALL encode the LoRA rank matrix, model, dataset and split, controlled hyperparameters, seed, entrypoint, resource request, tracking destination metadata, and artifact policy.
3. WHEN the evaluation Job_Configuration is created, THE Planning_Golden_Path SHALL encode checkpoint resolution intent, dataset and split, primary metric, secondary metrics, entrypoint, resource request, and matching experiment-group metadata.
4. WHEN a Job_Configuration requests a GPU in an SSH-targeted project, THE Job_Configuration SHALL declare the Slurm backend and label execution as unavailable until Phase 6.
5. WHEN a Job_Configuration includes W&B metadata, THE Job_Configuration SHALL treat the metadata as a planned destination without performing live verification before Phase 7.
6. WHEN a Job_Configuration includes Hugging Face metadata, THE Job_Configuration SHALL treat the metadata as a planned destination without upload or live verification before Phase 8.
7. IF a Job_Configuration contains a secret, credential, unresolved required placeholder, or missing required key, THEN THE Golden_Path_Validator SHALL reject the planning output before approval-request generation.

### Requirement 7: Concise approval handoff

**User Story:** As a researcher, I want a concise approval summary, so that I can make an informed decision without reading every YAML field first.

#### Acceptance Criteria

1. WHEN the Experiment_Plan and both Job_Configurations pass local validation, THE Planning_Golden_Path SHALL present an Approval_Summary and wait for Explicit_Approval.
2. WHEN the Approval_Summary is presented, THE Approval_Summary SHALL place the recommended plan and Agent_Default summary before experiment details.
3. WHEN the Approval_Summary is presented, THE Approval_Summary SHALL include the objective, hypothesis, evidence-backed baseline, primary metric, success criterion, ablation matrix, estimated run count, resource estimate, principal risks, planned W&B and Hugging Face destinations, and artifact paths.
4. WHEN the Approval_Summary describes External_Integration metadata, THE Approval_Summary SHALL label each destination as planned and unverified in Phase 4.
5. WHEN the Approval_Summary ends, THE Approval_Summary SHALL request approval or modification and state that no execution or Run creation has occurred.

### Requirement 8: Approval and side-effect guards

**User Story:** As a researcher, I want enforceable approval guards, so that a planning interaction cannot consume resources or alter execution records.

#### Acceptance Criteria

1. WHILE Explicit_Approval is absent, THE Planning_Golden_Path SHALL create zero Run directories and zero Run metadata files.
2. WHILE Phase 4 validation is active, THE Planning_Golden_Path SHALL perform zero SSH, Slurm, live W&B, and Hugging Face Hub operations.
3. WHILE Phase 4 validation is active, THE Planning_Golden_Path SHALL create zero Git commits.
4. IF a generated command invokes a training entrypoint, evaluation entrypoint, Run initializer, SSH client, Slurm client, W&B client, Hugging Face client, or Git commit operation, THEN THE Golden_Path_Validator SHALL fail the Scenario_Fixture.
5. IF user text contains an execution instruction before approval, THEN THE Planning_Golden_Path SHALL preserve generated planning artifacts and return an approval-required response.

### Requirement 9: Deterministic fixture-based validation

**User Story:** As a maintainer, I want deterministic local scenario validation, so that Phase 4 behavior can be reviewed and regression-tested without external dependencies.

#### Acceptance Criteria

1. WHEN the Golden_Path_Validator runs, THE Golden_Path_Validator SHALL use Scenario_Fixtures for Project_Settings, prior research, user turns, expected assistant turns, and expected planning artifacts.
2. WHEN the Golden_Path_Validator evaluates the successful Scenario_Fixture, THE Golden_Path_Validator SHALL verify the ordered flow from request through prior research, Research_Grill, artifact generation, Approval_Summary, and awaiting-approval termination.
3. WHEN the Golden_Path_Validator evaluates Guard_Scenarios, THE Golden_Path_Validator SHALL cover multi-question turns, stable-setting re-asks, unsupported evidence claims, incomplete metric-baseline-success decisions, unresolved placeholders, pre-approval execution, Run creation, and External_Integration attempts.
4. WHEN tests create or modify planning artifacts, THE Golden_Path_Validator SHALL confine writes to a Fixture_Workspace.
5. WHEN validation completes, THE Golden_Path_Validator SHALL leave user-owned experiment directories, project records, and existing example artifacts byte-for-byte unchanged.
6. WHEN identical Scenario_Fixtures are validated repeatedly, THE Golden_Path_Validator SHALL produce equivalent pass/fail results and normalized diagnostics.
7. IF a Scenario_Fixture depends on wall-clock time, network state, credentials, or mutable external service data, THEN THE Golden_Path_Validator SHALL reject the Scenario_Fixture as nondeterministic.

### Requirement 10: Repository integration and traceability

**User Story:** As a maintainer, I want Phase 4 changes integrated with existing skills and conventions, so that the Golden Path strengthens the template without introducing a separate research harness.

#### Acceptance Criteria

1. WHEN Phase 4 implementation adds validation logic, THE Planning_Golden_Path SHALL use Python tests and repository-local fixtures without adding a common experiment runner or agent loop.
2. WHEN Phase 4 implementation updates skill guidance, THE Planning_Golden_Path SHALL preserve the distinct responsibilities of discover-prior-research, grill-me, and plan-ml-experiment.
3. WHEN automated tests report a failure, THE Golden_Path_Validator SHALL identify the Scenario_Fixture, violated requirement identifier, and relevant artifact or turn.
4. WHEN implementation tasks are defined, THE Planning_Golden_Path SHALL map every task to one or more acceptance-criteria identifiers.
5. WHEN the Phase 4 implementation suite completes, THE Golden_Path_Validator SHALL validate the existing LoRA example as read-only evidence and keep the example experiment unchanged.
