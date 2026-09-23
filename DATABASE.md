# Quotify Database Operations

Quotify keeps database lifecycle operations outside application startup and normal
web requests.

## Why

Flask-SQLAlchemy documents that create_all() creates missing tables but does not
update existing tables. Future schema changes should use a migration system.

The production application therefore does not create or seed tables when a user
opens the website.

## Production one-time bootstrap endpoint

Production database bootstrap is available only through an explicitly invoked
POST request:

    POST /admin/bootstrap-db

The endpoint is designed for Vercel production only. It checks that
`VERCEL_ENV=production`, requires a strong `DB_BOOTSTRAP_TOKEN`, creates missing
application tables, seeds only missing sample records, and records completion in
the `BootstrapRuns` table. After a successful bootstrap, later valid POSTs return
`already_completed` and do not run the seed workflow again.

Required Vercel production environment variable:

    DB_BOOTSTRAP_TOKEN=<generate a long random secret, at least 32 characters>

Set this only in the Vercel Production environment. Do not commit it, paste it in
URLs, or share it in logs.

Invoke it with the token in a header, not in the query string:

    curl -X POST https://<production-domain>/admin/bootstrap-db \
      -H "Authorization: Bearer <DB_BOOTSTRAP_TOKEN>"

Safe responses include only status, table names created, seed counts, and the
completion timestamp. They never include database URLs, passwords, or token
values.

## Initialize the database locally or from a maintenance shell

Make the same environment variables used by main.py available locally,
especially PRODUCTION_URL and SECRET_KEY.

Run:

    python scripts/init_db.py --confirm

This creates only missing application tables.

## Load sample data locally or from a maintenance shell

Run:

    python scripts/seed_db.py --confirm

The seed operation is idempotent. Re-running it does not create duplicate
sample posts or contacts.

## Recommended new production database workflow

1. Set `DB_BOOTSTRAP_TOKEN` in Vercel Production with a long random value.
2. Deploy the application.
3. Confirm GET requests to `/admin/bootstrap-db` do not run anything.
4. Send one POST request with the token in the `Authorization: Bearer ...` header.
5. Confirm the response is `completed`.
6. Re-run the same POST only if you want to confirm it now returns
   `already_completed`.
7. Remove or rotate `DB_BOOTSTRAP_TOKEN` after the production database is set up.

For future model/schema changes, introduce versioned migrations rather than
relying on create_all().

## Safety

The scripts require an explicit --confirm flag because this repository can be
configured for a production database. The production endpoint requires POST,
Vercel production, and a strong server-side secret. Sample data contains no
credentials or other secrets.
