---
schema_version: 1
experiment_id: prior-lora-rank-ablation
status: completed
primary_metric:
  name: accuracy
  direction: maximize
success_criteria:
  baseline_value: 0.853
  minimum_absolute_improvement: 0.015
  evaluation_split: validation
jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml
approval:
  status: approved
  approved_by: fixture-researcher
  approved_at: "2025-02-01T09:00:00Z"
  approved_commit: fixture-plan-v1
---

# Prior LoRA Rank Ablation

## Objective

Compare LoRA ranks `[4, 8, 16, 32]` for RoBERTa-base on GLUE SST-2 and select an accuracy/resource tradeoff for subsequent studies.

## Hypothesis

Validation accuracy will saturate by rank 16, making rank 16 preferable to rank 32 when training time and peak GPU memory are considered.

## Baseline

- Model: unfine-tuned `roberta-base`
- Dataset: GLUE SST-2 validation split
- Primary metric: accuracy, maximized
- Baseline value: `0.853`
- Source: fixed project reference recorded when this fixture experiment was planned

## Design

### Variables

LoRA rank was varied over `[4, 8, 16, 32]`.

### Controls

The model, SST-2 train/validation data, learning rate `2e-4`, three epochs, effective batch size `32`, LoRA dropout `0.1`, query/value targets, and seed `17` were held constant. LoRA alpha was set to twice each rank.

### Selection Rule

Select the lowest-cost rank within `0.002` absolute validation accuracy of the maximum observed rank. This rule distinguishes the efficiency-selected configuration from the absolute metric maximum.

## Expected Outcomes

The hypothesis is supported if rank 16 is within `0.002` of the maximum accuracy and rank 32 requires more training time or memory. It is refuted if rank 32 improves accuracy by more than `0.002` without a material resource increase.

## Limitations

A single seed cannot establish variance or ranking stability. Any follow-up using the same model, dataset, technique, and overlapping ranks is near-duplicate work only if it adds seed coverage or another material design difference.
