# Execution Policy

## Purpose

This document defines execution environment requirements, resource management policies, and environment detection strategies for training job execution. It guides Codex in making execution decisions that balance efficiency, safety, and user expectations.

## Slurm Requirement Rules

### When Slurm is REQUIRED

Slurm submission is required when ANY of the following conditions are met:

1. **GPU Jobs**: Any job that requests `resources.gpus > 0`
2. **CPU-Heavy Jobs**: Any job with estimated execution time >4 CPU-hours
   - Calculate as: `(cpus × estimated_hours) > 4`
   - Example: 8 CPUs for 1 hour = 8 CPU-hours (requires Slurm)
   - Example: 2 CPUs for 3 hours = 6 CPU-hours (requires Slurm)
   - Example: 4 CPUs for 30 minutes = 2 CPU-hours (local execution OK)

### When Local Execution is Acceptable

Local execution is suitable for:

- Quick smoke tests and debugging (<30 minutes expected runtime)
- CPU-only jobs with <4 CPU-hours total
- Development iteration on small datasets
- Configuration validation runs

### Estimation Guidelines

When exact runtime is unknown:

- **Conservative estimate**: Assume 2× the fastest similar experiment
- **Model size heuristics**:
  - Models <500M parameters: potentially suitable for local
  - Models >500M parameters: likely require Slurm
- **Dataset size heuristics**:
  - Datasets <10k examples: potentially suitable for local
  - Datasets >10k examples: likely require Slurm

When in doubt, prefer Slurm for reproducibility and resource isolation.

## Phase 2 Limitation: Local Execution Only

**IMPORTANT**: Phase 2 implementation supports local execution only. Slurm integration is deferred to Phase 6.

When a job triggers Slurm requirements but Slurm integration is not available:

1. **Inform the user** of the Slurm requirement and why it's triggered
2. **Warn about limitations** of local execution for this job type
3. **Offer to proceed locally** with explicit user confirmation
4. **Document the decision** in history.md with Phase 2 limitation note

Example warning message:
```
⚠️  This job requests 2 GPUs and is estimated to run for 6 hours (48 GPU-hours).
According to execution policy, this requires Slurm submission for proper resource
management and isolation.

Phase 2 limitation: Slurm integration is not yet implemented. I can attempt local
execution if you have the necessary hardware available, but this is not the
recommended approach for production training.

Would you like to proceed with local execution? (yes/no)
```

## Environment Manager Detection

Codex SHALL detect and activate the project environment in the following priority order:

### 1. Conda Environment (Highest Priority)

**Detection**:
- Check if `CONDA_DEFAULT_ENV` environment variable is set
- OR check if `environment.yaml` or `environment.yml` exists in workspace root
- OR run `conda env list` and look for environment matching project name

**Activation**:
```bash
conda activate <env-name>
```

**Validation**:
- Verify activation with `conda info --envs | grep '*'`
- Check Python path points to conda environment

**Creation** (if environment doesn't exist but configuration file exists):
```bash
conda env create -f environment.yaml
```

### 2. UV Project (Second Priority)

**Detection**:
- Check if `pyproject.toml` AND `uv.lock` exist in workspace root
- Check if `uv` command is available: `which uv`

**Activation**:
- UV manages environment automatically via `uv run` prefix
- No explicit activation needed

**Execution**:
```bash
uv run python <script.py> [args]
```

**Validation**:
- Run `uv pip list` to verify installed packages

**Creation** (if pyproject.toml exists but uv.lock doesn't):
```bash
uv lock
```

### 3. Virtual Environment (Third Priority)

**Detection**:
- Check if `VIRTUAL_ENV` environment variable is set
- OR check if `.venv/`, `venv/`, or `env/` directory exists in workspace root

**Activation**:
```bash
source <venv-path>/bin/activate
```

**Validation**:
- Check `VIRTUAL_ENV` is set after activation
- Verify Python path points to venv: `which python`

**Creation** (if no venv exists):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # if requirements.txt exists
```

### 4. System Python (Fallback)

**Detection**:
- If none of the above environments are detected
- Check Python version: `python3 --version`

**Warning**:
- Issue warning to user: "Using system Python. Consider creating a project environment for reproducibility."
- Log the decision in run.yaml

**Execution**:
```bash
python3 <script.py> [args]
```

## Environment Detection Algorithm

```python
def detect_environment(workspace_path):
    """
    Detect project environment in priority order.
    
    Returns:
        tuple: (env_type, env_name, activation_command)
    """
    # 1. Check Conda
    if os.getenv('CONDA_DEFAULT_ENV'):
        return ('conda', os.getenv('CONDA_DEFAULT_ENV'), f'conda activate {os.getenv("CONDA_DEFAULT_ENV")}')
    
    if (workspace_path / 'environment.yaml').exists():
        # Parse environment.yaml to get name
        env_name = parse_conda_env_name(workspace_path / 'environment.yaml')
        return ('conda', env_name, f'conda activate {env_name}')
    
    # 2. Check UV
    if (workspace_path / 'pyproject.toml').exists() and (workspace_path / 'uv.lock').exists():
        if shutil.which('uv'):
            return ('uv', 'uv-project', 'uv run')
    
    # 3. Check Virtual Environment
    if os.getenv('VIRTUAL_ENV'):
        return ('venv', os.getenv('VIRTUAL_ENV'), f'source {os.getenv("VIRTUAL_ENV")}/bin/activate')
    
    for venv_dir in ['.venv', 'venv', 'env']:
        venv_path = workspace_path / venv_dir
        if venv_path.exists() and (venv_path / 'bin' / 'python').exists():
            return ('venv', str(venv_path), f'source {venv_path}/bin/activate')
    
    # 4. Fall back to system Python
    return ('system', 'system', None)
```

## Quota Checking

### Quota Configuration

Project resource quotas are defined in `project-plan.md`:

```yaml
resource_quotas:
  max_gpus_per_job: 8
  max_cpus_per_job: 64
  max_memory_gb_per_job: 512
  max_job_time_hours: 72
  max_concurrent_jobs: 4
```

### Checking Procedure

Before executing a job, compare requested resources against quota limits:

1. **Parse job resources** from `resources` section of job YAML
2. **Parse project quotas** from `project-plan.md`
3. **Compare each resource** against corresponding quota
4. **Calculate utilization percentage** for each resource

### Violation Handling

**Hard violations** (requested > quota):
- Block execution
- Report violation with clear message
- Suggest adjusted resource values

Example:
```
❌ Resource quota violation:
   Requested: 16 GPUs
   Quota:     8 GPUs
   
Suggestion: Reduce to 8 GPUs or request quota increase from cluster admin.
```

**Soft warnings** (requested > 80% of quota):
- Allow execution but issue warning
- Log warning in run.yaml
- Mention in history.md entry

Example:
```
⚠️  High resource utilization:
   Requested: 7 GPUs (87.5% of quota)
   Quota:     8 GPUs
   
Proceeding with execution. Monitor cluster usage to avoid conflicts.
```

### Missing Quota Configuration

If `project-plan.md` doesn't define quotas:
- Issue one-time warning to user
- Suggest adding quota configuration
- Proceed with execution (no blocking)
- Log the missing configuration

## Resource Validation

### Required Resource Fields

Every job MUST specify:
- `resources.backend`: "local" or "slurm"
- `resources.gpus`: integer >= 0
- `resources.cpus`: integer >= 1
- `resources.memory_gb`: integer >= 1
- `resources.time`: string in HH:MM:SS format

### Optional Resource Fields

Jobs MAY specify:
- `resources.gpu_type`: string (e.g., "a100", "v100")
- `resources.partition`: string (Slurm partition name)
- `resources.constraint`: string (Slurm constraint)

### Validation Rules

1. **GPU/Backend consistency**: If `gpus > 0` and `backend == "local"`, warn about potential issues
2. **Memory reasonableness**: If `memory_gb > system_total_memory`, warn or block
3. **Time format**: Validate time string matches HH:MM:SS pattern
4. **CPU/GPU ratio**: Warn if ratio is unusual (e.g., 1 GPU with 64 CPUs)

## Execution Backend Selection

### Backend Decision Logic

```python
def select_backend(job_resources, slurm_available, user_preference):
    """
    Determine execution backend based on job requirements and availability.
    
    Priority:
    1. Explicit user preference (if safe)
    2. Slurm requirement rules
    3. Resource availability
    """
    # Check Slurm requirements
    requires_slurm = (
        job_resources['gpus'] > 0 or
        (job_resources['cpus'] * estimated_hours(job_resources['time'])) > 4
    )
    
    # Phase 2: Slurm not available
    if requires_slurm and not slurm_available:
        warn_and_confirm_local_execution()
        return 'local'
    
    # Honor explicit backend request if it meets requirements
    if job_resources.get('backend'):
        if job_resources['backend'] == 'local' and requires_slurm:
            warn("Job requires Slurm but 'local' backend specified")
            confirm_with_user()
        return job_resources['backend']
    
    # Default selection
    return 'slurm' if requires_slurm else 'local'
```

## Command Construction

### Configuration Style Support

Jobs specify how to pass parameters via `config_style`:

#### 1. Argument Style (Default)

Pass parameters as command-line arguments:

```bash
python train.py \
  --model-name meta-llama/Llama-2-7b-hf \
  --dataset-name wikitext \
  --learning-rate 1e-4 \
  --batch-size 8 \
  --epochs 3
```

#### 2. Hydra Style

Pass parameters as Hydra overrides:

```bash
python train.py \
  model.name=meta-llama/Llama-2-7b-hf \
  data.dataset=wikitext \
  training.lr=1e-4 \
  training.batch_size=8 \
  training.epochs=3
```

#### 3. JSON Style

Write parameters to JSON file, pass filename:

```bash
echo '{"model": "meta-llama/Llama-2-7b-hf", ...}' > config.json
python train.py --config config.json
```

#### 4. YAML Style

Write parameters to YAML file, pass filename:

```bash
cat > config.yaml <<EOF
model:
  name: meta-llama/Llama-2-7b-hf
...
EOF
python train.py --config config.yaml
```

### Parameter Type Handling

- **Strings**: Quote if they contain spaces
- **Numbers**: Pass as-is (integers or floats)
- **Booleans**: Convert to appropriate format
  - Argument style: `--flag` for true, omit for false
  - Hydra style: `flag=true` or `flag=false`
  - JSON/YAML: `true` or `false`
- **Lists**: Format depends on style
  - Argument style: `--tags tag1 --tags tag2`
  - Hydra style: `tags=[tag1,tag2]`
  - JSON/YAML: `["tag1", "tag2"]`

## Environment Variables

### Always Set

```bash
# Run tracking
export RUN_ID="<run-id>"
export EXPERIMENT_ID="<experiment-id>"
export JOB_ID="<job-id>"

# Output paths
export OUTPUT_DIR="<workspace>/outputs/<experiment-id>/<run-id>"
export LOG_DIR="<workspace>/experiments/<experiment-id>/runs/<run-id>/logs"
```

### Conditional: Weights & Biases

If `wandb.enabled == true`:

```bash
export WANDB_PROJECT="<from-project-plan>"
export WANDB_ENTITY="<from-project-plan>"
export WANDB_RUN_GROUP="<from-job.wandb.group>"
export WANDB_TAGS="<from-job.wandb.tags>"
export WANDB_RUN_ID="<run-id>"  # For run name consistency
export WANDB_DIR="<workspace>/outputs/<experiment-id>/<run-id>"
```

**Phase 2 Note**: W&B API integration is limited. These environment variables are set for training scripts that use W&B SDK directly. Advanced features (programmatic run analysis, artifact tracking) are deferred to Phase 7.

### Conditional: Hugging Face Hub

If `huggingface.push != "never"`:

```bash
export HF_TOKEN="<from-user-env-or-dotenv>"
export HF_HOME="<workspace>/.cache/huggingface"
```

Training scripts can use `huggingface.repo` from job configuration to determine push destination.

**Phase 2 Note**: Automated Hub uploads are deferred to Phase 8. Phase 2 only sets environment variables for training scripts that handle uploads directly.

## Execution Isolation

### Working Directory

Always execute training jobs from the workspace root:

```bash
cd <workspace-root>
<activation-command>
<training-command>
```

This ensures:
- Consistent relative path resolution
- Training scripts can locate data/ and src/ directories
- Output paths are predictable

### Process Management

For local execution:

- Use `subprocess.Popen()` with output capture
- Stream stdout/stderr to both console and log files
- Track process ID for potential interruption
- Set timeout based on `resources.time`
- Handle SIGINT/SIGTERM gracefully

### Cleanup

After execution (success or failure):

- Flush and close log files
- Deactivate environment (if applicable)
- Remove temporary configuration files (for JSON/YAML style)
- Archive large log files if needed

## Error Patterns and Recommendations

### Out of Memory (OOM)

**Symptoms**:
- Exit code 137 (SIGKILL)
- "CUDA out of memory" in stderr
- "Killed" message in logs

**Recommendations**:
1. Reduce batch size
2. Enable gradient checkpointing
3. Reduce sequence length
4. Use mixed precision training (fp16/bf16)
5. Request more memory in job resources

### Import Errors

**Symptoms**:
- "ModuleNotFoundError" in stderr
- "ImportError" in stderr

**Recommendations**:
1. Verify environment activation
2. Check requirements.txt or environment.yaml
3. Run `pip list` or `conda list` to see installed packages
4. Install missing dependencies

### File Not Found

**Symptoms**:
- "FileNotFoundError" in stderr
- "No such file or directory" in stderr

**Recommendations**:
1. Verify data paths in job configuration
2. Check that datasets are downloaded to data/ directory
3. Ensure entrypoint path is correct
4. Verify working directory is workspace root

### W&B Authentication

**Symptoms**:
- "wandb: ERROR Error authenticating" in logs
- "wandb: ERROR API key not found" in logs

**Recommendations**:
1. Check that WANDB_API_KEY is set in environment
2. Run `wandb login` in activated environment
3. Verify W&B entity and project exist
4. Check network connectivity to wandb.ai

### HuggingFace Authentication

**Symptoms**:
- "Token is required" in stderr
- "401 Unauthorized" when accessing models

**Recommendations**:
1. Check that HF_TOKEN is set in environment
2. Run `huggingface-cli login` in activated environment
3. Verify token has required permissions
4. Check if model/dataset requires authentication

## Monitoring and Logging

### Real-Time Monitoring

During execution, monitor:

- **Progress indicators**: Epoch numbers, step counts, loss values
- **Resource utilization**: GPU memory, CPU load (if tools available)
- **Time elapsed**: Compare against estimated duration
- **Error messages**: Watch for warnings and errors in stderr

### Log Organization

```
experiments/<experiment-id>/runs/<run-id>/logs/
├── stdout.log          # Full stdout capture
├── stderr.log          # Full stderr capture
└── execution.log       # Codex execution notes (start time, env detected, etc.)
```

### Log Parsing

After execution, parse logs to extract:

- **W&B run URL**: `wandb: 🚀 View run at https://wandb.ai/...`
- **Final metrics**: Loss values, accuracy, perplexity, etc.
- **Checkpoint paths**: Where final model was saved
- **Warnings**: Any warnings from training framework
- **Error context**: For failures, extract relevant error messages

## Security Considerations

### Credential Handling

- NEVER log API keys, tokens, or passwords
- Redact sensitive environment variables in execution.log
- Use secure environment variable sources (.env files with .gitignore)

### Path Validation

- Validate all paths stay within workspace bounds
- Prevent directory traversal attacks (e.g., `../../etc/passwd`)
- Verify entrypoint scripts before execution

### Resource Limits

- Enforce timeout to prevent runaway processes
- Monitor disk space to prevent filling filesystem
- Set memory limits to prevent system instability

## Phase Boundaries

### Phase 2 (Current): Local Execution

**Implemented**:
- ✅ Local backend selection
- ✅ Environment detection (conda, uv, venv, system)
- ✅ Quota checking against project-plan.md
- ✅ Command construction for all config styles
- ✅ Environment variable setup
- ✅ Basic W&B and HF environment support

**Not Implemented**:
- ❌ SSH execution
- ❌ Slurm submission
- ❌ Remote file transfer
- ❌ Job queue management

### Phase 6: SSH & Slurm Integration

**Future additions**:
- SSH connection management
- Remote file transfer (rsync)
- Slurm sbatch script generation
- Job status polling
- Remote log retrieval
- Node allocation tracking

### Phase 7: W&B Integration

**Future additions**:
- Programmatic run analysis via W&B API
- Artifact download and comparison
- Metric aggregation across runs
- Hyperparameter sweep coordination

### Phase 8: HuggingFace Hub Integration

**Future additions**:
- Automated model card generation
- Checkpoint upload with metadata
- Model repository management
- Version control for model releases

## References

- **Slurm Documentation**: https://slurm.schedmd.com/
- **Conda Environment Management**: https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html
- **UV Documentation**: https://github.com/astral-sh/uv
- **Weights & Biases Python SDK**: https://docs.wandb.ai/ref/python/
- **HuggingFace Hub Python Library**: https://huggingface.co/docs/huggingface_hub/

## Document History

- **2025-01-XX**: Initial creation (Phase 2 implementation)
- **Status**: Draft for Phase 2 review
