# Requirements Document

## Introduction

Phase 5 of the Codex-native AI/ML Research Workspace roadmap adds the **local lightweight job execution** layer on top of the existing run-initialization helper (`initialize_run.py`). After a user explicitly approves an experiment, Phase 5 must activate the project environment, construct the entrypoint command from the job's `config_style` and `parameters`, run a short CPU smoke-test job locally, capture stdout/stderr under the run directory, track the process through a lifecycle, and record both successful and failed attempts into `run.yaml` and `history.md`.

Phase 5 is deliberately bounded. It executes only short local CPU work. Any GPU job or CPU-heavy job must be rejected and deferred to Slurm (Phase 6), without ever spawning a local process. No live W&B API calls (Phase 7), no Hugging Face Hub uploads (Phase 8), no Git commits, and no network calls are performed. The execution layer composes with `initialize_run.py` rather than duplicating its responsibilities, and it stays framework-agnostic by using the project-declared run style instead of hardcoding any training framework.

This document specifies the behavior of the Phase 5 execution layer, implemented as a deterministic helper (`run_local.py`) in `.agents/skills/train-llm/scripts/`, with pure logic separated from a single thin subprocess execution step.

## Glossary

- **Local_Executor**: The Phase 5 component (`run_local.py`) that runs an approved job on the local machine and records the outcome. Composes with the Run_Initializer.
- **Run_Initializer**: The existing `initialize_run.py` helper that creates the run directory, `run.yaml`, and `resolved-job.yaml` with status `initialized`.
- **Run_Directory**: The directory `experiments/{experiment-id}/runs/{run-id}/` created by the Run_Initializer; the only location the Local_Executor is permitted to write.
- **Run_Record**: The `run.yaml` metadata file inside the Run_Directory.
- **Logs_Directory**: The `logs/` subdirectory inside the Run_Directory where stdout and stderr are captured.
- **History_File**: The experiment-level `history.md` file recording the sequence of execution attempts.
- **Job_Config**: The parsed job YAML (or `resolved-job.yaml`) describing `entrypoint`, `config_style`, `parameters`, `resources`, and optional `wandb`/`huggingface` sections.
- **Config_Style**: The parameter-passing convention declared in the Job_Config: one of `argument`, `hydra`, `json`, or `yaml`.
- **Environment_Manager**: The detected project environment type, one of `conda`, `uv`, `venv`, or `system`, chosen in that priority order.
- **Slurm_Required_Job**: A Job_Config that requests `resources.gpus` greater than zero, or whose estimated CPU-hours (`cpus` multiplied by the hour value derived from `resources.time`) exceed the local threshold of 4 CPU-hours.
- **Approval_Status**: The `approval.status` field in the experiment `plan.md`; execution is permitted only when it equals `approved`.
- **Run_Status**: The lifecycle state recorded in the Run_Record, one of `created`, `running`, `succeeded`, `failed`, `timed_out`, or `cancelled`.
- **Timeout_Seconds**: The maximum wall-clock duration derived from `resources.time` (or a configured default) after which the Local_Executor terminates the process.
- **WANDB_URL**: A Weights & Biases run URL that may appear in captured stdout/stderr and is parsed as plain text only.

## Requirements

### Requirement 1: Approval gating before execution

**User Story:** As an AI/ML researcher, I want local execution to run only after explicit approval, so that no job runs on my machine without my consent.

#### Acceptance Criteria

1. WHEN the Local_Executor is invoked for a job, THE Local_Executor SHALL read the Approval_Status from the experiment `plan.md` before constructing any command.
2. IF the Approval_Status is not equal to `approved`, THEN THE Local_Executor SHALL decline execution, SHALL NOT spawn a process, and SHALL report an approval-required outcome.
3. WHILE the Approval_Status equals `approved`, THE Local_Executor SHALL proceed to the environment-detection step.
4. IF the experiment `plan.md` is missing or does not contain an `approval.status` field, THEN THE Local_Executor SHALL decline execution and SHALL report a missing-approval outcome.

### Requirement 2: Slurm deferral for GPU and CPU-heavy jobs

**User Story:** As an AI/ML researcher, I want GPU and CPU-heavy jobs to be refused locally and deferred to Slurm, so that heavy workloads never run on the wrong machine before Phase 6 exists.

#### Acceptance Criteria

1. WHEN the Local_Executor classifies a Job_Config, THE Local_Executor SHALL compute whether the job is a Slurm_Required_Job using `resources.gpus` and estimated CPU-hours from `resources.cpus` and `resources.time`.
2. IF a Job_Config is a Slurm_Required_Job, THEN THE Local_Executor SHALL decline local execution, SHALL NOT spawn a process, and SHALL record a `deferred` outcome that identifies the Phase 6 Slurm dependency.
3. WHERE a Job_Config requests `resources.gpus` greater than zero, THE Local_Executor SHALL classify the job as a Slurm_Required_Job regardless of the estimated CPU-hours.
4. WHILE a Job_Config requests zero GPUs and estimated CPU-hours of 4 or fewer, THE Local_Executor SHALL classify the job as eligible for local execution.
5. WHEN the Local_Executor records a `deferred` outcome, THE Local_Executor SHALL append a corresponding entry to the History_File.

### Requirement 3: Environment detection and activation

**User Story:** As an AI/ML researcher, I want the executor to use my project's declared environment, so that the job runs with the correct dependencies.

#### Acceptance Criteria

1. WHEN the Local_Executor prepares to run an eligible job, THE Local_Executor SHALL detect the Environment_Manager in the priority order conda, then uv, then venv, then system.
2. WHERE a conda `environment.yaml` or an active conda environment is present, THE Local_Executor SHALL select the conda Environment_Manager and construct a `conda run` activation prefix.
3. WHERE conda is absent AND a `pyproject.toml` with a `uv.lock` and an available `uv` command are present, THE Local_Executor SHALL select the uv Environment_Manager and construct a `uv run` activation prefix.
4. WHERE conda and uv are absent AND a virtual environment directory or `VIRTUAL_ENV` is present, THE Local_Executor SHALL select the venv Environment_Manager and construct the corresponding activation prefix.
5. IF no project environment is detected, THEN THE Local_Executor SHALL select the system Environment_Manager and SHALL record a warning that system Python is used.
6. IF the selected environment activation step fails when the process is started, THEN THE Local_Executor SHALL set the Run_Status to `failed` and SHALL record the activation-failure reason in the Run_Record.

### Requirement 4: Command construction per config_style

**User Story:** As an AI/ML researcher, I want parameters passed in my project's declared style, so that my entrypoint receives arguments it understands without framework assumptions.

#### Acceptance Criteria

1. WHEN the Local_Executor constructs a command, THE Local_Executor SHALL combine the Environment_Manager activation prefix, a Python invocation, the Job_Config `entrypoint`, and the Job_Config `parameters` serialized according to the Config_Style.
2. WHERE the Config_Style equals `argument`, THE Local_Executor SHALL serialize each parameter as a double-dashed command-line flag with its value as a following token.
3. WHERE the Config_Style equals `hydra`, THE Local_Executor SHALL serialize each parameter as a `key=value` override token.
4. WHERE the Config_Style equals `json`, THE Local_Executor SHALL write the parameters to a JSON file inside the Run_Directory and SHALL pass the file path to the entrypoint.
5. WHERE the Config_Style equals `yaml`, THE Local_Executor SHALL write the parameters to a YAML file inside the Run_Directory and SHALL pass the file path to the entrypoint.
6. IF the Config_Style is absent from the Job_Config, THEN THE Local_Executor SHALL use the `argument` Config_Style as the default.
7. IF the Config_Style value is not one of `argument`, `hydra`, `json`, or `yaml`, THEN THE Local_Executor SHALL decline execution and SHALL report an unsupported-config-style outcome.
8. WHEN the Local_Executor serializes a parameter whose value contains whitespace, THE Local_Executor SHALL preserve the value as a single argument token.

### Requirement 5: Framework independence

**User Story:** As an AI/ML researcher, I want the executor to stay framework-agnostic, so that it works for PyTorch, JAX, or a custom loop without changes.

#### Acceptance Criteria

1. THE Local_Executor SHALL derive the executed command only from the Job_Config `entrypoint`, `parameters`, `config_style`, and the detected Environment_Manager.
2. THE Local_Executor SHALL construct commands without referencing any named training framework.
3. WHERE a Job_Config declares an arbitrary `entrypoint` path, THE Local_Executor SHALL use that path verbatim as the script argument.

### Requirement 6: Entrypoint existence check

**User Story:** As an AI/ML researcher, I want a missing entrypoint caught as a recorded failure, so that I get a tracked outcome instead of a silent crash.

#### Acceptance Criteria

1. WHEN the Local_Executor prepares an eligible job, THE Local_Executor SHALL verify that the Job_Config `entrypoint` resolves to an existing file within the workspace.
2. IF the `entrypoint` file does not exist, THEN THE Local_Executor SHALL set the Run_Status to `failed`, SHALL set an exit code reflecting the preparation failure, and SHALL record a missing-entrypoint reason in the Run_Record.
3. WHEN the Local_Executor records a missing-entrypoint failure, THE Local_Executor SHALL append a failure entry to the History_File.

### Requirement 7: Local execution and stdout/stderr capture

**User Story:** As an AI/ML researcher, I want the job's output captured to files, so that I can inspect logs for every attempt.

#### Acceptance Criteria

1. WHEN the Local_Executor runs an eligible job, THE Local_Executor SHALL execute the constructed command from the workspace root as the working directory.
2. WHEN the process runs, THE Local_Executor SHALL capture standard output to `stdout.log` and standard error to `stderr.log` within the Logs_Directory.
3. THE Local_Executor SHALL write all execution outputs and generated files only within the Run_Directory provided by the Run_Initializer.
4. WHEN the process completes, THE Local_Executor SHALL record the process exit code in the Run_Record.
5. WHERE the captured stdout or stderr contains a WANDB_URL, THE Local_Executor SHALL extract the WANDB_URL as plain text and SHALL record it in the Run_Record without contacting any external service.

### Requirement 8: Run status lifecycle

**User Story:** As an AI/ML researcher, I want each run tracked through a clear status lifecycle, so that I can tell at a glance how an attempt ended.

#### Acceptance Criteria

1. WHEN the Local_Executor begins execution of an eligible job, THE Local_Executor SHALL set the Run_Status to `running` and SHALL record a `started_at` timestamp in the Run_Record.
2. WHEN a process exits with code zero, THE Local_Executor SHALL set the Run_Status to `succeeded`, SHALL record a `completed_at` timestamp, and SHALL record an exit code of zero.
3. IF a process exits with a non-zero code, THEN THE Local_Executor SHALL set the Run_Status to `failed`, SHALL record a `completed_at` timestamp, and SHALL record the non-zero exit code.
4. IF the process exceeds the Timeout_Seconds, THEN THE Local_Executor SHALL terminate the process, SHALL set the Run_Status to `timed_out`, and SHALL record a `completed_at` timestamp.
5. IF the process is interrupted by a cancellation signal, THEN THE Local_Executor SHALL set the Run_Status to `cancelled` and SHALL record a `completed_at` timestamp.
6. WHEN the Local_Executor reads a Run_Record whose status is `initialized`, THE Local_Executor SHALL treat that status as the lifecycle state `created`.
7. THE Local_Executor SHALL set the Run_Status to one of `created`, `running`, `succeeded`, `failed`, `timed_out`, or `cancelled`.

### Requirement 9: Failed-run recording

**User Story:** As an AI/ML researcher, I want failed attempts recorded with the same rigor as successes, so that debugging information is never lost.

#### Acceptance Criteria

1. WHEN an attempt ends in `failed`, `timed_out`, or `cancelled`, THE Local_Executor SHALL update the Run_Record with the final Run_Status, the exit code, the `started_at` timestamp when execution began, and the `completed_at` timestamp.
2. WHEN an attempt fails during preparation before a process starts, THE Local_Executor SHALL record the failure reason in the Run_Record and SHALL preserve any captured output in the Logs_Directory.
3. THE Local_Executor SHALL retain the Run_Directory and its captured logs for every recorded attempt.

### Requirement 10: Timeout handling

**User Story:** As an AI/ML researcher, I want a bounded runtime for local jobs, so that a smoke test cannot hang my machine indefinitely.

#### Acceptance Criteria

1. WHEN the Local_Executor starts a process, THE Local_Executor SHALL derive the Timeout_Seconds from the Job_Config `resources.time` or from a configured default when `resources.time` is absent.
2. IF the process runtime reaches the Timeout_Seconds, THEN THE Local_Executor SHALL terminate the process and SHALL set the Run_Status to `timed_out`.
3. WHEN a timeout terminates the process, THE Local_Executor SHALL record the elapsed duration and the timeout threshold in the Run_Record.

### Requirement 11: History recording

**User Story:** As an AI/ML researcher, I want each attempt appended to history.md, so that the experiment keeps a factual chronological log.

#### Acceptance Criteria

1. WHEN an attempt reaches a terminal Run_Status, THE Local_Executor SHALL append an entry to the History_File that includes a timestamp, the run identifier, the job reference, and the final Run_Status.
2. WHERE the History_File does not yet exist in the experiment directory, THE Local_Executor SHALL create the History_File before appending the entry.
3. WHEN the Local_Executor appends a History_File entry for a succeeded run, THE Local_Executor SHALL include the exit code and the WANDB_URL when a WANDB_URL is present.
4. WHEN the Local_Executor appends a History_File entry, THE Local_Executor SHALL preserve existing History_File content.

### Requirement 12: Secret and cache boundaries

**User Story:** As an AI/ML researcher, I want no secrets or caches written into tracked files, so that the repository stays clean and safe to commit.

#### Acceptance Criteria

1. WHEN the Local_Executor records environment details in the Run_Record, THE Local_Executor SHALL exclude credential values such as API tokens and keys.
2. IF a credential-bearing environment variable is referenced for the child process, THEN THE Local_Executor SHALL pass the value only to the child process environment and SHALL record the variable name without its value.
3. THE Local_Executor SHALL write model checkpoints and W&B cache data outside the committed Run_Record and SHALL NOT embed such binary artifacts in `run.yaml`.
4. THE Local_Executor SHALL perform no network calls, no Git operations, and no Hugging Face Hub uploads during execution.
