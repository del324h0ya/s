"""NEURAL GOLD — Whop webhook receiver (Phase 2).

Phase 1 remains manual payment verification. This endpoint is included and
configured for the later automation phase, but it is not required for normal
Belmo bot operation.
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request, Response
from whop_sdk.lib.verify_webhook import unwrap

import database

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
logger = logging.getLogger("neural_whop_webhook")

WHOP_WEBHOOK_SECRET = os.getenv("WHOP_WEBHOOK_SECRET", "").strip()

PLAN_DURATIONS = {
    "plan_ksl11weFJ0z41": 7,
    "plan_Yc1JnCIP8jgII": 14,
    "plan_JDgh0geRuoSFX": 30,
}

app = FastAPI(title="NEURAL GOLD Whop Webhook", version="2.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "neural-gold-whop-webhook"}


@app.post("/webhooks/whop")
async def whop_webhook(request: Request, background: BackgroundTasks):
    if not WHOP_WEBHOOK_SECRET:
        logger.error("WHOP_WEBHOOK_SECRET is not configured.")
        return Response(status_code=503)

    payload = await request.body()
    try:
        event = unwrap(payload, headers=dict(request.headers), key=WHOP_WEBHOOK_SECRET)
    except Exception:
        logger.exception("Whop webhook verification failed.")
        return Response(status_code=401)

    if event.get("type") == "payment.succeeded":
        background.add_task(handle_payment_succeeded, event.get("data", {}))

    return Response(status_code=200)


def handle_payment_succeeded(payment: dict) -> None:
    plan_id = payment.get("plan_id")
    duration = PLAN_DURATIONS.get(plan_id)
    buyer_email = payment.get("member", {}).get("email", "unknown")

    if duration is None:
        logger.error("Unknown Whop plan_id: %s", plan_id)
        return

    token = f"XAU-NEURAL-{secrets.token_hex(6).upper()}"
    database.init_db()
    success = database.add_token_to_pool(token, duration_days=duration)

    if not success:
        logger.error("Failed to create token for payment %s", payment.get("id"))
        return

    # Phase 2 delivery must be connected to a verified customer identity.
    # Do not guess a Telegram account from an email/username.
    logger.info(
        "TOKEN ISSUED payment=%s duration=%sd buyer=%s token=%s",
        payment.get("id"), duration, buyer_email, token,
    )
