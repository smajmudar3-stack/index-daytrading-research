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

# Gamma quintile -> range expectation. 1 = deepest positive gamma (dealers damp),
# 5 = deepest negative (dealers amplify).
RANGE_READ = {
    1: ("COMPRESSES HARD", "range"),
    2: ("COMPRESSES", "range"),
    3: ("NO SIGNAL", None),
    4: ("EXPANDS", "move"),
    5: ("EXPANDS HARD", "move"),
}

# Measured expectancy for each structure, so no row can be read as a green light.
EVIDENCE = {
    "iron condor": "unconditional 0DTE: gross Sharpe 0.77, NET −0.20 (Vilkov). "
                   "Our own 11:00 entry measured −1.70%/trade on real quotes.",
    "iron butterfly": "same family as the condor. Every credit structure tested "
                      "here was negative after real fills, |t| > 9.",
    "long straddle": "buying 0DTE premium on a signal measured −10% to −11% per "
                     "trade. Below the flip specifically: −7.2%.",
    "long strangle": "below the flip measured −19.1% per trade. The worst of the four.",
}


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
                 source="realised/implied 0.843× high-γ vs 1.139× low-γ, t = −13.2 · "
                        "strikes from periscope_SPX.json")
