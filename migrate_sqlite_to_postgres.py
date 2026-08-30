#!/usr/bin/env python3
"""One-time SQLite -> PostgreSQL migration for Neural Gold."""
from __future__ import annotations

import os
from sqlalchemy import create_engine, text

SOURCE = os.getenv("SOURCE_DATABASE_URL", "").strip()
TARGET = os.getenv("TARGET_DATABASE_URL", "").strip()
if not SOURCE or not TARGET:
    raise SystemExit("Set SOURCE_DATABASE_URL and TARGET_DATABASE_URL before running migration.")
source_engine = create_engine(SOURCE, pool_pre_ping=True)
target_engine = create_engine(TARGET, pool_pre_ping=True)
os.environ["DATABASE_URL"] = TARGET
from database import Base
import whop_storage

Base.metadata.create_all(bind=target_engine)
whop_storage.init_phase2_db()
TABLES = ["users", "user_sessions", "token_pool", "whop_orders", "whop_webhook_events"]
with source_engine.connect() as src, target_engine.begin() as dst:
    for table in TABLES:
        exists = src.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:table"), {"table": table}).first() if SOURCE.startswith("sqlite") else src.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name=:table"), {"table": table}).first()
        if not exists:
            print(f"skip {table}: source table absent")
            continue
        rows = src.execute(text(f"SELECT * FROM {table}")).mappings().all()
        if not rows:
            print(f"copy {table}: 0 rows")
            continue
        columns = list(rows[0].keys())
        col_sql = ", ".join(columns)
        bind_sql = ", ".join(f":{c}" for c in columns)
        for row in rows:
            dst.execute(text(f"INSERT INTO {table} ({col_sql}) VALUES ({bind_sql}) ON CONFLICT DO NOTHING"), dict(row))
        print(f"copy {table}: {len(rows)} rows")
print("Migration completed. Verify row counts before switching Belmo DATABASE_URL.")
