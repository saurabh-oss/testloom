"""Requirement-based test case generator.

Takes requirement text (user stories, acceptance criteria, feature descriptions)
and generates structured test cases using the configured LLM.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog

from testloom.core.config import Settings
from testloom.core.exceptions import GenerationError, ParseError
from testloom.core.models import (
    GenerationRequest,
    Priority,
    TestCase,
    TestStep,
    TestSuite,
    TestType,
)
from testloom.gateway.base import LLMGateway
from testloom.generators.base import BaseGenerator
from testloom.prompts.engine import PromptEngine

logger = structlog.get_logger()


class RequirementGenerator(BaseGenerator):
    """Generate test cases from textual requirements.

    This is the primary generator for Phase 1. It takes a requirement
    (user story, feature spec, acceptance criteria) and produces a
    structured TestSuite with functional, negative, and edge-case scenarios.
    """

    def __init__(self, gateway: LLMGateway, settings: Settings) -> None:
        super().__init__(gateway, settings)
        self.prompt_engine = PromptEngine(settings.prompt_template_dir)

    async def generate(self, request: GenerationRequest) -> TestSuite:
        """Generate a test suite from a requirement."""
        logger.info("generation_start", max_cases=request.max_cases, types=request.test_types)

        system_prompt = self.prompt_engine.render(
            "test_generation",
            section="system",
        )
        user_prompt = self.prompt_engine.render(
            "test_generation",
            section="user",
            requirement=request.requirement_text,
            context=request.context or "No additional context provided.",
            test_types=", ".join(t.value for t in request.test_types),
            max_cases=request.max_cases,
            include_test_data=request.include_test_data,
            language=request.language,
        )

        messages = self.gateway.build_messages(system_prompt, user_prompt)
        response = await self.gateway.complete(messages)

        test_cases = self._parse_response(response.content, request, response.model)

        suite = TestSuite(
            id=f"suite-{uuid.uuid4().hex[:8]}",
            name=f"Generated tests for: {request.requirement_text[:80]}",
            description=f"AI-generated test suite from requirement text",
            test_cases=test_cases,
            source_requirement=request.requirement_text,
            generation_metadata={
                "model": response.model,
                "provider": response.provider,
                "tokens": response.usage,
                "latency_ms": response.latency_ms,
                "request_types": [t.value for t in request.test_types],
            },
        )

        logger.info(
            "generation_complete",
            total_cases=suite.total_cases,
            by_type={k.value: len(v) for k, v in suite.by_type.items()},
        )
        return suite

    def _parse_response(
        self, content: str, request: GenerationRequest, model: str
    ) -> list[TestCase]:
        """Parse LLM response into structured TestCase objects."""
        # Extract JSON from response (handle markdown code blocks)
        json_str = content.strip()
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            json_str = "\n".join(lines[1:])
            if json_str.endswith("```"):
                json_str = json_str[:-3]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ParseError(f"Failed to parse LLM response as JSON: {e}") from e

        test_cases_data = data if isinstance(data, list) else data.get("test_cases", [])

        test_cases: list[TestCase] = []
        for i, tc_data in enumerate(test_cases_data):
            if not isinstance(tc_data, dict):
                continue

            steps = [
                TestStep(
                    step_number=s.get("step_number", j + 1),
                    action=s.get("action", ""),
                    expected_result=s.get("expected_result", ""),
                    test_data=s.get("test_data"),
                )
                for j, s in enumerate(tc_data.get("steps", []))
                if isinstance(s, dict)
            ]

            tc = TestCase(
                id=tc_data.get("id", f"tc-{uuid.uuid4().hex[:8]}"),
                title=tc_data.get("title", f"Test Case {i + 1}"),
                description=tc_data.get("description", ""),
                preconditions=tc_data.get("preconditions", []),
                steps=steps,
                expected_outcome=tc_data.get("expected_outcome", ""),
                test_type=self._resolve_type(tc_data.get("test_type", "functional")),
                priority=self._resolve_priority(tc_data.get("priority", "medium")),
                tags=tc_data.get("tags", []) + request.tags,
                requirement_ids=tc_data.get("requirement_ids", []),
                model_used=model,
                confidence_score=tc_data.get("confidence_score"),
            )
            test_cases.append(tc)

        if not test_cases:
            raise GenerationError("LLM returned no parseable test cases")

        return test_cases[: request.max_cases]

    @staticmethod
    def _resolve_type(value: str) -> TestType:
        try:
            return TestType(value.lower().replace("-", "_").replace(" ", "_"))
        except ValueError:
            return TestType.FUNCTIONAL

    @staticmethod
    def _resolve_priority(value: str) -> Priority:
        try:
            return Priority(value.lower())
        except ValueError:
            return Priority.MEDIUM
