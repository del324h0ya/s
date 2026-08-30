# Production Disaster Recovery Runbook

## Recovery target
- RTO: 15 minutes for the application/database restore workflow.
- RPO: use the managed PostgreSQL provider's PITR window for primary recovery.
- Keep a second logical dump outside the application container.

## Daily backup
The repository includes `backup_postgres.sh` and a scheduled GitHub Actions workflow. Store the production `DATABASE_URL` as a repository/environment secret named `DATABASE_URL_BACKUP`.

## Restore
1. Provision a clean managed PostgreSQL database.
2. Restore the latest `.dump` with `pg_restore --clean --if-exists --no-owner --dbname="$TARGET_DATABASE_URL" backup.dump`.
3. Run `DATABASE_URL="$TARGET_DATABASE_URL" python migrate_db.py`.
4. Point Belmo `DATABASE_URL` to the restored database and redeploy.
5. Verify `/health`, `/start`, subscription status, and Whop webhook processing.

## Provider PITR
Use the managed provider's PITR as the primary recovery mechanism, then validate application data before reopening paid traffic.
