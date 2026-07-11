# tomoko-research-operator

Local browser-backed research operator for Tomoko. ChatGPT is the default provider;
Perplexity remains available as an explicit fallback.

This project is the intentionally messy edge of web research. It can drive a
logged-in Chrome/Chromium instance through Chrome DevTools Protocol, ask
ChatGPT by default, wait for the answer to settle, and return a structured
result to Tomoko.

Tomoko should see this as an external capability, not as part of its conversation
state machine.

## Shape

```text
Tomoko rule detector / background job
  -> research.search(query, mode, locale)
  -> world.observe(prompt, title, observed_at)
  -> tomoko-research-operator
       -> Chrome CDP
       -> ChatGPT UI (default) / Perplexity UI (optional)
       -> raw artifact
       -> ResearchResult / WorldObservationResult JSON
  -> Tomoko validates and writes DB rows
  -> TomoroSession receives ResearchResultReady
```

The default implementation targets ChatGPT. Perplexity can be selected for
comparison or fallback behind the same result model.

## Requirements

- Python 3.11+
- `uv`
- Chrome or Chromium launched with a local debugging port
- A logged-in ChatGPT session in that Chrome profile

Example Chrome launch:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9000 \
  --remote-allow-origins=http://127.0.0.1:9000 \
  --user-data-dir="$HOME/.chrome-tomoko-research"
```

## Setup

```bash
uv sync
uv run pytest
```

## Planned CLI

The early smoke path is CLI-first so Tomoko integration can stay thin:

```bash
uv run tomoko-research search "今日の日本の主要ニュース" --mode quick
```

Expected output is a single JSON `ResearchResult`.

Use Perplexity explicitly when needed:

```bash
uv run tomoko-research search "今日の日本の主要ニュース" --provider perplexity
```

The MCP server also honors `TOMOKO_RESEARCH_PROVIDER=perplexity`; its default
is `chatgpt`.

## Speakable-answer format

`research.search` adds a provider prompt that asks for a self-contained,
read-aloud-friendly answer. It keeps URLs, outlet names, and citation markers
out of the spoken body; for multi-item answers it asks for "what happened" and
"why it matters" sentences. Structured citations remain separate in
`ResearchResult.citations`.

## MCP Boundary

The production-facing boundary should be MCP protocol or a close local equivalent.
The key design point is not LLM tool calling. Tomoko will call the tool from
deterministic rules:

```text
"調べて" / "検索して" / "最新" / "今どうなってる"
  -> SearchIntentDetector
  -> MCP call research.search
```

The operator does not decide when Tomoko should speak. It only reports
`completed`, `failed`, or `needs_human`.

Local stdio server:

```bash
uv run tomoko-research-mcp
```

The server exposes:

- `research.search`: `query`, `mode`, `locale`, and `recency`.
- `world.observe`: `prompt`, `title`, `observed_at`, and `locale`.

`world.observe` is for Tomoko's world-observation background/manual collection
flow. It returns the provider text as a Markdown draft; Tomoko owns adding the
validated `informations/` frontmatter and running ingest/interpret.

## License Note

This project may study `chatgpt-el` behavior and selectors, but it does not copy
its GPL implementation. Keep this repository's implementation original unless
you intentionally change this repository's licensing posture.
