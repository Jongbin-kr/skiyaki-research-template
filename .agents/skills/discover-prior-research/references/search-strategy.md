# Search Strategy for Prior Research Discovery

## Overview

This document defines the systematic approach for discovering and consolidating prior experiment findings in the AI/ML research workspace. Use this strategy when the `discover-prior-research` skill is invoked to ensure comprehensive coverage and accurate reporting.

## Search Locations

### 1. Project-Level Documentation

**File**: `project-log.md` (workspace root)

**Purpose**: Contains project-level conclusions, cross-experiment insights, and high-level findings

**Search Strategy**:
- Read entire file if present
- Look for:
  - Overall project conclusions
  - Comparative statements across experiments
  - Lessons learned that apply broadly
  - References to specific experiments
  - Decisions about future research directions

**Tools**: `read_file`

### 2. Experiment Journals

**Files**: `experiments/*/journal.md`

**Purpose**: Contains narrative documentation of experiment execution, observations, and conclusions

**Search Strategy**:
- Use `grep_search` to find experiments mentioning relevant terms
- For each matching experiment, read the complete journal
- Look for:
  - Experiment objectives and motivation
  - Implementation decisions and rationale
  - Observations during training/evaluation
  - Unexpected findings or anomalies
  - Final conclusions and recommendations
  - References to baseline comparisons

**Tools**: `grep_search` with pattern `includePattern="experiments/*/journal.md"`, then `read_file`

### 3. Structured Results

**Files**: `experiments/*/results.yaml`

**Purpose**: Contains structured metrics, hyperparameters, and quantitative outcomes

**Search Strategy**:
- List all experiment directories
- Read results.yaml from each experiment
- Extract:
  - Final metrics (accuracy, loss, perplexity, etc.)
  - Hyperparameters used
  - Model configuration
  - Dataset information
  - W&B run IDs for verification
  - Hugging Face Hub locations

**Tools**: `list_directory` on `experiments/`, then `read_file` for each results.yaml

### 4. Git History

**Files**: Git commit logs and diffs

**Purpose**: Tracks changes to experiments over time, reveals iteration patterns

**Search Strategy**:
- Use `git log --all --grep="<search-term>"` to find relevant commits
- Use `git log --oneline --all -- experiments/` to see experiment-related changes
- For specific experiments, use `git log -- experiments/<experiment-name>/`
- Look for:
  - When experiments were created/modified
  - Configuration changes between runs
  - Abandoned approaches
  - Iteration patterns

**Tools**: `execute_bash` with git commands

## Evidence Consolidation Approach

### Combining Findings from Multiple Sources

When multiple sources provide information about the same topic:

1. **Prioritize by Specificity**:
   - Structured data (results.yaml) > Narrative conclusions (journal.md) > High-level summaries (project-log.md)
   - More recent findings > older findings (check Git timestamps if needed)

2. **Cross-Reference for Validation**:
   - Verify quantitative claims in journals against results.yaml
   - Confirm project-log statements against actual experiment outcomes
   - Check W&B run IDs when metrics are mentioned

3. **Resolve Conflicts**:
   - If metrics differ between journal and results.yaml, prefer results.yaml (structured source)
   - If conclusions differ, note both and flag the discrepancy
   - Check Git history to understand evolution of understanding

4. **Synthesize Narrative + Quantitative**:
   - Combine "model achieved 92% accuracy" (results.yaml) with "accuracy plateaued due to overfitting on validation set" (journal.md)
   - Link quantitative outcomes to qualitative observations

## Duplicate Experiment Detection

### Similarity Criteria

Two experiments are considered **similar** (potential duplicates) if they share:

1. **Same Core Objective**:
   - Testing the same hypothesis
   - Exploring the same hyperparameter
   - Using the same evaluation methodology

2. **Overlapping Hyperparameter Space**:
   - Same model architecture
   - Same dataset
   - Hyperparameter values within ±10% (for continuous values)
   - Same categorical hyperparameters (optimizer, activation functions, etc.)

3. **Comparable Metrics**:
   - Measuring the same evaluation metrics
   - Using the same test/validation splits

### Detection Process

1. **Extract Key Identifiers** from each experiment:
   ```yaml
   objective: "<what is being tested>"
   model: "<architecture name>"
   dataset: "<dataset identifier>"
   key_hyperparams:
     learning_rate: <value>
     batch_size: <value>
     lora_rank: <value>  # example
   metrics: ["<metric1>", "<metric2>"]
   ```

2. **Compare Pairwise**:
   - Check if objectives are semantically similar
   - Compare model and dataset for exact match
   - Check if key_hyperparams are within similarity threshold
   - Verify metrics overlap

3. **Report Duplicates with Evidence**:
   - List similar experiments together
   - Show which criteria matched
   - Include outcome comparison if both completed
   - Note any differences that make them non-duplicates

### Example Duplicate Detection

```
POTENTIAL DUPLICATES FOUND:
- Experiment: lora-rank-ablation-r16
- Experiment: lora-rank-sweep-r16
- Similarity: Both test LoRA rank=16 on same base model
- Difference: First is part of ablation study, second is part of sweep
- Recommendation: Reuse results from lora-rank-ablation-r16
```

## Reporting Format for Findings

### Structure for Main Agent Report

Present findings in the following structured format:

```markdown
## Prior Research Discovery Results

### Search Query
- **User Request**: <original user question or task>
- **Search Terms**: <keywords/patterns used>
- **Date**: <search date>

### Experiments Found

#### Experiment 1: <experiment-name>
- **Location**: `experiments/<experiment-name>/`
- **Objective**: <from journal.md or plan.md>
- **Status**: <completed | in-progress | abandoned>
- **Key Findings**:
  - <finding 1 with source: journal.md line X or results.yaml>
  - <finding 2>
- **Metrics**: <key metrics from results.yaml>
  - accuracy: X.XX
  - loss: X.XX
- **W&B Run**: <run-id if available>
- **HF Hub**: <model location if uploaded>

#### Experiment 2: <experiment-name>
...

### Project-Level Conclusions
<From project-log.md if relevant>

### Duplicate Detection Results
<List of similar experiments with recommendations>

### Recommended Baseline
**Experiment**: <name>
**Reason**: <why this is the best baseline for comparison>
**Metrics to Beat**:
- accuracy: X.XX
- loss: X.XX

### Evidence Links
- [Experiment 1 Journal](experiments/<name>/journal.md)
- [Experiment 1 Results](experiments/<name>/results.yaml)
- [Project Log](project-log.md)
- Git: `git log --oneline -- experiments/<name>/`

### Gaps Identified
<Areas not covered by prior research that may need new experiments>
```

### Reporting Guidelines

1. **Be Comprehensive but Concise**:
   - Include all relevant experiments
   - Summarize key findings, don't reproduce entire journals
   - Link to sources for details

2. **Prioritize Actionable Information**:
   - Highlight baseline metrics to beat
   - Note successful approaches to replicate
   - Warn about failed approaches to avoid

3. **Provide Evidence Trails**:
   - Always cite sources (file paths, line numbers, git commits)
   - Include W&B run IDs for metric verification
   - Link to Hugging Face Hub for model inspection

4. **Flag Uncertainties**:
   - Note when information is incomplete
   - Highlight conflicts between sources
   - Suggest verification steps if needed

5. **Format for Agent Consumption**:
   - Use structured markdown (headers, lists, code blocks)
   - Include exact file paths for Main Agent to read
   - Provide actionable next steps

## Example Search Workflow

```bash
# 1. Search for experiments matching topic
grep_search query="learning rate" includePattern="experiments/*/journal.md"

# 2. List all experiment directories
list_directory path="experiments/" depth=1

# 3. Read results from relevant experiments
read_file path="experiments/lr-sweep-001/results.yaml"
read_file path="experiments/lr-sweep-001/journal.md"

# 4. Check project-level conclusions
read_file path="project-log.md"

# 5. Review git history for context
execute_bash command="git log --oneline --all -- experiments/lr-sweep-001/"

# 6. Consolidate and report findings
# (Generate report following format above)
```

## Notes

- **Always verify W&B runs** if run IDs are provided in results.yaml
- **Cross-check metrics** between journal claims and results.yaml
- **Consider temporal order** - later experiments may invalidate earlier conclusions
- **Look for abandoned experiments** - these often contain valuable negative results
- **Check for plan.md** in experiment directories if journal.md is missing
