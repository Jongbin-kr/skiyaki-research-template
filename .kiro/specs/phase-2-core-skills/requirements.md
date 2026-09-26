# Requirements Document

## Introduction

This document specifies requirements for Phase 2: Core Skills Implementation. Phase 2 adds supporting materials to the six skills defined in Phase 1, making them executable by AI agents. Supporting materials include reference documentation (policies, schemas, examples), asset templates (YAML/Markdown files), and deterministic helper scripts where needed.

The implementation follows the architecture principle: **"SKILL.md is workflow, scripts/ are deterministic helpers, src/ is research code"**. This phase focuses on local execution only, with SSH/Slurm, W&B API, and HF Hub integrations deferred to future phases.

## Glossary

- **Skill**: A workflow defined in `.agents/skills/{skill-name}/SKILL.md`
- **Supporting_Materials**: Files that enable skill execution (references, assets, scripts)
- **Reference_Document**: Markdown file in `references/` providing policies, schemas, or guidelines
- **Asset_Template**: Template file in `assets/` used by skills to generate experiment artifacts
- **Helper_Script**: Python script in `scripts/` performing deterministic validation or initialization
- **Main_Agent**: The primary AI agent orchestrating skill execution
- **Codex**: The AI agent that executes skill workflows
- **Run**: A single execution of a training or evaluation job
- **Job**: A configuration file defining execution parameters for training or evaluation
- **Experiment**: A collection of related runs organized under a research objective

## Requirements

### Requirement 1: grill-me Skill Supporting Materials

**User Story:** As Codex, I want reference materials for the grill-me skill, so that I can systematically clarify research objectives through targeted questions.

#### Acceptance Criteria

1. THE grill-me Skill SHALL have a `references/grill-policy.md` file
2. THE grill-policy SHALL define question priority order (metric, baseline, success criteria, parameters)
3. THE grill-policy SHALL specify project-plan.md settings that must not be re-asked
4. THE grill-policy SHALL define termination criteria for questioning
5. THE grill-policy SHALL provide guidance for handling vague user answers

### Requirement 2: discover-prior-research Skill Supporting Materials

**User Story:** As Codex, I want reference materials for the discover-prior-research skill, so that I can systematically search for and consolidate prior experiment findings.

#### Acceptance Criteria

1. THE discover-prior-research Skill SHALL have a `references/search-strategy.md` file
2. THE search-strategy SHALL define search locations (project-log.md, experiments/*/journal.md, experiments/*/results.yaml, Git history)
3. THE search-strategy SHALL specify evidence consolidation approach
4. THE search-strategy SHALL define duplicate experiment detection logic
5. THE search-strategy SHALL specify reporting format for findings to Main_Agent

### Requirement 3: plan-ml-experiment Skill Supporting Materials

**User Story:** As Codex, I want templates and reference materials for the plan-ml-experiment skill, so that I can generate consistent, valid experiment plans and job configurations.

#### Acceptance Criteria

1. THE plan-ml-experiment Skill SHALL have asset templates in `assets/` directory
2. THE plan-ml-experiment Skill SHALL provide `assets/experiment-plan.md` template with YAML frontmatter structure
3. THE plan-ml-experiment Skill SHALL provide `assets/train-job.yaml` template with matrix support and resource fields
4. THE plan-ml-experiment Skill SHALL provide `assets/evaluate-job.yaml` template
5. THE plan-ml-experiment Skill SHALL have `references/plan-schema.md` defining frontmatter fields
6. THE plan-ml-experiment Skill SHALL have `references/approval-policy.md` defining approval requirements
7. THE plan-schema SHALL distinguish required fields from optional fields
8. THE approval-policy SHALL specify what changes require user re-approval
9. THE approval-policy SHALL define approval summary format

### Requirement 4: train-llm Skill Supporting Materials

**User Story:** As Codex, I want helper scripts and reference materials for the train-llm skill, so that I can validate job configurations, initialize run tracking, and execute training with proper environment management.

#### Acceptance Criteria

1. THE train-llm Skill SHALL have reference documents in `references/` directory
2. THE train-llm Skill SHALL have helper scripts in `scripts/` directory
3. THE train-llm Skill SHALL provide `references/execution-policy.md` defining execution requirements
4. THE train-llm Skill SHALL provide `references/run-tracking.md` defining run metadata structure
5. THE execution-policy SHALL specify when Slurm is required
6. THE execution-policy SHALL define environment manager detection approach (conda, uv, venv)
7. THE execution-policy SHALL specify quota checking approach
8. THE execution-policy SHALL limit Phase 2 to local execution only
9. THE run-tracking SHALL define Run ID format
10. THE run-tracking SHALL define run status transitions
11. THE run-tracking SHALL define run directory structure
12. THE train-llm Skill SHALL provide `scripts/validate_job.py` script
13. THE train-llm Skill SHALL provide `scripts/initialize_run.py` script
14. WHEN validate_job.py validates a job configuration THEN the script SHALL check required fields
15. WHEN validate_job.py validates a job configuration THEN the script SHALL verify entrypoint exists
16. WHEN validate_job.py validates a job configuration THEN the script SHALL check resource limits against quotas
17. WHEN validate_job.py completes validation THEN the script SHALL output JSON validation results
18. WHEN initialize_run.py initializes a run THEN the script SHALL create run directory structure
19. WHEN initialize_run.py initializes a run THEN the script SHALL generate Run ID
20. WHEN initialize_run.py initializes a run THEN the script SHALL write initial run.yaml
21. WHEN initialize_run.py initializes a run THEN the script SHALL copy and resolve job.yaml to resolved-job.yaml
22. WHEN initialize_run.py completes initialization THEN the script SHALL output run metadata JSON

### Requirement 5: evaluate-llm Skill Supporting Materials

**User Story:** As Codex, I want reference materials for the evaluate-llm skill, so that I can compare training runs, assess success criteria, and generate results summaries.

#### Acceptance Criteria

1. THE evaluate-llm Skill SHALL have reference documents in `references/` directory
2. THE evaluate-llm Skill SHALL provide `references/result-schema.md` defining results.yaml structure
3. THE evaluate-llm Skill SHALL provide `references/comparison-guidelines.md` defining comparison logic
4. THE result-schema SHALL define experiment metadata format
5. THE result-schema SHALL define best run identification format
6. THE result-schema SHALL define metric format standards
7. THE result-schema SHALL define baseline comparison format
8. THE comparison-guidelines SHALL specify run comparison approach
9. THE comparison-guidelines SHALL define success criteria assessment logic
10. THE comparison-guidelines SHALL specify when to call W&B Analyst subagent

### Requirement 6: finalize-experiment Skill Supporting Materials

**User Story:** As Codex, I want reference materials for the finalize-experiment skill, so that I can verify experiment completeness, validate artifacts, and propose safe Git commits.

#### Acceptance Criteria

1. THE finalize-experiment Skill SHALL have reference documents in `references/` directory
2. THE finalize-experiment Skill SHALL provide `references/completion-checklist.md` defining completion requirements
3. THE finalize-experiment Skill SHALL provide `references/git-safety.md` defining commit safety rules
4. THE completion-checklist SHALL define required files verification
5. THE completion-checklist SHALL define artifact link validation approach
6. THE completion-checklist SHALL define commit proposal format
7. THE git-safety SHALL specify files that must not be committed
8. THE git-safety SHALL define secret detection patterns
9. THE git-safety SHALL define large file detection approach

### Requirement 7: Script Architecture

**User Story:** As a developer, I want helper scripts to follow consistent architectural principles, so that they are maintainable, testable, and safe to execute.

#### Acceptance Criteria

1. WHEN a helper script is invoked THEN the script SHALL accept explicit file paths as arguments
2. THE helper scripts SHALL NOT rely on implicit current working directory
3. WHEN a helper script completes execution THEN the script SHALL output JSON for agent parsing
4. WHERE a helper script performs state changes THEN the script SHALL support --dry-run flag
5. THE helper scripts SHALL NOT contain hardcoded project values
6. THE helper scripts SHALL NOT import from project src/ directory
7. THE helper scripts SHALL handle missing files gracefully with clear error messages

### Requirement 8: Integration Requirements

**User Story:** As Codex, I want supporting materials to reference each other correctly, so that skills can compose and share common understanding.

#### Acceptance Criteria

1. THE grill-me references SHALL document project-plan.md schema
2. THE plan-ml-experiment Skill SHALL use asset templates from `assets/` directory
3. THE train-llm scripts SHALL support multiple environment managers (conda, uv, venv)
4. THE evaluate-llm references SHALL specify how to read training outputs
5. THE finalize-experiment references SHALL specify how to verify plan-ml-experiment outputs

### Requirement 9: Phase 2 Boundaries

**User Story:** As a developer, I want Phase 2 scope clearly bounded, so that I can focus on foundational capabilities without premature optimization.

#### Acceptance Criteria

1. THE Phase 2 implementation SHALL support local execution only
2. THE Phase 2 implementation SHALL NOT implement SSH integration
3. THE Phase 2 implementation SHALL NOT implement Slurm integration
4. THE Phase 2 implementation SHALL NOT implement W&B API integration
5. THE Phase 2 implementation SHALL accept W&B configuration placeholders
6. THE Phase 2 implementation SHALL NOT implement HF Hub upload
7. THE Phase 2 implementation SHALL accept HF Hub configuration placeholders

### Requirement 10: Validation

**User Story:** As a developer, I want supporting materials validated against the example experiment, so that I can trust they work correctly.

#### Acceptance Criteria

1. THE supporting materials SHALL be testable with experiments/example-lora-rank-ablation/
2. WHEN a script encounters missing files THEN the script SHALL handle the error gracefully
3. THE asset templates SHALL produce parseable YAML output
4. THE asset templates SHALL produce well-formed Markdown output
