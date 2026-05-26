"""Sweep confirmed deposits from derived addresses to MASTER_* wallets."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

import httpx
from eth_account import Account

from ..config import get_settings
from .keys import btc_private_key_wif, eth_private_key_bytes
from .monitors.eth import _rpc
from .types import PaymentAsset

log = logging.getLogger(__name__)

WEI = Decimal(10**18)
BLOCKSTREAM = "https://blockstream.info/api"
CHAIN_ID = 1
SOL_TX_FEE_LAMPORTS = 5000
LAMPORTS_PER_SOL = 1_000_000_000


class SweepDeferred(Exception):
    """Deposit address balance too low to sweep yet — try again later."""


async def deposit_on_chain_balance(
    client: httpx.AsyncClient, asset: PaymentAsset, address: str
) -> Decimal:
    from .monitors.holdings import get_address_holdings

    return await get_address_holdings(client, asset, address)


async def sweep_readiness(
    client: httpx.AsyncClient,
    asset: PaymentAsset,
    address: str,
    *,
    derivation_index: Optional[int] = None,
) -> tuple[bool, str]:
    """Return (ready, reason). Ready means we can sweep the full on-chain balance."""
    settings = get_settings()
    balance = await deposit_on_chain_balance(client, asset, address)

    if asset == PaymentAsset.SOL:
        lamports = int(balance * LAMPORTS_PER_SOL)
        min_lamports = max(
            int(Decimal(str(settings.sweep_min_sol)) * LAMPORTS_PER_SOL),
            SOL_TX_FEE_LAMPORTS + 1,
        )
        if lamports < min_lamports:
            return (
                False,
                f"SOL balance {balance} below sweep minimum "
                f"({settings.sweep_min_sol} SOL / {min_lamports} lamports)",
            )
        return True, ""

    if asset == PaymentAsset.ETH:
        if balance < Decimal(str(settings.sweep_min_eth)):
            return False, f"ETH balance {balance} below minimum {settings.sweep_min_eth}"
        gas_price = int(await _rpc(client, "eth_gasPrice", []), 16)
        need = Decimal(gas_price * 21_000) / WEI
        if balance <= need:
            return False, f"ETH balance {balance} too low for gas (~{need} ETH)"
        return True, ""

    if asset == PaymentAsset.BTC:
        if balance < Decimal(str(settings.sweep_min_btc)):
            return False, f"BTC balance {balance} below minimum {settings.sweep_min_btc}"
        return True, ""

    if asset in (PaymentAsset.USDC_ETH, PaymentAsset.USDC_SOL):
        min_usdc = Decimal(str(settings.sweep_min_usdc))
        if balance < min_usdc:
            return False, f"USDC balance {balance} below minimum {min_usdc}"
        if asset == PaymentAsset.USDC_ETH and derivation_index is not None:
            eth = await deposit_on_chain_balance(
                client, PaymentAsset.ETH, address
            )
            gas_price = int(await _rpc(client, "eth_gasPrice", []), 16)
            need = Decimal(gas_price * 80_000) / WEI
            if eth < need:
                return False, f"need ~{need} ETH on address for USDC sweep gas (have {eth})"
        if asset == PaymentAsset.USDC_SOL:
            sol = await deposit_on_chain_balance(client, PaymentAsset.SOL, address)
            if sol < Decimal(str(settings.sweep_min_sol)):
                return (
                    False,
                    f"need SOL on address for USDC sweep fees (have {sol}, "
                    f"min {settings.sweep_min_sol})",
                )
        return True, ""

    return False, f"unsupported asset {asset.value}"


def _master_for_asset(asset: PaymentAsset) -> str:
    settings = get_settings()
    if asset == PaymentAsset.BTC:
        return settings.master_btc_address.strip()
    if asset == PaymentAsset.ETH:
        return settings.master_eth_address.strip()
    if asset == PaymentAsset.USDC_ETH:
        return settings.master_usdc_eth
    if asset == PaymentAsset.SOL:
        return settings.master_solana_address.strip()
    if asset == PaymentAsset.USDC_SOL:
        return settings.master_usdc_solana
    raise ValueError(f"no master for {asset}")


async def sweep_payment(doc: dict[str, Any], *, force: bool = False) -> Optional[str]:
    """
    Move funds from deposit address to master. Returns sweep tx id/hash or None if skipped.
    """
    settings = get_settings()
    if not settings.payment_auto_sweep and not force:
        return None

    asset = PaymentAsset(doc["asset"])
    index = int(doc["derivation_index"])
    from_addr = (doc.get("address") or "").strip()
    master = _master_for_asset(asset)

    if not master:
        log.warning("sweep skipped: no master address for %s", asset.value)
        return None
    if from_addr.lower() == master.lower():
        log.info("sweep skipped: deposit is already master index")
        return None

    async with httpx.AsyncClient() as client:
        ready, reason = await sweep_readiness(
            client, asset, from_addr, derivation_index=index
        )
        if not ready:
            raise SweepDeferred(reason)

        if asset == PaymentAsset.ETH:
            return await _sweep_eth(client, index, from_addr, master)
        if asset == PaymentAsset.BTC:
            return await _sweep_btc(client, index, from_addr, master)
        if asset == PaymentAsset.USDC_ETH:
            return await _sweep_usdc_eth(client, index, from_addr, master)
        if asset == PaymentAsset.SOL:
            return await _sweep_sol(client, index, from_addr, master)
        if asset == PaymentAsset.USDC_SOL:
            return await _sweep_usdc_sol(client, index, from_addr, master)
        log.info("sweep not implemented for %s", asset.value)
        return None


async def _sweep_eth(
    client: httpx.AsyncClient,
    derivation_index: int,
    from_addr: str,
    master: str,
) -> str:
    balance_hex = await _rpc(client, "eth_getBalance", [from_addr, "latest"])
    balance_wei = int(balance_hex, 16)
    if balance_wei == 0:
        raise SweepDeferred("nothing to sweep (0 ETH balance)")

    gas_price_hex = await _rpc(client, "eth_gasPrice", [])
    gas_price = int(gas_price_hex, 16)
    gas_limit = 21_000
    fee = gas_price * gas_limit
    send_value = balance_wei - fee
    if send_value <= 0:
        raise SweepDeferred(
            f"ETH balance too low to pay gas (have {balance_wei} wei, need >{fee} wei fee)"
        )

    nonce_hex = await _rpc(client, "eth_getTransactionCount", [from_addr, "pending"])
    nonce = int(nonce_hex, 16)

    acct = Account.from_key(eth_private_key_bytes(derivation_index))
    tx = {
        "nonce": nonce,
        "to": master,
        "value": send_value,
        "gas": gas_limit,
        "gasPrice": gas_price,
        "chainId": CHAIN_ID,
    }
    signed = acct.sign_transaction(tx)
    raw = signed.raw_transaction.hex()
    if not raw.startswith("0x"):
        raw = "0x" + raw
    tx_hash = await _rpc(client, "eth_sendRawTransaction", [raw])
    log.info("ETH swept %s -> %s tx=%s", from_addr, master, tx_hash)
    return tx_hash


async def _sweep_usdc_eth(
    client: httpx.AsyncClient,
    derivation_index: int,
    from_addr: str,
    master: str,
) -> str:
    settings = get_settings()
    contract = settings.usdc_eth_contract
    data = "0x70a08231" + from_addr.lower().replace("0x", "").zfill(64)
    bal_hex = await _rpc(client, "eth_call", [{"to": contract, "data": data}, "latest"])
    amount = int(bal_hex, 16)
    if amount == 0:
        raise SweepDeferred("no USDC balance to sweep")

    # transfer(address,uint256)
    method = "0xa9059cbb"
    data = method + master.lower().replace("0x", "").zfill(64) + hex(amount)[2:].zfill(64)
    if not data.startswith("0x"):
        data = "0x" + data

    nonce = int(await _rpc(client, "eth_getTransactionCount", [from_addr, "pending"]), 16)
    gas_price = int(await _rpc(client, "eth_gasPrice", []), 16)

    # fund gas for token tx if needed
    eth_bal = int(await _rpc(client, "eth_getBalance", [from_addr, "latest"]), 16)
    gas_limit = 80_000
    need_gas = gas_price * gas_limit
    if eth_bal < need_gas:
        await _fund_gas_from_master(client, master, from_addr, need_gas - eth_bal + 10_000)

    acct = Account.from_key(eth_private_key_bytes(derivation_index))
    tx = {
        "nonce": nonce,
        "to": contract,
        "value": 0,
        "data": data,
        "gas": gas_limit,
        "gasPrice": gas_price,
        "chainId": CHAIN_ID,
    }
    signed = acct.sign_transaction(tx)
    raw = signed.raw_transaction.hex()
    if not raw.startswith("0x"):
        raw = "0x" + raw
    tx_hash = await _rpc(client, "eth_sendRawTransaction", [raw])
    log.info("USDC swept %s -> %s tx=%s", from_addr, master, tx_hash)
    return tx_hash


async def _fund_gas_from_master(
    client: httpx.AsyncClient, master: str, to_addr: str, amount_wei: int
) -> None:
    """Send a little ETH from master (index 0) so token sweep can pay gas."""
    if amount_wei <= 0:
        return
    nonce = int(await _rpc(client, "eth_getTransactionCount", [master, "pending"]), 16)
    gas_price = int(await _rpc(client, "eth_gasPrice", []), 16)
    gas_limit = 21_000
    acct = Account.from_key(eth_private_key_bytes(0))
    tx = {
        "nonce": nonce,
        "to": to_addr,
        "value": amount_wei,
        "gas": gas_limit,
        "gasPrice": gas_price,
        "chainId": CHAIN_ID,
    }
    signed = acct.sign_transaction(tx)
    raw = signed.raw_transaction.hex()
    if not raw.startswith("0x"):
        raw = "0x" + raw
    await _rpc(client, "eth_sendRawTransaction", [raw])
    log.info("funded gas %s wei to %s for token sweep", amount_wei, to_addr)


def _btc_address_script_pubkey(address: str) -> bytes:
    from embit.bech32 import decode

    hrp = "bc" if address.startswith("bc1") else "tb"
    ver, prog = decode(hrp, address)
    return bytes([ver, len(prog)]) + bytes(prog)


async def _sweep_btc(
    client: httpx.AsyncClient,
    derivation_index: int,
    from_addr: str,
    master: str,
) -> str:
    """Sweep all UTXOs from deposit address to master via Blockstream."""
    try:
        from embit import ec, script
        from embit.transaction import Transaction, TransactionInput, TransactionOutput
    except ImportError as e:
        raise RuntimeError("install embit for BTC sweep: pip install embit") from e

    utxo_r = await client.get(f"{BLOCKSTREAM}/address/{from_addr}/utxo", timeout=30)
    utxo_r.raise_for_status()
    utxos = utxo_r.json()
    if not utxos:
        raise SweepDeferred("no UTXOs to sweep")

    wif = btc_private_key_wif(derivation_index)
    key = ec.PrivateKey.from_wif(wif)
    spk = script.p2wpkh(key.pubkey)

    inputs = []
    total_in = 0
    for u in utxos:
        total_in += u["value"]
        inputs.append(
            TransactionInput(
                bytes.fromhex(u["txid"])[::-1],
                u["vout"],
                script=b"",
                sequence=0xFFFFFFFD,
            )
        )

    fee_rate = 12
    est_vsize = 110 + 40 * len(utxos)
    fee = est_vsize * fee_rate
    out_value = total_in - fee
    if out_value <= 546:
        raise SweepDeferred("BTC balance too small after fees")

    master_spk = _btc_address_script_pubkey(master)
    outputs = [TransactionOutput(out_value, master_spk)]

    tx = Transaction(vin=inputs, vout=outputs)
    for i in range(len(utxos)):
        tx.vin[i].script = spk.script_pubkey()
    tx.sign(key)
    raw = tx.serialize().hex()

    push = await client.post(f"{BLOCKSTREAM}/tx", content=raw, timeout=60)
    push.raise_for_status()
    txid = push.text.strip()
    log.info("BTC swept %s -> %s tx=%s", from_addr, master, txid)
    return txid


async def _sol_rpc(
    client: httpx.AsyncClient, method: str, params: list
) -> Any:
    settings = get_settings()
    r = await client.post(
        settings.solana_rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=60,
    )
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(body["error"])
    return body["result"]


async def _sweep_sol(
    client: httpx.AsyncClient,
    derivation_index: int,
    from_addr: str,
    master: str,
) -> str:
    from solders.hash import Hash
    from solders.message import Message
    from solders.pubkey import Pubkey
    from solders.system_program import TransferParams, transfer
    from solders.transaction import Transaction

    from .keys import sol_keypair
    from .sol_derivation import ensure_solana_profile

    ensure_solana_profile(get_settings().master_solana_address.strip())
    kp = sol_keypair(derivation_index)
    if str(kp.pubkey()) != from_addr:
        raise RuntimeError("sol keypair does not match deposit address")

    balance = await _sol_rpc(
        client, "getBalance", [from_addr, {"commitment": "confirmed"}]
    )
    lamports = int(balance.get("value", 0))
    fee = 5000
    # Drain deposit account: transfer all lamports minus tx fee (closes empty account).
    send_lamports = lamports - fee
    if send_lamports <= 0:
        raise SweepDeferred(
            f"SOL balance too low to sweep (have {lamports} lamports, need >{fee})"
        )

    blockhash = await _sol_rpc(
        client, "getLatestBlockhash", [{"commitment": "finalized"}]
    )
    bh = blockhash["value"]["blockhash"]
    ix = transfer(
        TransferParams(
            from_pubkey=kp.pubkey(),
            to_pubkey=Pubkey.from_string(master),
            lamports=send_lamports,
        )
    )
    msg = Message.new_with_blockhash([ix], kp.pubkey(), Hash.from_string(bh))
    tx = Transaction.new_unsigned(msg)
    tx.sign([kp], Hash.from_string(bh))
    raw = bytes(tx)
    import base64

    sig = await _sol_rpc(
        client,
        "sendTransaction",
        [base64.b64encode(raw).decode(), {"encoding": "base64", "skipPreflight": False}],
    )
    log.info("SOL swept %s -> %s sig=%s", from_addr, master, sig)
    return str(sig)


def _associated_token_address(owner: str, mint: str) -> str:
    from solders.pubkey import Pubkey

    TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    ATA_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    owner_pk = Pubkey.from_string(owner)
    mint_pk = Pubkey.from_string(mint)
    ata, _ = Pubkey.find_program_address(
        [bytes(owner_pk), bytes(TOKEN_PROGRAM), bytes(mint_pk)],
        ATA_PROGRAM,
    )
    return str(ata)


async def _sweep_usdc_sol(
    client: httpx.AsyncClient,
    derivation_index: int,
    from_addr: str,
    master: str,
) -> str:
    import base64
    import struct

    from solders.hash import Hash
    from solders.instruction import AccountMeta, Instruction
    from solders.message import Message
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction

    from .keys import sol_keypair
    from .sol_derivation import ensure_solana_profile

    ensure_solana_profile(get_settings().master_solana_address.strip())
    settings = get_settings()
    mint = settings.usdc_solana_mint
    kp = sol_keypair(derivation_index)

    accounts = await _sol_rpc(
        client,
        "getTokenAccountsByOwner",
        [
            from_addr,
            {"mint": mint},
            {"encoding": "jsonParsed", "commitment": "confirmed"},
        ],
    )
    value = accounts.get("value") or []
    if not value:
        raise SweepDeferred("no USDC token account to sweep")

    source = value[0]["pubkey"]
    amount_raw = int(
        (
            ((value[0].get("account") or {}).get("data") or {})
            .get("parsed", {})
            .get("info", {})
            .get("tokenAmount", {})
            .get("amount", 0)
        )
    )
    if amount_raw <= 0:
        raise SweepDeferred("no USDC balance to sweep")

    dest_ata = _associated_token_address(master, mint)
    dest_info = await _sol_rpc(
        client, "getAccountInfo", [dest_ata, {"encoding": "base64"}]
    )
    instructions = []
    if dest_info.get("value") is None:
        ATA_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
        TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        SYS_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
        mint_pk = Pubkey.from_string(mint)
        # createAssociatedTokenAccount (id=1)
        create_data = bytes([1])
        instructions.append(
            Instruction(
                program_id=ATA_PROGRAM,
                accounts=[
                    AccountMeta(kp.pubkey(), True, True),
                    AccountMeta(Pubkey.from_string(dest_ata), False, True),
                    AccountMeta(Pubkey.from_string(master), False, False),
                    AccountMeta(mint_pk, False, False),
                    AccountMeta(SYS_PROGRAM, False, False),
                    AccountMeta(TOKEN_PROGRAM, False, False),
                ],
                data=create_data,
            )
        )

    TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    transfer_data = bytes([3]) + struct.pack("<Q", amount_raw)
    instructions.append(
        Instruction(
            program_id=TOKEN_PROGRAM,
            accounts=[
                AccountMeta(Pubkey.from_string(source), False, True),
                AccountMeta(Pubkey.from_string(dest_ata), False, True),
                AccountMeta(kp.pubkey(), True, False),
            ],
            data=transfer_data,
        )
    )

    sol_bal = int(
        (await _sol_rpc(client, "getBalance", [from_addr, {"commitment": "confirmed"}]))
        .get("value", 0)
    )
    if sol_bal < 5_000_000:
        raise RuntimeError(
            "deposit address needs ~0.005 SOL on-chain to pay USDC sweep fees"
        )

    blockhash = await _sol_rpc(
        client, "getLatestBlockhash", [{"commitment": "finalized"}]
    )
    bh = blockhash["value"]["blockhash"]
    msg = Message.new_with_blockhash(instructions, kp.pubkey(), Hash.from_string(bh))
    tx = Transaction.new_unsigned(msg)
    tx.sign([kp], Hash.from_string(bh))
    sig = await _sol_rpc(
        client,
        "sendTransaction",
        [base64.b64encode(bytes(tx)).decode(), {"encoding": "base64"}],
    )
    log.info("USDC (Solana) swept %s -> %s sig=%s", from_addr, master, sig)
    return str(sig)
