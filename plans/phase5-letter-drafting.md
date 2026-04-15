# Plan: Phase 5 — Letter Drafting

> Source PRD: [GitHub Issue #9](https://github.com/ScottSucksAtProgramming/civicpulse/issues/9)

## Architectural Decisions

Durable decisions that apply across all phases:

- **Routes:** Three new endpoints under `/draft`: `POST /draft/suggest-recipient`, `POST /draft/generate`, `POST /draft/revise`. All registered via a FastAPI `APIRouter` included in `create_app()` before the `StaticFiles` mount.
- **Request/response schemas:**
  - `SuggestRecipientRequest {concern: str}` → `SuggestRecipientResponse {suggested_recipient: str, topic: str, abstracted_concern: str}`
  - `GenerateRequest {concern: str, outcome: str, tone: str, recipient: str}` → `GenerateResponse {letter: str, sources: list[Source]}`
  - `ReviseRequest {current_letter: str, revision_request: str, concern: str, recipient: str}` → `ReviseResponse {letter: str}`
- **Backend modules:** `RecipientClassifier` (Haiku tool_call, mirrors MetadataFilter pattern). `LetterGenerator` (BM25 retrieval + Sonnet completion, handles both generation and revision).
- **Models:** RecipientClassifier uses Haiku. LetterGenerator uses Sonnet. Both accept the existing provider abstraction.
- **Frontend state:** `draftMode: boolean`, `draftStep: string`, `draftContext: object` added to `chatApp()`. New message role `'letter'` for letter display. Draft mode is a parallel state layered on the existing chat, not a separate page.
- **Logging table:** `draft_log` table in SQLite: columns `recipient TEXT`, `topic TEXT`, `abstracted_concern TEXT`, `timestamp TEXT`. Raw concern is never stored.
- **Error handling:** All three endpoints return HTTP 503 on `LLMError`, matching `/query` behavior.
- **Test pattern:** `StubProvider` + `TestClient` + `monkeypatch`, identical to `test_query_api.py`.
- **Board list:** Shared constant used by both backend and frontend: Town Board, Town Council, Planning Board, Zoning Board of Appeals, Town Clerk, Department.

---

## Phase 1: Suggest Recipient — End to End

**User stories:** 1, 2, 3, 17, 20, 21, 23, 24, 25

### What to build

The first vertical cut through all layers. Tapping the "Contact a Representative" category card enters draft mode and the agent asks "What's your concern?" The user types a concern, the frontend calls `POST /draft/suggest-recipient`, the backend classifies it via a Haiku tool_call, logs an aggregate record to the `draft_log` SQLite table, and returns the classification. The frontend displays the suggestion in the chat thread (e.g. "It sounds like this is best addressed to the Planning Board.").

This slice delivers: Pydantic request/response models, the `RecipientClassifier` module, the `draft_log` table, the API router with one working endpoint, the router wired into the app factory, and the frontend state machine entering `draftMode` and advancing through `concern` to `recipient_confirm`. The frontend at this point displays the suggestion as text only — confirm/override UI comes in Phase 2.

### Acceptance criteria

- [ ] Tapping the "Contact a Representative" card sets `draftMode = true` and `draftStep = 'concern'`; the agent posts "What's your concern?" to the chat thread
- [ ] Submitting a concern calls `POST /draft/suggest-recipient` with `{concern: "..."}` and the suggested recipient is displayed in the chat
- [ ] The endpoint returns `{suggested_recipient, topic, abstracted_concern}` with HTTP 200
- [ ] A row is written to `draft_log` containing `recipient`, `topic`, `abstracted_concern`, and `timestamp` — raw concern is never stored
- [ ] `LLMError` from the provider returns HTTP 503 with the standard detail message
- [ ] Backend tests pass using `StubProvider` with no API key required

---

## Phase 2: Dialogue Collection

**User stories:** 4, 5, 6, 7, 25

### What to build

The remaining frontend dialogue steps that collect all inputs before letter generation. After the suggestion (Phase 1), the UI shows a [Yes] button and a board picker dropdown. The user confirms or overrides. The agent then asks "What outcome are you hoping for?" and collects a free-form response. The agent then asks about tone and shows three quick-tap buttons (Formal, Firm, Friendly). After tone selection, `draftContext` holds all four inputs and `draftStep` advances to `generating`.

This slice is frontend-only — no new backend endpoints.

### Acceptance criteria

- [ ] After the suggestion is shown, the UI displays a [Yes] button and a board picker with the six known options
- [ ] Selecting "Department" from the picker reveals a free-form text input for the department name
- [ ] Confirming or overriding advances `draftStep` to `outcome` and the agent asks about desired outcome
- [ ] Submitting an outcome advances `draftStep` to `tone` and shows three quick-tap tone buttons (Formal, Firm, Friendly)
- [ ] Tapping a tone button sets `draftContext.tone` and advances `draftStep` to `generating`
- [ ] At `generating`, `draftContext` contains non-empty values for `concern`, `confirmedRecipient`, `outcome`, and `tone`

---

## Phase 3: Letter Generation

**User stories:** 8, 9, 10, 22, 26

### What to build

When `draftStep` reaches `generating`, the frontend calls `POST /draft/generate`. The backend runs BM25 retrieval over the concern text using the existing `Retriever`, passes the retrieved chunks plus the four inputs to Sonnet, and returns `{letter, sources}`. If retrieval returns no chunks, the letter is generated from inputs alone with no fabricated citations. The frontend displays the letter in a new `role: 'letter'` message bubble with distinct styling and a sources toggle identical to Q&A answers.

### Acceptance criteria

- [ ] `POST /draft/generate` with valid inputs returns HTTP 200 with `{letter: str, sources: list}` where `letter` is non-empty
- [ ] When the vault contains relevant chunks, `sources` is populated and the letter references retrieved content
- [ ] When no relevant chunks exist, the endpoint returns a letter with an empty `sources` list (no fabrication)
- [ ] The frontend renders the letter in a visually distinct bubble (border, subtle background) with role `'letter'`
- [ ] A sources toggle appears below the letter bubble and works identically to Q&A source toggles
- [ ] A "Drafting your letter…" loading indicator appears during the API call
- [ ] `LLMError` returns HTTP 503; the frontend shows a styled error message in the thread
- [ ] Backend tests cover: generation with retrieval hits, generation with no hits, and LLM error

---

## Phase 4: Revision Loop

**User stories:** 11, 12, 25

### What to build

A [Revise] button in the action row below the letter bubble. Tapping it reveals a text input for the revision request. Submitting calls `POST /draft/revise`, the backend rewrites the letter with Sonnet, and the frontend replaces the letter bubble content with the revised version. `revisionCount` in `draftContext` increments with each revision. After the third revision, a soft nudge system message appears informing the resident they can download and edit the letter themselves. The nudge is informational — further revisions remain available.

### Acceptance criteria

- [ ] A [Revise] text button appears in the action row below the letter bubble
- [ ] Tapping [Revise] shows a text input for the revision request
- [ ] Submitting a revision calls `POST /draft/revise` and replaces the letter bubble text with the revised letter
- [ ] The revised letter is different from the input letter (backend test verifies non-identity)
- [ ] `revisionCount` increments with each successful revision
- [ ] After the third revision, a system message nudge appears in the chat thread
- [ ] The nudge does not prevent further revisions
- [ ] `LLMError` returns HTTP 503 with the standard detail message
- [ ] Backend tests cover: successful revision and LLM error

---

## Phase 5: PDF Download and Submit Online

**User stories:** 13, 14, 15, 16

### What to build

Two action buttons added to the letter bubble action row: [Download PDF] and [Submit Online].

**Download PDF:** jsPDF is loaded via CDN. On click, generates a formatted PDF with: today's date, recipient address block (hardcoded per board; falls back to a note to verify at townofbabylonny.gov), salutation, letter body, and closing. Downloaded as `letter-to-{recipient-slug}-{date}.pdf`.

**Submit Online:** On click, expands an inline panel below the letter bubble showing the letter text in a copyable textarea, a link to the official contact page for the confirmed recipient (from a hardcoded URL map), and brief step-by-step instructions.

This slice is frontend-only — no new backend endpoints.

### Acceptance criteria

- [ ] jsPDF loads from CDN without console errors
- [ ] Clicking [Download PDF] triggers a browser download of a `.pdf` file named `letter-to-{slug}-{date}.pdf`
- [ ] The PDF contains the date, address block (or verification note), salutation, letter body, and closing
- [ ] Clicking [Submit Online] reveals a panel with copyable letter text, a link to the official contact page, and instructions
- [ ] The link opens in a new tab
- [ ] The URL map covers all six board/office options
- [ ] Both buttons use the current letter text and remain functional after revisions

---

## Phase 6: Synthesizer Redirect and New Conversation Reset

**User stories:** 18, 19

### What to build

Two small integration touches. First, one sentence is added to the existing synthesizer system prompt: if the user asks to draft a letter, write to a representative, or contact an official, respond with a redirect to the "Contact a Representative" category card. Second, the existing "New conversation" button resets all draft state (`draftMode`, `draftStep`, `draftContext`) alongside the existing conversation reset.

### Acceptance criteria

- [ ] Typing "I want to write a letter to my representative" in free-form Q&A returns a response directing the user to the "Contact a Representative" option
- [ ] The redirect is in the synthesizer system prompt — no separate intent detection endpoint
- [ ] Clicking "New conversation" during an active draft resets `draftMode` to `false`, clears `draftContext`, and returns to the entry screen with category cards
- [ ] The existing "New conversation" behavior (clearing messages, resetting input) is unaffected for non-draft conversations
