"""LLM Gateway — Abstract interface for all model providers.

This is the foundational abstraction that makes TestLoom LLM-agnostic.
All LLM interactions go through this gateway, allowing providers to be
swapped via configuration without any code changes.

Architecture Decision Record: docs/architecture/adr-001-llm-gateway.md
"""

from __future__ import annotations

import asyncio
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

    # Transient HTTP status codes that warrant a retry
    _RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self._retry_attempts: int = int(kwargs.pop("retry_attempts", 3))
        self._retry_backoff: float = float(kwargs.pop("retry_backoff", 1.5))
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

        last_exc: Exception | None = None
        for attempt in range(self._retry_attempts):
            try:
                response = await self._call(messages, **merged_kwargs)
                response.latency_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "llm_call_complete",
                    provider=self.provider_name,
                    model=self.model,
                    latency_ms=round(response.latency_ms, 1),
                    tokens=response.usage,
                    attempt=attempt + 1,
                )
                return response

            except Exception as e:
                last_exc = e
                if not self._is_retryable(e) or attempt == self._retry_attempts - 1:
                    break
                wait = self._retry_backoff ** attempt
                logger.warning(
                    "llm_call_retry",
                    provider=self.provider_name,
                    model=self.model,
                    attempt=attempt + 1,
                    max_attempts=self._retry_attempts,
                    wait_s=round(wait, 2),
                    error=str(e),
                )
                await asyncio.sleep(wait)

        latency = (time.perf_counter() - start) * 1000
        logger.error(
            "llm_call_failed",
            provider=self.provider_name,
            model=self.model,
            error=str(last_exc),
            latency_ms=round(latency, 1),
            attempts=attempt + 1,
        )
        raise last_exc  # type: ignore[misc]

    def _is_retryable(self, exc: Exception) -> bool:
        """Return True if the exception represents a transient failure worth retrying."""
        msg = str(exc).lower()
        # Rate limits, server errors, timeouts are transient
        if any(kw in msg for kw in ("rate limit", "timeout", "connection", "503", "502", "500", "429")):
            return True
        # Check for status code attribute (some HTTP client exceptions expose it)
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        if status and int(status) in self._RETRYABLE_STATUS_CODES:
            return True
        return False

    def build_messages(self, system_prompt: str, user_prompt: str) -> list[LLMMessage]:
        """Helper to construct a standard system + user message list."""
        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
