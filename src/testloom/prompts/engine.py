"""Prompt template engine — loads, renders, and versions prompt templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, BaseLoader

from testloom.core.exceptions import TemplateError


class PromptEngine:
    """Load and render prompt templates from YAML files.

    Templates are stored as YAML with sections (system, user) and
    Jinja2 template syntax for variable interpolation.
    """

    def __init__(self, template_dir: Path) -> None:
        self.template_dir = template_dir
        self._cache: dict[str, dict[str, Any]] = {}
        self._jinja = Environment(loader=BaseLoader(), keep_trailing_newline=True)

    def _load(self, name: str) -> dict[str, Any]:
        if name in self._cache:
            return self._cache[name]

        path = self.template_dir / f"{name}.yaml"
        if not path.exists():
            raise TemplateError(f"Template not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise TemplateError(f"Template must be a YAML dict: {path}")

        self._cache[name] = data
        return data

    def render(self, name: str, section: str, **variables: Any) -> str:
        """Render a named template section with variables."""
        data = self._load(name)

        if section not in data:
            raise TemplateError(f"Section '{section}' not found in template '{name}'")

        template_str = data[section]
        if not isinstance(template_str, str):
            raise TemplateError(f"Section '{section}' in '{name}' must be a string")

        try:
            template = self._jinja.from_string(template_str)
            return template.render(**variables)
        except Exception as e:
            raise TemplateError(f"Failed to render template '{name}.{section}': {e}") from e

    def list_templates(self) -> list[str]:
        """List available template names."""
        if not self.template_dir.exists():
            return []
        return [p.stem for p in self.template_dir.glob("*.yaml")]
