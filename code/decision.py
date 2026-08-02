from __future__ import annotations

from datetime import datetime, time

from code.schemas import DecisionContext, RoutingDecision, RouterOutput

_ACTION_PRIORITY = ("notify", "digest", "mute")
_DND_NOTIFY_EXCEPTIONS = frozenset({"urgent", "payment"})


def decide_action(observation: RouterOutput, context: DecisionContext) -> RoutingDecision:
    """Choose the final routing action from model scores and DND policy overrides."""
    scores = {
        "notify": observation.notify_confidence,
        "digest": observation.digest_confidence,
        "mute": observation.mute_confidence,
    }
    preliminary_action = _pick_highest_confidence_action(scores, observation.action)
    final_action = preliminary_action
    final_reason = observation.reason.strip()

    if _should_reroute_notify_to_digest(
        action=preliminary_action,
        message_type=observation.message_type,
        context=context,
    ):
        final_action = "digest"
        final_reason = _append_reason(
            final_reason,
            "Moved to digest because it arrived during the user's DND window.",
        )

    confidence = scores[final_action]
    if final_action == "digest" and preliminary_action == "notify":
        confidence = max(confidence, scores["notify"])

    return RoutingDecision(
        message_id=context.message_id,
        action=final_action,
        message_type=observation.message_type,
        reason=final_reason,
        confidence=confidence,
        evidence_message_ids=_normalize_evidence_ids(observation.evidence_message_ids),
    )


def _pick_highest_confidence_action(scores: dict[str, float], preferred_action: str) -> str:
    highest_score = max(scores.values())
    tied_actions = [action for action in _ACTION_PRIORITY if scores[action] == highest_score]
    if preferred_action in tied_actions:
        return preferred_action
    return tied_actions[0]


def _should_reroute_notify_to_digest(
    action: str,
    message_type: str,
    context: DecisionContext,
) -> bool:
    if action != "notify":
        return False
    if message_type in _DND_NOTIFY_EXCEPTIONS:
        return False
    return _is_within_dnd_window(context.message_created_at, context.dnd_window)


def _is_within_dnd_window(
    message_created_at: str | None,
    dnd_window: tuple[str, str] | None,
) -> bool:
    if message_created_at is None or dnd_window is None:
        return False
    message_time = _parse_message_time(message_created_at)
    window_start = _parse_clock_time(dnd_window[0])
    window_end = _parse_clock_time(dnd_window[1])
    if message_time is None or window_start is None or window_end is None:
        return False

    if window_start == window_end:
        return False
    if window_start < window_end:
        return window_start <= message_time < window_end
    return message_time >= window_start or message_time < window_end


def _parse_message_time(value: str) -> time | None:
    normalized_value = value.strip()
    for parser in (datetime.fromisoformat,):
        try:
            return parser(normalized_value).time().replace(tzinfo=None)
        except ValueError:
            continue
    for format_string in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(normalized_value, format_string).time()
        except ValueError:
            continue
    return None


def _parse_clock_time(value: str) -> time | None:
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return None


def _append_reason(reason: str, suffix: str) -> str:
    cleaned_reason = reason.strip()
    if not cleaned_reason:
        return suffix
    if cleaned_reason.endswith((".", "!", "?")):
        return f"{cleaned_reason} {suffix}"
    return f"{cleaned_reason}. {suffix}"


def _normalize_evidence_ids(evidence_message_ids: list[str]) -> list[str]:
    normalized = [message_id.strip() for message_id in evidence_message_ids if message_id.strip()]
    if not normalized:
        return ["none"]
    return normalized
