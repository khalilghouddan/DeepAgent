from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.store import init_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create deep-agent tables in the Crawl4AI Postgres database."
    )
    parser.add_argument("--host", help="Postgres host, for example localhost.")
    parser.add_argument("--port", help="Postgres port, for example 5433.")
    parser.add_argument("--user", help="Postgres username.")
    parser.add_argument("--password", help="Postgres password.")
    parser.add_argument("--database", help="Postgres database name.")
    return parser.parse_args()


def apply_overrides(args: argparse.Namespace) -> None:
    overrides = {
        "DEEP_AGENT_DB_HOST": args.host,
        "DEEP_AGENT_DB_PORT": args.port,
        "DEEP_AGENT_DB_USER": args.user,
        "DEEP_AGENT_DB_PASSWORD": args.password,
        "DEEP_AGENT_DB_NAME": args.database,
    }
    for name, value in overrides.items():
        if value:
            os.environ[name] = value


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    args = parse_args()
    apply_overrides(args)
    init_db()
    print("Deep-agent database tables are ready.")


if __name__ == "__main__":
    main()
