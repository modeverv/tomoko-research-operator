from __future__ import annotations

import pytest

from tomoko_research_operator.models import ResearchRequest, ResearchResult
from tomoko_research_operator.perplexity import (
    ExtractedPerplexityResponse,
    build_prompt,
    classify_needs_human,
    result_from_extracted,
    snapshot_from_payload,
)


def test_research_request_normalizes_query() -> None:
    request = ResearchRequest(query="  Perplexity   API   最新  ")
    assert request.normalized_query() == "Perplexity API 最新"


def test_research_request_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="query"):
        ResearchRequest(query="   ").validate()


def test_research_request_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        ResearchRequest(query="x", mode="slow").validate()  # type: ignore[arg-type]


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
    assert result.full_text == "結論です。\n- 根拠1\n- 根拠2"
    assert result.bullets == ("根拠1", "根拠2")
    assert result.is_speakable()


def test_result_from_extracted_strips_trailing_source_section() -> None:
    result = result_from_extracted(
        ResearchRequest(query="調べて"),
        ExtractedPerplexityResponse(
            text=(
                "結論です。\n"
                "詳しい本文です。\n\n"
                "出典：\n"
                "ロイター：https://example.com/reuters\n"
                "日経：https://example.com/nikkei"
            )
        ),
    )

    assert result.short_answer == "結論です。"
    assert result.full_text == "結論です。\n詳しい本文です。"
    assert "出典" not in result.full_text


def test_classify_needs_human_detects_login_and_captcha() -> None:
    assert classify_needs_human("https://www.perplexity.ai/", "Please sign in") == "login required"
    assert (
        classify_needs_human("https://www.perplexity.ai/", "Verify you are human")
        == "captcha or verification"
    )


def test_snapshot_from_payload_extracts_citations_and_blocked_state() -> None:
    snapshot = snapshot_from_payload(
        {
            "url": "https://www.perplexity.ai/",
            "title": "Perplexity",
            "text": "Access denied",
            "html": "<main>Access denied</main>",
            "isGenerating": False,
            "citations": [
                {"title": "Example", "url": "https://example.com/page", "host": "example.com"},
                {"title": "No URL"},
            ],
        }
    )

    assert snapshot.needs_human_reason == "blocked by provider"
    assert len(snapshot.citations) == 1
    assert snapshot.citations[0].url == "https://example.com/page"
