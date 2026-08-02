from __future__ import annotations

import os

GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash-lite")
GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0"))
PROMPT_TOKEN_BUDGET: int = int(os.getenv("PROMPT_TOKEN_BUDGET", "2200"))
PROMPT_MAX_EVIDENCE_SNIPPETS: int = int(os.getenv("PROMPT_MAX_EVIDENCE_SNIPPETS", "3"))
PROMPT_TEXT_FIELD_CHAR_BUDGET: int = int(os.getenv("PROMPT_TEXT_FIELD_CHAR_BUDGET", "1200"))
PROMPT_EVIDENCE_SNIPPET_CHAR_BUDGET: int = int(os.getenv("PROMPT_EVIDENCE_SNIPPET_CHAR_BUDGET", "280"))
