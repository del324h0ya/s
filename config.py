"""NEURAL GOLD v3.2 configuration for Belmo deployment."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0") or 0)

BELMO_PUBLIC_URL = os.getenv("BELMO_PUBLIC_URL", "").strip().rstrip("/")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()

WHOP_COMPANY_API_KEY = os.getenv("WHOP_COMPANY_API_KEY", "").strip()
WHOP_API_KEY = (WHOP_COMPANY_API_KEY or os.getenv("WHOP_API_KEY", "")).strip()
WHOP_COMPANY_ID = os.getenv("WHOP_COMPANY_ID", "").strip()
WHOP_WEBHOOK_SECRET = os.getenv("WHOP_WEBHOOK_SECRET", "").strip()

GOLDAPI_API_KEY = os.getenv("GOLDAPI_API_KEY", "").strip()
PRICE_SYMBOL = "XAU/USD"
GOLDAPI_ENDPOINT = "https://www.goldapi.io/api/price/XAU/USD"

_raw_database_url = os.getenv("DATABASE_URL", "sqlite:///xauusd_bot.db").strip()
if _raw_database_url.startswith("sqlite:///") and not _raw_database_url.startswith("sqlite:////"):
    _db_name = _raw_database_url[len("sqlite:///"):].lstrip("/") or "xauusd_bot.db"
    _db_path = (Path(tempfile.gettempdir()) / _db_name).resolve()
    DATABASE_URL = f"sqlite:///{_db_path.as_posix()}"
else:
    DATABASE_URL = _raw_database_url

REQUIRE_POSTGRES = os.getenv("REQUIRE_POSTGRES", "0").strip().lower() in {"1", "true", "yes"}
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip()
LOG_FILE = str(Path(tempfile.gettempdir()) / "neural_gold_bot.log")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "production").strip()

NEURAL_VERSION = "v3.2"
SIGNAL_VALIDITY_MINUTES = 240

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it in Belmo Environment Variables.")
if not GOLDAPI_API_KEY:
    raise RuntimeError("GOLDAPI_API_KEY is not set. Add it in Belmo Environment Variables.")

if BELMO_PUBLIC_URL:
    if not TELEGRAM_WEBHOOK_SECRET:
        raise RuntimeError("TELEGRAM_WEBHOOK_SECRET is required when BELMO_PUBLIC_URL is set.")
    if not WHOP_WEBHOOK_SECRET:
        raise RuntimeError("WHOP_WEBHOOK_SECRET is required when BELMO_PUBLIC_URL is set.")
    if not WHOP_API_KEY:
        raise RuntimeError("WHOP_API_KEY/WHOP_COMPANY_API_KEY is required for production checkout flow.")
    if REQUIRE_POSTGRES and not DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")):
        raise RuntimeError("REQUIRE_POSTGRES is enabled but DATABASE_URL is not PostgreSQL.")
