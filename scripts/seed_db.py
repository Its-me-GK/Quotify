"""Seed Quotify with safe, idempotent demo records.

Usage: python scripts/seed_db.py --confirm
"""

import argparse
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)

from database.operations import initialize_schema, seed_records  # noqa: E402
from database.sample_data import SAMPLE_CONTACTS, SAMPLE_POSTS  # noqa: E402
from main import app  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Quotify with demo data.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that this command may connect to the configured database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.confirm:
        raise SystemExit("Refusing to seed the configured database without --confirm.")

    with app.app_context():
        initialize_schema()
        counts = seed_records(SAMPLE_POSTS, SAMPLE_CONTACTS)

    print(
        "Seed complete: "
        f"{counts['posts']} post(s) inserted, "
        f"{counts['contacts']} contact(s) inserted."
    )


if __name__ == "__main__":
    main()
