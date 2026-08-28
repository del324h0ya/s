# Premium UI Rewrite

## 2026-08-25

- Rebuilt the customer-facing Telegram experience around inline buttons.
- Added premium dark/gold visual hierarchy using Telegram HTML and Unicode UI glyphs.
- Added home dashboard with product explanation and access state.
- Added clickable Price, Signal, Analysis, Account, Access/Plans, Settings and Support modules.
- Added persistent bottom navigation pattern: Back left / Menu right.
- Added refresh controls for live price, signal and analysis.
- Added click-first token activation using a Telegram reply prompt.
- Retained `/token` as a fallback.
- Added automatic Telegram bot profile description and short description configuration.
- Reduced visible command clutter.
- Preserved existing MT5/API price engine and neural analysis engine.
- Preserved admin token, user listing and revoke commands.
- Preserved and strengthened timezone-safe datetime handling.
- Normalised SQLite naive datetimes to UTC-aware datetimes before comparisons.
