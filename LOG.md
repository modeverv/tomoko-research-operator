# LOG.md

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
