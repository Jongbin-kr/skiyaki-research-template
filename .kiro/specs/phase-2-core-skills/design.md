# Design Document: Phase 2 Core Skills Implementation

## Introduction

Phase 2 enhances the six skills defined in Phase 1 by adding supporting materials that enable executable workflows. This design follows the architectural principle: **"SKILL.md is workflow, scripts/ are deterministic helpers, src/ is research code"**.

The implementation provides:
- **Reference documents** (policies, schemas, guidelines) that guide agent decision-making
- **Asset templates** (YAML/Markdown) that ensure consistent artifact generation
- **Helper scripts** (Python) that perform deterministic validation and initialization operations

This phase focuses on local execution capabilities, deferring SSH/Slurm integration, W&B API access, and HuggingFace Hub uploads to future phases.

## Architecture Overview

### Directory Structure

```
.agents/skills/
├── grill-me/
│   ├── SKILL.md (existing)
│   └── references/
│       └── grill-policy.md (new)
├── discover-prior-research/
│   ├── SKILL.md (existing)
│   └── references/
│       └── search-strategy.md (new)
├── plan-ml-experiment/
│   ├── SKILL.md (existing)
│   ├── assets/
│   │   ├── experiment-plan.md (new)
│   │   ├── train-job.yaml (new)
│   │   └── evaluate-job.yaml (new)
│   └── references/
│       ├── plan-schema.md (new)
│       └── approval-policy.md (new)
├── train-llm/
│   ├── SKILL.md (existing)
│   ├── scripts/
│   │   ├── validate_job.py (new)
│   │   └── initialize_run.py (new)
│   └── references/
│       ├── execution-policy.md (new)
│       └── run-tracking.md (new)
├── evaluate-llm/
│   ├── SKILL.md (existing)
│   └── references/
│       ├── result-schema.md (new)
│       └── comparison-guidelines.md (new)
└── finalize-experiment/
    ├── SKILL.md (existing)
    └── references/
        ├── completion-checklist.md (new)
        └── git-safety.md (new)
```

### Design Principles

1. **Separation of Concerns**: SKILL.md defines workflow, references provide policies, assets provide templates, scripts perform deterministic operations
2. **Explicit Over Implicit**: Scripts accept explicit paths, no reliance on current working directory
3. **JSON Output**: All scripts output structured JSON for reliable agent parsing
4. **Graceful Degradation**: Missing files and invalid inputs produce clear error messages
5. **No Project Coupling**: Scripts are self-contained, no imports from project src/
6. **Phase Boundaries**: Local execution only, placeholders for future integrations

## Component Design

### 1. grill-me Skill

**Purpose**: Guide agents through systematic clarification of research objectives

**Components**:
- `references/grill-policy.md` - questioning strategy and priorities

**Design Details**:

The grill-policy document provides structured guidance for:
- **Question Priority Order**: Metric definition → Baseline identification → Success criteria → Hyperparameters
- **Stable Settings**: References project-plan.md for W&B entity, HF namespace, SSH host, Slurm partition - these should never be re-asked
- **Termination Criteria**: Stop when metric, baseline, and success criteria are clear
- **Vague Answer Handling**: Strategies for probing unclear responses without frustrating users

This is a pure reference document with no scripts needed.

### 2. discover-prior-research Skill

**Purpose**: Systematically search for and consolidate prior experiment findings

**Components**:
- `references/search-strategy.md` - search locations and consolidation approach

**Design Details**:

The search-strategy document defines:
- **Search Locations**:
  - `project-log.md` for project-level conclusions
  - `experiments/*/journal.md` for experiment narratives
  - `experiments/*/results.yaml` for structured metrics
  - Git history for changes over time
- **Evidence Consolidation**: How to combine findings from multiple sources
- **Duplicate Detection**: Identifying similar experiments by comparing objectives, hyperparameters, and metrics
- **Reporting Format**: Structure for presenting findings to Main Agent

Uses existing file tools (`read_file`, `grep_search`, `execute_bash` for git), no custom scripts needed.

### 3. plan-ml-experiment Skill

**Purpose**: Generate consistent, valid experiment plans and job configurations

**Components**:
- `assets/experiment-plan.md` - template with YAML frontmatter
- `assets/train-job.yaml` - training configuration template
- `assets/evaluate-job.yaml` - evaluation configuration template
- `references/plan-schema.md` - frontmatter field definitions
- `references/approval-policy.md` - approval workflow rules

**Design Details**:

**experiment-plan.md template**:
```markdown
---
experiment_id: <kebab-case-id>
status: awaiting_approval
primary_metric:
  name: <metric-name>
  direction: minimize|maximize
success_criteria:
  - <criterion-1>
  - <criterion-2>
jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml
approval:
  status: pending
  requested_at: <timestamp>
---

## Research Objective
...

## Baseline
...

## Design Rationale
...

## Agent-Determined Defaults
...

## Risks and Limitations
...
```

**train-job.yaml template structure**:
- Job metadata (job_id, type, entrypoint, config_style)
- Matrix for ablation studies (optional)
- Parameters (model, dataset, hyperparameters)
- Resources (backend, GPUs, CPUs, memory, time)
- W&B configuration (with Phase 7 note)
- HuggingFace configuration (with Phase 8 note)

**evaluate-job.yaml template structure**:
- Similar to train-job.yaml but for evaluation tasks
- Includes checkpoint path reference
- Evaluation-specific parameters (metrics, test split)

**plan-schema.md** defines:
- Required fields (experiment_id, status, primary_metric, success_criteria, jobs)
- Optional fields (baseline, hypothesis, risks)
- Field types and validation rules

**approval-policy.md** specifies:
- Changes requiring re-approval: metric change, resource increase >20%, new jobs added
- Approval summary format: objective, metric, success criteria, resources, W&B group, HF destination
- How to present agent recommendations vs. user-specified values

### 4. train-llm Skill

**Purpose**: Validate job configurations, initialize run tracking, and execute training

**Components**:
- `scripts/validate_job.py` - job configuration validation
- `scripts/initialize_run.py` - run directory and metadata initialization
- `references/execution-policy.md` - execution environment rules
- `references/run-tracking.md` - run metadata structure

**Design Details**:

**validate_job.py**:
```python
#!/usr/bin/env python3
"""
Validate job configuration file.

Usage:
  validate_job.py --job-file PATH --workspace PATH [--quota-file PATH]

Output (JSON):
  {
    "valid": true|false,
    "errors": [...],
    "warnings": [...],
    "checked": {
      "required_fields": true,
      "entrypoint_exists": true,
      "quota_compliance": true
    }
  }
"""
```

Validation checks:
- Required fields present (job_id, type, entrypoint, parameters, resources)
- Entrypoint file exists at specified path
- Resources within quota limits (if quota-file provided)
- Matrix syntax is valid (if present)
- W&B and HF configurations are well-formed

**initialize_run.py**:
```python
#!/usr/bin/env python3
"""
Initialize run directory and tracking metadata.

Usage:
  initialize_run.py --job-file PATH --experiment-dir PATH [--dry-run]

Output (JSON):
  {
    "run_id": "train-<job-name>__<timestamp>",
    "run_dir": "<absolute-path>",
    "status": "initialized",
    "created_files": [...],
    "timestamp": "<ISO8601>"
  }
"""
```

Initialization operations:
1. Generate Run ID: `{job_type}-{job_id}__{YYYYMMDDTHHMMSS}`
2. Create directory: `experiments/<experiment-id>/runs/<run-id>/`
3. Create subdirectory: `runs/<run-id>/logs/`
4. Write `run.yaml` with initial metadata (run_id, job_file, status: initialized, created_at)
5. Copy job file to `resolved-job.yaml` (with matrix resolution if applicable)
6. Return run metadata as JSON

**execution-policy.md** defines:
- **Slurm requirement triggers**: Any job requesting GPUs, any job with estimated >4 CPU hours
- **Environment detection order**: Check for conda env (CONDA_DEFAULT_ENV), uv project (pyproject.toml + uv.lock), venv (VIRTUAL_ENV), system Python
- **Quota checking**: Compare job resources against project-plan.md limits, warn if >80% quota usage
- **Phase 2 limitation**: Local execution only, document Slurm for reference but don't implement

**run-tracking.md** defines:
- **Run ID format**: `{type}-{job_id}__{YYYYMMDDTHHMMSS}`
- **Status transitions**: initialized → running → completed|failed
- **Directory structure**: `runs/<run-id>/{run.yaml, resolved-job.yaml, logs/, checkpoints/}`
- **run.yaml schema**: run_id, job_file, status, created_at, started_at, completed_at, exit_code, metrics

### 5. evaluate-llm Skill

**Purpose**: Compare training runs and assess success criteria

**Components**:
- `references/result-schema.md` - results.yaml structure
- `references/comparison-guidelines.md` - comparison logic

**Design Details**:

**result-schema.md** defines results.yaml structure:
```yaml
experiment_id: <id>
status: completed
best_run:
  run_id: <id>
  checkpoint: <path>
  metrics:
    <metric-name>: <value>
baseline:
  name: <baseline-name>
  metrics:
    <metric-name>: <value>
comparison:
  improvement: <percent>
  meets_success_criteria: true|false
success_criteria_assessment:
  - criterion: <text>
    met: true|false
    evidence: <description>
all_runs:
  - run_id: <id>
    metrics: {...}
completed_at: <timestamp>
```

**comparison-guidelines.md** specifies:
- **Run comparison approach**: Compare all runs by primary metric, identify best performer
- **Success assessment logic**: Check each success criterion against results, document evidence
- **Baseline comparison**: Calculate improvement percentage, consider direction (minimize vs maximize)
- **W&B Analyst delegation criteria**: Delegate when >5 runs, when metrics show unexpected patterns, when user requests detailed analysis

Uses file reading tools to parse run.yaml files and aggregate metrics.

### 6. finalize-experiment Skill

**Purpose**: Verify experiment completeness and propose safe Git commits

**Components**:
- `references/completion-checklist.md` - required files and validation
- `references/git-safety.md` - commit safety rules

**Design Details**:

**completion-checklist.md** defines:
- **Required files verification**:
  - `plan.md` exists and has approved status
  - `jobs/*.yaml` files exist and match plan
  - At least one run directory exists in `runs/`
  - `results.yaml` exists and is valid
  - `history.md` updated with run details
  - `journal.md` contains final conclusions
  - `project-log.md` reflects project-level outcomes
- **Artifact link validation**: Check that W&B run IDs and HF checkpoint paths in results.yaml are properly formatted
- **Commit proposal format**: List files to commit, provide commit message template, summarize experiment outcome

**git-safety.md** specifies:
- **Never commit**: `*.pth`, `*.pt`, `*.bin`, `*.safetensors` (checkpoints), `*.env` (secrets), `wandb/` (cache), `*.out`, `*.err` (raw Slurm logs), `__pycache__/`, `.DS_Store`
- **Secret detection patterns**: Regex for API keys, tokens, passwords in files before commit
- **Large file detection**: Warn if any file >10MB, block if >50MB

Uses git tools and file scanning, no custom scripts needed.

## Script Interface Design

All helper scripts follow a consistent interface pattern:

**Command-line interface**:
```
script_name.py --required-arg VALUE [--optional-arg VALUE] [--dry-run]
```

**Arguments**:
- All file paths are explicit arguments (no cwd assumptions)
- Use `--workspace PATH` for workspace root when needed
- Use `--dry-run` for state-changing operations

**Output format** (always JSON on stdout):
```json
{
  "status": "success|error",
  "message": "<human-readable summary>",
  "data": { ... },
  "errors": [ ... ],
  "warnings": [ ... ]
}
```

**Error handling**:
- Missing files: `{"status": "error", "message": "File not found: <path>", "errors": [...]}`
- Invalid data: `{"status": "error", "message": "Invalid YAML: <details>", "errors": [...]}`
- Exit codes: 0 for success, 1 for validation errors, 2 for runtime errors

**Testing hooks**:
- Scripts accept input via arguments (not stdin) for testability
- Support `--help` for usage information
- Provide `--version` for version tracking

## Data Models

### Job Configuration (YAML)

```yaml
job_id: string (required)
type: "train" | "evaluate" | "custom" (required)
entrypoint: string (required, path to script)
config_style: "argument" | "hydra" | "json" | "yaml"
matrix: dict<string, list> (optional, for ablations)
parameters: dict<string, any> (required)
resources:
  backend: "local" | "slurm"
  gpus: int
  cpus: int
  memory_gb: int
  time: string (HH:MM:SS format)
wandb:
  enabled: bool
  group: string
  tags: list<string>
huggingface:
  push: "never" | "final_only" | "milestone" | "every_save"
  repo: string | null
```

### Run Metadata (YAML)

```yaml
run_id: string
job_file: string (path)
experiment_id: string
status: "initialized" | "running" | "completed" | "failed"
created_at: string (ISO8601)
started_at: string (ISO8601, optional)
completed_at: string (ISO8601, optional)
exit_code: int (optional)
metrics: dict<string, float> (optional)
wandb_run_id: string (optional)
checkpoint_path: string (optional)
```

### Results Summary (YAML)

```yaml
experiment_id: string
status: "completed" | "partial" | "failed"
best_run:
  run_id: string
  checkpoint: string
  metrics: dict<string, float>
baseline:
  name: string
  metrics: dict<string, float>
comparison:
  improvement: float (percent)
  meets_success_criteria: bool
success_criteria_assessment:
  - criterion: string
    met: bool
    evidence: string
all_runs: list<run_summary>
completed_at: string (ISO8601)
```

## Error Handling

**File Not Found**:
- Scripts detect missing files early
- Provide absolute paths in error messages
- Suggest likely causes (e.g., "Did you run from workspace root?")

**Invalid YAML/JSON**:
- Report parsing errors with line numbers
- Provide snippet of problematic content
- Suggest fix if pattern is recognized

**Quota Violations**:
- Calculate current usage + requested resources
- Show quota limit and overage amount
- Suggest resource adjustments

**Environment Issues**:
- Detect missing environment managers gracefully
- Provide installation instructions in error message
- Support fallback to system Python with warning

## Testing Strategy

### Unit Tests
- Test each script independently with various inputs
- Mock file system operations where appropriate
- Verify JSON output parsing
- Test error conditions (missing files, invalid YAML)

### Integration Tests
- Test with `experiments/example-lora-rank-ablation/`
- Run full workflow: validate → initialize → track completion
- Verify generated files match schemas
- Test cross-skill references (e.g., finalize reads plan outputs)

### Property-Based Tests
- Generate random job configurations and verify validation logic
- Test run initialization with various experiment structures
- Verify scripts work from different working directories

## Phase 2 Limitations

**Explicitly NOT implemented**:
- SSH execution (Phase 6)
- Slurm job submission (Phase 6)
- W&B API calls for run analysis (Phase 7)
- HuggingFace Hub uploads (Phase 8)

**Placeholder support**:
- W&B configuration in job YAML (validated but not used)
- HF Hub configuration in job YAML (validated but not used)
- Slurm resource specifications (documented but local execution only)

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Job Validation Completeness

*For any* job configuration file, when validate_job.py processes it, the script SHALL check all required fields (job_id, type, entrypoint, parameters, resources), verify the entrypoint file exists, validate resource specifications against quotas if provided, and output structured JSON results indicating validation status and any errors found.

**Validates: Requirements 4.14, 4.15, 4.16, 4.17**

### Property 2: Run Initialization Consistency

*For any* valid job configuration and experiment directory, when initialize_run.py creates a run, the script SHALL generate a properly formatted Run ID, create the complete directory structure (run dir, logs subdir), write a valid run.yaml with initialized status, copy the job configuration to resolved-job.yaml, and output structured JSON metadata containing the run ID and created file paths.

**Validates: Requirements 4.18, 4.19, 4.20, 4.21, 4.22**

### Property 3: Script Interface Compliance

*For any* helper script in the scripts/ directory, when invoked with explicit file path arguments, the script SHALL produce identical results regardless of the current working directory, output structured JSON on stdout, support --dry-run flag if it modifies state, handle missing input files gracefully with clear error messages, and complete execution without importing from project src/ directory.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.6, 7.7**

### Property 4: Template YAML Validity

*For any* asset template file with .yaml extension, parsing the template content SHALL produce valid YAML structure with all required top-level keys present (job_id, type, entrypoint for job templates), and all placeholder values SHALL be clearly marked with angle brackets (e.g., `<model-name>`) to prevent accidental use of unresolved templates.

**Validates: Requirements 3.3, 3.4, 10.3**

### Property 5: Template Markdown Structure

*For any* asset template file with .md extension that includes YAML frontmatter, the file SHALL begin with `---` delimiter, contain valid YAML between delimiters, close with `---` delimiter, and have well-formed Markdown content after the frontmatter, with all required frontmatter fields defined in the schema present with placeholder values.

**Validates: Requirements 3.2, 10.4**

## Implementation Notes

**Python Version**: Scripts target Python 3.8+ for broad compatibility

**Dependencies**: Minimize external dependencies, prefer standard library:
- `argparse` for CLI parsing
- `json` and `yaml` (PyYAML) for data formats
- `pathlib` for path handling
- `datetime` for timestamps

**Code Style**: Follow PEP 8, use type hints, include docstrings

**Testing**: Use pytest for unit tests, support `pytest --cov` for coverage

**Documentation**: Each script includes `--help` with usage examples

**Logging**: Scripts output to stdout (JSON), may write verbose logs to stderr for debugging

## Future Extensibility

Design choices that support future phases:

- **SSH/Slurm**: Scripts accept `--backend` parameter (local only in Phase 2)
- **W&B API**: Configuration validated but not used, ready for Phase 7 integration
- **HF Hub**: Push policy validated but not executed, ready for Phase 8 integration
- **Matrix Expansion**: Job matrix structure supports complex ablations (Phase 5)
- **Subagent Delegation**: References document when to call W&B Analyst, Slurm Debugger (Phase 9)

## Security Considerations

- Scripts validate paths to prevent directory traversal
- Secret detection patterns prevent accidental Git commits of credentials
- No execution of arbitrary code from configuration files
- Dry-run mode allows review before state changes
- Large file detection prevents repository bloat
