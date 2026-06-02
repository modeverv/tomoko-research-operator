from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tomoko_research_operator.artifacts import ArtifactStore
from tomoko_research_operator.cdp import (
    CdpError,
    CdpSession,
    CdpTimeoutError,
    ChromeBrowserClient,
    ChromeTarget,
)
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


@dataclass(frozen=True, slots=True)
class PerplexitySnapshot:
    url: str
    title: str
    text: str
    html: str
    is_generating: bool
    needs_human_reason: str | None = None
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True, slots=True)
class PerplexityProviderConfig:
    debug_port: int = 9000
    connect_timeout_sec: float = 10.0
    navigation_timeout_sec: float = 25.0
    response_timeout_sec: float = 90.0
    settle_sec: float = 2.0
    poll_sec: float = 0.5
    min_answer_chars: int = 20
    artifacts_dir: Path = Path("artifacts")
    fresh_tab_per_request: bool = True


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


def classify_needs_human(url: str, text: str) -> str | None:
    haystack = f"{url}\n{text}".lower()
    checks = {
        "login required": ("sign in", "log in", "ログイン", "サインイン"),
        "captcha or verification": ("captcha", "verify you are human", "人間であること", "確認してください"),
        "blocked by provider": ("access denied", "blocked", "too many requests", "rate limit"),
    }
    for reason, markers in checks.items():
        if any(marker.lower() in haystack for marker in markers):
            return reason
    return None


def snapshot_from_payload(payload: dict[str, Any]) -> PerplexitySnapshot:
    citations = tuple(
        Citation(
            title=str(item.get("title") or item.get("url") or ""),
            url=str(item.get("url") or ""),
            source=str(item.get("host") or "") or None,
        )
        for item in payload.get("citations", [])
        if isinstance(item, dict) and item.get("url")
    )
    url = str(payload.get("url") or "")
    text = str(payload.get("text") or "").strip()
    return PerplexitySnapshot(
        url=url,
        title=str(payload.get("title") or ""),
        text=text,
        html=str(payload.get("html") or ""),
        is_generating=bool(payload.get("isGenerating")),
        needs_human_reason=classify_needs_human(url, text),
        citations=citations,
    )


def result_from_extracted(
    request: ResearchRequest,
    extracted: ExtractedPerplexityResponse,
    *,
    provider_trace_id: str | None = None,
    raw_artifact_path: str | None = None,
) -> ResearchResult:
    text = _clean_answer_text(extracted.text)
    if not text:
        return ResearchResult.failed(request.normalized_query(), "empty response", status="failed")
    bullets = tuple(line.strip("- ").strip() for line in text.splitlines() if line.strip().startswith("- "))
    short_answer = next((line.strip() for line in text.splitlines() if line.strip()), text)
    return ResearchResult(
        status="completed",
        query=request.normalized_query(),
        short_answer=short_answer,
        full_text=text,
        bullets=bullets,
        citations=extracted.citations,
        confidence=0.7,
        provider_trace_id=provider_trace_id,
        raw_artifact_path=raw_artifact_path,
    )


def _clean_answer_text(text: str) -> str:
    text = _strip_trailing_source_section(text)
    text = _strip_inline_urls(text)
    text = _strip_inline_citation_chips(text)
    return text.strip()


def _strip_trailing_source_section(text: str) -> str:
    lines = text.strip().splitlines()
    source_headings = {"出典", "出典:", "出典：", "Sources", "Sources:", "Sources："}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped in source_headings or stripped.startswith(("出典 ", "Sources ")):
            return "\n".join(lines[:index]).rstrip()
    return text.strip()


def _strip_inline_citation_chips(text: str) -> str:
    # Perplexity can leak visual citation chips into extracted text, e.g. "maff.go +1".
    citation_chip = re.compile(
        r"(?<![A-Za-z0-9_./:-])"
        r"(?:[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+(?:\s*\+\d+)?|[a-z][a-z0-9-]{2,}\s+\+\d+)"
        r"(?![A-Za-z0-9_./:-])"
    )
    text = citation_chip.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+([、。，．,.;:：])", r"\1", text)
    return "\n".join(line.rstrip() for line in text.splitlines())


def _strip_inline_urls(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+([、。，．,.;:：])", r"\1", text)
    return "\n".join(line.rstrip() for line in text.splitlines())


class PerplexityResearchProvider:
    def __init__(
        self,
        *,
        browser: ChromeBrowserClient | None = None,
        config: PerplexityProviderConfig | None = None,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self.config = config or PerplexityProviderConfig()
        self.browser = browser or ChromeBrowserClient(debug_port=self.config.debug_port)
        self.artifacts = artifact_store or ArtifactStore(self.config.artifacts_dir)

    def search(self, request: ResearchRequest) -> ResearchResult:
        request.validate()
        trace_id = self.artifacts.new_trace_id()
        try:
            target = self._ensure_perplexity_target()
            with CdpSession(
                target.websocket_debugger_url,
                timeout_sec=self.config.connect_timeout_sec,
            ) as session:
                self._prepare_page(session)
                prompt = build_prompt(request)
                self._wait_for_composer(session)
                submit = self._submit_prompt(session, prompt)
                if not submit.get("ok"):
                    return ResearchResult.failed(
                        request.normalized_query(),
                        str(submit.get("reason") or "could not submit query"),
                        status="needs_human",
                    )
                snapshot = self._wait_for_response(session)
                artifact_path = self._write_artifact(trace_id, request, target, snapshot)
                if snapshot.needs_human_reason:
                    return ResearchResult.failed(
                        request.normalized_query(),
                        snapshot.needs_human_reason,
                        status="needs_human",
                    )
                extracted = ExtractedPerplexityResponse(
                    text=snapshot.text,
                    citations=snapshot.citations,
                )
                return result_from_extracted(
                    request,
                    extracted,
                    provider_trace_id=trace_id,
                    raw_artifact_path=str(artifact_path),
                )
        except CdpTimeoutError as exc:
            return ResearchResult.failed(request.normalized_query(), str(exc), status="timeout")
        except (CdpError, OSError, TimeoutError) as exc:
            return ResearchResult.failed(request.normalized_query(), str(exc), status="failed")

    def _ensure_perplexity_target(self) -> ChromeTarget:
        if self.config.fresh_tab_per_request:
            target = self.browser.open_target(PERPLEXITY_URL)
            self.browser.activate_target(target.id)
            return target
        return self.browser.ensure_target(PERPLEXITY_URL, PERPLEXITY_URL)

    def _prepare_page(self, session: CdpSession) -> None:
        info = session.page_info()
        if not info.get("url", "").startswith(PERPLEXITY_URL):
            session.navigate(PERPLEXITY_URL, timeout_sec=self.config.navigation_timeout_sec)
        else:
            session.wait_for_ready_state(timeout_sec=self.config.navigation_timeout_sec)

    def _submit_prompt(self, session: CdpSession, prompt: str) -> dict[str, Any]:
        return _dict_or_reason(
            session.evaluate(_submit_script(prompt), timeout_sec=self.config.connect_timeout_sec)
        )

    def _wait_for_composer(self, session: CdpSession) -> None:
        deadline = time.monotonic() + self.config.navigation_timeout_sec
        last_reason = "composer not checked"
        while time.monotonic() < deadline:
            result = _dict_or_reason(session.evaluate(_composer_ready_script(), timeout_sec=5.0))
            if result.get("ok"):
                return
            last_reason = str(result.get("reason") or "composer not ready")
            time.sleep(self.config.poll_sec)
        raise CdpTimeoutError(f"Perplexity composer was not ready: {last_reason}")

    def _wait_for_response(self, session: CdpSession) -> PerplexitySnapshot:
        deadline = time.monotonic() + self.config.response_timeout_sec
        last_text = ""
        stable_since: float | None = None
        last_snapshot: PerplexitySnapshot | None = None
        while time.monotonic() < deadline:
            snapshot = snapshot_from_payload(
                _dict_or_reason(session.evaluate(_snapshot_script(), timeout_sec=5.0))
            )
            last_snapshot = snapshot
            if snapshot.needs_human_reason:
                return snapshot
            has_min_text = len(snapshot.text) >= self.config.min_answer_chars
            if snapshot.text != last_text:
                last_text = snapshot.text
                stable_since = time.monotonic()
            settled = stable_since is not None and time.monotonic() - stable_since >= self.config.settle_sec
            if has_min_text and settled and not snapshot.is_generating:
                return snapshot
            time.sleep(self.config.poll_sec)
        if last_snapshot is None:
            raise CdpTimeoutError("timed out before reading any Perplexity page snapshot")
        raise CdpTimeoutError(
            f"timed out waiting for Perplexity response to settle; chars={len(last_snapshot.text)}"
        )

    def _write_artifact(
        self,
        trace_id: str,
        request: ResearchRequest,
        target: ChromeTarget,
        snapshot: PerplexitySnapshot,
    ) -> Path:
        return self.artifacts.write_json(
            trace_id,
            {
                "provider": "perplexity",
                "trace_id": trace_id,
                "request": request,
                "target": target,
                "snapshot": snapshot,
            },
        )


def _dict_or_reason(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {"ok": False, "reason": "unexpected JavaScript result"}


def _submit_script(prompt: str) -> str:
    prompt_json = json.dumps(prompt)
    input_selector_json = json.dumps(ASK_INPUT_SELECTOR)
    return f"""
    (async () => {{
      const prompt = {prompt_json};
      const inputSelector = {input_selector_json};
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const findSubmit = () => [...document.querySelectorAll('button')].find((button) => {{
        const label = [
          button.getAttribute("aria-label") || "",
          button.textContent || "",
          button.title || ""
        ].join(" ").toLowerCase();
        const looksSubmit = label.includes("submit") || label.includes("send") ||
          label.includes("送信") || label.includes("search") || label.includes("ask");
        const looksStop = label.includes("stop") || label.includes("停止");
        return looksSubmit && !looksStop && !button.disabled && button.offsetParent !== null;
      }});
      const input =
        document.querySelector(inputSelector) ||
        document.querySelector('textarea') ||
        [...document.querySelectorAll('[contenteditable="true"]')]
          .find((el) => el.offsetParent !== null);
      if (!input) {{
        return {{ ok: false, reason: "input not found" }};
      }}

      input.focus();
      if (input.tagName === "TEXTAREA" || input.tagName === "INPUT") {{
        input.value = prompt;
        input.dispatchEvent(new Event("input", {{ bubbles: true }}));
        input.dispatchEvent(new Event("change", {{ bubbles: true }}));
      }} else {{
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(input);
        selection.removeAllRanges();
        selection.addRange(range);
        const inserted = document.execCommand("insertText", false, prompt);
        if (!inserted || (input.innerText || "").trim() !== prompt.trim()) {{
          input.textContent = prompt;
          input.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: "insertText", data: prompt }}));
        }}
        input.dispatchEvent(new Event("change", {{ bubbles: true }}));
        input.dispatchEvent(new KeyboardEvent("keyup", {{ bubbles: true, key: " " }}));
      }}

      let submit = null;
      const deadline = Date.now() + 5000;
      while (Date.now() < deadline) {{
        submit = findSubmit();
        if (submit) break;
        await sleep(100);
      }}
      if (!submit) {{
        return {{
          ok: false,
          reason: "submit button not enabled after prompt insertion",
          inputText: (input.innerText || input.value || "").slice(0, 200)
        }};
      }}
      submit.click();
      return {{ ok: true }};
    }})()
    """


def _composer_ready_script() -> str:
    input_selector_json = json.dumps(ASK_INPUT_SELECTOR)
    return f"""
    (() => {{
      const inputSelector = {input_selector_json};
      const input =
        document.querySelector(inputSelector) ||
        document.querySelector('textarea') ||
        [...document.querySelectorAll('[contenteditable="true"]')]
          .find((el) => el.offsetParent !== null);
      if (!input || input.offsetParent === null) {{
        return {{ ok: false, reason: "input not ready" }};
      }}
      return {{ ok: true }};
    }})()
    """


def _snapshot_script() -> str:
    response_selector_json = json.dumps(RESPONSE_SELECTOR)
    return f"""
    (() => {{
      const responseSelector = {response_selector_json};
      const markdownNodes = [...document.querySelectorAll(responseSelector)]
        .filter((el) => (el.innerText || "").trim().length > 0);
      const fallbackNodes = [...document.querySelectorAll('main article, main [data-testid], main')]
        .filter((el) => (el.innerText || "").trim().length > 0);
      const responseNode = markdownNodes.at(-1) || fallbackNodes.at(-1) || document.body;
      const text = (responseNode?.innerText || "").trim();
      const isGenerating = [...document.querySelectorAll('button')].some((button) => {{
        const label = [
          button.getAttribute("aria-label") || "",
          button.textContent || "",
          button.title || ""
        ].join(" ").toLowerCase();
        return (label.includes("stop") || label.includes("停止")) &&
          !button.disabled && button.offsetParent !== null;
      }});
      const citations = [...responseNode.querySelectorAll('a[href^="http"]')]
        .slice(0, 12)
        .map((anchor) => {{
          let host = "";
          try {{ host = new URL(anchor.href).host; }} catch (_) {{}}
          return {{
            title: (anchor.innerText || anchor.getAttribute("aria-label") || anchor.href || "").trim(),
            url: anchor.href,
            host
          }};
        }});
      return {{
        url: location.href,
        title: document.title || "",
        text,
        html: (responseNode?.outerHTML || "").slice(0, 300000),
        isGenerating,
        citations
      }};
    }})()
    """
