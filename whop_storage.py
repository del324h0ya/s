"""Phase 2 Whop persistence using the existing SQLAlchemy engine."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text

import database

logger = logging.getLogger("neural_gold.whop_storage")

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS whop_orders (
    id VARCHAR(64) PRIMARY KEY,
    telegram_id INTEGER NOT NULL,
    plan_id VARCHAR(128) NOT NULL,
    duration_days INTEGER NOT NULL,
    checkout_id VARCHAR(128) UNIQUE,
    payment_id VARCHAR(128) UNIQUE,
    membership_id VARCHAR(128),
    status VARCHAR(64) NOT NULL DEFAULT 'pending',
    token_hash VARCHAR(64),
    created_at TIMESTAMP NOT NULL,
    paid_at TIMESTAMP,
    notified_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_whop_orders_telegram_id ON whop_orders(telegram_id);
CREATE INDEX IF NOT EXISTS ix_whop_orders_plan_id ON whop_orders(plan_id);
CREATE INDEX IF NOT EXISTS ix_whop_orders_payment_id ON whop_orders(payment_id);
CREATE INDEX IF NOT EXISTS ix_whop_orders_membership_id ON whop_orders(membership_id);
CREATE INDEX IF NOT EXISTS ix_whop_orders_status ON whop_orders(status);
CREATE TABLE IF NOT EXISTS whop_webhook_events (
    id VARCHAR(128) PRIMARY KEY,
    event_type VARCHAR(128) NOT NULL,
    payment_id VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'received',
    created_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,
    error_message VARCHAR(1000)
);
CREATE INDEX IF NOT EXISTS ix_whop_webhook_events_event_type ON whop_webhook_events(event_type);
CREATE INDEX IF NOT EXISTS ix_whop_webhook_events_payment_id ON whop_webhook_events(payment_id);
CREATE INDEX IF NOT EXISTS ix_whop_webhook_events_status ON whop_webhook_events(status);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def init_phase2_db() -> None:
    with database.engine.begin() as conn:
        for statement in CREATE_SQL.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
    logger.info("Whop Phase 2 tables initialised.")


def create_order(order_id: str, telegram_id: int, plan_id: str, duration_days: int) -> bool:
    now = _now()
    try:
        with database.engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT OR IGNORE INTO whop_orders
                    (id, telegram_id, plan_id, duration_days, status, created_at, updated_at)
                    VALUES (:id, :telegram_id, :plan_id, :duration_days, 'pending', :created_at, :updated_at)
                """),
                {"id": order_id, "telegram_id": telegram_id, "plan_id": plan_id,
                 "duration_days": duration_days, "created_at": now, "updated_at": now},
            )
            return result.rowcount == 1
    except Exception:
        logger.exception("Failed to create Whop order %s", order_id)
        return False


def update_order(order_id: str, **fields) -> bool:
    allowed = {
        "checkout_id", "payment_id", "membership_id", "status", "token_hash",
        "paid_at", "notified_at",
    }
    values = {k: v for k, v in fields.items() if k in allowed}
    if not values:
        return False
    values["updated_at"] = _now()
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    values["id"] = order_id
    try:
        with database.engine.begin() as conn:
            result = conn.execute(
                text(f"UPDATE whop_orders SET {assignments} WHERE id = :id"), values
            )
            return result.rowcount == 1
    except Exception:
        logger.exception("Failed to update Whop order %s", order_id)
        return False


def get_order(order_id: str) -> dict | None:
    with database.engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM whop_orders WHERE id = :id"), {"id": order_id}
        ).mappings().first()
        return dict(row) if row else None


def get_order_by_payment(payment_id: str) -> dict | None:
    with database.engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM whop_orders WHERE payment_id = :payment_id"),
            {"payment_id": payment_id},
        ).mappings().first()
        return dict(row) if row else None


def get_order_by_membership(membership_id: str) -> dict | None:
    with database.engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM whop_orders WHERE membership_id = :membership_id"),
            {"membership_id": membership_id},
        ).mappings().first()
        return dict(row) if row else None


def claim_webhook(event_id: str, event_type: str, payment_id: str | None = None) -> bool:
    """Atomically claim an event for processing, while allowing failed events to retry."""
    now = _now()
    try:
        with database.engine.begin() as conn:
            inserted = conn.execute(
                text("""
                    INSERT OR IGNORE INTO whop_webhook_events
                    (id, event_type, payment_id, status, created_at)
                    VALUES (:id, :event_type, :payment_id, 'processing', :created_at)
                """),
                {"id": event_id, "event_type": event_type, "payment_id": payment_id, "created_at": now},
            )
            if inserted.rowcount == 1:
                return True

            reclaimed = conn.execute(
                text("""
                    UPDATE whop_webhook_events
                    SET status = 'processing', processed_at = NULL, error_message = NULL
                    WHERE id = :id AND status IN ('failed', 'received')
                """),
                {"id": event_id},
            )
            return reclaimed.rowcount == 1
    except Exception:
        logger.exception("Failed to claim Whop webhook %s", event_id)
        return False


def mark_webhook(event_id: str, status: str, error_message: str | None = None) -> None:
    with database.engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE whop_webhook_events
                SET status = :status, processed_at = :processed_at, error_message = :error_message
                WHERE id = :id
            """),
            {"id": event_id, "status": status, "processed_at": _now(), "error_message": error_message},
        )


def revoke_order_access(order_id: str) -> bool:
    """Revoke only the access issued by this order; preserve a newer purchase."""
    order = get_order(order_id)
    if not order or not order.get("token_hash"):
        return False
    user = database.get_user_by_telegram_id(int(order["telegram_id"]))
    if user is None or user.token != order["token_hash"]:
        return False
    return database.update_user(int(order["telegram_id"]), is_active=False)
