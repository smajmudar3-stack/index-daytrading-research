"""Directional call — states what is known, and WHY, including when that is "nothing".

A directional read was asked for, so this panel gives one. It gives the true one.

WHY THE HEADLINE IS A REFUSAL. Intraday direction was tested to exhaustion: 2,384
named-rule tests, 1,884 daily-horizon tests, 4,408 crafted 5-minute patterns,
328,854 spread cells across 31 indicators and six structures, 104 order-flow and
microstructure predictors, and 12 LSTM/GRU configurations walk-forward over 7.7
years. In every one of those sweeps the number of survivors came in at or BELOW
what chance alone produces.

The best result anywhere was an LSTM at 51.85% accuracy. Its 95% confidence
interval is [49.85%, 53.84%] -- it contains 50% -- and the year-by-year breakdown
shows 2020 contributed 144% of the total, meaning the other five years sum to
negative. Excluding 2020 the signal is -0.54bp/trade GROSS, before costs.

Putting a green "LONG" on the page from that would be the single most expensive
thing this dashboard could do, because it would look exactly like information.

WHAT THIS PANEL DOES GIVE YOU is the regime read, which IS measured: dealer gamma
determines whether moves get amplified or suppressed. That is not a direction, but
it changes which structure is appropriate, and it is the only conditioning in this
repo that ever produced a positive number.

Every figure below is pinned to a measured result so the panel and the research
cannot drift apart.
"""
from . import OK, panel, safe
from .today import _age_min, _load

# ---- measured constants. If the research changes, change them HERE, once.
ACC = 51.85           # best out-of-sample intraday accuracy found, LSTM32
CI_LO, CI_HI = 49.85, 53.84
P_VALUE = 0.279
YEARS_POS = "4 of 6"
EX_2020_BP = -0.54    # gross bp/trade with 2020 removed
CAPTURED_BP = 2.02    # bp of spot the signal captures
ODTE_HURDLE_BP = 62   # bp a 30-minute 0DTE needs to break even
CREDIT_PNL = -1.27    # mean %/trade collecting theta, 230,884 real-fill trades
DEBIT_PNL = -11.12    # mean %/trade paying theta

REGIME = {
    "amplified": {
        "label": "AMPLIFIED",
        "what": "Dealers are SHORT gamma — they hedge WITH the move.",
        "means": ("A push gets extended rather than absorbed, so moves run "
                  "further than they look like they should. Selling range in "
                  "this regime measured −1.31%/trade."),
        "do": ("Do not sell range here. If you hold a directional view from "
               "outside this dashboard, this is the regime where it can "
               "actually travel — but this model has no view to give you."),
        "sev": "watch",
    },
    "suppressed": {
        "label": "SUPPRESSED",
        "what": "Dealers are LONG gamma — they hedge AGAINST the move.",
        "means": ("They sell strength and buy weakness, so range compresses and "
                  "price gets pinned. This is the only regime where selling "
                  "range measured positive: +1.52%/trade at 87.2% win."),
        "do": ("The measured tilt favours SHORT premium with defined risk — a "
               "credit spread or condor — not a directional bet. Treat it as "
               "suggestive only: that +1.52% weakens to t = +1.67 once same-day "
               "trades are clustered properly, which is below significance."),
        "sev": "info",
    },
    "neutral": {
        "label": "NEUTRAL",
        "what": "Spot is near the gamma flip, so dealer hedging pushes neither way.",
        "means": ("No regime tilt in either direction. The flip is the level "
                  "that matters: above it moves get damped, below it amplified."),
        "do": "No directional signal and no regime tilt. Stand aside.",
        "sev": None,
    },
}


def _regime_key(g):
    """Quintile first, flip-vs-spot as the fallback. None if neither is readable."""
    if not g:
        return None
    q = g.get("quintile")
    try:
        q = int(q)
    except (TypeError, ValueError):
        q = None
    if q is not None:
        # Q1 is the LOWEST gex_z = most NEGATIVE dealer gamma. qcut labels
        # ascending. Reading this backwards inverts every line on the panel.
        return "amplified" if q <= 2 else "suppressed" if q >= 4 else "neutral"
    flip, spot = g.get("flip"), g.get("spot")
    try:
        flip, spot = float(flip), float(spot)
    except (TypeError, ValueError):
        return None
    if not flip:
        return None
    if abs(spot / flip - 1) < 0.001:
        return "neutral"
    return "suppressed" if spot > flip else "amplified"


@safe
def call():
    """The headline directional call. Currently, and honestly,: none."""
    rows = [
        {"k": "Directional signal", "v": "NONE", "severity": "stop",
         "sub": (f"The best intraday accuracy found in any test is {ACC}%. Its "
                 f"95% confidence interval is [{CI_LO}%, {CI_HI}%] — it contains "
                 f"50%, so the data cannot rule out that it is worthless "
                 f"(p = {P_VALUE}).")},
        {"k": "Why not just trade the 51.85%?", "v": "it was one year",
         "sub": (f"Positive in {YEARS_POS} walk-forward years, but 2020 alone "
                 f"contributed 144% of the total. Remove 2020 and the signal is "
                 f"{EX_2020_BP:+.2f} bp/trade GROSS — negative before you pay a "
                 f"single spread.")},
        {"k": "And with options?", "v": f"{ODTE_HURDLE_BP/CAPTURED_BP:.0f}× too small",
         "sub": (f"The move captured is {CAPTURED_BP:.2f} bp of spot. A 30-minute "
                 f"0DTE needs about {ODTE_HURDLE_BP} bp just to break even. "
                 f"Buying premium on this loses even if the edge is real.")},
        {"k": "How hard was this looked for?", "v": "~340,000 tests",
         "sub": ("2,384 named rules · 1,884 daily-horizon tests · 4,408 crafted "
                 "5-minute patterns · 328,854 spread cells · 104 order-flow and "
                 "microstructure predictors · 12 LSTM/GRU configs over 7.7 years. "
                 "Survivor counts landed at or below the rate chance produces.")},
    ]
    return panel("direction_call", "Direction", state=OK, severity="stop",
                 note="There is no validated directional edge. This is the "
                      "finding, not a missing feature.",
                 body={"rows": rows},
                 source="05_studies/scripts/ — deep_sequence.py, "
                        "spread_combo_hunt.py, predictor_battery.py")


@safe
def regime():
    """What IS measurable: the dealer-gamma regime. Context, not a direction."""
    g = _load("gex_snapshot.json")
    if not g:
        return panel("direction_regime", "Dealer gamma regime",
                     state="unavailable", severity="stop",
                     note="gex_snapshot.json is absent or failed its schema check.",
                     fix="Run 04_live_system/scan_all.py to rebuild it.")
    key = _regime_key(g)
    if key is None:
        return panel("direction_regime", "Dealer gamma regime",
                     state="unavailable", severity="stop",
                     note="The snapshot is present but carries neither a usable "
                          "quintile nor a flip/spot pair.",
                     fix="Check the gex writer in gex_periscope.py.")
    r = REGIME[key]
    rows = [
        {"k": "Regime", "v": r["label"], "severity": r["sev"],
         "sub": r["what"]},
        {"k": "What it does to price", "v": "", "sub": r["means"]},
        {"k": "What to do with it", "v": "", "sub": r["do"]},
    ]
    for lab, k in (("Net GEX", "gex_bn"), ("Gamma flip", "flip"),
                   ("Call wall", "call_wall"), ("Put wall", "put_wall")):
        if g.get(k) is not None:
            rows.append({"k": lab, "v": g[k]})
    return panel("direction_regime", "Dealer gamma regime", state=OK,
                 severity=r["sev"], body={"rows": rows},
                 age_min=_age_min(g.get("as_of")),
                 note="This is a REGIME read, not a direction. It tells you how "
                      "moves behave, not which way they go.",
                 source="live gex_snapshot.json")


@safe
def structure_note():
    """The largest measured effect in the research: which way theta points."""
    rows = [
        {"k": "Collecting theta", "v": f"{CREDIT_PNL:+.2f}% / trade",
         "sub": "Credit spreads, across 230,884 real-fill trades on the SPXW "
                "chain (bought at the ask, sold at the bid, every leg)."},
        {"k": "Paying theta", "v": f"{DEBIT_PNL:+.2f}% / trade", "severity": "stop",
         "sub": "Debit spreads and naked longs, same trades, same fills."},
        {"k": "The catch", "v": "both are negative",
         "sub": (f"Structure orientation is worth about "
                 f"{abs(DEBIT_PNL - CREDIT_PNL):.0f} percentage points per trade "
                 f"— the largest single effect measured here. But a better "
                 f"structure only lowers the bar; it does not manufacture a "
                 f"signal to clear it.")},
    ]
    return panel("direction_structure", "Why structure matters more than direction",
                 state=OK, severity="info", body={"rows": rows},
                 note="If you trade anyway, this is the one choice the evidence "
                      "actually supports.",
                 source="05_studies/scripts/vertical_hurdle.py")
