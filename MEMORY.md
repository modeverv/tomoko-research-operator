# MEMORY.md

## Confirmed Decisions

### Keep browser automation outside Tomoko

Chrome/Perplexity automation is fragile and account/UI dependent. It must stay in
this separate project. Tomoko should call it through an MCP-style capability and
own DB persistence itself.

### Rule-based invocation, not LLM tool calling

Tomoko should decide to call `research.search` through deterministic intent
detection. The conversation LLM should not autonomously choose this external
tool or send private memory to it.

### Do not copy chatgpt-el implementation

`chatgpt-el` is useful prior art for CDP selectors and workflow, but its source
files are GPLv3-or-later. This project starts as an original implementation.

### One provider path for CLI and MCP-style calls

`tomoko-research search` and `mcp_server.research_search` should call the same
`PerplexityResearchProvider` so smoke behavior and the eventual MCP boundary do
not drift.

### World observation uses the same operator boundary

Tomoko world-observation collection should not depend on Codex or Computer Use.
The operator exposes `world.observe` through the same MCP-style stdio server and
uses the same Chrome CDP / Perplexity provider path. The operator returns a
`WorldObservationResult.markdown_text` draft and raw artifact path; Tomoko owns
validated `informations/` frontmatter, DB ingest, and interpretation.

### Preserve full provider text at the operator boundary

`ResearchResult.short_answer` is for short speakable previews. The operator
should also return `ResearchResult.full_text` so downstream Tomoko code can
store or summarize the complete provider response without reading raw artifacts.
Provider source appendices such as trailing `出典:` sections should be stripped
from `full_text`; inline citation-chip text such as `maff.go +1` should also be
removed from cleaned answer text. Inline URLs should not be part of speakable
text; URLs belong in structured `citations` and raw artifacts.

### Wait for Perplexity composer readiness

Perplexity can expose the contenteditable input before the submit button is
ready. The provider should wait for both input and a visible submit button before
inserting text, then use stable text plus no stop button as completion evidence.

### Fresh tab per request

Each `research.search` call should open a fresh Perplexity tab by default. Reusing
an existing Perplexity tab can pick up a completed result page and its follow-up
composer, where the submit button stays disabled until after text insertion.

## Open Questions

- Whether the first production boundary should be real MCP stdio immediately or
  a CLI-compatible JSON contract that is later wrapped by MCP.
- Whether Perplexity response parsing should prefer DOM text, downloaded
  Markdown, or both. For now Tomoko re-adds deterministic frontmatter around the
  provider text before validation.

## Confirmed Decisions 2026-06-05

### World observation waits up to 600 seconds

The previous 240-second world-observation provider timeout is too short for long
Perplexity generations. The default `world.observe` provider timeout is now 600
seconds, while `TOMOKO_WORLD_OBSERVATION_PROVIDER_TIMEOUT_SEC` remains the
override.

### Do not classify needs-human while generation is active

Perplexity page text can contain words such as `blocked` while a long answer is
still streaming. `snapshot_from_payload()` should defer `classify_needs_human()`
when `isGenerating=true` and only treat block/login/captcha markers as terminal
after generation is no longer active.
