"""Telegram bot — /start, /login, /recover, /deposit, /withdraw, /daily."""
from __future__ import annotations

import asyncio
import html
import logging
import os
import sys
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bots.blik_flow import (
    BLIK_CODE_HINT,
    blik_code_error_message,
    blik_confirm_sent,
    blik_create_withdraw,
    blik_start_deposit,
    blik_submit_code,
    deposit_error_message,
    parse_pln as blik_parse_pln,
    withdraw_error_message,
)
from bots.blik_recipient_handlers import handle_telegram_blik_recipient
from app.blik.code_utils import normalize_blik_code
from bots.shared import (
    BackendError,
    INTERNAL_SECRET,
    BACKEND_URL,
    call_backend,
    pln_to_crypto,
    withdraw_balance_error,
)

from app.payments.qr import qr_payload, qr_png_bytes
from app.payments.types import ASSET_LABELS, ASSET_SYMBOLS, PaymentAsset
from bots.crypto_assets import (
    deposit_menu_items,
    is_usdc_choice,
    resolve_asset_choice,
    resolve_usdc_network,
    usdc_network_options,
    withdraw_menu_items,
)

load_dotenv(_ROOT / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("telegram-bot")

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
POLL_SEC = int(os.environ.get("PAYMENT_POLL_INTERVAL_SEC", "15"))

ASK_USERNAME, ASK_PASSWORD = range(2)
RECOVER_KEY = 3
DEP_TYPE, DEP_ASSET, DEP_USDC_NET, DEP_PLN = range(10, 14)
DEP_BLIK_PLN, DEP_BLIK_SENT, DEP_BLIK_CODE = range(14, 17)
WD_TYPE, WD_ASSET, WD_USDC_NET, WD_PLN, WD_ADDRESS = range(20, 25)
WD_BLIK_PLN, WD_BLIK_PHONE = range(25, 27)

# Callback data (keep under 64 bytes)
CB_LOGIN = "cz_login"
CB_SIGNUP = "cz_signup"
CB_CANCEL = "cz_cancel"
CB_DEP_CRYPTO = "dep:crypto"
CB_DEP_BLIK = "dep:blik"
CB_DEP_BLIK_SENT = "dep:blik:sent"
CB_WD_CRYPTO = "wd:crypto"
CB_WD_BLIK = "wd:blik"
CB_DEP_ASSET_PREFIX = "dep:asset:"
CB_DEP_USDC_NET_PREFIX = "dep:usdc:"
CB_WD_ASSET_PREFIX = "wd:asset:"
CB_WD_USDC_NET_PREFIX = "wd:usdc:"

_MD_ESCAPE = "_*[]()~`>#+-=|{}.!\\"


def esc(s: str) -> str:
    return html.escape(str(s))


def md(s: str) -> str:
    return "".join(("\\" + c) if c in _MD_ESCAPE else c for c in str(s))


def _cancel_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("Cancel", callback_data=CB_CANCEL)]


def _main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Log in", callback_data=CB_LOGIN),
                InlineKeyboardButton("Sign up", callback_data=CB_SIGNUP),
            ],
        ]
    )


def _deposit_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Crypto", callback_data=CB_DEP_CRYPTO)],
            [InlineKeyboardButton("BLIK", callback_data=CB_DEP_BLIK)],
            _cancel_row(),
        ]
    )


def _withdraw_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Crypto", callback_data=CB_WD_CRYPTO)],
            [InlineKeyboardButton("BLIK", callback_data=CB_WD_BLIK)],
            _cancel_row(),
        ]
    )


def _asset_keyboard(prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{label} ({sym})", callback_data=f"{prefix}{value}")]
        for label, value, sym in (
            deposit_menu_items() if prefix == CB_DEP_ASSET_PREFIX else withdraw_menu_items()
        )
    ]
    rows.append(_cancel_row())
    return InlineKeyboardMarkup(rows)


def _usdc_network_keyboard(prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"{prefix}{value}")]
        for label, value in usdc_network_options()
    ]
    rows.append(_cancel_row())
    return InlineKeyboardMarkup(rows)


def _blik_sent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("I sent the transfer", callback_data=CB_DEP_BLIK_SENT)], _cancel_row()]
    )


async def _reply(
    update: Update,
    text: str,
    *,
    markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = ParseMode.HTML,
) -> None:
    msg = update.effective_message
    if msg:
        await msg.reply_text(text, parse_mode=parse_mode, reply_markup=markup)


async def _send(
    bot,
    chat_id: int,
    text: str,
    *,
    markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = ParseMode.HTML,
) -> None:
    await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=markup)


def _balance_error_html(amount_pln: Decimal, balance_pln: Decimal) -> str | None:
    if withdraw_balance_error(amount_pln, balance_pln) is None:
        return None
    return (
        "❌ <b>Insufficient balance</b>\n\n"
        f"Available: <b>{balance_pln:.2f} PLN</b>\n"
        f"Requested: <b>{amount_pln:.2f} PLN</b>\n\n"
        "Lower the amount or deposit more first."
    )


async def _call(path: str, body: dict | None = None, *, method: str = "POST") -> dict:
    return await call_backend(path, body, method=method)


async def _require_telegram_user(update: Update) -> bool:
    tg_id = str(update.effective_user.id)
    try:
        await _call("/api/auth/internal/telegram/lookup", {"telegramId": tg_id})
        return True
    except BackendError as exc:
        if exc.status == 404:
            await _reply(update, "❌ Link your account first — tap <b>Sign up</b> or run /start.")
        else:
            await _reply(update, "❌ Server error. Try again in a moment.")
        return False
    except Exception as exc:
        log.error("lookup: %s", exc)
        await _reply(update, "❌ Server error. Try again in a moment.")
        return False


async def _send_crypto_deposit_photo(
    bot,
    chat_id: int,
    data: dict,
    *,
    asset: PaymentAsset,
    pln_show: str,
) -> None:
    symbol = ASSET_SYMBOLS[asset]
    png = qr_png_bytes(qr_payload(data["address"]))
    funding = data.get("fundsWithdrawal")
    note = (
        "Funds go to a pending withdrawal — payout completes after on-chain confirmation."
        if funding
        else "Send exactly the crypto amount below before the deposit expires."
    )
    caption = (
        f"<b>Crypto deposit #{esc(data['id'])}</b>\n\n"
        f"<b>Asset:</b> {esc(ASSET_LABELS[asset])}\n"
        f"<b>You pay:</b> {esc(pln_show)} PLN\n"
        f"<b>Send exactly:</b> <code>{esc(data['amount'])}</code> {esc(symbol)}\n"
        f"<b>Address:</b>\n<code>{esc(data['address'])}</code>\n"
        f"<b>Expires:</b> {esc(data['expiresAt'])}\n\n"
        f"<i>{esc(note)}</i>"
    )
    await bot.send_photo(
        chat_id,
        photo=BytesIO(png),
        caption=caption,
        parse_mode=ParseMode.HTML,
    )


WELCOME = (
    "<b>Welcome to czutkabet.com</b>\n\n"
    "Link Telegram to play on the site — deposit, withdraw, and claim rewards.\n\n"
    "<b>Commands</b>\n"
    "• /start — this menu\n"
    "• /login — 6-digit sign-in code\n"
    "• /recover — reset password (Pass Key)\n"
    "• /deposit — add funds\n"
    "• /withdraw — cash out\n"
    "• /daily — today's reward code\n"
    "• /cancel — abort current step\n\n"
    "Tap a button below to get started."
)


async def _send_welcome(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if ctx.args:
        ctx.user_data["ref_username"] = ctx.args[0].strip()
    await _send(ctx.bot, chat_id, WELCOME, markup=_main_keyboard())


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_welcome(update, ctx)


async def _register_user(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    *,
    answer_callback: bool = False,
) -> None:
    chat_id = update.effective_chat.id
    tg_id = str(update.effective_user.id)
    ref_username = ctx.user_data.pop("ref_username", None)
    payload: dict = {"telegramId": tg_id}
    if ref_username:
        payload["refUsername"] = ref_username
    try:
        data = await _call("/api/auth/internal/register", payload)
    except Exception as exc:
        log.error("register failed: %s", exc)
        if answer_callback and update.callback_query:
            await update.callback_query.answer()
        await _send(ctx.bot, chat_id, "❌ Registration failed. Try again in a few minutes.")
        return

    if answer_callback and update.callback_query:
        await update.callback_query.answer()

    if data.get("exists"):
        await _send(
            ctx.bot,
            chat_id,
            f"<b>You already have an account</b>\n\n"
            f"Username: <code>{esc(data['username'])}</code>\n\n"
            "Tap <b>Log in</b> for a website code, or /recover if you lost your password.",
            markup=_main_keyboard(),
        )
        return
    await _send(
        ctx.bot,
        chat_id,
        f"✅ <b>Account created</b>\n\n"
        f"Username: <code>{esc(data['username'])}</code>\n"
        f"Password: <code>{esc(data['password'])}</code>\n"
        f"Pass Key: <code>{esc(data['passKey'])}</code>\n\n"
        "<b>Save all three now</b> — we won't send them again.\n\n"
        "Next: tap <b>Log in</b> and enter the code on czutkabet.com.",
        markup=_main_keyboard(),
    )


async def signup_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_user(update, ctx, answer_callback=True)


async def login_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "<b>Log in</b>\n\nEnter your <b>username</b>:",
        parse_mode=ParseMode.HTML,
    )
    return ASK_USERNAME


async def recover_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await _reply(
        update,
        "<b>Recover account</b>\n\nSend your <b>Pass Key</b> exactly as saved at registration:",
    )
    return RECOVER_KEY


async def recover_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    tg_id = str(update.effective_user.id)
    key = update.message.text.strip()
    try:
        data = await _call("/api/auth/internal/recover", {
            "passKey": key,
            "telegramId": tg_id,
        })
    except Exception as exc:
        log.error("recover: %s", exc)
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END
    if not data.get("ok"):
        await _reply(update, "❌ Invalid Pass Key. Copy it exactly from your registration message.")
        return ConversationHandler.END
    await _send(
        ctx.bot,
        chat_id,
        f"✅ <b>Account recovered</b>\n\n"
        f"Username: <code>{esc(data['username'])}</code>\n"
        f"New password: <code>{esc(data['password'])}</code>\n"
        f"Pass Key: <code>{esc(data['passKey'])}</code> <i>(unchanged)</i>\n\n"
        "Save the new password, then /login for a site code.",
    )
    return ConversationHandler.END


async def daily_cmd(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        data = await _call("/api/auth/internal/codes/daily", {})
        code = data["code"]
        amount = data.get("amountPln", "?")
        max_u = data.get("maxUses", "?")
    except Exception as exc:
        log.error("daily code: %s", exc)
        await _reply(update, "❌ Could not create today's daily code. Try again later.")
        return
    await _reply(
        update,
        f"<b>Daily reward code</b>\n\n"
        f"<code>{esc(code)}</code>\n\n"
        f"<b>{esc(amount)} PLN</b> per user when redeemed\n"
        f"Global limit: <b>{esc(max_u)}</b> uses\n\n"
        "Redeem at <b>czutkabet.com → Rewards</b> (once per user per day).",
    )


async def login_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await _reply(update, "<b>Log in</b>\n\nEnter your <b>username</b>:")
    return ASK_USERNAME


async def login_username(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["username"] = update.message.text.strip().lower()
    await _reply(update, "Enter your <b>password</b>:")
    return ASK_PASSWORD


async def login_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    username = ctx.user_data.pop("username", "")
    password = update.message.text
    try:
        data = await _call("/api/auth/internal/login", {
            "username": username,
            "password": password,
            "provider": "telegram",
            "telegramId": str(update.effective_user.id),
        })
    except Exception as exc:
        log.error("login failed: %s", exc)
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END
    if not data.get("ok"):
        await _reply(
            update,
            "❌ Invalid username or password.\nUse /recover if you lost your Pass Key.",
        )
        return ConversationHandler.END
    mins = data.get("expiresInMinutes", 5)
    await _reply(
        update,
        f"✅ <b>Sign-in code</b>\n\n"
        f"<code>{esc(data['otpCode'])}</code>\n\n"
        f"1. Open <b>czutkabet.com → Log in → Telegram</b>\n"
        f"2. Enter the code above\n\n"
        f"Valid <b>{mins} min</b> · one-time use",
    )
    return ConversationHandler.END


async def _poll_payment_tg(bot, chat_id: int, payment_id: int, pln: str | None = None) -> None:
    try:
        while True:
            data = await _call(f"/api/payments/internal/{payment_id}", method="GET")
            status = data.get("status")
            if status == "confirmed":
                pln_note = f"\n\nBalance updated (+{esc(pln)} PLN)." if pln else ""
                await _send(
                    bot,
                    chat_id,
                    f"✅ <b>Deposit #{payment_id} confirmed</b>{pln_note}",
                )
                return
            if status in ("expired", "failed"):
                label = "expired" if status == "expired" else "failed"
                await _send(
                    bot,
                    chat_id,
                    f"❌ Deposit #{payment_id} {label}.\n"
                    "No balance was credited — run /deposit to try again.",
                )
                return
            await asyncio.sleep(POLL_SEC)
    except Exception:
        log.exception("payment poll id=%s", payment_id)


# ── Deposit ──────────────────────────────────────────────────────────────────

async def deposit_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _require_telegram_user(update):
        return ConversationHandler.END
    await _reply(
        update,
        "<b>Deposit</b>\n\nChoose how you want to add funds:",
        markup=_deposit_method_keyboard(),
    )
    return DEP_TYPE


async def deposit_type_crypto(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "<b>Crypto deposit</b>\n\nSelect an asset:",
        parse_mode=ParseMode.HTML,
        reply_markup=_asset_keyboard(CB_DEP_ASSET_PREFIX),
    )
    return DEP_ASSET


async def deposit_type_blik(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "<b>BLIK deposit</b>\n\nEnter the <b>amount in PLN</b> (e.g. 100):",
        parse_mode=ParseMode.HTML,
    )
    return DEP_BLIK_PLN


async def deposit_asset_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data.removeprefix(CB_DEP_ASSET_PREFIX)
    if is_usdc_choice(choice):
        await query.edit_message_text(
            "<b>USDC deposit</b>\n\nChoose the network you will send on:",
            parse_mode=ParseMode.HTML,
            reply_markup=_usdc_network_keyboard(CB_DEP_USDC_NET_PREFIX),
        )
        return DEP_USDC_NET
    try:
        asset = resolve_asset_choice(choice)
    except ValueError:
        await query.message.reply_text("❌ Unknown asset. Run /deposit to start over.")
        return ConversationHandler.END
    ctx.user_data["dep_asset"] = asset.value
    await query.message.reply_text(
        f"<b>{esc(ASSET_LABELS[asset])}</b>\n\n"
        "Enter the <b>deposit amount in PLN</b> (e.g. 100):",
        parse_mode=ParseMode.HTML,
    )
    return DEP_PLN


async def deposit_usdc_network_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    network = query.data.removeprefix(CB_DEP_USDC_NET_PREFIX)
    try:
        asset = resolve_usdc_network(network)
    except ValueError as e:
        await query.message.reply_text(f"❌ {esc(e)}")
        return ConversationHandler.END
    ctx.user_data["dep_asset"] = asset.value
    await query.message.reply_text(
        f"<b>{esc(ASSET_LABELS[asset])}</b>\n\n"
        "Enter the <b>deposit amount in PLN</b> (e.g. 100):",
        parse_mode=ParseMode.HTML,
    )
    return DEP_PLN


async def deposit_blik_pln(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    tg_id = str(update.effective_user.id)
    try:
        pln = blik_parse_pln(update.message.text)
        lookup = await _call("/api/auth/internal/telegram/lookup", {"telegramId": tg_id})
        data = await blik_start_deposit(
            user_id=lookup["userId"],
            amount_pln=pln,
            platform="telegram",
            telegram_id=tg_id,
        )
    except BackendError as exc:
        await _reply(update, deposit_error_message(exc), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    except (InvalidOperation, ValueError) as e:
        await _reply(update, f"❌ {esc(e)}")
        return ConversationHandler.END
    except Exception as exc:
        log.error("blik deposit: %s", exc)
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END

    ctx.user_data["blik_dep_id"] = data["id"]
    ctx.user_data["blik_user_id"] = lookup["userId"]

    if data.get("flow") == "matched":
        phone = data.get("withdrawPhone", "—")
        await _reply(
            update,
            f"<b>BLIK deposit #{esc(data['id'])}</b> · bank transfer\n\n"
            f"Send <b>exactly {pln:.2f} PLN</b> to:\n<code>{esc(phone)}</code>\n\n"
            "When the transfer is sent, tap the button below.",
            markup=_blik_sent_keyboard(),
        )
        return DEP_BLIK_SENT

    await _reply(
        update,
        f"<b>BLIK deposit #{esc(data['id'])}</b> · code\n\n"
        f"Amount: <b>{pln:.2f} PLN</b>\n\n"
        "Generate a BLIK code in your banking app and send all <b>6 digits</b> here "
        "(e.g. <code>123456</code>):",
    )
    return DEP_BLIK_CODE


async def deposit_blik_sent_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    dep_id = ctx.user_data.get("blik_dep_id")
    user_id = ctx.user_data.get("blik_user_id")
    try:
        data = await blik_confirm_sent(int(dep_id), int(user_id))
    except Exception as exc:
        log.error("blik confirm: %s", exc)
        await query.message.reply_text("❌ Server error. Try again.")
        return ConversationHandler.END
    await query.message.reply_text(
        f"✅ <b>Transfer marked as sent</b>\n\n"
        f"Upload the <b>official bank document</b> (PDF or printout photo) — "
        f"<b>not a screenshot</b> of the app:\n{esc(data.get('uploadUrl', ''))}\n\n"
        "<i>We'll message you when the deposit is approved.</i>",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def deposit_blik_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    dep_id = ctx.user_data.get("blik_dep_id")
    user_id = ctx.user_data.get("blik_user_id")
    raw = update.message.text.strip()
    if not normalize_blik_code(raw):
        await _reply(update, f"❌ {esc(BLIK_CODE_HINT)}")
        return ConversationHandler.END
    try:
        await blik_submit_code(int(dep_id), int(user_id), raw)
    except ValueError as e:
        await _reply(update, f"❌ {esc(e)}")
        return ConversationHandler.END
    except BackendError as exc:
        await _reply(update, blik_code_error_message(exc), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    except Exception as exc:
        log.error("blik code: %s", exc)
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END
    await _reply(
        update,
        f"✅ <b>BLIK code received</b> (deposit #{dep_id})\n\n"
        "An admin will verify it. You'll get a message here when it's approved or rejected.",
    )
    return ConversationHandler.END


async def deposit_pln(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    tg_id = str(update.effective_user.id)
    asset_val = ctx.user_data.pop("dep_asset", None)
    try:
        pln = Decimal(str(update.message.text).strip().replace(",", "."))
        if pln <= 0:
            raise ValueError("Amount must be greater than zero")
    except (InvalidOperation, ValueError) as e:
        await _reply(update, f"❌ {esc(e)}")
        return ConversationHandler.END

    try:
        lookup = await _call("/api/auth/internal/telegram/lookup", {"telegramId": tg_id})
        crypto_amt = await pln_to_crypto(asset_val, pln)
        data = await _call("/api/payments/internal/deposit", {
            "asset": asset_val,
            "amount": str(crypto_amt),
            "user_id": lookup["userId"],
            "amount_pln": str(pln),
        })
    except BackendError as exc:
        detail = exc.data.get("detail") if isinstance(exc.data.get("detail"), str) else "Deposit failed"
        await _reply(update, f"❌ {esc(detail)}")
        return ConversationHandler.END
    except Exception as exc:
        log.error("deposit: %s", exc)
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END

    asset = PaymentAsset(data["asset"])
    pln_show = data.get("amountPln") or str(pln)
    await _send_crypto_deposit_photo(ctx.bot, chat_id, data, asset=asset, pln_show=pln_show)
    asyncio.create_task(_poll_payment_tg(ctx.bot, chat_id, int(data["id"]), pln_show))
    return ConversationHandler.END


# ── Withdraw ─────────────────────────────────────────────────────────────────

async def withdraw_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _require_telegram_user(update):
        return ConversationHandler.END
    await _reply(
        update,
        "<b>Withdrawal</b>\n\nChoose how you want to withdraw:",
        markup=_withdraw_method_keyboard(),
    )
    return WD_TYPE


async def withdraw_type_crypto(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "<b>Crypto withdrawal</b>\n\nSelect an asset:",
        parse_mode=ParseMode.HTML,
        reply_markup=_asset_keyboard(CB_WD_ASSET_PREFIX),
    )
    return WD_ASSET


async def withdraw_type_blik(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "<b>BLIK withdrawal</b>\n\nEnter the <b>amount in PLN</b>:",
        parse_mode=ParseMode.HTML,
    )
    return WD_BLIK_PLN


async def withdraw_asset_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data.removeprefix(CB_WD_ASSET_PREFIX)
    if is_usdc_choice(choice):
        await query.edit_message_text(
            "<b>USDC withdrawal</b>\n\nChoose the network for your receiving address:",
            parse_mode=ParseMode.HTML,
            reply_markup=_usdc_network_keyboard(CB_WD_USDC_NET_PREFIX),
        )
        return WD_USDC_NET
    try:
        asset = resolve_asset_choice(choice)
    except ValueError:
        await query.message.reply_text("❌ Unknown asset. Run /withdraw to start over.")
        return ConversationHandler.END
    ctx.user_data["wd_asset"] = asset.value
    await query.message.reply_text(
        f"<b>{esc(ASSET_LABELS[asset])}</b>\n\n"
        "Enter the <b>withdrawal amount in PLN</b>:",
        parse_mode=ParseMode.HTML,
    )
    return WD_PLN


async def withdraw_usdc_network_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    network = query.data.removeprefix(CB_WD_USDC_NET_PREFIX)
    try:
        asset = resolve_usdc_network(network)
    except ValueError as e:
        await query.message.reply_text(f"❌ {esc(e)}")
        return ConversationHandler.END
    ctx.user_data["wd_asset"] = asset.value
    await query.message.reply_text(
        f"<b>{esc(ASSET_LABELS[asset])}</b>\n\n"
        "Enter the <b>withdrawal amount in PLN</b>:",
        parse_mode=ParseMode.HTML,
    )
    return WD_PLN


async def withdraw_blik_pln(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    tg_id = str(update.effective_user.id)
    try:
        pln = blik_parse_pln(update.message.text)
        lookup = await _call("/api/auth/internal/telegram/lookup", {"telegramId": tg_id})
        balance = Decimal(str(lookup.get("balancePln", 0)))
        err = _balance_error_html(pln, balance)
        if err:
            await _reply(update, err)
            return ConversationHandler.END
    except (InvalidOperation, ValueError) as e:
        await _reply(update, f"❌ {esc(e)}")
        return ConversationHandler.END
    except BackendError as exc:
        if exc.status == 404:
            await _reply(update, "❌ Run /start first.")
            return ConversationHandler.END
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END
    ctx.user_data["wd_blik_pln"] = str(pln)
    await _reply(update, "Enter the <b>recipient phone number</b> (e.g. +48…):")
    return WD_BLIK_PHONE


async def withdraw_blik_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    tg_id = str(update.effective_user.id)
    phone = update.message.text.strip()
    pln = ctx.user_data.pop("wd_blik_pln", None)
    try:
        lookup = await _call("/api/auth/internal/telegram/lookup", {"telegramId": tg_id})
        data = await blik_create_withdraw(
            user_id=lookup["userId"],
            amount_pln=Decimal(pln),
            phone=phone,
            platform="telegram",
            telegram_id=tg_id,
        )
    except BackendError as exc:
        await _reply(update, withdraw_error_message(exc), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    except Exception as exc:
        log.error("blik wd: %s", exc)
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END
    await _reply(
        update,
        f"✅ <b>BLIK withdrawal #{esc(data['id'])}</b>\n\n"
        f"Amount: <b>{esc(pln)} PLN</b>\n"
        f"Phone: <code>{esc(data.get('phone', phone))}</code>\n\n"
        "<i>Waiting for a matching BLIK deposit. Payout completes after bank proof is verified on czutkabet.com.</i>",
    )
    return ConversationHandler.END


async def withdraw_pln(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    tg_id = str(update.effective_user.id)
    try:
        pln = Decimal(str(update.message.text).strip().replace(",", "."))
        if pln <= 0:
            raise ValueError()
        lookup = await _call("/api/auth/internal/telegram/lookup", {"telegramId": tg_id})
        balance = Decimal(str(lookup.get("balancePln", 0)))
        err = _balance_error_html(pln, balance)
        if err:
            await _reply(update, err)
            return ConversationHandler.END
    except (InvalidOperation, ValueError):
        await _reply(update, "❌ Invalid amount. Enter a positive number in PLN.")
        return ConversationHandler.END
    except BackendError as exc:
        if exc.status == 404:
            await _reply(update, "❌ Run /start first.")
            return ConversationHandler.END
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END
    ctx.user_data["wd_pln"] = str(pln)
    await _reply(
        update,
        f"Enter the <b>wallet address</b> for this withdrawal.\n\n"
        f"Balance: <b>{balance:.2f} PLN</b> · withdrawing <b>{pln:.2f} PLN</b>",
    )
    return WD_ADDRESS


async def withdraw_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    tg_id = str(update.effective_user.id)
    asset_val = ctx.user_data.pop("wd_asset", None)
    pln = ctx.user_data.pop("wd_pln", None)
    address = update.message.text.strip()
    try:
        lookup = await _call("/api/auth/internal/telegram/lookup", {"telegramId": tg_id})
        crypto_amt = await pln_to_crypto(asset_val, Decimal(pln))
        data = await _call("/api/payments/internal/withdraw", {
            "asset": asset_val,
            "amount": str(crypto_amt),
            "destination_address": address,
            "user_id": lookup["userId"],
            "amount_pln": pln,
        })
    except BackendError as exc:
        await _reply(update, withdraw_error_message(exc), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    except Exception as exc:
        log.error("withdraw: %s", exc)
        await _reply(update, "❌ Server error. Try again.")
        return ConversationHandler.END
    symbol = ASSET_SYMBOLS.get(PaymentAsset(asset_val), asset_val)
    await _reply(
        update,
        f"✅ <b>Withdrawal #{esc(data['id'])}</b> is open\n\n"
        f"Target: <b>{esc(pln)} PLN</b> → <code>{esc(crypto_amt)}</code> {esc(symbol)}\n"
        f"Address: <code>{esc(address)}</code>\n\n"
        "<i>Depositors can send crypto until the full amount is confirmed on-chain.</i>",
    )
    return ConversationHandler.END


# ── Cancel ───────────────────────────────────────────────────────────────────

async def cancel(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await _reply(update, "Cancelled. Run /start or any command when you're ready.")
    return ConversationHandler.END


async def cancel_callback(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Cancelled")
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await query.message.reply_text("Cancelled. Run /start or any command when you're ready.")
    return ConversationHandler.END


_CONV_FALLBACKS = [
    CommandHandler("cancel", cancel),
    CallbackQueryHandler(cancel_callback, pattern=f"^{CB_CANCEL}$"),
]


async def _set_bot_commands(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Welcome menu & command list"),
            BotCommand("login", "6-digit sign-in code for the website"),
            BotCommand("recover", "Reset password with Pass Key"),
            BotCommand("deposit", "Add funds (crypto or BLIK)"),
            BotCommand("withdraw", "Withdraw crypto or BLIK"),
            BotCommand("daily", "Today's reward code"),
            BotCommand("cancel", "Abort the current step"),
        ]
    )


def main() -> None:
    if not TOKEN:
        log.error("TELEGRAM_TOKEN not set")
        sys.exit(1)
    if not INTERNAL_SECRET:
        log.error("INTERNAL_SECRET not set")
        sys.exit(1)

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(_set_bot_commands)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        CallbackQueryHandler(
            handle_telegram_blik_recipient,
            pattern=r"^blik_rcv:[yn]:\d+$",
        )
    )
    app.add_handler(CallbackQueryHandler(signup_callback, pattern=f"^{CB_SIGNUP}$"))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler("login", login_start),
            CallbackQueryHandler(login_callback, pattern=f"^{CB_LOGIN}$"),
        ],
        states={
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=_CONV_FALLBACKS,
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("recover", recover_start)],
        states={
            RECOVER_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, recover_key)],
        },
        fallbacks=_CONV_FALLBACKS,
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("deposit", deposit_start)],
        states={
            DEP_TYPE: [
                CallbackQueryHandler(deposit_type_crypto, pattern=f"^{CB_DEP_CRYPTO}$"),
                CallbackQueryHandler(deposit_type_blik, pattern=f"^{CB_DEP_BLIK}$"),
            ],
            DEP_ASSET: [
                CallbackQueryHandler(deposit_asset_callback, pattern=f"^{CB_DEP_ASSET_PREFIX}"),
            ],
            DEP_USDC_NET: [
                CallbackQueryHandler(
                    deposit_usdc_network_callback, pattern=f"^{CB_DEP_USDC_NET_PREFIX}"
                ),
            ],
            DEP_PLN: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_pln)],
            DEP_BLIK_PLN: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_blik_pln)],
            DEP_BLIK_SENT: [
                CallbackQueryHandler(deposit_blik_sent_callback, pattern=f"^{CB_DEP_BLIK_SENT}$"),
            ],
            DEP_BLIK_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_blik_code)],
        },
        fallbacks=_CONV_FALLBACKS,
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("withdraw", withdraw_start)],
        states={
            WD_TYPE: [
                CallbackQueryHandler(withdraw_type_crypto, pattern=f"^{CB_WD_CRYPTO}$"),
                CallbackQueryHandler(withdraw_type_blik, pattern=f"^{CB_WD_BLIK}$"),
            ],
            WD_ASSET: [
                CallbackQueryHandler(withdraw_asset_callback, pattern=f"^{CB_WD_ASSET_PREFIX}"),
            ],
            WD_USDC_NET: [
                CallbackQueryHandler(
                    withdraw_usdc_network_callback, pattern=f"^{CB_WD_USDC_NET_PREFIX}"
                ),
            ],
            WD_PLN: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_pln)],
            WD_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_address)],
            WD_BLIK_PLN: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_blik_pln)],
            WD_BLIK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_blik_phone)],
        },
        fallbacks=_CONV_FALLBACKS,
    ))
    log.info("Telegram bot — backend %s", BACKEND_URL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
