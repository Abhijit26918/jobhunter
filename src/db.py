"""SQLite schema + helpers. One file, no server."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.models import JobPosting

DB_PATH = Path("data/jobs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT UNIQUE,
    source TEXT, title TEXT, company TEXT, location TEXT,
    remote INTEGER, country TEXT, salary TEXT,
    url TEXT, description TEXT,
    posted_at TEXT, fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_fetched ON jobs(fetched_at);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    score REAL, reasons TEXT, created_at TEXT,
    UNIQUE(job_id)
);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score DESC);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    fit_summary TEXT, tailored_bullets TEXT, cover_letter TEXT,
    model_used TEXT, tokens INTEGER, revisions INTEGER,
    created_at TEXT,
    UNIQUE(job_id)
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    status TEXT DEFAULT 'new',
    applied_at TEXT, notes TEXT, updated_at TEXT,
    UNIQUE(job_id)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_job(conn: sqlite3.Connection, job: JobPosting) -> int | None:
    """INSERT OR IGNORE on fingerprint. Returns the new row id, or None if it was a dup."""
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO jobs
            (fingerprint, source, title, company, location, remote, country,
             salary, url, description, posted_at, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.fingerprint, job.source, job.title, job.company, job.location,
            int(job.remote), job.country, job.salary, job.url, job.description,
            job.posted_at, now(),
        ),
    )
    conn.commit()
    return cur.lastrowid if cur.rowcount else None


def upsert_match(conn: sqlite3.Connection, job_id: int, score: float, reasons: str) -> None:
    conn.execute(
        """
        INSERT INTO matches (job_id, score, reasons, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            score = excluded.score,
            reasons = excluded.reasons,
            created_at = excluded.created_at
        """,
        (job_id, score, reasons, now()),
    )
    conn.commit()


def upsert_draft(
    conn: sqlite3.Connection,
    job_id: int,
    fit_summary: str,
    tailored_bullets: str,
    cover_letter: str,
    model_used: str,
    tokens: int,
    revisions: int,
) -> None:
    conn.execute(
        """
        INSERT INTO drafts
            (job_id, fit_summary, tailored_bullets, cover_letter, model_used,
             tokens, revisions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            fit_summary = excluded.fit_summary,
            tailored_bullets = excluded.tailored_bullets,
            cover_letter = excluded.cover_letter,
            model_used = excluded.model_used,
            tokens = excluded.tokens,
            revisions = excluded.revisions,
            created_at = excluded.created_at
        """,
        (job_id, fit_summary, tailored_bullets, cover_letter, model_used, tokens,
         revisions, now()),
    )
    conn.commit()


def set_status(conn: sqlite3.Connection, job_id: int, status: str, notes: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO applications (job_id, status, applied_at, notes, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            status = excluded.status,
            applied_at = CASE WHEN excluded.status = 'applied' THEN excluded.updated_at
                              ELSE applications.applied_at END,
            notes = COALESCE(excluded.notes, applications.notes),
            updated_at = excluded.updated_at
        """,
        (job_id, status, now() if status == "applied" else None, notes, now()),
    )
    conn.commit()


def top_matches(
    conn: sqlite3.Connection,
    limit: int = 15,
    only_undrafted: bool = False,
    only_unapplied: bool = False,
) -> list[sqlite3.Row]:
    sql = """
        SELECT jobs.*, matches.score, matches.reasons,
               drafts.cover_letter, applications.status
        FROM jobs
        JOIN matches ON matches.job_id = jobs.id
        LEFT JOIN drafts ON drafts.job_id = jobs.id
        LEFT JOIN applications ON applications.job_id = jobs.id
        WHERE 1=1
    """
    if only_undrafted:
        sql += " AND drafts.id IS NULL"
    if only_unapplied:
        sql += " AND (applications.status IS NULL OR applications.status NOT IN ('applied','rejected'))"
    sql += " ORDER BY matches.score DESC LIMIT ?"
    return conn.execute(sql, (limit,)).fetchall()
