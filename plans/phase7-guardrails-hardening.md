# Plan: Phase 7 — Guardrails & Hardening

> Source PRD: GitHub issue #11 — Phase 7: Guardrails & Hardening

## Architectural decisions

Durable decisions that apply across all phases:

- **Confidence threshold**: Zero results OR top BM25 score below `CIVICPULSE_SCORE_FLOOR` (env var) → soft refusal. Short-circuit happens in `QueryPipeline.run()` BEFORE calling `Synthesizer.synthesize()` — no LLM call on the zero-results path.
- **Score floor default**: If `CIVICPULSE_SCORE_FLOOR` is unset, the threshold check is skipped (all results pass). The calibration script sets the recommended value in `.env.example`.
- **BM25 score convention**: FTS5 `rank` values are negative; the indexer already converts to positive via `abs(r["rank"])`. Higher = better match. All threshold comparisons use this positive convention.
- **`score` field on Source**: Add `score: float | None = None` to `Source` in `types.py`. Populated by `Retriever.retrieve()`. Not returned in API responses.
- **`clarifying` field on QueryResponse**: Add `clarifying: bool = False` to `QueryResponse` in `types.py`. Set to `True` when the Synthesizer returns a clarifying question instead of an answer. Frontend uses this field — not LLM output pattern-matching — to detect evaluative dialogue state.
- **Unanswered query log**: New `UnansweredLogger` class in `api/loggers.py` following the existing `QueryLogger`/`SoapboxLogger` pattern. Creates and writes to `unanswered_log` table in the existing `.index.db` SQLite database. Schema: `(id INTEGER PRIMARY KEY, redacted_query TEXT, failure_type TEXT, document_type TEXT, timestamp TEXT NOT NULL)`. Written at every soft-refusal point; never written for successful responses.
- **failure_type enum**: `zero_results | low_score | no_citation | pii_refusal | evaluative_redirect`
- **Soft-refusal surface**: One unified `QueryResponse(answer=<refusal_copy>, sources=[], clarifying=False)` to the user regardless of internal failure type.
- **Citation enforcement (pilot mode)**: No citation found → log `no_citation` to `unanswered_log` and attach all retrieved sources. Do NOT discard the answer. Can be tightened to hard refusal post-pilot.
- **Context-aware refusal variants**: Only produced when the Synthesizer runs (sources present but insufficient). Zero-results path always returns the static default warm-redirect copy — no additional LLM call.
- **Evaluative dialogue**: Handled via Synthesizer system prompt + `clarifying` field + client-side state. No new API endpoints. Second turn is a reformulated `/query` call with user criteria appended to the original question.
- **PII backstop**: Public officials, elected representatives, and named town employees acting in official capacity are in scope. Private individuals (non-officials) are refused.
- **System prompt layering**: Each phase that modifies the Synthesizer system prompt EXTENDS it — never replaces prior additions.
- **No new API endpoints** in Phase 7. `POST /query` response shape is unchanged except for the new `clarifying` field.

---

## Phase 1: Confidence Threshold + Unanswered Query Log

**User stories**: 1, 11, 12

### What to build

The foundation for all subsequent guardrails: a data-driven confidence floor, a logging table that captures every soft-refusal, and an updated soft-refusal message that warms the user toward what CivicPulse can help with.

**First task — update `NO_CONTENT_FALLBACK`**: Replace the existing generic fallback string in the Synthesizer with a warm redirect that explains 2–3 things CivicPulse can help with (e.g. meeting minutes, town ordinances, contacting a representative). This is a one-line change and the fastest user-visible improvement in the phase.

**Calibration script**: Write a simple Python script (not a CLI tool — no argparse, prints to stdout only) that runs a set of known-good queries against the current vault, records the BM25 scores for top results, computes the 25th-percentile score, and prints the recommended `CIVICPULSE_SCORE_FLOOR` value. Update `.env.example` with the recommended value and a comment explaining it.

**`UnansweredLogger`**: Create this class in `api/loggers.py` following the pattern of `QueryLogger` and `SoapboxLogger`. It creates the `unanswered_log` table if absent and exposes a `log_refusal(redacted_query, failure_type, document_type)` method. The redacted query must be passed through the existing `redact()` function before storage.

**`Source.score` field**: Add `score: float | None = None` to `Source` in `types.py`. Populate it in `Retriever.retrieve()` from the existing `Result.score` value. Exclude `score` from the API response (add it to `response_model_exclude` in the endpoint).

**Confidence threshold in `QueryPipeline.run()`**: After retrieval, before calling the Synthesizer: if zero results, return the default soft-refusal `QueryResponse` directly and call `unanswered_logger.log_refusal(...)` with `failure_type="zero_results"`. If all source scores are below `CIVICPULSE_SCORE_FLOOR`, return the same soft-refusal and log with `failure_type="low_score"`. Pass `UnansweredLogger` into `QueryPipeline` at construction time (same pattern as other dependencies).

**Endpoint wiring**: Mount `UnansweredLogger` on `app.state` in the FastAPI lifespan. The pipeline handles logging internally — the `/query` endpoint stays thin.

### Acceptance criteria

- [ ] `NO_CONTENT_FALLBACK` updated to include warm redirect mentioning CivicPulse scope examples
- [ ] Calibration script prints 25th-percentile score and recommended `CIVICPULSE_SCORE_FLOOR`; `.env.example` updated
- [ ] If `CIVICPULSE_SCORE_FLOOR` is unset, threshold check is skipped (all above-floor results pass through)
- [ ] `score: float | None` field added to `Source`; populated by `Retriever.retrieve()`; excluded from API response
- [ ] `UnansweredLogger` class created with `ensure_table()` and `log_refusal()` methods; `redact()` applied to query before storage
- [ ] Query returning zero results → soft-refusal response; `unanswered_log` entry written with `failure_type="zero_results"`
- [ ] Query returning only below-floor scores → soft-refusal response; `unanswered_log` entry written with `failure_type="low_score"`
- [ ] Query returning above-floor results → normal response; no `unanswered_log` entry written
- [ ] Successful responses do not write to `unanswered_log`

---

## Phase 2: Context-Aware Refusals + Citation Enforcement

**User stories**: 2, 3, 4, 5, 6, 10, 11

### What to build

Make refusal messages useful rather than generic when the Synthesizer runs, and enforce citation presence without discarding answers.

**Context-aware refusal copy** (Synthesizer runs, sources present but insufficient): Extend the Synthesizer system prompt so the LLM returns context-aware refusal copy when it determines the sources cannot answer the question. Variants:
- **Future/recent events**: "I may not have the latest information — check townofbabylonny.gov directly for current schedules."
- **Hyperlocal specifics**: "That level of detail isn't in my sources — contact Town Hall directly at [link]."
- **Wrong jurisdiction**: "That may fall under [county/state/federal] rather than the Town of Babylon — here's where to look: [link]."

Note: context-aware variants are only produced by the Synthesizer when it runs. If retrieval returns zero results, the pipeline short-circuits in Phase 1 and returns the static default warm-redirect copy — there is no LLM call to generate a context-aware variant.

**Citation enforcement**: After the LLM generates a response, check for at least one bracketed citation `[N]`. If none found: call `unanswered_logger.log_refusal(...)` with `failure_type="no_citation"`, and attach all retrieved sources to the response (pilot-permissive — preserve the answer). Remove the current silent fallback in `_select_sources()` that attaches all sources without logging. The behavioral change is: add the log write; the sources-attachment behavior is unchanged.

### Acceptance criteria

- [ ] Query about a future/upcoming event (sources present but no matching data) → context-aware refusal with schedule link; no `unanswered_log` entry (LLM-generated response, not pipeline refusal)
- [ ] Query about a hyperlocal street-level detail → context-aware refusal with Town Hall contact link
- [ ] Query about a state or federal topic → context-aware refusal with jurisdiction note and relevant link
- [ ] Off-topic query with zero retrieval results → default soft-refusal with warm redirect (static copy, no LLM call)
- [ ] LLM response with no `[N]` citation → `no_citation` logged to `unanswered_log`; all retrieved sources attached to response; answer not discarded
- [ ] LLM response with valid citations → normal citation-filtered response; no `unanswered_log` entry
- [ ] Previous silent all-sources fallback (no logging) is removed; any uncited response now logs before attaching sources
- [ ] Phase 1 system prompt additions are preserved (not overwritten)

---

## Phase 3a: PII Backstop

**User stories**: 9, 12

### What to build

A system prompt instruction that prevents the agent from surfacing private individual data, while explicitly allowing queries about public officials.

Extend the Synthesizer system prompt (do not overwrite Phase 1 or 2 additions): add an instruction that the agent must refuse queries seeking private information about a **private individual** — a person who is not a public official, elected representative, or named town employee acting in official capacity. Public officials are in scope for factual queries about their official actions, voting records, and public statements.

Refusal copy: "I only cover public government records and official Town of Babylon documents — I'm not able to look up information about private individuals."

When the Synthesizer returns this refusal: call `unanswered_logger.log_refusal(...)` with `failure_type="pii_refusal"`. Detection: the Synthesizer includes a marker in the response that the pipeline checks (e.g. a sentinel prefix, or a structured output field — implementer should choose the cleanest approach consistent with the existing Synthesizer pattern).

### Acceptance criteria

- [ ] Query seeking a private individual's address or complaint history → refused with PII scope message
- [ ] Query about a named public official's voting record or town decisions → normal retrieval proceeds (not refused)
- [ ] PII refusals logged to `unanswered_log` with `failure_type="pii_refusal"` and redacted query
- [ ] Phase 1 and Phase 2 system prompt additions are preserved

---

## Phase 3b: Evaluative Dialogue

**User stories**: 7, 8, 12

### What to build

A multi-turn dialogue that helps residents form their own opinions on evaluative questions without the agent ever taking a position.

**`clarifying` field on `QueryResponse`**: Add `clarifying: bool = False` to `QueryResponse` in `types.py`. When the Synthesizer returns a clarifying question, the pipeline sets `clarifying=True` on the response. The field is included in the API response so the frontend can act on it deterministically — no pattern-matching of LLM output.

**Synthesizer system prompt**: Extend (do not overwrite prior additions) with instructions to:
1. Detect explicit evaluative framing about officials or decisions: language like "doing a good job," "how well is X performing," "is X effective," "good leader." Conservative trigger — factual questions mentioning an official by name are not evaluative.
2. When evaluative framing is detected: return a clarifying question (e.g. "What matters most to you when evaluating this? For example: budget management, infrastructure improvements, responsiveness to residents?") and set the response such that `clarifying=True` is returned.
3. In all responses: never use evaluative language (good, bad, successful, failed) about any official or decision.

**Pipeline**: When the Synthesizer signals a clarifying question, `QueryPipeline.run()` returns the clarifying `QueryResponse` with `clarifying=True` and logs `failure_type="evaluative_redirect"` to `unanswered_log`. The `evaluative_redirect` is logged on the first turn (clarifying question), not the second.

**Frontend**: Detect `clarifying: true` in the API response. Enter criteria-elicitation mode: display the clarifying question, capture the user's criteria text, then reformulate the second query as "[original question] — specifically, I care about [user criteria]" and POST to `/query` again. The second turn is a normal query with no special frontend state.

### Acceptance criteria

- [ ] `clarifying: bool = False` added to `QueryResponse` in `types.py`
- [ ] Explicit evaluative query about an official → response with `clarifying=True` and a criteria question; `evaluative_redirect` logged
- [ ] Factual question mentioning an official by name (non-evaluative, e.g. "What did the Supervisor say at the last meeting?") → answered normally; `clarifying` remains `False`
- [ ] Reformulated query with user criteria → normal retrieval, response includes citations, `clarifying=False`
- [ ] Final criteria-elicitation response contains no evaluative language ("good", "bad", "successful", "failed")
- [ ] Frontend detects `clarifying: true` and enters criteria-capture mode
- [ ] Frontend reformulates second-turn query with user criteria and POSTs to `/query`
- [ ] Phase 1, 2, and 3a system prompt additions are preserved

---

## Phase 4: Adversarial Testing & Hardening

**User stories**: 13, 14

### What to build

A comprehensive adversarial test suite that locks in guardrail behavior and prevents regressions. All tests mock the LLM provider — no live API calls in CI.

Test categories:
- **Confidence threshold**: zero results → soft-refusal + `zero_results` log; below-floor score → soft-refusal + `low_score` log; above-floor → normal response, no log
- **Context-aware refusals**: future event (sources present, no useful match) → correct copy; hyperlocal → correct copy; wrong jurisdiction → correct copy; zero-results off-topic → default warm-redirect copy (static, no LLM)
- **Citation enforcement**: uncited LLM answer → `no_citation` logged, all sources attached; cited answer → normal citation-filtered response
- **Criteria-elicitation happy path**: evaluative framing → `clarifying=True` response + `evaluative_redirect` log; reformulated query → citations present, `clarifying=False`
- **Criteria-elicitation evaluative language**: assert "good", "bad", "successful", "failed" absent from final response
- **Criteria-elicitation no false positives**: factual question mentioning official → `clarifying=False`, normal retrieval
- **PII defense — private individual**: query seeking private address → `pii_refusal` response + log
- **PII defense — public official**: query about official's voting record → normal retrieval, not refused
- **Unanswered log completeness**: each failure_type (`zero_results`, `low_score`, `no_citation`, `pii_refusal`, `evaluative_redirect`) has a test asserting the correct log entry is written with redacted query and document_type
- **Political bias**: politically-framed question returns only retrieved facts; response contains no position-taking language
- **All existing tests continue to pass**

### Acceptance criteria

- [ ] All tests mock the LLM provider — no live API calls
- [ ] Test coverage for all 5 `failure_type` values, each verifying log entry contents
- [ ] Each context-aware refusal variant has at least one test asserting the correct copy
- [ ] Public official / private individual PII boundary has dedicated tests (both directions)
- [ ] Evaluative language absence tested in criteria-elicitation final response
- [ ] `clarifying` field tested: `True` on evaluative first turn, `False` on all other responses
- [ ] Political bias prompt tests assert response contains only retrieved facts
- [ ] All pre-existing tests pass
