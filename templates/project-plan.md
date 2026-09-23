---
schema_version: 1
project_id: my-research-project

# Environment configuration
environment:
  manager: miniconda          # Options: miniconda, uv, venv
  manifest: environment.yaml  # Path to environment file

# Execution configuration
execution:
  default_target: ssh         # Options: local, ssh
  ssh_host: research-cluster  # SSH config alias (Phase 6+)
  remote_project_root: /workspace/my-research-project  # Remote path (Phase 6+)
  direct_cpu_max_minutes: 10  # Max time for direct CPU execution
  require_slurm_for_gpu: true
  require_slurm_for_cpu_heavy: true

# Slurm configuration (Phase 6+)
slurm:
  partition: gpu
  account: my-account
  qos: normal
  max_gpus_per_job: 4
  max_concurrent_jobs: 8

# Weights & Biases configuration (Phase 7+)
wandb:
  entity: my-lab
  project: my-research-project
  mode: online                 # Options: online, offline
  keep_local_data: true

# Hugging Face Hub configuration (Phase 8+)
huggingface:
  namespace: my-lab
  private: false               # Default visibility for uploads
  push_policy: final_and_milestone  # Options: never, final_only, final_and_milestone, every_save
---

# Project Plan

## Research Objective

[Describe the overall research goal of this project]

## Research Questions

1. [Primary research question]
2. [Secondary research question]
3. [Additional questions...]

## Scope

### In Scope
- [What this project will investigate]
- [What models/architectures will be used]
- [What datasets will be used]

### Out of Scope
- [What this project will NOT investigate]
- [What is explicitly excluded]

## Baseline Approach

[Describe the baseline model/method that new experiments will be compared against]

## Evaluation Principles

### Primary Metrics
- [Main metric for success, e.g., "Accuracy on test set"]
- [Why this metric was chosen]

### Secondary Metrics
- [Additional metrics to track]
- [When they matter]

## Artifact Policy

### Checkpoint Management
- [When to save checkpoints]
- [Which checkpoints to upload to Hub]

### Data Privacy
- [Any data restrictions]
- [What can be shared publicly]

### Model Release
- [Conditions for releasing models]
- [Default visibility (private/public)]

## Approval Policy

### Experiments Requiring Review
- [Types of experiments that need extra scrutiny]
- [Budget thresholds for approval]

### Auto-Approved Experiments
- [Small-scale experiments that can proceed automatically]

## Notes

[Any additional project-specific guidelines or context]

---

## ⚠️ Security Warning

**DO NOT commit secrets, tokens, or credentials to this file or any other file in this repository.**

- Store W&B API keys in `~/.netrc` or environment variables
- Store Hugging Face tokens in `~/.huggingface/token` or environment variables
- Store SSH keys and credentials outside the repository
- Use `.env` files (excluded by .gitignore) for local development secrets
- Never hardcode passwords, API keys, or tokens in configuration files

If you accidentally commit a secret, consider it compromised and rotate it immediately.
