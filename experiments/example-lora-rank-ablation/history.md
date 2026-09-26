# Experiment History (Example)

This file records the chronological sequence of events for the LoRA rank ablation experiment. Entries are factual and focus on actions taken and results observed.

---

## 2025-01-15 09:30 — Experiment Plan Approved

- Reviewed experiment plan with 4 LoRA ranks [4, 8, 16, 32]
- Approved resource allocation: 40 GPU-hours estimated
- Committed plan and job configurations
- Commit: `abc123f`

---

## 2025-01-15 10:00 — Training Started (Rank 4)

- Submitted training job for rank 4 via Slurm
- Slurm job ID: 123453
- W&B run: `hopeful-dawn-39`
- Resources: 1 GPU, 32GB RAM, 8 hour limit

---

## 2025-01-15 13:50 — Training Completed (Rank 4)

- Run ID: `train-r4__20250115T100000`
- Status: succeeded
- Training time: 3.8 hours
- Final accuracy: 0.866
- Peak memory: 7.1 GB
- Checkpoint uploaded to W&B

---

## 2025-01-15 11:00 — Training Started (Rank 8)

- Submitted training job for rank 8 via Slurm
- Slurm job ID: 123454
- W&B run: `stellar-breeze-40`

---

## 2025-01-15 15:10 — Training Completed (Rank 8)

- Run ID: `train-r8__20250115T110000`
- Status: succeeded
- Training time: 4.1 hours
- Final accuracy: 0.871
- Peak memory: 7.6 GB

---

## 2025-01-15 14:25 — Training Started (Rank 16)

- Submitted training job for rank 16 via Slurm
- Slurm job ID: 123456
- W&B run: `vibrant-wave-42`

---

## 2025-01-15 18:47 — Training Completed (Rank 16)

- Run ID: `train-r16__20250115T142530`
- Status: succeeded
- Training time: 4.36 hours
- Final accuracy: 0.874 (best so far)
- Peak memory: 8.2 GB
- Checkpoint uploaded to Hugging Face: `my-lab/roberta-base-sst2-lora-r16`

---

## 2025-01-15 16:00 — Training Started (Rank 32)

- Submitted training job for rank 32 via Slurm
- Slurm job ID: 123457
- W&B run: `quiet-field-43`

---

## 2025-01-15 21:12 — Training Completed (Rank 32)

- Run ID: `train-r32__20250115T160000`
- Status: succeeded
- Training time: 5.2 hours
- Final accuracy: 0.875 (marginal improvement over rank 16)
- Peak memory: 9.8 GB

---

## 2025-01-15 19:00 — Evaluation Started

- Evaluating best checkpoint (rank 16) on test set
- Run ID: `eval-r16__20250115T190000`

---

## 2025-01-15 19:45 — Evaluation Completed

- Test accuracy: 0.874
- F1 score: 0.872
- Confirms validation metrics; no overfitting detected

---

## 2025-01-15 20:00 — W&B Analysis

- Compared all 4 training curves
- Rank 16 shows smooth convergence
- Rank 32 shows similar convergence pattern with minimal gain
- All ranks substantially beat baseline (0.853)

---

## 2025-01-15 20:15 — Experiment Finalized

- Success criteria met: 2.1% improvement over baseline
- Best model: rank 16 (0.874 accuracy)
- Recommendation: Use rank 16 for production
- Updated results.yaml, journal.md, project-log.md
- Experiment marked as completed

---
