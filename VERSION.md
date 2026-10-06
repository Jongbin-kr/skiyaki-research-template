# Versioning Scheme

This template follows [Semantic Versioning 2.0.0](https://semver.org/).

## Format

Version numbers use **MAJOR.MINOR.PATCH**:

- **MAJOR**: Incompatible changes requiring user action (file structure or
  convention changes that break existing experiments).
- **MINOR**: Backward-compatible additions (new skills, templates, conventions,
  documentation).
- **PATCH**: Backward-compatible fixes and clarifications.

## Current Version

**0.10.0** — v2: convention-only, code-free template.

This release replaces the earlier deterministic-harness design (Python scripts,
machine-enforced approval gates, strict `plan.md` frontmatter, success scoring,
and a subagent layer) with a lightweight, human-supervised, agent-driven
convention template.

### What v2 provides
- A three-stage workflow (Plan / Run / Finalize) documented in `AGENTS.md`, with
  six skills grouped under the stages.
- A simple experiment layout: a prose `plan.md`, a reproducible `run-config.yaml`
  (the one machine-read file, fed to the project's own training code),
  `history.md`, `journal.md`, plus `logs/` and `figures/`.
- Conventions for Slurm, Weights & Biases, Hugging Face, and git-safety written
  as guidance the human supervises — no code gates.
- No bundled scripts, no test harness, no enforced schemas.

### Pre-1.0 note
Versions before 1.0.0 are under active development; minor increments may include
breaking changes as the design stabilizes.

## History

- **0.10.0** — v2 rewrite: convention-only, code-free, agent-driven.
- **0.1.0** — initial release (v1 deterministic harness: scripts, gates, strict
  schemas). Superseded by v2.
