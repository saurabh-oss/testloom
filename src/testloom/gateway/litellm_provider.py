"""LiteLLM-based provider — single implementation that supports 100+ LLM providers.

LiteLLM acts as a universal adapter, so this one provider covers:
  - OpenAI (GPT-4o, GPT-4, GPT-3.5)
  - Anthropic (Claude 3.5, Claude 3)
  - Ollama (Llama 3, Mistral, CodeLlama — local)
  - Azure OpenAI
  - Google Vertex AI (Gemini)
  - AWS Bedrock
  - Hugging Face Inference
  - Any OpenAI-compatible endpoint

Configuration is model-string based:
  - "gpt-4o"                → OpenAI
  - "anthropic/claude-sonnet-4-20250514" → Anthropic
  - "ollama/llama3"         → Local Ollama
  - "azure/my-deployment"   → Azure OpenAI
"""

from __future__ import annotations

from typing import Any

from testloom.gateway.base import LLMGateway, LLMMessage, LLMResponse


class LiteLLMProvider(LLMGateway):
    """Universal LLM provider powered by LiteLLM."""

    @property
    def provider_name(self) -> str:
        return "litellm"

    async def _call(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        import litellm

        # Convert our message format to LiteLLM's
        llm_messages = [{"role": m.role, "content": m.content} for m in messages]

        response = await litellm.acompletion(
            model=self.model,
            messages=llm_messages,
            temperature=kwargs.get("temperature", 0.3),
            max_tokens=kwargs.get("max_tokens", 4096),
            api_key=kwargs.get("api_key"),
            api_base=kwargs.get("api_base"),
            timeout=kwargs.get("timeout", 120),
        )

        # Extract usage info
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider_name,
            usage=usage,
            metadata={"finish_reason": response.choices[0].finish_reason},
        )
