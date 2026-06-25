"""Lever adapter — https://api.lever.co/v0/postings/{company}?mode=json, no key, per target company."""

from __future__ import annotations

import httpx

from src.models import JobPosting
from src.sources.base import Source, USER_AGENT, TIMEOUT, strip_html

API_URL_TEMPLATE = "https://api.lever.co/v0/postings/{company}"


class Lever(Source):
    name = "lever"

    def __init__(self, companies: list[str]):
        self.companies = companies

    def fetch(self) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        for company in self.companies:
            try:
                resp = httpx.get(
                    API_URL_TEMPLATE.format(company=company),
                    params={"mode": "json"},
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                print(f"[lever] fetch failed for company={company}: {exc}")
                continue

            for item in data:
                try:
                    categories = item.get("categories") or {}
                    jobs.append(
                        JobPosting(
                            source=self.name,
                            title=item.get("text", ""),
                            company=company,
                            url=item.get("hostedUrl", ""),
                            description=strip_html(item.get("descriptionPlain", "")),
                            location=categories.get("location", ""),
                            remote=False,
                            country="",
                            salary="",
                            posted_at=str(item.get("createdAt", "")),
                        )
                    )
                except Exception as exc:
                    print(f"[lever] skipping malformed item: {exc}")
                    continue

        return jobs


if __name__ == "__main__":
    fetched = Lever(companies=["netflix"]).fetch()
    print(f"fetched {len(fetched)} jobs")
