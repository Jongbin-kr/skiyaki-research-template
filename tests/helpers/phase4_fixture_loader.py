"""Safe, deterministic loading for Phase 4 planning fixtures.

The loader is deliberately test-only.  It parses UTF-8 YAML with
``yaml.safe_load`` and treats Markdown as inert text; it never executes fixture
content, starts a subprocess, or accesses the network.

Schema
------
``scenario.yaml`` uses schema version 1 and follows the layout documented in
the Phase 4 design.  It references ``transcript.yaml``,
``action-manifest.yaml``, one ``source-workspace/`` directory, and an
``expected`` mapping of logical artifact names to fixture-relative files.
Split documents may also declare ``schema_version: 1``.  Extra mapping keys are
preserved/ignored so fixture authors can add validator-specific metadata
without changing this loader.

All referenced paths are relative to the scenario directory. Absolute paths,
``..`` components, and symlinks are rejected. Fixture inputs remain untouched.
A writable workspace is produced only by :func:`materialize_source_workspace`,
which copies ``source-workspace/`` beneath a caller-provided pytest
``tmp_path``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
from typing import Any, Iterable, Mapping, Optional

import yaml

from .phase4_models import EvidenceRecord, ObservedAction, Scenario, Turn


SCHEMA_VERSION = 1
SCENARIO_FILE = "scenario.yaml"
_FORBIDDEN_DEPENDENCIES = frozenset(
    {
        "clock",
        "credential",
        "credentials",
        "external_service",
        "mutable_external_data",
        "network",
        "network_state",
        "remote_service",
        "wall_clock",
        "wall_clock_time",
    }
)
_DEPENDENCY_KEYS = frozenset(
    {"dependencies", "dependency", "fixture_dependencies", "requires"}
)
_FRONTMATTER = re.compile(r"\A---[ \t]*\n(?P<yaml>.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class FixtureLoadError(ValueError):
    """A stable, location-addressed fixture loading failure."""

    code: str
    location: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code} at {self.location}: {self.detail}"


def _location(path: Path) -> str:
    return path.as_posix()


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def resolve_fixture_path(
    fixture_root: Path,
    relative_path: str | Path,
    *,
    must_exist: bool = True,
    expected_kind: Optional[str] = None,
) -> Path:
    """Resolve a fixture-relative path without allowing escape or symlinks.

    ``expected_kind`` may be ``"file"`` or ``"directory"``.  Rejecting
    symlinks makes the lexical confinement check sufficient even on platforms
    where a link inside the fixture points elsewhere.
    """
    root = Path(fixture_root)
    raw_path = str(relative_path)
    candidate_value = Path(relative_path)
    # Fixture paths are portable POSIX-style references. Treat backslashes as
    # separators for validation so Windows traversal/absolute forms cannot be
    # smuggled into a fixture created on POSIX.
    pure_value = PurePosixPath(raw_path.replace("\\", "/"))
    windows_value = PureWindowsPath(raw_path)
    location = raw_path.replace("\\", "/")

    if candidate_value.is_absolute() or pure_value.is_absolute() or windows_value.is_absolute():
        raise FixtureLoadError("FIXTURE_PATH_ABSOLUTE", location, "absolute paths are not allowed")
    if not pure_value.parts or any(part == ".." for part in pure_value.parts):
        raise FixtureLoadError("FIXTURE_PATH_TRAVERSAL", location, "parent traversal is not allowed")

    root = root.resolve(strict=True)
    candidate = root.joinpath(*pure_value.parts)
    # Check every existing component before resolve() follows any link.
    current = root
    for part in pure_value.parts:
        current = current / part
        if current.is_symlink():
            raise FixtureLoadError("FIXTURE_PATH_SYMLINK", location, "symlinked fixture paths are not allowed")

    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise FixtureLoadError("FIXTURE_PATH_TRAVERSAL", location, "path escapes the fixture root") from exc

    if must_exist and not resolved.exists():
        raise FixtureLoadError("FIXTURE_PATH_MISSING", location, "referenced fixture path does not exist")
    if expected_kind == "file" and resolved.exists() and not resolved.is_file():
        raise FixtureLoadError("FIXTURE_PATH_NOT_FILE", location, "expected a regular file")
    if expected_kind == "directory" and resolved.exists() and not resolved.is_dir():
        raise FixtureLoadError("FIXTURE_PATH_NOT_DIRECTORY", location, "expected a directory")
    return resolved


def load_yaml(path: Path, *, fixture_root: Optional[Path] = None) -> Any:
    """Load one UTF-8 YAML document using only PyYAML's safe loader."""
    yaml_path = (
        resolve_fixture_path(fixture_root, path, expected_kind="file")
        if fixture_root is not None
        else Path(path)
    )
    try:
        text = _normalize_text(yaml_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise FixtureLoadError("FIXTURE_READ_FAILED", _location(yaml_path), str(exc)) from exc
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise FixtureLoadError("FIXTURE_YAML_INVALID", _location(yaml_path), str(exc)) from exc
    return {} if value is None else value


def load_markdown(path: Path, *, fixture_root: Optional[Path] = None) -> str:
    """Load Markdown as normalized, inert UTF-8 text."""
    markdown_path = (
        resolve_fixture_path(fixture_root, path, expected_kind="file")
        if fixture_root is not None
        else Path(path)
    )
    try:
        return _normalize_text(markdown_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise FixtureLoadError("FIXTURE_READ_FAILED", _location(markdown_path), str(exc)) from exc


def load_markdown_frontmatter(path: Path) -> tuple[Mapping[str, Any], str]:
    """Safely parse optional YAML frontmatter and return it with the body."""
    text = load_markdown(path)
    match = _FRONTMATTER.match(text)
    if match is None:
        return {}, text
    try:
        metadata = yaml.safe_load(match.group("yaml")) or {}
    except yaml.YAMLError as exc:
        raise FixtureLoadError("FIXTURE_YAML_INVALID", _location(path), str(exc)) from exc
    if not isinstance(metadata, Mapping):
        raise FixtureLoadError("FIXTURE_SCHEMA_INVALID", _location(path), "frontmatter must be a mapping")
    _validate_declared_schema(metadata, path, required=False)
    return dict(metadata), text[match.end() :]


def _require_mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FixtureLoadError("FIXTURE_SCHEMA_INVALID", location, "expected a mapping")
    return value


def _validate_declared_schema(
    document: Mapping[str, Any], path: Path, *, required: bool
) -> None:
    if "schema_version" not in document:
        if required:
            raise FixtureLoadError("FIXTURE_SCHEMA_VERSION_MISSING", _location(path), "schema_version is required")
        return
    version = document["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        raise FixtureLoadError(
            "FIXTURE_SCHEMA_VERSION_UNSUPPORTED",
            _location(path),
            f"expected schema_version {SCHEMA_VERSION}",
        )


def _dependency_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key in ("kind", "name", "type", "source"):
            if key in value and isinstance(value[key], str):
                yield value[key]
        for item in value.values():
            if isinstance(item, (Mapping, list, tuple)):
                yield from _dependency_names(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _dependency_names(item)


def _normalize_dependency(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _reject_nondeterministic_dependencies(document: Mapping[str, Any], location: str) -> None:
    """Reject explicit runtime dependencies, not planned destination metadata."""
    for key, value in document.items():
        normalized_key = _normalize_dependency(str(key))
        if normalized_key in _DEPENDENCY_KEYS:
            forbidden = sorted(
                name
                for raw_name in _dependency_names(value)
                if (name := _normalize_dependency(raw_name)) in _FORBIDDEN_DEPENDENCIES
            )
            if forbidden:
                raise FixtureLoadError(
                    "FIXTURE_NONDETERMINISTIC_DEPENDENCY",
                    f"{location}.{key}",
                    f"forbidden fixture dependency: {forbidden[0]}",
                )
        if isinstance(value, Mapping):
            _reject_nondeterministic_dependencies(value, f"{location}.{key}")


def _flatten_settings(value: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, item in value.items():
        dotted = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, Mapping):
            flattened.update(_flatten_settings(item, dotted))
        else:
            flattened[dotted] = item
    return flattened


def _load_project_settings(source_workspace: Path) -> Mapping[str, Any]:
    project_plan = source_workspace / "project-plan.md"
    if not project_plan.is_file():
        return {}
    metadata, _ = load_markdown_frontmatter(project_plan)
    return _flatten_settings(metadata)


def _load_turns(document: Mapping[str, Any], fixture_root: Path) -> tuple[Turn, ...]:
    raw_turns = document.get("turns", ())
    if not isinstance(raw_turns, list):
        raise FixtureLoadError("FIXTURE_SCHEMA_INVALID", "transcript.turns", "expected a list")
    turns: list[Turn] = []
    for position, raw_turn in enumerate(raw_turns):
        item = _require_mapping(raw_turn, f"transcript.turns[{position}]")
        artifact = item.get("artifact")
        artifact_path = None
        if artifact is not None:
            artifact_path = resolve_fixture_path(fixture_root, str(artifact), expected_kind="file")
        try:
            turns.append(
                Turn(
                    index=int(item["index"]),
                    actor=str(item["actor"]),
                    kind=str(item["kind"]),
                    text=str(item.get("text", "")),
                    decision_key=item.get("decision_key"),
                    resolves=item.get("resolves"),
                    value=item.get("value"),
                    artifact=artifact_path,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FixtureLoadError("FIXTURE_SCHEMA_INVALID", f"transcript.turns[{position}]", str(exc)) from exc
    return tuple(turns)


def _load_actions(document: Mapping[str, Any]) -> tuple[ObservedAction, ...]:
    raw_actions = document.get("actions", ())
    if not isinstance(raw_actions, list):
        raise FixtureLoadError("FIXTURE_SCHEMA_INVALID", "action_manifest.actions", "expected a list")
    actions: list[ObservedAction] = []
    for position, raw_action in enumerate(raw_actions):
        item = _require_mapping(raw_action, f"action_manifest.actions[{position}]")
        try:
            actions.append(
                ObservedAction(
                    kind=str(item["kind"]),
                    target=str(item["target"]),
                    command=item.get("command"),
                    metadata=item.get("metadata", {}),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FixtureLoadError("FIXTURE_SCHEMA_INVALID", f"action_manifest.actions[{position}]", str(exc)) from exc
    return tuple(actions)


def _load_evidence(document: Mapping[str, Any]) -> tuple[EvidenceRecord, ...]:
    raw_records = document.get("evidence", document.get("evidence_records", ()))
    if not isinstance(raw_records, list):
        return ()
    records: list[EvidenceRecord] = []
    for position, raw_record in enumerate(raw_records):
        item = _require_mapping(raw_record, f"evidence[{position}]")
        evidence_id = item.get("evidence_id", item.get("id"))
        if evidence_id is None:
            raise FixtureLoadError("FIXTURE_SCHEMA_INVALID", f"evidence[{position}]", "evidence_id is required")
        records.append(
            EvidenceRecord(
                evidence_id=str(evidence_id),
                source_type=str(item.get("source_type", "repository")),
                source_ref=str(item.get("source_ref", "")),
                claims=tuple(str(claim) for claim in item.get("claims", ())),
                content_digest=item.get("content_digest"),
            )
        )
    return tuple(records)


def load_scenario(fixture_dir: Path) -> Scenario:
    """Load the documented split-file Phase 4 scenario into immutable models."""
    fixture_root = Path(fixture_dir).resolve(strict=True)
    if not fixture_root.is_dir():
        raise FixtureLoadError("FIXTURE_PATH_NOT_DIRECTORY", _location(fixture_root), "fixture root must be a directory")

    scenario_path = resolve_fixture_path(fixture_root, SCENARIO_FILE, expected_kind="file")
    scenario_doc = _require_mapping(load_yaml(scenario_path), SCENARIO_FILE)
    _validate_declared_schema(scenario_doc, scenario_path, required=True)
    _reject_nondeterministic_dependencies(scenario_doc, "scenario")

    transcript_ref = scenario_doc.get("transcript", "transcript.yaml")
    action_ref = scenario_doc.get("action_manifest", "action-manifest.yaml")
    transcript_path = resolve_fixture_path(fixture_root, str(transcript_ref), expected_kind="file")
    action_path = resolve_fixture_path(fixture_root, str(action_ref), expected_kind="file")
    transcript_doc = _require_mapping(load_yaml(transcript_path), str(transcript_ref))
    action_doc = _require_mapping(load_yaml(action_path), str(action_ref))
    _validate_declared_schema(transcript_doc, transcript_path, required=False)
    _validate_declared_schema(action_doc, action_path, required=False)
    _reject_nondeterministic_dependencies(transcript_doc, "transcript")
    _reject_nondeterministic_dependencies(action_doc, "action_manifest")

    source_ref = scenario_doc.get("source_workspace", "source-workspace")
    source_workspace = resolve_fixture_path(
        fixture_root, str(source_ref), expected_kind="directory"
    )

    raw_expected = _require_mapping(scenario_doc.get("expected", {}), "scenario.expected")
    expected_artifacts = {
        str(name): resolve_fixture_path(fixture_root, str(relative), expected_kind="file")
        for name, relative in raw_expected.items()
    }
    for path in expected_artifacts.values():
        if path.suffix.lower() in {".yaml", ".yml"}:
            artifact_doc = load_yaml(path)
            if isinstance(artifact_doc, Mapping):
                _validate_declared_schema(artifact_doc, path, required=False)
                _reject_nondeterministic_dependencies(artifact_doc, path.name)
        elif path.suffix.lower() in {".md", ".markdown"}:
            load_markdown_frontmatter(path)

    stable_settings = scenario_doc.get("stable_settings")
    if stable_settings is None:
        stable_settings = _load_project_settings(source_workspace)
    stable_settings = _require_mapping(stable_settings, "scenario.stable_settings")
    decisions = _require_mapping(scenario_doc.get("decisions", {}), "scenario.decisions")

    evidence = _load_evidence(scenario_doc)
    if not evidence:
        discovery_path = expected_artifacts.get("discovery_report")
        if discovery_path is not None:
            discovery_doc = load_yaml(discovery_path)
            if isinstance(discovery_doc, Mapping):
                evidence = _load_evidence(discovery_doc)

    try:
        return Scenario(
            scenario_id=str(scenario_doc["scenario_id"]),
            phase=int(scenario_doc["phase"]),
            user_request=str(scenario_doc.get("request", scenario_doc.get("user_request", ""))),
            stable_settings=stable_settings,
            decisions=decisions,
            transcript=_load_turns(transcript_doc, fixture_root),
            evidence=evidence,
            expected_artifacts=expected_artifacts,
            actions=_load_actions(action_doc),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FixtureLoadError("FIXTURE_SCHEMA_INVALID", SCENARIO_FILE, str(exc)) from exc


def materialize_source_workspace(
    fixture_dir: Path,
    tmp_path: Path,
    *,
    destination_name: str = "fixture-workspace",
) -> Path:
    """Copy the fixture source workspace into an isolated writable directory.

    The caller must provide an existing temporary directory (normally pytest's
    ``tmp_path``).  Neither the fixture tree nor any path outside that directory
    is modified.
    """
    fixture_root = Path(fixture_dir).resolve(strict=True)
    scenario_path = resolve_fixture_path(fixture_root, SCENARIO_FILE, expected_kind="file")
    scenario_doc = _require_mapping(load_yaml(scenario_path), SCENARIO_FILE)
    _validate_declared_schema(scenario_doc, scenario_path, required=True)
    _reject_nondeterministic_dependencies(scenario_doc, "scenario")
    source = resolve_fixture_path(
        fixture_root,
        str(scenario_doc.get("source_workspace", "source-workspace")),
        expected_kind="directory",
    )

    tmp_root = Path(tmp_path).resolve(strict=True)
    if not tmp_root.is_dir():
        raise FixtureLoadError("FIXTURE_TMP_NOT_DIRECTORY", _location(tmp_root), "tmp_path must be an existing directory")
    destination = resolve_fixture_path(
        tmp_root, destination_name, must_exist=False
    )
    if destination == tmp_root:
        raise FixtureLoadError("FIXTURE_WRITE_ESCAPED", destination_name, "destination must be below tmp_path")
    if destination.exists():
        raise FixtureLoadError("FIXTURE_DESTINATION_EXISTS", destination_name, "destination already exists")

    # resolve_fixture_path checked the source tree root. Reject links anywhere
    # below it before shutil can follow or reproduce them.
    for source_path in source.rglob("*"):
        if source_path.is_symlink():
            relative = source_path.relative_to(fixture_root).as_posix()
            raise FixtureLoadError("FIXTURE_PATH_SYMLINK", relative, "source workspace contains a symlink")
    shutil.copytree(source, destination, symlinks=False)
    return destination


# Concise compatibility aliases for tests that describe the operation as a copy.
copy_source_workspace = materialize_source_workspace
materialize_workspace = materialize_source_workspace


__all__ = [
    "FixtureLoadError",
    "SCHEMA_VERSION",
    "copy_source_workspace",
    "load_markdown",
    "load_markdown_frontmatter",
    "load_scenario",
    "load_yaml",
    "materialize_source_workspace",
    "materialize_workspace",
    "resolve_fixture_path",
]
