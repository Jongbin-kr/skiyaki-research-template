# Example: Learning Rate Search Plan

This is an example experiment plan for a learning rate search study.

## File: experiments/lr-search-rank16/plan.md

```markdown
---
schema_version: 1
experiment_id: lr-search-rank16
status: awaiting_approval

primary_metric:
  name: accuracy
  direction: maximize

success_criteria:
  minimum_improvement: 0.01  # 1% improvement over current best

jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml

approval:
  status: pending
  approved_by: null
  approved_at: null
  approved_commit: null
---

# Learning Rate Search with LoRA Rank 16

## Purpose

Find the optimal learning rate for LoRA rank 16 fine-tuning of RoBERTa-base on SST-2, building on previous rank ablation findings.

## Hypothesis

The default learning rate (2e-4) may not be optimal for rank 16. Testing a range around this value will find a better configuration.

## Baseline

- Model: RoBERTa-base with LoRA rank 16
- Dataset: GLUE SST-2
- Current best: accuracy = 0.874 (from experiment `lora-rank-ablation`)
- Learning rate: 2e-4
- Source: experiments/lora-rank-ablation/results.yaml

## Design

### Variables

Test learning rates: [5e-5, 1e-4, 2e-4, 3e-4, 5e-4]

### Controls

- Model: RoBERTa-base
- LoRA rank: 16
- LoRA alpha: 32
- LoRA target modules: query, value
- Dataset: SST-2
- Batch size: 8
- Gradient accumulation: 4 steps
- Training epochs: 3
- Random seed: 42

### Rationale

Testing range from 5e-5 (conservative) to 5e-4 (aggressive) around the current 2e-4. Range covers typical LoRA fine-tuning rates.

## Agent-Determined Defaults

- **Learning rate range: [5e-5, 5e-4]** - Standard search range for transformer fine-tuning
- **Fixed rank at 16** - Based on previous ablation showing this as optimal
- **Same batch config as baseline** - Isolates learning rate effect
- **3 epochs** - Consistent with baseline for fair comparison

## Risks and Limitations

- Limited to 5 learning rate values (full sweep would be expensive)
- No learning rate scheduling (constant rate only)
- Single random seed (results may vary)
- No warmup tuning (using default 0 steps)

## Expected Outcomes

### If Hypothesis Supported

A learning rate other than 2e-4 will improve accuracy by ≥1%. This would suggest:
- Update default learning rate for future experiments
- Next: Test learning rate schedule (linear, cosine decay)
- Next: Validate improved LR across other GLUE tasks

### If Hypothesis Refuted

If 2e-4 remains optimal or differences are <1%, would suggest:
- Current learning rate is well-tuned
- Next: Investigate other hyperparameters (warmup, weight decay)
- Next: Focus on architecture changes rather than optimization
```

## File: experiments/lr-search-rank16/jobs/train.yaml

```yaml
# Training Job Configuration

job_id: train-lr-search
type: train

# Execution
entrypoint: src/train_lora.py
config_style: argument

# Hyperparameter matrix (search)
matrix:
  learning_rate: [5.0e-5, 1.0e-4, 2.0e-4, 3.0e-4, 5.0e-4]

# Parameters passed to entrypoint
parameters:
  model_name: roberta-base
  dataset_name: glue
  dataset_config: sst2
  dataset_split: train
  num_epochs: 3
  batch_size: 8
  gradient_accumulation_steps: 4
  seed: 42
  
  # LoRA parameters (fixed from previous experiment)
  lora_rank: 16
  lora_alpha: 32
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
  group: lr-search-rank16
  tags:
    - learning-rate
    - hyperparameter-search
    - lora-rank-16

# Hugging Face Hub
huggingface:
  push: final_only
  repo: null
```

## File: experiments/lr-search-rank16/jobs/evaluate.yaml

```yaml
# Evaluation Job Configuration

job_id: eval-lr-search
type: evaluate

# Execution
entrypoint: src/evaluate.py
config_style: argument

# Parameters
parameters:
  checkpoint: null  # Filled at runtime
  dataset_name: glue
  dataset_config: sst2
  dataset_split: test
  batch_size: 16
  
  metrics:
    - accuracy
    - f1

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
  group: lr-search-rank16
  tags:
    - evaluation
```

## Approval Summary

**Experiment**: Learning Rate Search with LoRA Rank 16

**Objective**: Find optimal learning rate for rank 16 LoRA fine-tuning

**Hypothesis**: A learning rate other than 2e-4 will improve accuracy

**Primary Metric**: Accuracy (maximize)

**Success Criteria**: ≥1% improvement over current best (0.874)

**Baseline**: Best result from lora-rank-ablation (0.874 accuracy with LR=2e-4)

**Design**: 5 training runs testing LRs [5e-5, 1e-4, 2e-4, 3e-4, 5e-4] with rank 16 fixed

**Agent Recommendations**:
- LR range covers typical fine-tuning values
- All other hyperparameters match baseline for fair comparison
- Fixed rank at 16 based on previous findings

**Resources**:
- 5 training runs × 1 GPU × 8 hours = 40 GPU-hours
- 5 evaluation runs × 1 GPU × 2 hours = 10 GPU-hours
- Total: 50 GPU-hours estimated

**Execution**: Requires Slurm (GPU jobs)

**Tracking**:
- W&B group: `lr-search-rank16`
- HF uploads: final checkpoint only

**Dependencies**: Builds on `lora-rank-ablation` results

**Files Created**:
- Plan: `experiments/lr-search-rank16/plan.md`
- Training config: `experiments/lr-search-rank16/jobs/train.yaml`
- Evaluation config: `experiments/lr-search-rank16/jobs/evaluate.yaml`

**Ready for approval**. Reply "approved" to proceed with execution.
