# Production Readiness Audit — 0.1 to 0.8

## 0.1 Telegram webhook stability — BLOCKING
Implemented: secret-header validation; explicit malformed JSON/invalid shape/missing update ID responses; persistent `update_id` idempotency; failed processing returns HTTP 500 so Telegram can retry; failed updates are immediately reclaimable on retry; structured JSON webhook logs; admin alerts through the same Telegram bot; Sentry exception capture.

## 0.2 Price source policy — BLOCKING
Configured by product decision: **GoldAPI only**. The application uses GoldAPI for XAU/USD and returns `LIVE FEED UNAVAILABLE` when GoldAPI cannot provide a valid price. No alternate provider and no fabricated price are used.

## 0.3 500 concurrent webhook load test — BLOCKING
Implemented: `load_test_webhook.py` reports p50/p95/p99 and passes only when p95 < 1500 ms with zero 5xx responses. PostgreSQL pool defaults to 20 connections plus 40 overflow.

Run against staging: `python load_test_webhook.py --url https://STAGING/telegram/webhook --secret "$TELEGRAM_WEBHOOK_SECRET" --requests 500 --concurrency 500`

## 0.4 SQLite → managed PostgreSQL — BLOCKING
Implemented: psycopg driver, PostgreSQL support, `REQUIRE_POSTGRES=1` guard, `migrate_db.py`, and `migrate_sqlite_to_postgres.py`. Production requires a Neon/managed PostgreSQL connection string before launch.

## 0.5 Backup + DR
Implemented: `backup_postgres.sh`, daily GitHub Actions backup workflow using `DATABASE_URL_BACKUP`, 14-day artifact retention, and `DISASTER_RECOVERY.md`. Managed-provider backups/PITR remain the primary recovery layer.

## 0.6 Sentry / error monitoring
Implemented: `sentry-sdk[fastapi]`, production DSN/environment configuration, webhook exception capture, and Telegram admin alerts for webhook failures.

## 0.7 Token security
Implemented: SHA-256 token hashes, admin-only `/addtoken`, atomic single-use enforcement, and no raw-token application logging.

## 0.8 Core E2E smoke test
Prepared: Phase 2 webhook tests remain in CI; production-audit tests cover GoldAPI behavior and webhook update deduplication/retry. Staging E2E must exercise `/start`, payment/fulfillment, live price, signal, and account/expiry.

## Release gate
Production launch remains gated by a working managed PostgreSQL database, valid GoldAPI access, valid Sentry DSN when monitoring is enabled, a staging 500-concurrent run with p95 < 1.5s and zero 5xx, and one successful real payment + `payment.succeeded` fulfillment test.
