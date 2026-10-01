# Plan ML Experiment Skill

## Purpose

Create reviewable experiment plans and reproducible training/evaluation job configurations after discovery and the Research Grill resolve all material scientific decisions. This skill plans only: it does not execute jobs, create Runs, contact external services, or approve its own proposal.

## Prerequisites

- `discover-prior-research` produced repository-path or Git-commit evidence and identified unsupported values.
- `grill-me` resolved the objective, evidence-backed baseline, primary metric, measurable success criterion, ablation scope, and controlled parameters.
- `project-plan.md` supplied available stable Project_Settings; missing settings are recorded rather than invented.
- The decision ledger identifies each material value's origin as `user`, `project_setting`, `prior_evidence`, or `agent_default`.

If the baseline, primary metric, or success criterion is unresolved, return to the Research Grill. Do not generate an approval request.

## Procedure

1. **Record decisions and provenance**:
   - Preserve user choices as `user`, inherited Project_Settings as `project_setting`, cited repository findings as `prior_evidence`, and agent-selected values as `agent_default`.
   - For every Agent_Default, record the value, rationale, and either a repository/Git evidence source or `explicit_assumption: true`.
   - Never relabel inherited Project_Settings as Agent_Defaults.

2. **Create the planning structure**:
   - Generate a unique kebab-case experiment ID.
   - Create `experiments/<experiment-id>/`, `jobs/`, and `figures/` for planning artifacts.
   - Do not create `runs/`, Run metadata, resolved-job snapshots, or execution logs during planning.

3. **Write `plan.md`**:
   - Start from `templates/experiment-plan.md` (schema-compatible with this skill's asset).
   - Set `schema_version: 1`, `status: awaiting_approval`, and `approval.status: pending`; leave approval identity, time, and commit null.
   - Define the primary metric and direction plus a machine-checkable success criterion with metric, comparison/operator, and threshold.
   - Define the baseline value, metric direction, evaluation dataset and split, and repository path or Git commit source. Unsupported baseline values remain unresolved and block this step.
   - Place **Agent-Determined Defaults** before detailed design and risks. Include objective, testable hypothesis, variables, controls, rationale, risks/limitations, and supported/refuted interpretations.

4. **Create reproducible jobs**:
   - Create exactly the training and evaluation jobs referenced by the plan using `templates/train-job.yaml` and `templates/evaluate-job.yaml`.
   - Training records the ablation matrix, model, dataset/split, controlled hyperparameters, seed, entrypoint, resources, tracking destination, and artifact policy.
   - Evaluation records checkpoint-resolution intent, evaluation dataset/split, primary and secondary metrics, entrypoint, resources, and the same experiment group.
   - Record field provenance in each job without embedding credentials.

5. **Apply roadmap boundaries**:
   - For GPU work in an SSH-targeted project, plan `resources.backend: slurm` and label it `planned_unverified`, unavailable until Phase 6. Do not submit or query Slurm.
   - Label W&B destinations `planned_unverified`, unavailable for live verification until Phase 7. Do not contact W&B.
   - Label Hugging Face destinations/push policy `planned_unverified`, unavailable for upload or live verification until Phase 8. Do not contact the Hub.

6. **Estimate resources**:
   - Expand the matrix to calculate training run count, then include evaluation runs.
   - Estimate wall time and aggregate GPU-hours with stated assumptions and compare requests with recorded Project_Settings quotas.
   - Treat estimates and destinations as plans, not verified availability.

7. **Validate locally before requesting approval**:
   - Parse plan frontmatter and both job YAML files locally.
   - Reject missing required keys, unresolved required placeholders, secret-like keys/values, invalid or nonexistent relative job paths, mismatched experiment IDs/groups/metrics/datasets, non-measurable criteria, unsupported baseline claims, and resource arithmetic errors.
   - Confirm defaults precede design/risks, approval remains pending, no `runs/` content exists, and no execution/external/Git action occurred.
   - If validation fails, report the local issue and remain in planning; do not present an approval request.

8. **Present the terminal Approval Summary**:
   - Only after local validation passes, present a concise terminal summary in this order: recommended plan; Agent-Determined Defaults; objective and hypothesis; evidence-backed baseline; primary metric and measurable success criterion; matrix/run count/resources; principal risks; planned/unverified W&B and Hugging Face destinations with Phase 7/8 gates; artifact paths.
   - Label planned Slurm execution unavailable until Phase 6 where applicable.
   - End by asking the user to approve or request modifications and state: no execution or Run creation has occurred.
   - Stop and wait for explicit user approval. Approval and any later execution belong to a later interaction/phase.

## Output

- `experiments/<experiment-id>/plan.md`
- `experiments/<experiment-id>/jobs/train.yaml`
- `experiments/<experiment-id>/jobs/evaluate.yaml`
- A concise Approval Summary that terminates in `awaiting_approval`

## Prohibited Actions

- Do not execute training/evaluation, initialize a Run, or create a runner/agent loop.
- Do not use SSH/Slurm, live W&B, or Hugging Face Hub operations in Phase 4.
- Do not create a Git commit or mark the plan approved without explicit user approval.
