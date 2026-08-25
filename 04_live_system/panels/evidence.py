"""Evidence — how much this system actually knows.

The repo's defining property is that it knows what it does not know: modelled versus
measured P&L, priors versus measured weights, zero of sixty sessions of real-quote
evidence, an unproven condor and several refuted strategies. All of that was computed
and then buried. This view is the answer to "how much should I trust the other views".
"""
from . import OK, describe, empty, panel, safe, unavailable


@safe
@describe("evidence_meter", "How much of this is measured")
def meters():
    """The two numbers that decide how much the rest of the page is worth.

    1. measured fraction — what share of the track record came from real option premium
       rather than an estimate of underlying move times an assumed leverage factor.
    2. the credit log — the single highest-value open validation in the repo. Sixty
       sessions of real SPX 0DTE condor credits, compared against the model-free
       breakevens. Until it finishes, the 0DTE sleeve is unresolved.
    """
    ms = []

    try:
        import graduation
        s = graduation.stats()
        n = s.get("n") or 0
        pct = s.get("measured_pct")
        if pct is None and s.get("measured_fraction") is not None:
            pct = round(s["measured_fraction"] * 100)
        pct = pct or 0
        ms.append({
            "label": "Track record priced from real premium",
            "value": f"{pct}% of {n} closed trades" if n else "no closed trades yet",
            "pct": pct,
            "severity": None if pct >= 80 else "watch",
            "why": ("A modelled P&L is the underlying's move times an assumed leverage "
                    "factor. It is a guess. Only the measured share is evidence."),
        })
    except Exception as e:                          # noqa: BLE001
        ms.append({"label": "Track record priced from real premium",
                   "value": f"unavailable ({type(e).__name__})", "pct": 0,
                   "severity": "stop",
                   "why": "graduation.stats() could not be read, so trust nothing above."})

    try:
        import rules
        ev = rules.credit_evidence()
        n = ev.get("n", 0)
        need = ev.get("sessions_needed", 60)
        ms.append({
            "label": "Real-quote credit log",
            "value": f"{n} of {need} sessions",
            "pct": min(100, round(100 * n / max(need, 1))),
            "severity": "watch" if n < need else None,
            "why": ("Every backtest P&L in this repo is modelled. This log records what the "
                    "market actually pays for the exact structure, one row per session in the "
                    "entry window. It confirms or kills the 0DTE sleeve, and nothing else can."),
        })
    except Exception as e:                          # noqa: BLE001
        ms.append({"label": "Real-quote credit log", "value": f"unavailable ({type(e).__name__})",
                   "pct": 0, "severity": "stop",
                   "why": "rules.credit_evidence() could not be read."})

    return panel("evidence_meter", "How much of this is measured", state=OK,
                 body={"meters": ms},
                 note=("Read this before anything else on the page. A number with a low bar "
                       "under it is not a result, it is a placeholder."),
                 source="graduation.stats(), rules.credit_evidence()")


@safe
@describe("weights", "Signal weights — measured against prior")
def weights():
    """Every weight, tagged with whether it was measured or invented.

    signal_weights.py already made this distinction and pinned measured nulls at zero,
    which is the best idea in the codebase. It was never surfaced, so a fabricated
    prior of 0.35 looked exactly like a measured 0.30 on screen.
    """
    try:
        import signal_weights
        table = signal_weights.table()
    except Exception as e:                          # noqa: BLE001
        return unavailable("weights", "Signal weights",
                           f"signal_weights.table() failed: {type(e).__name__}: {e}")

    if not table:
        return empty("weights", "Signal weights", "The weight registry is empty.")

    tier_map = {"measured": "measured", "measured-weak": "measured",
                "unmeasured": "prior", "risk-flag": "prior", "measured-null": "null"}
    rows = []
    for r in table:
        tier = tier_map.get(r.get("tier"), "prior")
        # The key is `sign` and it is a STRING ("+" / "−"), not a number. Defaulting a
        # missing sign to positive would print short interest as a bullish input, which
        # inverts the single strongest finding in the repo (IC -0.107, and the sign being
        # negative is the whole point). An unknown sign says so instead.
        sign = r.get("sign") or "?"
        w = float(r.get("weight", 0) or 0)
        rows.append({
            "k": f"{r.get('input')} ({sign})",
            "v": f"{w:.2f}",
            "wpct": round(w / 0.35 * 100),      # 0.35 is the registry's largest weight
            "tier": tier,
            "severity": "watch" if tier == "prior" else None,
            "evidence": r.get("evidence") or "",
        })

    n_prior = sum(1 for r in rows if r["tier"] == "prior")
    n_null = sum(1 for r in rows if r["tier"] == "null")
    return panel("weights", "Signal weights — measured against prior", state=OK,
                 body={"rows": rows},
                 note=(f"{n_prior} of {len(rows)} weights are priors, not results, and {n_null} were "
                       "tested and found to carry no information. A prior is a guess someone wrote "
                       "down; uw_calibrate blends them toward measured values as live results "
                       "accumulate. The zeros are pinned so they cannot leak back in. A minus sign "
                       "means the input predicts the OPPOSITE of the intuitive story: high short "
                       "interest predicts lower forward returns, not a squeeze."),
                 source="signal_weights.table()")


@safe
@describe("verdicts", "What survived, and what did not")
def verdicts():
    """The standing verdicts, restated on the page rather than only in a document.

    These are hardcoded on purpose. They are the conclusions of the research, they do
    not change per cycle, and putting them behind a file read would mean the page could
    silently stop showing them. docs/VERDICT_LOG.md is the authority; this is the
    summary an operator sees without leaving the dashboard.
    """
    # `mag` (0..50, half-track) and `dir` draw each verdict as a diverging bar:
    # survivors extend right, the refuted extend left, length is evidence strength
    # for survivors and loss size for the refuted. The numbers stay printed beside
    # the bar; the bar is the glance, the number is the record.
    rows = [
        {"k": "Short interest (63d)", "v": "IC −0.107, sign NEGATIVE", "tier": "measured",
         "dir": "+", "mag": 34},
        {"k": "VIX backwardation", "v": "t +3.9 / +2.8 / +2.1, all splits", "tier": "measured",
         "dir": "+", "mag": 30},
        {"k": "Low dealer gamma as a filter", "v": "8 of 8 structures", "tier": "measured",
         "dir": "+", "mag": 40},
        {"k": "Dealer gamma → day's range", "v": "t −13.2 vs VIX9D", "tier": "measured",
         "dir": "+", "mag": 50},
        {"k": "0DTE condor on high gamma", "v": "≈ break-even on real quotes", "tier": "modelled",
         "severity": "watch", "dir": "+", "mag": 3},
        {"k": "Buying 0DTE premium on a signal", "v": "−10% to −11% per trade", "tier": "null",
         "severity": "stop", "dir": "-", "mag": 22},
        {"k": "Below the flip = buy premium", "v": "−7.2% to −19.1% per trade", "tier": "null",
         "severity": "stop", "dir": "-", "mag": 28},
        {"k": "Premium selling, 147,350 trades", "v": "every structure negative", "tier": "null",
         "severity": "stop", "dir": "-", "mag": 36},
        {"k": "Sector-rotation swing picks", "v": "worse than random, p = 0.87", "tier": "null",
         "severity": "stop", "dir": "-", "mag": 30},
        {"k": "Swing option overlays", "v": "all beaten by owning SPY", "tier": "null",
         "severity": "stop", "dir": "-", "mag": 26},
    ]
    return panel("verdicts", "What survived, and what did not", state=OK,
                 body={"rows": rows},
                 note=("Struck-through entries are refuted: they were tested honestly and lost "
                       "money. They are listed because knowing which parts do not work is what "
                       "this repo is actually worth."),
                 source="docs/VERDICT_LOG.md")


@safe
@describe("scorecard", "Calibration — are the calls honest")
def scorecard():
    """Whether a call stated at high conviction actually wins more often."""
    try:
        import scorecard as sc
        rep = sc.report()
    except Exception as e:                          # noqa: BLE001
        return unavailable("scorecard", "Calibration",
                           f"The scorecard could not be read: {type(e).__name__}: {e}",
                           fix="Check 04_live_system/data/scorecard.db")

    if not rep or not any((v.get("settled", 0) + v.get("pending", 0)) for v in rep.values()):
        return empty("scorecard", "Calibration — are the calls honest",
                     "Nothing logged yet. Calibration needs settled calls to measure.",
                     fix="Runs accumulate as cycles settle. idt refresh")

    rows = []
    stats = []
    for tab, v in sorted(rep.items()):
        settled = v.get("settled", 0)
        pending = v.get("pending", 0)
        rows.append({
            "k": tab,
            "v": (f"{settled} settled, {pending} pending"
                  + (f" · hit {v.get('hit_rate')}%" if v.get("hit_rate") is not None else "")),
            "severity": "watch" if settled < 30 else None,
        })
        stats.append({"n": str(settled), "l": f"{tab} settled",
                      "severity": "watch" if settled < 30 else None})
        stats.append({"n": str(pending), "l": f"{tab} pending"})
        if v.get("hit_rate") is not None:
            stats.append({"n": f"{v['hit_rate']}%", "l": f"{tab} hit rate"})
    return panel("scorecard", "Calibration — are the calls honest", state=OK,
                 body={"rows": rows, "stats": stats},
                 note=("Calibrated means a call stated at conviction 60 or above actually wins "
                       "more often than one below it. Under about 30 settled calls, a hit rate "
                       "is noise."),
                 source="scorecard.report()")
