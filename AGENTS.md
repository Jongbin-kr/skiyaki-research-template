# AI/ML Research Workflow

## Core Principles

This template provides a structured workflow for AI/ML research experiments with Codex assistance. The workflow emphasizes reproducibility, proper tracking, and systematic documentation of research findings.

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
