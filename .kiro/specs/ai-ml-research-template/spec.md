# Codex-native AI/ML Research Workspace 최종 구현 계획

## 요약

> **GitHub Template 하나에 AI/ML 프로젝트 구조와 Codex Research Harness를 함께 넣는다.**

별도의 Python Harness나 자체 Agent Loop는 만들지 않는다. Codex의 기존 Harness를 사용하고, GitHub Template이 다음을 제공한다.

| 구성 | 역할 |
|---|---|
| `AGENTS.md` | Codex Main Agent가 항상 따라야 하는 핵심 규칙 |
| `.agents/skills/` | 반복 가능한 연구 워크플로 |
| `agent-descriptions/` | Specialist subagent 역할과 권한 |
| `project-plan.md` | 프로젝트 목표와 연구·인프라 정책 |
| `project-log.md` | 프로젝트 전체의 연구 진행 기록 |
| `experiments/` | 실험 계획, Job, Run, 결과, Journal |
| `environment.yaml` | 프로젝트의 Conda 가상환경 |
| 기존 CLI/SDK | SSH, Slurm, W&B, Hugging Face, Git 연동 |

OpenAI 공식 문서에서도 저장소 수준의 지침은 `AGENTS.md`, 반복 워크플로는 Skills, 세부 자료와 script는 Skill의 references/scripts로 분리하는 방식을 권장한다. [OpenAI Codex 가이드](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)

---

# 1. 제품 정의

## 주요 사용자

코드를 직접 소유하고 SSH·Slurm·GPU 인프라를 사용하는 AI/ML 연구자.

## 기본 인터페이스

Codex Main Agent와의 채팅.

사용자가 직접 모든 학습 명령을 조립하기보다 다음과 같이 요청한다.

```text
“LoRA rank ablation을 해보자.”
```

Codex는 이를 다음 전체 연구 워크플로로 전환한다.

```text
Discover
→ Grill
→ Plan
→ Review
→ Approval
→ Train
→ Evaluate
→ Finalize
→ Commit Approval


## 완료 조건

실험은 다음이 모두 충족돼야 완료된 것으로 판단한다.

- 필요한 Train Run이 끝남
- 평가가 끝남
- 성공 기준 판정이 끝남
- W&B Run과 비교 결과가 확인됨
- 필요한 checkpoint가 Hugging Face Hub에 올라감
- `results.yaml`이 작성됨
- `history.md`가 갱신됨
- `journal.md`에 최종 결론이 작성됨
- `project-log.md`에 프로젝트 수준 결과가 반영됨
- Git commit 후보가 제시됨

Git commit 자체는 사용자 승인 후 수행한다.

---

# 2. 핵심 설계 원칙

## GitHub Template가 곧 v1 Harness

v1에서는 다음을 분리하지 않는다.

```text
GitHub Project Template
=
AI/ML Project Skeleton
+
Codex Research Harness
```

사용자는 GitHub의 **Use this template**로 프로젝트를 생성하고, `project-plan.md`와 가상환경만 설정하면 된다.

## Codex의 Agent Loop를 그대로 사용

구현하지 않는 것:

- 자체 LLM Agent Loop
- 공통 Python Harness
- 공통 Python Runner
- 별도 웹 백엔드
- 별도 IDE
- Agents API 기반 SaaS

사용하는 것:

- Codex Main Agent
- Codex subagent 기능
- `AGENTS.md`
- Repository-local Skills
- Codex shell/file/Git 도구
- 프로젝트에 설치된 SSH·Slurm·W&B·HF 도구

## 연구 프로젝트가 실행 환경을 소유

프로젝트마다 실행 환경이 다를 수 있다.

- Miniconda
- `uv`
- `venv`
- PyTorch
- JAX
- Transformers Trainer
- Accelerate
- Lightning
- Custom training loop

Harness는 특정 Python framework를 강제하지 않는다. 프로젝트의 기존 코드와 실행 방식을 조사한 뒤 사용한다.

## 판단과 실행을 분리

- Agent: 연구적 판단, 질문, 계획, 해석
- Skill: 반복 가능한 업무 절차
- 프로젝트 도구: 실제 학습·평가·제출
- YAML Job: 실행에 필요한 재현 가능한 설정
- Markdown: 사람이 검토해야 하는 계획과 해석

---

# 3. 최종 GitHub Template 구조

```text
ai-ml-research-template/
├── AGENTS.md
├── README.md
├── .gitignore
│
├── environment.yaml
├── project-plan.md
├── project-log.md
│
├── .agents/
│   └── skills/
│       ├── grill-me/
│       │   └── SKILL.md
│       ├── discover-prior-research/
│       │   └── SKILL.md
│       ├── plan-ml-experiment/
│       │   ├── SKILL.md
│       │   └── references/
│       ├── train-llm/
│       │   ├── SKILL.md
│       │   └── references/
│       ├── evaluate-llm/
│       │   ├── SKILL.md
│       │   └── references/
│       └── finalize-experiment/
│           ├── SKILL.md
│           └── references/
│
├── agent-descriptions/
│   ├── research-journal-git.md
│   ├── wandb-analyst.md
│   ├── huggingface-managing-specialist.md
│   ├── visualization-specialist.md
│   └── slurm-managing-specialist.md
│
├── templates/
│   ├── experiment-plan.md
│   ├── train-job.yaml
│   ├── evaluate-job.yaml
│   ├── run.yaml
│   ├── artifacts.yaml
│   ├── results.yaml
│   ├── history.md
│   └── journal.md
│
├── experiments/
│   └── .gitkeep
│
├── outputs/
│   └── .gitkeep
│
├── data/
│   └── README.md
│
├── notebooks/
├── src/
└── tests/
```

`src/`, `tests/`, 실행 script는 각 연구 프로젝트의 방식에 맞게 사용자가 채운다.

---

# 4. 프로젝트 수준 파일

## `environment.yaml`

Conda 가상환경 전용 파일이다.

```yaml
name: my-research-project

channels:
  - pytorch
  - nvidia
  - conda-forge

dependencies:
  - python=3.11
  - pytorch
  - pip
  - pip:
      - transformers
      - datasets
      - peft
      - wandb
      - huggingface-hub
```

`uv`를 사용하는 프로젝트는 `pyproject.toml`과 `uv.lock`을 대신 사용할 수 있다.

## `project-plan.md`

프로젝트의 장기 목표와 안정적인 정책을 정의한다.

형식은 Markdown + YAML frontmatter다.

```markdown
---
schema_version: 1
project_id: my-research-project

environment:
  manager: miniconda
  manifest: environment.yaml

execution:
  default_target: ssh
  ssh_host: research-cluster
  remote_project_root: /workspace/my-research-project
  direct_cpu_max_minutes: 10
  require_slurm_for_gpu: true
  require_slurm_for_cpu_heavy: true

slurm:
  partition: gpu
  account: my-account
  qos: normal
  max_gpus_per_job: 4
  max_concurrent_jobs: 8

wandb:
  entity: my-lab
  project: my-research-project
  mode: online
  keep_local_data: true

huggingface:
  namespace: my-lab
  private: true
  push_policy: final_and_milestone
---

# Project Plan

## 연구 목표

...

## 주요 연구 질문

...

## 기본 평가 원칙

...

## Artifact 정책

...
```

포함할 내용:

- 프로젝트 목적
- 연구 범위
- 주요 baseline
- 기본 평가 원칙
- 가상환경 관리자
- SSH host alias
- Slurm partition/account/qos
- 개인·프로젝트 quota
- W&B entity/project
- Hugging Face namespace
- artifact 공개 정책
- 승인 정책

포함하지 않을 내용:

- API token
- SSH private key
- password
- W&B/HF access token
- 개인 인증 정보

## `project-log.md`

프로젝트 전체의 중요 사건과 결론을 시간순으로 기록한다.

```markdown
## 2026-09-23 — LoRA rank ablation 완료

- 결론: rank 16 이후 성능 향상이 포화됨
- Best run: `train-r16__20260923T142530`
- Experiment: `experiments/lora-rank-ablation/`
- W&B: ...
- Hugging Face: ...
- Git commit: pending
- 다음 실험: rank 16 learning-rate ablation
```

`project-plan.md`와 역할을 분리한다.

| 파일 | 질문 |
|---|---|
| `project-plan.md` | 앞으로 무엇을, 어떤 원칙으로 연구할 것인가? |
| `project-log.md` | 지금까지 무엇을 했고 무엇을 배웠는가? |

---

# 5. Experiment 구조

```text
experiments/<experiment-id>/
├── plan.md
├── jobs/
│   ├── train.yaml
│   └── evaluate.yaml
├── runs/
│   └── <run-id>/
│       ├── run.yaml
│       ├── resolved-job.yaml
│       ├── artifacts.yaml
│       ├── logs/
│       └── wandb/
├── results.yaml
├── history.md
├── journal.md
└── figures/
```

## `plan.md`

Markdown + YAML frontmatter를 사용한다.

```markdown
---
schema_version: 1
experiment_id: lora-rank-ablation
status: awaiting_approval

primary_metric:
  name: eval_accuracy
  direction: maximize

success_criteria:
  minimum_improvement: 0.02

jobs:
  - jobs/train.yaml
  - jobs/evaluate.yaml

approval:
  status: pending
  approved_by:
  approved_at:
  approved_commit:
---

# LoRA Rank Ablation

## 목적

LoRA rank가 성능, 메모리, 학습 시간에 미치는 영향을 비교한다.

## 가설

rank 16 이후에는 성능 향상이 포화될 것이다.

## Baseline

...

## 설계 근거

...

## Agent가 판단한 사항

...

## 위험 및 제한

...
```

Frontmatter는 기계적으로 확인할 정보, Markdown 본문은 사람이 검토할 판단과 근거를 담는다.

## `jobs/*.yaml`

재현이 중요한 Python Job의 정확한 실행 설정을 기록한다.

```yaml
job_id: train-lora-rank-ablation
type: train

entrypoint: src/train.py
config_style: argument

matrix:
  lora_rank: [4, 8, 16, 32]

parameters:
  model_name: ...
  dataset_name: ...
  learning_rate: 0.0002
  epochs: 3
  seed: 42

resources:
  backend: slurm
  gpus: 1
  cpus: 8
  memory_gb: 64
  time: "08:00:00"

wandb:
  enabled: true
  group: lora-rank-ablation

huggingface:
  push: milestone
```

프로젝트가 Hydra나 다른 config system을 사용한다면 해당 형식을 그대로 참조해도 된다. Harness가 별도의 설정 체계를 강제로 덮어쓰지 않는다.

---

# 6. Job, Run, Slurm Log의 차이

| 개념 | 의미 |
|---|---|
| Experiment | 하나의 연구 질문을 검증하는 전체 단위 |
| Job | 실행하기로 계획하고 승인한 설정 |
| Run | Job을 실제로 실행한 한 번의 시도 |
| Slurm Job | Run을 수행하는 Slurm scheduler 작업 |
| Slurm Log | Slurm Job이 남긴 stdout/stderr |
| W&B Run | 같은 Run의 metric 추적 기록 |

하나의 Job은 여러 Run을 만들 수 있다.

```text
Job: train-lora-r8
├── Run 1: Slurm 123456 → OOM
├── Run 2: Slurm 123789 → 성공
└── Run 3: Slurm 124001 → 다른 seed 재현
```

## Run 디렉터리

```text
runs/train-r8__20260923T142530/
├── run.yaml
├── resolved-job.yaml
├── artifacts.yaml
├── logs/
│   ├── 20260923-142530_123456_train-lora-r8.out
│   └── 20260923-142530_123456_train-lora-r8.err
└── wandb/
```

## Slurm 로그 규칙

일반 Job:

```text
<YYYYMMDD-HHMMSS>_<job-id>_<job-name>.out
<YYYYMMDD-HHMMSS>_<job-id>_<job-name>.err
```

Slurm array:

```text
<YYYYMMDD-HHMMSS>_<array-job-id>_<task-id>_<job-name>.out
<YYYYMMDD-HHMMSS>_<array-job-id>_<task-id>_<job-name>.err
```

예:

```text
20260923-142530_123456_07_train-lora-r8.out
20260923-142530_123456_07_train-lora-r8.err
```

제출 시 Codex가 날짜를 확정하고 Slurm placeholder를 사용한다.

```bash
#SBATCH --output=.../logs/20260923-142530_%A_%a_%x.out
#SBATCH --error=.../logs/20260923-142530_%A_%a_%x.err
```

원본 로그는 기본적으로 Git에 커밋하지 않는다.

---

# 7. Main Agent

Main Agent는 루트 `AGENTS.md`로 정의한다.

별도의 `main-agent.md`가 핵심 source of truth가 되면 Codex가 항상 읽는다는 보장이 약해지므로, 반드시 지켜야 할 규칙은 `AGENTS.md`에 둔다.

## 책임

- 사용자의 연구 요청 해석
- 프로젝트 환경과 코드 확인
- 과거 연구 조사
- Research Grill
- 실험 계획과 Job 작성
- 사용자 승인 요청
- 필요한 코드 작성
- SSH/Slurm 제출
- W&B/HF 연동
- specialist subagent 호출
- 결과 통합
- 최종 commit 후보 제시

## 핵심 규칙

```markdown
# AI/ML research workflow

- Before planning a new experiment, inspect relevant prior experiments,
  project-log entries, journal entries, and Git history.
- Use the `grill-me` skill when material scientific decisions remain unresolved.
- Do not ask again for stable settings already recorded in `project-plan.md`.
- Store reproducible train and evaluation settings in YAML.
- Require Slurm for GPU and CPU-heavy jobs in configured SSH environments.
- Require explicit user approval before execution, after material changes,
  and before creating a Git commit.
- Track every execution attempt as a Run.
- Do not commit secrets, checkpoints, W&B caches, or raw Slurm logs.
- Do not mark an experiment complete until required evaluation, W&B tracking,
  Hub upload, journal, and project-log updates are verified.
```

`AGENTS.md`는 짧게 유지한다. 모든 Skill의 세부 절차를 복사해 넣지 않는다.

---

# 8. Subagent 구성

## Research Journal & Git Agent

초기부터 사용하는 핵심 subagent다.

### Discovery mode

실험 계획 전에 호출한다.

- `project-plan.md` 확인
- `project-log.md` 검색
- 관련 experiment 검색
- 관련 journal/results 검색
- Git history 검색
- 재사용 가능한 baseline/config 확인
- 이미 수행한 실험인지 판단

### Finalize mode

평가 후 호출한다.

- Job/Run/artifact 완전성 확인
- 결과와 결론의 일치 여부 확인
- `results.yaml` 작성
- `history.md` 갱신
- `journal.md` 작성
- `project-log.md` 갱신
- Git diff 검토
- commit 후보 제안

직접 commit하지 않는다.

## W&B Analyst

학습 결과를 로컬 W&B로 추적하고, web W&B 프로젝트 및 run을 관리한다.
학습 그래프 및 평가 결과 등을 분석해 main agent 및 사용자에게 insight를 제공한다. 

일반 W&B logging은 별도 Agent가 아니라 `train-llm`과 `evaluate-llm`의 일부다.

## Hugging Face Curator

다음 경우에만 호출한다.

- 여러 checkpoint 중 배포 대상을 골라야 함
- model card 작성이 복잡함
- repository/revision 정리가 필요함
- 공개 범위 검토가 필요함 (기본값은 public으로 고정)

일반 Hub push는 train/evaluate/finalize workflow 내부에서 처리한다.

## Visualization Specialist

논문·발표·보고서용 추가 시각화가 필요한 경우 선택적으로 호출한다.

## Slurm Debugger

정상적인 제출에는 호출하지 않는다.

다음 상황에서만 호출한다.

- 반복 OOM
- preemption
- dependency failure
- 환경 활성화 실패
- quota 또는 partition 문제
- node별 재현되지 않는 오류

---

# 9. Agent Description

`agent-descriptions/`는 이 프로젝트가 정의하는 관례다. Codex가 자동으로 모든 파일을 읽는다고 가정하지 않는다.

Main Agent가 specialist를 호출할 때 필요한 description만 읽는다.

```markdown
# Research Journal & Git Agent

## Mission

Find relevant prior work before planning and consolidate verified evidence
after an experiment finishes.

## Modes

- discovery
- finalize

## Allowed actions

- Read project files and Git history
- Analyze results
- Draft or update research records
- Propose a commit

## Prohibited actions

- Do not submit jobs
- Do not push checkpoints
- Do not create commits without explicit approval
- Do not claim success without verifying referenced artifacts

## Required output

- Findings
- Evidence inspected
- Proposed file changes
- Remaining risks
```

`AGENTS.md`에는 다음 routing 규칙만 둔다.

```markdown
For prior-work discovery or experiment finalization, load only
`agent-descriptions/research-journal-git.md` and delegate a bounded task
when subagent execution is useful.
```

---

# 10. Skills

## `grill-me`

기본 탑재한다.

- 한 번에 질문 하나
- 가장 중요한 미결정 사항부터 질문
- 프로젝트에 이미 기록된 안정적인 환경 정보는 재질문하지 않음
- vague answer에는 더 구체적인 후속 질문
- unknown과 decision을 구분
- baseline, metric, 성공 기준을 우선 검증
- 합의되지 않은 중요한 결정이 남아 있으면 실행 승인으로 넘어가지 않음

## `discover-prior-research`

- 관련 experiment 검색
- project log 검색
- journal/results 검색
- Git history 검색
- 유사한 baseline/config 수집
- 중복 실험 여부 판정
- Main Agent에 근거와 링크 반환

## `plan-ml-experiment`

- Grill 결과 정리
- `plan.md` 생성
- train/evaluate Job YAML 생성
- 예상 resource 계산
- W&B/HF 목적지 정리
- Agent가 선택한 기본값과 근거 기록
- 사용자 승인용 요약 생성

## `train-llm`

내부 preflight:

- 승인 상태 확인
- 프로젝트 가상환경 확인
- entrypoint 확인
- model/dataset revision 확인
- metric과 성공 기준 확인
- resource/quota 확인
- SSH/Slurm 정책 확인
- W&B/HF 설정 확인 (기본적으로는 every save, every push to hub, W&B도 기본적으로 로깅)

실행:

- Run ID 생성
- `resolved-job.yaml` 작성
- 가벼운 CPU 또는 Slurm 실행 선택
- W&B Run 연결
- 로그 경로 설정
- checkpoint 정책 적용
- `run.yaml`과 `history.md` 갱신

별도의 `check-job-details` Skill은 만들지 않는다.

## `evaluate-llm`

- 평가 Job 확인 또는 생성
- primary/secondary metric 계산
- baseline과 Run 비교
- W&B Run 비교
- 성공 기준 판정
- `results.yaml` 작성
- 필요시 W&B Analyst 호출


## `finalize-experiment`

- 필수 Run 종료 확인
- W&B 업로드 확인
- HF artifact 확인
- 누락된 결과 확인
- Research Journal & Git Agent 호출
- `history.md`, `journal.md`, `project-log.md` 갱신
- commit 후보 생성
- 사용자 승인 요청

---

# 11. Research Grill

실험 계획 전 순서:

```text
1. project-plan.md 확인
2. project-log.md 확인
3. 관련 experiment와 Git history 조사
4. 이미 결정된 사항과 미결정 사항 분리
5. 가장 중요한 질문 하나 제시
6. 답변에 따라 다음 질문 또는 기본값 제안
7. plan과 Job 작성
8. 최종 승인 요청
```

질문 대상:

- 연구 목적
- 가설
- baseline
- ablation 범위
- primary metric
- secondary metric
- 성공·실패 기준
- dataset과 split
- seed와 반복 횟수
- 비용·시간 제약
- artifact 공개 범위

다시 묻지 않을 대상:

- W&B entity
- HF namespace
- 기본 SSH host
- 기본 Slurm partition
- 기본 가상환경
- quota
- 기본 artifact 정책

위 항목은 `project-plan.md`에서 읽는다.

---

# 12. 승인 UX

사용자에게 긴 YAML을 그대로 보여주지 않는다.

승인 요청 순서:

1. **Agent의 권장안**
2. **Agent가 대신 판단한 항목**
3. **실험 목적과 가설**
4. **Primary metric과 성공 기준**
5. **예상 resource와 위험**
6. **W&B/HF 목적지**
7. **승인 또는 수정 요청**
8. **상세 plan/job 파일 경로**

예:

```text
권장안: LoRA rank 4/8/16/32를 동일 seed와 학습량으로 비교하겠습니다.

제가 결정한 사항:
- 지정되지 않은 learning rate는 현재 baseline과 동일하게 유지
- primary metric은 eval accuracy
- 동일 점수에서는 VRAM 사용량이 낮은 rank를 우선

성공 기준:
- baseline 대비 accuracy +2% 이상
- best checkpoint Hub 업로드
- 모든 Run이 같은 W&B group에 기록

예상 자원:
- GPU 1장 × 4 Run
- 각 Run 최대 8시간

승인하면 Slurm array를 제출하겠습니다.
세부 내용: experiments/lora-rank-ablation/plan.md
```

## 승인이 필요한 시점

- 첫 실험 실행 전
- 승인된 계획의 중요 변경 후
- Git commit 전

## 중요 변경

- 모델 변경
- dataset 또는 split 변경
- model/dataset revision 변경
- primary metric 변경
- 성공 기준 변경
- 학습량 증가
- GPU·시간·비용 증가
- W&B/HF 목적지 변경
- 학습 의미를 바꾸는 코드 변경

중요 변경이 발생하면 `approval.status`를 다시 `pending`으로 변경한다.

---

# 13. 실행 정책

## 가상환경

모든 train/evaluate Job은 프로젝트에 지정된 가상환경에서 실행한다.

기본값:

```text
Miniconda
```

지원:

```text
uv
venv
```

## 실행 위치

기본:

```text
SSH environment
```

정책:

| Job 종류 | 실행 방식 |
|---|---|
| 짧고 가벼운 CPU 검사 | 직접 실행 가능 |
| GPU Job | Slurm 강제 |
| CPU-heavy Job | Slurm 강제 |
| 긴 평가 Job | Slurm 권장 또는 강제 |
| 코드 syntax/unit test | 짧으면 직접 실행 가능 |

Harness가 통제하는 Codex 워크플로 안에서는 이 정책을 따라야 한다. 사용자가 직접 shell에서 실행하는 행위까지 기술적으로 차단하는 제품은 아니다.

## 프로젝트별 명령

Harness는 공통 Python command를 강제하지 않는다.

가능한 예:

```bash
conda run -n project python src/train.py --config jobs/train.yaml
```

```bash
uv run accelerate launch src/train.py --config jobs/train.yaml
```

```bash
sbatch scripts/train.slurm experiments/.../jobs/train.yaml
```

Skill은 프로젝트의 README, 기존 script, config 관례를 확인해 적합한 실행 명령을 선택한다.

---

# 14. W&B 정책

기본값:

- online mode
- W&B 웹 업로드
- experiment 단위 group
- Run별 고유 ID
- Git SHA 기록
- resolved config 기록
- local W&B data 유지

로컬 위치:

```text
experiments/<experiment-id>/runs/<run-id>/wandb/
```

Git에는 포함하지 않는다.

`run.yaml`에는 다음만 기록한다.

```yaml
wandb:
  entity: my-lab
  project: my-project
  run_id: abc123
  url: https://...
  sync_status: synced
```

Evaluate 단계에서 Run 비교가 자동으로 이루어져야 한다.

---

# 15. Hugging Face Hub 정책

기본 동작:

- 최종 checkpoint와 milestone checkpoint만 업로드
- 모든 중간 checkpoint를 무조건 올리지 않음
- repository와 revision 기록
- private/public 정책 준수
- model card 초안 생성
- 업로드 결과 검증

로컬 checkpoint:

```text
outputs/<experiment-id>/<run-id>/checkpoints/
```

Git에는 포함하지 않는다.

`artifacts.yaml`:

```yaml
artifacts:
  - type: model
    local_path: outputs/.../checkpoint-final
    hub_repo: my-lab/my-model
    revision: abcdef
    upload_status: uploaded
```

---

# 16. 연구 기록

## `history.md`

사실 중심의 실행 기록이다.

- 계획 생성
- 사용자 승인
- 코드 변경
- Job 제출
- Slurm ID
- 실패와 재시도
- 평가 완료
- W&B sync
- HF upload
- finalize
- commit 승인

## `journal.md`

해석 중심의 기록이다.

- 가설이 지지되었는가
- 어떤 Run이 가장 좋았는가
- 왜 그런 결과가 나왔는가
- limitation은 무엇인가
- 어떤 결론을 내릴 수 없는가
- 다음 실험은 무엇인가

## `project-log.md`

실험의 세부 내용을 복사하지 않는다.

프로젝트 방향에 영향을 준 결론과 링크만 기록한다.

## Hooks

v1에서는 hook 기반 자동 기록을 핵심 요구사항으로 두지 않는다.

초기에는 `train-llm`, `evaluate-llm`, `finalize-experiment` Skills가 필요한 시점에 기록한다.

워크플로가 안정된 뒤 다음을 hook 후보로 검토한다.

- Job 제출 후 history append
- Job 완료 후 Run 상태 기록
- W&B/HF 업로드 후 artifact 상태 기록
- commit 전 journal/results 누락 검사

---

# 17. Git 정책

## Git에 포함

- `AGENTS.md`
- `.agents/skills/`
- `agent-descriptions/`
- `templates/`
- `project-plan.md`
- `project-log.md`
- `environment.yaml`
- experiment `plan.md`
- `jobs/*.yaml`
- `run.yaml`
- `resolved-job.yaml`
- `artifacts.yaml`
- `results.yaml`
- `history.md`
- `journal.md`
- 최종 figure
- 연구 코드

## Git에서 제외

- secret
- token
- raw dataset
- dataset cache
- checkpoint
- W&B cache
- raw Slurm log
- 임시 output
- Python cache
- editor cache

예:

```gitignore
outputs/**
!outputs/.gitkeep

experiments/**/runs/**/logs/*.out
experiments/**/runs/**/logs/*.err
experiments/**/runs/**/wandb/

.env
*.token
__pycache__/
.ipynb_checkpoints/
```

---

# 18. 상태 모델

## Experiment 상태

```text
draft
→ grilling
→ planned
→ awaiting_approval
→ approved
→ running
→ evaluating
→ finalizing
→ completed
```

예외:

```text
failed
cancelled
blocked
```

## Run 상태

```text
created
→ submitted
→ pending
→ running
→ succeeded
```

예외:

```text
failed
cancelled
timed_out
preempted
```

Experiment와 Run의 상태를 분리한다.

---

# 19. 구현 로드맵

현재 구현 상태는 **0%**로 간주한다.

## Phase 0 — 명세 고정

산출물:

- 최종 파일 구조
- 용어 정의
- Agent/Skill/Tool 경계
- 승인 정책
- Git 정책
- Job/Run/Log 규칙
- LoRA rank ablation Golden Path

완료 기준:

- 신규 개발자가 문서만 읽고 구조를 설명할 수 있음
- Project, Experiment, Job, Run이 혼동되지 않음
- Python Harness가 범위에 포함되지 않음

## Phase 1 — GitHub Template Skeleton

구현:

- repository 생성
- `README.md`
- `AGENTS.md`
- `.gitignore`
- `environment.yaml`
- `project-plan.md`
- `project-log.md`
- 전체 폴더 구조
- 빈 template 파일

완료 기준:

- GitHub의 Use this template로 새 연구 프로젝트 생성 가능
- Codex가 루트 `AGENTS.md`를 적용
- secret과 대용량 파일이 기본적으로 제외됨

## Phase 2 — Core Skills

구현 순서:

1. `grill-me`
2. `discover-prior-research`
3. `plan-ml-experiment`
4. `train-llm`
5. `evaluate-llm`
6. `finalize-experiment`

각 Skill은 다음 구조를 사용한다.

```text
skill-name/
├── SKILL.md
├── references/
└── scripts/       # 필요한 경우에만
```

완료 기준:

- Skill description만 보고 Codex가 호출 시점을 구분
- Skill 간 책임 중복이 없음
- `check-job-details`, `compare-runs`, `publish-to-hub`가 별도 Skill로 노출되지 않음

## Phase 3 — Agent Descriptions

구현:

- Research Journal & Git Agent
- W&B Analyst
- Hugging Face Curator
- Visualization Specialist
- Slurm Debugger
- Main Agent routing 규칙

완료 기준:

- 각 Agent의 입력, 출력, 허용 행동, 금지 행동이 명확함
- 일반 API 호출과 분석용 subagent가 구분됨
- Main Agent가 모든 Agent description을 무조건 읽지 않음

## Phase 4 — Planning-only Golden Path

실제 학습을 실행하지 않고 다음을 검증한다.

```text
LoRA rank ablation 요청
→ prior research 조사
→ Grill
→ plan.md
→ train/evaluate YAML
→ 승인 요약
→ 사용자 승인 대기
```

완료 기준:

- 질문을 한 번에 하나만 함
- 기존 프로젝트 설정을 재질문하지 않음
- metric, baseline, 성공 기준이 포함됨
- Agent가 결정한 기본값이 앞부분에 요약됨
- 승인 전에는 실행하지 않음

## Phase 5 — 로컬 경량 Job

구현:

- 작은 CPU smoke test
- 프로젝트 환경 활성화
- Run ID 생성
- `resolved-job.yaml`
- `run.yaml`
- stdout/stderr
- `history.md` 갱신

완료 기준:

- 특정 Python framework에 종속되지 않음
- 프로젝트가 선언한 실행 방식을 사용
- 실패한 Run도 기록됨

## Phase 6 — SSH 및 Slurm

구현:

- SSH host 확인
- remote project path 확인
- 가상환경 확인
- Slurm script 생성
- submit/status/cancel
- array와 dependency
- retry/resume
- quota 확인
- 지정된 로그 이름 적용

완료 기준:

- GPU와 CPU-heavy Job이 직접 실행되지 않음
- Slurm Job과 Harness Run이 연결됨
- 실패, 취소, preemption이 Run에 기록됨
- 로그가 `날짜_jobid_jobname.out/.err` 규칙을 따름

## Phase 7 — W&B

구현:

- Run 생성과 resume
- group/tag
- config 기록
- Git SHA 기록
- local W&B directory
- Run 비교
- sync 상태 확인

완료 기준:

- LoRA rank Run들이 하나의 group으로 비교됨
- W&B URL과 ID가 `run.yaml`에 기록됨
- W&B 실패가 학습 실패와 구분됨

## Phase 8 — Hugging Face Hub

구현:

- repository 확인
- checkpoint 업로드
- revision 기록
- model card 초안
- upload 결과 확인
- private/public 정책

완료 기준:

- 업로드된 checkpoint를 revision으로 찾을 수 있음
- 필수 Hub upload 실패 시 Experiment를 완료 처리하지 않음

## Phase 9 — Finalize와 Git

구현:

- `results.yaml`
- `history.md`
- `journal.md`
- `project-log.md`
- Research Journal & Git Agent
- commit 후보

완료 기준:

- 결론이 실제 metric과 artifact를 참조
- project log가 experiment 세부사항을 중복 저장하지 않음
- 사용자 승인 전 commit하지 않음

## Phase 10 — Harness Evals

평가 시나리오:

- metric이 없는 요청
- baseline이 없는 요청
- 사용자가 parameter를 거의 지정하지 않은 요청
- 기존 실험과 중복되는 요청
- 승인 전 제출 유도
- 승인 후 Job 변경
- OOM 재시도
- Slurm preemption
- W&B만 실패
- HF만 실패
- 결과와 Journal 불일치
- commit 승인 누락

평가할 행동:

- 올바른 Skill 선택
- 불필요한 질문 최소화
- 승인 경계 준수
- 올바른 파일 생성
- 근거 없는 성공 선언 방지
- 적절한 subagent 호출

## Phase 11 — Release

구현:

- GitHub Template 활성화
- setup 가이드
- LoRA 예제
- 새 프로젝트 체크리스트
- contribution 가이드
- Harness version 기록
- template update 정책

완료 기준:

- 새로운 사용자가 별도 Harness 설치 없이 시작 가능
- 프로젝트 생성 후 30분 이내 첫 계획 작성 가능
- 예제 워크플로를 재현 가능

## Phase 12 — 선택적 확장

MVP 이후 검토한다.

- Codex Plugin 분리
- MCP tools
- hooks
- GitHub Actions
- W&B/HF/Slurm panel
- Experiment timeline
- approval card
- Notion/Google Drive 동기화
- Google Slides/PPT 결과 공유
- 별도 UI
- Agents API 기반 서비스

---

# 20. 첫 번째 PR 범위

첫 PR은 외부 시스템과 연결하지 않는다.

## 포함

- 최종 디렉터리 구조
- `README.md`
- `AGENTS.md`
- `.gitignore`
- `environment.yaml`
- `project-plan.md`
- `project-log.md`
- `grill-me`
- `discover-prior-research`
- `plan-ml-experiment`
- Experiment template
- Job template
- Run/result/history/journal template
- LoRA rank ablation 예제

## 제외

- 실제 SSH 접속
- 실제 Slurm 제출
- 실제 W&B 호출
- 실제 HF upload
- hooks
- Plugin
- UI

첫 PR의 성공 기준:

```text
사용자가 LoRA rank ablation을 요청했을 때
Codex가 기존 기록을 조사하고,
한 번에 하나씩 필요한 질문을 하며,
실행 가능한 plan/job을 작성하고,
간결한 승인 요청을 제시한 뒤 멈춘다.
```

---

# 21. MVP 성공 기준

MVP는 다음 시나리오를 끝까지 수행하면 성공이다.

```text
1. 사용자가 GitHub Template으로 프로젝트 생성
2. environment.yaml 또는 uv 환경 설정
3. project-plan.md 작성
4. “LoRA rank ablation을 해보자”고 요청
5. Codex가 과거 연구와 Git history 조사
6. Research Grill 수행
7. plan.md와 Job YAML 작성
8. 사용자가 승인
9. Codex가 SSH 환경에서 Slurm 제출
10. 날짜_jobid_이름 형식으로 로그 저장
11. W&B Run 비교
12. best checkpoint HF Hub 업로드
13. results/history/journal 작성
14. project-log 갱신
15. commit 후보 제안
16. 사용자 승인 후 commit
```

새 Codex 작업을 열더라도 다음 파일만 읽어 현재 상태를 복원할 수 있어야 한다.

- `project-plan.md`
- `project-log.md`
- 해당 experiment의 `plan.md`
- `jobs/`
- `runs/*/run.yaml`
- `results.yaml`
- `history.md`
- `journal.md`

---

# 22. MVP 범위 밖

- 새 IDE
- Docker 필수화
- 공통 Python Harness
- 자체 Agent Loop
- 자체 scheduler
- 자체 experiment database
- 완전 자율 연구
- 자동 Git commit
- 모든 checkpoint 자동 업로드
- 자체 W&B 대체 서비스
- 자체 Hugging Face 대체 저장소
- 자체 Slurm dashboard
- Notion/Slides 자동 동기화
- 별도 웹 애플리케이션

---

# 핵심 요약

| 항목 | 최종 결정 |
|---|---|
| v1 배포 단위 | GitHub Template 하나 |
| Codex Harness 위치 | GitHub Template 내부 |
| Main Agent | 루트 `AGENTS.md` |
| 반복 워크플로 | `.agents/skills/` |
| Subagent 역할 | `agent-descriptions/` |
| 기본 Skill | `grill-me` |
| 공통 Python Harness | 만들지 않음 |
| 프로젝트 실행 환경 | 각 프로젝트가 소유 |
| 기본 가상환경 | Miniconda |
| 기본 실행 위치 | Slurm이 설치된 SSH 환경 |
| GPU/CPU-heavy | Slurm 강제 |
| 프로젝트 계획 | `project-plan.md` |
| 프로젝트 기록 | `project-log.md` |
| Experiment 계획 | `experiments/<id>/plan.md` |
| 재현 가능한 Job | `jobs/*.yaml` |
| 실행 시도 | `runs/<run-id>/` |
| Slurm 로그 | `날짜시간_jobid_jobname.out/.err` |
| W&B | 웹 업로드 + local data |
| 모델 Artifact | Hugging Face Hub |
| 사용자 승인 | 실행 전, 중요 변경 후, commit 전 |
| Hooks | MVP 이후 |
| Plugin | 여러 프로젝트 업데이트가 필요해질 때 |
| 첫 구현 목표 | Planning-only LoRA rank ablation Golden Path |
```