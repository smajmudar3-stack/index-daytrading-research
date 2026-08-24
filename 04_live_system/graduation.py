"""graduation.py — the pre-registered paper→live graduation gate, and an honest projection of whether
the agent's REAL measured edge can reach the growth curve.

Two jobs:

1. GRADUATION GATE (MEICAgent pattern, RESEARCH_BOTS.md #1). A fixed, pre-registered bar the paper
   track must clear before real money is even discussed. Pre-registered means the bar is written down
   BEFORE the results are in — moving it afterwards to make a strategy pass is the purest form of
   self-deception, so the thresholds live here as constants and changing them is a visible code edit.

2. HONEST PROJECTION. Takes the agent's ACTUAL measured expectancy and trade frequency and projects
   the account forward against growth_plan's milestone curve. If the measured edge cannot reach the
   target, this says so in plain numbers rather than letting the curve imply that it can.

Important measurement caveat, stated up front: the agent logs UNDERLYING move, not option premium P&L.
We convert with an explicit per-structure leverage factor (LEVERAGE below). Those factors are honest
approximations, not fills — every number here is labelled as an estimate and should be treated as a
directional read on the edge, not as a broker statement.
"""
import os
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "agent_trades.db")
OUT = os.path.join(HERE, "data", "graduation.json")

# ── PRE-REGISTERED BAR — do not move these to make a result pass ───────────────
# Aligned to RULES.md §6.5, which sets the bar for the ONE structure that survived testing (the 0DTE
# condor). The backtested profile is a 91% win rate with losers averaging -50% of risk, so a mediocre
# win rate here is not "still profitable" — it means the structure is behaving differently than tested.
BAR = {
    "min_trades": 30,            # enough closed trades that win rate isn't noise
    "min_win_rate": 0.85,        # premium selling at 1.25 SD; backtest showed 91%
    "min_expectancy_pct": 0.0,   # must be genuinely positive net of costs
    "min_profit_factor": 1.50,
    "max_profit_factor": 4.00,   # implausibly high = a bug or a fluke, not an edge
    "max_drawdown_pct": 12.0,    # 1.5x the backtested -8.1% at 5% risk
}

# Rough option-level leverage vs the underlying move, by structure. Deliberately conservative.
LEVERAGE = {
    "LONG_CALL": 12.0, "LONG_PUT": 12.0,
    "CALL_DEBIT_SPREAD": 6.0, "PUT_DEBIT_SPREAD": 6.0,
    "CALL_CREDIT_SPREAD": 4.0, "PUT_CREDIT_SPREAD": 4.0, "IRON_CONDOR": 3.0,
}
DEFAULT_LEVERAGE = 5.0
COST_PCT = 2.0          # est. round-trip friction (spread + fees) as % of premium risked


def _con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def _closed():
    try:
        c = _con()
        rows = c.execute("SELECT * FROM trades WHERE status='closed' ORDER BY id").fetchall()
        c.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _trade_return_pct(t):
    """Option-level return for one closed trade, net of friction.

    Prefers pnl_real_pct — an actual premium-in/premium-out measurement from live quotes. Only falls
    back to the underlying-move × leverage ESTIMATE when the trade could not be priced."""
    real = t.get("pnl_real_pct")
    if real is not None:
        return max(float(real) - COST_PCT, -100.0)
    mv = t.get("pnl_pct")
    if mv is None:
        return None
    lev = LEVERAGE.get((t.get("structure") or "").upper(), DEFAULT_LEVERAGE)
    r = float(mv) * lev - COST_PCT
    # a defined-risk structure cannot lose more than the premium
    return max(r, -100.0)


def _measured_fraction(trades):
    """What share of the track record is real measurement vs. estimate — reported, never hidden."""
    if not trades:
        return 0.0
    n_real = sum(1 for t in trades if t.get("pnl_real_pct") is not None)
    return round(n_real / len(trades), 2)


def stats():
    trades = _closed()
    rets = [r for r in (_trade_return_pct(t) for t in trades) if r is not None]
    n = len(rets)
    if n == 0:
        return {"n": 0, "ready": False, "note": "no closed trades yet — the track record starts here"}
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    win_rate = len(wins) / n
    expectancy = sum(rets) / n
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    # equity curve on the estimated returns, for drawdown
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= (1 + r / 100.0)
        peak = max(peak, eq)
        mdd = max(mdd, (peak - eq) / peak * 100)
    return {
        "n": n,
        "win_rate": round(win_rate, 3),
        "avg_win_pct": round(sum(wins) / len(wins), 2) if wins else 0.0,
        "avg_loss_pct": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "expectancy_pct": round(expectancy, 2),
        "profit_factor": round(pf, 2) if pf != float("inf") else None,
        "max_drawdown_pct": round(mdd, 1),
        "total_return_pct": round((eq - 1) * 100, 1),
        "measured_fraction": _measured_fraction(trades),
    }


def check():
    """Score the paper track against the pre-registered bar."""
    s = stats()
    if not s.get("n"):
        return {"verdict": "NO DATA", "stats": s, "criteria": [], "passed": 0, "total": 0}
    pf = s.get("profit_factor")
    crit = [
        ("sample size",   s["n"] >= BAR["min_trades"],
         f"{s['n']} closed vs {BAR['min_trades']} required"),
        ("win rate",      s["win_rate"] >= BAR["min_win_rate"],
         f"{s['win_rate']*100:.0f}% vs {BAR['min_win_rate']*100:.0f}% required"),
        ("expectancy",    s["expectancy_pct"] > BAR["min_expectancy_pct"],
         f"{s['expectancy_pct']:+.2f}%/trade (est, net of {COST_PCT}% friction)"),
        ("profit factor", pf is not None and BAR["min_profit_factor"] <= pf <= BAR["max_profit_factor"],
         f"{pf if pf is not None else 'n/a'} vs {BAR['min_profit_factor']}–{BAR['max_profit_factor']} band"),
        ("drawdown",      s["max_drawdown_pct"] <= BAR["max_drawdown_pct"],
         f"{s['max_drawdown_pct']:.0f}% vs {BAR['max_drawdown_pct']:.0f}% max"),
    ]
    passed = sum(1 for _, ok, _ in crit if ok)
    verdict = "GRADUATED — eligible for supervised live sizing" if passed == len(crit) else "PAPER ONLY"
    return {"verdict": verdict, "stats": s, "passed": passed, "total": len(crit),
            "criteria": [{"name": nm, "pass": ok, "detail": d} for nm, ok, d in crit]}


def projection():
    """Given the MEASURED expectancy and trade rate, can the account reach the growth curve? Honest math."""
    try:
        import growth_plan
    except Exception:
        return {}
    s = stats()
    acct = growth_plan.get_account()
    ms = growth_plan.MILESTONES[-1]
    target_date, target_val = ms[0], ms[1]
    days = (datetime.strptime(target_date, "%Y-%m-%d").date() - datetime.now(ET).date()).days
    need_x = target_val / acct if acct else 0

    if not s.get("n") or s.get("expectancy_pct") is None:
        return {"target": target_val, "target_date": target_date, "account": acct,
                "need_x": round(need_x, 1), "days": days,
                "verdict": "unknown — not enough closed trades to measure an edge yet"}

    # risk fraction per trade from the hard cap
    risk_frac = growth_plan.RISK_CAP["max_risk_per_trade_pct"] / 100.0
    exp = s["expectancy_pct"] / 100.0
    trades = _closed()
    # observed trade rate per trading day
    try:
        d0 = min(datetime.fromisoformat(t["ts"]).date() for t in trades if t.get("ts"))
        span_days = max((datetime.now(ET).date() - d0).days, 1)
        per_day = len(trades) / span_days
    except Exception:
        per_day = 1.0
    trading_days = max(int(days * 5 / 7), 1)
    n_trades = per_day * trading_days
    growth_per_trade = 1 + risk_frac * exp
    projected = acct * (growth_per_trade ** n_trades) if growth_per_trade > 0 else 0

    if projected >= target_val:
        verdict = f"on this measured edge the curve is reachable (projected ${projected:,.0f})"
    else:
        # what expectancy WOULD be needed
        need_growth = (target_val / acct) ** (1 / n_trades) if n_trades > 0 and acct else 0
        need_exp = (need_growth - 1) / risk_frac * 100 if risk_frac else 0
        verdict = (f"NOT reachable on the measured edge — projects to ${projected:,.0f}, not ${target_val:,.0f}. "
                   f"Hitting it would need ~{need_exp:.1f}% expectancy per trade "
                   f"(measured: {s['expectancy_pct']:+.2f}%) over ~{n_trades:.0f} trades.")
    return {"target": target_val, "target_date": target_date, "account": acct, "need_x": round(need_x, 1),
            "days": days, "est_trades_remaining": round(n_trades), "measured_expectancy_pct": s["expectancy_pct"],
            "projected_account": round(projected), "verdict": verdict}


DIRECTIONAL = ("LONG_CALL", "LONG_PUT", "CALL_DEBIT_SPREAD", "PUT_DEBIT_SPREAD")
RANGE = ("IRON_CONDOR", "CALL_CREDIT_SPREAD", "PUT_CREDIT_SPREAD")


def by_strategy():
    """Split the track record into RANGE (the validated condor) vs DIRECTIONAL (long premium).

    These are different businesses with opposite payoff shapes — the condor wins small and often, the
    directional trade loses small and often and occasionally pays for everything. Blending them into
    one 'win rate' hides which one is actually making money. Backtesting said range +3.7%/trade and
    directional −10 to −11%/trade; this is where the account's own fills get to answer."""
    out = {}
    for label, structs in (("range", RANGE), ("directional", DIRECTIONAL)):
        rows = [t for t in _closed() if (t.get("structure") or "").upper() in structs]
        rets = [r for r in (_trade_return_pct(t) for t in rows) if r is not None]
        if not rets:
            out[label] = {"n": 0}
            continue
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r <= 0]
        gl = abs(sum(losses))
        eq = 1.0
        for r in rets:
            eq *= (1 + r / 100.0)
        out[label] = {
            "n": len(rets),
            "win_rate": round(len(wins) / len(rets), 3),
            "expectancy_pct": round(sum(rets) / len(rets), 2),
            "avg_win_pct": round(sum(wins) / len(wins), 2) if wins else 0.0,
            "avg_loss_pct": round(sum(losses) / len(losses), 2) if losses else 0.0,
            "profit_factor": round(sum(wins) / gl, 2) if gl > 0 else None,
            "best_pct": round(max(rets), 1),
            "total_return_pct": round((eq - 1) * 100, 1),
        }
    return out


def report():
    r = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "bar": BAR,
         "graduation": check(), "projection": projection(), "by_strategy": by_strategy()}
    json.dump(r, open(OUT, "w"), indent=2, default=str)
    return r


def prompt_block():
    """Feed the agent its own measured track record — it should trade differently at 40% win rate
    than at 65%, and it should know which it actually has."""
    g = check()
    s = g.get("stats") or {}
    if not s.get("n"):
        return ("TRACK RECORD: no closed trades yet. You are unproven — trade small and prioritise "
                "building a clean, honest sample over chasing the curve.")
    return (f"YOUR MEASURED TRACK RECORD (estimated, {s['n']} closed trades): win rate "
            f"{s['win_rate']*100:.0f}%, expectancy {s['expectancy_pct']:+.2f}%/trade, profit factor "
            f"{s.get('profit_factor')}, max drawdown {s['max_drawdown_pct']:.0f}%. Status: {g['verdict']} "
            f"({g['passed']}/{g['total']} pre-registered criteria met). Trade the edge you actually have, "
            "not the one you wish you had — if expectancy is negative, the correct action is to stand down "
            "far more often and only take the very best-aligned setups.")


if __name__ == "__main__":
    r = report()
    g = r["graduation"]
    print(f"── GRADUATION GATE ──  {g['verdict']}  ({g.get('passed')}/{g.get('total')})")
    for c in g.get("criteria", []):
        print(f"  {'✓' if c['pass'] else '✗'} {c['name']:<14} {c['detail']}")
    print("\n── STATS ──")
    print(json.dumps(g.get("stats", {}), indent=2))
    p = r.get("projection") or {}
    if p:
        print("\n── HONEST PROJECTION vs THE CURVE ──")
        print(f"  account ${p.get('account'):,} → target ${p.get('target'):,} by {p.get('target_date')} "
              f"({p.get('need_x')}x in {p.get('days')} days)")
        print(f"  {p.get('verdict')}")
