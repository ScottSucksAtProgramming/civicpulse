# Plan: Phase 2 — Core Retrieval Pipeline

> Source PRD: [GitHub Issue #4 — Phase 2: Core Retrieval Pipeline](https://github.com/ScottSucksAtProgramming/civicpulse/issues/4)

## Architectural decisions

Durable decisions that apply across all phases:

- **Module layout**: `backend/retrieval/` owns all pipeline logic (MetadataFilter, Retriever, Synthesizer, QueryPipeline). `backend/api/` owns the HTTP surface (FastAPI app, routes). `backend/types.py` holds shared Pydantic models — both sides import from it, never from each other.
- **Shared types**: `FilterSpec`, `Source`, and `QueryResponse` are Pydantic `BaseModel` subclasses in `backend/types.py`. These are the contracts between pipeline stages and double as FastAPI request/response schemas.
- **Dependency injection**: The Anthropic client and `FTSIndexer` are instantiated once in a FastAPI `lifespan` context manager and stored on `app.state`. Pipeline components receive them via constructor injection. No module-level singletons.
- **MetadataFilter LLM call**: Uses Anthropic tool-use (function-calling) with a `classify_query` tool whose input schema matches `FilterSpec`. Guaranteed JSON shape; no free-text parsing. MetadataFilter always uses `claude-haiku-4-5-20251001` regardless of the model param in the request.
- **Source attribution**: Sources come from the input chunks, not from LLM output. Chunks are passed as numbered references (`[1]`, `[2]`, ...) in the Synthesizer prompt. The LLM cites by number; the pipeline maps numbers back to known `Source` objects derived from vault frontmatter.
- **Failure contract**:
  - MetadataFilter LLM failure → log warning, fall through with empty `FilterSpec` (unfiltered BM25 search)
  - Retriever returns zero results → Synthesizer returns canned no-content response (no LLM call)
  - Synthesizer LLM failure → HTTP 503 with user-friendly error message
- **API contract**:
  - `POST /query` request: `{ "question": str, "model": str | None }`
  - `POST /query` response: `{ "answer": str, "sources": [{ "title", "url", "document_type", "date" }] }`
  - HTTP 200 for both normal answers and no-content fallbacks
  - HTTP 503 for Synthesizer LLM failures
  - HTTP 422 for malformed requests (FastAPI default)
- **Model selection**: `CIVICPULSE_MODEL` env var sets the synthesis default (default: `claude-haiku-4-5-20251001`). Optional `model` field in request body overrides per-request. MetadataFilter is always Haiku.
- **Top-N**: `CIVICPULSE_TOP_N` env var controls how many BM25 chunks are passed to the Synthesizer (default: `5`).

---

## Phase 1: Wired Retrieval (no LLM)

**User stories**: 8, 11, 15 — developer can call `POST /query`, get structured JSON back with real vault chunks, wire a frontend to it.

### What to build

Add `fastapi`, `uvicorn`, and `anthropic` to project dependencies. Define all Pydantic types (`FilterSpec`, `Source`, `QueryResponse`) in `backend/types.py`. Build the `Retriever` as a thin wrapper around the existing `FTSIndexer.query()` that accepts a `FilterSpec` and returns a list of `Source` objects.

Stand up the FastAPI application with a lifespan context manager that opens the FTS index and constructs the pipeline. Implement `POST /query` that accepts `{question, model}`, runs `Retriever` against the vault with no filter, and returns a `QueryResponse` with an empty `answer` string and the top-5 chunks as `sources[]`.

Write integration tests that seed a small test vault, build the FTS index, call `POST /query` via `TestClient`, and assert the response shape is correct and `sources` contains real vault chunks.

### Acceptance criteria

- [x] `fastapi`, `uvicorn`, and `anthropic` added to `pyproject.toml`
- [x] `FilterSpec`, `Source`, `QueryResponse` defined as Pydantic models in `backend/types.py`
- [x] `Retriever` wraps `FTSIndexer.query()` and accepts a `FilterSpec`; BM25 search runs against the real vault
- [x] `POST /query` returns HTTP 200 with `{ "answer": "", "sources": [...] }` shape
- [x] FastAPI app uses lifespan context manager; `FTSIndexer` and pipeline live on `app.state`
- [x] Integration test: seeded vault + `TestClient` call returns correct `sources` shape with real chunk metadata
- [x] `CIVICPULSE_TOP_N` env var controls number of returned chunks (default 5)

---

## Phase 2: LLM Synthesis + No-Content Fallback

**User stories**: 1, 2, 3, 4, 7, 12, 13, 14, 16 — resident asks a question and gets a grounded plain-language answer with source citations; gets a helpful message when no content is found.

### What to build

Build the `Synthesizer` module. It receives the original question and a list of `Source`-annotated chunks. If the chunk list is empty, it returns a canned no-content `QueryResponse` without calling the LLM. Otherwise it builds a prompt with numbered chunk references (`[1]`, `[2]`, ...) and calls the configured LLM to produce a grounded answer. The LLM is instructed to cite only by reference number. Sources are assembled from the input chunks (not parsed from LLM output) — whichever chunks are cited appear in `sources[]`; if none are cited, all passed-in chunks are included.

Build `QueryPipeline` to orchestrate: MetadataFilter (passthrough stub in this phase) → Retriever → Synthesizer. Wire the pipeline into `POST /query`.

Write end-to-end tests using `TestClient` with the Anthropic client mocked. Assert that a normal query returns a non-empty `answer` and populated `sources[]`. Assert that a query returning zero BM25 results returns the canned fallback without making an LLM call. Assert that Synthesizer LLM failure returns HTTP 503.

### Acceptance criteria

- [x] `Synthesizer` returns canned fallback (`answer` + `sources: []`) when chunk list is empty — no LLM call made
- [x] `Synthesizer` calls the LLM with numbered chunk references and populates `sources[]` from input chunks
- [x] No-content fallback message includes a link to `townofbabylonny.gov`
- [x] `QueryPipeline` orchestrates Retriever → Synthesizer (MetadataFilter is passthrough)
- [x] `POST /query` returns HTTP 503 with user-friendly message on Synthesizer LLM failure
- [x] End-to-end test (mocked LLM): normal query → HTTP 200 with `answer` + `sources`
- [x] End-to-end test (mocked LLM): zero-results query → HTTP 200 with canned fallback, no LLM call made
- [x] End-to-end test: Synthesizer LLM failure → HTTP 503

---

## Phase 3: Metadata Filter

**User stories**: 5, 6 — questions about specific document types or date ranges return more relevant results.

### What to build

Build `MetadataFilter` using Anthropic tool-use. Define a `classify_query` tool whose input schema matches `FilterSpec`. The module calls `claude-haiku-4-5-20251001` (hardcoded, not affected by the request's `model` param), extracts the tool-use response, and returns a populated `FilterSpec`. On any LLM failure (network error, rate limit, unexpected response shape), log a warning and return `FilterSpec(document_type=None, date_from=None, date_to=None)`.

Wire `MetadataFilter` into `QueryPipeline` replacing the passthrough stub. Filters flow from `MetadataFilter` into `Retriever` before BM25 runs.

Write unit tests with the Anthropic client mocked to return canned tool-use responses. Assert correct `FilterSpec` extraction for queries mentioning document types ("meeting minutes", "ordinance") and date references ("2024", "last year"). Assert the graceful fallback `FilterSpec` is returned when the mock raises an exception.

### Acceptance criteria

- [x] `MetadataFilter` uses Anthropic tool-use with a `classify_query` tool matching the `FilterSpec` schema
- [x] `MetadataFilter` always uses `claude-haiku-4-5-20251001` regardless of the request `model` param
- [x] On any LLM failure, `MetadataFilter` logs a warning and returns an empty `FilterSpec` (no exception propagated)
- [x] `QueryPipeline` wires `MetadataFilter` → `Retriever` → `Synthesizer`
- [x] Unit test (mocked LLM): query mentioning "meeting minutes" → `FilterSpec(document_type="meeting-minutes", ...)`
- [x] Unit test (mocked LLM): query mentioning a year → `FilterSpec(date_from="YYYY-01-01", date_to="YYYY-12-31")`
- [x] Unit test (mocked LLM): unfiltered query → `FilterSpec(None, None, None)`
- [x] Unit test: LLM exception → graceful fallback `FilterSpec`, no crash

---

## Phase 4: Model Selection & Configuration Hardening

**User stories**: 9, 10 — developers can escalate to Sonnet per-request; operators can change the default model and top-N without code changes.

### What to build

Thread the optional `model` request body field through `QueryPipeline` to `Synthesizer`. `Synthesizer` uses the provided model if present, otherwise falls back to `CIVICPULSE_MODEL` env var (default: `claude-haiku-4-5-20251001`). `MetadataFilter` ignores this field and always uses Haiku.

Ensure `CIVICPULSE_TOP_N` env var is read at startup (in the lifespan context) and passed to `Retriever`. Validate env var values at startup and log clear errors for invalid types.

Write a test asserting that passing `model=claude-sonnet-4-6` in the request body causes the Synthesizer mock to be called with that model ID. Write a test asserting that omitting `model` uses the `CIVICPULSE_MODEL` env var default.

### Acceptance criteria

- [x] `model` field in request body is optional; omitting it uses `CIVICPULSE_MODEL` env var
- [x] `Synthesizer` receives and uses the resolved model ID
- [x] `MetadataFilter` is unaffected by `model` override — always uses Haiku
- [x] `CIVICPULSE_TOP_N` env var is read at startup and passed to `Retriever`; invalid values produce a clear startup error
- [x] Test: `model=claude-sonnet-4-6` in request → Synthesizer called with `claude-sonnet-4-6`
- [x] Test: no `model` in request + `CIVICPULSE_MODEL=claude-haiku-4-5-20251001` → Synthesizer called with Haiku model ID
- [ ] Manual verification: end-to-end query with `model=claude-sonnet-4-6` returns a valid grounded answer from the live vault
