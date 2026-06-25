"""Application status tracking + funnel analytics."""

from __future__ import annotations

import sqlite3

from src import db

STATUSES = ["new", "reviewing", "applied", "screen", "interview", "offer", "rejected"]


def set_status(conn: sqlite3.Connection, job_id: int, status: str, notes: str | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"invalid status: {status!r}, must be one of {STATUSES}")
    db.set_status(conn, job_id, status, notes)


def funnel(conn: sqlite3.Connection) -> dict[str, int]:
    """Count of applications currently in each status."""
    counts = {status: 0 for status in STATUSES}
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM applications GROUP BY status").fetchall()
    for row in rows:
        if row["status"] in counts:
            counts[row["status"]] = row["n"]
    return counts


def conversion(conn: sqlite3.Connection) -> dict[str, float]:
    """Step-to-step conversion rates, assuming each status implies having passed prior ones."""
    counts = funnel(conn)
    applied = counts["applied"] + counts["screen"] + counts["interview"] + counts["offer"]
    screen = counts["screen"] + counts["interview"] + counts["offer"]
    interview = counts["interview"] + counts["offer"]
    offer = counts["offer"]

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator * 100, 1) if denominator else 0.0

    return {
        "applied_to_screen": rate(screen, applied),
        "screen_to_interview": rate(interview, screen),
        "interview_to_offer": rate(offer, interview),
    }


def by_source(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Match and apply counts grouped by job source."""
    return conn.execute(
        """
        SELECT jobs.source AS source,
               COUNT(DISTINCT matches.job_id) AS matched,
               COUNT(DISTINCT CASE WHEN applications.status IN ('applied','screen','interview','offer')
                                    THEN applications.job_id END) AS applied
        FROM jobs
        LEFT JOIN matches ON matches.job_id = jobs.id
        LEFT JOIN applications ON applications.job_id = jobs.id
        GROUP BY jobs.source
        ORDER BY matched DESC
        """
    ).fetchall()
