from __future__ import annotations

from code.decision import decide_action
from code.schemas import DecisionContext, RouterOutput


def _build_observation(
    *,
    action: str = "notify",
    message_type: str = "personal",
    reason: str = "Needs attention.",
    notify_confidence: float = 0.8,
    digest_confidence: float = 0.15,
    mute_confidence: float = 0.05,
    evidence_message_ids: list[str] | None = None,
) -> RouterOutput:
    resolved_evidence_ids = ["hist_001"] if evidence_message_ids is None else evidence_message_ids
    return RouterOutput(
        action=action,
        message_type=message_type,
        reason=reason,
        notify_confidence=notify_confidence,
        digest_confidence=digest_confidence,
        mute_confidence=mute_confidence,
        evidence_message_ids=resolved_evidence_ids,
    )


def _build_context(
    *,
    message_id: str = "msg_001",
    message_created_at: str | None = "2026-08-02 14:00",
    dnd_window: tuple[str, str] | None = ("22:00", "07:00"),
) -> DecisionContext:
    return DecisionContext(
        message_id=message_id,
        message_created_at=message_created_at,
        dnd_window=dnd_window,
    )


def test_decide_action_uses_highest_confidence_score() -> None:
    observation = _build_observation(
        action="digest",
        message_type="event",
        notify_confidence=0.2,
        digest_confidence=0.7,
        mute_confidence=0.1,
    )

    decision = decide_action(observation, _build_context())

    assert decision.message_id == "msg_001"
    assert decision.action == "digest"
    assert decision.message_type == "event"
    assert decision.confidence == 0.7
    assert decision.reason == "Needs attention."


def test_decide_action_prefers_model_action_when_top_scores_tie() -> None:
    observation = _build_observation(
        action="mute",
        message_type="spam",
        notify_confidence=0.45,
        digest_confidence=0.1,
        mute_confidence=0.45,
    )

    decision = decide_action(observation, _build_context())

    assert decision.action == "mute"
    assert decision.confidence == 0.45


def test_decide_action_reroutes_notify_to_digest_during_dnd() -> None:
    observation = _build_observation(
        action="notify",
        message_type="personal",
        reason="Friend asked for a reply.",
        notify_confidence=0.81,
        digest_confidence=0.27,
        mute_confidence=0.04,
    )
    context = _build_context(message_created_at="2026-08-02 23:15")

    decision = decide_action(observation, context)

    assert decision.action == "digest"
    assert decision.confidence == 0.81
    assert "DND window" in decision.reason


def test_decide_action_keeps_urgent_notify_during_dnd() -> None:
    observation = _build_observation(
        action="notify",
        message_type="urgent",
        notify_confidence=0.89,
        digest_confidence=0.08,
        mute_confidence=0.03,
    )
    context = _build_context(message_created_at="2026-08-02 23:15")

    decision = decide_action(observation, context)

    assert decision.action == "notify"
    assert decision.confidence == 0.89


def test_decide_action_keeps_payment_notify_during_dnd() -> None:
    observation = _build_observation(
        action="notify",
        message_type="payment",
        notify_confidence=0.76,
        digest_confidence=0.18,
        mute_confidence=0.06,
    )
    context = _build_context(message_created_at="2026-08-02 23:15")

    decision = decide_action(observation, context)

    assert decision.action == "notify"
    assert decision.confidence == 0.76


def test_decide_action_normalizes_missing_evidence_to_none() -> None:
    observation = _build_observation(
        action="mute",
        message_type="promotion",
        notify_confidence=0.05,
        digest_confidence=0.2,
        mute_confidence=0.75,
        evidence_message_ids=[],
    )

    decision = decide_action(observation, _build_context())

    assert decision.action == "mute"
    assert decision.evidence_message_ids == ["none"]
