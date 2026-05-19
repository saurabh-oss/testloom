"""Shared test fixtures for TestLoom."""

from __future__ import annotations

from pathlib import Path

import pytest

from testloom.core.config import LLMSettings, Settings
from testloom.core.models import GenerationRequest, TestType
from testloom.gateway.base import LLMGateway, LLMMessage, LLMResponse


class MockGateway(LLMGateway):
    """Mock LLM gateway for testing without real API calls."""

    def __init__(self, response_content: str = "", **kwargs):
        super().__init__(model="mock-model", **kwargs)
        self._response_content = response_content

    @property
    def provider_name(self) -> str:
        return "mock"

    async def _call(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        return LLMResponse(
            content=self._response_content,
            model="mock-model",
            provider="mock",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        )


SAMPLE_LLM_RESPONSE = '''{
  "test_cases": [
    {
      "id": "tc-001",
      "title": "Verify successful user login with valid credentials",
      "description": "Test that a user can log in with correct username and password",
      "preconditions": ["User account exists", "User is on login page"],
      "steps": [
        {"step_number": 1, "action": "Enter valid username", "expected_result": "Username field populated", "test_data": "testuser@example.com"},
        {"step_number": 2, "action": "Enter valid password", "expected_result": "Password field populated", "test_data": "SecurePass123!"},
        {"step_number": 3, "action": "Click Login button", "expected_result": "User redirected to dashboard"}
      ],
      "expected_outcome": "User is authenticated and sees the dashboard",
      "test_type": "functional",
      "priority": "critical",
      "tags": ["login", "authentication"],
      "requirement_ids": ["REQ-001"],
      "confidence_score": 0.95
    },
    {
      "id": "tc-002",
      "title": "Verify login fails with invalid password",
      "description": "Test that login is rejected when wrong password is provided",
      "preconditions": ["User account exists"],
      "steps": [
        {"step_number": 1, "action": "Enter valid username", "expected_result": "Username accepted"},
        {"step_number": 2, "action": "Enter incorrect password", "expected_result": "Password field populated", "test_data": "WrongPass!"},
        {"step_number": 3, "action": "Click Login button", "expected_result": "Error message displayed"}
      ],
      "expected_outcome": "Login is rejected with appropriate error message",
      "test_type": "negative",
      "priority": "high",
      "tags": ["login", "security"],
      "requirement_ids": ["REQ-001"],
      "confidence_score": 0.92
    }
  ]
}'''


@pytest.fixture
def mock_gateway() -> MockGateway:
    return MockGateway(response_content=SAMPLE_LLM_RESPONSE)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        llm=LLMSettings(provider="mock", model="mock-model"),
        prompt_template_dir=Path(__file__).parent.parent / "src" / "testloom" / "prompts" / "templates",
        output_dir=tmp_path / "output",
    )


@pytest.fixture
def sample_request() -> GenerationRequest:
    return GenerationRequest(
        requirement_text="As a user, I want to log in with my email and password so that I can access my account.",
        test_types=[TestType.FUNCTIONAL, TestType.NEGATIVE],
        max_cases=10,
    )
