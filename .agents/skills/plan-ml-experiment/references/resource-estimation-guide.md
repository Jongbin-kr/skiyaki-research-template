# Resource Estimation Guide

This guide helps estimate GPU hours, memory requirements, and execution time for ML experiments.

## GPU Hour Estimation

### Training Time Formula

```
GPU-hours = (dataset_size / effective_batch_size) × epochs × time_per_step × num_runs
```

**Components**:
- `dataset_size`: Number of training examples
- `effective_batch_size`: batch_size × gradient_accumulation_steps × num_gpus
- `epochs`: Number of training epochs
- `time_per_step`: Seconds per training step (model/hardware dependent)
- `num_runs`: Number of ablation runs (matrix expansion)

### Typical Training Times (per step)

**Small Models** (BERT-base, RoBERTa-base, 110M params):
- Single GPU (A100): 0.3-0.5 seconds/step
- Single GPU (V100): 0.5-0.8 seconds/step
- Single GPU (RTX 3090): 0.6-1.0 seconds/step

**Medium Models** (BERT-large, RoBERTa-large, 330M params):
- Single GPU (A100): 0.8-1.2 seconds/step
- Single GPU (V100): 1.5-2.5 seconds/step
- 2× A100: 0.5-0.8 seconds/step

**Large Models** (GPT-2 1.5B, 1.5B params):
- Single GPU (A100): 3-5 seconds/step
- 4× A100: 1-1.5 seconds/step
- 8× A100: 0.6-1.0 seconds/step

**Parameter-Efficient Methods** (LoRA, Adapters):
- Training time: 90-95% of full fine-tuning
- Memory usage: 30-50% of full fine-tuning
- Can fit larger models on same hardware

### Example Calculations

#### Example 1: Small Model, Single Dataset

**Setup**:
- Model: RoBERTa-base (110M params)
- Dataset: SST-2 (67k examples)
- Batch size: 8, accumulation: 4 (effective: 32)
- Epochs: 3
- Hardware: Single A100
- Matrix: 4 ablation runs

**Calculation**:
```
steps_per_epoch = 67,000 / 32 = 2,094 steps
total_steps = 2,094 × 3 epochs = 6,282 steps
time_per_step = 0.4 seconds

time_per_run = 6,282 × 0.4 / 3600 = 0.70 hours
total_time = 0.70 × 4 runs = 2.8 GPU-hours

# Add 20% buffer for initialization, checkpointing, evaluation
estimated_total = 2.8 × 1.2 = 3.4 GPU-hours
```

**Resource Request**: `time: "04:00:00"` (4 hours, with buffer)

#### Example 2: Medium Model, Large Dataset

**Setup**:
- Model: BERT-large (330M params)
- Dataset: SQuAD (88k examples)
- Batch size: 4, accumulation: 8 (effective: 32)
- Epochs: 2
- Hardware: 2× A100
- Matrix: Single run

**Calculation**:
```
steps_per_epoch = 88,000 / 32 = 2,750 steps
total_steps = 2,750 × 2 epochs = 5,500 steps
time_per_step = 0.6 seconds (2× GPU speedup)

time_per_run = 5,500 × 0.6 / 3600 = 0.92 hours
total_time = 0.92 GPU-hours (per GPU)
aggregate_time = 0.92 × 2 GPUs = 1.84 GPU-hours

# Add 20% buffer
estimated_total = 1.84 × 1.2 = 2.2 GPU-hours
wall_time = 1.1 hours (per GPU)
```

**Resource Request**: `time: "02:00:00"`, `gpus: 2`

## Memory Estimation

### Training Memory Formula

```
memory_required = model_memory + optimizer_memory + activation_memory + batch_memory
```

**Components**:
- `model_memory`: Model parameters in RAM
- `optimizer_memory`: Optimizer states (typically 2× model for Adam)
- `activation_memory`: Forward pass activations
- `batch_memory`: Current batch data

### Model Memory by Size

**Parameters to Memory (FP32)**:
- 110M params (BERT-base): ~0.44 GB
- 330M params (BERT-large): ~1.3 GB
- 1.5B params (GPT-2-XL): ~6 GB
- 7B params (Llama-2-7B): ~28 GB

**Total Training Memory (FP32, Adam)**:
- BERT-base: ~4-6 GB (model + optimizer + activations)
- BERT-large: ~10-16 GB
- GPT-2-XL: ~40-60 GB
- Llama-2-7B: ~150-200 GB

**With Mixed Precision (FP16/BF16)**:
- Reduces memory by ~40-50%
- BERT-base: ~2-3 GB
- BERT-large: ~6-8 GB
- GPT-2-XL: ~24-32 GB

**With LoRA/PEFT**:
- Reduces memory by ~50-70% vs full fine-tuning
- BERT-base with LoRA: ~1-2 GB
- BERT-large with LoRA: ~4-6 GB
- GPT-2-XL with LoRA: ~12-20 GB

### Memory Safety Rules

1. **Always add 20-30% buffer** for framework overhead
2. **Sequence length matters**: Memory scales with `batch_size × seq_length²`
3. **Gradient accumulation**: Trades memory for time (smaller batches, more steps)
4. **Activation checkpointing**: Reduces memory ~30% at cost of 20% slower training

### Example Memory Requests

#### Small Model
```yaml
resources:
  gpus: 1
  memory_gb: 16  # Comfortable for BERT-base with mixed precision
```

#### Medium Model
```yaml
resources:
  gpus: 1
  memory_gb: 32  # BERT-large full fine-tuning with mixed precision
```

#### Large Model
```yaml
resources:
  gpus: 4
  memory_gb: 80  # GPT-2-XL with LoRA, split across GPUs
```

## Evaluation Time Estimation

Evaluation is typically **much faster** than training:

- No backward pass (50% time savings)
- No optimizer updates
- Can use larger batch sizes (memory not needed for gradients)
- Single pass through data

**Rule of Thumb**: Evaluation takes 5-10% of training time

### Example Evaluation Times

**SST-2 Test Set** (1,821 examples):
- Batch size: 32
- Steps: 57
- Time per step: 0.1 seconds
- Total: 6 seconds

**SQuAD Dev Set** (10,570 examples):
- Batch size: 16
- Steps: 661
- Time per step: 0.2 seconds
- Total: 2.2 minutes

**Typical Evaluation Time Request**: `time: "01:00:00"` or `time: "02:00:00"`

## Resource Request Guidelines

### Time Limits

**Conservative Approach**:
```
requested_time = estimated_time × 1.5
```

**Why add buffer?**:
- Node startup time (1-5 minutes)
- Environment setup time
- Checkpoint saving time
- Data loading variability
- Preemption recovery

**Slurm Best Practices**:
- Shorter jobs get scheduled faster
- Jobs near partition limits wait longer
- Request minimum viable time
- Use checkpointing for long runs

### GPU Selection

**A100 (80GB)**:
- Best: Large models, high throughput
- Cost: Highest
- Availability: Often limited

**V100 (32GB)**:
- Best: Medium models, good balance
- Cost: Medium
- Availability: Good

**RTX 3090 (24GB)**:
- Best: Small-medium models, cost-effective
- Cost: Lower
- Availability: Varies

### CPU and Memory

**CPU Cores**:
- Rule: 4-8 CPUs per GPU
- Used for: Data loading, preprocessing
- More CPUs → faster data loading → better GPU utilization

**System Memory**:
- Rule: 4-8× GPU memory
- Example: 1× A100 80GB → request 256-512GB RAM
- Used for: Dataset caching, preprocessing

## Common Ablation Patterns

### Grid Search (2 variables)

```yaml
matrix:
  learning_rate: [1e-5, 2e-5, 5e-5]
  batch_size: [8, 16]
```

**Total runs**: 3 × 2 = 6 runs

**Resource calculation**:
```
estimated_per_run = 4 hours
total_gpu_hours = 6 × 4 = 24 GPU-hours
```

### Rank Ablation

```yaml
matrix:
  lora_rank: [4, 8, 16, 32]
```

**Total runs**: 4 runs

**Note**: Different ranks have slightly different memory/time, but usually negligible

### Seed Ensemble

```yaml
matrix:
  seed: [42, 43, 44]
```

**Total runs**: 3 runs

**Purpose**: Measure result variance

## Slurm Requirements

### When Slurm is Required

Per AGENTS.md rules:

1. **Always required for GPU jobs**: Any job requesting GPUs must use Slurm
2. **Required for CPU-heavy jobs**: Jobs exceeding `direct_cpu_max_minutes` (typically 10 minutes)

### When Direct Execution is Allowed

- Quick CPU tests (<10 minutes)
- Data preprocessing scripts
- Evaluation on small datasets (<1000 examples)
- Smoke tests

### Slurm Configuration Example

```yaml
resources:
  backend: slurm
  partition: gpu       # From project-plan.md
  account: my-account  # From project-plan.md
  qos: normal         # From project-plan.md
  gpus: 2
  cpus: 16
  memory_gb: 128
  time: "12:00:00"
```

## Quota Checking

Before approving experiments, check against project quotas in `project-plan.md`:

```yaml
slurm:
  max_gpus_per_job: 4
  max_concurrent_jobs: 8
  max_gpu_hours_per_week: 200  # Example project limit
```

**Validation**:
1. Requested GPUs ≤ `max_gpus_per_job`
2. Matrix expansion ≤ `max_concurrent_jobs` if submitted as array
3. Estimated GPU-hours ≤ remaining weekly quota

**If quota exceeded**:
- Suggest reducing matrix size
- Suggest splitting into multiple experiments
- Suggest increasing time estimates to reduce concurrent jobs

## Summary Checklist

When creating resource requests:

- [ ] Calculated estimated time using dataset size and model size
- [ ] Added 20-50% buffer for overhead
- [ ] Checked memory requirements match GPU type
- [ ] Verified Slurm is used for GPU jobs
- [ ] Requested appropriate CPU count (4-8 per GPU)
- [ ] Validated against project quotas
- [ ] Documented estimation rationale in plan.md
