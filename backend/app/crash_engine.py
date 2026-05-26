"""Shared Crash round loop — provably-fair multiplier game."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import math
import secrets
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from fastapi import WebSocket
from pymongo import ReturnDocument

from .casino_rtp import crash_multiplier, crash_payout_boost, resolve_rtp
from .db import get_db, next_id, now
from .rewards_service import record_vip_activity

log = logging.getLogger(__name__)

WAITING_SEC = 5.0
CRASHED_SEC = 2.5
TICK_INTERVAL = 0.05
GROWTH_RATE = 0.0693
HISTORY_MAX = 5
_CRASH_HISTORY_DOC_ID = "recent"
_MAX_WS_PER_IP = 5
_WS_IDLE_SEC = 300.0


def _crash_point(seed: str) -> float:
    digest = hmac.new(seed.encode(), b"crash", hashlib.sha256).digest()
    r = int.from_bytes(digest[:8], "big") / 2**64
    return crash_multiplier(r)


def multiplier_at(elapsed_sec: float) -> float:
    if elapsed_sec <= 0:
        return 1.0
    return round(math.exp(GROWTH_RATE * elapsed_sec), 2)


@dataclass
class CrashBet:
    user_id: int
    stake: Decimal
    auto_cashout: Optional[float] = None
    cashed_out: bool = False
    cashout_at: Optional[float] = None
    payout: Decimal = Decimal("0.00")


@dataclass
class CrashRound:
    round_id: int
    phase: str  # waiting | running | crashed
    seed: str
    crash_point: float
    waiting_ends_at: float
    running_started_at: Optional[float] = None
    crashed_at: Optional[float] = None
    bets: dict[int, CrashBet] = field(default_factory=dict)


class CrashEngine:
    def __init__(self) -> None:
        self._round: Optional[CrashRound] = None
        self._queued: dict[int, CrashBet] = {}
        self._history: list[float] = []
        self._clients: dict[WebSocket, Optional[int]] = {}
        self._ws_per_ip: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        self._round_counter = 0

    async def start(self) -> None:
        if self._task is not None:
            return
        await self._load_history()
        await self._new_round()
        self._task = asyncio.create_task(self._loop(), name="crash-engine")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        for ws in list(self._clients):
            try:
                await ws.close()
            except Exception:
                pass
        self._clients.clear()

    async def connect(
        self,
        ws: WebSocket,
        user_id: Optional[int] = None,
        *,
        client_ip: str = "unknown",
    ) -> None:
        ip = client_ip or "unknown"
        if self._ws_per_ip.get(ip, 0) >= _MAX_WS_PER_IP:
            await ws.close(code=1008, reason="too many connections")
            return
        self._ws_per_ip[ip] = self._ws_per_ip.get(ip, 0) + 1
        await ws.accept()
        self._clients[ws] = user_id
        try:
            await ws.send_json(self.public_snapshot(user_id))
            while True:
                await asyncio.wait_for(ws.receive_text(), timeout=_WS_IDLE_SEC)
        except Exception:
            pass
        finally:
            self._clients.pop(ws, None)
            count = self._ws_per_ip.get(ip, 1) - 1
            if count <= 0:
                self._ws_per_ip.pop(ip, None)
            else:
                self._ws_per_ip[ip] = count

    def public_snapshot(self, user_id: Optional[int] = None) -> dict[str, Any]:
        rnd = self._round
        if rnd is None:
            body: dict[str, Any] = {
                "phase": "waiting",
                "roundId": 0,
                "multiplier": 1.0,
                "countdown": WAITING_SEC,
                "history": self._history,
            }
            if user_id is not None:
                body["myBet"] = None
                body["queuedBet"] = self._queued_bet_view(user_id)
            return body

        mult = self._current_multiplier()
        countdown = max(0.0, rnd.waiting_ends_at - time.monotonic()) if rnd.phase == "waiting" else 0.0
        elapsed = 0.0
        if rnd.phase == "running" and rnd.running_started_at is not None:
            elapsed = max(0.0, time.monotonic() - rnd.running_started_at)
        total_wagered = sum(float(b.stake) for b in rnd.bets.values())
        active = sum(1 for b in rnd.bets.values() if not b.cashed_out)
        body: dict[str, Any] = {
            "phase": rnd.phase,
            "roundId": rnd.round_id,
            "multiplier": mult,
            "countdown": round(countdown, 2),
            "history": list(self._history),
            "playerCount": len(rnd.bets),
            "activeCount": active,
            "totalWagered": round(total_wagered, 2),
        }
        if rnd.phase == "running":
            body["elapsed"] = round(elapsed, 3)
        if rnd.phase == "crashed":
            body["crashPoint"] = rnd.crash_point
            if rnd.running_started_at is not None and rnd.crashed_at is not None:
                body["elapsed"] = round(max(0.0, rnd.crashed_at - rnd.running_started_at), 3)
        if user_id is not None:
            body["myBet"] = self._user_bet_view(user_id)
            body["queuedBet"] = self._queued_bet_view(user_id)
        return body

    def _user_bet_view(self, user_id: int) -> Optional[dict]:
        rnd = self._round
        if rnd is None:
            return None
        bet = rnd.bets.get(user_id)
        if bet is None:
            return None
        return {
            "stake": float(bet.stake),
            "autoCashout": bet.auto_cashout,
            "cashedOut": bet.cashed_out,
            "cashoutAt": bet.cashout_at,
            "payout": float(bet.payout),
        }

    def _queued_bet_view(self, user_id: int) -> Optional[dict]:
        bet = self._queued.get(user_id)
        if bet is None:
            return None
        return {"stake": float(bet.stake), "autoCashout": bet.auto_cashout}

    def _current_multiplier(self) -> float:
        rnd = self._round
        if rnd is None:
            return 1.0
        if rnd.phase == "crashed":
            return rnd.crash_point
        if rnd.phase != "running" or rnd.running_started_at is None:
            return 1.0
        elapsed = time.monotonic() - rnd.running_started_at
        return multiplier_at(elapsed)

    async def place_bet(
        self,
        user_id: int,
        stake: Decimal,
        auto_cashout: Optional[float],
        balance_lock,
    ) -> dict[str, Any]:
        async with self._lock:
            rnd = self._round
            if rnd is None:
                raise ValueError("round unavailable")

            if user_id in rnd.bets:
                raise ValueError("already bet this round")
            if user_id in self._queued:
                raise ValueError("already queued for next round")

            bet = CrashBet(user_id=user_id, stake=stake, auto_cashout=auto_cashout)

            if rnd.phase == "waiting":
                await balance_lock()
                rnd.bets[user_id] = bet
            else:
                await balance_lock()
                self._queued[user_id] = bet

            snap = self.public_snapshot(user_id)
        await self._broadcast()
        return snap

    async def cashout(self, user_id: int) -> dict[str, Any]:
        async with self._lock:
            rnd = self._round
            if rnd is None or rnd.phase != "running":
                raise ValueError("not running")
            bet = rnd.bets.get(user_id)
            if bet is None or bet.cashed_out:
                raise ValueError("no active bet")

            mult = self._current_multiplier()
            if mult >= rnd.crash_point:
                raise ValueError("round crashed")

            rtp = await self._user_rtp(user_id)
            payout = self._crash_payout(bet.stake, mult, rtp)
            bet.cashed_out = True
            bet.cashout_at = mult
            bet.payout = payout

            balance = await self._credit_payout(user_id, bet, mult, rnd)
            snap = self.public_snapshot(user_id)
            snap["balance"] = float(balance)
            snap["payout"] = float(payout)
            snap["cashoutAt"] = mult

        await self._broadcast()
        return snap

    async def _user_rtp(self, user_id: int) -> float:
        doc = await get_db().users.find_one({"id": user_id}, {"casino_rtp": 1})
        return resolve_rtp(doc)

    @staticmethod
    def _crash_payout(stake: Decimal, mult: float, rtp: float) -> Decimal:
        boost = crash_payout_boost(rtp)
        return (stake * Decimal(str(mult)) * Decimal(str(boost))).quantize(Decimal("0.01"))

    async def _refund_stake(self, user_id: int, stake: Decimal) -> Decimal:
        db = get_db()
        updated = await db.users.find_one_and_update(
            {"id": user_id},
            {"$inc": {"balance_pln": stake}},
            return_document=ReturnDocument.AFTER,
        )
        return updated["balance_pln"] if updated else Decimal("0")

    async def cancel_bet(self, user_id: int) -> dict[str, Any]:
        async with self._lock:
            rnd = self._round
            if rnd is None:
                raise ValueError("round unavailable")

            if user_id in self._queued:
                bet = self._queued.pop(user_id)
                balance = await self._refund_stake(user_id, bet.stake)
                snap = self.public_snapshot(user_id)
                snap["balance"] = float(balance)
            elif rnd.phase == "waiting" and user_id in rnd.bets:
                bet = rnd.bets[user_id]
                if bet.cashed_out:
                    raise ValueError("no cancellable bet")
                del rnd.bets[user_id]
                balance = await self._refund_stake(user_id, bet.stake)
                snap = self.public_snapshot(user_id)
                snap["balance"] = float(balance)
            else:
                raise ValueError("no cancellable bet")

        await self._broadcast()
        return snap

    async def _credit_payout(
        self,
        user_id: int,
        bet: CrashBet,
        mult: float,
        rnd: CrashRound,
    ) -> Decimal:
        db = get_db()
        updated = await db.users.find_one_and_update(
            {"id": user_id},
            {"$inc": {"balance_pln": bet.payout}},
            return_document=ReturnDocument.AFTER,
        )
        await db.casino_rounds.insert_one(
            {
                "id": await next_id("casino_rounds"),
                "user_id": user_id,
                "game": "crash",
                "stake_pln": bet.stake,
                "payout_pln": bet.payout,
                "details": {
                    "round_id": rnd.round_id,
                    "crash_point": rnd.crash_point,
                    "cashout_at": mult,
                    "won": True,
                },
                "server_seed": rnd.seed,
                "created_at": now(),
            }
        )
        await record_vip_activity(user_id, bet.stake, bet.payout)
        return updated["balance_pln"] if updated else Decimal("0")

    async def _settle_loser(self, user_id: int, bet: CrashBet, rnd: CrashRound) -> None:
        db = get_db()
        await db.casino_rounds.insert_one(
            {
                "id": await next_id("casino_rounds"),
                "user_id": user_id,
                "game": "crash",
                "stake_pln": bet.stake,
                "payout_pln": Decimal("0.00"),
                "details": {
                    "round_id": rnd.round_id,
                    "crash_point": rnd.crash_point,
                    "won": False,
                },
                "server_seed": rnd.seed,
                "created_at": now(),
            }
        )
        await record_vip_activity(user_id, bet.stake, Decimal("0"))

    async def _load_history(self) -> None:
        try:
            doc = await get_db().crash_history.find_one({"_id": _CRASH_HISTORY_DOC_ID})
            if not doc:
                return
            out: list[float] = []
            for item in (doc.get("history") or [])[-HISTORY_MAX:]:
                if isinstance(item, dict):
                    cp = item.get("crash_point")
                else:
                    cp = item
                if cp is not None:
                    out.append(float(cp))
            self._history = out
        except Exception as exc:
            log.warning("load crash history: %s", exc)

    def _record_resolution(self, crash_point: float) -> None:
        self._history.append(crash_point)
        if len(self._history) > HISTORY_MAX:
            self._history = self._history[-HISTORY_MAX:]
        asyncio.create_task(self._persist_resolution(crash_point))

    async def _persist_resolution(self, crash_point: float) -> None:
        try:
            await get_db().crash_history.update_one(
                {"_id": _CRASH_HISTORY_DOC_ID},
                {
                    "$push": {
                        "history": {
                            "$each": [crash_point],
                            "$slice": -HISTORY_MAX,
                        }
                    },
                    "$set": {"updated_at": now()},
                },
                upsert=True,
            )
        except Exception as exc:
            log.warning("persist crash resolution failed: %s", exc)

    async def _new_round(self) -> None:
        self._round_counter += 1
        seed = secrets.token_hex(32)
        self._round = CrashRound(
            round_id=self._round_counter,
            phase="waiting",
            seed=seed,
            crash_point=_crash_point(seed),
            waiting_ends_at=time.monotonic() + WAITING_SEC,
        )
        for user_id, bet in list(self._queued.items()):
            self._round.bets[user_id] = bet
        self._queued.clear()

    async def _loop(self) -> None:
        while True:
            try:
                await self._tick_once()
                await asyncio.sleep(TICK_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("crash tick failed")
                await asyncio.sleep(1)

    async def _tick_once(self) -> None:
        async with self._lock:
            rnd = self._round
            if rnd is None:
                await self._new_round()
                return

            now_mono = time.monotonic()

            if rnd.phase == "waiting" and now_mono >= rnd.waiting_ends_at:
                rnd.phase = "running"
                rnd.running_started_at = now_mono

            if rnd.phase == "running" and rnd.running_started_at is not None:
                mult = multiplier_at(now_mono - rnd.running_started_at)
                for uid, bet in list(rnd.bets.items()):
                    if bet.cashed_out or bet.auto_cashout is None:
                        continue
                    if mult >= bet.auto_cashout and bet.auto_cashout < rnd.crash_point:
                        auto_mult = bet.auto_cashout
                        rtp = await self._user_rtp(uid)
                        bet.cashed_out = True
                        bet.cashout_at = auto_mult
                        bet.payout = self._crash_payout(bet.stake, auto_mult, rtp)
                        await self._credit_payout(uid, bet, auto_mult, rnd)
                if mult >= rnd.crash_point:
                    rnd.phase = "crashed"
                    rnd.crashed_at = now_mono
                    for uid, bet in rnd.bets.items():
                        if not bet.cashed_out:
                            if bet.auto_cashout and bet.auto_cashout <= rnd.crash_point:
                                auto_mult = min(bet.auto_cashout, rnd.crash_point)
                                rtp = await self._user_rtp(uid)
                                bet.cashed_out = True
                                bet.cashout_at = auto_mult
                                bet.payout = self._crash_payout(bet.stake, auto_mult, rtp)
                                await self._credit_payout(uid, bet, auto_mult, rnd)
                            else:
                                await self._settle_loser(uid, bet, rnd)
                    self._record_resolution(rnd.crash_point)

            if rnd.phase == "crashed" and rnd.crashed_at is not None:
                if now_mono - rnd.crashed_at >= CRASHED_SEC:
                    await self._new_round()

        await self._broadcast()

    async def _broadcast(self) -> None:
        dead: list[WebSocket] = []
        for ws, user_id in list(self._clients.items()):
            try:
                await ws.send_json(self.public_snapshot(user_id))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.pop(ws, None)


_engine: Optional[CrashEngine] = None


def get_crash_engine() -> CrashEngine:
    global _engine
    if _engine is None:
        _engine = CrashEngine()
    return _engine
