from __future__ import annotations

import pytest

import tomoko_research_operator.mcp_server as mcp_server
from tomoko_research_operator.mcp_server import TOOL_NAME, WORLD_OBSERVE_TOOL_NAME, handle_json_rpc
from tomoko_research_operator.models import (
    ResearchRequest,
    ResearchResult,
    WorldObservationRequest,
    WorldObservationResult,
)


def test_mcp_initialize_response_contains_tools_capability() -> None:
    response = handle_json_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert response is not None
    assert response["id"] == 1
    assert response["result"]["capabilities"] == {"tools": {}}


def test_mcp_tools_list_exposes_research_search() -> None:
    response = handle_json_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert response is not None
    tool_names = [tool["name"] for tool in response["result"]["tools"]]
    assert TOOL_NAME in tool_names
    assert WORLD_OBSERVE_TOOL_NAME in tool_names


def test_research_provider_defaults_to_chatgpt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TOMOKO_RESEARCH_PROVIDER", raising=False)

    provider = mcp_server._research_provider()

    assert provider.provider_name == "chatgpt"


def test_research_provider_can_select_perplexity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOMOKO_RESEARCH_PROVIDER", "perplexity")

    provider = mcp_server._research_provider()

    assert provider.provider_name == "perplexity"


def test_mcp_tools_call_rejects_unknown_tool() -> None:
    response = handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "unknown", "arguments": {"query": "x"}},
        }
    )

    assert response is not None
    assert response["error"]["code"] == -32602


def test_mcp_tools_call_includes_full_text(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_research_search(request: ResearchRequest) -> ResearchResult:
        return ResearchResult(
            status="completed",
            query=request.normalized_query(),
            short_answer="冒頭だけです。",
            full_text="冒頭だけです。\n続きの本文です。",
        )

    monkeypatch.setattr(mcp_server, "research_search", fake_research_search)
    response = handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": TOOL_NAME, "arguments": {"query": "世界情勢"}},
        }
    )

    assert response is not None
    payload = response["result"]["structuredContent"]
    assert payload["short_answer"] == "冒頭だけです。"
    assert payload["full_text"] == "冒頭だけです。\n続きの本文です。"


def test_mcp_tools_call_world_observe_returns_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_world_observe(request: WorldObservationRequest) -> WorldObservationResult:
        return WorldObservationResult(
            status="completed",
            title=request.title,
            observed_at=request.observed_at,
            markdown_text="# 外界観測\n本文です。",
            provider_trace_id="world-observation-test",
        )

    monkeypatch.setattr(mcp_server, "world_observe", fake_world_observe)
    response = handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": WORLD_OBSERVE_TOOL_NAME,
                "arguments": {
                    "prompt": "公開情報だけでまとめて",
                    "title": "world_observation_2026-06-05",
                    "observed_at": "2026-06-05T09:00:00+09:00",
                },
            },
        }
    )

    assert response is not None
    payload = response["result"]["structuredContent"]
    assert payload["status"] == "completed"
    assert payload["markdown_text"] == "# 外界観測\n本文です。"
    assert payload["provider_trace_id"] == "world-observation-test"


def test_world_observation_provider_config_reads_timeout_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TOMOKO_WORLD_OBSERVATION_PROVIDER_TIMEOUT_SEC", "321")

    config = mcp_server._world_observation_provider_config()

    assert config.response_timeout_sec == 321
    assert config.min_answer_chars == 1200


def test_world_observation_provider_config_defaults_to_long_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TOMOKO_WORLD_OBSERVATION_PROVIDER_TIMEOUT_SEC", raising=False)

    config = mcp_server._world_observation_provider_config()

    assert config.response_timeout_sec == 600
    assert config.min_answer_chars == 1200
