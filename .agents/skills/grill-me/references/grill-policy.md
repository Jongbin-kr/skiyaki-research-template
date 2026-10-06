# Research Clarification Policy

## Purpose and Scope

This policy is the normative protocol for the `grill-me` skill. It makes each clarification turn reviewable, prevents stable project configuration from being re-asked, and records enough provenance for later planning. It governs local clarification and synthesis only; it never authorizes artifact creation, experiment execution, Run creation, Git commits, or external-system access.

## Structured Material Decision Protocol

A `Material_Decision` is a choice that changes experimental meaning, including the research objective, baseline, primary metric, success criterion, ablation scope, or a key controlled parameter.

While the `Research_Grill` is active, **each assistant turn MUST target exactly one structured `Material_Decision` and ask exactly one semantic question**. Use this logical envelope in transcripts or fixtures:

```yaml
kind: question
decision_key: primary_metric
prompt: "Which single primary metric should determine the winning rank?"
```

Rules:

1. `kind` is `question`.
2. `decision_key` names exactly one unresolved ledger entry.
3. `prompt` contains one focused question about that entry.
4. Explanatory context and a short list of answer options are allowed only when they support the same decision.
5. Do not bundle multiple prompts, add a second question, or ask for a stable setting in the same turn.
6. A follow-up retains the same `decision_key` until that decision is resolved or a labeled default is accepted.
7. The completion handoff occurs after the `Research_Grill` terminates and is not another grill question.

## Decision Priority

Select the highest-priority unresolved decision that is material to the request:

1. **Primary metric**: name, direction, and evaluation split needed for a measurable comparison.
2. **Baseline**: specific comparison reference, value when supported, split, and repository evidence or explicit user choice.
3. **Success criteria**: measurable threshold, relative improvement, non-inferiority margin, statistical criterion, or explicitly exploratory outcome.
4. **Research objective and hypothesis**: only when the request does not already establish them.
5. **Ablation scope**: variables or values that define the scientific comparison.
6. **Controlled parameters**: only controls whose choice could alter interpretation.

Do not ask implementation questions such as dtype, logging cadence, directory layout, or routine optimization settings. Those belong to planning.

## Canonical Stable Project Settings

This section is the **single canonical stable-key registry for the grill workflow**. Do not duplicate a competing list in `SKILL.md`. For every populated value in `project-plan.md`, consume it as inherited configuration and never ask the user to restate it.

### Environment and execution

- `environment.manager`
- `environment.manifest`
- `execution.default_target`
- `execution.ssh_host`
- `execution.remote_project_root`
- `execution.direct_cpu_max_minutes`
- `execution.require_slurm_for_gpu`
- `execution.require_slurm_for_cpu_heavy`

### Slurm and quota

- `slurm.partition`
- `slurm.account`
- `slurm.qos`
- `slurm.max_gpus_per_job`
- `slurm.max_concurrent_jobs`

### W&B

- `wandb.entity`
- `wandb.project`
- `wandb.mode`
- `wandb.keep_local_data`

### Hugging Face and artifact policy

- `huggingface.namespace`
- `huggingface.private`
- `huggingface.push_policy`
- `artifact_policy.checkpoint_management`
- `artifact_policy.data_privacy`
- `artifact_policy.model_release`

The `artifact_policy.*` decision keys represent populated values in the `project-plan.md` **Artifact Policy** body when those policies are not encoded in YAML frontmatter. Treat `huggingface.private`, `huggingface.push_policy`, and `wandb.keep_local_data` as machine-readable artifact-policy settings where applicable.

A missing key is not automatically a grill question. Ask about it only if the missing value changes experimental meaning; otherwise defer it to planning. Never treat `templates/project-plan.md` as populated project configuration.

## Decision Ledger

Initialize one ledger entry for every required decision:

- `research_objective`
- `baseline`
- `primary_metric`
- `success_criteria`
- `ablation_scope`
- `controlled_parameters`

Each entry uses this schema:

```yaml
key: baseline
value: "example-lora-rank-ablation rank 16"
origin: prior_evidence
rationale: "Existing result is comparable on model, dataset, and metric."
evidence_ids:
  - example-results
assumption: false
resolved: true
```

Allowed `origin` values are:

- `user`: explicitly selected or confirmed by the user.
- `project_setting`: inherited from populated `Project_Settings`.
- `prior_evidence`: resolved directly from cited repository evidence.
- `agent_default`: selected by the assistant rather than supplied by the user or inherited.

Ledger invariants:

1. Update or refine the answered entry **before** asking about another `decision_key`.
2. A resolved entry has a concrete value and origin.
3. A prior-evidence entry cites repository evidence identifiers or references.
4. An `agent_default` includes a rationale and either evidence references or `assumption: true`.
5. A `project_setting` remains distinguishable from an `agent_default`.
6. Record an intentional departure from prior evidence in the rationale and retain the conflicting evidence reference.
7. Never mark an unsupported baseline value resolved merely because a likely value exists.

## Handling Answers

### Sufficient answer

Update the matching ledger entry, including origin and provenance, then select the next unresolved decision. Ask no second question in the same assistant turn.

### Vague or insufficient answer

An answer is insufficient when it cannot establish a measurable or unambiguous value, such as “better,” “the usual model,” or “whatever makes sense.” Choose exactly one response:

1. **Focused follow-up**: ask one narrower question on the same `decision_key`, preferably with concise options; or
2. **Labeled Agent_Default**: propose one value labeled `Agent_Default`, state its rationale and evidence or explicit assumption, and ask one confirmation question about that same decision.

Examples:

```yaml
kind: question
decision_key: success_criteria
prompt: "For the Agent_Default, may I use non-inferiority within 2 accuracy points of the baseline?"
```

```yaml
kind: question
decision_key: baseline
prompt: "By 'current model,' do you mean the rank-16 run recorded in experiments/example-lora-rank-ablation/results.yaml?"
```

Do not accept a vague answer as resolved, silently choose a default, or move to a different decision before updating the ledger.

### “I don't know”

Apply the same one-decision rule. Offer one evidence-backed default when available. If no evidence supports a default, label it as an explicit assumption. If the baseline value itself lacks evidence, keep it unresolved rather than inventing a number.

## Evidence-Conflict Clarification

When a user answer conflicts with `Prior_Research_Evidence`:

1. Keep the current decision unresolved or refined-but-unconfirmed.
2. Cite the conflicting repository evidence in concise context.
3. Ask exactly one question with the same `decision_key` that distinguishes intentional deviation from misunderstanding.
4. If the user confirms intentional deviation, record origin `user`, preserve the evidence reference, and explain the deviation in `rationale`.
5. If the user corrects the answer, record the corrected value and its appropriate origin.

Example:

```yaml
kind: question
decision_key: baseline
prompt: "The structured result records rank 16 at 0.874 accuracy; do you intentionally want 0.875 as a new baseline, or should the ledger retain 0.874?"
```

This is one disambiguation question, not an invitation to revisit metric, scope, or infrastructure.

## Termination and Readiness

The critical readiness gate consists of:

- `baseline`
- `primary_metric`
- `success_criteria`

Continue the `Research_Grill` while any critical entry is unresolved. Approval-summary generation is blocked during that time.

Terminate the grill when all three critical entries are resolved and the ledger can record the research objective, ablation scope, and key controlled parameters from the request, evidence, user answers, inherited settings, or labeled defaults. On termination:

1. Do not ask about implementation details.
2. Do not ask about populated stable `Project_Settings`.
3. Return the ledger and intentional deviations to `plan-ml-experiment`.
4. If a noncritical value still needs implementation-level selection, leave it for planning as a documented default rather than prolonging the grill.

A user's request to move forward does not bypass unresolved critical decisions. Conversely, once the critical gate is resolved, do not continue questioning merely to optimize implementation choices.

## Anti-Patterns

- **Multiple decisions in one turn**: “What metric, baseline, and threshold should we use?”
- **Multiple questions disguised as one sentence**: “Which metric should we use, and should it be measured on validation or test?”
- **Stable-setting re-ask**: asking for `wandb.entity`, SSH host, Slurm partition, quota, or artifact destination when populated in `project-plan.md`.
- **Silent default**: selecting a value without the `agent_default` origin, rationale, and evidence or assumption.
- **Unsupported baseline**: inventing a baseline metric absent from repository evidence.
- **Unresolved handoff**: generating an approval request while baseline, primary metric, or success criteria is unresolved.
- **Scope leakage**: writing plans/jobs, creating Runs, executing entrypoints, contacting SSH/Slurm/W&B/Hugging Face, or committing Git changes during grilling.

## Clarification-Only Boundary

Permitted actions are local repository reads, focused user clarification, and
decision synthesis for handoff. The grill does not:

- write or modify `plan.md` or `run-config.yaml` (that is `plan-ml-experiment`),
- run training or evaluation,
- contact Slurm, W&B, or the Hugging Face Hub, or
- create a Git commit.

The only output is a set of resolved decisions handed to `plan-ml-experiment`.
