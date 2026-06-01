from __future__ import annotations

import pytest

import tomoko_research_operator.mcp_server as mcp_server
from tomoko_research_operator.mcp_server import TOOL_NAME, handle_json_rpc
from tomoko_research_operator.models import ResearchRequest, ResearchResult


def test_mcp_initialize_response_contains_tools_capability() -> None:
    response = handle_json_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert response is not None
    assert response["id"] == 1
    assert response["result"]["capabilities"] == {"tools": {}}


def test_mcp_tools_list_exposes_research_search() -> None:
    response = handle_json_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert response is not None
    assert response["result"]["tools"][0]["name"] == TOOL_NAME


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
