from __future__ import annotations

from tomoko_research_operator.chatgpt import ChatGPTResearchProvider
from tomoko_research_operator.perplexity import PerplexityProviderConfig, PerplexityResearchProvider

DEFAULT_PROVIDER = "chatgpt"
SUPPORTED_PROVIDERS = ("chatgpt", "perplexity")


def create_research_provider(
    provider_name: str = DEFAULT_PROVIDER,
    *,
    config: PerplexityProviderConfig | None = None,
) -> PerplexityResearchProvider:
    normalized = provider_name.strip().lower()
    if normalized == "chatgpt":
        return ChatGPTResearchProvider(config=config)
    if normalized == "perplexity":
        return PerplexityResearchProvider(config=config)
    supported = ", ".join(SUPPORTED_PROVIDERS)
    raise ValueError(f"unsupported research provider: {provider_name!r}; choose one of {supported}")
