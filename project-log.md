# Project Log

Project-level conclusions and phase outcomes for the skiyaki-research-template.
Experiment-level findings live in `experiments/*/journal.md`; this file records
template-build milestones and cross-cutting decisions.

## Phase Outcomes

### Phase 6 — SSH + Slurm integration (complete)

- Added `.agents/skills/train-llm/scripts/submit_slurm.py`: a deterministic helper
  that extends the Phase 5 Slurm deferral into a real submission path.
- **Design:** strict split between pure logic (sbatch generation, GRES/resource
  mapping, log naming, quota validation, job-id parsing, Slurm→Harness status
  mapping, approval decision, commit-candidate filtering, secret redaction) and a
  single injected `CommandRunner` I/O boundary.
  - Production: `SSHCommandRunner` (constructed only in `main()`).
  - Tests: `FakeCommandRunner` with scripted results; raises on unscripted
    commands so tests never leak to real SSH/Slurm/network.
- **Safety:** mutating remote actions (`sbatch`, `scancel`, transfer/clone, env
  creation) require `approval.status == approved` in the experiment `plan.md`.
  Read-only probes (`ssh echo`, `test -d`, `conda env list`, `sinfo`, `squeue`,
  `sacct`, `scontrol show`) are non-mutating.
- **Linkage:** `run.yaml` extended with `slurm_job_id`, `slurm_state` (raw;
  keeps OUT_OF_MEMORY distinct), mapped `status`, `submitted_at`, `node_list`,
  and `array_job_id`. No secret values are ever written.
- **Tests:** 18 design properties covered across property + integration suites
  (39 Phase 6 tests). Full suite: 148 passed, no real I/O.
- **Cluster facts** documented in `project-plan.md` from read-only SKIML probes:
  partition `gpu`, account `cluster`, QoS `normal` (gpu<=4, cpu<=8, mem<=80G,
  MaxWall 2 days), driver CUDA ceiling 12.4, conda-provided toolkit, no lmod/nvcc.

### Phases 1–5 (complete, committed)

- Phase 2: core skills + helper scripts (`validate_job.py`, `initialize_run.py`).
- Phase 3: agent descriptions for the specialist subagents.
- Phase 4: planning golden path (fixtures, validators, repository contract).
- Phase 5: `run_local.py` — approval-gated local CPU execution; GPU/CPU-heavy
  jobs hard-deferred to Slurm (Phase 6).

## Pending (future phases)

- **Phase 7:** W&B integration — set `wandb.entity` in `project-plan.md` first;
  no live API calls until then.
- **Phase 8:** Hugging Face Hub — set `huggingface.namespace` first; no uploads
  until then.
- First planned real use: clone and run https://github.com/allenai/EMO on SKIML
  (requires explicit approval before any job submission).
