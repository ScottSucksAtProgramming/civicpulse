# Scraping Notes — townofbabylonny.gov

## robots.txt Review

- **Review date:** 2026-04-12
- **robots.txt URL:** https://www.townofbabylonny.gov/robots.txt
- **Sitemap:** https://www.townofbabylonny.gov/sitemap.xml

### Full robots.txt (verbatim)

```
user-agent: Baiduspider
Disallow: /

User-agent: Yandex
Disallow: /

User-agent: *
Disallow: /activedit
Disallow: /admin
Disallow: /common/admin/
Disallow: /OJA
Disallow: /support
Disallow: /currenteventsview.asp
Disallow: /search.asp
Disallow: /currenteventsview.aspx
Disallow: /search.aspx
Disallow: /currentevents.aspx
Disallow: /Support
Disallow: /CurrentEventsView.asp
Disallow: /Search.asp
Disallow: /CurrentEventsView.aspx
Disallow: /Search.aspx
Disallow: /Search
Disallow: /CurrentEvents.aspx
Disallow: /Currentevents.aspx
Disallow: /map.aspx
Disallow: /map.asp
Disallow: /Map.aspx
Disallow: /Map.asp
Sitemap: /sitemap.xml
Disallow: /RSS.aspx

User-agent: Siteimprove
Crawl-delay: 20

User-agent: Siteimprovebot
Crawl-delay: 20

User-agent: Siteimprovebot-crawler
Crawl-delay: 20
```

### Disallowed paths (for `User-agent: *`)

| Path | Notes |
|------|-------|
| `/activedit`, `/admin`, `/common/admin/`, `/OJA` | Admin interfaces — irrelevant to CivicPulse |
| `/support`, `/Support` | Support pages — irrelevant |
| `/search.asp`, `/search.aspx`, `/Search.asp`, `/Search.aspx`, `/Search` | Search endpoints — we scrape pages directly, not search results |
| `/currenteventsview.asp(x)`, `/currentevents.aspx`, `/CurrentEvents.aspx` | Old ASP/ASPX event pages — not our target URL format |
| `/map.asp(x)`, `/Map.asp(x)` | Map pages — irrelevant |
| `/RSS.aspx` | RSS feed — irrelevant |

### Phase 1 target URL clearance

All Phase 1 scraping targets use path formats not listed in `Disallow`. **All clear to scrape.**

| Target | URL pattern | Allowed? |
|--------|-------------|----------|
| Main site pages | `/` (general) | ✅ |
| Agenda Center | `/AgendaCenter` | ✅ |
| Town Board agendas/minutes | `/AgendaCenter/Town-Board-4` | ✅ |
| Upcoming Public Meetings | `/459/Upcoming-Public-Meetings` | ✅ |
| Planning Board | `/123/Planning-Board` | ✅ |
| Town Council | `/115/Town-Council` | ✅ |
| All Departments | `/8/Departments` | ✅ |
| Planning & Development | `/147/Planning-Development` | ✅ |
| Town Clerk's Office | `/152/Town-Clerks-Office` | ✅ |
| Forms & Documents | `/243/Forms-Documents` | ✅ |
| FOIL | `/392/Freedom-of-Information-Law` | ✅ |

### Crawl-delay

No `Crawl-delay` directive is set for `User-agent: *`. CivicPulse will apply its own
**1-second minimum delay** between requests (configurable via `SCRAPER_DELAY_SECONDS`).

---

## Rate Limiting Policy

- Default delay between requests: 1.0 second (configurable via `SCRAPER_DELAY_SECONDS`)
- User agent: `CivicPulse/0.1 (civic research)`

---

## Additional Notes

- The sitemap at `/sitemap.xml` may be useful for discovering all indexable URLs — worth
  fetching before building individual scrapers to confirm path structures.
- No `Crawl-delay` for general bots; Siteimprove bots are throttled to 20s, indicating the
  server can handle moderate crawl rates fine.
- No `Allow` rules; all paths not listed in `Disallow` are implicitly permitted.
