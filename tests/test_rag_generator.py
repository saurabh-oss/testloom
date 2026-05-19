"""Tests for RAGGenerator with a mock ContextStore."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from testloom.core.models import GenerationRequest, TestType
from testloom.generators.rag_generator import RAGGenerator
from testloom.store.context_store import ContextChunk


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.count.return_value = 3
    store.query.return_value = [
        ContextChunk(
            id="tc-prev-001",
            text="Title: Verify user login\nType: functional\nDescription: Login happy path",
            metadata={"test_type": "functional", "priority": "critical"},
        )
    ]
    return store


@pytest.fixture
def rag_generator(mock_gateway, settings, mock_store):
    return RAGGenerator(mock_gateway, settings, mock_store, n_context=2)


@pytest.mark.asyncio
async def test_rag_generate_returns_suite(rag_generator, sample_request):
    suite = await rag_generator.generate(sample_request)
    assert suite.total_cases >= 1


@pytest.mark.asyncio
async def test_rag_injects_context_into_request(rag_generator, mock_store, sample_request):
    """RAG generator must call the store and inject context before generating."""
    suite = await rag_generator.generate(sample_request)
    mock_store.query.assert_called_once()
    assert suite.generation_metadata.get("rag_context_chunks") == 1


@pytest.mark.asyncio
async def test_rag_auto_indexes_suite(rag_generator, mock_store, sample_request):
    """Generated suite should be indexed back into the store."""
    await rag_generator.generate(sample_request)
    mock_store.index_test_suite.assert_called_once()


@pytest.mark.asyncio
async def test_rag_skips_retrieval_when_store_empty(mock_gateway, settings, sample_request):
    empty_store = MagicMock()
    empty_store.count.return_value = 0
    gen = RAGGenerator(mock_gateway, settings, empty_store, n_context=3, auto_index=False)
    suite = await gen.generate(sample_request)
    empty_store.query.assert_not_called()
    assert suite.total_cases >= 1


@pytest.mark.asyncio
async def test_rag_handles_retrieval_failure_gracefully(mock_gateway, settings, sample_request):
    """If store.query raises, generation must still succeed (graceful degradation)."""
    broken_store = MagicMock()
    broken_store.count.return_value = 5
    broken_store.query.side_effect = RuntimeError("ChromaDB unavailable")
    gen = RAGGenerator(mock_gateway, settings, broken_store, auto_index=False)
    suite = await gen.generate(sample_request)
    assert suite.total_cases >= 1  # fell back to base generation


def test_augment_request_adds_examples(rag_generator):
    request = GenerationRequest(
        requirement_text="Password reset via email",
        context="Original context.",
    )
    chunks = [
        ContextChunk(id="c1", text="Previous example text", metadata={"test_type": "functional"}),
    ]
    augmented = rag_generator._augment_request(request, chunks)
    assert "Previous example text" in augmented.context
    assert "Original context." in augmented.context


def test_augment_request_no_change_when_no_chunks(rag_generator):
    request = GenerationRequest(requirement_text="Some requirement")
    augmented = rag_generator._augment_request(request, [])
    assert augmented is request
