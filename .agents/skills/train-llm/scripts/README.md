# Train-LLM Helper Scripts

This directory contains deterministic helper scripts for the `train-llm` skill. These scripts perform validation, initialization, and tracking operations that support AI-assisted ML experiment workflows.

## Architecture Principle

**"SKILL.md is workflow, scripts/ are deterministic helpers, src/ is research code"**

These scripts:
- Accept explicit file paths (no implicit cwd dependencies)
- Output structured JSON for agent parsing
- Handle errors gracefully with clear messages
- Support `--dry-run` mode where applicable
- Do NOT import from project `src/` directory
- Do NOT contain hardcoded project values

## Dependencies

- **Python:** 3.8 or higher
- **Required packages:** PyYAML (`pip install pyyaml`)
- **Standard library:** argparse, json, pathlib, datetime, sys

## Scripts

### 1. validate_job.py

Validates job configuration files before execution, checking required fields, entrypoint existence, and resource specifications.

#### Purpose

- Verify job configuration has all required fields
- Check that entrypoint file exists
- Validate resource specifications (GPUs, CPUs, memory, time)
- Validate matrix syntax (if present)
- Validate W&B and HuggingFace configurations
- Check resource limits against quotas (optional)

#### Usage

```bash
# Basic validation
python validate_job.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --workspace /path/to/workspace

# With quota checking
python validate_job.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --workspace /path/to/workspace \
  --quota-file project-plan.md

# Show help
python validate_job.py --help

# Show version
python validate_job.py --version
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--job-file PATH` | Yes | Path to job configuration YAML file |
| `--workspace PATH` | Yes | Path to workspace root directory |
| `--quota-file PATH` | No | Path to quota configuration file (e.g., project-plan.md) |
| `--help` | No | Show help message and exit |
| `--version` | No | Show version information and exit |

#### Output Format (JSON)

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "checked": {
    "required_fields": true,
    "entrypoint_exists": true,
    "quota_compliance": false
  }
}
```

#### Exit Codes

- **0:** Validation successful
- **1:** Validation failed (job configuration errors)
- **2:** Runtime error (file not found, invalid YAML, etc.)

#### Validation Rules

**Required Fields:**
- `job_id` (string)
- `type` (one of: `train`, `evaluate`, `custom`)
- `entrypoint` (string path to script)
- `parameters` (dictionary)
- `resources` (dictionary)

**Resources Validation:**
- `gpus`: non-negative integer
- `cpus`: positive integer (≥ 1)
- `memory_gb`: positive number (≥ 1)
- `time`: string in HH:MM:SS format
- `backend`: one of `local`, `slurm`

**Matrix Validation:**
- Must be a dictionary
- Keys must be strings
- Values must be non-empty lists

**W&B Configuration:**
- `enabled`: boolean (required)
- `group`: string (optional)
- `tags`: list of strings (optional)

**HuggingFace Configuration:**
- `push`: one of `never`, `final_only`, `milestone`, `every_save` (required)
- `repo`: string or null (optional)

#### Examples

**Valid job file:**
```yaml
job_id: train-baseline
type: train
entrypoint: src/train.py
parameters:
  learning_rate: 2e-5
  batch_size: 8
resources:
  gpus: 1
  cpus: 4
  memory_gb: 16
  time: "02:00:00"
  backend: local
wandb:
  enabled: true
  group: baseline-experiments
  tags:
    - baseline
    - gpt2
```

**Validation command:**
```bash
python validate_job.py \
  --job-file experiments/baseline/jobs/train.yaml \
  --workspace /Users/researcher/aiml-harness
```

**Expected output (success):**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "checked": {
    "required_fields": true,
    "entrypoint_exists": true,
    "quota_compliance": false
  }
}
```

---

### 2. initialize_run.py

Initializes run directory structure and tracking metadata for training or evaluation jobs.

#### Purpose

- Generate unique Run ID with timestamp
- Create run directory structure
- Write initial run tracking metadata
- Copy and resolve job configuration
- Support dry-run mode for preview

#### Usage

```bash
# Initialize a training run
python initialize_run.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --experiment-dir experiments/my-exp

# Preview without creating files (dry-run)
python initialize_run.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --experiment-dir experiments/my-exp \
  --dry-run

# Show help
python initialize_run.py --help

# Show version
python initialize_run.py --version
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--job-file PATH` | Yes | Path to job configuration YAML file |
| `--experiment-dir PATH` | Yes | Path to experiment directory |
| `--dry-run` | No | Preview operations without creating files |
| `--help` | No | Show help message and exit |
| `--version` | No | Show version information and exit |

#### Output Format (JSON)

```json
{
  "status": "success",
  "message": "Run initialized successfully: train-baseline__20250115T142530",
  "data": {
    "run_id": "train-baseline__20250115T142530",
    "run_dir": "/path/to/experiments/my-exp/runs/train-baseline__20250115T142530",
    "status": "initialized",
    "created_files": [
      "/path/to/experiments/my-exp/runs/train-baseline__20250115T142530",
      "/path/to/experiments/my-exp/runs/train-baseline__20250115T142530/logs",
      "/path/to/experiments/my-exp/runs/train-baseline__20250115T142530/run.yaml",
      "/path/to/experiments/my-exp/runs/train-baseline__20250115T142530/resolved-job.yaml"
    ],
    "timestamp": "2025-01-15T14:25:30.123456"
  },
  "errors": [],
  "warnings": []
}
```

#### Exit Codes

- **0:** Success
- **1:** Validation error (missing files, invalid configuration)
- **2:** Runtime error (file system operations failed)

#### Run ID Format

```
{type}-{job_id}__{YYYYMMDDTHHMMSS}
```

Examples:
- `train-baseline__20250115T142530`
- `evaluate-test-set__20250115T150000`
- `custom-preprocess__20250115T160000`

#### Directory Structure Created

```
experiments/my-exp/runs/
└── train-baseline__20250115T142530/
    ├── run.yaml                 # Run tracking metadata
    ├── resolved-job.yaml        # Resolved job configuration
    └── logs/                    # Log files directory
```

#### run.yaml Structure

```yaml
run_id: train-baseline__20250115T142530
job_file: /path/to/experiments/my-exp/jobs/train.yaml
experiment_id: my-exp
status: initialized
created_at: '2025-01-15T14:25:30.123456'
started_at: null
completed_at: null
exit_code: null
metrics: {}
wandb_run_id: null
checkpoint_path: null
```

#### Examples

**Initialize a run:**
```bash
python initialize_run.py \
  --job-file experiments/baseline/jobs/train.yaml \
  --experiment-dir experiments/baseline
```

**Expected output (success):**
```json
{
  "status": "success",
  "message": "Run initialized successfully: train-baseline__20250115T142530",
  "data": {
    "run_id": "train-baseline__20250115T142530",
    "run_dir": "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530",
    "status": "initialized",
    "created_files": [
      "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530",
      "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530/logs",
      "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530/run.yaml",
      "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530/resolved-job.yaml"
    ],
    "timestamp": "2025-01-15T14:25:30.123456"
  },
  "errors": [],
  "warnings": []
}
```

**Dry-run preview:**
```bash
python initialize_run.py \
  --job-file experiments/baseline/jobs/train.yaml \
  --experiment-dir experiments/baseline \
  --dry-run
```

**Expected output (dry-run):**
```json
{
  "status": "success",
  "message": "Dry-run preview for run: train-baseline__20250115T142530",
  "data": {
    "run_id": "train-baseline__20250115T142530",
    "run_dir": "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530",
    "status": "preview",
    "created_files": [
      "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530",
      "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530/logs",
      "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530/run.yaml",
      "/Users/researcher/aiml-harness/experiments/baseline/runs/train-baseline__20250115T142530/resolved-job.yaml"
    ],
    "timestamp": "2025-01-15T14:25:30.123456",
    "dry_run": true
  },
  "errors": [],
  "warnings": []
}
```

### 3. run_local.py

Runs an **approved** job locally and records the outcome (Phase 5). Composes with
`initialize_run.py`: that script creates the run directory, `run.yaml`
(`status: initialized`), and `resolved-job.yaml`; `run_local.py` consumes the
existing run directory, executes a short local CPU job, captures output, tracks
the run lifecycle, and appends a `history.md` entry.

#### Purpose

- Gate execution on `approval.status == approved` in the experiment `plan.md`
- Hard-reject GPU and CPU-heavy jobs by deferring them to Slurm (Phase 6)
- Detect the project environment (conda > uv > venv > system) and activate it
- Build the command from the job `entrypoint`, `parameters`, and `config_style`
  (`argument` default, `hydra`, `json`, `yaml`) without any framework assumption
- Capture stdout/stderr to `runs/<run-id>/logs/`, enforce a timeout, and record
  the run status lifecycle (`created → running → succeeded | failed | timed_out | cancelled`)
- Record failed runs with the same rigor as successes; parse a W&B URL from logs
  as plain text only (no live W&B call)

#### Usage

```bash
# Run an approved job after initialize_run.py created the run directory
python run_local.py \
  --run-dir experiments/my-exp/runs/train-demo__20250115T142530 \
  --workspace .

# Override the default timeout (seconds)
python run_local.py \
  --run-dir experiments/my-exp/runs/<run-id> \
  --workspace . \
  --default-timeout 120

# Explicit plan path (defaults to <run-dir>/../../plan.md)
python run_local.py \
  --run-dir experiments/my-exp/runs/<run-id> \
  --workspace . \
  --plan-file experiments/my-exp/plan.md

python run_local.py --version
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--run-dir PATH` | Yes | Existing run directory created by `initialize_run.py` |
| `--workspace PATH` | Yes | Workspace root used as the process working directory and entrypoint base |
| `--plan-file PATH` | No | Experiment `plan.md`; defaults to `<run-dir>/../../plan.md` |
| `--default-timeout SECONDS` | No | Timeout used when the job declares no `resources.time` (default 600) |
| `--version` | No | Show version information and exit |

#### Exit Codes

- **0:** Local run executed and recorded (succeeded, or recorded failure/timeout)
- **1:** Declined — approval required, deferred to Slurm, unsupported config style, or preparation failure (e.g. missing entrypoint)
- **2:** Runtime error (missing run directory, PyYAML missing, filesystem/parse error)

#### Composition note

- `run_local.py` normalizes the on-disk status written by `initialize_run.py`:
  `initialized → created` (and `completed → succeeded`) when reading, then writes
  the roadmap lifecycle statuses on update.
- It writes only within the run directory, plus an append to the experiment
  `history.md`.

#### Phase boundaries

- **Phase 6 (SSH/Slurm):** GPU and CPU-heavy jobs are deferred, never run locally.
- **Phase 7 (W&B):** no live API calls; a W&B URL is only parsed from log text.
- **Phase 8 (Hugging Face Hub):** no uploads. No Git operations, no network calls.

### 4. submit_slurm.py

Submits an **approved** job to Slurm over SSH and records the linkage (Phase 6).
Extends the Phase 5 Slurm deferral in `run_local.py` into a real submission path.
Reads stable settings from `project-plan.md`, the job from `resolved-job.yaml`,
and the approval status from the experiment `plan.md`.

#### Design discipline

- **Pure logic** functions (sbatch generation, GRES/resource mapping, log naming,
  quota validation, job-id parsing, Slurm→Harness status mapping, approval
  decision, commit-candidate filtering, secret redaction) take plain data and
  perform no SSH, subprocess, network, or filesystem mutation.
- **All SSH/Slurm I/O** passes through a single injected `CommandRunner`.
  Production uses `SSHCommandRunner` (constructed only in `main()`); tests inject
  a `FakeCommandRunner` with scripted results. No real SSH or network ever occurs
  in tests.
- **Mutating remote actions** (`sbatch`, `scancel`, remote transfer/clone, env
  creation) require `approval.status == approved` in the experiment `plan.md`.
  Read-only probes (`ssh echo`, `test -d`, `conda env list`, `sinfo`, `squeue`,
  `sacct`, `scontrol show`) are non-mutating and still routed through the runner.

#### Subcommands

| Command | Description |
|---------|-------------|
| `verify` | Read-only probes: host reachability, remote-path existence, conda-env membership |
| `submit` | Approval- and quota-gated `sbatch` submission; records `slurm_job_id` and `submitted` status |
| `poll` | Query active jobs via `squeue`, completed via `sacct`; map state and capture node assignment |
| `cancel` | Approval-gated `scancel`; sets `cancelled` status on success |
| `retry` | Create a new run from a retryable prior (`failed`/`timed_out`/`cancelled`/`preempted`); prior run preserved |
| `resume` | Poll a previously recorded `slurm_job_id` without resubmitting; declines when no id is recorded |

#### Arguments (per subcommand)

| Argument | Description |
|----------|-------------|
| `--plan-file PATH` | Path to `project-plan.md` (stable settings; defaults to `project-plan.md`) |
| `--run-dir PATH` | Existing run directory created by `initialize_run.py` |
| `--experiment-plan PATH` | Experiment `plan.md` with the approval gate (defaults to `<run-dir>/../../plan.md`) |
| `--conda-env NAME` | Target conda environment name to verify and activate |

#### Exit Codes

- **0:** Action completed or recorded
- **1:** Declined — approval, quota, verification, or resume-not-possible
- **2:** Runtime error (missing/invalid `project-plan.md`, filesystem/parse error)

#### run.yaml linkage fields

On submit/poll, `submit_slurm.py` extends `run.yaml` with `slurm_job_id`,
`slurm_state` (raw Slurm state; keeps OUT_OF_MEMORY distinct from plain failure),
`status` (mapped Harness status), `submitted_at`, `node_list`, and
`array_job_id` for array jobs. No secret, token, or credential value is written.

#### CUDA / cluster note

The generated sbatch script sources the conda profile under the plan's
`remote_conda_root` and activates the target env **before** the run command. The
CUDA toolkit comes from the conda environment and is pinned at or below the
NVIDIA driver CUDA ceiling (12.4); there is no system `nvcc` and no lmod on the
SKIML cluster. GPU and CPU-heavy jobs always route through `sbatch`, never the
login node.

#### Phase boundaries

- **Phase 7 (W&B):** no live API calls.
- **Phase 8 (Hugging Face Hub):** no uploads.
- Real mutating remote actions require explicit user approval and are never
  exercised by tests.

## Common Workflows

### 1. Validate before execution

Always validate job configuration before initializing a run:

```bash
# Step 1: Validate job configuration
python validate_job.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --workspace .

# Check validation output
# If valid=true, proceed to initialization

# Step 2: Initialize run
python initialize_run.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --experiment-dir experiments/my-exp

# Step 3: Execute training (handled by train-llm skill)
```

### 2. Preview run initialization

Use dry-run to preview before creating files:

```bash
# Preview what will be created
python initialize_run.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --experiment-dir experiments/my-exp \
  --dry-run

# Review output, then run without --dry-run to create files
python initialize_run.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --experiment-dir experiments/my-exp
```

### 3. Validate with quota checking

Check resource requests against project quotas:

```bash
python validate_job.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --workspace . \
  --quota-file project-plan.md
```

### 4. Batch validation

Validate multiple job files in a loop:

```bash
for job_file in experiments/*/jobs/*.yaml; do
  echo "Validating: $job_file"
  python validate_job.py \
    --job-file "$job_file" \
    --workspace .
done
```

### 5. Working from different directories

Scripts accept absolute or relative paths and resolve them correctly:

```bash
# From workspace root
python .agents/skills/train-llm/scripts/validate_job.py \
  --job-file experiments/my-exp/jobs/train.yaml \
  --workspace .

# From scripts directory
cd .agents/skills/train-llm/scripts
python validate_job.py \
  --job-file ../../../../experiments/my-exp/jobs/train.yaml \
  --workspace ../../../..

# From experiment directory
cd experiments/my-exp
python ../../.agents/skills/train-llm/scripts/initialize_run.py \
  --job-file jobs/train.yaml \
  --experiment-dir .
```

## Testing Approach

### Unit Testing

Scripts follow testable design principles:

- **Pure functions:** Validation and metadata generation logic separated from I/O
- **Explicit inputs:** All file paths passed as arguments (no cwd assumptions)
- **Structured output:** JSON format enables automated testing
- **Error handling:** Graceful failures with clear error messages

### Property-Based Testing

Key properties to test:

1. **Job Validation Completeness:** For any valid job configuration, validation must check all required fields and report accurate results
2. **Run Initialization Consistency:** Run ID generation must be deterministic given the same inputs, and directory structure must match schema
3. **Script Interface Compliance:** All scripts must work from any working directory, output valid JSON, and handle missing files gracefully

### Integration Testing

Test with example experiment:

```bash
# Test validation with example experiment
python validate_job.py \
  --job-file experiments/example-lora-rank-ablation/jobs/train.yaml \
  --workspace .

# Test initialization with example experiment
python initialize_run.py \
  --job-file experiments/example-lora-rank-ablation/jobs/train.yaml \
  --experiment-dir experiments/example-lora-rank-ablation \
  --dry-run
```

### Manual Testing Checklist

- [ ] Scripts work from workspace root
- [ ] Scripts work from scripts directory
- [ ] Scripts work from arbitrary directories
- [ ] Validation catches missing required fields
- [ ] Validation verifies entrypoint existence
- [ ] Validation accepts valid configurations
- [ ] Initialization creates correct directory structure
- [ ] Initialization generates valid run.yaml
- [ ] Initialization handles duplicate runs (timestamp collision)
- [ ] Dry-run mode doesn't create files
- [ ] JSON output is parseable
- [ ] Error messages are clear and actionable

## Error Handling

### Common Errors

**Missing PyYAML dependency:**
```json
{
  "valid": false,
  "errors": ["PyYAML is required but not installed. Please install it with: pip install pyyaml"],
  "warnings": [],
  "checked": {
    "required_fields": false,
    "entrypoint_exists": false,
    "quota_compliance": false
  }
}
```

**File not found:**
```json
{
  "status": "error",
  "message": "Job file not found: experiments/my-exp/jobs/train.yaml",
  "data": {},
  "errors": ["File does not exist: /absolute/path/to/experiments/my-exp/jobs/train.yaml"],
  "warnings": []
}
```

**Invalid YAML syntax:**
```json
{
  "valid": false,
  "errors": ["Invalid YAML syntax: mapping values are not allowed here\n  in \"train.yaml\", line 5, column 15"],
  "warnings": [],
  "checked": {
    "required_fields": false,
    "entrypoint_exists": false,
    "quota_compliance": false
  }
}
```

**Missing required fields:**
```json
{
  "valid": false,
  "errors": ["Missing required fields: job_id, type, entrypoint"],
  "warnings": [],
  "checked": {
    "required_fields": false,
    "entrypoint_exists": false,
    "quota_compliance": false
  }
}
```

**Entrypoint not found:**
```json
{
  "valid": false,
  "errors": [
    "Entrypoint file not found: /absolute/path/to/src/train.py",
    "  (looking for 'src/train.py' relative to workspace /absolute/path/to/workspace)"
  ],
  "warnings": [],
  "checked": {
    "required_fields": true,
    "entrypoint_exists": false,
    "quota_compliance": false
  }
}
```

## Phase 2 Limitations

These scripts support **local execution only** in Phase 2:

- ✅ Local job validation
- ✅ Local run initialization
- ✅ Local directory structure creation
- ❌ SSH/remote execution (planned for future phases)
- ❌ Slurm job submission (planned for future phases)
- ❌ W&B API integration (planned for future phases)
- ❌ HuggingFace Hub uploads (planned for future phases)
- ❌ Matrix parameter resolution (planned for future phases)

Configuration placeholders for future features are accepted and validated but not executed.

## Related Documentation

- **SKILL.md:** Main workflow definition for train-llm skill
- **references/execution-policy.md:** When to use Slurm, environment detection
- **references/run-tracking.md:** Run status lifecycle and metadata schema
- **assets/train-job.yaml:** Job configuration template
- **assets/evaluate-job.yaml:** Evaluation job template

## Version History

- **0.1.0** (2025-01-15): Initial implementation with validation and initialization scripts

## Support

For issues or questions:
1. Check error messages in JSON output
2. Verify file paths are correct (use absolute paths when in doubt)
3. Ensure PyYAML is installed: `pip install pyyaml`
4. Review examples in this README
5. Check related reference documentation in `references/`
