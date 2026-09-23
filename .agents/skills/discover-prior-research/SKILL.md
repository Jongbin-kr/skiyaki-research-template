# Discover Prior Research Skill

## Purpose

Search project history to find related experiments, baselines, and past findings before creating new experiment plans.

## When to Use

Before creating any new experiment plan. This skill should be invoked to:
- Identify related past work
- Extract reusable baseline configurations
- Find comparable metrics for benchmarking
- Detect potential duplication of prior experiments
- Surface relevant conclusions from project history

## When NOT to Use

- During experiment execution (information already in plan)
- For routine status checks (use project log directly)
- When user explicitly requests ignoring past work

## Procedure

### 1. Read Project Configuration

**Objective**: Understand project scope and constraints

**Actions**:
- Load `project-plan.md` from repository root
- Extract research objectives and scope from frontmatter and body
- Note project-level constraints (resource limits, infrastructure, policies)
- Identify stable configuration parameters (W&B entity, HF namespace, etc.)

**Output**: Project context for interpreting experimental relevance

### 2. Search Project Log

**Objective**: Find high-level conclusions related to current request

**Actions**:
- Read `project-log.md` from repository root
- Extract keywords from user's request (model names, techniques, datasets, metrics)
- Search for entries containing matching keywords
- Identify:
  - Related conclusions
  - Links to past experiment directories
  - Key metric values achieved
  - Recommended next steps that relate to current request

**Output**: List of potentially relevant experiments with context

### 3. Search Experiment Directories

**Objective**: Deep dive into related experiments for detailed information

**Actions**:
- List all subdirectories in `experiments/`
- For each experiment directory:
  - Read `plan.md` to understand research objective and design
  - Check similarity to current request (models, datasets, techniques, hypotheses)
  - If relevant:
    - Read `results.yaml` for final metrics and outcomes
    - Read `journal.md` for conclusions, insights, and recommendations
    - Note the experiment status (completed, failed, cancelled)
    - Extract reusable job configurations from `jobs/*.yaml`

**Relevance Criteria**:
- Uses same or similar models
- Uses same or similar datasets
- Tests related hypotheses
- Involves comparable techniques or methods
- Addresses similar research questions

**Output**: 
- List of related experiments with directories
- Comparable baseline metrics
- Reusable job configurations
- Relevant findings and insights

### 4. Search Git History

**Objective**: Identify if similar work was attempted but removed or reverted

**Actions**:
- Run `git log --all --oneline --grep="<keywords>"` with relevant keywords
- Check recent commits (last 50-100) for experiment-related changes
- Look for:
  - Experiments that were committed then removed
  - Reverted changes related to current request
  - Branch names indicating similar work
- If relevant commits found:
  - Use `git show <commit>` to inspect what was done
  - Check commit messages for rationale or conclusions
  - Determine why work was removed (failed, superseded, incorrect approach)

**Output**: Historical context about attempted similar work

### 5. Extract Baselines

**Objective**: Collect baseline configurations and metrics for comparison

**Actions**:
- From relevant experiments identified above:
  - Extract baseline model names and configurations
  - Extract baseline metric values (especially primary metrics)
  - Extract successful job configurations (hyperparameters, resources)
  - Identify best-performing runs and their settings
- Organize baselines by:
  - Model type
  - Dataset
  - Task type
  - Technique/method

**Output**: 
- Reusable baseline configurations with metric values
- Best-known results for comparison
- Validated hyperparameter settings

### 6. Duplication Detection

**Objective**: Determine if current request duplicates past work

**Actions**:
- Compare current request against related experiments:
  - Same research objective/hypothesis?
  - Same model, dataset, and technique combination?
  - Same experimental parameters?
- If exact match found:
  - Check experiment status (completed, failed, cancelled)
  - Check if user is aware of existing work
  - Assess whether repetition is intentional (validation, reproduction)
- If near match found:
  - Identify key differences
  - Determine if differences warrant new experiment
  - Assess if existing experiment could be extended

**Duplication Assessment Levels**:
- **Exact Duplicate**: Same objective, design, and parameters
- **Near Duplicate**: Same objective, minor parameter differences
- **Related Work**: Similar objective, different approach
- **Novel Work**: No significant overlap with past experiments

**Output**: 
- Duplication assessment with level
- Recommendation (proceed, review existing, extend existing, clarify intent)
- Justification for recommendation

### 7. Synthesize Findings

**Objective**: Present organized summary for planning phase

**Actions**:
- Group findings by relevance (highly relevant, somewhat relevant, tangentially related)
- For each related experiment:
  - Provide experiment ID and directory path
  - Summarize research objective and key findings
  - List relevant metric values
  - Note any conclusions or recommendations
  - Highlight reusable configurations
- Summarize duplication assessment
- Provide overall recommendation for proceeding

**Output Format**:
```markdown
## Prior Research Discovery

### Project Context
- [Project objectives relevant to request]
- [Key constraints from project-plan.md]

### Related Experiments

#### Highly Relevant
1. **experiment-id-1** (`experiments/experiment-id-1/`)
   - Objective: [brief description]
   - Status: [completed/failed/cancelled]
   - Key Findings: [1-2 sentence summary]
   - Metrics: [relevant values]
   - Reusable: [job configs, baselines]
   - Link: [path to journal.md or results.yaml]

[Repeat for each highly relevant experiment]

#### Somewhat Relevant
[Similar format for less relevant experiments]

### Baseline Information

**Available Baselines for Comparison**:
- Model: [name], Dataset: [name], Metric: [value]
- Source: [experiment or paper]
- Configuration: [link to job YAML]

### Git History Notes
[Any relevant information from commit history]

### Duplication Assessment

**Level**: [Exact Duplicate | Near Duplicate | Related Work | Novel Work]

**Analysis**: [Explanation of overlap with past work]

**Recommendation**: 
- [ ] Proceed with new experiment (novel work)
- [ ] Review existing experiment results (duplicate)
- [ ] Extend existing experiment (near duplicate)
- [ ] Clarify intent with user (ambiguous overlap)

**Justification**: [Why this recommendation]
```

## Success Criteria

The discovery is successful when:
1. All relevant past experiments are identified and summarized
2. Baseline configurations and metrics are extracted for comparison
3. Duplication assessment is clear and justified
4. Recommendation is actionable for next phase
5. User can make informed decision about proceeding

## Output

Return synthesized findings to Main Agent in the format specified above, including:
- List of related experiments with context
- Baseline information for comparison
- Git history insights (if any)
- Duplication assessment with recommendation
- All relevant paths and links for further review

## Notes

- **Thoroughness vs. Speed**: Balance comprehensive search with timely response. If project has many experiments, prioritize recent ones and those matching key terms.
- **False Positives**: Better to surface potentially relevant experiments than miss important ones. Let planning phase filter further.
- **Insufficient History**: If project is new with no experiments, state this clearly and note that current request will establish baseline.
- **Ambiguous Matches**: When relevance is uncertain, include experiment with note about ambiguity rather than excluding.
