# Experiment Approval Request

## Recommended Plan

Approve `lora-rank-ablation` to test whether rank 16 remains the lowest-cost rank that preserves cross-seed mean validation accuracy for RoBERTa-base on GLUE SST-2. Status is `awaiting_approval`; approval is `pending`.

## Agent-Determined Defaults

- Reuse `src/train_lora.py` and `src/evaluate.py` from the comparable prior jobs.
- Evaluate all nine rank/seed checkpoints and aggregate results by rank; this is an explicit planning assumption required by the cross-seed objective.
- Reuse the prior conservative resource envelopes: 1 GPU, 8 CPUs, 32 GB, and 8 hours per training configuration; 1 GPU, 4 CPUs, 16 GB, and 2 hours for aggregate evaluation. These are requested limits, not verified durations.

## Objective and Hypothesis

Determine whether rank 16 remains the lowest-cost rank preserving mean validation accuracy across seeds 17, 42, and 73. The hypothesis is that rank 16 reaches at least 0.874 mean validation accuracy, stays within 0.002 of the best rank mean, and costs less than rank 32.

## Baseline, Metric, and Success Criterion

- **Baseline**: Prior LoRA rank 16 at seed 17, accuracy `0.874` on GLUE SST-2 validation, from `experiments/prior-lora-rank-ablation/results.yaml`.
- **Primary metric**: Mean validation accuracy across seeds, maximized.
- **Success criterion**: The selected rank's mean validation accuracy is at least `0.874`.

## Matrix, Resources, and Risks

- **Matrix**: ranks `[8, 16, 32]` crossed with seeds `[17, 42, 73]`.
- **Estimated count**: 9 training configurations plus 1 aggregate evaluation job, for 10 planned job invocations and 9 evaluated checkpoints.
- **Requested upper bound**: 74 GPU-hours from configured limits; at most 4 training configurations concurrently under inherited project settings.
- **Principal risks**: The baseline is single-seed while the proposed result is a three-seed mean; three seeds provide limited variance evidence; configured time limits are conservative rather than measured predictions.
- **Phase 6 boundary**: SSH-targeted Slurm execution on `gpu-a100` is planned and unverified; it is unavailable in Phase 4.

## Planned External Destinations

- **W&B, Phase 7**: `fixture-nlp-lab/sentiment-lora`, group `lora-rank-ablation`; planned and unverified, with no live access in Phase 4.
- **Hugging Face, Phase 8**: private `fixture-nlp-lab/lora-rank-ablation`, `final_only`; planned and unverified, with no upload in Phase 4.

## Artifact Paths

- `experiments/lora-rank-ablation/plan.md`
- `experiments/lora-rank-ablation/jobs/train.yaml`
- `experiments/lora-rank-ablation/jobs/evaluate.yaml`

## Approval Required

Please approve this plan or request modifications. No experiment execution, Run creation, credential use, external operation, or Git commit has occurred.
