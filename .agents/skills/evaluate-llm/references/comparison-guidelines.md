# Run Comparison Guidelines

## Purpose

This document defines the systematic approach for comparing training runs, assessing success criteria, and determining when to delegate detailed analysis to the W&B Analyst subagent.

## Run Comparison Approach

### Primary Metric Comparison

**Principle**: All runs within an experiment are compared using the primary metric defined in plan.md.

**Steps**:

1. **Extract Primary Metric Definition**:
   - Read `plan.md` frontmatter for `primary_metric.name` and `primary_metric.direction`
   - Direction values: `maximize` (higher is better) or `minimize` (lower is better)

2. **Collect Run Metrics**:
   - For each run in `runs/` directory, read `runs/<run-id>/run.yaml`
   - Extract the primary metric value from the `metrics` field
   - If metric is missing, mark run as incomplete and exclude from comparison

3. **Rank Runs**:
   - Sort runs by primary metric value according to direction
   - For `maximize`: sort descending (highest first)
   - For `minimize`: sort ascending (lowest first)
   - Identify the best performing run (rank 1)

4. **Record Comparison**:
   - Document best run ID, checkpoint path, and metric value
   - Document all runs with their rankings for reference
   - Note any runs that were excluded and why

**Example**: For `primary_metric: {name: accuracy, direction: maximize}`, a run with accuracy 0.874 outperforms one with 0.866.

### Secondary Metrics

While comparison is driven by the primary metric, secondary metrics provide valuable context:

- Training time and resource usage (for efficiency analysis)
- Additional task-specific metrics (e.g., F1 score alongside accuracy)
- Model characteristics (e.g., parameter count, memory usage)

**When to Consider Secondary Metrics**:
- Best run has only marginal improvement over second-best (<1% difference)
- Resource constraints are critical (memory, time, cost)
- Multiple metrics are part of success criteria

Document secondary metrics in the results summary but do not use them to override primary metric rankings unless success criteria explicitly require it.

## Baseline Comparison

### Baseline Definition

The baseline represents the reference performance against which the experiment's results are measured. Baselines come from:

1. **Plan.md Specification**: Explicitly stated baseline in the experiment plan
2. **Prior Experiments**: Best result from `project-log.md` or related experiment `results.yaml`
3. **Published Results**: Literature benchmarks or pretrained model performance
4. **No Fine-tuning**: Model performance without the intervention being tested

### Improvement Calculation

**Absolute Improvement**:
```
improvement = best_run_value - baseline_value
```

**Percentage Improvement**:

For metrics where higher is better (maximize):
```
improvement_percentage = ((best_run_value - baseline_value) / baseline_value) × 100
```

For metrics where lower is better (minimize):
```
improvement_percentage = ((baseline_value - best_run_value) / baseline_value) × 100
```

**Example**:
- Baseline accuracy: 0.853
- Best run accuracy: 0.874
- Absolute improvement: 0.874 - 0.853 = 0.021 (2.1 percentage points)
- Percentage improvement: ((0.874 - 0.853) / 0.853) × 100 = 2.46%

**Important**: Distinguish between absolute improvement (difference in metric values, e.g., 2.1 percentage points for accuracy) and percentage improvement (relative change, e.g., 2.46% improvement).

### Missing Baseline Handling

If no baseline is defined or available:
- **Option 1**: Use the worst-performing run from the current experiment as an internal baseline (useful for ablation studies)
- **Option 2**: Note that baseline comparison is unavailable and focus on relative rankings within the experiment
- **Option 3**: Ask user to specify baseline before finalizing results

Document the baseline source clearly in results.yaml to ensure reproducibility.

## Success Criteria Assessment

### Assessment Logic

**Process**:

1. **Extract Success Criteria**: Read `success_criteria` from plan.md frontmatter or plan body
2. **Evaluate Each Criterion**: Check whether the best run meets each criterion
3. **Document Evidence**: For each criterion, record whether it was met and provide specific evidence
4. **Overall Success Determination**: Experiment succeeds if ALL criteria are met

### Common Success Criteria Patterns

**Minimum Improvement Threshold**:
```yaml
success_criteria:
  minimum_improvement: 0.02  # 2% absolute improvement required
```

Assessment:
- Calculate absolute improvement: `best_run_value - baseline_value`
- Met if: `improvement >= minimum_improvement`
- Evidence: "Achieved 0.021 improvement (target: ≥0.02)"

**Minimum Metric Value**:
```yaml
success_criteria:
  minimum_accuracy: 0.87
```

Assessment:
- Met if: `best_run_value >= minimum_accuracy`
- Evidence: "Achieved 0.874 accuracy (target: ≥0.87)"

**Resource Constraints**:
```yaml
success_criteria:
  maximum_training_time_hours: 6.0
  maximum_memory_gb: 10.0
```

Assessment:
- Met if: `actual_resource_usage <= maximum_allowed`
- Evidence: "Training time: 4.36 hours (limit: 6.0 hours)"

**Multiple Criteria** (all must be met):
```yaml
success_criteria:
  - minimum_improvement: 0.02
  - maximum_training_time_hours: 6.0
  - convergence_achieved: true
```

Assessment:
- Evaluate each criterion independently
- Overall success requires ALL to be met
- Evidence: Document each criterion separately with pass/fail and supporting data

### Assessment Documentation Format

Record assessment in results.yaml:

```yaml
success_criteria_assessment:
  - criterion: "minimum_improvement: 0.02"
    met: true
    evidence: "Achieved 0.021 absolute improvement over baseline (2.46% relative)"
  
  - criterion: "maximum_training_time_hours: 6.0"
    met: true
    evidence: "Training completed in 4.36 hours, well within limit"
  
  - criterion: "convergence_achieved: true"
    met: true
    evidence: "Validation loss plateaued after epoch 2, final loss 0.234"

overall_success: true
rationale: |
  All success criteria met. Experiment achieved target improvement (2.1% vs 2.0% target)
  with acceptable resource usage. Hypothesis confirmed: rank 16 provides optimal
  accuracy/efficiency tradeoff.
```

### Partial Success Handling

If some but not all criteria are met:
- Set `overall_success: false`
- In rationale, explain which criteria failed and by how much
- Suggest next steps (e.g., "Consider increasing training time to meet accuracy target")

### Ambiguous Criteria Handling

If success criteria are vague (e.g., "good performance", "reasonable efficiency"):
- Request clarification from user before finalizing assessment
- Document assumptions made if clarification is unavailable
- Be conservative: lean toward marking as not met if criterion is ambiguous

## W&B Analyst Subagent Delegation

### When to Call W&B Analyst

Delegate detailed analysis to the W&B Analyst subagent in these situations:

**1. Large Run Count (>5 runs)**:
- Manual comparison becomes error-prone and time-consuming
- W&B Analyst can efficiently aggregate and visualize trends
- Example: Hyperparameter sweep with 10+ configurations

**2. Unexpected Patterns**:
- Best run performs worse than baseline (possible bug or misconfiguration)
- High variance across runs with identical configurations (non-determinism issue)
- Metrics show unexpected relationships (e.g., accuracy increases but loss also increases)
- Training divergence or instability (loss spikes, NaN values)
- Performance degrades across epochs when improvement was expected

**3. Complex Multi-Metric Analysis**:
- Success criteria depend on tradeoffs between multiple metrics
- Need to identify Pareto-optimal runs (e.g., accuracy vs. training time)
- Requires correlation analysis between metrics

**4. User Request**:
- User explicitly asks for detailed W&B analysis
- User requests specific visualizations (learning curves, metric distributions)
- User wants comparative analysis with runs from other experiments

**5. Baseline Inconsistency**:
- Results conflict with stated baseline or prior experiment results
- Need to verify baseline metrics from W&B history
- Baseline comes from a W&B run and needs validation

### How to Delegate

**Delegation Protocol**:

1. **Prepare Context**:
   - Experiment ID and plan.md path
   - List of W&B run IDs to analyze
   - Primary and secondary metrics of interest
   - Specific question or analysis goal

2. **Invoke W&B Analyst**:
   ```
   Delegate to W&B Analyst subagent:
   - Experiment: example-lora-rank-ablation
   - Runs: [train-r4__20250115T100000, train-r8__20250115T110000, ...]
   - Question: "Why does rank 32 show only marginal improvement over rank 16 
     despite 20% increase in parameters?"
   - Analysis type: learning curves, metric correlations, resource usage comparison
   ```

3. **Incorporate Analysis**:
   - Review W&B Analyst findings
   - Integrate key insights into results.yaml findings section
   - Reference W&B Analyst report in journal.md
   - Include any generated visualizations in experiment figures/

### When NOT to Delegate

Do not delegate to W&B Analyst if:
- Run count is small (≤5 runs) and metrics are clear
- Only primary metric comparison is needed (no complex analysis required)
- Results clearly meet or fail success criteria without ambiguity
- W&B integration is not yet implemented (Phase 2 limitation)

In Phase 2, W&B Analyst delegation is documented but not executable. Include placeholders in journal.md noting where W&B analysis would be valuable for future reference.

## Comparison Workflow Summary

**Standard Evaluation Flow**:

1. **Read plan.md** → Extract primary_metric, success_criteria, baseline
2. **Scan runs/ directory** → Collect all run.yaml files
3. **Extract metrics** → Parse primary metric values from each run
4. **Rank runs** → Sort by primary metric according to direction
5. **Identify best run** → Record run_id, checkpoint, metrics
6. **Calculate baseline comparison** → Compute absolute and percentage improvement
7. **Assess success criteria** → Evaluate each criterion with evidence
8. **Determine overall success** → All criteria must be met
9. **Check delegation triggers** → If >5 runs or unexpected patterns, consider W&B Analyst
10. **Draft results.yaml** → Document all findings in structured format

**Quality Checks**:

- Verify all runs have complete metric data
- Confirm primary metric direction is correctly applied
- Double-check improvement calculations (easy to confuse absolute vs. percentage)
- Ensure success criteria assessment is evidence-based, not subjective
- Review for consistency between best_run selection and success assessment

## Phase 2 Limitations

**Current Phase (Local Execution)**:
- Comparison relies on metrics recorded in local run.yaml files
- No automated W&B API queries
- W&B Analyst delegation is documented but not executable
- Manual W&B web UI inspection may be needed for detailed analysis

**Future Phases**:
- Phase 7: Automated W&B API integration for run querying and comparison
- Phase 7: Executable W&B Analyst subagent with programmatic access
- Phase 7: Automated generation of comparison visualizations

For now, provide clear instructions for manual W&B inspection when detailed analysis is needed.

## References

- **result-schema.md**: Defines results.yaml structure for recording comparison outcomes
- **SKILL.md**: Defines overall evaluate-llm workflow
- **project-plan.md**: Source of experiment metadata and resource quotas
- **plan.md**: Source of primary metric, success criteria, and baseline definitions
- **run.yaml**: Individual run metadata and metrics

## Examples

### Example 1: Simple Ablation Study (3 runs)

**Setup**:
- Primary metric: accuracy (maximize)
- Baseline: 0.853
- Success criteria: minimum_improvement = 0.02
- Runs: rank-4 (0.866), rank-8 (0.871), rank-16 (0.874)

**Comparison**:
1. Rank runs: rank-16 (best), rank-8, rank-4
2. Best run: rank-16 with 0.874 accuracy
3. Improvement: 0.874 - 0.853 = 0.021 (meets ≥0.02 threshold)
4. Success assessment: criterion met ✓
5. Overall success: true
6. W&B delegation: not needed (only 3 runs, clear winner)

### Example 2: Large Hyperparameter Sweep (12 runs, unexpected pattern)

**Setup**:
- Primary metric: validation_loss (minimize)
- Baseline: 1.23
- Success criteria: validation_loss < 1.10
- Runs: 12 runs with varying learning rates and batch sizes

**Comparison**:
1. Rank runs by validation_loss (ascending)
2. Best run: lr-0.001_bs-16 with validation_loss = 1.08
3. Improvement: (1.23 - 1.08) / 1.23 = 12.2% improvement
4. Success assessment: 1.08 < 1.10 ✓
5. Overall success: true
6. **Unexpected pattern detected**: Run with lr-0.0005 has lower training loss but higher validation loss (overfitting?)
7. **Delegate to W&B Analyst**: "Investigate apparent overfitting pattern in lr-0.0005 runs. Compare train vs. validation loss curves across all learning rates."

### Example 3: Failed Experiment (criteria not met)

**Setup**:
- Primary metric: F1 score (maximize)
- Baseline: 0.78
- Success criteria: minimum_improvement = 0.05 AND training_time < 10 hours
- Best run: F1 = 0.82, training_time = 12 hours

**Comparison**:
1. Best run: F1 = 0.82
2. Improvement: 0.82 - 0.78 = 0.04 (absolute), 5.1% (relative)
3. Success assessment:
   - Criterion 1 (minimum_improvement = 0.05): 0.04 < 0.05 ✗
   - Criterion 2 (training_time < 10 hours): 12 > 10 ✗
4. Overall success: false
5. Rationale: "Failed to meet improvement threshold (4% vs. 5% target). Training time also exceeded limit (12h vs. 10h limit). Consider: (1) increasing training epochs, (2) adjusting learning rate, (3) revisiting success criteria if 4% improvement is actually valuable."

---

**Document Version**: 1.0  
**Last Updated**: Phase 2 Core Skills Implementation  
**Related Requirements**: 5.3, 5.8, 5.9, 5.10
