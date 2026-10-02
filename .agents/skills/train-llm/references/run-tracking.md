# Run Tracking Reference

## Overview

This document defines the run tracking system for ML training and evaluation jobs. A **Run** represents a single execution of a job configuration, tracked from initialization through completion with structured metadata.

The run tracking system provides:
- Unique identification for every execution
- State transition tracking from initialization to completion
- Standardized directory structure for logs and artifacts
- Machine-readable metadata for analysis and comparison

## Run ID Format

### Structure

```
{type}-{job_id}__{YYYYMMDDTHHMMSS}
```

### Components

- **type**: Job type from job configuration (`train`, `evaluate`, or `custom`)
- **job_id**: Job identifier from job configuration (must be kebab-case)
- **timestamp**: Execution timestamp in ISO 8601 basic format
  - `YYYY`: 4-digit year
  - `MM`: 2-digit month (01-12)
  - `DD`: 2-digit day (01-31)
  - `T`: Literal separator character
  - `HH`: 2-digit hour (00-23)
  - `MM`: 2-digit minute (00-59)
  - `SS`: 2-digit second (00-59)

### Examples

```
train-baseline__20250115T142530
train-lora-r16__20250115T143022
evaluate-test-set__20250115T150145
custom-data-prep__20250115T151200
```

### Properties

- **Uniqueness**: Timestamp precision to the second ensures uniqueness for manual runs
- **Sortability**: Lexicographic sort orders runs chronologically
- **Readability**: Human-readable components aid navigation and debugging
- **Parseability**: Consistent format enables automated extraction of metadata

### Collision Handling

If multiple runs start within the same second (rare in interactive use):
- Append suffix: `{run_id}-{counter}` (e.g., `train-baseline__20250115T142530-2`)
- Counter starts at 2 for readability
- Initialize_run.py detects collisions and auto-increments

## Run Status Transitions

### Status Values

| Status | Meaning |
|--------|---------|
| `initialized` | Run directory created, ready to execute |
| `running` | Job currently executing |
| `completed` | Job finished successfully |
| `failed` | Job terminated with error |

### State Diagram

```
initialized ──────> running ──────> completed
                      │
                      └────────────> failed
```

### Status Transitions

#### initialized → running
- **Trigger**: Job execution starts
- **Metadata Updated**: `started_at` timestamp written
- **Files Created**: `logs/` subdirectory populated

#### running → completed
- **Trigger**: Job exits with code 0
- **Metadata Updated**: 
  - `completed_at` timestamp written
  - `exit_code` set to 0
  - `metrics` populated from job output (if available)
  - `checkpoint_path` written (if applicable)
  - `wandb_run_id` written (if W&B enabled)
- **Files Finalized**: Logs closed, checkpoints saved

#### running → failed
- **Trigger**: Job exits with non-zero code or crashes
- **Metadata Updated**:
  - `completed_at` timestamp written
  - `exit_code` set to actual exit code
  - `error_summary` written with failure reason
- **Files Finalized**: Error logs captured, partial artifacts preserved

### Status Field Rules

- Status MUST be one of the four defined values
- Transitions MUST follow the state diagram (no backward transitions)
- Each transition MUST update appropriate timestamp fields
- Failed runs MUST preserve logs and partial outputs for debugging

## Run Directory Structure

### Standard Layout

```
experiments/{experiment-id}/runs/{run-id}/
├── run.yaml                    # Run metadata (required)
├── resolved-job.yaml           # Job configuration with resolved matrix (required)
├── logs/                       # Execution logs (required)
│   ├── train.log              # Primary job output
│   ├── stderr.log             # Error stream capture
│   └── slurm-{job-id}.out     # Slurm output (if applicable)
└── checkpoints/               # Model checkpoints (optional)
    ├── checkpoint-1000/
    ├── checkpoint-2000/
    └── final/
```

### Directory Components

#### run.yaml
- **Purpose**: Central metadata file tracking run lifecycle
- **Format**: YAML (see schema below)
- **Updates**: Modified during state transitions
- **Required**: Yes, created during initialization

#### resolved-job.yaml
- **Purpose**: Snapshot of actual job configuration used for this run
- **Format**: YAML matching job configuration schema
- **Matrix Resolution**: If source job has matrix, this file contains the specific parameter combination for this run
- **Required**: Yes, created during initialization
- **Immutable**: Written once, never modified

#### logs/
- **Purpose**: Capture all execution output for debugging and analysis
- **Contents**:
  - `train.log`: Merged stdout/stderr from job entrypoint
  - `stderr.log`: Isolated stderr for error analysis
  - `slurm-{job-id}.out`: Slurm job output (Phase 6+)
- **Retention**: Preserved locally — kept indefinitely for failed runs, may be compressed for completed runs
- **Version control**: These logs stay local and are excluded from Git by default. Never commit logs from failed/errored runs; record the exit status and a concise error summary in `run.yaml` and `history.md` instead. A small curated excerpt from a successful run may be committed as evidence after a secret/path check.
- **Required**: Yes, directory created during initialization

#### checkpoints/
- **Purpose**: Store model checkpoints saved during training
- **Structure**: Subdirectories per checkpoint (e.g., `checkpoint-1000/`, `final/`)
- **Management**: Created by training script, not by run tracking system
- **Required**: No, only for training runs that save checkpoints
- **Git Handling**: Never committed (large binary files)

### Path References

All paths in run.yaml SHOULD be absolute or relative to workspace root:
- Absolute: `/Users/researcher/project/experiments/exp1/runs/run1/logs/train.log`
- Workspace-relative: `experiments/exp1/runs/run1/logs/train.log`

Relative paths enable repository portability across machines.

## run.yaml Schema

### Required Fields

```yaml
run_id: string                  # Unique run identifier (format: {type}-{job_id}__{timestamp})
job_file: string                # Path to source job configuration file
experiment_id: string           # Parent experiment identifier
status: string                  # Current run status (initialized|running|completed|failed)
created_at: string              # ISO 8601 timestamp of initialization
```

### Optional Fields

```yaml
started_at: string              # ISO 8601 timestamp when execution began
completed_at: string            # ISO 8601 timestamp when execution finished
exit_code: integer              # Process exit code (0 = success, >0 = failure)
error_summary: string           # Brief error description for failed runs
metrics: dict                   # Key-value pairs of evaluation metrics
  {metric_name}: float
wandb_run_id: string            # Weights & Biases run identifier (if enabled)
wandb_url: string               # Direct URL to W&B run dashboard
checkpoint_path: string         # Path to best/final checkpoint
huggingface_repo: string        # HF Hub repository if checkpoint pushed
command: string                 # Actual command executed (for reproducibility)
environment: dict               # Environment details
  python_version: string
  cuda_version: string
  conda_env: string
notes: string                   # Free-form notes added by agent or user
```

### Complete Example

```yaml
run_id: train-lora-r16__20250115T142530
job_file: experiments/lora-ablation/jobs/train.yaml
experiment_id: lora-ablation
status: completed
created_at: 2025-01-15T14:25:30Z
started_at: 2025-01-15T14:25:45Z
completed_at: 2025-01-15T15:42:18Z
exit_code: 0
metrics:
  train_loss: 0.234
  eval_loss: 0.456
  eval_accuracy: 0.892
  train_runtime: 4593.21
wandb_run_id: abc123def456
wandb_url: https://wandb.ai/username/project/runs/abc123def456
checkpoint_path: experiments/lora-ablation/runs/train-lora-r16__20250115T142530/checkpoints/final
command: python src/train.py --config experiments/lora-ablation/jobs/train.yaml --lora-rank 16
environment:
  python_version: "3.10.12"
  cuda_version: "11.8"
  conda_env: ml-research
notes: Baseline training run for LoRA rank ablation study
```

### Field Validation Rules

- `run_id` MUST match format `{type}-{job_id}__{YYYYMMDDTHHMMSS}`
- `status` MUST be one of: `initialized`, `running`, `completed`, `failed`
- All timestamp fields MUST be valid ISO 8601 format
- `exit_code` MUST be non-negative integer
- `metrics` values MUST be numeric (int or float)
- `checkpoint_path` MUST exist if status is `completed` and job type is `train`

## Tracking Workflow

### 1. Run Initialization

**Triggered By**: Agent about to execute a job

**Operations**:
1. Generate run ID from job metadata and current timestamp
2. Create run directory: `experiments/{experiment-id}/runs/{run-id}/`
3. Create logs subdirectory: `runs/{run-id}/logs/`
4. Write initial `run.yaml` with status `initialized`
5. Copy job configuration to `resolved-job.yaml`
6. Return run metadata to agent

**Script**: `initialize_run.py` (see execution-policy.md)

### 2. Job Execution

**Triggered By**: Agent with initialized run

**Operations**:
1. Update `run.yaml` status to `running`
2. Record `started_at` timestamp
3. Execute job with output redirected to `logs/train.log`
4. Monitor execution progress
5. Capture metrics from job output

**Responsibility**: SKILL.md workflow (train-llm or evaluate-llm)

### 3. Run Completion

**Triggered By**: Job process exits

**Operations**:
1. Capture exit code
2. Update `run.yaml` status to `completed` or `failed`
3. Record `completed_at` timestamp
4. Extract metrics from output (if successful)
5. Record checkpoint location (if applicable)
6. Close log files

**Responsibility**: SKILL.md workflow

### 4. Result Analysis

**Triggered By**: evaluate-llm skill

**Operations**:
1. Read `run.yaml` files for all runs in experiment
2. Compare metrics across runs
3. Identify best run by primary metric
4. Generate `results.yaml` summary

**Reference**: evaluate-llm/references/result-schema.md

## Matrix Run Handling

When a job configuration includes a matrix for ablation studies, each matrix combination generates a separate run.

### Matrix in Source Job

```yaml
job_id: lora-ablation
type: train
matrix:
  lora_rank: [4, 8, 16, 32]
  learning_rate: [1e-4, 5e-4]
# ... other config
```

### Generated Runs

```
train-lora-ablation__20250115T142530    # lora_rank=4, lr=1e-4
train-lora-ablation__20250115T142531    # lora_rank=4, lr=5e-4
train-lora-ablation__20250115T142532    # lora_rank=8, lr=1e-4
train-lora-ablation__20250115T142533    # lora_rank=8, lr=5e-4
train-lora-ablation__20250115T142534    # lora_rank=16, lr=1e-4
train-lora-ablation__20250115T142535    # lora_rank=16, lr=5e-4
train-lora-ablation__20250115T142536    # lora_rank=32, lr=1e-4
train-lora-ablation__20250115T142537    # lora_rank=32, lr=5e-4
```

### resolved-job.yaml Contents

Each run's `resolved-job.yaml` contains the specific parameter combination:

```yaml
job_id: lora-ablation
type: train
# Matrix removed, replaced with resolved values:
parameters:
  lora_rank: 16
  learning_rate: 0.0001
  # ... other parameters
```

This enables exact reproducibility: re-running from `resolved-job.yaml` produces identical configuration.

## Metadata Queries

Common queries agents perform on run metadata:

### Find All Runs for Experiment

```bash
ls experiments/{experiment-id}/runs/
```

Returns list of run IDs.

### Get Run Status

```bash
grep "^status:" experiments/{experiment-id}/runs/{run-id}/run.yaml
```

### Find Completed Runs

```bash
grep -l "status: completed" experiments/{experiment-id}/runs/*/run.yaml
```

### Extract Metrics from Run

```bash
grep -A 10 "^metrics:" experiments/{experiment-id}/runs/{run-id}/run.yaml
```

Agents use `read_file` tool to parse full YAML for structured access.

### Compare Runs by Metric

1. Read all `run.yaml` files in experiment
2. Parse `metrics` section
3. Sort by target metric
4. Report best run

(Implemented in evaluate-llm skill)

## Error Recovery

### Orphaned Runs

**Symptom**: Run directory exists with status `initialized` or `running` but no active process

**Detection**: Check for runs with `started_at` timestamp >24 hours ago and status not `completed`/`failed`

**Resolution**: Agent marks as `failed` with `error_summary: "Process terminated unexpectedly"`

### Incomplete Metadata

**Symptom**: `run.yaml` missing required fields

**Detection**: Schema validation fails when reading run metadata

**Resolution**: Agent attempts to reconstruct from available data (logs, job file), marks run as suspect

### Corrupted Logs

**Symptom**: Log files truncated or unreadable

**Detection**: File exists but cannot be parsed or is empty

**Resolution**: Preserve corrupted file with `.corrupted` suffix, note in run metadata

## Phase-Specific Behavior

### Phase 2: Local Execution

- Runs execute in foreground or background on local machine
- No Slurm integration (Slurm fields in metadata reserved for future)
- W&B tracking configured but API integration deferred
- Checkpoint paths reference local filesystem

### Phase 6: SSH/Slurm Integration (Future)

- Run initialization occurs locally, execution on remote cluster
- Additional metadata: `slurm_job_id`, `partition`, `node_list`
- Logs fetched from cluster after completion
- Run status polling via Slurm commands

### Phase 7: W&B Integration (Future)

- `wandb_run_id` populated during initialization
- Metrics synced bidirectionally (job → W&B, W&B → run.yaml)
- Failure detection via W&B API

### Phase 8: HF Hub Integration (Future)

- `huggingface_repo` field populated on checkpoint push
- Model card generation includes run metadata
- Checkpoint tracking via HF Hub API

## Best Practices

### For Agents

1. **Always initialize before execution**: Call `initialize_run.py` before running job
2. **Update status atomically**: Write complete `run.yaml` in single operation
3. **Preserve failed runs**: Never delete run directories, even on failure
4. **Record commands**: Store actual executed command for reproducibility
5. **Validate before analysis**: Check run status before trusting metrics

### For Users

1. **Don't manually edit run.yaml**: Let agents manage metadata
2. **Preserve directory structure**: Don't reorganize runs/ directory
3. **Compress old logs**: Large log files can be gzipped to save space
4. **Backup before cleanup**: Archive run directories before deletion
5. **Use run IDs in notes**: Reference specific runs in journal.md and history.md

## Related Documentation

- **execution-policy.md**: Job execution requirements and environment detection
- **evaluate-llm/result-schema.md**: How run metadata feeds into results.yaml
- **plan-ml-experiment/plan-schema.md**: Experiment plan references to jobs and runs
- **finalize-experiment/completion-checklist.md**: Verifying run completeness before Git commit

## Appendix: JSON Schema for Validation

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Run Metadata",
  "type": "object",
  "required": ["run_id", "job_file", "experiment_id", "status", "created_at"],
  "properties": {
    "run_id": {
      "type": "string",
      "pattern": "^(train|evaluate|custom)-[a-z0-9-]+__[0-9]{8}T[0-9]{6}(-[0-9]+)?$"
    },
    "job_file": {
      "type": "string"
    },
    "experiment_id": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$"
    },
    "status": {
      "type": "string",
      "enum": ["initialized", "running", "completed", "failed"]
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "started_at": {
      "type": "string",
      "format": "date-time"
    },
    "completed_at": {
      "type": "string",
      "format": "date-time"
    },
    "exit_code": {
      "type": "integer",
      "minimum": 0
    },
    "error_summary": {
      "type": "string"
    },
    "metrics": {
      "type": "object",
      "additionalProperties": {
        "type": "number"
      }
    },
    "wandb_run_id": {
      "type": "string"
    },
    "wandb_url": {
      "type": "string",
      "format": "uri"
    },
    "checkpoint_path": {
      "type": "string"
    },
    "huggingface_repo": {
      "type": "string"
    },
    "command": {
      "type": "string"
    },
    "environment": {
      "type": "object",
      "properties": {
        "python_version": {"type": "string"},
        "cuda_version": {"type": "string"},
        "conda_env": {"type": "string"}
      }
    },
    "notes": {
      "type": "string"
    }
  }
}
```
