---
name: db-migrations
description: >-
  Use when writing, reviewing, or running Postgres schema migrations in the
  api service. Creates timestamped SQL migration files, checks them for
  locking and data-loss risks, and runs them against local and staging
  databases. Excludes schema design reviews (use db-schema-review) and query
  performance tuning (use pg-query-tuning).
---

# Database migrations

Migrations live in `services/api/migrations/` and are plain SQL.

## Writing a migration

1. Name the file `YYYYMMDDHHMM_short_description.sql`, using UTC time.
2. Write the `-- up` section first, then a `-- down` section that reverses it exactly.
3. Start every migration with `SET lock_timeout = '5s';` so a blocked migration fails within five seconds and can be retried.
4. Add new columns as nullable, backfill in batches of 10,000 rows, then add the `NOT NULL` constraint in a separate migration.
5. Create indexes with `CREATE INDEX CONCURRENTLY`, in a migration of their own, because concurrent index builds can't run inside a transaction.

## Running migrations

- Local: `pnpm db:migrate`
- Staging: `pnpm db:migrate --env staging`
- Check status: `pnpm db:status`

## Production

Production migrations run through the release pipeline after a maintainer approves the release.

Dropping a column or table deletes data permanently. Before any `DROP` statement, take a snapshot with `pnpm db:snapshot`, and ask the user to confirm the table name before applying it anywhere outside local.
