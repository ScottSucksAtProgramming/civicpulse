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
