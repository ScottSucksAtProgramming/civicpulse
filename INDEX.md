# CivicPulse Index

Quick-reference for finding content in this directory. For conventions, see `context/conventions.md`.

## Documentation

| File | Purpose | When to Use |
|------|---------|-------------|
| `docs/CivicPulse_PRD.md` | Full product requirements document — features, architecture, data sources, roadmap | Before implementing any feature; source of truth for scope and constraints |
| `docs/CivicPulse_Resources.md` | Links to all data sources, APIs, and tools referenced during planning | When setting up scrapers or integrations |
| `docs/references/` | Reference articles and research (e.g. the no-escape theorem PDF) | Background reading |
| `plans/civicpulse.md` | 8-phase vertical-slice implementation plan derived from the PRD | When starting a new phase or evaluating architectural decisions |
| `todo.taskpaper` | Task tracking file by milestone phase — use `na next` to see current next actions | Daily task management |

## Key Architecture References (from PRD)

| Component | Decision |
|-----------|----------|
| LLM | Claude Haiku (default) / Claude Sonnet (complex queries) via Anthropic API |
| Storage | Knowledge vault — Markdown files with YAML frontmatter; no vector database |
| Search | SQLite FTS5 (BM25 keyword) + LLM semantic re-ranking; no embedding service |
| Retrieval flow | Metadata filter → BM25 search → LLM re-ranking → grounded response |
| Data sources | townofbabylonny.gov, eCode360, YouTube Data API, Town Clerk docs |
| Frontend | Mobile-friendly web chat, no login required |
| Privacy | No PII — PII redaction pipeline required before any storage |

## Phases (from PRD)

| Phase | Description |
|-------|-------------|
| Phase 1 | Pilot — Town of Babylon scraper, RAG pipeline, web chat, letter drafting, aggregate logging |
| Phase 2 | Validation — hallucination monitoring, qualitative feedback, open-source model eval |
| Phase 3 | Expansion — additional municipalities, government partnerships, insights dashboard |

## context/

| File | Purpose |
|------|---------|
| `conventions.md` | Filing patterns, naming rules, privacy boundaries, and architectural standards for this project |
| `lessons.md` | Running log of lessons learned during development |

## Task Tracking

`.taskpaper` — Next actions for this project. Run `na next` to see pending tasks.
