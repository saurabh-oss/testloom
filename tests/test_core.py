"""Tests for core models and configuration."""

from testloom.core.config import Settings, LLMSettings
from testloom.core.models import (
    GenerationRequest, TestCase, TestSuite, TestStep, TestType, Priority,
)


class TestModels:
    def test_test_case_creation(self):
        tc = TestCase(
            id="tc-001",
            title="Test login",
            description="Verify login works",
            expected_outcome="User logged in",
        )
        assert tc.id == "tc-001"
        assert tc.test_type == TestType.FUNCTIONAL
        assert tc.priority == Priority.MEDIUM

    def test_test_suite_counts(self):
        suite = TestSuite(
            id="s-001",
            name="Login Tests",
            test_cases=[
                TestCase(id="tc-1", title="T1", description="D1", expected_outcome="O1", test_type=TestType.FUNCTIONAL),
                TestCase(id="tc-2", title="T2", description="D2", expected_outcome="O2", test_type=TestType.NEGATIVE),
                TestCase(id="tc-3", title="T3", description="D3", expected_outcome="O3", test_type=TestType.FUNCTIONAL),
            ],
        )
        assert suite.total_cases == 3
        assert len(suite.by_type[TestType.FUNCTIONAL]) == 2
        assert len(suite.by_type[TestType.NEGATIVE]) == 1

    def test_generation_request_defaults(self):
        req = GenerationRequest(requirement_text="Some requirement")
        assert req.max_cases == 20
        assert req.output_format == "json"
        assert TestType.FUNCTIONAL in req.test_types


class TestConfig:
    def test_default_settings(self):
        settings = Settings()
        assert settings.llm.provider == "openai"
        assert settings.llm.temperature == 0.3
        assert settings.log_level == "INFO"

    def test_custom_llm_settings(self):
        llm = LLMSettings(provider="anthropic", model="claude-sonnet-4-20250514", temperature=0.5)
        assert llm.provider == "anthropic"
        assert llm.temperature == 0.5
