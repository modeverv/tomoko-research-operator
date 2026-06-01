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

### Preserve full provider text at the operator boundary

`ResearchResult.short_answer` is for short speakable previews. The operator
should also return `ResearchResult.full_text` so downstream Tomoko code can
store or summarize the complete provider response without reading raw artifacts.
Provider source appendices such as trailing `出典:` sections should be stripped
from `full_text`; URLs belong in structured `citations` and raw artifacts.

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
  Markdown, or both.
