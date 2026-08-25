"""Markets — the read-only context. No panel here renders an action verb.

These are the levels and readings an operator looks at while deciding. The decision
itself lives in the Today view, and only there. That separation is the fix for the
page shouting several conflicting headlines at once, which master_panel()'s own
docstring recorded as the original problem.
"""
from .today import _age_min, _load, _snapshot
from . import OK, STALE, describe, empty, panel, safe, unavailable


def _periscope(sym):
    name = f"periscope_{sym}.json"
    key = f"peri_{sym.lower()}"
    title = f"{sym} gamma levels"
    p, bad = _snapshot(name)
    if bad and bad["kind"] == "empty":
        return empty(key, title, bad["why"], fix=bad["fix"])
    if bad and bad["kind"] == "unavailable":
        return unavailable(key, title, bad["why"], fix=bad["fix"])
    if p is not None and not p.get("ok"):
        return unavailable(key, title,
                           f"The {sym} periscope failed: {p.get('error', 'no reason recorded')}",
                           fix="idt audit")

    age = _age_min(name)
    stale = bool(bad and bad["kind"] == "stale")
    rows = [
        {"k": "spot", "v": f"{p.get('spot', '—')}"},
        {"k": "gamma flip", "v": f"{p.get('gamma_flip') or 'none within ±10%'}"},
        {"k": "call wall", "v": f"{p.get('call_wall', '—')}"},
        {"k": "put wall", "v": f"{p.get('put_wall', '—')}"},
        {"k": "net GEX", "v": f"{p.get('net_gex_musd', '—')} $M / 1%"},
    ]
    pos = p.get("position") or {}
    if pos.get("note"):
        rows.append({"k": "position", "v": pos["note"],
                     "severity": "watch" if pos.get("at_wall") else None})

    # The ladder: put wall, gamma flip and spot drawn between the walls on one
    # axis. The four numbers above ARE this picture; drawing it is the panel.
    ladder = None
    spot, cw, pw = p.get("spot"), p.get("call_wall"), p.get("put_wall")
    flip = p.get("gamma_flip")
    if spot and cw and pw and cw > pw:
        lo = min(pw, spot, *( [flip] if flip else [] ))
        hi = max(cw, spot, *( [flip] if flip else [] ))
        span = (hi - lo) or 1

        def pct(v):
            # 8% margins so a level on the edge keeps its label on the page.
            return round(8 + (v - lo) / span * 84, 2)

        levels = [
            {"kind": "wall", "label": "put wall", "px": f"{pw:g}", "pct": pct(pw)},
            {"kind": "wall", "label": "call wall", "px": f"{cw:g}", "pct": pct(cw)},
            {"kind": "spot", "label": "spot", "px": f"{spot:g}", "pct": pct(spot)},
        ]
        if flip:
            levels.insert(2, {"kind": "flip", "label": "gamma flip", "px": f"{flip:g}",
                              "pct": pct(flip)})
        ladder = {"levels": levels,
                  "left": "downside support", "right": "upside magnet"}

    stats = []
    if p.get("net_gex_musd") is not None:
        stats.append({"n": f"{p['net_gex_musd']:g}", "l": "net GEX $M / 1%"})
    posd = p.get("position") or {}
    if posd.get("pct_to_call_wall") is not None:
        stats.append({"n": f"{posd['pct_to_call_wall']}%", "l": "to call wall"})
    if posd.get("pct_to_put_wall") is not None:
        stats.append({"n": f"{posd['pct_to_put_wall']}%", "l": "above put wall"})

    return panel(key, title,
                 state=STALE if stale else OK,
                 severity="watch" if stale else None,
                 age_min=age,
                 body={"rows": rows, "text": p.get("signal_why", ""),
                       "ladder": ladder, "stats": stats},
                 note=p.get("signal", ""),
                 source=p.get("spot_source") or "yfinance chain")


@safe
@describe("peri_spx", "SPX gamma levels")
def periscope_spx():
    return _periscope("SPX")


@safe
@describe("peri_ndx", "NDX gamma levels")
def periscope_ndx():
    return _periscope("NDX")


@safe
@describe("swing", "Swing signals")
def swing():
    """Days-to-weeks direction. Kept because two of its three inputs are measured.

    The swing OPTION overlays are all refuted (every one was beaten by owning SPY on
    return, Sharpe and drawdown), and sector rotation picks names that do worse than
    random. What survived is the underlying signal set: short interest with a negative
    sign, and VIX backwardation. So this panel reports signals, not trades.
    """
    sw = _load("swing_snapshot.json")
    if sw is None:
        return empty("swing", "Swing signals", "No swing snapshot yet.",
                     fix="idt refresh   (writes 04_live_system/data/swing_snapshot.json)")

    sigs = sw.get("signals") or []
    if not sigs:
        return empty("swing", "Swing signals",
                     "The scan ran and found no names clearing the threshold.")

    age = _age_min("swing_snapshot.json")
    rows = []
    for s in sigs[:12]:
        conv = s.get("conviction")
        rows.append({"k": s.get("ticker", "?"),
                     "v": f"{s.get('direction', '')} · conviction {conv if conv is not None else '—'}",
                     "dir_word": s.get("direction", ""),
                     "conv": int(conv) if conv is not None else 0})
    return panel("swing", "Swing signals",
                 state=STALE if (age or 0) > 1500 else OK, age_min=age,
                 body={"rows": rows},
                 note=("Signals, not trades. Every option overlay tested on these was beaten by "
                       "simply owning the index, so the honest expression is the underlying."),
                 source="swing_signals.run()")


@safe
@describe("gaps", "Gap and go candidates")
def gaps():
    g = _load("gap_snapshot.json")
    if g is None:
        return empty("gaps", "Gap and go candidates", "No gap scan yet.",
                     fix="idt refresh   (writes 04_live_system/data/gap_snapshot.json)")
    cands = g.get("candidates") or []
    if not cands:
        return empty("gaps", "Gap and go candidates",
                     "No setups right now. Most days have none; forcing one gives the edge back.")
    age = _age_min("gap_snapshot.json")
    rows = [{"k": c.get("ticker", "?"), "v": c.get("setup", "")} for c in cands[:10]]
    return panel("gaps", "Gap and go candidates",
                 state=STALE if (age or 0) > 30 else OK, age_min=age,
                 body={"rows": rows},
                 note=("This edge is stress-tested by one script and has no entry in "
                       "docs/VERDICT_LOG.md, so treat it as unverified rather than validated."),
                 source="gap_scanner.run()")


@safe
@describe("blackswan", "Far-OTM convexity")
def blackswan():
    """Partial credit only, and the panel says which part.

    Far-OTM buying measured −45.6% overall. Two things inside it were real: filtering
    to contracts with a bid-ask spread of 20% or less took it to +5.6%, and returns
    improve monotonically toward the money, reaching +26.1% in the 16 to 30 delta band.
    So the useful finding is about EXECUTION and DELTA, not about buying lottery tickets.
    """
    bs = _load("blackswan_scan.json")
    # mag scales |return| onto the half-track, 90% = full. The picture IS the
    # finding: the tails lose huge, the 16-30 delta band is the only real payer.
    findings = [
        {"k": "far tail", "v": "−90%", "dir": "-", "mag": 50, "severity": "stop"},
        {"k": "unfiltered far-OTM", "v": "−45.6%", "dir": "-", "mag": 25, "severity": "stop"},
        {"k": "spread ≤ 20% only", "v": "+5.6%", "dir": "+", "mag": 3},
        {"k": "16–30 delta band", "v": "+26.1%", "dir": "+", "mag": 15},
    ]
    rows = []
    note = ("Buying the cheapest contract is the worst version of this trade. The spread "
            "filter mattered more than any signal tested for choosing which contract to buy.")
    if bs and bs.get("candidates"):
        for c in bs["candidates"][:6]:
            rows.append({"k": c.get("ticker", "?"), "v": c.get("why", "")})
    else:
        note += " No live scan has been written, so only the standing findings are shown."
    return panel("blackswan", "Far-OTM convexity", state=OK,
                 body={"rows": rows, "findings": findings}, note=note,
                 source="02_findings/FINDINGS_BLACKSWAN.md, blackswan_scan.json")
