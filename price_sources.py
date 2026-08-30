"""XAU/USD market-price source using GoldAPI only.

Every returned price is obtained from GoldAPI. When GoldAPI is unavailable,
the caller receives a clear feed-unavailable error; no price is fabricated.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)
FAST_TIMEOUT = aiohttp.ClientTimeout(total=8)


class SourceUnavailable(Exception):
    pass


def _timestamp(value: Any) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    return str(value or datetime.now(timezone.utc).isoformat())


async def fetch_goldapi() -> dict[str, Any]:
    api_key = os.getenv("GOLDAPI_API_KEY", "").strip()
    if not api_key:
        raise SourceUnavailable("GoldAPI: no API key configured")

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.goldapi.io/api/price/XAU/USD",
            headers={"x-access-token": api_key, "Content-Type": "application/json"},
            timeout=FAST_TIMEOUT,
        ) as resp:
            if resp.status == 429:
                raise SourceUnavailable("GoldAPI: rate limit reached")
            if resp.status in (401, 403):
                raise SourceUnavailable("GoldAPI: authentication failed")
            resp.raise_for_status()
            data = await resp.json()

    price = data.get("price")
    bid = data.get("bid")
    ask = data.get("ask")
    if not all(isinstance(v, (int, float)) and v > 0 for v in (price, bid, ask)):
        raise SourceUnavailable("GoldAPI: invalid price/bid/ask")

    return {
        "source": "GOLD_API",
        "symbol": "XAU/USD",
        "bid": float(bid),
        "ask": float(ask),
        "close": float(price),
        "high": float(data.get("high_price", price)),
        "low": float(data.get("low_price", price)),
        "change": float(data.get("ch", data.get("change", 0.0)) or 0.0),
        "change_percent": float(data.get("chp", data.get("change_percent", 0.0)) or 0.0),
        "volume": "N/A",
        "timestamp": _timestamp(data.get("timestamp") or data.get("datetime")),
        "exchange": data.get("exchange", "FOREX"),
    }


async def fetch_price_cascade() -> dict[str, Any]:
    """Return the live GoldAPI price or raise a truthful unavailable error."""
    try:
        result = await fetch_goldapi()
        logger.info("Price fetched source=GOLD_API")
        return result
    except Exception as exc:
        logger.error("GoldAPI unavailable source=GOLD_API error=%s", exc)
        raise RuntimeError("LIVE FEED UNAVAILABLE") from exc
