"""Notify users on Discord / Telegram after BLIK events."""
from __future__ import annotations

import logging

import httpx

from .config import get_settings

log = logging.getLogger(__name__)


def _discord_token() -> str:
    return get_settings().discord_token.strip()


def _telegram_token() -> str:
    return get_settings().telegram_token.strip()


async def notify_discord(discord_id: str, message: str) -> bool:
    token = _discord_token()
    if not token or not discord_id:
        return False
    url = "https://discord.com/api/v10/users/@me/channels"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, headers=headers, json={"recipient_id": discord_id})
            if not r.is_success:
                log.warning("discord dm channel failed: %s %s", r.status_code, r.text[:200])
                return False
            ch_id = r.json().get("id")
            if not ch_id:
                return False
            msg_r = await client.post(
                f"https://discord.com/api/v10/channels/{ch_id}/messages",
                headers=headers,
                json={"content": message[:2000]},
            )
            if not msg_r.is_success:
                log.warning("discord dm send failed: %s %s", msg_r.status_code, msg_r.text[:200])
                return False
            return True
    except Exception:
        log.exception("discord notify")
        return False


async def notify_telegram(telegram_id: str, message: str) -> bool:
    token = _telegram_token()
    if not token or not telegram_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                url,
                json={"chat_id": int(telegram_id), "text": message, "parse_mode": "HTML"},
            )
            if not r.is_success:
                log.warning(
                    "telegram send failed chat=%s: %s %s",
                    telegram_id,
                    r.status_code,
                    r.text[:300],
                )
                return False
            body = r.json()
            if not body.get("ok"):
                log.warning("telegram send not ok chat=%s: %s", telegram_id, body)
                return False
            return True
    except Exception:
        log.exception("telegram notify chat=%s", telegram_id)
        return False


async def notify_discord_components(
    discord_id: str,
    message: str,
    *,
    custom_yes: str,
    custom_no: str,
) -> bool:
    token = _discord_token()
    if not token or not discord_id:
        return False
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    components = [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 3,
                    "label": "Yes — I received it",
                    "custom_id": custom_yes[:100],
                },
                {
                    "type": 2,
                    "style": 4,
                    "label": "No — not received",
                    "custom_id": custom_no[:100],
                },
            ],
        }
    ]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://discord.com/api/v10/users/@me/channels",
                headers=headers,
                json={"recipient_id": discord_id},
            )
            if not r.is_success:
                log.warning("discord dm channel failed: %s %s", r.status_code, r.text[:200])
                return False
            ch_id = r.json().get("id")
            if not ch_id:
                return False
            msg_r = await client.post(
                f"https://discord.com/api/v10/channels/{ch_id}/messages",
                headers=headers,
                json={"content": message[:2000], "components": components},
            )
            if not msg_r.is_success:
                log.warning("discord components send failed: %s %s", msg_r.status_code, msg_r.text[:200])
                return False
            return True
    except Exception:
        log.exception("discord notify components")
        return False


async def notify_telegram_keyboard(
    telegram_id: str,
    message: str,
    *,
    yes_data: str,
    no_data: str,
) -> bool:
    token = _telegram_token()
    if not token or not telegram_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    markup = {
        "inline_keyboard": [
            [
                {"text": "Yes — I received it", "callback_data": yes_data[:64]},
                {"text": "No — not received", "callback_data": no_data[:64]},
            ]
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                url,
                json={
                    "chat_id": int(telegram_id),
                    "text": message,
                    "parse_mode": "HTML",
                    "reply_markup": markup,
                },
            )
            if not r.is_success:
                log.warning(
                    "telegram keyboard send failed chat=%s: %s %s",
                    telegram_id,
                    r.status_code,
                    r.text[:300],
                )
                return False
            body = r.json()
            if not body.get("ok"):
                log.warning("telegram keyboard not ok chat=%s: %s", telegram_id, body)
                return False
            return True
    except Exception:
        log.exception("telegram notify keyboard chat=%s", telegram_id)
        return False


async def notify_deposit_event(
    *,
    discord_id: str | None,
    telegram_id: str | None,
    message: str,
    telegram_message: str | None = None,
) -> None:
    tg_text = telegram_message if telegram_message is not None else message
    if discord_id:
        await notify_discord(discord_id, message)
    if telegram_id:
        await notify_telegram(telegram_id, tg_text)
