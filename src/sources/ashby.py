"""Ashby adapter — https://api.ashbyhq.com/posting-api/job-board/{org}, no key, per target org."""

from __future__ import annotations

import httpx

from src.models import JobPosting
from src.sources.base import Source, USER_AGENT, TIMEOUT, strip_html

API_URL_TEMPLATE = "https://api.ashbyhq.com/posting-api/job-board/{org}"


class Ashby(Source):
    name = "ashby"

    def __init__(self, orgs: list[str]):
        self.orgs = orgs

    def fetch(self) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        for org in self.orgs:
            try:
                resp = httpx.get(
                    API_URL_TEMPLATE.format(org=org),
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                print(f"[ashby] fetch failed for org={org}: {exc}")
                continue

            for item in data.get("jobs", []):
                try:
                    description = strip_html(
                        item.get("descriptionPlain") or item.get("descriptionHtml") or ""
                    )
                    jobs.append(
                        JobPosting(
                            source=self.name,
                            title=item.get("title", ""),
                            company=org,
                            url=item.get("jobUrl", ""),
                            description=description,
                            location=item.get("location", ""),
                            remote=False,
                            country="",
                            salary="",
                            posted_at=item.get("publishedAt", ""),
                        )
                    )
                except Exception as exc:
                    print(f"[ashby] skipping malformed item: {exc}")
                    continue

        return jobs


if __name__ == "__main__":
    fetched = Ashby(orgs=["ramp"]).fetch()
    print(f"fetched {len(fetched)} jobs")
