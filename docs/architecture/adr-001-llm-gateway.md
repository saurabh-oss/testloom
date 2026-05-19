# ADR-001: LLM Gateway Pattern

## Status
Accepted

## Context
TestLoom must support multiple LLM providers without coupling business logic to any specific vendor. Customers may use OpenAI, Anthropic, local Ollama models, or enterprise-specific endpoints.

## Decision
Implement an **LLM Gateway** pattern with:
1. An abstract `LLMGateway` base class defining the interface (`complete`, `build_messages`)
2. A `GatewayRegistry` factory that resolves the correct provider from configuration
3. **LiteLLM** as the default universal provider (supports 100+ backends via model-string conventions)
4. Support for custom provider registration for specialized needs

## Consequences
- **Positive**: Zero code changes to swap providers; configuration-only switching
- **Positive**: LiteLLM handles most providers out of the box
- **Positive**: Custom providers can be registered for on-prem or proprietary endpoints
- **Trade-off**: LiteLLM adds a dependency, but it's well-maintained and widely adopted
- **Trade-off**: Provider-specific features (streaming, function calling) need explicit abstraction

## Alternatives Considered
1. **Direct SDK calls per provider** — rejected; creates tight coupling and duplication
2. **Custom adapter per provider** — rejected for Phase 1; LiteLLM covers this more efficiently
3. **LangChain's LLM abstraction** — reserved for Phase 2 agent orchestration layer
