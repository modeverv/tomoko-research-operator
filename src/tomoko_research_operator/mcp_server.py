"""MCP-style research boundary.

This module intentionally keeps the function boundary small so Tomoko can call
the same DTO-shaped capability through a real MCP stdio wrapper later.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from tomoko_research_operator.artifacts import json_default
from tomoko_research_operator.models import ResearchRequest, ResearchResult
from tomoko_research_operator.perplexity import PerplexityResearchProvider

PROTOCOL_VERSION = "2024-11-05"
TOOL_NAME = "research.search"


def research_search(request: ResearchRequest) -> ResearchResult:
    return PerplexityResearchProvider().search(request)


def tool_schema() -> dict[str, Any]:
    return {
        "name": TOOL_NAME,
        "description": "Search Perplexity through a local logged-in Chrome tab.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "mode": {"type": "string", "enum": ["quick", "deep"], "default": "quick"},
                "locale": {"type": "string", "default": "ja-JP"},
                "recency": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }


def handle_json_rpc(payload: dict[str, Any]) -> dict[str, Any] | None:
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "tomoko-research-operator", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return _result(request_id, {"tools": [tool_schema()]})
    if method == "tools/call":
        name = params.get("name")
        if name != TOOL_NAME:
            return _error(request_id, -32602, f"unknown tool: {name}")
        arguments = params.get("arguments")
        if not isinstance(arguments, dict):
            return _error(request_id, -32602, "tools/call arguments must be an object")
        try:
            result = research_search(
                ResearchRequest(
                    query=str(arguments.get("query") or ""),
                    mode=arguments.get("mode", "quick"),
                    locale=str(arguments.get("locale") or "ja-JP"),
                    recency=arguments.get("recency"),
                )
            )
        except ValueError as exc:
            return _error(request_id, -32602, str(exc))
        result_payload = json.loads(json.dumps(result, default=json_default, ensure_ascii=False))
        return _result(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result_payload, ensure_ascii=False),
                    }
                ],
                "structuredContent": result_payload,
                "isError": result.status != "completed",
            },
        )
    return _error(request_id, -32601, f"method not found: {method}")


def serve_stdio(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("JSON-RPC payload must be an object")
            response = handle_json_rpc(payload)
        except Exception as exc:  # noqa: BLE001 - stdio server must return protocol errors
            response = _error(None, -32700, str(exc))
        if response is None:
            continue
        stdout.write(json.dumps(response, default=json_default, ensure_ascii=False) + "\n")
        stdout.flush()


def main() -> None:
    serve_stdio()


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
