"""Tests for dynamic fair crypto odds."""
from __future__ import annotations

from app.btc_price_samples import BtcPriceSamples
from app.crypto_fair_odds import CryptoFairOddsService, _realized_annual_vol
from app.crypto_odds import (
    CRYPTO_BTC_VOL,
    calc_crypto_odds_with_vol,
    time_urgency_scale,
)


def test_samples_keep_last_30():
    buf = BtcPriceSamples(30)
    for i in range(40):
        buf.record(100_000.0 + i, i * 1000)
    assert len(buf) == 30
    assert buf.list()[0].price == 100_010.0


def test_realized_vol_from_flat_prices_is_low():
    samples = BtcPriceSamples(10)
    t0 = 1_000_000
    for i in range(10):
        samples.record(50_000.0 + (i % 2) * 0.01, t0 + i * 2000)
    vol = _realized_annual_vol(samples.list())
    assert vol is not None
    assert vol < 0.15


def test_dynamic_vol_uses_observed_when_enough_samples():
    svc = CryptoFairOddsService()
    t0 = 2_000_000
    p = 100_000.0
    for i in range(12):
        svc.record_price(p + (i % 2) * 0.5, t0 + i * 1500)
    eff = svc.effective_vol()
    assert CRYPTO_BTC_VOL <= eff <= 3.20


def test_time_left_amplifies_odds_near_close():
    vol = CRYPTO_BTC_VOL
    gap = (100_050.0, 100_000.0)
    early = calc_crypto_odds_with_vol(vol, *gap, 270.0, window_sec=300.0)
    late = calc_crypto_odds_with_vol(vol, *gap, 30.0, window_sec=300.0)
    assert late["up"] < early["up"]
    assert late["down"] > early["down"]
    assert time_urgency_scale(30.0, 300.0) < time_urgency_scale(270.0, 300.0)


def test_calc_odds_with_window_matches_helper():
    svc = CryptoFairOddsService()
    o = svc.calc_odds(100_050.0, 100_000.0, 180.0, window="5m")
    expected = calc_crypto_odds_with_vol(
        svc.effective_vol(),
        100_050.0,
        100_000.0,
        180.0,
        window_sec=300.0,
    )
    assert o == expected
    assert o["up"] >= 1.01
    assert o["down"] >= 1.01


def test_movement_summary_trend():
    svc = CryptoFairOddsService()
    t0 = 3_000_000
    for i in range(8):
        svc.record_price(100_000.0 + i * 15.0, t0 + i * 1000)
    meta = svc.fair_odds_meta()
    assert meta["trend"] == "up"
    assert meta["recentMovePct"] > 0


def test_odds_context_includes_time_fraction():
    svc = CryptoFairOddsService()
    ctx = svc.odds_context(60.0, window="5m")
    assert ctx["window"] == "5m"
    assert ctx["timeFraction"] == 0.2
    assert ctx["timeScale"] < 1.0
