from __future__ import annotations

import json
import time
from typing import Any

from tomoko_research_operator.cdp import CdpSession, CdpTimeoutError
from tomoko_research_operator.perplexity import (
    PerplexityResearchProvider,
    PerplexitySnapshot,
    _dict_or_reason,
    snapshot_from_payload,
)

CHATGPT_URL = "https://chatgpt.com/"


class ChatGPTResearchProvider(PerplexityResearchProvider):
    """Research provider that drives a logged-in ChatGPT tab through local CDP."""

    provider_name = "chatgpt"
    provider_url = CHATGPT_URL

    def _submit_prompt(self, session: CdpSession, prompt: str) -> dict[str, Any]:
        return _dict_or_reason(session.evaluate(_submit_script(prompt), timeout_sec=self.config.connect_timeout_sec))

    def _wait_for_composer(self, session: CdpSession) -> None:
        deadline = time.monotonic() + self.config.navigation_timeout_sec
        last_reason = "composer not checked"
        while time.monotonic() < deadline:
            result = _dict_or_reason(session.evaluate(_composer_ready_script(), timeout_sec=5.0))
            if result.get("ok"):
                return
            last_reason = str(result.get("reason") or "composer not ready")
            time.sleep(self.config.poll_sec)
        raise CdpTimeoutError(f"ChatGPT composer was not ready: {last_reason}")

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
            if snapshot.text != last_text:
                last_text = snapshot.text
                stable_since = time.monotonic()
            settled = stable_since is not None and time.monotonic() - stable_since >= self.config.settle_sec
            if len(snapshot.text) >= self.config.min_answer_chars and settled and not snapshot.is_generating:
                return snapshot
            time.sleep(self.config.poll_sec)
        if last_snapshot is None:
            raise CdpTimeoutError("timed out before reading any ChatGPT page snapshot")
        raise CdpTimeoutError(
            f"timed out waiting for ChatGPT response to settle; chars={len(last_snapshot.text)}"
        )


def _submit_script(prompt: str) -> str:
    prompt_json = json.dumps(prompt)
    return f"""
    (async () => {{
      const prompt = {prompt_json};
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const visible = (element) => element && element.offsetParent !== null;
      const findInput = () =>
        document.querySelector('#prompt-textarea [contenteditable="true"]') ||
        document.querySelector('#prompt-textarea textarea') ||
        [...document.querySelectorAll('[contenteditable="true"], textarea')].find(visible);
      const findSubmit = () => [...document.querySelectorAll('button')].find((button) => {{
        const label = [button.getAttribute('aria-label') || '', button.textContent || '', button.title || '']
          .join(' ').toLowerCase();
        const canSend = ['send', 'submit', '送信'].some((word) => label.includes(word));
        const isStop = ['stop', '停止'].some((word) => label.includes(word));
        return canSend && !isStop && !button.disabled && visible(button);
      }});
      const input = findInput();
      if (!input) return {{ ok: false, reason: 'input not found' }};
      input.focus();
      if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {{
        input.value = prompt;
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
      }} else {{
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(input);
        selection.removeAllRanges();
        selection.addRange(range);
        document.execCommand('insertText', false, prompt);
        input.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: prompt }}));
      }}
      for (let attempt = 0; attempt < 50; attempt += 1) {{
        const submit = findSubmit();
        if (submit) {{ submit.click(); return {{ ok: true }}; }}
        await sleep(100);
      }}
      return {{ ok: false, reason: 'submit button not enabled after prompt insertion' }};
    }})()
    """


def _composer_ready_script() -> str:
    return """
    (() => {
      const input = document.querySelector('#prompt-textarea [contenteditable="true"]') ||
        document.querySelector('#prompt-textarea textarea') ||
        [...document.querySelectorAll('[contenteditable="true"], textarea')]
          .find((element) => element.offsetParent !== null);
      return input && input.offsetParent !== null
        ? { ok: true }
        : { ok: false, reason: 'input not ready' };
    })()
    """


def _snapshot_script() -> str:
    return """
    (() => {
      const visible = (element) => element && element.offsetParent !== null;
      const assistants = [...document.querySelectorAll('[data-message-author-role="assistant"]')]
        .filter((element) => visible(element) && (element.innerText || '').trim());
      const markdown = [...document.querySelectorAll('main .markdown, main [class*="markdown"]')]
        .filter((element) => visible(element) && (element.innerText || '').trim());
      const responseNode = assistants.at(-1) || markdown.at(-1) || document.querySelector('main');
      const text = (responseNode?.innerText || '').trim();
      const isGenerating = [...document.querySelectorAll('button')].some((button) => {
        const label = [button.getAttribute('aria-label') || '', button.textContent || '', button.title || '']
          .join(' ').toLowerCase();
        return visible(button) && !button.disabled && (label.includes('stop') || label.includes('停止'));
      });
      const citations = [...(responseNode?.querySelectorAll('a[href^="http"]') || [])]
        .slice(0, 12)
        .map((anchor) => {
          let host = '';
          try { host = new URL(anchor.href).host; } catch (_) {}
          return { title: (anchor.innerText || anchor.getAttribute('aria-label') || anchor.href).trim(), url: anchor.href, host };
        });
      for (const match of text.matchAll(/https?:\\/\\/[^\\s<]+/g)) {
        const url = match[0].replace(/[),.。]+$/, '');
        if (citations.some((citation) => citation.url === url)) continue;
        let host = '';
        try { host = new URL(url).host; } catch (_) {}
        citations.push({ title: url, url, host });
      }
      return { url: location.href, title: document.title || '', text,
        html: (responseNode?.outerHTML || '').slice(0, 300000), isGenerating, citations };
    })()
    """
