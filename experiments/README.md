# Experiments Directory

This directory contains all experimental work for the project. Each experiment is a self-contained investigation with its own plan, configurations, runs, and results.

## Structure

Each experiment follows this structure:

```
<experiment-id>/
├── plan.md              # Research question, hypothesis, and design
├── jobs/                # Training and evaluation configurations
│   ├── train.yaml
│   └── evaluate.yaml
├── runs/                # Execution attempts
│   └── <run-id>/
│       ├── run.yaml            # Run metadata and status
│       ├── resolved-job.yaml   # Exact configuration used
│       └── logs/               # Execution logs
├── results.yaml         # Final metrics and outcomes
├── history.md           # Chronological timeline of events
├── journal.md           # Analysis, insights, and conclusions
└── figures/             # Visualizations and plots
```

## Example Experiment

### `example-lora-rank-ablation/`

This is a **complete, realistic example** demonstrating the template's experiment structure. It shows:

- ✅ Clear research question: "What is the optimal LoRA rank for fine-tuning?"
- ✅ Hypothesis-driven design with baseline comparison
- ✅ Ablation study with multiple configurations (ranks 4, 8, 16, 32)
- ✅ Complete job configurations with resource requirements
- ✅ Example run with logs and metadata
- ✅ Comprehensive results with metrics and recommendations
- ✅ Factual history timeline
- ✅ Thoughtful journal with analysis and next steps

**Purpose**: Reference this example when:
- Planning your first experiment
- Understanding experiment documentation
- Learning the template's structure
- Training new team members

**Note**: This is an example only. The training was not actually executed. You can:
- Keep it as a reference
- Delete it when starting your own research
- Use it as a template for your experiments

## Creating New Experiments

### Using Codex

Request an experiment from Codex:

```
"I want to compare LoRA ranks 8 and 16 for fine-tuning RoBERTa on SST-2"
```

Codex will:
1. Search for related past experiments
2. Ask clarifying questions about metrics and success criteria
3. Generate a complete experiment plan and job configurations
4. Request your approval before execution

### Manual Creation

1. Create experiment directory:
   ```bash
   mkdir -p experiments/<experiment-id>/{jobs,runs,figures}
   ```

2. Copy templates:
   ```bash
   cp templates/experiment-plan.md experiments/<experiment-id>/plan.md
   cp templates/train-job.yaml experiments/<experiment-id>/jobs/train.yaml
   cp templates/evaluate-job.yaml experiments/<experiment-id>/jobs/evaluate.yaml
   ```

3. Fill in the templates with your research question and configuration

4. Execute and track runs following the workflow in AGENTS.md

## Experiment Lifecycle

1. **Planning**: Create `plan.md` with research question, hypothesis, baseline
2. **Configuration**: Define jobs in `jobs/*.yaml` with reproducible settings
3. **Approval**: Get explicit approval before execution (see AGENTS.md)
4. **Execution**: Run training/evaluation, track in `runs/`
5. **Evaluation**: Calculate metrics, compare to baseline
6. **Finalization**: Write `results.yaml`, update `history.md` and `journal.md`
7. **Archival**: Update `project-log.md`, commit experiment to Git

## Best Practices

### Research Questions
- State clear, testable hypotheses
- Define specific success criteria
- Identify baseline for comparison

### Configuration
- Use YAML for reproducibility
- Document all hyperparameters
- Use matrix for ablation studies

### Documentation
- **history.md**: Factual, chronological events
- **journal.md**: Analysis, interpretation, insights
- Keep them distinct in purpose

### Version Control
- ✅ Commit: plans, configs, results, documentation
- ❌ Don't commit: checkpoints, logs, W&B caches, secrets

## Finding Related Work

Before starting a new experiment:

1. Search `project-log.md` for related conclusions
2. Browse experiments in this directory for similar work
3. Ask Codex to use the `discover-prior-research` skill

This prevents duplicating past work and helps identify reusable configurations.

## Questions?

- See [AGENTS.md](../AGENTS.md) for workflow rules
- See [templates/](../templates/) for file formats
- See [.agents/skills/](../.agents/skills/) for detailed workflows
- See the example experiment as a reference

---

**Start your first experiment by asking Codex, or manually create a directory following the structure above.**
