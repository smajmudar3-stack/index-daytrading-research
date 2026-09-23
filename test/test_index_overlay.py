"""The index overlay: the measured signal, exposure applied to the NEXT session, borrow charged."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_live_system"))
import index_overlay as io  # noqa: E402


def test_signal_is_the_conjunction_and_one_sided():
    spy = np.linspace(100, 200, 260)                         # rising: SMA50 > SMA200
    on, det = io.signal_from(np.array([22.0]), np.array([20.0]), spy)
    assert on is True and det["golden_cross"] and det["vix_ratio"] == 1.1
    on, _ = io.signal_from(np.array([18.0]), np.array([20.0]), spy)       # contango
    assert on is False
    on, _ = io.signal_from(np.array([22.0]), np.array([20.0]), spy[::-1])  # falling tape
    assert on is False
    assert io.signal_from(np.array([22.0]), np.array([20.0]), spy[:100])[0] is None


def test_exposure_is_base_plus_boost():
    assert io.target_exposure(False) == io.BASE_X
    assert io.target_exposure(True) == io.BASE_X + io.BOOST_X


def test_ledger_applies_yesterdays_exposure_and_charges_borrow(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "DB", str(tmp_path / "io.db"))
    idx = pd.bdate_range("2025-01-01", periods=203)
    spy = pd.Series(np.linspace(100, 160, 203), index=idx)          # golden cross throughout
    vix = pd.Series([25.0] * 203, index=idx); vix3m = pd.Series([20.0] * 203, index=idx)  # backwardated
    px = pd.DataFrame({"^VIX": vix, "^VIX3M": vix3m, "SPY": spy})
    # the first run books ONLY the last session: the record starts the day the module ran
    io.book(px.iloc[:-1], now=pd.Timestamp("2025-12-01"))
    d0 = io.ledger()["days"][0]
    assert io.ledger()["summary"]["sessions"] == 1
    assert d0["exposure"] == 2.0 and d0["day_ret"] == d0["spy_ret"] * io.BASE_X   # no prior decision
    # the next session applies yesterday's 2x and charges borrow on the levered share
    io.book(px, now=pd.Timestamp("2025-12-02"))
    d1 = io.ledger()["days"][1]
    expected = 2.0 * d1["spy_ret"] - 1.0 * io.BORROW_RATE / 252
    assert abs(d1["day_ret"] - expected) < 1e-12
    # idempotent
    io.book(px, now=pd.Timestamp("2025-12-03"))
    assert io.ledger()["summary"]["sessions"] == 2


def test_snapshot_schema_registered():
    from idt import snapshots
    name, spec = snapshots.schema_for(io.OUT)
    assert name == "index_overlay" and "exposure" in spec["required_when_ok"]
