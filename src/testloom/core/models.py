"""Domain models for test case generation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Test case priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TestType(str, Enum):
    """Types of test cases the framework can generate."""

    FUNCTIONAL = "functional"
    NEGATIVE = "negative"
    EDGE_CASE = "edge_case"
    BOUNDARY = "boundary"
    INTEGRATION = "integration"
    API = "api"
    REGRESSION = "regression"
    SMOKE = "smoke"


class TestStep(BaseModel):
    """A single step within a test case."""

    step_number: int
    action: str
    expected_result: str
    test_data: str | None = None


class TestCase(BaseModel):
    """A generated test case with full metadata."""

    id: str = Field(description="Unique identifier for the test case")
    title: str = Field(description="Concise test case title")
    description: str = Field(description="Detailed description of what is being tested")
    preconditions: list[str] = Field(default_factory=list)
    steps: list[TestStep] = Field(default_factory=list)
    expected_outcome: str = Field(description="Overall expected outcome")
    test_type: TestType = TestType.FUNCTIONAL
    priority: Priority = Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(
        default_factory=list,
        description="Traceability: IDs of source requirements",
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str | None = Field(default=None, description="LLM model that generated this")
    confidence_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="AI confidence in this test case"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestSuite(BaseModel):
    """A collection of related test cases."""

    id: str
    name: str
    description: str = ""
    test_cases: list[TestCase] = Field(default_factory=list)
    source_requirement: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generation_metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_cases(self) -> int:
        return len(self.test_cases)

    @property
    def by_type(self) -> dict[TestType, list[TestCase]]:
        result: dict[TestType, list[TestCase]] = {}
        for tc in self.test_cases:
            result.setdefault(tc.test_type, []).append(tc)
        return result


class GenerationRequest(BaseModel):
    """Input request for test case generation."""

    requirement_text: str = Field(description="The requirement or user story text")
    context: str | None = Field(default=None, description="Additional context")
    test_types: list[TestType] = Field(
        default_factory=lambda: [TestType.FUNCTIONAL, TestType.NEGATIVE, TestType.EDGE_CASE],
    )
    max_cases: int = Field(default=20, ge=1, le=100)
    priority_filter: Priority | None = None
    tags: list[str] = Field(default_factory=list)
    output_format: str = Field(default="json", pattern="^(json|markdown|csv|junit)$")
    include_test_data: bool = True
    language: str = Field(default="en", description="Language for generated test cases")
