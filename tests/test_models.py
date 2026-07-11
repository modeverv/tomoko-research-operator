from __future__ import annotations

import pytest

from tomoko_research_operator.models import (
    ResearchRequest,
    ResearchResult,
    WorldObservationRequest,
    WorldObservationResult,
)
from tomoko_research_operator.perplexity import (
    ExtractedPerplexityResponse,
    build_prompt,
    classify_needs_human,
    result_from_extracted,
    snapshot_from_payload,
)
from tomoko_research_operator.chatgpt import CHATGPT_URL, ChatGPTResearchProvider, _snapshot_script


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


def test_world_observation_request_requires_prompt_title_and_observed_at() -> None:
    with pytest.raises(ValueError, match="prompt"):
        WorldObservationRequest(prompt=" ", title="world", observed_at="2026-06-05").validate()
    with pytest.raises(ValueError, match="title"):
        WorldObservationRequest(prompt="prompt", title=" ", observed_at="2026-06-05").validate()
    with pytest.raises(ValueError, match="observed_at"):
        WorldObservationRequest(prompt="prompt", title="world", observed_at=" ").validate()


def test_failed_world_observation_result_must_use_failure_status() -> None:
    with pytest.raises(ValueError, match="failed world observation status"):
        WorldObservationResult.failed(
            "world_observation_2026-06-05",
            "2026-06-05T09:00:00+09:00",
            "reason",
            status="completed",
        )  # type: ignore[arg-type]


def test_build_prompt_keeps_query_and_mode_instruction() -> None:
    prompt = build_prompt(ResearchRequest(query="今日のAIニュース", mode="quick"))
    assert "今日のAIニュース" in prompt
    assert "口頭で読める短い答え" in prompt


def test_build_prompt_requests_a_speakable_answer_and_separate_sources() -> None:
    prompt = build_prompt(ResearchRequest(query="今日のニュース"))

    assert "読み上げ" in prompt
    assert "URL・媒体名・引用記号を入れない" in prompt
    assert "出典URLだけを列挙" in prompt


def test_chatgpt_provider_uses_chatgpt_target_and_result_provider() -> None:
    provider = ChatGPTResearchProvider()

    assert provider.provider_name == "chatgpt"
    assert provider.provider_url == CHATGPT_URL


def test_chatgpt_snapshot_script_keeps_plain_text_source_urls_as_citations() -> None:
    assert "matchAll" in _snapshot_script()


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


def test_result_from_extracted_strips_inline_citation_chips_and_source_tail() -> None:
    result = result_from_extracted(
        ResearchRequest(query="食料自給率"),
        ExtractedPerplexityResponse(
            text=(
                "日本の食料自給率は38％です 。 maff.go +1\n"
                "主な数値\n"
                "カロリーベース食料自給率 38％ 並み maff.go\n"
                "農林水産省のページ https://www.maff.go.jp/j/press/kanbo/anpo/251010.html\n"
                "コメ価格高騰で生産額ベースは上昇した mainichi +1\n"
                "政府の2030年度目標は45％だが、未達です sankei +1\n"
                "出典 農林水産省「令和6年度食料自給率」: https://www.maff.go.jp/example"
            )
        ),
    )

    assert result.full_text == (
        "日本の食料自給率は38％です。\n"
        "主な数値\n"
        "カロリーベース食料自給率 38％ 並み\n"
        "農林水産省のページ\n"
        "コメ価格高騰で生産額ベースは上昇した\n"
        "政府の2030年度目標は45％だが、未達です"
    )
    assert "maff.go" not in result.full_text
    assert "mainichi +1" not in result.full_text
    assert "sankei +1" not in result.full_text
    assert "https://www.maff.go.jp/j/press/kanbo/anpo/251010.html" not in result.full_text
    assert "https://www.maff.go.jp/example" not in result.full_text


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


def test_snapshot_from_payload_defers_blocked_state_while_generating() -> None:
    snapshot = snapshot_from_payload(
        {
            "url": "https://www.perplexity.ai/",
            "title": "Perplexity",
            "text": "This long answer is still generating and mentions blocked requests.",
            "html": "<main>still running</main>",
            "isGenerating": True,
            "citations": [],
        }
    )

    assert snapshot.is_generating
    assert snapshot.needs_human_reason is None
