from __future__ import annotations

from tomoko_research_operator.mcp_server import TOOL_NAME, handle_json_rpc


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
