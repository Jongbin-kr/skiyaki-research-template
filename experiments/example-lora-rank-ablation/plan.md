---
schema_version: 1
experiment_id: example-lora-rank-ablation
status: completed

primary_metric:
  name: accuracy
  direction: maximize

success_criteria:
  minimum_improvement: 0.02  # 2% improvement over baseline

jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml

approval:
  status: approved
  approved_by: researcher
  approved_at: 2025-01-15T09:30:00Z
  approved_commit: abc123f
---

# LoRA Rank Ablation Study (Example)

> **Note**: This is an example experiment demonstrating the template structure. It shows a realistic research workflow with complete documentation.

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
