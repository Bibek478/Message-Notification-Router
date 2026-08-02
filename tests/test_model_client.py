from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from code.model_client import RouterModelClient
from code.schemas import RouterOutput


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
