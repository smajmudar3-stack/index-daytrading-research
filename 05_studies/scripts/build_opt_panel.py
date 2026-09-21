"""build_opt_panel.py — dump the Dolt EOD option chains + daily OHLCV to parquet, once.

The Dolt `options.option_chain` table holds 114M rows (2019-02 -> 2026-08, ~1,500 names a
day, bid/ask/IV/greeks). Dolt answers a single-day query in ~0.3s and a single-SYMBOL query
in ~8s, because the primary key is date-first. So the dump walks DAYS, never symbols, and
writes one parquet per month under DATA_ROOT/opt_panel/. Every cross-sectional study in
05_studies reads those parquets; nothing re-queries Dolt.

Outputs (under DATA_ROOT/opt_panel/):
  chain_YYYY-MM.parquet   every chain row for the month
  ohlcv.parquet           daily bars, every symbol, 2018-01 onward
  earnings.parquet        earnings_calendar
  volhist.parquet         volatility_history (iv/hv current)
"""
import subprocess, sys, os, time
from io import StringIO
from datetime import date, timedelta
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from idt import paths  # noqa: E402

DOLT = paths.require_data("dolt")
OUT = os.path.join(paths.DATA_ROOT, "opt_panel")
os.makedirs(OUT, exist_ok=True)


def dolt(db, sql, timeout=900):
    r = subprocess.run(["dolt", "sql", "-q", sql, "-r", "csv"], cwd=os.path.join(DOLT, db),
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        return pd.DataFrame()
    return pd.read_csv(StringIO(r.stdout))


def days(a, b):
    d = a
    while d <= b:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def dump_chain(start=date(2019, 2, 9), end=date(2026, 8, 6)):
    cur_month, buf = None, []
    t0 = time.time()
    for d in days(start, end):
        m = d.strftime("%Y-%m")
        if cur_month and m != cur_month:
            flush(cur_month, buf); buf = []
        cur_month = m
        f = os.path.join(OUT, f"chain_{m}.parquet")
        if os.path.exists(f):
            continue
        df = dolt("options", "select date, act_symbol, expiration, strike, call_put, bid, ask, "
                             f"vol, delta, gamma, theta, vega from option_chain where date='{d}'")
        if len(df):
            buf.append(df)
        print(f"{d} {len(df):>7} rows  {time.time()-t0:6.0f}s", flush=True)
    if buf:
        flush(cur_month, buf)


def flush(m, buf):
    if not buf:
        return
    df = pd.concat(buf, ignore_index=True)
    for c in ("bid", "ask", "vol", "delta", "gamma", "theta", "vega", "strike"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
    df["date"] = pd.to_datetime(df["date"]); df["expiration"] = pd.to_datetime(df["expiration"])
    df["act_symbol"] = df["act_symbol"].astype("category"); df["call_put"] = df["call_put"].astype("category")
    df.to_parquet(os.path.join(OUT, f"chain_{m}.parquet"), index=False)
    print(f"wrote chain_{m}.parquet {len(df)} rows", flush=True)


def dump_ohlcv(start=date(2018, 1, 1), end=date(2026, 8, 6)):
    f = os.path.join(OUT, "ohlcv.parquet")
    if os.path.exists(f):
        return
    buf, t0 = [], time.time()
    # Month-range queries use the date-first primary key; ~20k rows a day.
    d = start
    while d <= end:
        e = (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        e = min(e, end)
        df = dolt("stocks", "select date, act_symbol, open, high, low, close, volume from ohlcv "
                            f"where date between '{d}' and '{e}'")
        buf.append(df)
        print(f"ohlcv {d} .. {e} {len(df)} rows {time.time()-t0:5.0f}s", flush=True)
        d = e + timedelta(days=1)
    df = pd.concat(buf, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    df["act_symbol"] = df["act_symbol"].astype("category")
    df.to_parquet(f, index=False)
    print("wrote ohlcv.parquet", len(df), flush=True)


def dump_small():
    f = os.path.join(OUT, "earnings.parquet")
    if not os.path.exists(f):
        dolt("earnings", "select act_symbol, date, `when` from earnings_calendar").to_parquet(f, index=False)
        print("wrote earnings.parquet", flush=True)
    f = os.path.join(OUT, "splits.parquet")
    if not os.path.exists(f):
        dolt("stocks", "select * from split").to_parquet(f, index=False)
        print("wrote splits.parquet", flush=True)
    for tbl, cols in (("eps_history", "act_symbol, period_end_date, reported, estimate"),
                      ("income_statement", "act_symbol, date, period, sales, gross_profit, net_income, "
                                           "average_shares, diluted_net_eps"),
                      ("cash_flow_statement", "act_symbol, date, period, net_cash_from_operating_activities, "
                                              "property_and_equipment, issuance_of_capital_stock, "
                                              "payment_of_dividends_and_other_distributions, issuance_of_debt")):
        f = os.path.join(OUT, f"{tbl}.parquet")
        if not os.path.exists(f):
            dolt("earnings", f"select {cols} from {tbl}", timeout=1800).to_parquet(f, index=False)
            print(f"wrote {tbl}.parquet", flush=True)
    f = os.path.join(OUT, "volhist.parquet")
    if not os.path.exists(f):
        dolt("options", "select date, act_symbol, hv_current, iv_current, iv_year_high, iv_year_low "
                        "from volatility_history").to_parquet(f, index=False)
        print("wrote volhist.parquet", flush=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "small"):
        dump_small()
    if what in ("all", "ohlcv"):
        dump_ohlcv()
    if what in ("all", "chain"):
        dump_chain()
