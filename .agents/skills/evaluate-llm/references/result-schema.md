# Results Schema Reference

## Overview

This document defines the structure and format of `results.yaml` files, which record the final outcomes of ML experiments. The results file serves as the authoritative record of experiment performance, enabling comparison across experiments and tracking project progress over time.

## Purpose

The `results.yaml` file:
- Records the best performing run and its metrics
- Documents baseline comparisons and improvement calculations
- Assesses whether success criteria were met
- Summarizes all runs for comparative analysis
- Provides findings, limitations, and recommendations
- Serves as input for project-level reporting (project-log.md)

## File Location

Results files are stored at:
```
experiments/<experiment-id>/results.yaml
```

## Schema Definition

### Top-Level Structure

```yaml
experiment_id: string (required)
completed_at: string (required, ISO8601 timestamp)
best_run: object (required)
primary_metric: object (required)
secondary_metrics: list (optional)
all_runs: list (required)
success: object (required)
findings: list (optional)
limitations: list (optional)
recommendations: object (optional)
```

### experiment_id (required)

**Type**: `string`

**Description**: Unique identifier for the experiment, matching the experiment directory name and plan.md frontmatter.

**Format**: Kebab-case string (e.g., `example-lora-rank-ablation`)

**Example**:
```yaml
experiment_id: learning-rate-search
```

### completed_at (required)

**Type**: `string`

**Description**: Timestamp when the experiment was finalized and results recorded.

**Format**: ISO8601 timestamp with timezone (e.g., `2025-01-15T20:15:00Z`)

**Example**:
```yaml
completed_at: 2025-01-15T20:15:00Z
```

### best_run (required)

**Type**: `object`

**Description**: Identifies the best performing run based on the primary metric.

**Required Fields**:
- `run_id` (string): Full Run ID in format `{type}-{job_id}__{YYYYMMDDTHHMMSS}`
- `job_id` (string): Job identifier from job configuration
- `checkpoint` (string): HuggingFace Hub path or local path to model checkpoint

**Optional Fields**:
- Additional context fields relevant to the experiment (e.g., `lora_rank`, `learning_rate`)

**Example**:
```yaml
best_run:
  run_id: train-r16__20250115T142530
  job_id: train-lora-rank
  checkpoint: my-lab/roberta-base-sst2-lora-r16
  lora_rank: 16
```

### primary_metric (required)

**Type**: `object`

**Description**: Reports the primary metric used for run selection, including baseline comparison.

**Required Fields**:
- `name` (string): Metric name (e.g., `accuracy`, `perplexity`, `f1`)
- `value` (number): Metric value for best run

**Optional Fields** (for baseline comparison):
- `baseline_value` (number): Baseline metric value for comparison
- `improvement` (number): Absolute improvement over baseline
- `improvement_percentage` (number): Percentage improvement over baseline

**Example**:
```yaml
primary_metric:
  name: accuracy
  value: 0.874
  baseline_value: 0.853
  improvement: 0.021  # 2.1% absolute improvement
  improvement_percentage: 2.46  # 2.46% relative improvement
```

**Calculation Rules**:
- For metrics where **higher is better** (accuracy, f1, etc.):
  - `improvement = value - baseline_value`
  - `improvement_percentage = (improvement / baseline_value) * 100`
- For metrics where **lower is better** (perplexity, loss, etc.):
  - `improvement = baseline_value - value`
  - `improvement_percentage = (improvement / baseline_value) * 100`

**Note**: Improvement values can be negative if performance regressed below baseline.

### secondary_metrics (optional)

**Type**: `list` of objects

**Description**: Additional metrics tracked during the experiment (e.g., F1, training time, memory usage, parameter count).

**Object Structure**:
- `name` (string, required): Metric name
- `value` (number, required): Metric value for best run
- `baseline_value` (number, optional): Baseline value for comparison
- `improvement` (number, optional): Absolute improvement
- Additional context fields as needed (e.g., `percentage_of_total`)

**Example**:
```yaml
secondary_metrics:
  - name: f1
    value: 0.872
    baseline_value: 0.851
    improvement: 0.021
  - name: training_time_hours
    value: 4.36
  - name: peak_memory_gb
    value: 8.2
  - name: trainable_parameters
    value: 294912
    percentage_of_total: 0.23
```

### all_runs (required)

**Type**: `list` of objects

**Description**: Summary of all experiment runs for comparative analysis. Used to understand performance trends across hyperparameter variations.

**Minimum Required Fields per Run**:
- `run_id` (string): Full Run ID
- Primary metric value (field name matches `primary_metric.name`)

**Recommended Fields per Run**:
- Job-specific context fields (e.g., `lora_rank`, `learning_rate`, `batch_size`)
- Key resource metrics (e.g., `training_time_hours`, `peak_memory_gb`)

**Ordering**: List runs in logical order (e.g., by hyperparameter value, by metric performance)

**Example**:
```yaml
all_runs:
  - lora_rank: 4
    run_id: train-r4__20250115T100000
    accuracy: 0.866
    training_time_hours: 3.8
    peak_memory_gb: 7.1
  - lora_rank: 8
    run_id: train-r8__20250115T110000
    accuracy: 0.871
    training_time_hours: 4.1
    peak_memory_gb: 7.6
  - lora_rank: 16
    run_id: train-r16__20250115T142530
    accuracy: 0.874
    training_time_hours: 4.36
    peak_memory_gb: 8.2
```

### success (required)

**Type**: `object`

**Description**: Assesses whether experiment success criteria were met, with supporting rationale.

**Required Fields**:
- `criteria_met` (boolean): Overall success assessment
- `rationale` (string): Detailed explanation of why criteria were or were not met

**Optional Fields**:
- `detailed_assessment` (list): Per-criterion assessment (see Detailed Success Assessment below)

**Example**:
```yaml
success:
  criteria_met: true
  rationale: |
    Experiment met success criteria: achieved 2.1% improvement over baseline (target: ≥2%).
    Hypothesis confirmed: rank 16 provides excellent accuracy (0.874) with reasonable
    efficiency. Rank 32 shows only marginal improvement (+0.1%) while requiring 19%
    more training time and 19.5% more memory.
```

#### Detailed Success Assessment (optional)

For experiments with multiple success criteria, use `detailed_assessment`:

```yaml
success:
  criteria_met: true
  rationale: |
    Experiment achieved 3 of 3 success criteria.
  detailed_assessment:
    - criterion: "Achieve ≥2% accuracy improvement over baseline"
      met: true
      evidence: "Best run achieved 2.46% improvement (0.874 vs 0.853)"
    - criterion: "Training time <6 hours per run"
      met: true
      evidence: "All runs completed in 3.8-5.2 hours"
    - criterion: "Memory usage <10GB"
      met: true
      evidence: "Peak memory ranged from 7.1-9.8GB across all runs"
```

### findings (optional)

**Type**: `list` of strings

**Description**: Key insights and observations from the experiment. These should be actionable learnings that inform future work.

**Guidelines**:
- Focus on unexpected results or confirmed hypotheses
- Include performance trends observed across runs
- Note efficiency tradeoffs (accuracy vs. speed/memory)
- Highlight surprising outcomes

**Example**:
```yaml
findings:
  - Performance saturates between rank 16 and 32 (diminishing returns)
  - Rank 4 surprisingly competitive (0.866), only 0.8% behind best
  - Training time scales roughly linearly with rank
  - Memory usage increases moderately with rank
  - All ranks substantially outperform baseline (≥1.5% improvement)
```

### limitations (optional)

**Type**: `list` of strings

**Description**: Acknowledged constraints and threats to validity. These guide interpretation of results and identify areas for future investigation.

**Common Limitation Categories**:
- Single task/dataset (generalization concerns)
- Fixed hyperparameters (incomplete search space)
- Single architecture (architecture-specific conclusions)
- Missing measurements (e.g., inference latency, statistical significance)
- Environmental constraints (hardware, time, budget)

**Example**:
```yaml
limitations:
  - Single task (SST-2) - generalization to other tasks unverified
  - Fixed learning rate - optimal LR may vary by rank
  - Single model architecture (RoBERTa-base)
  - No inference latency measurements
  - No statistical significance testing (single seed)
```

### recommendations (optional)

**Type**: `object`

**Description**: Actionable guidance based on experiment results. Structure varies by experiment type.

**Common Patterns**:

#### Single Recommendation
```yaml
recommendations:
  use_case: production
  recommended_value: 16
  rationale: Best balance of accuracy and efficiency
```

#### Multiple Recommendations by Use Case
```yaml
recommendations:
  use_case: production
  recommended_rank: 16
  rationale: Best balance of accuracy (0.874) and efficiency
  
  alternative_low_memory:
    recommended_rank: 8
    accuracy: 0.871
    tradeoff: -0.3% accuracy for -6% training time and -7% memory
  
  alternative_maximum_accuracy:
    recommended_rank: 32
    accuracy: 0.875
    tradeoff: +0.1% accuracy for +19% training time and +19.5% memory
```

#### Next Steps
```yaml
recommendations:
  next_experiments:
    - Evaluate on additional tasks (MNLI, QNLI)
    - Test with different architectures (BERT, DeBERTa)
    - Measure inference latency across ranks
    - Run with multiple random seeds for statistical validation
```

## Metric Format Standards

### Naming Conventions

Use clear, standard metric names:

**Classification Metrics**:
- `accuracy` - overall accuracy
- `f1` - F1 score (specify macro/micro if relevant)
- `precision` - precision score
- `recall` - recall score
- `auc_roc` - Area under ROC curve

**Generative Metrics**:
- `perplexity` - language model perplexity
- `bleu` - BLEU score for translation
- `rouge_l` - ROUGE-L score for summarization

**Resource Metrics**:
- `training_time_hours` - total training duration
- `peak_memory_gb` - peak GPU memory usage
- `trainable_parameters` - count of trainable parameters
- `total_parameters` - count of all parameters

### Value Precision

**Performance Metrics**: Use 3-4 decimal places for fractional metrics
```yaml
accuracy: 0.874  # Good
accuracy: 0.87432189  # Too precise, noise dominates
accuracy: 0.87  # Too coarse for small differences
```

**Resource Metrics**: Use sensible precision for the unit
```yaml
training_time_hours: 4.36  # Good
peak_memory_gb: 8.2  # Good
trainable_parameters: 294912  # Exact count is fine
```

**Improvement Percentages**: Use 2 decimal places
```yaml
improvement_percentage: 2.46  # Good
improvement_percentage: 2.4623891  # Too precise
```

## Baseline Comparison Format

### With Baseline

When a baseline exists, always include comparison fields:

```yaml
primary_metric:
  name: accuracy
  value: 0.874
  baseline_value: 0.853
  improvement: 0.021
  improvement_percentage: 2.46
```

### Without Baseline

When no baseline exists (e.g., first experiment on a new task):

```yaml
primary_metric:
  name: accuracy
  value: 0.874
```

### Baseline Identification

Document the baseline in the `success` section or comments:

```yaml
# Baseline: zero-shot GPT-3.5 performance from Smith et al. (2024)
primary_metric:
  name: accuracy
  value: 0.874
  baseline_value: 0.425
  improvement: 0.449
  improvement_percentage: 105.65
```

## Complete Example

```yaml
# Experiment Results: LoRA Rank Ablation
# Objective: Determine optimal LoRA rank for SST-2 sentiment classification

experiment_id: example-lora-rank-ablation
completed_at: 2025-01-15T20:15:00Z

# Best performing run
best_run:
  run_id: train-r16__20250115T142530
  job_id: train-lora-rank
  checkpoint: my-lab/roberta-base-sst2-lora-r16
  lora_rank: 16

# Primary metric
primary_metric:
  name: accuracy
  value: 0.874
  baseline_value: 0.853
  improvement: 0.021
  improvement_percentage: 2.46

# Secondary metrics
secondary_metrics:
  - name: f1
    value: 0.872
    baseline_value: 0.851
    improvement: 0.021
  - name: training_time_hours
    value: 4.36
  - name: peak_memory_gb
    value: 8.2
  - name: trainable_parameters
    value: 294912
    percentage_of_total: 0.23

# All runs summary
all_runs:
  - lora_rank: 4
    run_id: train-r4__20250115T100000
    accuracy: 0.866
    training_time_hours: 3.8
    peak_memory_gb: 7.1
  - lora_rank: 8
    run_id: train-r8__20250115T110000
    accuracy: 0.871
    training_time_hours: 4.1
    peak_memory_gb: 7.6
  - lora_rank: 16
    run_id: train-r16__20250115T142530
    accuracy: 0.874
    training_time_hours: 4.36
    peak_memory_gb: 8.2
  - lora_rank: 32
    run_id: train-r32__20250115T160000
    accuracy: 0.875
    training_time_hours: 5.2
    peak_memory_gb: 9.8

# Success assessment
success:
  criteria_met: true
  rationale: |
    Experiment met success criteria: achieved 2.1% improvement over baseline (target: ≥2%).
    Hypothesis confirmed: rank 16 provides excellent accuracy (0.874) with reasonable
    efficiency. Rank 32 shows only marginal improvement (+0.1%) while requiring 19%
    more training time and 19.5% more memory.
  detailed_assessment:
    - criterion: "Achieve ≥2% accuracy improvement over baseline"
      met: true
      evidence: "Best run achieved 2.46% improvement (0.874 vs 0.853)"
    - criterion: "Training time <6 hours per run"
      met: true
      evidence: "All runs completed in 3.8-5.2 hours"
    - criterion: "Memory usage <10GB"
      met: true
      evidence: "Peak memory ranged from 7.1-9.8GB across all runs"

# Key findings
findings:
  - Performance saturates between rank 16 and 32 (diminishing returns)
  - Rank 4 surprisingly competitive (0.866), only 0.8% behind best
  - Training time scales roughly linearly with rank
  - Memory usage increases moderately with rank
  - All ranks substantially outperform baseline (≥1.5% improvement)

# Limitations
limitations:
  - Single task (SST-2) - generalization to other tasks unverified
  - Fixed learning rate - optimal LR may vary by rank
  - Single model architecture (RoBERTa-base)
  - No inference latency measurements
  - No statistical significance testing (single seed)

# Recommendations
recommendations:
  use_case: production
  recommended_rank: 16
  rationale: Best balance of accuracy (0.874) and efficiency
  
  alternative_low_memory:
    recommended_rank: 8
    accuracy: 0.871
    tradeoff: -0.3% accuracy for -6% training time and -7% memory
  
  alternative_maximum_accuracy:
    recommended_rank: 32
    accuracy: 0.875
    tradeoff: +0.1% accuracy for +19% training time and +19.5% memory
```

## Validation Checklist

When creating or reviewing a results.yaml file, verify:

- [ ] `experiment_id` matches experiment directory and plan.md
- [ ] `completed_at` timestamp is in ISO8601 format with timezone
- [ ] `best_run.run_id` exists in experiments/*/runs/ directory
- [ ] `primary_metric` includes name and value at minimum
- [ ] Improvement calculations are correct (if baseline exists)
- [ ] Improvement direction is appropriate (higher/lower is better)
- [ ] `all_runs` includes all completed runs with consistent fields
- [ ] `success.criteria_met` is boolean (true/false)
- [ ] `success.rationale` provides clear evidence for assessment
- [ ] Metric values use appropriate precision (3-4 decimals for fractions)
- [ ] File is valid YAML (no syntax errors)

## Integration with Other Artifacts

### Input Sources

The results.yaml file is typically generated by reading:
- `experiments/<experiment-id>/runs/*/run.yaml` - run metadata and metrics
- `experiments/<experiment-id>/plan.md` - success criteria, primary metric, baseline
- W&B run data (Phase 7+) - detailed metrics, system usage
- Evaluation script outputs - final metric calculations

### Output Consumers

The results.yaml file is used by:
- `history.md` - chronicling experiment execution and outcomes
- `journal.md` - recording analysis and conclusions
- `project-log.md` - tracking project-level progress
- `comparison-guidelines.md` - comparing across experiments
- Future experiments - establishing new baselines

## Best Practices

### Be Honest About Limitations
Document what you didn't test, measure, or control. This builds trust and guides future work.

### Quantify Tradeoffs
When recommending configurations, clearly state what is gained and lost (e.g., "+0.1% accuracy for +19% training time").

### Include Context
Add explanatory comments for non-obvious baselines, metric definitions, or experimental choices.

### Use Consistent Units
Stick to standard units across experiments:
- Time: hours (not minutes or seconds)
- Memory: GB (not MB)
- Parameters: raw count (not millions)

### Link to Evidence
Reference W&B run IDs, HuggingFace checkpoints, or log files to support claims.

### Update Regularly
Results files should be updated incrementally as runs complete, not created all at once at the end.

## Common Patterns

### Ablation Studies
Focus on how performance varies with a single factor (e.g., LoRA rank, learning rate).

```yaml
all_runs:
  - lora_rank: 4
    accuracy: 0.866
  - lora_rank: 8
    accuracy: 0.871
  - lora_rank: 16
    accuracy: 0.874
  - lora_rank: 32
    accuracy: 0.875
```

### Hyperparameter Searches
Show the explored space and optimal configuration.

```yaml
all_runs:
  - learning_rate: 1e-5
    batch_size: 16
    accuracy: 0.861
  - learning_rate: 2e-5
    batch_size: 16
    accuracy: 0.874
  - learning_rate: 5e-5
    batch_size: 16
    accuracy: 0.868
```

### Baseline Comparisons
Compare new approach against established methods.

```yaml
# Baseline: Full fine-tuning of RoBERTa-base
primary_metric:
  name: accuracy
  value: 0.874
  baseline_value: 0.876
  improvement: -0.002
  improvement_percentage: -0.23

findings:
  - LoRA achieves 99.8% of full fine-tuning accuracy
  - LoRA trains 3.2x faster (4.4h vs 14.1h)
  - LoRA uses 94% fewer trainable parameters (295K vs 125M)
```

## Summary

The results.yaml file is the authoritative record of experiment outcomes. It should:
- Be machine-readable (valid YAML) and human-readable (clear structure, comments)
- Provide complete information for understanding experiment success
- Support comparison across experiments and tracking over time
- Document limitations and provide actionable recommendations
- Use consistent formatting and naming conventions

Follow this schema to ensure results are comparable, reproducible, and useful for future research.
