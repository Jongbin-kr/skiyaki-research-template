---
schema_version: 1
project_id: sentiment-lora-research

environment:
  manager: miniconda
  manifest: environment.yaml

execution:
  default_target: ssh
  ssh_host: fixture-research-cluster
  remote_project_root: /srv/research/sentiment-lora
  direct_cpu_max_minutes: 10
  require_slurm_for_gpu: true
  require_slurm_for_cpu_heavy: true

slurm:
  partition: gpu-a100
  account: nlp-research
  qos: normal
  max_gpus_per_job: 2
  max_concurrent_jobs: 4

wandb:
  entity: fixture-nlp-lab
  project: sentiment-lora
  mode: online
  keep_local_data: true

huggingface:
  namespace: fixture-nlp-lab
  private: true
  push_policy: final_only
---

# Project Plan

## Research Objective

Identify parameter-efficient LoRA configurations for RoBERTa-base sentiment classification that preserve validation accuracy while reducing training cost.

## Research Questions

1. Which LoRA rank gives the best validation-accuracy and resource tradeoff on GLUE SST-2?
2. Does the preferred rank remain competitive across multiple random seeds?

## Scope

### In Scope

- RoBERTa-base with LoRA adapters on attention query and value projections.
- GLUE SST-2 training and validation splits.
- Rank, validation accuracy, F1, training time, and peak GPU memory comparisons.

### Out of Scope

- Full-parameter fine-tuning, non-SST-2 datasets, inference serving, and external-system verification during planning.

## Baseline Approach

For follow-up rank studies, use LoRA rank 16 at validation accuracy `0.874` as the comparison baseline. This value is the best efficiency-selected configuration from `experiments/prior-lora-rank-ablation/results.yaml`; rank 32 reached `0.875` but did not justify its additional resource cost. The underlying unfine-tuned RoBERTa-base reference is `0.853` validation accuracy.

## Evaluation Principles

- Primary metric: validation accuracy, maximized.
- Secondary metrics: validation F1, training time, and peak GPU memory.
- New rank recommendations must report per-seed values and aggregate mean when multiple seeds are used.

## Artifact Policy

- Keep intermediate checkpoints local and untracked.
- The Hugging Face destination is planning metadata only; publish only a final approved checkpoint in Phase 8 or later.
- W&B values are planning metadata only; live verification is unavailable until Phase 7.

## Approval Policy

Every GPU experiment requires explicit plan approval before execution. SSH and Slurm execution remain unavailable until Phase 6.
