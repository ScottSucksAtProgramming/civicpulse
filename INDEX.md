# CivicPulse Index

Quick-reference for finding content in this directory. For conventions, see `context/conventions.md`.

## Documentation

| File | Purpose | When to Use |
|------|---------|-------------|
| `docs/CivicPulse_PRD.md` | Full product requirements document — features, architecture, data sources, roadmap | Before implementing any feature; source of truth for scope and constraints |
| `docs/CivicPulse_Resources.md` | Links to all data sources, APIs, and tools referenced during planning | When setting up scrapers or integrations |
| `docs/references/` | Reference articles and research (e.g. the no-escape theorem PDF) | Background reading |
| `plans/civicpulse.md` | 8-phase vertical-slice implementation plan derived from the PRD | When starting a new phase or evaluating architectural decisions |
| `plans/phase3-web-chat.md` | 4-phase implementation plan for the Phase 3 Web Chat MVP | When building or extending the frontend |
| `plans/phase4-expanded-corpus.md` | 6-phase implementation plan for expanded corpus: eCode360, YouTube, forms depth, taxonomy fix | When implementing Phase 4 |
| `plans/phase5-letter-drafting.md` | Design decisions and implementation plan for letter drafting feature (Phase 5) | When implementing Phase 5 |
| `todo.taskpaper` | Task tracking file by milestone phase — use `na next` to see current next actions | Daily task management |

## Key Architecture References (from PRD)

| Component | Decision |
|-----------|----------|
| LLM | Claude Haiku (default) / Claude Sonnet (complex queries) via Anthropic API |
| Storage | Knowledge vault — Markdown files with YAML frontmatter; no vector database |
| Search | SQLite FTS5 (BM25 keyword) + LLM semantic re-ranking; no embedding service |
| Retrieval flow | Metadata filter → BM25 search → LLM re-ranking → grounded response |
| Data sources | townofbabylonny.gov, eCode360, YouTube Data API, Town Clerk docs |
| Frontend | Alpine.js + HTML/CSS served as static files from FastAPI (`frontend/`); no build step |
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
