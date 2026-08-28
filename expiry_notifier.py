"""Scheduled H-2 subscription expiry reminders for NEURAL GOLD."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Integer, String, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import database
import phase2_bot

logger = logging.getLogger("neural_gold.expiry_notifier")


class ExpiryNotice(database.Base):
    __tablename__ = "expiry_notices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    expiry_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=False)
    language = Column(String(8), nullable=True)


TEXT = {
    "id": (
        "<b>⚠️ CLEARANCE EXPIRING IN 2 DAYS</b>\n\n"
        "Koneksi premium Anda akan berakhir dalam 2 hari.\n\n"
        "Pertahankan akses ke Neural Strikes, Structure Map, dan Alpha Terminal dengan memilih clearance berikut:"
    ),
    "en": (
        "<b>⚠️ CLEARANCE EXPIRING IN 2 DAYS</b>\n\n"
        "Your premium connection expires in 2 days.\n\n"
        "Maintain access to Neural Strikes, Structure Map, and Alpha Terminal by selecting a clearance level below:"
    ),
}


def _buttons(telegram_id: int, lang: str) -> InlineKeyboardMarkup:
    labels = {
        "id": [("🕐 PERPANJANG 7 HARI", 7), ("📅 PERPANJANG 14 HARI", 14), ("🗓️ PERPANJANG 30 HARI", 30)],
        "en": [("🕐 EXTEND 7 DAYS", 7), ("📅 EXTEND 14 DAYS", 14), ("🗓️ EXTEND 30 DAYS", 30)],
    }
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, url=phase2_bot.checkout_link(telegram_id, days))]
        for label, days in labels.get(lang, labels["en"])
    ])


def _already_sent(session, telegram_id: int, expiry_at: datetime) -> bool:
    row = session.scalar(select(ExpiryNotice).where(ExpiryNotice.telegram_id == telegram_id))
    if row is None:
        return False
    return database.normalize_datetime_utc(row.expiry_at) == database.normalize_datetime_utc(expiry_at)


def _claim(session, telegram_id: int, expiry_at: datetime, language: str) -> None:
    row = session.scalar(select(ExpiryNotice).where(ExpiryNotice.telegram_id == telegram_id))
    now = datetime.now(timezone.utc)
    if row is None:
        row = ExpiryNotice(telegram_id=telegram_id, expiry_at=expiry_at, sent_at=now, language=language)
        session.add(row)
    else:
        row.expiry_at = expiry_at
        row.sent_at = now
        row.language = language
    session.commit()


async def check_expiring(context) -> None:
    now = datetime.now(timezone.utc)
    lower = now + timedelta(hours=1)
    upper = now + timedelta(hours=3)
    session = database._get_session()
    try:
        users = session.scalars(
            select(database.User).where(
                database.User.is_active == True,  # noqa: E712
                database.User.subscription_expiry.is_not(None),
            )
        ).all()
        for user in users:
            expiry = database.normalize_datetime_utc(user.subscription_expiry)
            if expiry is None or not (lower <= expiry <= upper):
                continue
            if _already_sent(session, user.telegram_id, expiry):
                continue
            lang = user.language if user.language in TEXT else "en"
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=TEXT[lang],
                    parse_mode="HTML",
                    reply_markup=_buttons(user.telegram_id, lang),
                )
                _claim(session, user.telegram_id, expiry, lang)
                logger.info("Sent H-2 expiry reminder to %s", user.telegram_id)
            except Exception:
                logger.exception("Failed H-2 expiry reminder for %s", user.telegram_id)
    finally:
        session.close()


def schedule(application) -> None:
    job_queue = application.job_queue
    if job_queue is None:
        logger.warning("JobQueue unavailable; H-2 expiry reminder is not scheduled.")
        return
    if job_queue.get_jobs_by_name("neural_gold_expiry_check"):
        return
    job_queue.run_repeating(
        check_expiring,
        interval=3600,
        first=30,
        name="neural_gold_expiry_check",
    )
    logger.info("H-2 subscription expiry reminder scheduled hourly.")
