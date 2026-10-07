"""memecoin_book.py — the memecoin paper book: ONE pre-registered rule from the first GMGN
copy-trade replay, booked on every qualifying signal at the price a copier gets, with a
ledger. PAPER ONLY. Holds no key, sends nothing.

THE RULE, fixed on 2026-10-07 from the first 325 settled replays (02_findings/memecoins.md):
    copy every SMART-MONEY buy (GMGN source `smartmoney`, not KOL) on SOLANA,
    fill at the first 30-second candle close at or after the leader's timestamp + 60 s,
    sell at the first close at or after fill + 300 s,
    $100 notional, costs 1% venue + 0.5% router + 2% slippage EACH WAY (7% round trip).
Why this rule and not another: in the replay, KOL buys lost at every horizon; smart-money
buys were +6-8% net at five minutes (hit 0.27, payoff ~4) and negative by an hour; the two
halves disagreed (A −12%, B +1%). So the book books exactly this, every signal, and the
ledger decides. It is NOT a recommendation: the measured expectation is inside the noise.

RULE B (added 2026-10-07 from the pump.fun birth study, the one cell of ~100 above water):
    a mint whose curve price rose >= 50% between the +1 and +2 minute marks; buy at the
    +2 minute curve price (the trader's own impact charged exactly), sell at the +10 minute
    curve price; $100. Settled straight from pumpfun.db's RPC curve readings, no API call.
    The study's +13% on 51 mints was measured from the +1 price (trap 6); this book measures
    from +2 and its first 49 signals were -45% net, hit 0.06. Kept running as the record.

HOW. Every RUN_S seconds: every smartmoney/sol BUY in gmgn.db older than SETTLE_AFTER_S
and not yet booked gets one 30-second kline pull covering [ts-30, ts+480]; the fill and the
exit are read from it; a trade with no fill candle is recorded as `unfilled`, never
dropped. Everything else — hit rate, payoff, net P&L, by leader tag, by hour — is read from
the ledger by the Markets panel and by `05_studies/memecoin_gmgn_score.py`.
"""
import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone

from idt import db as _db
from idt import paths, snapshots

DB = paths.state("memecoin_book.db")
SRC_DB = paths.state("gmgn.db")
OUT = "memecoin_book_snapshot.json"
CLI = "gmgn-cli"
RUN_S = 300
SETTLE_AFTER_S = 480
LAG_S = 60
HOLD_S = 300
NOTIONAL = 100.0
COST_SIDE = 0.01 + 0.005 + 0.02
RULE = {"source": "smartmoney", "chain": "sol", "lag_s": LAG_S, "hold_s": HOLD_S, "notional": NOTIONAL, "cost_side": COST_SIDE,
        "fixed_on": "2026-10-07", "basis": "first 325 settled GMGN replays: smart-money +6-8% net at 5 min (hit 0.27, payoff ~4), halves disagree"}


def _now():
    return time.time()


def con():
    c = _db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        tx TEXT PRIMARY KEY, booked REAL, signal_ts REAL, token TEXT, symbol TEXT, maker TEXT, tags TEXT, launchpad TEXT,
        lead_px REAL, fill_ts REAL, fill_px REAL, exit_ts REAL, exit_px REAL, gross REAL, net REAL, pnl_usd REAL, status TEXT, err TEXT)""")
    return c


def kline(addr, t_from, t_to):
    r = subprocess.run([CLI, "market", "kline", "--chain", "sol", "--address", addr, "--resolution", "30s",
                        "--from", str(int(t_from)), "--to", str(int(t_to)), "--raw"], capture_output=True, text=True, timeout=40)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError((r.stderr or r.stdout or "no output")[:160])
    bars = [(float(k["time"]) / 1000.0, float(k["close"])) for k in json.loads(r.stdout).get("list") or []]
    return sorted(bars)


def first_close_at_or_after(bars, t, tol=120):
    for bt, c in bars:
        if bt >= t:
            return (bt, c) if bt - t <= tol else (None, None)
    return None, None


def settle(bars, signal_ts):
    """(fill_ts, fill_px, exit_ts, exit_px, gross, net) from the bars, or None if no fill."""
    fts, fpx = first_close_at_or_after(bars, signal_ts + LAG_S)
    if not fpx:
        return None
    ets, epx = first_close_at_or_after(bars, fts + HOLD_S)
    if not epx:
        return None
    gross = epx / fpx - 1
    net = (1 + gross) * (1 - COST_SIDE) ** 2 - 1
    return fts, fpx, ets, epx, gross, net


def run_once(now=None, max_new=40):
    now = now or _now()
    c = con()
    src = sqlite3.connect(SRC_DB)
    src.row_factory = sqlite3.Row
    cands = src.execute("""SELECT tx, ts, token, symbol, maker, tags, launchpad, price_usd FROM smart_trades
                           WHERE src='smartmoney' AND side='buy' AND COALESCE(chain,'sol')='sol' AND token IS NOT NULL
                             AND ts <= ? AND ts >= ? ORDER BY ts""", (now - SETTLE_AFTER_S, now - 6 * 3600)).fetchall()
    src.close()
    booked = filled = 0
    for r in cands:
        if booked >= max_new:
            break
        if c.execute("SELECT 1 FROM trades WHERE tx=?", (r["tx"],)).fetchone():
            continue
        booked += 1
        try:
            bars = kline(r["token"], r["ts"] - 30, r["ts"] + SETTLE_AFTER_S)
            s = settle(bars, r["ts"])
        except Exception as e:                                # noqa: BLE001
            c.execute("INSERT OR IGNORE INTO trades (tx, booked, signal_ts, token, symbol, maker, tags, launchpad, lead_px, status, err) "
                      "VALUES (?,?,?,?,?,?,?,?,?,'error',?)", (r["tx"], now, r["ts"], r["token"], r["symbol"], r["maker"], r["tags"], r["launchpad"], r["price_usd"], str(e)[:160]))
            continue
        if s is None:
            c.execute("INSERT OR IGNORE INTO trades (tx, booked, signal_ts, token, symbol, maker, tags, launchpad, lead_px, status) "
                      "VALUES (?,?,?,?,?,?,?,?,?,'unfilled')", (r["tx"], now, r["ts"], r["token"], r["symbol"], r["maker"], r["tags"], r["launchpad"], r["price_usd"]))
            continue
        fts, fpx, ets, epx, gross, net = s
        c.execute("INSERT OR IGNORE INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'closed',NULL)",
                  (r["tx"], now, r["ts"], r["token"], r["symbol"], r["maker"], r["tags"], r["launchpad"], r["price_usd"],
                   fts, fpx, ets, epx, gross, net, NOTIONAL * net))
        filled += 1
        time.sleep(0.5)
    c.commit()
    c.close()
    try:
        wave = run_wave_once(now)
    except Exception as e:                                    # noqa: BLE001
        wave = {"error": str(e)[:120]}
    out = {"ok": True, "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "rule": RULE, "booked_this_run": booked,
           "filled_this_run": filled, "ledger": ledger(), "wave_rule": {"signal": f"curve price +{int(WAVE_MIN_R01*100)}% between +1 and +2 min",
           "entry": "+2 min curve price", "exit": "+10 min curve price", "notional": NOTIONAL, "fixed_on": "2026-10-07",
           "basis": "pump.fun birth study cell (+13% from the +1 price) was trap 6; from the +2 price the first 49 signals were -45% net, hit 0.06"}, "wave_run": wave, "wave_ledger": wave_ledger()}
    snapshots.write(OUT, out)
    return out


PF_DB = paths.state("pumpfun.db")
WAVE_MIN_R01 = 0.50


def _curve_cost(usd, vsol, sol_usd):
    x = usd / max(sol_usd, 1.0)
    imp = x / max(vsol, 1.0)
    return 1 - (1 - 0.015) ** 2 / ((1 + imp) ** 2)


def _at(ks, age, tol):
    best = min(ks, key=lambda r: abs(r["age_s"] - age), default=None)
    return best if best is not None and abs(best["age_s"] - age) <= tol else None


def run_wave_once(now=None):
    """RULE B, settled from the curve readings already recorded. Idempotent per mint."""
    now = now or _now()
    c = con()
    c.execute("""CREATE TABLE IF NOT EXISTS wave_trades (mint TEXT PRIMARY KEY, booked REAL, created REAL, symbol TEXT, r01 REAL,
                 vsol2 REAL, fill_px REAL, exit_px REAL, gross REAL, net REAL, pnl_usd REAL, status TEXT)""")
    try:
        pf = sqlite3.connect(PF_DB)
        pf.row_factory = sqlite3.Row
        mints = pf.execute("SELECT mint, created, symbol, sol_usd0 FROM mints WHERE created <= ? AND created >= ?",
                           (now - 720, now - 86400)).fetchall()
        booked = filled = 0
        for m in mints:
            if c.execute("SELECT 1 FROM wave_trades WHERE mint=?", (m["mint"],)).fetchone():
                continue
            ks = pf.execute("SELECT age_s, price_sol, vsol FROM marks WHERE mint=? AND price_sol IS NOT NULL ORDER BY age_s", (m["mint"],)).fetchall()
            k1, k2, k10 = _at(ks, 60, 45), _at(ks, 120, 45), _at(ks, 600, 150)
            if k1 is None or k2 is None or not k1["price_sol"] or not k2["price_sol"]:
                continue
            if k10 is None:
                continue                                         # not settled yet; re-tried next run
            r01 = k2["price_sol"] / k1["price_sol"] - 1
            booked += 1
            if r01 < WAVE_MIN_R01:
                c.execute("INSERT OR IGNORE INTO wave_trades (mint, booked, created, symbol, r01, status) VALUES (?,?,?,?,?,'no_signal')",
                          (m["mint"], now, m["created"], m["symbol"], r01))
                continue
            fill, exit_ = k2["price_sol"], (k10["price_sol"] or 0)
            gross = (exit_ / fill - 1) if exit_ > 0 else -1.0
            cost = _curve_cost(NOTIONAL, (k2["vsol"] or 30e9) / 1e9, m["sol_usd0"] or 120.0)
            net = -1.0 if gross <= -0.999 else (1 + gross) * (1 - cost) - 1
            c.execute("INSERT OR IGNORE INTO wave_trades VALUES (?,?,?,?,?,?,?,?,?,?,?,'closed')",
                      (m["mint"], now, m["created"], m["symbol"], r01, (k2["vsol"] or 0) / 1e9, fill, exit_, gross, net, NOTIONAL * net))
            filled += 1
        pf.close()
        c.commit()
    finally:
        c.close()
    return {"scanned": booked, "signals": filled}


def wave_ledger():
    c = con()
    c.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in c.execute("SELECT * FROM wave_trades WHERE status='closed' ORDER BY created DESC LIMIT 400").fetchall()]
        n_scan = c.execute("SELECT COUNT(*) FROM wave_trades").fetchone()[0]
    except sqlite3.Error:
        rows, n_scan = [], 0
    c.close()
    if not rows:
        return {"recent": [], "summary": {"n": 0, "scanned": n_scan}}
    nets = [r["net"] for r in rows]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    mid = sorted(r["created"] for r in rows)[len(rows) // 2]

    def _s(rs):
        if not rs:
            return {"n": 0}
        n = [r["net"] for r in rs]
        return {"n": len(rs), "hit": round(sum(1 for x in n if x > 0) / len(n), 3), "mean_net_pct": round(100 * sum(n) / len(n), 2),
                "pnl_usd": round(sum(r["pnl_usd"] for r in rs), 2)}
    return {"recent": rows[:60], "summary": {"n": len(rows), "scanned": n_scan, "hit": round(len(wins) / len(nets), 3),
                                              "mean_net_pct": round(100 * sum(nets) / len(nets), 2), "median_net_pct": round(100 * sorted(nets)[len(nets) // 2], 2),
                                              "payoff": round((sum(wins) / len(wins)) / (-sum(losses) / len(losses)), 2) if wins and losses else None,
                                              "pnl_usd": round(sum(r["pnl_usd"] for r in rows), 2),
                                              "half_A": _s([r for r in rows if r["created"] < mid]), "half_B": _s([r for r in rows if r["created"] >= mid])}}


def ledger():
    c = con()
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("SELECT * FROM trades ORDER BY signal_ts DESC LIMIT 400").fetchall()]
    allc = [dict(r) for r in c.execute("SELECT net, gross, pnl_usd, signal_ts, tags, launchpad FROM trades WHERE status='closed'").fetchall()]
    n_unf = c.execute("SELECT COUNT(*) FROM trades WHERE status='unfilled'").fetchone()[0]
    n_err = c.execute("SELECT COUNT(*) FROM trades WHERE status='error'").fetchone()[0]
    c.close()

    def _sum(rs):
        if not rs:
            return {"n": 0}
        nets = [r["net"] for r in rs]
        wins = [x for x in nets if x > 0]
        losses = [x for x in nets if x <= 0]
        return {"n": len(rs), "hit": round(len(wins) / len(nets), 3), "mean_net_pct": round(100 * sum(nets) / len(nets), 2),
                "median_net_pct": round(100 * sorted(nets)[len(nets) // 2], 2),
                "payoff": round((sum(wins) / len(wins)) / (-sum(losses) / len(losses)), 2) if wins and losses else None,
                "pnl_usd": round(sum(r["pnl_usd"] for r in rs), 2), "best_pct": round(100 * max(nets), 1), "worst_pct": round(100 * min(nets), 1)}
    summary = _sum(allc)
    if allc:
        mid = sorted(r["signal_ts"] for r in allc)[len(allc) // 2]
        summary["half_A"] = _sum([r for r in allc if r["signal_ts"] < mid])
        summary["half_B"] = _sum([r for r in allc if r["signal_ts"] >= mid])
    summary["unfilled"] = n_unf
    summary["errors"] = n_err
    return {"recent": rows[:60], "summary": summary}


def loop(max_secs=None):
    t0 = time.time()
    while max_secs is None or time.time() - t0 < max_secs:
        try:
            o = run_once()
            s = o["ledger"]["summary"]
            print(f"{datetime.now(timezone.utc):%H:%M:%S} booked={o['booked_this_run']} filled={o['filled_this_run']} | closed={s.get('n')} hit={s.get('hit')} "
                  f"mean_net={s.get('mean_net_pct')}% pnl=${s.get('pnl_usd')} unfilled={s.get('unfilled')}", flush=True)
        except Exception as e:                                # noqa: BLE001
            print(f"{datetime.now(timezone.utc):%H:%M:%S} run failed: {type(e).__name__}: {str(e)[:120]}", flush=True)
        time.sleep(RUN_S)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        print(json.dumps(run_once(), indent=1, default=str)[:2500])
    else:
        loop(float(sys.argv[1]) if len(sys.argv) > 1 else None)
