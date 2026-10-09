---
name: train-llm
description: Execute a planned training run using the project's own training code, and record what happened in history.md. Use in the Run stage after a plan and run-config.yaml are approved. Runs short CPU work locally and GPU/CPU-heavy jobs via Slurm; asks before submitting.
---

# Train LLM Skill

**Stage:** Run

Execute a planned training run using the project's own training code, and record
what happened. There is no built-in runner — you build and run the command from
the project's conventions, then write the outcome to `history.md`.

## Prerequisites

- An approved `plan.md` and a `run-config.yaml` exist for the experiment.
- The user has said to proceed (you are the human-in-the-loop; ask before
  submitting jobs).

## Procedure

1. **Read the project's run method.** Inspect the project's README, `src/`, and
   `environment.yaml` to learn how training is launched (e.g.
   `python src/train.py`, `accelerate launch`, a Hydra config, a Slurm script).
   Do not assume a framework.

2. **Build the command from `run-config.yaml`.** Map its entrypoint and
   parameters to the project's expected invocation. Expand any ablation matrix
   into one command per combination.
   - **Use the environment recorded in `project-plan.md`, invoked explicitly.**
     Run through that env's interpreter — `conda run -n <env> python ...` or the
     env's absolute Python — and for distributed launches use that env's own
     `torchrun` / `accelerate`. **Never** use a bare `torchrun` / `python`: on a
     cluster it can silently resolve to base conda or system Python with the
     wrong PyTorch/CUDA and fail at the first GPU op. If no environment is
     recorded yet, stop and run Setup first.

3. **Choose where it runs.**
   - Short CPU checks may run locally in the recorded project environment.
   - GPU and CPU-heavy jobs go through **Slurm** (`sbatch`) on the configured
     cluster — never run heavy work on a login node. Generate an sbatch script
     that **activates the recorded environment and invokes its interpreter
     explicitly** (not a bare `torchrun`/`python`); write logs to the
     experiment's `logs/` directory.

4. **Configure tracking.** If W&B is enabled, set the environment so runs group
   by experiment and keep local data. If Hugging Face push is configured, honor
   the project's push policy. Never print or commit tokens.

5. **Run and capture.** Launch the job (ask the user first). Capture stdout/stderr
   to `logs/`. For Slurm, record the job id.

6. **Record in `history.md`.** Add an entry per run attempt: timestamp, Slurm job
   id (if any), resources, status (succeeded / failed / timed out / cancelled),
   and any W&B URL. Record failures with the same care as successes — note the
   error cause briefly so it stays reproducible without committing the raw log.

## Notes

- Raw `logs/*.out` / `*.err` stay local (gitignored). Summarize outcomes in
  `history.md`.
- Do not retry a failed run automatically without asking the user.
- For matrix jobs, record one `history.md` entry per combination.
