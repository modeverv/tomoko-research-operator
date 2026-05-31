from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class ArtifactStore:
    def __init__(self, root: Path | str = "artifacts") -> None:
        self.root = Path(root)

    def new_trace_id(self, prefix: str = "perplexity") -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"{prefix}-{stamp}"

    def write_json(self, trace_id: str, payload: dict[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{trace_id}.json"
        path.write_text(
            json.dumps(payload, default=json_default, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
