from __future__ import annotations

from code.evidence import EvidenceIndex, build_evidence_index, retrieve_evidence
from code.schemas import MessageHistoryRow


def test_retrieve_evidence_returns_ranked_history_ids() -> None:
    history_rows = [
        MessageHistoryRow(
            message_id="message_001",
            user_id="u_001",
            conversation_type="personal",
            group_id=None,
            business_id=None,
            sender_user_id="u_002",
            created_at="2026-05-01 10:00",
            message_text="urgent payment verification needed now",
            media_type=None,
            media_id=None,
            forwarded_count=0,
        ),
        MessageHistoryRow(
            message_id="message_002",
            user_id="u_001",
            conversation_type="business",
            group_id=None,
            business_id="business_001",
            sender_user_id=None,
            created_at="2026-05-02 10:00",
            message_text="delivery failed pay small fee to release package",
            media_type=None,
            media_id=None,
            forwarded_count=0,
        ),
        MessageHistoryRow(
            message_id="message_003",
            user_id="u_001",
            conversation_type="group",
            group_id="group_001",
            business_id=None,
            sender_user_id="u_003",
            created_at="2026-05-03 10:00",
            message_text="family dinner plans for tonight",
            media_type=None,
            media_id=None,
            forwarded_count=0,
        ),
    ]

    index = build_evidence_index(history_rows)
    result = retrieve_evidence(index, user_id="u_001", query_text="urgent payment issue", top_k=2)

    assert result == ["message_001", "message_002"]


def test_retrieve_evidence_returns_none_for_empty_query() -> None:
    index = EvidenceIndex(user_id="u_001", documents=[], bm25_index={}, vector_index={}, document_ids=[])

    assert retrieve_evidence(index, user_id="u_001", query_text="", top_k=3) == []
