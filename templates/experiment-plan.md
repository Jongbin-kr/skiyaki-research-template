---
schema_version: 1
experiment_id: <experiment-id>
status: awaiting_approval
primary_metric:
  name: <metric-name>
  direction: <maximize-or-minimize>
success_criteria:
  metric: <metric-name>
  comparison: <comparison-to-baseline>
  operator: <gte-or-lte>
  threshold: <numeric-threshold>
baseline:
  name: <baseline-name>
  metric:
    name: <metric-name>
    value: <numeric-value>
    direction: <maximize-or-minimize>
  evaluation:
    dataset: <dataset-name>
    split: <evaluation-split>
  source: <repository-path-or-git-commit>
jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml
approval:
  status: pending
  approved_by: null
  approved_at: null
  approved_commit: null
---

# <Experiment Title>

## Agent-Determined Defaults

List only values selected by the agent. Every entry must include its rationale and repository/Git evidence, or state that it is an explicit assumption.

| Decision | Value | Rationale | Evidence or assumption |
|---|---|---|---|
| <decision> | <value> | <rationale> | <repository-path-or-commit-or-explicit-assumption> |

## Decision Provenance

Record each material decision exactly once using `user`, `project_setting`, `prior_evidence`, or `agent_default`.

| Decision | Value | Origin | Source |
|---|---|---|---|
| research_objective | <value> | <origin> | <user-turn-project-setting-path-or-evidence-ref> |
| baseline | <value> | <origin> | <source> |
| primary_metric | <value> | <origin> | <source> |
| success_criteria | <value> | <origin> | <source> |
| ablation_scope | <value> | <origin> | <source> |
| controlled_parameters | <value> | <origin> | <source> |

## Purpose

[State the resolved research objective.]

## Hypothesis

[State a testable prediction tied to the primary metric and success threshold.]

## Evidence-Backed Baseline

- **Name/configuration**: [baseline name and configuration]
- **Metric**: [name, numeric value, and maximize/minimize direction]
- **Evaluation data**: [dataset and split]
- **Source**: [repository path or Git commit]

## Design

### Variables

[Specify the ablation matrix or manipulated variables.]

### Controls

[Specify the model, data, seed strategy, and hyperparameters held constant.]

### Rationale

[Explain why the design tests the hypothesis and provides a valid baseline comparison.]

## Risks and Limitations

- [Principal risk or limitation]

## Expected Outcomes

### If Hypothesis Supported

[Interpret results meeting the measurable criterion.]

### If Hypothesis Refuted

[Interpret results not meeting the measurable criterion.]
