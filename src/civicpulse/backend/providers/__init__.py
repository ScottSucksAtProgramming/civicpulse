import os

from civicpulse.backend.providers.anthropic import AnthropicProvider
from civicpulse.backend.providers.base import LLMError, LLMProvider
from civicpulse.backend.providers.openai_compat import OpenAICompatibleProvider


def get_provider() -> LLMProvider:
    provider = os.getenv("CIVICPULSE_PROVIDER", "openai-compatible")
    if provider == "openai-compatible":
        api_key = os.getenv("CIVICPULSE_API_KEY")
        if not api_key:
            raise ValueError(
                "CIVICPULSE_API_KEY is required for "
                "CIVICPULSE_PROVIDER=openai-compatible"
            )
        return OpenAICompatibleProvider(
            base_url=os.getenv("CIVICPULSE_BASE_URL", "https://api.openai.com/v1"),
            api_key=api_key,
        )
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for CIVICPULSE_PROVIDER=anthropic")
        return AnthropicProvider(api_key=api_key)

    raise ValueError(
        "CIVICPULSE_PROVIDER must be one of: openai-compatible, anthropic"
    )


__all__ = [
    "get_provider",
    "AnthropicProvider",
    "LLMError",
    "LLMProvider",
    "OpenAICompatibleProvider",
]
