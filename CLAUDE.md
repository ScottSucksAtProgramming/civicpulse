# CivicPulse — Civic Engagement & Local Government Intelligence Agent

## Purpose

CivicPulse is a conversational AI agent that helps Town of Babylon, NY residents understand and engage with their local government. It provides plain-language answers to civic questions using RAG over official public sources, helps residents find local services, and assists with drafting communications to elected representatives. Privacy is foundational: no PII is collected, stored, or logged.

## Tree

```
civicpulse/
  CLAUDE.md
  INDEX.md
  .taskpaper
  todo.taskpaper
  .gitignore
  .python-version
  .env.example
  pyproject.toml
  src/
    civicpulse/
      scraper/
        sources/
      backend/
        api/
        providers/
          __init__.py
          anthropic.py
          base.py
          openai_compat.py
        retrieval/
          metadata_filter.py
          query_pipeline.py
          retriever.py
          synthesizer.py
        types.py
  tests/
    backend/
      test_anthropic_provider.py
      test_metadata_filter.py
      test_openai_provider.py
      test_query_api.py
    scraper/
      fixtures/
  vault/
  frontend/
  docs/
    CivicPulse_PRD.md
    CivicPulse_Resources.md
    scraping_policy.md
    references/
      the_price_of_meaning_why_rag_knowledge_graphs_and_every_semantic_memory_will_always_fail.pdf
  plans/
    civicpulse.md
    phase1-scaffold.md
    phase1-implementation.md
    pdf-date-extraction.md
    phase2-retrieval-pipeline.md
    multi-provider-llm.md
  context/
    conventions.md
    lessons.md
```

## Rules

1. On session start within `civicpulse/`, read this file, then `INDEX.md`.
2. The PRD (`CivicPulse_PRD.md`) is the authoritative spec. Read it before implementing features or making architectural decisions.
3. Privacy is non-negotiable. No code may collect, log, or transmit personally identifiable information. PII redaction must be applied before any data is stored.
4. The agent must remain strictly non-partisan and non-advocacy. It informs; it never directs political opinions or votes.
5. All civic content answers must be grounded in retrieved documents (RAG), not LLM training data. Responses must cite their source.
6. LLM defaults: Claude Haiku for standard queries, Claude Sonnet for complex queries. Architecture must allow model swapping without rewriting core logic.
7. Data sources are public government websites (Town of Babylon). Respect robots.txt, rate-limit scrapers, use YouTube Data API only — no direct video scraping.
8. When creating, renaming, or deleting files, update the Tree section above.
9. Follow the Note-Taking protocol: log lessons to `context/lessons.md` after completing tasks.
10. Use `na next` to see pending tasks. Add tasks with `na add "Task text"`.

## Note-Taking

After completing a task, log any corrections, preferences, patterns, or discoveries.

**Protocol:**

1. Write a dated one-liner to the appropriate location:
   - General project lessons → `context/lessons.md`
   - Topic-specific lessons → the relevant context file's Lessons Learned section
2. If 3+ related lessons accumulate in `context/lessons.md`, extract into a new context file in `context/`, add a Lessons Learned section, and update `INDEX.md` and the Tree above.
3. Do not ask permission to log lessons. Just log them.

### Recent Lessons (last 5)

<!-- Claude maintains this as a quick-reference mirror of the most recent entries from context/lessons.md. -->

- 2026-04-13 — `create_app(vault_path)` must default to `None` and resolve from `CIVICPULSE_VAULT_PATH` env var so uvicorn `--factory` mode works without args.
- 2026-04-13 — `MetadataFilter` requires a system prompt explaining the tool's purpose; bare user messages cause models to return text instead of calling the tool, producing a silent `LLMError` fallback to empty filter.
- 2026-04-13 — Multi-provider LLM abstraction: `LLMProvider` protocol + `LLMError` in `backend/providers/base.py`; `tool_call()` takes `tool_name` + raw JSON Schema separately — each provider wraps into its own envelope; `AnthropicProvider` lazy-imports SDK in `__init__`; all SDK exceptions wrapped as `LLMError`.
- 2026-04-13 — Provider startup config belongs in FastAPI lifespan: validate `CIVICPULSE_PROVIDER` and required API keys there, build one shared provider instance, and pass `CIVICPULSE_FILTER_MODEL` separately from `CIVICPULSE_MODEL` so MetadataFilter can stay cheaper without touching QueryPipeline or the route handler.
- 2026-04-13 — Phase 2 architecture: Pydantic types in `backend/types.py`; FastAPI lifespan context manager; `MetadataFilter` uses tool-use for guaranteed JSON shape; sources attributed from input chunks via numbered references; MetadataFilter failure → empty FilterSpec fallback; Synthesizer failure → HTTP 503.
