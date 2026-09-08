"""Pricing. One Black-Scholes, one rate, and a refusal to price what it cannot.

The repo's central finding is that a MODELLED option price overstated a credit by
mispricing the wings, and that inflation was the entire apparent 0DTE edge: +3.7% per
trade modelled against approximately break-even on 1,919 sessions of real bid/ask.
When the model is the thing that misled you, it deserves tests.
"""
import math

import numpy as np
import pytest

from idt import bs


# ------------------------------------------------------------ the model itself ---

def test_put_call_parity_holds():
    """C - P = S - K*exp(-rT). If parity breaks, the model is wrong, not approximate."""
    S, K, T, iv, r = 6000.0, 5950.0, 0.05, 0.18, bs.RISK_FREE
    c = float(bs.price(S, K, T, iv, call=True))
    p = float(bs.price(S, K, T, iv, call=False))
    assert c - p == pytest.approx(S - K * math.exp(-r * T), rel=1e-9)


def test_at_expiry_returns_intrinsic_not_a_model_number():
    assert float(bs.price(6000, 5900, 0, 0.2, call=True)) == pytest.approx(100.0)
    assert float(bs.price(6000, 5900, 0, 0.2, call=False)) == pytest.approx(0.0)
    assert float(bs.price(6000, 6100, 0, 0.2, call=False)) == pytest.approx(100.0)


def test_zero_vol_returns_intrinsic():
    assert float(bs.price(6000, 5900, 0.05, 0, call=True)) == pytest.approx(100.0)


def test_price_is_monotone_in_vol():
    """More vol is worth more. A model that fails this is not usable for a wing."""
    prev = -1.0
    for iv in (0.05, 0.10, 0.20, 0.40, 0.80):
        v = float(bs.price(6000, 6100, 0.05, iv, call=True))
        assert v > prev
        prev = v


def test_gamma_is_highest_at_the_money():
    atm = float(bs.gamma(6000, 6000, 0.02, 0.15))
    for k in (5800, 5900, 6100, 6200):
        assert float(bs.gamma(6000, k, 0.02, 0.15)) < atm


def test_delta_bounds():
    for k in (5000, 5900, 6000, 6100, 7000):
        d = float(bs.delta(6000, k, 0.05, 0.2, call=True))
        assert 0.0 <= d <= 1.0
        dp = float(bs.delta(6000, k, 0.05, 0.2, call=False))
        assert -1.0 <= dp <= 0.0


def test_vectorised_and_scalar_agree():
    """gex_periscope calls this with numpy arrays and condor with scalars."""
    ks = np.array([5900.0, 6000.0, 6100.0])
    vec = bs.gamma(6000.0, ks, 0.02, 0.15)
    for i, k in enumerate(ks):
        assert float(vec[i]) == pytest.approx(float(bs.gamma(6000.0, float(k), 0.02, 0.15)))


# ------------------------------------------------------- one rate, everywhere ---

def test_live_modules_share_one_risk_free_rate():
    """Four implementations existed with two different rates, and nothing compared them."""
    import sys, os
    live = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "04_live_system")
    if live not in sys.path:
        sys.path.insert(0, live)
    import condor
    import gex_periscope

    S, K, T, iv = 6000.0, 6050.0, 0.02, 0.15
    assert condor._bs(S, K, T, iv, call=True) == pytest.approx(
        float(bs.price(S, K, T, iv, call=True))), "condor drifted from idt.bs"
    assert float(gex_periscope.bs_gamma(S, K, T, iv)) == pytest.approx(
        float(bs.gamma(S, K, T, iv))), "gex_periscope drifted from idt.bs"


# ----------------------------------------------- the pricer refuses bad quotes ---
#
# option_pricer's whole contract is that it returns None rather than a plausible-looking
# fabrication. "Everything returns None on failure instead of a plausible-looking
# fabrication" is its own docstring, and it is the guardrail that stops an untradeable
# strike reaching the book.

@pytest.fixture
def pricer():
    import sys, os
    live = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "04_live_system")
    if live not in sys.path:
        sys.path.insert(0, live)
    import option_pricer
    return option_pricer


def test_pricer_declares_its_liquidity_floors(pricer):
    """These thresholds are provisional and must stay visible, not buried in a branch."""
    assert pricer.MAX_SPREAD_PCT > 0
    assert pricer.MAX_SPREAD_PCT_EQUITY > pricer.MAX_SPREAD_PCT, \
        "an equity vertical legitimately quotes wider than a liquid index"
    assert pricer.MIN_OI >= 1


class _FakeChain:
    """A yfinance-shaped option chain, so quote() can be exercised without a network."""

    def __init__(self, rows):
        import pandas as pd
        self.calls = pd.DataFrame(rows)
        self.puts = pd.DataFrame(rows)


def _chain_of(bid, ask, oi=500, strike=6000.0):
    return _FakeChain([{"strike": strike, "bid": bid, "ask": ask, "openInterest": oi,
                        "impliedVolatility": 0.15}])


@pytest.mark.parametrize("bid,ask,why", [
    (0.0, 1.20, "a zero bid is not a two-sided market"),
    (1.20, 0.0, "a zero ask is not a two-sided market"),
    (1.50, 1.20, "a crossed market (bid above ask) is not a market"),
    (0.0, 0.0, "an empty quote is not a price"),
])
def test_pricer_refuses_an_untradeable_quote(pricer, monkeypatch, bid, ask, why):
    """It must return None rather than a plausible-looking number.

    This is option_pricer's own stated contract: "everything returns None on failure
    instead of a plausible-looking fabrication". It is the guardrail that stops an
    untradeable strike reaching the book, and it had no test.
    """
    monkeypatch.setattr(pricer, "_chain", lambda sym, expiry: _chain_of(bid, ask))
    assert pricer.quote("SPY", "2026-08-25", 6000.0, "C") is None, why


def test_pricer_prices_a_clean_two_sided_market(pricer, monkeypatch):
    monkeypatch.setattr(pricer, "_chain", lambda sym, expiry: _chain_of(1.20, 1.30))
    q = pricer.quote("SPY", "2026-08-25", 6000.0, "C")
    assert q is not None
    assert q["mid"] == pytest.approx(1.25)
    assert q["tradeable"] is True


def test_pricer_marks_an_illiquid_strike_untradeable(pricer, monkeypatch):
    """Low open interest does not make the quote a lie, so it prices but refuses."""
    monkeypatch.setattr(pricer, "_chain",
                        lambda sym, expiry: _chain_of(1.20, 1.30, oi=1))
    q = pricer.quote("SPY", "2026-08-25", 6000.0, "C")
    assert q is not None
    assert q["tradeable"] is False
    assert "open interest" in q["reject"]


def test_pricer_returns_none_when_there_is_no_chain(pricer, monkeypatch):
    """A missing chain is an absent market, not an empty one."""
    monkeypatch.setattr(pricer, "_chain", lambda sym, expiry: None)
    assert pricer.quote("SPY", "2026-08-25", 6000.0, "C") is None
