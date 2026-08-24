"""sleeves.py — capital split into independent sleeves, each with its own risk budget and cadence.

The account is divided so a bad run in one strategy cannot consume the other's capital. Risk per trade
is computed against the SLEEVE, never the whole account, which is the point of separating them.

    0DTE  $2,000 — the one validated edge (RULES.md §1.2 condor). Managed continuously while a
                   position is open, because a 0DTE position's whole life is a single session.
    SWING $3,000 — checked hourly. See the honesty note below.

HONESTY NOTE ON THE SWING SLEEVE
    Out-of-sample testing rejected every swing OPTIONS structure tested (RULES.md §3.6-3.8, §4):
    sector-rotation picks did worse than random (p=0.867); long index debit spreads returned less than
    owning SPY with half the Sharpe and worse drawdown; 35-DTE put credit spreads lost to buy-and-hold
    and had a four-year dead period. There is no validated swing options edge in this data.

    So this sleeve runs in one of two modes, and the choice is explicit rather than buried:
      "index"    — hold the index (or a modest leveraged ETF). This is what the research supports.
      "options"  — the least-bad tested program (35-DTE put credit spreads at small size), clearly
                   labelled a DIVERSIFIER and not an edge, requiring live-quote validation first.
    Default is "index", because that is what the evidence says. Changing it is a deliberate act.
"""
import os
import json
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "data", "sleeves.json")

DEFAULTS = {
    "0dte": {
        "capital": 2000.0,
        "max_risk_per_trade_pct": 12.0,   # of the SLEEVE
        "max_open": 1,                    # RULES.md: one condor at a time (correlated-tail cap)
        "cadence_seconds": 600,           # decide every ~10 min inside the entry window
        "monitor_seconds": 60,            # while a position is open, check every minute
    },
    "swing": {
        "capital": 3000.0,
        "max_risk_per_trade_pct": 8.0,
        "max_open": 2,
        "cadence_seconds": 3600,          # hourly, as requested
        "monitor_seconds": 3600,
        "mode": "index",                  # "index" (evidence-backed) | "options" (diversifier only)
    },
}


def _load():
    try:
        cfg = json.load(open(CFG))
    except Exception:
        cfg = {}
    out = {}
    for k, v in DEFAULTS.items():
        out[k] = {**v, **(cfg.get(k) or {})}
    return out


def save(cfg):
    json.dump(cfg, open(CFG, "w"), indent=2)
    return cfg


def get(name):
    return _load().get(name, {})


def all_sleeves():
    return _load()


def total_capital():
    return sum(s.get("capital", 0) for s in _load().values())


def sleeve_for(decision):
    """Which sleeve does this decision draw from? 0DTE expiry -> the 0DTE sleeve, else swing."""
    return "0dte" if (decision.get("expiry") or "").upper() == "0DTE" else "swing"


def budget(name):
    s = get(name)
    cap = float(s.get("capital", 0))
    return {"sleeve": name, "capital": cap,
            "max_risk_dollars": round(cap * float(s.get("max_risk_per_trade_pct", 0)) / 100.0, 2),
            "max_risk_pct": s.get("max_risk_per_trade_pct"),
            "max_open": s.get("max_open")}


def open_count(name):
    """Open positions currently attributed to a sleeve."""
    try:
        import ai_trader
        n = 0
        for t in ai_trader.open_trades():
            if sleeve_for(t) == name:
                n += 1
        return n
    except Exception:
        return 0


def set_capital(name, value):
    cfg = _load()
    if name in cfg:
        cfg[name]["capital"] = float(value)
        save(cfg)
    return cfg


def prompt_block():
    c = _load()
    _z, s = c["0dte"], c["swing"]
    zb, sb = budget("0dte"), budget("swing")
    mode = s.get("mode", "index")
    swing_line = (
        "the research supports HOLDING THE INDEX here, not buying or selling option premium — "
        "every swing options structure tested lost to simply owning SPY on return, Sharpe and drawdown. "
        "Do not propose swing option trades while this sleeve is in 'index' mode."
        if mode == "index" else
        "this sleeve is in 'options' mode: 35-DTE put credit spreads at SMALL size only, explicitly a "
        "diversifier and NOT a validated edge. Keep size minimal and expect no alpha."
    )
    return (
        f"CAPITAL SLEEVES — risk is budgeted per sleeve, never against the whole account.\n"
        f"  0DTE sleeve: ${zb['capital']:,.0f} · max ${zb['max_risk_dollars']:,.0f} risk/trade "
        f"({zb['max_risk_pct']}%) · max {zb['max_open']} open (currently {open_count('0dte')}). "
        f"This is where the one validated edge lives.\n"
        f"  SWING sleeve: ${sb['capital']:,.0f} · max ${sb['max_risk_dollars']:,.0f} risk/trade "
        f"({sb['max_risk_pct']}%) · max {sb['max_open']} open (currently {open_count('swing')}), "
        f"mode '{mode}' — {swing_line}\n"
        f"A 0DTE proposal draws on the 0DTE sleeve only; anything longer-dated draws on the swing sleeve. "
        f"Never size a trade against the combined balance."
    )


if __name__ == "__main__":
    c = _load()
    print(f"total capital: ${total_capital():,.0f}")
    for name in ("0dte", "swing"):
        b = budget(name)
        s = c[name]
        print(f"\n{name.upper():6s} ${b['capital']:,.0f} | risk/trade ${b['max_risk_dollars']:,.0f} "
              f"({b['max_risk_pct']}%) | max open {b['max_open']} (now {open_count(name)})")
        print(f"       decide every {s['cadence_seconds']}s · monitor every {s['monitor_seconds']}s"
              + (f" · mode {s['mode']}" if s.get("mode") else ""))
    # what the 0DTE sleeve can actually hold
    try:
        import rules, sizing
        cd = rules.build_condor("SPY", account=c["0dte"]["capital"])
        if cd and cd.get("ok"):
            sz = sizing.size_trade(cd["risk_pts"], 80, account=c["0dte"]["capital"],
                                   sleeve_cap_pct=c["0dte"]["max_risk_per_trade_pct"])
            print(f"\nSPY condor vs the 0DTE sleeve: risk ${cd['risk_pts']*100:,.0f}/contract -> {sz['reason']}")
    except Exception as e:
        print("\n(condor sizing preview unavailable:", type(e).__name__, str(e)[:60], ")")
