# Production Security Review

## Token generation and storage
- `TokenPool.token_hash` stores SHA-256 hashes, not plaintext activation tokens.
- `/addtoken` is protected by `auth.require_admin`, which compares the Telegram user ID to `ADMIN_TELEGRAM_ID`.
- `/addtoken` returns the plaintext token only to the authenticated administrator through Telegram.
- Application logs record token creation/activation events without the raw token.
- Activation claims a token with one atomic SQL `UPDATE ... WHERE is_used=false`, preventing concurrent double-consumption.

## Webhook secrets
- Telegram webhook requests validate `X-Telegram-Bot-Api-Secret-Token`.
- Whop Standard Webhooks validate `webhook-id`, `webhook-timestamp`, and `webhook-signature`.
- Logs exclude secret values.

## Operational controls
- Rotate Telegram, Whop, GoldAPI, Metals-API and Sentry credentials through the hosting provider.
- Keep production database credentials outside Git.
- Run the 500-concurrent load test against staging before launch.
