# Example: LoRA Rank Ablation Study

> **⚠️ This is an example experiment for demonstration purposes.**  
> The training was not actually executed. Use this as a reference for structuring your own experiments.

## Purpose

This example demonstrates:
- Complete experiment structure following the template
- Realistic research question and hypothesis-driven design
- Proper documentation at each stage
- Best practices for job configuration and run tracking

## Research Question

**"What is the optimal LoRA rank for fine-tuning RoBERTa-base on SST-2 sentiment classification?"**

## Key Features

### 1. Clear Hypothesis
"LoRA rank 16 will provide the best accuracy/efficiency tradeoff, with ranks 16+ showing diminishing returns."

### 2. Ablation Design
Tests LoRA ranks [4, 8, 16, 32] with controlled variables (learning rate, batch size, epochs).

### 3. Job Configuration
- `jobs/train.yaml`: Training configuration with matrix for ablation
- `jobs/evaluate.yaml`: Evaluation configuration

### 4. Run Tracking
- `runs/train-r16__20250115T142530/`: Example run showing structure
  - `run.yaml`: Metadata and execution status
  - `resolved-job.yaml`: Exact configuration used
  - `logs/train.log`: Training output

### 5. Results Documentation
- `results.yaml`: Metrics, baseline comparison, recommendations
- `history.md`: Chronological timeline of execution events
- `journal.md`: Analysis, insights, and recommended next steps

## What to Learn From This Example

### From `plan.md`
- ✅ Clear research objective and hypothesis
- ✅ Defined baseline with specific metrics
- ✅ Explicit success criteria (≥2% improvement)
- ✅ Documented agent-determined defaults with rationale
- ✅ Acknowledged risks and limitations
- ✅ Expected outcomes for different scenarios

### From `jobs/train.yaml`
- ✅ Matrix configuration for ablation (lora_rank: [4, 8, 16, 32])
- ✅ All hyperparameters explicitly specified
- ✅ Resource requirements defined
- ✅ W&B and Hugging Face settings configured

### From `runs/.../run.yaml`
- ✅ Complete execution metadata
- ✅ Status tracking (created → running → succeeded)
- ✅ Slurm job IDs and W&B run URLs
- ✅ Reference to resolved configuration
- ✅ Artifacts produced listed

### From `results.yaml`
- ✅ Best run identified with metrics
- ✅ Baseline comparison with improvement percentage
- ✅ Summary of all runs for comparison
- ✅ Success assessment with rationale
- ✅ Key findings and limitations
- ✅ Actionable recommendations

### From `history.md`
- ✅ Factual, chronological event log
- ✅ Each entry: timestamp, action, outcome
- ✅ No interpretation, just facts
- ✅ Links to runs and external resources

### From `journal.md`
- ✅ Hypothesis assessment (supported/refuted)
- ✅ Detailed analysis of findings
- ✅ Unexpected results highlighted
- ✅ Theoretical implications discussed
- ✅ Limitations acknowledged
- ✅ Recommended next experiments
- ✅ Production recommendations with tradeoffs

## How to Use This Example

### As a Reference
Keep this directory as a reference when:
- Planning your first experiment
- Structuring documentation
- Writing job configurations
- Analyzing results

### As a Template
Copy structure for your experiments:
```bash
cp -r experiments/example-lora-rank-ablation experiments/your-experiment-name
# Then edit files with your research question and configuration
```

### For Training
Use this to train team members on:
- Experiment structure
- Documentation best practices
- Job configuration format
- Result analysis approach

## Cleanup

You can safely delete this directory when:
- You understand the experiment structure
- You've created your own experiments
- You no longer need the reference

Or keep it indefinitely as documentation.

## Differences From Real Experiments

1. **No actual execution**: Training logs are synthetic examples
2. **Simplified**: Real experiments may have more runs, figures, and complexity
3. **Complete**: Real in-progress experiments will have missing files until finalized

## Related Files

- See [../README.md](../README.md) for experiments directory overview
- See [../../templates/](../../templates/) for blank templates
- See [../../AGENTS.md](../../AGENTS.md) for research workflow rules
- See [../../.agents/skills/](../../.agents/skills/) for detailed workflows

---

**Questions?** Ask Codex to explain any part of this example experiment.
