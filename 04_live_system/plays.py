"""plays.py — the Plays desk: a few swing plays a week, each with a timeline, an enumerated
reasoning stack, an expected profit and a confidence label it earned. Every play is a signal
this repo measured, expressed the way that measured best, priced at the ask and the bid,
recorded in a ledger the day it is issued and scored against what it promised. PAPER.

WHAT A PLAY IS. A stock signal with a measured forward return:
  SURPRISE      top-25 earnings surprise, 63-session hold     +7.4% hit 0.60 in shares (n 346 with chains)
  RANKER        surprise + residual + 12-1 momentum, 21 sess  +2.0% hit 0.52
  STRESS_VIX25  bottom-40 reversal composite while VIX > 25   +5.5% hit 0.60
  STRESS_ALL    the same book out of regime                   +1.0% hit 0.52 (booked at Sholo's instruction)
expressed as the structure that measured best for it on seven years of real chains
(05_studies/play_structures_test.py -> opt_panel/play_structures.parquet). THE MEASUREMENT
SAYS SHARES. Every option structure tested on these signals (70/40 and 50/25 call debits,
60- and 80-delta long calls, a 30/15 put credit) lost per dollar of risk once the round
trip was paid: 12–57% of max risk goes to the bid-ask alone at these horizons. The stress
long calls print a huge raw mean, and 99% of it is the top 5% of trades, at up to 1,722x on
chains quoted in pre-split units; with those rows removed and the rest clipped at 3x, the
in-regime long call is +4% with a median of −36% and a flat 2022–23 split, and every other
cell is negative. So a card LEADS with the measured expression and prints the option legs
beside it, priced off the live ladder, with that structure's own measured number — the
reader sees what the option costs against what the shares made and chooses with the
numbers in front of them. An option cell would issue as the lead only when its clipped
mean is positive in every split with a median better than −35% and 100+ trades; today
none does, and the gate stays so the next backtest can change that without a code change.

Nothing from the desk notes, Unusual Whales or the morning research session MAKES a play:
none of those measured a direction. They are the reasoning stack around a measured one —
the macro theme, the catalysts inside the hold, what the options market prices, the news —
and a disagreement lowers the confidence or vetoes; it never raises it.

HOW MANY. N_PER_WEEK new plays at most, on ISSUE_WEEKDAYS, ranked by measured expectancy
per dollar of risk, a bonus when two books name the same stock, a veto when the desk notes
argue against it or a high-importance macro print lands on the expiry.
"""
import json
import math
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from idt import db as _db
from idt import paths, snapshots

ET = ZoneInfo("America/New_York")
OUT = "plays_snapshot.json"
DB = paths.state("plays.db")
PRIORS_FILE = os.path.join(paths.DATA_ROOT, "opt_panel", "play_structures.parquet")
RESEARCH_FILE = "plays_research.json"

N_PER_WEEK = 3
ISSUE_WEEKDAYS = (0, 2)               # Monday and Wednesday, after the stock books have refreshed
MAX_COST_PCT = 25.0                   # round-trip bid-ask as a share of max risk (the weekly book's 20% was for 14 DTE)
MIN_OI = 25
RISK_PER_PLAY_USD = 500.0             # sizing shown on the card: a $5k account, ten percent a play
CLIP_HI = 3.0                         # a 4x return on a debit inside 21–95 DTE is the most a real fill plausibly pays
MIN_PRIOR_N = 100
MIN_MEDIAN = -0.35
SHARES_COST_PCT = 0.1
MIN_MONEYNESS, MAX_MONEYNESS = 0.5, 1.5   # the long strike as a share of spot; outside it the chain is in the wrong units

SOURCES = {
    "surprise": {"snapshot": "swing_stock_snapshot.json", "sessions": 63, "dte": 95,
                 "measured": "+4.24% over SPY per quarter, t 2.3, hit 0.49, payoff 1.6, all three splits; +7.4% hit 0.60 on the names with chains (signal_accuracy.md, play_structures.md)"},
    "ranker": {"snapshot": "swing_ranker_snapshot.json", "sessions": 21, "dte": 35,
               "measured": "+0.84% over SPY per 4 weeks, hit 0.49, payoff 1.24, all three splits (signal_accuracy.md)"},
    "stress_vix25": {"snapshot": "stress_reversal_snapshot.json", "sessions": 10, "dte": 21,
                     "measured": "+2.59% over SPY per 10 sessions when VIX > 25, hit 0.56, t 2.6; +5.5% hit 0.60 on the names with chains (stress_reversal.md)"},
    "stress_all": {"snapshot": "stress_reversal_snapshot.json", "sessions": 10, "dte": 21,
                   "measured": "out of regime: +1.0% hit 0.52 in shares, flat to negative over SPY; booked at Sholo's instruction and scored separately (stress_reversal.md)"},
}
STRUCT_PREFERENCE = ["shares", "long_call_80", "long_call_60", "call_debit_70_40", "call_debit_50_25", "put_credit_30_15"]
OPTION_ALTS = ["long_call_80", "call_debit_70_40", "long_call_60"]
STRUCT_LABEL = {"shares": "Shares", "call_debit_70_40": "Call debit spread, 70/40 delta", "call_debit_50_25": "Call debit spread, 50/25 delta",
                "put_credit_30_15": "Put credit spread, 30/15 delta", "long_call_80": "Deep call, 80 delta (stock replacement)",
                "long_call_60": "Long call, 60 delta"}


def _now():
    return datetime.now(ET)


def _stamp():
    return _now().strftime("%Y-%m-%d %H:%M")


def _notify(title, msg):
    try:
        import subprocess
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}" sound name "Glass"'], timeout=5, check=False)
    except Exception:                                         # noqa: BLE001
        pass


# ------------------------------------------------------------------ priors ---

SPLITS = {"A": ("2019-01-01", "2021-12-31"), "B": ("2022-01-01", "2023-12-31"), "C": ("2024-01-01", "2026-12-31")}


def _cell(s, col):
    v = s[col].dropna().clip(-1, CLIP_HI)
    if len(v) < 30:
        return None
    win, loss = v[v > 0], v[v <= 0]
    sp = {}
    for k, (a, b) in SPLITS.items():
        vv = s[(s.date >= a) & (s.date <= b)][col].dropna().clip(-1, CLIP_HI)
        sp[k] = round(float(vv.mean()), 3) if len(vv) >= 15 else None
    raw = s[col].dropna()
    top = raw.sort_values(ascending=False)
    return {"mean": round(float(v.mean()), 3), "median": round(float(v.median()), 3), "hit": round(float((v > 0).mean()), 3),
            "payoff": round(float(win.mean() / -loss.mean()), 2) if len(loss) and loss.mean() < 0 and len(win) else None,
            "n": int(len(v)), "p25": round(float(v.quantile(.25)), 3), "p75": round(float(v.quantile(.75)), 3),
            "splits": sp, "raw_mean": round(float(raw.mean()), 3),
            "top5_share": round(float(top.head(max(1, len(top) // 20)).sum() / top.sum()), 2) if top.sum() > 0 else None,
            "t": round(float(v.mean() / v.std() * math.sqrt(len(v))), 2) if v.std() > 0 else None}


def priors():
    """{(signal, structure): cell} from the backtest, or {} if it has not been run. Means are
    clipped at CLIP_HI per dollar of risk; the raw mean and the top-5% share are kept beside
    them so a tail-driven cell is visible as one. 'shares' is the stock reference."""
    if not os.path.exists(PRIORS_FILE):
        return {}
    try:
        import pandas as pd
        t = pd.read_parquet(PRIORS_FILE)
    except Exception:                                         # noqa: BLE001
        return {}
    out = {}
    t["date"] = t["date"].astype(str)
    # A 60- or 80-delta strike sits near spot. 1,289 of 23,521 rows had the long strike below
    # half of spot or above one and a half times it: chains quoted in pre-split units against
    # split-adjusted prices (VEON at 812 with a 1-strike call). They paid 1,722x on paper and
    # carried the whole stress long-call result; they are not trades anyone could have made.
    mny = t["strike_l"] / t["spot_0"]
    t = t[(mny >= MIN_MONEYNESS) & (mny <= MAX_MONEYNESS)]
    for (sig, struct), s in t.groupby(["signal", "struct"]):
        c = _cell(s, "pnl_risk")
        if c:
            c["cost_pct"] = round(float(s.cost_pct.median() * 100), 1)
            out[(sig, struct)] = c
    if "stock_ret" in t.columns:
        for sig, s in t.drop_duplicates(["date", "act_symbol", "signal"]).groupby("signal"):
            c = _cell(s, "stock_ret")
            if c:
                c["cost_pct"] = SHARES_COST_PCT
                out[(sig, "shares")] = c
    return out


def _qualifies(p):
    sp = [v for v in p["splits"].values() if v is not None]
    return p["n"] >= MIN_PRIOR_N and p["mean"] > 0 and bool(sp) and all(v > 0 for v in sp) and p["median"] >= MIN_MEDIAN


def best_structure(sig, pri):
    """The structure with the best clipped mean per $ risk for this signal among cells that
    qualify (positive in every split, median above −35%, 100+ trades). Shares when nothing
    else qualifies and shares are positive. (None, None) when nothing measured positive."""
    cands = sorted(((p["mean"], st) for (s, st), p in pri.items() if s == sig and _qualifies(p)), reverse=True)
    if cands:
        return cands[0][1], pri[(sig, cands[0][1])]
    sh = pri.get((sig, "shares"))
    if sh and sh["mean"] > 0:
        return "shares", sh
    return None, None


def confidence(p, agreements, vetoes):
    """A label earned from the prior, never typed."""
    if vetoes:
        return "vetoed"
    if not p:
        return "unmeasured"
    sp = [v for v in p["splits"].values() if v is not None]
    all_pos = bool(sp) and all(v > 0 for v in sp)
    if p["mean"] > 0 and all_pos and p["hit"] >= 0.45:
        return "measured, all splits" + (" + two books agree" if agreements > 1 else "")
    if p["mean"] > 0 and all_pos:
        return "measured, all splits; paid by the tail (hit below 45%)"
    if p["mean"] > 0:
        return "weak: positive overall, a split negative"
    return "negative prior"


# -------------------------------------------------------------- candidates ---

def _snap(name):
    p, st = snapshots.read(name)
    if p is None or not p.get("ok") or st in ("absent", "unreadable", "wrong_version", "incomplete"):
        return None, f"{name} {st if p is None else 'blocked: ' + str(p.get('blocked'))}"
    return p, None


def candidates(now=None):
    """Every name a measured book holds right now, with its sources and the signal numbers.
    The stress snapshot maps to stress_vix25 in regime and stress_all out of it."""
    out, notes, seen = {}, [], set()
    for sig, cfg in SOURCES.items():
        if cfg["snapshot"] in seen:
            continue
        seen.add(cfg["snapshot"])
        p, err = _snap(cfg["snapshot"])
        if err:
            notes.append(err)
            continue
        key = sig
        if cfg["snapshot"] == "stress_reversal_snapshot.json":
            key = "stress_vix25" if p.get("regime_on") else "stress_all"
        for pk in p.get("picks") or []:
            tk = pk.get("ticker")
            if not tk:
                continue
            c = out.setdefault(tk, {"ticker": tk, "sources": [], "signal_detail": {}})
            c["sources"].append(key)
            c["signal_detail"][key] = {k: pk.get(k) for k in ("sue", "sue_pct", "rank", "cohort", "resid_mom", "mom12_1", "ret1m", "ret1w", "bb_pos", "report_date", "close", "spot")}
    return list(out.values()), notes


def context_for(tk, now=None):
    """The reasoning stack around a name: macro theme, catalysts inside the hold, vol read,
    research bullets. Every element names its source; a missing one says so."""
    now = now or _now()
    ctx = {"macro": None, "macro_side": 0, "events": [], "earnings": None, "research": None, "uw": None}
    try:
        import desk_notes
        ov, st = desk_notes.overlay()
        if ov and st in ("ok", "stale"):
            hits = desk_notes.theme_for(ov, tk)
            if hits:
                ctx["macro"] = [{"theme": t.get("label"), "stance": t.get("stance"), "side": s, "why": t.get("why"), "updated": t.get("updated")} for t, s in hits]
                tot = sum(s for _, s in hits)
                ctx["macro_side"] = int(tot > 0) - int(tot < 0)
            ctx["macro_as_of"] = ov.get("as_of")
            ctx["regime_line"] = ov.get("regime_line")
    except Exception as e:                                    # noqa: BLE001
        ctx["macro_error"] = str(e)[:80]
    try:
        import macro_calendar
        ctx["events"] = [{"date": e["date"], "label": e["label"], "days_away": e["days_away"], "importance": e.get("importance")}
                         for e in macro_calendar.upcoming(within_days=100, now=now)]
    except Exception as e:                                    # noqa: BLE001
        ctx["events_error"] = str(e)[:80]
    try:
        import market_basis
        ne = market_basis.next_earnings(tk)
        if ne:
            ctx["earnings"] = ne if isinstance(ne, dict) else {"date": str(ne)}
    except Exception as e:                                    # noqa: BLE001
        ctx["earnings_error"] = str(e)[:80]
    try:
        import earnings_vol
        v = earnings_vol.vrp(tk)
        if v:
            ctx["uw"] = {"vrp": v}
    except Exception:                                         # noqa: BLE001
        pass
    try:
        r = snapshots.read(RESEARCH_FILE)[0] or {}
        item = (r.get("names") or {}).get(tk)
        if item:
            ctx["research"] = item
            ctx["research_as_of"] = r.get("as_of")
    except Exception:                                         # noqa: BLE001
        pass
    return ctx


# --------------------------------------------------------------- structure ---

def _spot(tk):
    import weekly_swing as ws
    try:
        h = ws._yf().Ticker(tk).fast_info
        s = float(h.get("lastPrice") or h.get("last_price") or 0) or None
        if s:
            return s
    except Exception:                                         # noqa: BLE001
        pass
    try:
        import price_cache
        d = price_cache.history([tk], days=10, refresh_first=False).get(tk)
        return float(d["close"].iloc[-1]) if d is not None and len(d) else None
    except Exception:                                         # noqa: BLE001
        return None


def _expiries(tk):
    import weekly_swing as ws
    try:
        return list(ws._yf().Ticker(tk).options or [])
    except Exception:                                         # noqa: BLE001
        return []


def _pick_expiry(exps, target_dte, earnings_date, now):
    """Nearest listed expiry to the target; if the name reports inside the window the expiry
    BEFORE the print is preferred when it still covers at least 60% of the horizon (the drift
    was measured without the next print inside it)."""
    today = now.date()
    cands = []
    for e in exps:
        try:
            d = datetime.strptime(e, "%Y-%m-%d").date()
        except ValueError:
            continue
        dte = (d - today).days
        if dte < max(7, int(target_dte * 0.5)) or dte > int(target_dte * 1.7):
            continue
        cands.append((e, dte))
    if not cands:
        return None, None, None
    note = None
    if earnings_date:
        try:
            ed = datetime.strptime(str(earnings_date)[:10], "%Y-%m-%d").date()
            before = [(e, dte) for e, dte in cands if datetime.strptime(e, "%Y-%m-%d").date() < ed]
            if before and before[-1][1] >= target_dte * 0.6:
                e, dte = min(before, key=lambda x: abs(x[1] - target_dte))
                return e, dte, f"expiry kept BEFORE the {ed} earnings print; the drift was measured without the next print inside the hold"
            note = f"the {ed} print falls inside the hold: the expiry covers it and the card says so"
        except ValueError:
            pass
    e, dte = min(cands, key=lambda x: abs(x[1] - target_dte))
    return e, dte, note


def _delta_strike(df, target_delta, spot, is_call, dte=30):
    """The listed strike nearest a target delta: weekly_swing's helper (the chain's own
    implied vols through idt.bs), with a moneyness proxy when the chain carries no IV."""
    import weekly_swing as ws
    k = ws._delta_strike(df, spot, dte, target_delta, call=is_call)
    if k is not None:
        return k
    from math import erf, log, sqrt
    T = max(dte, 1) / 365.0
    best = None
    for k in sorted(set(float(x) for x in df["strike"].dropna())):
        z = log(spot / k) / (0.35 * sqrt(T))
        nd = 0.5 * (1 + erf(z / sqrt(2)))
        d = nd if is_call else nd - 1
        dist = abs(abs(d) - target_delta)
        if best is None or dist < best[0]:
            best = (dist, k)
    return best[1] if best else None


def _shares(tk, sessions, now):
    spot = _spot(tk)
    if not spot:
        return None, "no spot price"
    end = _add_sessions(now.date(), sessions)
    return {"name": "shares", "label": STRUCT_LABEL["shares"], "legs": [{"right": "S", "strike": round(spot, 2), "price": round(spot, 2), "buying": True, "qty": 1}],
            "legs_text": "Buy shares at the next open", "net": round(spot, 2), "is_debit": True, "max_risk": round(spot, 2), "max_reward": None,
            "rr": None, "cost_pct": SHARES_COST_PCT, "breakevens": [round(spot, 2)], "width": None, "multiplier": 1,
            "expiry": end.isoformat(), "dte": (end - now.date()).days, "expiry_note": None, "spot": round(spot, 2), "iv_atm": None}, None


def price_structure(tk, struct, dte_target, earnings_date=None, now=None, sessions=None):
    """Build and price one structure off the live ladder. Returns (bits, refusal). Money
    fields are DOLLARS per contract (per share for shares)."""
    now = now or _now()
    if struct == "shares":
        return _shares(tk, sessions or 21, now)
    import weekly_swing as ws
    import weekly_structures as st
    exps = _expiries(tk)
    if not exps:
        return None, "no listed expiries"
    exp, dte, exp_note = _pick_expiry(exps, dte_target, earnings_date, now)
    if not exp:
        return None, f"no expiry within the {dte_target}-day window"
    calls, puts = ws._chain(tk, exp)
    if calls is None or puts is None or not len(calls):
        return None, f"chain for {exp} unreadable"
    spot = _spot(tk)
    if not spot:
        return None, "no spot price"
    cl, pu = ws._side_ladder(calls), ws._side_ladder(puts)

    def quote(right, strike, buying):
        df = calls if right == "C" else puts
        lg, err = ws._leg_quote(df, strike, buying)
        if lg and (lg.get("oi") or 0) < MIN_OI:
            return None, f"{strike:g} has {lg.get('oi')} open interest (limit {MIN_OI})"
        return lg, err

    if struct in ("call_debit_70_40", "call_debit_50_25"):
        d1, d2 = (0.70, 0.40) if struct.endswith("70_40") else (0.50, 0.25)
        k1 = ws._snap(cl, _delta_strike(calls, d1, spot, True, dte))
        k2 = ws._snap(cl, _delta_strike(calls, d2, spot, True, dte), {k1})
        spec, name = [("C", k1, True, 1), ("C", k2, False, 1)], "call_debit"
    elif struct == "put_credit_30_15":
        k1 = ws._snap(pu, _delta_strike(puts, 0.30, spot, False, dte))
        k2 = ws._snap(pu, _delta_strike(puts, 0.15, spot, False, dte), {k1})
        spec, name = [("P", k1, False, 1), ("P", k2, True, 1)], "put_credit"
    elif struct in ("long_call_80", "long_call_60"):
        k1 = ws._snap(cl, _delta_strike(calls, 0.80 if struct.endswith("80") else 0.60, spot, True, dte))
        spec, name = [("C", k1, True, 1)], "long_call"
    else:
        return None, f"{struct}: no builder"
    if any(s[1] is None for s in spec):
        return None, f"{struct}: a strike could not be placed on the listed ladder"
    if name == "long_call":
        lg, err = quote("C", spec[0][1], True)
        if err:
            return None, f"{struct}: {err}"
        net = lg["price"]
        cost_pct = 2 * lg["half_spread"] / net * 100 if net else 999
        if cost_pct > MAX_COST_PCT:
            return None, f"{struct}: round-trip spread is {cost_pct:.0f}% of the premium (limit {MAX_COST_PCT:.0f}%)"
        bits = {"name": struct, "legs": [{**lg, "right": "C", "qty": 1, "buying": True}], "legs_text": f"Buy {spec[0][1]:g}C", "net": round(net, 2),
                "is_debit": True, "max_risk": round(net * 100, 0), "max_reward": None, "rr": None, "cost_pct": round(cost_pct, 1),
                "breakevens": [round(spec[0][1] + net, 2)], "width": None}
    else:
        bits, err = st.assemble(name, spec, quote, MAX_COST_PCT)
        if err:
            return None, f"{struct}: {err}"
        bits["max_risk"] = round(bits["max_risk"] * 100, 0)
        bits["max_reward"] = round(bits["max_reward"] * 100, 0) if bits.get("max_reward") is not None and math.isfinite(bits["max_reward"]) else None
    bits.update({"name": struct, "label": STRUCT_LABEL[struct], "multiplier": 100, "expiry": exp, "dte": dte, "expiry_note": exp_note,
                 "spot": round(spot, 2), "iv_atm": ws._atm_iv(calls, puts, spot)})
    return bits, None


# ------------------------------------------------------------------- issue ---

def _con():
    try:
        con = _db.connect(DB)
    except sqlite3.Error:
        return None
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS plays (
        id INTEGER PRIMARY KEY, issued TEXT NOT NULL, ticker TEXT NOT NULL, sources TEXT, structure TEXT, legs_text TEXT,
        legs_json TEXT, expiry TEXT, dte INTEGER, spot REAL, net REAL, max_risk REAL, max_reward REAL, cost_pct REAL,
        horizon_sessions INTEGER, horizon_end TEXT, expected_pct REAL, expected_usd REAL, hit REAL, payoff REAL, confidence TEXT,
        reasoning_json TEXT, status TEXT NOT NULL DEFAULT 'open', cur_net REAL, pnl_pct REAL, pnl_usd REAL, spot_cur REAL,
        updated TEXT, closed TEXT, close_why TEXT, contracts INTEGER, multiplier INTEGER DEFAULT 100)""")
    return con


def _issued_this_week(con, now):
    monday = (now.date() - timedelta(days=now.weekday())).isoformat()
    return con.execute("SELECT COUNT(*) FROM plays WHERE issued >= ?", (monday,)).fetchone()[0]


def _open_tickers(con):
    return {r[0] for r in con.execute("SELECT ticker FROM plays WHERE status='open'")}


def _add_sessions(d, n):
    k = 0
    while k < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            k += 1
    return d


def _timeline(now, bits, sessions, horizon_end, events, earnings, is_shares, research_catalysts=None):
    t = [{"when": _add_sessions(now.date(), 1).isoformat(),
          "what": "enter at the open" + ("; the ledger fills at that print" if is_shares else ": every leg at the ask when bought, the bid when sold; the ledger records that fill")}]
    mid = _add_sessions(now.date(), sessions // 2).isoformat()
    t.append({"when": mid, "what": "checkpoint: is the thesis intact (the signal's own numbers, the macro theme, no veto)? no price stop" + ("" if is_shares else " on a debit — measured to hurt")})
    for e in events or []:
        if e.get("importance") == "high" or "FOMC" in str(e.get("label")) or "CPI" in str(e.get("label")) or "jobs" in str(e.get("label")).lower():
            t.append({"when": e["date"], "what": f"macro: {e['label']}", "kind": "macro"})
    if earnings and earnings.get("date"):
        ed = str(earnings["date"])[:10]
        t.append({"when": ed, "what": "this name reports" + (" (inside the hold; the card carries it)" if ed <= horizon_end else " (after the exit)")})
    for cat in research_catalysts or []:
        t.append({"when": cat["date"], "what": f"catalyst (research, sourced): {cat['label']}", "kind": "research"})
    t.append({"when": horizon_end, "what": f"exit: the measured horizon ({sessions} sessions) ends; " + ("sell at the open" if is_shares else "close at the bid/ask, or let expiry settle if it is within days")})
    if not is_shares and bits["expiry"] != horizon_end:
        t.append({"when": bits["expiry"], "what": "expiry"})
    return sorted(t, key=lambda x: x["when"])


def _option_alt(tk, sig, pri, dte, earnings_date, now):
    """The option expression of a shares play, priced off the ladder with its own measured
    number, so the reader can compare the two with the costs in front of them."""
    last = "no option expression could be priced"
    for struct in OPTION_ALTS:
        bits, err = price_structure(tk, struct, dte, earnings_date, now)
        if bits:
            p = pri.get((sig, struct))
            return {"structure": struct, "label": STRUCT_LABEL[struct], "legs_text": bits["legs_text"], "net": bits["net"], "expiry": bits["expiry"],
                    "dte": bits["dte"], "max_risk": bits["max_risk"], "max_reward": bits["max_reward"], "cost_pct": bits["cost_pct"],
                    "breakevens": bits.get("breakevens"), "iv_atm": bits.get("iv_atm"), "prior": p,
                    "verdict": (f"measured {p['mean'] * 100:+.0f}% of risk per trade on this signal (median {p['median'] * 100:+.0f}%, hit {p['hit']:.2f}, n {p['n']}); "
                                f"the bid-ask alone is {p['cost_pct']:.0f}% of risk" if p else "unmeasured on this signal")}
        last = err
    return {"refused": last}


def build_play(c, pri, now):
    """One candidate -> a priced, reasoned card or a refusal with its reason."""
    tk = c["ticker"]
    sig = sorted(c["sources"], key=lambda s: -SOURCES[s]["sessions"])[0]       # the longest-horizon measured signal leads
    struct, p = best_structure(sig, pri)
    if struct is None:
        return None, {"ticker": tk, "sources": c["sources"], "why": f"no expression of the {sig} signal measured positive"}
    ctx = context_for(tk, now)
    vetoes = []
    if ctx.get("macro_side", 0) < 0:
        vetoes.append("the desk notes argue AGAINST this name: " + "; ".join(m["theme"] for m in ctx["macro"] if m["side"] < 0))
    ed = (ctx.get("earnings") or {}).get("date")
    bits, err = price_structure(tk, struct, SOURCES[sig]["dte"], ed, now, sessions=SOURCES[sig]["sessions"])
    if err and struct != "shares":
        sh = pri.get((sig, "shares"))
        if sh and sh["mean"] > 0:
            struct, p = "shares", sh
            bits, err = price_structure(tk, "shares", SOURCES[sig]["dte"], ed, now, sessions=SOURCES[sig]["sessions"])
    if err:
        return None, {"ticker": tk, "sources": c["sources"], "why": err}
    for e in ctx.get("events") or []:
        if e["date"] == bits["expiry"] and e.get("importance") == "high":
            vetoes.append(f"{e['label']} lands on the expiry {e['date']}")
    horizon_end = _add_sessions(now.date(), SOURCES[sig]["sessions"]).isoformat()
    # THE RESEARCH FEEDS IN HERE, and only downward. The morning session's sourced catalysts
    # inside the hold go on the timeline; its "against" list lowers the rank between equal
    # priors and is printed on the card; a lock-up expiry or a binary regulatory date inside
    # the hold is a veto, because the measured drift was never measured through one.
    res = ctx.get("research") or {}
    against = [a for a in (res.get("against") or []) if a]
    r_cats = []
    for cat in res.get("catalysts") or []:
        d = str(cat.get("date") or "")[:10]
        if len(d) == 10 and d[:4].isdigit() and now.date().isoformat() < d <= horizon_end:
            r_cats.append({"date": d, "label": cat.get("label") or "catalyst", "url": cat.get("url")})
            low = (cat.get("label") or "").lower()
            if any(k in low for k in ("lock-up", "lockup", "lock up", "fda", "pdufa", "adcom", "court ruling", "verdict")):
                vetoes.append(f"research: {cat.get('label')} on {d}, inside the hold")
    conf = confidence(p, len(c["sources"]), vetoes)
    if against and not vetoes:
        conf += f" · research flags {len(against)} concern{'s' if len(against) > 1 else ''}"
    exp_pct = p["mean"] * 100 if p else None
    contracts = max(1, int(RISK_PER_PLAY_USD // bits["max_risk"])) if bits["max_risk"] else 1
    is_shares = struct == "shares"
    option_alt = _option_alt(tk, sig, pri, SOURCES[sig]["dte"], ed, now) if is_shares else None
    reasoning = {
        "signal": {"source": sig, "measured": SOURCES[sig]["measured"], "detail": c["signal_detail"].get(sig), "also_in": [s for s in c["sources"] if s != sig]},
        "structure": {"why": STRUCT_LABEL[struct], "prior": p, "cost_pct": bits["cost_pct"], "iv_atm": bits.get("iv_atm"), "expiry_note": bits.get("expiry_note"),
                      "measurement": ("shares are the expression that measured positive for this signal; every option structure tested on it lost per dollar of risk after the round trip (play_structures.md)"
                                      if is_shares else "this option cell measured positive in every split with a median above −35%")},
        "option_alt": option_alt,
        "macro": {"themes": ctx.get("macro"), "regime_line": ctx.get("regime_line"), "as_of": ctx.get("macro_as_of")},
        "events": [e for e in (ctx.get("events") or []) if e["days_away"] <= bits["dte"]],
        "earnings": ctx.get("earnings"),
        "vol": ctx.get("uw"),
        "research": ctx.get("research"),
        "research_catalysts": r_cats,
        "vetoes": vetoes,
    }
    reasoning["timeline"] = _timeline(now, bits, SOURCES[sig]["sessions"], horizon_end, reasoning["events"], ctx.get("earnings"), is_shares, r_cats)
    reasoning["card"] = {"structure_label": STRUCT_LABEL[struct], "is_debit": bits["is_debit"], "max_reward": bits["max_reward"], "rr": bits.get("rr"),
                         "breakevens": bits.get("breakevens"), "width": bits.get("width"), "spot": bits["spot"], "contracts": contracts,
                         "median_pct": round(p["median"] * 100, 1) if p else None, "p25_pct": round(p["p25"] * 100, 1) if p else None,
                         "p75_pct": round(p["p75"] * 100, 1) if p else None, "splits": p["splits"] if p else None, "prior_n": p["n"] if p else None,
                         "top5_share": p.get("top5_share") if p else None, "sources": c["sources"], "lead_source": sig, "is_shares": is_shares,
                         "unit": "share" if is_shares else "contract"}
    play = {"ticker": tk, "sources": c["sources"], "lead_source": sig, "structure": struct, "structure_label": STRUCT_LABEL[struct],
            "legs_text": bits["legs_text"], "legs": bits["legs"], "expiry": bits["expiry"], "dte": bits["dte"], "spot": bits["spot"],
            "net": bits["net"], "is_debit": bits["is_debit"], "max_risk": bits["max_risk"], "max_reward": bits["max_reward"], "rr": bits.get("rr"),
            "cost_pct": bits["cost_pct"], "breakevens": bits.get("breakevens"), "horizon_sessions": SOURCES[sig]["sessions"], "horizon_end": horizon_end,
            "multiplier": bits.get("multiplier", 100),
            "expected_pct": round(exp_pct, 1) if exp_pct is not None else None,
            "expected_usd": round(exp_pct / 100 * bits["max_risk"] * contracts, 0) if exp_pct is not None else None,
            "contracts": contracts, "risk_usd": round(bits["max_risk"] * contracts, 0),
            "hit": p["hit"] if p else None, "payoff": p["payoff"] if p else None, "confidence": conf, "reasoning": reasoning,
            "timeline": reasoning["timeline"], "card": reasoning["card"],
            "research_concerns": len(against),
            "score": (p["mean"] if p else -1) * (1.25 if len(c["sources"]) > 1 else 1.0) - (10 if vetoes else 0) - 0.002 * len(against)}
    return play, None


def issue(now=None, force=False):
    """Issue up to N_PER_WEEK new plays. Returns the snapshot payload."""
    now = now or _now()
    con = _con()
    pri = priors()
    cands, notes = candidates(now)
    out = {"as_of": _stamp(), "ok": True, "priors_available": bool(pri), "notes": notes, "issued": [], "considered": [], "refused": []}
    if con is None:
        out.update(ok=False, blocked="ledger database could not be opened")
        snapshots.write(OUT, out)
        return out
    already = _issued_this_week(con, now)
    room = max(0, N_PER_WEEK - already)
    due = force or (now.weekday() in ISSUE_WEEKDAYS)
    open_tk = _open_tickers(con)
    if not cands:
        out["note"] = "no measured book holds a candidate right now: " + "; ".join(notes)
    built = []
    for c in sorted(cands, key=lambda c: (-len(c["sources"]), c["ticker"]))[:40]:
        if c["ticker"] in open_tk:
            out["refused"].append({"ticker": c["ticker"], "why": "already an open play"})
            continue
        play, ref = build_play(c, pri, now)
        if ref:
            out["refused"].append(ref)
        else:
            built.append(play)
    built.sort(key=lambda p: -p["score"])
    out["considered"] = [{k: p[k] for k in ("ticker", "sources", "structure", "structure_label", "legs_text", "expected_pct", "hit", "confidence", "cost_pct", "score", "research_concerns")} for p in built]
    if due and room:
        for p in [b for b in built if not b["reasoning"]["vetoes"] and (b["expected_pct"] or 0) > 0][:room]:
            con.execute("""INSERT INTO plays (issued, ticker, sources, structure, legs_text, legs_json, expiry, dte, spot, net, max_risk, max_reward,
                           cost_pct, horizon_sessions, horizon_end, expected_pct, expected_usd, hit, payoff, confidence, reasoning_json, contracts, multiplier)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (_stamp(), p["ticker"], ",".join(p["sources"]), p["structure"], p["legs_text"], json.dumps(p["legs"], default=str), p["expiry"], p["dte"],
                         p["spot"], p["net"], p["max_risk"], p["max_reward"], p["cost_pct"], p["horizon_sessions"], p["horizon_end"], p["expected_pct"],
                         p["expected_usd"], p["hit"], p["payoff"], p["confidence"], json.dumps(p["reasoning"], default=str), p["contracts"], p["multiplier"]))
            out["issued"].append(p)
        con.commit()
        if out["issued"]:
            _notify("Plays desk: new plays issued (paper)", ", ".join(f"{p['ticker']} {p['structure_label']}" for p in out["issued"]))
    out["issue_window"] = {"due_today": due, "issued_this_week": already + len(out["issued"]), "cap": N_PER_WEEK,
                           "issue_days": [("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[d] for d in ISSUE_WEEKDAYS]}
    out["priors_table"] = sorted([{"signal": k[0], "struct": k[1], "label": STRUCT_LABEL.get(k[1], k[1]), **v} for k, v in pri.items()],
                                 key=lambda r: (r["signal"], -r["mean"]))
    out["sources"] = {k: {"sessions": v["sessions"], "dte": v["dte"], "measured": v["measured"]} for k, v in SOURCES.items()}
    out["open"] = open_plays(con)
    con.close()
    snapshots.write(OUT, out)
    return out


# --------------------------------------------------------------- discretionary ---

def book_manual(ticker, legs, expiry, net, max_risk, horizon_end, label, why, timeline, contracts=1, multiplier=100,
                expected_pct=None, hit=None, sources="discretionary", now=None):
    """Record a play the operator asked for by hand, so it is scored like every other card.
    `legs` is [{right, strike, price, buying, qty}] at the fills asked (ask bought, bid sold);
    `max_risk` and `net` are per contract in dollars and per share respectively, like the
    engine's own rows. Confidence is 'unmeasured' by construction: nothing here came from a
    prior. Returns the row id. Places nothing."""
    now = now or _now()
    con = _con()
    if con is None:
        return None
    reasoning = {"signal": {"source": sources, "measured": why, "detail": None, "also_in": []},
                 "structure": {"why": label, "prior": None, "cost_pct": None, "iv_atm": None, "expiry_note": None, "measurement": "discretionary: no measured prior"},
                 "option_alt": None, "macro": {"themes": None}, "events": [], "earnings": None, "vol": None, "research": None,
                 "research_catalysts": [], "vetoes": [], "timeline": sorted(timeline, key=lambda t: t["when"]),
                 "card": {"structure_label": label, "is_debit": net > 0, "max_reward": None, "rr": None, "breakevens": None, "width": None,
                          "spot": _spot(ticker), "contracts": contracts, "median_pct": None, "p25_pct": None, "p75_pct": None, "splits": None,
                          "prior_n": None, "top5_share": None, "sources": [sources], "lead_source": sources, "is_shares": multiplier == 1,
                          "unit": "share" if multiplier == 1 else "contract"}}
    legs_text = " / ".join(f"{'Buy' if lg['buying'] else 'Sell'} {lg['strike']:g}{lg['right']}" for lg in legs)
    cur = con.execute("""INSERT INTO plays (issued, ticker, sources, structure, legs_text, legs_json, expiry, dte, spot, net, max_risk, max_reward,
                         cost_pct, horizon_sessions, horizon_end, expected_pct, expected_usd, hit, payoff, confidence, reasoning_json, contracts, multiplier)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (_stamp(), ticker, sources, "discretionary", legs_text, json.dumps(legs), expiry,
                       (datetime.strptime(expiry, "%Y-%m-%d").date() - now.date()).days, reasoning["card"]["spot"], net, max_risk, None, None, None,
                       horizon_end, expected_pct, round(expected_pct / 100 * max_risk * contracts, 0) if expected_pct is not None else None, hit, None,
                       "unmeasured: asked for by hand, scored like the rest", json.dumps(reasoning, default=str), contracts, multiplier))
    con.commit()
    rid = cur.lastrowid
    con.close()
    return rid


# ------------------------------------------------------------------ ledger ---

def open_plays(con=None):
    own = con is None
    con = con or _con()
    if con is None:
        return []
    rows = [dict(r) for r in con.execute("SELECT * FROM plays ORDER BY issued DESC LIMIT 200").fetchall()]
    for r in rows:
        try:
            r["reasoning"] = json.loads(r.pop("reasoning_json") or "{}")
            r["legs"] = json.loads(r.pop("legs_json") or "[]")
        except ValueError:
            r["reasoning"], r["legs"] = {}, []
    if own:
        con.close()
    return rows


def mark(now=None):
    """Re-price every open play at exit prices (sell the long at the bid, buy the short back
    at the ask; shares at the last print), close at the horizon end or expiry. Never raises."""
    import weekly_swing as ws
    now = now or _now()
    con = _con()
    if con is None:
        return {"ok": False}
    marked = closed = 0
    today = now.date().isoformat()
    for r in con.execute("SELECT * FROM plays WHERE status='open'").fetchall():
        r = dict(r)
        try:
            legs = json.loads(r["legs_json"] or "[]")
            mult = r.get("multiplier") or 100
            spot = _spot(r["ticker"])
            if r["structure"] == "shares":
                if not spot:
                    continue
                cur = spot
            else:
                calls, puts = ws._chain(r["ticker"], r["expiry"])
                cur, ok = 0.0, True
                for lg in legs:
                    df = calls if lg["right"] == "C" else puts
                    row = ws._row(df, lg["strike"]) if df is not None else None
                    if row is None:
                        ok = False
                        break
                    px = float(row.get("bid") or 0) if lg["buying"] else float(row.get("ask") or 0)
                    cur += (1 if lg["buying"] else -1) * lg["qty"] * px
                if not ok:
                    continue
            n = r["contracts"] or 1
            pnl = (cur - r["net"]) * mult * n
            risk = (r["max_risk"] or 0) * n
            done = today >= r["horizon_end"] or (r["structure"] != "shares" and today >= r["expiry"])
            con.execute("UPDATE plays SET cur_net=?, pnl_usd=?, pnl_pct=?, spot_cur=?, updated=?, status=?, closed=?, close_why=? WHERE id=?",
                        (round(cur, 2), round(pnl, 0), round(pnl / risk * 100, 1) if risk else None, spot, _stamp(),
                         "closed" if done else "open", _stamp() if done else None,
                         ("horizon reached" if today >= r["horizon_end"] else "expiry") if done else None, r["id"]))
            marked += 1
            closed += int(done)
        except Exception:                                     # noqa: BLE001
            continue
    con.commit()
    con.close()
    return {"ok": True, "marked": marked, "closed": closed}


def scorecard():
    con = _con()
    if con is None:
        return {}
    cl = [dict(r) for r in con.execute("SELECT * FROM plays WHERE status='closed'").fetchall()]
    op = [dict(r) for r in con.execute("SELECT * FROM plays WHERE status='open'").fetchall()]
    con.close()
    sc = [r for r in cl if r.get("pnl_pct") is not None]
    out = {"n_open": len(op), "n_closed": len(cl)}
    if sc:
        out.update({"hit": round(sum(1 for r in sc if r["pnl_pct"] > 0) / len(sc), 2), "avg_pnl_pct": round(sum(r["pnl_pct"] for r in sc) / len(sc), 1),
                    "pnl_usd": round(sum(r["pnl_usd"] or 0 for r in sc), 0),
                    "promised_vs_delivered": round(sum(r["pnl_pct"] for r in sc) / len(sc) - sum(r["expected_pct"] or 0 for r in sc) / len(sc), 1)})
    if op:
        out["open_pnl_usd"] = round(sum(r.get("pnl_usd") or 0 for r in op), 0)
    return out


if __name__ == "__main__":
    import sys
    if "--mark" in sys.argv:
        print(mark())
    elif "--priors" in sys.argv:
        for k, v in sorted(priors().items()):
            print(k, {x: v[x] for x in ("n", "mean", "median", "hit", "payoff", "splits", "top5_share", "cost_pct")})
    else:
        o = issue(force="--force" in sys.argv)
        print(json.dumps({k: o.get(k) for k in ("ok", "priors_available", "notes", "issue_window")}, default=str))
        for p in o.get("considered", [])[:12]:
            print(" ", p)
        print(" issued:", [(p["ticker"], p["legs_text"], p["expected_pct"], p["confidence"]) for p in o.get("issued", [])])
        print(" refused:", len(o.get("refused", [])), o.get("refused", [])[:6])
