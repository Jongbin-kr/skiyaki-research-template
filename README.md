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

1. Click **Use this template** on GitHub.
2. Edit `environment.yaml` (an example conda env) for your project, and create it.
3. Fill in `project-plan.md` with your stable settings (cluster, W&B entity,
   Hugging Face namespace, quotas).
4. Open the project in your agent and describe an experiment, e.g.
   *"Compare LoRA ranks 8, 16, 32 for fine-tuning RoBERTa on SST-2."*

The agent will review prior work, ask clarifying questions, write the plan and
run config, and — with your go-ahead — run and document the experiment.

## How It Works: Stages

Research moves through three stages; each groups the skills used in it. See
[AGENTS.md](AGENTS.md) for the full workflow and conventions.

| Stage | Goal | Skills |
|---|---|---|
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
├── .agents/skills/           # Skills (markdown procedures), grouped by stage
│   ├── explore-project-history/
│   ├── grill-me/
│   ├── plan-ml-experiment/
│   ├── train-llm/
│   ├── evaluate-llm/
│   └── finalize-experiment/
│
├── templates/                # Blank templates (plan.md, run-config.yaml, history.md, journal.md)
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
