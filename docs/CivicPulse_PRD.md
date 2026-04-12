**CivicPulse**

A Civic Engagement & Local Government Intelligence Agent

**Product Requirements Document**

Version 1.0 \| Draft \| April 2026

  ----------------------- -----------------------------------------------
  **Pilot Region**        Town of Babylon, New York

  **Status**              Draft -- Subject to Revision

  **Author**              Confidential

  **Last Updated**        April 2026
  ----------------------- -----------------------------------------------

**1. Executive Summary**

CivicPulse is a conversational AI agent designed to help everyday
residents understand and engage with their local government. The agent
provides plain-language explanations of bills, laws, budgets, and civic
processes; connects residents to local services and community resources;
and---if they choose---helps them draft communications to their elected
representatives. The pilot will be built around the Town of Babylon, New
York, with a long-term vision of expanding to other municipalities
across the country.

The core mission is simple: inform without agenda, empower without
pressure. CivicPulse will never tell residents what to think or how to
vote. It will give them the information they need to make their own
decisions.

**2. Problem Statement**

Most residents have no reliable, accessible way to stay informed about
what their local government is actually doing. The specific problems
CivicPulse addresses are:

-   Information is scattered across multiple government websites with no
    central hub.

-   Official documents are written in dense legal and bureaucratic
    language most people cannot parse.

-   Local news is increasingly filtered through editorial opinions,
    leaving residents uncertain whether they are getting the full
    picture.

-   Residents do not know what services, programs, or resources their
    government offers them---from adult education to financial
    assistance to community events.

-   Civic engagement (contacting representatives, attending hearings)
    feels overwhelming and inaccessible to most people.

**3. Goals & Non-Goals**

**3.1 Goals**

-   Provide a non-judgmental, conversational interface for exploring
    local government activity.

-   Help residents understand civic processes---how a bill becomes a
    law, how town meetings work, how to use government services.

-   Surface upcoming meetings, votes, budget changes, zoning decisions,
    and other civic events.

-   Connect residents to local services: financial aid, adult education,
    counseling, community programs, and events.

-   Assist residents in drafting personalized letters or emails to their
    elected representatives.

-   Collect anonymous, aggregate conversation data to surface what
    issues matter most to the community.

**3.2 Non-Goals**

-   CivicPulse will NOT collect, store, or analyze personally
    identifiable information.

-   CivicPulse will NOT push residents toward any political position,
    candidate, or action.

-   CivicPulse will NOT serve as a substitute for official legal or
    governmental advice.

-   CivicPulse will NOT require user accounts, logins, or registration
    to use.

-   CivicPulse will NOT partner directly with government IT systems in
    the initial pilot phase.

**4. Target Users**

CivicPulse is designed for any resident of the Town of Babylon who wants
to be more informed. No prior civic knowledge is required or assumed.
The agent should feel welcoming to:

-   Residents who have never attended a town hall meeting and don\'t
    know where to start.

-   People facing a specific problem---housing, benefits,
    employment---who don\'t know what government help exists.

-   Engaged citizens who want unfiltered access to what their
    representatives are actually voting on.

-   Residents who want to contact their representatives but don\'t know
    how.

-   Community members curious about upcoming events, programs, and local
    activities.

**5. Core Features**

**5.1 Guided Entry Point**

When a user first arrives, the agent offers a welcoming, conversational
guided entry to help them find what they are looking for. The entry
point surfaces the main categories of help available without implying
those are the only options. Users can bypass the guide at any time and
ask free-form questions.

**5.2 Civic Information & Document Q&A**

The agent answers questions about what the Town of Babylon is
doing---bills, ordinances, zoning decisions, budget changes, public
hearings, board meeting outcomes, and more. All answers are drawn from
official government sources, not from model training data, using
Retrieval-Augmented Generation (RAG). The agent will:

-   Explain documents in plain language.

-   Break down legal jargon and bureaucratic terminology.

-   Provide context about how a decision might affect residents.

-   Say \"I don\'t know\" or direct users to official sources if
    information is unavailable.

**5.3 Civic Education**

The agent proactively offers to explain how local government works---how
bills become laws, how the town board voting process operates, how
residents can participate in public hearings, and how to register to
vote. This educational layer is offered, not forced, and is designed to
empower residents without directing them.

**5.4 Local Services & Resources Finder**

The agent helps residents discover what the Town of Babylon offers,
including:

-   Adult education programs

-   Financial assistance and housing support

-   Counseling and mental health resources

-   Community events, parks, and recreation

-   Recycling schedules, permits, and public facilities

If a resident describes a problem they are facing, the agent will
identify relevant government programs or resources that may help.

**5.5 Representative Communication Assistant**

If a resident wants to contact an elected official, the agent will:

-   Engage them in a brief back-and-forth dialogue to understand their
    concerns and desired tone.

-   Help draft a personalized, clear letter or email in their own voice.

-   Provide a downloadable PDF of the letter for mailing.

-   Provide the direct link or website where the message can be
    submitted electronically.

The agent will never advocate for a position. The resident drives the
content and the decision to send.

**5.6 Anonymous Aggregate Data Collection**

To surface what issues matter most to the community, CivicPulse logs
conversation topics and themes---never personal information.
Additionally, a voluntary \"soapbox\" feature allows any user to submit
a free-form message about what matters to them in their community. This
data feeds an aggregate insights dashboard.

The agent will be transparent about this collection. A privacy statement
on the site and within the agent\'s own responses will explain: what is
collected (topics, themes), what is not collected (names, addresses, IP
addresses, any identifying information), and how the data may be used.

**6. Privacy & Data Principles**

Privacy is foundational to CivicPulse, not an afterthought. The
following principles are non-negotiable:

-   **No personal data collection.**

```{=html}
<!-- -->
```
-   No names, email addresses, phone numbers, or physical addresses will
    be stored.

-   No IP addresses or device identifiers will be logged.

-   If a user volunteers personal information in conversation, it will
    be used only within that session and never stored.

```{=html}
<!-- -->
```
-   **De-identification pipeline.**

```{=html}
<!-- -->
```
-   All conversation logs will pass through an automated PII detection
    and redaction layer before storage.

-   Pattern matching and AI-assisted review will flag and strip
    addresses, names, and other identifiers.

```{=html}
<!-- -->
```
-   **Transparency by default.**

```{=html}
<!-- -->
```
-   A clear privacy statement will be displayed on the site.

-   The agent itself can answer questions about what data is and is not
    collected.

```{=html}
<!-- -->
```
-   **Aggregate only.**

```{=html}
<!-- -->
```
-   Stored data will consist of anonymized topics, themes, and
    conversation categories---nothing that can be traced to an
    individual.

**7. Technical Architecture**

**7.1 Data Sources (Pilot: Town of Babylon)**

The agent will pull from publicly available government sources
including:

-   townofbabylonny.gov -- Official town website

-   Agenda Center -- Town Board, Planning Board, Zoning Board meeting
    agendas and minutes

-   eCode360 -- Town of Babylon code, ordinances, and zoning laws

-   YouTube (Town of Babylon channel) -- Meeting livestreams and
    recordings (via YouTube API and auto-generated captions)

-   Town Clerk forms, documents, and FOIL resources

-   Supplementary civics educational materials (how bills work, how
    meetings function, etc.)

**7.2 Data Pipeline**

A scheduled web scraper (running nightly or weekly depending on update
frequency) will pull new and updated content from the above sources.
Content will be chunked into meaningful segments and stored as
structured Markdown files with YAML frontmatter in a hierarchical
knowledge vault. No vector database or embedding service is required.

Each document chunk is stored as a `.md` file with frontmatter metadata
including: `source_url`, `document_type` (e.g. meeting-minutes,
ordinance, service-page), `date`, `meeting_id` (where applicable), and
`chunk_index`. The vault directory structure mirrors document type and
date, making the knowledge base human-inspectable and auditable. The
vault can be opened as an Obsidian vault for curation, verification, and
debugging during development — Obsidian is a development tool, not a
runtime dependency.

A full-text search index (SQLite FTS5 or Typesense) is built over the
vault and updated incrementally as new files are added.

**7.3 Hybrid Retrieval & Generation**

Pure semantic (vector) retrieval organises information by meaning, which
causes two mathematically unavoidable failure modes as the corpus grows:
interference-driven forgetting (older documents get crowded out) and
false recall (factually distinct documents with similar meaning get
conflated). Civic documents are especially vulnerable because they
contain many semantically similar records (e.g. multiple zoning
variances, recurring meeting minutes). The knowledge vault design
addresses this by separating exact episodic storage from semantic
reasoning.

When a user asks a question, the system will:

1.  Apply metadata filters where inferable from the query (date range,
    document type, meeting type) to narrow the candidate set before any
    retrieval occurs.

2.  Run BM25 keyword search over the filtered vault to retrieve the
    top-N candidate chunks. Keyword search handles civic-specific
    terminology (ordinance numbers, street addresses, program names)
    without semantic interference.

3.  Pass the top-N chunks to the LLM for semantic re-ranking and
    synthesis. The LLM selects the most relevant chunks and generates a
    response grounded only in that retrieved content.

4.  The LLM generates a response based only on the retrieved content,
    not its training data. Each response cites the source file and URL.

5.  If no relevant content is found, the agent will say so and direct
    the user to official sources.

**7.4 Language Model**

Initial implementation will use Claude Haiku (Anthropic) via API for
cost efficiency. Claude Sonnet will serve as a fallback for more complex
queries. Open-source models (e.g., Llama, Mistral) will be evaluated for
migration once the product is validated, to reduce API costs at scale.

Usage limits and budget caps will be configured to prevent runaway API
costs. The architecture should allow model swapping without rewriting
core logic.

**7.5 Guardrails**

Multiple layers will prevent hallucination and off-topic responses:

-   System prompt engineering: The LLM is explicitly instructed to
    answer only from retrieved content and to say \"I don\'t know\" when
    information is unavailable.

-   Source citation: Responses will reference the document or source
    they are drawn from.

-   Confidence thresholds: Low-confidence responses will surface a
    disclaimer and a link to the original source.

-   Post-generation filtering: Outputs will be checked before delivery
    for factual grounding.

-   Scope guardrails: The agent is instructed to stay within the civic
    domain and redirect off-topic queries.

**7.6 Frontend**

A simple, mobile-friendly web chat interface. No login required. The
interface will include a guided entry flow, a free-form chat input, and
a disclaimer noting that responses may occasionally contain errors and
that official sources should be verified for important decisions.

**7.7 Backend & Orchestration**

A backend API layer will orchestrate the retrieval pipeline, LLM calls,
logging, and letter generation output. The retrieval pipeline reads
directly from the knowledge vault via the full-text search index; no
vector database or embedding framework is required. The logging system
will handle de-identification and aggregate data storage separately from
the conversation pipeline.

**8. Town of Babylon Data Source Reference**

  ---------------------- ---------------------------------------------------------
  **Source**             **URL**

  Official Website       townofbabylonny.gov

  Agenda Center          townofbabylonny.gov/AgendaCenter

  Town Board Agendas     townofbabylonny.gov/AgendaCenter/Town-Board-4

  Public Meetings        townofbabylonny.gov/459/Upcoming-Public-Meetings

  Planning Board         townofbabylonny.gov/123/Planning-Board

  Town Council           townofbabylonny.gov/115/Town-Council

  Town Code (eCode360)   ecode360.com/BA0924

  Zoning Code            ecode360.com/6810323

  All Departments        townofbabylonny.gov/8/Departments

  Town Clerk             townofbabylonny.gov/152/Town-Clerks-Office

  Forms & Documents      townofbabylonny.gov/243/Forms-Documents

  FOIL (Public Records)  townofbabylonny.gov/392/Freedom-of-Information-Law

  Property Portal        property.townofbabylon.com

  Federal/State/County   townofbabylonny.gov/880/Federal-State-County-Government
  Links                  
  ---------------------- ---------------------------------------------------------

**9. Scraping & Legal Considerations**

Scraping publicly available government websites is generally permissible
under U.S. law, particularly for public interest and informational use
cases. However, the following precautions will be taken:

-   The town\'s robots.txt and terms of service will be reviewed before
    scraping begins.

-   Scraping will be rate-limited and respectful of server load.

-   YouTube content will be accessed via the official YouTube Data API
    only---no direct video scraping.

-   Auto-generated captions from YouTube will be used for meeting
    transcription where available.

-   A long-term goal is to establish an official data-sharing
    relationship with the Town of Babylon.

-   A disclaimer on the site will clarify that CivicPulse is an
    independent tool, not affiliated with or endorsed by the Town of
    Babylon.

**10. Aggregate Insights & Civic Intelligence**

Every conversation will be anonymized and logged for aggregate analysis.
Over time this data will reveal:

-   Which issues residents ask about most frequently.

-   What services people are unaware of or struggling to find.

-   What concerns are trending in the community at any given time.

A voluntary soapbox feature will allow users to submit a free-form
statement about what matters to them, contributing to the aggregate
signal without tying anything to an individual.

Potential use cases for this data include:

-   Public insight reports summarizing community concerns (published
    periodically).

-   A premium data access tier for municipal governments or civic
    organizations interested in deeper analysis.

-   Research partnerships with local universities or journalism
    organizations.

**11. Success Metrics**

The following metrics will be used to evaluate the pilot:

  ----------------------------------- -----------------------------------
  **Metric**                          **Target / Notes**

  User conversations per month        Growth trend; no fixed target in
                                      pilot

  Hallucination rate                  \< 5% of responses flagged as
                                      inaccurate

  Letter drafts generated             Track volume and completion rate

  Aggregate topic diversity           Breadth of civic topics surfaced

  Repeat usage                        Indicator of value and trust

  Community awareness (qualitative)   User feedback and testimonials
  ----------------------------------- -----------------------------------

**12. Risks & Mitigations**

-   **Hallucination / misinformation:**

```{=html}
<!-- -->
```
-   Mitigation: RAG architecture, source citations, confidence
    thresholds, and prominent disclaimer on site.

```{=html}
<!-- -->
```
-   **Scraping access disrupted:**

```{=html}
<!-- -->
```
-   Mitigation: Monitor scraper health; build direct government
    relationships over time.

```{=html}
<!-- -->
```
-   **API cost overruns:**

```{=html}
<!-- -->
```
-   Mitigation: Usage caps, Haiku-first model strategy, open-source
    model migration path.

```{=html}
<!-- -->
```
-   **Privacy breach:**

```{=html}
<!-- -->
```
-   Mitigation: PII redaction pipeline, no personal data architecture
    from day one.

```{=html}
<!-- -->
```
-   **Political misuse or misrepresentation:**

```{=html}
<!-- -->
```
-   Mitigation: Agent stays strictly informational; no advocacy;
    independent disclaimer.

**13. Roadmap**

**Phase 1 -- Pilot (Town of Babylon)**

-   Build scraper for all Town of Babylon data sources.

-   Set up vector database and RAG pipeline.

-   Build web chat interface with guided entry flow.

-   Implement letter drafting feature with PDF export.

-   Launch anonymized aggregate data logging.

-   Publish site with privacy statement.

**Phase 2 -- Validation & Refinement**

-   Monitor usage and hallucination rates.

-   Gather qualitative feedback from Babylon residents.

-   Refine prompts, guardrails, and knowledge base.

-   Evaluate open-source model alternatives.

-   Publish first community insights report.

**Phase 3 -- Expansion**

-   Expand to additional Long Island municipalities.

-   Explore official government data partnerships.

-   Develop insights dashboard for civic organizations.

-   Evaluate sustainability model (donations, data access tiers).

**14. Open Questions**

-   What is the right cadence for data refreshes from the town website?

-   Should the agent support voice input in a future version?

-   How will the community insights reports be formatted and
    distributed?

-   Should there be any human moderation of the soapbox submissions?

-   What is the sustainability/revenue model once the pilot is
    validated?

*End of Document*
