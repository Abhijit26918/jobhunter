# JobHunt Co-Pilot — Build Spec

**A local-first, near-zero-cost agent that aggregates jobs/internships (India + abroad), scores them against your CV, and drafts tailored applications for you to review and send.**

Built in **VS Code with Claude Code**. Designed to be shared: a friend clones the repo, drops in their own CV + a free API key, and it works.

---

## 0. Design principles (read once, they explain everything)

1. **Co-pilot, not auto-submit.** The agent *finds, scores, and drafts*. You review and click apply. This avoids ToS violations + account bans and produces genuinely tailored applications, not detectable spam.
2. **Three-tier cost funnel.** Expensive work only happens on a tiny slice of data:
   - Tier 1 — **Rule filters** (free): keyword/location/seniority/freshness. Kills 80% of noise.
   - Tier 2 — **Local embeddings** (free): rank survivors by similarity to your CV. Runs on your laptop, no API.
   - Tier 3 — **LLM tailoring** (cheap): only the top ~5–10 matches/day get an LLM call for fit analysis + tailored bullets + cover letter.
3. **Local-first & portable.** Python + **SQLite** (one file, no server). Config + CV are plain files. Pluggable LLM provider so anyone uses whatever free key they have.
4. **Legal data only.** Official/free APIs (RemoteOK, Remotive, Adzuna, etc.) + ATS board JSON endpoints. No fragile HTML scraping of sites that forbid it; no LinkedIn scraping (use saved-search email alerts there instead).

---

## 1. Tech stack (all free / near-free)

| Layer | Choice | Why | Cost |
|---|---|---|---|
| Language | **Python 3.11+** | You know it | free |
| Storage | **SQLite** | Zero setup, single file, perfect for sharing | free |
| Job data | RemoteOK, Remotive, Arbeitnow, Jobicy, Himalayas, Adzuna, HN Who's Hiring, Greenhouse/Lever/Ashby boards | Mix of no-key + free-key APIs | free |
| Matching | **sentence-transformers** (`all-MiniLM-L6-v2`) | Local embeddings, no API cost | free |
| LLM tailoring | **Pluggable**: Claude Haiku / Gemini Flash (free tier) / Groq (free) / Ollama (local) | Cheap or free | ~₹0–few ₹/day |
| Config | **YAML** + `.env` | Easy for friends to edit | free |
| Review UI | **Streamlit** | Python-native dashboard, no frontend work | free |
| HTTP | `httpx` | Modern, async-capable | free |
| Build tool | **Claude Code in VS Code** | Scaffolds + writes modules from this spec | — |

---

## 2. Job data sources (your aggregation layer)

**No API key needed (start here):**
- **RemoteOK** — `https://remoteok.com/api` → JSON array, free. (First element is metadata; skip it.)
- **Remotive** — `https://remotive.io/api/remote-jobs?category=software-dev` (also `data` category). Free; optional email-generated key.
- **Arbeitnow** — `https://www.arbeitnow.com/api/job-board-api` — free, paginated.
- **Jobicy** — `https://jobicy.com/api/v2/remote-jobs?count=50&tag=data-science` — free.
- **Himalayas** — free remote-jobs API, search by keyword/country/seniority.
- **Hacker News "Who is Hiring"** — via Algolia API `https://hn.algolia.com/api/v1/search?tags=comment,story_<id>` — free; great for startups.

**Free key (add in week 2 for India + abroad coverage):**
- **Adzuna** — register for free app_id + app_key. Endpoint pattern: `https://api.adzuna.com/v1/api/jobs/in/search/1?app_id=...&app_key=...&what=data%20scientist`. Country code `in` = India, `gb`/`us` for abroad. Excellent India coverage.

**Targeted-company boards (no key, high signal):**
- **Greenhouse:** `https://boards-api.greenhouse.io/v1/boards/{company}/jobs`
- **Lever:** `https://api.lever.co/v0/postings/{company}?mode=json`
- **Ashby:** `https://api.ashbyhq.com/posting-api/job-board/{company}`
- Keep a list of fintech companies you want (Razorpay, CRED, Stripe, Navi, …) and poll their boards directly. This is your highest-quality source.

**Manual-paste fallback:** a CLI command `add-job <url>` that fetches a JD page and adds it, for one-off LinkedIn/Internshala listings you find by hand.

---

## 3. Architecture

```
                 ┌─────────────────────────────────────────┐
   SOURCES  ───► │ ingest.py  (fetch all → normalize → dedup)│ ──► SQLite: jobs
                 └─────────────────────────────────────────┘
                                    │
   cv.md ──► profile.py (embed CV)  │
                                    ▼
                 ┌─────────────────────────────────────────┐
                 │ match.py  Tier1 rule filter → Tier2 embed │ ──► SQLite: matches
                 │           similarity → score 0–100        │
                 └─────────────────────────────────────────┘
                                    │ top N only
                                    ▼
                 ┌─────────────────────────────────────────┐
                 │ tailor.py  Tier3 LLM: fit analysis +      │ ──► SQLite: drafts
                 │            tailored bullets + cover letter │
                 └─────────────────────────────────────────┘
                                    │
              ┌─────────────────────┴────────────────────┐
              ▼                                           ▼
   digest.py (daily markdown/email)        app.py  Streamlit review dashboard
                                           (read → edit draft → mark applied →
                                            funnel analytics)   ──► SQLite: applications
```

### File structure
```
jobhunt-copilot/
├── README.md
├── CLAUDE.md                # project context for Claude Code (see §7)
├── requirements.txt
├── .env.example             # API keys template
├── config.yaml              # search prefs, sources, model provider
├── cv.md                    # YOUR resume in plain text/markdown
├── data/
│   └── jobs.db              # SQLite (gitignored)
├── src/
│   ├── db.py                # schema + helpers
│   ├── models.py            # JobPosting dataclass
│   ├── llm.py               # provider abstraction (Claude/Gemini/Groq/Ollama)
│   ├── profile.py           # load + embed CV, preferences
│   ├── ingest.py            # orchestrate sources → dedup → store
│   ├── match.py             # rule filter + embedding score
│   ├── tailor.py            # LLM draft generation (top-N only)
│   ├── tracker.py           # application status + analytics
│   ├── digest.py            # daily digest generator
│   └── sources/
│       ├── base.py          # Source interface: fetch() -> list[JobPosting]
│       ├── remoteok.py
│       ├── remotive.py
│       ├── arbeitnow.py
│       ├── adzuna.py
│       ├── greenhouse.py    # parametrized by company
│       └── hackernews.py
├── app.py                   # Streamlit dashboard
└── run.py                   # CLI entrypoint (ingest|match|tailor|digest)
```

---

## 4. Data model (SQLite schema)

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT UNIQUE,        -- hash(title+company+location) for dedup
    source TEXT, title TEXT, company TEXT, location TEXT,
    remote INTEGER, country TEXT, salary TEXT,
    url TEXT, description TEXT,
    posted_at TEXT, fetched_at TEXT
);

CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    score REAL,                     -- 0–100
    rule_passed INTEGER,
    reasons TEXT,                   -- short why-it-matched
    created_at TEXT,
    UNIQUE(job_id)
);

CREATE TABLE drafts (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    fit_summary TEXT,
    tailored_bullets TEXT,
    cover_letter TEXT,
    model_used TEXT, tokens INTEGER,
    created_at TEXT,
    UNIQUE(job_id)
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    status TEXT DEFAULT 'new',      -- new|reviewing|applied|screen|interview|offer|rejected
    applied_at TEXT, notes TEXT, updated_at TEXT,
    UNIQUE(job_id)
);
```

---

## 5. Module specs (what to ask Claude Code to build, in order)

### `models.py` — `JobPosting` dataclass
Fields matching the `jobs` table. Add a `.fingerprint()` method (hash of normalized title+company+location) so every source produces dedup-able records.

### `sources/base.py` — Source interface
Abstract `Source` with `name` and `fetch() -> list[JobPosting]`. Every adapter subclasses this and maps that API's JSON into `JobPosting`. **This is the extensibility win:** adding a new job board = one new file.

### `ingest.py`
Loop enabled sources from `config.yaml`, call `.fetch()`, catch per-source errors (one dead API shouldn't kill the run), dedup by fingerprint, upsert into `jobs`. Log counts per source.

### `profile.py`
Load `cv.md`, compute its embedding once and cache it. Hold the user's keyword/location preferences from config. Expose `cv_embedding` and `must_have` / `nice_to_have` / `exclude` keyword lists.

### `match.py` — the funnel
- **Tier 1 rule filter:** drop jobs failing must-haves (e.g. not remote when remote required, missing core keywords, wrong seniority, older than N days, contains exclude words like "senior"/"5+ years"). Cheap string ops.
- **Tier 2 embedding score:** embed each surviving JD, cosine-similarity vs `cv_embedding`, scale to 0–100. Optionally blend in a keyword-overlap bonus. Store top results in `matches` with a short `reasons` string.

### `llm.py` — provider abstraction
Single function `complete(prompt: str, system: str = "") -> str`. Read `LLM_PROVIDER` from `.env` and route to:
- `anthropic` (Claude Haiku — cheap),
- `gemini` (Flash — generous free tier),
- `groq` (free, fast),
- `ollama` (fully local, ₹0).
Friends pick whatever they have a key for. Keep prompts provider-agnostic.

### `tailor.py` — Tier 3 (cost-guarded)
For the **top N** matches (config: `daily_llm_budget: 8`) that don't already have a draft:
- One LLM call returns JSON with: `fit_summary` (2–3 lines: why you fit + any gap), `tailored_bullets` (3–4 resume bullets rewritten for this JD using only true facts from `cv.md`), `cover_letter` (short, specific, no clichés).
- **Guardrails:** cache by `job_id` (never re-draft), hard daily cap, log token use. This is what keeps cost near zero.
- **Honesty rule baked into the prompt:** only use real facts from the CV; never fabricate experience.

### `tracker.py`
Move applications through statuses; compute funnel analytics (applied → screen → interview → offer rates, response time, best-performing sources/keywords). This analytics layer is gold for interviews ("I A/B-tested my own job search").

### `digest.py`
Generate a daily markdown digest: top matches, scores, fit summaries, links to draft + apply. Optional: send via email (SMTP / a free service). Run via cron / Task Scheduler.

### `app.py` — Streamlit review dashboard
Tabs: **Review** (cards: score, why, JD link, editable draft, "Mark applied" button) · **Pipeline** (kanban of statuses) · **Analytics** (funnel charts). This is the daily-driver UI and a great demo screenshot for your portfolio.

### `run.py` — CLI
`python run.py ingest|match|tailor|digest|all` so the whole pipeline runs with one command (and cron-able).

---

## 6. Build sequence (ship something usable each week)

**MVP — Weekend 1 (prove the core loop):**
`db.py` + `models.py` + `sources/remoteok.py` + `profile.py` + `match.py` + a CLI that prints ranked matches.
→ *End state:* run one command, see your top 10 matching remote jobs in the terminal. **Already useful.**

**v0.2 — Week 2 (coverage + tracking + UI):**
Add Remotive/Arbeitnow/Adzuna + Greenhouse for target companies · dedup · `tracker.py` · basic Streamlit Review tab.
→ *End state:* dozens of fresh matches daily, reviewable in a browser, status tracking.

**v0.3 — Week 3 (the "agent" brain):**
`llm.py` + `tailor.py` with the cost funnel + draft caching.
→ *End state:* top matches come with a tailored cover letter + bullets you edit and send. **Now it's genuinely an agent.**

**v0.4 — Week 4 (polish + share):**
`digest.py` + email + Analytics tab + clean `README` + `.env.example` + `config.yaml` defaults + screenshots.
→ *End state:* a friend clones, adds CV + free key, runs `python run.py all`. Open-source it. Portfolio piece complete.

---

## 7. How to build it in VS Code with Claude Code

1. **Scaffold:** create the repo, open in VS Code, start Claude Code. Paste this spec (or keep this file in the repo) and ask it to scaffold the file structure + `requirements.txt` + `.env.example`.
2. **Add a `CLAUDE.md`** at repo root with project context — Claude Code reads it automatically so you don't re-explain each session. Put in it: the design principles (§0), the stack (§1), the schema (§4), and "build incrementally, ask before adding paid dependencies."
3. **Build module by module**, lowest-dependency first (`db` → `models` → `sources/base` → one source → `profile` → `match`). Test each before moving on. Don't let it generate the whole app at once — review as you go (you'll learn more and catch mistakes).
4. **Verify current Claude Code setup/commands** at the official docs (install, MCP, config), since details change: https://docs.claude.com/en/docs/claude-code/overview

**Example prompts to paste into Claude Code:**
> "Implement `src/sources/remoteok.py`. Subclass the `Source` base in `base.py`. Fetch `https://remoteok.com/api` with httpx, skip the first metadata element, map each item into a `JobPosting`, set `remote=True`. Handle network errors gracefully and return `[]` on failure. Add a `__main__` block that prints how many jobs were fetched."

> "Implement `match.py`. Tier-1 rule filter using must_have/exclude keywords and a max-age in days from config. Tier-2: embed each surviving JD with the cached model from profile.py, cosine-similarity vs cv_embedding, scale 0–100, write to the matches table. Keep embedding model loaded once."

> "Implement `tailor.py`. Pull the top `daily_llm_budget` matches without an existing draft, call `llm.complete` once each with a prompt that returns strict JSON {fit_summary, tailored_bullets, cover_letter}. Only use facts present in cv.md. Cache by job_id, never re-draft, log token usage."

---

## 8. Guardrails (keep it legal, cheap, and good)

- **Never auto-submit.** Human reviews every application. (Also dodges ToS/CAPTCHA hell.)
- **APIs over scraping.** Use the listed APIs/ATS endpoints. Don't scrape sites that forbid it; for LinkedIn use its own email job alerts and the manual-paste command.
- **Rate-limit & cache** every source; respect `robots.txt`; identify a sane User-Agent.
- **Cost caps:** daily LLM budget, draft caching, free embeddings. Log spend so there are no surprises.
- **Honesty in drafts:** prompt forbids inventing experience. A tailored bullet must be a true fact from your CV, re-angled — not a fabrication.
- **Privacy when sharing:** CV and `.env` are gitignored; friends supply their own.

---

## 9. Cost reality

- **₹0 path:** free APIs + local embeddings + **Ollama** or a **free LLM tier** (Gemini Flash / Groq) for tailoring. Genuinely free.
- **Pennies path:** Claude **Haiku** for tailoring on ~8 jobs/day → tiny cost; sharpest drafts. Check current model pricing at https://docs.claude.com/en/docs/about-claude/pricing before committing.
- The funnel means you *never* pay to look at the 80% of jobs that don't fit.

---

## 10. Why this doubles as a portfolio weapon

When you interview, this single repo lets you talk about: agent design, RAG/embeddings, a cost-optimization funnel, multi-source data engineering + dedup, a pluggable LLM abstraction, an analytics layer on your own funnel, and product judgment (co-pilot vs auto-submit). That's a *systems* story most students can't tell. Put a demo video + the analytics screenshot in the README.

---

### Immediate next step
Set up the empty repo + `CLAUDE.md`, then build the **MVP (Weekend 1)**: SQLite + RemoteOK source + CV embedding + ranked-matches CLI. Want me to write the starter `CLAUDE.md`, `config.yaml`, `requirements.txt`, and the `db.py` + `models.py` + first source so you can paste them straight into VS Code and start?
