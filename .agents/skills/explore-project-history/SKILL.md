# Explore Project History Skill

**Stage:** Plan

Inspect this repository's past experiments, results, project log, and Git history
before planning new work, so you build on prior findings and avoid duplicating
effort.

## When to Use

Before planning any new experiment, to:

- Find related conclusions and recommended next steps in `project-log.md`.
- Locate comparable past experiments via `experiments/*/journal.md` and their
  `run-config.yaml` and results notes.
- Extract reusable baselines and settings from prior `run-config.yaml` files.
- Review relevant Git history for prior changes and decisions.
- Judge whether the new request overlaps or duplicates past work.

## Procedure

1. **Read project context.** Skim `project-plan.md` for stable settings and
   `project-log.md` for prior conclusions and next-step suggestions.

2. **Scan experiments.** List `experiments/` and open the ones relevant to the
   request (same model, dataset, technique, or objective). Read their `plan.md`,
   `journal.md`, and `run-config.yaml`.

3. **Check Git history.** Look for related commits, reverted experiments, or
   changed interpretations. Cite the commit when it matters.

4. **Report findings to the user.** Summarize:
   - related prior work with where you found it (path or commit),
   - reusable baselines/settings and their source,
   - whether the request duplicates or extends existing work, and
   - open questions to resolve in the next step (grill-me).

## Notes

- Read-only: this skill inspects and summarizes; it does not write plans or run
  anything.
- Cite evidence (file path or commit) for each finding so the user can verify.
- See [references/search-strategy.md](references/search-strategy.md) for a
  thorough search approach.
