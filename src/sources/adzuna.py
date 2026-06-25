"""Adzuna adapter — free key required (ADZUNA_APP_ID/ADZUNA_APP_KEY in .env).

https://api.adzuna.com/v1/api/jobs/{country}/search/1
Loops over queries x countries from config.
"""

from __future__ import annotations

import os

import httpx

from src.models import JobPosting
from src.sources.base import Source, USER_AGENT, TIMEOUT, strip_html

API_URL_TEMPLATE = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
VALID_COUNTRIES = {  # Adzuna's supported country codes (subset relevant to this project)
    "in", "gb", "us", "ca", "au", "de", "fr", "nl", "sg", "za", "br", "it", "es", "pl",
}


class Adzuna(Source):
    name = "adzuna"

    def __init__(self, queries: list[str], countries: list[str]):
        self.queries = queries
        self.countries = [c for c in countries if c in VALID_COUNTRIES]

    def fetch(self) -> list[JobPosting]:
        app_id = os.environ.get("ADZUNA_APP_ID")
        app_key = os.environ.get("ADZUNA_APP_KEY")
        if not app_id or not app_key:
            print("[adzuna] skipping: ADZUNA_APP_ID / ADZUNA_APP_KEY not set in .env")
            return []

        jobs: list[JobPosting] = []
        for country in self.countries:
            for query in self.queries:
                try:
                    resp = httpx.get(
                        API_URL_TEMPLATE.format(country=country),
                        params={
                            "app_id": app_id,
                            "app_key": app_key,
                            "what": query,
                            "results_per_page": 50,
                        },
                        headers={"User-Agent": USER_AGENT},
                        timeout=TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    print(f"[adzuna] fetch failed for {country}/{query}: {exc}")
                    continue

                for item in data.get("results", []):
                    try:
                        salary_min = item.get("salary_min")
                        salary_max = item.get("salary_max")
                        salary = f"{salary_min}-{salary_max}" if salary_min or salary_max else ""

                        jobs.append(
                            JobPosting(
                                source=self.name,
                                title=item.get("title", ""),
                                company=(item.get("company") or {}).get("display_name", ""),
                                url=item.get("redirect_url", ""),
                                description=strip_html(item.get("description", "")),
                                location=(item.get("location") or {}).get("display_name", ""),
                                remote=False,
                                country=country,
                                salary=salary,
                                posted_at=item.get("created", ""),
                            )
                        )
                    except Exception as exc:
                        print(f"[adzuna] skipping malformed item: {exc}")
                        continue

        return jobs


if __name__ == "__main__":
    fetched = Adzuna(queries=["data scientist"], countries=["in"]).fetch()
    print(f"fetched {len(fetched)} jobs")
