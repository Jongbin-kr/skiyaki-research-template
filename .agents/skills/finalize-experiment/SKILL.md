# Finalize Experiment Skill

## Purpose

Verify experiment completeness, update documentation, and propose Git commit.

## Prerequisites

- Training runs completed
- Evaluation completed
- Results drafted

## When to Use

After evaluation completes and results are drafted, use this skill to:
- Verify all required artifacts exist and are properly referenced
- Finalize experiment documentation (results.yaml, history.md, journal.md)
- Update project-level log with conclusions
- Review Git changes and propose a commit

## When NOT to Use

- During active training or evaluation
- Before results are drafted
- When experiment is blocked or requires re-planning

## Procedure

### 1. Verify Completeness

Check that all required experiment artifacts exist and are valid:

- **Run Completion**:
  - Verify all required training runs have status "succeeded" in their run.yaml files
  - If runs failed, verify explicit failure explanation exists in history.md and journal.md
  - Verify evaluation run completed with status "succeeded"

- **Results Validation**:
  - Verify results.yaml exists in experiment root
  - Verify results.yaml references actual run IDs that exist in runs/ directory
  - Verify primary metric is recorded with numeric value
  - Verify baseline comparison is documented (if applicable)
  - Verify success criteria assessment is documented with clear rationale

- **Tracking Artifacts** (Phase-dependent):
  - Phase 7+: Verify W&B run URLs are recorded in run.yaml files
  - Phase 8+: Verify HF artifact upload records exist (if push policy requires)

- **Documentation Files**:
  - Verify history.md exists and contains chronological execution records
  - Verify plan.md exists and status field reflects completion state

### 2. Update Documentation

Finalize all experiment documentation files:

#### 2.1 Finalize results.yaml

Review and complete the drafted results.yaml:

- Verify best_run section references the correct run_id and checkpoint
- Verify primary_metric includes name, value, and direction
- If baseline exists, verify baseline_value and improvement percentage
- Add secondary_metrics as documented in evaluation
- Fill success section:
  - criteria_met: true/false based on success criteria in plan.md
  - rationale: explain why criteria were/weren't met
  - caveats: note any limitations or unexpected results
- Fill artifacts section (Phase 8+):
  - checkpoint: HF Hub URL or local path
  - wandb_runs: list of W&B run URLs
  - figures: list of saved visualizations
- Add resource_usage section:
  - total_gpu_hours: sum across all runs
  - total_cost: if cost tracking is enabled
  - peak_memory_gb: maximum memory used

#### 2.2 Update history.md

Append final completion entry to history.md:

```markdown
## [YYYY-MM-DD HH:MM] — Experiment Completed

- **Status**: Completed
- **Best Run**: <run-id>
- **Primary Metric**: <metric-name> = <value>
- **Baseline**: <baseline-value> (improvement: <percentage>)
- **Success Criteria**: <Met/Not Met> - <brief rationale>
- **Artifacts**:
  - Checkpoint: <path-or-url>
  - W&B: <run-url>
  - HF Hub: <model-url>
```

Include timestamp, best run reference, final metric values, success determination, and artifact locations.

#### 2.3 Write journal.md

Create or append to journal.md with interpretive analysis:

```markdown
# Experiment Journal: <Experiment ID>

## Final Entry — [YYYY-MM-DD]

### Hypothesis Assessment

**Original Hypothesis**: <state the hypothesis from plan.md>

**Result**: <Supported / Refuted / Unclear>

**Evidence**: <explain what the results show>

### Key Findings

1. <Most important finding>
2. <Second most important finding>
3. <Additional findings...>

### Unexpected Results

- <Any surprising outcomes>
- <Deviations from expectations>

### Limitations and Caveats

- <Methodological limitations>
- <Data or resource constraints>
- <Threats to validity>

### Interpretation

<Deeper analysis of what these results mean for the research question>

<How do these results connect to prior work?>

<What are the implications for future experiments?>

### Recommended Next Experiments

1. <Follow-up experiment idea>
   - Rationale: <why this is worth investigating>
   - Expected outcome: <what you'd learn>

2. <Alternative direction>
   - Rationale: <why this is worth investigating>
   - Expected outcome: <what you'd learn>

### Notes

<Any additional context, observations, or reminders for future reference>
```

The journal should:
- Assess whether the hypothesis was supported, refuted, or unclear
- List key findings and insights in order of importance
- Document unexpected results and surprises
- Note limitations and caveats that affect interpretation
- Provide interpretation connecting results to research objectives
- Suggest specific next experiments with rationale

### 3. Update Project Log

Add an entry to project-log.md at the repository root:

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

The project log entry should:
- Use reverse chronological order (newest first)
- Provide a concise one-line conclusion
- Link to the experiment directory
- Include key metric values with baseline comparison
- Note the next recommended steps

### 4. Review Git Changes

Examine all modified and new files to ensure they are commit-safe:

#### 4.1 List Changed Files

Use git status or similar to identify:
- New files (experiment plan, jobs, results, documentation)
- Modified files (project-log.md, any source code changes)
- Untracked files that should be added

#### 4.2 Security Review

Verify NO sensitive information is included:
- ❌ No secrets, API tokens, or authentication credentials
- ❌ No .env files or *.token files
- ❌ No personal information or sensitive data
- ❌ No internal hostnames or infrastructure details

#### 4.3 Artifact Review

Verify NO large artifacts are included:
- ❌ No model checkpoints (*.pt, *.bin, *.safetensors files)
- ❌ No W&B cache directories (wandb/)
- ❌ No raw Slurm logs (*.out, *.err files in runs/*/logs/)
- ❌ No large datasets or outputs

#### 4.4 Content Review

Verify appropriate content is included:
- ✅ Experiment plan (plan.md)
- ✅ Job configurations (jobs/*.yaml)
- ✅ Run tracking summaries (runs/*/run.yaml)
- ✅ Results and documentation (results.yaml, history.md, journal.md)
- ✅ Updated project log (project-log.md)
- ✅ Source code changes (if any)
- ✅ Updated .gitignore (if needed)

#### 4.5 History Verification

Ensure history.md contains summaries, not full logs:
- ✅ Execution events with timestamps and status
- ✅ Key metrics and outcomes
- ❌ NOT full stdout/stderr from runs

### 5. Propose Commit

Generate a well-structured commit message and present it for user approval:

#### 5.1 Commit Message Format

```
Complete <experiment-id>: <one-line summary>

<Blank line>

Key Changes:
- Completed <N> training runs with <primary-metric> = <value>
- <Success/failure> against success criteria (<brief rationale>)
- <Key finding or insight>
- Updated project log with conclusions

Experiment Details:
- Best Run: <run-id>
- Primary Metric: <metric-name> = <value> (<improvement>)
- Baseline: <baseline-value>
- W&B: <run-url> (Phase 7+)
- HF Hub: <model-url> (Phase 8+)

Next Steps:
- <Recommended follow-up work>
```

The commit message should:
- Start with "Complete <experiment-id>:" for consistency
- Provide one-line summary of the main finding
- Use bulleted list for key changes
- Include experiment details (run ID, metrics, artifacts)
- Note recommended next steps

#### 5.2 Present Proposal

Present the following to the user for review:

1. **Files to be committed**: Full list of new and modified files
2. **Commit message**: Formatted as above
3. **Summary**: Key findings and success determination
4. **Artifacts**: Locations of checkpoints and tracked runs
5. **Risks**: Any remaining issues or missing artifacts

#### 5.3 Request Approval

Explicitly ask the user:

> "I've verified experiment completeness and prepared a commit. The files above will be committed with the message shown. Should I proceed with the commit?"

Wait for explicit approval before proceeding.

### 6. Execute Commit (After Approval)

If user approves:

```bash
git add <list-of-files>
git commit -m "<commit-message>"
```

If user requests changes:
- Update the specified files
- Re-run verification checks
- Present updated proposal

## Output

After completing finalization:

- ✅ Finalized results.yaml in experiment directory
- ✅ Completed history.md with final entry
- ✅ Written journal.md with analysis and recommendations
- ✅ Updated project-log.md with project-level conclusion
- ✅ Git commit proposal with file list and message
- ✅ Verification report confirming no secrets or large artifacts

## Prohibited Actions

**DO NOT**:
- ❌ Create commits without explicit user approval
- ❌ Claim experiment success without verifying artifact references exist
- ❌ Proceed if required documentation is missing
- ❌ Commit secrets, tokens, credentials, or authentication files
- ❌ Commit model checkpoints or large binary artifacts
- ❌ Commit W&B cache directories or raw Slurm logs
- ❌ Auto-push commits to remote without user confirmation
- ❌ Modify prior experiment results or history entries
- ❌ Skip verification steps to speed up the process

## Completeness Checklist

Before proposing a commit, verify ALL items:

- [ ] All required runs completed successfully OR failures documented
- [ ] results.yaml exists and references valid run IDs
- [ ] Primary metric recorded with numeric value
- [ ] Success criteria assessment documented with rationale
- [ ] history.md has final completion entry
- [ ] journal.md has interpretive analysis and next steps
- [ ] project-log.md updated with project-level conclusion
- [ ] W&B run URLs recorded (Phase 7+)
- [ ] HF artifacts uploaded per push policy (Phase 8+)
- [ ] No secrets, tokens, or credentials in files
- [ ] No checkpoints or large artifacts staged
- [ ] No W&B caches or raw logs staged
- [ ] Commit message follows standard format

## Phase-Specific Behavior

### Phase 1 (Local Execution Only)
- Skip W&B verification
- Skip HF Hub verification
- Focus on local run completion and documentation

### Phase 6 (SSH + Slurm)
- Verify Slurm job IDs recorded in run.yaml
- Check for Slurm-specific errors in history.md

### Phase 7 (W&B Integration)
- Verify W&B run URLs in all run.yaml files
- Include W&B comparison in commit message
- Verify sync status is "synced" or document offline mode

### Phase 8 (HF Hub Integration)
- Verify checkpoints uploaded per push policy
- Verify model card exists (if applicable)
- Include HF Hub URLs in commit message and results.yaml

## Error Handling

If verification fails:

1. **Missing Required Runs**:
   - Report which runs are missing
   - Check if runs are still in progress
   - If failed, verify failure documentation exists

2. **Invalid References**:
   - Report which run IDs in results.yaml don't exist
   - Suggest correcting the reference or re-running evaluation

3. **Missing Documentation**:
   - Report which files are missing
   - Provide templates for missing files
   - Offer to create skeleton entries

4. **Security Issues**:
   - Report which files contain secrets or sensitive information
   - DO NOT proceed with commit
   - Ask user to remove sensitive content

5. **Large Artifacts**:
   - Report which large files are staged
   - Remind user of .gitignore policy
   - Ask if artifacts should be uploaded to HF Hub instead

## Examples

### Example 1: Successful Experiment

```
Experiment: lora-rank-ablation
Status: All runs succeeded
Primary Metric: accuracy = 0.874 (+2.1% over baseline)
Success Criteria: Met (improvement > 0.02)

Finalization:
✅ results.yaml complete with best run reference
✅ history.md updated with completion entry
✅ journal.md written with findings and next steps
✅ project-log.md updated
✅ No secrets or large artifacts

Commit Proposal:
Complete lora-rank-ablation: LoRA rank 16 provides best accuracy/efficiency tradeoff

Ready to commit 8 files. Proceed?
```

### Example 2: Experiment with Unexpected Results

```
Experiment: learning-rate-sweep
Status: All runs succeeded
Primary Metric: loss = 0.42 (no improvement over baseline)
Success Criteria: Not met (expected improvement > 0.05)

Finalization:
✅ results.yaml complete, notes unexpected result
✅ history.md updated with completion entry
✅ journal.md documents investigation into unexpected behavior
✅ project-log.md updated with recommendation to revisit hypothesis
✅ No secrets or large artifacts

Commit Proposal:
Complete learning-rate-sweep: No improvement observed, hypothesis requires revision

Ready to commit 9 files. Proceed?
```

### Example 3: Blocked Finalization

```
Experiment: multi-task-training
Status: Evaluation incomplete
Issue: Evaluation run shows status "running" but process is stuck

❌ Cannot finalize: evaluation incomplete
❌ Missing final metrics in results.yaml

Recommendation:
1. Check evaluation process status
2. If stuck, cancel and re-run evaluation
3. Return to finalize-experiment after evaluation completes

Do NOT proceed with commit until evaluation completes.
```

## Related Skills

- **evaluate-llm**: Should be completed before finalize-experiment
- **discover-prior-research**: Can reference when suggesting next experiments
- **plan-ml-experiment**: May be invoked for recommended follow-up work

## Related Documentation

- `templates/results.yaml`: Result file structure
- `templates/history.md`: History entry format
- `templates/journal.md`: Journal entry format
- `project-log.md`: Project-level log format
- `AGENTS.md`: Workflow rules and completion criteria
