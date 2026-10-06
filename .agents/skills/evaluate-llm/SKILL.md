# Evaluate LLM Skill

**Stage:** Run

Evaluate completed training runs, compare them against the baseline, and record
the results in prose. Uses the project's own evaluation code; nothing is scored
or gated automatically.

## Prerequisites

- Required training runs have finished (check `history.md`).
- The experiment's `plan.md` states the metric and baseline (or that the run is
  exploratory).

## Procedure

1. **Identify what to evaluate.** From `history.md`, find the successful runs and
   the best candidate(s) by the planned metric. Locate their checkpoints (local
   or on the Hugging Face Hub).

2. **Run evaluation.** Use the project's evaluation entrypoint with the relevant
   checkpoint and the evaluation dataset/split from `run-config.yaml`. Run short
   evaluations locally or via Slurm as appropriate; capture logs to `logs/`.

3. **Compare runs.** Rank runs by the primary metric (respecting whether higher
   or lower is better). Compute improvement over the baseline — be explicit about
   absolute vs. relative. Note useful secondary metrics (time, memory).

4. **Assess against the plan.** If the plan defined a success criterion, state
   plainly whether it was met and by how much, with the evidence. If the run was
   exploratory, summarize what was observed instead of a pass/fail.

5. **Record results.** Write the comparison and conclusion into `journal.md`
   (interpretation) and note the evaluation events in `history.md` (facts). Keep
   source metric values exact; label any derived numbers.

## Notes

- Compare only what the evidence supports; if it can't support a conclusion, say so.
- For many runs or surprising patterns, consider producing figures under
  `figures/` to make the comparison clear.
