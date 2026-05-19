# ADR-002: RAG Pipeline for Context-Aware Test Generation

**Status:** Accepted  
**Date:** 2026-05-19  
**Phase:** 2

---

## Context

Phase 1 `RequirementGenerator` treats every request in isolation. For large projects,
this produces inconsistent naming conventions, duplicate test cases across related requirements,
and misses reuse opportunities (e.g., a login precondition described 30 times instead of referenced once).

The solution is Retrieval-Augmented Generation (RAG): before calling the LLM, retrieve
semantically similar test cases from prior runs and inject them as few-shot examples.

---

## Decision

Implement a two-component RAG layer:

### 1. `ContextStore` (`src/testloom/store/context_store.py`)

- **Backend:** ChromaDB (`PersistentClient`) — local-first, no external service required.
- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` — small (80 MB), fast, good quality.
- **Storage unit:** One `ContextChunk` per `TestCase`. Text = title + type + description + steps + outcome.
- **Index trigger:** After every successful generation, the resulting `TestSuite` is automatically indexed (`auto_index=True`).
- **Query:** Cosine similarity search; returns top-n chunks closest to the incoming requirement text.

### 2. `RAGGenerator` (`src/testloom/generators/rag_generator.py`)

- Wraps `RequirementGenerator` — does not duplicate prompt/parsing logic.
- Retrieves n_context chunks from `ContextStore` (default 3).
- Injects retrieved examples as a labelled section in the `context` field of `GenerationRequest`.
- Records `rag_context_chunks` and `rag_chunk_ids` in `TestSuite.generation_metadata`.
- Gracefully degrades: if `ContextStore` is empty or unavailable, falls back to standard generation.

### 3. Input Processors (`src/testloom/inputs/processors.py`)

- `TextInputProcessor`: plain text, Markdown, RST.
- `PDFInputProcessor`: PDF via `pypdf` (lazy import, optional).
- `FileInputProcessor`: auto-selects by extension.
- `InputRegistry`: allows custom processors to be registered (Jira XML, Confluence HTML, etc.).

---

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| LangChain `VectorstoreRetriever` | Adds LangChain as a hard dependency; ChromaDB direct API is simpler and sufficient for Phase 2 |
| Pinecone / Weaviate | External service; contradicts the local-first, no-lock-in principle |
| In-memory store only | Not persistent across sessions; loses the "living memory" benefit |
| OpenAI embeddings | Requires API key for every project; defeats local dev / air-gap scenarios |

---

## Consequences

**Positive:**
- Test suites become progressively more consistent and project-aware as the store grows.
- Zero new external services — ChromaDB runs embedded in the same process.
- `RAGGenerator` and `RequirementGenerator` are interchangeable (both implement `BaseGenerator`).

**Negative / Trade-offs:**
- First `index_test_suite` call downloads `all-MiniLM-L6-v2` (~80 MB) from Hugging Face on first use.
- `chromadb` and `sentence-transformers` add ~400 MB to the install footprint (opt-in via `[rag]`).
- ChromaDB's HNSW index is single-node; for enterprise multi-tenant scale, Phase 5 should migrate to `pgvector`.

---

## Future (Phase 3)

- Multi-agent review mesh will use the same `ContextStore` to check for near-duplicate test cases.
- A `LangGraph` agent will orchestrate: Retrieve → Generate → Review → Index → Publish.
- `pgvector` adapter will be added as an alternative backend for PostgreSQL-hosted deployments.
