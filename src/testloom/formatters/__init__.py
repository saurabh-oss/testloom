"""Output formatters — convert TestSuite to various formats."""

from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from xml.dom import minidom

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


class JUnitFormatter(BaseFormatter):
    """Format test suite as JUnit XML — compatible with Jenkins, GitHub Actions, and most CI systems."""

    @property
    def extension(self) -> str:
        return "xml"

    def format(self, suite: TestSuite) -> str:
        testsuites = ET.Element("testsuites")
        ts = ET.SubElement(testsuites, "testsuite")
        ts.set("name", suite.name)
        ts.set("tests", str(suite.total_cases))
        ts.set("failures", "0")
        ts.set("errors", "0")
        ts.set("skipped", "0")
        ts.set("time", "0.0")
        ts.set("timestamp", suite.generated_at.isoformat())

        model = suite.generation_metadata.get("model", "unknown")
        props = ET.SubElement(ts, "properties")
        for key, value in [
            ("model", model),
            ("provider", suite.generation_metadata.get("provider", "unknown")),
            ("source_requirement", (suite.source_requirement or "")[:200]),
            ("total_cases", str(suite.total_cases)),
        ]:
            prop = ET.SubElement(props, "property")
            prop.set("name", key)
            prop.set("value", str(value))

        for tc in suite.test_cases:
            tc_elem = ET.SubElement(ts, "testcase")
            tc_elem.set("name", f"{tc.id}: {tc.title}")
            tc_elem.set("classname", tc.test_type.value)
            tc_elem.set("time", "0.0")

            # Steps and metadata as system-out
            lines = [
                f"Description: {tc.description}",
                f"Priority: {tc.priority.value}",
                f"Tags: {', '.join(tc.tags)}",
                "",
                "Preconditions:",
                *[f"  - {p}" for p in tc.preconditions],
                "",
                "Steps:",
            ]
            for step in tc.steps:
                data = f" [data: {step.test_data}]" if step.test_data else ""
                lines.append(f"  {step.step_number}. {step.action}{data}")
                lines.append(f"     → {step.expected_result}")
            lines += ["", f"Expected outcome: {tc.expected_outcome}"]
            if tc.requirement_ids:
                lines.append(f"Traces to: {', '.join(tc.requirement_ids)}")
            if tc.confidence_score is not None:
                lines.append(f"Confidence: {tc.confidence_score:.2f}")

            sysout = ET.SubElement(tc_elem, "system-out")
            sysout.text = "\n".join(lines)

        # Pretty-print with minidom
        raw = ET.tostring(testsuites, encoding="unicode")
        return minidom.parseString(raw).toprettyxml(indent="  ", encoding=None)  # type: ignore[return-value]


FORMATTERS: dict[str, type[BaseFormatter]] = {
    "json": JSONFormatter,
    "markdown": MarkdownFormatter,
    "md": MarkdownFormatter,
    "csv": CSVFormatter,
    "junit": JUnitFormatter,
    "xml": JUnitFormatter,
}


def get_formatter(name: str) -> BaseFormatter:
    """Get a formatter by name."""
    cls = FORMATTERS.get(name.lower())
    if cls is None:
        available = ", ".join(FORMATTERS.keys())
        raise ValueError(f"Unknown format '{name}'. Available: {available}")
    return cls()
