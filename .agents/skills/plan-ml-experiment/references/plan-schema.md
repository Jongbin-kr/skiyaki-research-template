# Experiment Plan Schema

This document defines the structure and validation rules for experiment plan frontmatter in `plan.md` files.

## Overview

Experiment plans use YAML frontmatter to capture structured metadata that guides workflow execution. The frontmatter appears at the top of `plan.md` between `---` delimiters.

## Frontmatter Structure

### Required Fields

These fields MUST be present in all experiment plans:

#### `schema_version` (integer)
- **Type**: Integer
- **Description**: Schema version for forward compatibility
- **Validation**: Must equal `1` in current implementation
- **Example**: `schema_version: 1`

#### `experiment_id` (string)
- **Type**: String (kebab-case)
- **Description**: Unique identifier for this experiment
- **Validation**: 
  - Must use kebab-case format (lowercase with hyphens)
  - Must be unique within the `experiments/` directory
  - Should be descriptive of the research objective
- **Example**: `experiment_id: lora-rank-ablation`

#### `status` (string)
- **Type**: String (enum)
- **Description**: Current workflow status of the experiment
- **Validation**: Must be one of:
  - `draft` - Initial creation, not yet complete
  - `grilling` - Undergoing clarification via grill-me skill
  - `planned` - Plan complete, awaiting approval
  - `awaiting_approval` - Submitted for user approval
  - `approved` - User has approved execution
  - `running` - Training jobs executing
  - `evaluating` - Evaluation in progress
  - `finalizing` - Completing documentation and artifacts
  - `completed` - Experiment finished successfully
  - `failed` - Experiment failed with unrecoverable error
  - `cancelled` - User cancelled the experiment
  - `blocked` - Experiment blocked pending user decision
- **Example**: `status: awaiting_approval`

#### `primary_metric` (object)
- **Type**: Object with required sub-fields
- **Description**: The main metric used to compare runs and assess success
- **Required sub-fields**:
  - `name` (string): Metric identifier (e.g., `perplexity`, `accuracy`, `f1_score`)
  - `direction` (enum): Optimization direction, either `maximize` or `minimize`
- **Validation**:
  - `name` must be a valid Python identifier (letters, digits, underscores)
  - `direction` must be either `maximize` or `minimize`
- **Example**:
  ```yaml
  primary_metric:
    name: perplexity
    direction: minimize
  ```

#### `success_criteria` (object)
- **Type**: Object with at least one criterion defined
- **Description**: Quantitative or qualitative criteria that determine experiment success
- **Validation**:
  - Must contain at least one sub-field
  - Common patterns:
    - `minimum_improvement` (float): Minimum improvement over baseline (e.g., `0.02` for 2%)
    - `target_value` (float): Absolute metric target (e.g., `perplexity < 25.0`)
    - Custom criteria specific to research objective
- **Example**:
  ```yaml
  success_criteria:
    minimum_improvement: 0.02  # 2% improvement over baseline
    maximum_perplexity: 25.0
  ```

#### `jobs` (array of strings)
- **Type**: Array of strings (relative file paths)
- **Description**: List of job configuration files to execute
- **Validation**:
  - Each entry must be a relative path starting with `jobs/`
  - Each path must end with `.yaml`
  - Each referenced file must exist when plan is approved
  - Must contain at least one job file
- **Example**:
  ```yaml
  jobs:
    - jobs/train.yaml
    - jobs/evaluate.yaml
  ```

#### `approval` (object)
- **Type**: Object with approval tracking fields
- **Description**: Tracks approval status and history
- **Required sub-fields**:
  - `status` (enum): `pending`, `approved`, or `rejected`
  - `approved_by` (string or null): Username or identifier of approver
  - `approved_at` (string or null): ISO8601 timestamp of approval
  - `approved_commit` (string or null): Git commit SHA at approval time
- **Validation**:
  - `status` must be one of the three enum values
  - When `status` is `approved`, other fields should be populated
  - `approved_at` must be valid ISO8601 format if present
- **Example**:
  ```yaml
  approval:
    status: pending
    approved_by: null
    approved_at: null
    approved_commit: null
  ```

### Optional Fields

These fields MAY be present to provide additional context:

#### `hypothesis` (string)
- **Type**: String
- **Description**: Testable prediction about experiment outcome
- **Usage**: Helps frame experiment in scientific terms
- **Example**: `hypothesis: "Increasing LoRA rank improves model performance but with diminishing returns after rank 16"`

#### `baseline` (object)
- **Type**: Object with baseline comparison information
- **Description**: Reference point for assessing experiment results
- **Common sub-fields**:
  - `name` (string): Identifier for baseline (e.g., `prior-experiment-001`, `published-paper`)
  - `model` (string): Baseline model identifier
  - `dataset` (string): Baseline dataset identifier
  - `metrics` (object): Baseline metric values
  - `source` (string): Where baseline comes from
- **Example**:
  ```yaml
  baseline:
    name: full-finetuning-baseline
    model: meta-llama/Llama-2-7b-hf
    metrics:
      perplexity: 28.3
    source: experiments/prior-full-finetune
  ```

#### `risks` (array of strings)
- **Type**: Array of strings
- **Description**: Potential issues or limitations
- **Usage**: Document known constraints or concerns
- **Example**:
  ```yaml
  risks:
    - "Small dataset may not show statistical significance"
    - "GPU memory limits may constrain batch size"
  ```

#### `related_experiments` (array of strings)
- **Type**: Array of strings (experiment IDs)
- **Description**: References to related or prior experiments
- **Usage**: Track experiment lineage and context
- **Example**:
  ```yaml
  related_experiments:
    - lora-r8-initial-test
    - full-finetune-baseline
  ```

## Validation Rules

### Schema-Level Validation

1. **YAML Parsing**: Frontmatter must parse as valid YAML
2. **Delimiter Presence**: Frontmatter must be enclosed by `---` delimiters
3. **Required Field Presence**: All required fields must exist
4. **Type Checking**: Each field must match its defined type
5. **Enum Validation**: Enum fields must use valid values only

### Semantic Validation

1. **Experiment ID Uniqueness**: No two experiments in `experiments/` may share the same `experiment_id`
2. **Job File Existence**: All paths in `jobs` array must reference existing files at approval time
3. **Metric Direction Consistency**: If comparing to a baseline, `primary_metric.direction` must be consistent with how improvement is calculated
4. **Status Transition Logic**: Status changes must follow valid workflow progression (e.g., cannot jump from `draft` to `completed`)

### Cross-Reference Validation

1. **Baseline References**: If `baseline.source` references another experiment, that experiment should exist
2. **Related Experiments**: Experiments listed in `related_experiments` should exist in `experiments/`
3. **Job Configuration Alignment**: Jobs listed in frontmatter should align with narrative description in plan body

## Usage in Skills

### plan-ml-experiment Skill
- Creates new plans using this schema
- Validates user input against required fields
- Populates agent-determined defaults
- Ensures all required fields present before requesting approval

### train-llm Skill
- Reads `jobs` array to identify training configurations
- Checks `status` field to verify approval before execution
- Updates `status` field as jobs progress

### evaluate-llm Skill
- Reads `primary_metric` to determine comparison criteria
- Uses `success_criteria` to assess results
- References `baseline` for improvement calculations

### finalize-experiment Skill
- Verifies all required fields present
- Validates final `status` is appropriate
- Ensures `approval` tracking is complete

## Example Complete Frontmatter

```yaml
---
schema_version: 1
experiment_id: lora-rank-ablation
status: awaiting_approval

primary_metric:
  name: perplexity
  direction: minimize

success_criteria:
  minimum_improvement: 0.02
  target_perplexity: 25.0

hypothesis: "Increasing LoRA rank improves performance with diminishing returns after rank 16"

baseline:
  name: full-finetuning
  model: meta-llama/Llama-2-7b-hf
  dataset: wikitext-103
  metrics:
    perplexity: 28.3
  source: experiments/full-finetune-baseline

jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml

approval:
  status: pending
  approved_by: null
  approved_at: null
  approved_commit: null

risks:
  - "Limited dataset size may affect generalization"
  - "High memory requirements may limit batch size"

related_experiments:
  - lora-initial-test
  - full-finetune-baseline
---
```

## Error Messages

When validation fails, provide clear error messages:

**Missing Required Field**:
```
Error: Missing required field 'primary_metric' in plan frontmatter
Expected: primary_metric object with 'name' and 'direction' fields
```

**Invalid Enum Value**:
```
Error: Invalid value 'running_training' for field 'status'
Valid values: draft, grilling, planned, awaiting_approval, approved, running, evaluating, finalizing, completed, failed, cancelled, blocked
```

**Invalid Type**:
```
Error: Field 'jobs' must be an array of strings
Found: string
```

**Semantic Validation Failure**:
```
Error: Experiment ID 'lora-test' already exists in experiments/lora-test/
Each experiment must have a unique experiment_id
```

## Version History

- **Schema Version 1** (Current): Initial schema definition with core required fields and optional enhancement fields
