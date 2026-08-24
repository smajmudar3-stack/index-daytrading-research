"""Does ANY intraday signal work inside a specific MACRO/regime pocket? Condition the core
momentum & mean-reversion signals on VIX regime, time-of-day, trend-vs-range day, gap, and
day-of-week. Looking for a POSITIVE t>=2 pocket that also holds out-of-sample (2024-25 vs 2026)."""
import glob
import numpy as np
import pandas as pd
import yfinance as yf
import intraday_patterns as ip

RT = 0.0003


def enrich(tk):
    b = ip.indicators(ip.load5(tk))
    b["t"] = b.index.strftime("%H:%M")
    b["dow"] = b.index.dayofweek
    b["vix"] = pd.Series(b["day"]).map(lambda d: vix_d.reindex([pd.Timestamp(d)]).ffill().iloc[0]
                                       if pd.Timestamp(d) in vix_d.index or True else np.nan).values
    b["vix"] = pd.Series(vix_d.reindex(pd.to_datetime(b["day"])).ffill().values, index=b.index)
    # opening 30-min range per day; trend-up = above OR high, trend-dn = below OR low
    orh = b.between_time("09:30", "10:00").groupby("day")["high"].max()
    orl = b.between_time("09:30", "10:00").groupby("day")["low"].min()
    b["orh"] = pd.Series(b["day"]).map(orh).values
    b["orl"] = pd.Series(b["day"]).map(orl).values
    b["trend_up"] = b["close"] > b["orh"]
    b["trend_dn"] = b["close"] < b["orl"]
    # gap (today open vs prior close) from daily
    dcl = b.groupby("day")["close"].last()
    dop = b.groupby("day")["open"].first()
    gap = (dop / dcl.shift(1) - 1)
    b["gap"] = pd.Series(b["day"]).map(gap).values
    b["fE"] = ip.eod(b)
    b["f60"] = ip.fwd(b, 12)
    return b


def edge(b, mask, direction, horizon="fE"):
    r = (direction * b[horizon][mask.fillna(False)] - RT).dropna()
    if len(r) < 40:
        return None
    t = r.mean()/(r.std()/np.sqrt(len(r))) if r.std() > 0 else 0
    return r.mean()*100, t, (r > 0).mean()*100, len(r)


def report(tk):
    b = enrich(tk)
    c = b["close"]
    x = lambda s: s & ~s.shift(1).fillna(False)
    # core signals to condition
    mom = x(c > b.high.rolling(12).max().shift(1))          # breakout momentum
    rev = x(c < b.bb_dn)                                     # mean-reversion long
    print(f"\n===== {tk}: conditional edges (EOD horizon, net) — hunting a POSITIVE t>=2 pocket =====")
    conds = [
        ("momentum breakout | trend-up day", mom & b["trend_up"], +1),
        ("momentum breakout | VIX>20", mom & (b["vix"] > 20), +1),
        ("momentum breakout | VIX<15", mom & (b["vix"] < 15), +1),
        ("momentum breakout | before 11:00", mom & (b["t"] < "11:00"), +1),
        ("momentum breakout | after 14:00 (power hour)", mom & (b["t"] >= "14:00"), +1),
        ("momentum breakout | gap-up day", mom & (b["gap"] > 0.003), +1),
        ("mean-rev BB | VIX>20", rev, +1),
        ("mean-rev BB | range day (inside OR)", rev & ~b["trend_up"] & ~b["trend_dn"], +1),
        ("mean-rev BB | after 14:00", rev & (b["t"] >= "14:00"), +1),
        ("mean-rev BB | Monday", rev & (b["dow"] == 0), +1),
        ("trend-up day, hold to close (any bar >VWAP, 11am)", x((b["t"] == "11:00") & (c > b["vwap"]) & b["trend_up"]), +1),
    ]
    hits = []
    for name, mask, d in conds:
        e = edge(b, mask, d)
        if e:
            ret, t, win, n = e
            flag = "  <== POSITIVE t>=2" if t >= 2 else ("  (neg)" if t <= -2 else "")
            print(f"  {name:48} ret {ret:+.3f}%  t {t:+.1f}  win {win:.0f}%  n={n}{flag}")
            if t >= 2:
                hits.append((name, mask, d))
    # OOS check any positive hit
    if hits:
        print("  --- OOS check on positive pockets (train<2026, test>=2026) ---")
        for name, mask, d in hits:
            tr = b[b.index < "2026-01-01"]; te = b[b.index >= "2026-01-01"]
            for lbl, seg in [("train", tr), ("test26", te)]:
                m = mask.reindex(seg.index)
                e = edge(seg, m, d)
                if e:
                    print(f"    {name} [{lbl}]: ret {e[0]:+.3f}% t {e[1]:+.1f} n={e[3]}")
    else:
        print("  >>> NO positive t>=2 conditional pocket found.")


def main():
    # these were module-level before the guard; the functions above
    # still read them, so they stay global — only the work moved.
    global vix_d

    vix_d = yf.download("^VIX", start="2024-01-01", progress=False, auto_adjust=False,
                        multi_level_index=False).rename(columns=str.lower)["close"]

    for tk in ["SPY", "QQQ"]:
        report(tk)


if __name__ == "__main__":
    main()
