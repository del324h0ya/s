"""NEURAL GOLD Telegram command menu localization.

Public command descriptions use NEURAL GOLD product terminology while remaining
short and understandable. Administrator-only commands are exposed only to the
configured administrator's command menu.
"""
from __future__ import annotations

import logging

from telegram import BotCommand, BotCommandScopeChat
from telegram.error import TelegramError

logger = logging.getLogger("neural_gold.command_localization")

PUBLIC_COMMANDS: dict[str, list[tuple[str, str]]] = {
    "en": [
        ("start", "Open NEURAL GOLD console"),
        ("token", "Activate NEURAL GOLD access"),
        ("status", "Read NEURAL GOLD access"),
        ("help", "Open NEURAL GOLD guide"),
    ],
    "vi": [
        ("start", "Mở bảng điều khiển NEURAL GOLD"),
        ("token", "Kích hoạt quyền truy cập NEURAL GOLD"),
        ("status", "Xem trạng thái NEURAL GOLD"),
        ("help", "Mở hướng dẫn NEURAL GOLD"),
    ],
    "id": [
        ("start", "Buka konsol NEURAL GOLD"),
        ("token", "Aktifkan akses NEURAL GOLD"),
        ("status", "Lihat status akses NEURAL GOLD"),
        ("help", "Buka panduan NEURAL GOLD"),
    ],
    "hi": [
        ("start", "NEURAL GOLD कंसोल खोलें"),
        ("token", "NEURAL GOLD एक्सेस सक्रिय करें"),
        ("status", "NEURAL GOLD एक्सेस देखें"),
        ("help", "NEURAL GOLD गाइड खोलें"),
    ],
    "zh": [
        ("start", "打开 NEURAL GOLD 控制台"),
        ("token", "激活 NEURAL GOLD 访问权限"),
        ("status", "查看 NEURAL GOLD 访问状态"),
        ("help", "打开 NEURAL GOLD 指南"),
    ],
}

ADMIN_COMMANDS: dict[str, list[tuple[str, str]]] = {
    "en": PUBLIC_COMMANDS["en"] + [
        ("addtoken", "Create NEURAL GOLD token"),
        ("listusers", "Read NEURAL GOLD users"),
        ("revoke", "Revoke NEURAL GOLD access"),
    ],
    "vi": PUBLIC_COMMANDS["vi"] + [
        ("addtoken", "Tạo token NEURAL GOLD"),
        ("listusers", "Xem người dùng NEURAL GOLD"),
        ("revoke", "Thu hồi quyền NEURAL GOLD"),
    ],
    "id": PUBLIC_COMMANDS["id"] + [
        ("addtoken", "Buat token NEURAL GOLD"),
        ("listusers", "Lihat pengguna NEURAL GOLD"),
        ("revoke", "Cabut akses NEURAL GOLD"),
    ],
    "hi": PUBLIC_COMMANDS["hi"] + [
        ("addtoken", "NEURAL GOLD टोकन बनाएं"),
        ("listusers", "NEURAL GOLD उपयोगकर्ता देखें"),
        ("revoke", "NEURAL GOLD एक्सेस रद्द करें"),
    ],
    "zh": PUBLIC_COMMANDS["zh"] + [
        ("addtoken", "创建 NEURAL GOLD 令牌"),
        ("listusers", "查看 NEURAL GOLD 用户"),
        ("revoke", "撤销 NEURAL GOLD 访问权限"),
    ],
}


def _commands(items: list[tuple[str, str]]) -> list[BotCommand]:
    return [BotCommand(command, description) for command, description in items]


async def install(bot, admin_telegram_id: int | None = None) -> None:
    """Install localized command menus without making admin-menu failure fatal."""
    for lang, items in PUBLIC_COMMANDS.items():
        try:
            await bot.set_my_commands(_commands(items), language_code=lang)
        except TelegramError as exc:
            logger.warning(
                "Public Telegram command localization failed language=%s: %s",
                lang,
                exc,
            )

    if admin_telegram_id:
        scope = BotCommandScopeChat(chat_id=admin_telegram_id)
        for lang, items in ADMIN_COMMANDS.items():
            try:
                await bot.set_my_commands(
                    _commands(items), scope=scope, language_code=lang
                )
            except TelegramError as exc:
                logger.warning(
                    "Admin Telegram command menu unavailable chat_id=%s language=%s: %s",
                    admin_telegram_id,
                    lang,
                    exc,
                )
