---
experiment_id: <kebab-case-id>
status: awaiting_approval
primary_metric:
  name: <metric-name>
  direction: minimize|maximize
success_criteria:
  - <criterion-1>
  - <criterion-2>
jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml
approval:
  status: pending
  requested_at: <timestamp>
---

## Research Objective

[Describe the research question or hypothesis being investigated. What specific aspect of model behavior, training methodology, or architectural choice are you exploring?]

## Baseline

[Specify the baseline for comparison. This could be:
- A previous experiment (reference by experiment_id)
- A published result (include citation)
- A standard configuration (describe setup)
- "None" for initial experiments]

## Design Rationale

[Explain the experimental design choices:
- Why these specific hyperparameters or configurations?
- What variations are being tested (if using matrix)?
- How will results answer the research question?]

## Agent-Determined Defaults

[Document any parameters where agent selected defaults. Examples:
- Learning rate scheduler: cosine with warmup (standard for this model family)
- Batch size: 8 (maximum fitting in 16GB GPU with gradient accumulation)
- Evaluation frequency: every 500 steps (balancing overhead vs. monitoring)]

## Risks and Limitations

[Identify potential issues:
- Known limitations of the approach
- Resource constraints that may affect results
- Assumptions that may not hold
- Alternative approaches not explored in this experiment]
