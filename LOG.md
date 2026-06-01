# LOG.md

## 2026-06-01 Session 1

### Planned

- Stop losing the provider response after the first speakable line.
- Keep the existing `short_answer` behavior while carrying full text across the
  operator DTO and MCP response.

### Done

- Added `ResearchResult.full_text`.
- Populated `full_text` from the extracted Perplexity response.
- Added unit coverage that model shaping and MCP structured output include
  `full_text`.
- Updated architecture and repo memory docs for the new DTO contract.

### Verification

- `mise x python@3.14 uv@0.11.16 -- uv run pytest`
  - 18 passed
- `mise x python@3.14 uv@0.11.16 -- uv run ruff check .`
  - pass

## 2026-05-31 Session 1

### Planned

- Create the first project footing for a Perplexity-focused research operator.
- Keep it separate from Tomoko and from GPL code copied from `chatgpt-el`.
- Add architecture docs, agent instructions, basic DTOs, and tests.

### Done

- Added project docs: `AGENTS.md`, `README.md`, `ARCHITECTURE.md`, `PLAN.md`, and `MEMORY.md`.
- Added original Python scaffold for `ResearchRequest`, `ResearchResult`, CDP target selection, Perplexity prompt/result shaping, CLI placeholder, and MCP placeholder.
- Added unit tests for DTO validation, prompt shaping, result shaping, and CDP target selection.

### Verification

- `PYTHONPATH=src /Users/seijiro/.local/share/mise/installs/python/3.14/bin/pytest -q`
  - 7 passed
- `PYTHONPATH=src python3 -m compileall src tests`
  - pass
- `uv run pytest` / `uv run ruff check .`
  - not run because `uv` is not available in this shell
- `python3 -m ruff check .`
  - not run because `ruff` is not installed in this shell

## 2026-05-31 Session 2

### Planned

- Implement the first real Chrome CDP and Perplexity query round trip.
- Harden tab handling enough to reuse or create a Perplexity tab safely.
- Keep provider-specific DOM selectors in `perplexity.py`.
- Add unit tests for target parsing, local-host CDP guardrails, and status mapping.

### Done

- Added `ChromeBrowserClient` for local-only `/json/version`, `/json/list`,
  `/json/new`, and `/json/activate` usage.
- Added `CdpSession` helpers for `Runtime.evaluate`, navigation, ready-state
  waits, page info, and CDP error handling.
- Added `PerplexityResearchProvider` with composer readiness polling, prompt
  submission, stop-button plus stable-text completion detection, needs-human
  classification, citation extraction, and JSON artifact capture.
- Changed provider tab ownership to open a fresh Perplexity tab per request by
  default, avoiding stale result-page follow-up composers.
- Wired `tomoko-research search` and `mcp_server.research_search` through the
  same provider.
- Added a minimal stdio MCP/JSON-RPC server entrypoint as
  `tomoko-research-mcp`, exposing `tools/list` and `tools/call` for
  `research.search`.
- Added package build metadata so `uv run pytest` can import the `src/` package.

### Manual Smoke

- Connected to Chrome on `127.0.0.1:9000`.
- Observed browser version `Chrome/149.0.7827.53`.
- Ran:
  `mise x python@3.14 uv@0.11.16 -- uv run tomoko-research search "2026年5月31日の日本の首相は誰ですか。短く答えてください" --timeout-sec 60 --artifacts-dir artifacts/smoke`
- Result:
  - `status="completed"`
  - artifact saved under `artifacts/smoke/perplexity-20260531T095823Z.json`
  - first CDP live bug found and fixed: `/json/activate` returns plain text,
    not JSON.
  - second live issue found and fixed: submit-button detection can race page
    hydration, so the provider now waits for a ready composer before inserting
    and submitting text.
- MCP stdio smoke:
  - `printf ... "tools/list" | mise x python@3.14 uv@0.11.16 -- uv run tomoko-research-mcp`
  - returned one tool named `research.search`.
- Follow-up MCP call smoke after fresh-tab change:
  - `tools/call` with query `今日のOpenAI関連ニュースを短く調べて`
  - `status="completed"`
  - artifact saved under `artifacts/perplexity-20260531T101202Z.json`

### Verification

- `mise x python@3.14 uv@0.11.16 -- uv run pytest`
  - 17 passed
- `mise x python@3.14 uv@0.11.16 -- uv run ruff check .`
  - pass
