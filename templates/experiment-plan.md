---
schema_version: 1
experiment_id: <experiment-id>
status: draft  # Options: draft, grilling, planned, awaiting_approval, approved, running, evaluating, finalizing, completed, failed, cancelled, blocked

primary_metric:
  name: <metric-name>
  direction: maximize  # Options: maximize, minimize

success_criteria:
  minimum_improvement: 0.02  # Minimum improvement over baseline
  # Add other criteria as needed

jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml

approval:
  status: pending  # Options: pending, approved, rejected
  approved_by: null
  approved_at: null
  approved_commit: null
---

# <Experiment Title>

## Purpose

[Describe the research question this experiment addresses]

## Hypothesis

[State your hypothesis about what you expect to find]

## Baseline

[Describe the baseline approach for comparison]

- Model: [baseline model]
- Dataset: [baseline dataset and split]
- Metrics: [baseline metric values]
- Source: [where baseline comes from - prior experiment, paper, etc.]

## Design

[Explain the experimental design]

### Variables

[What you're changing/ablating]

### Controls

[What you're keeping constant]

### Rationale

[Why this design will test your hypothesis]

## Agent-Determined Defaults

[List any parameters the agent chose and why]

- [Parameter]: [value] - [rationale]

## Risks and Limitations

[What could go wrong or limit conclusions]

- [Risk 1]
- [Risk 2]

## Expected Outcomes

[What results would support or refute your hypothesis]

### If Hypothesis Supported
[What you'd conclude and do next]

### If Hypothesis Refuted
[What you'd conclude and do next]
