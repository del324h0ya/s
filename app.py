"""NEURAL GOLD v3.2 — Belmo HTTP/Webhook entry point."""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from contextlib import asynccontextmanager
from urllib.parse import unquote

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from telegram import Update

import command_localization
import database
import expiry_notifier
import premium_visuals
import whop_api_phase2
import whop_storage
from config import BELMO_PUBLIC_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET
from main import build_application, post_init, setup_logging
from whop_webhook_phase2 import handle_event, notify_customer, verify_signature

logger = logging.getLogger("neural_gold.belmo")
telegram_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app
    setup_logging()
    database.init_db()
    whop_storage.init_phase2_db()
    premium_visuals.install()
    telegram_app = build_application()
    await telegram_app.initialize()
    await post_init(telegram_app)
    await command_localization.install(telegram_app.bot, database_admin_id())
    expiry_notifier.schedule(telegram_app)
    await telegram_app.start()

    if BELMO_PUBLIC_URL:
        webhook_url = f"{BELMO_PUBLIC_URL}/telegram/webhook"
        try:
            await telegram_app.bot.set_webhook(
                url=webhook_url,
                secret_token=TELEGRAM_WEBHOOK_SECRET or None,
                drop_pending_updates=True,
            )
            logger.info("Telegram webhook configured: %s", webhook_url)
        except Exception:
            logger.exception("Telegram webhook registration failed: %s", webhook_url)
    else:
        logger.warning("BELMO_PUBLIC_URL is not set; webhook registration skipped.")

    yield

    if telegram_app:
        try:
            if BELMO_PUBLIC_URL:
                await telegram_app.bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            logger.exception("Failed to delete Telegram webhook")
        await telegram_app.stop()
        await telegram_app.shutdown()


def database_admin_id() -> int | None:
    """Return the configured admin Telegram ID without duplicating config logic."""
    try:
        from config import ADMIN_TELEGRAM_ID
        return ADMIN_TELEGRAM_ID
    except Exception:
        return None


app = FastAPI(title="NEURAL GOLD v3.2", version="3.2.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {"service": "NEURAL GOLD v3.2", "status": "online"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "neural-gold", "telegram": telegram_app is not None}


@app.get("/checkout/{days}")
async def checkout_redirect(days: int, token: str):
    """Validate the short-lived Telegram plan link, create a Whop checkout,
    and redirect directly to Whop.
    """
    if days not in (7, 14, 30):
        raise HTTPException(status_code=404, detail="Plan not found")
    try:
        raw = unquote(token)
        payload, signature = raw.rsplit(".", 1)
        telegram_id_text, days_text, expires_text = payload.split(":", 2)
        telegram_id = int(telegram_id_text)
        signed_days = int(days_text)
        expires = int(expires_text)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid payment link")

    if signed_days != days or expires < int(time.time()):
        raise HTTPException(status_code=410, detail="Payment link expired")

    key = (TELEGRAM_BOT_TOKEN or "neural-gold").encode("utf-8")
    expected = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid payment link")

    purchase_url, order_id, error = await whop_api_phase2.create_checkout_for_user(telegram_id, days)
    if not purchase_url:
        logger.error("Direct checkout creation failed telegram=%s order=%s error=%s", telegram_id, order_id, error)
        raise HTTPException(status_code=503, detail="Checkout temporarily unavailable")

    return RedirectResponse(url=purchase_url, status_code=303)


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    if telegram_app is None:
        raise HTTPException(status_code=503, detail="Bot is starting")
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        if update is None:
            raise ValueError("Invalid Telegram update")
        await telegram_app.process_update(update)
        return {"ok": True}
    except Exception:
        logger.exception("Telegram webhook processing failed")
        return JSONResponse(status_code=200, content={"ok": False})


@app.post("/webhooks/whop")
async def whop_webhook(request: Request, background: BackgroundTasks):
    payload = await request.body()
    try:
        event = verify_signature(payload, dict(request.headers))
    except Exception:
        logger.exception("Whop webhook verification failed")
        return Response(status_code=401)

    event_id = str(event.get("id") or request.headers.get("webhook-id") or "")
    event_type = str(event.get("type") or "")
    data = event.get("data") or {}
    if not event_id or not event_type:
        return Response(status_code=400)

    payment_id = str(data.get("id") or "") or None
    if not whop_storage.claim_webhook(event_id, event_type, payment_id):
        return Response(status_code=200)

    try:
        result = handle_event(event_type, data)
        whop_storage.mark_webhook(event_id, "processed")
        if result and telegram_app is not None:
            raw_token, duration, order_id = result
            order = whop_storage.get_order(order_id)
            if order is not None:
                background.add_task(notify_customer, telegram_app.bot, order["telegram_id"], raw_token, duration, order_id)
        return Response(status_code=200)
    except Exception as exc:
        logger.exception("Whop event processing failed event=%s", event_id)
        whop_storage.mark_webhook(event_id, "failed", str(exc)[:1000])
        return Response(status_code=500)
