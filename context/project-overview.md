# Project Overview — Message Notification Router

## What We're Building

An AI-powered WhatsApp message routing agent that classifies every incoming message in `dataset/messages.csv` as:

- **`notify`** — interrupt the user now
- **`digest`** — useful, show later
- **`mute`** — low-value, repetitive, suspicious, or unsafe

Decisions are **personalized per user** using structured behavioral profiles built from the provided dataset.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python |
| Data models | Pydantic v2 |
| LLM | Gemini (multimodal — handles text, image, voice, multilingual) |
| Evidence retrieval | BM25 (lexical) + vector similarity (semantic) |
| Output format | Structured JSON via Gemini function calling / response schema |
| Entry point | `code/main.py` |

---

## Dataset at a Glance

| File | Role |
|---|---|
| `messages.csv` | 265 incoming messages to classify |
| `users.csv` | User behavior: DND window, open/reply/dismiss/report rates |
| `groups.csv` + `group_members.csv` | Group type, size, user's role and behavior per group |
| `business_accounts.csv` | Business verification, domain trust, report counts |
| `user_business_history.csv` | User↔business relationship, opt-in/out, engagement |
| `message_history.csv` | ~1000 historical messages for pattern matching |
| `message_events.csv` | User reactions to historical messages (open/reply/dismiss/mute/report) |
| `daily_notification_summary.csv` | Per-user daily notification load and dismissal trend |
| `images.csv` + `voice_notes.csv` | Media file paths for multimodal messages |
| `sample_messages.csv` | Solved examples showing expected output format |

---

## Output Contract

`output.csv` must have exactly one row per `message_id` in `messages.csv`:

```
message_id, action, message_type, reason, confidence, evidence_message_ids
```

- `action`: `notify` | `digest` | `mute`
- `message_type`: `personal` | `urgent` | `event` | `payment` | `business_update` | `promotion` | `greeting` | `forward` | `spam` | `scam` | `unknown`
- `confidence`: float 0–1
- `evidence_message_ids`: semicolon-separated historical IDs, or `none`

---

## Key Design Decisions

- **Profile pre-computation**: All user/group/business behavioral data is loaded and structured into Pydantic profiles *before* inference, not per-message.
- **Multimodal inference**: Images and voice notes are passed directly to Gemini — no separate OCR/ASR pipeline.
- **Hybrid evidence retrieval**: BM25 + vector similarity over `message_history` to find the most relevant past messages as evidence.
- **DND as soft signal**: The user's Do-Not-Disturb window influences routing confidence but is not a hard override.
- **Prompt injection awareness**: Several messages in the dataset attempt to hijack routing decisions — mitigations are addressed in a dedicated guardrails phase.

---

## Submission Artifacts

| File | Description |
|---|---|
| `output.csv` | Predictions for all rows in `messages.csv` |
| `code.zip` | Full runnable solution + this README |
| `log.txt` | Chat transcript from `%USERPROFILE%\hackerrank_orchestrate_august26\log.txt` |
