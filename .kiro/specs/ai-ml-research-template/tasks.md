# Implementation Plan: AI/ML Research Template Phase 1

## Overview

This plan implements Phase 1 of the GitHub Template Skeleton, creating the foundational repository structure with Codex integration, skills, templates, and documentation. No external system integration (SSH, Slurm, W&B, HF) is included in Phase 1.

The implementation focuses on creating a complete, self-documenting template that users can immediately use via GitHub's "Use this template" feature.

## Tasks

- [x] 1. Initialize repository structure
  - Create root directory with all subdirectories
  - Create all placeholder directories with .gitkeep files
  - Set up proper directory permissions
  - _Requirements: 1.1, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 2. Create core configuration files
  - [x] 2.1 Create AGENTS.md with core research workflow rules
    - Define workflow principles
    - Document approval requirements
    - List execution requirements
    - Reference skills and subagents
    - Keep content concise for consistent Codex application
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_
  
  - [x] 2.2 Create environment.yaml template
    - Include Python version specification
    - Add PyTorch and CUDA channels
    - List core ML dependencies (transformers, datasets, peft)
    - Add experiment tracking libraries (wandb, huggingface-hub)
    - Include helpful comments for customization
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [x] 2.3 Create project-plan.md template
    - Design YAML frontmatter schema with all configuration fields
    - Add environment manager specification
    - Add execution and Slurm configuration
    - Add W&B and Hugging Face configuration
    - Write markdown body with research objectives template
    - Include clear warnings against committing secrets
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_
  
  - [x] 2.4 Create project-log.md template
    - Write format guidelines and instructions
    - Include example entry format
    - Add initial setup entry
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 2.5 Create .gitignore file
    - Exclude Python cache and build artifacts
    - Exclude secrets and credentials patterns
    - Exclude outputs/ directory while preserving .gitkeep
    - Exclude experiment run logs (*.out, *.err in runs/*/logs/)
    - Exclude wandb/ directories in experiments
    - Exclude editor-specific files
    - Add .gitkeep preservation rules
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9_
  
  - [x] 2.6 Create VERSION file
    - Set initial version to 0.1.0
    - Document semantic versioning scheme
    - _Requirements: 15.1, 15.2, 15.3_
  
  - [x] 2.7 Create LICENSE file
    - Choose between MIT and Apache 2.0
    - Include appropriate license text
    - _Requirements: 1.4_

- [x] 3. Checkpoint - Verify core structure
  - Ensure all configuration files are valid
  - Verify .gitignore patterns work correctly
  - Ask user if questions arise

- [x] 4. Create skill definitions
  - [x] 4.1 Create grill-me skill
    - Create .agents/skills/grill-me/ directory
    - Write SKILL.md with purpose, when to use, procedure, and output
    - Document one-question-at-a-time approach
    - Include gap identification and prioritization logic
    - _Requirements: 3.1, 3.2_
  
  - [x] 4.2 Create discover-prior-research skill
    - Create .agents/skills/discover-prior-research/ directory
    - Write SKILL.md with search procedure
    - Document project-log and experiment search logic
    - Include Git history search approach
    - Document duplication detection procedure
    - _Requirements: 3.1, 3.3_
  
  - [x] 4.3 Create plan-ml-experiment skill
    - Create .agents/skills/plan-ml-experiment/ directory
    - Write SKILL.md with planning procedure
    - Document plan.md creation steps
    - Document job YAML generation steps
    - Include resource estimation logic
    - Add approval summary generation procedure
    - Create references/ subdirectory with example plans
    - _Requirements: 3.1, 3.4, 3.8_
  
  - [x] 4.4 Create train-llm skill
    - Create .agents/skills/train-llm/ directory
    - Write SKILL.md with execution procedure
    - Document preflight checks (approval, environment, resources)
    - Document run preparation (ID generation, directory creation)
    - Document Phase 1 local execution approach
    - Include history.md update procedure
    - Note Phase 6+ Slurm integration as future work
    - _Requirements: 3.1, 3.5_
  
  - [x] 4.5 Create evaluate-llm skill
    - Create .agents/skills/evaluate-llm/ directory
    - Write SKILL.md with evaluation procedure
    - Document checkpoint loading and metric calculation
    - Document baseline comparison logic
    - Document success criteria assessment
    - Include results.yaml drafting procedure
    - _Requirements: 3.1, 3.6_
  
  - [x] 4.6 Create finalize-experiment skill
    - Create .agents/skills/finalize-experiment/ directory
    - Write SKILL.md with finalization procedure
    - Document completeness verification checks
    - Document results, history, journal update procedures
    - Document project-log update procedure
    - Document Git review and commit proposal procedure
    - List prohibited actions (no auto-commit, must verify artifacts)
    - _Requirements: 3.1, 3.7_

- [x] 5. Create agent descriptions
  - [x] 5.1 Create research-journal-git.md
    - Document mission and two modes (discovery, finalize)
    - List allowed actions (read, analyze, draft, propose)
    - List prohibited actions (no submit, no push, no auto-commit)
    - Define required outputs for each mode
    - _Requirements: 14.1, 14.2, 14.7_
  
  - [x] 5.2 Create wandb-analyst.md
    - Document mission (training analysis, run comparison)
    - List allowed actions (W&B API queries, analysis, reporting)
    - List prohibited actions (no job submission, no config changes)
    - Define required outputs
    - _Requirements: 14.1, 14.3, 14.7_
  
  - [x] 5.3 Create huggingface-managing-specialist.md
    - Document mission (Hub management, model cards)
    - List allowed actions (Hub operations, card creation)
    - List prohibited actions (no unauthorized uploads, respect push policy)
    - Define required outputs
    - _Requirements: 14.1, 14.4, 14.7_
  
  - [x] 5.4 Create visualization-specialist.md
    - Document mission (research presentation graphics)
    - List allowed actions (create figures, format for publication)
    - List prohibited actions (no data manipulation)
    - Define required outputs
    - _Requirements: 14.1, 14.5, 14.7_
  
  - [x] 5.5 Create slurm-managing-specialist.md
    - Document mission (Slurm debugging and troubleshooting)
    - List allowed actions (diagnose issues, suggest fixes)
    - List prohibited actions (no changes without approval)
    - Define required outputs
    - _Requirements: 14.1, 14.6, 14.7_

- [x] 6. Checkpoint - Verify skills and agent descriptions
  - Ensure all SKILL.md files follow consistent format
  - Verify agent descriptions have all required sections
  - Ask user if questions arise

- [x] 7. Create experiment templates
  - [x] 7.1 Create experiment-plan.md template
    - Design YAML frontmatter with experiment metadata
    - Include status field with all possible values
    - Include primary_metric with name and direction
    - Include success_criteria section
    - Include jobs list and approval section
    - Write markdown body template with sections for purpose, hypothesis, design, risks
    - _Requirements: 6.2, 6.3, 6.4_
  
  - [x] 7.2 Create train-job.yaml template
    - Include job metadata (job_id, type, entrypoint)
    - Include matrix section for ablations
    - Include parameters section with common hyperparameters
    - Include resources section (backend, GPUs, CPUs, memory, time)
    - Include wandb configuration
    - Include huggingface push policy
    - Add helpful comments explaining each section
    - _Requirements: 7.1, 7.3, 7.4, 7.5, 7.6, 7.7_
  
  - [x] 7.3 Create evaluate-job.yaml template
    - Include evaluation-specific parameters
    - Include checkpoint reference (filled at runtime)
    - Include metrics list
    - Include resource configuration (typically less than training)
    - _Requirements: 7.2, 7.3, 7.5, 7.6_
  
  - [x] 7.4 Create run.yaml template
    - Include run identification fields (run_id, experiment_id, job_id)
    - Include status tracking with all possible values
    - Include timestamps (started_at, completed_at)
    - Include Slurm tracking section (for Phase 6+)
    - Include W&B tracking section
    - Include resolved config reference
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [x] 7.5 Create results.yaml template
    - Include experiment metadata
    - Include best run reference
    - Include primary metric with baseline comparison
    - Include secondary metrics list
    - Include success assessment section
    - Include all runs summary
    - Include artifacts section
    - _Requirements: 9.1, 9.5_
  
  - [x] 7.6 Create history.md template
    - Write format guidelines (reverse chronological, factual)
    - Include example entries showing proper format
    - Cover all event types (plan, approval, execution, evaluation, finalization)
    - _Requirements: 9.2, 9.6_
  
  - [x] 7.7 Create journal.md template
    - Write format guidelines (interpretation-focused)
    - Include sections for hypothesis assessment, findings, unexpected results
    - Include sections for limitations and next steps
    - Provide example entry showing proper style
    - _Requirements: 9.3, 9.7_
  
  - [x] 7.8 Create artifacts.yaml template
    - Include artifact tracking structure
    - Support multiple artifact types (model, figure, metrics)
    - Include Hub tracking fields
    - Include W&B tracking fields
    - Include Git commit tracking
    - _Requirements: 9.4_

- [x] 8. Create data README
  - [x] 8.1 Write data/README.md
    - Explain data directory organization
    - Provide guidelines for dataset storage
    - Note that data/ is excluded from Git by default
    - Suggest alternatives for large datasets (symlinks, data registries)
    - _Requirements: 12.4_

- [x] 9. Checkpoint - Verify templates
  - Ensure all templates are complete and consistent
  - Verify YAML templates are valid
  - Verify markdown templates follow format guidelines
  - Ask user if questions arise

- [x] 10. Create comprehensive README
  - [x] 10.1 Write introduction and quick start
    - Explain what the template is and who it's for
    - Provide 5-minute setup guide
    - Show example of requesting an experiment from Codex
    - _Requirements: 13.1, 13.5_
  
  - [x] 10.2 Document project structure
    - Explain directory layout
    - Describe purpose of each major directory
    - Explain relationship between AGENTS.md, skills, and templates
    - _Requirements: 13.4, 13.7_
  
  - [x] 10.3 Document configuration
    - Explain how to customize project-plan.md
    - Explain how to customize environment.yaml
    - Provide examples of common configurations
    - _Requirements: 13.3_
  
  - [x] 10.4 Document core concepts
    - Define Experiment, Job, Run
    - Explain workflow from request to completion
    - Describe approval gates
    - _Requirements: 13.1, 13.2_
  
  - [x] 10.5 Document skills and subagents
    - List available skills with brief descriptions
    - Explain when to use each skill
    - List available subagents with purposes
    - Link to detailed skill and agent documentation
    - _Requirements: 13.1, 13.7_
  
  - [x] 10.6 Add phase status and roadmap
    - Document Phase 1 completion status
    - List future phases and planned features
    - Set expectations about current limitations
    - _Requirements: 15.4_
  
  - [x] 10.7 Add contributing and license sections
    - Link to Codex documentation
    - Explain how to improve the template
    - Include license information
    - _Requirements: 13.6, 1.4_

- [x] 11. Create example experiment (optional reference)
  - [x] 11.1 Create example LoRA rank ablation experiment
    - Create experiments/example-lora-rank-ablation/ directory
    - Write example plan.md with realistic research question
    - Create example train.yaml and evaluate.yaml in jobs/
    - Create example run in runs/ showing proper structure
    - Write example results.yaml with metrics
    - Write example history.md showing event timeline
    - Write example journal.md showing interpretation
    - Mark directory as optional/example in README
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 8.1, 9.1, 9.2, 9.3_

- [x] 12. Final verification and polish
  - [x] 12.1 Verify directory structure completeness
    - Check all required directories exist
    - Verify .gitkeep files are in place
    - Verify no placeholder content remains in production files
    - _Requirements: 1.1, 12.6_
  
  - [x] 12.2 Verify .gitignore effectiveness
    - Test that secrets patterns are excluded
    - Test that outputs/ is excluded with .gitkeep preserved
    - Test that logs are excluded
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.9_
  
  - [x] 12.3 Verify all cross-references
    - Check that AGENTS.md references to skills are correct
    - Check that README links to correct files
    - Check that templates reference correct paths
    - _Requirements: 2.7, 13.7_
  
  - [x] 12.4 Verify YAML validity
    - Validate environment.yaml syntax
    - Validate all template YAML files
    - Validate YAML frontmatter in markdown files
    - _Requirements: 4.2, 7.3, 8.2, 9.5_
  
  - [x] 12.5 Test template creation flow
    - Create a test project using "Use this template"
    - Verify all files are copied correctly
    - Verify .gitignore works in the new project
    - Verify README instructions are clear and accurate
    - _Requirements: 1.1, 1.2, 1.3_

- [ ] 13. Prepare for GitHub release
  - [ ] 13.1 Tag version 0.1.0
    - Create Git tag for initial release
    - Write release notes summarizing Phase 1 features
    - _Requirements: 15.2, 15.3_
  
  - [ ] 13.2 Enable "Use this template" on GitHub
    - Configure repository as a template
    - Verify template settings are correct
    - _Requirements: 1.1_
  
  - [ ] 13.3 Create GitHub repository description
    - Write concise repository description
    - Add relevant topics/tags (ai, ml, research, codex, template)
    - _Requirements: 1.1, 13.1_

## Notes

- **Language**: All files use Markdown, YAML, or plain text - no programming language implementation required
- **Phase 1 Scope**: This phase creates structure and documentation only. No SSH, Slurm, W&B, or Hugging Face integration is implemented
- **Testing**: Manual testing via "Use this template" is sufficient for Phase 1. Future phases may add automated tests
- **Documentation-First**: README and templates should be exceptionally clear since they guide users and Codex
- **Example Experiment**: Task 11 is optional but recommended - it serves as both documentation and validation
- **Codex Integration**: The template is designed to work with Codex's existing agent system. No custom Codex extensions are required

## Success Criteria

Phase 1 is complete when:

1. ✅ A user can click "Use this template" and get a working repository
2. ✅ Codex reads and applies AGENTS.md rules automatically
3. ✅ All skills are discoverable and properly formatted
4. ✅ All templates are complete and include helpful comments
5. ✅ README provides clear setup instructions
6. ✅ .gitignore properly excludes secrets and large files
7. ✅ A user can request an experiment and Codex produces a plan with job configurations
8. ✅ The repository is self-documenting with examples and references

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6"] },
    { "id": 3, "tasks": ["5.1", "5.2", "5.3", "5.4", "5.5"] },
    { "id": 4, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7", "7.8", "8.1"] },
    { "id": 5, "tasks": ["10.1", "10.2", "10.3", "10.4", "10.5", "10.6", "10.7"] },
    { "id": 6, "tasks": ["11.1"] },
    { "id": 7, "tasks": ["12.1", "12.2", "12.3", "12.4"] },
    { "id": 8, "tasks": ["12.5"] },
    { "id": 9, "tasks": ["13.1", "13.2", "13.3"] }
  ]
}
```
