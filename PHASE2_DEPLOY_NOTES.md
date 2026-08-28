# Phase 2 deploy notes

Phase 2 adds per-user Whop checkout sessions, signed Whop webhook fulfillment, token issuance, and Telegram delivery.

## Runtime environment

Set these Belmo variables:
- WHOP_API_KEY
- WHOP_COMPANY_ID
- WHOP_WEBHOOK_SECRET
- BELMO_PUBLIC_URL
- TELEGRAM_WEBHOOK_SECRET

Keep the existing Telegram, GoldAPI, database, and logging variables.

Whop webhook endpoint:
`POST /webhooks/whop`

Telegram webhook endpoint remains:
`POST /telegram/webhook`
