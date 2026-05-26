"""Discord bot — channel panels, daily codes, rewards, crypto deposit."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import discord
from discord import app_commands

from bots.discord_embeds import (
    daily_code_embed,
    daily_panel_embed,
    reward_code_dm_embed,
    reward_cooldown_embed,
    reward_fail_embed,
    reward_sent_embed,
    rewards_panel_embed,
)
from bots.blik_recipient_handlers import handle_discord_blik_recipient
from bots.discord_wallet import (
    WALLET_CHANNEL_ID,
    WalletPanelView,
    _LegacyWalletPanelView,
    _lookup_user,
    post_wallet_panel,
)
from bots.shared import (
    INTERNAL_SECRET,
    BACKEND_URL,
    BackendError,
    call_backend,
    channel_id,
    has_czutka_tag,
    schedule_daily_discord_post,
)

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("discord-bot")

TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()
APP_ID = os.environ.get("DISCORD_APP_ID", "").strip()
AUTH_CHANNEL_ID = channel_id("DISCORD_AUTH_CHANNEL_ID", "DISCORD_CHANNEL_ID")
DAILY_CHANNEL_ID = channel_id("DISCORD_DAILY_CHANNEL_ID")
REWARDS_CHANNEL_ID = channel_id("DISCORD_REWARDS_CHANNEL_ID", "DISCORD_NICK_REWARD_CHANNEL_ID")
ADMIN_USER_IDS = {
    x.strip()
    for x in os.environ.get("DISCORD_ADMIN_USER_IDS", "").split(",")
    if x.strip()
}


def _is_admin(interaction: discord.Interaction) -> bool:
    if str(interaction.user.id) in ADMIN_USER_IDS:
        return True
    perms = interaction.user.guild_permissions if interaction.guild else None
    return bool(perms and perms.manage_guild)


async def _create_daily_code() -> dict:
    return await call_backend("/api/auth/internal/codes/daily", {})


async def _post_daily_code(client: discord.Client) -> None:
    if not DAILY_CHANNEL_ID:
        log.warning("DISCORD_DAILY_CHANNEL_ID not set — skip daily post")
        return
    ch = client.get_channel(int(DAILY_CHANNEL_ID))
    if not isinstance(ch, discord.TextChannel):
        log.warning("daily channel not found")
        return
    try:
        data = await _create_daily_code()
    except Exception:
        log.exception("daily code create failed")
        return
    await ch.send(
        embed=daily_code_embed(
            data["code"],
            midnight_drop=True,
            amount_pln=data.get("amountPln"),
            max_uses=data.get("maxUses"),
        )
    )


async def _send_to_channel(
    interaction: discord.Interaction,
    env_id: str,
    env_name: str,
    content: str,
    view: discord.ui.View | None = None,
) -> None:
    if not env_id:
        await interaction.response.send_message(f"❌ Missing {env_name}.", ephemeral=True)
        return
    ch = interaction.client.get_channel(int(env_id))
    if not isinstance(ch, discord.TextChannel):
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    await ch.send(content, view=view)
    await interaction.response.send_message(f"✅ Posted to {ch.mention}.", ephemeral=True)


# ── UI ───────────────────────────────────────────────────────────────────────

class LoginModal(discord.ui.Modal, title="Log in"):
    username = discord.ui.TextInput(label="Username", required=True, max_length=64)
    password = discord.ui.TextInput(label="Password", required=True, max_length=128)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            data = await call_backend("/api/auth/internal/login", {
                "username": str(self.username).strip().lower(),
                "password": str(self.password),
                "provider": "discord",
                "discordId": str(interaction.user.id),
            })
        except Exception as exc:
            log.exception("login error: %s", exc)
            await interaction.followup.send(
                "❌ **Server error** — we could not complete login. Please try again in a few minutes.",
                ephemeral=True,
            )
            return
        if not data.get("ok"):
            await interaction.followup.send(
                "❌ **Invalid username or password.**\n"
                "Use the exact credentials from your registration DM, or **Recover account** with your Pass Key.",
                ephemeral=True,
            )
            return
        mins = data.get("expiresInMinutes", 5)
        dm = await interaction.user.create_dm()
        await dm.send(
            f"✅ **Login successful**\n\n"
            f"**Your 6-digit sign-in code:**\n\n**`{data['otpCode']}`**\n\n"
            f"**Next steps:**\n"
            f"1. Open **czutkabet.com** and choose **Log in → Discord**\n"
            f"2. Enter the code above when prompted\n\n"
            f"Valid for **{mins} minutes** · **one-time use** (request a new code if it expires)"
        )
        await interaction.followup.send(
            "✅ **Check your DMs** — your sign-in code was sent in a private message.",
            ephemeral=True,
        )


class RecoverModal(discord.ui.Modal, title="Recover account"):
    pass_key = discord.ui.TextInput(
        label="Recovery Pass Key",
        placeholder="e.g. falcon_river_482",
        required=True,
        max_length=128,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            data = await call_backend("/api/auth/internal/recover", {
                "passKey": str(self.pass_key).strip(),
                "discordId": str(interaction.user.id),
            })
        except Exception as exc:
            log.exception("recover error: %s", exc)
            await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
            return
        if not data.get("ok"):
            await interaction.followup.send(
                "❌ **Invalid Pass Key.** Copy it exactly from your original registration message.",
                ephemeral=True,
            )
            return
        dm = await interaction.user.create_dm()
        await dm.send(
            f"✅ **Account recovered**\n\n"
            f"**Username:** `{data['username']}`\n"
            f"**New password:** `{data['password']}`\n"
            f"**Pass Key:** `{data['passKey']}` _(unchanged)_\n\n"
            "**Save the new password now.**\n"
            "Then press **Log in** on the server to get a fresh 6-digit code for czutkabet.com."
        )
        await interaction.followup.send(
            "✅ **Check your DMs** — your updated credentials were sent privately.",
            ephemeral=True,
        )


class PanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Register", style=discord.ButtonStyle.success, custom_id="cz_register")
    async def register(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            data = await call_backend(
                "/api/auth/internal/discord/register",
                {"discordId": str(interaction.user.id)},
            )
        except Exception as exc:
            log.exception("register error: %s", exc)
            await interaction.followup.send(
                "❌ **Server error** — registration failed. Please try again later.",
                ephemeral=True,
            )
            return
        dm = await interaction.user.create_dm()
        if data.get("exists"):
            await dm.send(
                f"**You already have an account**\n\n"
                f"**Username:** `{data['username']}`\n\n"
                "Press **Log in** on the server to receive a 6-digit code for czutkabet.com.\n"
                "Lost your password? Use **Recover account** with your Pass Key."
            )
        else:
            await dm.send(
                f"✅ **Account created**\n\n"
                f"**Username:** `{data['username']}`\n"
                f"**Password:** `{data['password']}`\n"
                f"**Pass Key (recovery):** `{data['passKey']}`\n\n"
                "**Save all three values now — we will not send them again.**\n"
                "The Pass Key is required for **Recover account** if you forget your login.\n\n"
                "**To sign in on the website:**\n"
                "1. Press **Log in** here and enter username + password\n"
                "2. Copy the 6-digit code from this bot's DM\n"
                "3. Enter it on **czutkabet.com → Log in → Discord**"
            )
        await interaction.followup.send(
            "✅ **Check your DMs** — your account details were sent privately.",
            ephemeral=True,
        )

    @discord.ui.button(label="Log in", style=discord.ButtonStyle.primary, custom_id="cz_login")
    async def login(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await interaction.response.send_modal(LoginModal())

    @discord.ui.button(label="Recover account", style=discord.ButtonStyle.secondary, custom_id="cz_recover")
    async def recover(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await interaction.response.send_modal(RecoverModal())


class RewardsView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Check", style=discord.ButtonStyle.success, custom_id="cz_nick_reward")
    async def claim(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        user = interaction.user
        names = [user.name, getattr(user, "global_name", None)]
        if isinstance(user, discord.Member) and user.nick:
            names.append(user.nick)
        if not has_czutka_tag(*names):
            await interaction.followup.send(embed=reward_fail_embed(), ephemeral=True)
            return
        try:
            data = await call_backend(
                "/api/auth/internal/discord/nick-reward",
                {"discordId": str(user.id)},
            )
            code = data["code"]
        except BackendError as exc:
            if exc.status == 404:
                await interaction.followup.send(
                    "❌ **No linked account.** Register first in the **Auth** channel (**Register** button).",
                    ephemeral=True,
                )
                return
            if exc.status == 429:
                detail = exc.data.get("detail")
                ms_left = 0
                if isinstance(detail, dict):
                    ms_left = int(detail.get("retryAfterMs") or 0)
                await interaction.followup.send(
                    embed=reward_cooldown_embed(ms_left),
                    ephemeral=True,
                )
                return
            log.exception("nick reward")
            await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
            return
        except Exception:
            log.exception("nick reward")
            await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
            return
        dm = await user.create_dm()
        await dm.send(embed=reward_code_dm_embed(code))
        await interaction.followup.send(embed=reward_sent_embed(), ephemeral=True)


# ── client ───────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
_scheduler = None


async def _send_embed_to_channel(
    interaction: discord.Interaction,
    env_id: str,
    name: str,
    embed: discord.Embed,
    view: discord.ui.View | None = None,
) -> None:
    if not env_id:
        await interaction.response.send_message(f"❌ Missing {name}.", ephemeral=True)
        return
    ch = client.get_channel(int(env_id))
    if not isinstance(ch, discord.TextChannel):
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    await ch.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Posted to {ch.mention}.", ephemeral=True)


@tree.command(name="auth", description="Post registration / login panel (admin).")
async def auth_cmd(interaction: discord.Interaction) -> None:
    if not _is_admin(interaction):
        await interaction.response.send_message("❌ **Permission denied.**", ephemeral=True)
        return
    await _send_to_channel(
        interaction,
        AUTH_CHANNEL_ID,
        "DISCORD_AUTH_CHANNEL_ID",
        (
            "## Welcome to czutkabet.com\n\n"
            "Link your Discord to the site so you can deposit, withdraw, and claim rewards.\n\n"
            "**Register** — new account (credentials sent to your DMs)\n"
            "**Log in** — get a 6-digit code for the website\n"
            "**Recover account** — reset password with your Pass Key"
        ),
        PanelView(),
    )


@tree.command(name="daily", description="Post daily rewards panel + today's code (admin).")
async def daily_cmd(interaction: discord.Interaction) -> None:
    if not _is_admin(interaction):
        await interaction.response.send_message("❌ **Permission denied.**", ephemeral=True)
        return
    if not DAILY_CHANNEL_ID:
        await interaction.response.send_message("❌ Missing DISCORD_DAILY_CHANNEL_ID.", ephemeral=True)
        return
    ch = client.get_channel(int(DAILY_CHANNEL_ID))
    if not isinstance(ch, discord.TextChannel):
        await interaction.response.send_message("❌ Could not access the daily channel.", ephemeral=True)
        return
    await ch.send(embed=daily_panel_embed())
    try:
        data = await _create_daily_code()
    except Exception:
        log.exception("daily code create")
        await interaction.response.send_message("❌ Failed to create today's code.", ephemeral=True)
        return
    await ch.send(
        embed=daily_code_embed(
            data["code"],
            amount_pln=data.get("amountPln"),
            max_uses=data.get("maxUses"),
        )
    )
    await interaction.response.send_message(f"✅ Daily panel + code posted to {ch.mention}.", ephemeral=True)


@tree.command(name="rewards", description="Post nick reward panel (admin).")
async def rewards_cmd(interaction: discord.Interaction) -> None:
    if not _is_admin(interaction):
        await interaction.response.send_message("❌ **Permission denied.**", ephemeral=True)
        return
    await _send_embed_to_channel(
        interaction,
        REWARDS_CHANNEL_ID,
        "DISCORD_REWARDS_CHANNEL_ID",
        rewards_panel_embed(),
        RewardsView(),
    )


@tree.command(name="deposit", description="Post wallet deposit/withdraw panel (admin).")
async def deposit_cmd(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    if not _is_admin(interaction):
        await interaction.followup.send("❌ **Permission denied.**", ephemeral=True)
        return
    if not WALLET_CHANNEL_ID:
        await interaction.followup.send("❌ Missing DISCORD_DEPOSIT_WITHDRAW_CHANNEL_ID.", ephemeral=True)
        return
    ch = client.get_channel(int(WALLET_CHANNEL_ID))
    if not isinstance(ch, discord.TextChannel):
        await interaction.followup.send("❌ Could not access the wallet channel.", ephemeral=True)
        return
    from bots.discord_wallet import PANEL_POST_COOLDOWN_SEC, post_wallet_panel

    if await post_wallet_panel(ch):
        await interaction.followup.send(f"✅ Wallet panel posted to {ch.mention}.", ephemeral=True)
    else:
        await interaction.followup.send(
            f"A panel was posted recently — wait **{PANEL_POST_COOLDOWN_SEC}s** and try again.",
            ephemeral=True,
        )


_views_registered = False


@client.event
async def on_interaction(interaction: discord.Interaction) -> None:
    if await handle_discord_blik_recipient(interaction, _lookup_user):
        return


@client.event
async def on_ready() -> None:
    global _scheduler, _views_registered
    if not _views_registered:
        client.add_view(PanelView())
        client.add_view(RewardsView())
        client.add_view(WalletPanelView())
        client.add_view(_LegacyWalletPanelView())
        _views_registered = True
    await tree.sync()

    async def _daily_job() -> None:
        await _post_daily_code(client)

    _scheduler = schedule_daily_discord_post(_daily_job)
    log.info("Logged in as %s — backend %s", client.user, BACKEND_URL)


def main() -> None:
    if not TOKEN or not APP_ID:
        log.error("DISCORD_TOKEN or DISCORD_APP_ID not set")
        sys.exit(1)
    if not INTERNAL_SECRET:
        log.error("INTERNAL_SECRET not set")
        sys.exit(1)
    client.run(TOKEN)


if __name__ == "__main__":
    main()
