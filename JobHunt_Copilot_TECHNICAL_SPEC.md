# JobHunt Co-Pilot — Complete Technical Implementation Spec (v1.0)

> **This is the single source of truth for the project.** Hand it to Claude Code in VS Code.
> It covers everything from day 1 to ship: architecture, data model, every module's
> contract, every data source, the LangChain/LangGraph tailoring agent, testing,
> scheduling, and a phase-by-phase plan with acceptance criteria.

---

## 0. How to use this document with Claude Code

1. Put this file in the repo root as `SPEC.md`, and keep a short `CLAUDE.md` that says
   *"Read SPEC.md for the full design. Build in the order in §13. Ask before adding paid
   deps or frameworks. Don't use LangChain/LangGraph outside the tailoring step."*
2. Build **one module at a time, in the order in §13**. For each: ask Claude Code to
   implement it using the contract in §8, then run its tests (§11), then commit.
3. Never let Claude Code generate the whole app in one shot — review every module; you
   must be able to explain this code in interviews.
4. Where this spec references library APIs that change fast (LangChain, LangGraph, exact
   model names/pricing), **verify against current docs at build time**:
   - Claude models/pricing: https://docs.claude.com
   - LangGraph: https://langchain-ai.github.io/langgraph/
   This spec gives the correct *design*; confirm exact import paths/signatures live.

**Current state:** Phase 1 (MVP) modules already exist — `db.py`, `models.py`,
`profile.py`, `match.py`, `sources/base.py`, `sources/remoteok.py`, `run.py`, plus
`config.yaml`, `cv.md`, `requirements.txt`. This spec describes them (so the doc is
self-contained) and fully specs everything still to build.

---

## 1. Product overview & non-negotiable principles

**What it is:** a local-first agent that aggregates jobs/internships (India + abroad),
ranks them against the user's CV, and drafts tailored applications the user reviews and
sends. Shareable: a friend clones, adds their CV + a free API key, and runs it.

**Non-negotiable principles (do not violate):**
1. **Co-pilot, never auto-submit.** The agent finds → scores → drafts. The human reviews
   and clicks apply. No automated form submission, ever. (Protects accounts, avoids ToS
   violations, produces non-spam applications.)
2. **Three-tier cost funnel** so expensive work hits only a tiny slice of data:
   Tier 1 rule filter (free) → Tier 2 local embeddings ranking (free, on-device) →
   Tier 3 LLM tailoring on only the top ~8 matches/day (cheap).
3. **Local-first & portable.** Python + SQLite (one file), config + CV as plain files,
   pluggable LLM provider (bring-your-own-key).
4. **Legal data only.** Official/free APIs + ATS board endpoints. No scraping of sites
   that forbid it; no LinkedIn scraping (use its own email alerts + manual paste).
5. **Honest drafts.** Tailoring prompts must only use true facts from the CV. Never
   fabricate experience.

---

## 2. System architecture

```
SOURCES (adapters)                                            data/jobs.db (SQLite)
  remoteok / remotive / arbeitnow / jobicy / adzuna / ──►  ingest.py  ──►  jobs
  greenhouse / lever / ashby / hackernews / manual            (fetch, normalize, dedup)
                                                                    │
cv.md ──► profile.py (embed CV once)                                │
                                                                    ▼
                                            match.py:  Tier1 rule filter
                                                       Tier2 embedding cosine  ──► matches
                                                       score 0–100
                                                                    │ top N only
                                                                    ▼
                          tailor.py (LangGraph agent):  analyze JD → draft →
                          critique →(revise if weak)→ finalize          ──► drafts
                          (LLM calls via llm.py = LangChain)
                                                                    │
                       ┌────────────────────────────┬──────────────┘
                       ▼                             ▼
            digest.py (daily md/email)     app.py (Streamlit: Review / Pipeline / Analytics)
                                           tracker.py (status transitions, analytics) ──► applications
```

Two distinct subsystems:
- **The pipeline** (ingest → match → review/track) is plain Python.
- **The tailoring agent** (inside `tailor.py`) is the only place LangGraph + LangChain
  are used (see §9).

---

## 3. Tech stack & rationale

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | `int \| None` syntax, modern typing |
| Storage | SQLite via stdlib `sqlite3` | zero setup, single file, portable |
| HTTP | `httpx` | modern, timeouts, can go async later |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | local, free, fast, 384-dim |
| Vector math | `numpy` | cosine via dot product on normalized vectors |
| Config | `pyyaml` | human-editable |
| Review UI | `streamlit` | Python-native, no frontend code |
| LLM layer (v0.3) | `langchain` + provider pkgs | one interface across providers + structured output |
| Agent (v0.3) | `langgraph` | stateful draft→critique→revise loop |
| Env | `python-dotenv` | load API keys from `.env` |
| Tests | `pytest` | per-module unit tests with fixtures |
| Scheduling | cron / Task Scheduler | daily run |

**requirements.txt by phase:**
```
# Phase 1 (MVP) — already in place
httpx>=0.27
sentence-transformers>=3.0
numpy>=1.26
pyyaml>=6.0
# Phase 2
streamlit>=1.36
python-dotenv>=1.0
# Phase 3 (tailoring) — verify current versions at build time
langchain>=0.3
langgraph>=0.2
langchain-anthropic
langchain-google-genai
langchain-groq
langchain-ollama
pydantic>=2
# Dev
pytest>=8
```

---

## 4. Repository layout (final)

```
jobhunt-copilot/
├── SPEC.md                  # this document
├── CLAUDE.md                # short pointer to SPEC.md + working agreement
├── README.md                # setup + run instructions
├── requirements.txt
├── .env.example
├── .gitignore               # data/, .env, .venv/, __pycache__/, *.db
├── config.yaml
├── cv.md
├── data/
│   ├── jobs.db              # gitignored
│   └── digests/             # dated markdown digests
├── tests/
│   ├── fixtures/            # saved sample API responses (JSON)
│   ├── test_models.py
│   ├── test_db.py
│   ├── test_sources.py
│   ├── test_match.py
│   └── test_tailor.py       # uses a fake LLM provider — no API cost
├── src/
│   ├── __init__.py
│   ├── db.py
│   ├── models.py
│   ├── profile.py
│   ├── match.py
│   ├── llm.py               # v0.3 — LangChain provider abstraction
│   ├── tailor.py            # v0.3 — LangGraph reflection loop
│   ├── tracker.py           # v0.2 — status + analytics
│   ├── digest.py            # v0.4 — daily digest
│   ├── ingest.py            # v0.2 — extracted from run.py when sources multiply
│   └── sources/
│       ├── __init__.py
│       ├── base.py
│       ├── remoteok.py
│       ├── remotive.py
│       ├── arbeitnow.py
│       ├── jobicy.py
│       ├── adzuna.py
│       ├── greenhouse.py
│       ├── lever.py
│       ├── ashby.py
│       ├── hackernews.py
│       └── manual.py        # add a single JD by URL
├── app.py                   # v0.2 — Streamlit dashboard
└── run.py                   # CLI: ingest | match | tailor | digest | all
```

`.gitignore` must include `data/`, `.env`, `.venv/`, `__pycache__/`, `*.db` so personal
data and keys never get committed.

---

## 5. Environment & configuration

**`.env.example`** (friends copy to `.env`, fill what they have):
```
# LLM provider for tailoring (v0.3). One of: anthropic | gemini | groq | ollama
LLM_PROVIDER=gemini
LLM_MODEL=               # optional override; sensible default per provider in llm.py
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
GROQ_API_KEY=
# Adzuna (free key) — India + abroad coverage (v0.2)
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
# Email digest (v0.4, optional) — Gmail app password, not your login password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
DIGEST_TO=
```

**`config.yaml`** (full schema):
```yaml
profile:
  cv_path: cv.md

search:
  must_have: [data, machine learning, ml, python, analyst]   # ≥1 must appear
  nice_to_have: [fraud, risk, fintech, sql, pytorch, intern, anomaly, credit, model]
  exclude: [senior, staff, principal, lead, manager, "5+ years", "7+ years", clearance]
  remote_only: true
  max_age_days: 30                 # v0.2: drop stale postings (needs date parsing)
  countries: [in, gb, us, remote]  # used by adzuna + country filter

sources:
  remoteok:   { enabled: true }
  remotive:   { enabled: false }
  arbeitnow:  { enabled: false }
  jobicy:     { enabled: false, tag: data-science }
  adzuna:     { enabled: false, queries: ["data scientist", "data science intern", "fraud analyst"] }
  greenhouse: { enabled: false, boards: [stripe, ramp, plaid, brex] }
  lever:      { enabled: false, companies: [] }
  ashby:      { enabled: false, orgs: [] }
  hackernews: { enabled: false }

match:
  top_n_display: 15
  daily_llm_budget: 8     # Tier-3 cap (tailoring)

tailor:
  max_revisions: 1        # critique→revise loop cap (cost guard)
  min_acceptable_score: 7 # critic's 1–10 threshold to stop revising
```

---

## 6. Data model (SQLite)

`profile.py` produces a **`JobPosting`** (the in-memory contract every source returns):
```
source:str, title:str, company:str, url:str, description:str="", location:str="",
remote:bool=False, country:str="", salary:str="", posted_at:str=""
property fingerprint -> sha256(norm(title)|norm(company)|norm(location))[:16]
```

**Schema** (extend the existing MVP schema with the columns below as phases land):
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT UNIQUE,
    source TEXT, title TEXT, company TEXT, location TEXT,
    remote INTEGER, country TEXT, salary TEXT,
    url TEXT, description TEXT,
    posted_at TEXT, fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_fetched ON jobs(fetched_at);

CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    score REAL, reasons TEXT, created_at TEXT,
    UNIQUE(job_id)
);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score DESC);

CREATE TABLE drafts (                         -- v0.3
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    fit_summary TEXT, tailored_bullets TEXT, cover_letter TEXT,
    model_used TEXT, tokens INTEGER, revisions INTEGER,
    created_at TEXT,
    UNIQUE(job_id)
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    status TEXT DEFAULT 'new',  -- new|reviewing|applied|screen|interview|offer|rejected
    applied_at TEXT, notes TEXT, updated_at TEXT,
    UNIQUE(job_id)
);
```

`db.py` helpers (existing + to add):
- `connect()`, `init_db()`, `now()` — exist.
- `upsert_job(conn, job) -> int|None` — INSERT OR IGNORE on fingerprint; returns new id or None on dup. Exists.
- `upsert_match(conn, job_id, score, reasons)` — ON CONFLICT(job_id) update. Exists.
- **Add:** `upsert_draft(conn, job_id, fit, bullets, cover, model, tokens, revisions)`.
- **Add:** `set_status(conn, job_id, status, notes=None)` — upsert into applications.
- **Add:** `top_matches(conn, limit, only_undrafted=False, only_unapplied=False)` — join jobs+matches(+drafts+applications), order by score desc.

---

## 7. Data sources (adapters)

Every adapter subclasses `Source` (`src/sources/base.py`) and implements
`fetch() -> list[JobPosting]`, returning `[]` on any failure (one dead API must not kill
the run). Register each in the `SOURCES` dict in `run.py`/`ingest.py`. Always send a sane
`User-Agent`, a 30s timeout, and wrap network calls in try/except.

| Source | Endpoint | Key? | Notes / field mapping |
|---|---|---|---|
| **RemoteOK** *(done)* | `https://remoteok.com/api` | no | array; `[0]` is metadata (skip items without `id`). `position`→title, `company`, `url`, `description`(HTML)+`tags`, `location`, `salary_min/max`, `date`. remote=True. |
| **Remotive** | `https://remotive.io/api/remote-jobs` (optional `?search=data`) | no | `jobs[]`: `title`, `company_name`, `url`, `candidate_required_location`→location, `description`(HTML), `salary`, `publication_date`. remote=True. |
| **Arbeitnow** | `https://www.arbeitnow.com/api/job-board-api` | no | `data[]`: `title`, `company_name`, `url`, `description`(HTML), `remote`(bool), `location`, `tags[]`, `created_at`. paginate via `links.next`. |
| **Jobicy** | `https://jobicy.com/api/v2/remote-jobs?count=50&tag=<tag>` | no | `jobs[]`: `jobTitle`, `companyName`, `url`, `jobExcerpt`/`jobDescription`, `jobGeo`→location, `pubDate`, `annualSalaryMin/Max`. remote=True. |
| **Adzuna** | `https://api.adzuna.com/v1/api/jobs/{country}/search/1?app_id=&app_key=&what=&results_per_page=50` | free key | India coverage. `results[]`: `title`, `company.display_name`, `redirect_url`, `description`, `location.display_name`, `created`, `salary_min/max`. country from config (`in`,`gb`,`us`). loop over `queries` × `countries`. |
| **Greenhouse** | `https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true` | no | per target company. `jobs[]`: `title`, `absolute_url`, `location.name`, `content`(HTML, may be escaped). |
| **Lever** | `https://api.lever.co/v0/postings/{company}?mode=json` | no | list: `text`→title, `hostedUrl`, `categories.location`/`.team`, `descriptionPlain`, `createdAt`. |
| **Ashby** | `https://api.ashbyhq.com/posting-api/job-board/{org}` | no | `jobs[]`: `title`, `jobUrl`, `location`, `descriptionPlain`/`descriptionHtml`, `publishedAt`. |
| **HackerNews** | Algolia: find latest "Ask HN: Who is hiring" story, then `https://hn.algolia.com/api/v1/items/{storyId}` | no | `children[]` = postings; `text`(HTML), free-form. Title/company unstructured → store comment as description, title="HN Who is hiring". Advanced/optional. |
| **manual** | n/a | no | `add(url)` fetches a JD page with httpx, strips HTML, stores one JobPosting. For one-off LinkedIn/Internshala finds. |

Each adapter: strip HTML from descriptions (reuse a shared `_strip_html`), normalize whitespace, set `remote`/`country` sensibly, and keep a `__main__` block printing `fetched N jobs` for quick manual testing.

---

## 8. Module specifications

For each: **path · purpose · key functions (signature → behavior) · edge cases · Claude Code prompt.**

### 8.1 `src/models.py` *(done)*
`JobPosting` dataclass (§6) + `_norm()` + `row_to_job(row)->JobPosting`. Fingerprint is the dedup key.

### 8.2 `src/db.py` *(done; extend per §6)*
SQLite schema + helpers. Add `upsert_draft`, `set_status`, `top_matches` in their phases.

### 8.3 `src/profile.py` *(done; extend in v0.2)*
Loads `config.yaml` + `cv.md`, computes `cv_embedding` once (cached model via `lru_cache`), exposes `must_have/nice_to_have/exclude/remote_only` and `embed(text)`. v0.2: also expose `max_age_days`, `countries`.

### 8.4 `src/match.py` *(done; extend in v0.2)*
`_passes_rules(job, profile)->(bool,reason)` then `score_matches(profile)->[(score,job,hits)]`. Score = `max(0,cosine)*100 + 2*nice_hits`, clamped 100. v0.2: add a `max_age_days` rule (parse `posted_at`; if unparseable, keep the job rather than drop it).

### 8.5 `src/sources/*` 
Per §7. **Claude Code prompt (template, repeat per source):**
> "Implement `src/sources/<name>.py`. Subclass `Source` from `base.py`. Fetch `<endpoint>`
> with httpx (30s timeout, custom User-Agent). Map fields as: <mapping from §7>. Strip HTML
> from the description, normalize whitespace, set remote/country. Return `[]` on any
> exception (log a one-line `[<name>] fetch failed: ...`). Add a `__main__` block printing
> the count. Then add a fixture in `tests/fixtures/<name>.json` and a test in
> `tests/test_sources.py` that feeds the fixture through the mapper and asserts the fields."

### 8.6 `src/ingest.py` (v0.2, extracted from run.py)
`run_ingest(config)->int`: iterate enabled sources from config, instantiate via a `SOURCE_REGISTRY`, call `fetch()`, upsert, count new. Per-source try/except. For parametrized sources (adzuna queries/countries, greenhouse boards, lever companies), the adapter reads its own sub-config.

### 8.7 `src/llm.py` (v0.3 — LangChain provider abstraction)
**Purpose:** one interface across providers; structured JSON output.
```
def get_model():                      # reads LLM_PROVIDER/LLM_MODEL from env
    # returns a LangChain chat model: ChatAnthropic | ChatGoogleGenerativeAI
    #         | ChatGroq | ChatOllama, with a sensible default model per provider.
def structured(pydantic_cls):         # model.with_structured_output(pydantic_cls)
def complete(system:str, user:str) -> str   # plain text fallback
```
Default models per provider (override via `LLM_MODEL`; **verify current names at build time**):
anthropic→a Haiku-class model (cheapest Claude), gemini→a Flash model, groq→a Llama model, ollama→`llama3.1`.
**Edge cases:** missing key for the chosen provider → raise a clear error naming the env var. Log token usage from the response metadata when available.

**Claude Code prompt:**
> "Implement `src/llm.py` using LangChain. `get_model()` reads `LLM_PROVIDER` and optional
> `LLM_MODEL` from env and returns the matching LangChain chat model with a cheap default
> model per provider. Add `structured(pydantic_cls)` returning a structured-output runnable,
> and `complete(system,user)` for plain text. Raise a clear error if the required API key is
> missing. Verify current LangChain class names and model strings against the docs first."

### 8.8 `src/tailor.py` (v0.3 — LangGraph reflection agent) — see §9 for full design.

### 8.9 `src/tracker.py` (v0.2)
```
STATUSES = ["new","reviewing","applied","screen","interview","offer","rejected"]
def set_status(job_id, status, notes=None)      # validates status, writes applications
def funnel(conn) -> dict                          # counts per status
def conversion(conn) -> dict                      # applied→screen→interview→offer rates
def by_source(conn) -> list                       # match/apply counts grouped by source
```

### 8.10 `src/digest.py` (v0.4)
```
def build_digest(conn, limit) -> str   # markdown: top undrafted/unapplied matches +
                                       # score + fit_summary + apply link
def write_digest(md) -> Path           # data/digests/YYYY-MM-DD.md
def email_digest(md)                   # optional SMTP send if env configured
```

### 8.11 `app.py` (v0.2 — Streamlit)
Tabs:
- **Review:** `top_matches(only_unapplied=True)`. Per card: title, company, score, `reasons`, JD link; if a draft exists show editable `cover_letter` + bullets; buttons set status (`reviewing`/`applied`/`rejected`). A "Generate draft" button calls `tailor` for that one job (respects budget).
- **Pipeline:** group applications by status (kanban-ish columns).
- **Analytics:** `st.bar_chart` of `funnel()` + conversion rates + `by_source()`.
Run: `streamlit run app.py`. No browser storage; all state in SQLite.

### 8.12 `run.py` (CLI; extend)
`python run.py [ingest|match|tailor|digest|all]`. Already does ingest+match. Add `tailor`
(call the agent on top `daily_llm_budget` undrafted matches) and `digest`.

---

## 9. The tailoring agent (LangChain + LangGraph) — full design

This is the **only** place frameworks are used. Lives in `src/tailor.py`.

**Pydantic output model:**
```python
class TailoredApplication(BaseModel):
    fit_summary: str          # 2–3 lines: why a fit + any gap, honest
    tailored_bullets: list[str]   # 3–4 résumé bullets re-angled from cv.md (true facts only)
    cover_letter: str         # short, specific, no clichés
```

**Graph state (TypedDict):**
```python
class TailorState(TypedDict):
    job: dict          # title, company, description
    cv: str
    jd_points: str     # key requirements extracted from the JD
    draft: TailoredApplication | None
    critique: dict     # {score:int 1–10, issues:str}
    revisions: int
```

**Nodes:**
1. `analyze_jd` — LLM extracts the JD's key requirements into `jd_points`.
2. `draft` — LLM produces a `TailoredApplication` from `cv` + `jd_points` (structured output). **System prompt forbids inventing experience; bullets must derive from `cv.md`.**
3. `critique` — LLM scores the draft 1–10 on specificity, honesty, and JD-fit; returns issues. Increment `revisions`.
4. `finalize` — pass-through; the accepted draft is the output.

**Edges:**
```
START → analyze_jd → draft → critique
critique → (conditional):
    if critique.score < tailor.min_acceptable_score AND revisions < tailor.max_revisions → draft
    else → finalize
finalize → END
```
Build with `StateGraph(TailorState)`, `add_node`, `add_edge`, `add_conditional_edges`,
`compile()`, then `graph.invoke(initial_state)`. **Verify LangGraph's current API** before
coding.

**Public function:**
```python
def tailor_job(job: dict, cv: str, config: dict) -> TailoredApplication
def run_tailoring(config)   # pull top `daily_llm_budget` undrafted matches,
                            # skip any with an existing draft (cache), call tailor_job,
                            # upsert_draft with model_used/tokens/revisions
```

**Why this shape matters (interview story):** the draft→critique→revise loop is the
"reflection" agent pattern; `max_revisions` caps cost; the honesty constraint is enforced
in-prompt; LangChain handles provider + structured parsing so the graph stays clean.

**Claude Code prompt:**
> "Implement `src/tailor.py` as a LangGraph agent. Define the `TailoredApplication`
> Pydantic model and `TailorState` TypedDict from SPEC §9. Build nodes analyze_jd, draft,
> critique, finalize using the model from `llm.py`; the draft node uses structured output
> and a system prompt that forbids fabricating experience. Add the conditional edge from
> critique using `tailor.min_acceptable_score` and `tailor.max_revisions` from config.
> Expose `tailor_job(...)` and `run_tailoring(config)` that caches by job_id and writes via
> `db.upsert_draft`. Verify current LangGraph/LangChain APIs against the docs first. Add a
> test in `tests/test_tailor.py` using a FAKE provider (a stub model returning canned JSON)
> so the test costs nothing and exercises one forced revision."

---

## 10. Cost control

- **Tier 1 (rules):** free string ops; eliminate ~80% before any model runs.
- **Tier 2 (embeddings):** local `all-MiniLM-L6-v2`; zero API cost; cache the CV embedding.
- **Tier 3 (LLM):** only the top `daily_llm_budget` (default 8) **undrafted** matches; draft
  caching (one draft per job, ever); `max_revisions` cap (default 1) on the critique loop;
  log `tokens` + `model_used` per draft. Net cost: free on Ollama / a free tier, or pennies
  on a Haiku-class model.
- Provide a `--dry-run` flag on `run.py tailor` that prints which jobs *would* be drafted
  without calling the model.

---

## 11. Testing strategy

- **No network, no API spend in tests.** Save real API responses once into
  `tests/fixtures/<source>.json`; tests feed fixtures through the mappers.
- `test_models.py` — fingerprint stability + dedup equality; `row_to_job` round-trip.
- `test_db.py` — upsert dedup returns None on dup; match/draft conflict-update; status set.
- `test_sources.py` — each adapter's mapper produces correct `JobPosting` fields from its
  fixture; empty/garbage input → `[]`.
- `test_match.py` — rule filter (must_have/exclude/remote); score ordering with a tiny
  embedding stub or a fixed CV; nice-to-have bonus.
- `test_tailor.py` — **fake LLM provider** (returns canned `TailoredApplication` and a
  critique that fails once then passes) to verify the LangGraph loop revises exactly once
  and finalizes; assert `db.upsert_draft` called with `revisions=1`.
- Run: `pytest -q`. Target: every module has at least one test before it's "done".

---

## 12. Guardrails / legal / ethics

- **Never auto-submit.** No code path posts an application form.
- **APIs over scraping.** Use the §7 endpoints. Don't scrape sites that forbid it; LinkedIn
  via its own email alerts + `manual` adapter only.
- **Rate-limit & be polite:** 30s timeouts, a descriptive User-Agent, don't hammer a board
  (cache results; the daily run is enough).
- **Honesty in drafts** (enforced in the draft system prompt): bullets must be true facts
  from `cv.md`, re-angled — never invented.
- **Privacy when sharing:** `.env`, `data/`, `cv.md` are gitignored; each user supplies
  their own. Never commit anyone's data or keys.

---

## 13. Build plan (day 1 → ship) with acceptance criteria

Assume ~25–35 hrs/week. "DoD" = Definition of Done (must pass before moving on).

### Phase 1 — MVP *(largely done)*  · Days 1–2
- Day 1: repo + venv + `db.py` + `models.py` + `sources/base.py` + `sources/remoteok.py`.
  **DoD:** `python -m src.sources.remoteok` prints a job count; `test_models` + `test_db` pass.
- Day 2: `profile.py` + `match.py` + `run.py`.
  **DoD:** `python run.py all` prints ranked matches; `test_match` passes.

### Phase 2 — Coverage + tracking + UI · Days 3–9
- Day 3–4: `remotive`, `arbeitnow`, `jobicy` adapters + extract `ingest.py` + `SOURCE_REGISTRY`.
  **DoD:** all four sources ingest; dedup across sources verified; `test_sources` passes.
- Day 5: Adzuna adapter (free key, India + abroad, queries×countries) + `.env` loading.
  **DoD:** Adzuna returns India results into the DB.
- Day 6: Greenhouse/Lever/Ashby adapters for a target-company list.
  **DoD:** at least one company board ingests.
- Day 7: `tracker.py` (statuses + analytics) + `db.set_status`/`top_matches`.
  **DoD:** can move a job through statuses; funnel counts compute.
- Day 8–9: `app.py` Streamlit — Review + Pipeline tabs.
  **DoD:** `streamlit run app.py` shows ranked matches; can mark a job applied; persists to DB.

### Phase 3 — The agent (tailoring) · Days 10–16
- Day 10–11: `llm.py` (LangChain provider abstraction) + `.env` provider switch.
  **DoD:** `complete()` works against the user's chosen free provider; missing-key error is clear.
- Day 12–14: `tailor.py` (LangGraph reflection loop) + `db.upsert_draft` + `run.py tailor`.
  **DoD:** top-N undrafted matches get a tailored draft; caching prevents re-draft; budget + max_revisions enforced; `test_tailor` (fake provider) passes.
- Day 15: wire drafts into the Streamlit Review tab (editable, per-job "Generate draft").
  **DoD:** a draft shows under its match and is editable.
- Day 16: `--dry-run` + token logging + cost sanity check.
  **DoD:** dry-run lists would-be drafts without spending.

### Phase 4 — Polish + share · Days 17–21
- Day 17–18: `digest.py` (markdown + optional email) + Analytics tab.
  **DoD:** a dated digest file is produced; analytics charts render.
- Day 19: scheduling (§14) + full `README` + screenshots + `.env.example`.
  **DoD:** a scheduled daily run produces a digest unattended.
- Day 20: end-to-end test on yourself for a day; fix rough edges.
- Day 21: open-source — license, clean history, a short demo video/GIF in the README.
  **DoD:** a friend can clone, add CV + key, and run `python run.py all` from the README alone.

---

## 14. Scheduling & deployment

Local daily run (no server needed). Linux/macOS cron:
```
0 8 * * *  cd /path/to/jobhunt-copilot && .venv/bin/python run.py all && .venv/bin/python run.py tailor && .venv/bin/python run.py digest
```
Windows: Task Scheduler → daily trigger → action `…\.venv\Scripts\python.exe run.py all`
(chain the others, or a small `.bat`). Optional later: a cheap always-on box or a GitHub
Actions scheduled workflow (mind that secrets/keys live in Actions secrets, and the SQLite
file would need to persist as an artifact or move to a hosted DB).

---

## 15. Sharing / open-sourcing checklist

- `.gitignore` covers `data/`, `.env`, `.venv/`, `*.db`, `__pycache__/`.
- `.env.example` + a "bring your own free key" note in the README.
- `cv.md` shipped as a template (not your real one) — or instruct users to replace it.
- A LICENSE (MIT is fine for a portfolio tool).
- README: 60-second setup, the cost-funnel explanation, a screenshot/GIF, the roadmap.
- A short architecture paragraph + the §2 diagram so reviewers grasp it fast.

---

## 16. Stretch ideas (after ship)

- Company-research sub-agent: for top matches, a small tool-using LangGraph node does a web
  lookup and folds a company-specific line into the cover letter.
- Embedding cache for JDs (store vectors) so re-matching is instant at scale.
- A second matcher signal: keyword TF-IDF blended with embeddings.
- Telegram/Slack digest instead of email.
- Multi-CV support (different CV per lane: fraud vs credit vs product DS).

---

## Appendix A — Claude Code prompt library (copy-paste)

- **New source:** see §8.5 template.
- **llm.py:** see §8.7.
- **tailor.py:** see §9.
- **ingest extraction:** "Extract the ingest loop from `run.py` into `src/ingest.py` with a
  `SOURCE_REGISTRY` and `run_ingest(config)->int`. Each source reads its own sub-config.
  Per-source try/except so one failure doesn't abort the run. Update `run.py` to import it."
- **tracker.py:** "Implement `src/tracker.py` per SPEC §8.9: `set_status`, `funnel`,
  `conversion`, `by_source`, plus `db.set_status`/`db.top_matches`. Add `test` for status
  transitions and funnel counts."
- **app.py:** "Implement `app.py` (Streamlit) per SPEC §8.11: Review, Pipeline, Analytics
  tabs reading from SQLite via `db.top_matches`, `tracker.funnel`. No browser storage."
- **digest.py:** "Implement `src/digest.py` per SPEC §8.10: `build_digest`, `write_digest`
  to `data/digests/YYYY-MM-DD.md`, optional `email_digest` via SMTP env vars."

---

*End of spec. Build in §13 order. Verify LangChain/LangGraph/model-name specifics against
current docs at build time. Keep functions small — you'll be defending this in interviews.*
