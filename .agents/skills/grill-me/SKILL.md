# Grill Me Skill

## Purpose

Resolve consequential scientific choices through focused questioning before plan creation. The grill clarifies decisions only; it does not design implementation details, create planning artifacts, execute jobs, initialize Runs, or contact external systems.

## When to Use

- The research objective or hypothesis is unclear.
- The comparison baseline is undefined or unsupported by available evidence.
- The primary metric or measurable success criterion is unresolved.
- The ablation scope or a key controlled parameter changes experimental meaning.
- A user choice conflicts with repository-backed prior research.

## When NOT to Use

- The value is a populated stable `Project_Settings` entry in `project-plan.md`.
- The decision is already resolved in the current decision ledger.
- The question concerns implementation details that belong to `plan-ml-experiment`.
- Baseline, primary metric, and success criteria are resolved and remaining values can be inherited or recorded as labeled defaults.

## Required Inputs

- The current research request.
- The prior-research discovery report, including evidence references, conflicts, and unresolved baseline facts.
- Populated `Project_Settings` from `project-plan.md`; a template is not populated project configuration.
- The current decision ledger, if grilling has already begun.

Load [references/grill-policy.md](references/grill-policy.md) as the normative source for the structured turn format, canonical stable-setting keys, decision-ledger schema, and response rules.

## Procedure

1. **Initialize the decision ledger**
   - Create entries for `research_objective`, `baseline`, `primary_metric`, `success_criteria`, `ablation_scope`, and `controlled_parameters`.
   - Preserve any values resolved by the user, prior evidence, or inherited `Project_Settings`; record each value's origin.
   - Never invent an unsupported baseline value.

2. **Consume stable settings**
   - Read populated values using the canonical keys in `grill-policy.md`.
   - Mark inherited values with origin `project_setting`; do not relabel them as `agent_default`.
   - Do not ask the user to restate a populated stable setting. A missing setting may be asked only when it is material to experimental meaning, not merely to implementation.

3. **Select one Material_Decision**
   - Choose the highest-priority unresolved decision: primary metric, baseline, success criteria, then objective/scope or key controlled parameters as needed.
   - While the `Research_Grill` is active, every assistant turn MUST contain exactly one structured `Material_Decision` target and exactly one semantic question about that target.
   - Do not bundle alternatives as separate questions or append a second request for information.

4. **Resolve the answer before moving on**
   - Update or refine the matching ledger entry before selecting another decision.
   - For an insufficient answer, ask one focused follow-up on the same decision or propose one clearly labeled `Agent_Default` with rationale and evidence or an explicit assumption.
   - For an evidence conflict, ask one focused clarification that distinguishes an intentional deviation from a misunderstanding; do not silently override either source.

5. **Terminate the grill**
   - Continue grilling while any of `baseline`, `primary_metric`, or `success_criteria` is unresolved.
   - Stop immediately once those three critical decisions are resolved and the required ledger record can be completed. Do not ask about implementation details or populated stable settings.
   - Return the completed decision ledger to `plan-ml-experiment`. Approval-summary generation remains blocked if any critical decision is unresolved.

## Output

Return a decision ledger containing:

- Research objective.
- Evidence-backed baseline or an explicit user-selected baseline.
- Primary metric, direction, and evaluation split where known.
- Measurable success criteria.
- Ablation scope.
- Key controlled parameters.
- For every entry: value, origin, rationale, evidence references or explicit assumption, and resolved state.
- Any intentional deviations from prior evidence.

## Phase 4 Boundary

This skill performs local repository reading, conversation, and decision synthesis only. It MUST NOT create or modify experiment plans, job YAML, Run directories, or Run metadata; invoke training or evaluation; use SSH or Slurm; query live W&B; access Hugging Face Hub; or create Git commits. Hand planning-ready decisions to `plan-ml-experiment` and preserve the no-execution boundary.
