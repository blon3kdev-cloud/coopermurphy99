"""Discord / Telegram handlers for withdrawal-owner BLIK receipt confirmation."""
from __future__ import annotations

import logging

import discord
from telegram import Update
from telegram.ext import ContextTypes

from bots.shared import BackendError, call_backend

log = logging.getLogger("bots.blik_recipient")


def _recipient_reply_message(data: dict, *, received: bool) -> str:
    if data.get("alreadyAnswered"):
        prev = "received" if data.get("received") else "not received"
        return f"ℹ️ You already answered for this transfer (**{prev}**)."
    if data.get("status") == "depositor_withdraw_unlocked":
        return (
            "✅ **Confirmed** — you received the BLIK.\n\n"
            "The depositor's **BLIK withdrawals are unlocked** again."
        )
    if data.get("status") == "depositor_withdraw_blocked":
        return (
            "❌ **Recorded** — you reported that you did **not** receive this BLIK.\n\n"
            "The depositor's **BLIK withdrawals are now blocked** on the site."
        )
    if received:
        return "✅ **Thank you** — you confirmed receipt. The depositor has been notified."
    return "❌ **Recorded** — payment not received."


async def blik_recipient_confirm(
    deposit_id: int,
    user_id: int,
    *,
    received: bool,
) -> dict:
    return await call_backend(
        "/api/blik/internal/deposit/recipient-confirm",
        {
            "deposit_id": deposit_id,
            "user_id": user_id,
            "received": received,
        },
    )


async def handle_discord_blik_recipient(
    interaction: discord.Interaction,
    lookup_user,
) -> bool:
    if interaction.type != discord.InteractionType.component:
        return False
    custom_id = (interaction.data or {}).get("custom_id") or ""
    received: bool | None = None
    if custom_id.startswith("blik_rcv_yes:"):
        received = True
        dep_part = custom_id.split(":", 1)[1]
    elif custom_id.startswith("blik_rcv_no:"):
        received = False
        dep_part = custom_id.split(":", 1)[1]
    else:
        return False

    try:
        deposit_id = int(dep_part)
    except ValueError:
        return True

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        lookup = await lookup_user(interaction)
        if not lookup:
            await interaction.followup.send("❌ **No linked account.**", ephemeral=True)
            return True
        data = await blik_recipient_confirm(
            deposit_id,
            int(lookup["userId"]),
            received=received,
        )
        await interaction.followup.send(
            _recipient_reply_message(data, received=received),
            ephemeral=True,
        )
    except BackendError as exc:
        detail = exc.data.get("detail", "Request failed")
        await interaction.followup.send(f"❌ **{detail}**", ephemeral=True)
    except Exception:
        log.exception("discord blik recipient confirm")
        await interaction.followup.send("❌ **Server error.**", ephemeral=True)
    return True


async def handle_telegram_blik_recipient(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    parts = query.data.split(":")
    if len(parts) != 3 or parts[0] != "blik_rcv" or parts[1] not in ("y", "n"):
        return

    received = parts[1] == "y"
    try:
        deposit_id = int(parts[2])
    except ValueError:
        await query.answer("Invalid request", show_alert=True)
        return

    await query.answer()
    tg_id = str(update.effective_user.id)
    try:
        lookup = await call_backend(
            "/api/auth/internal/telegram/lookup",
            {"telegramId": tg_id},
        )
        data = await blik_recipient_confirm(
            deposit_id,
            int(lookup["userId"]),
            received=received,
        )
        await query.message.reply_text(
            _recipient_reply_message(data, received=received),
            parse_mode="Markdown",
        )
    except BackendError as exc:
        detail = exc.data.get("detail", "Request failed")
        await query.message.reply_text(f"❌ {detail}")
    except Exception:
        log.exception("telegram blik recipient confirm")
        await query.message.reply_text("❌ Server error.")
