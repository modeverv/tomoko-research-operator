from __future__ import annotations

import argparse
import json

from tomoko_research_operator.artifacts import json_default
from tomoko_research_operator.models import ResearchRequest
from tomoko_research_operator.perplexity import PerplexityProviderConfig, PerplexityResearchProvider


def main() -> None:
    parser = argparse.ArgumentParser(prog="tomoko-research")
    subcommands = parser.add_subparsers(dest="command", required=True)

    search = subcommands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--mode", choices=["quick", "deep"], default="quick")
    search.add_argument("--locale", default="ja-JP")
    search.add_argument("--recency")
    search.add_argument("--debug-port", type=int, default=9000)
    search.add_argument("--timeout-sec", type=float, default=90.0)
    search.add_argument("--artifacts-dir", default="artifacts")

    args = parser.parse_args()
    if args.command == "search":
        request = ResearchRequest(
            query=args.query,
            mode=args.mode,
            locale=args.locale,
            recency=args.recency,
        )
        request.validate()
        provider = PerplexityResearchProvider(
            config=PerplexityProviderConfig(
                debug_port=args.debug_port,
                response_timeout_sec=args.timeout_sec,
                artifacts_dir=args.artifacts_dir,
            )
        )
        result = provider.search(request)
        print(json.dumps(result, default=json_default, ensure_ascii=False))


if __name__ == "__main__":
    main()
