from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from code.model_client import RouterModelClient
from code.schemas import RouterOutput, DataStore, ImageRow, VoiceNoteRow
from code.io_utils import resolve_media_path


@dataclass
class _FakeResponse:
    parsed: object | None = None
    text: str | None = None


class _FakeModels:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, object]] = []

    def generate_content(self, *, model: str, contents: object, config: object) -> _FakeResponse:
        self.calls.append((model, contents))
        if not self._responses:
            raise AssertionError("No fake response configured.")
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.models = _FakeModels(responses)


def _load_text_only_sample_prompts() -> list[str]:
    sample_path = Path(__file__).resolve().parents[1] / "dataset" / "sample_messages.csv"
    prompts: list[str] = []
    with sample_path.open(mode="r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("media_type"):
                continue
            prompts.append(row.get("message_text", "") or "")
            if len(prompts) == 3:
                break
    return prompts


def test_call_model_parses_three_text_sample_messages() -> None:
    prompts = _load_text_only_sample_prompts()
    assert len(prompts) == 3

    responses = [
        _FakeResponse(
            parsed={
                "action": "notify",
                "message_type": "urgent",
                "reason": "Urgent account request.",
                "notify_confidence": 0.92,
                "digest_confidence": 0.05,
                "mute_confidence": 0.03,
                "evidence_message_ids": ["hist_001"],
            }
        ),
        _FakeResponse(
            text=(
                '{"action":"digest","message_type":"event","reason":"Can wait until later.",'
                '"notify_confidence":0.1,"digest_confidence":0.8,"mute_confidence":0.1,'
                '"evidence_message_ids":["hist_002","hist_003"]}'
            )
        ),
        _FakeResponse(
            parsed=RouterOutput(
                action="mute",
                message_type="spam",
                reason="Low-value promotional message.",
                notify_confidence=0.02,
                digest_confidence=0.08,
                mute_confidence=0.9,
                evidence_message_ids=["hist_004"],
            )
        ),
    ]

    client = RouterModelClient(client=_FakeClient(responses), model_name="test-model")

    outputs = [client.call_model(prompt=prompt) for prompt in prompts]

    assert [output.action for output in outputs] == ["notify", "digest", "mute"]
    assert [output.message_type for output in outputs] == ["urgent", "event", "spam"]
    assert outputs[0].evidence_message_ids == ["hist_001"]
    assert outputs[1].evidence_message_ids == ["hist_002", "hist_003"]
    assert outputs[2].evidence_message_ids == ["hist_004"]


def test_call_model_with_media(tmp_path: Path) -> None:
    img_file = tmp_path / "img_001.jpg"
    img_file.write_bytes(b"dummy image bytes")
    audio_file = tmp_path / "vn_001.mp3"
    audio_file.write_bytes(b"dummy audio bytes")

    responses = [
        _FakeResponse(
            parsed={
                "action": "notify",
                "message_type": "personal",
                "reason": "Multimodal message response.",
                "notify_confidence": 0.9,
                "digest_confidence": 0.05,
                "mute_confidence": 0.05,
                "evidence_message_ids": ["none"],
            }
        )
    ]

    fake_client = _FakeClient(responses)
    client = RouterModelClient(client=fake_client, model_name="test-model")

    output = client.call_model(
        prompt="Describe this image and audio",
        media=[img_file, audio_file],
    )

    calls = fake_client.models.calls
    assert len(calls) == 1
    model, contents = calls[0]
    assert model == "test-model"
    assert isinstance(contents, list)
    assert len(contents) == 3
    assert contents[0].text == "Describe this image and audio"
    assert contents[1].inline_data.mime_type == "image/jpeg"
    assert contents[1].inline_data.data == b"dummy image bytes"
    assert contents[2].inline_data.mime_type == "audio/mpeg"
    assert contents[2].inline_data.data == b"dummy audio bytes"
    assert output.action == "notify"


def test_resolve_media_path() -> None:
    data = DataStore(
        users=[],
        daily_notification_summary=[],
        groups=[],
        group_members=[],
        business_accounts=[],
        user_business_history=[],
        message_history=[],
        message_events=[],
        images=[ImageRow(image_id="img_123", file_path="media/images/img_123.jpg")],
        voice_notes=[VoiceNoteRow(voice_note_id="vn_456", file_path="media/audio/vn_456.mp3")],
        messages=[],
        sample_messages=[],
    )

    dataset_dir = Path("/mock/dataset")

    resolved_img = resolve_media_path("image", "img_123", data, dataset_dir)
    assert resolved_img == Path("/mock/dataset/media/images/img_123.jpg")

    resolved_vn = resolve_media_path("voice", "vn_456", data, dataset_dir)
    assert resolved_vn == Path("/mock/dataset/media/audio/vn_456.mp3")

    assert resolve_media_path(None, None, data, dataset_dir) is None
    assert resolve_media_path("image", "img_missing", data, dataset_dir) is None
