from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from code.config import GEMINI_API_KEY, GEMINI_MODEL_NAME, GEMINI_TEMPERATURE
from code.schemas import RouterOutput


class ModelClientError(RuntimeError):
    """Base error for Gemini client setup or response parsing failures."""


class ModelConfigurationError(ModelClientError):
    """Raised when the Gemini client cannot be configured."""


class ModelResponseError(ModelClientError):
    """Raised when the Gemini response cannot be converted to RouterOutput."""


class _GenerateContentResponse(Protocol):
    parsed: object | None
    text: str | None


class _ModelsService(Protocol):
    def generate_content(
        self,
        *,
        model: str,
        contents: Sequence[types.Part] | str,
        config: types.GenerateContentConfig,
    ) -> _GenerateContentResponse:
        """Generate a structured Gemini response."""


class _GenAIClient(Protocol):
    models: _ModelsService


def _to_part(media_item: Path) -> types.Part:
    if not media_item.exists():
        raise ModelConfigurationError(f"Media file does not exist: {media_item}")

    mime_type, _ = mimetypes.guess_type(media_item.name)
    resolved_mime_type = mime_type or "application/octet-stream"
    return types.Part.from_bytes(data=media_item.read_bytes(), mime_type=resolved_mime_type)


def _coerce_router_output(payload: object) -> RouterOutput:
    if isinstance(payload, RouterOutput):
        return payload
    if isinstance(payload, BaseModel):
        return RouterOutput.model_validate(payload.model_dump())
    if isinstance(payload, Mapping):
        return RouterOutput.model_validate(dict(payload))
    if isinstance(payload, str):
        return RouterOutput.model_validate_json(payload)
    raise ModelResponseError(f"Unsupported Gemini response payload type: {type(payload)!r}")


class RouterModelClient:
    """Thin Gemini wrapper that returns a validated RouterOutput schema."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        client: _GenAIClient | None = None,
    ) -> None:
        resolved_model_name = model_name or GEMINI_MODEL_NAME
        if not resolved_model_name:
            raise ModelConfigurationError("Gemini model name is not configured.")

        if client is not None:
            self._client = client
        else:
            resolved_api_key = api_key or GEMINI_API_KEY
            if not resolved_api_key:
                raise ModelConfigurationError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=resolved_api_key)

        self.model_name = resolved_model_name

    def call_model(self, prompt: str, media: list[Path] | None = None) -> RouterOutput:
        contents: Sequence[types.Part] | str
        if media:
            parts = [types.Part.from_text(text=prompt)]
            parts.extend(_to_part(item) for item in media)
            contents = parts
        else:
            contents = prompt

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=GEMINI_TEMPERATURE,
                response_mime_type="application/json",
                response_schema=RouterOutput,
            ),
        )

        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            try:
                return _coerce_router_output(parsed)
            except ValidationError as exc:
                raise ModelResponseError("Gemini parsed response failed schema validation.") from exc

        text = getattr(response, "text", None)
        if not text:
            raise ModelResponseError("Gemini response did not include parsed content or text.")

        try:
            return _coerce_router_output(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ModelResponseError("Gemini response text could not be validated as RouterOutput.") from exc


_default_client: RouterModelClient | None = None


def get_default_model_client() -> RouterModelClient:
    global _default_client
    if _default_client is None:
        _default_client = RouterModelClient()
    return _default_client


def call_model(prompt: str, media: list[Path] | None = None) -> RouterOutput:
    """Call Gemini and return a validated RouterOutput observation."""
    return get_default_model_client().call_model(prompt=prompt, media=media)
