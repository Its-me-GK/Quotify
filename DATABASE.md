# Quotify Database Operations

Quotify keeps database lifecycle operations outside the web request path.

## Why

Flask-SQLAlchemy documents that create_all() creates missing tables but does not
update existing tables. Future schema changes should use a migration system.

The production application therefore does not create or seed tables when a user
opens the website.

## Initialize the database

Make the same environment variables used by main.py available locally,
especially PRODUCTION_URL and SECRET_KEY.

Run:

    python scripts/init_db.py --confirm

This creates only missing application tables.

## Load sample data

Run:

    python scripts/seed_db.py --confirm

The seed operation is idempotent. Re-running it does not create duplicate
sample posts or contacts.

## Recommended new-database workflow

1. Run scripts/init_db.py --confirm.
2. Run scripts/seed_db.py --confirm when demo/sample content is required.
3. Verify the application.
4. Do not add database initialization to Vercel request handling.

For future model/schema changes, introduce versioned migrations rather than
relying on create_all().

## Safety

The scripts require an explicit --confirm flag because this repository is
configured for a production database. Sample data contains no credentials or
other secrets.
