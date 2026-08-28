# NEURAL GOLD v3.2 — Belmo Phase 1 Deployment

## Runtime

Belmo Starter API Service:
- Python
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- One long-running HTTP service
- Telegram uses webhook mode

## Environment Variables

Set these in Belmo (do not upload `.env` with secrets):

```text
TELEGRAM_BOT_TOKEN=...
ADMIN_TELEGRAM_ID=...
BELMO_PUBLIC_URL=https://YOUR-BELMO-DOMAIN
TELEGRAM_WEBHOOK_SECRET=...
GOLDAPI_API_KEY=...
DATABASE_URL=sqlite:///xauusd_bot.db
WHOP_WEBHOOK_SECRET=...
LOG_LEVEL=INFO
```

## Telegram webhook

The application registers:

`POST /telegram/webhook`

Telegram sends the secret header automatically when `TELEGRAM_WEBHOOK_SECRET`
is configured.

## Health

`GET /health`

## Phase 1 payment flow

1. Customer sends `/start`.
2. Inactive customer is routed directly to ACCESS / PLANS.
3. Customer chooses 7D / 14D / 30D and opens the real Whop checkout.
4. Customer taps `I HAVE PAID`.
5. Bot sends a payment notice to the configured admin.
6. Admin verifies the Whop payment manually.
7. Admin creates a token with:
   - `/addtoken 7`
   - `/addtoken 14`
   - `/addtoken 30`
8. Admin sends the token to the customer.
9. Customer taps ACTIVATE TOKEN and enters the token.
10. Subscription expiry is calculated using timezone-aware UTC.

## Important

- MT5 is not used.
- No price is fabricated if GoldAPI is unavailable.
- SQLite is suitable for initial testing, but do not assume local container
  storage is durable forever. Move subscription state to an external
  persistent database before scaling paid production.
- The included `whop_webhook.py` is Phase 2 groundwork; it is not required
  for Phase 1 manual verification.
