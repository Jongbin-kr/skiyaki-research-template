# Example: LoRA Rank Ablation Study

> **⚠️ This is an example experiment for demonstration purposes.**
> The training was not actually executed; the numbers are illustrative. Use it as
> a reference for structuring your own experiments, then delete it when ready.

## Purpose

Demonstrates the v2 experiment layout and a hypothesis-driven, well-documented
research workflow.

## Research Question

**"What is the optimal LoRA rank for fine-tuning RoBERTa-base on SST-2?"**
Hypothesis: rank 16 gives the best accuracy/efficiency tradeoff, with diminishing
returns beyond it.

## Files In This Experiment

```
example-lora-rank-ablation/
├── plan.md           # Objective, hypothesis, design, decisions (prose)
├── run-config.yaml   # Reproducible run settings (fed to the training code)
├── history.md        # Factual timeline of what was run and the outcomes
├── journal.md        # Interpretation, findings, conclusions, next steps
├── logs/             # Run/Slurm logs (local only, gitignored)
└── figures/          # Optional visualizations
```

## What to Learn From Each File

- **`plan.md`** — a clear objective and testable hypothesis, an evidence-backed
  baseline, a controlled ablation design, an explicit (optional) success
  criterion, and a decisions table showing where each choice came from.
- **`run-config.yaml`** — the one machine-read file: entrypoint, parameters, the
  ablation matrix (`lora_rank: [4, 8, 16, 32]`), resources, and W&B / Hugging
  Face settings. This is what the project's training code consumes.
- **`history.md`** — factual, reverse-chronological events (submissions, Slurm
  job ids, completions, outcomes). No interpretation.
- **`journal.md`** — the analysis: hypothesis assessment, best run and why,
  unexpected results, limitations, and recommended next experiments.

## How to Use

Copy the structure for a new experiment:

```bash
cp -r experiments/example-lora-rank-ablation experiments/your-experiment-name
# then edit plan.md and run-config.yaml for your research question
```

Or ask the agent to plan a new experiment and it will create this structure for you.

## Related

- [../README.md](../README.md) — experiments directory overview
- [../../templates/](../../templates/) — blank templates
- [../../AGENTS.md](../../AGENTS.md) — workflow, stages, and conventions
- [../../.agents/skills/](../../.agents/skills/) — the skills used in each stage
