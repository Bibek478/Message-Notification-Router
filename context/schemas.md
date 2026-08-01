## Pydantic Profile Models

### `UserBaseProfile`
> Source: `users.csv` + `daily_notification_summary.csv`

```python
class UserBaseProfile(BaseModel):
    user_id: str
    dnd_window: tuple[str, str]          # e.g. ("22:00", "07:00")
    openness_rate: float                 # messages_opened / total received (30d)
    reply_rate: float                    # messages_replied / opened (30d)
    dismissal_rate: float                # notifications_dismissed / sent (30d)
    report_tendency: int                 # messages_reported_30d
    avg_daily_notifications: float       # from daily_notification_summary
    avg_daily_dismissed: float
```

### `UserGroupProfile`
> Source: `group_members.csv` + `groups.csv`

```python
class UserGroupProfile(BaseModel):
    user_id: str
    group_id: str
    group_type: str                      # family, society, coworker, etc.
    role: str                            # member | admin
    group_muted: bool
    read_rate: float                     # messages_read / sent in group (30d)
    reply_rate: float
    dismissals_in_group: int
```

### `UserBusinessProfile`
> Source: `user_business_history.csv` + `business_accounts.csv`

```python
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
```

### `BehavioralMemoryProfile`
> Source: `message_history.csv` + `message_events.csv`

```python
class BehavioralMemoryProfile(BaseModel):
    user_id: str
    scam_report_count: int               # messages reported by this user historically
    forward_ignore_count: int            # forwarded messages that were muted/dismissed
    template_fatigue: dict[str, int]     # business_id → dismissal streak
    reply_urgency_count: int             # how often user replies fast to urgent messages
```

### `PairProfile` (built at inference time)
> Source: `message_history` + `message_events` filtered to (sender, receiver) pair

```python
class PairProfile(BaseModel):
    sender_id: str
    receiver_id: str
    total_messages: int
    reply_rate: float                    # how often receiver replies to this sender
    dismiss_rate: float                  # how often dismissed
    mute_rate: float
    report_rate: float
    typical_reaction_time_min: float | None
```

---

## Structured Output Schema (Pydantic)

```python
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
```

---