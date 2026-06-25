"""Build enabled sources from config and run the ingest loop. Extracted from run.py
so the registry can grow without bloating the CLI."""

from __future__ import annotations

import sqlite3

from src import db
from src.sources.adzuna import Adzuna
from src.sources.arbeitnow import Arbeitnow
from src.sources.ashby import Ashby
from src.sources.base import Source
from src.sources.greenhouse import Greenhouse
from src.sources.jobicy import Jobicy
from src.sources.lever import Lever
from src.sources.remoteok import RemoteOK
from src.sources.remotive import Remotive


def build_sources(config: dict) -> list[Source]:
    """Instantiate every enabled source, reading each one's own sub-config."""
    sources_cfg = config.get("sources", {})
    search_cfg = config.get("search", {})
    sources: list[Source] = []

    if sources_cfg.get("remoteok", {}).get("enabled"):
        sources.append(RemoteOK())

    if sources_cfg.get("remotive", {}).get("enabled"):
        sources.append(Remotive())

    if sources_cfg.get("arbeitnow", {}).get("enabled"):
        sources.append(Arbeitnow())

    jobicy_cfg = sources_cfg.get("jobicy", {})
    if jobicy_cfg.get("enabled"):
        sources.append(Jobicy(tag=jobicy_cfg.get("tag", "")))

    adzuna_cfg = sources_cfg.get("adzuna", {})
    if adzuna_cfg.get("enabled") and adzuna_cfg.get("queries"):
        sources.append(
            Adzuna(queries=adzuna_cfg["queries"], countries=search_cfg.get("countries", []))
        )

    greenhouse_cfg = sources_cfg.get("greenhouse", {})
    if greenhouse_cfg.get("enabled") and greenhouse_cfg.get("boards"):
        sources.append(Greenhouse(boards=greenhouse_cfg["boards"]))

    lever_cfg = sources_cfg.get("lever", {})
    if lever_cfg.get("enabled") and lever_cfg.get("companies"):
        sources.append(Lever(companies=lever_cfg["companies"]))

    ashby_cfg = sources_cfg.get("ashby", {})
    if ashby_cfg.get("enabled") and ashby_cfg.get("orgs"):
        sources.append(Ashby(orgs=ashby_cfg["orgs"]))

    return sources


def run_ingest(conn: sqlite3.Connection, config: dict) -> int:
    """Fetch every enabled source, dedup, upsert into jobs. One dead source can't abort the run."""
    new_count = 0
    for source in build_sources(config):
        try:
            jobs = source.fetch()
        except Exception as exc:
            print(f"[{source.name}] fetch failed: {exc}")
            continue

        added = sum(1 for job in jobs if db.upsert_job(conn, job) is not None)
        print(f"[{source.name}] fetched {len(jobs)}, added {added} new")
        new_count += added

    return new_count
