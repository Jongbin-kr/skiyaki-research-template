# Train LLM Skill

## Purpose

Execute training jobs with proper environment activation, tracking, and logging.

## Prerequisites

- Experiment plan is approved
- Job YAML exists and is valid
- Project environment is configured (environment.yaml or equivalent)

## Procedure

### 1. Preflight Checks

Before executing any training job, verify:

- **Approval Status**: Check that `approval.status == "approved"` in plan.md
- **Experiment ID**: Verify experiment-id is valid and experiment directory exists
- **Job ID**: Verify job-id is valid and job YAML file exists in jobs/ directory
- **Entrypoint**: Check that entrypoint file exists and is executable
- **Environment**: Check that project environment exists (conda env, venv, etc.)
- **Configuration**: Verify W&B and HF configurations exist in project-plan.md
- **Slurm Requirements**: Check if job requires Slurm (GPU or CPU-heavy)
- **Resources**: Check resource quotas and availability against project-plan.md limits

If any preflight check fails, report the issue to the user and do not proceed.

### 2. Prepare Run

Before execution, set up the run tracking structure:

- **Generate Run ID**: Create unique run ID using format `<job-id>__<timestamp>` where timestamp is `YYYYMMDDTHHMMSS`
- **Create Directory**: Create `runs/<run-id>/` directory in experiment directory
- **Create Logs Directory**: Create `runs/<run-id>/logs/` subdirectory
- **Copy Job Configuration**: Copy job YAML to `runs/<run-id>/resolved-job.yaml`
- **Create Run Record**: Create `runs/<run-id>/run.yaml` with initial state:
  - run_id: `<job-id>__<timestamp>`
  - experiment_id: from plan.md
  - job_id: from job file
  - job_file: path to original job YAML
  - status: "created"
  - started_at: null
  - completed_at: null
  - exit_code: null
  - resolved_config: "resolved-job.yaml"

### 3. Execution (Phase 1: Local Only)

Execute the training job locally:

- **Activate Environment**: Activate project environment using the appropriate command:
  - Conda: `conda activate <env-name>`
  - venv: `source <venv-path>/bin/activate`
  - uv: `uv run` (if using uv)
- **Construct Command**: Build execution command from job entrypoint and parameters
  - Parse parameters from job YAML
  - Convert to appropriate format based on config_style (argument, hydra, json, yaml)
  - Include all hyperparameters and dataset configurations
- **Set Environment Variables**: Configure runtime environment:
  - W&B environment variables (if wandb.enabled == true)
    - WANDB_PROJECT, WANDB_ENTITY, WANDB_RUN_GROUP, WANDB_TAGS
  - Hugging Face environment variables (if huggingface.push != never)
    - HF_TOKEN (from user's environment or .env)
    - Push policy configuration
- **Update Status**: Update run.yaml status to "running" and set started_at timestamp
- **Execute Command**: Run the training command with:
  - stdout/stderr capture to logs directory
  - Real-time output monitoring
  - Process ID tracking
- **Monitor Execution**: Watch for completion or failure

### 4. Track Execution

After execution completes (success or failure):

- **Update Run Record**: Update `runs/<run-id>/run.yaml` with:
  - status: "succeeded", "failed", "cancelled", or "timed_out"
  - completed_at: timestamp
  - exit_code: process exit code
- **Save Logs**: Save captured stdout/stderr to `runs/<run-id>/logs/`:
  - stdout.log
  - stderr.log
- **Extract W&B URL** (if enabled): Parse W&B run URL from logs and add to run.yaml:
  - wandb.run_id
  - wandb.url
  - wandb.sync_status

### 5. Update History

After execution completes, record the attempt in history.md:

- **Append Entry**: Add new entry to experiment's history.md with:
  - Timestamp in format `[YYYY-MM-DD HH:MM]`
  - Event description: "Training Run Started" or "Training Run Succeeded/Failed"
  - Run ID
  - Job reference
  - Status
  - Duration (if completed)
  - W&B run URL (if available)
  - Key observations (if any)

Example entry format:
```markdown
## 2025-01-15 08:00 — Training Run Started

- Run ID: train-baseline__20250115T080000
- Job: jobs/train.yaml
- Resources: 1 GPU, 8 CPUs, 32GB RAM
- Status: running

## 2025-01-15 12:30 — Training Run Succeeded

- Run ID: train-baseline__20250115T080000
- Status: succeeded
- Duration: 4.5 hours
- Exit code: 0
- W&B: https://wandb.ai/my-lab/my-project/runs/abc123
- Checkpoint saved: outputs/baseline-experiment/train-baseline__20250115T080000/checkpoint-final
```

## Output

After successful execution, the skill produces:

- `runs/<run-id>/run.yaml` with complete execution status
- `runs/<run-id>/resolved-job.yaml` with exact configuration used
- `runs/<run-id>/logs/stdout.log` and `stderr.log` with execution logs
- Updated `history.md` entry documenting the execution
- Training outputs in outputs directory (checkpoints, metrics, etc.)

## Phase 1 Limitations

Phase 1 implementation has the following limitations:

- **Local Execution Only**: SSH execution not implemented (requires Phase 6)
- **No Slurm Integration**: Slurm submission not implemented (requires Phase 6)
- **Limited Suitability**: Local execution only suitable for:
  - Smoke tests and debugging
  - Small models and datasets
  - CPU-only quick experiments
- **Manual W&B**: W&B environment setup is basic (full integration in Phase 7)
- **Manual HF Hub**: Hugging Face Hub push is basic (full integration in Phase 8)

## Notes

### Future Phase Integration

When Phase 6+ is implemented, this skill will:

- **SSH Execution**: Transfer files to remote host and execute there
- **Slurm Submission**: Generate sbatch scripts and submit to Slurm scheduler
- **Job Monitoring**: Poll Slurm job status and retrieve logs when complete
- **Advanced Tracking**: Track Slurm job IDs, node assignments, and queue times

### Error Handling

If execution fails:

- Record failure status in run.yaml
- Save error logs for debugging
- Update history.md with failure entry
- Suggest potential fixes based on error patterns:
  - OOM errors: reduce batch size, enable gradient checkpointing
  - Import errors: check environment dependencies
  - File not found: verify data paths in job configuration
  - W&B auth errors: check API token configuration

Do NOT automatically retry failed runs without user approval.

### Multi-Run Jobs

For jobs with matrix parameters (ablations):

- Each matrix combination generates a separate run ID
- All runs share the same job-id prefix
- Each run gets its own directory and tracking files
- History.md contains an entry for each run
- Consider generating summary table after all runs complete

### Resource Management

For local execution:

- Be aware of system resource limits (RAM, disk space)
- Warn user if job requirements exceed available resources
- Monitor disk space during execution
- Suggest remote execution for large jobs
