# Common Experiment Patterns

This guide describes common ML experiment patterns and how to structure them.

## Pattern 1: Hyperparameter Ablation

**When to use**: Testing the effect of a single hyperparameter while keeping others constant

**Structure**:
- Single variable in matrix
- All other parameters fixed
- Clear baseline value in the range

**Example**: LoRA rank ablation

```yaml
matrix:
  lora_rank: [4, 8, 16, 32]

parameters:
  learning_rate: 2.0e-4  # Fixed
  batch_size: 8          # Fixed
  epochs: 3              # Fixed
```

**Success criteria**: Find optimal value or determine saturation point

**Common ablations**:
- Learning rate: `[1e-5, 2e-5, 5e-5, 1e-4, 2e-4]`
- Batch size: `[4, 8, 16, 32]`
- LoRA rank: `[4, 8, 16, 32, 64]`
- Dropout: `[0.0, 0.1, 0.2, 0.3]`
- Number of layers: `[2, 4, 6, 8, 12]`

## Pattern 2: Grid Search

**When to use**: Testing combinations of 2-3 hyperparameters

**Structure**:
- Multiple variables in matrix
- Tests all combinations
- Can be expensive (exponential growth)

**Example**: Learning rate + batch size

```yaml
matrix:
  learning_rate: [1e-4, 2e-4, 5e-4]
  batch_size: [8, 16]

# Total runs: 3 × 2 = 6
```

**Success criteria**: Find best combination

**Warning**: Grid search grows quickly:
- 2 variables × 3 values each = 9 runs
- 3 variables × 3 values each = 27 runs
- Consider random search or Bayesian optimization for large spaces

## Pattern 3: Baseline Comparison

**When to use**: Comparing a new approach against established baseline(s)

**Structure**:
- Clear baseline configuration
- New approach with proposed improvements
- Same evaluation protocol

**Example**: Full fine-tuning vs. LoRA

```yaml
# Run 1: Baseline
experiment_id: baseline-full-finetune
parameters:
  training_mode: full
  learning_rate: 3e-5

# Run 2: Proposed
experiment_id: lora-finetune
parameters:
  training_mode: lora
  lora_rank: 16
  learning_rate: 2e-4
```

**Success criteria**: New approach meets or exceeds baseline on primary metric

**Considerations**:
- Ensure fair comparison (same data, same evaluation)
- Report training time and memory in addition to accuracy
- Consider multiple metrics (accuracy, efficiency, inference speed)

## Pattern 4: Architecture Search

**When to use**: Comparing different model architectures or configurations

**Structure**:
- Different model names or architectural configs
- Consistent training protocol
- Same task and data

**Example**: Comparing BERT variants

```yaml
matrix:
  model_name: ["bert-base-uncased", "roberta-base", "albert-base-v2"]

parameters:
  learning_rate: 3e-5  # Same for all
  epochs: 3            # Same for all
```

**Success criteria**: Identify best architecture for task

**Considerations**:
- Different architectures may need different hyperparameters
- Consider inference time/model size tradeoffs
- Vocabulary differences may affect tokenization

## Pattern 5: Data Ablation

**When to use**: Testing effect of training data size or composition

**Structure**:
- Different dataset sizes or subsets
- Same model and training config
- Tracks performance vs. data size

**Example**: Data efficiency study

```yaml
matrix:
  data_fraction: [0.1, 0.25, 0.5, 0.75, 1.0]

parameters:
  model_name: roberta-base
  learning_rate: 2e-4
  epochs: 3
```

**Success criteria**: Determine data requirements or efficiency

**Considerations**:
- Use consistent sampling (same seed for reproducibility)
- May need to adjust epochs (more data = fewer epochs)
- Useful for understanding when more data is worth collecting

## Pattern 6: Multi-Task Evaluation

**When to use**: Validating an approach across multiple tasks or datasets

**Structure**:
- Single training configuration
- Multiple evaluation tasks
- Cross-task comparison

**Example**: GLUE benchmark evaluation

```yaml
# Training on single task
parameters:
  train_dataset: mnli

# Evaluation on multiple tasks
evaluation_tasks:
  - mnli
  - sst2
  - qnli
  - qqp
```

**Success criteria**: Approach generalizes across tasks

**Considerations**:
- Each task may have different best hyperparameters
- Consider task-specific vs. shared parameters
- Weight tasks appropriately in success criteria

## Pattern 7: Seed Ensemble / Variance Study

**When to use**: Measuring result stability and variance

**Structure**:
- Multiple random seeds
- Identical configuration otherwise
- Statistical analysis of results

**Example**: Variance measurement

```yaml
matrix:
  seed: [42, 43, 44, 45, 46]  # 5 seeds

parameters:
  model_name: roberta-base
  learning_rate: 2e-4
  # ... other params fixed
```

**Success criteria**: Mean performance + confidence intervals

**Considerations**:
- Minimum 3 seeds, prefer 5+ for good statistics
- Report mean, std dev, min, max
- Compare confidence intervals, not just means
- More expensive (5× the runs)

## Pattern 8: Transfer Learning

**When to use**: Testing model generalization to new domains/tasks

**Structure**:
- Train on source task/domain
- Evaluate on target task/domain
- Compare to baseline trained on target

**Example**: Domain adaptation

```yaml
# Stage 1: Pre-training
parameters:
  train_dataset: source_domain
  epochs: 10

# Stage 2: Fine-tuning
parameters:
  checkpoint: <stage-1-checkpoint>
  train_dataset: target_domain
  epochs: 3
  learning_rate: 1e-5  # Lower LR for fine-tuning
```

**Success criteria**: Transfer outperforms training from scratch

## Pattern 9: Incremental Validation

**When to use**: Building confidence in an approach step-by-step

**Structure**:
- Start with smallest viable test
- Incrementally increase complexity
- Each stage validates before proceeding

**Example**: Scaling up

```yaml
# Stage 1: Smoke test (quick validation)
experiment_id: smoke-test
parameters:
  data_fraction: 0.01
  epochs: 1
  
# Stage 2: Small-scale validation
experiment_id: small-scale
parameters:
  data_fraction: 0.1
  epochs: 3

# Stage 3: Full experiment
experiment_id: full-scale
parameters:
  data_fraction: 1.0
  epochs: 10
```

**Success criteria**: Each stage succeeds before next begins

**Benefits**:
- Catch bugs early (cheap)
- Validate approach before expensive runs
- Iterative refinement

## Pattern 10: Comparative Study

**When to use**: Reproducing and comparing published methods

**Structure**:
- Implement multiple published approaches
- Use consistent evaluation protocol
- Compare to reported results

**Example**: Method comparison

```yaml
# Method 1: Baseline
experiment_id: baseline-method
parameters:
  approach: standard_finetuning

# Method 2: Published Method A
experiment_id: method-a
parameters:
  approach: published_method_a

# Method 3: Published Method B
experiment_id: method-b
parameters:
  approach: published_method_b

# Method 4: Proposed
experiment_id: our-method
parameters:
  approach: proposed_method
```

**Success criteria**: Reproduce published results, proposed method improves

**Considerations**:
- Document any deviations from published setup
- Use same data splits and metrics
- Note hardware differences if applicable

## Planning Checklist

When creating an experiment plan, verify:

### Research Design
- [ ] Clear research question
- [ ] Testable hypothesis
- [ ] Defined baseline
- [ ] Success criteria specified
- [ ] Primary metric identified

### Configuration
- [ ] Variables and controls identified
- [ ] Matrix expansion calculated
- [ ] Agent defaults documented
- [ ] Rationale for choices provided

### Resources
- [ ] GPU hours estimated
- [ ] Memory requirements checked
- [ ] Time limits appropriate
- [ ] Quota compliance verified

### Reproducibility
- [ ] Random seeds specified
- [ ] All hyperparameters documented
- [ ] Data splits defined
- [ ] Evaluation protocol clear

### Tracking
- [ ] W&B group defined
- [ ] Tags appropriate
- [ ] HF push policy set
- [ ] Run naming convention clear

### Risk Assessment
- [ ] Limitations documented
- [ ] Potential failures considered
- [ ] Fallback options identified
- [ ] Expected outcomes described

## Anti-Patterns to Avoid

### ❌ Kitchen Sink Experiment

**Problem**: Testing too many variables at once

```yaml
# DON'T DO THIS
matrix:
  learning_rate: [1e-5, 2e-5, 5e-5]
  batch_size: [4, 8, 16]
  lora_rank: [8, 16, 32]
  dropout: [0.1, 0.2]
# Total: 3 × 3 × 3 × 2 = 54 runs!
```

**Solution**: Break into multiple focused experiments

### ❌ Undefined Success

**Problem**: No clear success criteria

```markdown
# DON'T DO THIS
success_criteria:
  - Model should perform well
  - Results should be interesting
```

**Solution**: Specific, measurable criteria

```markdown
success_criteria:
  minimum_improvement: 0.02  # 2% over baseline
  maximum_training_time: 8 hours per run
```

### ❌ Missing Baseline

**Problem**: No comparison point

**Solution**: Always define baseline (published result, previous experiment, or simple approach)

### ❌ Unfair Comparison

**Problem**: Different evaluation protocols for different methods

**Solution**: Ensure consistent data, metrics, and evaluation splits

### ❌ Single Seed Comparison

**Problem**: Claiming improvement based on single run

**Solution**: Use multiple seeds or acknowledge limitation

### ❌ Undocumented Defaults

**Problem**: Critical parameters not specified

**Solution**: Explicitly list all hyperparameters, even if using defaults

## Templates by Pattern

### Quick Ablation Template

```markdown
## Purpose
Test effect of [parameter] on [task]

## Hypothesis
[Expected outcome]

## Baseline
[Current best configuration and metric]

## Design
- Variable: [parameter values]
- Controls: [fixed parameters]

## Success Criteria
- Minimum improvement: [threshold]
```

### Comparison Template

```markdown
## Purpose
Compare [approach A] vs [approach B] on [task]

## Hypothesis
[Approach A] will outperform [approach B] because [reason]

## Baselines
- Approach A: [description and reported results]
- Approach B: [description and reported results]

## Design
- Same data, same evaluation protocol
- Same hyperparameter tuning budget

## Success Criteria
- [Approach] achieves [threshold] on [metric]
```

### Exploration Template

```markdown
## Purpose
Explore whether [approach] is viable for [task]

## Hypothesis
[Approach] can achieve reasonable performance on [task]

## Baseline
[Simple or published baseline]

## Design
- Start with default hyperparameters
- Incremental complexity: smoke test → small scale → full scale

## Success Criteria
- Smoke test: no errors, completes successfully
- Small scale: within 5% of baseline
- Full scale: matches or exceeds baseline
```
