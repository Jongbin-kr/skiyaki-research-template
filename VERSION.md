# Versioning Scheme

This template follows [Semantic Versioning 2.0.0](https://semver.org/).

## Format

Version numbers use the format: **MAJOR.MINOR.PATCH**

- **MAJOR**: Incremented for incompatible changes that require user action
  - Breaking changes to file structure or schemas
  - Removal of skills or significant workflow changes
  - Changes that break existing experiments or configurations

- **MINOR**: Incremented for new features in a backward-compatible manner
  - New skills or subagent definitions
  - New template files
  - Enhanced documentation or examples
  - New phases (SSH, Slurm, W&B, Hugging Face integration)

- **PATCH**: Incremented for backward-compatible bug fixes
  - Documentation corrections
  - Template improvements
  - Bug fixes in skill definitions
  - Clarifications without structural changes

## Current Version

**0.9.0** - Full Workflow Implemented (Phases 1-9)

This release implements the complete research workflow end to end: repository
structure, skills, specialist agent descriptions, and the deterministic helper
scripts for planning, local execution, SSH/Slurm submission, W&B tracking,
Hugging Face Hub publication, and experiment finalization with a Git commit
proposal. External operations are gated on explicit user approval; W&B entity
and Hugging Face namespace stay as placeholders until a consuming project sets
them.

### Implemented Features
- Complete directory structure for AI/ML research projects
- AGENTS.md with core research workflow rules
- Six research workflow skills (grill-me, discover-prior-research, plan-ml-experiment, train-llm, evaluate-llm, finalize-experiment)
- Five specialist agent descriptions
- Comprehensive templates for experiments, jobs, runs, and results
- Conda environment configuration
- Project configuration and logging infrastructure
- Deterministic helper scripts: validate_job, initialize_run, run_local,
  submit_slurm, track_wandb, publish_hf, finalize_experiment
- Property-based and integration test suites for the helper scripts
- Immediate usability via GitHub's "Use this template" feature

### Pre-1.0 Note
Versions before 1.0.0 indicate the template is under active development. Minor
version increments may include breaking changes as the design stabilizes. The
1.0.0 milestone is reserved for a stabilized release after real-world use.

## Version History

### 0.9.0 — Full workflow (Phases 1-9)
- Phase 1: repository structure, AGENTS.md, templates, documentation
- Phase 2: six core skills + helper scripts (validate_job, initialize_run)
- Phase 3: five specialist agent descriptions and routing rules
- Phase 4: planning-only golden path (fixtures, validators, repository contract)
- Phase 5: run_local.py — approval-gated local CPU execution
- Phase 6: submit_slurm.py — SSH + Slurm submission and run linkage
- Phase 7: track_wandb.py — Weights & Biases tracking
- Phase 8: publish_hf.py — Hugging Face Hub publication
- Phase 9: finalize_experiment.py — finalization and Git commit proposal
- All external/mutating actions are approval-gated; tests use injected fakes
  with no real SSH/W&B/Hub/network or Git I/O

### 0.1.0 (Phase 1)
- Initial release: foundational structure, skills, templates, documentation

### Planned
- **1.0.0** - Stabilized release after real-world use
- Phase 10 (Harness Evals) and later extensions remain on the roadmap
