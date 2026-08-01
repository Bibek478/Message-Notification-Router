import csv
from pathlib import Path
from typing import Any, Dict, List, Union

from code.schemas import (
    UserRow,
    DailyNotificationSummaryRow,
    GroupRow,
    GroupMemberRow,
    BusinessAccountRow,
    UserBusinessHistoryRow,
    MessageHistoryRow,
    MessageEventRow,
    ImageRow,
    VoiceNoteRow,
    MessageRow,
    SampleMessageRow,
    DataStore,
    RoutingDecision,
)

def _clean_row(row: Dict[str, str]) -> Dict[str, Any]:
    """Helper to strip spaces and convert empty strings to None."""
    cleaned: Dict[str, Any] = {}
    for k, v in row.items():
        val = v.strip()
        cleaned[k] = None if val == "" else val
    return cleaned

def load_users(dataset_dir: Path) -> List[UserRow]:
    """Loads users.csv into a list of UserRow models."""
    path = dataset_dir / "users.csv"
    rows: List[UserRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(UserRow(**cleaned))
    return rows

def load_daily_notification_summary(dataset_dir: Path) -> List[DailyNotificationSummaryRow]:
    """Loads daily_notification_summary.csv."""
    path = dataset_dir / "daily_notification_summary.csv"
    rows: List[DailyNotificationSummaryRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(DailyNotificationSummaryRow(**cleaned))
    return rows

def load_groups(dataset_dir: Path) -> List[GroupRow]:
    """Loads groups.csv."""
    path = dataset_dir / "groups.csv"
    rows: List[GroupRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(GroupRow(**cleaned))
    return rows

def load_group_members(dataset_dir: Path) -> List[GroupMemberRow]:
    """Loads group_members.csv."""
    path = dataset_dir / "group_members.csv"
    rows: List[GroupMemberRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(GroupMemberRow(**cleaned))
    return rows

def load_business_accounts(dataset_dir: Path) -> List[BusinessAccountRow]:
    """Loads business_accounts.csv."""
    path = dataset_dir / "business_accounts.csv"
    rows: List[BusinessAccountRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(BusinessAccountRow(**cleaned))
    return rows

def load_user_business_history(dataset_dir: Path) -> List[UserBusinessHistoryRow]:
    """Loads user_business_history.csv."""
    path = dataset_dir / "user_business_history.csv"
    rows: List[UserBusinessHistoryRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(UserBusinessHistoryRow(**cleaned))
    return rows

def load_message_history(dataset_dir: Path) -> List[MessageHistoryRow]:
    """Loads message_history.csv."""
    path = dataset_dir / "message_history.csv"
    rows: List[MessageHistoryRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(MessageHistoryRow(**cleaned))
    return rows

def load_message_events(dataset_dir: Path) -> List[MessageEventRow]:
    """Loads message_events.csv."""
    path = dataset_dir / "message_events.csv"
    rows: List[MessageEventRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(MessageEventRow(**cleaned))
    return rows

def load_images(dataset_dir: Path) -> List[ImageRow]:
    """Loads images.csv."""
    path = dataset_dir / "images.csv"
    rows: List[ImageRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(ImageRow(**cleaned))
    return rows

def load_voice_notes(dataset_dir: Path) -> List[VoiceNoteRow]:
    """Loads voice_notes.csv."""
    path = dataset_dir / "voice_notes.csv"
    rows: List[VoiceNoteRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(VoiceNoteRow(**cleaned))
    return rows

def load_messages(dataset_dir: Path) -> List[MessageRow]:
    """Loads messages.csv."""
    path = dataset_dir / "messages.csv"
    rows: List[MessageRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(MessageRow(**cleaned))
    return rows

def load_sample_messages(dataset_dir: Path) -> List[SampleMessageRow]:
    """Loads sample_messages.csv."""
    path = dataset_dir / "sample_messages.csv"
    rows: List[SampleMessageRow] = []
    with open(path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cleaned = _clean_row(row)
            rows.append(SampleMessageRow(**cleaned))
    return rows

def load_all_data(dataset_dir: Path) -> DataStore:
    """Loads all CSV files and returns a unified DataStore wrapper."""
    return DataStore(
        users=load_users(dataset_dir),
        daily_notification_summary=load_daily_notification_summary(dataset_dir),
        groups=load_groups(dataset_dir),
        group_members=load_group_members(dataset_dir),
        business_accounts=load_business_accounts(dataset_dir),
        user_business_history=load_user_business_history(dataset_dir),
        message_history=load_message_history(dataset_dir),
        message_events=load_message_events(dataset_dir),
        images=load_images(dataset_dir),
        voice_notes=load_voice_notes(dataset_dir),
        messages=load_messages(dataset_dir),
        sample_messages=load_sample_messages(dataset_dir),
    )

def write_output(decisions: List[RoutingDecision], output_path: Path) -> None:
    """Writes the prediction RoutingDecisions to output_path matching project specs."""
    fieldnames = ["message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"]
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in decisions:
            evidence_str = ";".join(d.evidence_message_ids) if d.evidence_message_ids else "none"
            writer.writerow({
                "message_id": d.message_id,
                "action": d.action,
                "message_type": d.message_type,
                "reason": d.reason,
                "confidence": round(d.confidence, 4),
                "evidence_message_ids": evidence_str
            })
