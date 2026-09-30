# Implementation Plan: Phase 3 Agent Descriptions

## Overview

This plan strengthens the five preserved specialist description files, adds selective bounded-delegation routing to `AGENTS.md`, and aligns `README.md` with current capabilities and roadmap gates. Implementation is limited to Markdown documentation. It does not add an automated contract validator or implement SSH, Slurm, W&B API, or Hugging Face Hub operations.

Each prompt is scoped so a code-generation agent can modify one file or one non-conflicting file group, preserve existing useful content, and incrementally wire the documentation into a consistent routing system.

## Tasks

- [x] 1. Standardize the five specialist contracts
  - [x] 1.1 Update `agent-descriptions/research-journal-git.md`
    - Preserve the filename and separate Discovery Mode from Finalize Mode.
    - Add Mission, When to Invoke, Required Inputs, Allowed Actions, Prohibited Actions, Required Output, and Escalation sections.
    - Define readable repository evidence, permitted research-record edits, missing-file handling, finalization completeness evidence, and commit approval boundaries.
    - Require outputs to cite sources, completed work, unresolved risks, and the recommended Main Agent action.
    - _Requirements: 1.1, 2.1-2.7, 5.1-5.3, 8.1-8.2_

  - [x] 1.2 Update `agent-descriptions/wandb-analyst.md`
    - Preserve the filename and canonical routing name `W&B Analyst`.
    - Add all seven standard contract sections and define local run exports, repository metrics, comparison goals, and expected evidence as inputs.
    - Limit Phase 3 work to local or user-provided metrics; label live W&B queries and remote mutations as Phase 7 capabilities.
    - Preserve source metric values and define escalation for missing exports, conflicting evidence, and requests requiring live W&B access.
    - _Requirements: 1.1, 1.4, 2.1-2.7, 4.2, 4.4-4.6, 5.1-5.2, 5.4-5.5, 8.1-8.3, 8.5_

  - [x] 1.3 Update `agent-descriptions/huggingface-managing-specialist.md`
    - Preserve the filename and identify `Hugging Face Curator` as the canonical routing name.
    - Add all seven standard contract sections and define local model metadata, evaluation evidence, audience, privacy, and push policy as inputs.
    - Limit Phase 3 work to local model-card drafting and metadata review; label Hub queries, repository operations, verification, and uploads as Phase 8 capabilities.
    - Preserve upload approval, privacy, push-policy, and credential boundaries; define a non-executing escalation path for unavailable Hub work.
    - _Requirements: 1.1-1.2, 1.4-1.5, 2.1-2.7, 4.3-4.6, 5.1-5.2, 5.6-5.7, 8.1-8.3, 8.5_

  - [x] 1.4 Update `agent-descriptions/visualization-specialist.md`
    - Preserve the filename and useful figure guidance while organizing the contract under the seven standard headings.
    - Define local result files, user-provided data, plot objective, audience, formats, and output path as required inputs.
    - Require source-value preservation and disclosure of filtering, aggregation, smoothing, axis truncation, and other transformations.
    - Limit live W&B retrieval to Phase 7 while allowing local exports, and preserve review-before-commit boundaries.
    - _Requirements: 1.1, 1.4, 2.1-2.7, 4.2, 4.4-4.6, 5.1-5.2, 5.8-5.9, 8.1-8.3, 8.5_

  - [x] 1.5 Update `agent-descriptions/slurm-managing-specialist.md`
    - Preserve the filename and identify `Slurm Debugger` as the canonical routing name.
    - Add all seven standard contract sections and define user-provided logs, copied status output, job YAML, cluster context, and observed symptoms as inputs.
    - Limit Phase 3 work to offline diagnosis; label SSH, scheduler queries, live diagnosis, submission, resubmission, cancellation, and configuration mutation as Phase 6 capabilities or prohibited actions.
    - Require unexecuted-command labeling and escalation that names the Phase 6 dependency without claiming live verification.
    - _Requirements: 1.1, 1.3-1.5, 2.1-2.7, 4.1, 4.4-4.6, 5.1-5.2, 5.10-5.11, 8.1-8.3, 8.5_

- [x] 2. Add Main Agent routing policy
  - [x] 2.1 Update the `AGENTS.md` Subagents section
    - Add the five canonical routing names, concrete triggers, and preserved description paths.
    - Explicitly map Hugging Face Curator and Slurm Debugger to their existing filenames.
    - Define narrowest-match selection, no-match retention, separate delegations for multi-specialist workflows, and prohibition of loading all descriptions by default.
    - Define the bounded delegation packet fields: objective, permitted and excluded scope, relevant paths/evidence, expected output, approval constraints, and roadmap gates.
    - Keep routing concise and defer specialist details to selectively loaded descriptions.
    - _Requirements: 1.1-1.5, 3.1-3.7, 4.1-4.6, 5.1, 8.1-8.4_

- [x] 3. Align user-facing specialist documentation
  - [x] 3.1 Update the `README.md` specialist and roadmap sections
    - List all five canonical routing names and link each name to the preserved description path.
    - Describe selective loading and bounded delegation consistently with `AGENTS.md`.
    - Distinguish Phase 3 local artifact work from Phase 6 SSH/Slurm, Phase 7 W&B, and Phase 8 Hugging Face Hub operations.
    - Remove or revise language that presents roadmap-gated external capabilities as currently operational.
    - Preserve concise summaries and defer full behavior contracts to the linked description files.
    - _Requirements: 1.1-1.5, 4.1-4.6, 6.1-6.5, 8.1-8.3_

- [x] 4. Checkpoint - Ensure contract and routing edits are complete
  - Ensure all planned Markdown edits are present, ask the user if questions arise.

- [x] 5. Perform requirement-traceable documentation review
  - [x] 5.1 Review and correct specialist contract completeness
    - Apply a checklist to all five descriptions for the seven required headings, explicit read/write scope, approvals, missing-input escalation, out-of-scope escalation, evidence, completed work, risks, and next actions.
    - Correct omissions or contradictions in the specialist files without adding scripts or schemas.
    - Record the checklist findings in the implementation change or pull-request review summary.
    - **Property 1: Specialist contract completeness**
    - **Validates: Requirements 2.1-2.7, 7.1, 7.5**

  - [x] 5.2 Review and correct routing uniqueness and selective loading
    - Cross-check all five canonical names and paths in `AGENTS.md` and `README.md`.
    - Review representative single-match, overlapping-match, multi-specialist, and no-match scenarios against the routing instructions.
    - Correct mappings or instructions that permit ambiguous routing or default bulk loading.
    - Record the checklist findings in the implementation change or pull-request review summary.
    - **Property 2: Routing uniqueness and selective loading**
    - **Validates: Requirements 1.1-1.5, 3.1-3.7, 7.2**

  - [x] 5.3 Review and correct roadmap-gate consistency
    - Cross-check every SSH, Slurm, W&B, and Hugging Face capability statement in the specialist files, `AGENTS.md`, and `README.md`.
    - Confirm local artifact work is separated from Phase 6, Phase 7, and Phase 8 external operations and every blocked path gives a non-executing next step.
    - Correct present-tense claims that imply unavailable external access.
    - Record the checklist findings in the implementation change or pull-request review summary.
    - **Property 3: Roadmap-gate consistency**
    - **Validates: Requirements 4.1-4.6, 5.5, 5.7, 5.11, 6.2, 6.5, 7.3**

  - [x] 5.4 Review and correct safety, compatibility, and Phase 3 scope
    - Verify approval gates, sensitive-artifact exclusions, metric/data integrity rules, and specialist-specific prohibited actions.
    - Resolve every specialist link and confirm all existing skill and specialist filenames remain unchanged.
    - Inspect the final diff and remove any execution code, external integration, upload automation, credentials, or contract-validator utility outside Phase 3 scope.
    - Record a zero-unresolved-conflicts checklist in the implementation change or pull-request review summary.
    - **Property 4: Safety, compatibility, and scope preservation**
    - **Validates: Requirements 5.1-5.11, 6.1, 6.3-6.4, 7.4, 7.6-7.7, 8.1-8.5**

- [x] 6. Final checkpoint - Ensure documentation review passes
  - Ensure all review checks pass, all conflicts are resolved, and only Phase 3 documentation changes remain; ask the user if questions arise.

## Notes

- Implementation language/medium: Markdown; the design does not use pseudocode for an executable implementation.
- Phase 3 preserves all existing skill and specialist filenames.
- Hugging Face Curator maps to `agent-descriptions/huggingface-managing-specialist.md`.
- Slurm Debugger maps to `agent-descriptions/slurm-managing-specialist.md`.
- External Slurm, W&B, and Hugging Face capabilities remain owned by Phases 6, 7, and 8 respectively.
- Correctness properties are verified by required documentation-review subtasks, not property-based tests or a new contract validator.
- No tasks create commits, run jobs, contact external services, or modify experiment code.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["3.1"] },
    { "id": 3, "tasks": ["5.1"] },
    { "id": 4, "tasks": ["5.2"] },
    { "id": 5, "tasks": ["5.3"] },
    { "id": 6, "tasks": ["5.4"] }
  ]
}
```
