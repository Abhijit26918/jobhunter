"""CLI entrypoint: python run.py [ingest|match|all]"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from src import db
from src.ingest import run_ingest
from src.profile import load_profile

load_dotenv()


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
