---
name: plan-ml-experiment
description: Turn resolved decisions into a reviewable experiment folder — a prose plan.md and a reproducible run-config.yaml. Use in the Plan stage after prior work is reviewed and open questions are resolved, to create the experiment and present it for approval. Plans only; does not run anything.
---

# Plan ML Experiment Skill

**Stage:** Plan

Turn resolved decisions into a reviewable experiment folder: a prose `plan.md`
and a reproducible `run-config.yaml`. This skill plans only — it does not execute
jobs or run anything.

## Prerequisites

- `explore-project-history` surfaced related prior work and reusable settings.
- `grill-me` resolved the objective, baseline, and (optionally) metric and
  success criterion.
- Stable settings come from `project-plan.md`; record what's missing rather than
  inventing it.

## Procedure

1. **Decide the branch — ask before creating one.** Never create or switch a
   branch on your own. Before any `git branch` or `git switch -c`, propose the
   exact name and ask the user, in one question: "`experiment/<id>` 브랜치를
   파도 될까요?" Create it only after the user says yes.

   Which case you are in decides whether a new branch is even needed:
   - **A new line of work** (first experiment, or a topic clearly different from
     the current branch's work): propose a new `experiment/<id>` branch and ask.
   - **A follow-up in the same line** (another run of the same topic while the
     conversation continues — a tweaked hyperparameter, one more ablation cell,
     a re-run): do NOT open a new branch. Stay on the current
     `experiment/<id>` branch. A branch holds a line of related experiments, not
     a single run.
   - **Unsure whether the topic has drifted far enough to warrant a new branch:**
     ask. Say what changed, and ask whether to finalize the current experiment
     and open a new branch, or keep going on this one. Let the user decide.

   If the user declines a branch, continue on the current branch.

2. **Create the experiment folder.** Choose a kebab-case id and create
   `experiments/<experiment-id>/` with `logs/` and `figures/` subdirectories.

3. **Write `plan.md` (prose, no frontmatter).** Include:
   - **Objective** — the resolved research question.
   - **Hypothesis** — a testable prediction (or note that the run is exploratory).
   - **Baseline** — what you compare against, with its source (path or commit).
   - **Design** — variables/ablation, controls held constant, and rationale.
   - **Decisions** — the key choices and where each came from (user, project
     setting, prior evidence, or your suggestion).
   - **Metric & success criterion** — if defined; otherwise state it's exploratory.
   - **Risks / limitations.**

   Start from [the plan template](../../templates/plan.md).

4. **Write `run-config.yaml`.** This is the reproducible, machine-read config that
   the project's training/evaluation code consumes. Capture entrypoint, parameters,
   any ablation matrix, seed, resources, and W&B / Hugging Face settings. Start
   from [the run-config template](../../templates/run-config.yaml). Do not
   embed secrets.

5. **Estimate scope.** Expand any matrix to a run count, estimate wall time and
   GPU-hours, and compare against the project's quotas in `project-plan.md`. Note
   this in `plan.md`.

6. **Summarize for the user.** Present a concise summary — recommended plan, the
   decisions you made, objective/hypothesis, baseline, metric & criterion (if
   any), run count & resources, and where the files are — then ask for approval
   or changes. Do not run anything; execution belongs to the Run stage.

## Output

- `experiments/<experiment-id>/plan.md`
- `experiments/<experiment-id>/run-config.yaml`
- A short approval summary for the user.

See the worked example at `experiments/example-lora-rank-ablation/` for a
complete plan.md + run-config.yaml.
