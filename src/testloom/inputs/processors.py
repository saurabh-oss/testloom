"""Input processors — read requirement text from various file and data sources.

Each processor handles a specific source format and returns plain text
that can be fed directly into a GenerationRequest.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

import structlog

logger = structlog.get_logger()


class BaseInputProcessor(ABC):
    """Abstract input processor."""

    #: File extensions this processor handles (lowercase, with dot)
    extensions: ClassVar[frozenset[str]] = frozenset()

    @abstractmethod
    def read(self, source: str | Path) -> str:
        """Return the requirement text extracted from *source*."""

    def supports(self, source: str | Path) -> bool:
        """Return True if this processor can handle the given source."""
        return Path(source).suffix.lower() in self.extensions


class TextInputProcessor(BaseInputProcessor):
    """Read plain text and Markdown files."""

    extensions: ClassVar[frozenset[str]] = frozenset({".txt", ".md", ".rst", ".text"})

    def read(self, source: str | Path) -> str:
        text = Path(source).read_text(encoding="utf-8")
        logger.debug("input_read", processor="text", path=str(source), chars=len(text))
        return text


class PDFInputProcessor(BaseInputProcessor):
    """Extract text from PDF files using pypdf.

    Requires: pip install pypdf  (included in testloom[rag])
    """

    extensions: ClassVar[frozenset[str]] = frozenset({".pdf"})

    def read(self, source: str | Path) -> str:
        try:
            import pypdf
        except ImportError as e:
            raise ImportError(
                "PDF support requires pypdf. Install with: pip install pypdf"
                " (or: pip install 'testloom[rag]')"
            ) from e

        reader = pypdf.PdfReader(str(source))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(p for p in pages if p.strip())
        logger.debug("input_read", processor="pdf", path=str(source), pages=len(reader.pages))
        return text


class FileInputProcessor(BaseInputProcessor):
    """Auto-selecting processor — picks the right implementation by file extension."""

    extensions: ClassVar[frozenset[str]] = (
        TextInputProcessor.extensions | PDFInputProcessor.extensions
    )

    def __init__(self) -> None:
        self._processors: list[BaseInputProcessor] = [
            TextInputProcessor(),
            PDFInputProcessor(),
        ]

    def read(self, source: str | Path) -> str:
        path = Path(source)
        for proc in self._processors:
            if proc.supports(path):
                return proc.read(path)
        raise ValueError(
            f"No input processor for '{path.suffix}'. "
            f"Supported: {sorted(self.extensions)}"
        )

    def supports(self, source: str | Path) -> bool:
        return Path(source).suffix.lower() in self.extensions


class InputRegistry:
    """Central registry for input processors.

    Custom processors can be registered for proprietary formats
    (e.g., Jira XML exports, Confluence HTML pages).
    """

    _registry: dict[str, BaseInputProcessor] = {}

    @classmethod
    def register(cls, extension: str, processor: BaseInputProcessor) -> None:
        """Register a custom processor for a file extension (e.g., '.jira')."""
        cls._registry[extension.lower()] = processor

    @classmethod
    def read(cls, source: str | Path) -> str:
        """Read a file using the best available processor."""
        path = Path(source)
        ext = path.suffix.lower()

        # Check custom registry first
        if ext in cls._registry:
            return cls._registry[ext].read(path)

        # Fall back to auto-selector
        return FileInputProcessor().read(path)

    @classmethod
    def supported_extensions(cls) -> list[str]:
        builtin = sorted(FileInputProcessor.extensions)
        custom = sorted(cls._registry.keys())
        return sorted(set(builtin + custom))
