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
│   ├── example-lora-rank-ablation/  # Example experiment (see below)
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

### Example Experiment

The template includes a complete example experiment at `experiments/example-lora-rank-ablation/` demonstrating:

- **Realistic research question**: Optimal LoRA rank for fine-tuning RoBERTa-base on SST-2
- **Complete documentation**: Plan, job configurations, run records, results, history, and journal
- **Best practices**: Hypothesis, baseline comparison, success criteria, detailed analysis
- **Real-world structure**: Shows what a finished experiment looks like

**Example files**:
- `plan.md`: Research objective, hypothesis, design rationale
- `jobs/train.yaml`: Training configuration with LoRA rank ablation matrix
- `jobs/evaluate.yaml`: Evaluation configuration
- `runs/train-r16__20250115T142530/`: Example run with logs and metadata
- `results.yaml`: Metrics, comparisons, recommendations
- `history.md`: Timeline of execution events
- `journal.md`: Detailed analysis and insights

This example is safe to delete when you start your own research, or keep it as a reference.

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

## Research Workflow Tools

### Skills

Skills are reusable research workflows that Codex uses automatically. Each skill is defined in `.agents/skills/<skill-name>/SKILL.md`.

#### grill-me
**Purpose**: Clarify experimental decisions through targeted questions

**When to use**:
- Research objective is unclear
- Baseline for comparison is undefined
- Success criteria are not specified
- Important hyperparameters are unspecified
- Ablation scope is ambiguous

**What it does**:
- Identifies gaps in experiment definition
- Asks one focused question at a time
- Suggests reasonable defaults when you're unsure
- Documents resolved decisions for planning

**Example**: If you request "train a model" without specifics, this skill will ask about your baseline, metrics, and success criteria before creating a plan.

See [`.agents/skills/grill-me/SKILL.md`](.agents/skills/grill-me/SKILL.md) for detailed workflow.

#### discover-prior-research
**Purpose**: Search project history to find related experiments and baselines

**When to use**:
- Before creating any new experiment plan
- To find comparable metrics for benchmarking
- To detect potential duplication of prior work
- To extract reusable baseline configurations

**What it does**:
- Searches `project-log.md` for related conclusions
- Examines past experiments for similar work
- Extracts baseline configurations and metrics
- Assesses whether your request duplicates past work
- Reviews Git history for related changes

**Example**: Before starting a new LoRA experiment, this skill finds your previous LoRA work and suggests reusing successful configurations.

See [`.agents/skills/discover-prior-research/SKILL.md`](.agents/skills/discover-prior-research/SKILL.md) for detailed workflow.

#### plan-ml-experiment
**Purpose**: Create detailed experiment plans and job configurations

**When to use**:
- After research questions are clarified (via grill-me)
- After prior research has been reviewed
- When you're ready to formalize an experiment design

**What it does**:
- Creates experiment directory structure
- Generates `plan.md` with research objective and design
- Creates job YAML files for training and evaluation
- Estimates resource requirements
- Checks against project quotas
- Generates approval summary for review

**Example**: Converts "compare LoRA ranks 8 and 16" into a complete experiment plan with training jobs, evaluation jobs, and resource estimates.

See [`.agents/skills/plan-ml-experiment/SKILL.md`](.agents/skills/plan-ml-experiment/SKILL.md) for detailed workflow.

#### train-llm
**Purpose**: Execute training jobs with proper tracking and logging

**When to use**:
- After experiment plan is approved
- When you're ready to start training

**What it does**:
- Verifies approval status and environment
- Creates run tracking structure
- Activates project environment
- Executes training with stdout/stderr capture
- Updates run status and timestamps
- Records execution in `history.md`
- Extracts W&B URLs from logs

**Phase 1 limitation**: Local execution only (SSH and Slurm coming in Phase 6)

See [`.agents/skills/train-llm/SKILL.md`](.agents/skills/train-llm/SKILL.md) for detailed workflow.

#### evaluate-llm
**Purpose**: Run evaluation and compare results against baselines

**When to use**:
- After training runs complete successfully
- When you're ready to assess experiment results

**What it does**:
- Verifies training completion
- Identifies best checkpoint
- Executes evaluation job
- Calculates primary and secondary metrics
- Compares against baseline from plan
- Assesses success criteria
- Drafts `results.yaml`

**Example**: Loads the best LoRA checkpoint, evaluates on test set, compares accuracy to baseline, and determines if success criteria are met.

See [`.agents/skills/evaluate-llm/SKILL.md`](.agents/skills/evaluate-llm/SKILL.md) for detailed workflow.

#### finalize-experiment
**Purpose**: Complete experiment documentation and propose Git commit

**When to use**:
- After evaluation completes
- When you're ready to document and commit results

**What it does**:
- Verifies all required artifacts exist
- Finalizes `results.yaml`
- Updates `history.md` with completion entry
- Writes `journal.md` with analysis and next steps
- Updates `project-log.md` with project-level conclusion
- Reviews Git changes for secrets and large files
- Proposes commit with structured message
- Waits for explicit approval before committing

**Safety checks**:
- No secrets, tokens, or credentials
- No model checkpoints or large artifacts
- No W&B caches or raw Slurm logs

See [`.agents/skills/finalize-experiment/SKILL.md`](.agents/skills/finalize-experiment/SKILL.md) for detailed workflow.

### Subagents

For complex tasks, Codex can delegate to specialist subagents. Each subagent has focused expertise and clear boundaries.

#### Research Journal & Git Agent
**Mission**: Find relevant prior work and consolidate verified evidence

**Modes**:
- **Discovery Mode**: Search project history before planning experiments
- **Finalize Mode**: Complete documentation and propose commits after experiments

**Use when**:
- You need comprehensive prior work search across multiple sources
- You're ready to finalize and commit experiment results
- You need help structuring research documentation

**What it does**:
- Searches project logs and experiment directories
- Analyzes past findings and conclusions
- Extracts reusable baselines
- Verifies experiment completeness
- Reviews Git changes for safety
- Drafts commit messages

**What it won't do**:
- Submit or execute training jobs
- Commit without explicit user approval
- Push checkpoints or large artifacts

See [`agent-descriptions/research-journal-git.md`](agent-descriptions/research-journal-git.md) for details.

#### W&B Analyst
**Mission**: Analyze training runs and compare experiments using Weights & Biases

**Use when**:
- You need detailed training curve analysis
- You want to compare metrics across multiple runs
- You need to identify training anomalies (divergence, plateaus)
- You want statistical summaries of run groups

**What it does**:
- Queries W&B API for run metadata and metrics
- Analyzes loss curves, learning rates, gradient norms
- Compares runs within and across experiments
- Identifies best checkpoints based on validation metrics
- Generates analysis reports with recommendations

**What it won't do**:
- Submit or execute training jobs
- Modify W&B run configurations
- Delete or archive W&B runs

**Availability**: Phase 7+ (W&B integration)

See [`agent-descriptions/wandb-analyst.md`](agent-descriptions/wandb-analyst.md) for details.

#### Hugging Face Managing Specialist
**Mission**: Manage Hub operations and create model cards

**Use when**:
- You need to create or update model cards
- You want to verify artifact upload status
- You need help with Hub repository management
- You want to ensure push policy compliance

**What it does**:
- Drafts comprehensive model cards with metadata
- Documents architecture, training, and limitations
- Verifies checkpoint uploads to Hub
- Validates push policy compliance
- Generates artifact tracking entries

**What it won't do**:
- Upload artifacts without explicit approval
- Override push policies from job configurations
- Upload private data when project requires privacy
- Commit Hugging Face tokens

**Availability**: Phase 8+ (Hugging Face Hub integration)

See [`agent-descriptions/huggingface-managing-specialist.md`](agent-descriptions/huggingface-managing-specialist.md) for details.

#### Visualization Specialist
**Mission**: Create research presentation graphics and publication figures

**Use when**:
- You need publication-quality figures
- You want training curves or metric comparisons
- You need ablation study visualizations
- You're preparing papers, presentations, or reports

**What it does**:
- Creates matplotlib/seaborn/plotly figures
- Generates training curves and comparisons
- Formats figures for publication (high DPI, multiple formats)
- Applies consistent styling
- Provides figure captions and interpretations

**What it won't do**:
- Manipulate or alter raw data values
- Create misleading visualizations
- Execute training or evaluation code
- Commit figures without review

**Common visualizations**:
- Training curves (loss, metrics over time)
- Ablation comparisons (bar charts, line plots, heatmaps)
- Multi-experiment comparisons with error bars
- Dataset statistics and distributions

See [`agent-descriptions/visualization-specialist.md`](agent-descriptions/visualization-specialist.md) for details.

#### Slurm Managing Specialist
**Mission**: Diagnose Slurm job failures and troubleshoot cluster issues

**Use when**:
- Slurm jobs fail with unclear errors
- Jobs are stuck in pending state
- Out-of-memory (OOM) errors occur
- Jobs are preempted or terminated unexpectedly
- Environment or module loading issues arise

**What it does**:
- Reads and interprets Slurm logs (*.out, *.err)
- Parses Slurm error messages
- Queries job status (squeue, sacct, scontrol)
- Diagnoses common issues (OOM, preemption, quotas, timeouts)
- Suggests resource adjustments
- Recommends configuration fixes

**What it won't do**:
- Modify configurations without approval
- Submit or resubmit jobs automatically
- Cancel running jobs without request
- Make assumptions about cluster policies

**Availability**: Phase 6+ (Slurm integration)

See [`agent-descriptions/slurm-managing-specialist.md`](agent-descriptions/slurm-managing-specialist.md) for details.

### When to Use Skills vs. Subagents

**Use skills** (automatic):
- Skills are invoked automatically by Codex during standard workflows
- You don't need to explicitly request them
- Example: "Plan an experiment" → Codex uses discover-prior-research, grill-me, and plan-ml-experiment automatically

**Use subagents** (explicit delegation):
- Request subagents when you need specialized expertise
- Useful for complex analysis or multi-step processes
- Example: "Analyze my W&B runs and identify the best configuration" → Codex delegates to W&B Analyst

## Phase 1 Status

✅ **Implemented**:
- Complete directory structure
- Agent definitions and skills
- Experiment templates
- Comprehensive documentation

🚧 **Future Phases**:
- Phase 6: SSH and Slurm execution
- Phase 7: W&B integration
- Phase 8: Hugging Face Hub integration
- Phase 9: Git automation

## Contributing

Contributions are welcome! To improve this template:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with "Use this template"
5. Submit a pull request

For Codex-specific questions, see the [Codex documentation](https://docs.kiro.ai/).

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Version**: 0.1.0 (Phase 1)
