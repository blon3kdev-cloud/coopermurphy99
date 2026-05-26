"""Styled Discord embeds — daily rewards & nick rewards."""
from __future__ import annotations

import discord

from bots.shared import CZUTKA_NICK_TAG

# Brand accents
COLOUR_DAILY = 0xF59E0B   # amber
COLOUR_REWARD = 0x8B5CF6  # violet
COLOUR_SUCCESS = 0x22C55E
COLOUR_ERROR = 0xEF4444
FOOTER = "czutkabet.com"


def daily_panel_embed() -> discord.Embed:
    e = discord.Embed(
        title="Daily Rewards",
        description=(
            "Every day you can claim a **free reward code** and add PLN to your balance.\n\n"
            "A **new code is posted here every night at midnight** (Europe/Warsaw). "
            "Copy it quickly — codes are limited and meant for personal use."
        ),
        colour=COLOUR_DAILY,
    )
    e.add_field(
        name="How it works",
        value=(
            "1. Wait for today's code post in this channel\n"
            "2. Copy the full code (no extra spaces)\n"
            "3. Open **czutkabet.com → Rewards**, paste the code, and confirm"
        ),
        inline=False,
    )
    e.add_field(name="Reset", value="**00:00** Europe/Warsaw", inline=True)
    e.add_field(name="Codes", value="**Active** — redeem on site", inline=True)
    e.set_footer(text=FOOTER, icon_url=None)
    return e


def daily_code_embed(
    code: str,
    *,
    midnight_drop: bool = False,
    amount_pln: float | None = None,
    max_uses: int | None = None,
) -> discord.Embed:
    title = "Today's code" if not midnight_drop else "New daily code"
    e = discord.Embed(
        title=title,
        description=(
            "Use this code on the website to credit your account. "
            "**One redemption per user per day** — do not post the code publicly."
        ),
        colour=COLOUR_DAILY,
    )
    e.add_field(name="Your code", value=f"```{code}```", inline=False)
    if amount_pln is not None:
        e.add_field(
            name="Amount",
            value=f"**{amount_pln:g} PLN** added to your balance per successful redeem",
            inline=True,
        )
    if max_uses is not None:
        e.add_field(
            name="Global limit",
            value=f"**{max_uses}** total redemptions across all users",
            inline=True,
        )
    e.add_field(
        name="Redeem",
        value=(
            "**czutkabet.com → Rewards** — paste the code and submit.\n"
            "Each valid use adds PLN to your site balance."
        ),
        inline=False,
    )
    if midnight_drop:
        e.set_author(name="Daily drop · midnight Warsaw")
    e.set_footer(text=FOOTER)
    return e


def rewards_panel_embed() -> discord.Embed:
    e = discord.Embed(
        title="Nick reward",
        description=(
            f"Show **{CZUTKA_NICK_TAG}** in your Discord **nickname** or **display name** "
            "to unlock an extra bonus code on top of daily rewards.\n\n"
            "When your name qualifies, press **Check** below — the code is sent to your DMs."
        ),
        colour=COLOUR_REWARD,
    )
    e.add_field(
        name="Requirements",
        value=(
            f"• `{CZUTKA_NICK_TAG}` visible in server nickname **or** global display name\n"
            "• A **czutkabet.com** account linked via the **Auth** channel (Register first)"
        ),
        inline=False,
    )
    e.add_field(
        name="Reward",
        value="A **one-time bonus code** in your private messages after verification.",
        inline=True,
    )
    e.add_field(
        name="Cooldown",
        value="**24 hours** between claims for the same Discord account.",
        inline=True,
    )
    e.add_field(name="Action", value="Press **Check** when your nick includes the tag", inline=True)
    e.set_footer(text=FOOTER)
    return e


def reward_code_dm_embed(code: str) -> discord.Embed:
    e = discord.Embed(
        title="✅ Nick reward unlocked",
        description="Your Discord name includes the required tag. Here is your bonus code:",
        colour=COLOUR_SUCCESS,
    )
    e.add_field(name="Code", value=f"```{code}```", inline=False)
    e.add_field(
        name="Redeem on site",
        value=(
            "1. Go to **czutkabet.com → Rewards**\n"
            "2. Paste the code above and confirm\n"
            "3. PLN is added to your balance automatically"
        ),
        inline=False,
    )
    e.add_field(
        name="Next claim",
        value=(
            "You can press **Check** again in **24 hours** if you still have "
            f"**{CZUTKA_NICK_TAG}** in your nick."
        ),
        inline=False,
    )
    e.set_footer(text="Single-use code · keep it private")
    return e


def reward_fail_embed() -> discord.Embed:
    return discord.Embed(
        title="❌ Tag not found",
        description=(
            f"We could not find **{CZUTKA_NICK_TAG}** in your server nickname or display name.\n\n"
            "**How to fix:**\n"
            "• Server name → Edit profile → add the tag to nickname or display name\n"
            "• Press **Check** again after saving"
        ),
        colour=COLOUR_ERROR,
    )


def reward_sent_embed() -> discord.Embed:
    return discord.Embed(
        title="✅ Check your DMs",
        description=(
            "Your reward code was sent in a **private message** from this bot.\n\n"
            "If you do not see it, enable DMs from server members in your privacy settings."
        ),
        colour=COLOUR_SUCCESS,
    )


def reward_cooldown_embed(ms_left: int) -> discord.Embed:
    from bots.shared import format_cooldown

    left = format_cooldown(ms_left)
    return discord.Embed(
        title="Cooldown active",
        description=(
            "Nick rewards can be claimed **once every 24 hours** per Discord account.\n\n"
            f"**Time remaining:** {left}\n\n"
            f"Keep **{CZUTKA_NICK_TAG}** in your nick, then press **Check** again when the timer ends."
        ),
        colour=COLOUR_DAILY,
    )
