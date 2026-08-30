"""
database.py — SQLAlchemy ORM models and database operations.

PostgreSQL is the production target. SQLite remains available for local/CI use.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Integer, String, create_engine, event, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL

logger = logging.getLogger(__name__)


def normalize_datetime_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(128), nullable=True)
    first_name = Column(String(128), nullable=True)
    language = Column(String(8), default="en", nullable=False)
    token = Column(String(256), nullable=True, index=True)
    is_active = Column(Boolean, default=False, nullable=False)
    subscription_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    state = Column(String(64), default="idle", nullable=False)
    last_price_bid = Column(Float, nullable=True)
    last_price_ask = Column(Float, nullable=True)
    last_price_high = Column(Float, nullable=True)
    last_price_low = Column(Float, nullable=True)
    last_signal_time = Column(DateTime, nullable=True)
    last_fetch_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class TokenPool(Base):
    __tablename__ = "token_pool"
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    duration_days = Column(Integer, default=30, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    used_at = Column(DateTime, nullable=True)
    used_by_telegram_id = Column(BigInteger, nullable=True)


class TelegramWebhookEvent(Base):
    __tablename__ = "telegram_webhook_events"
    update_id = Column(BigInteger, primary_key=True)
    status = Column(String(32), nullable=False, default="processing")
    received_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(String(1000), nullable=True)


if DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")):
    engine = create_engine(
        DATABASE_URL, echo=False, pool_pre_ping=True,
        pool_size=int(__import__("os").getenv("DB_POOL_SIZE", "20")),
        max_overflow=int(__import__("os").getenv("DB_MAX_OVERFLOW", "40")),
        pool_timeout=int(__import__("os").getenv("DB_POOL_TIMEOUT", "10")),
    )
else:
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        if DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")):
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT USING telegram_id::bigint"))
                conn.execute(text("ALTER TABLE token_pool ALTER COLUMN used_by_telegram_id TYPE BIGINT USING used_by_telegram_id::bigint"))
                conn.execute(text("ALTER TABLE telegram_webhook_events ALTER COLUMN update_id TYPE BIGINT USING update_id::bigint"))
            logger.info("Database migration applied: Telegram identifiers -> BIGINT")
        if DATABASE_URL.startswith("sqlite"):
            inspector = __import__("sqlalchemy").inspect(engine)
            cols = {c["name"] for c in inspector.get_columns("users")}
            if "language" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN language VARCHAR(8) NOT NULL DEFAULT 'en'"))
                logger.info("Database migration applied: users.language")
        logger.info("Database tables initialised successfully.")
    except Exception as exc:
        logger.exception("Failed to initialise database tables: %s", exc)
        raise


def _get_session() -> Session:
    return SessionLocal()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def get_user_by_telegram_id(telegram_id: int) -> User | None:
    session = _get_session()
    try:
        return session.scalar(select(User).where(User.telegram_id == telegram_id))
    except Exception as exc:
        logger.exception("get_user_by_telegram_id failed: %s", exc)
        return None
    finally:
        session.close()


def get_user_language(telegram_id: int) -> str:
    session = _get_session()
    try:
        user = session.scalar(select(User).where(User.telegram_id == telegram_id))
        return user.language if user and user.language else "en"
    except Exception as exc:
        logger.warning("get_user_language failed: %s", exc)
        return "en"
    finally:
        session.close()


def set_user_language(telegram_id: int, language: str) -> bool:
    session = _get_session()
    try:
        user = session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return False
        user.language = language
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        logger.exception("set_user_language failed: %s", exc)
        return False
    finally:
        session.close()


def get_user_by_token(token: str) -> User | None:
    session = _get_session()
    try:
        return session.scalar(select(User).where(User.token == _hash_token(token)))
    except Exception as exc:
        logger.exception("get_user_by_token failed: %s", exc)
        return None
    finally:
        session.close()


def create_user(telegram_id: int, username: str | None, first_name: str | None, language: str = "en") -> User:
    session = _get_session()
    try:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name, language=language, is_active=False)
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info("Created user %d (%s)", telegram_id, username or "no-username")
        return user
    except Exception as exc:
        session.rollback()
        logger.exception("create_user failed: %s", exc)
        raise
    finally:
        session.close()


def activate_user_token(telegram_id: int, raw_token: str, duration_days: int | None = None) -> bool:
    session = _get_session()
    try:
        token_hash = _hash_token(raw_token)
        result = session.execute(text("""
            UPDATE token_pool
            SET is_used = :used, used_at = :used_at, used_by_telegram_id = :telegram_id
            WHERE token_hash = :token_hash AND is_used = :unused
        """), {"used": True, "used_at": datetime.now(timezone.utc), "telegram_id": telegram_id, "token_hash": token_hash, "unused": False})
        if result.rowcount != 1:
            logger.warning("Token activation failed for user %d: token not found or already used.", telegram_id)
            return False
        pool_entry = session.scalar(select(TokenPool).where(TokenPool.token_hash == token_hash))
        if pool_entry is None:
            session.rollback()
            return False
        if duration_days is None:
            duration_days = pool_entry.duration_days
        user = session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, is_active=False)
            session.add(user)
            session.flush()
        now = datetime.now(timezone.utc)
        current_expiry = normalize_datetime_utc(user.subscription_expiry)
        base_time = current_expiry if user.is_active and current_expiry and current_expiry > now else now
        from datetime import timedelta
        user.token = token_hash
        user.is_active = True
        user.subscription_expiry = base_time + timedelta(days=duration_days)
        session.commit()
        logger.info("User %d activated token (expires %s).", telegram_id, user.subscription_expiry.isoformat())
        return True
    except Exception as exc:
        session.rollback()
        logger.exception("activate_user_token failed: %s", exc)
        return False
    finally:
        session.close()


def update_user(telegram_id: int, **kwargs) -> bool:
    session = _get_session()
    try:
        user = session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return False
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        logger.exception("update_user failed: %s", exc)
        return False
    finally:
        session.close()


def add_token_to_pool(raw_token: str, duration_days: int = 30) -> bool:
    session = _get_session()
    try:
        session.add(TokenPool(token_hash=_hash_token(raw_token), duration_days=duration_days))
        session.commit()
        logger.info("Token added to pool (duration=%d days).", duration_days)
        return True
    except Exception as exc:
        session.rollback()
        logger.exception("add_token_to_pool failed: %s", exc)
        return False
    finally:
        session.close()


def list_all_users() -> list[dict]:
    session = _get_session()
    try:
        rows = session.scalars(select(User).order_by(User.id)).all()
        return [{"id": u.id, "telegram_id": u.telegram_id, "username": u.username, "first_name": u.first_name, "is_active": u.is_active, "subscription_expiry": u.subscription_expiry.isoformat() if u.subscription_expiry else None} for u in rows]
    except Exception as exc:
        logger.exception("list_all_users failed: %s", exc)
        return []
    finally:
        session.close()


def revoke_user(telegram_id: int) -> bool:
    return update_user(telegram_id, is_active=False, token=None)


def get_or_create_session(user_id: int) -> UserSession:
    session = _get_session()
    try:
        row = session.scalar(select(UserSession).where(UserSession.user_id == user_id))
        if row is not None:
            return row
        row = UserSession(user_id=user_id)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
    except Exception as exc:
        session.rollback()
        logger.exception("get_or_create_session failed: %s", exc)
        raise
    finally:
        session.close()


def update_session(user_id: int, **kwargs) -> None:
    session = _get_session()
    try:
        row = session.scalar(select(UserSession).where(UserSession.user_id == user_id))
        if row is None:
            return
        for key, value in kwargs.items():
            if hasattr(row, key):
                setattr(row, key, value)
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception("update_session failed: %s", exc)
    finally:
        session.close()


def claim_telegram_update(update_id: int) -> bool:
    session = _get_session()
    now = datetime.now(timezone.utc)
    try:
        session.add(TelegramWebhookEvent(update_id=update_id, status="processing", received_at=now))
        session.commit()
        return True
    except Exception:
        session.rollback()
        row = session.scalar(select(TelegramWebhookEvent).where(TelegramWebhookEvent.update_id == update_id))
        if row is None:
            raise
        if row.status == "processed":
            return False
        if row.status == "failed":
            row.status = "processing"
            row.received_at = now
            row.processed_at = None
            row.error_message = None
            session.commit()
            return True
        age = (now - normalize_datetime_utc(row.received_at)).total_seconds() if row.received_at else 999999
        if age >= 60:
            row.status = "processing"
            row.received_at = now
            row.processed_at = None
            row.error_message = None
            session.commit()
            return True
        return False
    finally:
        session.close()


def mark_telegram_update(update_id: int, status: str, error_message: str | None = None) -> None:
    session = _get_session()
    try:
        row = session.scalar(select(TelegramWebhookEvent).where(TelegramWebhookEvent.update_id == update_id))
        if row:
            row.status = status
            row.processed_at = datetime.now(timezone.utc)
            row.error_message = error_message[:1000] if error_message else None
            session.commit()
    except Exception:
        session.rollback()
        logger.exception("mark_telegram_update failed update_id=%s", update_id)
    finally:
        session.close()
