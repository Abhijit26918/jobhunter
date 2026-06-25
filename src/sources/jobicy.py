"""Jobicy adapter — https://jobicy.com/api/v2/remote-jobs, no key required."""

from __future__ import annotations

import httpx

from src.models import JobPosting
from src.sources.base import Source, USER_AGENT, TIMEOUT, strip_html

API_URL = "https://jobicy.com/api/v2/remote-jobs"


class Jobicy(Source):
    name = "jobicy"

    def __init__(self, tag: str = "", count: int = 50):
        self.tag = tag
        self.count = count

    def fetch(self) -> list[JobPosting]:
        params = {"count": self.count}
        if self.tag:
            params["tag"] = self.tag

        try:
            resp = httpx.get(
                API_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[jobicy] fetch failed: {exc}")
            return []

        jobs: list[JobPosting] = []
        for item in data.get("jobs", []):
            try:
                salary_min = item.get("annualSalaryMin")
                salary_max = item.get("annualSalaryMax")
                salary = f"{salary_min}-{salary_max}" if salary_min or salary_max else ""
                description = strip_html(
                    item.get("jobDescription") or item.get("jobExcerpt") or ""
                )

                jobs.append(
                    JobPosting(
                        source=self.name,
                        title=item.get("jobTitle", ""),
                        company=item.get("companyName", ""),
                        url=item.get("url", ""),
                        description=description,
                        location=item.get("jobGeo", ""),
                        remote=True,
                        country="",
                        salary=salary,
                        posted_at=item.get("pubDate", ""),
                    )
                )
            except Exception as exc:
                print(f"[jobicy] skipping malformed item: {exc}")
                continue

        return jobs


if __name__ == "__main__":
    fetched = Jobicy().fetch()
    print(f"fetched {len(fetched)} jobs")
