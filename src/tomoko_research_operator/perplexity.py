from __future__ import annotations

from dataclasses import dataclass

from tomoko_research_operator.models import Citation, ResearchRequest, ResearchResult

PERPLEXITY_URL = "https://www.perplexity.ai/"
ASK_INPUT_SELECTOR = 'div#ask-input[contenteditable="true"]'
SUBMIT_BUTTON_SELECTOR = (
    'button[aria-label*="停止"], button[aria-label*="Stop"], '
    'button[aria-label="送信"], button[aria-label="Submit"]'
)
RESPONSE_SELECTOR = 'div[id^="markdown-content-"]'


@dataclass(frozen=True, slots=True)
class ExtractedPerplexityResponse:
    text: str
    citations: tuple[Citation, ...] = ()


def build_prompt(request: ResearchRequest) -> str:
    request.validate()
    lines = [
        request.normalized_query(),
        "",
        "回答は日本語で、根拠がある範囲だけを短くまとめてください。",
        "可能なら出典URLも示してください。",
    ]
    if request.recency:
        lines.append(f"鮮度条件: {request.recency}")
    if request.mode == "quick":
        lines.append("長い調査ではなく、口頭で読める短い答えを優先してください。")
    else:
        lines.append("少し深く調べ、重要な相違点と未確定点を分けてください。")
    return "\n".join(lines)


def result_from_extracted(
    request: ResearchRequest,
    extracted: ExtractedPerplexityResponse,
    *,
    provider_trace_id: str | None = None,
    raw_artifact_path: str | None = None,
) -> ResearchResult:
    text = extracted.text.strip()
    if not text:
        return ResearchResult.failed(request.normalized_query(), "empty response", status="failed")
    bullets = tuple(line.strip("- ").strip() for line in text.splitlines() if line.strip().startswith("- "))
    short_answer = next((line.strip() for line in text.splitlines() if line.strip()), text)
    return ResearchResult(
        status="completed",
        query=request.normalized_query(),
        short_answer=short_answer,
        bullets=bullets,
        citations=extracted.citations,
        confidence=0.7,
        provider_trace_id=provider_trace_id,
        raw_artifact_path=raw_artifact_path,
    )

