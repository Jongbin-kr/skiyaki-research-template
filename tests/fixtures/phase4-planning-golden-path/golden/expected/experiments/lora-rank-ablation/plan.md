---
schema_version: 1
experiment_id: lora-rank-ablation
status: awaiting_approval
primary_metric:
  name: accuracy
  direction: maximize
  aggregation: mean_across_seeds
success_criteria:
  metric: accuracy
  comparison: mean_validation_accuracy
  operator: gte
  threshold: 0.874
baseline:
  name: prior-rank16-efficiency-selection
  configuration: LoRA rank 16 at seed 17
  metric:
    name: accuracy
    value: 0.874
    direction: maximize
  evaluation:
    dataset: glue/sst2
    split: validation
  source: experiments/prior-lora-rank-ablation/results.yaml
jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml
approval:
  status: pending
  approved_by: null
  approved_at: null
  approved_commit: null
---

# Multi-Seed LoRA Rank Ablation

## Agent-Determined Defaults

| Decision | Value | Rationale | Evidence or assumption |
|---|---|---|---|
| Training entrypoint | `src/train_lora.py` | Reuse the entrypoint associated with the comparable prior configuration. | `experiments/prior-lora-rank-ablation/jobs/train.yaml` |
| Evaluation entrypoint | `src/evaluate.py` | Reuse the prior evaluation interface for the same dataset and metrics. | `experiments/prior-lora-rank-ablation/jobs/evaluate.yaml` |
| Evaluation checkpoint resolution | Evaluate every rank/seed checkpoint and aggregate by rank | The objective compares cross-seed means, which requires every planned matrix checkpoint. | Explicit assumption derived from the resolved objective |
| Per-configuration resource envelope | 1 GPU, 8 CPUs, 32 GB memory, 8 hours for training; 1 GPU, 4 CPUs, 16 GB memory, 2 hours for evaluation | Reuse conservative envelopes from the comparable prior jobs; these are limits, not measured duration claims. | `experiments/prior-lora-rank-ablation/jobs/train.yaml`; `experiments/prior-lora-rank-ablation/jobs/evaluate.yaml` |

## Decision Provenance

| Decision | Value | Origin | Source |
|---|---|---|---|
| research_objective | Test whether rank 16 remains the lowest-cost rank preserving mean validation accuracy across seeds. | user | transcript turn 3; `project-plan.md` |
| baseline | Prior rank 16 at seed 17 with 0.874 validation accuracy. | user | transcript turn 5; `experiments/prior-lora-rank-ablation/results.yaml` |
| primary_metric | Mean validation accuracy across seeds, maximized. | user | transcript turn 7 |
| success_criteria | Selected rank mean validation accuracy is at least 0.874. | user | transcript turn 9 |
| ablation_scope | Ranks `[8, 16, 32]` crossed with seeds `[17, 42, 73]`. | user | transcript turn 11; `project-log.md` |
| controlled_parameters | Preserve the prior model, data, learning rate, epochs, effective batch size, LoRA alpha rule, dropout, and target modules. | user | transcript turn 13; `experiments/prior-lora-rank-ablation/jobs/train.yaml` |

## Inherited Project Settings

The Miniconda environment; SSH execution target; remote project root; Slurm requirement, partition `gpu-a100`, account `nlp-research`, QoS `normal`, and concurrency limits; W&B destination `fixture-nlp-lab/sentiment-lora`; and private Hugging Face namespace `fixture-nlp-lab` with `final_only` push policy are inherited from `project-plan.md`. They are not Agent-Determined Defaults and were not re-asked.

## Purpose

Determine whether LoRA rank 16 remains the lowest-cost rank that preserves mean validation accuracy across multiple seeds for RoBERTa-base on GLUE SST-2.

## Hypothesis

Across seeds 17, 42, and 73, rank 16 will achieve mean validation accuracy of at least 0.874 and remain within 0.002 absolute accuracy of the highest-mean rank while using no more resources than rank 32.

## Evidence-Backed Baseline

- **Name/configuration**: Prior efficiency-selected RoBERTa-base LoRA rank 16 at seed 17.
- **Metric**: Accuracy `0.874`, maximized.
- **Evaluation data**: GLUE SST-2 validation split.
- **Source**: `experiments/prior-lora-rank-ablation/results.yaml`, corroborated by `experiments/prior-lora-rank-ablation/journal.md`.
- **Context limitation**: The baseline is a single-seed result; the proposed primary result is a three-seed mean.

## Design

### Variables

Cross LoRA ranks `[8, 16, 32]` with seeds `[17, 42, 73]`, producing nine training configurations. Evaluate every resulting checkpoint and aggregate validation accuracy and F1 by rank.

### Controls

Hold `roberta-base`, GLUE SST-2 train/validation data, learning rate `2e-4`, three epochs, batch size `8`, gradient accumulation `4` for effective batch size `32`, LoRA alpha at twice rank, LoRA dropout `0.1`, and query/value target modules constant. Use the same evaluation entrypoint, validation split, batch size `16`, and metric definitions for every checkpoint.

### Rationale

The prior study compared the same model, dataset, technique, and overlapping ranks but used only seed 17. The narrowed matrix follows the documented next step in `project-log.md`; adding two seeds tests whether the 0.001 rank-16 versus rank-32 difference is stable. The study is therefore a near-duplicate extension rather than an exact repeat.

### Selection Rule

First require a candidate rank's mean validation accuracy to be at least `0.874`. Among passing ranks within `0.002` absolute accuracy of the maximum rank mean, select the lowest-cost rank using aggregate training time and peak GPU memory as secondary evidence.

## Planned External Destinations

- **Phase 6**: SSH-targeted GPU work is planned for Slurm on partition `gpu-a100`; execution and availability are unverified and unavailable in Phase 4.
- **Phase 7**: W&B group `lora-rank-ablation` under `fixture-nlp-lab/sentiment-lora` is a planned, unverified destination; no live access occurs in Phase 4.
- **Phase 8**: Private Hugging Face repository `fixture-nlp-lab/lora-rank-ablation` with `final_only` policy is a planned, unverified destination; no upload occurs in Phase 4.

## Risks and Limitations

- The baseline is one historical seed, while the success result is a three-seed mean, so direct threshold interpretation should retain that context.
- Three seeds improve confidence but do not provide a high-powered variance estimate.
- Requested job time and memory are conservative limits, not verified cluster-duration measurements.
- The experiment covers only RoBERTa-base on GLUE SST-2 and does not establish rank behavior elsewhere.

## Expected Outcomes

### If Hypothesis Supported

If rank 16 reaches mean validation accuracy of at least 0.874, remains within 0.002 of the best rank mean, and costs less than rank 32, retain rank 16 as the project recommendation with stronger cross-seed support.

### If Hypothesis Refuted

If rank 16 misses 0.874 or falls more than 0.002 below the best rank mean, revise the efficiency recommendation using the measured mean, per-seed spread, training time, and memory results rather than preserving the single-seed conclusion.
