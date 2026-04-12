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
      backend/
  tests/
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
