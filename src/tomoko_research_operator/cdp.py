from __future__ import annotations

import json
from json import JSONDecodeError
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from itertools import count
from typing import Any


@dataclass(frozen=True, slots=True)
class ChromeTarget:
    id: str
    url: str
    title: str
    websocket_debugger_url: str


class CdpError(RuntimeError):
    pass


class CdpTimeoutError(CdpError):
    pass


class ChromeBrowserClient:
    def __init__(self, debug_port: int = 9000, host: str = "127.0.0.1") -> None:
        if host not in {"127.0.0.1", "localhost"}:
            raise ValueError("Chrome CDP host must be local")
        self.debug_port = debug_port
        self.host = host

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.debug_port}"

    def request_json(
        self,
        path: str,
        *,
        timeout_sec: float = 5.0,
        method: str = "GET",
    ) -> Any:
        request = urllib.request.Request(f"{self.base_url}{path}", method=method)
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        if not body:
            return None
        try:
            return json.loads(body)
        except JSONDecodeError:
            return body

    def version(self) -> dict[str, Any]:
        payload = self.request_json("/json/version")
        if not isinstance(payload, dict):
            raise CdpError("unexpected /json/version response")
        return payload

    def list_targets(self) -> list[ChromeTarget]:
        return _targets_from_payload(self.request_json("/json/list"))

    def open_target(self, url: str) -> ChromeTarget:
        encoded = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")
        payload = self.request_json(f"/json/new?{encoded}", method="PUT")
        targets = _targets_from_payload([payload])
        if not targets:
            raise CdpError("Chrome did not return a page target for /json/new")
        return targets[0]

    def activate_target(self, target_id: str) -> None:
        self.request_json(f"/json/activate/{urllib.parse.quote(target_id)}")

    def ensure_target(self, url_prefix: str, create_url: str) -> ChromeTarget:
        targets = self.list_targets()
        target = choose_target(targets, url_prefix)
        if target is None:
            target = self.open_target(create_url)
        self.activate_target(target.id)
        return target


def _targets_from_payload(payload: Any) -> list[ChromeTarget]:
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise CdpError("unexpected /json/list response")
    targets: list[ChromeTarget] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "page":
            continue
        ws_url = item.get("webSocketDebuggerUrl")
        if not ws_url:
            continue
        targets.append(
            ChromeTarget(
                id=str(item.get("id") or ""),
                url=str(item.get("url") or ""),
                title=str(item.get("title") or ""),
                websocket_debugger_url=str(ws_url),
            )
        )
    return targets


def list_targets(debug_port: int = 9000) -> list[ChromeTarget]:
    return ChromeBrowserClient(debug_port=debug_port).list_targets()


def choose_target(targets: list[ChromeTarget], url_prefix: str) -> ChromeTarget | None:
    for target in reversed(targets):
        if target.url.startswith(url_prefix):
            return target
    return None


class CdpSession:
    def __init__(self, websocket_url: str, timeout_sec: float = 10.0) -> None:
        self._websocket_url = websocket_url
        self._timeout_sec = timeout_sec
        self._ids = count(1)
        self._ws: Any | None = None

    def __enter__(self) -> CdpSession:
        import websocket

        self._ws = websocket.create_connection(self._websocket_url, timeout=self._timeout_sec)
        self.call("Page.enable")
        self.call("Runtime.enable")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("CDP session is not connected")
        request_id = next(self._ids)
        payload: dict[str, Any] = {"id": request_id, "method": method}
        if params:
            payload["params"] = params
        self._ws.send(json.dumps(payload))
        while True:
            response = json.loads(self._ws.recv())
            if response.get("id") == request_id:
                if "error" in response:
                    error = response["error"]
                    message = error.get("message") if isinstance(error, dict) else str(error)
                    raise CdpError(f"{method} failed: {message}")
                return response

    def evaluate(self, expression: str, *, timeout_sec: float | None = None) -> Any:
        params: dict[str, Any] = {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        }
        if timeout_sec is not None:
            params["timeout"] = int(timeout_sec * 1000)
        response = self.call("Runtime.evaluate", params)
        result = response.get("result", {}).get("result", {})
        if result.get("subtype") == "error":
            raise CdpError(f"Runtime.evaluate returned an error: {result.get('description')}")
        return result.get("value")

    def navigate(self, url: str, *, timeout_sec: float = 20.0) -> None:
        self.call("Page.navigate", {"url": url})
        self.wait_for_ready_state(timeout_sec=timeout_sec)

    def wait_for_ready_state(self, *, timeout_sec: float = 20.0) -> str:
        deadline = time.monotonic() + timeout_sec
        last_state = ""
        while time.monotonic() < deadline:
            state = self.evaluate("document.readyState")
            last_state = str(state or "")
            if last_state in {"interactive", "complete"}:
                return last_state
            time.sleep(0.2)
        raise CdpTimeoutError(f"document.readyState stayed {last_state!r}")

    def page_info(self) -> dict[str, str]:
        value = self.evaluate(
            """
            (() => ({
              title: document.title || "",
              url: location.href || "",
              readyState: document.readyState || ""
            }))()
            """
        )
        if isinstance(value, dict):
            return {str(key): str(val) for key, val in value.items()}
        return {"title": "", "url": "", "readyState": ""}
