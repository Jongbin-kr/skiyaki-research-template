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
   - Run GPU jobs in SSH environments through Slurm (`submit_slurm.py`), never on the login node
   - Run CPU-heavy jobs in SSH environments through Slurm; only short, light CPU work may run locally (`run_local.py`)
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
   - Required run comparisons are verified (W&B tracking via `track_wandb.py`, or local/user-provided evidence)
   - Required checkpoint publication is verified by revision (Hugging Face Hub via `publish_hf.py`); an unverified required upload blocks completion
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

Delegate only a bounded task that benefits from specialist expertise. Use these canonical routing names and preserved descriptions:

| Routing name | Trigger | Preserved description | Scope |
|---|---|---|---|
| Research Journal & Git | Prior-work synthesis or experiment finalization and Git proposal | [`agent-descriptions/research-journal-git.md`](agent-descriptions/research-journal-git.md) | Local repository evidence and documentation; commits remain approval-gated |
| W&B Analyst | Specialist comparison of training runs | [`agent-descriptions/wandb-analyst.md`](agent-descriptions/wandb-analyst.md) | W&B run metrics and local or user-provided exports |
| Hugging Face Curator | Model-card or Hub artifact curation | [`agent-descriptions/huggingface-managing-specialist.md`](agent-descriptions/huggingface-managing-specialist.md) | Canonical alias for the preserved filename; Hub mutations remain approval-gated |
| Visualization Specialist | Research figures from available results | [`agent-descriptions/visualization-specialist.md`](agent-descriptions/visualization-specialist.md) | Local results and exports |
| Slurm Debugger | Diagnosis of a Slurm failure | [`agent-descriptions/slurm-managing-specialist.md`](agent-descriptions/slurm-managing-specialist.md) | Canonical alias for the preserved filename; diagnosis of job failures, with mutating remote actions approval-gated |

Keep unmatched work in the Main Agent. For a match, select the narrowest specialist able to complete the task and load only its description immediately before delegation; never bulk-load all descriptions. If multiple specialists are needed, split the work into separate bounded delegations and repeat selection and selective loading for each.

Each delegation packet must state:

- **Objective:** one verifiable outcome.
- **Scope:** permitted actions and excluded adjacent work.
- **Inputs:** relevant paths and evidence.
- **Expected output:** the required bounded result.
- **Constraints:** applicable approval gates. Delegation never bypasses explicit user approval for job execution, material configuration changes, Git commits, artifact uploads, or destructive remote actions; work blocked on a missing approval or unset configuration (e.g. `wandb.entity`, `huggingface.namespace`) must say so and return a non-executing next step.
