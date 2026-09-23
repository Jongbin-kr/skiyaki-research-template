# Design Document

## Introduction

This document describes the design for Phase 1 of the AI/ML Research Workspace GitHub Template. The template provides a complete research project skeleton with integrated Codex agent definitions, skills, and structured directories for experiments, enabling AI-assisted ML research workflows.

The design emphasizes simplicity, clarity, and immediate usability while preparing for future phases that will add SSH, Slurm, W&B, and Hugging Face integration.

## Architecture Overview

The template follows a layered architecture:

```
┌─────────────────────────────────────────┐
│         GitHub Template                  │
│  (User clicks "Use this template")       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│      Research Project Instance           │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Codex Integration Layer          │ │
│  │  (AGENTS.md, skills/, agent-desc/) │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Configuration Layer              │ │
│  │  (project-plan.md, environment)    │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Experiment Structure Layer       │ │
│  │  (experiments/, templates/)        │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Project Code Layer               │ │
│  │  (src/, tests/, notebooks/)        │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Component Design

### 1. Repository Root Structure

```
ai-ml-research-template/
├── AGENTS.md                    # Main agent rules
├── README.md                    # Template documentation
├── LICENSE                      # MIT or Apache 2.0
├── VERSION                      # 0.1.0
├── .gitignore                   # Git exclusions
├── environment.yaml             # Conda environment
├── project-plan.md              # Project configuration
├── project-log.md               # Research progress log
│
├── .agents/
│   └── skills/                  # Reusable workflows
│
├── agent-descriptions/          # Subagent role definitions
├── templates/                   # File templates
├── experiments/                 # Experiment storage
├── outputs/                     # Training outputs
├── data/                        # Dataset storage
├── notebooks/                   # Jupyter notebooks
├── src/                         # Source code
└── tests/                       # Test code
```

### 2. AGENTS.md Structure

The root AGENTS.md file defines core rules that Codex applies automatically:

```markdown
# AI/ML Research Workflow

## Core Principles

[Brief introduction to the research workflow]

## Workflow Rules

1. **Prior Research Discovery**: Before planning experiments, inspect:
   - project-log.md for project-level conclusions
   - experiments/*/journal.md for past findings
   - experiments/*/results.yaml for comparable baselines
   - Git history for related changes

2. **Research Grill**: Use the `grill-me` skill when:
   - Research objectives are unclear
   - Baseline comparisons are undefined
   - Success criteria are not established
   - Important experimental parameters are unspecified

3. **Stable Configuration**: Do not re-ask for:
   - W&B entity and project (in project-plan.md)
   - Hugging Face namespace (in project-plan.md)
   - SSH host and remote paths (in project-plan.md)
   - Slurm partition and account (in project-plan.md)
   - Default resource limits (in project-plan.md)

4. **Execution Requirements**:
   - Store reproducible settings in YAML (jobs/*.yaml)
   - Require Slurm for GPU jobs in SSH environments
   - Require Slurm for CPU-heavy jobs in SSH environments
   - Track every execution attempt as a Run

5. **Approval Gates**:
   - Require explicit user approval before job execution
   - Require approval after material experiment changes
   - Require approval before creating Git commits

6. **Version Control**:
   - Do not commit secrets, tokens, or credentials
   - Do not commit model checkpoints
   - Do not commit W&B cache directories
   - Do not commit raw Slurm logs (*.out, *.err)
   - Commit experiment plans, configurations, and results

7. **Completion Criteria**: An experiment is complete when:
   - Required training runs finish successfully
   - Evaluation completes with metric calculations
   - Success criteria are assessed
   - W&B runs are compared and verified
   - Required checkpoints are uploaded to Hugging Face Hub
   - results.yaml is written
   - history.md is updated
   - journal.md contains final conclusions
   - project-log.md reflects project-level outcomes
   - Git commit candidate is proposed

## Skills

The following skills implement standard research procedures:

- `grill-me`: Clarify experimental decisions through targeted questions
- `discover-prior-research`: Search past experiments and project history
- `plan-ml-experiment`: Create experiment plans and job configurations
- `train-llm`: Execute training jobs with proper tracking
- `evaluate-llm`: Run evaluation and compare results
- `finalize-experiment`: Complete experiment documentation and propose commits

See `.agents/skills/*/SKILL.md` for detailed workflow definitions.

## Subagents

For complex tasks, delegate to specialist subagents:

- Research Journal & Git: Discovery and finalization modes
- W&B Analyst: Training analysis and run comparison
- Hugging Face Curator: Model card and repository management
- Visualization Specialist: Research presentation graphics
- Slurm Debugger: Cluster-specific troubleshooting

Load agent descriptions from `agent-descriptions/` only when delegating.
```

**Design Rationale**: 
- Concise format ensures Codex reads and applies rules consistently
- Skills are referenced but not fully documented here (kept in separate files)
- Clear separation between what to always enforce vs. what to delegate
- Explicit completion criteria prevent premature success claims

### 3. Skills Structure

Each skill follows OpenAI's recommended structure:

```
.agents/skills/<skill-name>/
├── SKILL.md              # Workflow definition
├── references/           # Supporting documentation (optional)
└── scripts/              # Helper scripts (optional)
```

#### 3.1 grill-me Skill

**Purpose**: Ask targeted questions to resolve experimental ambiguities

**SKILL.md Structure**:

```markdown
# Grill Me Skill

## Purpose

Clarify experimental decisions through focused questioning before creating detailed plans.

## When to Use

- User request lacks clear research objective
- Baseline for comparison is undefined
- Success criteria are not specified
- Important hyperparameters are unspecified
- Ablation scope is ambiguous

## When NOT to Use

- Information is already in project-plan.md
- Information is in recent experiment plans
- Question is about implementation details (defer to planning phase)

## Procedure

1. **Identify Gaps**:
   - Check project-plan.md for stable configuration
   - Review recent experiments for similar work
   - List unknowns that affect experiment design

2. **Prioritize Questions**:
   - Focus on research objective and hypothesis
   - Then baseline and primary metric
   - Then success criteria
   - Then experimental parameters
   - Ask one question at a time

3. **Handle Responses**:
   - If answer is vague, ask for specifics
   - If answer is "I don't know", suggest reasonable defaults
   - If answer conflicts with past experiments, clarify intent
   - If answer is clear, move to next question

4. **Completion**:
   - Stop when research objective, baseline, metric, and success criteria are clear
   - Document resolved decisions for plan creation
   - Return summary to Main Agent

## Output

- Resolved research objective
- Baseline for comparison
- Primary and secondary metrics
- Success criteria
- Key experimental parameters
- Documented assumptions and defaults
```

#### 3.2 discover-prior-research Skill

**SKILL.md Structure**:

```markdown
# Discover Prior Research Skill

## Purpose

Search project history to find related experiments, baselines, and past findings.

## When to Use

Before creating any new experiment plan.

## Procedure

1. **Read Project Configuration**:
   - Load project-plan.md for research objectives and scope
   - Note project-level constraints and policies

2. **Search Project Log**:
   - Search project-log.md for keywords related to current request
   - Identify relevant conclusions and links to past experiments

3. **Search Experiments**:
   - List experiments/ subdirectories
   - For each experiment, check:
     - plan.md for similarity to current request
     - results.yaml for comparable metrics
     - journal.md for relevant findings

4. **Search Git History**:
   - Check recent commits for related changes
   - Identify if similar work was attempted and reverted

5. **Extract Baselines**:
   - Identify reusable job configurations
   - Collect baseline metrics for comparison
   - Note successful and failed approaches

6. **Duplication Check**:
   - Determine if current request duplicates a past experiment
   - If duplicate, suggest reviewing existing results instead

## Output

- List of related experiments with links
- Relevant findings from project-log.md and journals
- Reusable baseline configurations
- Duplication assessment with recommendation
```

#### 3.3 plan-ml-experiment Skill

**SKILL.md Structure**:

```markdown
# Plan ML Experiment Skill

## Purpose

Create detailed experiment plans and job configurations after research questions are clarified.

## Prerequisites

- Research objective is clear (from grill-me or user request)
- Prior research has been reviewed (from discover-prior-research)
- Project-plan.md contains stable configuration

## Procedure

1. **Create Experiment Directory**:
   - Generate experiment ID from research objective (kebab-case)
   - Create experiments/<experiment-id>/ structure
   - Create subdirectories: jobs/, runs/, figures/

2. **Write Plan Document**:
   - Use templates/experiment-plan.md as base
   - Fill YAML frontmatter:
     - experiment_id
     - status: "awaiting_approval"
     - primary_metric with direction
     - success_criteria
     - jobs: list of job files
     - approval: pending
   - Write markdown body:
     - Research objective and hypothesis
     - Baseline description
     - Design rationale
     - Agent-determined defaults with justification
     - Risks and limitations

3. **Create Job Configurations**:
   - For training: use templates/train-job.yaml
   - For evaluation: use templates/evaluate-job.yaml
   - Fill required fields:
     - job_id, type, entrypoint
     - parameters (model, dataset, hyperparameters)
     - matrix for ablations
     - resources (backend, GPUs, memory, time)
     - wandb configuration
     - huggingface push policy

4. **Estimate Resources**:
   - Calculate expected GPU hours
   - Check against project quotas in project-plan.md
   - Note if Slurm is required (GPU or CPU-heavy)

5. **Generate Approval Summary**:
   - List agent's recommendations
   - List agent-determined defaults with rationale
   - Summarize objective, metric, success criteria
   - List expected resources and execution time
   - List W&B group and HF destination
   - Provide paths to detailed plan and job files

## Output

- experiments/<experiment-id>/plan.md
- experiments/<experiment-id>/jobs/train.yaml
- experiments/<experiment-id>/jobs/evaluate.yaml
- Approval summary for user
```

**references/ Content**:
- Example experiment plans
- Common ablation patterns
- Resource estimation guidelines

#### 3.4 train-llm Skill

**SKILL.md Structure**:

```markdown
# Train LLM Skill

## Purpose

Execute training jobs with proper environment activation, tracking, and logging.

## Prerequisites

- Experiment plan is approved
- Job YAML exists and is valid
- Project environment is configured (environment.yaml or equivalent)

## Procedure

1. **Preflight Checks**:
   - Verify approval.status == "approved" in plan.md
   - Verify experiment-id and job-id are valid
   - Check entrypoint file exists
   - Check project environment exists
   - Check W&B and HF configurations in project-plan.md
   - Check Slurm requirements (GPU or CPU-heavy)
   - Check resource quotas and availability

2. **Prepare Run**:
   - Generate run ID: <job-id>__<timestamp>
   - Create runs/<run-id>/ directory
   - Create runs/<run-id>/logs/ directory
   - Copy job YAML to runs/<run-id>/resolved-job.yaml
   - Create runs/<run-id>/run.yaml with initial state

3. **Execution** (Phase 1: Local Only):
   - Activate project environment (conda/uv/venv)
   - Construct command from job entrypoint and parameters
   - Set up W&B environment variables (if enabled)
   - Set up HF environment variables for push policy
   - Execute command with stdout/stderr capture
   - Monitor execution

4. **Track Execution**:
   - Update run.yaml with status changes
   - Record start and end timestamps
   - Record exit code and status (succeeded/failed)
   - Save logs to runs/<run-id>/logs/

5. **Update History**:
   - Append execution record to history.md
   - Include run ID, job ID, status, and timestamp
   - Include W&B run URL (if available)

## Output

- runs/<run-id>/run.yaml with execution status
- runs/<run-id>/resolved-job.yaml with exact configuration
- runs/<run-id>/logs/ with execution logs
- Updated history.md entry

## Phase 1 Limitations

- SSH execution not implemented (requires Phase 6)
- Slurm submission not implemented (requires Phase 6)
- Local execution only suitable for smoke tests
```

#### 3.5 evaluate-llm Skill

**SKILL.md Structure**:

```markdown
# Evaluate LLM Skill

## Purpose

Run evaluation jobs, calculate metrics, and compare results against baselines.

## Prerequisites

- Training run completed successfully
- Evaluation job YAML exists
- Primary metric is defined in plan.md

## Procedure

1. **Check Training Completion**:
   - Verify required training runs have status "succeeded"
   - Identify best checkpoint based on validation metric
   - Verify checkpoint exists locally or on HF Hub

2. **Prepare Evaluation**:
   - Load evaluation job configuration
   - Verify evaluation dataset and split
   - Create evaluation run ID: <eval-job-id>__<timestamp>
   - Create runs/<eval-run-id>/ directory

3. **Execute Evaluation**:
   - Activate project environment
   - Construct evaluation command
   - Execute with proper checkpoint reference
   - Capture metrics output

4. **Calculate Metrics**:
   - Extract primary metric value
   - Extract secondary metrics (if defined)
   - Compare against baseline (from plan.md or prior experiments)
   - Calculate improvement percentage

5. **Compare W&B Runs** (Phase 1: Manual):
   - List W&B run URLs from training runs
   - Provide comparison instructions to user
   - Document comparison results

6. **Assess Success Criteria**:
   - Apply success criteria from plan.md
   - Determine if experiment succeeded or failed
   - Document assessment rationale

7. **Draft Results**:
   - Use templates/results.yaml as base
   - Fill best run reference
   - Fill primary and secondary metrics
   - Fill baseline comparison
   - Fill success assessment
   - Note any caveats or limitations

## Output

- runs/<eval-run-id>/run.yaml with evaluation status
- Drafted results.yaml (not yet committed)
- Updated history.md with evaluation entry
- Success/failure assessment with rationale
```

#### 3.6 finalize-experiment Skill

**SKILL.md Structure**:

```markdown
# Finalize Experiment Skill

## Purpose

Verify experiment completeness, update documentation, and propose Git commit.

## Prerequisites

- Training runs completed
- Evaluation completed
- Results drafted

## Procedure

1. **Verify Completeness**:
   - Check all required runs have succeeded or explicit failure explanation exists
   - Check results.yaml exists and references actual runs
   - Check primary metric is recorded
   - Check success criteria assessment is documented
   - Check W&B run URLs are recorded (for Phase 7+)
   - Check HF artifact uploads are recorded (for Phase 8+)

2. **Update Documentation**:
   - Review and finalize results.yaml
   - Append final entry to history.md with:
     - Completion timestamp
     - Best run reference
     - Final metric values
     - Success determination
   - Write journal.md entry with:
     - Hypothesis assessment (supported/refuted/unclear)
     - Key findings and insights
     - Unexpected results
     - Limitations and caveats
     - Recommended next experiments

3. **Update Project Log**:
   - Add entry to project-log.md with:
     - Date and experiment ID
     - One-line conclusion
     - Link to experiment directory
     - Key metric values
     - Next steps

4. **Review Git Changes**:
   - List all modified and new files
   - Verify no secrets, tokens, or credentials included
   - Verify no checkpoints or large artifacts included
   - Verify no raw logs included (history.md has summaries)

5. **Propose Commit**:
   - Generate commit message following format:
     - First line: "Complete <experiment-id>: <one-line summary>"
     - Body: bulleted list of key changes and findings
   - Present file list and commit message to user
   - Request approval before committing

## Output

- Finalized results.yaml
- Completed history.md
- Written journal.md
- Updated project-log.md
- Git commit proposal (awaiting user approval)

## Prohibited Actions

- Do not create commits without explicit user approval
- Do not claim success without verifying artifact references
- Do not proceed if required documentation is missing
```

### 4. Agent Descriptions Structure

Each agent description follows a consistent format:

```markdown
# <Agent Name>

## Mission

[One-sentence description of agent's purpose]

## Modes

[If applicable, list different operating modes]

## Allowed Actions

- [List of permitted operations]

## Prohibited Actions

- [List of forbidden operations]

## Required Output

[What the agent must return to Main Agent]
```

#### Example: research-journal-git.md

```markdown
# Research Journal & Git Agent

## Mission

Find relevant prior work before planning experiments and consolidate verified evidence after experiments complete.

## Modes

### Discovery Mode

Invoked before experiment planning to:
- Search project-log.md for related work
- Search experiments/ for similar studies
- Extract reusable baselines and configurations
- Assess duplication risk

### Finalize Mode

Invoked after evaluation to:
- Verify experiment completeness
- Draft and update research documentation
- Review Git changes
- Propose commits with appropriate messages

## Allowed Actions

- Read all project files and Git history
- Analyze experimental results
- Draft or update research records (results.yaml, history.md, journal.md, project-log.md)
- Propose Git commits with file lists and messages

## Prohibited Actions

- Do not submit jobs or execute training
- Do not push checkpoints or large artifacts
- Do not create commits without explicit user approval
- Do not claim experiment success without verifying artifact references exist

## Required Output

### Discovery Mode
- List of related experiments with links
- Relevant past findings
- Reusable configurations
- Duplication assessment

### Finalize Mode
- Completeness verification
- Updated documentation files
- Git commit proposal with message
- Remaining risks or missing artifacts
```

### 5. Configuration Files

#### 5.1 environment.yaml

```yaml
# AI/ML Research Project Environment
# 
# This file defines the Conda environment for the research project.
# Modify channels and dependencies based on your specific needs.
#
# To create the environment:
#   conda env create -f environment.yaml
#
# To activate:
#   conda activate <project-name>
#
# To update:
#   conda env update -f environment.yaml --prune

name: my-research-project

channels:
  - pytorch
  - nvidia
  - conda-forge

dependencies:
  - python=3.11
  - pytorch::pytorch
  - pytorch::torchvision
  - pytorch::torchaudio
  - pip
  - pip:
      # Core ML libraries
      - transformers>=4.36.0
      - datasets>=2.16.0
      - accelerate>=0.25.0
      - peft>=0.7.0
      
      # Experiment tracking
      - wandb>=0.16.0
      
      # Model Hub
      - huggingface-hub>=0.20.0
      
      # Development tools
      - jupyter
      - ipython
      - pytest
      
      # Optional: Add your project-specific dependencies here
      # - your-package>=1.0.0
```

**Design Rationale**:
- Conda for base environment management (GPU drivers, CUDA)
- pip for Python packages that update frequently
- Version pins on critical libraries to ensure reproducibility
- Comments guide users on customization

#### 5.2 project-plan.md

```markdown
---
schema_version: 1
project_id: my-research-project

# Environment configuration
environment:
  manager: miniconda          # Options: miniconda, uv, venv
  manifest: environment.yaml  # Path to environment file

# Execution configuration
execution:
  default_target: ssh         # Options: local, ssh
  ssh_host: research-cluster  # SSH config alias (Phase 6+)
  remote_project_root: /workspace/my-research-project  # Remote path (Phase 6+)
  direct_cpu_max_minutes: 10  # Max time for direct CPU execution
  require_slurm_for_gpu: true
  require_slurm_for_cpu_heavy: true

# Slurm configuration (Phase 6+)
slurm:
  partition: gpu
  account: my-account
  qos: normal
  max_gpus_per_job: 4
  max_concurrent_jobs: 8

# Weights & Biases configuration (Phase 7+)
wandb:
  entity: my-lab
  project: my-research-project
  mode: online                 # Options: online, offline
  keep_local_data: true

# Hugging Face Hub configuration (Phase 8+)
huggingface:
  namespace: my-lab
  private: false               # Default visibility for uploads
  push_policy: final_and_milestone  # Options: never, final_only, final_and_milestone, every_save
---

# Project Plan

## Research Objective

[Describe the overall research goal of this project]

## Research Questions

1. [Primary research question]
2. [Secondary research question]
3. [Additional questions...]

## Scope

### In Scope
- [What this project will investigate]
- [What models/architectures will be used]
- [What datasets will be used]

### Out of Scope
- [What this project will NOT investigate]
- [What is explicitly excluded]

## Baseline Approach

[Describe the baseline model/method that new experiments will be compared against]

## Evaluation Principles

### Primary Metrics
- [Main metric for success, e.g., "Accuracy on test set"]
- [Why this metric was chosen]

### Secondary Metrics
- [Additional metrics to track]
- [When they matter]

## Artifact Policy

### Checkpoint Management
- [When to save checkpoints]
- [Which checkpoints to upload to Hub]

### Data Privacy
- [Any data restrictions]
- [What can be shared publicly]

### Model Release
- [Conditions for releasing models]
- [Default visibility (private/public)]

## Approval Policy

### Experiments Requiring Review
- [Types of experiments that need extra scrutiny]
- [Budget thresholds for approval]

### Auto-Approved Experiments
- [Small-scale experiments that can proceed automatically]

## Notes

[Any additional project-specific guidelines or context]
```

**Design Rationale**:
- YAML frontmatter for machine-readable configuration
- Markdown body for human-readable policies
- Clear separation of what is stable (infrastructure) vs. what evolves (research questions)
- Placeholder values guide users on what to fill in
- Phase indicators show which fields are used in which implementation phase

#### 5.3 project-log.md

```markdown
# Project Log

This file records significant project-level events, conclusions, and decisions in chronological order. Each experiment should add an entry here upon completion.

## Format Guidelines

- Use reverse chronological order (newest first)
- Include date, experiment ID, one-line conclusion
- Link to experiment directory
- List key metrics
- Note next steps

---

## [YYYY-MM-DD] — Initial Project Setup

- Created project from ai-ml-research-template
- Configured environment.yaml with PyTorch and Transformers
- Set up project-plan.md with research objectives
- Ready to begin first experiment

---

## Example Entry (Remove This)

## 2025-01-15 — LoRA Rank Ablation Completed

- **Conclusion**: LoRA rank 16 provides best accuracy/efficiency tradeoff
- **Best Run**: `train-r16__20250115T142530`
- **Experiment**: `experiments/lora-rank-ablation/`
- **Key Metrics**: 
  - Accuracy: 0.874 (+2.1% over baseline)
  - Memory: 8.2GB
  - Training time: 4.5 hours
- **Next Steps**: Investigate learning rate ablation with rank 16

---
```

### 6. Template Files

All template files are stored in `templates/` directory:

#### 6.1 experiment-plan.md

```markdown
---
schema_version: 1
experiment_id: <experiment-id>
status: draft  # Options: draft, grilling, planned, awaiting_approval, approved, running, evaluating, finalizing, completed, failed, cancelled, blocked

primary_metric:
  name: <metric-name>
  direction: maximize  # Options: maximize, minimize

success_criteria:
  minimum_improvement: 0.02  # Minimum improvement over baseline
  # Add other criteria as needed

jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml

approval:
  status: pending  # Options: pending, approved, rejected
  approved_by: null
  approved_at: null
  approved_commit: null
---

# <Experiment Title>

## Purpose

[Describe the research question this experiment addresses]

## Hypothesis

[State your hypothesis about what you expect to find]

## Baseline

[Describe the baseline approach for comparison]

- Model: [baseline model]
- Dataset: [baseline dataset and split]
- Metrics: [baseline metric values]
- Source: [where baseline comes from - prior experiment, paper, etc.]

## Design

[Explain the experimental design]

### Variables

[What you're changing/ablating]

### Controls

[What you're keeping constant]

### Rationale

[Why this design will test your hypothesis]

## Agent-Determined Defaults

[List any parameters the agent chose and why]

- [Parameter]: [value] - [rationale]

## Risks and Limitations

[What could go wrong or limit conclusions]

- [Risk 1]
- [Risk 2]

## Expected Outcomes

[What results would support or refute your hypothesis]

### If Hypothesis Supported
[What you'd conclude and do next]

### If Hypothesis Refuted
[What you'd conclude and do next]
```

#### 6.2 train-job.yaml

```yaml
# Training Job Configuration
# 
# This file defines reproducible training settings.
# It will be copied to runs/<run-id>/resolved-job.yaml before execution.

job_id: train-<experiment-id>
type: train

# Execution
entrypoint: src/train.py
config_style: argument  # Options: argument, hydra, json, yaml

# Hyperparameter matrix (for ablations)
matrix:
  # Example: lora_rank: [4, 8, 16, 32]
  # Leave empty for single-run jobs
  {}

# Parameters passed to entrypoint
parameters:
  model_name: <model-name>
  dataset_name: <dataset-name>
  dataset_split: train
  learning_rate: 2.0e-4
  num_epochs: 3
  batch_size: 8
  gradient_accumulation_steps: 4
  seed: 42
  
  # Add model-specific parameters
  # lora_r: 16
  # lora_alpha: 32

# Resource requirements
resources:
  backend: slurm  # Options: local, slurm (Phase 1: local only)
  gpus: 1
  cpus: 8
  memory_gb: 32
  time: "08:00:00"  # HH:MM:SS format

# Weights & Biases tracking (Phase 7+)
wandb:
  enabled: true
  group: <experiment-id>
  tags:
    - <experiment-tag>

# Hugging Face Hub (Phase 8+)
huggingface:
  push: milestone  # Options: never, final_only, milestone, every_save
  repo: null  # Auto-determined from project-plan.md if null
```

#### 6.3 evaluate-job.yaml

```yaml
# Evaluation Job Configuration

job_id: eval-<experiment-id>
type: evaluate

# Execution
entrypoint: src/evaluate.py
config_style: argument

# Parameters
parameters:
  checkpoint: null  # Filled at runtime from best training run
  dataset_name: <dataset-name>
  dataset_split: test
  batch_size: 16
  
  # Metrics to compute
  metrics:
    - accuracy
    - f1
    # Add others as needed

# Resources (evaluation typically needs less than training)
resources:
  backend: slurm  # Options: local, slurm
  gpus: 1
  cpus: 4
  memory_gb: 16
  time: "02:00:00"

# Tracking
wandb:
  enabled: true
  group: <experiment-id>
  tags:
    - evaluation
```

#### 6.4 run.yaml

```yaml
# Run Execution Record
# 
# This file tracks a single execution attempt of a job.

run_id: <job-id>__<timestamp>
experiment_id: <experiment-id>
job_id: <job-id>
job_file: jobs/<job>.yaml

# Execution status
status: created  # Options: created, submitted, pending, running, succeeded, failed, cancelled, timed_out, preempted
started_at: null
completed_at: null
exit_code: null

# Slurm tracking (Phase 6+)
slurm:
  job_id: null
  array_task_id: null
  partition: null
  node: null

# W&B tracking (Phase 7+)
wandb:
  run_id: null
  url: null
  sync_status: null  # Options: synced, failed, disabled

# Resolved configuration
resolved_config: resolved-job.yaml

# Artifacts produced (Phase 8+)
artifacts:
  checkpoints: []
  logs: []
  figures: []
```

#### 6.5 results.yaml

```yaml
# Experiment Results
# 
# This file records the final outcomes of the experiment.

experiment_id: <experiment-id>
completed_at: <timestamp>

# Best performing run
best_run:
  run_id: <run-id>
  job_id: <job-id>
  checkpoint: <checkpoint-path-or-hub-url>

# Primary metric
primary_metric:
  name: <metric-name>
  value: <value>
  baseline_value: <baseline-value>
  improvement: <percentage>

# Secondary metrics
secondary_metrics:
  - name: <metric-name>
    value: <value>
  # Add more as needed

# Success assessment
success:
  criteria_met: <true/false>
  rationale: <explanation>

# All training runs
runs:
  - run_id: <run-id>
    status: <status>
    primary_metric_value: <value>
  # List all runs

# Artifacts
artifacts:
  wandb_group: <url>
  hub_repos:
    - <repo/revision>

# Caveats
notes: |
  <Any important caveats, limitations, or notes>
```

#### 6.6 history.md

```markdown
# Experiment History

This file records factual execution events in chronological order.

## Format Guidelines

- Reverse chronological (newest first)
- Factual, not interpretive (interpretation goes in journal.md)
- Include timestamps, run IDs, status, and links

---

## [YYYY-MM-DD HH:MM] — Event Description

[Factual description of what happened]

- Run ID: <run-id>
- Status: <status>
- W&B: <url>
- Notes: <any relevant facts>

---

## Example Entries (Remove These)

## 2025-01-15 14:30 — Experiment Finalized

- Completed journal entry with findings
- Updated project-log.md with conclusion
- Proposed Git commit: "Complete lora-rank-ablation: rank 16 optimal"

## 2025-01-15 12:00 — Evaluation Completed

- Run ID: eval-r16__20250115T120000
- Status: succeeded
- Primary metric: accuracy = 0.874
- Baseline: accuracy = 0.853
- Improvement: +2.1%
- Success criteria met: improvement > 2%

## 2025-01-15 08:00 — Training Run Succeeded

- Run ID: train-r16__20250115T080000
- Status: succeeded
- Duration: 4.5 hours
- W&B: https://wandb.ai/my-lab/my-project/runs/abc123
- Checkpoint saved: outputs/lora-rank-ablation/train-r16__20250115T080000/checkpoint-final

## 2025-01-15 03:30 — Training Run Started

- Run ID: train-r16__20250115T080000
- Job: jobs/train.yaml with lora_rank=16
- Resources: 1 GPU, 8 CPUs, 32GB RAM
- Slurm Job ID: 123456 (Phase 6+)

## 2025-01-14 16:00 — Experiment Approved

- User approved experiment plan
- Approval recorded in plan.md
- Ready to start training

## 2025-01-14 15:00 — Plan Created

- Created plan.md and job configurations
- Defined LoRA rank ablation: [4, 8, 16, 32]
- Estimated resources: 4 GPU jobs × 8 hours each
- Awaiting user approval

---
```

#### 6.7 journal.md

```markdown
# Experiment Journal

This file records interpretations, insights, and conclusions.

## Format Guidelines

- Focus on "why" and "what does this mean", not just "what happened"
- Compare results to hypotheses
- Note unexpected findings
- Suggest follow-up experiments
- Document limitations

---

## Final Conclusions

[Written after experiment completes]

### Hypothesis Assessment

[Was your hypothesis supported, refuted, or unclear?]

### Key Findings

[What did you learn?]

1. [Finding 1]
2. [Finding 2]

### Unexpected Results

[Anything surprising?]

### Limitations

[What conclusions can you NOT make?]

1. [Limitation 1]
2. [Limitation 2]

### Recommended Next Steps

[What should be investigated next?]

1. [Next experiment 1]
2. [Next experiment 2]

---

## Intermediate Observations

[Optional: notes during execution]

### [YYYY-MM-DD] — Observation

[Any interesting observations during training or evaluation]

---

## Example Entry (Remove This)

## Final Conclusions

### Hypothesis Assessment

**Hypothesis**: LoRA rank 16+ would saturate performance gains.

**Result**: Supported. Rank 16 achieved 87.4% accuracy. Rank 32 only improved to 87.5% (+0.1%), not worth the 2× memory cost.

### Key Findings

1. Rank 16 provides the best accuracy/efficiency tradeoff
2. Ranks below 8 significantly hurt performance (-3% accuracy)
3. Memory usage scales linearly with rank as expected
4. Training time increased less than expected (rank 32 only +15% vs rank 8)

### Unexpected Results

- Rank 4 was more effective than anticipated (only -1.5% vs baseline)
- Could be useful for extremely memory-constrained deployment

### Limitations

1. Only tested on one dataset (GLUE SST-2)
2. Only tested one base model (RoBERTa-base)
3. Did not test interaction with other hyperparameters (learning rate, etc.)
4. Did not measure inference latency

### Recommended Next Steps

1. **High Priority**: Learning rate ablation with rank 16
   - Hypothesis: Default LR may not be optimal for rank 16
   
2. **Medium Priority**: Generalization check across GLUE tasks
   - Verify rank 16 is optimal for other tasks
   
3. **Low Priority**: Inference latency benchmark
   - Measure actual deployment impact of different ranks

---
```

#### 6.8 artifacts.yaml

```yaml
# Experiment Artifacts
# 
# This file tracks all artifacts produced during the experiment.

experiment_id: <experiment-id>

artifacts:
  # Model checkpoints
  - type: model
    local_path: outputs/<experiment-id>/<run-id>/checkpoint-final
    hub_repo: null  # Phase 8+: <namespace>/<model-name>
    hub_revision: null  # Phase 8+: commit SHA
    upload_status: local  # Options: local, uploading, uploaded, failed
    size_mb: <size>
    created_at: <timestamp>
  
  # Figures and visualizations
  - type: figure
    local_path: experiments/<experiment-id>/figures/<figure-name>.png
    description: <description>
    created_at: <timestamp>
  
  # Evaluation results
  - type: metrics
    local_path: experiments/<experiment-id>/results.yaml
    description: Final evaluation metrics
    created_at: <timestamp>

# W&B artifacts (Phase 7+)
wandb:
  group_url: null
  run_urls: []

# Git commit tracking
git:
  commit_sha: null
  committed_at: null
  commit_message: null
```

### 7. .gitignore Design

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Jupyter
.ipynb_checkpoints/
*.ipynb_checkpoints

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local
*.token
credentials.json

# Conda
.conda/

# Outputs (large training artifacts)
outputs/**
!outputs/.gitkeep

# Experiment logs (raw Slurm logs not committed)
experiments/**/runs/**/logs/*.out
experiments/**/runs/**/logs/*.err
experiments/**/runs/**/wandb/

# Data (large datasets not committed)
data/**
!data/.gitkeep
!data/README.md

# Temporary files
*.tmp
.DS_Store
Thumbs.db
```

**Design Rationale**:
- Exclude all Python cache and build artifacts
- Exclude sensitive files (secrets, tokens)
- Exclude large files (outputs, logs, data)
- Use .gitkeep to preserve directory structure
- Allow explicit documentation (data/README.md)

### 8. README.md Design

The README.md provides comprehensive getting-started documentation:

**Structure**:
1. **Introduction**: What this template is and who it's for
2. **Quick Start**: 5-minute setup guide
3. **Project Structure**: Directory overview with explanations
4. **Configuration**: How to customize project-plan.md and environment.yaml
5. **Usage**: Example of requesting an experiment from Codex
6. **Concepts**: Explanation of Experiments, Jobs, Runs
7. **Skills**: Overview of available skills
8. **Subagents**: When to use specialists
9. **Phase Status**: What's implemented and what's coming
10. **Contributing**: How to improve the template
11. **License**: MIT/Apache 2.0

**Example Sections**:

```markdown
# AI/ML Research Workspace Template

> A GitHub template that combines AI/ML project structure with Codex Research Harness for AI-assisted experiment planning, execution, and tracking.

## What Is This?

This template provides everything you need to start an AI/ML research project with Codex integration:

- 📋 **Structured experiments**: Standard format for plans, jobs, runs, and results
- 🤖 **Codex skills**: Reusable workflows for planning, training, evaluation
- 📊 **Experiment tracking**: Organized history and journals for every experiment
- 🔧 **Infrastructure integration**: Ready for SSH, Slurm, W&B, Hugging Face (future phases)
- 📝 **Research log**: Project-level progress tracking

## Who Is This For?

AI/ML researchers who:
- Write their own training code (PyTorch, JAX, etc.)
- Use SSH and GPU clusters (Slurm)
- Want AI assistance with experiment planning and execution
- Need structured experiment tracking

## Quick Start

### 1. Create Your Project

Click "Use this template" on GitHub to create your research project.

### 2. Configure Environment

Edit `environment.yaml`:

```yaml
name: your-project-name  # Change this
# ... add your dependencies
```

Create the environment:

```bash
conda env create -f environment.yaml
conda activate your-project-name
```

### 3. Configure Project

Edit `project-plan.md`:

```yaml
---
project_id: your-project-name  # Change this
environment:
  manager: miniconda
  manifest: environment.yaml

# ... fill in your infrastructure details
---
```

### 4. Start Research

Open your project in Codex and say:

> "I want to compare LoRA ranks 8, 16, and 32 for fine-tuning RoBERTa on SST-2."

Codex will:
1. Search for related past experiments
2. Ask clarifying questions (metric, baseline, success criteria)
3. Create an experiment plan with job configurations
4. Request your approval
5. (Future phases: execute training, track results, propose commits)

## Project Structure

```
your-project/
├── AGENTS.md                 # Core rules Codex follows
├── project-plan.md           # Your infrastructure and policies
├── project-log.md            # Project-level research progress
│
├── .agents/skills/           # Reusable research workflows
│   ├── grill-me/            # Ask clarifying questions
│   ├── discover-prior-research/  # Find related work
│   ├── plan-ml-experiment/  # Create experiment plans
│   ├── train-llm/           # Execute training
│   ├── evaluate-llm/        # Run evaluation
│   └── finalize-experiment/ # Complete documentation
│
├── agent-descriptions/       # Subagent role definitions
├── templates/               # File templates for experiments
├── experiments/             # All experimental work
│   └── <experiment-id>/
│       ├── plan.md          # Research question and design
│       ├── jobs/            # Training/eval configurations
│       ├── runs/            # Execution attempts
│       ├── results.yaml     # Final outcomes
│       ├── history.md       # Factual timeline
│       ├── journal.md       # Interpretations and insights
│       └── figures/         # Visualizations
│
├── outputs/                 # Training outputs (not in Git)
├── src/                     # Your training/eval code
├── tests/                   # Your tests
├── notebooks/               # Jupyter notebooks
└── data/                    # Datasets (not in Git)
```

## Core Concepts

### Experiment
A single research question investigation with:
- **Plan**: Research objective, hypothesis, design
- **Jobs**: Reproducible training/evaluation configurations
- **Runs**: Individual execution attempts
- **Results**: Metrics and success assessment
- **History**: Factual execution timeline
- **Journal**: Interpretations and conclusions

### Job
A reproducible execution configuration (YAML):
- Entrypoint and parameters
- Resource requirements
- Matrix for ablations
- W&B and HF settings

### Run
A single execution attempt:
- Status tracking (created → running → succeeded/failed)
- Logs and outputs
- Links to W&B runs and checkpoints

## Available Skills

- **grill-me**: Clarifies experimental decisions through targeted questions
- **discover-prior-research**: Searches project history for related work
- **plan-ml-experiment**: Creates detailed experiment plans and job configs
- **train-llm**: Executes training with proper tracking
- **evaluate-llm**: Runs evaluation and compares results
- **finalize-experiment**: Completes documentation and proposes commits

See `.agents/skills/*/SKILL.md` for detailed workflows.

## Phase 1 Status

✅ **Implemented**:
- Complete directory structure
- Agent definitions and skills
- Experiment templates
- Documentation

🚧 **Future Phases**:
- Phase 6: SSH and Slurm execution
- Phase 7: W&B integration
- Phase 8: Hugging Face Hub integration
- Phase 9: Git automation

## License

MIT License - see LICENSE file for details
```

## Data Flow

### Experiment Creation Flow

```
User Request
    ↓
┌─────────────────────────┐
│  discover-prior-research │
│  - Search project-log    │
│  - Find related exps     │
│  - Extract baselines     │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│      grill-me            │
│  - Clarify objective     │
│  - Define metric         │
│  - Set success criteria  │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  plan-ml-experiment      │
│  - Create plan.md        │
│  - Generate job YAMLs    │
│  - Estimate resources    │
└─────────────────────────┘
    ↓
User Approval
    ↓
┌─────────────────────────┐
│      train-llm           │
│  - Create run            │
│  - Execute training      │
│  - Track status          │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│     evaluate-llm         │
│  - Load checkpoint       │
│  - Run evaluation        │
│  - Calculate metrics     │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  finalize-experiment     │
│  - Update docs           │
│  - Verify completeness   │
│  - Propose commit        │
└─────────────────────────┘
    ↓
User Approval → Git Commit
```

## Error Handling

### Missing Configuration

**Scenario**: User hasn't filled in project-plan.md

**Handling**:
- Skills check for required fields before execution
- Prompt user to complete configuration
- Provide examples of what to fill in

### Job Execution Failure

**Scenario**: Training run fails with OOM error

**Handling**:
- Record failure status in run.yaml
- Append failure entry to history.md
- Suggest adjustments (reduce batch size, enable gradient checkpointing)
- Allow retry with modified configuration

### Incomplete Experiment

**Scenario**: Finalize called before evaluation completes

**Handling**:
- Verify all required runs succeeded
- Verify results.yaml references actual artifacts
- Block commit proposal if verification fails
- List missing requirements for user

## Security Considerations

### Secrets Management

**Design**:
- Never commit .env, *.token, credentials.json
- .gitignore excludes common secret patterns
- project-plan.md warns against including tokens
- Skills check for secret patterns before proposing commits

### File Size Management

**Design**:
- outputs/ excluded from Git
- Checkpoint paths recorded but files not committed
- Raw Slurm logs excluded (summaries in history.md)
- .gitignore preserves structure with .gitkeep

## Correctness Properties

### Property 1: Configuration completeness before execution

**For any** training or evaluation job execution request, the system SHALL verify that project-plan.md contains required configuration fields (environment manager, execution target, resource limits) before proceeding with job creation.

**Validates: Requirements 4.3, 4.4, 4.5**

### Property 2: Experiment directory structure consistency

**For any** newly created experiment, the directory structure SHALL include plan.md, jobs/ subdirectory, runs/ subdirectory, and figures/ subdirectory as defined in templates.

**Validates: Requirements 6.5, 6.6**

### Property 3: Git exclusion of sensitive files

**For any** file path matching patterns defined in .gitignore (*.token, .env, outputs/**, *.out, *.err in run logs), the file SHALL NOT appear in Git commit proposals.

**Validates: Requirements 2.5, 11.2, 11.3, 11.4, 11.5**

### Property 4: Approval requirement before execution

**For any** job execution request, if plan.md shows approval.status != "approved", the system SHALL block execution and request user approval.

**Validates: Requirements 2.4**

### Property 5: Experiment completion verification

**For any** experiment marked as complete, the system SHALL verify that results.yaml, history.md, and journal.md exist and contain non-template content.

**Validates: Requirements 2.6, 9.5, 9.6, 9.7**

### Property 6: Run status tracking

**For any** job execution attempt, a run.yaml file SHALL be created with status "created" before execution starts, and status SHALL be updated to "succeeded", "failed", or other terminal state after execution completes.

**Validates: Requirements 8.2, 8.3**

### Property 7: Project log update on completion

**For any** experiment that reaches "completed" status, an entry SHALL be added to project-log.md with date, experiment ID, conclusion, and link to experiment directory.

**Validates: Requirements 5.3**

### Property 8: Job configuration reproducibility

**For any** run execution, the resolved-job.yaml SHALL be a copy of the original job YAML with all matrix variables expanded and all parameters explicitly specified.

**Validates: Requirements 7.3, 8.5**

### Property 9: Skill procedure adherence

**For any** skill invocation, the skill SHALL follow the procedure steps defined in its SKILL.md and SHALL produce all required outputs listed in the output section.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

### Property 10: Agent description boundary enforcement

**For any** subagent invocation, the Main_Agent SHALL verify that requested actions are in the agent's "Allowed Actions" list and SHALL NOT request actions in the "Prohibited Actions" list.

**Validates: Requirements 14.7**

### Property 11: Template file usage

**For any** newly created experiment plan, job configuration, or run record, the content SHALL include all sections defined in the corresponding template file from templates/ directory.

**Validates: Requirements 6.2, 6.3, 6.4, 7.1, 7.2, 8.1, 9.1, 9.2, 9.3, 9.4**

### Property 12: YAML frontmatter validity

**For any** file that uses YAML frontmatter (plan.md, project-plan.md), the frontmatter SHALL be valid YAML and SHALL contain all required fields defined in the corresponding template.

**Validates: Requirements 4.2, 6.3, 6.4**

## Implementation Notes

### Phase 1 Scope

Phase 1 focuses on **structure and documentation only**:

- Create all directories and template files
- Write all skill definitions
- Write all agent descriptions
- Write comprehensive README
- No actual SSH, Slurm, W&B, or HF integration
- Local execution only (suitable for smoke tests)

### Testing Strategy

Phase 1 success criteria:

1. **Template Creation**: User can click "Use this template" and get a working repository
2. **Codex Integration**: Codex reads and applies AGENTS.md rules
3. **Skill Discovery**: Codex can find and understand skill definitions
4. **Planning**: User can request an experiment and Codex produces plan.md and job YAMLs
5. **Approval Flow**: Codex requests approval before execution (even though Phase 1 doesn't execute)
6. **Documentation**: README clearly explains setup and usage

### Design Decisions

1. **Why YAML frontmatter?**
   - Machine-readable configuration
   - Human-readable markdown body
   - Single-file convenience
   - Git-friendly (text diffs)

2. **Why separate skills from AGENTS.md?**
   - Keeps AGENTS.md concise (Codex always reads it)
   - Skills are only loaded when needed
   - Easier to maintain and update individual workflows
   - Follows OpenAI's recommended pattern

3. **Why agent-descriptions/ separate from skills/?**
   - Skills are workflows Main Agent executes
   - Agent descriptions define other agents' capabilities
   - Different use cases: skills = "how to do X", descriptions = "what agent Y can do"

4. **Why both history.md and journal.md?**
   - history.md: factual timeline (what happened and when)
   - journal.md: interpretation (what it means and why)
   - Separation keeps facts from opinions
   - Both are useful for different purposes (debugging vs. research insights)

5. **Why project-log.md separate from experiments/?**
   - Project-level view of progress
   - Quick reference without diving into experiment details
   - Helps Main Agent avoid duplicating experiments
   - Builds institutional knowledge over time

## Future Extensions

### Phase 6+ Considerations

When SSH and Slurm are added:

- train-llm skill will generate Slurm batch scripts
- run.yaml will track Slurm job IDs
- Logs will follow naming convention: `YYYYMMDD-HHMMSS_jobid_jobname.out`
- Skills will check project-plan.md for Slurm configuration

### Phase 7+ Considerations

When W&B is added:

- Jobs will include W&B group and tags
- Runs will track W&B run URLs
- evaluate-llm will use W&B API for run comparison
- W&B Analyst subagent will be invoked for complex analysis

### Phase 8+ Considerations

When Hugging Face Hub is added:

- Checkpoints will be uploaded based on push_policy
- artifacts.yaml will track Hub repositories and revisions
- Hugging Face Curator will be invoked for complex model card creation

## Conclusion

This design provides a complete, self-contained GitHub template that:

1. **Immediately Usable**: No external Harness installation required
2. **Codex-Native**: Integrates naturally with Codex's agent system
3. **Research-Focused**: Structured around experiments, not arbitrary code
4. **Extensible**: Clear path for adding infrastructure integrations in future phases
5. **Self-Documenting**: Templates and examples guide users

The template transforms how researchers interact with Codex, turning natural language requests into structured, tracked, reproducible experiments.
