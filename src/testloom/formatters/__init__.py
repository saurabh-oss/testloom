"""Output formatters — convert TestSuite to various formats."""

from __future__ import annotations

import csv
import io
import json
from abc import ABC, abstractmethod

from testloom.core.models import TestSuite


class BaseFormatter(ABC):
    """Abstract output formatter."""

    @abstractmethod
    def format(self, suite: TestSuite) -> str:
        """Format a test suite to string output."""

    @property
    @abstractmethod
    def extension(self) -> str:
        """File extension for this format."""


class JSONFormatter(BaseFormatter):
    """Format test suite as JSON."""

    @property
    def extension(self) -> str:
        return "json"

    def format(self, suite: TestSuite) -> str:
        return suite.model_dump_json(indent=2)


class MarkdownFormatter(BaseFormatter):
    """Format test suite as readable Markdown."""

    @property
    def extension(self) -> str:
        return "md"

    def format(self, suite: TestSuite) -> str:
        lines = [
            f"# {suite.name}",
            "",
            f"**Generated:** {suite.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  ",
            f"**Total Cases:** {suite.total_cases}  ",
            "",
            "---",
            "",
        ]

        for tc in suite.test_cases:
            lines.append(f"## {tc.id}: {tc.title}")
            lines.append("")
            lines.append(f"**Type:** {tc.test_type.value} | **Priority:** {tc.priority.value}")
            if tc.tags:
                lines.append(f"**Tags:** {', '.join(tc.tags)}")
            lines.append("")
            lines.append(tc.description)
            lines.append("")

            if tc.preconditions:
                lines.append("**Preconditions:**")
                for pre in tc.preconditions:
                    lines.append(f"- {pre}")
                lines.append("")

            if tc.steps:
                lines.append("| Step | Action | Expected Result | Test Data |")
                lines.append("|------|--------|-----------------|-----------|")
                for step in tc.steps:
                    data = step.test_data or "—"
                    lines.append(f"| {step.step_number} | {step.action} | {step.expected_result} | {data} |")
                lines.append("")

            lines.append(f"**Expected Outcome:** {tc.expected_outcome}")
            if tc.requirement_ids:
                lines.append(f"**Traces to:** {', '.join(tc.requirement_ids)}")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


class CSVFormatter(BaseFormatter):
    """Format test suite as CSV."""

    @property
    def extension(self) -> str:
        return "csv"

    def format(self, suite: TestSuite) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Title", "Type", "Priority", "Description",
            "Preconditions", "Expected Outcome", "Tags", "Requirement IDs",
        ])
        for tc in suite.test_cases:
            writer.writerow([
                tc.id,
                tc.title,
                tc.test_type.value,
                tc.priority.value,
                tc.description,
                "; ".join(tc.preconditions),
                tc.expected_outcome,
                "; ".join(tc.tags),
                "; ".join(tc.requirement_ids),
            ])
        return output.getvalue()


FORMATTERS: dict[str, type[BaseFormatter]] = {
    "json": JSONFormatter,
    "markdown": MarkdownFormatter,
    "md": MarkdownFormatter,
    "csv": CSVFormatter,
}


def get_formatter(name: str) -> BaseFormatter:
    """Get a formatter by name."""
    cls = FORMATTERS.get(name.lower())
    if cls is None:
        available = ", ".join(FORMATTERS.keys())
        raise ValueError(f"Unknown format '{name}'. Available: {available}")
    return cls()
