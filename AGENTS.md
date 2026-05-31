# AGENTS.md

This repository is a local research operator for Tomoko.

It controls a logged-in Chrome/Chromium tab through the Chrome DevTools Protocol
and exposes a small MCP-style research capability to Tomoko. It is intentionally
separate from the Tomoko runtime repository.

## Hard Boundaries

- Do not import Tomoko application code from this repository.
- Do not write to the Tomoko PostgreSQL database from this repository.
- Do not store user private conversation history in provider prompts or raw artifacts.
- Do not copy GPL code from `chatgpt-el`; use it only as prior art and reimplement locally.
- Do not make Chrome automation part of Tomoko's hot conversation path.
- Do not treat browser UI automation as reliable. Every operation must have timeout,
  failure, and `needs_human` states.

## Responsibilities

This repository owns:

- Connecting to a local Chrome DevTools endpoint.
- Opening or reusing a Perplexity tab.
- Submitting one query at a time.
- Waiting for a completed browser response.
- Capturing raw artifacts for debugging.
- Returning a structured `ResearchResult`.

Tomoko owns:

- Rule-based search intent detection.
- Calling this operator.
- Validating returned results.
- Inserting research jobs/results/citations into Tomoko DB.
- Emitting `ResearchResultReady` into TomoroSession.
- Deciding when to say "調べ終わったよ" or reveal the answer.

## Work Rules

- Keep provider-specific DOM selectors isolated in `perplexity.py`.
- Keep CDP transport isolated in `cdp.py`.
- Keep result shapes in `models.py`.
- Add tests before changing parsing, completion detection, or status mapping.
- Prefer deterministic rules over LLM interpretation.
- Raw HTML, screenshots, and downloaded Markdown belong under `artifacts/` and must not be committed.

## Verification

Run before commit:

```bash
uv run pytest
uv run ruff check .
```

If Chrome/Perplexity behavior is changed, also run a manual smoke against a
dedicated Chrome profile and record the result in `LOG.md`.

