"""NEURAL GOLD Phase 2 runtime UI and checkout patch."""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply

import auth
import main
from config import BELMO_PUBLIC_URL, TELEGRAM_BOT_TOKEN

logger = logging.getLogger("neural_gold.phase2_bot")

L = {
    "en": {"days7":"🟢 7 DAYS","days14":"🟡 14 DAYS","days30":"🔵 30 DAYS","paid":"💳 I HAVE PAID","language":"🌐 LANGUAGE","access_plans":"◆ ACCESS / PLANS","public_menu":"PUBLIC MENU","choose_language":"Choose your interface language before activation.","select_plan":"Select a subscription package to continue.","support_title":"◉ CONTACT SUPPORT","support_prompt":"Send your question or describe the issue in your next message.","support_routed":"Your message will be routed securely to support.","support_empty":"Please describe your issue in a message.","support_sent":"<b>SUPPORT REQUEST SENT</b>\n\nYour message has been routed to support. You will receive a response through Telegram."},
    "vi": {"days7":"🟢 7 NGÀY","days14":"🟡 14 NGÀY","days30":"🔵 30 NGÀY","paid":"💳 TÔI ĐÃ THANH TOÁN","language":"🌐 NGÔN NGỮ","access_plans":"◆ QUYỀN TRUY CẬP & GÓI","public_menu":"MENU CÔNG KHAI","choose_language":"Chọn ngôn ngữ giao diện trước khi kích hoạt.","select_plan":"Chọn gói đăng ký để tiếp tục.","support_title":"◉ LIÊN HỆ HỖ TRỢ","support_prompt":"Gửi câu hỏi hoặc mô tả vấn đề trong tin nhắn tiếp theo.","support_routed":"Tin nhắn của bạn sẽ được chuyển an toàn đến bộ phận hỗ trợ.","support_empty":"Hãy mô tả vấn đề của bạn trong một tin nhắn.","support_sent":"<b>ĐÃ GỬI YÊU CẦU HỖ TRỢ</b>\n\nYêu cầu của bạn đã được chuyển đến bộ phận hỗ trợ. Bạn sẽ nhận được phản hồi qua Telegram."},
    "id": {"days7":"🟢 7 HARI","days14":"🟡 14 HARI","days30":"🔵 30 HARI","paid":"💳 SAYA SUDAH MEMBAYAR","language":"🌐 BAHASA","access_plans":"◆ AKSES & PAKET","public_menu":"MENU PUBLIK","choose_language":"Pilih bahasa antarmuka sebelum aktivasi.","select_plan":"Pilih paket langganan untuk melanjutkan.","support_title":"◉ HUBUNGI DUKUNGAN","support_prompt":"Kirim pertanyaan atau jelaskan masalah Anda pada pesan berikutnya.","support_routed":"Pesan Anda akan diteruskan secara aman ke dukungan.","support_empty":"Jelaskan masalah Anda dalam satu pesan.","support_sent":"<b>PERMINTAAN DUKUNGAN TERKIRIM</b>\n\nPesan Anda telah diteruskan ke dukungan. Anda akan menerima respons melalui Telegram."},
    "hi": {"days7":"🟢 7 दिन","days14":"🟡 14 दिन","days30":"🔵 30 दिन","paid":"💳 मैंने भुगतान कर दिया है","language":"🌐 भाषा","access_plans":"◆ एक्सेस और प्लान","public_menu":"सार्वजनिक मेनू","choose_language":"सक्रिय करने से पहले अपनी इंटरफेस भाषा चुनें।","select_plan":"जारी रखने के लिए सदस्यता प्लान चुनें।","support_title":"◉ सहायता से संपर्क करें","support_prompt":"अपना प्रश्न भेजें या अगली संदेश में समस्या बताएं।","support_routed":"आपका संदेश सुरक्षित रूप से सहायता टीम को भेजा जाएगा।","support_empty":"एक संदेश में अपनी समस्या बताएं।","support_sent":"<b>सहायता अनुरोध भेज दिया गया</b>\n\nआपका संदेश सहायता टीम को भेज दिया गया है। आपको Telegram के माध्यम से उत्तर मिलेगा।"},
    "zh": {"days7":"🟢 7 天","days14":"🟡 14 天","days30":"🔵 30 天","paid":"💳 我已付款","language":"🌐 语言","access_plans":"◆ 访问与套餐","public_menu":"公共菜单","choose_language":"激活前请选择界面语言。","select_plan":"请选择订阅套餐以继续。","support_title":"◉ 联系支持","support_prompt":"请在下一条消息中发送您的问题或描述遇到的问题。","support_routed":"您的消息将安全地转交给支持团队。","support_empty":"请在一条消息中描述您的问题。","support_sent":"<b>支持请求已发送</b>\n\n您的消息已转交支持团队。您将通过 Telegram 收到回复。"},
}

_ORIGINAL_T = main.t


def _t(lang: str, key: str, **kwargs) -> str:
    overrides = {
        "vi": {"account_intel":"THÔNG TIN TÀI KHOẢN"},
        "id": {"account_intel":"INTELIJEN AKUN"},
        "hi": {"account_intel":"खाता जानकारी"},
        "zh": {"account_intel":"账户情报"},
    }
    if lang in overrides and key in overrides[lang]:
        return overrides[lang][key]
    return _ORIGINAL_T(lang, key, **kwargs)


def _ui(lang: str, key: str) -> str:
    return L.get(lang, L["en"]).get(key, L["en"][key])


def checkout_link(telegram_id: int, days: int) -> str:
    expires = int(time.time()) + 15 * 60
    payload = f"{telegram_id}:{days}:{expires}"
    key = (TELEGRAM_BOT_TOKEN or "neural-gold").encode("utf-8")
    signature = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{BELMO_PUBLIC_URL}/checkout/{days}?token={quote(payload + '.' + signature)}"


def access_keyboard(update):
    lang = main._lang(update)
    telegram_id = update.effective_user.id
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_ui(lang, "days7"), url=checkout_link(telegram_id, 7)), InlineKeyboardButton(_ui(lang, "days14"), url=checkout_link(telegram_id, 14)), InlineKeyboardButton(_ui(lang, "days30"), url=checkout_link(telegram_id, 30))],
        [InlineKeyboardButton(_t(lang, "activate"), callback_data="action:token"), InlineKeyboardButton(_ui(lang, "paid"), callback_data="paid:menu")],
        [InlineKeyboardButton(_t(lang, "account_status"), callback_data="screen:account")],
        [InlineKeyboardButton(_t(lang, "back"), callback_data="nav:home"), InlineKeyboardButton(_t(lang, "menu"), callback_data="nav:home")],
    ])


def public_menu_keyboard(update):
    lang = main._lang(update)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_ui(lang, "language"), callback_data="settings:language")],
        [InlineKeyboardButton(_ui(lang, "access_plans"), callback_data="screen:access")],
        [InlineKeyboardButton(_t(lang, "back"), callback_data="nav:access")],
    ])


def support_keyboard(update):
    lang = main._lang(update)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(lang, "contact"), callback_data="support:open")],
        [InlineKeyboardButton(_t(lang, "back"), callback_data="nav:home"), InlineKeyboardButton(_t(lang, "menu"), callback_data="nav:home")],
    ])


async def _render_public_menu(update, context):
    lang = main._lang(update)
    text = (f"<b>NEURAL GOLD</b>\n{main.DIVIDER}\n\n<b>{_ui(lang, 'public_menu')}</b>\n\n"
            f"{_ui(lang, 'language')}\n{_ui(lang, 'choose_language')}\n\n"
            f"{_ui(lang, 'access_plans')}\n{_ui(lang, 'select_plan')}")
    await main._present(update, text, public_menu_keyboard(update))


async def _callback_router(update, context):
    query = update.callback_query
    data = (query.data or "") if query else ""
    user = update.effective_user
    if query is None or user is None:
        return
    lang = main._lang(update)
    if data == "action:token":
        await query.answer()
        context.user_data["awaiting_token"] = True
        await main._present(
            update,
            "<b>🔑 ACTIVATE TOKEN</b>\n\nEnter your single-use activation token below.",
            access_keyboard(update),
        )
        return
    if data.startswith("buy:"):
        await query.answer("Checkout is available from the plan button.", show_alert=True)
        return
    if data == "support:open":
        await query.answer()
        context.user_data["awaiting_support"] = True
        await query.message.reply_text(f"<b>{_ui(lang, 'support_title')}</b>\n\n{_ui(lang, 'support_prompt')}\n{_ui(lang, 'support_routed')}", parse_mode="HTML")
        return
    if data == "settings:language":
        await query.answer()
        await main._present(update, f"<b>🌐 {_t(lang, 'choose_language')}</b>\n{main.DIVIDER}\n\n{_t(lang, 'language_names')}", main.language_keyboard(update))
        return
    if data == "nav:home" and not auth.verify_token(user.id)[0]:
        await query.answer()
        await _render_public_menu(update, context)
        return
    if data == "nav:access":
        await query.answer()
        await main.render_access(update, context)
        return
    if data == "screen:support":
        await query.answer()
        await main._present(update, f"<b>{_ui(lang, 'support_title')}</b>\n{main.DIVIDER}\n\n{_ui(lang, 'support_prompt')}", support_keyboard(update))
        return
    await _original_router(update, context)


async def _unknown_text_handler(update, context):
    if context.user_data.get("awaiting_support"):
        context.user_data["awaiting_support"] = False
        user = update.effective_user
        text = (update.message.text or "").strip()
        lang = main._lang(update)
        if not text:
            await update.message.reply_text(_ui(lang, "support_empty"))
            context.user_data["awaiting_support"] = True
            return
        support_text = (f"<b>NEURAL GOLD SUPPORT REQUEST</b>\n\nCustomer: <b>{main._esc(user.first_name or 'Trader')}</b>\n"
                        f"Username: <code>@{main._esc(user.username or 'N/A')}</code>\n"
                        f"Telegram ID: <code>{user.id}</code>\n\nMessage:\n{main._esc(text)}")
        if main.ADMIN_TELEGRAM_ID:
            try:
                await context.bot.send_message(chat_id=main.ADMIN_TELEGRAM_ID, text=support_text, parse_mode="HTML")
            except Exception:
                logger.exception("Failed to route support request")
        await update.message.reply_text(_ui(lang, "support_sent"), parse_mode="HTML", reply_markup=access_keyboard(update))
        return
    await _original_unknown_text(update, context)


_original_router = main.callback_router
_original_unknown_text = main.unknown_text_handler


def install() -> None:
    main.t = _t
    main.access_keyboard = access_keyboard
    main.support_keyboard = support_keyboard
    main.callback_router = _callback_router
    main.unknown_text_handler = _unknown_text_handler
