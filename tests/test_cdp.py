from __future__ import annotations

from tomoko_research_operator.cdp import ChromeTarget, choose_target


def test_choose_target_prefers_most_recent_matching_page() -> None:
    targets = [
        ChromeTarget("1", "https://www.perplexity.ai/", "old", "ws://old"),
        ChromeTarget("2", "https://example.com/", "other", "ws://other"),
        ChromeTarget("3", "https://www.perplexity.ai/search/foo", "new", "ws://new"),
    ]

    target = choose_target(targets, "https://www.perplexity.ai/")

    assert target is not None
    assert target.websocket_debugger_url == "ws://new"


def test_choose_target_returns_none_without_match() -> None:
    assert choose_target([], "https://www.perplexity.ai/") is None

