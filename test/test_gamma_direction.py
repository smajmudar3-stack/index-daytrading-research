"""The quintile direction, pinned by a test.

pd.qcut labels ascending, so Q1 is the LOWEST gex_z -- the most NEGATIVE dealer
gamma, where hedging amplifies moves -- and Q5 the highest, where price pins.
Both panels shipped this inverted once, which would have recommended selling
range in exactly the regime that measured -1.31%/trade.

The measurement these assert against (05_studies/scripts/gex_structures_test.py,
17,230 real-quote trades):

    iron condor   Q1 -1.31%   Q4 -1.83%   Q5 +1.52%  (87.2% win, t +3.73)
    long strangle Q1 -12.39%             Q5 -48.31%
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_live_system"))

from panels import signals, structures


def test_q1_is_the_amplifying_regime_not_the_pinning_one():
    label, _ = signals.GAMMA_MEANING[1]
    assert label == "AMPLIFIED", f"Q1 is the lowest gamma; got {label!r}"
    label5, _ = signals.GAMMA_MEANING[5]
    assert label5 == "PINNED", f"Q5 is the highest gamma; got {label5!r}"


def test_low_gamma_signal_fires_at_low_quintiles():
    # the 8-of-8 directional finding is about LOW gamma, which is Q1-Q2
    assert signals.GAMMA_MEANING[1][0] != signals.GAMMA_MEANING[5][0]
    src = open(os.path.join(os.path.dirname(__file__), "..",
                            "04_live_system", "panels", "signals.py")).read()
    assert '"fires": q <= 2' in src, "low-gamma signal must fire on low quintiles"


def test_range_structures_only_argued_in_the_pinning_regime():
    # selling range measured POSITIVE only at Q5
    assert structures.RANGE_READ[5][1] == "range", "Q5 pins; range structures fit"
    assert structures.RANGE_READ[1][1] == "move", "Q1 amplifies; long premium fits"


def test_q4_is_treated_as_no_signal():
    # measured -1.83%/trade: a hole, not a gradient step
    assert structures.RANGE_READ[4][1] is None, "Q4 measured negative; must not fire"
