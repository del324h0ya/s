# NEURAL GOLD — Premium Telegram UI

## UX changes

The bot is now designed as a product dashboard instead of a command list.

### Home
- Premium dark / gold visual language.
- Product positioning appears immediately after `/start`.
- Access state is visible at a glance.
- Primary modules are available as inline buttons.

### Navigation
Every secondary screen ends with:
- `← BACK` on the left.
- `⌂ MENU` on the right.

Users no longer need to remember `/price`, `/signal`, or `/status`.

### Price
Tap **PRICE** → live XAU/USD data is fetched and displayed.
The screen includes mid price, bid/ask, high/low, movement, source, and update timestamp.

### Signal
Tap **SIGNAL** → the existing neural signal engine is presented as a compact premium execution card.

### Analysis
Tap **ANALYSIS** → the existing technical/market engine is presented as a structured market-intelligence card.

### Account
Tap **ACCOUNT** → real-time subscription status, expiry, Telegram ID and username.

### Access
Tap **ACCESS / PLANS** → membership overview and secure token activation.
The activation flow is click-first: tap **ACTIVATE TOKEN**, then enter the single-use token in the Telegram reply field. The `/token` command remains as a fallback.

### Bot profile
At startup, `post_init()` updates Telegram's bot profile metadata:
- Short description: AI market intelligence for XAU/USD.
- Full description: premium product positioning.
- Minimal command menu: `/start`, `/token`, `/status`, `/help`.

This removes the feeling that the bot is a raw developer utility.

## Important Telegram limitation

The Telegram client can display `No messages here yet...` before the user presses **START**. That placeholder is controlled by Telegram and cannot be replaced by bot code. After START, the bot immediately sends the new premium dashboard.
