# AI/ML Research Workflow

This repository is a **convention template** for AI/ML research with an AI coding
agent. It provides structure, conventions, and reusable skills — not a framework
or runner. A human supervises the work in chat; the agent reads the project's own
code and runs experiments adapted to it. There is no hidden harness, no code that
gates or scores your work.

## How It Works: Stages and Skills

Research progresses through stages. Each stage groups the skills the agent uses
in it. The agent moves through them with you, not autonomously. **Setup** runs
once when a project is first created; **Plan → Run → Finalize** repeats per
experiment.

| Stage | Goal | Skills |
|---|---|---|
| **Setup** *(one-time)* | Configure the environment and `project-plan.md` for a new project, then hand off to Plan | [`setup-project`](.agents/skills/setup-project/SKILL.md) |
| **Plan** | Decide what to run: review prior work, resolve open questions, write the plan and run config | [`explore-project-history`](.agents/skills/explore-project-history/SKILL.md), [`grill-me`](.agents/skills/grill-me/SKILL.md), [`plan-ml-experiment`](.agents/skills/plan-ml-experiment/SKILL.md) |
| **Run** | Execute training and evaluation, record what happened | [`train-llm`](.agents/skills/train-llm/SKILL.md), [`evaluate-llm`](.agents/skills/evaluate-llm/SKILL.md), [`visualize-with-html`](.agents/skills/visualize-with-html/SKILL.md) |
| **Finalize** | Interpret results, update records, propose a commit | [`finalize-experiment`](.agents/skills/finalize-experiment/SKILL.md) |

Skills are guidance the agent reads when relevant; they are plain markdown
procedures, not scripts.

## Experiment Layout

Each experiment is a self-contained folder:

```
experiments/<experiment-id>/
├── plan.md           # Objective, hypothesis, design, decisions (prose)
├── run-config.yaml   # Reproducible run settings — passed to your training code
├── history.md        # Factual timeline: what was run, when, Slurm IDs, outcomes
├── journal.md        # Interpretation: findings, conclusions, next steps
├── logs/             # Raw run logs (.out/.err/.log) — local, gitignored; commit a summary.md instead
├── data/             # Large tabular results as CSV (optional, see convention 11)
└── figures/          # Visualizations — single self-contained HTML files
```

`run-config.yaml` is the one machine-read file: it is the input to the project's
own training/evaluation code. Everything else is written for humans to read.

Figures are single self-contained HTML files, not PNGs — see the
[`visualize-with-html`](.agents/skills/visualize-with-html/SKILL.md) skill.

## Conventions

These are conventions the agent follows and you supervise — not enforced gates.

1. **Prior work first.** Before planning, inspect `project-log.md`,
   `experiments/*/journal.md`, past `run-config.yaml` files, and relevant Git
   history for related work and reusable settings.

2. **A branch per line of experiments — ask before creating one.** A branch
   `experiment/<experiment-id>` holds a line of related experiments, not a single
   run. Keep the plan, run config, and records for that line on its branch. This
   keeps `main` clean, makes a failed line easy to discard, and allows parallel
   work.

   The agent never creates or switches a branch on its own. Before any branch
   operation it proposes the exact name and asks the user. Follow-up runs on the
   same topic stay on the current branch — do not open a new branch per run. When
   the topic drifts far from the current branch's work, the agent asks whether to
   finalize the current experiment and open a new branch, rather than piling
   unrelated work onto a branch that is effectively done. At Finalize, the user
   decides whether to merge the branch into `main` or keep it as a standalone
   record — both are fine.

3. **Clarify before planning.** When the objective, baseline, or metric is
   unclear, ask focused questions (one at a time). A metric and success criterion
   are encouraged but optional — exploratory runs are fine; just say so.

4. **Reproducible settings in YAML.** Put training/evaluation parameters in
   `run-config.yaml` so a run can be reproduced and read by the project's code.

5. **Execution environment.** Run jobs in the project's environment
   (`environment.yaml` / `uv` / `venv`). GPU and CPU-heavy jobs go through Slurm
   (`sbatch`) on the configured cluster — never run heavy work on a login node.
   Short CPU checks may run locally.

6. **Tracking and artifacts.** Track runs with Weights & Biases when configured
   (group by experiment, keep local data). Push checkpoints to the Hugging Face
   Hub per the project's push policy; repositories are public by default. Confirm
   with the user before pushing anything that must stay private, and never make a
   public repository private (or vice versa) without an explicit decision.
   **Local checkpoints** go under `outputs/<experiment-id>/<run-id>/` (gitignored).
   Disk retention: if nothing is pushed to the Hub, keep all local checkpoints
   (the local copy is the only one); if checkpoints are pushed to the Hub, keep
   only the best 3 locally and prune the rest (the Hub is the backup).

7. **Record every run.** Note each execution attempt in `history.md` (time, Slurm
   job id, status, outcome), including failures. Write interpretation in
   `journal.md`.

8. **Human-in-the-loop.** The agent proposes; you approve in chat. Nothing in a
   file blocks execution — you are the approval gate. Ask the user before
   submitting jobs, uploading artifacts, or committing.

9. **Git safety (review before committing).** Commit plans, configs, results, and
   documentation. Never commit secrets or credentials, model checkpoints, or W&B
   caches. Raw run/Slurm logs (`*.out`, `*.err`, `*.log`) are what tools emit;
   they stay local under each experiment's `logs/` and are gitignored. What we
   read and commit is a human-written summary (e.g. a `summary.md`), not the raw
   log. A human reviews the diff before any commit.

10. **Visualization and large data.** Save visualizations as single
   self-contained HTML files under `figures/` — not PNGs. Interactivity, when
   needed, uses Plotly loaded from a CDN; never embed the Plotly JS bundle in the
   file. Keep a figure's data light enough to write inline; when a chart's data
   is large, store it as CSV under the experiment's `data/` and have the figure
   read from it rather than inlining thousands of values. See the
   [`visualize-with-html`](.agents/skills/visualize-with-html/SKILL.md) skill.

11. **Completion.** An experiment is done when required runs finished, results are
   recorded, `history.md` and `journal.md` are written, `project-log.md` reflects
   the project-level outcome, and a commit is proposed for your approval.

## Project Configuration

`project-plan.md` holds stable project settings (environment, SSH/Slurm,
W&B/Hugging Face) as readable notes — don't re-ask for values recorded there.
`project-log.md` records project-level conclusions over time.
