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

**0.1.0** - Initial Phase 1 Release

This is the first public release of the AI/ML Research Workspace Template, providing the foundational repository structure with Codex integration, skills, templates, and documentation.

### Phase 1 Features
- Complete directory structure for AI/ML research projects
- AGENTS.md with core research workflow rules
- Six research workflow skills (grill-me, discover-prior-research, plan-ml-experiment, train-llm, evaluate-llm, finalize-experiment)
- Five specialist agent descriptions
- Comprehensive templates for experiments, jobs, runs, and results
- Conda environment configuration
- Project configuration and logging infrastructure
- Immediate usability via GitHub's "Use this template" feature

### Pre-1.0 Note
Versions before 1.0.0 indicate the template is under active development. Minor version increments may include breaking changes as the design stabilizes. Once version 1.0.0 is reached, semantic versioning will be strictly followed.

## Version History

### 0.1.0 (Phase 1) - [Date TBD]
- Initial release with complete Phase 1 implementation
- Foundation for AI/ML research with Codex integration
- Local execution support only (no SSH/Slurm/W&B/HF integration)

### Planned Future Versions
- **0.2.0** - Phase 2: Example experiment implementations
- **0.3.0** - Phase 3: Enhanced documentation and guides
- **0.4.0** - Phase 4-5: Additional templates and utilities
- **0.6.0** - Phase 6: SSH and Slurm integration
- **0.7.0** - Phase 7: Weights & Biases integration
- **0.8.0** - Phase 8: Hugging Face Hub integration
- **1.0.0** - Stable release with all core features complete
