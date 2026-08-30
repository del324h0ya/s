"""Whop checkout creation for Neural Gold Phase 2."""
from __future__ import annotations

import json
import uuid

import aiohttp

import whop_storage
from config import BELMO_PUBLIC_URL, WHOP_API_KEY, WHOP_COMPANY_ID

WHOP_API_BASE = "https://api.whop.com/api/v1"
WHOP_API_VERSION_DATE = "2026-08-25-2"

PLAN_IDS = {
    7: "plan_ksl11weFJ0z41",
    14: "plan_Yc1JnCIP8jgII",
    30: "plan_JDgh0geRuoSFX",
}


async def create_checkout_for_user(telegram_id: int, duration_days: int):
    plan_id = PLAN_IDS.get(duration_days)
    if not plan_id:
        return None, None, "unsupported_plan"
    if not WHOP_API_KEY:
        return None, None, "WHOP_API_KEY_not_configured"
    if not WHOP_COMPANY_ID:
        return None, None, "WHOP_COMPANY_ID_not_configured"

    order_id = f"ng_{uuid.uuid4().hex}"
    if not whop_storage.create_order(order_id, telegram_id, plan_id, duration_days):
        return None, None, "database_order_create_failed"

    payload = {
        "company_id": WHOP_COMPANY_ID,
        "plan_id": plan_id,
        "mode": "payment",
        "metadata": {
            "neural_order_id": order_id,
            "telegram_id": str(telegram_id),
            "duration_days": str(duration_days),
        },
        "redirect_url": BELMO_PUBLIC_URL or None,
    }
    headers = {
        "Authorization": f"Bearer {WHOP_API_KEY}",
        "Content-Type": "application/json",
        "Api-Version-Date": WHOP_API_VERSION_DATE,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{WHOP_API_BASE}/checkout_configurations",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                body = await response.text()
                if response.status >= 400:
                    return None, order_id, f"whop_http_{response.status}:{body}"
                data = json.loads(body)
    except Exception as exc:
        return None, order_id, f"whop_request_failed:{exc}"

    checkout_url = data.get("purchase_url") or data.get("checkout_url")
    checkout_id = data.get("id")
    if checkout_id:
        whop_storage.update_order(order_id, checkout_configuration_id=checkout_id)
    if not checkout_url:
        return None, order_id, "whop_missing_purchase_url"
    return checkout_url, order_id, None
