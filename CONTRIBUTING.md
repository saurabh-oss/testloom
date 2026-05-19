# Contributing to TestLoom

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
git clone https://github.com/saurabh-oss/testloom.git
cd testloom
pip install -e ".[all]"
pre-commit install
```

## Code Standards

- **Python 3.11+** with type hints on all public functions
- **Ruff** for linting and formatting (`make lint`, `make format`)
- **Pytest** for testing with >80% coverage target
- **Conventional commits** for PR titles (`feat:`, `fix:`, `docs:`, `refactor:`)

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Write tests for new functionality
3. Ensure `make lint` and `make test` pass
4. Submit a PR with a clear description of the change

## Architecture Decisions

For significant changes, create an Architecture Decision Record (ADR) in `docs/architecture/`. Use the existing ADR-001 as a template.

## Reporting Issues

Use GitHub Issues with the provided templates for bug reports and feature requests.
