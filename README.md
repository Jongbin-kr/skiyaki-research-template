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
├── .agents/
│   ├── skills/               # Reusable research workflows
│   │   ├── grill-me/            # Ask clarifying questions
│   │   ├── explore-project-history/  # Inspect this repo's past work
│   │   ├── plan-ml-experiment/  # Create experiment plans
│   │   ├── train-llm/           # Execute training
│   │   ├── evaluate-llm/        # Run evaluation
│   │   └── finalize-experiment/ # Complete documentation
│   └── agents/               # Subagent role descriptions
│
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

#### explore-project-history
**Purpose**: Inspect this repository's past experiments, results, project log, and Git history to find related work and baselines

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

See [`.agents/skills/explore-project-history/SKILL.md`](.agents/skills/explore-project-history/SKILL.md) for detailed workflow.

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

**Execution targets**: Local CPU runs via `run_local.py`; GPU and CPU-heavy jobs submit to Slurm over SSH via `submit_slurm.py`. All mutating remote actions are approval-gated.

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

Codex delegates only bounded tasks that benefit from specialist expertise. It selects the narrowest matching specialist, loads only that specialist's description immediately before delegation, and keeps unmatched work in the Main Agent. Work requiring multiple specialists is split into separate delegations; descriptions are never bulk-loaded. Each delegation identifies one objective, permitted and excluded scope, relevant paths or evidence, expected output, and applicable approval and roadmap gates.

| Canonical routing name | Scope | Gate |
|---|---|---|
| [Research Journal & Git](.agents/agents/research-journal-git.md) | Synthesize prior work or finalize research documentation and a Git proposal. | Commits require explicit user approval. |
| [W&B Analyst](.agents/agents/wandb-analyst.md) | Compare training-run metrics and local or user-provided run exports. | Reads tracking data; makes no config changes. |
| [Hugging Face Curator](.agents/agents/huggingface-curator.md) | Draft model cards and curate Hub artifacts and metadata. | Hub mutations (create/upload/visibility) require approval. |
| [Visualization Specialist](.agents/agents/visualization-specialist.md) | Create figures from results and user-provided data. | No data manipulation. |
| [Slurm Debugger](.agents/agents/slurm-debugger.md) | Diagnose Slurm job failures from logs, status output, and job configuration. | Mutating remote actions require approval. |

The linked descriptions define the full specialist contracts. Delegation does not bypass approval requirements; blocked work returns the relevant missing approval or configuration dependency and a non-executing next step.

### When to Use Skills vs. Subagents

**Use skills** for standard research workflows that Codex invokes automatically, such as prior-research discovery, clarification, and experiment planning.

**Use subagents** when a bounded task matches one specialist's expertise. For example, comparison of training runs can be delegated to the W&B Analyst, and model-card curation to the Hugging Face Curator.

## Current Status and Roadmap

✅ **Implemented (Phases 1-9)**:
- Structured experiment directories, templates, skills, and documentation
- Selective, bounded delegation to the five documented specialists
- Planning golden path: prior-research discovery, grilling, plan/job generation
- Local CPU execution (`run_local.py`) and SSH + Slurm submission (`submit_slurm.py`)
- Weights & Biases tracking (`track_wandb.py`) and run comparison
- Hugging Face Hub publication with upload verification (`publish_hf.py`)
- Experiment finalization and Git commit proposal (`finalize_experiment.py`)

🔒 **Gated on your configuration and approval**:
- Set `wandb.entity` and `huggingface.namespace` in `project-plan.md` before any
  online W&B run or Hub upload — helper scripts tolerate the placeholders and
  never call out until configured.
- Every execution, upload, and commit requires explicit user approval.

🗺️ **Roadmap**:
- **Phase 10**: Harness evaluation scenarios for agent behavior
- **1.0.0**: Stabilized release after real-world use

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

**Version**: 0.9.0 (Phases 1-9 implemented)
