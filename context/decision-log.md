# Decision Log — Message Notification Router

This log records the core design and architectural decisions made for the WhatsApp Message Notification Router project.

---

## [2026-08-01] DEC-01: Profile Pre-computation and Caching Strategy

* **Status:** Accepted
* **Context:** The system needs access to historical user behaviour, group relationships, and business interactions to make personalized notification decisions. Generating these on the fly from raw CSV files for every message is too slow and token-inefficient. Also, re-parsing these CSVs on every run introduces startup latency.
* **Decision:** Pre-compute structured Profiles (using Pydantic models) for all users, groups, and businesses from the dataset CSVs before starting the inference loop, and save them in JSON format in a new directory called `profiles/` at the project root. During runs, the system loads these JSONs if they exist, falling back to parser computation only if they are missing or outdated. At inference time, retrieve these profiles and dynamically compute a sender-receiver `PairProfile`.
* **Rationale:** Reduces LLM context token usage, isolates data loading and aggregation, and eliminates compute startup overhead on repeated execution runs by caching profile structures in readable JSON format.

---

## [2026-08-01] DEC-02: LLM Service & Multimodal Pipeline

* **Status:** Accepted
* **Context:** Messages in `messages.csv` can be text-only, image files (posters, screenshots), or audio files (voice notes), and can contain multiple languages (Hindi, Hinglish, etc.).
* **Decision:** Use Gemini API. Pass image and audio media files directly to the Gemini API using its native multimodal capabilities rather than building separate OCR (text-extraction) and ASR (transcription) pipelines.
* **Rationale:** Gemini natively excels at multilingual and multimodal tasks in a single call. Eliminating separate OCR/ASR pipeline components simplifies the repository architecture, prevents cascading errors, and reduces preprocessing time.

---

## [2026-08-01] DEC-03: Evidence Retrieval Methodology

* **Status:** Accepted
* **Context:** The system must identify and output related historical message IDs (`evidence_message_ids`) from `message_history.csv` that explain/support the routing decision.
* **Decision:** Implement a hybrid retrieval system over `message_history.csv` combining BM25 lexical search and vector semantic similarity.
* **Rationale:** BM25 leverages exact keyword matching, which is ideal for catching identical templates, codes, or specific names. Vector similarity handles paraphrased meanings, synonyms, and cross-lingual matches (e.g., an OTP scam written in Hindi vs. English). Combining these ensures robust retrieval.

---

## [2026-08-01] DEC-04: Do-Not-Disturb (DND) Window Treatment

* **Status:** Accepted
* **Context:** Users have specified Do-Not-Disturb (DND) windows. Overriding all messages during DND may miss emergency notifications, while ignoring DND entirely defeats its purpose.
* **Decision:** Treat the DND window as a "soft signal". Introduce the DND start/end times and the incoming message timestamp to the LLM prompt as context, rather than implementing a hard code-level block or override.
* **Rationale:** Allows the router to make nuanced exceptions for high-urgency pings (e.g., family emergency, immediate transaction issues) while respecting the quiet window for standard or promotion notifications.

---

## [2026-08-01] DEC-05: Decision logic boundary ("Model observes, code decides")

* **Status:** Accepted
* **Context:** Ensuring deterministic, controllable behavior for crucial notification routing is difficult if the LLM directly outputs a final text flag without validation.
* **Decision:** The LLM's role is to "observe" and return structured confidence scores for all actions (`notify`, `digest`, `mute`) in a Pydantic schema. Path selection (picking the highest score, executing fallback contingencies, and applying guardrails) is handled entirely in deterministic Python code.
* **Rationale:** Makes the decision logic testable via unit tests with mock outputs, allows deterministic post-model overrides, and guarantees the output strictly adheres to project constraints.
