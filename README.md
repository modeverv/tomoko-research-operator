# tomoko-research-operator

Local Perplexity research operator for Tomoko.

This project is the intentionally messy edge of web research. It can drive a
logged-in Chrome/Chromium instance through Chrome DevTools Protocol, ask
Perplexity a question, wait for the answer to settle, and return a structured
result to Tomoko.

Tomoko should see this as an external capability, not as part of its conversation
state machine.

## Shape

```text
Tomoko rule detector
  -> research.search(query, mode, locale)
  -> tomoko-research-operator
       -> Chrome CDP
       -> Perplexity UI
       -> raw artifact
       -> ResearchResult JSON
  -> Tomoko validates and writes DB rows
  -> TomoroSession receives ResearchResultReady
```

The first implementation targets Perplexity only. Multi-provider support can
come later behind the same result model.

## Requirements

- Python 3.11+
- `uv`
- Chrome or Chromium launched with a local debugging port
- A logged-in Perplexity session in that Chrome profile

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
uv run tomoko-research search "Perplexity API pricing latest" --mode quick
```

Expected output is a single JSON `ResearchResult`.

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

## License Note

This project may study `chatgpt-el` behavior and selectors, but it does not copy
its GPL implementation. Keep this repository's implementation original unless
you intentionally change this repository's licensing posture.

