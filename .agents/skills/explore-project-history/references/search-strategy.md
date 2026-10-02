# Search Strategy for Prior Research Discovery

## Overview

This reference defines a deterministic, local, read-only search strategy for the `explore-project-history` skill. The result is a complete evidence inventory and synthesis, not an experiment plan or execution action.

## Scope and Safety

Permitted operations:

- Read local repository files
- List local directories
- Search local file contents
- Inspect local Git logs and diffs without changing history
- Synthesize evidence in the response

Prohibited operations:

- Writing project, experiment, Run, or planning artifacts
- Running training or evaluation entrypoints
- Contacting SSH, Slurm, W&B, Hugging Face Hub, or other external systems
- Fetching Git remotes or creating commits
- Treating remote IDs or destinations as live-verified evidence

## Search Dimensions

Derive search terms and relevance from the request across these dimensions:

```yaml
model: <model family or identifier>
dataset: <dataset and configuration>
technique: <method such as LoRA>
objective: <research question or hypothesis>
parameter_range: <ablation or sweep range>
metrics: [<primary and comparison metrics>]
evaluation: <split, protocol, seeds, aggregation>
```

Use these dimensions both to select relevant experiments and to classify duplication. Record the dimensions searched so a `Novel Work` result is bounded to the inspected local scope.

## Required Source Inventory

The report must account for every applicable source class. Use exact repository-relative paths; for Git evidence use a commit identifier and, when possible, an affected path.

| Source class | Required search | Inventory record |
|---|---|---|
| Project settings | Root `project-plan.md` | Exact path as inspected, or missing/unpopulated |
| Project conclusions | Root `project-log.md` | Exact path as inspected, or missing/unpopulated |
| Experiment plans | Relevant `experiments/*/plan.md` | One record per relevant path; explicit missing record where expected |
| Experiment journals | Relevant `experiments/*/journal.md` | One record per relevant path; explicit missing record where expected |
| Structured results | Relevant `experiments/*/results.yaml` | One record per relevant path; explicit missing record where expected |
| Job configurations | Relevant `experiments/*/jobs/*.yaml` | One record per relevant path; explicit missing record where expected |
| Git history | Relevant local commits and diffs | Commit ID plus path/finding, or no relevant entry found |

An inspected source stays in the inventory even when it yields no finding. A source discovered through a summary must still be inspected directly when available and relevant.

## Root Records and Templates

Only populated files at the repository root count as current project records:

- `project-plan.md`
- `project-log.md`

Files such as `templates/project-plan.md`, `templates/project-log.md`, `templates/journal.md`, and `templates/results.yaml` define examples or schemas. They are not project evidence, do not satisfy a missing root-source check, and must not support a current finding or baseline. When only a template exists, record the corresponding root source as missing or unpopulated.

## Search Procedure

### 1. Inventory Root Project Records

Check exact root paths rather than searching by basename alone.

For a populated `project-plan.md`, extract only context needed for discovery: project scope, constraints, stable settings, intended datasets/models, and evidence policies.

For a populated `project-log.md`, extract project-level conclusions, cross-experiment comparisons, experiment links, and future directions. Follow referenced local experiment paths and inventory them separately.

If either root file is absent, empty, or only placeholder content, create a `missing_sources` entry with the exact expected path and reason.

### 2. Inventory Experiments Before Filtering

List `experiments/` and identify candidate directories using the search dimensions. Inspect each candidate's `plan.md` to determine relevance. Include experiments that may establish:

- direct model/dataset/technique overlap;
- the same research objective or parameter range;
- a comparable metric or baseline;
- a failed or abandoned approach;
- reusable job settings; or
- evidence that the request duplicates earlier work.

Record why an experiment is relevant or excluded. Do not infer that a missing journal or results file has no relevant information; record it as missing.

### 3. Inspect Every Relevant Experiment Source

For each relevant experiment, inspect:

- `plan.md`: intended objective, hypothesis, baseline, variables, controls, and status
- `journal.md`: narrative observations, interpretations, caveats, conclusions, and recommendations
- `results.yaml`: structured metrics, run summaries, outcome assessments, and configuration facts
- `jobs/*.yaml`: local reproducible settings and resource declarations

Never run a job configuration. A configured W&B run, Hugging Face repository, SSH host, or Slurm backend is descriptive metadata only.

### 4. Inspect Local Git Provenance

Use bounded, read-only local Git inspection, for example:

```bash
git log --oneline --all -- experiments/
git log --oneline --all -- experiments/<experiment-id>/
git log --oneline --all --grep="<relevant-term>"
git show --stat <commit>
git show <commit> -- <relevant-path>
```

Use `git show` on a relevant path before claiming that a commit supports a substantive finding. Record full commit IDs in the report when available. Do not fetch, pull, query hosting APIs, change branches, or modify history.

### 5. Close the Inventory

Before synthesis, verify that every required source class is represented by at least one `inspected` or `missing` record as applicable. Also verify that every relevant experiment has records for its plan, journal, structured results, and relevant job YAML.

A minimal inventory record is:

```yaml
- source_type: structured_results
  status: inspected
  source_ref: experiments/example/results.yaml
  relevance: supports accuracy comparison
```

A missing-source record is:

```yaml
- source_type: project_log
  status: missing
  source_ref: project-log.md
  reason: no populated root project log exists; template files are not project evidence
```

## Provenance Rules

### Repository-Path Evidence

Every file-backed finding must cite an exact repository-relative path, for example:

```yaml
statement: rank 16 achieved accuracy 0.874
support: direct
sources:
  - experiments/example-lora-rank-ablation/results.yaml
```

Line numbers are optional precision, not a substitute for the path.

### Git Evidence

Every history-backed finding must cite a commit identifier. Include a path when the finding depends on file content:

```yaml
statement: the example experiment entered the repository in this change
support: direct
sources:
  - commit: <full-commit-id>
    path: experiments/example-lora-rank-ablation/
```

A commit message supports only the historical statement expressed by that message. Quantitative or scientific claims require inspection of the relevant committed file.

### Evidence versus Interpretation

Label each item:

- `direct`: explicitly present in a cited source
- `derived`: calculated or compared from cited local values
- `interpretation`: qualitative synthesis of cited evidence
- `unresolved`: insufficient or incompatible evidence

Search terms, directory names, external URLs, W&B run IDs, and Hugging Face repository names are not standalone proof of a scientific finding.

## Structured-versus-Narrative Comparison

Structured results are authoritative for matching quantitative comparisons, but they do not erase narrative discrepancies.

For every metric mentioned in both `results.yaml` and a narrative source:

1. Normalize the metric name without changing meaning.
2. Establish whether model/configuration, dataset, split, seed/aggregation, checkpoint, and evaluation protocol match.
3. Compare exact values and units.
4. Record agreement as corroboration.
5. Record any mismatch in `conflicts`, even if structured results will be used for the numeric comparison.
6. If contexts differ or are incomplete, do not choose between values; mark the comparison unresolved.

Conflict record:

```yaml
- metric: accuracy
  context: <model, dataset, split, aggregation>
  structured:
    value: <value>
    source_ref: experiments/<id>/results.yaml
  narrative:
    value_or_claim: <value or text>
    source_ref: experiments/<id>/journal.md
  status: explained | unresolved
  explanation: <local evidence only>
  impact: <baseline/conclusion usability>
```

When contexts match and values conflict, use the structured value for quantitative comparison while explicitly retaining the conflict. Narrative sources remain authoritative for their own observations, caveats, and interpretations.

## Baseline Support Rules

A supported baseline requires all of:

```yaml
model: <identifier and relevant configuration>
dataset: <identifier/configuration>
split: <evaluation split>
metric:
  name: <name>
  value: <numeric value>
  direction: maximize | minimize
evaluation_context: <seed/aggregation/protocol when available>
source_ref: <repository path or Git commit>
```

Before recommending a baseline, confirm that:

- the cited source actually contains or directly supports the value;
- its evaluation context is comparable to the requested experiment;
- any structured/narrative conflict is recorded; and
- the baseline is not merely an uncited assertion in a template or plan.

If any material support is unavailable, report:

```yaml
baseline:
  status: unresolved
  missing_support: <value, split, context, or provenance>
  research_grill_decision: <one focused decision to resolve later>
```

Do not interpolate, estimate, select a convenient prior value, or convert an unsupported external citation into repository evidence. The Research Grill resolves unsupported baseline decisions; discovery only identifies the gap.

## Duplication Classification

### Comparison Matrix

Compare the request and each relevant experiment on:

| Dimension | Requested | Prior experiment | Match status |
|---|---|---|---|
| Objective/hypothesis | | | exact/partial/different/unknown |
| Model/configuration | | | exact/similar/different/unknown |
| Dataset/configuration/split | | | exact/similar/different/unknown |
| Technique | | | exact/similar/different/unknown |
| Parameter range | | | exact/overlap/disjoint/unknown |
| Metrics/protocol | | | exact/comparable/different/unknown |
| Controlled settings | | | exact/partial/different/unknown |

### Classification Rules

Assign exactly one overall level:

- **Exact Duplicate**: objective and all material design/evaluation dimensions are the same.
- **Near Duplicate**: the core objective is the same and most material dimensions match, with bounded differences such as additional seeds, a small range extension, or one added metric.
- **Related Work**: one or more meaningful dimensions overlap, but the objective or material design differs enough to answer a different question.
- **Novel Work**: no significant overlap appears in the complete inspected local evidence.

Unknown dimensions cannot establish an exact duplicate. Report them as gaps. For every classification include matched dimensions, different or unknown dimensions, evidence paths/commits, and one recommendation:

- `review existing`
- `extend existing`
- `clarify intent`
- `proceed`

Do not collapse all overlap into “potential duplicate”; the report must select and justify one of the four levels.

## Discovery Report Contract

The report must contain these sections even when empty:

1. `Request and Search Scope`
2. `Inspected-Source Inventory`
3. `Missing Sources`
4. `Findings`
5. `Comparable Baselines`
6. `Structured-vs-Narrative Conflicts`
7. `Reusable Local Settings`
8. `Git History Notes`
9. `Duplication Assessment`
10. `Gaps and Handoff`

Use `None identified` rather than omitting an empty conflicts, findings, settings, or gaps section.

Example inventory:

```markdown
### Inspected-Source Inventory
| Source type | Status | Repository path or Git provenance | Relevance/result |
|---|---|---|---|
| project log | missing | `project-log.md` | No populated root record; template excluded |
| experiment plan | inspected | `experiments/example/plan.md` | Model and technique overlap |
| structured results | inspected | `experiments/example/results.yaml` | Supports metric comparison |
| Git history | inspected | commit `<full-id>`, path `experiments/example/` | Establishes change provenance |
```

Example finding:

```markdown
- **Rank 16 achieved 0.874 accuracy.**
  - Evidence: `experiments/example/results.yaml`
  - Support: direct
```

Example unresolved baseline:

```markdown
- **Requested baseline**: unresolved
  - Missing support: no comparable value with a cited local evaluation split
  - Research Grill decision: choose or supply an evidence-backed baseline
```

## Completion Checklist

Before returning discovery results, confirm:

- [ ] Root `project-plan.md` is inspected or explicitly missing/unpopulated.
- [ ] Root `project-log.md` is inspected or explicitly missing/unpopulated.
- [ ] Every relevant experiment plan is inventoried.
- [ ] Every relevant experiment journal is inventoried or explicitly missing.
- [ ] Every relevant structured result is inventoried or explicitly missing.
- [ ] Every relevant job configuration is inventoried or explicitly missing.
- [ ] Relevant local Git entries are inventoried, or absence is explicit.
- [ ] Every finding cites a repository path or commit identifier.
- [ ] Matching structured and narrative metrics were compared.
- [ ] Every mismatch has an explicit conflict record.
- [ ] Every baseline value is supported or marked unresolved.
- [ ] Duplication is classified as exact, near, related, or novel with evidence.
- [ ] Templates are not treated as populated project evidence.
- [ ] No file was modified, no job or Run was created, and no external system was contacted.
