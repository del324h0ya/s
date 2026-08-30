import os
import time
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TEST")
os.environ.setdefault("GOLDAPI_API_KEY", "test")
os.environ.setdefault("ADMIN_TELEGRAM_ID", "0")
os.environ.setdefault("DATABASE_URL", "sqlite:///production_audit_test.db")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("BELMO_PUBLIC_URL", "")
os.environ.setdefault("WHOP_WEBHOOK_SECRET", "test-whop")

import price_sources


class GoldApiPriceTests(unittest.IsolatedAsyncioTestCase):
    async def test_goldapi_price_is_returned(self):
        payload = {
            "price": 3000.1,
            "bid": 3000.0,
            "ask": 3000.2,
            "high_price": 3010.0,
            "low_price": 2990.0,
            "ch": 5.0,
            "chp": 0.17,
            "timestamp": 1777500000,
        }
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value=payload)
        response.raise_for_status = lambda: None

        session = AsyncMock()
        session.__aenter__.return_value = session
        session.get.return_value.__aenter__.return_value = response
        session.get.return_value.__aexit__.return_value = None

        with patch.object(price_sources.aiohttp, "ClientSession", return_value=session):
            result = await price_sources.fetch_price_cascade()

        self.assertEqual(result["source"], "GOLD_API")
        self.assertEqual(result["symbol"], "XAU/USD")
        self.assertEqual(result["close"], 3000.1)

    async def test_goldapi_failure_is_truthfully_reported(self):
        with patch.object(price_sources, "fetch_goldapi", AsyncMock(side_effect=RuntimeError("rate limit"))):
            with self.assertRaisesRegex(RuntimeError, "LIVE FEED UNAVAILABLE"):
                await price_sources.fetch_price_cascade()


class WebhookStorageTests(unittest.TestCase):
    def test_update_id_deduplication(self):
        import database
        database.init_db()
        update_id = int(time.time() * 1000)
        self.assertTrue(database.claim_telegram_update(update_id))
        self.assertFalse(database.claim_telegram_update(update_id))
        database.mark_telegram_update(update_id, "processed")

    def test_failed_update_is_immediately_retryable(self):
        import database
        database.init_db()
        update_id = int(time.time() * 1000) + 1
        self.assertTrue(database.claim_telegram_update(update_id))
        database.mark_telegram_update(update_id, "failed", "test")
        self.assertTrue(database.claim_telegram_update(update_id))
        database.mark_telegram_update(update_id, "processed")


if __name__ == "__main__":
    unittest.main()
