# AI/ML Research Workspace Template

> A GitHub template that gives an AI coding agent the structure, conventions, and
> skills to help you plan, run, and document AI/ML research — without a hidden
> framework. You supervise; the agent adapts to your project's own code.

## What Is This?

A **convention template**, not a runner. It provides:

- 📁 **A standard experiment layout** — plan, run config, history, journal per experiment
- 🤖 **Skills** — reusable markdown procedures the agent follows, grouped into stages
- 📝 **Conventions** — Slurm, W&B, Hugging Face, and git-safety practices written as guidance
- 🧭 **AGENTS.md** — the rules the agent reads every time

There is no code that gates or scores your work. The agent proposes, you approve
in chat, and experiments run using your project's own training code.

## Who Is This For?

AI/ML researchers who write their own training code (PyTorch, JAX, etc.), use SSH
+ GPU clusters (Slurm), and want AI assistance that stays general and
human-supervised.

## Quick Start

### 1. Create your project

Click **Use this template** on GitHub to make a new repository, then clone it.
(To wrap an existing research repo, copy this template's convention files —
`AGENTS.md`, `.agents/`, `experiments/`, `project-plan.md`, `project-log.md`
— into it.)

### 2. Let the agent set you up *(one-time)*

Open the project in your agent and say: **"Help me set up this project."** The
agent runs the **Setup** stage and asks you one thing at a time to configure:

- **Environment** — if the project already has an `environment.yaml` /
  `pyproject.toml`, it's used; otherwise the agent helps create a conda env.
- **`project-plan.md`** — your stable settings, with hints on where to find each:
  - SSH host — an alias in your `~/.ssh/config`
  - Slurm partition / account / QoS — from `sinfo` and `sacctmgr show user $USER`
  - CUDA ceiling — from `nvidia-smi`
  - W&B entity — your wandb.ai profile; Hugging Face namespace — your HF user/org

Tokens stay in your environment, never in the repo. Prefer this to editing
`project-plan.md` by hand, though you can do that too.

### 3. Create the environment

```bash
conda env create -f environment.yaml && conda activate <env-name>
```

### 4. Run your first experiment

Describe it to the agent, e.g. *"Compare LoRA ranks 8, 16, 32 for fine-tuning
RoBERTa on SST-2."* The agent then works through:

- **Plan** — reviews prior work, asks clarifying questions, writes `plan.md` +
  `run-config.yaml`, and asks for your approval.
- **Run** — (after approval) runs training/evaluation and records it in `history.md`.
- **Finalize** — interprets results in `journal.md`, updates `project-log.md`,
  and proposes a commit.

### 5. What you get

Each experiment leaves a self-contained folder under `experiments/<id>/` with
its plan, run config, factual history, and interpretation.

## How It Works: Stages

**Setup** runs once; **Plan → Run → Finalize** repeats per experiment. See
[AGENTS.md](AGENTS.md) for the full workflow and conventions.

| Stage | Goal | Skills |
|---|---|---|
| **Setup** *(one-time)* | Configure environment and `project-plan.md` | `setup-project` |
| **Plan** | Decide what to run | `explore-project-history`, `grill-me`, `plan-ml-experiment` |
| **Run** | Execute and record | `train-llm`, `evaluate-llm` |
| **Finalize** | Interpret and commit | `finalize-experiment` |

Each skill is a markdown procedure under `.agents/skills/<name>/SKILL.md`.

## Project Structure

```
your-project/
├── AGENTS.md                 # Workflow, stages, and conventions the agent follows
├── project-plan.md           # Stable project settings (prose)
├── project-log.md            # Project-level conclusions over time
│
├── .agents/
│   ├── skills/               # Skills (markdown procedures), grouped by stage
│   │   ├── setup-project/
│   │   ├── explore-project-history/
│   │   ├── grill-me/
│   │   ├── plan-ml-experiment/
│   │   ├── train-llm/
│   │   ├── evaluate-llm/
│   │   └── finalize-experiment/
│   └── templates/            # Blank templates the skills copy from
│
├── experiments/              # Your experiments
│   ├── example-lora-rank-ablation/   # Worked example (safe to delete)
│   └── <experiment-id>/
│       ├── plan.md           # Objective, hypothesis, design (prose)
│       ├── run-config.yaml   # Reproducible settings — fed to your training code
│       ├── history.md        # Factual timeline
│       ├── journal.md        # Interpretation and conclusions
│       ├── logs/             # Run/Slurm logs (local only, gitignored)
│       └── figures/          # Visualizations
│
├── environment.yaml          # Example conda environment
├── src/                      # Your training/eval code
├── notebooks/                # Jupyter notebooks
├── outputs/                  # Training outputs (not in Git)
└── data/                     # Datasets (not in Git)
```

The only machine-read file in an experiment is `run-config.yaml` — it is passed
to your training code. Everything else is written for people to read.

## Example Experiment

`experiments/example-lora-rank-ablation/` is a complete worked example (a LoRA
rank ablation on RoBERTa/SST-2) showing the plan, run config, history, and
journal. The training wasn't actually run — the numbers are illustrative. Delete
it when you start your own work, or keep it as a reference.

## Conventions (summary)

- GPU / CPU-heavy jobs go through Slurm; short CPU checks may run locally.
- Track runs with W&B when configured; publish checkpoints to the Hugging Face
  Hub per your push policy (private by default).
- Record every run in `history.md`; interpret in `journal.md`.
- You are the approval gate — the agent asks before running jobs, uploading, or
  committing.
- Never commit secrets, checkpoints, W&B caches, or raw logs; a human reviews the
  diff before committing.

## License

MIT License — see [LICENSE](LICENSE).

---

**Version**: 0.10.0 (v2 — convention-only, code-free)
