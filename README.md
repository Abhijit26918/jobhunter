# JobHunt Co-Pilot

A local-first, near-zero-cost agent that aggregates jobs/internships (India + abroad),
scores them against your CV, and drafts tailored applications for you to review and send.

**Co-pilot, not auto-submit.** It finds, scores, and drafts. You review and click apply.

See [`JobHunt_Copilot_TECHNICAL_SPEC.md`](JobHunt_Copilot_TECHNICAL_SPEC.md) for the full
design (data model, sources, the tailoring agent, build plan).

## Setup

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # fill in whatever free API keys you have
```

Copy [`cv.example.md`](cv.example.md) to `cv.md` and replace it with your own CV in
plain markdown (`cv.md` is gitignored — it never gets committed to this public repo).
Adjust `config.yaml` (`search.must_have` / `nice_to_have` / `exclude`) to match what
you're looking for.

## Run

```bash
python run.py all          # ingest + match: prints your top ranked jobs
streamlit run app.py       # Review (mark applied/rejected) + Pipeline tabs
```

## Status

Phase 1 (MVP) + Phase 2 (coverage/tracking/UI) done:
- Sources: RemoteOK, Remotive, Arbeitnow, Jobicy (no key, enabled by default).
  Adzuna, Greenhouse, Lever, Ashby are implemented but disabled until you add a
  free Adzuna key (`.env`) or company board slugs (`config.yaml`).
- `src/tracker.py` — application status tracking + funnel analytics.
- `app.py` — Streamlit Review + Pipeline tabs.

See the technical spec's build plan (§13) for what's next: Phase 3 is the
LangGraph-based tailoring agent (`src/llm.py` + `src/tailor.py`), Phase 4 is the
daily digest + Analytics tab + open-source polish.
