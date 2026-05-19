"""Custom exceptions for TestLoom."""


class TestLoomError(Exception):
    """Base exception for all TestLoom errors."""


class ConfigurationError(TestLoomError):
    """Raised when configuration is invalid or missing."""


class LLMGatewayError(TestLoomError):
    """Raised when an LLM provider call fails."""


class ProviderNotFoundError(LLMGatewayError):
    """Raised when the requested LLM provider is not registered."""


class GenerationError(TestLoomError):
    """Raised when test case generation fails."""


class ParseError(GenerationError):
    """Raised when LLM output cannot be parsed into structured test cases."""


class TemplateError(TestLoomError):
    """Raised when a prompt template cannot be loaded or rendered."""


class FormatterError(TestLoomError):
    """Raised when output formatting fails."""
