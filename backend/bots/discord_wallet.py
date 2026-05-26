"""Discord wallet channel — deposit (PLN → crypto) and withdrawal flows."""
from __future__ import annotations

import asyncio
import io
import logging
import os
from decimal import Decimal, InvalidOperation

import discord

from bots.blik_flow import (
    BLIK_CODE_HINT,
    blik_code_error_message,
    blik_confirm_sent,
    blik_create_withdraw,
    blik_start_deposit,
    blik_submit_code,
    deposit_error_message,
    parse_pln,
    withdraw_error_message,
)
from app.blik.code_utils import normalize_blik_code
from bots.crypto_assets import (
    deposit_menu_items,
    is_usdc_choice,
    resolve_asset_choice,
    resolve_usdc_network,
    usdc_network_options,
    withdraw_menu_items,
)
from bots.shared import (
    BackendError,
    call_backend,
    channel_id,
    format_withdraw_detail,
    pln_to_crypto,
    withdraw_balance_error,
)

log = logging.getLogger("discord-wallet")

WALLET_CHANNEL_ID = channel_id("DISCORD_DEPOSIT_WITHDRAW_CHANNEL_ID")
_panel_post_cooldown: dict[int, float] = {}
PANEL_POST_COOLDOWN_SEC = 15


async def _safe_defer(interaction: discord.Interaction, *, ephemeral: bool = True) -> None:
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)


async def post_wallet_panel(channel: discord.TextChannel) -> bool:
    """Post one wallet panel; returns False if channel is on cooldown."""
    import time

    cid = channel.id
    ts = time.monotonic()
    last = _panel_post_cooldown.get(cid, 0)
    if ts - last < PANEL_POST_COOLDOWN_SEC:
        return False
    _panel_post_cooldown[cid] = ts
    await channel.send(
        "## Wallet\n\n"
        "**Deposit** — choose **Crypto** or **BLIK**, then enter the amount in PLN.\n"
        "**Withdrawal** — cash out to crypto or a phone transfer (BLIK).\n\n"
        "_You must register in the **Auth** channel before using the wallet._",
        view=WalletPanelView(),
    )
    return True
POLL_SEC = int(os.environ.get("PAYMENT_POLL_INTERVAL_SEC", "15"))
_withdraw_ctx: dict[str, dict] = {}


async def _lookup_user(interaction: discord.Interaction) -> dict | None:
    try:
        return await call_backend(
            "/api/auth/internal/discord/lookup",
            {"discordId": str(interaction.user.id)},
        )
    except BackendError as exc:
        if exc.status == 404:
            return None
        raise


async def _poll_deposit_confirmed(user: discord.abc.User, payment_id: int, pln: str, crypto: str, symbol: str) -> None:
    try:
        while True:
            data = await call_backend(f"/api/payments/internal/{payment_id}", method="GET")
            status = data.get("status")
            if status == "confirmed":
                await user.send(
                    f"✅ **Deposit #{payment_id} confirmed**\n\n"
                    f"**Amount:** **{pln} PLN** → `{crypto}` {symbol}\n"
                    f"Your PLN balance on **czutkabet.com** has been updated."
                )
                return
            if status in ("expired", "failed"):
                label = "expired" if status == "expired" else "failed"
                await user.send(
                    f"❌ **Deposit #{payment_id} {label}**\n\n"
                    "No funds were credited. Start a new deposit if you still want to add balance."
                )
                return
            await asyncio.sleep(POLL_SEC)
    except Exception:
        log.exception("deposit poll id=%s", payment_id)


# ── Panel (persistent) ───────────────────────────────────────────────────────

class WalletPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Deposit", style=discord.ButtonStyle.success, custom_id="cz_wallet_deposit_v2")
    async def deposit(self, interaction: discord.Interaction, _btn: discord.ui.Button) -> None:
        await _wallet_deposit_start(interaction)

    @discord.ui.button(label="Withdrawal", style=discord.ButtonStyle.danger, custom_id="cz_wallet_withdraw")
    async def withdraw(self, interaction: discord.Interaction, _btn: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "**Withdrawal** — choose how you want to receive funds:",
            view=WithdrawMethodView(),
            ephemeral=True,
        )


class _LegacyWalletPanelView(discord.ui.View):
    """Old wallet panels used custom_id cz_wallet_deposit — keep routing to current deposit flow."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Deposit",
        style=discord.ButtonStyle.success,
        custom_id="cz_wallet_deposit",
    )
    async def deposit(self, interaction: discord.Interaction, _btn: discord.ui.Button) -> None:
        await _wallet_deposit_start(interaction)


# ── Deposit ───────────────────────────────────────────────────────────────────

class WalletDepositAssetView(discord.ui.View):
    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=180)
        self._user_id = user_id
        options = [
            discord.SelectOption(label=label, value=value, description=desc)
            for label, value, desc in deposit_menu_items()
        ]
        sel = discord.ui.Select(placeholder="BTC, ETH, SOL, USDC…", options=options)

        async def on_select(i: discord.Interaction) -> None:
            choice = i.data["values"][0]
            if is_usdc_choice(choice):
                await i.response.edit_message(
                    content="**USDC deposit** — choose the network you will send on:",
                    view=WalletDepositUsdcNetworkView(self._user_id),
                )
                return
            asset = resolve_asset_choice(choice)
            await i.response.send_modal(WalletDepositPlnModal(asset, self._user_id))

        sel.callback = on_select
        self.add_item(sel)


class WalletDepositUsdcNetworkView(discord.ui.View):
    def __init__(self, user_id: int) -> None:
        super().__init__(timeout=180)
        self._user_id = user_id
        options = [
            discord.SelectOption(label=label, value=value)
            for label, value in usdc_network_options()
        ]
        sel = discord.ui.Select(placeholder="Ethereum or Solana", options=options)

        async def on_select(i: discord.Interaction) -> None:
            try:
                asset = resolve_usdc_network(i.data["values"][0])
            except ValueError as e:
                await i.response.send_message(f"❌ {e}", ephemeral=True)
                return
            await i.response.send_modal(WalletDepositPlnModal(asset, self._user_id))

        sel.callback = on_select
        self.add_item(sel)


class WalletDepositPlnModal(discord.ui.Modal, title="Deposit amount (PLN)"):
    pln_amount = discord.ui.TextInput(
        label="Amount in PLN",
        placeholder="e.g. 100",
        required=True,
        max_length=16,
    )

    def __init__(self, asset, user_id: int) -> None:
        super().__init__()
        self._asset = asset
        self._user_id = user_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await _safe_defer(interaction)
        from app.payments.qr import qr_payload, qr_png_bytes
        from app.payments.types import ASSET_LABELS, ASSET_SYMBOLS

        try:
            pln = Decimal(str(self.pln_amount).strip().replace(",", "."))
            if pln <= 0:
                raise ValueError("Amount must be greater than zero")
        except (InvalidOperation, ValueError) as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        try:
            crypto_amt = await pln_to_crypto(self._asset.value, pln)
            data = await call_backend("/api/payments/internal/deposit", {
                "asset": self._asset.value,
                "amount": str(crypto_amt),
                "user_id": self._user_id,
                "amount_pln": str(pln),
            })
        except BackendError as exc:
            detail = exc.data.get("detail") if isinstance(exc.data.get("detail"), str) else str(exc)
            await interaction.followup.send(
                f"❌ {detail}" if exc.status == 400 else "❌ Deposits are disabled or the server returned an error.",
                ephemeral=True,
            )
            return
        except Exception as exc:
            log.exception("deposit: %s", exc)
            await interaction.followup.send(f"❌ {exc}", ephemeral=True)
            return

        symbol = ASSET_SYMBOLS[self._asset]
        crypto_str = data["amount"]
        pln_display = data.get("amountPln") or f"{pln:.2f}"
        png = qr_png_bytes(qr_payload(data["address"]))
        file = discord.File(io.BytesIO(png), filename="qr.png")
        funding = data.get("fundsWithdrawal")
        match_note = (
            "\n\n_Funds go to a pending withdrawal address — the linked withdrawal completes automatically once confirmed on-chain._"
            if funding
            else "\n\n_Send **exactly** the crypto amount shown to the address above before it expires._"
        )
        embed = discord.Embed(
            title=f"Crypto deposit #{data['id']}",
            description=(
                f"**Asset:** {ASSET_LABELS[self._asset]}\n"
                f"**You pay (PLN):** {pln_display} PLN\n"
                f"**Send exactly:** `{crypto_str}` {symbol}\n"
                f"**To address:** `{data['address']}`\n"
                f"**Expires:** {data['expiresAt']}"
                f"{match_note}"
            ),
            colour=discord.Colour.green(),
        )
        embed.set_image(url="attachment://qr.png")
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        asyncio.create_task(
            _poll_deposit_confirmed(
                interaction.user, int(data["id"]), f"{pln:.2f}", crypto_str, symbol
            )
        )


class DepositTypeSelect(discord.ui.Select):
    """Step 1 — Crypto or BLIK (must pick before asset / amount)."""

    def __init__(self, user_id: int, discord_id: str) -> None:
        self._user_id = user_id
        self._discord_id = discord_id
        options = [
            discord.SelectOption(
                label="Crypto",
                value="crypto",
                description="BTC, ETH, USDC…",
            ),
            discord.SelectOption(
                label="BLIK",
                value="blik",
                description="Bank transfer or BLIK code",
            ),
        ]
        super().__init__(
            placeholder="Choose: Crypto or BLIK",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="cz_deposit_type_select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        choice = self.values[0]
        if choice == "crypto":
            await interaction.response.edit_message(
                content="**Crypto deposit** — select the asset you will send:",
                view=WalletDepositAssetView(self._user_id),
            )
            return
        await interaction.response.send_modal(
            WalletDepositBlikPlnModal(self._user_id, self._discord_id)
        )


class WalletDepositTypeView(discord.ui.View):
    def __init__(self, user_id: int, discord_id: str) -> None:
        super().__init__(timeout=300)
        self.add_item(DepositTypeSelect(user_id, discord_id))


class WalletDepositBlikPlnModal(discord.ui.Modal, title="BLIK deposit (PLN)"):
    pln_amount = discord.ui.TextInput(
        label="Amount in PLN",
        placeholder="e.g. 100",
        required=True,
        max_length=16,
    )

    def __init__(self, user_id: int, discord_id: str) -> None:
        super().__init__()
        self._user_id = user_id
        self._discord_id = discord_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await _safe_defer(interaction)
        try:
            pln = parse_pln(str(self.pln_amount))
            data = await blik_start_deposit(
                user_id=self._user_id,
                amount_pln=pln,
                platform="discord",
                discord_id=self._discord_id,
            )
        except BackendError as exc:
            await interaction.followup.send(deposit_error_message(exc), ephemeral=True)
            return
        except (InvalidOperation, ValueError) as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except Exception:
            log.exception("blik deposit start")
            await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
            return

        if data.get("flow") == "matched":
            phone = data.get("withdrawPhone", "—")
            await interaction.followup.send(
                f"**BLIK deposit #{data['id']}** · matched transfer\n\n"
                f"Send **exactly {pln:.2f} PLN** to:\n"
                f"`{phone}`\n\n"
                f"When the transfer is sent, click **I have sent the transfer** below.\n"
                f"You will then upload proof from your banking app.",
                view=BlikConfirmSentView(data["id"], self._user_id),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"**BLIK deposit #{data['id']}** · code flow\n\n"
            f"**Amount:** **{pln:.2f} PLN**\n"
            "Generate a BLIK code in your banking app, then click **Enter BLIK code** and submit all 6 digits.",
            view=BlikEnterCodeView(data["id"], self._user_id),
            ephemeral=True,
        )


class BlikConfirmSentView(discord.ui.View):
    def __init__(self, deposit_id: int, user_id: int) -> None:
        super().__init__(timeout=600)
        self._deposit_id = deposit_id
        self._user_id = user_id

    @discord.ui.button(label="I have sent the transfer", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, _btn: discord.ui.Button) -> None:
        await _safe_defer(interaction)
        try:
            data = await blik_confirm_sent(self._deposit_id, self._user_id)
        except Exception:
            log.exception("blik confirm sent")
            await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
            return
        url = data.get("uploadUrl", "")
        await interaction.followup.send(
            f"✅ **Transfer marked as sent**\n\n"
            f"**Upload proof** — open this link and submit the **official bank document only** "
            f"(PDF or photo of a printout). **Screenshots of the banking app are rejected.**\n"
            f"{url}\n\n"
            "_We will message you here when the deposit is approved or if we need a new upload._",
            ephemeral=True,
        )


class BlikEnterCodeView(discord.ui.View):
    def __init__(self, deposit_id: int, user_id: int) -> None:
        super().__init__(timeout=600)
        self._deposit_id = deposit_id
        self._user_id = user_id

    @discord.ui.button(label="Enter BLIK code", style=discord.ButtonStyle.primary)
    async def enter_code(self, interaction: discord.Interaction, _btn: discord.ui.Button) -> None:
        await interaction.response.send_modal(BlikCodeModal(self._deposit_id, self._user_id))


def _read_modal_text(modal: discord.ui.Modal) -> str:
    """Read TextInput value — must use children, not class-level descriptors."""
    for child in modal.children:
        if isinstance(child, discord.ui.TextInput) and child.value:
            return str(child.value).strip()
    return ""


class BlikCodeModal(discord.ui.Modal, title="BLIK code"):
    def __init__(self, deposit_id: int, user_id: int) -> None:
        super().__init__()
        self._deposit_id = deposit_id
        self._user_id = user_id
        self.add_item(
            discord.ui.TextInput(
                label="6-digit code",
                placeholder="123456 or 123 456",
                min_length=6,
                max_length=8,
                required=True,
            )
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await _safe_defer(interaction)
        raw = _read_modal_text(self)
        if not normalize_blik_code(raw):
            await interaction.followup.send(f"❌ {BLIK_CODE_HINT}", ephemeral=True)
            return
        try:
            await blik_submit_code(self._deposit_id, self._user_id, raw)
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except BackendError as exc:
            await interaction.followup.send(blik_code_error_message(exc), ephemeral=True)
            return
        except Exception:
            log.exception("blik code")
            await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
            return
        await interaction.followup.send(
            f"✅ **BLIK code received** (deposit #{self._deposit_id})\n\n"
            "An admin will verify the code. You will get a DM here when it is approved or rejected.",
            ephemeral=True,
        )


async def _wallet_deposit_start(interaction: discord.Interaction) -> None:
    await _safe_defer(interaction)
    try:
        data = await _lookup_user(interaction)
    except Exception:
        log.exception("lookup")
        await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
        return
    if not data:
        await interaction.followup.send(
            "❌ **No linked account.** Register in the **Auth** channel first.",
            ephemeral=True,
        )
        return
    await interaction.followup.send(
        "**Deposit** — pick **Crypto** or **BLIK** from the menu below, then follow the steps.",
        view=WalletDepositTypeView(data["userId"], str(interaction.user.id)),
        ephemeral=True,
    )


# ── Withdraw ──────────────────────────────────────────────────────────────────

class WithdrawMethodView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=180)

    @discord.ui.button(label="Crypto", style=discord.ButtonStyle.primary)
    async def crypto(self, interaction: discord.Interaction, _btn: discord.ui.Button) -> None:
        await _safe_defer(interaction)
        try:
            data = await _lookup_user(interaction)
        except Exception:
            log.exception("lookup withdraw")
            await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
            return
        if not data:
            await interaction.followup.send(
                "❌ **No linked account.** Register in the **Auth** channel first.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            "**Crypto withdrawal** — select the asset you want to receive:",
            view=WithdrawCryptoAssetView(),
            ephemeral=True,
        )

    @discord.ui.button(label="Phone transfer", style=discord.ButtonStyle.secondary)
    async def tel(self, interaction: discord.Interaction, _btn: discord.ui.Button) -> None:
        await interaction.response.send_modal(WithdrawTelModal())


class WithdrawCryptoAssetView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=180)
        options = [
            discord.SelectOption(label=label, value=value, description=desc)
            for label, value, desc in withdraw_menu_items()
        ]
        sel = discord.ui.Select(placeholder="BTC, ETH, SOL, USDC…", options=options)

        async def on_select(i: discord.Interaction) -> None:
            choice = i.data["values"][0]
            await i.response.defer(ephemeral=True, thinking=True)
            try:
                data = await _lookup_user(i)
            except Exception:
                log.exception("lookup withdraw")
                await i.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
                return
            if not data:
                await i.followup.send(
                    "❌ **No linked account.** Register in the **Auth** channel first.",
                    ephemeral=True,
                )
                return
            balance = Decimal(str(data.get("balancePln", 0)))
            if is_usdc_choice(choice):
                await i.followup.send(
                    "**USDC withdrawal** — choose the network for your receiving address:",
                    view=WithdrawUsdcNetworkView(data["userId"], balance),
                    ephemeral=True,
                )
                return
            from app.payments.types import PaymentAsset

            asset = resolve_asset_choice(choice)
            await i.followup.send_modal(
                WithdrawCryptoModal(asset, data["userId"], balance)
            )

        sel.callback = on_select
        self.add_item(sel)


class WithdrawUsdcNetworkView(discord.ui.View):
    def __init__(self, user_id: int, balance_pln: Decimal) -> None:
        super().__init__(timeout=180)
        self._user_id = user_id
        self._balance_pln = balance_pln
        options = [
            discord.SelectOption(label=label, value=value)
            for label, value in usdc_network_options()
        ]
        sel = discord.ui.Select(placeholder="Ethereum or Solana", options=options)

        async def on_select(i: discord.Interaction) -> None:
            try:
                asset = resolve_usdc_network(i.data["values"][0])
            except ValueError as e:
                await i.response.send_message(f"❌ {e}", ephemeral=True)
                return
            await i.response.send_modal(
                WithdrawCryptoModal(asset, self._user_id, self._balance_pln)
            )

        sel.callback = on_select
        self.add_item(sel)


class WithdrawCryptoModal(discord.ui.Modal, title="Crypto withdrawal"):
    amount = discord.ui.TextInput(label="Amount in PLN", placeholder="e.g. 100", required=True)
    address = discord.ui.TextInput(
        label="Your receiving address",
        required=True,
        max_length=128,
    )

    def __init__(self, asset, user_id: int, balance_pln: Decimal) -> None:
        super().__init__()
        self._asset = asset
        self._user_id = user_id
        self._balance_pln = balance_pln

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            pln = Decimal(str(self.amount).strip().replace(",", "."))
            if pln <= 0:
                raise ValueError("Amount must be greater than zero")
        except (InvalidOperation, ValueError) as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        err = withdraw_balance_error(pln, self._balance_pln)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        ctx = {
            "method": "crypto",
            "asset": self._asset.value,
            "user_id": self._user_id,
            "amount_pln": str(pln),
            "address": str(self.address).strip(),
        }
        _withdraw_ctx[str(interaction.user.id)] = ctx
        await interaction.response.send_message(
            f"**Review crypto withdrawal**\n"
            f"**Balance after:** {self._balance_pln - pln:.2f} PLN\n"
            f"**Asset:** `{ctx['asset']}`\n"
            f"**Amount (PLN):** `{pln:.2f}`\n"
            f"**Destination:** `{ctx['address']}`\n\n"
            "Confirm only if the address is correct — crypto transfers cannot be reversed.",
            view=WithdrawConfirmView("crypto", ctx),
            ephemeral=True,
        )


class WithdrawTelModal(discord.ui.Modal, title="Phone transfer (BLIK)"):
    amount = discord.ui.TextInput(label="Amount in PLN", placeholder="e.g. 50", required=True)
    phone = discord.ui.TextInput(
        label="Your phone number",
        placeholder="+48…",
        required=True,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            lookup = await _lookup_user(interaction)
        except Exception:
            log.exception("lookup tel withdraw")
            await interaction.response.send_message(
                "❌ **Server error.** Please try again.",
                ephemeral=True,
            )
            return
        if not lookup:
            await interaction.response.send_message(
                "❌ **No linked account.** Register in the **Auth** channel first.",
                ephemeral=True,
            )
            return

        try:
            pln = parse_pln(str(self.amount))
        except (InvalidOperation, ValueError) as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        balance = Decimal(str(lookup.get("balancePln", 0)))
        err = withdraw_balance_error(pln, balance)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        ctx = {
            "method": "tel",
            "amount": str(pln),
            "phone": str(self.phone).strip(),
            "user_id": lookup["userId"],
        }
        _withdraw_ctx[str(interaction.user.id)] = ctx
        await interaction.response.send_message(
            f"**Review BLIK withdrawal**\n"
            f"**Balance after:** {balance - pln:.2f} PLN\n"
            f"**Amount:** **{pln:.2f} PLN**\n"
            f"**Phone:** `{ctx['phone']}`\n\n"
            "After you confirm, depositors can send matching BLIK transfers to fund this payout.",
            view=WithdrawConfirmView("tel", ctx),
            ephemeral=True,
        )


class WithdrawConfirmView(discord.ui.View):
    def __init__(self, method: str, ctx: dict) -> None:
        super().__init__(timeout=120)
        self._method = method
        self._ctx = ctx

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, _btn: discord.ui.Button) -> None:
        await _safe_defer(interaction)
        if self._method == "crypto":
            from app.payments.types import PaymentAsset

            try:
                pln = Decimal(str(self._ctx.get("amount_pln", "")).strip().replace(",", "."))
                if pln <= 0:
                    raise ValueError("Amount must be greater than zero")
                asset = PaymentAsset(self._ctx["asset"])
                crypto_amt = await pln_to_crypto(asset.value, pln)
                data = await call_backend("/api/payments/internal/withdraw", {
                    "asset": asset.value,
                    "amount": str(crypto_amt),
                    "destination_address": self._ctx.get("address", ""),
                    "user_id": self._ctx.get("user_id"),
                    "amount_pln": str(pln),
                })
            except BackendError as exc:
                detail = exc.data.get("detail")
                msg = format_withdraw_detail(detail)
                if not msg and isinstance(detail, str):
                    msg = f"❌ {detail}"
                if not msg:
                    msg = "❌ **Server error.** Please try again."
                await interaction.followup.send(msg, ephemeral=True)
                return
            except (InvalidOperation, ValueError) as e:
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
                return
            except Exception as exc:
                log.exception("withdraw: %s", exc)
                await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
                return
            msg = (
                f"✅ **Withdrawal #{data['id']} is open**\n\n"
                f"**Target:** **{pln:.2f} PLN** → `{crypto_amt}` {asset.value}\n"
                f"**Address:** `{self._ctx.get('address')}`\n\n"
                "Depositors can send crypto to this address (including partial amounts). "
                "The withdrawal closes automatically once the full amount is confirmed on-chain."
            )
            await interaction.followup.send(msg, ephemeral=True)
            return
        try:
            user_id = self._ctx.get("user_id")
            if not user_id:
                lookup = await _lookup_user(interaction)
                if not lookup:
                    await interaction.followup.send("❌ **No linked account.**", ephemeral=True)
                    return
                user_id = lookup["userId"]
            pln = parse_pln(str(self._ctx.get("amount", "")))
            data = await blik_create_withdraw(
                user_id=int(user_id),
                amount_pln=pln,
                phone=str(self._ctx.get("phone", "")),
                platform="discord",
                discord_id=str(interaction.user.id),
            )
        except BackendError as exc:
            await interaction.followup.send(withdraw_error_message(exc), ephemeral=True)
            return
        except (InvalidOperation, ValueError) as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except Exception:
            log.exception("blik withdraw")
            await interaction.followup.send("❌ **Server error.** Please try again.", ephemeral=True)
            return
        msg = (
            f"✅ **BLIK withdrawal #{data['id']} is waiting for deposits**\n\n"
            f"**Amount:** **{pln:.2f} PLN**\n"
            f"**Phone:** `{data.get('phone')}`\n\n"
            "Other users can deposit the same PLN amount via BLIK. "
            "The payout completes only after the depositor uploads bank proof on **czutkabet.com** and our system verifies it."
        )
        await interaction.followup.send(msg, ephemeral=True)


