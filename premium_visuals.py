"""NEURAL GOLD v3.2 — consolidated Telegram UI layer."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def _active(update) -> bool:
    import auth
    user = update.effective_user
    return bool(user and auth.verify_token(user.id)[0])


def _days_label(days: int) -> str:
    return {7: "🕐 7 DAYS — TACTICAL TRIAL", 14: "📅 14 DAYS — STRATEGIC ENTRY", 30: "🗓️ 30 DAYS — FULL OPERATIONAL CONTROL"}[days]


def _checkout(update, days: int) -> str:
    import phase2_bot
    return phase2_bot.checkout_link(update.effective_user.id, days)


def home_keyboard(update):
    active = _active(update)
    rows = []
    if active:
        rows.append([InlineKeyboardButton("🧠 Neural Strikes", callback_data="screen:signal"), InlineKeyboardButton("📊 Structure Map", callback_data="screen:analysis")])
        rows.append([InlineKeyboardButton("👑 Operator Hub", callback_data="screen:account")])
    else:
        rows.append([InlineKeyboardButton("📈 Market Pulse 🔒", callback_data="screen:price"), InlineKeyboardButton("🧠 Neural Strikes 🔒", callback_data="screen:signal")])
        rows.append([InlineKeyboardButton("📊 Structure Map 🔒", callback_data="screen:analysis"), InlineKeyboardButton("👑 Operator Hub", callback_data="screen:account")])
    rows.extend([
        [InlineKeyboardButton("⚙️ System Sync", callback_data="screen:settings"), InlineKeyboardButton("🌐 Uplink", callback_data="screen:support")],
        [InlineKeyboardButton("💎 Premium Clearance", callback_data="screen:access")],
        [InlineKeyboardButton("⌂ MENU", callback_data="nav:home")],
    ])
    return InlineKeyboardMarkup(rows)


def access_keyboard(update):
    active = _active(update)
    rows = []
    if not active:
        rows.append([InlineKeyboardButton("🎯 SELECT CLEARANCE", callback_data="screen:price")])
        rows.append([InlineKeyboardButton("🔑 ACTIVATE TOKEN", callback_data="action:token"), InlineKeyboardButton("💳 I HAVE PAID", callback_data="paid:menu")])
    else:
        rows.append([InlineKeyboardButton("👑 OPERATOR HUB", callback_data="screen:account")])
    rows.append([InlineKeyboardButton("🌐 UPLINK", callback_data="screen:support")])
    rows.append([InlineKeyboardButton("⌂ MENU", callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)


def price_keyboard(update):
    import main
    if _active(update):
        return main._original_price_keyboard(update)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_days_label(7), url=_checkout(update, 7))],
        [InlineKeyboardButton(_days_label(14), url=_checkout(update, 14))],
        [InlineKeyboardButton(_days_label(30), url=_checkout(update, 30))],
        [InlineKeyboardButton("← BACK", callback_data="screen:access"), InlineKeyboardButton("⌂ MENU", callback_data="nav:home")],
    ])


async def render_access(update, context):
    import main
    active = _active(update)
    if active:
        user = update.effective_user
        db_user = main.database.get_user_by_telegram_id(user.id)
        expiry = main.database.normalize_datetime_utc(db_user.subscription_expiry) if db_user else None
        expiry_text = expiry.strftime("%d %b %Y • %H:%M UTC") if expiry else "—"
        text = (
            "<b>PREMIUM ACCESS NEURAL GOLD v3.2</b>\n"
            "-------------------------------------------------\n\n"
            "<b>🟢 CLEARANCE ACTIVE</b>\n\n"
            f"Access until <code>{expiry_text}</code>\n\n"
            "Your Alpha Terminal is synchronized."
        )
    else:
        text = (
            "<b>PREMIUM ACCESS NEURAL GOLD v3.2</b>\n"
            "-------------------------------------------------\n\n"
            "<i>\"Anda berada di dalam, tapi Anda belum 'terhubung'.\"</i>\n\n"
            "Pasar XAU/USD adalah mesin pemindah uang dari trader amatir ke institusi. Tanpa akses ke saraf pusat kami, Anda hanyalah statistik dalam data likuiditas mereka.\n\n"
            "<b>Jangan hanya trading. Dominasi.</b>\n\n"
            "Aktifkan enkripsi premium untuk menghentikan penebakan dan mulai melihat struktur pasar yang sebenarnya:\n\n"
            "📈 Institutional Orderflow (Live XAU/USD)\n"
            "🧠 Neural Precision Strikes (Signals)\n"
            "📊 Market Architecture (Structural Analysis)\n"
            "👑 Alpha Terminal (Private Dashboard)\n\n"
            "<b>SELECT YOUR CLEARANCE LEVEL:</b>\n"
            "Gunakan <b>🎯 SELECT CLEARANCE</b> untuk membuka pilihan 7/14/30 hari.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>🔑 ACTIVATE TOKEN</b> setelah pembelian dan masukkan token sekali pakai."
        )
    await main._present(update, text, access_keyboard(update))


async def render_price(update, context):
    import main
    if _active(update):
        await main._original_render_price(update, context)
        return
    text = (
        "<b>📈 MARKET PULSE // CLEARANCE</b>\n"
        "NEURAL GOLD v3.2\n"
        f"{main.DIVIDER}\n\n"
        "<i>Clearance levels control the duration of your premium connection.</i>\n\n"
        "<b>SELECT YOUR CLEARANCE LEVEL:</b>\n\n"
        "🕐 <b>7 DAYS — Tactical Trial</b>\n"
        "📅 <b>14 DAYS — Strategic Entry</b>\n"
        "🗓️ <b>30 DAYS — Full Operational Control</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>SELECT A CLEARANCE LEVEL TO CONTINUE.</b>"
    )
    await main._present(update, text, price_keyboard(update))


async def render_home(update, context, edit: bool = True):
    import main
    user = update.effective_user
    if user is None:
        return
    if _active(update):
        text = (
            "<b>NEURAL GOLD v3.2 // ALPHA TERMINAL</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Operator: <b>{main._safe_user_name(user)}</b>\n"
            "Status: CLEARANCE GRANTED ✅\n\n"
            "<i>\"Saraf pusat XAU/USD kini tersinkronisasi dengan akun Anda. Seluruh data market telah difilter; hanya presisi yang tersisa.</i>\n\n"
            "Gunakan modul di bawah untuk mendominasi aliran harga.\n\n"
            "<b>S E L E C T _ M O D U L E</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🧠 Neural Strikes (Signals)\n"
            "📊 Structure Map (Structural Analysis)\n"
            "👑 Operator Hub (Private Dashboard)\n"
            "⚙️ System Sync (Settings)\n"
            "🌐 Uplink (Support)"
        )
    else:
        text = (
            "<b>NEURAL GOLD v3.2 // ALPHA TERMINAL</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Operator: <b>{main._safe_user_name(user)}</b>\n"
            "Status: CLEARANCE PENDING ⏳\n\n"
            "<i>Market intelligence is visible. Premium signal layers remain encrypted until clearance is activated.</i>\n\n"
            "<b>S E L E C T _ M O D U L E</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📈 Market Pulse (Clearance Levels)\n"
            "🧠 Neural Strikes 🔒\n"
            "📊 Structure Map 🔒\n"
            "👑 Operator Hub (Private Dashboard)\n"
            "⚙️ System Sync (Settings)\n"
            "🌐 Uplink (Support)"
        )
    await main._present(update, text, home_keyboard(update), edit=edit)


async def callback_router(update, context):
    """Single UI owner; delegate only legacy Phase-2 service callbacks."""
    import main
    import auth
    import phase2_bot
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    data = query.data or ""

    if data in {"nav:home", "screen:home"}:
        await query.answer()
        await render_home(update, context)
        return
    if data == "nav:access" or data == "screen:access":
        await query.answer()
        await render_access(update, context)
        return
    if data == "screen:price":
        await query.answer()
        await render_price(update, context)
        return
    if data == "action:token":
        await query.answer()
        context.user_data["awaiting_token"] = True
        await main._present(update, "<b>🔑 ACTIVATE TOKEN</b>\n\nEnter your single-use activation token below to sync your clearance.", access_keyboard(update))
        return
    if data == "screen:signal" and not auth.verify_token(user.id)[0]:
        await query.answer("🔒 CLEARANCE REQUIRED", show_alert=True)
        await render_access(update, context)
        return
    if data == "screen:analysis" and not auth.verify_token(user.id)[0]:
        await query.answer("🔒 CLEARANCE REQUIRED", show_alert=True)
        await render_access(update, context)
        return

    # Phase-2 retains payment confirmation, language, support, and token
    # service callbacks without taking ownership of the main UI.
    await phase2_bot._callback_router(update, context)


async def unknown_text_handler(update, context):
    import phase2_bot
    await phase2_bot._unknown_text_handler(update, context)


def install() -> None:
    import main
    if getattr(main, "_original_render_price", None) is None:
        main._original_render_price = main.render_price
    if getattr(main, "_original_price_keyboard", None) is None:
        main._original_price_keyboard = main.price_keyboard
    main.home_keyboard = home_keyboard
    main.access_keyboard = access_keyboard
    main.price_keyboard = price_keyboard
    main.render_access = render_access
    main.render_price = render_price
    main.render_home = render_home
    main.callback_router = callback_router
    main.unknown_text_handler = unknown_text_handler
    main._emoji_ui_installed = True
