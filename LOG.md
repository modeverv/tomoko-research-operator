# LOG.md

## 2026-07-11 Session 1

### Done

- Added `ChatGPTResearchProvider` as the default local Chrome backend.
- Kept Perplexity selectable with `--provider perplexity` or
  `TOMOKO_RESEARCH_PROVIDER=perplexity`.
- Added a shared prompt contract for read-aloud-friendly answers: no URLs or
  source labels in the spoken body, plus a "what happened / why it matters"
  structure for multi-item answers.
- Kept ChatGPT DOM selectors and completion detection isolated in `chatgpt.py`.

### Manual Smoke

- Connected to the dedicated Chrome CDP endpoint on `127.0.0.1:9000`.
- Ran the default `tomoko-research search` path against a logged-in ChatGPT
  session for a current Japan-news query.
- Result: `status="completed"`, `provider="chatgpt"`; the answer completed,
  produced a speakable summary, and returned structured source URLs.
- Raw artifact was written under `/tmp/tomoko-chatgpt-smoke-2/` and was not
  added to the repository.

### Verification

- `uv run pytest` — 31 passed
- `uv run ruff check .` — pass
- `git diff --check` — pass

## 2026-06-02 Session 1

### Planned

- Remove Perplexity citation-chip text such as `maff.go +1` and inline URLs
  from cleaned answer text.
- Keep trailing source appendices out of `full_text` even when the heading is
  written as `出典 ...` on the same line.

### Done

- Added a shared answer-text cleaning step before `short_answer`, `full_text`,
  and bullets are derived.
- Added deterministic stripping for inline lowercase citation chips such as
  `maff.go`, `mainichi +1`, and `sankei +1`.
- Added deterministic stripping for inline `http` / `https` URLs before
  speakable text is derived.
- Added unit coverage using a food-self-sufficiency style answer sample.

### Verification

- `mise x python@3.14 uv@0.11.16 -- uv run pytest`
  - 20 passed
- `mise x python@3.14 uv@0.11.16 -- uv run ruff check .`
  - pass

## 2026-06-05 Session 3

### Planned

- Extend world-observation Perplexity response waiting for long generations.
- Avoid treating provider-block text as needs-human while Perplexity is still generating.

### Done

- Changed the world-observation provider timeout default from 240 seconds to 600 seconds.
- Kept `TOMOKO_WORLD_OBSERVATION_PROVIDER_TIMEOUT_SEC` as the override knob.
- Deferred `classify_needs_human()` while `isGenerating=true`, so long answers that mention `blocked` do not become `needs_human` before generation settles.
- Added focused tests for the 600-second default and generating-state block deferral.

### Verification

- `uv run pytest tests/test_mcp_server.py tests/test_models.py -q`
  - 20 passed
- `uv run ruff check src/tomoko_research_operator/mcp_server.py src/tomoko_research_operator/perplexity.py tests/test_mcp_server.py tests/test_models.py`
  - pass
- `git diff --check`
  - pass

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

## 2026-06-01 Session 2

### Planned

- Remove provider-generated trailing source appendices from answer text while
  keeping structured citations.

### Done

- Added deterministic stripping for trailing `出典:` / `出典：` sections before
  populating `short_answer`, `full_text`, and bullets.
- Added unit coverage for source-section stripping.
- Updated architecture and repo memory notes to clarify that citations remain
  structured data.

### Verification

- `mise x python@3.14 uv@0.11.16 -- uv run pytest`
  - 19 passed
- `mise x python@3.14 uv@0.11.16 -- uv run ruff check .`
  - pass

## 2026-06-05 Session 1

### Planned

- Add a world-observation collection tool that Tomoko can call without Codex / Computer Use.
- Reuse the existing Chrome CDP / Perplexity provider path and keep Tomoko DB writes out of this repo.
- Preserve `research.search` behavior while adding a separate MCP tool.

### Done

- Added `WorldObservationRequest` and `WorldObservationResult`.
- Added `PerplexityResearchProvider.observe_world()` using the same fresh-tab, submit, wait, and artifact path as research search.
- Exposed `world.observe` from the stdio MCP server alongside `research.search`.
- Documented that Tomoko owns frontmatter normalization and `informations/` ingest.

### Verification

- `uv run pytest tests/test_mcp_server.py tests/test_models.py -q`
  - 17 passed
- `uv run ruff check src/tomoko_research_operator/models.py src/tomoko_research_operator/perplexity.py src/tomoko_research_operator/mcp_server.py tests/test_mcp_server.py tests/test_models.py`
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
