# Requirements Document

## Introduction

This document specifies the requirements for Phase 1 of the AI/ML Research Workspace GitHub Template. The template combines an AI/ML project skeleton with a Codex Research Harness, enabling researchers to create new research projects that integrate with Codex's agent system for experiment planning, execution, and tracking.

Phase 1 focuses on creating the foundational repository structure without external system connections (SSH, Slurm, W&B, Hugging Face). The template must be immediately usable via GitHub's "Use this template" feature.

## Glossary

- **Template_Repository**: The GitHub repository that serves as the source for new AI/ML research projects
- **Research_Project**: A user's project instance created from the Template_Repository
- **Codex**: OpenAI's AI development environment that provides agent capabilities
- **Main_Agent**: The primary Codex agent defined in AGENTS.md that orchestrates research workflows
- **Skill**: A reusable research workflow definition stored in .agents/skills/
- **Experiment**: A single research question validation unit with plan, jobs, runs, and results
- **Job**: A planned execution configuration for training or evaluation
- **Run**: A single execution attempt of a Job
- **Harness**: The collection of agent definitions, skills, and templates that enable AI-assisted research

## Requirements

### Requirement 1

**User Story:** As a GitHub user, I want to create a new AI/ML research project from a template, so that I can start research with pre-configured Codex integration.

#### Acceptance Criteria

1. WHEN a user clicks "Use this template" on GitHub, THE Template_Repository SHALL create a new Research_Project with complete directory structure
2. THE Template_Repository SHALL include a README.md that explains setup steps and project structure
3. THE Research_Project SHALL be functional immediately after creation without requiring Harness installation
4. THE Template_Repository SHALL use MIT or Apache 2.0 license to allow unrestricted research use

### Requirement 2

**User Story:** As a researcher, I want Codex to follow consistent research workflow rules, so that experiment planning and execution are reliable.

#### Acceptance Criteria

1. THE Research_Project SHALL contain an AGENTS.md file at the repository root
2. THE AGENTS.md SHALL define core research workflow rules that apply to all experiments
3. THE AGENTS.md SHALL specify when to require Slurm execution for GPU and CPU-heavy jobs
4. THE AGENTS.md SHALL define approval requirements before job execution, after material changes, and before Git commits
5. THE AGENTS.md SHALL prohibit committing secrets, checkpoints, W&B caches, and raw Slurm logs
6. THE AGENTS.md SHALL define experiment completion criteria including evaluation, tracking, uploads, and documentation
7. WHEN Codex opens the Research_Project, THE Main_Agent SHALL apply rules from AGENTS.md

### Requirement 3

**User Story:** As a researcher, I want reusable research workflow definitions, so that I can execute standard procedures consistently.

#### Acceptance Criteria

1. THE Research_Project SHALL contain a .agents/skills/ directory
2. THE Research_Project SHALL include a grill-me skill for clarifying experimental decisions
3. THE Research_Project SHALL include a discover-prior-research skill for searching past experiments
4. THE Research_Project SHALL include a plan-ml-experiment skill for creating experiment plans
5. THE Research_Project SHALL include a train-llm skill for training execution
6. THE Research_Project SHALL include an evaluate-llm skill for evaluation execution
7. THE Research_Project SHALL include a finalize-experiment skill for completing experiments
8. WHEN a Skill requires supporting documentation, THE Skill SHALL store it in a references/ subdirectory

### Requirement 4

**User Story:** As a researcher, I want to define project-specific execution policies, so that Codex follows my infrastructure and resource constraints.

#### Acceptance Criteria

1. THE Research_Project SHALL contain a project-plan.md file at the repository root
2. THE project-plan.md SHALL use Markdown format with YAML frontmatter
3. THE project-plan.md frontmatter SHALL include environment manager specification (miniconda, uv, venv)
4. THE project-plan.md frontmatter SHALL include execution configuration (default target, SSH host, remote path)
5. THE project-plan.md frontmatter SHALL include Slurm configuration (partition, account, qos, resource limits)
6. THE project-plan.md frontmatter SHALL include W&B configuration (entity, project, mode)
7. THE project-plan.md frontmatter SHALL include Hugging Face configuration (namespace, privacy, push policy)
8. THE project-plan.md body SHALL include research objectives, scope, and baseline information
9. THE project-plan.md SHALL NOT contain secrets, tokens, or authentication credentials

### Requirement 5

**User Story:** As a researcher, I want to track project-level research progress, so that I can understand what has been learned over time.

#### Acceptance Criteria

1. THE Research_Project SHALL contain a project-log.md file at the repository root
2. THE project-log.md SHALL use chronological entry format with date headers
3. WHEN an experiment completes, THE project-log.md SHALL record conclusions, best runs, and links to experiments
4. THE project-log.md SHALL NOT duplicate detailed experiment information already in experiment directories

### Requirement 6

**User Story:** As a researcher, I want a standard structure for organizing experiments, so that all experimental artifacts are consistently located.

#### Acceptance Criteria

1. THE Research_Project SHALL contain an experiments/ directory at the repository root
2. THE Research_Project SHALL provide experiment templates in templates/experiment-plan.md
3. THE experiment template SHALL use Markdown with YAML frontmatter
4. THE experiment frontmatter SHALL include experiment ID, status, primary metric, success criteria, and approval fields
5. THE experiment structure SHALL include subdirectories for jobs/, runs/, and figures/
6. THE experiment structure SHALL include files for plan.md, results.yaml, history.md, and journal.md

### Requirement 7

**User Story:** As a researcher, I want templates for Job configurations, so that I can define reproducible training and evaluation settings.

#### Acceptance Criteria

1. THE Research_Project SHALL provide a train-job.yaml template in templates/
2. THE Research_Project SHALL provide an evaluate-job.yaml template in templates/
3. THE Job template SHALL include fields for job ID, type, entrypoint, and parameters
4. THE Job template SHALL include matrix support for ablation studies
5. THE Job template SHALL include resource specifications (backend, GPUs, CPUs, memory, time)
6. THE Job template SHALL include W&B configuration fields
7. THE Job template SHALL include Hugging Face push policy fields

### Requirement 8

**User Story:** As a researcher, I want templates for Run tracking, so that I can record every execution attempt consistently.

#### Acceptance Criteria

1. THE Research_Project SHALL provide a run.yaml template in templates/
2. THE run template SHALL include Run ID, Job reference, status, and timestamps
3. THE run template SHALL include Slurm job ID and array task ID fields
4. THE run template SHALL include W&B run ID and URL fields
5. THE run template SHALL include resolved configuration reference

### Requirement 9

**User Story:** As a researcher, I want templates for experiment results and documentation, so that I can record outcomes consistently.

#### Acceptance Criteria

1. THE Research_Project SHALL provide a results.yaml template in templates/
2. THE Research_Project SHALL provide a history.md template in templates/
3. THE Research_Project SHALL provide a journal.md template in templates/
4. THE Research_Project SHALL provide an artifacts.yaml template in templates/
5. THE results template SHALL include primary and secondary metrics, best run references, and success determination
6. THE history template SHALL use chronological fact-based entry format
7. THE journal template SHALL use interpretation-focused entry format with conclusions and next steps

### Requirement 10

**User Story:** As a researcher, I want a Python environment definition, so that I can reproduce the research environment.

#### Acceptance Criteria

1. THE Research_Project SHALL contain an environment.yaml file for Conda
2. THE environment.yaml SHALL specify Python version, PyTorch, and core ML libraries
3. THE environment.yaml SHALL include pip dependencies for transformers, datasets, peft, wandb, and huggingface-hub
4. THE environment.yaml SHALL use conda-forge, pytorch, and nvidia channels

### Requirement 11

**User Story:** As a researcher, I want appropriate files excluded from Git, so that secrets and large artifacts are not accidentally committed.

#### Acceptance Criteria

1. THE Research_Project SHALL contain a .gitignore file at the repository root
2. THE .gitignore SHALL exclude outputs/ directory contents
3. THE .gitignore SHALL exclude experiment run logs (*.out, *.err files in runs/*/logs/)
4. THE .gitignore SHALL exclude experiment wandb/ directories
5. THE .gitignore SHALL exclude .env files and *.token files
6. THE .gitignore SHALL exclude Python cache directories (__pycache__/, *.pyc)
7. THE .gitignore SHALL exclude Jupyter notebook checkpoints
8. THE .gitignore SHALL exclude editor-specific files (.vscode/, .idea/)
9. THE .gitignore SHALL preserve directory structure with .gitkeep files

### Requirement 12

**User Story:** As a researcher, I want placeholder directories for standard project components, so that I know where to add code and data.

#### Acceptance Criteria

1. THE Research_Project SHALL contain a src/ directory for source code
2. THE Research_Project SHALL contain a tests/ directory for test code
3. THE Research_Project SHALL contain a notebooks/ directory for Jupyter notebooks
4. THE Research_Project SHALL contain a data/ directory with a README.md explaining data organization
5. THE Research_Project SHALL contain an outputs/ directory with a .gitkeep file
6. THE Research_Project SHALL preserve empty directories using .gitkeep files

### Requirement 13

**User Story:** As a researcher, I want clear setup instructions, so that I can start using the template immediately.

#### Acceptance Criteria

1. THE README.md SHALL explain the template's purpose and target users
2. THE README.md SHALL provide step-by-step setup instructions
3. THE README.md SHALL explain how to configure project-plan.md
4. THE README.md SHALL explain the directory structure
5. THE README.md SHALL provide an example of requesting a simple experiment from Codex
6. THE README.md SHALL link to relevant Codex documentation
7. THE README.md SHALL explain the relationship between AGENTS.md, skills, and templates

### Requirement 14

**User Story:** As a researcher working with specialist subagents, I want clear role definitions, so that Codex delegates tasks appropriately.

#### Acceptance Criteria

1. THE Research_Project SHALL contain an agent-descriptions/ directory
2. THE Research_Project SHALL include research-journal-git.md describing the research journal and Git specialist
3. THE Research_Project SHALL include wandb-analyst.md describing the W&B analysis specialist
4. THE Research_Project SHALL include huggingface-managing-specialist.md describing the Hub management specialist
5. THE Research_Project SHALL include visualization-specialist.md describing the visualization specialist
6. THE Research_Project SHALL include slurm-managing-specialist.md describing the Slurm debugging specialist
7. WHEN an agent description is defined, THE description SHALL specify mission, modes, allowed actions, and prohibited actions

### Requirement 15

**User Story:** As a template maintainer, I want version tracking, so that users know which template version they're using.

#### Acceptance Criteria

1. THE Template_Repository SHALL include a VERSION file or version field in a metadata file
2. THE version SHALL follow semantic versioning (MAJOR.MINOR.PATCH)
3. THE initial Phase 1 release SHALL use version 0.1.0
4. THE README.md SHALL document the current version and phase completion status
