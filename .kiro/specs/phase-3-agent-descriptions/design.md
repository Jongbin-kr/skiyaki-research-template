# Design Document: Phase 3 Agent Descriptions

## Overview

Phase 3 converts the five existing specialist descriptions from uneven role summaries into consistent delegation contracts and adds selective routing to the root `AGENTS.md`. Existing filenames remain stable. The user-facing specialist names Hugging Face Curator and Slurm Debugger are explicit aliases for the existing files `huggingface-managing-specialist.md` and `slurm-managing-specialist.md`.

The implementation medium is Markdown. The repository contains Python helper scripts from Phase 2, but Phase 3 does not modify or add executable Python. External integrations remain roadmap-gated: SSH and Slurm in Phase 6, W&B in Phase 7, and Hugging Face Hub in Phase 8.

### Goals and Non-Goals

#### Goals

- Give every specialist a complete, reviewable delegation contract.
- Define deterministic Main Agent routing in `AGENTS.md`.
- Load only the description required for the immediate bounded delegation.
- Preserve existing filenames and links.
- Distinguish local artifact analysis from unavailable external operations.
- Align `README.md`, `AGENTS.md`, and specialist descriptions.
- Validate Phase 3 through documented human review.

#### Non-Goals

- Implement subagent runtime infrastructure.
- Add SSH or Slurm commands, submission, or live diagnosis.
- Add W&B API access.
- Add Hugging Face Hub access or uploads.
- Change experiment execution, evaluation, or run tracking.
- Add an automated specialist-contract validator.
- Rename skills or specialist description files.

## Architecture

```text
User request
    |
    v
Root AGENTS.md (Main Agent policy)
    |-- determine whether delegation is needed
    |-- select the narrowest matching specialist
    |-- construct a bounded delegation packet
    |-- load exactly one matching description
    v
agent-descriptions/<preserved-filename>.md
    |-- validate required inputs
    |-- enforce current phase and approval gates
    |-- perform only allowed local/documentation work
    |-- return evidence, work, risks, and next action
    v
Main Agent integrates the bounded result
```

The architecture has three documentation layers:

1. **Routing policy (`AGENTS.md`)**: selects a specialist and governs selective loading.
2. **Specialist contracts (`agent-descriptions/*.md`)**: define inputs, action boundaries, outputs, and escalation.
3. **User guidance (`README.md`)**: exposes names, paths, current availability, and delegation behavior without duplicating full contracts.

### File Impact

```text
AGENTS.md                                           # modify: routing and bounded delegation
README.md                                           # modify: names, paths, phase gates, selective loading
agent-descriptions/
├── research-journal-git.md                         # modify: standardized contract
├── wandb-analyst.md                                # modify: standardized contract, Phase 7 gate
├── huggingface-managing-specialist.md              # modify: Curator alias, Phase 8 gate
├── visualization-specialist.md                     # modify: standardized contract, local sources
└── slurm-managing-specialist.md                    # modify: Debugger alias, Phase 6 gate
```

No source, test, job, experiment, skill, or integration file is modified in Phase 3.

## Components and Interfaces

### 1. Main Agent Routing Policy

The `## Subagents` section in `AGENTS.md` becomes a compact routing contract with three parts.

#### 1.1 Canonical Routing Table

| Routing name | Trigger | Description path | Phase 3 capability |
|---|---|---|---|
| Research Journal & Git | Prior-work synthesis or experiment finalization/Git proposal | `agent-descriptions/research-journal-git.md` | Local repository evidence and documentation |
| W&B Analyst | Training-run comparison requiring specialist analysis | `agent-descriptions/wandb-analyst.md` | Local exported metrics only; live W&B starts Phase 7 |
| Hugging Face Curator | Model-card or Hub artifact curation | `agent-descriptions/huggingface-managing-specialist.md` | Local model-card drafting only; Hub operations start Phase 8 |
| Visualization Specialist | Research figures from available results | `agent-descriptions/visualization-specialist.md` | Local result and figure work; live W&B sources start Phase 7 |
| Slurm Debugger | Slurm failure diagnosis | `agent-descriptions/slurm-managing-specialist.md` | Offline review of user-provided artifacts only; live cluster access starts Phase 6 |

The routing name is canonical in Main Agent instructions. A description may retain its existing title, but alias text must make the mapping explicit.

#### 1.2 Selection Procedure

```markdown
1. Keep the task in the Main Agent when no specialist expertise is needed.
2. Identify the narrowest specialist whose trigger covers the bounded task.
3. Read only that specialist's description.
4. Build one delegation packet from the required inputs in that description.
5. Delegate one bounded task and integrate the returned evidence.
6. For a second specialist, repeat selection and loading as a separate delegation.
```

The procedure explicitly forbids preloading all descriptions. A broad request is decomposed before loading descriptions rather than sent as one cross-specialist delegation.

#### 1.3 Delegation Packet Interface

Every delegated task receives:

```yaml
objective: one verifiable outcome
scope:
  allowed: bounded actions for this delegation
  excluded: adjacent work retained by the Main Agent
inputs:
  paths: relevant repository paths
  evidence: user-provided records or prior findings
expected_output: specialist contract output relevant to the task
approval_constraints: approvals and roadmap gates that apply
```

This YAML is a documentation model, not a new serialized runtime format.

### 2. Specialist Contract Template

Each preserved specialist file uses the same top-level contract:

```markdown
# <Canonical or Existing Specialist Title>

> Routing name: ...
> Description path: ...
> Availability: ...

## Mission
## When to Invoke
## Required Inputs
## Allowed Actions
## Prohibited Actions
## Required Output
## Escalation
```

Existing useful sections such as Modes, Scope, Usage Guidelines, and visualization best practices may remain as subordinate or additional sections. The seven required headings provide a common interface.

#### 2.1 Required Inputs

Required Inputs name only evidence necessary for a bounded task, such as:

- Repository paths and search terms for prior-research discovery.
- Local run exports, metrics, and comparison objective for W&B analysis.
- Local checkpoint metadata, results, and intended audience for a model card.
- Source result files, requested plot, and output constraints for visualization.
- User-provided logs, job configuration, status output, and cluster context for offline Slurm diagnosis.

A specialist reports missing input instead of widening the search or inventing evidence.

#### 2.2 Allowed and Prohibited Actions

Allowed Actions distinguish reads from writes and state exact output locations where applicable. Prohibited Actions retain approval and evidence-integrity rules. A future external action may be described for roadmap context, but it is prohibited in Phase 3 and paired with the phase that owns implementation.

#### 2.3 Required Output Envelope

Every description requires these output categories:

```yaml
evidence:
  - source path or user-provided artifact
completed_work:
  - bounded analysis or created/updated artifact
unresolved_risks:
  - missing, uncertain, or contradictory evidence
recommended_next_action: one Main Agent action or null
```

Specialist-specific fields remain under these categories. For example, a visualization result also records formats and dimensions; a finalization result includes a commit proposal but no commit.

#### 2.4 Escalation

Escalation has two branches:

- **Missing input**: identify the exact missing artifact or decision and return control to the Main Agent.
- **Boundary or phase gate**: stop before the action, identify the prohibited or unavailable capability, cite the approval or roadmap dependency, and suggest a non-executing next step.

### 3. Specialist-Specific Design

#### 3.1 Research Journal & Git

- Preserve Discovery Mode and Finalize Mode.
- Discovery reads local project history and returns linked evidence, baselines, and duplication risk.
- Finalize verifies local completion artifacts, updates permitted research records, and proposes a commit.
- Commit creation remains approval-gated.
- Missing `project-plan.md` or `project-log.md` is reported explicitly; absence is not silently treated as empty content.

#### 3.2 W&B Analyst

- Current scope accepts local exports, run records, and metrics already present in the repository or supplied by the user.
- The specialist preserves source values and separates observations from interpretations.
- Live API queries, remote metadata changes, and remote lifecycle actions are unavailable until Phase 7.
- A request requiring live data returns a Phase 7 dependency plus instructions for supplying a local export as the non-executing alternative.

#### 3.3 Hugging Face Curator

- `Hugging Face Curator` is the routing name for `huggingface-managing-specialist.md`.
- Current scope drafts local model cards and reviews local metadata against documented policies.
- Hub queries, repository creation/modification, upload verification, and uploads are unavailable until Phase 8.
- Privacy, visibility, and push policy remain mandatory inputs for any future Hub operation.
- No credential may enter a generated document or commit proposal.

#### 3.4 Visualization Specialist

- Current scope produces figures from local results and user-provided data.
- Source values remain unchanged; filtering, aggregation, smoothing, axis truncation, or other transformations are disclosed.
- Live W&B retrieval is unavailable until Phase 7, but local W&B exports are valid inputs.
- Figure creation does not authorize a Git commit.

#### 3.5 Slurm Debugger

- `Slurm Debugger` is the routing name for `slurm-managing-specialist.md`.
- Current scope reviews user-provided logs, copied status output, and job YAML without contacting a cluster.
- SSH commands, scheduler queries, live status inspection, submission, resubmission, cancellation, and configuration mutation are unavailable until Phase 6.
- The specialist may recommend commands for the user to run, but must label commands as unexecuted and avoid claiming live verification.

### 4. README Integration

The README keeps concise specialist summaries but changes them to:

- Use the five canonical routing names.
- Link each name to the preserved filename.
- State current local capability and roadmap phase for external capability.
- Explain that the Main Agent loads one description only when making a bounded delegation.
- Avoid presenting explicit subagent requests as bypasses around routing, approvals, or phase gates.

The README does not duplicate the full contract; `AGENTS.md` remains authoritative for routing and each description remains authoritative for specialist behavior.

## Data Models

Phase 3 defines documentation structures rather than runtime objects or persisted application data.

| Model | Required fields | Purpose |
|---|---|---|
| Routing_Entry | canonical routing name, invocation trigger, preserved description path, Phase 3 capability | Maps one bounded task category to one selectively loaded specialist description. |
| Delegation_Packet | objective, allowed and excluded scope, input paths and evidence, expected output, approval constraints | Carries the bounded task from the Main_Agent to the selected specialist. |
| Specialist_Contract | routing metadata, Mission, When to Invoke, Required Inputs, Allowed Actions, Prohibited Actions, Required Output, Escalation | Standardizes each preserved specialist description without changing its filename or specialist scope. |
| Specialist_Output | evidence, completed work, unresolved risks, recommended next action | Returns a reviewable bounded result to the Main_Agent. |

The models are expressed in Markdown tables, headings, and illustrative YAML only. Phase 3 introduces no runtime schema, serializer, database, validator, or external-service data model.

## Roadmap Capability Matrix

| Capability | Phase 3 behavior | Owning phase |
|---|---|---|
| Local repository research discovery and finalization drafting | Available | Phase 3 |
| Local metrics/run-export analysis | Available | Phase 3 |
| Live W&B API query or mutation | Unavailable | Phase 7 |
| Local model-card drafting and metadata review | Available | Phase 3 |
| Hugging Face Hub query, repository operation, or upload | Unavailable | Phase 8 |
| Local visualization from available files | Available | Phase 3 |
| Offline Slurm diagnosis from supplied artifacts | Available | Phase 3 |
| SSH, scheduler query, submission, cancellation, or live diagnosis | Unavailable | Phase 6 |

## Error Handling

| Condition | Required behavior |
|---|---|
| Required file is absent | Name the missing path and return control to Main Agent |
| Evidence conflicts across files | Cite each source, avoid choosing silently, and request adjudication |
| No specialist matches | Main Agent keeps the task; no descriptions are bulk-loaded |
| Multiple specialists match | Select the narrowest first or split into separate bounded tasks |
| Delegation packet is too broad | Specialist stops and identifies the scope that must be narrowed |
| Approval is missing | Specialist stops before the gated action and reports the required approval |
| External capability is unavailable | Specialist cites Phase 6, 7, or 8 and offers a local/non-executing alternative |
| Output path is outside allowed scope | Specialist returns the conflict without writing |

## Testing Strategy

Phase 3 uses review checks rather than executable contract validation.

### Review A: Contract Completeness

For each of the five descriptions, inspect the seven required headings and verify readable inputs, writable outputs, evidence expectations, and escalation behavior.

### Review B: Routing and Mapping

Cross-check `AGENTS.md` and `README.md` for exactly five canonical names, correct preserved paths, narrowest-match routing, bounded packet fields, and the prohibition on default bulk loading.

### Review C: Roadmap and Safety

Cross-check all present-tense capability claims. Verify Phase 6 for SSH/Slurm, Phase 7 for W&B, and Phase 8 for Hugging Face Hub. Review approval and prohibited-action clauses for every specialist.

### Review D: Scope and Links

Inspect the implementation diff to confirm only Phase 3 documentation changed, all relative links resolve, no filenames were changed, and no validator or integration code was added.

Review findings are recorded in the implementation change or pull-request checklist. Any conflict is corrected before completion.

## Correctness Properties

*A correctness property is an invariant that must hold across the finite Phase 3 documentation set. Because Phase 3 is documentation-only, these properties guide structured review and do not create property-based test code or an automated contract validator.*

### Property 1: Specialist contract completeness

For all five Specialist_Descriptions, the document contains Mission, When to Invoke, Required Inputs, Allowed Actions, Prohibited Actions, Required Output, and Escalation sections, and the contract identifies evidence, permitted writes, approval gates, missing-input behavior, out-of-scope behavior, completed work, risks, and next actions.

**Validates: Requirements 2.1**

**Additional traceability:** Requirements 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 7.1, 7.5

### Property 2: Routing uniqueness and selective loading

For any bounded task considered for delegation, the Main_Agent selects at most one narrowest matching specialist per delegation, loads only that specialist's preserved description path, supplies the bounded delegation packet, and retains unmatched work without loading all descriptions.

**Validates: Requirements 3.2**

**Additional traceability:** Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 7.2

### Property 3: Roadmap-gate consistency

For any Phase_3_Documentation statement about SSH, Slurm, W&B, or Hugging Face Hub, the statement distinguishes available local artifact work from unavailable external operations and maps external operations to Phase 6, Phase 7, or Phase 8 respectively.

**Validates: Requirements 4.4**

**Additional traceability:** Requirements 4.1, 4.2, 4.3, 4.5, 4.6, 5.5, 5.7, 5.11, 6.2, 6.5, 7.3

### Property 4: Safety, compatibility, and scope preservation

For all Phase 3 documentation changes, preserved specialist and skill filenames remain valid, every applicable approval and sensitive-artifact boundary remains explicit, source metrics and visualization data retain integrity, README links resolve to existing descriptions, and no execution, external integration, upload, or contract-validator implementation is introduced.

**Validates: Requirements 8.1**

**Additional traceability:** Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 6.1, 6.3, 6.4, 7.4, 7.6, 7.7, 8.2, 8.3, 8.4, 8.5

## Requirements Traceability

| Design component | Requirements |
|---|---|
| Canonical routing table and aliases | 1.1-1.5, 3.1 |
| Selection procedure and packet | 3.2-3.7 |
| Standard contract template | 2.1-2.7 |
| Documentation data models | 2.1-2.7, 3.1-3.7 |
| Specialist-specific boundaries | 4.1-5.11 |
| README integration | 6.1-6.5 |
| Documentation review strategy | 7.1-7.7 |
| File impact and non-goals | 8.1-8.5 |

## Implementation Notes

- Edit Markdown only.
- Preserve useful existing specialist content while reorganizing it under the standard contract headings.
- Prefer explicit current/future capability tables or callouts over scattered parenthetical phase notes.
- Keep `AGENTS.md` concise because it is always loaded; put specialist detail in selectively loaded description files.
- Do not add dependencies, scripts, schemas, tests, network calls, credentials, or shell wrappers.
