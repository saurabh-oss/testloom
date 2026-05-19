# 🧵 TestLoom

### Weaving comprehensive test cases from the threads of your requirements.

**Open-source, LLM-agnostic framework for AI-powered test case generation.**

[![CI](https://github.com/saurabh-oss/testloom/actions/workflows/ci.yml/badge.svg)](https://github.com/saurabh-oss/testloom/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)

---

## What is TestLoom?

Just like a loom weaves raw threads into structured fabric, **TestLoom** takes your raw requirements — user stories, API specs, acceptance criteria — and weaves them into comprehensive, structured test suites using AI. It's designed for QA teams, SDETs, and test architects who want to accelerate test design without vendor lock-in.

**Key principles:**
- **LLM-agnostic** — swap between OpenAI, Anthropic, Ollama (local), Azure, or any provider via configuration
- **Open source** — Apache 2.0 licensed, no proprietary dependencies
- **Extensible** — plugin architecture for custom generators, formatters, and integrations
- **Enterprise-ready** — governance guardrails, audit logging, and human-in-the-loop review

## Quick Start

### Installation

```bash
pip install testloom
```

### Generate test cases

```bash
# From a requirements file
testloom generate --input requirements.md --format markdown --output tests.md

# From inline text
testloom generate --text "As a user, I want to reset my password via email" --format json

# Using a local model (zero cost)
testloom generate --input story.md --model ollama/llama3
```

### Python SDK

```python
import asyncio
from testloom import Settings, GenerationRequest, RequirementGenerator
from testloom.gateway.registry import GatewayRegistry

settings = Settings.load("testloom.yaml")
gateway = GatewayRegistry.create(settings.llm)
generator = RequirementGenerator(gateway, settings)

request = GenerationRequest(
    requirement_text="Users can filter products by category, price range, and rating",
    max_cases=15,
)

suite = asyncio.run(generator.generate(request))

for tc in suite.test_cases:
    print(f"[{tc.test_type.value}] {tc.title}")
```

## Configuration

Create `testloom.yaml` in your project root:

```yaml
llm:
  provider: openai           # openai, anthropic, ollama, azure, litellm
  model: gpt-4o              # any model supported by the provider
  temperature: 0.3
  max_tokens: 4096

generation:
  max_cases_per_request: 20
  include_negative_cases: true
  include_edge_cases: true
  include_test_data: true

log_level: INFO
```

Or use environment variables:

```bash
export TESTLOOM_LLM__PROVIDER=anthropic
export TESTLOOM_LLM__MODEL=claude-sonnet-4-20250514
export TESTLOOM_LLM__API_KEY=sk-...
```

## Supported LLM Providers

| Provider | Model String | Notes |
|----------|-------------|-------|
| OpenAI | `gpt-4o`, `gpt-4o-mini` | Default provider |
| Anthropic | `anthropic/claude-sonnet-4-20250514` | Via LiteLLM |
| Ollama | `ollama/llama3`, `ollama/mistral` | Local, zero cost |
| Azure OpenAI | `azure/your-deployment` | Enterprise |
| AWS Bedrock | `bedrock/anthropic.claude-3` | Enterprise |
| Any OpenAI-compatible | Custom `api_base` URL | Self-hosted |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI / SDK / API                    │
├─────────────────────────────────────────────────────┤
│              Generator (RequirementGenerator)         │
│    ┌──────────────────────────────────────────┐      │
│    │         Prompt Engine (Jinja2+YAML)       │      │
│    └──────────────────────────────────────────┘      │
├─────────────────────────────────────────────────────┤
│        LLM Gateway (Provider Abstraction)            │
│    ┌─────────┬─────────┬────────┬─────────┐         │
│    │ OpenAI  │Anthropic│ Ollama │ Custom  │         │
│    └─────────┴─────────┴────────┴─────────┘         │
├─────────────────────────────────────────────────────┤
│          Output Formatters (JSON/MD/CSV/XML)         │
└─────────────────────────────────────────────────────┘
```

See [Architecture Decision Records](docs/architecture/) for design rationale.

## Development

```bash
# Clone and setup
git clone https://github.com/saurabh-oss/testloom.git
cd testloom
make dev

# Run tests
make test

# Lint and format
make lint
make format

# Build Docker image
make docker
```

### Using Docker Compose (includes Ollama + ChromaDB)

```bash
cd docker
docker compose up -d

# Use local Ollama model
docker exec ollama ollama pull llama3
testloom generate --text "Login requirement" --model ollama/llama3
```

## Project Structure

```
testloom/
├── src/testloom/
│   ├── cli/            # CLI entry points (Click)
│   ├── core/           # Models, config, exceptions
│   ├── gateway/        # LLM provider abstraction
│   ├── generators/     # Test case generators
│   ├── prompts/        # Prompt templates (YAML + Jinja2)
│   ├── formatters/     # Output formatters
│   └── utils/          # Logging, helpers
├── tests/              # Pytest test suite
├── docs/               # Architecture docs, ADRs
├── docker/             # Container configuration
└── examples/           # Usage examples
```

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 0** | Project scaffold, CI/CD, core abstractions | ✅ Complete |
| **Phase 1** | LLM gateway, basic generation, CLI | 🔄 In Progress |
| **Phase 2** | RAG pipeline, LangGraph agents, multi-format input | 📋 Planned |
| **Phase 3** | Multi-agent review, quality scoring, governance | 📋 Planned |
| **Phase 4** | CI/CD integration, REST API, Web UI | 📋 Planned |
| **Phase 5** | Enterprise scale, observability, plugins | 📋 Future |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
