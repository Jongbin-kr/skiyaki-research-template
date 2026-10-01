"""Property validation for Phase 4 workflow ordering, grilling, and decisions."""

from __future__ import annotations

from typing import Any

from hypothesis import given, settings, strategies as st

from helpers.phase4_models import (
    APPROVAL_BLOCKING_DECISION_KEYS,
    MATERIAL_DECISION_KEYS,
    STABLE_SETTING_KEYS,
    WORKFLOW_STATES,
    Decision,
    Turn,
)
from helpers.phase4_workflow_validator import (
    validate_decision_ledger,
    validate_grill,
    validate_state_sequence,
)


MATERIAL_QUESTIONS = {
    "research_objective": "What research objective should this ablation test?",
    "baseline": "Which baseline should this ablation use?",
    "primary_metric": "Which primary metric should determine success?",
    "success_criteria": "What success criterion should the ablation meet?",
    "ablation_scope": "Which ranks should the ablation scope include?",
    "controlled_parameters": "Which controls should remain fixed?",
}
STABLE_QUESTIONS = {
    "environment.manager": "Which environment manager should we use?",
    "execution.default_target": "Which execution target should we use?",
    "execution.ssh_host": "Which SSH host should we use?",
    "execution.remote_project_root": "Which remote path should we use?",
    "execution.require_slurm_for_gpu": "Should GPU work require Slurm?",
    "execution.require_slurm_for_cpu_heavy": "Should CPU-heavy work require Slurm?",
    "slurm.partition": "Which Slurm partition should we use?",
    "slurm.account": "Which Slurm account should we use?",
    "slurm.qos": "Which Slurm quality of service should we use?",
    "slurm.max_gpus_per_job": "What GPU quota should we use?",
    "slurm.max_concurrent_jobs": "What concurrent job quota should we use?",
    "wandb.entity": "Which W&B entity should we use?",
    "wandb.project": "Which W&B project should we use?",
    "wandb.mode": "Which W&B mode should we use?",
    "huggingface.namespace": "Which Hugging Face namespace should we use?",
    "huggingface.private": "Should Hugging Face artifacts be private?",
    "huggingface.push_policy": "Which Hugging Face push policy should we use?",
}
VAGUE_ANSWERS = ("", "idk", "I don't know", "not sure", "whatever", "you decide")
VALID_ORIGINS = ("user", "project_setting", "prior_evidence", "agent_default")


def _codes(result: Any) -> set[str]:
    return {diagnostic.code for diagnostic in result.diagnostics}


def _turn(
    index: int,
    actor: str,
    kind: str,
    text: str,
    *,
    decision_key: str | None = None,
    resolves: str | None = None,
    value: Any = None,
) -> Turn:
    return Turn(
        index=index,
        actor=actor,
        kind=kind,
        text=text,
        decision_key=decision_key,
        resolves=resolves,
        value=value,
    )


@settings(max_examples=100, deadline=None)
@given(
    mutation=st.sampled_from(("valid", "prefix", "swap", "forbidden")),
    cut=st.integers(min_value=0, max_value=len(WORKFLOW_STATES) - 1),
    swap_index=st.integers(min_value=0, max_value=len(WORKFLOW_STATES) - 2),
    forbidden=st.sampled_from(("approved", "run_created", "submitted", "running")),
)
def test_property_1_ordered_planning_state_transitions(
    mutation: str,
    cut: int,
    swap_index: int,
    forbidden: str,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 1: Ordered planning state transitions

    **Validates: Requirements 1.1, 3.2, 3.5, 5.1, 7.1, 9.2**
    """
    states = list(WORKFLOW_STATES)
    expected_codes: set[str] = set()

    if mutation == "prefix":
        states = states[:cut]
        expected_codes.update({"FLOW_STATE_OUT_OF_ORDER", "FLOW_NOT_AWAITING_APPROVAL"})
        if "discovered" not in states:
            expected_codes.add("FLOW_DISCOVERY_OUT_OF_ORDER")
    elif mutation == "swap":
        states[swap_index], states[swap_index + 1] = (
            states[swap_index + 1],
            states[swap_index],
        )
        expected_codes.add("FLOW_STATE_OUT_OF_ORDER")
        if swap_index == 1:
            expected_codes.add("FLOW_DISCOVERY_OUT_OF_ORDER")
        if swap_index == len(WORKFLOW_STATES) - 2:
            expected_codes.add("FLOW_NOT_AWAITING_APPROVAL")
    elif mutation == "forbidden":
        states.append(forbidden)
        expected_codes.update(
            {
                "FLOW_FORBIDDEN_PHASE4_STATE",
                "FLOW_STATE_OUT_OF_ORDER",
                "FLOW_NOT_AWAITING_APPROVAL",
            }
        )

    result = validate_state_sequence(states, scenario_id="property-1")

    if mutation == "valid":
        assert result.valid
        assert result.diagnostics == ()
    else:
        assert not result.valid
        assert expected_codes <= _codes(result)
        assert all(diagnostic.scenario_id == "property-1" for diagnostic in result.diagnostics)


@settings(max_examples=100, deadline=None)
@given(
    behavior=st.sampled_from(
        (
            "focused",
            "bundled",
            "stable_reask",
            "vague_default",
            "vague_unhandled",
            "conflict_clarified",
            "conflict_misdirected",
        )
    ),
    target=st.sampled_from(sorted(MATERIAL_DECISION_KEYS)),
    second_target=st.sampled_from(sorted(MATERIAL_DECISION_KEYS)),
    stable_target=st.sampled_from(sorted(STABLE_SETTING_KEYS)),
    vague_answer=st.sampled_from(VAGUE_ANSWERS),
)
def test_property_4_focused_non_redundant_grilling(
    behavior: str,
    target: str,
    second_target: str,
    stable_target: str,
    vague_answer: str,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 4: Focused, non-redundant grilling

    **Validates: Requirements 3.1, 3.3, 3.4, 3.6**
    """
    stable_settings: dict[str, Any] = {}
    transcript = [
        _turn(0, "assistant", "discovery_report", "Repository evidence inspected."),
    ]
    expected_codes: set[str] = set()

    if behavior == "stable_reask":
        stable_settings[stable_target] = "configured"
        transcript.extend(
            (
                _turn(
                    1,
                    "assistant",
                    "grill_question",
                    STABLE_QUESTIONS[stable_target],
                    decision_key=stable_target,
                ),
                _turn(
                    2,
                    "user",
                    "grill_answer",
                    "Use the configured value.",
                    resolves=stable_target,
                    value="configured",
                ),
            )
        )
        expected_codes.add("GRILL_STABLE_SETTING_REASK")
    elif behavior in {"conflict_clarified", "conflict_misdirected"}:
        question_target = target if behavior == "conflict_clarified" else second_target
        if behavior == "conflict_misdirected" and question_target == target:
            question_target = next(key for key in sorted(MATERIAL_DECISION_KEYS) if key != target)
        transcript.extend(
            (
                _turn(
                    1,
                    "assistant",
                    "evidence_conflict",
                    "The requested choice conflicts with prior evidence.",
                    decision_key=target,
                ),
                _turn(
                    2,
                    "assistant",
                    "grill_question",
                    MATERIAL_QUESTIONS[question_target],
                    decision_key=question_target,
                ),
                _turn(
                    3,
                    "user",
                    "grill_answer",
                    "This is an intentional deviation.",
                    resolves=question_target,
                    value="intentional deviation",
                ),
            )
        )
        if behavior == "conflict_misdirected":
            expected_codes.add("GRILL_CONFLICT_NOT_CLARIFIED")
    else:
        question_text = MATERIAL_QUESTIONS[target]
        if behavior == "bundled":
            other = second_target
            if other == target:
                other = next(key for key in sorted(MATERIAL_DECISION_KEYS) if key != target)
            question_text = f"Which {target.replace('_', ' ')} and {other.replace('_', ' ')} should we use?"
            expected_codes.add("GRILL_MULTIPLE_QUESTIONS")
        transcript.append(
            _turn(
                1,
                "assistant",
                "grill_question",
                question_text,
                decision_key=target,
            )
        )
        if behavior in {"vague_default", "vague_unhandled"}:
            transcript.append(
                _turn(
                    2,
                    "user",
                    "grill_answer",
                    vague_answer,
                    resolves=target,
                    value=vague_answer,
                )
            )
            if behavior == "vague_default":
                transcript.append(
                    _turn(
                        3,
                        "assistant",
                        "agent_default",
                        "Applying a labeled default.",
                        resolves=target,
                        value="evidence-backed default",
                    )
                )
            else:
                transcript.extend(
                    (
                        _turn(
                            3,
                            "assistant",
                            "grill_question",
                            MATERIAL_QUESTIONS[second_target],
                            decision_key=second_target,
                        ),
                        _turn(
                            4,
                            "user",
                            "grill_answer",
                            "resolved",
                            resolves=second_target,
                            value="resolved",
                        ),
                    )
                )
                expected_codes.add("GRILL_INSUFFICIENT_ANSWER_UNHANDLED")
        else:
            transcript.append(
                _turn(
                    2,
                    "user",
                    "grill_answer",
                    "resolved",
                    resolves=target,
                    value="resolved",
                )
            )

    result = validate_grill(
        transcript,
        stable_settings,
        scenario_id="property-4",
    )

    if behavior in {"focused", "vague_default", "conflict_clarified"}:
        assert result.valid
        assert result.diagnostics == ()
    else:
        assert not result.valid
        assert expected_codes <= _codes(result)
        assert all(diagnostic.scenario_id == "property-4" for diagnostic in result.diagnostics)


def _complete_ledger() -> dict[str, Decision]:
    return {
        key: Decision(
            key=key,
            value=f"resolved-{key}",
            origin="user",
            rationale="Explicitly selected by the user.",
            resolved=True,
        )
        for key in MATERIAL_DECISION_KEYS
    }


@settings(max_examples=100, deadline=None)
@given(
    target=st.sampled_from(sorted(MATERIAL_DECISION_KEYS)),
    origin=st.sampled_from(VALID_ORIGINS),
    default_support=st.sampled_from(("evidence", "assumption", "missing")),
    unresolved_blocker=st.one_of(
        st.none(), st.sampled_from(sorted(APPROVAL_BLOCKING_DECISION_KEYS))
    ),
)
def test_property_5_decision_provenance_and_readiness(
    target: str,
    origin: str,
    default_support: str,
    unresolved_blocker: str | None,
) -> None:
    """Feature: phase-4-planning-golden-path, Property 5: Decision provenance and readiness

    **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
    """
    decisions = _complete_ledger()
    evidence_ids: tuple[str, ...] = ()
    assumption = False
    rationale = "Recorded decision provenance."

    if origin == "prior_evidence":
        evidence_ids = ("prior-lora-result",)
    elif origin == "agent_default":
        if default_support == "evidence":
            evidence_ids = ("prior-lora-result",)
        elif default_support == "assumption":
            assumption = True

    decisions[target] = Decision(
        key=target,
        value=f"resolved-{target}",
        origin=origin,
        rationale=rationale,
        evidence_ids=evidence_ids,
        resolved=True,
        assumption=assumption,
    )

    if unresolved_blocker is not None:
        current = decisions[unresolved_blocker]
        decisions[unresolved_blocker] = Decision(
            key=current.key,
            value=None,
            origin=current.origin,
            rationale=current.rationale,
            evidence_ids=current.evidence_ids,
            resolved=False,
            assumption=current.assumption,
        )

    result = validate_decision_ledger(
        decisions,
        scenario_id="property-5",
        approval_requested=True,
    )
    codes = _codes(result)

    if origin == "agent_default" and default_support == "missing":
        assert "DEFAULT_SUPPORT_MISSING" in codes
    else:
        assert "DEFAULT_SUPPORT_MISSING" not in codes

    if unresolved_blocker is not None:
        assert not result.valid
        assert "DECISION_REQUIRED_UNRESOLVED" in codes
        assert "DECISION_APPROVAL_BLOCKED" in codes
        blocker_diagnostics = [
            diagnostic
            for diagnostic in result.diagnostics
            if diagnostic.code == "DECISION_APPROVAL_BLOCKED"
        ]
        assert any(
            diagnostic.location == f"decisions.{unresolved_blocker}"
            for diagnostic in blocker_diagnostics
        )
    elif not (origin == "agent_default" and default_support == "missing"):
        assert result.valid
        assert result.diagnostics == ()

    assert decisions[target].origin == origin
    if origin == "project_setting":
        assert decisions[target].origin != "agent_default"
    assert all(diagnostic.scenario_id == "property-5" for diagnostic in result.diagnostics)
