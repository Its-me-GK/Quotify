"""Initialize the Quotify database schema.

Usage: python scripts/init_db.py --confirm
"""

import argparse
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)

from database.operations import initialize_schema  # noqa: E402
from main import app  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize Quotify database tables.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that this command may connect to the configured database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.confirm:
        raise SystemExit(
            "Refusing to initialize the configured database without --confirm."
        )

    with app.app_context():
        tables = initialize_schema()

    print("Database schema initialized successfully.")
    print("Tables:", ", ".join(tables))


if __name__ == "__main__":
    main()
