# JobHunt Co-Pilot — working agreement

Read `JobHunt_Copilot_TECHNICAL_SPEC.md` for the full design (single source of truth).
`JobHunt_Copilot_Build_Spec.md` is the earlier, higher-level version — defer to the
technical spec where they differ.

- Build one module at a time, in the order in the technical spec's §13 build plan.
- Ask before adding paid dependencies or new frameworks.
- Don't use LangChain/LangGraph outside the tailoring step (`src/tailor.py`).
- Never auto-submit applications. The human always reviews and clicks apply.
- Drafts/tailoring must only use true facts from `cv.md` — never fabricate experience.
- `.env`, `data/`, `.venv/`, `*.db`, `cv.md`, `*.pdf` are gitignored — never commit
  personal data or keys. `cv.example.md` is the public placeholder; real CVs stay local.

## Current state
Phase 1 (MVP) done. Phase 2 (coverage + tracking + UI) done: source adapters for
remoteok/remotive/arbeitnow/jobicy (no key) + adzuna/greenhouse/lever/ashby
(parametrized, disabled until keys/company lists are added), `src/ingest.py`,
`src/tracker.py`, `app.py` (Streamlit Review + Pipeline tabs). Next: Phase 3 —
`src/llm.py` + `src/tailor.py` (LangGraph tailoring agent).
