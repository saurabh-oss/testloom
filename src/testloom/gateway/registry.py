"""Provider registry — resolves and creates LLM gateway instances."""

from __future__ import annotations

from typing import Any

from testloom.core.config import LLMSettings
from testloom.core.exceptions import ProviderNotFoundError
from testloom.gateway.base import LLMGateway
from testloom.gateway.litellm_provider import LiteLLMProvider


class GatewayRegistry:
    """Factory that creates the appropriate LLM gateway from configuration.

    LiteLLM is the default provider since it supports 100+ backends via
    model-string conventions. Custom providers can be registered for
    specialized needs (e.g., on-prem endpoints with custom auth).
    """

    _custom_providers: dict[str, type[LLMGateway]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[LLMGateway]) -> None:
        """Register a custom provider class."""
        cls._custom_providers[name] = provider_cls

    @classmethod
    def create(cls, settings: LLMSettings) -> LLMGateway:
        """Create an LLM gateway instance from settings.

        Resolution order:
        1. Custom registered providers (exact match on provider name)
        2. LiteLLM (default — handles openai, anthropic, ollama, azure, etc.)
        """
        provider = settings.provider.lower()

        common_kwargs: dict[str, Any] = dict(
            api_key=settings.api_key,
            api_base=settings.api_base,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            timeout=settings.timeout,
            retry_attempts=settings.retry_attempts,
            retry_backoff=settings.retry_backoff,
        )

        # Check custom providers first
        if provider in cls._custom_providers:
            return cls._custom_providers[provider](model=settings.model, **common_kwargs)

        # Default: use LiteLLM which handles most providers via model string
        model_string = settings.model
        if provider not in ("openai", "litellm") and "/" not in model_string:
            # LiteLLM convention: "provider/model" for non-OpenAI
            model_string = f"{provider}/{settings.model}"

        return LiteLLMProvider(model=model_string, **common_kwargs)

    @classmethod
    def available_providers(cls) -> list[str]:
        """List all known provider names."""
        builtin = ["openai", "anthropic", "ollama", "azure", "litellm"]
        custom = list(cls._custom_providers.keys())
        return sorted(set(builtin + custom))
