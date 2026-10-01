"""Immutable, test-only data models for Phase 4 planning validation.

The constants and structures in this module describe fixture data; they do not
perform workflow actions or contact external systems.
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Tuple


# Project settings that the research grill consumes without asking again.
STABLE_SETTING_KEYS = frozenset(
    {
        "environment.manager",
        "execution.default_target",
        "execution.ssh_host",
        "execution.remote_project_root",
        "execution.require_slurm_for_gpu",
        "execution.require_slurm_for_cpu_heavy",
        "slurm.partition",
        "slurm.account",
        "slurm.qos",
        "slurm.max_gpus_per_job",
        "slurm.max_concurrent_jobs",
        "wandb.entity",
        "wandb.project",
        "wandb.mode",
        "huggingface.namespace",
        "huggingface.private",
        "huggingface.push_policy",
    }
)

# Decisions required for a reviewable plan and the subset that blocks approval.
MATERIAL_DECISION_KEYS = frozenset(
    {
        "research_objective",
        "baseline",
        "primary_metric",
        "success_criteria",
        "ablation_scope",
        "controlled_parameters",
    }
)
REQUIRED_MATERIAL_DECISIONS = MATERIAL_DECISION_KEYS
APPROVAL_BLOCKING_DECISION_KEYS = frozenset(
    {"baseline", "primary_metric", "success_criteria"}
)

# The ordered Phase 4 state machine. Later execution states are intentionally
# excluded from the valid sequence and listed separately for guard validation.
WORKFLOW_STATES = (
    "requested",
    "discovered",
    "grilling",
    "decisions_resolved",
    "artifacts_validated",
    "awaiting_approval",
)
PHASE4_WORKFLOW_STATES = WORKFLOW_STATES
PHASE4_TERMINAL_STATE = "awaiting_approval"
FORBIDDEN_PHASE4_STATES = frozenset(
    {"approved", "run_created", "submitted", "running"}
)

# External operations are metadata-only until their roadmap phase is available.
EXTERNAL_PHASES = MappingProxyType(
    {
        "ssh": 6,
        "slurm": 6,
        "wandb": 7,
        "huggingface": 8,
    }
)
EXTERNAL_OPERATION_PHASES = EXTERNAL_PHASES

_DIAGNOSTIC_TIMESTAMP_PATTERNS = (
    re.compile(r"\b\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"),
    re.compile(r"\b\d{8}T\d{6}(?:Z)?\b"),
)
_TEMP_PATH_PATTERN = re.compile(
    r"(?i)(?:[A-Za-z]:)?/(?:private/)?(?:var/(?:folders|tmp)|tmp|temp)(?:/[^\s,;:)\]}]+)*"
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(token|password|api[_-]?key|private[_-]?key|secret)\b"
    r"(\s*[:=]\s*)(?:[^\s,;]+|\"[^\"]*\"|'[^']*')"
)
_CREDENTIAL_PREFIX_PATTERN = re.compile(
    r"\b(?:hf_[A-Za-z0-9]{8,}|(?:api|key|secret)-[A-Za-z0-9_-]{8,})\b"
)


def _immutable_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a read-only shallow copy with deterministic insertion order."""
    return MappingProxyType(dict(value))


def normalize_diagnostic_message(message: str) -> str:
    """Normalize volatile or sensitive diagnostic text deterministically.

    The normalization removes known timestamp forms, redacts secret-like
    assignments and credential tokens, replaces absolute temporary paths, and
    uses POSIX separators so diagnostics compare equally across platforms.
    """
    normalized = str(message).replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\\", "/")
    for pattern in _DIAGNOSTIC_TIMESTAMP_PATTERNS:
        normalized = pattern.sub("<timestamp>", normalized)
    normalized = _TEMP_PATH_PATTERN.sub("<tmp_path>", normalized)
    normalized = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: "%s%s<redacted>" % (match.group(1), match.group(2)),
        normalized,
    )
    normalized = _CREDENTIAL_PREFIX_PATTERN.sub("<redacted>", normalized)
    return "\n".join(line.rstrip() for line in normalized.strip().split("\n"))


@dataclass(frozen=True)
class Turn:
    """One structured user or assistant transcript turn."""

    index: int
    actor: str
    kind: str
    text: str = ""
    decision_key: Optional[str] = None
    resolves: Optional[str] = None
    value: Any = None
    artifact: Optional[Path] = None


@dataclass(frozen=True)
class EvidenceRecord:
    """A repository-backed evidence source and the claims it supports."""

    evidence_id: str
    source_type: str
    source_ref: str
    claims: Tuple[str, ...] = field(default_factory=tuple)
    content_digest: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "claims", tuple(self.claims))


@dataclass(frozen=True)
class Decision:
    """A material planning decision with explicit provenance."""

    key: str
    value: Any
    origin: str
    rationale: str
    evidence_ids: Tuple[str, ...] = field(default_factory=tuple)
    resolved: bool = False
    assumption: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ids", tuple(self.evidence_ids))


@dataclass(frozen=True)
class ObservedAction:
    """A declared action for boundary and side-effect validation."""

    kind: str
    target: str
    command: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _immutable_mapping(self.metadata))


@dataclass(frozen=True)
class Scenario:
    """A complete, self-contained Phase 4 planning scenario."""

    scenario_id: str
    phase: int
    user_request: str
    stable_settings: Mapping[str, Any]
    decisions: Mapping[str, Any]
    transcript: Tuple[Turn, ...]
    evidence: Tuple[EvidenceRecord, ...]
    expected_artifacts: Mapping[str, Path]
    actions: Tuple[ObservedAction, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "stable_settings", _immutable_mapping(self.stable_settings))
        object.__setattr__(self, "decisions", _immutable_mapping(self.decisions))
        object.__setattr__(self, "transcript", tuple(self.transcript))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(
            self, "expected_artifacts", _immutable_mapping(self.expected_artifacts)
        )
        object.__setattr__(self, "actions", tuple(self.actions))


@dataclass(frozen=True)
class Diagnostic:
    """A stable, requirement-addressed validation failure."""

    scenario_id: str
    requirement: str
    code: str
    location: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "location", self.location.replace("\\", "/"))
        object.__setattr__(
            self, "message", normalize_diagnostic_message(self.message)
        )

    @property
    def sort_key(self) -> Tuple[str, str, str]:
        """Return the canonical deterministic diagnostic ordering key."""
        return (self.requirement, self.code, self.location)


def order_diagnostics(diagnostics: Iterable[Diagnostic]) -> Tuple[Diagnostic, ...]:
    """Return diagnostics in the canonical deterministic order."""
    return tuple(sorted(diagnostics, key=lambda diagnostic: diagnostic.sort_key))


@dataclass(frozen=True)
class ValidationResult:
    """The deterministic result of validating one scenario."""

    valid: bool
    diagnostics: Tuple[Diagnostic, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", order_diagnostics(self.diagnostics))

    @classmethod
    def from_diagnostics(
        cls, diagnostics: Iterable[Diagnostic]
    ) -> "ValidationResult":
        """Build a result whose validity follows the presence of diagnostics."""
        ordered = order_diagnostics(diagnostics)
        return cls(valid=not ordered, diagnostics=ordered)
