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

- If the project already has an environment manifest (a cloned repo's
  `environment.yaml`, `pyproject.toml` + `uv.lock`, or `requirements.txt`),
  **use it** — don't override the project's own setup. Detect the manager it
  implies (conda / uv / venv).
- Otherwise, default to a **conda** environment: confirm a name, Python version,
  and the core frameworks/dependencies, and write `environment.yaml`.
- Record the chosen manager and manifest in `project-plan.md` under
  `environment`. The project then uses this environment for all runs; prefer it
  over system Python.
- Point the user at creating it (e.g. `conda env create -f environment.yaml`).
  Don't assume a specific training framework beyond what the project declares.

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
