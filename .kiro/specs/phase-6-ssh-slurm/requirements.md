# Requirements Document

## Introduction

Phase 6 of the Codex-native AI/ML Research Workspace roadmap adds the **SSH and Slurm execution** layer on top of the Phase 5 local-execution helper. In Phase 5, `run_local.py` hard-defers every GPU job and every CPU-heavy job to Slurm (the `DEFER_SLURM` decision) without implementing the remote path. Phase 6 implements that deferred path: it verifies the configured SSH submit host, the remote project path, and the remote conda environment; generates a deterministic Slurm `sbatch` script from a job YAML; validates requested resources against the project QoS caps before submission; submits the job over SSH; parses the returned Slurm job id; polls status; cancels; supports array and dependency jobs; supports retry and resume; applies the mandated log-naming rule; and links the resulting Slurm job back to the Harness Run by recording Slurm linkage fields and a mapped status in `run.yaml`.

Phase 6 is deliberately bounded. All stable settings are read from the repository `project-plan.md` and are never re-asked. Real remote mutating actions — submitting with `sbatch`, cancelling with `scancel`, transferring or cloning remote files, and creating the remote conda environment — require explicit user approval and never execute during automated tests. Read-only probes (`ssh echo`, `sinfo`, `squeue`, `sacct`, `scontrol show`) are used only through an injected command runner so that tests fake them without any real network access. The design separates pure logic (sbatch script string generation, resource-to-SBATCH mapping, quota validation, Slurm-to-Harness status mapping, log-name construction, job-id parsing) from the injected `CommandRunner` boundary used for SSH and Slurm I/O. Live Weights & Biases API work remains in Phase 7, and Hugging Face Hub work remains in Phase 8; neither is implemented here. Generated scripts and `run.yaml` records never contain secrets, and raw `.out`/`.err` logs, checkpoints, and W&B caches are never committed.

This document specifies the behavior of the Phase 6 execution layer, implemented as a deterministic helper (`submit_slurm.py`) in `.agents/skills/train-llm/scripts/`, with pure logic separated from a single injected command-runner boundary for all SSH and Slurm calls.

## Glossary

- **Slurm_Submitter**: The Phase 6 component (`submit_slurm.py`) that verifies the remote environment, generates and submits Slurm scripts, polls and cancels jobs, and links the Slurm job to the Harness Run.
- **Command_Runner**: The injected interface that executes a command (locally or over SSH) and returns an exit code with captured stdout and stderr. All SSH and Slurm calls pass through the Command_Runner so tests can supply a fake implementation.
- **Local_Executor**: The existing Phase 5 component (`run_local.py`) that runs eligible local jobs and defers GPU and CPU-heavy jobs to Slurm.
- **Project_Plan**: The repository-root `project-plan.md` file whose YAML frontmatter supplies stable settings: SSH host alias, remote project root, remote conda root, Slurm partition, account, QoS, and QoS caps.
- **SSH_Host**: The submit-host alias recorded as `execution.ssh_host` in the Project_Plan (value `SKIML`).
- **Remote_Project_Root**: The remote directory recorded as `execution.remote_project_root` in the Project_Plan under which jobs run and logs are written.
- **Remote_Conda_Root**: The remote miniconda installation path recorded as `environment.remote_conda_root` in the Project_Plan.
- **Conda_Env_Name**: The project conda environment name declared in the project `environment.yaml` manifest.
- **Job_Config**: The parsed job YAML describing `job_id`, `type`, `entrypoint`, `config_style`, `parameters`, a `resources` section, and optional `array` and `dependency` fields.
- **Resources**: The `resources` section of a Job_Config declaring `gpus`, `cpus`, `mem_gb` (or `memory_gb`), `time`, and optional `gpu_type` and `partition`.
- **QoS_Caps**: The per-user QoS `normal` limits recorded in the Project_Plan: `gpus` at most 4, `cpus` at most 8, `mem_gb` at most 80, and wall time at most 2 days (`2-00:00:00`).
- **Sbatch_Script**: The deterministic Slurm batch script string generated from a Job_Config and Project_Plan settings, containing `#SBATCH` directives, conda activation, and the project-declared run command.
- **Gres_Spec**: The Slurm generic-resource request string: `gpu:<N>` when no GPU type is set, or `gpu:<type>:<N>` for `A6000`, `PRO6000`, or `4090`.
- **Slurm_Job_Id**: The numeric job identifier returned by `sbatch` and parsed from its stdout.
- **Array_Job**: A Job_Config declaring an `array` specification (for example `0-7`), submitted as a Slurm array that produces one array job id and multiple task ids.
- **Dependency_Spec**: A Job_Config field expressing a Slurm dependency (for example `afterok:<jobid>`) applied as the `#SBATCH --dependency` directive.
- **Log_Name**: The constructed Slurm log file base name following the mandated rule, excluding the `.out`/`.err` suffix.
- **Date_Prefix**: The `YYYYMMDD-HHMMSS` timestamp fixed at submit time and embedded literally in the Slurm `--output`/`--error` directives alongside the Slurm placeholders.
- **Slurm_State**: A Slurm job state reported by `squeue` or `sacct`, one of `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMEOUT`, `OUT_OF_MEMORY`, or `PREEMPTED`.
- **Run_Status**: The Harness Run lifecycle state recorded in `run.yaml`, one of `submitted`, `pending`, `running`, `succeeded`, `failed`, `cancelled`, `timed_out`, or `preempted`.
- **Run_Record**: The `run.yaml` metadata file inside the Run directory, extended in Phase 6 with Slurm linkage fields.
- **Mutating_Remote_Action**: Any remote action that changes remote or scheduler state: `sbatch` submission, `scancel`, remote file transfer or clone, and remote conda environment creation.
- **Approval_Status**: The `approval.status` field in the experiment `plan.md`; mutating remote actions proceed only when it equals `approved`.

## Requirements

### Requirement 1: SSH host reachability verification

**User Story:** As an AI/ML researcher, I want the submitter to confirm the configured SSH host is reachable before anything else, so that failures surface early with a clear cause.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter begins a submission or verification task, THE Slurm_Submitter SHALL read the SSH_Host from the Project_Plan rather than prompting for it.
2. WHEN the Slurm_Submitter verifies reachability, THE Slurm_Submitter SHALL issue a read-only probe through the Command_Runner that runs a non-mutating remote command over the SSH_Host.
3. IF the reachability probe returns a non-zero exit code, THEN THE Slurm_Submitter SHALL report an unreachable-host outcome and SHALL NOT attempt any Mutating_Remote_Action.
4. WHILE the reachability probe returns exit code zero, THE Slurm_Submitter SHALL record the SSH_Host as reachable and proceed to remote-path verification.

### Requirement 2: Remote project path verification

**User Story:** As an AI/ML researcher, I want the submitter to confirm the remote project directory exists, so that jobs do not run against a missing or wrong path.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter verifies the remote path, THE Slurm_Submitter SHALL read the Remote_Project_Root from the Project_Plan.
2. WHEN the Slurm_Submitter checks the Remote_Project_Root, THE Slurm_Submitter SHALL issue a read-only directory-existence probe through the Command_Runner.
3. IF the Remote_Project_Root does not exist on the remote host, THEN THE Slurm_Submitter SHALL report a missing-remote-path outcome and SHALL NOT submit any job.
4. WHILE the Remote_Project_Root exists, THE Slurm_Submitter SHALL record the remote path as verified and proceed to environment verification.

### Requirement 3: Remote conda environment verification

**User Story:** As an AI/ML researcher, I want the submitter to confirm the project conda environment is present on the cluster, so that a submitted job finds its dependencies.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter verifies the remote environment, THE Slurm_Submitter SHALL read the Remote_Conda_Root from the Project_Plan and the Conda_Env_Name from the project `environment.yaml`.
2. WHEN the Slurm_Submitter checks for the environment, THE Slurm_Submitter SHALL issue a read-only probe through the Command_Runner that lists conda environments under the Remote_Conda_Root.
3. IF the Conda_Env_Name is absent from the probe output, THEN THE Slurm_Submitter SHALL report a missing-environment outcome that identifies remote environment creation as a Mutating_Remote_Action requiring approval.
4. WHILE the Conda_Env_Name is present in the probe output, THE Slurm_Submitter SHALL record the environment as verified.

### Requirement 4: Sbatch script generation

**User Story:** As an AI/ML researcher, I want a correct and reproducible sbatch script generated from my job YAML, so that submission is deterministic and auditable.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter generates an Sbatch_Script from a Job_Config, THE Slurm_Submitter SHALL map the partition, account, and QoS from the Project_Plan into `#SBATCH --partition`, `#SBATCH --account`, and `#SBATCH --qos` directives.
2. WHEN the Slurm_Submitter maps the Resources, THE Slurm_Submitter SHALL emit `#SBATCH --cpus-per-task` from `resources.cpus`, `#SBATCH --mem` from `resources.mem_gb` in gigabytes, and `#SBATCH --time` from `resources.time`.
3. WHERE the Resources request `gpus` greater than zero, THE Slurm_Submitter SHALL emit a `#SBATCH --gres` directive whose value equals the Gres_Spec derived from `gpus` and the optional `gpu_type`.
4. WHEN the Slurm_Submitter emits the activation section, THE Slurm_Submitter SHALL source the conda profile under the Remote_Conda_Root and activate the Conda_Env_Name before the run command.
5. WHEN the Slurm_Submitter emits the run command, THE Slurm_Submitter SHALL use the project-declared entrypoint and parameters without embedding any training-framework name chosen by the Slurm_Submitter.
6. THE Slurm_Submitter SHALL include a comment in the Sbatch_Script stating that the CUDA toolkit is supplied by the conda environment and is pinned at or below the driver CUDA ceiling of 12.4.
7. THE Sbatch_Script SHALL NOT contain any secret, token, password, or credential value.

### Requirement 5: Quota pre-check against QoS caps

**User Story:** As an AI/ML researcher, I want requested resources checked against my QoS limits before submission, so that over-limit jobs are rejected locally instead of being rejected by the scheduler.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter prepares to submit, THE Slurm_Submitter SHALL validate the Resources against the QoS_Caps read from the Project_Plan before any `sbatch` submission.
2. IF `resources.gpus` exceeds 4, THEN THE Slurm_Submitter SHALL reject the job with a quota-violation outcome and SHALL NOT submit.
3. IF `resources.cpus` exceeds 8, THEN THE Slurm_Submitter SHALL reject the job with a quota-violation outcome and SHALL NOT submit.
4. IF `resources.mem_gb` exceeds 80, THEN THE Slurm_Submitter SHALL reject the job with a quota-violation outcome and SHALL NOT submit.
5. IF the wall time derived from `resources.time` exceeds 2 days, THEN THE Slurm_Submitter SHALL reject the job with a quota-violation outcome and SHALL NOT submit.
6. WHILE every requested resource is within the QoS_Caps, THE Slurm_Submitter SHALL mark the quota check as passed and allow submission to proceed.

### Requirement 6: Submission and job-id parsing

**User Story:** As an AI/ML researcher, I want the submitter to submit the generated script and capture the Slurm job id, so that the run is tracked against a real scheduler job.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter submits an approved job, THE Slurm_Submitter SHALL invoke `sbatch` with the generated Sbatch_Script through the Command_Runner over the SSH_Host.
2. WHEN `sbatch` returns successfully, THE Slurm_Submitter SHALL parse the Slurm_Job_Id from the `sbatch` stdout.
3. IF the `sbatch` stdout does not contain a parseable Slurm_Job_Id, THEN THE Slurm_Submitter SHALL report a submission-failure outcome and SHALL NOT record a Slurm_Job_Id in the Run_Record.
4. WHEN a Slurm_Job_Id is parsed, THE Slurm_Submitter SHALL record the Slurm_Job_Id and set the Run_Status to `submitted` in the Run_Record.

### Requirement 7: Status polling and Slurm-to-Harness mapping

**User Story:** As an AI/ML researcher, I want Slurm job states translated into the Harness Run status model, so that `run.yaml` reflects the true outcome including preemption, out-of-memory, and timeout.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter polls a submitted job, THE Slurm_Submitter SHALL query the Slurm_State through the Command_Runner using `squeue` for active jobs and `sacct` for completed jobs.
2. WHEN the Slurm_State is `PENDING`, THE Slurm_Submitter SHALL map the Run_Status to `pending`.
3. WHEN the Slurm_State is `RUNNING`, THE Slurm_Submitter SHALL map the Run_Status to `running`.
4. WHEN the Slurm_State is `COMPLETED`, THE Slurm_Submitter SHALL map the Run_Status to `succeeded`.
5. IF the Slurm_State is `FAILED` or `OUT_OF_MEMORY`, THEN THE Slurm_Submitter SHALL map the Run_Status to `failed` and SHALL record the originating Slurm_State in the Run_Record.
6. IF the Slurm_State is `CANCELLED`, THEN THE Slurm_Submitter SHALL map the Run_Status to `cancelled`.
7. IF the Slurm_State is `TIMEOUT`, THEN THE Slurm_Submitter SHALL map the Run_Status to `timed_out`.
8. IF the Slurm_State is `PREEMPTED`, THEN THE Slurm_Submitter SHALL map the Run_Status to `preempted`.

### Requirement 8: Job cancellation

**User Story:** As an AI/ML researcher, I want to cancel a submitted Slurm job, so that I can stop a run that is no longer wanted.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter is asked to cancel a job, THE Slurm_Submitter SHALL treat the cancellation as a Mutating_Remote_Action requiring the Approval_Status to equal `approved`.
2. WHILE the Approval_Status equals `approved`, THE Slurm_Submitter SHALL invoke `scancel` with the Slurm_Job_Id through the Command_Runner over the SSH_Host.
3. WHEN the cancellation command returns exit code zero, THE Slurm_Submitter SHALL set the Run_Status to `cancelled` in the Run_Record.
4. IF the Approval_Status does not equal `approved`, THEN THE Slurm_Submitter SHALL decline the cancellation and SHALL NOT invoke `scancel`.

### Requirement 9: Array job support

**User Story:** As an AI/ML researcher, I want to submit array jobs, so that ablation sweeps run as a single Slurm array.

#### Acceptance Criteria

1. WHERE a Job_Config declares an `array` specification, THE Slurm_Submitter SHALL emit a `#SBATCH --array` directive whose value equals the declared array specification.
2. WHEN the Slurm_Submitter generates log directives for an Array_Job, THE Slurm_Submitter SHALL embed the array task placeholder in the `--output` and `--error` directives.
3. WHEN `sbatch` returns for an Array_Job, THE Slurm_Submitter SHALL parse the array Slurm_Job_Id and record it in the Run_Record.

### Requirement 10: Dependency support

**User Story:** As an AI/ML researcher, I want to express job dependencies, so that a run starts only after a prerequisite job reaches the required state.

#### Acceptance Criteria

1. WHERE a Job_Config declares a Dependency_Spec, THE Slurm_Submitter SHALL emit a `#SBATCH --dependency` directive whose value equals the declared Dependency_Spec.
2. WHILE a Job_Config declares no Dependency_Spec, THE Slurm_Submitter SHALL omit the `#SBATCH --dependency` directive from the Sbatch_Script.

### Requirement 11: Retry and resume

**User Story:** As an AI/ML researcher, I want to retry a failed run and resume tracking of an existing Slurm job, so that recovery does not create duplicate or orphaned runs.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter retries a job whose previous Run_Status is `failed`, `timed_out`, `cancelled`, or `preempted`, THE Slurm_Submitter SHALL create a new Run_Record for the retry attempt and SHALL preserve the prior Run_Record.
2. WHEN the Slurm_Submitter resumes tracking of a Run that already records a Slurm_Job_Id, THE Slurm_Submitter SHALL poll the recorded Slurm_Job_Id without issuing a new `sbatch` submission.
3. IF a resume target has no recorded Slurm_Job_Id, THEN THE Slurm_Submitter SHALL report a resume-not-possible outcome and SHALL NOT submit a new job.

### Requirement 12: Mandated log naming

**User Story:** As an AI/ML researcher, I want Slurm logs named by the mandated convention, so that logs are traceable to date, job id, task, and job name.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter builds log directives for a regular job, THE Slurm_Submitter SHALL set the `--output` base name to `<Date_Prefix>_%A_%x` and the `--error` base name to the same stem, with `.out` and `.err` suffixes respectively.
2. WHEN the Slurm_Submitter builds log directives for an Array_Job, THE Slurm_Submitter SHALL set the `--output` base name to `<Date_Prefix>_%A_%a_%x` and the `--error` base name to the same stem, with `.out` and `.err` suffixes respectively.
3. WHEN the Slurm_Submitter fixes the Date_Prefix, THE Slurm_Submitter SHALL use a single `YYYYMMDD-HHMMSS` timestamp captured at submit time for both the `--output` and `--error` directives.
4. WHEN the Slurm_Submitter constructs a resolved Log_Name from a Slurm_Job_Id, an optional task id, and a job name, THE Slurm_Submitter SHALL produce `<Date_Prefix>_<jobid>_<jobname>` for a regular job and `<Date_Prefix>_<jobid>_<taskid>_<jobname>` for an Array_Job task.

### Requirement 13: Run-to-Slurm linkage in run.yaml

**User Story:** As an AI/ML researcher, I want the Slurm job linked to its Harness Run, so that `run.yaml` captures the scheduler identity and current status.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter records a submitted job, THE Slurm_Submitter SHALL write the Slurm_Job_Id, the submit time, and the queue time into the Run_Record.
2. WHEN the Slurm_Submitter observes a node assignment from `squeue` or `sacct`, THE Slurm_Submitter SHALL write the assigned node list into the Run_Record.
3. WHEN the Slurm_Submitter maps a Slurm_State to a Run_Status, THE Slurm_Submitter SHALL write the mapped Run_Status into the Run_Record.
4. THE Run_Record SHALL NOT contain any secret, token, password, or credential value.

### Requirement 14: Approval gating for mutating remote actions

**User Story:** As an AI/ML researcher, I want every remote action that changes state to require my approval, so that no submission, cancellation, transfer, or environment creation happens without my consent.

#### Acceptance Criteria

1. WHEN the Slurm_Submitter prepares a Mutating_Remote_Action, THE Slurm_Submitter SHALL read the Approval_Status from the experiment `plan.md` before executing the action.
2. IF the Approval_Status does not equal `approved`, THEN THE Slurm_Submitter SHALL decline the Mutating_Remote_Action and SHALL report an approval-required outcome.
3. WHILE the Approval_Status equals `approved`, THE Slurm_Submitter SHALL permit the Mutating_Remote_Action to execute through the Command_Runner.
4. WHEN the Slurm_Submitter runs under test with a fake Command_Runner, THE Slurm_Submitter SHALL route every SSH and Slurm call through the injected Command_Runner so that no real network call occurs.

### Requirement 15: Login-node and secret safety boundaries

**User Story:** As an AI/ML researcher, I want heavy work kept off the login node and secrets kept out of artifacts, so that the Phase 6 layer honors cluster policy and the artifact policy.

#### Acceptance Criteria

1. THE Slurm_Submitter SHALL route every GPU job and every CPU-heavy job through `sbatch` and SHALL NOT execute such a job directly on the login node.
2. WHEN the Slurm_Submitter issues a read-only probe on the login node, THE Slurm_Submitter SHALL restrict the probe to non-mutating verification commands.
3. THE Slurm_Submitter SHALL exclude raw `.out` and `.err` logs, checkpoints, and W&B cache directories from any content it marks as commit candidates.
4. THE Slurm_Submitter SHALL NOT invoke the live Weights & Biases API or the Hugging Face Hub, deferring those actions to Phase 7 and Phase 8 respectively.
