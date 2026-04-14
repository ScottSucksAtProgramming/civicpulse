# Plan: Phase 3 — Web Chat MVP

> Source PRD: [GitHub Issue #7](https://github.com/ScottSucksAtProgramming/civicpulse/issues/7)

## Architectural decisions

Durable decisions that apply across all phases:

- **Frontend stack:** HTML + CSS + Alpine.js (loaded from CDN). No build step, no bundler, no Node dependency.
- **File layout:** `frontend/index.html` (single page), `frontend/styles.css`. All Alpine.js logic lives in `index.html` as inline `<script>` tags.
- **Serving:** FastAPI mounts `StaticFiles` at `"/"` with `html=True` **after** all API routes are registered. The `frontend/` directory path is resolved to an absolute path inside `create_app()` to avoid working-directory-relative breakage under uvicorn `--factory` mode.
- **API contract:** Frontend calls `POST /query` with `{"question": string}`. Response shape: `{"answer": string, "sources": [{"title": string, "url": string, "document_type": string, "date": string|null}]}`. No auth, no session tokens.
- **Screen model:** Alpine.js manages a `screen` state variable with two values: `"entry"` (category cards visible) and `"chat"` (message thread visible). The input bar is visible on both screens.
- **Category data:** Defined as a single JS array of objects `{id, label, icon, examplePrompt}`. This is the only place to edit to add, remove, or reorder cards.
- **Message model:** Each message in the chat thread is `{role: "user"|"assistant"|"system", text, sources[], timestamp}`. System messages are used for accuracy nudges and errors.
- **Non-affiliation:** The tool is explicitly not affiliated with, endorsed by, or associated with the Town of Babylon. This must be impossible to miss.
- **Privacy:** No user data is collected, stored, or transmitted beyond the anonymous question text sent to `POST /query`.

---

## Phase 1: Backend serves the frontend shell

**User stories:** 1 (open without account), 10 (non-affiliation disclaimer), 13 (mobile-friendly)

### What to build

Mount the `frontend/` directory as a static file server in the existing FastAPI app, then build the page skeleton. The result is a browser-loadable page at `http://localhost:8000/` that shows the disclaimer banner, the CivicPulse header, a placeholder content area, and a fixed input bar at the bottom of the viewport. No functionality yet — just structure and styles.

The StaticFiles mount must use an absolute path derived from the source file location, not a relative path, so it works regardless of the directory uvicorn is invoked from. The mount must be registered after the existing `/query` route.

### Acceptance criteria

- [ ] `GET /` returns `frontend/index.html` from a running uvicorn instance
- [ ] `GET /styles.css` returns the stylesheet
- [ ] `POST /query` still works as before (existing tests pass)
- [ ] Page displays a persistent disclaimer banner stating CivicPulse is not affiliated with the Town of Babylon
- [ ] Page displays the CivicPulse name/header
- [ ] A text input and send button are visible and fixed to the bottom of the viewport
- [ ] Page is usable on a 375px-wide mobile screen (no horizontal scroll, no overlapping elements)
- [ ] Alpine.js loads from CDN with no console errors

---

## Phase 2: Entry screen — category cards

**User stories:** 2 (see category cards), 3 (tap card pre-fills input), 4 (bypass guide with free-form input)

### What to build

Implement the entry screen as the default view. Six category cards are rendered from a JS data array — this array is the single source of truth and is clearly commented for future maintainers. Each card has a label, an icon, and an example prompt.

Tapping a card pre-fills the text input with the card's example prompt (editable, not auto-submitted) and moves focus to the input. The user can also ignore the cards entirely and type directly into the input at any time. The input bar is always visible on both the entry and chat screens.

**Category cards (in order):**
1. What's Happening? — *"What are the upcoming town meetings and recent decisions?"*
2. Explain an Issue — *"Tell me about [issue or topic]"*
3. Find a Service — *"How do I [task or need]?"*
4. My Representatives — *"Who represents me and what have they voted on?"*
5. Contact a Representative — *"I want to reach out to my representative about an issue"*
6. How Government Works — *"How does the Town Board make decisions?"*

### Acceptance criteria

- [ ] Six category cards render on load in a 2-column grid (3 rows)
- [ ] Tapping a card pre-fills the input with that card's example prompt
- [ ] Input remains editable after a card is tapped
- [ ] User can type in the input at any time without tapping a card first
- [ ] Cards are driven by a single JS data array (not hardcoded in HTML)
- [ ] Adding, removing, or reordering a card requires changing only the data array
- [ ] Category cards are not shown once the chat screen is active
- [ ] Cards are tappable on mobile (minimum 44px touch target)

---

## Phase 3: Chat thread + live API integration

**User stories:** 5 (scrolling thread), 6 (loading indicator), 7 (source citation links), 12 (directed to official sources on no-results), 14–19 (all topic category questions return grounded answers)

### What to build

Wire the input bar to `POST /query`. On submission: the user's question is appended to the message thread, the screen transitions to `"chat"`, a loading placeholder ("Searching town records…") appears in the thread, and the API call is made. When the response arrives, the placeholder is replaced with the answer and its sources. The thread auto-scrolls to the latest message after every new entry.

Each assistant message renders its sources collapsed behind a "Show sources (N)" toggle. Tapping the toggle expands a list of linked source titles with their dates inline. Sources stay expanded or collapsed independently per message.

If the API returns an error (503 or network failure), a styled error message is appended to the thread and the input is immediately re-enabled. The error message never uses a browser `alert()`.

The input is disabled and the send button shows a spinner for the duration of any in-flight request. Submitting an empty input does nothing.

### Acceptance criteria

- [ ] Submitting a question appends it to the thread and triggers `POST /query`
- [ ] A "Searching town records…" placeholder appears while the request is in flight
- [ ] The placeholder is replaced by the answer when the response arrives
- [ ] The screen transitions from `entry` to `chat` on first submission
- [ ] The thread auto-scrolls to the latest message after each new entry
- [ ] Each answer shows a "Show sources (N)" toggle
- [ ] Tapping the toggle reveals source titles as clickable links with dates
- [ ] Sources open in a new tab
- [ ] Input is disabled and send button shows a spinner during in-flight requests
- [ ] A 503 or network error appends a styled error message to the thread
- [ ] Input is re-enabled immediately after an error
- [ ] Submitting an empty input does nothing

---

## Phase 4: Copy, reset, and accuracy nudges

**User stories:** 8 (copy with attribution), 9 (new conversation), 11 (periodic accuracy reminder), 20 (privacy info accessible)

### What to build

Add three finishing touches:

**Copy button:** Each assistant message gets a copy icon. Clicking it writes a formatted string to the clipboard: the answer text, a "Sources:" block with each source title and URL on its own line, and a closing attribution line referencing CivicPulse with its URL. The attribution URL is a single named constant at the top of the JS file — one line to update when the domain is set.

**New conversation:** A button in the header clears the message array and resets `screen` to `"entry"`, returning the user to the category cards. The input is also cleared.

**Accuracy nudges:** A system message ("Answers are AI-generated from public records — always verify important information at official sources.") is automatically injected into the chat thread after the first assistant response in a session, then after every fifth assistant response. Styled distinctly from user and assistant messages (muted, smaller text).

**Privacy statement:** A link in the page footer reads "Privacy & Data Use." For Phase 3 it scrolls to an inline `<section>` with a plain-language statement: what data is and is not collected. Full policy is a future task.

### Acceptance criteria

- [ ] Each assistant message has a copy button
- [ ] Copying writes: answer text + sources block + CivicPulse attribution line
- [ ] Attribution URL is a single named constant in the JS
- [ ] "New conversation" button appears in the header during the chat screen
- [ ] Clicking it clears the thread, clears the input, and returns to the entry screen
- [ ] An accuracy nudge system message is injected after the 1st assistant response
- [ ] An accuracy nudge is injected after every 5th assistant response thereafter
- [ ] Accuracy nudge messages are visually distinct from user and assistant messages
- [ ] A "Privacy & Data Use" link is accessible from the page footer
- [ ] The privacy section accurately describes that no personal data is collected or stored
