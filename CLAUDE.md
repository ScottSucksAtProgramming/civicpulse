# CivicPulse — Civic Engagement & Local Government Intelligence Agent

## Purpose

CivicPulse is a conversational AI agent that helps Town of Babylon, NY residents understand and engage with their local government. It provides plain-language answers to civic questions using RAG over official public sources, helps residents find local services, and assists with drafting communications to elected representatives. Privacy is foundational: no PII is collected, stored, or logged.

## Tree

```
civicpulse/
  CLAUDE.md
  INDEX.md
  README.md
  .taskpaper
  todo.taskpaper
  .gitignore
  .python-version
  .env.example
  pyproject.toml
  src/
    civicpulse/
      scraper/
        importers/
          __init__.py
          ecode360.py
        sources/
          __init__.py
          agenda_center.py
          babylon_website.py
          ecode_api.py
          youtube.py
      backend/
        api/
          app.py
          draft.py
          loggers.py
          soapbox.py
        privacy.py
        providers/
          __init__.py
          anthropic.py
          base.py
          openai_compat.py
        retrieval/
          letter_generator.py
          metadata_filter.py
          query_pipeline.py
          recipient_classifier.py
          retriever.py
          soapbox_pipeline.py
          synthesizer.py
        types.py
  tests/
    backend/
      test_anthropic_provider.py
      test_metadata_filter.py
      test_openai_provider.py
      test_privacy.py
      test_query_api.py
    retrieval/
      golden_set.yaml
    scraper/
      fixtures/
      test_babylon_website.py
      test_cli.py
      test_ecode360.py
      test_ecode_api.py
      test_youtube.py
  vault/
    privacy/
      privacy-policy.md
  frontend/
    index.html
    privacy.html
  scripts/
    calibrate_score_floor.py
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
    phase3-web-chat.md
    phase4-expanded-corpus.md
    phase5-letter-drafting.md
    phase6-privacy-logging-soapbox.md
    phase7-guardrails-hardening.md
    phase8-monitoring-pilot-validation.md
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

# 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

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

- 2026-04-22 — Phase 8 monitoring design: feedback thumbs up/down is per-answer; thumbs-down reveals optional text box only; document_type derived client-side from sources[0].document_type (no QueryResponse schema change); ScraperLogger called from CLI entry point not BaseScraper to preserve scraper/backend boundary; draft_log gains event_type column ('suggestion' vs 'generation') so letter completion rate is measurable; no_citation is the hallucination proxy (clearly labeled, not a semantic grounding check); report is on-demand CLI script (scripts/report.py). PRD at GitHub issue #12; plan at plans/phase8-monitoring-pilot-validation.md.
- 2026-04-22 — Phase 7 guardrails design: confidence threshold = zero results OR below BM25 score floor → soft refusal; unanswered queries logged as redacted query + failure type + document_type for manual weekly review; scope guardrails via retrieval-first (not classifier) + warm redirect; citation failures use same unified soft-refusal message; budget cap is provider-agnostic (ops-only alert, no user-facing degradation); PII defense = clean vault sources + system prompt backstop; political/evaluative questions use criteria-elicitation dialogue (agent never takes position); context-aware soft-refusals distinguish future/recent events, hyperlocal specifics, wrong jurisdiction; post-generation grounding check deferred to Phase 8.
- 2026-04-22 — Phase 6 Soapbox/Privacy design: redact() is regex-only + stateless (no LLM pass) in backend/privacy.py — applied at every DB write site; QueryPipeline.run() returns (QueryResponse, FilterSpec) so endpoint can log document_type to query_log without extra LLM call; Soapbox uses separate soapboxStep/soapboxMessages vars (not draftStep); /soapbox/submit makes no LLM call — pure storage; privacy policy is a vault doc (document_type: privacy) so RAG answers privacy questions naturally; /privacy.html is a StaticFiles-served static file, no new route. Plan at plans/phase6-privacy-logging-soapbox.md.
- 2026-04-15 — Phase 5 letter drafting design: client-side state only (no sessions); 5-step frontend state machine (concern → suggest-recipient via Haiku → confirm/override → outcome → tone → generate via Sonnet); 3 backend endpoints (/draft/suggest-recipient, /draft/generate, /draft/revise); jsPDF CDN for PDF export; two delivery buttons (Download PDF / Submit Online); logging stores only third-person LLM rewrite + topic + recipient (raw concern never persisted). Plan at plans/phase5-letter-drafting.md.
- 2026-04-14 — MetadataFilter system prompt needs: (1) today's date injected dynamically for relative date resolution; (2) per-type descriptions so LLM routes clerk-form vs clerk, meeting-video vs public-meeting correctly; (3) explicit instruction to leave dates null for vague references like "last month" — over-filtering on relative dates yields NO SOURCES.
