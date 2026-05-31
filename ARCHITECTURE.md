# ARCHITECTURE.md

## Goal

Provide Tomoko with a cheap local research capability by automating the user's
own logged-in browser session, while keeping browser fragility outside Tomoko.

## Non-Goals

- No Tomoko DB writes.
- No TomoroSession state decisions.
- No LLM tool-calling policy.
- No general browser automation framework.
- No guarantee that Perplexity UI automation is stable.

## Components

```text
Research MCP-style interface
  -> PerplexityResearchProvider
      -> ChromeCdpClient
      -> PerplexityPage
      -> ResponseExtractor
  -> ArtifactStore
  -> ResearchResult
```

## Boundary With Tomoko

Tomoko calls this project and receives structured data. Tomoko then validates and
stores that data in Tomoko's PostgreSQL schema.

This project returns:

- Query metadata.
- Result status.
- Short answer.
- Bullet points.
- Citations.
- Provider trace id.
- Raw artifact path.
- Failure reason when applicable.

This project never decides:

- Whether Tomoko should interrupt.
- Whether a result should enter memory.
- How citations map to Tomoko DB rows.
- Whether a result is safe to speak.

## State Model

Browser automation is job-oriented:

```text
pending -> running -> completed
                  -> failed
                  -> needs_human
                  -> timeout
```

Only one browser job should run at a time at first. Perplexity and Chrome tabs
are shared mutable UI state; concurrency should be added only after a queue and
per-job tab ownership are explicit.

## Chrome Strategy

Use a dedicated Chrome profile where possible. Reusing a daily browser profile is
convenient but risky: existing tabs, focus, extensions, and account state can
change automation behavior.

The operator should:

- Connect only to `127.0.0.1`.
- Prefer a tab whose URL starts with `https://www.perplexity.ai/`.
- Create or navigate a tab when needed.
- Record page URL and title in every artifact.
- Capture enough raw HTML/text to debug selector drift.

## Completion Strategy

Perplexity UI completion is not a protocol event. Treat completion as a heuristic:

- submit button is no longer a stop button, and
- response text has stayed unchanged for a short settle window, and
- minimum non-empty response length is reached.

If these disagree, return `timeout` or `needs_human`, not partial success.

## MCP Shape

Initial tool:

```text
research.search
  input:
    query: string
    mode: quick | deep
    locale: string
    recency: optional string
  output:
    ResearchResult
```

Tomoko may call this through a real MCP client later. The internal implementation
should keep the same DTO even if the first smoke path is CLI.

## Artifact Policy

Raw browser artifacts are debugging records, not Tomoko memory.

- Store artifacts under `artifacts/`.
- Do not commit real artifacts.
- Redact or avoid private account/user data where practical.
- Return only artifact paths and structured excerpts to callers.

