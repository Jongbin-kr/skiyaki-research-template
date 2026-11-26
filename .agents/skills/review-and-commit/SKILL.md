---
name: review-and-commit
description: Review staged changes for safety, write a clear commit message following the STE-KO coding surface, and commit only after the user approves. Use whenever committing code or experiment work; the finalize-experiment skill also calls this skill for its commit step.
---

# Review and Commit Skill

Review a change, write a disciplined commit message, and commit only with the
user's approval. The commit message follows the **STE-KO coding surface** — a
controlled-language spec for commit messages and work reports. This skill is
general: use it for any commit, and `finalize-experiment` calls it for its
commit step.

STE-KO rules live in [`references/ste-ko-SPEC.md`](references/ste-ko-SPEC.md)
(rule body) and [`references/ste-ko-dictionary.md`](references/ste-ko-dictionary.md)
(approved and disallowed expressions). Read them before writing the message.

## When to Use

- After implementation or experiment work is done and you want to commit.
- Called by `finalize-experiment` for its commit proposal.

## Procedure

### 1. Review the diff

Show the user what changed (`git status`, `git diff`). Summarize it in one or
two sentences: what changed and why.

### 2. Branch check (before staging)

Confirm the change lands on the right branch. This project keeps a branch per
experiment (`experiment/<experiment-id>`). A commit must match its branch: an
experiment's commit belongs only on that experiment's branch, not on `main` and
not on another experiment's branch.

1. Read the current branch: `git branch --show-current`. Show it to the user.
2. Find which experiment ids the change touches. Look at the changed paths:
   `experiments/<id>/...` and `outputs/<id>/...` each name an experiment id.
   Collect the set of ids the diff touches.
3. Classify the change:
   - **Project-level work** — no experiment id in the paths (templates, skills,
     AGENTS.md, project-plan.md, project-log.md, shared config). Belongs on
     `main`. If the current branch is not `main`, stop and tell the user.
   - **Single-experiment work** — exactly one experiment id. Belongs on
     `experiment/<id>` with that exact id. Stop and tell the user if the current
     branch is anything else — whether `main`, or a different experiment branch
     such as `experiment/<other-id>`. Compare the id in the branch name to the id
     in the paths; they must be identical.
4. Stop and tell the user to split the commit when the change mixes categories:
   - more than one experiment id in one diff, or
   - experiment work together with project-level work.
   Each part commits separately on its own branch.

When you stop, do not commit. Ask whether to switch to the right branch or create
it (`git switch -c experiment/<id>`). Never switch branches or create one without
the user's approval. This step checks; the user decides.

### 3. Safety review (before staging)

Exclude anything that must not be committed:
- secrets, tokens, credentials (`.env`, `*.token`, `credentials.json`, `*.pem`, keys)
- model checkpoints and large binaries (`*.pt`, `*.bin`, `*.safetensors`, `*.ckpt`)
- W&B caches (`wandb/`)
- raw run/Slurm logs (`experiments/*/logs/*.out`, `*.err`, `*.log`) — these are
  what tools emit; they are gitignored and stay local. Commit a human-written
  summary (e.g. `summary.md`) instead, not the raw log.

Stage specific files by name rather than `git add -A`, so nothing unexpected
slips in. If a credential-bearing file is staged, stop and tell the user.

### 4. Write the commit message — STE-KO coding surface

Apply the STE-KO coding surface (SPEC.md chapter 10 plus the always-on rules).
The load-bearing rules for a commit message:

- **10.6 — write what changed and why.** The code already shows how; the message
  says what and why. Not "refactoring and cleanup".
- **10.8 — never claim a check you did not run.** If tests, build, or migration
  did not run, say so. Separate what ran from what did not. The agent breaks this
  rule most often.
- **10.9 — list what is left.** When reporting finished work, include what was
  skipped, what failed, and what the next person should do.
- **10.7 — locate code as `file:line`**; keep identifiers verbatim (1.4).
- **6.1 conclusion first / 6.2 separate fact, inference, unverified / 6.4 do not
  drop failures and unfinished work.**

**Language.** Write the commit message in the project's commit language.
- Korean commits: apply STE-KO in full — vocabulary via dictionary.md, no double
  passives (3.2), noun stacks of 3 or fewer (2.1), and the rest.
- English commits: the Korean grammar and vocabulary rules do not apply; still
  follow the language-neutral coding-surface principles above (what and why, no
  false check claims, list what is left, conclusion first).

### 5. Propose, then commit on approval

Present the file list and the drafted message. **Do not commit until the user
approves.** On approval, stage the reviewed files and commit. Push only if the
user asks.

## Output

- The change confirmed to land on the matching branch: `main` for project-level
  work, `experiment/<id>` for that exact experiment id — never `main`, never
  another experiment's branch. Mixed or multi-experiment changes split first.
- A safety-reviewed set of staged files (no secrets, checkpoints, caches, or raw logs).
- A commit message that follows the STE-KO coding surface.
- A commit created only after explicit user approval.
