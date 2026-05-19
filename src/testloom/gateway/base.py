"""LLM Gateway — Abstract interface for all model providers.

This is the foundational abstraction that makes TestLoom LLM-agnostic.
All LLM interactions go through this gateway, allowing providers to be
swapped via configuration without any code changes.

Architecture Decision Record: docs/architecture/adr-001-llm-gateway.md
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class LLMMessage:
    """A single message in a conversation."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMGateway(ABC):
    """Abstract base for all LLM providers.

    Every provider (OpenAI, Anthropic, Ollama, etc.) implements this
    interface. The GatewayRegistry resolves the correct implementation
    based on configuration.

    Usage:
        gateway = GatewayRegistry.create(settings.llm)
        response = await gateway.complete(messages)
    """

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self._config = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'openai', 'anthropic')."""

    @abstractmethod
    async def _call(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        """Execute the actual LLM call. Implemented by each provider."""

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send messages to the LLM and return a structured response.

        This method handles logging, timing, and error handling around
        the provider-specific _call implementation.
        """
        start = time.perf_counter()
        merged_kwargs = {**self._config}
        if temperature is not None:
            merged_kwargs["temperature"] = temperature
        if max_tokens is not None:
            merged_kwargs["max_tokens"] = max_tokens
        merged_kwargs.update(kwargs)

        logger.info(
            "llm_call_start",
            provider=self.provider_name,
            model=self.model,
            message_count=len(messages),
        )

        try:
            response = await self._call(messages, **merged_kwargs)
            response.latency_ms = (time.perf_counter() - start) * 1000

            logger.info(
                "llm_call_complete",
                provider=self.provider_name,
                model=self.model,
                latency_ms=round(response.latency_ms, 1),
                tokens=response.usage,
            )
            return response

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.error(
                "llm_call_failed",
                provider=self.provider_name,
                model=self.model,
                error=str(e),
                latency_ms=round(latency, 1),
            )
            raise

    def build_messages(self, system_prompt: str, user_prompt: str) -> list[LLMMessage]:
        """Helper to construct a standard system + user message list."""
        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
