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
    out = {"ok": True, "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "rule": RULE, "booked_this_run": booked,
           "filled_this_run": filled, "ledger": ledger()}
    snapshots.write(OUT, out)
    return out


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
