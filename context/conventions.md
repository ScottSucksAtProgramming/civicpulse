---
title: "CivicPulse Conventions"
summary: "Filing patterns, naming rules, privacy boundaries, and architectural standards for the CivicPulse project"
created: 2026-04-12
updated: 2026-04-12
---

# CivicPulse Conventions

## What Belongs Here

- All source code for the CivicPulse agent (scraper, RAG pipeline, backend API, frontend)
- Configuration files (env templates, vector DB config, scraper schedules)
- Prompt templates and system prompt files
- Data pipeline scripts and embedding utilities
- Tests for all of the above

## What Does NOT Belong Here

- Planning notes and non-code documentation → `~/Documents/1_projects/` (Obsidian vault)
- Raw scraped data or vector database snapshots → store externally or in a gitignored `data/` folder
- API keys or secrets → `.env` only, never committed; provide `.env.example` instead
- Any file containing real resident data or conversation logs

## Privacy Boundaries

- **Never commit** any file that could contain PII — names, emails, addresses, IP addresses, phone numbers.
- Conversation logs go through a PII redaction pipeline before any persistence. The raw log must never touch disk.
- If a user volunteers personal info in conversation, it is session-scoped only — do not pass it to any logging or analytics path.
- The aggregate data store holds only anonymized topics and themes, nothing traceable to an individual.

## Naming Conventions

- Use `snake_case` for Python files and directories.
- Use `kebab-case` for frontend files and routes.
- Prompt template files: `{feature}_system_prompt.txt` (e.g., `civic_qa_system_prompt.txt`, `letter_draft_system_prompt.txt`).
- Scraper modules named by source: `scraper_babylon_website.py`, `scraper_ecode360.py`, `scraper_youtube.py`.

## Model Usage

- Default to Claude Haiku for all standard RAG queries.
- Escalate to Claude Sonnet only for complex queries (multi-document reasoning, letter drafting).
- Model selection must be configurable via environment variable — no hardcoded model strings in business logic.
- Keep system prompts in external template files, not inline in code.

## RAG Architecture Standards

- All responses to civic questions must be grounded in retrieved chunks, not model training data.
- Every response must include a source citation (document name and URL where applicable).
- If retrieval returns no relevant results, the agent must say so and point to the official source — never hallucinate.
- Confidence threshold behavior (low-confidence disclaimer + source link) must be implemented before launch.

## Data Source Rules

- Only scrape publicly accessible pages. Check `robots.txt` before adding a new source.
- Rate-limit all scrapers. No aggressive crawling.
- YouTube: use YouTube Data API only. No direct video or audio scraping.
- eCode360: respect their terms of service; consider caching aggressively to minimize requests.

## Lessons Learned

<!-- Append dated one-liners below as patterns emerge during development. -->
