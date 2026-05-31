from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from tomoko_research_operator.models import ResearchRequest, ResearchResult


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def main() -> None:
    parser = argparse.ArgumentParser(prog="tomoko-research")
    subcommands = parser.add_subparsers(dest="command", required=True)

    search = subcommands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--mode", choices=["quick", "deep"], default="quick")
    search.add_argument("--locale", default="ja-JP")
    search.add_argument("--recency")

    args = parser.parse_args()
    if args.command == "search":
        request = ResearchRequest(
            query=args.query,
            mode=args.mode,
            locale=args.locale,
            recency=args.recency,
        )
        request.validate()
        result = ResearchResult.failed(
            request.normalized_query(),
            "browser automation is not implemented yet",
            status="needs_human",
        )
        print(json.dumps(result, default=_json_default, ensure_ascii=False))


if __name__ == "__main__":
    main()

