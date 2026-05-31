# PLAN.md

## Phase 0: Project Footing

- [x] Create separate git repository next to Tomoko.
- [x] Document Tomoko/operator responsibility boundary.
- [x] Add MCP-style DTO and provider skeleton.
- [x] Add tests for DTO/status basics.
- [x] Initial commit.

## Phase 1: CDP Smoke

- [x] Connect to `http://127.0.0.1:9000/json/version`.
- [x] List page targets from `/json/list`.
- [x] Open a fresh Perplexity tab per request by default.
- [x] Read current title and URL through `Runtime.evaluate`.
- [x] Add unit tests for target selection without a live browser.
- [x] Add a manual smoke note to `LOG.md`.

## Phase 2: Perplexity Query Round Trip

- [x] Submit a query to the visible Perplexity input.
- [x] Wait for a non-empty answer.
- [x] Detect completion with stop-button and stable-text heuristics.
- [x] Save raw text/HTML artifact.
- [x] Return `ResearchResult(status="completed")`.
- [x] Return `needs_human` for login/captcha/blocked states.

## Phase 3: MCP Server

- [x] Expose `research.search` through a real MCP server.
- [x] Preserve the same `ResearchRequest` / `ResearchResult` DTO.
- [x] Add a JSON CLI wrapper for local smoke.
- [ ] Document Tomoko integration contract.

## Phase 4: Tomoko Integration Plan

- [ ] Add Tomoko-side rule-based `SearchIntentDetector`.
- [ ] Add Tomoko-side research client.
- [ ] Add Tomoko DB schema for jobs/results/citations.
- [ ] Emit `ResearchResultReady` into TomoroSession.
- [ ] Add notice/reveal candidate handling.
