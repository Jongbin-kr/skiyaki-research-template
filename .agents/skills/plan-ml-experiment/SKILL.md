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
