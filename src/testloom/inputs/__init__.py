"""TestLoom input processors — read requirements from various sources."""

from testloom.inputs.processors import (
    BaseInputProcessor,
    FileInputProcessor,
    InputRegistry,
    PDFInputProcessor,
    TextInputProcessor,
)

__all__ = [
    "BaseInputProcessor",
    "TextInputProcessor",
    "PDFInputProcessor",
    "FileInputProcessor",
    "InputRegistry",
]
