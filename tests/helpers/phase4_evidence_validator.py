"""Pure evidence and discovery-report validation for Phase 4 fixtures.

The validator operates only on caller-supplied mappings and repository-local
fixture files.  It never invokes Git, starts a process, or accesses a network.
Structured result files are authoritative for quantitative comparisons, while
narrative disagreements must remain represented by explicit conflict records.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from typing import Any

import yaml

from .phase4_models import Diagnostic, EvidenceRecord, Scenario, ValidationResult


_REQUIRED_SOURCE_TYPES = frozenset(
    {
        "project_plan",
        "project_log",
        "experiment_plan",
        "experiment_journal",
        "structured_results",
        "job_configuration",
        "git_history",
    }
)
_NARRATIVE_SOURCE_TYPES = frozenset(
    {"project_log", "experiment_plan", "experiment_journal", "journal", "narrative"}
)
_STRUCTURED_SOURCE_TYPES = frozenset(
    {"structured_result", "structured_results", "results", "results_yaml"}
)
_INSPECTED_STATUSES = frozenset({"inspected", "present", "available"})
_MISSING_STATUSES = frozenset({"absent", "missing", "unavailable", "unpopulated"})
_DUPLICATION_LEVELS = frozenset(
    {"exact_duplicate", "near_duplicate", "related_work", "novel_work"}
)
_DIMENSION_ALIASES = {
    "objective_hypothesis": "objective",
    "objective": "objective",
    "hypothesis": "objective",
    "model_configuration": "model",
    "model": "model",
    "dataset_configuration_split": "dataset",
    "dataset": "dataset",
    "dataset_split": "dataset",
    "technique": "technique",
    "parameter_range": "parameter_range",
    "parameters": "parameter_range",
    "metrics_protocol": "metrics",
    "metric": "metrics",
    "metrics": "metrics",
    "controlled_settings": "controls",
    "controls": "controls",
}
_EXACT = frozenset({"exact", "same", "match", "matched", "identical"})
_PARTIAL = frozenset({"similar", "partial", "overlap", "overlapping", "comparable"})
_DIFFERENT = frozenset({"different", "disjoint", "none", "no_overlap"})
_UNKNOWN = frozenset({"unknown", "unresolved", "missing"})
_COMMIT_RE = re.compile(r"(?i)(?:commit[:\s]+)?\b([0-9a-f]{7,64})\b")
_METRIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_. /-]*$", re.IGNORECASE)


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _items(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return tuple(value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return (value,)


def _location_ref(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    return text if text else "<missing>"


def _source_type(value: Any) -> str:
    normalized = _norm(value)
    aliases = {
        "plan": "experiment_plan",
        "journal": "experiment_journal",
        "results": "structured_results",
        "result": "structured_results",
        "results_yaml": "structured_results",
        "structured_result": "structured_results",
        "job": "job_configuration",
        "job_config": "job_configuration",
        "train_job": "job_configuration",
        "evaluate_job": "job_configuration",
        "evaluation_job": "job_configuration",
        "git": "git_history",
        "git_entry": "git_history",
        "project_settings": "project_plan",
    }
    return aliases.get(normalized, normalized)


def _diagnostic(
    scenario_id: str,
    requirement: str,
    code: str,
    location: str,
    message: str,
) -> Diagnostic:
    return Diagnostic(
        scenario_id=scenario_id,
        requirement=requirement,
        code=code,
        location=location,
        message=message,
    )


def _safe_local_path(workspace: Path, source_ref: str) -> Path | None:
    """Resolve a repository-relative source without following an escape."""
    raw = str(source_ref).strip()
    portable = raw.replace("\\", "/")
    posix = PurePosixPath(portable)
    windows = PureWindowsPath(raw)
    if not raw or posix.is_absolute() or windows.is_absolute() or ".." in posix.parts:
        return None
    root = workspace.resolve(strict=False)
    current = root
    for part in posix.parts:
        current = current / part
        if current.is_symlink():
            return None
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def _load_local_document(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return text
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _declared_commits(
    workspace: Path, declared: Mapping[str, Any] | Iterable[Any] | None
) -> frozenset[str]:
    values: list[Any] = []
    if declared is not None:
        values.extend(_items(declared))
    metadata = _safe_local_path(workspace, "git-evidence.yaml")
    if metadata is not None and metadata.is_file():
        document = _load_local_document(metadata)
        if isinstance(document, Mapping):
            values.extend(_items(document.get("entries")))
    commits: set[str] = set()
    for item in values:
        if isinstance(item, Mapping):
            raw = item.get("commit", item.get("commit_id", item.get("id")))
        else:
            raw = item
        match = _COMMIT_RE.search(str(raw or ""))
        if match:
            commits.add(match.group(1).lower())
    return frozenset(commits)


def _commit_from_ref(source_ref: str) -> str | None:
    match = _COMMIT_RE.search(str(source_ref))
    return match.group(1).lower() if match else None


def _evidence_index(
    scenario_evidence: Iterable[EvidenceRecord], report: Mapping[str, Any]
) -> dict[str, EvidenceRecord]:
    records = list(scenario_evidence)
    for position, item in enumerate(_items(report.get("evidence", report.get("evidence_records")))):
        if not isinstance(item, Mapping):
            continue
        evidence_id = item.get("evidence_id", item.get("id"))
        if evidence_id is None:
            continue
        records.append(
            EvidenceRecord(
                evidence_id=str(evidence_id),
                source_type=str(item.get("source_type", "repository")),
                source_ref=str(item.get("source_ref", "")),
                claims=tuple(str(claim) for claim in _items(item.get("claims"))),
                content_digest=item.get("content_digest"),
            )
        )
    # Keep the first record: duplicate IDs receive a separate diagnostic and do
    # not silently redirect existing findings to later evidence.
    return {record.evidence_id: record for record in reversed(records)}


def _inventory(report: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = report.get("inspected", report.get("source_inventory", report.get("inventory", ())))
    return tuple(item for item in _items(raw) if isinstance(item, Mapping))


def _available_relevant_sources(workspace: Path) -> dict[str, set[str]]:
    """Inventory deterministic evidence classes physically present locally."""
    available: dict[str, set[str]] = {kind: set() for kind in _REQUIRED_SOURCE_TYPES}
    roots = {
        "project_plan": workspace / "project-plan.md",
        "project_log": workspace / "project-log.md",
    }
    for kind, path in roots.items():
        if path.is_file():
            available[kind].add(path.relative_to(workspace).as_posix())
    experiments = workspace / "experiments"
    if experiments.is_dir():
        for path in sorted(experiments.glob("*/plan.md")):
            available["experiment_plan"].add(path.relative_to(workspace).as_posix())
        for path in sorted(experiments.glob("*/journal.md")):
            available["experiment_journal"].add(path.relative_to(workspace).as_posix())
        for path in sorted(experiments.glob("*/results.y*ml")):
            available["structured_results"].add(path.relative_to(workspace).as_posix())
        for path in sorted(experiments.glob("*/jobs/*.y*ml")):
            available["job_configuration"].add(path.relative_to(workspace).as_posix())
    git_metadata = workspace / "git-evidence.yaml"
    if git_metadata.is_file():
        available["git_history"].add("git-evidence.yaml")
    return available


def _metric_name(entry: Mapping[str, Any]) -> str | None:
    raw = entry.get("metric", entry.get("name"))
    if isinstance(raw, Mapping):
        raw = raw.get("name")
    if raw is None:
        return None
    name = str(raw).strip().lower()
    return name if _METRIC_NAME_RE.match(name) else None


def _number(value: Any) -> float | None:
    if type(value) not in {int, float}:
        return None
    return float(value)


def _structured_metrics(document: Any) -> dict[str, set[float]]:
    """Collect named numeric metrics from conventional structured results."""
    found: dict[str, set[float]] = {}

    def add(name: Any, value: Any) -> None:
        metric = str(name).strip().lower()
        number = _number(value)
        if number is not None and _METRIC_NAME_RE.match(metric):
            found.setdefault(metric, set()).add(number)

    def walk(value: Any, parent: str = "") -> None:
        if isinstance(value, Mapping):
            name = value.get("name", value.get("metric"))
            if isinstance(name, str) and "value" in value:
                add(name, value["value"])
            for key, item in value.items():
                normalized = _norm(key)
                if normalized in {"accuracy", "f1", "precision", "recall", "loss", "perplexity", "bleu", "rouge", "auc"}:
                    add(normalized, item)
                elif normalized == "value" and parent in found:
                    add(parent, item)
                walk(item, normalized)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                walk(item, parent)

    walk(document)
    return found


def _comparison_entries(report: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    for key in ("metric_comparisons", "metric_cross_checks", "structured_narrative_comparisons"):
        if key in report:
            return tuple(item for item in _items(report[key]) if isinstance(item, Mapping))
    return ()


def _observation(entry: Mapping[str, Any], side: str) -> tuple[float | None, str]:
    raw = entry.get(side, {})
    if not isinstance(raw, Mapping):
        return _number(raw), ""
    value = raw.get("value", raw.get("value_or_claim"))
    return _number(value), str(raw.get("source_ref", ""))


def _conflict_key(metric: str, structured: float, narrative: float) -> tuple[str, float, float]:
    return (metric.strip().lower(), structured, narrative)


def classify_duplication(overlap_facts: Mapping[str, Any] | Sequence[Any]) -> str:
    """Derive one duplication level from declared dimensional overlap facts.

    Facts may be a dimension-to-status mapping or a sequence of mappings with
    ``dimension`` and ``status``/``match`` fields. Unknown dimensions never
    establish exact or near duplication.
    """
    statuses: dict[str, str] = {}
    if isinstance(overlap_facts, Mapping):
        source = overlap_facts.get("dimensions", overlap_facts)
        if isinstance(source, Mapping):
            for dimension, raw in source.items():
                value = raw.get("status", raw.get("match")) if isinstance(raw, Mapping) else raw
                canonical = _DIMENSION_ALIASES.get(_norm(dimension), _norm(dimension))
                statuses[canonical] = _norm(value)
        else:
            overlap_facts = _items(source)
    if not statuses and not isinstance(overlap_facts, Mapping):
        for item in _items(overlap_facts):
            if not isinstance(item, Mapping):
                continue
            dimension = item.get("dimension", item.get("name"))
            value = item.get("status", item.get("match"))
            if dimension is not None and value is not None:
                canonical = _DIMENSION_ALIASES.get(_norm(dimension), _norm(dimension))
                statuses[canonical] = _norm(value)

    material = {key: statuses.get(key, "unknown") for key in set(_DIMENSION_ALIASES.values())}
    known = [status for status in material.values() if status not in _UNKNOWN]
    if known and all(status in _EXACT for status in material.values()):
        return "exact_duplicate"
    objective = material["objective"]
    core = (material["model"], material["dataset"], material["technique"])
    matched = sum(status in _EXACT | _PARTIAL for status in material.values())
    if objective in _EXACT and all(status in _EXACT | _PARTIAL for status in core) and matched >= 5:
        return "near_duplicate"
    if any(status in _EXACT | _PARTIAL for status in known):
        return "related_work"
    return "novel_work"


def _validate_inventory(
    scenario_id: str,
    report: Mapping[str, Any],
    workspace: Path,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    inventory = _inventory(report)
    available = _available_relevant_sources(workspace)
    represented: dict[str, list[tuple[str, str, int]]] = {}
    for position, item in enumerate(inventory):
        kind = _source_type(item.get("source_type", item.get("type", "")))
        status = _norm(item.get("status", "inspected"))
        source_ref = str(item.get("source_ref", item.get("path", item.get("provenance", ""))))
        represented.setdefault(kind, []).append((status, source_ref, position))
        if status not in _INSPECTED_STATUSES | _MISSING_STATUSES:
            diagnostics.append(_diagnostic(scenario_id, "2.1", "EVIDENCE_INVENTORY_STATUS_INVALID", f"discovery_report.inspected[{position}].status", "inventory status must be inspected or explicitly missing"))
        if kind == "project_log" and status in _INSPECTED_STATUSES and _location_ref(source_ref).startswith("templates/"):
            diagnostics.append(_diagnostic(scenario_id, "2.5", "EVIDENCE_TEMPLATE_NOT_PROJECT_SOURCE", f"discovery_report.inspected[{position}].source_ref", "templates/project-log.md cannot satisfy the root project-log source"))

    for kind in sorted(_REQUIRED_SOURCE_TYPES):
        entries = represented.get(kind, [])
        if not entries:
            diagnostics.append(_diagnostic(scenario_id, "2.1", "EVIDENCE_SOURCE_CLASS_UNACCOUNTED", f"discovery_report.inspected.{kind}", f"source class {kind} must be inspected or explicitly missing"))
            continue
        actual_paths = available[kind]
        inspected_refs = {ref.replace("\\", "/") for status, ref, _ in entries if status in _INSPECTED_STATUSES}
        for path in sorted(actual_paths - inspected_refs):
            # Git history may be represented by a declared commit rather than
            # the fixture metadata filename itself.
            if kind == "git_history" and any(_commit_from_ref(ref) for ref in inspected_refs):
                continue
            diagnostics.append(_diagnostic(scenario_id, "2.1", "EVIDENCE_AVAILABLE_SOURCE_NOT_INSPECTED", f"discovery_report.inspected.{kind}", f"available relevant source was not inventoried: {path}"))
        if not actual_paths and not any(status in _MISSING_STATUSES for status, _, _ in entries):
            diagnostics.append(_diagnostic(scenario_id, "2.1", "EVIDENCE_MISSING_SOURCE_NOT_EXPLICIT", f"discovery_report.inspected.{kind}", f"unavailable source class {kind} must be explicitly marked missing"))

    missing = tuple(item for item in _items(report.get("missing_sources")) if isinstance(item, Mapping))
    for kind, entries in represented.items():
        for status, source_ref, position in entries:
            if status not in _MISSING_STATUSES:
                continue
            matched = any(
                _source_type(item.get("source_type", item.get("type", ""))) == kind
                and str(item.get("source_ref", item.get("path", ""))) == source_ref
                for item in missing
            )
            if not matched:
                diagnostics.append(_diagnostic(scenario_id, "2.5", "EVIDENCE_MISSING_SOURCE_RECORD_REQUIRED", f"discovery_report.inspected[{position}]", "missing inventory entries require a matching explicit missing_sources record"))
    return diagnostics


def validate_discovery_report(
    scenario_id: str,
    report: Mapping[str, Any],
    source_workspace: Path,
    *,
    evidence_records: Iterable[EvidenceRecord] = (),
    declared_git_commits: Mapping[str, Any] | Iterable[Any] | None = None,
    overlap_facts: Mapping[str, Any] | Sequence[Any] | None = None,
) -> ValidationResult:
    """Validate one discovery report and return deterministic diagnostics."""
    diagnostics: list[Diagnostic] = []
    workspace = Path(source_workspace)
    if not workspace.is_dir():
        diagnostics.append(_diagnostic(scenario_id, "2.1", "EVIDENCE_WORKSPACE_MISSING", "source_workspace", "source workspace is not a local directory"))
        return ValidationResult.from_diagnostics(diagnostics)
    if not isinstance(report, Mapping):
        diagnostics.append(_diagnostic(scenario_id, "2.1", "EVIDENCE_REPORT_INVALID", "discovery_report", "discovery report must be a mapping"))
        return ValidationResult.from_diagnostics(diagnostics)

    diagnostics.extend(_validate_inventory(scenario_id, report, workspace))
    commits = _declared_commits(workspace, declared_git_commits)
    records = list(evidence_records)
    for item in _items(report.get("evidence", report.get("evidence_records"))):
        if isinstance(item, Mapping) and item.get("evidence_id", item.get("id")) is not None:
            report_record = EvidenceRecord(str(item.get("evidence_id", item.get("id"))), str(item.get("source_type", "repository")), str(item.get("source_ref", "")), tuple(str(value) for value in _items(item.get("claims"))), item.get("content_digest"))
            # ``load_scenario`` derives immutable evidence records from this
            # same report.  Treat an equivalent projection as one declaration,
            # while preserving genuinely repeated/conflicting IDs for errors.
            if report_record not in records:
                records.append(report_record)
    ids = [record.evidence_id for record in records]
    for evidence_id in sorted({value for value in ids if ids.count(value) > 1}):
        diagnostics.append(_diagnostic(scenario_id, "2.2", "EVIDENCE_ID_DUPLICATE", f"discovery_report.evidence.{evidence_id}", "evidence identifiers must be unique"))
    evidence = _evidence_index(evidence_records, report)
    resolved: dict[str, Any] = {}
    inspected_refs = {
        str(item.get("source_ref", item.get("path", item.get("provenance", ""))))
        for item in _inventory(report)
        if _norm(item.get("status", "inspected")) in _INSPECTED_STATUSES
    }
    for evidence_id, record in sorted(evidence.items()):
        location = f"discovery_report.evidence.{evidence_id}.source_ref"
        commit = _commit_from_ref(record.source_ref)
        if _source_type(record.source_type) == "git_history" or commit:
            if commit is None or commit not in commits:
                diagnostics.append(_diagnostic(scenario_id, "2.2", "EVIDENCE_COMMIT_UNDECLARED", location, "Git provenance must resolve to a commit declared by fixture metadata"))
            else:
                resolved[evidence_id] = {"commit": commit}
        else:
            path = _safe_local_path(workspace, record.source_ref)
            if path is None:
                diagnostics.append(_diagnostic(scenario_id, "2.2", "EVIDENCE_PATH_UNSAFE", location, "evidence source must be a safe repository-relative path"))
            elif not path.is_file():
                diagnostics.append(_diagnostic(scenario_id, "2.2", "EVIDENCE_PATH_MISSING", location, f"evidence source does not exist: {_location_ref(record.source_ref)}"))
            else:
                resolved[evidence_id] = _load_local_document(path)
        if record.source_ref not in inspected_refs and not (commit and any(commit == _commit_from_ref(ref) for ref in inspected_refs)):
            diagnostics.append(_diagnostic(scenario_id, "2.1", "EVIDENCE_SOURCE_NOT_INSPECTED", location, "cited evidence must also appear in the inspected-source inventory"))

    findings = tuple(item for item in _items(report.get("findings")) if isinstance(item, Mapping))
    for position, finding in enumerate(findings):
        references = tuple(str(value) for value in _items(finding.get("evidence_ids", finding.get("sources"))))
        if not references:
            diagnostics.append(_diagnostic(scenario_id, "2.2", "EVIDENCE_UNSUPPORTED_CLAIM", f"discovery_report.findings[{position}]", "every finding must cite at least one evidence identifier"))
        for evidence_id in references:
            if evidence_id not in evidence or evidence_id not in resolved:
                diagnostics.append(_diagnostic(scenario_id, "2.2", "EVIDENCE_FINDING_PROVENANCE_INVALID", f"discovery_report.findings[{position}].evidence_ids", f"finding cites unresolved evidence: {evidence_id}"))

    conflicts = tuple(item for item in _items(report.get("conflicts")) if isinstance(item, Mapping))
    conflict_keys: set[tuple[str, float, float]] = set()
    for position, conflict in enumerate(conflicts):
        metric = _metric_name(conflict)
        structured, structured_ref = _observation(conflict, "structured")
        narrative, narrative_ref = _observation(conflict, "narrative")
        if metric is None or structured is None or narrative is None or not structured_ref or not narrative_ref:
            diagnostics.append(_diagnostic(scenario_id, "2.3", "EVIDENCE_CONFLICT_INCOMPLETE", f"discovery_report.conflicts[{position}]", "conflict records require metric, both values, and both source references"))
        else:
            conflict_keys.add(_conflict_key(metric, structured, narrative))

    for position, comparison in enumerate(_comparison_entries(report)):
        metric = _metric_name(comparison)
        structured, structured_ref = _observation(comparison, "structured")
        narrative, narrative_ref = _observation(comparison, "narrative")
        if metric is None or structured is None or narrative is None:
            diagnostics.append(_diagnostic(scenario_id, "2.3", "EVIDENCE_METRIC_COMPARISON_INCOMPLETE", f"discovery_report.metric_comparisons[{position}]", "metric comparison requires named structured and narrative numeric values"))
            continue
        mismatch = structured != narrative
        if mismatch and _conflict_key(metric, structured, narrative) not in conflict_keys:
            diagnostics.append(_diagnostic(scenario_id, "2.3", "EVIDENCE_CONFLICT_UNRECORDED", f"discovery_report.metric_comparisons[{position}]", "structured and narrative metric mismatch requires an explicit conflict record"))
        selected = comparison.get("comparison_value", comparison.get("selected_value"))
        if selected is not None and _number(selected) != structured:
            diagnostics.append(_diagnostic(scenario_id, "2.3", "EVIDENCE_STRUCTURED_PRECEDENCE_VIOLATED", f"discovery_report.metric_comparisons[{position}].comparison_value", "quantitative comparison must use the structured result value while preserving conflicts"))
        if structured_ref and structured_ref not in inspected_refs:
            diagnostics.append(_diagnostic(scenario_id, "2.3", "EVIDENCE_METRIC_SOURCE_NOT_INSPECTED", f"discovery_report.metric_comparisons[{position}].structured.source_ref", "structured metric source was not inspected"))
        if narrative_ref and narrative_ref not in inspected_refs:
            diagnostics.append(_diagnostic(scenario_id, "2.3", "EVIDENCE_METRIC_SOURCE_NOT_INSPECTED", f"discovery_report.metric_comparisons[{position}].narrative.source_ref", "narrative metric source was not inspected"))

    baselines = tuple(item for item in _items(report.get("baselines", report.get("comparable_baselines"))) if isinstance(item, Mapping))
    for position, baseline in enumerate(baselines):
        location = f"discovery_report.baselines[{position}]"
        status = _norm(baseline.get("status", "supported"))
        if status == "unresolved":
            if not baseline.get("missing_support"):
                diagnostics.append(_diagnostic(scenario_id, "2.6", "EVIDENCE_BASELINE_UNRESOLVED_REASON_MISSING", location, "unresolved baselines must identify missing support"))
            continue
        metric = _metric_name(baseline)
        metric_data = baseline.get("metric") if isinstance(baseline.get("metric"), Mapping) else {}
        value = _number(metric_data.get("value", baseline.get("value")))
        direction = metric_data.get("direction", baseline.get("direction"))
        evidence_id = baseline.get("source_evidence_id", baseline.get("evidence_id"))
        required = {
            "model": baseline.get("model"),
            "dataset": baseline.get("dataset"),
            "split": baseline.get("split"),
            "metric": metric,
            "value": value,
            "direction": direction,
            "provenance": evidence_id or baseline.get("source_ref"),
        }
        missing = sorted(key for key, item in required.items() if item is None or item == "")
        if missing:
            diagnostics.append(_diagnostic(scenario_id, "2.6", "EVIDENCE_BASELINE_SUPPORT_INCOMPLETE", location, f"supported baseline is missing: {', '.join(missing)}"))
            continue
        source_record = evidence.get(str(evidence_id)) if evidence_id is not None else None
        if source_record is None and baseline.get("source_ref"):
            source_record = next((record for record in evidence.values() if record.source_ref == baseline.get("source_ref")), None)
        if source_record is None or source_record.evidence_id not in resolved:
            diagnostics.append(_diagnostic(scenario_id, "2.6", "EVIDENCE_BASELINE_UNSUPPORTED", location, "baseline value must cite resolvable evidence"))
            continue
        structured_candidates: set[float] = set()
        for record in evidence.values():
            if _source_type(record.source_type) in _STRUCTURED_SOURCE_TYPES and record.evidence_id in resolved:
                structured_candidates.update(_structured_metrics(resolved[record.evidence_id]).get(str(metric), set()))
        if structured_candidates:
            if value not in structured_candidates:
                diagnostics.append(_diagnostic(scenario_id, "2.6", "EVIDENCE_BASELINE_VALUE_MISMATCH", f"{location}.value", "baseline value does not match the cited structured results"))
            if _source_type(source_record.source_type) not in _STRUCTURED_SOURCE_TYPES:
                diagnostics.append(_diagnostic(scenario_id, "2.3", "EVIDENCE_STRUCTURED_PRECEDENCE_VIOLATED", f"{location}.source_evidence_id", "a matching structured result must support the quantitative baseline"))

    duplication = report.get("duplication", report.get("duplication_assessment"))
    if not isinstance(duplication, Mapping):
        diagnostics.append(_diagnostic(scenario_id, "2.4", "EVIDENCE_DUPLICATION_MISSING", "discovery_report.duplication", "duplication assessment is required"))
    else:
        reported = _norm(duplication.get("level", duplication.get("classification", "")))
        if reported not in _DUPLICATION_LEVELS:
            diagnostics.append(_diagnostic(scenario_id, "2.4", "EVIDENCE_DUPLICATION_CLASS_INVALID", "discovery_report.duplication.level", "duplication level must be exact duplicate, near duplicate, related work, or novel work"))
        facts = overlap_facts if overlap_facts is not None else duplication.get("overlap_facts", duplication.get("dimensions", report.get("overlap_facts")))
        if facts is None:
            diagnostics.append(_diagnostic(scenario_id, "2.4", "EVIDENCE_DUPLICATION_FACTS_MISSING", "discovery_report.duplication", "duplication classification requires declared dimensional overlap facts"))
        elif reported in _DUPLICATION_LEVELS:
            expected = classify_duplication(facts)
            if reported != expected:
                diagnostics.append(_diagnostic(scenario_id, "2.4", "EVIDENCE_DUPLICATION_CLASS_MISMATCH", "discovery_report.duplication.level", f"declared overlap facts require {expected}"))
        if not _items(duplication.get("evidence_ids", duplication.get("sources"))):
            diagnostics.append(_diagnostic(scenario_id, "5.3", "EVIDENCE_DUPLICATION_PROVENANCE_MISSING", "discovery_report.duplication", "duplication assessment must cite prior-research evidence"))
        if reported != "exact_duplicate" and not _items(duplication.get("differences", duplication.get("different_or_unknown_dimensions"))):
            diagnostics.append(_diagnostic(scenario_id, "5.4", "EVIDENCE_DUPLICATION_DIFFERENCES_MISSING", "discovery_report.duplication", "non-exact duplication assessments must preserve material differences or unknowns"))

    return ValidationResult.from_diagnostics(diagnostics)


def validate_evidence(
    scenario: Scenario,
    discovery_report: Mapping[str, Any],
    source_workspace: Path,
    **kwargs: Any,
) -> ValidationResult:
    """Validate evidence for an immutable :class:`Scenario`."""
    return validate_discovery_report(
        scenario.scenario_id,
        discovery_report,
        source_workspace,
        evidence_records=scenario.evidence,
        **kwargs,
    )


def validate_scenario_evidence(
    scenario: Scenario,
    source_workspace: Path,
    discovery_report: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ValidationResult:
    """Load the scenario's discovery YAML when a mapping is not supplied."""
    report = discovery_report
    if report is None:
        path = scenario.expected_artifacts.get("discovery_report")
        if path is None:
            return ValidationResult.from_diagnostics(
                (_diagnostic(scenario.scenario_id, "2.1", "EVIDENCE_REPORT_MISSING", "scenario.expected.discovery_report", "scenario does not declare a discovery report"),)
            )
        document = _load_local_document(Path(path))
        if not isinstance(document, Mapping):
            return ValidationResult.from_diagnostics(
                (_diagnostic(scenario.scenario_id, "2.1", "EVIDENCE_REPORT_INVALID", "scenario.expected.discovery_report", "discovery report must be valid YAML mapping"),)
            )
        report = document
    return validate_evidence(scenario, report, source_workspace, **kwargs)


# Compatibility names for tests and composed validators.
validate_evidence_and_discovery_report = validate_discovery_report
validate_discovery_evidence = validate_discovery_report


__all__ = [
    "classify_duplication",
    "validate_discovery_evidence",
    "validate_discovery_report",
    "validate_evidence",
    "validate_evidence_and_discovery_report",
    "validate_scenario_evidence",
]
