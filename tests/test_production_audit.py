import asyncio
import os
import time
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TEST")
os.environ.setdefault("GOLDAPI_API_KEY", "test")
os.environ.setdefault("METALS_API_KEY", "test")
os.environ.setdefault("ADMIN_TELEGRAM_ID", "0")
os.environ.setdefault("DATABASE_URL", "sqlite:///production_audit_test.db")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("BELMO_PUBLIC_URL", "")
os.environ.setdefault("WHOP_WEBHOOK_SECRET", "test-whop")

import price_sources


class PriceFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_metals_api_fallback_is_used(self):
        fallback = {"source": "METALS_API", "symbol": "XAU/USD", "bid": 3000.0, "ask": 3000.2, "close": 3000.1, "high": 3000.1, "low": 3000.1, "change": 0.0, "change_percent": 0.0, "volume": "N/A", "timestamp": "2026-08-30T00:00:00+00:00", "exchange": "GLOBAL"}
        with patch.object(price_sources, "fetch_goldapi", AsyncMock(side_effect=RuntimeError("rate limit"))), patch.object(price_sources, "fetch_metals_api", AsyncMock(return_value=fallback)):
            result = await price_sources.fetch_price_cascade()
        self.assertEqual(result["source"], "METALS_API")
        self.assertGreater(result["close"], 0)


class WebhookStorageTests(unittest.TestCase):
    def test_update_id_deduplication(self):
        import database
        database.init_db()
        update_id = int(time.time() * 1000)
        self.assertTrue(database.claim_telegram_update(update_id))
        self.assertFalse(database.claim_telegram_update(update_id))
        database.mark_telegram_update(update_id, "processed")


if __name__ == "__main__":
    unittest.main()
