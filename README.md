# 🧵 TestLoom

### Weaving comprehensive test cases from the threads of your requirements.

**Open-source, LLM-agnostic framework for AI-powered test case generation.**

[![CI](https://github.com/saurabh-oss/testloom/actions/workflows/ci.yml/badge.svg)](https://github.com/saurabh-oss/testloom/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-purple.svg)](CHANGELOG.md)

---

## What is TestLoom?

Just like a loom weaves raw threads into structured fabric, **TestLoom** takes your raw requirements — user stories, API specs, acceptance criteria — and weaves them into comprehensive, structured test suites using AI. It's designed for QA teams, SDETs, and test architects who want to accelerate test design without vendor lock-in.

**Key principles:**
- **LLM-agnostic** — swap between OpenAI, Anthropic, Ollama (local), Azure, or any provider via one line of config
- **Open source** — Apache 2.0 licensed, no proprietary dependencies
- **RAG-powered** — builds a living knowledge base of your project's test history for progressively better generation
- **Enterprise-ready** — retry logic, audit logging, JUnit CI output, governance guardrails

---

## Quick Start

### Installation

```bash
# Core — basic generation
pip install testloom

# With RAG support (ChromaDB vector store, PDF input)
pip install "testloom[rag]"
```

### Generate from a file

```bash
testloom generate --input requirements.md --format markdown --output tests.md
```

### Generate with specific test types

```bash
testloom generate --text "Users can filter products by category and price range" \
  --types functional,negative,boundary \
  --context "Filters are applied client-side; max 500 products per page" \
  --max-cases 12
```

### Batch-generate across multiple requirements

```bash
# requirements.md: one requirement per blank-line-separated paragraph
testloom batch requirements.md --output-dir output/ --format junit --concurrency 3
```

### Use a free local model (zero API cost)

```bash
ollama pull llama3
testloom generate --input story.md --model ollama/llama3
```

---

## Python SDK

### Basic generation

```python
import asyncio
from testloom import Settings, GenerationRequest, RequirementGenerator, GatewayRegistry

settings = Settings.load("testloom.yaml")
gateway  = GatewayRegistry.create(settings.llm)
gen      = RequirementGenerator(gateway, settings)

suite = asyncio.run(gen.generate(GenerationRequest(
    requirement_text="Users can filter products by category, price range, and rating",
    max_cases=15,
)))

for tc in suite.test_cases:
    print(f"[{tc.priority.value}] [{tc.test_type.value}] {tc.title}")
```

### RAG-augmented generation

```python
from testloom import ContextStore, RAGGenerator, GatewayRegistry, Settings, GenerationRequest

settings = Settings.load("testloom.yaml")
gateway  = GatewayRegistry.create(settings.llm)
store    = ContextStore(persist_dir="./chroma_data")   # persists across runs
gen      = RAGGenerator(gateway, settings, store, n_context=3)

# First run: no context yet, generates normally and indexes the result
# Subsequent runs: injects semantically similar past test cases into the prompt
suite = asyncio.run(gen.generate(GenerationRequest(
    requirement_text="Password reset via email link",
)))
print(f"Generated {suite.total_cases} cases, "
      f"used {suite.generation_metadata['rag_context_chunks']} context chunks")
```

### Batch generation

```python
suites = asyncio.run(gen.generate_batch(requests, concurrency=3))
```

---

## Configuration

Create `testloom.yaml` in your project root:

```yaml
llm:
  provider: openai           # openai | anthropic | ollama | azure | litellm
  model: gpt-4o
  temperature: 0.3
  max_tokens: 4096
  retry_attempts: 3          # retries on rate-limit / timeout / 5xx
  retry_backoff: 1.5         # exponential backoff base (seconds)

generation:
  max_cases_per_request: 20
  include_negative_cases: true
  include_edge_cases: true
  include_test_data: true

log_level: INFO
```

Or use environment variables (takes priority over the YAML file):

```bash
export TESTLOOM_LLM__PROVIDER=anthropic
export TESTLOOM_LLM__MODEL=anthropic/claude-sonnet-4-6
export TESTLOOM_LLM__API_KEY=sk-ant-...
export TESTLOOM_LLM__RETRY_ATTEMPTS=5
```

---

## CLI Reference

```
testloom generate   --input / --text     # Source requirement
                    --format             # json | markdown | csv | junit | xml
                    --output             # Write to file (default: stdout)
                    --max-cases          # Cap on generated cases (default 20)
                    --model              # Override LLM (e.g. ollama/llama3)
                    --types              # Comma-sep types: functional,negative,boundary,...
                    --context            # Extra context injected into the prompt

testloom batch      <requirements_file>  # One requirement per blank-line paragraph
                    --output-dir         # Directory for output files (default: output/)
                    --format             # Same options as generate
                    --max-cases          # Per-requirement cap (default 15)
                    --concurrency        # Parallel LLM calls (default 3)

testloom config                          # Show current settings
testloom providers                       # List available LLM providers
testloom version                         # Show version
```

### Output formats

| Format | Flag | Use case |
|--------|------|---------|
| Markdown | `--format markdown` | Human review, PR comments |
| JSON | `--format json` | API integrations, tooling |
| CSV | `--format csv` | Excel, test management import |
| JUnit XML | `--format junit` | Jenkins, GitHub Actions, CI reports |

---

## Supported LLM Providers

| Provider | Model String | Notes |
|----------|-------------|-------|
| OpenAI | `gpt-4o`, `gpt-4o-mini` | Default provider |
| Anthropic | `anthropic/claude-sonnet-4-6` | Via LiteLLM |
| Ollama | `ollama/llama3`, `ollama/mistral` | Local, zero cost |
| Azure OpenAI | `azure/your-deployment` | Enterprise VNet |
| AWS Bedrock | `bedrock/anthropic.claude-3` | AWS credentials |
| Any OpenAI-compatible | Set `api_base` | Self-hosted / on-prem |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CLI / Python SDK / REST API                │
├──────────────────────────────────────────────────────────────┤
│          Generators                                           │
│   ┌─────────────────────┐  ┌──────────────────────────────┐  │
│   │ RequirementGenerator │  │ RAGGenerator                 │  │
│   │  (Phase 1 ✅)        │  │  (Phase 2 ✅)                │  │
│   └─────────────────────┘  └──────────────────────────────┘  │
│          ↑ Prompt Engine (Jinja2 + YAML templates)            │
├──────────────────────────────────────────────────────────────┤
│   ContextStore (ChromaDB)     LLM Gateway (LiteLLM)          │
│   [living test knowledge]     [100+ providers, retry]         │
│                               ┌────┬──────────┬──────┬──────┐│
│                               │GPT │ Claude   │Llama │Azure ││
│                               └────┴──────────┴──────┴──────┘│
├──────────────────────────────────────────────────────────────┤
│   Output Formatters: JSON | Markdown | CSV | JUnit XML        │
│   Input Processors:  TXT | Markdown | PDF                     │
└──────────────────────────────────────────────────────────────┘
```

See [Architecture Decision Records](docs/architecture/) for design rationale.

---

## Development

```bash
# Clone and setup
git clone https://github.com/saurabh-oss/testloom.git
cd testloom
make dev

# Run tests
make test

# Lint and format
make lint && make format

# Build Docker image (includes ChromaDB + Ollama)
make docker
```

### Using Docker Compose

```bash
cd docker
docker compose up -d

# Pull a local model and generate against it
docker exec ollama ollama pull llama3
testloom generate --text "Login requirement" --model ollama/llama3
```

---

## Project Structure

```
testloom/
├── src/testloom/
│   ├── cli/            # CLI — generate, batch, config, providers
│   ├── core/           # Domain models, config, exceptions
│   ├── gateway/        # LLM Gateway abstraction (LiteLLM, retry)
│   ├── generators/     # RequirementGenerator, RAGGenerator
│   ├── store/          # ContextStore (ChromaDB vector store)
│   ├── inputs/         # Input processors (TXT, MD, PDF)
│   ├── prompts/        # Prompt templates (YAML + Jinja2)
│   ├── formatters/     # JSON, Markdown, CSV, JUnit XML
│   └── utils/          # Logging, JSON extraction
├── tests/              # Pytest suite (async, mock gateway)
├── docs/               # GitHub Pages site + Architecture ADRs
├── docker/             # Dockerfile + Compose (ChromaDB + Ollama)
└── examples/           # Usage examples
```

---

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 0** | Project scaffold, CI/CD, core abstractions | ✅ Complete |
| **Phase 1** | LLM gateway, generation, CLI, JUnit, retry | ✅ Complete |
| **Phase 2** | RAG pipeline, ContextStore, input processors | ✅ Complete |
| **Phase 3** | Multi-agent review mesh, quality scoring, governance | 🔄 In Progress |
| **Phase 4** | CI/CD plugins, REST API, Web UI | 📋 Planned |
| **Phase 5** | Enterprise scale, observability, plugins | 📋 Future |

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
