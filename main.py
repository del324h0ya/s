"""
main.py — Premium Telegram UI for the XAU/USD Neural Signal Engine.

The bot is intentionally command-light: customers navigate the product with
inline buttons instead of memorising commands. Commands remain available for
administration and token activation.
"""

import html
import logging
import os
import secrets
import sys
from datetime import datetime, timezone

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import api_handler
import auth
import database
from i18n import LANGUAGES, detect_language, language_buttons, t
from config import (
    ADMIN_TELEGRAM_ID,
    LOG_FILE,
    LOG_FORMAT,
    LOG_LEVEL,
    NEURAL_VERSION,
    TELEGRAM_BOT_TOKEN,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# PREMIUM UI CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

GOLD = "◆"
DIVIDER = "━━━━━━━━━━━━━━━━━━━━"

WHOP_CHECKOUT_URLS = {
    7: "https://whop.com/checkout/plan_ksl11weFJ0z41",
    14: "https://whop.com/checkout/plan_Yc1JnCIP8jgII",
    30: "https://whop.com/checkout/plan_JDgh0geRuoSFX",
}

PLAN_LABELS = {
    7: "7 DAYS • SHORT TERM",
    14: "14 DAYS • STANDARD",
    30: "30 DAYS • PREMIUM",
}

# Customer-facing Alpha-Senti terminology. Internal calculation keys remain
# unchanged for backward compatibility with the signal engine/database.
ALPHA_TERMS = {
    "rsi": "TEMPORAL MOMENTUM RESONANCE",
    "macd": "DUAL-PHASE CONVERGENCE MANIFOLD",
    "ema": "SYNAPTIC TREND ALIGNMENT",
    "stoch": "PROBABILISTIC FLUX",
    "atr": "VOLATILITY VARIANCE",
    "bollinger": "QUANTUM ENVELOPE POSITION",
}

SHORT_DESCRIPTION = (
    "NEURAL GOLD v3.2 — Premium XAU/USD market intelligence."
)
BOT_DESCRIPTION = (
    "NEURAL GOLD v3.2 — PREMIUM XAU/USD MARKET INTELLIGENCE\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Welcome, Trader.\n\n"
    "Real-time gold intelligence, built for fast decisions.\n\n"
    "Monitor the XAU/USD market through live pricing, neural signal reads, "
    "market structure and private account access."
)


def _lang(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "en"
    return database.get_user_language(user.id)


def _lang_text(update: Update, key: str) -> str:
    return t(_lang(update), key)


def _localized_text(update: Update, text: str) -> str:
    """Translate stable UI phrases while preserving live values and Alpha-Senti terms."""
    lang = _lang(update)
    if lang == "en":
        return text
    # Stable UI phrases that occur throughout the existing premium screens.
    replacements = {
        "LIVE MARKET FEED":"live_feed", "NEURAL SIGNAL":"neural_signal", "MARKET ANALYSIS":"analysis_title",
        "SELECT A MODULE":"select_module", "PREMIUM ACCESS ACTIVE":"premium_active", "ACCESS NOT ACTIVATED":"access_off",
        "Live intelligence unlocked.":"unlocked", "Activate access to unlock live intelligence.":"locked_hint",
        "Real-time gold intelligence, built for fast decisions.":"real_time",
        "Monitor the XAU/USD market through live pricing, neural signal reads, market structure and private account access.":"monitor",
        "Everything is one tap away.":"one_tap", "ACCOUNT INTELLIGENCE":"account_intel", "YOUR PREMIUM ACCESS":"your_access",
        "PREMIUM ACCESS":"premium_access", "NEURAL GOLD MEMBERSHIP":"membership", "Your access unlocks:":"unlocks",
        "ACCESS REQUIRED":"access_required", "Not activated":"not_activated", "ACTIVE":"active", "READY TO ACTIVATE":"ready",
        "SETTINGS":"settings_title", "INTERFACE CONTROL":"interface_control", "DISPLAY PROFILE":"display_profile",
        "Premium dark interface":"premium_dark", "Gold-accent navigation":"gold_nav", "Compact market cards":"compact_cards",
        "REGION":"region", "Language":"language_value", "Core settings are controlled by the bot configuration.":"core_settings",
        "PREMIUM SUPPORT":"support_title", "DIRECT ASSISTANCE":"direct_help",
        "Need help with access, token activation or account issues?":"support_need", "Support channel":"support_channel",
        "Tap the button below to contact the administrator.":"support_tap", "For security, never share your activation token publicly.":"security",
        "This module is part of the premium intelligence layer.":"locked",
        "Activate a valid subscription token to continue.":"activate_required",
        "Your account and token are verified automatically.":"verified_auto",
        "Your premium access is now active.":"activation_active", "Your intelligence modules are unlocked.":"modules_unlocked",
        "The token is invalid or has already been used.":"invalid_token", "Please refresh in a moment.":"please_refresh",
    }
    for phrase, key in replacements.items():
        text = text.replace(phrase, t(lang, key))
    return text


def _esc(value: object) -> str:
    return html.escape(str(value))


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _format_timestamp(value: str) -> str:
    """Render feed timestamps as compact UTC clock time for the terminal UI."""
    try:
        raw = value.replace("Z", "+00:00")
        return datetime.fromisoformat(raw).strftime("%H:%M:%S")
    except Exception:
        return _esc(value[-8:] if len(value) >= 8 else value)


def _safe_user_name(user) -> str:
    return _esc(user.first_name or "Trader")


def _nav_keyboard(update: Update, *rows: tuple[str, str], back: str = "home") -> InlineKeyboardMarkup:
    lang = _lang(update)
    keyboard = [[InlineKeyboardButton(label, callback_data=data)] for label, data in rows]
    keyboard.append([InlineKeyboardButton(t(lang, "back"), callback_data=f"nav:{back}"), InlineKeyboardButton(t(lang, "menu"), callback_data="nav:home")])
    return InlineKeyboardMarkup(keyboard)


def home_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang,"price"), callback_data="screen:price"), InlineKeyboardButton(t(lang,"signal"), callback_data="screen:signal")],
        [InlineKeyboardButton(t(lang,"analysis"), callback_data="screen:analysis"), InlineKeyboardButton(t(lang,"account"), callback_data="screen:account")],
        [InlineKeyboardButton(t(lang,"access"), callback_data="screen:access"), InlineKeyboardButton(t(lang,"settings"), callback_data="screen:settings")],
        [InlineKeyboardButton(t(lang,"support"), callback_data="screen:support")],
        [InlineKeyboardButton(t(lang,"back"), callback_data="nav:home"), InlineKeyboardButton(t(lang,"menu"), callback_data="nav:home")]])


def price_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"refresh"), callback_data="screen:price"), InlineKeyboardButton(t(lang,"signal"), callback_data="screen:signal")],
        [InlineKeyboardButton(t(lang,"market_analysis"), callback_data="screen:analysis")],
        [InlineKeyboardButton(t(lang,"back"), callback_data="nav:home"), InlineKeyboardButton(t(lang,"menu"), callback_data="nav:home")]])


def signal_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"new_signal"), callback_data="screen:signal"), InlineKeyboardButton(t(lang,"live_price"), callback_data="screen:price")],
        [InlineKeyboardButton(t(lang,"market_analysis"), callback_data="screen:analysis")],
        [InlineKeyboardButton(t(lang,"back"), callback_data="nav:home"), InlineKeyboardButton(t(lang,"menu"), callback_data="nav:home")]])


def account_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"access"), callback_data="screen:access")], [InlineKeyboardButton(t(lang,"refresh_status"), callback_data="screen:account")], [InlineKeyboardButton(t(lang,"back"), callback_data="nav:home"), InlineKeyboardButton(t(lang,"menu"), callback_data="nav:home")]])


def access_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    rows = [
        [InlineKeyboardButton("🟢 7 DAYS", url=WHOP_CHECKOUT_URLS[7])],
        [InlineKeyboardButton("🟡 14 DAYS", url=WHOP_CHECKOUT_URLS[14])],
        [InlineKeyboardButton("🔵 30 DAYS", url=WHOP_CHECKOUT_URLS[30])],
        [InlineKeyboardButton("💳 I HAVE PAID", callback_data="paid:menu")],
        [InlineKeyboardButton(t(lang, "activate"), callback_data="action:token")],
        [InlineKeyboardButton(t(lang, "account_status"), callback_data="screen:account")],
        [InlineKeyboardButton(t(lang, "support"), callback_data="screen:support")],
        [InlineKeyboardButton(t(lang, "back"), callback_data="nav:home"), InlineKeyboardButton(t(lang, "menu"), callback_data="nav:home")],
    ]
    return InlineKeyboardMarkup(rows)


def analysis_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang,"live_price"), callback_data="screen:price"), InlineKeyboardButton(t(lang,"signal"), callback_data="screen:signal")], [InlineKeyboardButton(t(lang,"refresh_analysis"), callback_data="screen:analysis")], [InlineKeyboardButton(t(lang,"back"), callback_data="nav:home"), InlineKeyboardButton(t(lang,"menu"), callback_data="nav:home")]])


def settings_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    rows = [[InlineKeyboardButton(t(lang,"language"), callback_data="settings:language")], [InlineKeyboardButton(t(lang,"interface"), callback_data="noop")], [InlineKeyboardButton(t(lang,"timezone"), callback_data="noop")], [InlineKeyboardButton(t(lang,"data_mode"), callback_data="noop")], [InlineKeyboardButton(t(lang,"back"), callback_data="nav:home"), InlineKeyboardButton(t(lang,"menu"), callback_data="nav:home")]]
    return InlineKeyboardMarkup(rows)


def language_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    rows = [[InlineKeyboardButton(label, callback_data=data)] for label, data in language_buttons()]
    rows.append([InlineKeyboardButton(t(lang,"back"), callback_data="nav:home"), InlineKeyboardButton(t(lang,"menu"), callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)


def support_keyboard(update: Update) -> InlineKeyboardMarkup:
    lang = _lang(update)
    rows = []
    if ADMIN_TELEGRAM_ID:
        rows.append([InlineKeyboardButton(t(lang,"contact"), url=f"tg://user?id={ADMIN_TELEGRAM_ID}")])
    rows.append([InlineKeyboardButton(t(lang,"back"), callback_data="nav:home"), InlineKeyboardButton(t(lang,"menu"), callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════════════════════════════
# SCREEN RENDERERS
# ═══════════════════════════════════════════════════════════════════════

async def render_home(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = True) -> None:
    user = update.effective_user
    if user is None:
        return

    db_user = database.get_user_by_telegram_id(user.id)
    active = False
    if db_user:
        active, _ = auth.verify_token(user.id)

    if not active:
        await render_access(update, context)
        return

    access_line = "● PREMIUM ACCESS ACTIVE"
    access_hint = "Live intelligence unlocked."

    text = (
        f"<b>NEURAL GOLD</b>  <code>{NEURAL_VERSION}</code>\n"
        f"<i>PREMIUM XAU/USD MARKET INTELLIGENCE</i>\n"
        f"{DIVIDER}\n\n"
        f"Welcome, <b>{_safe_user_name(user)}</b>.\n\n"
        f"<b>Real-time gold intelligence, built for fast decisions.</b>\n"
        f"Monitor the XAU/USD market through live pricing, neural\n"
        f"signal reads, market structure and private account access.\n\n"
        f"<b>{GOLD} {access_line}</b>\n"
        f"<i>{access_hint}</i>\n\n"
        f"<b>SELECT A MODULE</b>\n"
        f"Price  •  Signal  •  Analysis  •  Account\n"
        f"Access  •  Settings  •  Support\n\n"
        f"<i>Everything is one tap away.</i>"
    )
    await _present(update, text, home_keyboard(update), edit=edit)


async def render_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return

    valid, _ = auth.verify_token(user.id)
    if not valid:
        await render_locked(update, "price")
        return

    await _answer_loading(update, "Syncing live market feed…")
    try:
        data = await api_handler.get_cached_or_fresh_price(user.id)
        bid = float(data["bid"])
        ask = float(data["ask"])
        mid = (bid + ask) / 2
        change = float(data.get("change", 0))
        pct = float(data.get("change_percent", 0))
        change_mark = "+" if change >= 0 else ""
        source = _esc(data.get("source", "Live feed"))
        raw_ts = str(data.get("timestamp", "—"))
        timestamp = _format_timestamp(raw_ts)
        move_icon = "📈" if change > 0 else ("📉" if change < 0 else "⚡️")
        text = (
            f"<b>🟢 LIVE MARKET FEED</b>\n"
            f"<pre>┍━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┑\n"
            f"  SYSTEM: MARKET_DATA_SATELLITE // XAU_USD\n"
            f"  STATUS: [LIVE]          TIMESTAMP: {timestamp}\n"
            f"┕━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┙\n"
            f"  SYMBOL     XAU/USD · GOLD SPOT\n"
            f"  PRICE      {_money(mid)} ⚡️ [STABLE]\n"
            f"  BID/ASK    {_money(bid)} / {_money(ask)}\n"
            f"  ─────────────────────────────────────────────\n"
            f"  SESSION HIGH:  {_money(float(data['high']))}\n"
            f"  SESSION LOW:   {_money(float(data['low']))}\n"
            f"  NET CHANGE:    {change_mark}{change:.2f} ({change_mark}{pct:.2f}%) {move_icon}\n"
            f"  ─────────────────────────────────────────────\n"
            f"  UPLINK:  {source}   // MODE: LIVE\n"
            f"</pre>"
            f"<i>Market feed may vary slightly by venue.</i>"
        )
        await _present(update, text, price_keyboard(update))
    except Exception as exc:
        logger.exception("Premium price screen failed: %s", exc)
        await _present(update, "<b>🟢 LIVE MARKET FEED</b>\n\n<pre>┍━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┑\n  STATUS: [OFFLINE]\n  MARKET DATA UPLINK TEMPORARILY UNAVAILABLE\n┕━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┙</pre>\nPlease refresh in a moment.", price_keyboard(update))


async def render_signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return

    valid, _ = auth.verify_token(user.id)
    if not valid:
        await render_locked(update, "signal")
        return

    await _answer_loading(update, "Building neural signal…")
    try:
        data = await api_handler.get_cached_or_fresh_price(user.id)
        indicators = api_handler._simulate_technical_indicators(float(data["bid"]), float(data.get("change_percent", 0)))
        signal = api_handler._determine_signal(float(data["bid"]), indicators)
        direction = signal["direction"]
        icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}[direction]
        confidence = float(signal["confidence"])
        confidence_tag = "HIGH" if confidence >= 70 else ("MODERATE" if confidence >= 55 else "MARGINAL")
        setup = "AWAITING CONFIRMATION" if direction == "HOLD" else f"{_money(signal['entry_low'])} — {_money(signal['entry_high'])}"
        align = "POSITIVE" if "BULLISH" in str(indicators.get("ema_trend", "")) else ("NEGATIVE" if "BEARISH" in str(indicators.get("ema_trend", "")) else "NEUTRAL")
        text = (
            f"<b>🟡 NEURAL SIGNAL</b>\n"
            f"<i>Designed as an institutional intelligence brief</i>\n"
            f"<pre>◤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◥\n"
            f"   NEURAL-SIGNAL // ALGO-READ : XAU_USD\n"
            f"   OPERATIONAL STATUS: SCANNING...\n"
            f"◣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◢\n"
            f"  SIGNAL:      {icon} {direction}\n"
            f"  CONFIDENCE:  {confidence:.1f}% [{confidence_tag}]\n"
            f"  MOMENTUM:    {_esc(signal['momentum'])}\n"
            f"  LIQUIDITY:   {_esc(signal['liquidity'])}\n"
            f"  VOLATILITY:   {_esc(signal['volatility'])}\n"
            f"  ─────────────────────────────────────────────\n"
            f"  EXECUTION MAP:\n"
            f"  ▸ ENTRY:    [{_esc(setup)}]\n"
            f"  ▸ TP_1:     {_money(signal['tp1']) if signal['tp1'] else '—'}  |  TP_2: {_money(signal['tp2']) if signal['tp2'] else '—'}  |  TP_3: {_money(signal['tp3']) if signal['tp3'] else '—'}\n"
            f"  ▸ STOP_LOSS: {_money(signal['sl']) if signal['sl'] else '—'}  |  R:R: 1 : {signal['risk_reward']}\n"
            f"  ─────────────────────────────────────────────\n"
            f"  ALPHA-SENTI MATRIX:\n"
            f"  [TEMPORAL MOMENTUM RESONANCE]: {indicators['rsi']}\n"
            f"  [DUAL-PHASE CONVERGENCE MANIFOLD]: {indicators['macd_hist']:+.2f}\n"
            f"  [SYNAPTIC TREND ALIGNMENT]: {_esc(indicators['ema_trend']).upper()}\n"
            f"  [PROBABILISTIC FLUX]: {indicators['stoch_k']} | [SYNAPTIC ALIGNMENT]: {align}\n"
            f"  ─────────────────────────────────────────────\n"
            f"  LOG: Algorithmic projection layer active.\n"
            f"</pre>"
            f"<i>Algorithmic projection — not financial advice.</i>"
        )
        await _present(update, text, signal_keyboard(update))
    except Exception as exc:
        logger.exception("Signal screen failed: %s", exc)
        await _present(update, "<b>🟡 NEURAL SIGNAL</b>\n\n<pre>◤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◥\n  STATUS: SIGNAL ENGINE UNAVAILABLE\n◣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◢</pre>\nPlease refresh in a moment.", signal_keyboard(update))


async def render_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return
    valid, _ = auth.verify_token(user.id)
    if not valid:
        await render_locked(update, "analysis")
        return

    await _answer_loading(update, "Reading market structure…")
    try:
        data = await api_handler.get_cached_or_fresh_price(user.id)
        bid = float(data["bid"])
        pct = float(data.get("change_percent", 0))
        indicators = api_handler._simulate_technical_indicators(bid, pct)
        signal = api_handler._determine_signal(bid, indicators)
        bias = _esc(signal["momentum"])
        bias_icon = _bias_icon(signal["momentum"])
        rsi = float(indicators["rsi"])
        stoch = float(indicators["stoch_k"])
        rsi_state = "OVERSOLD" if rsi < 30 else ("OVERBOUGHT" if rsi > 70 else "NEUTRAL")
        stoch_state = "OVERSOLD" if stoch < 20 else ("OVERBOUGHT" if stoch > 80 else "NEUTRAL")
        text = (
            f"<b>🔵 MARKET ANALYSIS</b>\n"
            f"<i>Designed as a quantitative deep-dive</i>\n"
            f"<pre>⌁─────────────────────────────────────────────⌁\n"
            f"  ANALYSIS_STRUCTURE :: MOMENTUM &amp; VOLATILITY\n"
            f"⌁─────────────────────────────────────────────⌁\n"
            f"  MARKET BIAS:   {bias_icon} {bias.upper()}\n"
            f"  ─────────────────────────────────────────────\n"
            f"  ALPHA-SENTI MATRIX:\n"
            f"  ▸ TEMPORAL MOMENTUM RESONANCE:    {indicators['rsi']} [{rsi_state}]\n"
            f"  ▸ DUAL-PHASE CONVERGENCE MANIFOLD: {indicators['macd_hist']:+.2f}\n"
            f"  ▸ SYNAPTIC TREND ALIGNMENT:        {_esc(indicators['ema_trend'])}\n"
            f"  ▸ PROBABILISTIC FLUX:               {indicators['stoch_k']} [{stoch_state}]\n"
            f"  ▸ VOLATILITY VARIANCE:               {indicators['atr']}\n"
            f"  ▸ QUANTUM ENVELOPE POSITION:        {_esc(indicators['bb_position']).upper()}\n"
            f"  ─────────────────────────────────────────────\n"
            f"  LIQUIDITY MODEL:\n"
            f"  ▸ LEVEL:         {_esc(signal['liquidity']).upper()}\n"
            f"  ▸ CONFIDENCE:    {signal['confidence']}%\n"
            f"  ─────────────────────────────────────────────\n"
            f"  SOURCE: SIGNAL_ENGINE_C2 // LIVE FEED LINKED\n"
            f"</pre>"
            f"<i>Analysis generated from the current feed and signal engine.</i>"
        )
        await _present(update, text, analysis_keyboard(update))
    except Exception as exc:
        logger.exception("Analysis screen failed: %s", exc)
        await _present(update, "<b>🔵 MARKET ANALYSIS</b>\n\n<pre>⌁─────────────────────────────────────────────⌁\n  STATUS: ANALYSIS ENGINE UNAVAILABLE\n⌁─────────────────────────────────────────────⌁</pre>\nPlease refresh in a moment.", analysis_keyboard(update))


def _bias_icon(momentum: str) -> str:
    if "BULLISH" in momentum:
        return "🟢"
    if "BEARISH" in momentum:
        return "🔴"
    return "🟡"


async def render_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return
    db_user = database.get_user_by_telegram_id(user.id)
    if db_user is None:
        text = (
            f"<b>♛ ACCOUNT</b>\n{DIVIDER}\n\n"
            f"Profile not registered yet.\n\n"
            f"Tap <b>ACCESS / PLANS</b> to activate your account."
        )
    else:
        valid, reason = auth.verify_token(user.id)
        expiry = database.normalize_datetime_utc(db_user.subscription_expiry)
        expiry_text = expiry.strftime("%d %b %Y • %H:%M UTC") if expiry else "Not activated"
        status = "ACTIVE" if valid else reason.replace("_", " ").upper()
        status_icon = "🟢" if valid else "○"
        text = (
            f"<b>♛ ACCOUNT INTELLIGENCE</b>\n"
            f"<i>YOUR PREMIUM ACCESS</i>\n"
            f"{DIVIDER}\n\n"
            f"<b>{status_icon} {status}</b>\n\n"
            f"Telegram ID  <code>{user.id}</code>\n"
            f"Username     <code>@{_esc(user.username or 'N/A')}</code>\n"
            f"Access until <code>{expiry_text}</code>\n\n"
            f"<i>Your private access status is checked in real time.</i>"
        )
    await _present(update, text, account_keyboard(update))


async def render_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    active = False
    if user:
        active, _ = auth.verify_token(user.id)

    state = "ACTIVE" if active else "READY TO ACTIVATE"
    icon = "🟢" if active else "◆"
    text = (
        f"<b>◆ PREMIUM ACCESS</b>\n"
        f"<i>NEURAL GOLD MEMBERSHIP</i>\n"
        f"{DIVIDER}\n\n"
        f"<b>{icon} {state}</b>\n\n"
        f"Your access unlocks:\n"
        f"◈ Live XAU/USD pricing\n"
        f"◎ Neural trade signals\n"
        f"⌁ Market structure analysis\n"
        f"♛ Private account dashboard\n\n"
        f"<b>ACCESS PACKAGES</b>\n"
        f"7 DAYS   •   SHORT TERM\n"
        f"14 DAYS  •   STANDARD\n"
        f"30 DAYS  •   PREMIUM\n\n"
        f"<i>Enter your single-use activation token after purchase.</i>"
    )
    await _present(update, text, access_keyboard(update))


async def render_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"<b>⚙ SETTINGS</b>\n"
        f"<i>INTERFACE CONTROL</i>\n"
        f"{DIVIDER}\n\n"
        f"<b>DISPLAY PROFILE</b>\n"
        f"◈ Premium dark interface\n"
        f"◆ Gold-accent navigation\n"
        f"⌁ Compact market cards\n\n"
        f"<b>REGION</b>\n"
        f"Timezone  <code>Asia/Jakarta</code>\n"
        f"Language  <code>{_lang(update).upper()}</code>\n\n"
        f"<i>Core settings are controlled by the bot configuration.</i>"
    )
    await _present(update, text, settings_keyboard(update))


async def render_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"<b>◉ PREMIUM SUPPORT</b>\n"
        f"<i>DIRECT ASSISTANCE</i>\n"
        f"{DIVIDER}\n\n"
        f"Need help with access, token activation or account issues?\n\n"
        f"<b>Support channel</b>\n"
        f"Tap the button below to contact the administrator.\n\n"
        f"<i>For security, never share your activation token publicly.</i>"
    )
    await _present(update, text, support_keyboard(update))


async def render_locked(update: Update, module: str) -> None:
    labels = {
        "price": "LIVE PRICE",
        "signal": "NEURAL SIGNAL",
        "analysis": "MARKET ANALYSIS",
    }
    label = labels.get(module, module.upper())
    text = (
        f"<b>🔒 {label}</b>\n"
        f"{DIVIDER}\n\n"
        f"This module is part of the premium intelligence layer.\n\n"
        f"<b>ACCESS REQUIRED</b>\n"
        f"Activate a valid subscription token to continue.\n\n"
        f"<i>Your account and token are verified automatically.</i>"
    )
    await _present(update, text, access_keyboard(update))


# ═══════════════════════════════════════════════════════════════════════
# TELEGRAM PRESENTATION HELPERS
# ═══════════════════════════════════════════════════════════════════════

async def _answer_loading(update: Update, text: str) -> None:
    query = update.callback_query
    if query:
        try:
            await query.answer(text, show_alert=False)
        except Exception:
            pass


async def _present(
    update: Update,
    text: str,
    keyboard: InlineKeyboardMarkup,
    edit: bool = True,
) -> None:
    query = update.callback_query
    if query and edit:
        try:
            await query.edit_message_text(text=_localized_text(update, text), parse_mode="HTML", reply_markup=keyboard)
            return
        except Exception as exc:
            logger.debug("Could not edit callback message: %s", exc)

    if update.message:
        await update.message.reply_text(_localized_text(update, text), parse_mode="HTML", reply_markup=keyboard)


# ═══════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return
    try:
        existing = database.get_user_by_telegram_id(user.id)
        if existing is None:
            database.create_user(user.id, user.username, user.first_name, detect_language(user.language_code))
            logger.info("New user registered: %d (%s)", user.id, user.username)
    except Exception as exc:
        logger.exception("Failed to register user during /start: %s", exc)
    active, _ = auth.verify_token(user.id)
    if not active:
        await render_access(update, context)
        return
    await render_home(update, context, edit=False)


async def activate_token_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_token: str) -> None:
    """Activate a single-use token and return the user to the premium dashboard."""
    user = update.effective_user
    if user is None:
        return

    existing = database.get_user_by_telegram_id(user.id)
    if existing is None:
        database.create_user(user.id, user.username, user.first_name)

    import hashlib
    from sqlalchemy import select
    from database import TokenPool, _get_session

    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
    session = _get_session()
    try:
        entry = session.scalar(
            select(TokenPool).where(TokenPool.token_hash == token_hash, TokenPool.is_used == False)  # noqa: E712
        )
        duration = entry.duration_days if entry else 30
    finally:
        session.close()

    success = database.activate_user_token(user.id, raw_token, duration)
    if success:
        db_user = database.get_user_by_telegram_id(user.id)
        expiry = database.normalize_datetime_utc(db_user.subscription_expiry) if db_user else None
        expiry_text = expiry.strftime("%d %b %Y • %H:%M UTC") if expiry else "—"
        text = (
            f"<b>✓ ACCESS ACTIVATED</b>\n{DIVIDER}\n\n"
            f"Your premium access is now active.\n\n"
            f"Expires  <code>{expiry_text}</code>\n"
            f"Package  <b>{duration} days</b>\n\n"
            f"Your intelligence modules are unlocked."
        )
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=home_keyboard(update))
    else:
        await update.message.reply_text(
            "<b>✕ ACTIVATION FAILED</b>\n\n"
            "The token is invalid or has already been used.\n\n"
            "Tap <b>ACCESS / PLANS</b> to try again.",
            parse_mode="HTML",
            reply_markup=access_keyboard(update),
        )


async def token_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Accept a token after the user taps ACTIVATE TOKEN."""
    if not context.user_data.get("awaiting_token"):
        return
    context.user_data["awaiting_token"] = False
    raw_token = (update.message.text or "").strip()
    if not raw_token:
        await update.message.reply_text("Please send the activation token.", reply_markup=access_keyboard(update))
        return
    try:
        await activate_token_for_user(update, context, raw_token)
    except Exception as exc:
        logger.exception("Interactive token activation failed: %s", exc)
        await update.message.reply_text("⚠ Activation service temporarily unavailable.", parse_mode="HTML", reply_markup=access_keyboard(update))


async def token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback activation command for users who prefer commands."""
    if not context.args:
        await update.message.reply_text(
            "<b>🔑 ACTIVATE ACCESS</b>\n\n"
            "Tap the activation button and enter your single-use token.",
            parse_mode="HTML",
            reply_markup=access_keyboard(update),
        )
        return
    try:
        await activate_token_for_user(update, context, " ".join(context.args).strip())
    except Exception as exc:
        logger.exception("Error during /token: %s", exc)
        await update.message.reply_text("⚠ Activation service temporarily unavailable.", parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        active, _ = auth.verify_token(user.id)
        if not active:
            await render_access(update, context)
            return
    await render_home(update, context, edit=False)


# ═══════════════════════════════════════════════════════════════════════
# ADMIN HANDLERS
# ═══════════════════════════════════════════════════════════════════════

@auth.require_admin
async def addtoken_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) == 0:
        generated, days = secrets.token_urlsafe(24), 30
    elif len(args) == 1 and args[0].isdigit():
        generated, days = secrets.token_urlsafe(24), int(args[0])
    else:
        generated = args[0].strip()
        days = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 30
    try:
        if database.add_token_to_pool(generated, duration_days=days):
            await update.message.reply_text(
                f"<b>✓ TOKEN CREATED</b>\n\n<code>{generated}</code>\n\nDuration <b>{days} days</b>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text("<b>✕ TOKEN CREATION FAILED</b>", parse_mode="HTML")
    except Exception:
        logger.exception("Error in /addtoken")
        await update.message.reply_text("⚠ Internal error.", parse_mode="HTML")


@auth.require_admin
async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        users = database.list_all_users()
        if not users:
            await update.message.reply_text("No registered users.")
            return
        lines = [f"<b>USERS • {len(users)}</b>", DIVIDER]
        for u in users:
            icon = "🟢" if u["is_active"] else "○"
            exp = u["subscription_expiry"][:16] if u["subscription_expiry"] else "—"
            lines.append(f"{icon} <code>{u['telegram_id']}</code> @{_esc(u['username'] or '-')} • {exp}")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception:
        logger.exception("Error in /listusers")
        await update.message.reply_text("⚠ Could not fetch users.", parse_mode="HTML")


@auth.require_admin
async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].strip().lstrip("-").isdigit():
        await update.message.reply_text("Usage: <code>/revoke TELEGRAM_ID</code>", parse_mode="HTML")
        return
    target_id = int(context.args[0].strip())
    try:
        success = database.revoke_user(target_id)
        await update.message.reply_text(
            f"{'✓' if success else '✕'} User <code>{target_id}</code> {'revoked' if success else 'not found'}.",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Error in /revoke")
        await update.message.reply_text("⚠ Internal error.", parse_mode="HTML")


async def paid_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notify the configured admin that a customer reports a completed Whop payment."""
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    try:
        await query.answer("Payment notice sent.", show_alert=False)
    except Exception:
        pass

    username = f"@{user.username}" if user.username else "(no username)"
    text = (
        "<b>💳 PAYMENT NOTICE</b>\n"
        f"{DIVIDER}\n"
        f"Customer: <b>{_esc(user.first_name or 'Trader')}</b>\n"
        f"Username: <code>{_esc(username)}</code>\n"
        f"Telegram ID: <code>{user.id}</code>\n\n"
        "Customer reports that a Whop payment was completed.\n"
        "Verify the Whop order manually, then issue the matching token."
    )
    if ADMIN_TELEGRAM_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=text,
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("Failed to send payment notice to admin")

    await query.message.reply_text(
        "<b>PAYMENT NOTICE REGISTERED</b>\n\n"
        "Your payment notice has been sent to support. "
        "After manual verification, the administrator will provide your single-use activation token.",
        parse_mode="HTML",
        reply_markup=access_keyboard(update),
    )

# ═══════════════════════════════════════════════════════════════════════
# CALLBACK ROUTER
# ═══════════════════════════════════════════════════════════════════════

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    data = query.data or ""

    if data == "noop":
        await query.answer("This setting is controlled by the bot configuration.", show_alert=True)
        return

    if data == "paid:menu":
        await paid_confirmation(update, context)
        return

    if data.startswith("nav:"):
        try:
            await query.answer()
        except Exception:
            pass
        target = data.split(":", 1)[1]
        if target == "home":
            await render_home(update, context)
        else:
            await render_home(update, context)
        return

    if data.startswith("screen:"):
        target = data.split(":", 1)[1]
        if target in {"home", "account", "access", "settings", "support"}:
            try:
                await query.answer()
            except Exception:
                pass
        if target == "home":
            await render_home(update, context)
        elif target == "price":
            await render_price(update, context)
        elif target == "signal":
            await render_signal(update, context)
        elif target == "analysis":
            await render_analysis(update, context)
        elif target == "account":
            await render_account(update, context)
        elif target == "access":
            await render_access(update, context)
        elif target == "settings":
            await render_settings(update, context)
        elif target == "support":
            await render_support(update, context)
        return

    if data.startswith("lang:"):
        lang = data.split(":", 1)[1]
        if lang not in LANGUAGES:
            lang = "en"
        database.set_user_language(query.from_user.id, lang)
        try:
            await query.answer(t(lang, "saved"))
        except Exception:
            pass
        await render_home(update, context)
        return

    if data == "settings:language":
        try:
            await query.answer()
        except Exception:
            pass
        lang = _lang(update)
        await _present(update, f"<b>🌐 {t(lang, 'choose_language')}</b>\n{DIVIDER}\n\n{t(lang, 'language_names')}", language_keyboard(update))
        return

    if data == "action:token":
        try:
            await query.answer()
        except Exception:
            pass
        context.user_data["awaiting_token"] = True
        try:
            await query.message.reply_text(
                "<b>🔑 SECURE ACTIVATION</b>\n\n"
                "Enter your single-use activation token below.",
                parse_mode="HTML",
                reply_markup=ForceReply(selective=True),
            )
        except Exception:
            await query.message.reply_text(
                "<b>🔑 SECURE ACTIVATION</b>\n\nEnter your single-use activation token.",
                parse_mode="HTML",
            )
        return


async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Never leave an unknown command unanswered."""
    await update.message.reply_text(
        "<b>NEURAL GOLD</b>\n\n"
        "⌁ Command not recognized.\n"
        "Use <b>/start</b> to open ACCESS / PLANS and the premium dashboard.",
        parse_mode="HTML",
        reply_markup=access_keyboard(update),
    )


async def unknown_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle arbitrary customer text without silently ignoring it."""
    if context.user_data.get("awaiting_token"):
        await token_text_handler(update, context)
        return
    await update.message.reply_text(
        "<b>NEURAL GOLD</b>\n\n"
        "⌁ Input not recognized.\n"
        "Use the premium menu below or tap <b>ACCESS / PLANS</b>.",
        parse_mode="HTML",
        reply_markup=access_keyboard(update),
    )


# ═══════════════════════════════════════════════════════════════════════
# ERROR / LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    logger.error("Unhandled exception: %s", error, exc_info=error)
    if isinstance(update, Update):
        query = update.callback_query
        if query:
            try:
                await query.edit_message_text(
                    "<b>NEURAL GOLD</b>\n\n⚠ <b>Module temporarily unavailable.</b>\nPlease tap <b>MENU</b> and try again.",
                    parse_mode="HTML",
                    reply_markup=home_keyboard(update),
                )
            except Exception:
                pass
        elif update.message:
            try:
                await update.message.reply_text(
                    "⚠ <b>Temporary service error</b>\nPlease try again.",
                    parse_mode="HTML",
                    reply_markup=home_keyboard(update),
                )
            except Exception:
                pass


async def post_init(application: Application) -> None:
    database.init_db()
    try:
        await application.bot.set_my_short_description(SHORT_DESCRIPTION)
        await application.bot.set_my_description(BOT_DESCRIPTION)
        await application.bot.set_my_commands(
            [
                ("start", "Open premium dashboard"),
                ("token", "Activate access token"),
                ("status", "View account status"),
                ("help", "Open dashboard"),
            ]
        )
        logger.info("Telegram premium profile metadata configured.")
    except Exception as exc:
        logger.warning("Could not configure Telegram profile metadata: %s", exc)


def setup_logging() -> None:
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    if not root.handlers:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(log_level)
        sh.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(sh)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

def build_application() -> Application:
    """Build the Telegram application for Belmo webhook processing."""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("token", token_command))
    application.add_handler(CommandHandler("status", lambda u, c: render_account(u, c)))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addtoken", addtoken_command))
    application.add_handler(CommandHandler("listusers", listusers_command))
    application.add_handler(CommandHandler("revoke", revoke_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler))
    application.add_handler(MessageHandler(filters.TEXT, unknown_text_handler))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_error_handler(global_error_handler)
    return application


def main() -> None:
    """Local-development fallback only. Belmo production uses app.py + webhook."""
    setup_logging()
    database.init_db()
    application = build_application()
    logger.info("Starting local polling mode.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
