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

Replace [`cv.md`](cv.md) with your own CV in plain markdown, and adjust `config.yaml`
(`search.must_have` / `nice_to_have` / `exclude`) to match what you're looking for.

## Run

```bash
python run.py all      # ingest + match: prints your top ranked jobs
```

## Status

Phase 1 (MVP): SQLite + RemoteOK source + CV embedding + ranked-matches CLI. See the
technical spec's build plan (§13) for what's next (more sources, Streamlit review UI,
LLM-tailored drafts, daily digest).
