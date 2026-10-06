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

5. **Review the diff for safety.** Before proposing a commit, review what would be
   staged and exclude anything that must not be committed:
   - secrets, tokens, credentials,
   - model checkpoints and large binaries,
   - W&B caches,
   - raw Slurm logs (`experiments/*/logs/*.out`, `*.err`).

   Commit plans, configs, results, and documentation only.

6. **Propose the commit.** Present the file list and a clear commit message to the
   user. Do not commit until the user approves. Push only if asked.

## Output

- Finalized `journal.md`, updated `history.md` and `project-log.md`.
- A proposed commit (file list + message) awaiting user approval.
