# Project Log

Project-level conclusions are listed newest first. Detailed measurements remain in the linked experiment records.

## 2025-02-03 — Prior LoRA Rank Ablation Completed

- **Conclusion:** Rank 16 is the efficiency-selected SST-2 configuration at `0.874` validation accuracy; rank 32 is the absolute maximum at `0.875` but costs more time and memory.
- **Best efficiency-selected configuration:** `rank=16`, seed `17`.
- **Experiment:** [`experiments/prior-lora-rank-ablation/`](experiments/prior-lora-rank-ablation/)
- **Evidence:** [`results.yaml`](experiments/prior-lora-rank-ablation/results.yaml) and [`journal.md`](experiments/prior-lora-rank-ablation/journal.md)
- **Next step:** Repeat ranks `[8, 16, 32]` across multiple seeds before changing the project recommendation.
- **Duplication guidance:** Another RoBERTa-base/SST-2 LoRA rank study is a near duplicate only when it adds seed coverage or otherwise changes the comparison design; an identical matrix and seed is an exact duplicate.

## 2025-01-20 — Project Initialized

- Set the project scope to LoRA efficiency studies on GLUE SST-2.
- Recorded stable execution and destination settings in [`project-plan.md`](project-plan.md).
