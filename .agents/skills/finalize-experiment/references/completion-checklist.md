# Experiment Completion Checklist

This document defines the verification requirements for experiment completion, specifying what files must exist, how to validate artifact references, and the format for proposing Git commits.

## Overview

The finalize-experiment skill uses this checklist to ensure experiments are properly completed, documented, and ready for version control. All items must be verified before proposing a Git commit.

## Required Files Verification

### 1. Experiment Plan
**File**: `experiments/<experiment-id>/plan.md`

**Verification**:
- File exists and is readable
- Contains valid YAML frontmatter between `---` delimiters
- Frontmatter includes required fields:
  - `experiment_id: <string>`
  - `status: <string>` (should be "completed" or "partial")
  - `primary_metric: <object>` with `name` and `direction`
  - `success_criteria: <list>`
  - `jobs: <list>`
- Frontmatter includes approval section with:
  - `approval.status: "approved"`
  - `approval.approved_at: <timestamp>`
- Markdown body contains research objective and design rationale

**Failure Handling**:
- If plan.md missing: BLOCK finalization, report error
- If status not "completed"/"partial": WARN, ask user to confirm
- If approval.status not "approved": BLOCK, experiment never approved for execution

### 2. Job Configuration Files
**Files**: All YAML files referenced in `plan.md` frontmatter `jobs` list

**Verification**:
- Each referenced job file exists in `experiments/<experiment-id>/jobs/`
- Each job file is valid YAML
- Each job contains required top-level keys:
  - `job_id: <string>`
  - `type: <"train"|"evaluate"|"custom">`
  - `entrypoint: <path>`
  - `parameters: <object>`
  - `resources: <object>`

**Failure Handling**:
- If any job file missing: BLOCK finalization, list missing files
- If job file invalid YAML: BLOCK finalization, report parsing error
- If job missing required keys: WARN, document in commit message

### 3. Run Directories
**Location**: `experiments/<experiment-id>/runs/`

**Verification**:
- At least one run directory exists
- Each run directory follows naming convention: `<type>-<job-id>__<timestamp>`
- Each run directory contains:
  - `run.yaml` - run metadata file
  - `resolved-job.yaml` - job configuration snapshot
  - `logs/` subdirectory (may be empty if logs not yet generated)

**Run Metadata Verification** (`run.yaml`):
- Contains required fields:
  - `run_id: <string>`
  - `job_file: <path>`
  - `status: <string>`
  - `created_at: <timestamp>`
- If status is "completed":
  - `completed_at: <timestamp>` exists
  - `exit_code: <int>` exists
- If status is "failed":
  - Failure documented in `history.md`

**Failure Handling**:
- If no run directories exist: BLOCK finalization, no runs were executed
- If run.yaml missing: WARN, document incomplete run tracking
- If all runs have status "failed": WARN, ask user to confirm experiment failure
- If run status is "running": WARN, suggest waiting for completion or canceling

### 4. Results File
**File**: `experiments/<experiment-id>/results.yaml`

**Verification**:
- File exists and is valid YAML
- Contains required top-level keys:
  - `experiment_id: <string>` (matches directory name)
  - `best_run: <object>` with `run_id`, `checkpoint`, metrics
  - `primary_metric: <object>` with `name`, `value`
  - `success: <object>` with `criteria_met`, `rationale`
  - `completed_at: <timestamp>`
- `best_run.run_id` references an actual run directory in `runs/`
- `primary_metric.name` matches the metric in `plan.md`
- All numeric metric values are valid numbers (not null, not string)

**Optional but Recommended**:
- `secondary_metrics: <list>` - additional metrics tracked
- `all_runs: <list>` - summary of all runs for comparison
- `findings: <list>` - key insights from experiment
- `limitations: <list>` - known limitations and caveats
- `recommendations: <object>` - recommended next steps

**Failure Handling**:
- If results.yaml missing: BLOCK finalization, no results documented
- If best_run.run_id doesn't exist: ERROR, invalid reference
- If primary_metric missing or invalid: ERROR, incomplete results
- If success section missing: WARN, ask user to assess criteria

### 5. History File
**File**: `experiments/<experiment-id>/history.md`

**Verification**:
- File exists and is readable
- Contains chronological entries in Markdown format
- Latest entry indicates completion status
- All run executions are documented with:
  - Timestamp
  - Run ID
  - Status (succeeded/failed)
  - Key metrics (for completed runs)

**Entry Format** (example):
```markdown
## [YYYY-MM-DD HH:MM] — <Event Description>

- **Status**: <status>
- **Run ID**: <run-id> (if applicable)
- **Metrics**: <key-metrics> (if applicable)
- **Details**: <additional-context>
```

**Final Entry Requirements**:
- Title indicates completion: "Experiment Completed" or "Experiment Failed"
- Includes best run reference
- Includes primary metric value
- Includes success determination

**Failure Handling**:
- If history.md missing: WARN, create skeleton file, ask user to fill
- If no completion entry: WARN, offer to generate from results.yaml
- If entries don't match runs/: WARN, document discrepancy

### 6. Journal File
**File**: `experiments/<experiment-id>/journal.md`

**Verification**:
- File exists and is readable
- Contains interpretive analysis (not just execution log)
- Includes sections:
  - **Hypothesis Assessment**: Was hypothesis supported/refuted?
  - **Key Findings**: Most important discoveries
  - **Interpretation**: What the results mean
  - **Recommended Next Experiments**: Follow-up work

**Quality Indicators**:
- Analysis connects results to research objectives
- Findings are specific and evidence-based
- Recommendations are actionable and justified
- Limitations are acknowledged

**Failure Handling**:
- If journal.md missing: WARN, offer template, ask user to provide analysis
- If journal is only execution log: WARN, request interpretive content
- If recommendations missing: WARN, suggest user add next steps

### 7. Project Log
**File**: `project-log.md` (at repository root)

**Verification**:
- File exists at workspace root
- Contains entry for this experiment
- Entry is in reverse chronological order (newest first)
- Entry includes:
  - Date in `## [YYYY-MM-DD]` format
  - Experiment title
  - One-line conclusion
  - Link to experiment directory
  - Key metrics
  - Next steps recommendation

**Entry Format**:
```markdown
## [YYYY-MM-DD] — <Experiment Title>

- **Conclusion**: <One-line summary of main finding>
- **Best Run**: `<run-id>`
- **Experiment**: `experiments/<experiment-id>/`
- **Key Metrics**: 
  - <Primary Metric>: <value> (<improvement> over baseline)
  - <Secondary Metric>: <value>
- **Next Steps**: <Brief note on recommended follow-up work>

---
```

**Failure Handling**:
- If project-log.md missing: CREATE file with experiment entry
- If entry for experiment missing: ADD entry
- If entry not at top: WARN, offer to reorder
- If entry incomplete: WARN, offer to complete from results.yaml

## Artifact Link Validation

Verify that external artifact references are properly formatted and documented.

### W&B Run IDs (Phase 7+)

**Location**: `experiments/<experiment-id>/runs/<run-id>/run.yaml`

**Field**: `wandb_run_id: <string>`

**Format Requirements**:
- 8-character alphanumeric string (e.g., `"2a3b4c5d"`)
- OR full W&B URL format: `"https://wandb.ai/<entity>/<project>/runs/<run-id>"`

**Verification**:
- Check if `wandb.enabled: true` in job configuration
- If enabled, verify `wandb_run_id` exists in run.yaml
- Validate format matches expected pattern
- For Phase 2: Accept placeholder or null (W&B not yet integrated)

**Failure Handling**:
- If W&B enabled but run_id missing: WARN, document missing tracking link
- If format invalid: ERROR, provide correct format example
- If Phase 7+: Consider calling W&B Analyst subagent to verify runs exist

### HuggingFace Checkpoint Paths (Phase 8+)

**Location**: 
- `experiments/<experiment-id>/results.yaml` → `best_run.checkpoint`
- `experiments/<experiment-id>/runs/<run-id>/run.yaml` → `checkpoint_path`

**Format Requirements**:
- HF Hub format: `"<namespace>/<repo-name>"` (e.g., `"my-lab/roberta-base-sst2-lora-r16"`)
- OR local path: `"experiments/<experiment-id>/runs/<run-id>/checkpoints/<checkpoint-name>"`
- OR explicit URL: `"https://huggingface.co/<namespace>/<repo-name>"`

**Verification**:
- Check if `huggingface.push` in job configuration is not `"never"`
- If push policy requires upload, verify checkpoint reference exists
- For Hub paths, verify format is valid (namespace/repo pattern)
- For local paths, verify directory exists (Phase 2 only)
- For Phase 2: Accept local paths only (Hub upload not yet integrated)

**Failure Handling**:
- If push policy requires upload but checkpoint missing: ERROR, checkpoint not saved
- If local checkpoint path invalid: ERROR, file not found
- If Hub format invalid: WARN, provide correct format
- If Phase 8+: Consider checking if Hub repo exists and is accessible

### Artifact Consistency Checks

**Cross-Reference Validation**:
1. `results.yaml` → `best_run.checkpoint` should match best run's `run.yaml` → `checkpoint_path`
2. `results.yaml` → `best_run.run_id` should reference existing directory in `runs/`
3. All W&B run IDs should use consistent entity and project from `plan.md`
4. All HF repos should use consistent namespace from project-plan.md

**Failure Handling**:
- If references inconsistent: ERROR, document discrepancy, ask user to clarify
- If run_id mismatch: ERROR, results reference wrong run
- If namespace inconsistent: WARN, verify user intended different namespace

## Commit Proposal Format

After all verification passes, generate a structured Git commit proposal.

### Commit Message Template

```
<type>(<scope>): <one-line summary>

<blank line>

<body>

<blank line>

<footer>
```

**Type**: Always `"feat"` for completed experiments

**Scope**: `<experiment-id>`

**One-line Summary**: Brief description of experiment outcome (max 72 characters)

**Body**: Multi-line description with structured sections

**Footer**: Optional references (e.g., "Closes #123")

### Detailed Format

```
feat(experiment-id): <Primary finding in ≤72 chars>

Complete <experiment-id> experiment.

Research Objective:
<One-line summary of research question>

Results:
- Primary Metric: <metric-name> = <value> (<direction> by <improvement>)
- Success Criteria: <Met|Not Met>
- Best Run: <run-id>
- Baseline: <baseline-name> = <baseline-value>

Key Findings:
- <Finding 1>
- <Finding 2>
- <Finding 3>

Artifacts:
- Checkpoint: <checkpoint-path>
- W&B: <wandb-run-url> (Phase 7+)
- HF Hub: <huggingface-repo-url> (Phase 8+)

Resources Used:
- Total GPU Hours: <gpu-hours>
- Total Runs: <run-count>
- Duration: <duration>

Next Steps:
<Recommended follow-up work from journal.md>

Files:
- experiments/<experiment-id>/plan.md
- experiments/<experiment-id>/jobs/*.yaml
- experiments/<experiment-id>/runs/<run-id>/run.yaml
- experiments/<experiment-id>/results.yaml
- experiments/<experiment-id>/history.md
- experiments/<experiment-id>/journal.md
- project-log.md
```

### Commit Message Generation Rules

1. **One-line Summary**:
   - Start with primary finding or outcome
   - Use present tense: "improve", "demonstrate", "confirm", "refute"
   - Keep under 72 characters
   - Examples:
     - `"LoRA rank 16 provides best accuracy-efficiency tradeoff"`
     - `"Learning rate 2e-4 improves convergence by 15%"`
     - `"Hypothesis refuted: larger batch sizes degrade performance"`

2. **Results Section**:
   - Always include primary metric with value and improvement
   - State success criteria determination (Met/Not Met)
   - Reference best run ID
   - Include baseline comparison if applicable

3. **Key Findings**:
   - List 2-4 most important discoveries
   - Focus on actionable insights
   - Cite evidence (metric values, comparisons)

4. **Artifacts**:
   - List all relevant artifact links (checkpoints, W&B, HF)
   - Use placeholders for phases not yet implemented
   - Ensure links are accessible and formatted correctly

5. **Next Steps**:
   - Copy recommended next steps from journal.md
   - Keep concise (1-2 sentences or bullets)
   - Focus on immediate follow-up, not long-term vision

6. **Files**:
   - List all files included in commit
   - Use relative paths from workspace root
   - Group by experiment vs project-level files

### Example Commit Messages

**Example 1: Successful Experiment**

```
feat(lora-rank-ablation): LoRA rank 16 provides best accuracy-efficiency tradeoff

Complete lora-rank-ablation experiment.

Research Objective:
Determine optimal LoRA rank for fine-tuning Llama-2-7b on Wikitext-103.

Results:
- Primary Metric: perplexity = 27.1 (improved by 4.2%)
- Success Criteria: Met (improvement > 2%)
- Best Run: train-r16__20250115T142530
- Baseline: Full fine-tuning = 28.3

Key Findings:
- Performance saturates between rank 16 and 32 (diminishing returns)
- Rank 16 achieves 27.1 perplexity with 23% of full model parameters
- Training time scales linearly with rank (4.3h for rank 16)

Artifacts:
- Checkpoint: my-lab/llama2-7b-wikitext-lora-r16
- Runs: experiments/lora-rank-ablation/runs/

Resources Used:
- Total GPU Hours: 34 hours
- Total Runs: 5 (4 training + 1 evaluation)
- Duration: 10 hours (parallel execution)

Next Steps:
Test rank 16 on additional datasets to verify generalization.

Files:
- experiments/lora-rank-ablation/plan.md
- experiments/lora-rank-ablation/jobs/train.yaml
- experiments/lora-rank-ablation/jobs/evaluate.yaml
- experiments/lora-rank-ablation/runs/train-r16__20250115T142530/run.yaml
- experiments/lora-rank-ablation/results.yaml
- experiments/lora-rank-ablation/history.md
- experiments/lora-rank-ablation/journal.md
- project-log.md
```

**Example 2: Experiment with Unexpected Results**

```
feat(learning-rate-sweep): Hypothesis refuted: higher LR degrades performance

Complete learning-rate-sweep experiment.

Research Objective:
Determine if higher learning rates accelerate convergence for RoBERTa fine-tuning.

Results:
- Primary Metric: loss = 0.42 (no improvement over baseline)
- Success Criteria: Not Met (expected improvement > 5%)
- Best Run: train-lr2e4__20250116T093000
- Baseline: Standard LR (2e-4) = 0.41

Key Findings:
- Higher learning rates (>2e-4) degrade final performance
- Learning rate 2e-4 remains optimal despite longer convergence
- Aggressive LR schedules cause training instability after epoch 2

Artifacts:
- Checkpoint: my-lab/roberta-base-sst2-lr-sweep-best
- Runs: experiments/learning-rate-sweep/runs/

Resources Used:
- Total GPU Hours: 18 hours
- Total Runs: 6 (5 training + 1 evaluation)
- Duration: 6 hours (parallel execution)

Next Steps:
Investigate adaptive LR schedules (cosine decay, warmup) as alternative to fixed higher LR.

Files:
- experiments/learning-rate-sweep/plan.md
- experiments/learning-rate-sweep/jobs/train.yaml
- experiments/learning-rate-sweep/jobs/evaluate.yaml
- experiments/learning-rate-sweep/runs/train-lr2e4__20250116T093000/run.yaml
- experiments/learning-rate-sweep/results.yaml
- experiments/learning-rate-sweep/history.md
- experiments/learning-rate-sweep/journal.md
- project-log.md
```

**Example 3: Partial Experiment (Some Runs Failed)**

```
feat(multi-task-training): Partial results - single-task outperforms multi-task

Complete multi-task-training experiment (partial).

Research Objective:
Evaluate whether multi-task training improves generalization across NLP tasks.

Results:
- Primary Metric: avg_accuracy = 0.81 (declined by 3.2%)
- Success Criteria: Not Met (expected improvement > 2%)
- Best Run: train-single-task__20250117T140000
- Baseline: Single-task average = 0.837

Key Findings:
- Multi-task training underperformed single-task baseline across all tasks
- Task interference observed (negative transfer between sentiment and NER)
- Single-task models remain recommended for production use

Artifacts:
- Checkpoint: my-lab/roberta-multitask-best (underperformed)
- Runs: experiments/multi-task-training/runs/

Resources Used:
- Total GPU Hours: 42 hours
- Total Runs: 4 (2 training completed, 1 failed, 1 evaluation)
- Duration: 14 hours

Next Steps:
Investigate task-specific adapter layers to mitigate negative transfer.

Notes:
Run train-multi-all__20250117T160000 failed due to OOM error. 
Documented in history.md. Results based on successful runs only.

Files:
- experiments/multi-task-training/plan.md
- experiments/multi-task-training/jobs/train.yaml
- experiments/multi-task-training/jobs/evaluate.yaml
- experiments/multi-task-training/runs/train-single-task__20250117T140000/run.yaml
- experiments/multi-task-training/results.yaml
- experiments/multi-task-training/history.md
- experiments/multi-task-training/journal.md
- project-log.md
```

## Commit Proposal Presentation

Present the commit proposal to the user with the following structure:

```markdown
## 🎯 Experiment Finalization Ready

**Experiment**: `<experiment-id>`
**Status**: <Completed|Partial>
**Success Criteria**: <Met|Not Met>

### Verification Summary
✅ All required files present and valid
✅ Artifact references verified
✅ Documentation complete
✅ No secrets or large files staged

### Commit Proposal

**Message**:
```
<commit-message-as-generated>
```

**Files to Commit** (<N> files):
```
experiments/<experiment-id>/plan.md
experiments/<experiment-id>/jobs/train.yaml
experiments/<experiment-id>/jobs/evaluate.yaml
experiments/<experiment-id>/runs/<run-id>/run.yaml
experiments/<experiment-id>/results.yaml
experiments/<experiment-id>/history.md
experiments/<experiment-id>/journal.md
project-log.md
```

**Summary**:
- **Primary Metric**: <metric> = <value> (<improvement-description>)
- **Best Checkpoint**: `<checkpoint-path>`
- **GPU Hours**: <hours>
- **Next Steps**: <one-line-summary>

---

**Ready to commit?** Type "yes" to proceed, or provide feedback for changes.
```

## Verification Failure Handling

If verification fails, present issues clearly and offer solutions:

```markdown
## ⚠️ Verification Issues Found

Cannot finalize experiment due to the following issues:

### ❌ ERRORS (must fix before commit)
1. **Missing results.yaml**: No results file found at `experiments/<id>/results.yaml`
   - **Solution**: Run evaluate-llm skill to generate results
   
2. **Invalid run reference**: results.yaml references run "train-r16__20250115T142530" but directory doesn't exist
   - **Solution**: Correct the run_id in results.yaml or verify run directory name

### ⚠️ WARNINGS (recommended fixes)
1. **Incomplete journal.md**: Journal file missing "Recommended Next Experiments" section
   - **Solution**: Add follow-up experiment recommendations to journal.md
   
2. **No completion entry in history.md**: Last entry is from run execution, no final summary
   - **Solution**: I can generate a completion entry from results.yaml

---

**Actions**:
- Fix ERRORS before attempting to commit
- Address WARNINGS to improve documentation quality
- Re-run finalize-experiment after corrections

**Need help fixing these issues?** Let me know which ones to address.
```

## Completion Verification Script (Future)

For automation and consistency, consider implementing a helper script:

```bash
# Future: Phase 3+
.agents/skills/finalize-experiment/scripts/verify_completion.py \
  --experiment-dir experiments/lora-rank-ablation \
  --output json
```

**Output**:
```json
{
  "experiment_id": "lora-rank-ablation",
  "complete": true,
  "errors": [],
  "warnings": [
    "history.md: No completion entry found"
  ],
  "files_verified": {
    "plan.md": "valid",
    "jobs/train.yaml": "valid",
    "jobs/evaluate.yaml": "valid",
    "runs/train-r16__20250115T142530/run.yaml": "valid",
    "results.yaml": "valid",
    "history.md": "valid_with_warnings",
    "journal.md": "valid"
  },
  "artifacts": {
    "wandb_runs": ["2a3b4c5d"],
    "checkpoints": ["my-lab/roberta-base-sst2-lora-r16"]
  },
  "ready_for_commit": true
}
```

**Note**: Script implementation deferred to Phase 3. Phase 2 uses manual verification following this checklist.

## Phase-Specific Requirements

### Phase 2 (Local Execution Only)
- ✅ Verify local file structure and documentation
- ✅ Validate YAML formats and required fields
- ✅ Check run completion status
- ⏸️ Skip W&B run validation (not integrated)
- ⏸️ Skip HF Hub upload verification (not integrated)
- ✅ Accept local checkpoint paths only

### Phase 6 (SSH + Slurm)
- ✅ Verify Slurm job IDs in run.yaml
- ✅ Check for Slurm-specific error patterns
- ✅ Validate remote path references

### Phase 7 (W&B Integration)
- ✅ Validate W&B run IDs exist and are synced
- ✅ Verify entity and project consistency
- ✅ Include W&B URLs in commit message
- ✅ Consider calling W&B Analyst for run verification

### Phase 8 (HuggingFace Hub)
- ✅ Verify checkpoints uploaded per push policy
- ✅ Check HF repo accessibility
- ✅ Validate model card exists (if applicable)
- ✅ Include HF Hub URLs in commit message

## Version History

- **Version 1** (Current): Initial completion checklist for Phase 2 (local execution only)
