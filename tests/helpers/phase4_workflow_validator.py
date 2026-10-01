"""Pure workflow, grill, and decision validation for Phase 4 fixtures.

This test-only module interprets already-recorded scenario data.  It never
advances a workflow, writes an artifact, or invokes an external operation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any, Optional

from .phase4_fixture_loader import FixtureLoadError, load_markdown_frontmatter
from .phase4_models import (
    APPROVAL_BLOCKING_DECISION_KEYS,
    FORBIDDEN_PHASE4_STATES,
    MATERIAL_DECISION_KEYS,
    PHASE4_TERMINAL_STATE,
    STABLE_SETTING_KEYS,
    WORKFLOW_STATES,
    Decision,
    Diagnostic,
    Scenario,
    Turn,
    ValidationResult,
)

_ALLOWED_ORIGINS = frozenset(
    {"user", "project_setting", "prior_evidence", "agent_default"}
)
_VAGUE_ANSWERS = frozenset(
    {
        "",
        "idk",
        "i don't know",
        "i do not know",
        "not sure",
        "unsure",
        "unknown",
        "whatever",
        "you decide",
    }
)
_QUESTION_KINDS = frozenset({"question", "grill_question"})
_ANSWER_KINDS = frozenset({"answer", "grill_answer"})
_UPDATE_KINDS = frozenset({"decision_update", "ledger_update", "agent_default"})
_DISCOVERY_KINDS = frozenset({"discovery", "discovery_report", "discovered"})
_ARTIFACT_KINDS = frozenset(
    {"artifact_generation", "artifacts_generated", "artifacts_validated", "plan"}
)
_APPROVAL_SUMMARY_KINDS = frozenset(
    {"approval_summary", "approval_request", "awaiting_approval"}
)
_CONFLICT_KINDS = frozenset({"evidence_conflict", "decision_conflict"})

# These aliases are intentionally conservative.  They are used only to detect
# clearly bundled prompts such as "Which metric and baseline should we use?";
# structured decision_key remains the source of truth for question identity.
_DECISION_TEXT_ALIASES = {
    "research_objective": re.compile(r"\b(?:objective|research question)\b", re.I),
    "baseline": re.compile(r"\bbaseline\b", re.I),
    "primary_metric": re.compile(r"\b(?:primary )?metric\b", re.I),
    "success_criteria": re.compile(r"\b(?:success criteri(?:on|a)|threshold)\b", re.I),
    "ablation_scope": re.compile(r"\b(?:ablation scope|rank(?:s| range)?)\b", re.I),
    "controlled_parameters": re.compile(
        r"\b(?:controlled? (?:parameter|setting)s?|hyperparameters?|controls?)\b",
        re.I,
    ),
}


@dataclass(frozen=True)
class _DecisionView:
    key: str
    value: Any
    origin: str
    rationale: str
    evidence_ids: tuple[str, ...]
    resolved: bool
    assumption: bool


def _diag(
    scenario_id: str,
    requirement: str,
    code: str,
    location: str,
    message: str,
) -> Diagnostic:
    return Diagnostic(scenario_id, requirement, code, location, message)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (Mapping, Sequence)) and not isinstance(value, (str, bytes)):
        return bool(value)
    return True


def _decision_view(key: str, value: Any) -> Optional[_DecisionView]:
    if isinstance(value, Decision):
        return _DecisionView(
            key=value.key,
            value=value.value,
            origin=value.origin,
            rationale=value.rationale,
            evidence_ids=tuple(value.evidence_ids),
            resolved=value.resolved,
            assumption=value.assumption,
        )
    if not isinstance(value, Mapping):
        return None
    evidence = value.get("evidence_ids", ())
    if isinstance(evidence, str):
        evidence = (evidence,)
    elif not isinstance(evidence, Sequence):
        evidence = ()
    return _DecisionView(
        key=str(value.get("key", key)),
        value=value.get("value"),
        origin=str(value.get("origin", "")),
        rationale=str(value.get("rationale", "")),
        evidence_ids=tuple(str(item) for item in evidence),
        resolved=value.get("resolved") is True,
        assumption=value.get("assumption") is True,
    )


def _is_vague(turn: Turn) -> bool:
    candidate = turn.value if turn.value is not None else turn.text
    if not isinstance(candidate, str):
        return not _present(candidate)
    normalized = re.sub(r"[.!?]+$", "", candidate.strip().lower())
    return normalized in _VAGUE_ANSWERS


def _bundles_questions(text: str) -> bool:
    if text.count("?") != 1:
        return True
    matched = [
        key for key, pattern in _DECISION_TEXT_ALIASES.items() if pattern.search(text)
    ]
    if len(matched) < 2:
        return False
    return bool(re.search(r"\b(?:and|or|also)\b", text, re.I))


def derive_workflow_states(scenario: Scenario) -> tuple[str, ...]:
    """Derive normalized state observations from a structured transcript.

    Artifact generation is treated as validated fixture output; artifact
    semantics themselves are checked by ``phase4_artifact_validator``.
    """
    states: list[str] = []

    def append(state: str) -> None:
        if not states or states[-1] != state:
            states.append(state)

    for turn in scenario.transcript:
        kind = turn.kind.strip().lower()
        if kind == "request":
            append("requested")
        elif kind in _DISCOVERY_KINDS:
            append("discovered")
        elif kind in _QUESTION_KINDS or kind in _ANSWER_KINDS or kind in _UPDATE_KINDS:
            append("grilling")
        elif kind == "decisions_resolved":
            append("decisions_resolved")
        elif kind in _ARTIFACT_KINDS:
            if "decisions_resolved" not in states:
                append("decisions_resolved")
            append("artifacts_validated")
        elif kind in _APPROVAL_SUMMARY_KINDS:
            append("awaiting_approval")
        elif kind in FORBIDDEN_PHASE4_STATES:
            append(kind)
    return tuple(states)


def validate_state_sequence(
    states: Sequence[str], *, scenario_id: str = "phase4"
) -> ValidationResult:
    """Validate the exact ordered Phase 4 state progression.

    This low-level entry point is intended for property tests that generate
    reordered, truncated, duplicated, or forbidden state sequences.
    """
    diagnostics: list[Diagnostic] = []
    normalized = tuple(str(state).strip().lower() for state in states)

    for index, state in enumerate(normalized):
        location = f"workflow.states[{index}]"
        if state in FORBIDDEN_PHASE4_STATES:
            diagnostics.append(_diag(
                scenario_id, "1.2", "FLOW_FORBIDDEN_PHASE4_STATE", location,
                f"State '{state}' is beyond the Phase 4 approval boundary.",
            ))
        elif state not in WORKFLOW_STATES:
            diagnostics.append(_diag(
                scenario_id, "1.1", "FLOW_STATE_UNKNOWN", location,
                f"Unknown workflow state '{state}'.",
            ))

    if normalized != WORKFLOW_STATES:
        mismatch = next(
            (
                index
                for index, pair in enumerate(zip(normalized, WORKFLOW_STATES))
                if pair[0] != pair[1]
            ),
            min(len(normalized), len(WORKFLOW_STATES)),
        )
        diagnostics.append(_diag(
            scenario_id, "1.1", "FLOW_STATE_OUT_OF_ORDER",
            f"workflow.states[{mismatch}]",
            "Workflow states must follow request, discovery, grilling, decisions "
            "resolved, artifacts validated, and awaiting approval exactly once.",
        ))

    discovery = normalized.index("discovered") if "discovered" in normalized else None
    grill = normalized.index("grilling") if "grilling" in normalized else None
    if discovery is None or (grill is not None and discovery > grill):
        diagnostics.append(_diag(
            scenario_id, "1.1", "FLOW_DISCOVERY_OUT_OF_ORDER", "workflow.states",
            "Prior-research discovery must occur before Research Grill.",
        ))

    if not normalized or normalized[-1] != PHASE4_TERMINAL_STATE:
        diagnostics.append(_diag(
            scenario_id, "7.1", "FLOW_NOT_AWAITING_APPROVAL", "workflow.terminal_state",
            "Phase 4 must terminate while awaiting explicit approval.",
        ))
    return ValidationResult.from_diagnostics(diagnostics)


def validate_grill(
    transcript: Sequence[Turn],
    stable_settings: Mapping[str, Any],
    *,
    scenario_id: str = "phase4",
) -> ValidationResult:
    """Validate discovery ordering and focused answer/update sequencing."""
    diagnostics: list[Diagnostic] = []
    discovery_seen = False
    pending_key: Optional[str] = None
    pending_vague = False
    conflict_key: Optional[str] = None

    for position, turn in enumerate(transcript):
        kind = turn.kind.strip().lower()
        location = f"transcript.turns[{position}]"
        if kind in _DISCOVERY_KINDS:
            discovery_seen = True
            continue

        if kind in _CONFLICT_KINDS:
            conflict_key = turn.decision_key or turn.resolves
            continue

        if kind in _QUESTION_KINDS:
            key = str(turn.decision_key or "")
            if not discovery_seen:
                diagnostics.append(_diag(
                    scenario_id, "1.1", "FLOW_DISCOVERY_OUT_OF_ORDER", location,
                    "Research Grill question appears before prior-research discovery.",
                ))
            if pending_key is not None:
                code = (
                    "GRILL_INSUFFICIENT_ANSWER_UNHANDLED"
                    if pending_vague
                    else "GRILL_ANSWER_MISSING"
                )
                requirement = "3.4" if pending_vague else "3.2"
                diagnostics.append(_diag(
                    scenario_id, requirement, code, location,
                    f"Decision '{pending_key}' must be resolved or refined before another question.",
                ))
            populated_stable = key in STABLE_SETTING_KEYS and _present(stable_settings.get(key))
            if (not key or key not in MATERIAL_DECISION_KEYS) and not populated_stable:
                diagnostics.append(_diag(
                    scenario_id, "3.5", "GRILL_NON_MATERIAL_QUESTION",
                    f"{location}.decision_key",
                    "Each grill question must identify one Material_Decision.",
                ))
            if populated_stable:
                diagnostics.append(_diag(
                    scenario_id, "3.3", "GRILL_STABLE_SETTING_REASK",
                    f"{location}.decision_key",
                    f"Populated Project_Settings key '{key}' must be inherited, not re-asked.",
                ))
            if _bundles_questions(turn.text):
                diagnostics.append(_diag(
                    scenario_id, "3.1", "GRILL_MULTIPLE_QUESTIONS", location,
                    "An assistant grill turn must contain exactly one semantic question.",
                ))
            if conflict_key is not None:
                if key != conflict_key:
                    diagnostics.append(_diag(
                        scenario_id, "3.6", "GRILL_CONFLICT_NOT_CLARIFIED", location,
                        f"Evidence conflict for '{conflict_key}' requires one focused clarification question.",
                    ))
                conflict_key = None
            pending_key = key or None
            pending_vague = False
            continue

        if kind in _ANSWER_KINDS:
            resolved_key = str(turn.resolves or "")
            if pending_key is None or resolved_key != pending_key:
                diagnostics.append(_diag(
                    scenario_id, "3.2", "GRILL_ANSWER_DECISION_MISMATCH",
                    f"{location}.resolves",
                    "A grill answer must update the decision targeted by the preceding question.",
                ))
            elif _is_vague(turn):
                pending_vague = True
            else:
                pending_key = None
                pending_vague = False
            continue

        if kind in _UPDATE_KINDS:
            resolved_key = str(turn.resolves or turn.decision_key or "")
            if pending_key is not None and resolved_key == pending_key and _present(turn.value):
                pending_key = None
                pending_vague = False
            elif pending_key is not None:
                diagnostics.append(_diag(
                    scenario_id, "3.2", "GRILL_LEDGER_UPDATE_MISMATCH", location,
                    f"Ledger update must resolve pending decision '{pending_key}'.",
                ))

    if pending_key is not None:
        diagnostics.append(_diag(
            scenario_id, "3.2", "GRILL_DECISION_NOT_UPDATED", "transcript.end",
            f"Decision '{pending_key}' remains unanswered at the end of Research Grill.",
        ))
    if conflict_key is not None:
        diagnostics.append(_diag(
            scenario_id, "3.6", "GRILL_CONFLICT_NOT_CLARIFIED", "transcript.end",
            f"Evidence conflict for '{conflict_key}' was not clarified.",
        ))
    return ValidationResult.from_diagnostics(diagnostics)


def validate_decision_ledger(
    decisions: Mapping[str, Any],
    *,
    scenario_id: str = "phase4",
    approval_requested: bool = False,
    stable_settings: Optional[Mapping[str, Any]] = None,
) -> ValidationResult:
    """Validate material-decision completeness, provenance, and readiness."""
    diagnostics: list[Diagnostic] = []
    stable_settings = stable_settings or {}

    for key in sorted(MATERIAL_DECISION_KEYS):
        location = f"decisions.{key}"
        if key not in decisions:
            diagnostics.append(_diag(
                scenario_id, "4.1", "DECISION_REQUIRED_MISSING", location,
                f"Required Material_Decision '{key}' is not recorded.",
            ))
            if approval_requested and key in APPROVAL_BLOCKING_DECISION_KEYS:
                diagnostics.append(_diag(
                    scenario_id, "4.5", "DECISION_REQUIRED_UNRESOLVED", location,
                    f"Approval cannot be requested while '{key}' is unresolved.",
                ))
            continue

        view = _decision_view(key, decisions[key])
        if view is None:
            diagnostics.append(_diag(
                scenario_id, "4.1", "DECISION_RECORD_INVALID", location,
                "Decision must be a Decision model or mapping with value, origin, and resolved fields.",
            ))
            continue
        if view.key != key:
            diagnostics.append(_diag(
                scenario_id, "4.1", "DECISION_KEY_MISMATCH", f"{location}.key",
                f"Decision record key '{view.key}' does not match ledger key '{key}'.",
            ))
        if view.origin not in _ALLOWED_ORIGINS:
            diagnostics.append(_diag(
                scenario_id, "4.4", "DECISION_ORIGIN_INVALID", f"{location}.origin",
                "Decision origin must be user, project_setting, prior_evidence, or agent_default.",
            ))
        resolved = view.resolved and _present(view.value)
        if not resolved:
            diagnostics.append(_diag(
                scenario_id, "4.1", "DECISION_REQUIRED_UNRESOLVED", location,
                f"Required Material_Decision '{key}' has no resolved value.",
            ))
            if approval_requested and key in APPROVAL_BLOCKING_DECISION_KEYS:
                diagnostics.append(_diag(
                    scenario_id, "4.5", "DECISION_APPROVAL_BLOCKED", location,
                    f"Approval summary must be deferred until '{key}' is resolved.",
                ))

        if view.origin == "agent_default":
            if not view.rationale.strip():
                diagnostics.append(_diag(
                    scenario_id, "4.2", "DEFAULT_RATIONALE_MISSING",
                    f"{location}.rationale",
                    "Agent_Default requires a non-empty rationale.",
                ))
            if not view.evidence_ids and not view.assumption:
                diagnostics.append(_diag(
                    scenario_id, "4.2", "DEFAULT_SUPPORT_MISSING", location,
                    "Agent_Default requires evidence_ids or assumption: true.",
                ))
            if key in STABLE_SETTING_KEYS and _present(stable_settings.get(key)):
                diagnostics.append(_diag(
                    scenario_id, "4.4", "PROJECT_SETTING_MISLABELED_DEFAULT",
                    f"{location}.origin",
                    "An inherited Project_Settings value cannot be labeled Agent_Default.",
                ))
        elif view.origin == "prior_evidence" and not view.evidence_ids:
            diagnostics.append(_diag(
                scenario_id, "4.4", "DECISION_EVIDENCE_MISSING", location,
                "A prior_evidence decision origin requires at least one evidence_id.",
            ))

    return ValidationResult.from_diagnostics(diagnostics)


def _plan_state_diagnostics(scenario: Scenario) -> list[Diagnostic]:
    plan = scenario.expected_artifacts.get("plan")
    if plan is None:
        return []
    try:
        metadata, _ = load_markdown_frontmatter(plan)
    except (FixtureLoadError, OSError, ValueError) as exc:
        return [_diag(
            scenario.scenario_id, "1.2", "FLOW_PLAN_STATE_UNREADABLE", "expected.plan",
            f"Plan approval state could not be read: {exc}",
        )]

    diagnostics: list[Diagnostic] = []
    if metadata.get("status") != "awaiting_approval":
        diagnostics.append(_diag(
            scenario.scenario_id, "1.2", "FLOW_PLAN_NOT_AWAITING_APPROVAL",
            "expected.plan:status",
            "Experiment status must remain awaiting_approval before explicit approval.",
        ))
    approval = metadata.get("approval")
    approval_status = approval.get("status") if isinstance(approval, Mapping) else None
    if approval_status != "pending":
        diagnostics.append(_diag(
            scenario.scenario_id, "1.2", "FLOW_APPROVAL_NOT_PENDING",
            "expected.plan:approval.status",
            "Approval status must remain pending before explicit approval.",
        ))
    return diagnostics


def validate_workflow(
    scenario: Scenario,
    *,
    states: Optional[Sequence[str]] = None,
) -> ValidationResult:
    """Validate one complete Phase 4 scenario without performing any action.

    ``states`` is injectable for state-machine property tests.  Normal scenario
    and integration tests should omit it and use transcript-derived states.
    """
    diagnostics: list[Diagnostic] = []
    observed_states = tuple(states) if states is not None else derive_workflow_states(scenario)
    diagnostics.extend(
        validate_state_sequence(observed_states, scenario_id=scenario.scenario_id).diagnostics
    )
    diagnostics.extend(
        validate_grill(
            scenario.transcript,
            scenario.stable_settings,
            scenario_id=scenario.scenario_id,
        ).diagnostics
    )
    approval_requested = any(
        turn.kind.strip().lower() in _APPROVAL_SUMMARY_KINDS
        for turn in scenario.transcript
    )
    diagnostics.extend(
        validate_decision_ledger(
            scenario.decisions,
            scenario_id=scenario.scenario_id,
            approval_requested=approval_requested,
            stable_settings=scenario.stable_settings,
        ).diagnostics
    )
    diagnostics.extend(_plan_state_diagnostics(scenario))

    meaningful_turns = tuple(
        turn for turn in scenario.transcript if turn.kind.strip().lower() != "note"
    )
    if meaningful_turns:
        last = meaningful_turns[-1]
        if last.kind.strip().lower() not in _APPROVAL_SUMMARY_KINDS:
            diagnostics.append(_diag(
                scenario.scenario_id, "7.1", "FLOW_APPROVAL_SUMMARY_NOT_TERMINAL",
                f"transcript.turns[{len(scenario.transcript) - 1}]",
                "Approval_Summary must be the terminal Phase 4 turn.",
            ))
        elif not re.search(r"\b(?:approv(?:e|al)|modif(?:y|ication))\b", last.text, re.I):
            diagnostics.append(_diag(
                scenario.scenario_id, "7.1", "FLOW_APPROVAL_REQUEST_MISSING",
                f"transcript.turns[{len(scenario.transcript) - 1}].text",
                "Terminal Approval_Summary must request approval or modification.",
            ))

    return ValidationResult.from_diagnostics(diagnostics)


# Discoverable aliases for upcoming scenario, integration, and property tests.
validate_scenario_workflow = validate_workflow
validate_workflow_states = validate_state_sequence
validate_research_grill = validate_grill
validate_decisions = validate_decision_ledger


__all__ = [
    "derive_workflow_states",
    "validate_decision_ledger",
    "validate_decisions",
    "validate_grill",
    "validate_research_grill",
    "validate_scenario_workflow",
    "validate_state_sequence",
    "validate_workflow",
    "validate_workflow_states",
]
