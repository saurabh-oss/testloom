"""ChromaDB-backed vector store for RAG context injection.

Stores previously generated test cases and project knowledge so that
new generation requests can benefit from relevant historical examples.

Requires: pip install testloom[rag]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from testloom.core.models import TestSuite

logger = structlog.get_logger()


@dataclass
class ContextChunk:
    """A single retrievable piece of context."""

    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextStore:
    """ChromaDB-backed vector store for test-generation context.

    Usage::

        store = ContextStore(persist_dir="./chroma_data")
        store.index_test_suite(suite)           # index after generation
        chunks = store.query("login requirement", n_results=3)
    """

    def __init__(
        self,
        collection_name: str = "testloom",
        persist_dir: str | Path = "./chroma_data",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        try:
            import chromadb
            from chromadb.utils.embedding_functions import (
                SentenceTransformerEmbeddingFunction,
            )
        except ImportError as e:
            raise ImportError(
                "RAG support requires extra dependencies. "
                "Install with: pip install 'testloom[rag]'"
            ) from e

        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        ef = SentenceTransformerEmbeddingFunction(model_name=embedding_model)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "context_store_ready",
            collection=collection_name,
            persist_dir=str(self._persist_dir),
            doc_count=self._collection.count(),
        )

    # ─── Write ────────────────────────────────────────────────────────────

    def add(self, chunks: list[ContextChunk]) -> None:
        """Upsert context chunks into the store."""
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )
        logger.debug("context_store_add", count=len(chunks))

    def index_test_suite(self, suite: TestSuite) -> None:
        """Index all test cases from a TestSuite for future retrieval.

        Each test case becomes one context chunk so the RAG generator
        can pull in relevant examples based on semantic similarity.
        """
        chunks: list[ContextChunk] = []
        for tc in suite.test_cases:
            steps_text = " | ".join(
                f"{s.action} → {s.expected_result}" for s in tc.steps
            )
            text = (
                f"Title: {tc.title}\n"
                f"Type: {tc.test_type.value}\n"
                f"Description: {tc.description}\n"
                f"Steps: {steps_text}\n"
                f"Expected outcome: {tc.expected_outcome}"
            )
            chunks.append(ContextChunk(
                id=f"tc-{suite.id}-{tc.id}",
                text=text,
                metadata={
                    "suite_id": suite.id,
                    "test_type": tc.test_type.value,
                    "priority": tc.priority.value,
                    "tags": ",".join(tc.tags),
                    "requirement_ids": ",".join(tc.requirement_ids),
                    "model_used": tc.model_used or "",
                },
            ))
        self.add(chunks)
        logger.info("suite_indexed", suite_id=suite.id, chunks_added=len(chunks))

    def index_text(self, text: str, doc_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Index arbitrary text (e.g., a Confluence page or design doc) as a single chunk."""
        self.add([ContextChunk(id=doc_id, text=text, metadata=metadata or {})])

    # ─── Read ─────────────────────────────────────────────────────────────

    def query(self, query_text: str, n_results: int = 5) -> list[ContextChunk]:
        """Retrieve the top-n most semantically relevant context chunks."""
        total = self._collection.count()
        if total == 0:
            return []

        actual_n = min(n_results, total)
        results = self._collection.query(
            query_texts=[query_text],
            n_results=actual_n,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[ContextChunk] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
            chunk = ContextChunk(id=doc_id, text=doc, metadata={**meta, "_distance": dist})
            chunks.append(chunk)

        logger.debug("context_store_query", query=query_text[:80], results=len(chunks))
        return chunks

    def count(self) -> int:
        """Return total number of indexed chunks."""
        return self._collection.count()

    def delete_collection(self) -> None:
        """Wipe the entire collection (use with caution)."""
        self._client.delete_collection(self._collection.name)
        logger.warning("context_store_deleted", collection=self._collection.name)
