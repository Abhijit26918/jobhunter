"""JobPosting dataclass — the in-memory contract every source adapter returns."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


def _norm(s: str) -> str:
    """Lowercase, collapse whitespace, strip — for stable fingerprint inputs."""
    return re.sub(r"\s+", " ", s or "").strip().lower()


@dataclass
class JobPosting:
    source: str
    title: str
    company: str
    url: str
    description: str = ""
    location: str = ""
    remote: bool = False
    country: str = ""
    salary: str = ""
    posted_at: str = ""

    @property
    def fingerprint(self) -> str:
        key = f"{_norm(self.title)}|{_norm(self.company)}|{_norm(self.location)}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def row_to_job(row) -> JobPosting:
    """Map a sqlite3.Row (or tuple matching the jobs table column order) back to a JobPosting."""
    return JobPosting(
        source=row["source"],
        title=row["title"],
        company=row["company"],
        url=row["url"],
        description=row["description"] or "",
        location=row["location"] or "",
        remote=bool(row["remote"]),
        country=row["country"] or "",
        salary=row["salary"] or "",
        posted_at=row["posted_at"] or "",
    )
