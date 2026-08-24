"""graduation.py — the pre-registered paper→live graduation gate, and an honest projection of whether
the agent's REAL measured edge can reach the growth curve.

Two jobs:

1. GRADUATION GATE (MEICAgent pattern, RESEARCH_BOTS.md #1). A fixed, pre-registered bar the paper
   track must clear before real money is even discussed. Pre-registered means the bar is written down
   BEFORE the results are in — moving it afterwards to make a strategy pass is the purest form of
   self-deception, so the thresholds live here as constants and changing them is a visible code edit.
   BAR_FINGERPRINT pins those constants: edit a threshold without updating the pin and every import
   of this module fails, by design.

2. HONEST PROJECTION. Takes the agent's ACTUAL measured expectancy and trade frequency and projects
   the account forward against growth_plan's milestone curve. If the measured edge cannot reach the
   target, this says so in plain numbers rather than letting the curve imply that it can.

Important measurement caveat, stated up front: the agent logs UNDERLYING move, not option premium P&L.
We convert with an explicit per-structure leverage factor (LEVERAGE below). Those factors are honest
approximations, not fills — every number here is labelled as an estimate and should be treated as a
directional read on the edge, not as a broker statement.

Which is why stats() reports measured_fraction, n_measured and n_modelled at the top level: the share
of the track record priced from real option quotes is the single number that says how much of the rest
to believe. It is not a footnote; it belongs on the first screen.
"""
import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from idt import db, paths

log = logging.getLogger("graduation")

ET = ZoneInfo("America/New_York")
# Both live under STATE_ROOT (04_live_system/data by default). These used to be built with
# os.path.join(HERE, "data", ...) and opened with a bare sqlite3 handle — no directory creation,
# no WAL, a 5-second lock. That is how a fresh clone raised "unable to open database file" inside
# a render and took the whole page down.
DB = paths.state("agent_trades.db")
OUT = paths.state("graduation.json")

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

# The pinned digest of the bar above. A pre-registered threshold that can be edited in one quiet line
# is not pre-registered, so moving one now takes TWO deliberate edits and shows up twice in the diff.
# The fingerprint also rides along in graduation.json and in check(), so an old report can be compared
# against a current bar and a change is visible after the fact, not only at review time.
BAR_FINGERPRINT = "82a663afedee5046"


def bar_fingerprint():
    """Digest of the pre-registered bar as it currently stands in the source."""
    payload = json.dumps(sorted(BAR.items()), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


if bar_fingerprint() != BAR_FINGERPRINT:
    raise RuntimeError(
        "graduation.BAR was changed but BAR_FINGERPRINT was not.\n"
        f"    pinned:  {BAR_FINGERPRINT}\n"
        f"    current: {bar_fingerprint()}\n"
        "  The bar is pre-registered: it is written down before the results are in, and moving it\n"
        "  afterwards so a strategy passes is the failure this whole module exists to prevent.\n"
        "  If the change is deliberate, set BAR_FINGERPRINT to the current value above and record\n"
        "  what changed, and why, in docs/VERDICT_LOG.md.")

# Rough option-level leverage vs the underlying move, by structure. Deliberately conservative.
LEVERAGE = {
    "LONG_CALL": 12.0, "LONG_PUT": 12.0,
    "CALL_DEBIT_SPREAD": 6.0, "PUT_DEBIT_SPREAD": 6.0,
    "CALL_CREDIT_SPREAD": 4.0, "PUT_CREDIT_SPREAD": 4.0, "IRON_CONDOR": 3.0,
}
DEFAULT_LEVERAGE = 5.0
COST_PCT = 2.0          # est. round-trip friction (spread + fees) as % of premium risked


class BookUnavailable(RuntimeError):
    """The trade book could not be read.

    Deliberately distinct from "no trades yet". The old code returned [] for both, so a corrupt or
    locked database rendered as a clean empty scorecard — the reader cannot tell "nothing has
    happened" from "we cannot see what happened", and only one of those is safe to trust.
    """


def _closed():
    """Every closed trade, oldest first. Raises BookUnavailable if the book cannot be read."""
    try:
        c = db.connect(DB, readonly=True)
    except sqlite3.Error as e:
        log.error("graduation: cannot open the trade book at %s: %s", DB, e)
        raise BookUnavailable(f"cannot open {DB}: {e}") from e
    c.row_factory = sqlite3.Row
    try:
        rows = c.execute("SELECT * FROM trades WHERE status='closed' ORDER BY id").fetchall()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            return []          # the book has never been written to. Honestly empty, not broken.
        log.error("graduation: cannot read the trade book at %s: %s", DB, e)
        raise BookUnavailable(f"cannot read {DB}: {e}") from e
    finally:
        c.close()
    return [dict(r) for r in rows]


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


def _measured_split(trades):
    """The counts behind measured_fraction, so the fraction can be checked rather than believed.

    measured   the trade was re-priced at the live market on the way out (pnl_real_pct). This is the
               only kind of row that makes the track record a measurement.
    modelled   no exit price, so the return is the underlying's move times a leverage factor.
    unmarked   closed with neither number. It counts against measured_fraction (it is in the
               denominator) but contributes no return, which is exactly why the counts are shown.
    """
    n_closed = len(trades)
    n_measured = sum(1 for t in trades if t.get("pnl_real_pct") is not None)
    n_modelled = sum(1 for t in trades
                     if t.get("pnl_real_pct") is None and t.get("pnl_pct") is not None)
    frac = _measured_fraction(trades)
    if n_closed == 0:
        note = "No closed trades yet, so nothing has been measured."
    elif n_measured == 0:
        note = (f"0 of {n_closed} closed trades were priced from real option quotes. Every P&L number "
                f"here is an estimate: the underlying's move times a leverage factor.")
    else:
        rest = n_closed - n_measured
        note = (f"{n_measured} of {n_closed} closed trades ({round(frac * 100)}%) were priced from real "
                f"option quotes. The other {rest} {'is' if rest == 1 else 'are'} an estimate: the "
                f"underlying's move times a leverage factor.")
    return {"measured_fraction": frac, "measured_pct": round(frac * 100),
            "n_closed": n_closed, "n_measured": n_measured, "n_modelled": n_modelled,
            "n_unmarked": n_closed - n_measured - n_modelled, "measured_note": note}


def stats():
    """The track record. Always returns a dict; never lets an unreadable book read as an empty one."""
    try:
        trades = _closed()
    except BookUnavailable as e:
        return {"n": 0, "ready": False, "unavailable": True, "error": str(e),
                "measured_fraction": None, "measured_pct": None, "n_closed": None,
                "n_measured": None, "n_modelled": None, "n_unmarked": None,
                "measured_note": "The trade book could not be read, so this is not 'no trades yet'.",
                "note": f"trade book unreadable: {e}"}
    split = _measured_split(trades)
    rets = [r for r in (_trade_return_pct(t) for t in trades) if r is not None]
    n = len(rets)
    if n == 0:
        return {"n": 0, "ready": False,
                "note": "no closed trades yet — the track record starts here", **split}
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
        # measured vs modelled, up front. n is the number of trades that produced a return
        # (measured + modelled); n_closed is every closed trade, which is what the fraction divides by.
        **split,
    }


def check():
    """Score the paper track against the pre-registered bar."""
    s = stats()
    # measured_fraction rides on the verdict itself: passing the bar on a track record that was never
    # priced at a real market is not the same result as passing it on fills, and the dashboard should
    # not have to dig into stats to find that out.
    head = {"bar_fingerprint": BAR_FINGERPRINT,
            "measured_fraction": s.get("measured_fraction"),
            "measured_pct": s.get("measured_pct"),
            "n_measured": s.get("n_measured"),
            "n_modelled": s.get("n_modelled"),
            "measured_note": s.get("measured_note")}
    if s.get("unavailable"):
        return {"verdict": "UNAVAILABLE: the trade book could not be read", "stats": s,
                "criteria": [], "passed": 0, "total": 0, **head}
    if not s.get("n"):
        return {"verdict": "NO DATA", "stats": s, "criteria": [], "passed": 0, "total": 0, **head}
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
            "criteria": [{"name": nm, "pass": ok, "detail": d} for nm, ok, d in crit], **head}


def projection():
    """Given the MEASURED expectancy and trade rate, can the account reach the growth curve? Honest math."""
    try:
        import growth_plan
    except Exception as e:
        # Returning {} used to make "the growth plan failed to load" look identical to "there is no
        # projection". The keys below are the ones the dashboard formats, so it renders the reason.
        log.warning("graduation.projection: growth_plan unavailable (%s: %s)", type(e).__name__, e)
        return {"verdict": f"unavailable: growth_plan could not be loaded ({type(e).__name__})",
                "error": f"{type(e).__name__}: {e}", "account": 0, "target": 0,
                "target_date": "", "need_x": 0, "days": 0}
    s = stats()
    acct = growth_plan.get_account()
    ms = growth_plan.MILESTONES[-1]
    target_date, target_val = ms[0], ms[1]
    days = (datetime.strptime(target_date, "%Y-%m-%d").date() - datetime.now(ET).date()).days
    need_x = target_val / acct if acct else 0

    if s.get("unavailable"):
        return {"target": target_val, "target_date": target_date, "account": acct,
                "need_x": round(need_x, 1), "days": days,
                "verdict": "unavailable: the trade book could not be read, so there is no measured edge to project"}
    if not s.get("n") or s.get("expectancy_pct") is None:
        return {"target": target_val, "target_date": target_date, "account": acct,
                "need_x": round(need_x, 1), "days": days,
                "verdict": "unknown — not enough closed trades to measure an edge yet"}

    # risk fraction per trade from the hard cap
    risk_frac = growth_plan.RISK_CAP["max_risk_per_trade_pct"] / 100.0
    exp = s["expectancy_pct"] / 100.0
    trades = _closed()
    # observed trade rate per trading day
    dated = [t["ts"] for t in trades if t.get("ts")]
    rate_source = "measured from the book"
    per_day = 1.0
    try:
        d0 = min(datetime.fromisoformat(t).date() for t in dated)
        span_days = max((datetime.now(ET).date() - d0).days, 1)
        per_day = len(trades) / span_days
    except (ValueError, TypeError) as e:
        # An assumed trade rate drives the projected account value, so it may not be assumed quietly.
        log.warning("graduation.projection: cannot read trade timestamps (%s) — assuming 1 trade/day", e)
        rate_source = "ASSUMED 1 trade/day (timestamps unreadable)"
    if not dated:
        rate_source = "ASSUMED 1 trade/day (no trade timestamps in the book)"
        log.warning("graduation.projection: no usable timestamps — assuming 1 trade/day")
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
            "trade_rate_source": rate_source, "measured_fraction": s.get("measured_fraction"),
            "projected_account": round(projected), "verdict": verdict}


DIRECTIONAL = ("LONG_CALL", "LONG_PUT", "CALL_DEBIT_SPREAD", "PUT_DEBIT_SPREAD")
RANGE = ("IRON_CONDOR", "CALL_CREDIT_SPREAD", "PUT_CREDIT_SPREAD")


def by_strategy():
    """Split the track record into RANGE (the validated condor) vs DIRECTIONAL (long premium).

    These are different businesses with opposite payoff shapes — the condor wins small and often, the
    directional trade loses small and often and occasionally pays for everything. Blending them into
    one 'win rate' hides which one is actually making money. Backtesting said range +3.7%/trade and
    directional −10 to −11%/trade; this is where the account's own fills get to answer."""
    try:
        closed = _closed()
    except BookUnavailable as e:
        return {"unavailable": True, "error": str(e)}
    out = {}
    for label, structs in (("range", RANGE), ("directional", DIRECTIONAL)):
        rows = [t for t in closed if (t.get("structure") or "").upper() in structs]
        rets = [r for r in (_trade_return_pct(t) for t in rows) if r is not None]
        if not rets:
            out[label] = {"n": 0, **_measured_split(rows)}
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
            **_measured_split(rows),
        }
    return out


def report():
    r = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "bar": BAR,
         "bar_fingerprint": BAR_FINGERPRINT,
         "graduation": check(), "projection": projection(), "by_strategy": by_strategy()}
    try:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=2, default=str)
    except OSError as e:
        # The dashboard reads this file. A failed write leaves yesterday's scorecard on screen
        # looking current, so say so rather than returning as if it landed.
        log.error("graduation.report: could not write %s: %s", OUT, e)
        r["write_error"] = f"{type(e).__name__}: {e}"
    return r


def prompt_block():
    """Feed the agent its own measured track record — it should trade differently at 40% win rate
    than at 65%, and it should know which it actually has."""
    g = check()
    s = g.get("stats") or {}
    if s.get("unavailable"):
        return ("TRACK RECORD: unavailable, the trade book could not be read. Treat yourself as "
                "unproven and trade at minimum size until it can be.")
    if not s.get("n"):
        return ("TRACK RECORD: no closed trades yet. You are unproven — trade small and prioritise "
                "building a clean, honest sample over chasing the curve.")
    return (f"YOUR MEASURED TRACK RECORD (estimated, {s['n']} closed trades): win rate "
            f"{s['win_rate']*100:.0f}%, expectancy {s['expectancy_pct']:+.2f}%/trade, profit factor "
            f"{s.get('profit_factor')}, max drawdown {s['max_drawdown_pct']:.0f}%. "
            f"{s.get('measured_note', '')} Status: {g['verdict']} "
            f"({g['passed']}/{g['total']} pre-registered criteria met). Trade the edge you actually have, "
            "not the one you wish you had — if expectancy is negative, the correct action is to stand down "
            "far more often and only take the very best-aligned setups.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    r = report()
    g = r["graduation"]
    print(f"── GRADUATION GATE ──  {g['verdict']}  ({g.get('passed')}/{g.get('total')})")
    for c in g.get("criteria", []):
        print(f"  {'✓' if c['pass'] else '✗'} {c['name']:<14} {c['detail']}")
    print(f"  bar fingerprint {BAR_FINGERPRINT} (pre-registered; a change here is a two-line edit)")
    print(f"\n── MEASURED vs MODELLED ──\n  {g.get('measured_note')}")
    print("\n── STATS ──")
    print(json.dumps(g.get("stats", {}), indent=2))
    p = r.get("projection") or {}
    if p:
        print("\n── HONEST PROJECTION vs THE CURVE ──")
        print(f"  account ${p.get('account'):,} → target ${p.get('target'):,} by {p.get('target_date')} "
              f"({p.get('need_x')}x in {p.get('days')} days)")
        print(f"  {p.get('verdict')}")
