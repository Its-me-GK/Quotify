"""Database lifecycle operations.

These helpers are used by dedicated scripts and the protected production
bootstrap endpoint. They are never called from application startup.
"""

from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from main import BootstrapRuns, Contacts, Posts, db


def initialize_schema() -> list[str]:
    """Create missing application tables and return the resulting table names."""
    db.create_all()
    inspector = inspect(db.engine)
    return sorted(inspector.get_table_names())


def seed_records(posts: Iterable[dict], contacts: Iterable[dict]) -> dict[str, int]:
    """Insert sample records idempotently and return insertion counts."""
    inserted_posts = 0
    inserted_contacts = 0

    try:
        for post_data in posts:
            if Posts.query.filter_by(slug=post_data["slug"]).first() is not None:
                continue
            db.session.add(Posts(**post_data))
            inserted_posts += 1

        for contact_data in contacts:
            existing = Contacts.query.filter_by(
                email=contact_data["email"],
                message=contact_data["message"],
            ).first()
            if existing is not None:
                continue
            db.session.add(Contacts(**contact_data))
            inserted_contacts += 1

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return {"posts": inserted_posts, "contacts": inserted_contacts}


def bootstrap_production_database(posts: Iterable[dict], contacts: Iterable[dict]) -> dict:
    """Run the explicit one-time production bootstrap workflow."""
    inspector = inspect(db.engine)
    tables_before = set(inspector.get_table_names())

    tables_after = set(initialize_schema())
    tables_created = sorted(tables_after - tables_before)

    completed_run = BootstrapRuns.query.order_by(BootstrapRuns.id.asc()).first()
    if completed_run is not None:
        return {
            "status": "already_completed",
            "tables_created": [],
            "seeded": {"posts": 0, "contacts": 0},
            "completed_at": completed_run.completed_at,
        }

    counts = seed_records(posts, contacts)
    completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = f"posts={counts['posts']};contacts={counts['contacts']}"

    try:
        db.session.add(
            BootstrapRuns(completed_at=completed_at, result_summary=summary)
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    return {
        "status": "completed",
        "tables_created": tables_created,
        "seeded": counts,
        "completed_at": completed_at,
    }
