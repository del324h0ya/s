# Phase 2 build/test scope

CI should verify dependency installation, Python syntax/undefined names, and the existing pytest suite.

Runtime verification after deployment:
1. GET /health returns status ok.
2. Telegram /start opens the access screen.
3. A plan button creates a unique Whop checkout session.
4. Whop payment.succeeded creates a single-use activation token and sends it to the matching Telegram account.
