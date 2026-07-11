from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

ResearchMode = Literal["quick", "deep"]
ResearchStatus = Literal["pending", "running", "completed", "failed", "needs_human", "timeout"]
WorldObservationStatus = Literal["completed", "failed", "needs_human", "timeout"]


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    query: str
    mode: ResearchMode = "quick"
    locale: str = "ja-JP"
    recency: str | None = None

    def normalized_query(self) -> str:
        return " ".join(self.query.split())

    def validate(self) -> None:
        if not self.normalized_query():
            raise ValueError("query must not be empty")
        if self.mode not in {"quick", "deep"}:
            raise ValueError("mode must be quick or deep")


@dataclass(frozen=True, slots=True)
class Citation:
    title: str
    url: str
    source: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchResult:
    status: ResearchStatus
    query: str
    provider: str = "perplexity"
    short_answer: str = ""
    full_text: str = ""
    bullets: tuple[str, ...] = ()
    citations: tuple[Citation, ...] = ()
    confidence: float | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    provider_trace_id: str | None = None
    raw_artifact_path: str | None = None
    error_reason: str | None = None

    @classmethod
    def failed(cls, query: str, reason: str, status: ResearchStatus = "failed") -> ResearchResult:
        if status not in {"failed", "needs_human", "timeout"}:
            raise ValueError("failed result status must be failed, needs_human, or timeout")
        return cls(status=status, query=query, error_reason=reason)

    def is_speakable(self) -> bool:
        return self.status == "completed" and bool(self.short_answer.strip())


@dataclass(frozen=True, slots=True)
class WorldObservationRequest:
    prompt: str
    title: str
    observed_at: str
    locale: str = "ja-JP"

    def normalized_prompt(self) -> str:
        return self.prompt.strip()

    def validate(self) -> None:
        if not self.normalized_prompt():
            raise ValueError("prompt must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.observed_at.strip():
            raise ValueError("observed_at must not be empty")


@dataclass(frozen=True, slots=True)
class WorldObservationResult:
    status: WorldObservationStatus
    title: str
    observed_at: str
    provider: str = "perplexity"
    markdown_text: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    provider_trace_id: str | None = None
    raw_artifact_path: str | None = None
    error_reason: str | None = None

    @classmethod
    def failed(
        cls,
        title: str,
        observed_at: str,
        reason: str,
        status: WorldObservationStatus = "failed",
    ) -> WorldObservationResult:
        if status not in {"failed", "needs_human", "timeout"}:
            raise ValueError("failed world observation status must be failed, needs_human, or timeout")
        return cls(status=status, title=title, observed_at=observed_at, error_reason=reason)
