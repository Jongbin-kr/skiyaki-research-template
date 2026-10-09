---
name: setup-project
description: Configure a newly created research project for its first use. Use when project-plan.md still contains template placeholders, or when setting up the project's environment and stable infrastructure settings (SSH, Slurm, W&B, Hugging Face) before the first experiment.
---

# Setup Project Skill

**Stage:** Setup (one-time, first run)

Help a first-time user configure a new project created from this template: set up
the environment and fill in `project-plan.md` with the project's stable settings.
Ask one thing at a time, write the files, and hand off to the Plan stage. This is
a one-time onboarding step — skip it if the project is already configured.

## When to Use

- Right after creating a project from the template (or cloning a research repo
  into it), before the first experiment.
- When `project-plan.md` still holds template placeholders
  (`my-research-project`, `research-cluster`, `my-lab`).

## Procedure

Ask about one item at a time; don't dump a long form. Confirm what you learn,
then write it into the right file.

### 1. Environment

**Never assume the environment or the manager. Discover what exists, ask the
user, then record the decision.** Picking the wrong interpreter is a common cause
of failed runs (e.g. a bare `torchrun` silently resolving to base conda instead
of the intended env).

1. **Discover existing environments.** Inspect what the machine/cluster already
   has before proposing anything:
   - conda envs: `conda env list`
   - the project's own manifest, if any: `environment.yaml`, `pyproject.toml` +
     `uv.lock`, or `requirements.txt`
   - active/available managers: `which conda uv`, `$VIRTUAL_ENV`, `$CONDA_DEFAULT_ENV`
   Report what you found (e.g. "there's a conda env `MoE` with PyTorch 2.11 /
   CUDA 13.0, and the project declares no manifest").

2. **Ask the user which environment to use.** Do not silently pick one. Present
   the options you found and let the user choose:
   - reuse an existing env (e.g. their `MoE` conda env),
   - create a new dedicated env (recommended when version compatibility matters —
     e.g. the project needs a specific Transformers/PyTorch/CUDA combo that would
     disturb a shared env),
   - or, if nothing suitable exists, ask whether to create a **conda** or **uv**
     environment and build it.
   When creating a new env, confirm the Python version and the key
   framework/CUDA versions the project code requires (check the project's
   README/setup/requirements), and prefer an isolated env over mutating a shared one.

3. **Record the decision in `project-plan.md`** under `environment`: the chosen
   `manager` (conda / uv / venv), the env name or path, and the manifest. This is
   a stable setting — all later runs use this environment.

4. **Pin how jobs invoke it, so runs don't drift to the wrong interpreter.**
   Record the exact activation/invocation to use in every run — e.g.
   `conda run -n <env> python ...` or the env's absolute Python
   (`/path/to/envs/<env>/bin/python`), and for distributed launches the env's own
   `torchrun`/`accelerate`. Avoid bare `torchrun`/`python` that can resolve to
   base conda or system Python. Don't assume a training framework beyond what the
   project declares.

### 2. Stable project settings → `project-plan.md`

Collect only **stable infrastructure settings** that don't change per experiment.
For each, tell the user where to find it if they're unsure:

- **Execution / SSH:** `ssh_host` (an alias in the user's `~/.ssh/config`),
  remote project root, remote data root. Whether GPU / CPU-heavy work must use
  Slurm (usually yes on a cluster).
- **Slurm:** partition, account, QoS, and per-job caps (max GPUs/CPUs/memory/time).
  - partition → `sinfo`
  - account / QoS → `sacctmgr show user $USER` (or ask the cluster admin)
- **CUDA / toolkit:** driver CUDA ceiling → `nvidia-smi` (top-right "CUDA
  Version"); note whether the toolkit comes from conda or a module system.
- **Weights & Biases:** `entity` (your W&B username/team from the wandb.ai
  profile) and `project` name; online/offline mode.
- **Hugging Face:** `namespace` (your HF user/org) and the default push policy;
  keep repositories private by default.

Write these into `project-plan.md`, replacing the placeholders. Leave the
research-objective / baseline / evaluation sections for the Plan stage — those
are per-experiment, not stable settings.

### 3. Safety

- Never put secrets in `project-plan.md` or any file: W&B/HF tokens live in the
  environment (`~/.netrc`, `~/.huggingface/token`) or `.env` (gitignored), not in
  the repo. Record only non-secret identifiers (entity, namespace, host alias).

### 4. Hand off to Plan

When the environment is set and `project-plan.md` is filled, tell the user setup
is done and move to the **Plan** stage: use `explore-project-history` and
`grill-me` to scope the first experiment. Setup does not plan or run anything.

## Output

- A working environment (or clear instructions to create it) and the recorded
  manager/manifest in `project-plan.md`.
- `project-plan.md` with the project's stable settings filled in (no secrets).
- A hand-off to the Plan stage.
