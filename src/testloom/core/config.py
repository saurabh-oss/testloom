"""Configuration management — YAML files, environment variables, and CLI overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    provider: str = Field(default="openai", description="LLM provider: openai, anthropic, ollama, etc.")
    model: str = Field(default="gpt-4o", description="Model identifier")
    api_key: str | None = Field(default=None, description="API key (prefer env var)")
    api_base: str | None = Field(default=None, description="Custom API base URL")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100)
    timeout: int = Field(default=120, description="Request timeout in seconds")


class GenerationSettings(BaseSettings):
    """Defaults for test case generation."""

    max_cases_per_request: int = Field(default=20, ge=1, le=100)
    include_negative_cases: bool = True
    include_edge_cases: bool = True
    include_boundary_cases: bool = True
    include_test_data: bool = True
    default_language: str = "en"


class Settings(BaseSettings):
    """Root configuration for TestLoom."""

    model_config = SettingsConfigDict(
        env_prefix="TESTLOOM_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    project_name: str = "testloom"
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_format: str = Field(default="console", pattern="^(console|json)$")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)

    prompt_template_dir: Path = Field(
        default=Path(__file__).parent.parent / "prompts" / "templates",
    )
    output_dir: Path = Field(default=Path.cwd() / "output")

    @classmethod
    def from_yaml(cls, path: str | Path) -> Settings:
        """Load settings from a YAML config file, with env var overrides."""
        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        return cls(**data)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> Settings:
        """Load settings with priority: env vars > config file > defaults."""
        if config_path:
            return cls.from_yaml(config_path)

        # Auto-discover config files
        for candidate in [
            Path.cwd() / "testloom.yaml",
            Path.cwd() / "testloom.yml",
            Path.cwd() / ".testloom.yaml",
        ]:
            if candidate.exists():
                return cls.from_yaml(candidate)

        return cls()
