"""Static repository contracts for the Phase 4 planning-only Golden Path.

These tests inspect documentation, templates, fixtures, spec traceability, and the
local Git delta. They do not execute a research workflow or contact services.

Validates: Requirements 9.3, 10.1, 10.2, 10.4, 10.5
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
PLANNING_ASSETS = SKILLS / "plan-ml-experiment" / "assets"
TEMPLATES = ROOT / "templates"
SPEC = ROOT / ".kiro" / "specs" / "phase-4-planning-golden-path"
GUARDS = ROOT / "tests" / "fixtures" / "phase4-planning-golden-path" / "guards"

EXPECTED_GUARDS = {
    "guard-bundled-questions",
    "guard-escaped-write",
    "guard-forbidden-command",
    "guard-huggingface-attempt",
    "guard-nondeterministic-dependency",
    "guard-preapproval-execution-request",
    "guard-run-creation",
    "guard-slurm-attempt",
    "guard-ssh-attempt",
    "guard-stable-setting-reask",
    "guard-unresolved-baseline",
    "guard-unresolved-placeholder",
    "guard-unresolved-primary-metric",
    "guard-unresolved-success-criteria",
    "guard-unsupported-baseline",
    "guard-unsupported-finding",
    "guard-wandb-attempt",
}

PLAN_REQUIRED_PATHS = {
    "schema_version",
    "experiment_id",
    "status",
    "primary_metric.name",
    "primary_metric.direction",
    "success_criteria.metric",
    "success_criteria.comparison",
    "success_criteria.operator",
    "success_criteria.threshold",
    "baseline.name",
    "baseline.metric.name",
    "baseline.metric.value",
    "baseline.metric.direction",
    "baseline.evaluation.dataset",
    "baseline.evaluation.split",
    "baseline.source",
    "jobs",
    "approval.status",
    "approval.approved_by",
    "approval.approved_at",
    "approval.approved_commit",
}

COMMON_JOB_REQUIRED_PATHS = {
    "job_id",
    "type",
    "entrypoint",
    "config_style",
    "parameters.dataset_name",
    "parameters.dataset_split",
    "resources.backend",
    "resources.status",
    "resources.available_phase",
    "resources.gpus",
    "resources.cpus",
    "resources.memory_gb",
    "resources.time",
    "wandb.enabled",
    "wandb.status",
    "wandb.available_phase",
    "wandb.entity",
    "wandb.project",
    "wandb.group",
    "huggingface.push",
    "huggingface.status",
    "huggingface.available_phase",
    "huggingface.namespace",
    "huggingface.repo",
    "huggingface.private",
    "provenance.resources.origin",
    "provenance.resources.source",
    "provenance.wandb.origin",
    "provenance.wandb.source",
    "provenance.huggingface.origin",
    "provenance.huggingface.source",
}

TRAIN_REQUIRED_PATHS = COMMON_JOB_REQUIRED_PATHS | {
    "matrix.lora_rank",
    "parameters.model_name",
    "parameters.learning_rate",
    "parameters.num_epochs",
    "parameters.batch_size",
    "parameters.gradient_accumulation_steps",
    "parameters.seed",
    "provenance.matrix.lora_rank.origin",
    "provenance.matrix.lora_rank.source",
    "provenance.controlled_parameters.origin",
    "provenance.controlled_parameters.source",
}

EVALUATE_REQUIRED_PATHS = COMMON_JOB_REQUIRED_PATHS | {
    "parameters.checkpoint",
    "parameters.checkpoint_resolution",
    "parameters.primary_metric",
    "parameters.secondary_metrics",
    "provenance.parameters.checkpoint_resolution.origin",
    "provenance.parameters.checkpoint_resolution.source",
    "provenance.parameters.primary_metric.origin",
    "provenance.parameters.primary_metric.source",
    "provenance.secondary_metrics.origin",
    "provenance.secondary_metrics.source",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(path: Path) -> Mapping[str, Any]:
    text = _read(path)
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    end = text.find("\n---\n", 4)
    assert end >= 0, f"{path} must close YAML frontmatter"
    value = yaml.safe_load(text[4:end])
    assert isinstance(value, Mapping), f"{path} frontmatter must be a mapping"
    return value


def _yaml_mapping(path: Path) -> Mapping[str, Any]:
    value = yaml.safe_load(_read(path))
    assert isinstance(value, Mapping), f"{path} must contain a YAML mapping"
    return value


def _contains_path(current: Any, components: tuple[str, ...]) -> bool:
    """Resolve nested fields while allowing literal dotted YAML keys."""
    if not components:
        return True
    if not isinstance(current, Mapping):
        return False
    for width in range(len(components), 0, -1):
        key = ".".join(components[:width])
        if key in current and _contains_path(current[key], components[width:]):
            return True
    return False


def _assert_paths(document: Mapping[str, Any], required: set[str], source: Path) -> None:
    missing = [
        dotted_path
        for dotted_path in sorted(required)
        if not _contains_path(document, tuple(dotted_path.split(".")))
    ]
    assert not missing, f"{source} is missing required fields: {missing}"


def _git_delta() -> set[Path]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "-uall"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: set[Path] = set()
    for line in completed.stdout.splitlines():
        raw = line[3:]
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.add(Path(raw.strip('"')))
    return paths


def test_planning_skills_keep_distinct_handoff_responsibilities() -> None:
    """Discovery reads, grill resolves, and planning writes reviewable artifacts."""
    discovery = _read(SKILLS / "discover-prior-research" / "SKILL.md")
    grill = _read(SKILLS / "grill-me" / "SKILL.md")
    planning = _read(SKILLS / "plan-ml-experiment" / "SKILL.md")

    assert "This skill is read/synthesis-only" in discovery
    assert "does not choose a final experimental design" in discovery
    assert "must not choose the value or create a plan" in discovery
    assert "Surface conflicts and unresolved scientific decisions for the Research Grill" in discovery

    assert "Resolve consequential scientific choices through focused questioning" in grill
    assert "every assistant turn MUST contain exactly one structured `Material_Decision`" in grill
    assert "does not design implementation details, create planning artifacts" in grill
    assert "Return the completed decision ledger to `plan-ml-experiment`" in grill

    assert "Create reviewable experiment plans and reproducible training/evaluation job configurations" in planning
    assert "`discover-prior-research` produced" in planning
    assert "`grill-me` resolved" in planning
    assert "Create exactly the training and evaluation jobs referenced by the plan" in planning
    assert "Stop and wait for explicit user approval" in planning


def test_root_and_skill_templates_are_synchronized_and_complete() -> None:
    """Duplicate plan/train/evaluate templates remain byte-identical and complete."""
    pairs = {
        "experiment-plan.md": PLAN_REQUIRED_PATHS,
        "train-job.yaml": TRAIN_REQUIRED_PATHS,
        "evaluate-job.yaml": EVALUATE_REQUIRED_PATHS,
    }

    for name, required_paths in pairs.items():
        root_template = TEMPLATES / name
        skill_template = PLANNING_ASSETS / name
        assert _read(root_template) == _read(skill_template), f"template drift: {name}"
        document = _frontmatter(root_template) if name.endswith(".md") else _yaml_mapping(root_template)
        _assert_paths(document, required_paths, root_template)

    train = _yaml_mapping(TEMPLATES / "train-job.yaml")
    evaluate = _yaml_mapping(TEMPLATES / "evaluate-job.yaml")
    assert train["type"] == "train"
    assert evaluate["type"] == "evaluate"
    assert train["resources"]["available_phase"] == evaluate["resources"]["available_phase"] == 6
    assert train["wandb"]["available_phase"] == evaluate["wandb"]["available_phase"] == 7
    assert train["huggingface"]["available_phase"] == evaluate["huggingface"]["available_phase"] == 8


def test_agent_defaults_are_front_loaded() -> None:
    """Defaults precede detailed design/risks in plans and approval guidance."""
    for path in (TEMPLATES / "experiment-plan.md", PLANNING_ASSETS / "experiment-plan.md"):
        text = _read(path)
        defaults = text.index("## Agent-Determined Defaults")
        assert defaults < text.index("## Design")
        assert defaults < text.index("## Risks and Limitations")

    planning = _read(SKILLS / "plan-ml-experiment" / "SKILL.md")
    summary_rule = planning[planning.index("8. **Present the terminal Approval Summary**") :]
    assert summary_rule.index("recommended plan") < summary_rule.index("Agent-Determined Defaults")
    assert summary_rule.index("Agent-Determined Defaults") < summary_rule.index("objective and hypothesis")


def test_guard_fixture_inventory_is_exact_and_traceable() -> None:
    """All 17 focused guard scenarios declare stable diagnostic expectations."""
    guard_files = sorted(GUARDS.glob("*.yaml"))
    assert len(guard_files) == 17

    documents = [_yaml_mapping(path) for path in guard_files]
    scenario_ids = {str(document.get("scenario_id")) for document in documents}
    assert scenario_ids == EXPECTED_GUARDS

    for path, document in zip(guard_files, documents):
        assert document.get("base") == "../golden", path
        assert isinstance(document.get("mutation"), Mapping), path
        failure = document.get("expected_failure")
        assert isinstance(failure, Mapping), path
        assert re.fullmatch(r"\d+\.\d+", str(failure.get("requirement"))), path
        assert re.fullmatch(r"[A-Z][A-Z0-9_]+", str(failure.get("code"))), path
        assert isinstance(failure.get("location"), str) and failure["location"], path


def test_every_phase4_implementation_leaf_task_has_requirement_references() -> None:
    """Every decimal-numbered implementation leaf maps to acceptance criteria."""
    text = _read(SPEC / "tasks.md")
    matches = list(re.finditer(r"^  - \[[^\]]+\]\*? (\d+\.\d+)\s+.+$", text, re.MULTILINE))
    assert matches, "no Phase 4 implementation leaf tasks found"

    missing: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else text.index("\n- [", match.end())
        block = text[match.start() : end]
        if not re.search(
            r"(?:_Requirements:|\*\*Validates: Requirements) "
            r"\d+\.\d+(?:, \d+\.\d+)*",
            block,
        ):
            missing.append(match.group(1))
    assert not missing, f"leaf tasks missing requirement references: {missing}"


def test_phase4_delta_stays_in_allowed_paths_without_runtime_artifacts() -> None:
    """Phase 4 remains test/documentation-only and introduces no execution residue."""
    delta = _git_delta()
    # Hypothesis' local example database is generated test cache, not implementation.
    implementation_delta = {path for path in delta if path.parts[:1] != (".hypothesis",)}
    allowed_prefixes = (
        Path(".agents/skills"),
        Path("templates"),
        Path("tests"),
        Path(".kiro/specs"),
    )
    outside = sorted(
        str(path)
        for path in implementation_delta
        if not any(path == prefix or prefix in path.parents for prefix in allowed_prefixes)
    )
    assert not outside, f"Phase 4 changed files outside allowed paths: {outside}"

    prohibited: list[str] = []
    checkpoint_suffixes = {".ckpt", ".pt", ".pth", ".safetensors", ".bin"}
    for path in implementation_delta:
        lowered_parts = tuple(part.lower() for part in path.parts)
        lowered_name = path.name.lower().replace("-", "_")
        if "runs" in lowered_parts:
            prohibited.append(str(path))
        if path.suffix.lower() in checkpoint_suffixes:
            prohibited.append(str(path))
        if "wandb" in lowered_parts or path.name in {"wandb-debug.log", "wandb-summary.json"}:
            prohibited.append(str(path))
        if path.suffix.lower() in {".out", ".err"}:
            prohibited.append(str(path))
        helper_scripts = Path(".agents/skills/train-llm/scripts")
        is_helper = helper_scripts in path.parents
        if path.suffix == ".py" and path.parts[:1] != ("tests",) and not is_helper:
            prohibited.append(str(path))
        if any(token in lowered_name for token in ("experiment_runner", "research_runner", "agent_loop")):
            prohibited.append(str(path))

    assert not prohibited, f"prohibited Phase 4 runtime additions: {sorted(set(prohibited))}"
