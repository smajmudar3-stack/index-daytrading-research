"""Which option structure the gamma regime argues for, with real strikes.

The range read is the one part of the 0DTE work that survived. Measured on 1,919
sessions of real SPXW quotes, realised range came in at 0.843x implied on
high-gamma days and 1.139x on low-gamma days, t = -13.2. That is a genuine,
model-free statement about how far price travels.

WHAT IT IS NOT. It does not make any of these structures profitable. Every credit
structure this repo tested measured negative after real fills, |t| > 9 across
147,350 SPY trades, and Vilkov reproduces it independently: an unconditional 0DTE
iron condor is gross Sharpe 0.77 and NET -0.20. The specific condor this system
once shipped at "+3.7% per trade, VALIDATED & ROBUST" came from Black-Scholes
with a linear skew approximation; on real bid/ask it is about break-even, and the
11:00 entry the engine actually used measured -1.70%.

So this panel answers a narrower question, and only that one:

    "If I have already decided to express a range view, which structure fits
     today's regime, and at which strikes?"

It never says to put the trade on. Only today.answer() may state an action, and
the gates decide that. Every structure here carries the measured number next to
it so the size of the claim is visible at the moment of reading it.

Strikes are taken from the live dealer-gamma map -- the call and put walls are
where dealer hedging actually concentrates, which is what makes them the
structurally correct short strikes rather than a round number.
"""
from idt import snapshots

from . import EMPTY, OK, UNAVAILABLE, panel, safe

# Gamma quintile -> range expectation. pd.qcut labels ASCENDING, so Q1 is the
# LOWEST gex_z (most NEGATIVE dealer gamma, moves amplify) and Q5 the HIGHEST
# (most positive, price pins). This was inverted in the first version of this
# file and would have recommended condors in exactly the regime that loses.
#
# Q4 is deliberately no-signal: measured -1.83%/trade, a hole in the gradient.
# High gamma is not enough; it takes DEEP positive gamma.
RANGE_READ = {
    1: ("EXPANDS HARD", "move"),
    2: ("EXPANDS", "move"),
    3: ("NO SIGNAL", None),
    4: ("COMPRESSES (measured hole)", None),
    5: ("COMPRESSES HARD", "range"),
}

# Measured expectancy for each structure, so no row can be read as a green light.
# Measured directly on 1,919 sessions of real SPXW bid/ask, 17,230 trades, held
# to the 16:00 cash settle. Credit structures on capital at risk, debit on premium
# paid. See 05_studies/scripts/gex_structures_test.py.
EVIDENCE = {
    "iron condor": "MEASURED −0.25%/trade on 4,310 real-quote trades, t = −0.47. "
                   "Win rate 74.8% — high win rate, negative expectancy.",
    "iron butterfly": "MEASURED −0.35%/trade on 4,310 trades, t = −0.56, "
                      "57.0% win rate.",
    "long straddle": "MEASURED −5.69%/trade on 4,305 trades, t = −4.75. "
                     "Significantly negative, not merely unprofitable.",
    "long strangle": "MEASURED −11.54%/trade, median −100%. Most expire worthless.",
}

# The gamma conditioning does NOT work in the direction the range read predicts.
# Condor mean by quintile: Q1 −1.31%, Q2 +0.29%, Q3 +0.04%, Q4 −1.83%, Q5 +1.52%.
# Q1 is the most positive gamma — where compression should make a condor work best
# — and it is the WORST cell. One cell of 100 cleared the |t| = 3.03 noise
# threshold (condor, 12:00 entry, Q5, t = +3.15), which is exactly what 100 tests
# produce by chance, and it sits in the quintile opposite to the theory. It is not
# treated as a finding.
GAMMA_CONDITIONING = ("Tested across 5 quintiles x 5 entry times: the range read "
                      "does not convert into a profitable structure, and the best "
                      "condor cell is in the wrong quintile.")

# WHY THIS PANEL USES ONE NUMBER AND NOT THE WHOLE GAMMA PICTURE.
# The obvious objection is that a single quintile throws away net GEX level, flip
# distance, wall geometry, gamma concentration and the next significant strike in
# each direction. All seven were measured against realised range / implied move on
# 1,384 sessions, split 60/40 (05_studies/scripts/gamma_features_test.py):
#
#   feature          IC train   IC test
#   net_gamma          -0.099    -0.014
#   flip_dist          -0.022    -0.001
#   wall_width         +0.103    +0.008
#   wall_pos           -0.055    -0.013
#   concentration      -0.091    -0.075   <- best, t = -1.76, still not significant
#   next_up            +0.039    -0.003
#   next_dn            +0.107    -0.012   <- sign flips
#
# Every one collapses out of sample, and next_dn reverses. The quintile itself is
# no better: IC -0.105 in train, -0.020 in test, with realised/implied running
# 1.493 at the most negative gamma down to 1.387 at the most positive -- the right
# direction, a 7% spread, and no out-of-sample significance.
#
# So the panel keeps the quintile not because it is good but because nothing
# richer survives the split, and adding six dead inputs to one weak one would
# only make the output look more authoritative than the evidence is.


def _read(name):
    payload, status = snapshots.read(name)
    if status in ("absent", "unreadable", "wrong_version", "incomplete"):
        return None
    return payload


def _round_to(x, step):
    return round(x / step) * step


def _strikes(spot, call_wall, put_wall, step):
    """Short strikes at the walls, wings one step beyond. Falls back to a
    symmetric construction when a wall is missing, and says which it used."""
    if call_wall and put_wall and put_wall < spot < call_wall:
        sc, sp = float(call_wall), float(put_wall)
        basis = "dealer walls"
    else:
        w = _round_to(spot * 0.004, step) or step
        sc, sp = _round_to(spot + w, step), _round_to(spot - w, step)
        basis = "±0.4% of spot (a wall was missing)"
    wing = max(step * 2, _round_to((sc - sp) * 0.5, step))
    return sc, sp, wing, basis


@safe
def gamma_structures():
    p = _read("periscope_SPX.json")
    g = _read("gex_snapshot.json")
    if not p or not g:
        return panel("gamma_structures", "Structure for this regime",
                     state=UNAVAILABLE,
                     note="needs both periscope_SPX.json and gex_snapshot.json",
                     fix="idt refresh")

    spot = p.get("spot")
    if not spot:
        return panel("gamma_structures", "Structure for this regime",
                     state=UNAVAILABLE, note="no spot in the periscope",
                     fix="idt refresh")

    try:
        q = max(1, min(5, int(g.get("quintile"))))
    except (TypeError, ValueError):
        q = 3
    label, want = RANGE_READ[q]
    step = 5.0 if spot > 3000 else 1.0
    sc, sp, wing, basis = _strikes(spot, p.get("call_wall"), p.get("put_wall"), step)
    atm = _round_to(spot, step)

    if want is None:
        return panel("gamma_structures", "Structure for this regime", state=EMPTY,
                     severity="info",
                     body={"quintile": q, "label": label, "spot": spot,
                           "flip": p.get("gamma_flip"), "rows": [], "basis": basis},
                     note="Gamma is mid-quintile and price is near the flip, so the "
                          "range read has no signal today. Neither structure family "
                          "is argued for.",
                     source="realised/implied 0.843× high-γ vs 1.139× low-γ, t = −13.2")

    if want == "range":
        rows = [
            {"name": "iron condor", "fits": True,
             "legs": f"sell {sp:g}P / buy {sp-wing:g}P · sell {sc:g}C / buy {sc+wing:g}C",
             "why": "Short strikes sit at the walls, where dealer hedging resists. "
                    "Compression is what the regime argues for.",
             "risk": f"max loss {wing:g} points minus credit, per side",
             "ev": EVIDENCE["iron condor"]},
            {"name": "iron butterfly", "fits": True,
             "legs": f"sell {atm:g}P + sell {atm:g}C · buy {atm-wing:g}P / buy {atm+wing:g}C",
             "why": "Tighter than the condor and pays more if price pins the flip. "
                    "Also loses faster if it does not.",
             "risk": f"max loss {wing:g} points minus credit",
             "ev": EVIDENCE["iron butterfly"]},
            {"name": "long straddle", "fits": False,
             "legs": f"buy {atm:g}P + buy {atm:g}C",
             "why": "Argued AGAINST today. This needs range expansion and the "
                    "regime says compression.",
             "risk": "max loss the premium paid",
             "ev": EVIDENCE["long straddle"]},
        ]
    else:
        rows = [
            {"name": "long straddle", "fits": True,
             "legs": f"buy {atm:g}P + buy {atm:g}C",
             "why": "Dealers are short gamma, so their hedging feeds the move "
                    "rather than damping it. Expansion is what the regime argues for.",
             "risk": "max loss the premium paid — bounded, no assignment path",
             "ev": EVIDENCE["long straddle"]},
            {"name": "long strangle", "fits": True,
             "legs": f"buy {sp:g}P + buy {sc:g}C",
             "why": "Cheaper than the straddle and needs a bigger move. The walls "
                    "are the natural strikes because that is where hedging thins out.",
             "risk": "max loss the premium paid",
             "ev": EVIDENCE["long strangle"]},
            {"name": "iron condor", "fits": False,
             "legs": f"sell {sp:g}P / buy {sp-wing:g}P · sell {sc:g}C / buy {sc+wing:g}C",
             "why": "Argued AGAINST today. Selling range into an expanding regime is "
                    "the wrong side of the one thing that measured.",
             "risk": f"max loss {wing:g} points minus credit, per side",
             "ev": EVIDENCE["iron condor"]},
        ]

    return panel("gamma_structures", "Structure for this regime", state=OK,
                 severity="watch" if q >= 4 else "info",
                 body={"quintile": q, "label": label, "spot": spot,
                       "flip": p.get("gamma_flip"), "call_wall": p.get("call_wall"),
                       "put_wall": p.get("put_wall"), "basis": basis, "rows": rows},
                 note=f"Gamma quintile {q} of 5 — range {label}. Strikes from the "
                      f"live dealer map. This is which structure FITS the regime, "
                      f"not a recommendation to trade it.",
                 source="range read: realised/implied 0.843× high-γ vs 1.139× "
                        "low-γ, t = −13.2 · structures measured on 17,230 real-quote "
                        "trades, all negative · strikes from periscope_SPX.json")
