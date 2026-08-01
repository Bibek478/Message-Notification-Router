This file governs *how* we build. The platform's `AGENTS.md` at repo root governs the mandatory onboarding/logging contract and the dataset/output contract — read that too, and never edit it.

---

## Read Before Anything Else

Read in this order before writing any code:

1. `AGENTS.md` (repo root) — platform contract, logging rules, dataset/output spec. Non-negotiable, not ours to change.
2. `context/project-overview.md` — problem scope, in/out of scope, MVP definition
3. `context/architecture.md` — model-observes/code-decides boundary, data flow
4. `context/schemas.md` — Pydantic schemas for model output and decision I/O
5. `context/code-standards.md` — conventions
6. `context/decision-log.md` — decisions made so far, so you don't re-litigate them
7. `context/progress-tracker.md` — current build state

---

## Rules That Never Change

- **The model observes, code decides.** The LLM fills a structured schema describing what it perceived. A separate deterministic function reads that schema and makes the notify/digest/mute call. Never let the model's free text or its own confidence claim be the final authority.
- Every decision-logic branch must have a corresponding unit test using a fabricated (fake) model output — no API call needed to test decision code.
- Every guardrail/validation rule lives in code, applied *after* the model call — never trust the prompt alone to enforce a safety-critical rule.
- Before proposing a non-trivial design choice, state it and wait for confirmation rather than just implementing it. Trivial choices (variable naming, which stdlib function) don't need this.
- Never write to `context/decision-log.md` on your own initiative. Append only when the user has already stated the reasoning in this conversation, and even then, ask before appending.
- Update `context/progress-tracker.md` after every completed feature.
- Never touch organizer-only files or hardcode labels — per `AGENTS.md` §6.3.
- Comply with the logging requirements in `AGENTS.md` §5 for every turn — this is separate from and in addition to `decision-log.md`.

---

## Working Style

- Read context files first. Never assume — verify against `architecture.md` before implementing.
- One feature at a time. Fully complete and testable before moving to the next.
- When something breaks the same way twice after a correction, stop and say so — don't keep guessing.
- Flag scope creep. If a request goes beyond what `project-overview.md` defines as in-scope, say so before building it.
