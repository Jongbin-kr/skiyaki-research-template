# Experiment History

This file records factual execution events in chronological order.

## Format Guidelines

- **Reverse chronological order**: Newest events appear first
- **Factual, not interpretive**: Record what happened, not why or what it means (interpretation goes in journal.md)
- **Include all event types**: Planning, approval, execution, evaluation, and finalization
- **Required details**: Timestamps, run IDs, status codes, and relevant links
- **Concise entries**: One paragraph per event with bulleted facts

## Event Types

### Planning Events
- Experiment plan created
- Job configurations generated
- Resource estimates calculated

### Approval Events
- User approved or rejected experiment
- Material changes requiring re-approval

### Execution Events
- Training runs started
- Training runs completed (succeeded/failed)
- Resource usage and duration

### Evaluation Events
- Evaluation started
- Evaluation completed
- Metrics calculated and compared to baseline

### Finalization Events
- Documentation updates (results.yaml, journal.md)
- Project log updated
- Git commit proposed or created

---

## [YYYY-MM-DD HH:MM] — Event Description

[Factual description of what happened]

- Run ID: <run-id>
- Status: <status>
- W&B: <url>
- Notes: <any relevant facts>

---

## Example Entries (Remove These After First Real Entry)

## 2025-01-15 14:30 — Experiment Finalized

- Completed journal entry with findings
- Updated project-log.md with conclusion
- Proposed Git commit: "Complete lora-rank-ablation: rank 16 optimal"

## 2025-01-15 12:00 — Evaluation Completed

- Run ID: eval-r16__20250115T120000
- Status: succeeded
- Primary metric: accuracy = 0.874
- Baseline: accuracy = 0.853
- Improvement: +2.1%
- Success criteria met: improvement > 2%

## 2025-01-15 08:00 — Training Run Succeeded

- Run ID: train-r16__20250115T080000
- Status: succeeded
- Duration: 4.5 hours
- W&B: https://wandb.ai/my-lab/my-project/runs/abc123
- Checkpoint saved: outputs/lora-rank-ablation/train-r16__20250115T080000/checkpoint-final

## 2025-01-15 03:30 — Training Run Started

- Run ID: train-r16__20250115T080000
- Job: jobs/train.yaml with lora_rank=16
- Resources: 1 GPU, 8 CPUs, 32GB RAM
- Slurm Job ID: 123456 (Phase 6+)

## 2025-01-14 16:00 — Experiment Approved

- User approved experiment plan
- Approval recorded in plan.md
- Ready to start training

## 2025-01-14 15:00 — Plan Created

- Created plan.md and job configurations
- Defined LoRA rank ablation: [4, 8, 16, 32]
- Estimated resources: 4 GPU jobs × 8 hours each
- Awaiting user approval

---
