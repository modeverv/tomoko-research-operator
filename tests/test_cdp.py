from __future__ import annotations

import pytest

from tomoko_research_operator.cdp import (
    CdpError,
    ChromeBrowserClient,
    ChromeTarget,
    _targets_from_payload,
    choose_target,
)


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


def test_targets_from_payload_filters_non_pages_and_missing_websocket() -> None:
    targets = _targets_from_payload(
        [
            {"type": "service_worker", "url": "https://www.perplexity.ai/", "id": "skip"},
            {"type": "page", "url": "https://example.com/", "id": "no-ws"},
            {
                "type": "page",
                "id": "keep",
                "url": "https://www.perplexity.ai/",
                "title": "Perplexity",
                "webSocketDebuggerUrl": "ws://keep",
            },
        ]
    )

    assert targets == [
        ChromeTarget(
            id="keep",
            url="https://www.perplexity.ai/",
            title="Perplexity",
            websocket_debugger_url="ws://keep",
        )
    ]


def test_targets_from_payload_rejects_unexpected_shape() -> None:
    with pytest.raises(CdpError, match="unexpected"):
        _targets_from_payload("not a target")


def test_browser_client_rejects_non_local_host() -> None:
    with pytest.raises(ValueError, match="local"):
        ChromeBrowserClient(host="example.com")


def test_browser_client_accepts_plain_text_activate_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            return None

        def read(self) -> bytes:
            return b"Target activated"

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: FakeResponse())

    assert ChromeBrowserClient().request_json("/json/activate/target") == "Target activated"
