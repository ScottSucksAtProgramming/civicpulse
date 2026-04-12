# CivicPulse — Data Source Scraping Policy

Last updated: 2026-04-12

This document records the scraping permissions, constraints, and legal basis for each
data source used by CivicPulse. Update this file whenever a new source is added or a
robots.txt is re-reviewed.

---

## Legal Basis

Scraping publicly available government websites for civic, informational, and public-interest
purposes is generally permissible under U.S. law. Key precedents and considerations:

- **hiQ Labs v. LinkedIn (9th Cir. 2022):** Accessing publicly available web data does not
  violate the Computer Fraud and Abuse Act (CFAA).
- **Public domain:** Content published by a U.S. government entity (federal, state, or local)
  is not subject to copyright protection under 17 U.S.C. § 105 (federal works). Municipal
  government documents in New York are similarly treated as public records.
- **Freedom of Information:** Town of Babylon documents, meeting minutes, and agendas are
  public records under New York's Freedom of Information Law (FOIL).

CivicPulse is a non-commercial, public-interest civic tool. No data is resold or used for
advertising. This context supports the permissibility of scraping.

**This is not legal advice.** Re-evaluate if CivicPulse becomes commercial or expands to
jurisdictions with stricter terms of service.

---

## Sources

### 1. townofbabylonny.gov

| Field | Detail |
|-------|--------|
| **Base URL** | https://www.townofbabylonny.gov |
| **robots.txt** | https://www.townofbabylonny.gov/robots.txt |
| **robots.txt reviewed** | 2026-04-12 |
| **Crawl-delay** | None specified for `*`; CivicPulse uses 1s self-imposed |
| **Sitemap** | https://www.townofbabylonny.gov/sitemap.xml |

**Allowed (Phase 1 targets):**

| Path | Content |
|------|---------|
| `/AgendaCenter` | All board agendas and minutes |
| `/AgendaCenter/Town-Board-4` | Town Board agendas and minutes |
| `/459/Upcoming-Public-Meetings` | Upcoming meeting schedule |
| `/123/Planning-Board` | Planning Board |
| `/115/Town-Council` | Town Council |
| `/8/Departments` | All departments index |
| `/147/Planning-Development` | Planning & Development |
| `/152/Town-Clerks-Office` | Town Clerk's Office |
| `/243/Forms-Documents` | Forms and Documents Center |
| `/392/Freedom-of-Information-Law` | FOIL resources |

**Disallowed (do not scrape):**

| Path(s) | Reason |
|---------|--------|
| `/admin`, `/activedit`, `/common/admin/`, `/OJA` | Admin interfaces |
| `/support`, `/Support` | Support pages |
| `/Search`, `/search.asp`, `/search.aspx`, `/Search.asp`, `/Search.aspx` | Search endpoints |
| `/currentevents.aspx`, `/CurrentEvents.aspx`, `/currenteventsview.asp(x)` | Old ASP event pages |
| `/map.asp`, `/map.aspx`, `/Map.asp`, `/Map.aspx` | Map pages |
| `/RSS.aspx` | RSS feed |

**Full robots.txt:** See `src/civicpulse/scraper/SCRAPING_NOTES.md`

---

### 2. eCode360 (ecode360.com)

| Field | Detail |
|-------|--------|
| **URLs** | https://ecode360.com/BA0924 (Town Code), https://ecode360.com/6810323 (Zoning) |
| **robots.txt** | https://ecode360.com/robots.txt |
| **robots.txt reviewed** | Not yet — Phase 4 task |
| **Phase** | Phase 4 |

**Status:** robots.txt and terms of service review required before scraping begins.
See `todo.taskpaper` → Phase 4 → "Review eCode360 robots.txt and access constraints."

---

### 3. YouTube Data API (Town of Babylon channel)

| Field | Detail |
|-------|--------|
| **Access method** | YouTube Data API v3 only — no direct video or page scraping |
| **API docs** | https://developers.google.com/youtube/v3 |
| **Credentials** | API key required — see Phase 4 setup task |
| **Phase** | Phase 4 |

**Constraints:**
- Direct scraping of YouTube pages or video files is **prohibited** by YouTube's Terms of Service.
- Access captions only via the `captions` resource of the Data API.
- Auto-generated captions (`trackKind: asr`) are the primary source for meeting transcripts.
- Respect YouTube Data API quota limits (10,000 units/day on free tier).

**Status:** API credentials not yet set up. See `todo.taskpaper` → Phase 4.

---

## Scraping Standards (all sources)

- **Rate limiting:** Minimum 1-second delay between requests (`SCRAPER_DELAY_SECONDS`)
- **User agent:** `CivicPulse/0.1 (civic research)` (`SCRAPER_USER_AGENT`)
- **robots.txt:** Parsed and enforced before any URL is fetched
- **Re-review cadence:** Re-check robots.txt for each source annually or before any new
  scraping target is added
- **On access denial:** If a source returns 403 or blocks the user agent, stop immediately
  and document in `SCRAPING_NOTES.md` — do not attempt to circumvent
