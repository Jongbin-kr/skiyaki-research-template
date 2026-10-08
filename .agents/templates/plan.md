# <Experiment Title>

> Copy this file to `experiments/<experiment-id>/plan.md` and fill it in.
> This is a human-readable plan — plain prose, no enforced schema. The
> reproducible settings live next to it in `run-config.yaml`.

## Objective

[The research question this experiment answers.]

## Hypothesis

[A testable prediction. If this is an exploratory run with no fixed prediction,
say so here.]

## Baseline

[What you compare against: configuration, metric value, dataset/split, and where
it comes from — a repository path or Git commit. Write "none / exploratory" if
there is no baseline.]

## Design

- **Variables:** [what you manipulate — e.g. an ablation matrix]
- **Controls:** [what is held constant: model, data, seed, hyperparameters]
- **Rationale:** [why this design tests the hypothesis]

## Metric & Success Criterion

[The primary metric and how success is judged, if defined. Optional — for an
exploratory run, state what you'll look at instead of a pass/fail bar.]

## Decisions

[Record the key choices and where each came from: the user, project settings,
prior evidence, or an agent suggestion. This keeps the plan traceable.]

| Decision | Value | Source |
|---|---|---|
| [e.g. learning rate] | [value] | [user / project-plan.md / prior experiment / agent suggestion] |

## Risks & Limitations

- [Principal risk or limitation, and what it means for interpreting results.]

## Resource Estimate

[Run count (expand any matrix), rough wall time and GPU-hours, and whether it
fits the project's quotas in project-plan.md.]
