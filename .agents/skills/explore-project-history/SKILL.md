# Explore Project History Skill

Inspect this repository's past experiments, results, project log, and Git history before planning new work.

## Purpose

Inspect and synthesize local repository evidence before a new experiment is planned. Produce a traceable discovery report covering prior findings, supported baselines, reusable settings, duplication, conflicts, and evidence gaps.

This skill is read/synthesis-only. It does not choose a final experimental design, write planning artifacts, create a Run, execute jobs, contact external systems, or commit changes.

## When to Use

Use before creating any new experiment plan to:

- Identify related past work and negative results
- Extract repository-supported baseline configurations and metrics
- Find reusable local job settings
- Detect exact, near, or partial duplication
- Surface conflicts and unresolved scientific decisions for the Research Grill

## When NOT to Use

- During experiment execution
- For routine status checks when the caller only needs one known project record
- To query SSH, Slurm, W&B, Hugging Face Hub, or any other external system
- To generate or approve an experiment plan
- When the user explicitly requests ignoring past work

## Operating Boundary

Allowed work is limited to local repository reads, local Git-history inspection, and synthesis in the response. Treat W&B IDs, Hugging Face locations, remote paths, and Slurm metadata as unverified references only; do not follow or verify them through external services. Do not modify project or experiment files while performing discovery.

## Procedure

### 1. Build the Source Inventory

**Objective**: Account for every applicable evidence class before drawing conclusions.

Inspect and record each available source in these classes:

1. Root `project-plan.md`
2. Root `project-log.md`
3. Each relevant `experiments/<experiment-id>/plan.md`
4. Each relevant `experiments/<experiment-id>/journal.md`
5. Each relevant `experiments/<experiment-id>/results.yaml`
6. Each relevant `experiments/<experiment-id>/jobs/*.yaml`
7. Each relevant local Git-history entry

First inventory `experiments/` and use the request's model, dataset, technique, objective, metric, and parameter range to determine relevance. A source is relevant when it can establish overlap, a baseline, a reusable setting, a prior conclusion, or historical context. Do not silently omit a relevant source because another file summarizes it.

For every source class, record either:

- `inspected`: the exact repository-relative path, or a Git commit identifier plus path when applicable; or
- `missing`: the expected path or search scope and a concise reason, such as absent, unpopulated, or no relevant Git entry found.

The inventory is part of the final report, including inspected sources that produced no finding. Search terms alone are not provenance.

### 2. Read Project Context

If root `project-plan.md` exists and is populated, extract project scope, constraints, and stable settings needed to interpret prior work. If it is absent or unpopulated, add it to `missing_sources`.

If root `project-log.md` exists and is populated, inspect it for cross-experiment conclusions, experiment links, metric summaries, and recommended next steps. If it is absent or unpopulated, add it to `missing_sources`.

Files under `templates/`, including `templates/project-plan.md` and `templates/project-log.md`, are examples only. They never satisfy the root-source check and must not be cited as current project evidence. The existence of a template does not change an absent root record into an inspected source.

### 3. Inspect Relevant Experiments

For every relevant experiment:

- Read `plan.md` for the objective, hypothesis, model, dataset, technique, variables, controls, intended baseline, and status.
- Read `journal.md` for narrative observations, conclusions, caveats, failures, and recommendations.
- Read `results.yaml` for structured metrics, configurations, run summaries, and outcome assessments.
- Read relevant `jobs/*.yaml` for reproducible settings; do not execute the entrypoints.
- Record absent expected files explicitly rather than inferring their contents.

A plan's intended or externally attributed baseline is not automatically a locally validated baseline. Preserve its stated source and support status.

### 4. Inspect Relevant Local Git History

Use read-only local Git commands to identify relevant commits, removed experiments, reversions, and changes in interpretation. Record the full commit identifier when available and the affected repository path. A commit message alone supports only what it states; inspect the relevant diff before using it as evidence for a substantive finding.

Git provenance has one of these forms:

- `commit: <full-commit-id>`
- `commit: <full-commit-id>, path: <repository-relative-path>`

Do not fetch remotes, inspect hosted services, create branches, or create commits.

### 5. Extract Findings and Provenance

Every reported finding must cite at least one inspected evidence reference:

- Repository evidence: `path: experiments/<id>/results.yaml`
- Git evidence: `commit: <full-commit-id>, path: experiments/<id>/...`

Include line numbers when useful, but a line number never replaces the path or commit. Separate evidence from inference:

- **Supported finding**: directly stated or derivable from cited local evidence
- **Interpretation**: a synthesis based on cited evidence
- **Unresolved**: not supported well enough to report as fact

Do not cite W&B run IDs, Hugging Face repositories, papers named in a plan, or other external references as verified evidence unless their supporting content exists locally in an inspected repository source.

### 6. Reconcile Structured and Narrative Evidence

When `results.yaml` and narrative sources (`journal.md`, `project-log.md`, or plan prose) describe the same metric or quantitative outcome:

1. Compare metric name, value, direction, dataset/configuration, split, seed or aggregation, and evaluation context.
2. If they agree, record the corroborating references.
3. If they differ, add an explicit conflict record containing:
   - the metric and comparison context;
   - the structured value and exact source path;
   - the narrative value or claim and exact source path;
   - whether the mismatch is explainable from local evidence; and
   - the effect on baseline or conclusion usability.
4. Use structured results as the quantitative value for comparison when contexts match, but never hide or silently overwrite the narrative mismatch.
5. If contexts do not match or cannot be established, keep the values separate and mark the comparison unresolved.

Narrative conclusions remain useful for interpretation and caveats; structured precedence applies only to matching quantitative comparisons.

### 7. Extract Supported Baselines and Reusable Settings

A baseline entry must include:

- model and configuration;
- dataset and split;
- metric name, value, and direction;
- relevant evaluation context such as seed or aggregation when available; and
- at least one inspected repository path or Git commit identifier supporting the value.

Reusable job settings must cite the relevant `jobs/*.yaml` path and remain descriptive. Do not label settings validated merely because a job file exists.

If local evidence does not support a requested baseline value, report it as `unresolved`; do not estimate, copy an uncited value, or invent one. State what evidence is missing and hand the unresolved baseline decision to the Research Grill. Discovery may identify the question, but it must not choose the value or create a plan.

### 8. Classify Duplication

Compare the request with prior experiments across:

- model;
- dataset and split;
- technique;
- research objective or hypothesis;
- parameter or ablation range;
- metrics and evaluation method; and
- important controlled settings.

Assign exactly one classification:

- **Exact Duplicate**: same objective and materially same model, dataset, technique, design, parameter range, and evaluation.
- **Near Duplicate**: same core objective with limited material differences, such as added seeds or a modest range extension.
- **Related Work**: meaningful overlap in model, dataset, technique, objective, or range, but a different question or design.
- **Novel Work**: no significant overlap in the inspected repository evidence.

Report matched dimensions, differing dimensions, cited evidence, and a recommendation: review existing, extend existing, clarify intent, or proceed. `Novel Work` means no overlap was found in the inspected local scope, not that no related work exists elsewhere.

### 9. Synthesize the Discovery Report

Use this structure:

```markdown
## Project History Review

### Request and Search Scope
- Request: <request>
- Relevance dimensions: <model, dataset, technique, objective, range, metrics>
- Local scope only: yes

### Inspected-Source Inventory
| Source type | Status | Repository path or Git provenance | Relevance/result |
|---|---|---|---|
| project plan | inspected/missing | `project-plan.md` | <context or reason> |
| project log | inspected/missing | `project-log.md` | <findings or reason> |
| experiment plan | inspected/missing | `experiments/<id>/plan.md` | <result> |
| experiment journal | inspected/missing | `experiments/<id>/journal.md` | <result> |
| structured results | inspected/missing | `experiments/<id>/results.yaml` | <result> |
| job configuration | inspected/missing | `experiments/<id>/jobs/<file>.yaml` | <result> |
| Git history | inspected/missing | commit `<full-id>`, path `<path>` | <result> |

### Missing Sources
- `<expected path or scope>`: <absent, unpopulated, or no relevant entry>

### Findings
- **<finding>**
  - Evidence: `<repository path>` and/or commit `<full-id>`
  - Support: direct | derived | interpretation

### Comparable Baselines
- **<baseline name>**: <metric>=<value> (<direction>) on <dataset/split>
  - Evidence: `<repository path>` or commit `<full-id>`
  - Support status: supported
- **Requested baseline**: unresolved
  - Missing support: <what evidence is required>
  - Research Grill decision: <focused unresolved decision>

### Structured-vs-Narrative Conflicts
- Metric/context: <metric and evaluation context>
- Structured: <value>, source `<results path>`
- Narrative: <value/claim>, source `<journal/log/plan path>`
- Resolution/status: <explained or unresolved>
- Impact: <effect on baseline or conclusion>

### Reusable Local Settings
- <setting>: <value>, source `<job YAML path>`

### Duplication Assessment
- Classification: Exact Duplicate | Near Duplicate | Related Work | Novel Work
- Matched dimensions: <list>
- Different dimensions: <list>
- Evidence: `<path>` and/or commit `<full-id>`
- Recommendation: review existing | extend existing | clarify intent | proceed
- Justification: <evidence-backed rationale>

### Gaps and Handoff
- <missing evidence, unresolved baseline, or material uncertainty for Research Grill>
```

Use `None identified` for an empty conflicts or gaps section. Never omit `Inspected-Source Inventory`, `Missing Sources`, `Structured-vs-Narrative Conflicts`, or `Duplication Assessment`.

## Success Criteria

Discovery is complete when:

1. Every applicable source class is represented as inspected or explicitly missing.
2. Every finding and supported baseline has repository-path or Git-commit provenance.
3. Matching structured and narrative metrics were compared and conflicts were recorded.
4. Duplication is classified with evidence and dimensional differences.
5. Root templates were not treated as populated project evidence.
6. Unsupported baseline values remain unresolved for the Research Grill.
7. The work remained local, read/synthesis-only, and produced no planning or execution side effects.

## Output

Return the Discovery Report to the Main Agent. Include the complete source inventory, missing sources, findings with provenance, supported or unresolved baselines, conflict records, reusable local settings, Git context, duplication classification, and focused gaps for the Research Grill.
