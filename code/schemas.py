from typing import Literal
from pydantic import BaseModel, Field

# --- CSV Row Schemas ---

class UserRow(BaseModel):
    user_id: str
    do_not_disturb_window: str
    messages_opened_30d: int
    messages_replied_30d: int
    notifications_dismissed_30d: int
    messages_reported_30d: int

class DailyNotificationSummaryRow(BaseModel):
    user_id: str
    date: str
    notifications_sent: int
    notifications_dismissed: int

class GroupRow(BaseModel):
    group_id: str
    group_name: str
    group_type: str
    member_count: int
    admin_count: int
    created_at: str
    messages_30d: int

class GroupMemberRow(BaseModel):
    group_id: str
    user_id: str
    role: str
    joined_at: str
    messages_sent_30d: int
    messages_read_30d: int
    replies_sent_30d: int
    notifications_dismissed_30d: int
    group_muted_by_user: int  # 0 or 1

class BusinessAccountRow(BaseModel):
    business_id: str
    display_name: str
    brand_name: str
    category: str
    verified: int  # 0 or 1
    official_domain: str | None = None
    domain_used_by_sender: str | None = None
    account_age_days: int
    messages_sent_30d: int
    user_reports_30d: int
    domain_used_by_sender_age_days: int | None = None

class UserBusinessHistoryRow(BaseModel):
    user_id: str
    business_id: str
    why_user_knows_account: str
    last_activity_at: str
    allows_promotions: int  # 0 or 1
    promotions_opted_out_at: str | None = None
    activity_count_180d: int
    messages_opened_30d: int
    messages_dismissed_30d: int
    messages_replied_30d: int
    last_reply_at: str | None = None

class MessageHistoryRow(BaseModel):
    message_id: str
    user_id: str
    conversation_type: str
    group_id: str | None = None
    business_id: str | None = None
    sender_user_id: str | None = None
    created_at: str
    message_text: str | None = None
    media_type: str | None = None
    media_id: str | None = None
    forwarded_count: int

class MessageEventRow(BaseModel):
    user_id: str
    message_id: str
    message_opened: int  # 0 or 1
    message_replied: int  # 0 or 1
    reaction_time_minutes: float | None = None
    notification_dismissed: int  # 0 or 1
    muted_after_message: int  # 0 or 1
    message_reported: int  # 0 or 1

class ImageRow(BaseModel):
    image_id: str
    file_path: str

class VoiceNoteRow(BaseModel):
    voice_note_id: str
    file_path: str

class MessageRow(BaseModel):
    message_id: str
    user_id: str
    conversation_type: str
    group_id: str | None = None
    business_id: str | None = None
    sender_user_id: str | None = None
    created_at: str
    message_text: str | None = None
    media_type: str | None = None
    media_id: str | None = None
    forwarded_count: int

class SampleMessageRow(BaseModel):
    message_id: str
    user_id: str
    conversation_type: str
    group_id: str | None = None
    business_id: str | None = None
    sender_user_id: str | None = None
    created_at: str
    message_text: str | None = None
    media_type: str | None = None
    media_id: str | None = None
    forwarded_count: int
    action: str
    message_type: str
    reason: str
    confidence: float
    evidence_message_ids: str

class DataStore(BaseModel):
    users: list[UserRow]
    daily_notification_summary: list[DailyNotificationSummaryRow]
    groups: list[GroupRow]
    group_members: list[GroupMemberRow]
    business_accounts: list[BusinessAccountRow]
    user_business_history: list[UserBusinessHistoryRow]
    message_history: list[MessageHistoryRow]
    message_events: list[MessageEventRow]
    images: list[ImageRow]
    voice_notes: list[VoiceNoteRow]
    messages: list[MessageRow]
    sample_messages: list[SampleMessageRow]


# --- Profiles & Inference Boundary Schemas ---

class UserBaseProfile(BaseModel):
    user_id: str
    dnd_window: tuple[str, str]          # e.g. ("22:00", "07:00")
    openness_rate: float                 # messages_opened / total received (30d)
    reply_rate: float                    # messages_replied / opened (30d)
    dismissal_rate: float                # notifications_dismissed / sent (30d)
    report_tendency: int                 # messages_reported_30d
    avg_daily_notifications: float       # from daily_notification_summary
    avg_daily_dismissed: float

class UserGroupProfile(BaseModel):
    user_id: str
    group_id: str
    group_type: str                      # family, society, coworker, etc.
    role: str                            # member | admin
    group_muted: bool
    read_rate: float                     # messages_read / sent in group (30d)
    reply_rate: float
    dismissals_in_group: int

class UserBusinessProfile(BaseModel):
    user_id: str
    business_id: str
    is_verified: bool
    domain_matches: bool                 # official_domain == domain_used_by_sender
    relationship_reason: str             # e.g. "recent_grocery_delivery"
    allows_promotions: bool
    opted_out: bool
    last_activity_days_ago: int
    open_rate_30d: float
    dismissal_rate_30d: float
    user_reports_on_business_30d: int

class BehavioralMemoryProfile(BaseModel):
    user_id: str
    scam_report_count: int               # messages reported by this user historically
    forward_ignore_count: int            # forwarded messages that were muted/dismissed
    template_fatigue: dict[str, int]     # business_id → dismissal streak
    reply_urgency_count: int             # how often user replies fast to urgent messages

class PairProfile(BaseModel):
    sender_id: str
    receiver_id: str
    total_messages: int
    reply_rate: float                    # how often receiver replies to this sender
    dismiss_rate: float                  # how often dismissed
    mute_rate: float
    report_rate: float
    typical_reaction_time_min: float | None

class RouterOutput(BaseModel):
    action: Literal["notify", "digest", "mute"]
    message_type: Literal[
        "personal", "urgent", "event", "payment", "business_update",
        "promotion", "greeting", "forward", "spam", "scam", "unknown"
    ]
    reason: str
    notify_confidence: float = Field(ge=0.0, le=1.0)
    digest_confidence: float = Field(ge=0.0, le=1.0)
    mute_confidence: float = Field(ge=0.0, le=1.0)
    evidence_message_ids: list[str]

class RoutingDecision(BaseModel):
    action: Literal["notify", "digest", "mute"]
    message_type: str
    reason: str
    confidence: float
    evidence_message_ids: list[str]


class ProfileStore(BaseModel):
    user_base_profiles: dict[str, UserBaseProfile] = Field(default_factory=dict)
    user_group_profiles: dict[str, list[UserGroupProfile]] = Field(default_factory=dict)
    user_business_profiles: dict[str, list[UserBusinessProfile]] = Field(default_factory=dict)
    behavioral_memory_profiles: dict[str, BehavioralMemoryProfile] = Field(default_factory=dict)
    generated_at: str


class ProfileCachePayload(BaseModel):
    cache_version: int = 1
    dataset_fingerprint: dict[str, dict[str, int]]
    profile_store: ProfileStore
