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

## Open Questions

- Whether the first production boundary should be real MCP stdio immediately or
  a CLI-compatible JSON contract that is later wrapped by MCP.
- Whether Perplexity response parsing should prefer DOM text, downloaded
  Markdown, or both.

