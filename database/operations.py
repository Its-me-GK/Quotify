"""Database lifecycle operations.

These helpers are used by dedicated scripts and are never called from request
handlers or application startup.
"""

from collections.abc import Iterable

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from main import Contacts, Posts, db


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
