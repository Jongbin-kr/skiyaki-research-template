---
schema_version: 1
project_id: skiyaki-research

environment:
  manager: miniconda
  manifest: environment.yaml
  remote_conda_root: /data6/jongbinwon/miniconda3

execution:
  default_target: ssh
  ssh_host: SKIML
  remote_project_root: /home/jongbinwon/data/skiyaki-research-template
  remote_data_root: /home/jongbinwon/data
  direct_cpu_max_minutes: 10
  require_slurm_for_gpu: true
  require_slurm_for_cpu_heavy: true

slurm:
  partition: gpu
  account: cluster
  qos: normal
  default_time: "00:30:00"
  max_time: "5-00:00:00"
  # QoS 'normal' per-user caps: gpu<=4, cpu<=8, mem<=80G, MaxWall 2 days
  max_gpus_per_job: 4
  max_cpus_per_job: 8
  max_mem_gb_per_job: 80
  max_concurrent_jobs: 8

cuda:
  driver_version: "550.127.05"
  driver_cuda_version: "12.4"
  toolkit_source: conda  # no module system; install cudatoolkit via conda env
  notes: >
    No environment-modules/lmod on this cluster and no system nvcc.
    Pin the CUDA toolkit inside the conda environment (e.g. pytorch-cuda=12.1
    or 12.4) so it stays within the 12.4 driver ceiling.

wandb:
  entity: TODO-set-before-phase-7
  project: skiyaki-research
  mode: online
  keep_local_data: true

huggingface:
  namespace: TODO-set-before-phase-8
  private: true
  push_policy: final_and_milestone
---

# Project Plan

## Research Objective

TODO: state the project's research objective. First planned use is cloning and
running https://github.com/allenai/EMO on the SKIML GPU cluster.

## Compute Environment (SKIML cluster)

- **Login/submit host**: `SKIML` (`jongbinwon@147.47.200.198:22555`), hostname `master`, Ubuntu 20.04.
- **Scheduler**: Slurm. Submit from the login node; GPU and CPU-heavy jobs MUST use `sbatch`/Slurm (never run directly on the login node).
- **Default partition**: `gpu` (default, DefaultTime 30 min, MaxTime 5 days).
- **Nodes**:
  | Node | GPUs | GPU count | CPUs | Memory |
  |------|------|-----------|------|--------|
  | master | RTX 4090 | 3 | 64 | 515 GB |
  | n01, n02 | RTX A6000 | 8 each | 64 | 515 GB |
  | n03, n04, n05 | RTX PRO 6000 | 8 each | 192 | 1031 GB |
- **GRES request syntax**: `--gres=gpu:<N>` (generic) or target a type with
  `--gres=gpu:A6000:<N>` / `gpu:PRO6000:<N>` / `gpu:4090:<N>`.
- **Account/QoS (mine)**: account `cluster`, partition `gpu`, default QoS `normal`.
- **QoS `normal` per-user limits**: `gpu<=4`, `cpu<=8`, `mem<=80G`, MaxWall 2 days.
  Larger-footprint QoS exist (e.g. `8gpu`, `6gpu200mem`, `4gpu40cpu300mem`, `5days`,
  `mfds_2_weeks`) but are not assigned to me by default; request explicitly if needed.

## CUDA / Toolkit

- NVIDIA driver `550.127.05`, driver CUDA ceiling **12.4**.
- No environment-modules/lmod and no system `nvcc`.
- Install the CUDA toolkit **inside the conda environment** (e.g. `pytorch-cuda=12.1`
  or `12.4`); keep the runtime toolkit at or below the 12.4 driver ceiling.

## Storage

- Remote project root: `/home/jongbinwon/data/skiyaki-research-template`
  (`/home/jongbinwon/data` is a symlink to `/data6/jongbinwon`; `/data6` has ~3.8 TB free of 7 TB).
- Keep datasets and checkpoints under `/home/jongbinwon/data`, not in `$HOME`.

## Environment Manager

- Miniconda at `/data6/jongbinwon/miniconda3`, auto-activated from `~/.bashrc`.
- Define per-project environments via `environment.yaml`.

## Evaluation Principles

TODO: define primary metric(s), baselines, and success criteria per experiment.

## Artifact Policy

- Do not commit checkpoints, W&B caches, raw Slurm logs (`*.out`/`*.err`), or secrets.
- W&B: online mode, local data kept under the run directory.
- Hugging Face: private by default; push final and milestone checkpoints only.

## Approval Policy

- Explicit user approval is required before job execution, after material changes,
  and before any Git commit.
- GPU and CPU-heavy jobs are Slurm-only; the login node is never used for training.

## Pending Setup

- `wandb.entity` — set before Phase 7.
- `huggingface.namespace` — set before Phase 8.
- Research objective, baselines, and success criteria — fill in when the EMO work is scoped.
