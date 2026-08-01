# Code Standards

Implementation rules for this project. Python, terminal agent, no frontend.

---

## Engineering Mindset

- Read context files before implementing — never assume.
- Scope is sacred — only build what the current feature requires.
- Every feature must be testable immediately after implementation.
- Clean over clever — code a stranger (or interviewer) can read without you narrating it.
- One thing at a time. Complete one piece fully before starting the next.
- Failures are expected — wrap model calls and I/O in try/except, log, never let one row crash the whole run.

---

## Python

- Python 3.11+ features are fine (match statements, `X | Y` unions).
- Type hints on every function signature — parameters and return type, no exceptions.
- Never use bare `Any` — narrow with `Union`/`Literal`/a real type where possible.
- Pydantic models for every structured boundary: model output, decision function input/output, CSV row shapes.
- Use `dataclass` only for internal, non-serialized structures where Pydantic validation isn't needed.
- `pathlib.Path` for all file paths — never raw string concatenation.
- f-strings for formatting — never `%` or `.format()`.
- No mutable default arguments (`def f(x: list = [])` is a bug, not a style choice).

---

## File and Function Naming

- Files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes/Pydantic models: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`, defined once, imported everywhere — never re-declared
- **No generic dumping-ground names**: no `helper.py`, `utils.py` (unless genuinely tiny and single-purpose), `final.py`, `test2.py`, `new_main.py`. A stranger should know what's inside from the filename alone.
- One clear responsibility per file. If a file is doing "model calling" and "decision logic," split it — that boundary is the whole architecture.

---

## Project Structure

```
code/
├── main.py              → entry point, orchestrates the full run
├── io_utils.py           → reading dataset/ CSVs, writing output.csv
├── model_client.py       → LLM API calls only, returns structured observation
├── schemas.py            → Pydantic models (or split further if it grows)
├── decision.py           → pure functions, notify/digest/mute logic — NO API calls
├── guardrails.py         → post-model validation, retry limits, fallback rules
├── cache.py               → response caching for evals/reruns
└── config.py              → constants (MATCH thresholds, retry limits, etc.)
tests/
├── test_decision.py       → one test per branch/rule, fabricated model outputs
├── test_guardrails.py
└── golden/                → hand-labeled golden dataset + eval runner
```

`decision.py` must never import anything that makes a network call. This is enforced by review, not by tooling — check it explicitly before submission.

---

## Function Structure

```python
def decide_action(observation: MessageObservation, context: DecisionContext) -> RoutingDecision:
    """One-line description of the rule this function enforces."""
    # early-exit guardrail checks first
    # then branch logic
    # return a fully-typed result — never a raw dict
```

- Every function that can fail returns a typed result or raises a specific exception — never silently returns `None` to mean "failed."
- Docstring states *why* the function exists / what rule it enforces, not what the code literally does line by line.

---

## Error Handling

- No bare `except:` — always catch a specific exception type.
- No empty except blocks — always log or handle.
- Model API failures: retry with a hard cap (define the cap in `config.py`), then fall back to a defined default — never crash the whole batch on one row's failure.
- Log format: `[module_name] message` — e.g. `[model_client] retry 2/3 for message_id=1042`.
- Malformed model output (wrong schema, invalid label) is a guardrail failure, not a crash — validate, reject, retry, or fall back per the rule in `guardrails.md`.

---

## Comments

- No comments explaining *what* the code does — code should be self-explanatory through naming.
- Comments only for *why* — a non-obvious decision, a workaround, a constraint from the dataset.
- No leftover TODOs in submitted code.

---

## Testing

- Every branch in `decision.py` gets a unit test with a fabricated (hand-constructed) `MessageObservation` — zero API calls.
- Every "must never happen" rule gets an explicit adversarial test that tries to violate it and asserts it's blocked.
- Golden dataset evals are separate from unit tests — real API calls, cached, run deliberately not constantly.
- Run pytest before every commit that touches `decision.py` or `guardrails.py`.

---

## Dependencies

Don't add a package without a reason. Check first: does the stdlib already do this? Approved so far:

- `pydantic` — schemas
- `openai` or `anthropic` — model client (pick one, document which in `architecture.md`)
- `pandas` — CSV handling (only if plain `csv` module gets unwieldy)
- `pytest` — testing
- `python-dotenv` — reading `.env` for API keys

Update this list before installing anything not on it.

---

## Environment Variables

- All secrets in `.env`, never hardcoded, never logged (see `AGENTS.md` §5.4).
- `config.py` reads env vars once at import time — nothing else calls `os.environ` directly.

---

## Determinism

- Per `AGENTS.md` §6.3, keep behavior deterministic where possible.
- Set `temperature=0` (or lowest available) for the model's observation call unless you have a specific reason not to — document that reason in `architecture.md` if so.
- Decision logic (`decision.py`) is pure Python — inherently deterministic, no randomness, no time-based branching unless the rule genuinely requires it.
