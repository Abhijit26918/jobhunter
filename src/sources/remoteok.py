"""RemoteOK adapter — https://remoteok.com/api, no key required."""

from __future__ import annotations

import httpx

from src.models import JobPosting
from src.sources.base import Source, USER_AGENT, TIMEOUT, strip_html

API_URL = "https://remoteok.com/api"


class RemoteOK(Source):
    name = "remoteok"

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
            print(f"[remoteok] fetch failed: {exc}")
            return []

        jobs: list[JobPosting] = []
        for item in data:
            if not item.get("id"):
                continue  # first element is metadata
            try:
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                salary = f"{salary_min}-{salary_max}" if salary_min or salary_max else ""
                description = strip_html(item.get("description", ""))
                tags = item.get("tags") or []
                if tags:
                    description = f"{description} Tags: {', '.join(tags)}".strip()

                jobs.append(
                    JobPosting(
                        source=self.name,
                        title=item.get("position", ""),
                        company=item.get("company", ""),
                        url=item.get("url", ""),
                        description=description,
                        location=item.get("location", ""),
                        remote=True,
                        country="",
                        salary=salary,
                        posted_at=item.get("date", ""),
                    )
                )
            except Exception as exc:
                print(f"[remoteok] skipping malformed item: {exc}")
                continue

        return jobs


if __name__ == "__main__":
    fetched = RemoteOK().fetch()
    print(f"fetched {len(fetched)} jobs")
