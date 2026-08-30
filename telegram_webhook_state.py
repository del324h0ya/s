"""Persistent Telegram webhook state helpers used by the HTTP adapter."""
from __future__ import annotations

from sqlalchemy import select

import database


def mark_failed(update_id: int, error_message: str) -> None:
    database.mark_telegram_update(update_id, "failed", error_message)


def get_status(update_id: int) -> str | None:
    session = database.SessionLocal()
    try:
        row = session.scalar(select(database.TelegramWebhookEvent).where(database.TelegramWebhookEvent.update_id == update_id))
        return row.status if row else None
    except Exception:
        return None
    finally:
        session.close()
