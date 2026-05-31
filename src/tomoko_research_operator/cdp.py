from __future__ import annotations

import json
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


def list_targets(debug_port: int = 9000) -> list[ChromeTarget]:
    with urllib.request.urlopen(  # noqa: S310 - local CDP endpoint only
        f"http://127.0.0.1:{debug_port}/json/list",
        timeout=5,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    targets: list[ChromeTarget] = []
    for item in payload:
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
                return response

    def evaluate(self, expression: str) -> Any:
        response = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        result = response.get("result", {}).get("result", {})
        return result.get("value")
