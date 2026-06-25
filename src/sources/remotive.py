"""Remotive adapter — https://remotive.io/api/remote-jobs, no key required."""

from __future__ import annotations

import httpx

from src.models import JobPosting
from src.sources.base import Source, USER_AGENT, TIMEOUT, strip_html

API_URL = "https://remotive.io/api/remote-jobs"


class Remotive(Source):
    name = "remotive"

    def fetch(self) -> list[JobPosting]:
        try:
            resp = httpx.get(
                API_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[remotive] fetch failed: {exc}")
            return []

        jobs: list[JobPosting] = []
        for item in data.get("jobs", []):
            try:
                jobs.append(
                    JobPosting(
                        source=self.name,
                        title=item.get("title", ""),
                        company=item.get("company_name", ""),
                        url=item.get("url", ""),
                        description=strip_html(item.get("description", "")),
                        location=item.get("candidate_required_location", ""),
                        remote=True,
                        country="",
                        salary=item.get("salary", "") or "",
                        posted_at=item.get("publication_date", ""),
                    )
                )
            except Exception as exc:
                print(f"[remotive] skipping malformed item: {exc}")
                continue

        return jobs


if __name__ == "__main__":
    fetched = Remotive().fetch()
    print(f"fetched {len(fetched)} jobs")
