from __future__ import annotations

import pytest

from tomoko_research_operator.models import ResearchRequest, ResearchResult
from tomoko_research_operator.perplexity import (
    ExtractedPerplexityResponse,
    build_prompt,
    result_from_extracted,
)


def test_research_request_normalizes_query() -> None:
    request = ResearchRequest(query="  Perplexity   API   最新  ")
    assert request.normalized_query() == "Perplexity API 最新"


def test_research_request_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="query"):
        ResearchRequest(query="   ").validate()


def test_failed_result_must_use_failure_status() -> None:
    with pytest.raises(ValueError, match="failed result status"):
        ResearchResult.failed("query", "reason", status="completed")  # type: ignore[arg-type]


def test_build_prompt_keeps_query_and_mode_instruction() -> None:
    prompt = build_prompt(ResearchRequest(query="今日のAIニュース", mode="quick"))
    assert "今日のAIニュース" in prompt
    assert "口頭で読める短い答え" in prompt


def test_result_from_extracted_creates_speakable_completed_result() -> None:
    result = result_from_extracted(
        ResearchRequest(query="調べて"),
        ExtractedPerplexityResponse(text="結論です。\n- 根拠1\n- 根拠2"),
    )
    assert result.status == "completed"
    assert result.short_answer == "結論です。"
    assert result.bullets == ("根拠1", "根拠2")
    assert result.is_speakable()

