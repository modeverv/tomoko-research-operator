from __future__ import annotations

"""Placeholder for the real MCP server boundary.

The first committed shape keeps DTOs and CLI stable. Phase 3 will wire these
models into the Python MCP SDK or an equivalent stdio server.
"""

from tomoko_research_operator.models import ResearchRequest, ResearchResult


def research_search(request: ResearchRequest) -> ResearchResult:
    request.validate()
    return ResearchResult.failed(
        request.normalized_query(),
        "MCP server is not implemented yet",
        status="needs_human",
    )

