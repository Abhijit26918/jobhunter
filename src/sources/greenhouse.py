"""Greenhouse adapter — https://boards-api.greenhouse.io/v1/boards/{board}/jobs, no key, per target company."""

from __future__ import annotations

import httpx

from src.models import JobPosting
from src.sources.base import Source, USER_AGENT, TIMEOUT, strip_html

API_URL_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"


class Greenhouse(Source):
    name = "greenhouse"

    def __init__(self, boards: list[str]):
        self.boards = boards

    def fetch(self) -> list[JobPosting]:
        jobs: list[JobPosting] = []
        for board in self.boards:
            try:
                resp = httpx.get(
                    API_URL_TEMPLATE.format(board=board),
                    params={"content": "true"},
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                print(f"[greenhouse] fetch failed for board={board}: {exc}")
                continue

            for item in data.get("jobs", []):
                try:
                    jobs.append(
                        JobPosting(
                            source=self.name,
                            title=item.get("title", ""),
                            company=board,
                            url=item.get("absolute_url", ""),
                            description=strip_html(item.get("content", "")),
                            location=(item.get("location") or {}).get("name", ""),
                            remote=False,
                            country="",
                            salary="",
                            posted_at=item.get("updated_at", ""),
                        )
                    )
                except Exception as exc:
                    print(f"[greenhouse] skipping malformed item: {exc}")
                    continue

        return jobs


if __name__ == "__main__":
    fetched = Greenhouse(boards=["stripe"]).fetch()
    print(f"fetched {len(fetched)} jobs")
