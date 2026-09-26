# Implementation Plan: Phase 2 Core Skills Implementation

## Overview

This plan implements supporting materials for all six skills: reference documents (policies, schemas, guidelines), asset templates (YAML/Markdown), and helper scripts (Python). The implementation follows the architecture principle: "SKILL.md is workflow, scripts/ are deterministic helpers, src/ is research code."

All helper scripts will be implemented in Python 3.8+ with minimal dependencies (standard library + PyYAML).

## Tasks

- [x] 1. Create grill-me skill supporting materials
  - [x] 1.1 Create grill-policy.md reference document
    - Write question priority order section (metric → baseline → success criteria → parameters)
    - Document stable project-plan.md settings that must not be re-asked (W&B entity, HF namespace, SSH host, Slurm partition)
    - Define termination criteria for questioning (all critical decisions resolved)
    - Provide guidance for handling vague user answers (follow-up probing strategies)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Create discover-prior-research skill supporting materials
  - [x] 2.1 Create search-strategy.md reference document
    - Define search locations (project-log.md, experiments/*/journal.md, experiments/*/results.yaml, Git history)
    - Specify evidence consolidation approach (combine findings from multiple sources)
    - Define duplicate experiment detection logic (compare objectives, hyperparameters, metrics)
    - Specify reporting format for findings to Main Agent (structured summary with evidence links)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Create plan-ml-experiment skill supporting materials
  - [x] 3.1 Create asset templates directory and base templates
    - Create `.agents/skills/plan-ml-experiment/assets/` directory
    - Create `experiment-plan.md` template with YAML frontmatter structure
    - Include required frontmatter fields (experiment_id, status, primary_metric, success_criteria, jobs, approval)
    - Include markdown sections (Research Objective, Baseline, Design Rationale, Agent-Determined Defaults, Risks)
    - _Requirements: 3.1, 3.2_
  
  - [x] 3.2 Create job configuration templates
    - Create `train-job.yaml` template with all sections (metadata, matrix, parameters, resources, wandb, huggingface)
    - Include helpful comments explaining each section
    - Add placeholder values with angle bracket notation (e.g., `<model-name>`)
    - Create `evaluate-job.yaml` template with evaluation-specific structure
    - _Requirements: 3.3, 3.4_
  
  - [x] 3.3 Create plan-ml-experiment reference documents
    - Create `references/plan-schema.md` defining frontmatter fields
    - Mark required vs optional fields clearly
    - Define field types and validation rules
    - Create `references/approval-policy.md` defining approval workflow
    - Specify what changes require re-approval (metric change, >20% resource increase, new jobs)
    - Define approval summary format
    - _Requirements: 3.5, 3.6, 3.7, 3.8, 3.9_

- [~] 4. Checkpoint - Ensure all templates are valid
  - Verify YAML templates parse correctly
  - Verify Markdown templates have valid frontmatter structure
  - Ask user if questions arise

- [ ] 5. Create train-llm skill reference documents
  - [~] 5.1 Create execution-policy.md reference document
    - Define when Slurm is required (GPU jobs, CPU-heavy jobs)
    - Specify environment manager detection order (conda, uv, venv, system Python)
    - Define quota checking approach (compare against project-plan.md limits)
    - Note Phase 2 limitation: local execution only
    - _Requirements: 4.1, 4.3, 4.5, 4.6, 4.7, 4.8_
  
  - [~] 5.2 Create run-tracking.md reference document
    - Define Run ID format (`{type}-{job_id}__{YYYYMMDDTHHMMSS}`)
    - Specify run status transitions (initialized → running → completed|failed)
    - Define run directory structure (run.yaml, resolved-job.yaml, logs/, checkpoints/)
    - Document run.yaml schema with all fields
    - _Requirements: 4.4, 4.9, 4.10, 4.11_

- [ ] 6. Implement validate_job.py script
  - [~] 6.1 Create script with CLI argument parsing
    - Accept `--job-file PATH`, `--workspace PATH`, `--quota-file PATH` arguments
    - Add `--help` and `--version` flags
    - Use argparse for argument handling
    - _Requirements: 4.12, 7.1_
  
  - [~] 6.2 Implement validation logic
    - Check required fields present (job_id, type, entrypoint, parameters, resources)
    - Verify entrypoint file exists at specified path
    - Validate resources against quotas if quota-file provided
    - Validate matrix syntax if present
    - Validate W&B and HF configurations are well-formed
    - _Requirements: 4.14, 4.15, 4.16_
  
  - [~] 6.3 Implement error handling and JSON output
    - Handle missing files gracefully with clear error messages
    - Handle invalid YAML with parsing error details
    - Output structured JSON with validation results (valid, errors, warnings, checked)
    - Test from different working directories to ensure no cwd dependency
    - _Requirements: 4.17, 7.2, 7.3, 7.7_
  
  - [ ]*  6.4 Write property tests for validate_job.py
    - **Property 1: Job Validation Completeness**
    - **Validates: Requirements 4.14, 4.15, 4.16, 4.17**

- [ ] 7. Implement initialize_run.py script
  - [~] 7.1 Create script with CLI argument parsing
    - Accept `--job-file PATH`, `--experiment-dir PATH` arguments
    - Add `--dry-run`, `--help`, `--version` flags
    - Use argparse for argument handling
    - _Requirements: 4.13, 7.1, 7.4_
  
  - [~] 7.2 Implement run initialization logic
    - Generate Run ID in format `{type}-{job_id}__{YYYYMMDDTHHMMSS}`
    - Create run directory structure (`runs/<run-id>/`, `runs/<run-id>/logs/`)
    - Write run.yaml with initial metadata (run_id, job_file, status: initialized, created_at)
    - Copy job file to resolved-job.yaml (with matrix resolution if applicable)
    - _Requirements: 4.18, 4.19, 4.20, 4.21_
  
  - [~] 7.3 Implement dry-run mode and JSON output
    - Support --dry-run flag to preview without creating files
    - Output structured JSON with run metadata (run_id, run_dir, status, created_files, timestamp)
    - Handle missing files gracefully
    - Test from different working directories
    - _Requirements: 4.22, 7.2, 7.3, 7.4, 7.7_
  
  - [ ]* 7.4 Write property tests for initialize_run.py
    - **Property 2: Run Initialization Consistency**
    - **Validates: Requirements 4.18, 4.19, 4.20, 4.21, 4.22**

- [ ] 8. Create evaluate-llm skill supporting materials
  - [~] 8.1 Create result-schema.md reference document
    - Define results.yaml structure with all fields
    - Document experiment metadata format
    - Define best run identification format
    - Define metric format standards
    - Define baseline comparison format
    - _Requirements: 5.2, 5.4, 5.5, 5.6, 5.7_
  
  - [~] 8.2 Create comparison-guidelines.md reference document
    - Specify run comparison approach (compare by primary metric)
    - Define success criteria assessment logic (check each criterion with evidence)
    - Define baseline comparison calculation (improvement percentage)
    - Specify when to call W&B Analyst subagent (>5 runs, unexpected patterns, user request)
    - _Requirements: 5.3, 5.8, 5.9, 5.10_

- [ ] 9. Create finalize-experiment skill supporting materials
  - [~] 9.1 Create completion-checklist.md reference document
    - Define required files verification list (plan.md, jobs/*.yaml, runs/, results.yaml, history.md, journal.md, project-log.md)
    - Specify artifact link validation approach (W&B run IDs, HF checkpoint paths)
    - Define commit proposal format (files to commit, message template, outcome summary)
    - _Requirements: 6.2, 6.4, 6.5, 6.6_
  
  - [~] 9.2 Create git-safety.md reference document
    - List files that must never be committed (checkpoints, secrets, caches, logs)
    - Define secret detection patterns (regex for API keys, tokens, passwords)
    - Define large file detection approach (warn >10MB, block >50MB)
    - _Requirements: 6.3, 6.7, 6.8, 6.9_

- [~] 10. Checkpoint - Ensure all scripts work correctly
  - Test validate_job.py with valid and invalid job files
  - Test initialize_run.py with example experiment
  - Verify JSON output from all scripts
  - Ask user if questions arise

- [ ]* 11. Write integration tests
  - [ ]* 11.1 Test with example-lora-rank-ablation experiment
    - Validate existing train.yaml job file
    - Initialize a test run using existing experiment structure
    - Verify all generated files match schemas
    - _Requirements: 8.1, 8.2, 8.3, 10.1_
  
  - [ ]* 11.2 Write property test for script interface compliance
    - **Property 3: Script Interface Compliance**
    - Test all scripts work from different working directories
    - Verify JSON output format
    - Test dry-run modes
    - Test error handling for missing files
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.6, 7.7**
  
  - [ ]* 11.3 Write property tests for template validity
    - **Property 4: Template YAML Validity**
    - Parse all .yaml templates and verify structure
    - **Validates: Requirements 3.3, 3.4, 10.3**
    - **Property 5: Template Markdown Structure**
    - Parse all .md templates with frontmatter and verify structure
    - **Validates: Requirements 3.2, 10.4**

- [ ] 12. Final documentation and verification
  - [~] 12.1 Add --help documentation to all scripts
    - Include usage examples in help text
    - Document all arguments and flags
    - Add version information
    - _Requirements: 7.1, 7.3_
  
  - [~] 12.2 Create README for scripts directory
    - Document script purposes and usage
    - Provide examples of common workflows
    - Note dependencies (Python 3.8+, PyYAML)
    - Document testing approach
    - _Requirements: 7.5, 7.6_
  
  - [~] 12.3 Verify Phase 2 boundaries
    - Confirm no SSH implementation present
    - Confirm no Slurm implementation present
    - Confirm no W&B API calls present
    - Confirm no HF Hub uploads present
    - Verify placeholders exist for future phases
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [~] 13. Final checkpoint - Complete implementation verification
  - Run all tests (unit and property tests)
  - Test full workflow with example experiment
  - Verify all reference documents are complete
  - Verify all templates are valid
  - Ensure all scripts output valid JSON
  - Ask user if questions arise

## Notes

- Tasks marked with `*` are optional test-related sub-tasks that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties from the design document
- Integration tests verify cross-component interactions
- All scripts use Python 3.8+ with minimal dependencies (standard library + PyYAML)
- Phase 2 focuses on local execution only, with placeholders for future integrations

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["3.1", "3.2", "3.3"] },
    { "id": 2, "tasks": ["5.1", "5.2"] },
    { "id": 3, "tasks": ["6.1", "7.1"] },
    { "id": 4, "tasks": ["6.2", "7.2"] },
    { "id": 5, "tasks": ["6.3", "7.3"] },
    { "id": 6, "tasks": ["6.4", "7.4", "8.1", "8.2", "9.1", "9.2"] },
    { "id": 7, "tasks": ["11.1", "11.2", "11.3"] },
    { "id": 8, "tasks": ["12.1", "12.2", "12.3"] }
  ]
}
```
