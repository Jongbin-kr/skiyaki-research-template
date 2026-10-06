# Grill Me Skill

**Stage:** Plan

Clarify the consequential scientific decisions before writing a plan, by asking
focused questions one at a time. This skill resolves decisions only — it does not
write the plan, create configs, or run anything.

## When to Use

When a material decision is unclear or unsupported, such as:

- the research objective or hypothesis,
- the comparison baseline,
- the primary metric (if the run is meant to be measured),
- the ablation scope or a controlled parameter that changes the experiment's meaning,
- a conflict between the user's request and prior repository evidence.

## When NOT to Use

- The value is already recorded in `project-plan.md` (don't re-ask stable settings).
- It's an implementation detail (logging cadence, directory layout) — leave that
  to planning.
- The run is explicitly exploratory and the user is fine without a fixed metric.

## Procedure

1. **Start from what's known.** Use findings from `explore-project-history` and
   stable settings from `project-plan.md`. Don't re-ask settled values.

2. **Ask one question at a time.** Each turn, raise exactly one decision and ask
   one focused question about it. Don't bundle several questions together.

3. **Prefer the highest-impact decision first:** objective → baseline → primary
   metric → success criterion → ablation scope → key controls.

4. **Offer a reasonable default when the user is unsure.** Propose a value,
   explain why, and note it as your suggestion so the choice stays visible.

5. **Metric and success criterion are encouraged but optional.** If the user says
   the run is exploratory, record that and move on — do not force a threshold.

6. **Record each resolved decision** (value, and whether it came from the user,
   project settings, prior evidence, or your suggestion) so planning can reuse it.

## Output

A short summary of the resolved decisions, ready to hand to `plan-ml-experiment`.
