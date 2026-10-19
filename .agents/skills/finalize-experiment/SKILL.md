---
name: finalize-experiment
description: Complete an experiment's documentation, update the project log, review the diff for safety, and propose a Git commit for the user to approve. Use in the Finalize stage after runs and evaluation are recorded. Does not commit automatically.
---

# Finalize Experiment Skill

**Stage:** Finalize

Complete an experiment's documentation, update the project log, and propose a Git
commit for the user to approve. No automatic completion scoring and no automatic
commit — you prepare and the user decides.

## Prerequisites

- Required runs finished and evaluation is recorded (`history.md`, `journal.md`).

## Procedure

1. **Check the record is complete.** Confirm the experiment folder has `plan.md`,
   `run-config.yaml`, and up-to-date `history.md` and `journal.md`. If a required
   run failed, make sure the failure is documented rather than hidden.

2. **Finalize `journal.md`.** Write the final conclusions: was the hypothesis
   supported, which run was best and why, limitations, and recommended next
   steps. Keep conclusions tied to recorded evidence — don't claim a result that
   isn't in the records.

3. **Update `history.md`** with the finalization entry (date, outcome summary).

4. **Update `project-log.md`.** Add a short project-level entry: one-line
   conclusion, best run, link to the experiment folder, key metrics, and the next
   step. Don't duplicate the full experiment detail here.

5. **Review and commit — use the `review-and-commit` skill.** Hand the commit off
   to [`review-and-commit`](../review-and-commit/SKILL.md): it runs the safety
   review (no secrets, checkpoints, W&B caches, or raw logs), writes the commit
   message following the STE-KO coding surface, and commits only after the user
   approves. Commit plans, run configs, results, and documentation only.

6. **Branch decision (if the experiment used its own branch).** Ask the user how
   to resolve the `experiment/<experiment-id>` branch: merge it into `main` to
   consolidate the record, or keep it as a standalone branch. Both are fine; do
   neither without the user's choice.

## Output

- Finalized `journal.md`, updated `history.md` and `project-log.md`.
- A commit proposed via `review-and-commit`, awaiting user approval.
- The user's decision on merging or keeping the experiment branch.
