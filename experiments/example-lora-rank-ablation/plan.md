# LoRA Rank Ablation Study (Example)

> **Note**: This is an example experiment demonstrating the v2 template layout —
> a prose `plan.md` plus a reproducible `run-config.yaml`, with `history.md` and
> `journal.md` for the record. Training was not actually executed; the numbers
> here are illustrative. Safe to delete when you start your own research.

## Objective

Determine the optimal LoRA rank for fine-tuning RoBERTa-base on SST-2 sentiment
classification, balancing accuracy and memory efficiency.

## Hypothesis

LoRA ranks 16 and above will saturate performance gains, with diminishing returns
for higher ranks. Rank 16 will provide the best accuracy/efficiency tradeoff.

## Baseline

- **Configuration:** RoBERTa-base, pre-trained, no fine-tuning
- **Metric:** accuracy = 0.853, F1 = 0.851
- **Evaluation data:** GLUE SST-2, validation split
- **Source:** published RoBERTa paper baseline

## Design

- **Variables:** LoRA rank ∈ [4, 8, 16, 32]
- **Controls:** RoBERTa-base, SST-2, learning rate 2e-4, effective batch size 32
  (batch 8 × 4 grad-accum), 3 epochs, seed 42, LoRA alpha = 2×rank, dropout 0.1,
  target modules = query & value projections
- **Rationale:** powers of two over [4, 32] give clear comparison points across
  the practical deployment range, from constrained (rank 4) to high-capacity
  (rank 32), with rank as the only manipulated variable.

## Metric & Success Criterion

- **Primary metric:** accuracy (maximize), on the SST-2 validation split
- **Success criterion:** the selected rank improves accuracy by at least 0.02
  (absolute) over the baseline.

## Decisions

| Decision | Value | Source |
|---|---|---|
| Learning rate | 2e-4 | agent suggestion (standard for LoRA fine-tuning) |
| Effective batch size | 32 (8 × 4 grad-accum) | agent suggestion (memory/convergence balance) |
| Epochs | 3 | agent suggestion (typical for GLUE; avoids overfitting) |
| LoRA alpha | 2 × rank | agent suggestion (standard scaling) |
| Target modules | query, value | agent suggestion (most commonly fine-tuned) |

## Risks & Limitations

- Single dataset (SST-2) may not generalize to other tasks.
- Single architecture (RoBERTa-base) may have a different optimal rank than larger/smaller models.
- Fixed learning rate may not be optimal for every rank.
- No inference-latency measurement (accuracy focus only).
- Single seed — no statistical significance testing.

## Resource Estimate

4 ranks × 1 training run each = 4 GPU runs, ~4-5 h each on one GPU (~18 GPU-hours
total), plus a short evaluation run. Within the project's single-GPU quota.
