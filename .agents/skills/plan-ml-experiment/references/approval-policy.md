# Experiment Approval Policy

This document defines the approval workflow for experiment plans, specifying when user approval is required, what changes trigger re-approval, and how to present approval requests to users.

## Overview

The approval workflow ensures users maintain control over resource allocation, research direction, and experimental rigor. Agents propose experiment plans and job configurations, but execution begins only after explicit user approval.

## Approval Workflow States

### 1. Initial Plan Creation
**Status**: `draft` → `planned` → `awaiting_approval`

**Triggers**:
- Agent completes experiment plan generation
- All required frontmatter fields populated
- All job configuration files created
- Plan narrative written with research objective, design, and risks

**Agent Actions**:
- Set `status: awaiting_approval`
- Set `approval.status: pending`
- Generate approval summary (see format below)
- Present to user with explicit approval request

**User Actions**:
- Review plan and job configurations
- Approve, reject, or request modifications

### 2. Approval Granted
**Status**: `awaiting_approval` → `approved`

**Agent Actions**:
- Set `status: approved`
- Set `approval.status: approved`
- Set `approval.approved_by: <user-identifier>`
- Set `approval.approved_at: <ISO8601-timestamp>`
- Set `approval.approved_commit: <git-commit-sha>` (if in Git repository)
- Proceed to execution phase

### 3. Approval Rejected
**Status**: `awaiting_approval` → `draft`

**Agent Actions**:
- Revert `status: draft`
- Keep `approval.status: rejected` for history
- Incorporate user feedback
- Regenerate plan based on feedback
- Return to state 1 when ready

### 4. Modifications After Approval
**Status**: `approved` → `awaiting_approval` (if re-approval required)

**Triggers**: See "Changes Requiring Re-Approval" section below

**Agent Actions**:
- Set `status: awaiting_approval`
- Set `approval.status: pending`
- Generate change summary highlighting what changed
- Present to user with re-approval request

## Changes Requiring Re-Approval

The following modifications to an approved experiment require user re-approval:

### 1. Primary Metric Change
**Examples**:
- Changing `primary_metric.name` from `perplexity` to `accuracy`
- Changing `primary_metric.direction` from `minimize` to `maximize`

**Rationale**: Changing the primary metric fundamentally alters how success is assessed and runs are compared.

**Re-approval Required**: **YES**

### 2. Success Criteria Modification
**Examples**:
- Changing `minimum_improvement` from `0.02` to `0.05`
- Adding or removing success criteria
- Modifying target metric values

**Rationale**: Success criteria define the experiment's objectives; changes affect research validity.

**Re-approval Required**: **YES**

### 3. Resource Increase >20%
**Examples**:
- Increasing GPUs from 1 to 2 (100% increase)
- Increasing memory from 32GB to 40GB (25% increase)
- Increasing time limit from 4 hours to 6 hours (50% increase)

**Calculation**:
```
percent_increase = ((new_value - old_value) / old_value) * 100
if percent_increase > 20:
    require_reapproval()
```

**Rationale**: Significant resource increases affect cost and cluster usage; user should explicitly authorize.

**Re-approval Required**: **YES** (if any resource exceeds 20% threshold)

### 4. New Jobs Added
**Examples**:
- Adding `jobs/ablation-extra.yaml` to the jobs list
- Introducing a second evaluation job

**Rationale**: New jobs change the scope and duration of the experiment.

**Re-approval Required**: **YES**

### 5. Job Configuration Matrix Expansion
**Examples**:
- Changing `lora_rank: [8, 16]` to `lora_rank: [4, 8, 16, 32]`
- Adding a new matrix dimension (e.g., adding `learning_rate: [1e-4, 2e-4]`)

**Rationale**: Matrix expansion multiplies the number of runs, significantly increasing resource usage.

**Re-approval Required**: **YES**

### 6. Hyperparameter Changes Within Approved Jobs
**Examples**:
- Changing `learning_rate: 2e-4` to `learning_rate: 3e-4`
- Adjusting `batch_size: 8` to `batch_size: 16`

**Rationale**: These are expected adjustments within the approved experimental scope.

**Re-approval Required**: **NO** (but document in history.md)

### 7. Resource Decrease or Minor Adjustments
**Examples**:
- Decreasing GPUs from 2 to 1
- Reducing time limit from 8 hours to 6 hours
- Increasing memory by 10% (under threshold)

**Rationale**: Resource decreases reduce cost; minor increases are acceptable optimizations.

**Re-approval Required**: **NO**

### 8. Documentation Updates
**Examples**:
- Adding clarifications to plan narrative
- Updating risk statements
- Correcting typos or formatting

**Rationale**: Documentation improvements don't affect execution.

**Re-approval Required**: **NO**

## Approval Summary Format

When requesting approval (initial or re-approval), present a structured summary for efficient user review.

### Standard Approval Request

```markdown
## Experiment Approval Request

**Experiment ID**: `<experiment-id>`
**Status**: Awaiting Approval

### Research Objective
<Brief 1-2 sentence summary of research question>

### Primary Metric
- **Metric**: <metric-name>
- **Direction**: <maximize|minimize>

### Success Criteria
- <criterion-1>
- <criterion-2>
- <criterion-N>

### Baseline
<If defined: baseline name and key metrics>
<If not defined: "No formal baseline defined">

### Jobs to Execute
1. **<job-id>** (`<job-file>`)
   - Type: <train|evaluate|custom>
   - Entrypoint: `<script-path>`
   - Matrix: <matrix-summary or "None">
   - Resources: <gpu-count> GPU, <cpu-count> CPU, <memory> GB RAM, <time-limit>

2. **<job-id>** (`<job-file>`)
   - ...

### Total Resource Estimate
- **Total GPU Hours**: <calculated-estimate>
- **Total Runs**: <number-of-runs>
- **Estimated Duration**: <time-estimate>

### W&B Integration
- **Enabled**: <yes|no>
- **Group**: <wandb-group>
- **Tags**: <tag-list>

### HuggingFace Integration
- **Push Policy**: <never|final_only|milestone|every_save>
- **Repository**: <hf-repo or "Auto-determined">

### Agent Recommendations
<List any parameters or design choices agent determined with rationale>
- <parameter>: <value> - <rationale>

### Risks and Limitations
<List known risks from plan.md>
- <risk-1>
- <risk-2>

---

**Review Required**: Please approve or provide feedback for modifications.
```

### Re-Approval Request (After Modification)

```markdown
## Experiment Re-Approval Required

**Experiment ID**: `<experiment-id>`
**Previous Approval**: <timestamp> by <approver>

### Changes Made
The following changes require re-approval:

1. **<Change Type>**: <change-description>
   - **Previous**: <old-value>
   - **New**: <new-value>
   - **Reason**: <why-change-was-made>

2. **<Change Type>**: <change-description>
   - ...

### Impact Assessment
- **Resource Change**: <resource-delta-summary>
- **Run Count Change**: <old-count> → <new-count>
- **Estimated Duration Change**: <old-estimate> → <new-estimate>

### Updated Summary
<Include relevant sections from standard approval format that changed>

---

**Review Required**: Changes exceed auto-approval threshold. Please review and approve.
```

## Agent Recommendations vs. User Specifications

Clearly distinguish between agent-determined values and user-specified requirements:

### User-Specified Values
- Explicitly mentioned in user's request
- Must be respected exactly
- Labeled as "User-specified" in approval summary

**Example**: User says "train for 5 epochs" → `num_epochs: 5` (user-specified)

### Agent Recommendations
- Determined by agent based on best practices, resource availability, or research norms
- Can be adjusted if user requests changes
- Labeled as "Agent recommendation" with rationale

**Example**: Agent chooses `batch_size: 8` based on memory constraints → documented in "Agent-Determined Defaults" section

### Presentation in Approval Request

```markdown
### Configuration Summary

**User-Specified Parameters**:
- `num_epochs: 5` (per user request)
- `model_name: meta-llama/Llama-2-7b-hf` (per user request)

**Agent-Determined Defaults**:
- `learning_rate: 2e-4` - Standard for LoRA fine-tuning (can adjust if needed)
- `batch_size: 8` - Optimized for 1x A100 40GB GPU memory
- `gradient_accumulation_steps: 4` - Achieves effective batch size of 32
- `warmup_steps: 100` - 10% of total steps following best practices
```

## Approval Timeout and Expiration

### No Automatic Expiration
- Approved experiments do not automatically expire
- Approval remains valid until execution begins or user explicitly revokes

### Stale Approval Warning
If significant time has passed since approval (e.g., >7 days) and experiment hasn't started:
```markdown
⚠️ **Note**: This experiment was approved <N> days ago. 
Resource availability and research context may have changed. 
Consider reviewing before execution.
```

## Multi-Experiment Batch Approval

For related experiments (e.g., hyperparameter sweep across multiple experiment directories):

### Individual Approval (Default)
- Each experiment in `experiments/<id>/` gets separate approval
- Allows fine-grained control
- User can approve subset of proposed experiments

### Batch Approval (Future Enhancement)
- Present multiple related experiments together
- Show combined resource requirements
- Allow approve-all or selective approval
- **Note**: Not implemented in Phase 2

## Approval in Non-Interactive Contexts

### Automated Workflows (Future)
For unattended execution (e.g., scheduled experiments):
- Require explicit pre-authorization in project-plan.md
- Define resource caps and auto-approval rules
- Log all auto-approved experiments for audit
- **Note**: Not implemented in Phase 2

## Security and Safety Checks

Before presenting approval request, agent MUST verify:

1. **No Secrets in Configuration**: Job files contain no API keys, tokens, or credentials
2. **Resource Quotas**: Requested resources within project quotas (from project-plan.md)
3. **Valid Paths**: All entrypoint scripts exist and are readable
4. **Dependency Conflicts**: No obvious conflicts in configuration (e.g., incompatible parameters)

If any check fails:
```markdown
❌ **Approval Blocked**: Pre-approval validation failed

**Issue**: <specific-problem>
**Resolution**: <recommended-fix>

Cannot request approval until this issue is resolved.
```

## Example Approval Interactions

### Example 1: Initial Approval

**Agent**:
```markdown
## Experiment Approval Request

**Experiment ID**: `lora-rank-ablation`
**Status**: Awaiting Approval

### Research Objective
Determine optimal LoRA rank for fine-tuning Llama-2-7b on Wikitext-103 by comparing ranks 4, 8, 16, and 32.

### Primary Metric
- **Metric**: perplexity
- **Direction**: minimize

### Success Criteria
- Achieve at least 2% improvement over full fine-tuning baseline (perplexity < 27.7)
- Identify rank with best performance-efficiency tradeoff

### Baseline
Full fine-tuning baseline: perplexity 28.3 (from experiments/full-finetune-baseline)

### Jobs to Execute
1. **train** (`jobs/train.yaml`)
   - Type: train
   - Entrypoint: `src/train.py`
   - Matrix: `lora_rank: [4, 8, 16, 32]` (4 runs)
   - Resources: 1 GPU, 8 CPU, 32 GB RAM, 08:00:00 per run

2. **evaluate** (`jobs/evaluate.yaml`)
   - Type: evaluate
   - Entrypoint: `src/evaluate.py`
   - Matrix: None (1 run, evaluates all checkpoints)
   - Resources: 1 GPU, 4 CPU, 16 GB RAM, 02:00:00

### Total Resource Estimate
- **Total GPU Hours**: ~34 hours (4 training runs × 8h + 1 eval × 2h)
- **Total Runs**: 5 (4 training + 1 evaluation)
- **Estimated Duration**: ~10 hours (if 4 GPUs available for parallel training)

### W&B Integration
- **Enabled**: Yes
- **Group**: lora-rank-ablation
- **Tags**: lora, ablation, llama2

### HuggingFace Integration
- **Push Policy**: final_only
- **Repository**: Auto-determined from project-plan.md

### Agent Recommendations
- `learning_rate: 2e-4` - Standard for LoRA fine-tuning based on published research
- `batch_size: 8` - Optimized for A100 40GB memory constraints
- `lora_alpha: 32` - Standard 2× rank scaling for alpha parameter

### Risks and Limitations
- Small dataset (Wikitext-103) may not fully demonstrate scaling behavior
- GPU memory limits prevent testing ranks >32
- Single random seed limits statistical confidence

---

**Ready to proceed?** Please review and approve to begin training.
```

**User Response**: "Approved, but reduce time limit to 6 hours per run"

**Agent Actions**:
1. Update `resources.time: "06:00:00"` in train.yaml
2. Resource decrease <20%, no re-approval needed
3. Document change in history.md
4. Set approval status to approved
5. Proceed to execution

### Example 2: Re-Approval Required

**Agent**:
```markdown
## Experiment Re-Approval Required

**Experiment ID**: `lora-rank-ablation`
**Previous Approval**: 2024-01-15T10:30:00Z by user

### Changes Made
The following changes require re-approval:

1. **Matrix Expansion**: Added more LoRA ranks to ablation study
   - **Previous**: `lora_rank: [4, 8, 16, 32]` (4 runs)
   - **New**: `lora_rank: [4, 8, 16, 32, 64, 128]` (6 runs)
   - **Reason**: User requested testing higher ranks to find upper limit

2. **Resource Increase**: Increased GPU requirement for larger ranks
   - **Previous**: 1 GPU per run
   - **New**: 2 GPUs per run (for ranks 64 and 128)
   - **Reason**: Ranks 64+ exceed single-GPU memory limits

### Impact Assessment
- **Resource Change**: +50% GPU hours (34h → 51h)
- **Run Count Change**: 4 training runs → 6 training runs
- **Estimated Duration Change**: ~10 hours → ~15 hours (if 4 GPUs available)

### Updated Total Resource Estimate
- **Total GPU Hours**: ~51 hours (6 training runs, some with 2 GPUs)
- **Total Runs**: 7 (6 training + 1 evaluation)
- **Estimated Duration**: ~15 hours (with parallel execution)

---

**Review Required**: Changes exceed 20% resource threshold. Please review and approve.
```

**User Response**: "Approved"

**Agent Actions**:
1. Update approval fields with new timestamp
2. Proceed to execution with expanded matrix

## Compliance and Audit

### Approval Audit Trail
Every approval is recorded with:
- Timestamp (ISO8601)
- Approver identity (username or session ID)
- Git commit SHA at approval time (if available)
- Configuration snapshot (preserved in approved-plan.yaml)

### Post-Execution Verification
After experiment completes, finalize-experiment skill verifies:
- Executed configuration matches approved configuration
- No unauthorized modifications were made
- All runs are accounted for

If discrepancies found:
```markdown
⚠️ **Approval Verification Warning**

Executed configuration differs from approved configuration:
- Approved: `lora_rank: [4, 8, 16, 32]`
- Executed: `lora_rank: [4, 8, 16, 32, 64]`

This suggests manual modification after approval. Please review.
```

## Version History

- **Version 1** (Current): Initial approval policy with 20% resource threshold and standard change categories
