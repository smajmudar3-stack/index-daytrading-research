"""index_overlay.py — the paper index sleeve: long the index at BASE_X, add BOOST_X while
VIX is backwardated inside a golden cross. The one growth path this repo measured.

02_findings/goal_feasibility.md rebuilt the signal from ^VIX, ^VIX3M and SPY over 2006–2026:
    front VIX above three-month VIX  AND  SPY 50-day average above its 200-day average
Held 21 days it earned +1.80% a trade (t +2.71, 56 non-overlapping trades, 73% winners),
+1.28 points over the unconditional 21-day return. Traded on its own it is worth 4.7%/yr
because it is in cash 77% of the time. As an OVERLAY — always long, twice the exposure
while it fires — it measured 15.3%/yr against 11.5% for buy-and-hold, with a 59% maximum
drawdown. That configuration is what this module runs, in paper, marked every day.

WHAT IT IS NOT. Not a prediction of direction; a sizing rule on a position that is always
on. Not a fast path: at 15%/yr, $5,000 reaches $50,000 in sixteen years, and the Monte
Carlo in the same finding prices every faster sizing as ruin. It is here so the measured
thing runs and gets judged forward, next to the two books, instead of living in a study.

THE DISCIPLINE. Exposure is decided at the close from data available at the close and
applied to the NEXT session's return -- the same next-open rule every ledger here uses.
Leverage above 1x is charged BORROW_RATE on the borrowed share, daily. The equity curve
starts at START_EQUITY on the first day the module ran and is never re-based.

RECORDS ONLY. Nothing here places an order; `risk_gates.DRY_RUN` stays True.
"""
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from idt import db as _db
from idt import paths, snapshots

ET = ZoneInfo("America/New_York")
OUT = "index_overlay_snapshot.json"
DB = paths.state("index_overlay.db")

BASE_X = 1.0          # always long the index at this multiple
BOOST_X = 1.0         # added while the signal is on: the measured "2x while on" configuration
BORROW_RATE = 0.06    # annual, on the borrowed share, charged daily
START_EQUITY = 5000.0
MEASURED = {"cagr": 0.153, "max_dd": 0.588, "buy_hold_cagr": 0.115,
            "source": "02_findings/goal_feasibility.md, 2006-07 → 2026-06, 56 firings"}


def _now():
    return datetime.now(ET)


def signal_from(vix, vix3m, spy_close):
    """(on, detail) from aligned daily series. Pure, so it is testable.

    `spy_close` needs 200 sessions. Signal = VIX/VIX3M > 1.0 and SMA50 > SMA200 on the
    LAST row. One-sided by construction: the off state votes nothing about direction.
    """
    if len(spy_close) < 200 or len(vix) < 1 or len(vix3m) < 1:
        return None, {"why": "not enough history"}
    ratio = float(vix[-1]) / float(vix3m[-1])
    s50 = sum(spy_close[-50:]) / 50.0
    s200 = sum(spy_close[-200:]) / 200.0
    golden = bool(s50 > s200)
    on = bool(ratio > 1.0 and golden)
    return on, {"vix_ratio": round(ratio, 3), "golden_cross": golden,
                "sma50": round(s50, 2), "sma200": round(s200, 2)}


def target_exposure(on):
    return BASE_X + (BOOST_X if on else 0.0)


def fetch():
    """Daily closes for ^VIX, ^VIX3M, SPY (1y). None on failure."""
    try:
        import yfinance as yf
        px = yf.download(["^VIX", "^VIX3M", "SPY"], period="1y", interval="1d",
                         progress=False, auto_adjust=True)["Close"].dropna()
        return px
    except Exception:                                         # noqa: BLE001
        return None


def _con():
    try:
        con = _db.connect(DB)
    except sqlite3.Error:
        return None
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS days (
        date TEXT PRIMARY KEY, spy REAL, vix_ratio REAL, golden INTEGER, signal INTEGER,
        exposure REAL, spy_ret REAL, day_ret REAL, equity REAL, stamped TEXT)""")
    return con


def book(px, now=None):
    """Append every session in `px` not yet in the ledger, applying yesterday's exposure to
    today's SPY return. Returns the last row. Idempotent: re-running adds nothing."""
    con = _con()
    if con is None:
        return None
    rows = {r["date"]: dict(r) for r in con.execute("SELECT * FROM days ORDER BY date")}
    last = rows[max(rows)] if rows else None
    spy = px["SPY"]
    dates = [d.strftime("%Y-%m-%d") for d in px.index]
    # THE RECORD STARTS THE DAY THE MODULE FIRST RAN, not 200 sessions earlier. Back-filling
    # from history would make the first month of the "forward" record a backtest.
    first = len(dates) - 1 if not rows else 0
    newest = max(rows) if rows else ""
    for i, d in enumerate(dates):
        # only sessions AFTER the newest booked one: never back-fill behind the record
        if d in rows or i < max(200, first) or d <= newest:
            continue
        on, det = signal_from(px["^VIX"].values[:i + 1], px["^VIX3M"].values[:i + 1], spy.values[:i + 1])
        exposure = target_exposure(on)
        spy_ret = float(spy.iloc[i] / spy.iloc[i - 1] - 1)
        prev_x = last["exposure"] if last else BASE_X          # yesterday's decision applies today
        day_ret = prev_x * spy_ret - max(0.0, prev_x - 1.0) * BORROW_RATE / 252.0
        equity = (last["equity"] if last else START_EQUITY) * (1 + day_ret)
        row = {"date": d, "spy": float(spy.iloc[i]), "vix_ratio": det.get("vix_ratio"),
               "golden": int(bool(det.get("golden_cross"))), "signal": int(bool(on)),
               "exposure": exposure, "spy_ret": spy_ret, "day_ret": day_ret, "equity": equity,
               "stamped": (now or _now()).strftime("%Y-%m-%d %H:%M")}
        con.execute("INSERT OR IGNORE INTO days VALUES (?,?,?,?,?,?,?,?,?,?)",
                    tuple(row[k] for k in ("date", "spy", "vix_ratio", "golden", "signal", "exposure",
                                           "spy_ret", "day_ret", "equity", "stamped")))
        last = row
    con.commit()
    con.close()
    return last


def ledger():
    con = _con()
    if con is None:
        return {"days": [], "summary": {}}
    days = [dict(r) for r in con.execute("SELECT * FROM days ORDER BY date")]
    con.close()
    if not days:
        return {"days": [], "summary": {}}
    eq = [d["equity"] for d in days]
    peak, dd = eq[0], 0.0
    for e in eq:
        peak = max(peak, e); dd = min(dd, e / peak - 1)
    bh = START_EQUITY
    for d in days:
        bh *= 1 + d["spy_ret"]
    return {"days": days[-30:], "summary": {
        "since": days[0]["date"], "sessions": len(days), "equity": round(eq[-1], 2),
        "return_pct": round((eq[-1] / START_EQUITY - 1) * 100, 2),
        "buy_hold_equity": round(bh, 2), "max_dd_pct": round(dd * 100, 2),
        "days_on": sum(d["signal"] for d in days)}}


def run(now=None):
    px = fetch()
    if px is None or len(px) < 200:
        out = {"ok": False, "as_of": (now or _now()).strftime("%Y-%m-%d %H:%M ET"),
               "blocked": "VIX / VIX3M / SPY history unreadable"}
        snapshots.write(OUT, out)
        return out
    last = book(px, now=now)
    on, det = signal_from(px["^VIX"].values, px["^VIX3M"].values, px["SPY"].values)
    out = {"ok": True, "as_of": (now or _now()).strftime("%Y-%m-%d %H:%M ET"),
           "signal_on": bool(on), "detail": det, "exposure": target_exposure(on),
           "base_x": BASE_X, "boost_x": BOOST_X, "measured": MEASURED,
           "ledger": ledger(), "last": last}
    snapshots.write(OUT, out)
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str)[:2500])
