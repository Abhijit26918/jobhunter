"""Arbeitnow adapter — https://www.arbeitnow.com/api/job-board-api, no key required, paginated."""

from __future__ import annotations

import httpx

from src.models import JobPosting
from src.sources.base import Source, USER_AGENT, TIMEOUT, strip_html

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 5  # cost/time guard — this board has many pages


class Arbeitnow(Source):
    name = "arbeitnow"

    def fetch(self) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        url = API_URL

        for _ in range(MAX_PAGES):
            if not url:
                break
            try:
                resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
                resp.raise_for_status()
                payload = resp.json()
            except Exception as exc:
                print(f"[arbeitnow] fetch failed: {exc}")
                break

            for item in payload.get("data", []):
                try:
                    tags = item.get("tags") or []
                    description = strip_html(item.get("description", ""))
                    if tags:
                        description = f"{description} Tags: {', '.join(tags)}".strip()

                    jobs.append(
                        JobPosting(
                            source=self.name,
                            title=item.get("title", ""),
                            company=item.get("company_name", ""),
                            url=item.get("url", ""),
                            description=description,
                            location=item.get("location", ""),
                            remote=bool(item.get("remote", False)),
                            country="",
                            salary="",
                            posted_at=str(item.get("created_at", "")),
                        )
                    )
                except Exception as exc:
                    print(f"[arbeitnow] skipping malformed item: {exc}")
                    continue

            url = (payload.get("links") or {}).get("next") or None

        return jobs


if __name__ == "__main__":
    fetched = Arbeitnow().fetch()
    print(f"fetched {len(fetched)} jobs")
