---
title: "CivicPulse Lessons Learned"
summary: "Running log of corrections, preferences, and discoveries during CivicPulse development"
created: 2026-04-12
updated: 2026-04-12
---

# CivicPulse Lessons Learned

<!-- Append dated one-liners below. When 3+ related lessons accumulate, extract into a dedicated context file. -->

2026-04-12 — Replaced vector DB (Pinecone/Weaviate) with knowledge vault (markdown + YAML frontmatter) + SQLite FTS5 BM25 retrieval, based on the "no-escape theorem" paper showing semantic embedding systems have unavoidable false recall and forgetting at scale. Civic documents (similar zoning/meeting records) are especially vulnerable to false recall.
2026-04-12 — Knowledge vault can double as an Obsidian vault for curation and inspection during development; Obsidian is a dev tool only, not a runtime dependency.
2026-04-12 — Retrieval flow locked in as: metadata filter → BM25 keyword search → LLM re-ranking (Haiku) → grounded response with source citation.
2026-04-12 — Implementation plan written to plans/civicpulse.md (8 vertical-slice phases). Task tracking in todo.taskpaper (na-compatible).
2026-04-12 — Phase 1 scraper recursion follows same-domain links at depth 1, so live verification can take several minutes before the final vault index is written and query CLI results appear.
2026-04-12 — AgendaCenterScraper date extraction only works on HTML pages; PDF meeting minutes have dates embedded in body text rather than page titles, so those chunks land in vault/meeting-minutes/undated/ — needs a PDF-aware date parser in a future pass.
2026-04-12 — Subclass __init__ that hardcodes seed_urls must accept seed_urls as an optional param (defaulting to SEED_URLS) so BaseScraper.scrape() can recursively instantiate self.__class__(seed_urls=[link]) without TypeError; caught by Codex before implementation.
2026-04-13 — BaseScraper._extract_pdf() joins pages with "\n\n", making page boundaries unrecoverable from content; never try to re-isolate page 1 from content after the join — pass all of content to _parse_date() (re.search finds anywhere in string). RawDocument is a dataclass; use dataclasses.replace() to update fields, not direct mutation. PDF integration tests require a structurally valid binary fixture — plain bytes or fake strings cause pdfplumber to raise and the test never reaches the code under test. Use pytest caplog for log-warning assertions; logger name is the subclass name (AgendaCenterScraper).
2026-04-14 — Phase 3 frontend: Alpine.js (CDN, no build step) + single index.html served via FastAPI StaticFiles. StaticFiles must use an absolute path from __file__ — relative paths break under uvicorn --factory. Mount must be registered after API routes. Category cards defined as a JS data array (single source of truth). Opening message with inline category cards seeded via init() so the thread starts conversationally. Card tap submits immediately (no pre-fill). Enter submits, Shift+Enter newlines. PRD at GitHub issue #7; plan at plans/phase3-web-chat.md.
2026-04-13 — Phase 2 architecture (retrieval pipeline): Pydantic models for shared types (FilterSpec, Source, QueryResponse) in backend/types.py; FastAPI lifespan context manager for startup/shutdown (not module-level singletons); MetadataFilter uses Anthropic tool-use for guaranteed JSON shape and always uses Haiku; sources attributed from input chunks via numbered references (not parsed from LLM output); MetadataFilter failure → empty FilterSpec fallback; Synthesizer failure → HTTP 503; plan at plans/phase2-retrieval-pipeline.md.
2026-04-13 — Multi-provider LLM abstraction: LLMProvider protocol + LLMError in backend/providers/base.py (not types.py — different concern); tool_call() takes tool_name + raw JSON Schema separately, each provider wraps into its own envelope; AnthropicProvider lazy-imports SDK in __init__ to avoid ImportError at module load; all SDK exceptions wrapped as LLMError so pipeline never sees provider-specific types; plan at plans/multi-provider-llm.md.
2026-04-13 — Provider startup config belongs in FastAPI lifespan: validate `CIVICPULSE_PROVIDER` and required API keys at startup, construct one shared provider instance there, and resolve `CIVICPULSE_FILTER_MODEL` separately from `CIVICPULSE_MODEL` so MetadataFilter can stay cheaper without touching QueryPipeline or the route handler.
2026-04-13 — Natural-language questions cannot be sent directly into SQLite FTS5 `MATCH`; normalize user queries into tokenized OR terms in the Retriever wrapper so `FTSIndexer` stays unchanged and question-like input does not throw syntax errors.
2026-04-13 — `create_app(vault_path)` must default vault_path to None and resolve from `CIVICPULSE_VAULT_PATH` env var (default `./vault`) so uvicorn `--factory` mode (which calls with no args) works without errors.
2026-04-13 — MetadataFilter requires a system prompt explaining the tool's purpose; sending a bare user message with no context causes models to return text instead of calling the tool, producing an `AttributeError` on `tool_calls` which is silently swallowed as `LLMError`. Always include a system prompt in tool_call() messages.
2026-04-13 — Debug logging in openai_compat.tool_call() should use `getattr(msg, "content", None)` rather than `msg.content` — SimpleNamespace mocks in tests won't have the attribute if the real response doesn't need it.
