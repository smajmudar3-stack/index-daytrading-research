"""The three signals that survived testing, and what to do when one fires.

Everything else in this repo is a null. These three are the exceptions, each
measured out-of-sample and each with a stated limit:

  short interest       IC -0.107 at 63d, n=13,219, monotone across every bucket.
                       The sign is NEGATIVE -- high short float predicts LOWER
                       returns. The squeeze thesis is backwards.
  VIX backwardation    t +3.9 / +2.8 / +2.1 on train / validate / test. The only
                       signal that held across all three splits.
  low dealer gamma     8 of 8 directional structures paid more in low gamma. Not
                       a direction call -- a statement about whether directional
                       bets get paid at all.

This panel exists because those three were previously buried in a paragraph
among a dozen refuted ones. A signal you have to go looking for is a signal you
will miss.

WHAT THIS PANEL WILL NOT DO. gex_snapshot.json carries `stance: "buy_premium"`
when gamma is low. That rule is REFUTED -- buying premium below the flip measured
-7.2% per trade on straddles and -19.1% on strangles. Low gamma says directional
structures are RELATIVELY better, not that buying premium is profitable. The
distinction is the difference between a real finding and a lost account, so the
raw `stance` field is deliberately never read here.
"""
from idt import snapshots

from . import EMPTY, OK, UNAVAILABLE, panel, safe

# Gamma quintile -> what it means for price, in the operator's language.
# 1 = deepest positive gamma (dealers dampen), 5 = deepest negative (dealers amplify).
GAMMA_MEANING = {
    1: ("AMPLIFIED", "Dealers are deeply short gamma. They buy strength and sell "
                     "weakness, which feeds the move. Trends run and gaps run "
                     "furthest. Measured: selling range here loses 1.31%/trade."),
    2: ("LOOSE", "Dealers are short gamma. Hedging adds to moves rather than "
                 "damping them, so a push tends to keep going."),
    3: ("NEUTRAL", "Dealer positioning is not pushing price either way. Whatever "
                   "happens is the market's doing, not the hedging flow's."),
    4: ("STICKY", "Dealer hedging damps moves, but not enough. Measured: this is "
                  "a HOLE -- selling range here still lost 1.83%/trade."),
    5: ("PINNED", "Dealers are deeply long gamma. They sell rallies and buy dips, "
                  "pinning price to the big strikes. This is the one regime where "
                  "selling range measured POSITIVE: +1.52%/trade, 87.2% win."),
}

SHORT_FLOAT_FIRE = 20.0     # percent of float; below this the signal is noise
MIN_CONVICTION = 55


def _load(name):
    """Read through the schema validator, never straight off disk.

    An earlier draft of this panel opened the file directly and so happily
    rendered a snapshot the rest of the page was refusing -- a gex v1 file whose
    `stance` field still said "buy_premium", the refuted order. Bypassing the
    guard is how a retired instruction gets back onto the screen, so the panel
    now fails exactly where every other panel fails.
    """
    payload, status = snapshots.read(name)
    # status is a STRING verdict, not a dict. "stale" is still usable and says so
    # elsewhere on the page; the other four are refusals.
    if status in ("absent", "unreadable", "wrong_version", "incomplete"):
        return None
    return payload


def _vix_term():
    """Spot VIX against VIX3M. Backwardation (spot above 3-month) is the signal."""
    c = _load("edge_state.json")
    if c and c.get("vix_ratio"):
        return c.get("vix"), c.get("vix_ratio")
    return None, None


def _gamma():
    """Quintile 1-5 and the plain-English read. Never returns the refuted stance."""
    g = _load("gex_snapshot.json")
    if not g:
        return None
    q = g.get("quintile")
    try:
        q = int(q)
    except (TypeError, ValueError):
        return None
    q = max(1, min(5, q))
    label, meaning = GAMMA_MEANING[q]
    return {
        "score": q, "label": label, "meaning": meaning,
        "gex_bn": g.get("gex_bn"), "gex_z": g.get("gex_z"),
        "neg": bool(g.get("neg_gamma")),
        "as_of": g.get("as_of"), "applies_to": g.get("applies_to"),
        # Q1 is the LOWEST gex_z, i.e. the most NEGATIVE dealer gamma.
        # qcut labels ascending, so low quintile = low gamma. Getting this
        # backwards inverts every recommendation built on it.
        "fires": q <= 2,
    }


def _short_interest():
    """Names in the live swing scan whose short float clears the threshold."""
    s = _load("swing_snapshot.json")
    if not s:
        return []
    out = []
    for sig in (s.get("signals") or []):
        sf = sig.get("short_float_pct")
        try:
            sf = float(sf)
        except (TypeError, ValueError):
            continue
        # Above 60 is a vendor error, not a signal -- BYND has printed 758%.
        if not (SHORT_FLOAT_FIRE <= sf <= 60.0):
            continue
        out.append({"ticker": sig.get("ticker"), "short_float": round(sf, 1),
                    "direction": sig.get("direction"),
                    "conviction": sig.get("conviction"),
                    "last": sig.get("last")})
    out.sort(key=lambda x: -x["short_float"])
    return out[:8]


@safe
def patterns():
    """The loud one. Fires only on the three measured signals, never on anything else."""
    gam = _gamma()
    vix, ratio = _vix_term()
    shorts = _short_interest()

    if gam is None and vix is None and not shorts:
        return panel("patterns", "Validated signals", state=UNAVAILABLE,
                     note="no gamma, VIX or swing snapshot could be read",
                     fix="idt refresh")

    fires = []

    if gam and gam["fires"]:
        fires.append({
            "name": "LOW DEALER GAMMA",
            "reading": f"{gam['label']} — quintile {gam['score']} of 5",
            "means": gam["meaning"],
            "capitalise":
                "Directional structures pay more here than in high gamma — 8 of 8 "
                "tested did. Favour a debit call or put spread over a range trade, "
                "and give the position room rather than a tight stop, because the "
                "hedging flow that normally caps a move is now feeding it.",
            "not": "This does NOT mean buy premium outright. That specific rule was "
                   "measured at −7.2% per trade on straddles and −19.1% on strangles.",
            "evidence": "8 of 8 directional structures paid more in low gamma",
        })

    if ratio and ratio > 1.0:
        fires.append({
            "name": "VIX BACKWARDATION",
            "reading": f"VIX {vix:.1f} above VIX3M — ratio {ratio:.3f}",
            "means":
                "Near-term fear is priced above three-month fear. The market is "
                "paying up for protection RIGHT NOW rather than later, which "
                "historically marks stress that resolves upward.",
            "capitalise":
                "This is the only signal that held across all three time splits. "
                "It is a multi-week bullish tilt, not a day trade — express it in "
                "the swing book with a 3–8 week horizon, and size it as one "
                "position among several rather than a single concentrated bet.",
            "not": "It says nothing about today's direction. Do not trade it 0DTE.",
            "evidence": "t = +3.9 / +2.8 / +2.1 across train / validate / test",
        })

    if shorts:
        top = shorts[0]
        fires.append({
            "name": "HIGH SHORT INTEREST",
            "reading": f"{len(shorts)} name(s) above {SHORT_FLOAT_FIRE:.0f}% of float — "
                       f"top {top['ticker']} at {top['short_float']}%",
            "means":
                "Heavy shorting predicts LOWER forward returns, not a squeeze. "
                "Short sellers are right on average, and the effect grows out to "
                "about 63 days. This is the strongest signal in the whole repo — "
                "and its sign is the opposite of the popular story.",
            "capitalise":
                "Lean BEARISH on these names over 4–13 weeks. The cleanest "
                "expression is short stock or a deep-ITM put; a far-OTM put is the "
                "wrong vehicle, because the measured edge is a small mean shift "
                "and OTM options need a large move to pay. Hold as a basket — the "
                "edge is cross-sectional, so any single name is close to a coin flip.",
            "not": "Do not read this as squeeze fuel. That is the sign error the "
                   "measurement corrects.",
            "evidence": "IC −0.107 at 63d, n = 13,219, monotone across every bucket",
            "names": shorts,
        })

    body = {"fires": fires, "gamma": gam,
            "quiet": [] if fires else _quiet(gam, ratio, shorts)}

    if not fires:
        return panel("patterns", "Validated signals", state=EMPTY,
                     body=body, severity="info",
                     note="None of the three measured signals is firing. That is the "
                          "normal state — they fire on a minority of days.",
                     source="short interest IC −0.107 · VIX t +3.9/+2.8/+2.1 · gamma 8-of-8")

    return panel("patterns", "PATTERN IDENTIFIED", state=OK, body=body,
                 severity="watch" if len(fires) == 1 else "stop",
                 note=f"{len(fires)} of 3 validated signals firing. These are the only "
                      f"three that survived out-of-sample testing.",
                 source="short interest IC −0.107 · VIX t +3.9/+2.8/+2.1 · gamma 8-of-8")


def _quiet(gam, ratio, shorts):
    """Why each signal is silent, so 'nothing firing' never reads as 'nothing checked'."""
    rows = []
    if gam:
        rows.append(("Low dealer gamma",
                     f"quintile {gam['score']} of 5 ({gam['label']}) — fires at 1 or 2"))
    else:
        rows.append(("Low dealer gamma", "no gamma snapshot"))
    if ratio:
        rows.append(("VIX backwardation",
                     f"ratio {ratio:.3f} — fires above 1.000 (contango now)"))
    else:
        rows.append(("VIX backwardation", "no VIX term structure"))
    rows.append(("High short interest",
                 f"no scanned name above {SHORT_FLOAT_FIRE:.0f}% of float"
                 if not shorts else f"{len(shorts)} names"))
    return rows


@safe
def gamma_meter():
    """Gamma out of 5 as its own panel, so it is readable at a glance every day."""
    g = _gamma()
    if not g:
        return panel("gamma_meter", "Dealer gamma today", state=UNAVAILABLE,
                     note="gex_snapshot.json could not be read", fix="idt refresh")
    return panel("gamma_meter", "Dealer gamma today", state=OK,
                 body={
                     "score": g["score"], "label": g["label"], "meaning": g["meaning"],
                     "gex_bn": g["gex_bn"], "gex_z": g["gex_z"],
                     "applies_to": g.get("applies_to"),
                     "scale": [(i, GAMMA_MEANING[i][0]) for i in range(1, 6)],
                 },
                 severity="watch" if g["score"] <= 2 or g["score"] == 5 else "info",
                 note="1 = dealers AMPLIFY moves (lowest gamma) · 5 = dealers PIN price (highest)",
                 source=f"gex_snapshot.json, {g.get('as_of', 'unknown time')}")
