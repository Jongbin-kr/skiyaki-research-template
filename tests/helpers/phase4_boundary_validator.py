"""Pure boundary and preservation checks for Phase 4 planning fixtures.

This test-only module treats commands as inert text.  It never invokes a
subprocess, imports an integration client, or accesses the network.  The only
filesystem operations are local path inspection and byte reads used to build
protected-path snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from types import MappingProxyType
from typing import Iterable, Mapping, Optional, Sequence

from .phase4_models import (
    Diagnostic,
    EXTERNAL_PHASES,
    ObservedAction,
    Scenario,
    ValidationResult,
)


_ROOT_PROJECT_RECORDS = (
    "project-plan.md",
    "project-log.md",
)
_DEFAULT_PROTECTED_PATHS = (
    "experiments/example-lora-rank-ablation",
    *_ROOT_PROJECT_RECORDS,
)

_READ_KINDS = frozenset({"local_read", "read", "file_read", "repository_read"})
_WRITE_KINDS = frozenset({"local_write", "write", "file_write", "planning_write"})
_COMMAND_KINDS = frozenset(
    {"command", "execute", "execution", "invoke", "run", "shell", "subprocess"}
)

_FENCED_COMMAND = re.compile(
    r"```(?:bash|console|sh|shell|zsh)?[ \t]*\n(?P<body>.*?)```",
    re.IGNORECASE | re.DOTALL,
)
_INLINE_COMMAND = re.compile(r"(?<!`)`(?P<body>[^`\n]+)`(?!`)")
_URL_OR_REMOTE = re.compile(r"(?i)^(?:https?|ssh)://|^[^/\s]+@[^:\s]+:")
_RUN_PATH = re.compile(r"(?:^|/)runs(?:/|$)", re.IGNORECASE)

# Patterns are deliberately command-oriented.  Merely documenting a planned
# entrypoint or destination outside a command span must remain valid in Phase 4.
_COMMAND_RULES = (
    (
        "execution",
        re.compile(
            r"(?ix)(?:^|[;&|]\s*)(?:(?:(?:python(?:3(?:\.\d+)?)?|uv\s+run|"
            r"accelerate\s+launch|torchrun)\s+)(?:\./)?"
            r"(?:[^\s;&|]+[/\\])*(?:train|training|evaluate|evaluation|eval)"
            r"(?:[_-][\w.-]+)?\.py\b|\./(?:[^\s;&|]+[/\\])*"
            r"(?:train|training|evaluate|evaluation|eval)(?:[_-][\w.-]+)?\.py\b)"
        ),
    ),
    (
        "run",
        re.compile(
            r"(?ix)(?:initialize[_-]?run(?:\.py)?\b|(?:mkdir|touch|cp|mv|tee)\b"
            r"[^\n;&|]*\bruns[/\\])"
        ),
    ),
    (
        "ssh",
        re.compile(r"(?im)(?:^|[;&|]\s*|\bsudo\s+)(?:ssh|scp|sftp|mosh)\b|\brsync\b[^\n]*(?:ssh|[^\s]+@[^:]+:)"),
    ),
    (
        "slurm",
        re.compile(r"(?im)(?:^|[;&|]\s*|\bsudo\s+)(?:sbatch|srun|squeue|scancel|sacct|scontrol|sinfo)\b"),
    ),
    (
        "wandb",
        re.compile(r"(?im)(?:^|[;&|]\s*)(?:wandb\b|python[^\n;&|]*\b(?:import\s+wandb|wandb\.(?:init|login|Api|sync)\b))"),
    ),
    (
        "huggingface",
        re.compile(
            r"(?im)(?:^|[;&|]\s*)(?:(?:huggingface-cli|hf)\b|"
            r"python[^\n;&|]*\b(?:huggingface_hub|HfApi|upload_(?:file|folder))\b)"
        ),
    ),
    (
        "git",
        re.compile(r"(?im)(?:^|[;&|]\s*)git\s+(?:-[^\s]+\s+)*commit\b"),
    ),
)

_STRUCTURED_FAMILIES = {
    "ssh": "ssh",
    "scp": "ssh",
    "sftp": "ssh",
    "remote_access": "ssh",
    "slurm": "slurm",
    "sbatch": "slurm",
    "srun": "slurm",
    "wandb": "wandb",
    "wandb_api": "wandb",
    "wandb_cli": "wandb",
    "huggingface": "huggingface",
    "hugging_face": "huggingface",
    "huggingface_hub": "huggingface",
    "hf_hub": "huggingface",
}
_EXECUTION_KINDS = frozenset(
    {
        "train",
        "training",
        "evaluate",
        "evaluation",
        "entrypoint",
        "entrypoint_execution",
        "training_execution",
        "evaluation_execution",
    }
)
_RUN_KINDS = frozenset(
    {"run_create", "run_created", "run_initialize", "run_initialization", "run_write"}
)
_GIT_COMMIT_KINDS = frozenset({"git_commit", "commit"})


@dataclass(frozen=True)
class ProtectedPathSnapshot:
    """Stable inventory and SHA-256 state for protected repository paths."""

    repository_root: str
    protected_paths: tuple[str, ...]
    inventory: tuple[str, ...]
    digests: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "protected_paths", tuple(self.protected_paths))
        object.__setattr__(self, "inventory", tuple(self.inventory))
        object.__setattr__(self, "digests", MappingProxyType(dict(self.digests)))


def _normalize_kind(kind: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(kind).strip().lower()).strip("_")


def _location(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_repository_path(repository_root: Path, value: str | Path) -> Path:
    """Resolve a protected path beneath ``repository_root`` without traversal."""
    raw = str(value)
    portable = PurePosixPath(raw.replace("\\", "/"))
    windows = PureWindowsPath(raw)
    if portable.is_absolute() or windows.is_absolute() or ".." in portable.parts:
        raise ValueError(f"protected path is not repository-relative: {raw}")
    root = repository_root.resolve(strict=True)
    candidate = root.joinpath(*portable.parts).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"protected path escapes repository root: {raw}") from exc
    return candidate


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_protected_paths(
    repository_root: Path,
    protected_paths: Iterable[str | Path] = (),
    *,
    include_defaults: bool = True,
) -> ProtectedPathSnapshot:
    """Inventory and hash protected paths using local reads only.

    Missing protected roots are retained in ``protected_paths`` but contribute
    no inventory entry. Directories, regular files, and symlinks are inventoried;
    SHA-256 digests are recorded for regular files and symlink target text.
    """
    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository_root must be a directory")

    requested = list(_DEFAULT_PROTECTED_PATHS if include_defaults else ())
    requested.extend(str(path) for path in protected_paths)
    normalized = tuple(sorted(dict.fromkeys(PurePosixPath(item.replace("\\", "/")).as_posix() for item in requested)))

    inventory: set[str] = set()
    digests: dict[str, str] = {}
    for relative in normalized:
        protected = _safe_repository_path(root, relative)
        if not protected.exists() and not protected.is_symlink():
            continue
        paths = [protected]
        if protected.is_dir() and not protected.is_symlink():
            paths.extend(sorted(protected.rglob("*"), key=lambda item: item.as_posix()))
        for item in paths:
            name = _location(item, root)
            if item.is_symlink():
                inventory.add(f"symlink:{name}")
                digests[name] = hashlib.sha256(
                    str(item.readlink()).encode("utf-8")
                ).hexdigest()
            elif item.is_dir():
                inventory.add(f"directory:{name}")
            elif item.is_file():
                inventory.add(f"file:{name}")
                digests[name] = _hash_file(item)
            else:
                inventory.add(f"other:{name}")

    return ProtectedPathSnapshot(
        repository_root=root.as_posix(),
        protected_paths=normalized,
        inventory=tuple(sorted(inventory)),
        digests={name: digests[name] for name in sorted(digests)},
    )


def compare_protected_snapshots(
    before: ProtectedPathSnapshot,
    after: ProtectedPathSnapshot,
    *,
    scenario_id: str,
) -> ValidationResult:
    """Report any protected path, inventory, or byte-digest mutation."""
    diagnostics: list[Diagnostic] = []
    if before.protected_paths != after.protected_paths:
        diagnostics.append(
            Diagnostic(
                scenario_id,
                "9.5",
                "PROTECTED_PATH_SET_CHANGED",
                "protected_paths",
                "Protected path declarations changed during validation.",
            )
        )

    before_inventory = set(before.inventory)
    after_inventory = set(after.inventory)
    for entry in sorted(before_inventory - after_inventory):
        diagnostics.append(
            Diagnostic(
                scenario_id,
                "9.5",
                "PROTECTED_PATH_REMOVED",
                entry.split(":", 1)[-1],
                "A protected path inventory entry was removed.",
            )
        )
    for entry in sorted(after_inventory - before_inventory):
        diagnostics.append(
            Diagnostic(
                scenario_id,
                "9.5",
                "PROTECTED_PATH_ADDED",
                entry.split(":", 1)[-1],
                "A protected path inventory entry was added.",
            )
        )
    for name in sorted(set(before.digests) & set(after.digests)):
        if before.digests[name] != after.digests[name]:
            diagnostics.append(
                Diagnostic(
                    scenario_id,
                    "9.5",
                    "PROTECTED_CONTENT_CHANGED",
                    name,
                    "Protected path content changed during validation.",
                )
            )
    return ValidationResult.from_diagnostics(diagnostics)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_action_target(target: str, fixture_workspace: Path) -> Optional[Path]:
    raw = str(target).strip()
    portable = PurePosixPath(raw.replace("\\", "/"))
    windows = PureWindowsPath(raw)
    if windows.is_absolute() and not Path(raw).is_absolute():
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        if ".." in portable.parts:
            return None
        candidate = fixture_workspace.joinpath(*portable.parts)
    try:
        return candidate.resolve(strict=False)
    except OSError:
        return None


def _family_for_action(action: ObservedAction) -> Optional[str]:
    kind = _normalize_kind(action.kind)
    target = _normalize_kind(action.target)
    for token, family in _STRUCTURED_FAMILIES.items():
        if kind == token or kind.startswith(f"{token}_"):
            return family
    if _URL_OR_REMOTE.search(action.target.strip()):
        return "ssh" if action.target.strip().lower().startswith("ssh:") else None
    if kind in _COMMAND_KINDS:
        for family, pattern in _COMMAND_RULES:
            if family in EXTERNAL_PHASES and pattern.search(action.command or action.target):
                return family
    # Explicit metadata can classify an otherwise generic structured action.
    integration = _normalize_kind(str(action.metadata.get("integration", "")))
    return _STRUCTURED_FAMILIES.get(integration)


def _diagnostic_for_command(
    command: str,
    *,
    scenario_id: str,
    location: str,
) -> Optional[Diagnostic]:
    for family, pattern in _COMMAND_RULES:
        if not pattern.search(command):
            continue
        if family in EXTERNAL_PHASES:
            phase = EXTERNAL_PHASES[family]
            return Diagnostic(
                scenario_id,
                "8.4",
                "BOUNDARY_EXTERNAL_OPERATION",
                location,
                f"Blocked {family} operation; live use is unavailable until Phase {phase}.",
            )
        if family == "run":
            return Diagnostic(
                scenario_id,
                "8.1",
                "BOUNDARY_RUN_CREATED",
                location,
                "Run initialization or Run content is prohibited in Phase 4.",
            )
        if family == "git":
            return Diagnostic(
                scenario_id,
                "8.3",
                "BOUNDARY_GIT_COMMIT",
                location,
                "Git commit creation is prohibited in Phase 4.",
            )
        return Diagnostic(
            scenario_id,
            "8.4",
            "BOUNDARY_EXECUTION_ATTEMPT",
            location,
            "Training or evaluation entrypoint invocation is prohibited in Phase 4.",
        )
    return None


def extract_shell_commands(text: str) -> tuple[tuple[str, str], ...]:
    """Extract fenced and inline command spans without interpreting them."""
    spans: list[tuple[int, str, str]] = []
    fenced_ranges: list[tuple[int, int]] = []
    for match in _FENCED_COMMAND.finditer(str(text)):
        fenced_ranges.append(match.span())
        spans.append((match.start(), "fence", match.group("body").strip()))
    for match in _INLINE_COMMAND.finditer(str(text)):
        if any(start <= match.start() < end for start, end in fenced_ranges):
            continue
        spans.append((match.start(), "inline", match.group("body").strip()))
    return tuple((kind, command) for _, kind, command in sorted(spans))


def validate_observed_actions(
    actions: Sequence[ObservedAction],
    *,
    fixture_workspace: Path,
    scenario_id: str,
) -> ValidationResult:
    """Validate declared actions without performing any declared operation."""
    workspace = Path(fixture_workspace).resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("fixture_workspace must be a directory")
    diagnostics: list[Diagnostic] = []

    for index, action in enumerate(actions):
        location = f"action-manifest.actions[{index}]"
        kind = _normalize_kind(action.kind)
        family = _family_for_action(action)
        if family is not None:
            diagnostics.append(
                Diagnostic(
                    scenario_id,
                    "8.2",
                    "BOUNDARY_EXTERNAL_OPERATION",
                    location,
                    f"Blocked {family} operation; live use is unavailable until Phase {EXTERNAL_PHASES[family]}.",
                )
            )
            continue
        if kind in _EXECUTION_KINDS:
            diagnostics.append(
                Diagnostic(scenario_id, "8.4", "BOUNDARY_EXECUTION_ATTEMPT", location,
                           "Training or evaluation entrypoint invocation is prohibited in Phase 4.")
            )
            continue
        if kind in _RUN_KINDS or _RUN_PATH.search(action.target.replace("\\", "/")):
            diagnostics.append(
                Diagnostic(scenario_id, "8.1", "BOUNDARY_RUN_CREATED", location,
                           "Run initialization or Run content is prohibited in Phase 4.")
            )
            continue
        if kind in _GIT_COMMIT_KINDS:
            diagnostics.append(
                Diagnostic(scenario_id, "8.3", "BOUNDARY_GIT_COMMIT", location,
                           "Git commit creation is prohibited in Phase 4.")
            )
            continue
        if action.command:
            command_diagnostic = _diagnostic_for_command(
                action.command, scenario_id=scenario_id, location=f"{location}.command"
            )
            if command_diagnostic is not None:
                diagnostics.append(command_diagnostic)
                continue
        if kind in _READ_KINDS:
            if _URL_OR_REMOTE.search(action.target.strip()):
                diagnostics.append(
                    Diagnostic(scenario_id, "1.3", "BOUNDARY_READ_NOT_LOCAL", location,
                               "Phase 4 permits repository-local reads only.")
                )
            continue
        if kind in _WRITE_KINDS:
            resolved = _resolve_action_target(action.target, workspace)
            if resolved is None or not _is_within(resolved, workspace):
                diagnostics.append(
                    Diagnostic(scenario_id, "9.4", "FIXTURE_WRITE_ESCAPED", location,
                               "Declared write is outside the Fixture_Workspace.")
                )
            continue
        if kind in _COMMAND_KINDS:
            diagnostics.append(
                Diagnostic(scenario_id, "1.3", "BOUNDARY_ACTION_NOT_ALLOWED", location,
                           "Phase 4 permits only local reads and Fixture_Workspace writes.")
            )
            continue
        diagnostics.append(
            Diagnostic(scenario_id, "1.3", "BOUNDARY_ACTION_NOT_ALLOWED", location,
                       "Unknown structured action is not allowed in Phase 4.")
        )

    return ValidationResult.from_diagnostics(diagnostics)


def validate_command_texts(
    texts: Mapping[str, str] | Iterable[tuple[str, str]],
    *,
    scenario_id: str,
) -> ValidationResult:
    """Scan fenced and inline commands in assistant-authored text."""
    items = texts.items() if isinstance(texts, Mapping) else texts
    diagnostics: list[Diagnostic] = []
    for location, text in sorted(items, key=lambda item: str(item[0])):
        for ordinal, (span_kind, command) in enumerate(extract_shell_commands(text)):
            diagnostic = _diagnostic_for_command(
                command,
                scenario_id=scenario_id,
                location=f"{str(location).replace(chr(92), '/')}:{span_kind}[{ordinal}]",
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    return ValidationResult.from_diagnostics(diagnostics)


def _scenario_command_texts(scenario: Scenario) -> dict[str, str]:
    texts = {
        f"transcript.turns[{turn.index}]": turn.text
        for turn in scenario.transcript
        if turn.actor.strip().lower() == "assistant" and turn.text
    }
    for name, path in scenario.expected_artifacts.items():
        if path.suffix.lower() not in {".md", ".markdown"}:
            continue
        try:
            texts[f"expected.{name}"] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            # Fixture loading owns read/schema diagnostics. Boundary validation
            # remains pure and does not duplicate those failures.
            continue
    return texts


def validate_boundary(
    scenario: Scenario,
    *,
    fixture_workspace: Path,
    command_texts: Optional[Mapping[str, str] | Iterable[tuple[str, str]]] = None,
) -> ValidationResult:
    """Validate all Phase 4 action, command, and write boundaries."""
    diagnostics = list(
        validate_observed_actions(
            scenario.actions,
            fixture_workspace=fixture_workspace,
            scenario_id=scenario.scenario_id,
        ).diagnostics
    )
    texts = _scenario_command_texts(scenario) if command_texts is None else command_texts
    diagnostics.extend(
        validate_command_texts(texts, scenario_id=scenario.scenario_id).diagnostics
    )
    return ValidationResult.from_diagnostics(diagnostics)


# Compatibility aliases use the terminology from the design and task text.
create_protected_snapshot = snapshot_protected_paths
compare_snapshots = compare_protected_snapshots
validate_boundary_and_commands = validate_boundary
validate_actions = validate_observed_actions


__all__ = [
    "ProtectedPathSnapshot",
    "compare_protected_snapshots",
    "compare_snapshots",
    "create_protected_snapshot",
    "extract_shell_commands",
    "snapshot_protected_paths",
    "validate_actions",
    "validate_boundary",
    "validate_boundary_and_commands",
    "validate_command_texts",
    "validate_observed_actions",
]
