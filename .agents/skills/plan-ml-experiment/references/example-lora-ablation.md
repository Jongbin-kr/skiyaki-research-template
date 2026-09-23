# Example: LoRA Rank Ablation Plan

This is an example experiment plan for a LoRA rank ablation study.

## File: experiments/lora-rank-ablation/plan.md

```markdown
---
schema_version: 1
experiment_id: lora-rank-ablation
status: awaiting_approval

primary_metric:
  name: accuracy
  direction: maximize

success_criteria:
  minimum_improvement: 0.02  # 2% improvement over baseline

jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml

approval:
  status: pending
  approved_by: null
  approved_at: null
  approved_commit: null
---

# LoRA Rank Ablation Study

## Purpose

Determine the optimal LoRA rank for fine-tuning RoBERTa-base on SST-2 sentiment classification, balancing accuracy and memory efficiency.

## Hypothesis

LoRA ranks 16 and above will saturate performance gains, with diminishing returns for higher ranks. Rank 16 will provide the best accuracy/efficiency tradeoff.

## Baseline

- Model: RoBERTa-base (pre-trained, no fine-tuning)
- Dataset: GLUE SST-2 (67k train, 872 validation, 1821 test)
- Metrics: accuracy = 0.853, F1 = 0.851
- Source: Published RoBERTa paper baseline

## Design

### Variables

Test LoRA rank values: [4, 8, 16, 32]

### Controls

- Model architecture: RoBERTa-base
- Dataset: SST-2
- Learning rate: 2e-4
- Batch size: 8
- Gradient accumulation: 4 steps
- Training epochs: 3
- Random seed: 42
- LoRA alpha: 2 × rank (standard scaling)
- LoRA target modules: query and value projections

### Rationale

Testing powers of 2 for rank provides clear comparison points. Range [4, 32] covers practical deployment scenarios from extremely constrained (rank 4) to high-capacity (rank 32).

## Agent-Determined Defaults

- **Learning rate: 2e-4** - Standard for LoRA fine-tuning, proven effective across multiple tasks
- **Batch size: 8 with 4× accumulation** - Effective batch size of 32, balances memory and convergence
- **3 epochs** - Typical for GLUE tasks; more epochs risk overfitting on small datasets
- **LoRA alpha scaling: 2 × rank** - Standard practice maintains consistent effective learning rates
- **Target modules: query and value** - Most commonly fine-tuned attention components

## Risks and Limitations

- Single dataset (SST-2) may not generalize findings to other tasks
- Single model architecture (RoBERTa-base) may have different optimal ranks than larger/smaller models
- Fixed learning rate may not be optimal for all rank values
- No interaction testing with other hyperparameters
- No inference latency measurement (accuracy focus only)

## Expected Outcomes

### If Hypothesis Supported

Rank 16 will show strong performance with acceptable memory usage. Higher ranks (32) will show minimal improvement (<1%). This would suggest:
- Use rank 16 for production deployments
- Next: Test learning rate variations with rank 16
- Next: Validate rank 16 across other GLUE tasks

### If Hypothesis Refuted

If rank 32 shows significant improvement (>2% over rank 16), would suggest:
- Model benefits from higher capacity
- Next: Test even higher ranks (64, 128)
- Next: Investigate why baseline needed more parameters

If rank 4 performs nearly as well as rank 16, would suggest:
- Task is simpler than anticipated
- Next: Investigate why low rank suffices
- Next: Test on harder tasks
```

## File: experiments/lora-rank-ablation/jobs/train.yaml

```yaml
# Training Job Configuration

job_id: train-lora-rank
type: train

# Execution
entrypoint: src/train_lora.py
config_style: argument

# Hyperparameter matrix (ablation)
matrix:
  lora_rank: [4, 8, 16, 32]

# Parameters passed to entrypoint
parameters:
  model_name: roberta-base
  dataset_name: glue
  dataset_config: sst2
  dataset_split: train
  learning_rate: 2.0e-4
  num_epochs: 3
  batch_size: 8
  gradient_accumulation_steps: 4
  seed: 42
  
  # LoRA parameters
  lora_alpha: null  # Set to 2 × lora_rank
  lora_dropout: 0.1
  lora_target_modules: ["query", "value"]

# Resource requirements
resources:
  backend: slurm
  gpus: 1
  cpus: 8
  memory_gb: 32
  time: "08:00:00"

# Weights & Biases tracking
wandb:
  enabled: true
  group: lora-rank-ablation
  tags:
    - lora
    - ablation
    - roberta
    - sst2

# Hugging Face Hub
huggingface:
  push: milestone
  repo: null  # Auto-determined from project-plan.md
```

## File: experiments/lora-rank-ablation/jobs/evaluate.yaml

```yaml
# Evaluation Job Configuration

job_id: eval-lora-rank
type: evaluate

# Execution
entrypoint: src/evaluate.py
config_style: argument

# Parameters
parameters:
  checkpoint: null  # Filled at runtime from best training run
  dataset_name: glue
  dataset_config: sst2
  dataset_split: test
  batch_size: 16
  
  # Metrics to compute
  metrics:
    - accuracy
    - f1
    - precision
    - recall

# Resources
resources:
  backend: slurm
  gpus: 1
  cpus: 4
  memory_gb: 16
  time: "02:00:00"

# Tracking
wandb:
  enabled: true
  group: lora-rank-ablation
  tags:
    - evaluation
```

## Approval Summary

**Experiment**: LoRA Rank Ablation Study

**Objective**: Determine optimal LoRA rank for RoBERTa-base on SST-2

**Hypothesis**: Rank 16 will provide best accuracy/efficiency tradeoff

**Primary Metric**: Accuracy (maximize)

**Success Criteria**: ≥2% improvement over baseline (0.853)

**Baseline**: RoBERTa-base published results (0.853 accuracy)

**Design**: 4 training runs testing ranks [4, 8, 16, 32] with fixed hyperparameters

**Agent Recommendations**:
- Learning rate: 2e-4 (standard for LoRA)
- Batch size: 8 with 4× accumulation (effective batch 32)
- Epochs: 3 (standard for GLUE)
- LoRA alpha: 2 × rank (standard scaling)

**Resources**:
- 4 training runs × 1 GPU × 8 hours = 32 GPU-hours
- 4 evaluation runs × 1 GPU × 2 hours = 8 GPU-hours
- Total: 40 GPU-hours estimated

**Execution**: Requires Slurm (GPU jobs)

**Tracking**:
- W&B group: `lora-rank-ablation`
- HF uploads: milestone checkpoints only

**Files Created**:
- Plan: `experiments/lora-rank-ablation/plan.md`
- Training config: `experiments/lora-rank-ablation/jobs/train.yaml`
- Evaluation config: `experiments/lora-rank-ablation/jobs/evaluate.yaml`

**Ready for approval**. Reply "approved" to proceed with execution.
