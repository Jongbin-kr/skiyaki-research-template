# Project Log

Project-level conclusions and phase outcomes for the skiyaki-research-template.
Experiment-level findings live in `experiments/*/journal.md`; this file records
template-build milestones and cross-cutting decisions.

## Phase Outcomes

### Phase 8 — Hugging Face Hub publication (complete)

- Added `.agents/skills/train-llm/scripts/publish_hf.py`: a deterministic helper
  that verifies the Hub repo, decides push eligibility, uploads checkpoints,
  records revisions, drafts a model card, verifies the upload by revision, and
  applies the private/public policy.
- **Design:** same pure-logic / single-injected-boundary split. All Hub I/O
  routes through one `HfClient` (`RealHfClient` in `main()` only, `huggingface_hub`
  imported lazily; `FakeHfClient` in tests, raises on unscripted ops).
- **Push policy:** pure `decide_push(policy, kind)` over never/final_only/
  milestone/final_and_milestone/every_save × final/milestone/intermediate;
  intermediate only under every_save; ineligible => skipped_by_policy, exit 1.
- **Safety:** mutating actions (create/ensure repo, set visibility, upload,
  revision) gated on approval; visibility never silently turns a private repo
  public. Placeholder namespace declines mutating actions (exit 1), never crashes.
- **Verification:** after upload, the checkpoint is located by its recorded
  revision; if not locatable, hf_status=upload_failed and the experiment is
  signaled not-complete (exit 1). hf_status is separate from the training status,
  so a Hub failure never flips the run to failed.
- **Secret safety:** no HF_TOKEN/credential value reaches run.yaml, the model
  card, or the envelope. Checkpoints upload to the Hub, never added to Git.
- **Tests:** 21 design properties covered across property + integration suites
  (31 Phase 8 tests). Full suite: 211 passed, no real Hub/network I/O.
- `huggingface.namespace` remains the placeholder; real value to be set before
  uploads (planned with the EMO work).

### Phase 7 — W&B experiment tracking (complete)

- Added `.agents/skills/train-llm/scripts/track_wandb.py`: a deterministic helper
  that creates/resumes W&B runs, assigns group/tags, records resolved config and
  Git SHA, manages the local W&B directory, compares runs within a group, and
  checks sync status.
- **Design:** same pure-logic / single-injected-boundary split as Phase 6. All
  W&B I/O routes through one `WandbClient` (`RealWandbClient` in `main()` only,
  `wandb` imported lazily; `FakeWandbClient` in tests, raises on unscripted ops).
- **Safety:** mutating actions (create/resume/config/finish/sync) gated on
  `approval.status == approved`; read-only actions (run.yaml read, URL parse,
  local dir inspection) ungated.
- **Failure distinction:** `run.yaml` carries `wandb_status`
  (`not_started|running|synced|sync_failed|offline`) separate from the training
  `status`, so a failed sync never flips the run to failed.
- **Placeholder tolerance:** `wandb.entity = TODO-set-before-phase-7` declines in
  online mode (exit 1) and downgrades to offline otherwise; never crashes.
- **Secret safety:** property test caught a real bug — the config key `_env_keys`
  matched the credential pattern (contains "KEY") and was being dropped; renamed
  to `_env_names`. No credential values reach run.yaml, config, or the envelope.
- **Tests:** 23 design properties covered across property + integration suites
  (32 Phase 7 tests). Full suite: 180 passed, no real W&B/network I/O.
- `wandb.entity` remains the placeholder; real value to be set before online runs
  (planned with the EMO clone).

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
