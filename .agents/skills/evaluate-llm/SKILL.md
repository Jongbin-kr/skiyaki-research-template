# Evaluate LLM Skill

## Purpose

Run evaluation jobs, calculate metrics, and compare results against baselines.

## Prerequisites

- Training run completed successfully
- Evaluation job YAML exists
- Primary metric is defined in plan.md

## Procedure

1. **Check Training Completion**:
   - Verify required training runs have status "succeeded"
   - Identify best checkpoint based on validation metric
   - Verify checkpoint exists locally or on HF Hub

2. **Prepare Evaluation**:
   - Load evaluation job configuration
   - Verify evaluation dataset and split
   - Create evaluation run ID: <eval-job-id>__<timestamp>
   - Create runs/<eval-run-id>/ directory

3. **Execute Evaluation**:
   - Activate project environment
   - Construct evaluation command
   - Execute with proper checkpoint reference
   - Capture metrics output

4. **Calculate Metrics**:
   - Extract primary metric value
   - Extract secondary metrics (if defined)
   - Compare against baseline (from plan.md or prior experiments)
   - Calculate improvement percentage

5. **Compare W&B Runs** (Phase 1: Manual):
   - List W&B run URLs from training runs
   - Provide comparison instructions to user
   - Document comparison results

6. **Assess Success Criteria**:
   - Apply success criteria from plan.md
   - Determine if experiment succeeded or failed
   - Document assessment rationale

7. **Draft Results**:
   - Use templates/results.yaml as base
   - Fill best run reference
   - Fill primary and secondary metrics
   - Fill baseline comparison
   - Fill success assessment
   - Note any caveats or limitations

## Output

- runs/<eval-run-id>/run.yaml with evaluation status
- Drafted results.yaml (not yet committed)
- Updated history.md with evaluation entry
- Success/failure assessment with rationale
