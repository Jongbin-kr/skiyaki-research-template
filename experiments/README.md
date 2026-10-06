# Experiments

This directory holds all experimental work. Each experiment is a self-contained
folder with its plan, run config, and research records.

## Structure

```
<experiment-id>/
├── plan.md           # Objective, hypothesis, design, decisions (prose)
├── run-config.yaml   # Reproducible run settings — fed to your training code
├── history.md        # Factual timeline of what was run and the outcomes
├── journal.md        # Interpretation, conclusions, next steps
├── logs/             # Run/Slurm logs (kept local, gitignored)
└── figures/          # Visualizations
```

`run-config.yaml` is the only machine-read file — it is passed to the project's
training/evaluation code. The rest is written for people to read.

## Example Experiment

`example-lora-rank-ablation/` is a complete worked example (LoRA rank ablation on
RoBERTa/SST-2) — plan, run config, history, and journal. The training wasn't
actually run; the numbers are illustrative. Keep it as a reference or delete it
when you start your own work.

## Creating New Experiments

### With the agent

Just describe the experiment, e.g. *"compare LoRA ranks 8 and 16 for fine-tuning
RoBERTa on SST-2."* The agent reviews prior work, asks clarifying questions,
writes `plan.md` + `run-config.yaml`, and — with your go-ahead — runs and
documents it.

### Manually

```bash
mkdir -p experiments/<experiment-id>/{logs,figures}
cp templates/plan.md experiments/<experiment-id>/plan.md
cp templates/run-config.yaml experiments/<experiment-id>/run-config.yaml
cp templates/history.md experiments/<experiment-id>/history.md
cp templates/journal.md experiments/<experiment-id>/journal.md
```

Then fill them in and follow the workflow in [AGENTS.md](../AGENTS.md).

## Lifecycle (stages)

1. **Plan** — review prior work, clarify decisions, write `plan.md` + `run-config.yaml`
2. **Run** — execute training/evaluation (Slurm for GPU/heavy jobs), record in `history.md`
3. **Finalize** — interpret in `journal.md`, update `project-log.md`, propose a commit

## Version Control

- ✅ Commit: plans, run configs, research notes, documentation
- ❌ Don't commit: checkpoints, raw logs (`logs/*.out`/`*.err`), W&B caches, secrets

## Finding Related Work

Before a new experiment: check `project-log.md`, browse this directory, or ask
the agent to use the `explore-project-history` skill. This avoids duplicating
past work and surfaces reusable settings.

---

See [AGENTS.md](../AGENTS.md) for the workflow, [templates/](../templates/) for
blank files, and [.agents/skills/](../.agents/skills/) for the stage skills.
