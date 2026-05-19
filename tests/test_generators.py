"""Tests for generators and formatters."""

import pytest

from testloom.core.models import GenerationRequest, TestType
from testloom.formatters import get_formatter, JSONFormatter, MarkdownFormatter, CSVFormatter
from testloom.generators.requirement_generator import RequirementGenerator
from tests.conftest import MockGateway, SAMPLE_LLM_RESPONSE


class TestRequirementGenerator:
    @pytest.mark.asyncio
    async def test_generate_returns_suite(self, mock_gateway, settings, sample_request):
        gen = RequirementGenerator(mock_gateway, settings)
        suite = await gen.generate(sample_request)
        assert suite.total_cases == 2
        assert suite.test_cases[0].title == "Verify successful user login with valid credentials"
        assert suite.test_cases[1].test_type == TestType.NEGATIVE

    @pytest.mark.asyncio
    async def test_generate_respects_max_cases(self, settings):
        gateway = MockGateway(response_content=SAMPLE_LLM_RESPONSE)
        gen = RequirementGenerator(gateway, settings)
        request = GenerationRequest(requirement_text="test", max_cases=1)
        suite = await gen.generate(request)
        assert suite.total_cases == 1

    @pytest.mark.asyncio
    async def test_generate_includes_metadata(self, mock_gateway, settings, sample_request):
        gen = RequirementGenerator(mock_gateway, settings)
        suite = await gen.generate(sample_request)
        assert "model" in suite.generation_metadata
        assert "tokens" in suite.generation_metadata


class TestFormatters:
    @pytest.mark.asyncio
    async def test_json_formatter(self, mock_gateway, settings, sample_request):
        gen = RequirementGenerator(mock_gateway, settings)
        suite = await gen.generate(sample_request)
        output = JSONFormatter().format(suite)
        assert "tc-001" in output
        assert "test_cases" in output

    @pytest.mark.asyncio
    async def test_markdown_formatter(self, mock_gateway, settings, sample_request):
        gen = RequirementGenerator(mock_gateway, settings)
        suite = await gen.generate(sample_request)
        output = MarkdownFormatter().format(suite)
        assert "## tc-001" in output
        assert "| Step |" in output

    @pytest.mark.asyncio
    async def test_csv_formatter(self, mock_gateway, settings, sample_request):
        gen = RequirementGenerator(mock_gateway, settings)
        suite = await gen.generate(sample_request)
        output = CSVFormatter().format(suite)
        assert "ID,Title" in output
        assert "tc-001" in output

    def test_get_formatter_invalid(self):
        with pytest.raises(ValueError, match="Unknown format"):
            get_formatter("invalid")
