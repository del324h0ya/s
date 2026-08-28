"""XAU/USD price feed using GoldAPI.io.

No synthetic/fallback prices are generated. If GoldAPI is unavailable or
returns invalid data, the caller must show DATA OFFLINE / LIVE FEED UNAVAILABLE.
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


async def fetch_goldapi() -> dict[str, Any]:
    api_key = os.getenv("GOLDAPI_API_KEY", "").strip()
    if not api_key:
        raise SourceUnavailable("GoldAPI: no API key configured")

    url = "https://www.goldapi.io/api/price/XAU/USD"
    headers = {
        "x-access-token": api_key,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=FAST_TIMEOUT) as resp:
            if resp.status == 429:
                raise SourceUnavailable("GoldAPI: rate limit reached")
            if resp.status in (401, 403):
                raise SourceUnavailable("GoldAPI: authentication failed")
            resp.raise_for_status()
            data = await resp.json()

    price = data.get("price")
    bid = data.get("bid")
    ask = data.get("ask")
    if not isinstance(price, (int, float)) or price <= 0:
        raise SourceUnavailable("GoldAPI: invalid price")
    if not isinstance(bid, (int, float)) or bid <= 0:
        raise SourceUnavailable("GoldAPI: invalid bid")
    if not isinstance(ask, (int, float)) or ask <= 0:
        raise SourceUnavailable("GoldAPI: invalid ask")

    ts = data.get("datetime")
    if not ts:
        ts = datetime.now(timezone.utc).isoformat()

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
        "timestamp": str(ts),
        "exchange": data.get("exchange", "FOREX"),
    }


async def fetch_price_cascade() -> dict[str, Any]:
    try:
        result = await fetch_goldapi()
        logger.info("Price fetched from GoldAPI")
        return result
    except Exception as exc:
        logger.warning("GoldAPI unavailable: %s", exc)
        raise RuntimeError("LIVE FEED UNAVAILABLE") from exc
