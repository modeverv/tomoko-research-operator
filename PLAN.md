# PLAN.md

## Phase 0: Project Footing

- [x] Create separate git repository next to Tomoko.
- [x] Document Tomoko/operator responsibility boundary.
- [x] Add MCP-style DTO and provider skeleton.
- [x] Add tests for DTO/status basics.
- [x] Initial commit.

## Phase 1: CDP Smoke

- [ ] Connect to `http://127.0.0.1:9000/json/version`.
- [ ] List page targets from `/json/list`.
- [ ] Reuse or open a Perplexity tab.
- [ ] Read current title and URL through `Runtime.evaluate`.
- [ ] Add unit tests for target selection without a live browser.
- [ ] Add a manual smoke note to `LOG.md`.

## Phase 2: Perplexity Query Round Trip

- [ ] Submit a query to the visible Perplexity input.
- [ ] Wait for a non-empty answer.
- [ ] Detect completion with stop-button and stable-text heuristics.
- [ ] Save raw text/HTML artifact.
- [ ] Return `ResearchResult(status="completed")`.
- [ ] Return `needs_human` for login/captcha/blocked states.

## Phase 3: MCP Server

- [ ] Expose `research.search` through a real MCP server.
- [ ] Preserve the same `ResearchRequest` / `ResearchResult` DTO.
- [ ] Add a JSON CLI wrapper for local smoke.
- [ ] Document Tomoko integration contract.

## Phase 4: Tomoko Integration Plan

- [ ] Add Tomoko-side rule-based `SearchIntentDetector`.
- [ ] Add Tomoko-side research client.
- [ ] Add Tomoko DB schema for jobs/results/citations.
- [ ] Emit `ResearchResultReady` into TomoroSession.
- [ ] Add notice/reveal candidate handling.

