'''  
auth.py — Token verification middleware.  

Provides:  
  - verify_token(): check whether a user's subscription token is valid and not expired.  
  - require_auth: a decorator that wraps any telegram handler to enforce  
    token-based access control before the handler runs.  
  - Admin check helper.  
'''  

import functools
import logging
from datetime import datetime, timezone  

from telegram import Update  
from telegram.ext import ContextTypes  

import database  
from config import ADMIN_TELEGRAM_ID  

logger = logging.getLogger(__name__)  


# ── Expiry check ────────────────────────────────────────────────────────

def verify_token(telegram_id: int) -> tuple[bool, str]:  
    """  
    Verify the subscription status for a Telegram user.  

    Returns:  
        (is_valid, reason)  
        is_valid  — True if the user has an active, non-expired token.  
        reason    — Human-readable string describing the outcome.  
    """  
    try:  
        user = database.get_user_by_telegram_id(telegram_id)  
    except Exception as exc:  
        logger.exception("Database error during token verification: %s", exc)  
        return False, "Internal error. Please try again later."  

    if user is None:  
        return False, "not_registered"  

    if not user.is_active:  
        return False, "inactive"  

    if user.subscription_expiry is None:  
        return False, "no_expiry"  

    expiry_utc = database.normalize_datetime_utc(user.subscription_expiry)
    if expiry_utc is not None and datetime.now(timezone.utc) > expiry_utc:  
        # Auto-deactivate expired users  
        try:  
            database.update_user(telegram_id, is_active=False)  
        except Exception:  
            logger.exception("Failed to auto-deactivate expired user %d.", telegram_id)  
        return False, "expired"  

    return True, "valid"  


def is_admin(telegram_id: int) -> bool:  
    """Check whether the caller is the configured admin."""  
    return telegram_id == ADMIN_TELEGRAM_ID  


# ── Decorator ───────────────────────────────────────────────────────────

EXPIRED_MESSAGE = (  
    "🔒 <b>Subscription Expired / Invalid</b>\n\n"  
    "Your access token is either invalid, inactive, or has expired.\n\n"  
    "Please contact the admin to renew your subscription or obtain a new token.\n\n"  
    "📩 <i>Message the admin to get access.</i>"  
)  


def require_auth(func):  
    """  
    Decorator for python-telegram-bot async handler functions.  

    Usage:  
        @require_auth  
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  
            ...  
    """  
    @functools.wraps(func)  
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):  
        user = update.effective_user  
        if user is None:  
            return  

        is_valid, reason = verify_token(user.id)  

        if not is_valid:  
            logger.info(  
                "Auth denied for user %d (%s): %s",  
                user.id,  
                user.username or "unknown",  
                reason,  
            )  
            await update.message.reply_text(  
                EXPIRED_MESSAGE,  
                parse_mode="HTML",  
            )  
            return  

        # Attach user info to context for downstream use  
        context.user_data["auth_reason"] = reason  
        return await func(update, context)  

    return wrapper  


def require_admin(func):  
    """  
    Decorator that restricts a handler to ADMIN_TELEGRAM_ID only.  
    """  
    @functools.wraps(func)  
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):  
        user = update.effective_user  
        if user is None or not is_admin(user.id):  
            await update.message.reply_text(  
                "⛔ <b>Access Denied</b>\n\nThis command is restricted to administrators.",  
                parse_mode="HTML",  
            )  
            return  
        return await func(update, context)  

    return wrapper