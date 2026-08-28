"""Whop Standard Webhooks verification and Phase 2 fulfillment."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any

import database
import whop_storage
from config import WHOP_WEBHOOK_SECRET
from visuals import visual_path

logger = logging.getLogger("neural_whop_webhook")
PLAN_DURATIONS = {
    "plan_ksl11weFJ0z41": 7,
    "plan_Yc1JnCIP8jgII": 14,
    "plan_JDgh0geRuoSFX": 30,
}


class FulfillmentRetryableError(RuntimeError):
    """Signal that Whop should retry a payment webhook."""


def _signing_key(secret: str) -> bytes:
    """Decode Standard Webhooks secrets; support Whop production and sandbox prefixes."""
    value = secret.strip()
    if value.startswith("whsec_"):
        encoded = value[6:]
    elif value.startswith("ws_"):
        encoded = value[3:]
    else:
        return value.encode("utf-8")
    try:
        return base64.b64decode(encoded + "=" * (-len(encoded) % 4), validate=True)
    except (binascii.Error, ValueError):
        return encoded.encode("utf-8")


def verify_signature(payload: bytes, headers: dict) -> dict:
    if not WHOP_WEBHOOK_SECRET:
        raise ValueError("WHOP_WEBHOOK_SECRET is not configured")
    h = {str(k).lower(): str(v) for k, v in headers.items()}
    webhook_id = h.get("webhook-id", "")
    timestamp = h.get("webhook-timestamp", "")
    signature = h.get("webhook-signature", "")
    if not webhook_id or not timestamp or not signature:
        raise ValueError("Missing webhook verification headers")
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise ValueError("Invalid webhook timestamp") from exc
    if abs(time.time() - ts) > 300:
        raise ValueError("Webhook timestamp outside 5 minute tolerance")

    signed = f"{webhook_id}.{timestamp}.".encode("utf-8") + payload
    digest = base64.b64encode(
        hmac.new(_signing_key(WHOP_WEBHOOK_SECRET), signed, hashlib.sha256).digest()
    ).decode("ascii")
    passed = signature.split()
    if not any(
        item.startswith("v1,") and hmac.compare_digest(item[3:], digest)
        for item in passed
    ):
        raise ValueError("Invalid webhook signature")
    return json.loads(payload.decode("utf-8"))


def _token() -> str:
    return f"XAU-NEURAL-{secrets.token_hex(8).upper()}"


def _issue_and_activate(telegram_id: int, duration_days: int) -> tuple[str, str] | None:
    """Create a single-use token, consume it immediately, and activate the Telegram account."""
    raw_token = _token()
    if not database.add_token_to_pool(raw_token, duration_days=duration_days):
        return None
    if not database.activate_user_token(telegram_id, raw_token, duration_days):
        logger.error("Automatic activation failed telegram=%s duration=%s", telegram_id, duration_days)
        return None
    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
    return raw_token, token_hash


def handle_payment_succeeded(payment: dict) -> tuple[str, int, str] | None:
    metadata = payment.get("metadata") or {}
    order_id = str(metadata.get("neural_order_id") or "")
    payment_id = str(payment.get("id") or "")
    plan = payment.get("plan") or {}
    plan_id = str(plan.get("id") or payment.get("plan_id") or "")
    if not order_id or not payment_id:
        raise FulfillmentRetryableError(
            f"Payment missing order/payment identity payment={payment_id}"
        )

    order = whop_storage.get_order(order_id)
    if order is None:
        raise FulfillmentRetryableError(f"Unknown Neural Gold order_id={order_id}")

    duration = PLAN_DURATIONS.get(plan_id) or PLAN_DURATIONS.get(order["plan_id"])
    if duration is None or duration != order["duration_days"]:
        whop_storage.update_order(
            order_id, status="rejected_plan_mismatch", payment_id=payment_id
        )
        return None

    existing = whop_storage.get_order_by_payment(payment_id)
    if existing is not None and existing.get("token_hash"):
        return None

    issued = _issue_and_activate(int(order["telegram_id"]), duration)
    if issued is None:
        whop_storage.update_order(
            order_id, status="fulfillment_failed", payment_id=payment_id
        )
        raise FulfillmentRetryableError(
            f"Automatic activation failed order={order_id} payment={payment_id}"
        )

    raw_token, token_hash = issued
    membership = payment.get("membership") or {}
    whop_storage.update_order(
        order_id,
        payment_id=payment_id,
        membership_id=str(membership.get("id") or "") or None,
        token_hash=token_hash,
        paid_at=datetime.now(timezone.utc),
        status="active",
    )
    logger.info(
        "Whop payment fulfilled payment=%s order=%s telegram=%s duration=%sd",
        payment_id,
        order_id,
        order["telegram_id"],
        duration,
    )
    return raw_token, duration, order_id


def _event_metadata(event_type: str, data: dict) -> tuple[dict, str | None, str | None]:
    metadata = data.get("metadata") or {}
    payment_id = str(data.get("id") or "") or None
    membership_id = None

    if event_type.startswith("refund."):
        payment = data.get("payment") or {}
        payment_id = str(payment.get("id") or payment_id or "") or None
        metadata = payment.get("metadata") or metadata
        membership = payment.get("membership") or {}
        membership_id = str(membership.get("id") or "") or None
    elif event_type.startswith("membership."):
        membership_id = str(data.get("id") or "") or None

    return metadata, payment_id, membership_id


def _is_full_successful_refund(data: dict) -> bool:
    if str(data.get("status") or "").lower() != "succeeded":
        return False
    payment = data.get("payment") or {}
    try:
        return float(data.get("amount")) >= float(payment.get("total"))
    except (TypeError, ValueError):
        return False


def handle_event(event_type: str, data: dict) -> tuple[str, int, str] | None:
    if event_type == "payment.succeeded":
        return handle_payment_succeeded(data)

    metadata, payment_id, membership_id = _event_metadata(event_type, data)
    order_id = str(metadata.get("neural_order_id") or "")
    order = whop_storage.get_order(order_id) if order_id else None

    if order is None and payment_id:
        order = whop_storage.get_order_by_payment(payment_id)
        order_id = str(order["id"]) if order else ""
    if order is None and membership_id:
        order = whop_storage.get_order_by_membership(membership_id)
        order_id = str(order["id"]) if order else ""

    if not order_id:
        return None

    if event_type == "payment.failed":
        whop_storage.update_order(order_id, status="payment_failed", payment_id=payment_id)
    elif event_type in {"refund.created", "refund.updated"}:
        status = str(data.get("status") or "pending").lower()
        whop_storage.update_order(order_id, status=f"refund_{status}", payment_id=payment_id)
        if _is_full_successful_refund(data):
            whop_storage.revoke_order_access(order_id)
    elif event_type == "membership.deactivated":
        whop_storage.update_order(
            order_id, status="membership_deactivated", membership_id=membership_id
        )
        whop_storage.revoke_order_access(order_id)
    elif event_type == "membership.cancel_at_period_end_changed":
        whop_storage.update_order(
            order_id,
            status="cancel_at_period_end_changed",
            membership_id=membership_id,
        )
    elif event_type == "membership.activated":
        whop_storage.update_order(
            order_id, status="membership_active", membership_id=membership_id
        )
    return None


async def notify_customer(
    bot: Any, telegram_id: int, raw_token: str, duration_days: int, order_id: str
) -> None:
    try:
        asset = visual_path("success")
        if asset:
            try:
                with open(asset, "rb") as fh:
                    await bot.send_photo(
                        chat_id=telegram_id,
                        photo=fh,
                        caption="<b>PAYMENT CONFIRMED</b>\n<i>NEURAL GOLD v3.2</i>",
                        parse_mode="HTML",
                    )
            except Exception:
                logger.exception("Premium payment visual delivery failed")
        await bot.send_message(
            chat_id=telegram_id,
            text=(
                "<b>✓ PAYMENT VERIFIED</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Your <b>{duration_days}-day</b> Neural Gold access is now <b>ACTIVE</b>.\n\n"
                "Your Telegram account was activated automatically.\n"
                "A single-use activation token was generated and consumed securely as part of fulfillment."
            ),
            parse_mode="HTML",
        )
        whop_storage.update_order(
            order_id,
            notified_at=datetime.now(timezone.utc),
            status="customer_notified",
        )
    except Exception as exc:
        logger.exception(
            "Failed to notify Telegram user %s for order %s: %s",
            telegram_id,
            order_id,
            exc,
        )
        whop_storage.update_order(order_id, status="active_notification_failed")
