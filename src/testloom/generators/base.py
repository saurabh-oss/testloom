"""Base generator interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from testloom.core.config import Settings
from testloom.core.models import GenerationRequest, TestSuite
from testloom.gateway.base import LLMGateway


class BaseGenerator(ABC):
    """Abstract base for all test case generators."""

    def __init__(self, gateway: LLMGateway, settings: Settings) -> None:
        self.gateway = gateway
        self.settings = settings

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> TestSuite:
        """Generate test cases from a request."""
