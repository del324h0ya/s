# Pre-START Telegram screen

The premium introduction shown before the user taps START is configured through the Telegram Bot API `set_my_description()` in `main.py`.

The bot cannot send a normal chat message before the user presses START; Telegram controls the pre-START screen. Therefore the introduction is provided as the bot description, with no inline menu or customer buttons in the description itself.

After START, `/start` renders the full premium dashboard and its inline navigation.

If Telegram still shows `No messages here yet...` after changing the description, reopen the bot profile/chat or wait for Telegram client cache to refresh. The Python bot cannot replace that Telegram-owned placeholder directly.
