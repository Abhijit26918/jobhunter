"""CLI entrypoint: python run.py [ingest|match|all]"""

from __future__ import annotations

import sys

from src import db
from src.profile import load_profile
from src.sources.remoteok import RemoteOK

SOURCE_REGISTRY = {
    "remoteok": RemoteOK,
}


def run_ingest(conn, config: dict) -> int:
    new_count = 0
    sources_cfg = config.get("sources", {})
    for name, cls in SOURCE_REGISTRY.items():
        if not sources_cfg.get(name, {}).get("enabled"):
            continue
        try:
            jobs = cls().fetch()
        except Exception as exc:
            print(f"[{name}] fetch failed: {exc}")
            continue
        added = 0
        for job in jobs:
            if db.upsert_job(conn, job) is not None:
                added += 1
        print(f"[{name}] fetched {len(jobs)}, added {added} new")
        new_count += added
    return new_count


def run_match(conn, profile) -> None:
    from src.match import run_match as _run_match

    count = _run_match(conn, profile)
    print(f"scored {count} jobs")


def print_top_matches(conn, profile, limit: int = 15) -> None:
    rows = db.top_matches(conn, limit=limit)
    if not rows:
        print("No matches yet.")
        return
    print(f"\nTop {len(rows)} matches:\n")
    for row in rows:
        print(f"  [{row['score']:.1f}] {row['title']} @ {row['company']}")
        print(f"        {row['url']}")
        print(f"        {row['reasons']}\n")


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"

    profile = load_profile()
    conn = db.connect()
    db.init_db(conn)

    if command in ("ingest", "all"):
        run_ingest(conn, profile.config)

    if command in ("match", "all"):
        run_match(conn, profile)

    if command == "all":
        print_top_matches(conn, profile, limit=profile.config.get("match", {}).get("top_n_display", 15))

    if command not in ("ingest", "match", "all"):
        print(f"Unknown command: {command}. Use ingest|match|all.")
        sys.exit(1)


if __name__ == "__main__":
    main()
