"""The funnel: Tier 1 free rule filter, Tier 2 free local-embedding score."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import numpy as np

from src import db
from src.profile import Profile, embed


def _passes_rules(job: sqlite3.Row, profile: Profile) -> tuple[bool, str]:
    text = f"{job['title']} {job['description']}".lower()

    if profile.remote_only and not job["remote"]:
        return False, "not remote"

    if profile.must_have and not any(k in text for k in profile.must_have):
        return False, "missing must-have keyword"

    for k in profile.exclude:
        if k in text:
            return False, f"excluded keyword: {k}"

    posted_at = job["posted_at"]
    if posted_at:
        try:
            posted = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - posted).days
            if age_days > profile.max_age_days:
                return False, f"stale ({age_days}d old)"
        except (ValueError, TypeError):
            pass  # unparseable date -> keep the job rather than drop it

    return True, ""


def score_matches(conn: sqlite3.Connection, profile: Profile) -> list[tuple[float, sqlite3.Row, str]]:
    """Score every job currently in the jobs table. Returns (score, job_row, reasons) sorted desc."""
    jobs = conn.execute("SELECT * FROM jobs").fetchall()
    results: list[tuple[float, sqlite3.Row, str]] = []

    for job in jobs:
        passed, reason = _passes_rules(job, profile)
        if not passed:
            continue

        text = f"{job['title']} {job['description']}"
        job_embedding = embed(text)
        cosine = float(np.dot(profile.cv_embedding, job_embedding))

        text_lower = text.lower()
        nice_hits = [k for k in profile.nice_to_have if k in text_lower]

        score = min(100.0, max(0.0, cosine) * 100 + 2 * len(nice_hits))
        reasons = f"cosine={cosine:.2f}; nice_hits={','.join(nice_hits) if nice_hits else 'none'}"
        results.append((score, job, reasons))

    results.sort(key=lambda r: r[0], reverse=True)
    return results


def run_match(conn: sqlite3.Connection, profile: Profile) -> int:
    """Score all jobs and upsert into the matches table. Returns count of matches written."""
    results = score_matches(conn, profile)
    for score, job, reasons in results:
        db.upsert_match(conn, job["id"], score, reasons)
    return len(results)
