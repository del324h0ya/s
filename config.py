"""NEURAL GOLD v3.2 configuration for Belmo deployment."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0") or 0)

BELMO_PUBLIC_URL = os.getenv("BELMO_PUBLIC_URL", "").strip().rstrip("/")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()

WHOP_API_KEY = os.getenv("WHOP_API_KEY", "").strip()
WHOP_COMPANY_ID = os.getenv("WHOP_COMPANY_ID", "").strip()
WHOP_WEBHOOK_SECRET = os.getenv("WHOP_WEBHOOK_SECRET", "").strip()

GOLDAPI_API_KEY = os.getenv("GOLDAPI_API_KEY", "").strip()
PRICE_SYMBOL = "XAU/USD"
GOLDAPI_ENDPOINT = "https://www.goldapi.io/api/price/XAU/USD"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///xauusd_bot.db").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip()
LOG_FILE = str(BASE_DIR / "bot_logs.log")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

NEURAL_VERSION = "v3.2"
SIGNAL_VALIDITY_MINUTES = 240

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it in Belmo Environment Variables.")
if not GOLDAPI_API_KEY:
    raise RuntimeError("GOLDAPI_API_KEY is not set. Add it in Belmo Environment Variables.")

if not BELMO_PUBLIC_URL:
    # Allow local development; production Belmo should set the public URL.
    BELMO_PUBLIC_URL = ""
