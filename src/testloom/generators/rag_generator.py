"""RAG-augmented test case generator — Phase 2.

Enriches the generation prompt with semantically relevant examples
retrieved from a ContextStore before calling the LLM, improving
test case quality and consistency across a project.
"""

from __future__ import annotations

import uuid

import structlog

from testloom.core.config import Settings
from testloom.core.models import GenerationRequest, TestSuite
from testloom.gateway.base import LLMGateway
from testloom.generators.base import BaseGenerator
from testloom.generators.requirement_generator import RequirementGenerator
from testloom.store.context_store import ContextChunk, ContextStore

logger = structlog.get_logger()


class RAGGenerator(BaseGenerator):
    """Test case generator augmented with Retrieval-Augmented Generation.

    Workflow:
    1. Query the ContextStore for chunks similar to the incoming requirement.
    2. Inject the retrieved examples into the prompt context.
    3. Delegate to RequirementGenerator for the actual LLM call.
    4. Index the resulting TestSuite back into the store (living memory).

    Usage::

        store = ContextStore(persist_dir="./chroma_data")
        gen = RAGGenerator(gateway, settings, store, n_context=3)
        suite = await gen.generate(request)
    """

    def __init__(
        self,
        gateway: LLMGateway,
        settings: Settings,
        store: ContextStore,
        n_context: int = 3,
        auto_index: bool = True,
    ) -> None:
        super().__init__(gateway, settings)
        self.store = store
        self.n_context = n_context
        self.auto_index = auto_index
        self._base_generator = RequirementGenerator(gateway, settings)

    async def generate(self, request: GenerationRequest) -> TestSuite:
        """Generate test cases with RAG context injection."""
        retrieved = self._retrieve(request.requirement_text)

        augmented_request = self._augment_request(request, retrieved)

        logger.info(
            "rag_generation_start",
            requirement_snippet=request.requirement_text[:80],
            context_chunks=len(retrieved),
        )

        suite = await self._base_generator.generate(augmented_request)

        suite.generation_metadata["rag_context_chunks"] = len(retrieved)
        suite.generation_metadata["rag_chunk_ids"] = [c.id for c in retrieved]

        if self.auto_index:
            self.store.index_test_suite(suite)

        logger.info(
            "rag_generation_complete",
            suite_id=suite.id,
            total_cases=suite.total_cases,
            context_chunks_used=len(retrieved),
        )
        return suite

    def _retrieve(self, requirement_text: str) -> list[ContextChunk]:
        """Query the store; return empty list if store is empty."""
        try:
            return self.store.query(requirement_text, n_results=self.n_context)
        except Exception as exc:
            logger.warning("rag_retrieval_failed", error=str(exc))
            return []

    def _augment_request(
        self,
        request: GenerationRequest,
        retrieved: list[ContextChunk],
    ) -> GenerationRequest:
        """Inject retrieved examples into the request context."""
        if not retrieved:
            return request

        example_blocks = []
        for i, chunk in enumerate(retrieved, 1):
            test_type = chunk.metadata.get("test_type", "")
            priority = chunk.metadata.get("priority", "")
            label = f"Example {i}" + (f" ({test_type}, {priority})" if test_type else "")
            example_blocks.append(f"{label}:\n{chunk.text}")

        rag_section = (
            "\n\n--- Relevant examples from project knowledge base ---\n"
            + "\n\n".join(example_blocks)
            + "\n--- End of examples ---\n"
        )

        existing_context = request.context or ""
        merged_context = (existing_context + rag_section).strip()

        return request.model_copy(update={"context": merged_context})
