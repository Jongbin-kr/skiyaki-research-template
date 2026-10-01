"""Pure, test-only validation for Phase 4 planning artifacts.

The module parses an experiment plan, train/evaluate job YAML, and an approval
summary.  It performs no writes, subprocess calls, execution, or external
requests.  Public validators accept either already-loaded values (convenient
for property tests) or repository-local paths (convenient for scenario tests).
"""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import math
import re
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

import yaml

try:  # Package import under pytest and direct namespace-package loading.
    from .phase4_models import Diagnostic, ValidationResult
except ImportError:  # Compatibility for callers that add tests/helpers to sys.path.
    from phase4_models import Diagnostic, ValidationResult


DocumentSource = Union[str, Path, Mapping[str, Any]]
TextSource = Union[str, Path]

_REQUIRED_PLAN_KEYS = (
    "schema_version", "experiment_id", "status", "primary_metric",
    "success_criteria", "baseline", "jobs", "approval",
)
_REQUIRED_JOB_KEYS = ("job_id", "type", "entrypoint", "parameters", "resources")
_REQUIRED_PLAN_HEADINGS = (
    "agent-determined defaults", "decision provenance", "purpose", "hypothesis",
    "evidence-backed baseline", "design", "variables", "controls", "rationale",
    "risks and limitations", "expected outcomes", "if hypothesis supported",
    "if hypothesis refuted",
)
_ORIGINS = frozenset({"user", "project_setting", "prior_evidence", "agent_default"})
_SECRET_KEYS = re.compile(
    r"(?:^|[_-])(token|password|passwd|api[_-]?key|private[_-]?key|client[_-]?secret|access[_-]?key|secret)(?:$|[_-])",
    re.IGNORECASE,
)
_SECRET_VALUES = re.compile(
    r"(?:\bhf_[A-Za-z0-9]{8,}\b|\bsk-[A-Za-z0-9_-]{12,}\b|"
    r"\bAKIA[0-9A-Z]{16}\b|\bgh[opusr]_[A-Za-z0-9]{20,}\b|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
_ANGLE_PLACEHOLDER = re.compile(r"<[^>\n]+>")
_BRACKET_PLACEHOLDER = re.compile(
    r"\[(?:describe|state|specify|list|add|insert|replace|choose|enter|todo)\b[^]\n]*\]",
    re.IGNORECASE,
)
_SENTINEL_PLACEHOLDER = re.compile(
    r"^(?:TODO|TBD|REPLACE_ME|FIXME|CHANGEME|YOUR[_-].*|fixture[_-]?sentinel)$",
    re.IGNORECASE,
)
_KEBAB_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_TABLE_DIVIDER = re.compile(r"^:?-{3,}:?$")


@dataclass(frozen=True)
class ParsedPlan:
    """Parsed YAML frontmatter, Markdown body, and ordered headings."""

    frontmatter: Mapping[str, Any]
    body: str
    headings: tuple[str, ...]


@dataclass(frozen=True)
class ResourceEstimate:
    """Deterministic upper-bound arithmetic derived from job requests."""

    train_runs: int
    evaluate_runs: int
    total_runs: int
    train_gpu_hours: float
    evaluate_gpu_hours: float
    total_gpu_hours: float


class ArtifactParseError(ValueError):
    """Raised by public parsers when an artifact cannot be interpreted safely."""


def _read_text(source: TextSource) -> str:
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    return source


def _location(source: object, fallback: str) -> str:
    if isinstance(source, Path):
        parts = source.as_posix().split("/")
        if "experiments" in parts:
            return "/".join(parts[parts.index("experiments"):])
        if "expected" in parts:
            return "/".join(parts[parts.index("expected"):])
        return source.name
    return fallback


def _heading_name(value: str) -> str:
    value = re.sub(r"[`*_]", "", value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def parse_markdown_headings(markdown: str) -> tuple[str, ...]:
    """Return normalized Markdown ATX headings in document order."""
    return tuple(_heading_name(match.group(2)) for match in _HEADING.finditer(markdown))


def parse_plan(source: TextSource) -> ParsedPlan:
    """Parse plan YAML frontmatter and ordered Markdown headings."""
    text = _read_text(source).replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n"):
        raise ArtifactParseError("plan must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ArtifactParseError("plan frontmatter closing delimiter is missing")
    try:
        frontmatter = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        raise ArtifactParseError("plan frontmatter is invalid YAML") from exc
    if not isinstance(frontmatter, Mapping):
        raise ArtifactParseError("plan frontmatter must be a mapping")
    body = text[end + 5:]
    return ParsedPlan(dict(frontmatter), body, parse_markdown_headings(body))


def parse_yaml_document(source: DocumentSource) -> Mapping[str, Any]:
    """Return a safe, shallow-copied YAML mapping."""
    if isinstance(source, Mapping):
        return dict(source)
    text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ArtifactParseError("artifact is invalid YAML") from exc
    if not isinstance(value, Mapping):
        raise ArtifactParseError("artifact YAML must be a mapping")
    return dict(value)


def _diag(
    scenario_id: str, requirement: str, code: str, location: str, message: str
) -> Diagnostic:
    return Diagnostic(scenario_id, requirement, code, location, message)


def _walk(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _walk(child, child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return bool(
        _ANGLE_PLACEHOLDER.search(stripped)
        or _BRACKET_PLACEHOLDER.search(stripped)
        or _SENTINEL_PLACEHOLDER.fullmatch(stripped)
    )


def _content_diagnostics(
    value: Any,
    *,
    scenario_id: str,
    location: str,
    placeholder_code: str,
    requirement: str,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for path, item in _walk(value):
        leaf = path.rsplit(".", 1)[-1].split("[", 1)[0]
        if path and _SECRET_KEYS.search(leaf):
            diagnostics.append(_diag(
                scenario_id, "6.7", "JOB_SECRET_DETECTED", f"{location}:{path}",
                "Secret-like field is not allowed; value=<redacted>.",
            ))
        elif isinstance(item, str) and _SECRET_VALUES.search(item):
            diagnostics.append(_diag(
                scenario_id, "6.7", "JOB_SECRET_DETECTED", f"{location}:{path}",
                "Secret-like value is not allowed; value=<redacted>.",
            ))
        if _placeholder(item):
            diagnostics.append(_diag(
                scenario_id, requirement, placeholder_code, f"{location}:{path or 'body'}",
                "Required placeholder remains unresolved.",
            ))
    return diagnostics


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _required_keys(
    document: Mapping[str, Any], keys: Sequence[str], *, scenario_id: str,
    requirement: str, code: str, location: str,
) -> list[Diagnostic]:
    return [
        _diag(scenario_id, requirement, code, f"{location}:{key}", f"Missing required key '{key}'.")
        for key in keys if key not in document
    ]


def _markdown_tables(markdown: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(_TABLE_DIVIDER.fullmatch(cell) for cell in cells):
                continue
            current.append(cells)
        elif current:
            if len(current) >= 2:
                tables.append(current)
            current = []
    if len(current) >= 2:
        tables.append(current)
    return tables


def _section(markdown: str, heading: str) -> str:
    matches = list(_HEADING.finditer(markdown))
    wanted = _heading_name(heading)
    for index, match in enumerate(matches):
        if _heading_name(match.group(2)) != wanted:
            continue
        level = len(match.group(1))
        end = len(markdown)
        for later in matches[index + 1:]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        return markdown[match.end():end].strip()
    return ""


def validate_plan(
    plan: Union[ParsedPlan, TextSource], *, scenario_id: str = "phase4",
    location: Optional[str] = None,
) -> ValidationResult:
    """Validate plan schema, review order, placeholders, and provenance."""
    loc = location or _location(plan, "plan.md")
    try:
        parsed = plan if isinstance(plan, ParsedPlan) else parse_plan(plan)
    except (ArtifactParseError, OSError) as exc:
        return ValidationResult.from_diagnostics([_diag(
            scenario_id, "5.1", "PLAN_PARSE_INVALID", loc, str(exc)
        )])

    fm, body = parsed.frontmatter, parsed.body
    diagnostics = _required_keys(
        fm, _REQUIRED_PLAN_KEYS, scenario_id=scenario_id, requirement="5.1",
        code="PLAN_REQUIRED_KEY_MISSING", location=loc,
    )
    diagnostics.extend(_content_diagnostics(
        fm, scenario_id=scenario_id, location=loc,
        placeholder_code="PLAN_PLACEHOLDER_UNRESOLVED", requirement="5.5",
    ))
    for path, item in _walk(body):
        if _placeholder(item):
            diagnostics.append(_diag(
                scenario_id, "5.5", "PLAN_PLACEHOLDER_UNRESOLVED", f"{loc}:body",
                "Required placeholder remains unresolved.",
            ))
            break

    experiment_id = fm.get("experiment_id")
    if fm.get("schema_version") != 1:
        diagnostics.append(_diag(scenario_id, "5.1", "PLAN_SCHEMA_INVALID", f"{loc}:schema_version", "Schema version must equal 1."))
    if not isinstance(experiment_id, str) or not _KEBAB_ID.fullmatch(experiment_id):
        diagnostics.append(_diag(scenario_id, "5.1", "PLAN_EXPERIMENT_ID_INVALID", f"{loc}:experiment_id", "Experiment identifier must use kebab-case."))
    if fm.get("status") != "awaiting_approval":
        diagnostics.append(_diag(scenario_id, "5.1", "PLAN_STATUS_INVALID", f"{loc}:status", "Phase 4 plan status must be awaiting_approval."))

    approval = _mapping(fm.get("approval"))
    if approval.get("status") != "pending" or any(
        approval.get(key) is not None for key in ("approved_by", "approved_at", "approved_commit")
    ):
        diagnostics.append(_diag(scenario_id, "5.1", "PLAN_APPROVAL_NOT_PENDING", f"{loc}:approval", "Approval must be pending with null identity, timestamp, and commit."))

    metric = _mapping(fm.get("primary_metric"))
    if not isinstance(metric.get("name"), str) or metric.get("direction") not in {"maximize", "minimize"}:
        diagnostics.append(_diag(scenario_id, "5.1", "PLAN_PRIMARY_METRIC_INVALID", f"{loc}:primary_metric", "Primary metric needs a name and maximize/minimize direction."))
    criteria = _mapping(fm.get("success_criteria"))
    if (
        criteria.get("metric") != metric.get("name")
        or criteria.get("operator") not in {"gte", "lte"}
        or not _number(criteria.get("threshold"))
        or not isinstance(criteria.get("comparison"), str)
    ):
        diagnostics.append(_diag(scenario_id, "5.1", "PLAN_SUCCESS_CRITERIA_INVALID", f"{loc}:success_criteria", "Success criteria must be measurable and match the primary metric."))

    baseline = _mapping(fm.get("baseline"))
    baseline_metric = _mapping(baseline.get("metric"))
    evaluation = _mapping(baseline.get("evaluation"))
    if (
        baseline_metric.get("name") != metric.get("name")
        or baseline_metric.get("direction") != metric.get("direction")
        or not _number(baseline_metric.get("value"))
        or not all(isinstance(evaluation.get(k), str) and evaluation.get(k) for k in ("dataset", "split"))
        or not isinstance(baseline.get("source"), str) or not baseline.get("source")
    ):
        diagnostics.append(_diag(scenario_id, "5.4", "PLAN_BASELINE_INVALID", f"{loc}:baseline", "Baseline must align on metric/direction and include numeric value, dataset, split, and source."))

    jobs = fm.get("jobs")
    expected_jobs = ("jobs/train.yaml", "jobs/evaluate.yaml")
    if not isinstance(jobs, list) or tuple(jobs) != expected_jobs:
        diagnostics.append(_diag(scenario_id, "5.1", "PLAN_JOB_PATHS_INVALID", f"{loc}:jobs", "Plan must reference jobs/train.yaml then jobs/evaluate.yaml exactly."))
    elif any(PurePosixPath(job).is_absolute() or ".." in PurePosixPath(job).parts for job in jobs):
        diagnostics.append(_diag(scenario_id, "5.1", "PLAN_JOB_PATHS_INVALID", f"{loc}:jobs", "Job paths must remain relative to the experiment."))

    headings = parsed.headings
    for required in _REQUIRED_PLAN_HEADINGS:
        if required not in headings:
            diagnostics.append(_diag(scenario_id, "5.2", "PLAN_SECTION_MISSING", f"{loc}:heading:{required}", f"Required heading '{required}' is missing."))
    positions = {heading: headings.index(heading) for heading in set(headings)}
    defaults_pos = positions.get("agent-determined defaults", 10**6)
    if defaults_pos > min(positions.get("design", 10**6), positions.get("risks and limitations", 10**6)):
        diagnostics.append(_diag(scenario_id, "4.3", "PLAN_DEFAULTS_ORDER_INVALID", f"{loc}:heading:agent-determined-defaults", "Agent-Determined Defaults must precede Design and Risks and Limitations."))

    defaults = _section(body, "agent-determined defaults")
    provenance = _section(body, "decision provenance")
    default_rows = _markdown_tables(defaults)
    provenance_rows = _markdown_tables(provenance)
    if not default_rows:
        diagnostics.append(_diag(scenario_id, "4.2", "PLAN_DEFAULT_PROVENANCE_INVALID", f"{loc}:agent-determined-defaults", "Defaults require value, rationale, and evidence or explicit assumption."))
    else:
        for row in default_rows[0][1:]:
            if len(row) < 4 or not all(cell.strip() for cell in row[:4]) or (
                "assumption" not in row[3].lower() and not re.search(r"(?:/|\.ya?ml|\.md|\b[0-9a-f]{7,40}\b)", row[3], re.I)
            ):
                diagnostics.append(_diag(scenario_id, "4.2", "PLAN_DEFAULT_PROVENANCE_INVALID", f"{loc}:agent-determined-defaults", "Each Agent Default needs a rationale and evidence source or explicit assumption."))
                break
    if not provenance_rows:
        diagnostics.append(_diag(scenario_id, "4.4", "PLAN_DECISION_PROVENANCE_INVALID", f"{loc}:decision-provenance", "Decision Provenance table is missing."))
    else:
        rows = provenance_rows[0][1:]
        row_map = {row[0].strip(): row for row in rows if len(row) >= 4}
        for key in ("research_objective", "baseline", "primary_metric", "success_criteria", "ablation_scope", "controlled_parameters"):
            row = row_map.get(key)
            if row is None or row[2].strip() not in _ORIGINS or not row[1].strip() or not row[3].strip():
                diagnostics.append(_diag(scenario_id, "4.4", "PLAN_DECISION_PROVENANCE_INVALID", f"{loc}:decision-provenance:{key}", f"Decision '{key}' needs value, valid origin, and source."))
        default_names = {row[0].strip() for row in default_rows[0][1:]} if default_rows else set()
        mislabeled = [key for key, row in row_map.items() if row[2].strip() == "project_setting" and key in default_names]
        if mislabeled:
            diagnostics.append(_diag(scenario_id, "4.4", "PLAN_PROJECT_SETTING_AS_DEFAULT", f"{loc}:agent-determined-defaults", "Inherited Project Settings must not be listed as Agent Defaults."))

    if not re.search(r"(?:experiments/[^\s)`]+|\b[0-9a-f]{7,40}\b)", body, re.I):
        diagnostics.append(_diag(scenario_id, "5.3", "PLAN_EVIDENCE_REFERENCE_MISSING", f"{loc}:body", "Plan narrative must cite a repository path or Git commit."))
    return ValidationResult.from_diagnostics(diagnostics)


def _time_hours(value: Any) -> Optional[float]:
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,3}:\d{2}:\d{2}", value):
        return None
    hours, minutes, seconds = (int(part) for part in value.split(":"))
    if minutes > 59 or seconds > 59:
        return None
    return hours + minutes / 60.0 + seconds / 3600.0


def matrix_cardinality(matrix: Any) -> int:
    """Return the Cartesian cardinality of a job matrix (one when empty)."""
    if matrix in (None, {}):
        return 1
    if not isinstance(matrix, Mapping):
        return 0
    cardinality = 1
    for values in matrix.values():
        if not isinstance(values, (list, tuple)) or not values:
            return 0
        cardinality *= len(values)
    return cardinality


def calculate_resource_estimate(
    train_job: Mapping[str, Any], evaluate_job: Mapping[str, Any]
) -> ResourceEstimate:
    """Calculate planned run count and requested GPU-hour upper bounds.

    Evaluation defaults to one run.  A fixture can explicitly provide an
    evaluation matrix when each training combination is evaluated separately.
    """
    train_runs = matrix_cardinality(train_job.get("matrix"))
    evaluate_runs = matrix_cardinality(evaluate_job.get("matrix"))
    train_resources = _mapping(train_job.get("resources"))
    eval_resources = _mapping(evaluate_job.get("resources"))
    train_hours = _time_hours(train_resources.get("time")) or 0.0
    eval_hours = _time_hours(eval_resources.get("time")) or 0.0
    train_gpu_hours = train_runs * train_hours * (train_resources.get("gpus") or 0)
    eval_gpu_hours = evaluate_runs * eval_hours * (eval_resources.get("gpus") or 0)
    return ResourceEstimate(
        train_runs, evaluate_runs, train_runs + evaluate_runs,
        train_gpu_hours, eval_gpu_hours, train_gpu_hours + eval_gpu_hours,
    )


def _phase_metadata_diagnostics(
    section: Mapping[str, Any], *, phase: int, name: str, scenario_id: str,
    location: str, requirement: str,
) -> list[Diagnostic]:
    if section.get("status") != "planned_unverified" or section.get("available_phase") != phase:
        return [_diag(
            scenario_id, requirement, "JOB_PHASE_LABEL_INVALID", f"{location}:{name}",
            f"{name} must be planned_unverified and unavailable until Phase {phase}.",
        )]
    return []


def validate_jobs(
    train_job: DocumentSource,
    evaluate_job: DocumentSource,
    *,
    plan: Optional[Union[ParsedPlan, TextSource]] = None,
    scenario_id: str = "phase4",
    train_location: Optional[str] = None,
    evaluate_location: Optional[str] = None,
    project_settings: Optional[Mapping[str, Any]] = None,
) -> ValidationResult:
    """Validate job schemas and plan/train/evaluate cross-file semantics."""
    train_loc = train_location or _location(train_job, "jobs/train.yaml")
    eval_loc = evaluate_location or _location(evaluate_job, "jobs/evaluate.yaml")
    diagnostics: list[Diagnostic] = []
    try:
        train = parse_yaml_document(train_job)
    except (ArtifactParseError, OSError) as exc:
        diagnostics.append(_diag(scenario_id, "6.2", "JOB_YAML_INVALID", train_loc, str(exc)))
        train = {}
    try:
        evaluate = parse_yaml_document(evaluate_job)
    except (ArtifactParseError, OSError) as exc:
        diagnostics.append(_diag(scenario_id, "6.3", "JOB_YAML_INVALID", eval_loc, str(exc)))
        evaluate = {}
    if not train or not evaluate:
        return ValidationResult.from_diagnostics(diagnostics)

    for document, loc, expected_type, requirement in (
        (train, train_loc, "train", "6.2"), (evaluate, eval_loc, "evaluate", "6.3")
    ):
        diagnostics.extend(_required_keys(
            document, _REQUIRED_JOB_KEYS, scenario_id=scenario_id, requirement=requirement,
            code="JOB_REQUIRED_KEY_MISSING", location=loc,
        ))
        diagnostics.extend(_content_diagnostics(
            document, scenario_id=scenario_id, location=loc,
            placeholder_code="JOB_PLACEHOLDER_UNRESOLVED", requirement="6.7",
        ))
        if document.get("type") != expected_type:
            diagnostics.append(_diag(scenario_id, requirement, "JOB_TYPE_INVALID", f"{loc}:type", f"Job type must be '{expected_type}'."))
        if not isinstance(document.get("entrypoint"), str) or not document.get("entrypoint"):
            diagnostics.append(_diag(scenario_id, requirement, "JOB_ENTRYPOINT_INVALID", f"{loc}:entrypoint", "Job entrypoint must be a non-empty path."))
        resources = _mapping(document.get("resources"))
        for key in ("backend", "gpus", "cpus", "memory_gb", "time"):
            if key not in resources:
                diagnostics.append(_diag(scenario_id, requirement, "JOB_RESOURCE_INVALID", f"{loc}:resources.{key}", f"Resource key '{key}' is required."))
        if any(not isinstance(resources.get(key), int) or isinstance(resources.get(key), bool) or resources.get(key) < 0 for key in ("gpus", "cpus", "memory_gb")) or _time_hours(resources.get("time")) is None:
            diagnostics.append(_diag(scenario_id, requirement, "JOB_RESOURCE_INVALID", f"{loc}:resources", "Resources need non-negative integer GPU/CPU/memory values and HH:MM:SS time."))
        provenance = _mapping(document.get("provenance"))
        if not provenance:
            diagnostics.append(_diag(scenario_id, "4.4", "JOB_PROVENANCE_MISSING", f"{loc}:provenance", "Job value origins must be recorded."))
        else:
            for key, record in provenance.items():
                record = _mapping(record)
                origin = record.get("origin")
                valid = origin in _ORIGINS
                if origin == "agent_default":
                    valid = valid and bool(record.get("rationale")) and bool(
                        record.get("evidence") or record.get("assumption") is True
                    )
                else:
                    valid = valid and bool(record.get("source"))
                if not valid:
                    diagnostics.append(_diag(scenario_id, "4.4", "JOB_PROVENANCE_INVALID", f"{loc}:provenance.{key}", "Provenance needs a valid origin and source, or agent-default rationale plus evidence/assumption."))

    train_params = _mapping(train.get("parameters"))
    eval_params = _mapping(evaluate.get("parameters"))
    matrix = _mapping(train.get("matrix"))
    ranks = matrix.get("lora_rank")
    if not isinstance(ranks, list) or not ranks or any(not isinstance(rank, int) or isinstance(rank, bool) or rank <= 0 for rank in ranks) or len(set(ranks)) != len(ranks):
        diagnostics.append(_diag(scenario_id, "6.2", "JOB_MATRIX_INVALID", f"{train_loc}:matrix.lora_rank", "LoRA rank matrix must contain unique positive integers."))
    required_train_parameters = (
        "model_name", "dataset_name", "dataset_split", "learning_rate",
        "num_epochs", "batch_size", "gradient_accumulation_steps",
    )
    seed_declared = "seed" in train_params or "seed" in matrix
    if not all(key in train_params for key in required_train_parameters) or not seed_declared:
        diagnostics.append(_diag(scenario_id, "6.2", "JOB_CONTROL_MISSING", f"{train_loc}:parameters", "Training model, data, controlled hyperparameters, and seed are required."))
    if not all(key in eval_params for key in ("checkpoint_resolution", "dataset_name", "dataset_split", "primary_metric", "secondary_metrics")):
        diagnostics.append(_diag(scenario_id, "6.3", "JOB_EVALUATION_FIELD_MISSING", f"{eval_loc}:parameters", "Evaluation checkpoint intent, data, and metrics are required."))
    if eval_params.get("checkpoint_resolution") in (None, ""):
        diagnostics.append(_diag(scenario_id, "6.3", "JOB_CHECKPOINT_INTENT_INVALID", f"{eval_loc}:parameters.checkpoint_resolution", "Checkpoint resolution intent must be explicit."))

    parsed_plan: Optional[ParsedPlan] = None
    if plan is not None:
        try:
            parsed_plan = plan if isinstance(plan, ParsedPlan) else parse_plan(plan)
        except (ArtifactParseError, OSError) as exc:
            diagnostics.append(_diag(scenario_id, "5.1", "PLAN_PARSE_INVALID", _location(plan, "plan.md"), str(exc)))
    if parsed_plan:
        fm = parsed_plan.frontmatter
        experiment_id = fm.get("experiment_id")
        plan_metric = _mapping(fm.get("primary_metric")).get("name")
        baseline_eval = _mapping(_mapping(fm.get("baseline")).get("evaluation"))
        plan_dataset = baseline_eval.get("dataset")
        plan_split = baseline_eval.get("split")
        train_dataset = train_params.get("dataset_name")
        if train_params.get("dataset_config"):
            train_dataset = f"{train_dataset}/{train_params['dataset_config']}"
        eval_dataset = eval_params.get("dataset_name")
        if eval_params.get("dataset_config"):
            eval_dataset = f"{eval_dataset}/{eval_params['dataset_config']}"
        if eval_params.get("primary_metric") != plan_metric:
            diagnostics.append(_diag(scenario_id, "6.3", "JOB_METRIC_MISMATCH", f"{eval_loc}:parameters.primary_metric", "Evaluation primary metric must match the plan."))
        if plan_dataset not in {train_dataset, eval_dataset} or train_dataset != eval_dataset:
            diagnostics.append(_diag(scenario_id, "6.3", "JOB_DATASET_MISMATCH", f"{eval_loc}:parameters.dataset_name", "Plan and jobs must use the same dataset identity."))
        evaluation_split = train_params.get("evaluation_split", eval_params.get("dataset_split"))
        if eval_params.get("dataset_split") != plan_split or evaluation_split != plan_split:
            diagnostics.append(_diag(scenario_id, "5.4", "JOB_SPLIT_MISMATCH", f"{eval_loc}:parameters.dataset_split", "Evaluation split must match the plan baseline split."))
        for document, loc in ((train, train_loc), (evaluate, eval_loc)):
            wandb = _mapping(document.get("wandb"))
            if wandb.get("group") != experiment_id:
                diagnostics.append(_diag(scenario_id, "6.3", "JOB_GROUP_MISMATCH", f"{loc}:wandb.group", "W&B group must equal the experiment identifier."))

    train_wandb, eval_wandb = _mapping(train.get("wandb")), _mapping(evaluate.get("wandb"))
    train_hf, eval_hf = _mapping(train.get("huggingface")), _mapping(evaluate.get("huggingface"))
    if train_wandb.get("group") != eval_wandb.get("group"):
        diagnostics.append(_diag(scenario_id, "6.3", "JOB_GROUP_MISMATCH", f"{eval_loc}:wandb.group", "Train and evaluate jobs must share an experiment group."))
    for section, phase, name, requirement, loc in (
        (_mapping(train.get("resources")), 6, "resources", "6.4", train_loc),
        (_mapping(evaluate.get("resources")), 6, "resources", "6.4", eval_loc),
        (train_wandb, 7, "wandb", "6.5", train_loc),
        (eval_wandb, 7, "wandb", "6.5", eval_loc),
        (train_hf, 8, "huggingface", "6.6", train_loc),
        (eval_hf, 8, "huggingface", "6.6", eval_loc),
    ):
        diagnostics.extend(_phase_metadata_diagnostics(
            section, phase=phase, name=name, scenario_id=scenario_id,
            location=loc, requirement=requirement,
        ))

    settings = project_settings or {}
    target = _mapping(settings.get("execution")).get("default_target")
    if target is None:
        target = settings.get("execution.default_target")
    for document, loc in ((train, train_loc), (evaluate, eval_loc)):
        resources = _mapping(document.get("resources"))
        if (target == "ssh" or target is None) and (resources.get("gpus") or 0) > 0 and resources.get("backend") != "slurm":
            diagnostics.append(_diag(scenario_id, "6.4", "JOB_SLURM_REQUIRED", f"{loc}:resources.backend", "SSH-targeted GPU work must use the Slurm backend."))
    return ValidationResult.from_diagnostics(diagnostics)


def _contains_value(text: str, value: Any) -> bool:
    if value is None:
        return False
    candidates = {str(value)}
    if isinstance(value, float):
        candidates.add(format(value, "g"))
    return any(candidate.lower() in text.lower() for candidate in candidates)


def _summary_heading_positions(headings: Sequence[str]) -> list[int]:
    groups = (
        ("recommend",), ("agent-determined default", "agent default"),
        ("objective", "hypothesis"), ("baseline", "primary metric", "success criter"),
        ("matrix", "run", "resource", "risk"), ("destination", "wandb", "hugging face"),
        ("artifact", "path"), ("approval", "approve", "modify"),
    )
    positions: list[int] = []
    cursor = -1
    for aliases in groups:
        found = next((index for index, heading in enumerate(headings) if index > cursor and any(alias in heading for alias in aliases)), -1)
        positions.append(found)
        if found >= 0:
            cursor = found
    return positions


def validate_approval_summary(
    summary: TextSource,
    *,
    plan: Union[ParsedPlan, TextSource],
    train_job: DocumentSource,
    evaluate_job: DocumentSource,
    scenario_id: str = "phase4",
    location: Optional[str] = None,
) -> ValidationResult:
    """Validate ordered completeness and duplicated-value consistency."""
    loc = location or _location(summary, "approval-summary.md")
    diagnostics: list[Diagnostic] = []
    try:
        text = _read_text(summary)
        parsed = plan if isinstance(plan, ParsedPlan) else parse_plan(plan)
        train = parse_yaml_document(train_job)
        evaluate = parse_yaml_document(evaluate_job)
    except (ArtifactParseError, OSError) as exc:
        return ValidationResult.from_diagnostics([_diag(scenario_id, "7.1", "APPROVAL_INPUT_INVALID", loc, str(exc))])

    headings = parse_markdown_headings(text)
    positions = _summary_heading_positions(headings)
    if any(position < 0 for position in positions) or positions != sorted(positions):
        diagnostics.append(_diag(scenario_id, "7.2", "APPROVAL_SUMMARY_ORDER_INVALID", f"{loc}:headings", "Approval Summary sections are missing or out of required order."))
    diagnostics.extend(_content_diagnostics(
        text, scenario_id=scenario_id, location=loc,
        placeholder_code="APPROVAL_PLACEHOLDER_UNRESOLVED", requirement="7.3",
    ))

    fm = parsed.frontmatter
    metric = _mapping(fm.get("primary_metric"))
    criteria = _mapping(fm.get("success_criteria"))
    baseline = _mapping(fm.get("baseline"))
    baseline_metric = _mapping(baseline.get("metric"))
    train_params = _mapping(train.get("parameters"))
    values = (
        ("experiment identifier", fm.get("experiment_id")),
        ("primary metric", metric.get("name")),
        ("metric direction", metric.get("direction")),
        ("baseline value", baseline_metric.get("value")),
        ("baseline split", _mapping(baseline.get("evaluation")).get("split")),
        ("success threshold", criteria.get("threshold")),
        ("LoRA matrix", _mapping(train.get("matrix")).get("lora_rank")),
    )
    for label, value in values:
        if isinstance(value, list):
            present = all(_contains_value(text, item) for item in value)
        else:
            present = _contains_value(text, value)
        if not present:
            diagnostics.append(_diag(scenario_id, "7.3", "APPROVAL_VALUE_MISMATCH", f"{loc}:{label.replace(' ', '-')}", f"Approval Summary does not reproduce the {label}."))

    purpose = _section(parsed.body, "purpose")
    hypothesis = _section(parsed.body, "hypothesis")
    for label, section_text in (("objective", purpose), ("hypothesis", hypothesis)):
        significant = [word for word in re.findall(r"[A-Za-z0-9_-]+", section_text.lower()) if len(word) >= 6]
        if section_text and significant and not any(word in text.lower() for word in significant[:8]):
            diagnostics.append(_diag(scenario_id, "7.3", "APPROVAL_VALUE_MISMATCH", f"{loc}:{label}", f"Approval Summary does not reproduce the plan {label}."))

    estimate = calculate_resource_estimate(train, evaluate)
    run_count_pattern = rf"\b{estimate.total_runs}\s+planned\s+job\s+invocations?\b"
    if not re.search(run_count_pattern, text, re.IGNORECASE):
        diagnostics.append(_diag(scenario_id, "7.3", "APPROVAL_RUN_COUNT_MISMATCH", f"{loc}:run-count", f"Estimated run count must equal matrix arithmetic ({estimate.total_runs})."))
    gpu_hours_pattern = rf"\b{estimate.total_gpu_hours:g}\s+GPU-hours?\b"
    if estimate.total_gpu_hours and not re.search(gpu_hours_pattern, text, re.IGNORECASE):
        diagnostics.append(_diag(scenario_id, "7.3", "APPROVAL_RESOURCE_ARITHMETIC_MISMATCH", f"{loc}:resources", "GPU-hour estimate must match matrix cardinality, requested time, and GPU count."))
    for resources, name in ((_mapping(train.get("resources")), "train"), (_mapping(evaluate.get("resources")), "evaluate")):
        requested_hours = _time_hours(resources.get("time"))
        time_present = _contains_value(text, resources.get("time"))
        if requested_hours is not None:
            time_present = time_present or bool(
                re.search(rf"\b{requested_hours:g}\s+hours?\b", text, re.I)
            )
        if not _contains_value(text, resources.get("gpus")) or not time_present:
            diagnostics.append(_diag(scenario_id, "7.3", "APPROVAL_RESOURCE_MISMATCH", f"{loc}:resources:{name}", f"Summary must include {name} GPU and time requests."))

    for document, label in ((train, "W&B"), (train, "Hugging Face")):
        section_name = "wandb" if label == "W&B" else "huggingface"
        destination = _mapping(document.get(section_name))
        if label == "W&B":
            destination_values = (destination.get("entity"), destination.get("project"), destination.get("group"))
            requirement, phase = "7.4", 7
        else:
            destination_values = (destination.get("namespace"), destination.get("repo"))
            requirement, phase = "7.4", 8
        if not any(_contains_value(text, value) for value in destination_values if value):
            diagnostics.append(_diag(scenario_id, requirement, "APPROVAL_DESTINATION_MISMATCH", f"{loc}:{section_name}", f"Summary must include the planned {label} destination."))
        phase_pattern = rf"(?is){re.escape(label)}.{{0,180}}planned.{{0,120}}unverified.{{0,80}}phase\s*{phase}|{re.escape(label)}.{{0,180}}phase\s*{phase}.{{0,120}}planned.{{0,120}}unverified"
        if not re.search(phase_pattern, text):
            diagnostics.append(_diag(scenario_id, requirement, "APPROVAL_PHASE_LABEL_MISSING", f"{loc}:{section_name}", f"{label} must be labeled planned and unverified until Phase {phase}."))

    for path in fm.get("jobs", []):
        full_path = f"experiments/{fm.get('experiment_id')}/{path}"
        if path not in text and full_path not in text:
            diagnostics.append(_diag(scenario_id, "7.3", "APPROVAL_ARTIFACT_PATH_MISSING", f"{loc}:paths", f"Summary must include artifact path '{path}'."))
    plan_path = f"experiments/{fm.get('experiment_id')}/plan.md"
    if "plan.md" not in text and plan_path not in text:
        diagnostics.append(_diag(scenario_id, "7.3", "APPROVAL_ARTIFACT_PATH_MISSING", f"{loc}:paths", "Summary must include the plan path."))
    approval_ending = _section(text, "approval required")
    if not re.search(r"(?i)approv(?:e|al)|modify|request changes", approval_ending):
        diagnostics.append(_diag(scenario_id, "7.5", "APPROVAL_REQUEST_MISSING", f"{loc}:ending", "Summary must request approval or modification."))
    execution_declared = bool(
        re.search(r"(?i)no\s+(?:(?:experiment|training|evaluation)\s+)?execution|no\s+(?:training|evaluation)|(?:has|have)\s+not\s+(?:run|executed)", approval_ending)
    )
    run_declared = bool(
        re.search(r"(?i)no\s+run(?:\s+(?:artifact|creation|record|director))?|run\s+(?:has|was)\s+not\s+created", approval_ending)
        or re.search(r"(?i)no\s+[^.\n]*execution[^.\n]{0,100}\brun\s+creation\b", approval_ending)
    )
    if not (execution_declared and run_declared):
        diagnostics.append(_diag(scenario_id, "7.5", "APPROVAL_NO_EXECUTION_DECLARATION_MISSING", f"{loc}:ending", "Summary must state that no execution and no Run creation occurred."))
    if not train_params:
        diagnostics.append(_diag(scenario_id, "7.3", "APPROVAL_INPUT_INVALID", f"{loc}:train-job", "Training parameters are unavailable for consistency checks."))
    return ValidationResult.from_diagnostics(diagnostics)


def validate_artifacts(
    plan: TextSource,
    train_job: DocumentSource,
    evaluate_job: DocumentSource,
    approval_summary: TextSource,
    *,
    scenario_id: str = "phase4",
    project_settings: Optional[Mapping[str, Any]] = None,
) -> ValidationResult:
    """Validate the complete Phase 4 plan/job/summary artifact set."""
    diagnostics: list[Diagnostic] = []
    plan_result = validate_plan(plan, scenario_id=scenario_id)
    diagnostics.extend(plan_result.diagnostics)
    jobs_result = validate_jobs(
        train_job, evaluate_job, plan=plan, scenario_id=scenario_id,
        project_settings=project_settings,
    )
    diagnostics.extend(jobs_result.diagnostics)
    summary_result = validate_approval_summary(
        approval_summary, plan=plan, train_job=train_job,
        evaluate_job=evaluate_job, scenario_id=scenario_id,
    )
    diagnostics.extend(summary_result.diagnostics)
    return ValidationResult.from_diagnostics(diagnostics)


# Explicit aliases keep the helper easy to discover from scenario and property tests.
validate_artifact_set = validate_artifacts
validate_plan_artifact = validate_plan
validate_job_artifacts = validate_jobs
