"""The post-earnings drift voter: sign of the move across the print, abstaining when stale."""
import os
import sys
from datetime import date, timedelta

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_live_system"))
import pead  # noqa: E402


def _px(n=40, jump_at=None, jump=0.0):
    days = pd.bdate_range(end=date(2026, 9, 18), periods=n)
    closes = [100.0] * n
    if jump_at is not None:
        for i in range(jump_at, n):
            closes[i] = 100.0 * (1 + jump)
    return pd.DataFrame({"close": closes}, index=days)


def test_after_close_print_votes_the_sign_of_the_next_session():
    px = _px(jump_at=35, jump=0.06)
    rdate = px.index[34].date()                    # reported after this close
    v = pead.score(px, (rdate, "postmarket"))
    assert v["score"] > 0.8 and v["move_pct"] == 6.0
    v = pead.score(_px(jump_at=35, jump=-0.06), (rdate, "postmarket"))
    assert v["score"] < -0.8


def test_premarket_print_reads_prior_close_to_report_close():
    px = _px(jump_at=35, jump=0.03)
    rdate = px.index[35].date()                    # reported before this open
    v = pead.score(px, (rdate, "premarket"))
    assert v["move_pct"] == 3.0 and 0.4 < v["score"] < 0.8


def test_old_print_abstains_with_exactly_zero():
    px = _px(n=60, jump_at=20, jump=0.10)
    rdate = px.index[19].date()
    v = pead.score(px, (rdate, "postmarket"))
    assert v["score"] == 0.0 and "outside" in v["basis"]


def test_no_report_abstains():
    assert pead.score(_px(), None)["score"] == 0.0


def test_registry_carries_the_measured_weight():
    import signal_weights as sw
    w, tier, sign = sw.weight("pead")
    assert 0 < w <= 0.10 and sign == +1 and tier == "measured-weak"


def test_vote_is_bounded():
    px = _px(jump_at=35, jump=0.50)
    assert pead.score(px, (px.index[34].date(), "postmarket"))["score"] <= 1.0
    _ = timedelta  # keep the import honest for the helper
