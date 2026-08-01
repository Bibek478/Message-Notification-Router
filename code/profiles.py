from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from code.schemas import (
    BehavioralMemoryProfile,
    BusinessAccountRow,
    DataStore,
    GroupMemberRow,
    GroupRow,
    MessageEventRow,
    MessageHistoryRow,
    PairProfile,
    ProfileCachePayload,
    ProfileStore,
    UserBaseProfile,
    UserBusinessHistoryRow,
    UserBusinessProfile,
    UserGroupProfile,
)

PROFILE_CACHE_FILENAME = "profile_store.json"
PROFILE_CACHE_VERSION = 1
URGENT_REPLY_THRESHOLD_MINUTES = 10.0


@dataclass(frozen=True)
class MessageCoverageReport:
    missing_user_ids: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return not self.missing_user_ids


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    formats = ("%Y-%m-%d %H:%M", "%Y-%m-%d")
    for format_string in formats:
        try:
            return datetime.strptime(value, format_string).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _normalize_text(value: str | None) -> str:
    return "" if value is None else value.strip().lower()


def _parse_dnd_window(window: str | None) -> tuple[str, str]:
    if not window:
        return ("00:00", "00:00")
    if "-" not in window:
        cleaned = window.strip()
        return (cleaned, cleaned)
    start, end = window.split("-", maxsplit=1)
    return (start.strip(), end.strip())


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _dataset_reference_time(data: DataStore) -> datetime:
    timestamps: list[datetime] = []

    for row in data.message_history:
        parsed = _parse_timestamp(row.created_at)
        if parsed is not None:
            timestamps.append(parsed)

    for row in data.user_business_history:
        parsed = _parse_timestamp(row.last_activity_at)
        if parsed is not None:
            timestamps.append(parsed)
        parsed_reply = _parse_timestamp(row.last_reply_at)
        if parsed_reply is not None:
            timestamps.append(parsed_reply)

    for row in data.daily_notification_summary:
        parsed = _parse_timestamp(row.date)
        if parsed is not None:
            timestamps.append(parsed)

    for row in data.messages:
        parsed = _parse_timestamp(row.created_at)
        if parsed is not None:
            timestamps.append(parsed)

    if not timestamps:
        return datetime.now(timezone.utc)
    return max(timestamps)


def _dataset_fingerprint(dataset_dir: Path) -> dict[str, dict[str, int]]:
    fingerprint: dict[str, dict[str, int]] = {}
    for csv_name in (
        "users.csv",
        "daily_notification_summary.csv",
        "groups.csv",
        "group_members.csv",
        "business_accounts.csv",
        "user_business_history.csv",
        "message_history.csv",
        "message_events.csv",
        "images.csv",
        "voice_notes.csv",
        "messages.csv",
        "sample_messages.csv",
    ):
        file_path = dataset_dir / csv_name
        stat = file_path.stat()
        fingerprint[csv_name] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    return fingerprint


def _aggregate_daily_summary(data: DataStore) -> dict[str, tuple[float, float, int]]:
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for row in data.daily_notification_summary:
        bucket = totals[row.user_id]
        bucket[0] += row.notifications_sent
        bucket[1] += row.notifications_dismissed
        bucket[2] += 1
    return {
        user_id: (
            float(values[0]),
            float(values[1]),
            values[2],
        )
        for user_id, values in totals.items()
    }


def _build_user_base_profiles(data: DataStore) -> dict[str, UserBaseProfile]:
    summary_totals = _aggregate_daily_summary(data)
    user_rows = {row.user_id: row for row in data.users}
    user_ids = set(user_rows) | {row.user_id for row in data.messages}

    profiles: dict[str, UserBaseProfile] = {}
    for user_id in sorted(user_ids):
        user_row = user_rows.get(user_id)
        sent_total, dismissed_total, summary_days = summary_totals.get(user_id, (0.0, 0.0, 0))

        if user_row is None:
            profiles[user_id] = UserBaseProfile(
                user_id=user_id,
                dnd_window=("00:00", "00:00"),
                openness_rate=0.0,
                reply_rate=0.0,
                dismissal_rate=0.0,
                report_tendency=0,
                avg_daily_notifications=0.0,
                avg_daily_dismissed=0.0,
            )
            continue

        opened = float(user_row.messages_opened_30d)
        replied = float(user_row.messages_replied_30d)
        dismissed = float(user_row.notifications_dismissed_30d)
        total_received = sent_total if sent_total > 0 else opened + dismissed

        profiles[user_id] = UserBaseProfile(
            user_id=user_id,
            dnd_window=_parse_dnd_window(user_row.do_not_disturb_window),
            openness_rate=_safe_divide(opened, total_received),
            reply_rate=_safe_divide(replied, opened),
            dismissal_rate=_safe_divide(dismissed_total if dismissed_total > 0 else dismissed, total_received),
            report_tendency=user_row.messages_reported_30d,
            avg_daily_notifications=_safe_divide(sent_total, summary_days),
            avg_daily_dismissed=_safe_divide(dismissed_total, summary_days),
        )

    return profiles


def _build_group_profiles(data: DataStore) -> dict[str, list[UserGroupProfile]]:
    group_lookup = {row.group_id: row for row in data.groups}
    profiles: dict[str, list[UserGroupProfile]] = defaultdict(list)

    for row in data.group_members:
        group = group_lookup.get(row.group_id)
        profiles[row.user_id].append(
            UserGroupProfile(
                user_id=row.user_id,
                group_id=row.group_id,
                group_type=group.group_type if group is not None else "unknown",
                role=row.role,
                group_muted=bool(row.group_muted_by_user),
                read_rate=_safe_divide(float(row.messages_read_30d), float(row.messages_sent_30d)),
                reply_rate=_safe_divide(float(row.replies_sent_30d), float(row.messages_sent_30d)),
                dismissals_in_group=row.notifications_dismissed_30d,
            )
        )

    return dict(profiles)


def _build_business_profiles(data: DataStore) -> dict[str, list[UserBusinessProfile]]:
    business_lookup = {row.business_id: row for row in data.business_accounts}
    grouped_rows: dict[tuple[str, str], list[UserBusinessHistoryRow]] = defaultdict(list)
    for row in data.user_business_history:
        grouped_rows[(row.user_id, row.business_id)].append(row)

    reference_time = _dataset_reference_time(data)
    profiles: dict[str, list[UserBusinessProfile]] = defaultdict(list)

    for (user_id, business_id), rows in grouped_rows.items():
        rows = sorted(rows, key=lambda row: _parse_timestamp(row.last_activity_at) or datetime.min.replace(tzinfo=timezone.utc))
        latest_row = rows[-1]
        business = business_lookup.get(business_id)

        opened_total = sum(row.messages_opened_30d for row in rows)
        dismissed_total = sum(row.messages_dismissed_30d for row in rows)
        replied_total = sum(row.messages_replied_30d for row in rows)
        interaction_total = opened_total + dismissed_total + replied_total
        latest_activity = _parse_timestamp(latest_row.last_activity_at)
        days_ago = 0
        if latest_activity is not None:
            days_ago = max((reference_time - latest_activity).days, 0)

        profiles[user_id].append(
            UserBusinessProfile(
                user_id=user_id,
                business_id=business_id,
                is_verified=bool(business.verified) if business is not None else False,
                domain_matches=(
                    _normalize_text(business.official_domain) == _normalize_text(business.domain_used_by_sender)
                    if business is not None and business.official_domain is not None and business.domain_used_by_sender is not None
                    else False
                ),
                relationship_reason=latest_row.why_user_knows_account,
                allows_promotions=bool(latest_row.allows_promotions),
                opted_out=latest_row.promotions_opted_out_at is not None or not bool(latest_row.allows_promotions),
                last_activity_days_ago=days_ago,
                open_rate_30d=_safe_divide(float(opened_total), float(interaction_total)),
                dismissal_rate_30d=_safe_divide(float(dismissed_total), float(interaction_total)),
                user_reports_on_business_30d=business.user_reports_30d if business is not None else 0,
            )
        )

    return dict(profiles)


def _build_behavioral_memory_profiles(data: DataStore) -> dict[str, BehavioralMemoryProfile]:
    events_by_message_id = {row.message_id: row for row in data.message_events}
    history_by_user: dict[str, list[MessageHistoryRow]] = defaultdict(list)
    for row in data.message_history:
        history_by_user[row.user_id].append(row)

    profiles: dict[str, BehavioralMemoryProfile] = {}
    for user_id, history_rows in history_by_user.items():
        ordered_rows = sorted(history_rows, key=lambda row: _parse_timestamp(row.created_at) or datetime.min.replace(tzinfo=timezone.utc))
        scam_report_count = 0
        forward_ignore_count = 0
        template_fatigue: dict[str, int] = defaultdict(int)
        reply_urgency_count = 0

        for row in ordered_rows:
            event = events_by_message_id.get(row.message_id)
            if event is None:
                continue

            scam_report_count += event.message_reported
            ignored = event.notification_dismissed or event.muted_after_message
            if row.forwarded_count > 0 and ignored:
                forward_ignore_count += 1

            if row.business_id is not None and ignored:
                template_fatigue[row.business_id] += 1

            if event.message_replied and event.reaction_time_minutes is not None:
                if event.reaction_time_minutes <= URGENT_REPLY_THRESHOLD_MINUTES and _message_looks_urgent(row.message_text):
                    reply_urgency_count += 1

        profiles[user_id] = BehavioralMemoryProfile(
            user_id=user_id,
            scam_report_count=scam_report_count,
            forward_ignore_count=forward_ignore_count,
            template_fatigue=dict(template_fatigue),
            reply_urgency_count=reply_urgency_count,
        )

    for user_id in {row.user_id for row in data.messages}:
        profiles.setdefault(
            user_id,
            BehavioralMemoryProfile(
                user_id=user_id,
                scam_report_count=0,
                forward_ignore_count=0,
                template_fatigue={},
                reply_urgency_count=0,
            ),
        )

    return profiles


def _message_looks_urgent(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = _normalize_text(message_text)
    urgent_tokens = (
        "urgent",
        "asap",
        "immediately",
        "right now",
        "emergency",
        "call now",
        "please respond",
        "critical",
    )
    return any(token in normalized for token in urgent_tokens)


def _build_default_business_profile(user_id: str) -> list[UserBusinessProfile]:
    return []


def build_all_profiles(data: DataStore) -> ProfileStore:
    """Build all pre-computed profile families from the loaded CSV data."""
    return ProfileStore(
        user_base_profiles=_build_user_base_profiles(data),
        user_group_profiles=_build_group_profiles(data),
        user_business_profiles=_build_business_profiles(data),
        behavioral_memory_profiles=_build_behavioral_memory_profiles(data),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def build_pair_profile(data: DataStore, sender_id: str, receiver_id: str) -> PairProfile:
    """Build a sender-to-receiver behavioral summary from historical interactions."""
    relevant_history = [
        row for row in data.message_history
        if row.user_id == receiver_id and row.sender_user_id == sender_id
    ]
    if not relevant_history:
        return PairProfile(
            sender_id=sender_id,
            receiver_id=receiver_id,
            total_messages=0,
            reply_rate=0.0,
            dismiss_rate=0.0,
            mute_rate=0.0,
            report_rate=0.0,
            typical_reaction_time_min=None,
        )

    event_lookup = {row.message_id: row for row in data.message_events if row.user_id == receiver_id}
    reply_count = 0
    dismiss_count = 0
    mute_count = 0
    report_count = 0
    reaction_times: list[float] = []

    for row in relevant_history:
        event = event_lookup.get(row.message_id)
        if event is None:
            continue
        reply_count += event.message_replied
        dismiss_count += event.notification_dismissed
        mute_count += event.muted_after_message
        report_count += event.message_reported
        if event.reaction_time_minutes is not None:
            reaction_times.append(event.reaction_time_minutes)

    total_messages = len(relevant_history)
    typical_reaction_time_min = None
    if reaction_times:
        typical_reaction_time_min = sum(reaction_times) / len(reaction_times)

    return PairProfile(
        sender_id=sender_id,
        receiver_id=receiver_id,
        total_messages=total_messages,
        reply_rate=_safe_divide(float(reply_count), float(total_messages)),
        dismiss_rate=_safe_divide(float(dismiss_count), float(total_messages)),
        mute_rate=_safe_divide(float(mute_count), float(total_messages)),
        report_rate=_safe_divide(float(report_count), float(total_messages)),
        typical_reaction_time_min=typical_reaction_time_min,
    )


def validate_profile_coverage(data: DataStore, profile_store: ProfileStore) -> MessageCoverageReport:
    """Confirm that every message user has a base profile."""
    message_user_ids = {row.user_id for row in data.messages}
    missing_user_ids = tuple(sorted(user_id for user_id in message_user_ids if user_id not in profile_store.user_base_profiles))
    return MessageCoverageReport(missing_user_ids=missing_user_ids)


def _cache_file_path(profiles_dir: Path) -> Path:
    return profiles_dir / PROFILE_CACHE_FILENAME


def _load_cache_payload(cache_file: Path) -> ProfileCachePayload | None:
    if not cache_file.exists():
        return None
    raw_payload = cache_file.read_text(encoding="utf-8")
    return ProfileCachePayload.model_validate_json(raw_payload)


def _save_cache_payload(cache_file: Path, payload: ProfileCachePayload) -> None:
    cache_file.write_text(payload.model_dump_json(indent=2), encoding="utf-8")


def load_or_build_all_profiles(data: DataStore, dataset_dir: Path, profiles_dir: Path) -> ProfileStore:
    """Load cached profiles when possible and rebuild them when the dataset fingerprint changes."""
    profiles_dir.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_file_path(profiles_dir)
    current_fingerprint = _dataset_fingerprint(dataset_dir)
    cached_payload = _load_cache_payload(cache_file)

    if cached_payload is not None:
        if cached_payload.cache_version == PROFILE_CACHE_VERSION and cached_payload.dataset_fingerprint == current_fingerprint:
            return cached_payload.profile_store

    profile_store = build_all_profiles(data)
    _save_cache_payload(
        cache_file,
        ProfileCachePayload(
            cache_version=PROFILE_CACHE_VERSION,
            dataset_fingerprint=current_fingerprint,
            profile_store=profile_store,
        ),
    )
    return profile_store