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

### 2. Safety review (before staging)

Exclude anything that must not be committed:
- secrets, tokens, credentials (`.env`, `*.token`, `credentials.json`, `*.pem`, keys)
- model checkpoints and large binaries (`*.pt`, `*.bin`, `*.safetensors`, `*.ckpt`)
- W&B caches (`wandb/`)
- raw run/Slurm logs (`experiments/*/logs/*.out`, `*.err`)

Stage specific files by name rather than `git add -A`, so nothing unexpected
slips in. If a credential-bearing file is staged, stop and tell the user.

### 3. Write the commit message — STE-KO coding surface

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

### 4. Propose, then commit on approval

Present the file list and the drafted message. **Do not commit until the user
approves.** On approval, stage the reviewed files and commit. Push only if the
user asks.

## Output

- A safety-reviewed set of staged files (no secrets, checkpoints, caches, or raw logs).
- A commit message that follows the STE-KO coding surface.
- A commit created only after explicit user approval.
