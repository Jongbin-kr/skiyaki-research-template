# Implementation Plan: Phase 4 Planning-only Golden Path

## Overview

Implement a deterministic local validation suite for the documentation-driven flow `LoRA request → prior research → one-question-at-a-time grill → plan.md → train/evaluate YAML → concise approval summary → wait for approval`. The implementation strengthens existing skill guidance and templates, adds human-readable transcript/scenario fixtures, and validates the workflow with test-only Python helpers and pytest. No task executes an experiment, creates a real Run, contacts SSH/Slurm/W&B/Hugging Face, or creates a Git commit.

## Tasks

- [x] 1. Align the three planning skills and templates with the Phase 4 contract
  - [x] 1.1 Strengthen prior-research discovery guidance
    - Update `.agents/skills/discover-prior-research/SKILL.md` and `references/search-strategy.md` to require a complete inspected-source inventory, repository-path or Git-commit provenance for findings, structured/narrative conflict reporting, duplication classification, and explicit missing-source records.
    - Make clear that root templates are not populated project evidence and that unsupported baseline values remain unresolved.
    - Preserve discovery as a local read/synthesis responsibility without planning or execution behavior.
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 10.2_

  - [x] 1.2 Strengthen one-question-at-a-time grill guidance
    - Update `.agents/skills/grill-me/SKILL.md` and `references/grill-policy.md` so each assistant turn targets exactly one structured Material_Decision.
    - Centralize the stable Project_Settings keys that must be consumed without re-asking, including environment, SSH/remote path, Slurm, W&B, Hugging Face, quota, and artifact policy settings.
    - Define decision-ledger updates, vague-answer follow-up behavior, evidence-conflict clarification, and termination when baseline, metric, and success criteria are resolved.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.5, 10.2_

  - [x] 1.3 Align planning guidance and duplicate artifact templates
    - Update `.agents/skills/plan-ml-experiment/SKILL.md`, relevant planning references/assets, and matching root experiment/job templates to front-load Agent-Determined Defaults and preserve user/project/evidence/default provenance.
    - Require evidence-backed baseline details, measurable success criteria, pending approval metadata, pre-approval local validation, and a terminal concise Approval_Summary.
    - Add planned/unverified Phase 6, 7, and 8 boundary labels for Slurm, W&B, and Hugging Face destinations while keeping YAML reproducible.
    - Keep root templates and skill assets schema-compatible; do not add a runner or agent loop.
    - _Requirements: 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5, 10.1, 10.2_

- [x] 2. Create test-only scenario models and safe fixture loading
  - [x] 2.1 Implement immutable scenario, evidence, decision, action, and diagnostic models
    - Create `tests/helpers/phase4_models.py` with frozen dataclasses or equivalent typed structures for `Scenario`, `Turn`, `EvidenceRecord`, `Decision`, `ObservedAction`, `Diagnostic`, and `ValidationResult`.
    - Encode stable diagnostic ordering and normalized messages that exclude timestamps, secrets, absolute temporary paths, and platform-specific separators.
    - Define canonical stable-setting keys, required Material_Decisions, workflow states, and external-operation-to-roadmap-phase mappings.
    - _Requirements: 3.3, 4.1, 4.2, 4.4, 9.6, 10.3_

  - [x] 2.2 Implement traversal-safe fixture loading and isolated materialization
    - Create `tests/helpers/phase4_fixture_loader.py` to load safe YAML/Markdown fixtures, validate schema versions, and resolve fixture-relative paths without absolute-path or `..` traversal.
    - Copy writable source workspaces only into pytest `tmp_path`; keep dedicated fixture inputs read-only.
    - Reject fixture dependencies on wall-clock time, network state, credentials, or mutable external service data.
    - _Requirements: 9.1, 9.4, 9.7_

- [x] 3. Implement pure Phase 4 validators
  - [x] 3.1 Implement workflow, grill, and decision-ledger validation
    - Create `tests/helpers/phase4_workflow_validator.py` for ordered state transitions, discovery-before-grill, one question per assistant turn, answer-to-decision updates, stable-setting exclusions, critical-decision readiness, and terminal awaiting-approval behavior.
    - Return requirement-addressed diagnostics rather than executing any workflow action.
    - _Requirements: 1.1, 1.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.4, 4.5, 7.1, 10.3_

  - [x] 3.2 Implement evidence and discovery-report validation
    - Create `tests/helpers/phase4_evidence_validator.py` to validate inspected-source coverage, finding provenance, evidence-path/commit resolution, metric cross-checks, missing-source handling, baseline support, and model-based duplication classification.
    - Give structured results precedence for quantitative comparisons while requiring explicit conflict records for mismatches.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.3, 5.4, 10.3_

  - [x] 3.3 Implement plan, job, and approval-summary validation
    - Create `tests/helpers/phase4_artifact_validator.py` to parse plan frontmatter and headings, validate train/evaluate YAML schemas, reject unresolved placeholders and secret-like values, and cross-check metric, baseline, split, matrix, group, resources, and artifact paths.
    - Validate Agent-Determined Defaults heading order and provenance, pending approval metadata, planned/unverified external destinations, Approval_Summary ordering/completeness, and matrix/resource arithmetic.
    - Redact secret-like values in diagnostics.
    - _Requirements: 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1, 7.2, 7.3, 7.4, 7.5, 10.3_

  - [x] 3.4 Implement boundary, command, and preservation validation
    - Create `tests/helpers/phase4_boundary_validator.py` to permit only local reads and Fixture_Workspace writes and to reject entrypoint execution, Run initialization/content, SSH/Slurm operations, live W&B/Hugging Face operations, and Git commits.
    - Scan structured actions plus fenced/inline commands, map blocked integrations to Phases 6/7/8, and compare protected path inventories and SHA-256 digests before and after validation.
    - _Requirements: 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.4, 9.5, 10.3, 10.5_

- [x] 4. Add the successful transcript fixture and focused guard fixtures
  - [x] 4.1 Create synthetic project and prior-research evidence fixtures
    - Add `tests/fixtures/phase4-planning-golden-path/golden/source-workspace/` with populated fixture-only project settings/log and a relevant prior LoRA experiment containing plan, journal, structured results, and job YAML.
    - Add declared Git evidence based on relevant repository commits without invoking or changing Git history during fixture validation.
    - Ensure baseline claims and duplication differences are internally consistent and traceable.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 9.1, 9.5_

  - [x] 4.2 Create the complete Golden Path transcript and expected artifacts
    - Add `scenario.yaml`, `transcript.yaml`, `action-manifest.yaml`, `discovery-report.yaml`, expected awaiting-approval `plan.md`, expected `jobs/train.yaml`, expected `jobs/evaluate.yaml`, and expected concise `approval-summary.md`.
    - Resolve metric, baseline, success criteria, scope, and controls through one-question-at-a-time turns while inheriting all stable settings without questions.
    - Include no Run artifacts, approvals, execution commands, credentials, or external operations.
    - _Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 9.1, 9.2_

  - [x] 4.3 Create compact negative guard descriptors
    - Add guard scenarios for bundled questions, stable-setting re-asks, unsupported findings/baselines, unresolved metric-baseline-success decisions, unresolved placeholders, early execution requests, Run creation, forbidden commands, escaped writes, nondeterministic dependencies, and SSH/Slurm/W&B/Hugging Face attempts.
    - Give each guard exactly one primary mutation and expected requirement/code/location diagnostic.
    - _Requirements: 1.4, 1.5, 2.6, 3.1, 3.3, 4.5, 5.5, 6.7, 8.1, 8.2, 8.4, 8.5, 9.3, 9.4, 9.7, 10.3_

- [x] 5. Add automated Golden Path and property validation
  - [x]* 5.1 Write the successful scenario integration and preservation tests
    - Create `tests/test_phase4_planning_golden_path.py` to load the fixture into `tmp_path`, run all pure validators, assert the complete ordered flow and cross-artifact consistency, and compare protected repository/example hashes before and after.
    - Verify the terminal state is awaiting approval and the source workspace has no `runs/` delta.
    - _Requirements: 6.1, 7.1, 7.5, 8.1, 8.2, 8.3, 9.2, 9.4, 9.5, 10.5_

  - [x]* 5.2 Write property tests for ordered and focused planning behavior
    - Create `tests/test_phase4_workflow_properties.py` with at least 100 Hypothesis examples per property for reordered events, transcript prefixes, question targets, vague answers, decision origins, and unresolved critical decisions.
    - Tag and implement Design Properties 1, 4, and 5.
    - **Property 1: Ordered planning state transitions**
    - **Property 4: Focused, non-redundant grilling**
    - **Property 5: Decision provenance and readiness**
    - **Validates: Requirements 1.1, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.4, 4.5, 5.1, 7.1, 9.2**

  - [x]* 5.3 Write property tests for evidence closure and plan validity
    - Create `tests/test_phase4_evidence_plan_properties.py` with generated evidence inventories, supported/unsupported claims, metric conflicts, overlap facts, heading orders, evidence references, and placeholder insertion.
    - Tag and implement Design Properties 3 and 6.
    - **Property 3: Evidence closure and baseline integrity**
    - **Property 6: Plan validity and review order**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.3, 5.1, 5.2, 5.3, 5.4, 5.5**

  - [x]* 5.4 Write property tests for jobs and approval-summary consistency
    - Create `tests/test_phase4_artifact_properties.py` with generated LoRA matrices, train/evaluate fields, phase markers, destination combinations, secret-like fields, summary orders, and resource arithmetic.
    - Tag and implement Design Properties 7 and 8.
    - **Property 7: Reproducible and phase-bounded jobs**
    - **Property 8: Approval summary consistency**
    - **Validates: Requirements 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.2, 7.3, 7.4, 7.5**

  - [x]* 5.5 Write property tests for safety, isolation, determinism, and diagnostics
    - Create `tests/test_phase4_boundary_properties.py` with generated forbidden command variants, external action classes, relative/escaping paths, protected file sets, repeated validations, and invalid dependency declarations.
    - Tag and implement Design Properties 2, 9, 10, and 11.
    - **Property 2: Pre-approval safety invariant**
    - **Property 9: Fixture write confinement and preservation**
    - **Property 10: Deterministic validation**
    - **Property 11: Guard diagnostic traceability**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.3, 9.4, 9.5, 9.6, 9.7, 10.3, 10.5**

- [x] 6. Integrate repository contract checks and regression validation
  - [x]* 6.1 Add static skill, template, fixture-inventory, and task-traceability tests
    - Create `tests/test_phase4_repository_contract.py` to verify distinct skill responsibilities, synchronized required plan/job fields, front-loaded defaults, all required guard IDs, and requirement references on every implementation leaf task.
    - Assert Phase 4 additions remain under skills/templates/tests/spec paths and do not add a production runner, agent loop, Run artifact, checkpoint, W&B cache, or Slurm log.
    - _Requirements: 9.3, 10.1, 10.2, 10.4, 10.5_

  - [x]* 6.2 Run targeted and full automated regression suites and fix local validation defects
    - Run the bounded Phase 4 pytest files first, then the existing local test suite with non-watch execution.
    - Fix schema, fixture, validator, or compatibility failures without weakening approval, provenance, boundary, or preservation checks.
    - Confirm no protected repository data changed and no prohibited side effect occurred.
    - _Requirements: 8.1, 8.2, 8.3, 9.2, 9.3, 9.5, 9.6, 10.5_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for a faster implementation, though the Phase 4 completion criteria are strongest when all validation tasks are completed.
- Each leaf task references specific acceptance criteria for traceability.
- Property tests use at least 100 generated examples per property and include the required feature/property tag.
- Test writes are restricted to pytest `tmp_path`; tracked fixtures and the existing example experiment are read-only.
- External destinations are validated as planned metadata only. Phase 6 enables SSH/Slurm, Phase 7 enables live W&B, and Phase 8 enables Hugging Face Hub operations.
- No task authorizes training/evaluation execution, a real Run, an external integration, a Git commit, or modification of user-owned experiment records.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "2.1"] },
    { "id": 1, "tasks": ["2.2", "4.1"] },
    { "id": 2, "tasks": ["3.1", "3.2", "3.3", "3.4", "4.2"] },
    { "id": 3, "tasks": ["4.3"] },
    { "id": 4, "tasks": ["5.1", "5.2", "5.3", "5.4", "5.5", "6.1"] },
    { "id": 5, "tasks": ["6.2"] }
  ]
}
```
