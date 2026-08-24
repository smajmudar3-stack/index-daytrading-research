"""What actually precedes a BIG MOVE? The selection problem, done properly.

Everything tested so far measured the AVERAGE far-OTM contract. That answers
"is buying lottery tickets at random profitable" (no) but not the question that
matters: can you pick better than random?

So this drops options entirely and asks the cleaner underlying question:

    Given what a stock looks like TODAY, what is the probability it makes a
    move of >= 2 / 3 / 4 sigma over the next 21 or 42 trading days -- and which
    characteristics raise that probability above the base rate?

Sigma is each stock's OWN trailing 60-day volatility, so "big" means big for
that name rather than big in absolute terms. Every feature is computed from
data available at the close of day t and evaluated on day t+1 onward.

The bar: a feature is only interesting if it raises P(big move) materially
above the unconditional base rate AND does so in all three time splits. Lift is
reported as a ratio, because a feature that takes P(3-sigma) from 1.0% to 1.4%
is a 40% improvement in the thing that decides whether a far-OTM ticket ever
pays -- even though both numbers look small.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

from idt import paths

warnings.filterwarnings("ignore")
OUT = paths.data("bigmove")

SPLITS = {"2010-2016": ("2010-01-01", "2016-12-31"),
          "2017-2021": ("2017-01-01", "2021-12-31"),
          "2022-2026": ("2022-01-01", "2026-12-31")}
HORIZONS = [21, 42]
SIGMAS = [2, 3, 4]


def build_universe():
    """Liquid, optionable names with enough history and enough movement."""
    import yfinance as yf
    p = os.path.join(OUT, "prices.parquet")
    if os.path.exists(p):
        return pd.read_parquet(p)

    tk = """AAPL MSFT NVDA AMZN META GOOGL TSLA AVGO AMD INTC MU QCOM TXN ADBE CRM
    ORCL CSCO IBM NOW PANW SNOW NET DDOG SHOP UBER ABNB PLTR SMCI MRVL ON LRCX AMAT
    KLAC ARM COIN SQ PYPL WMT COST TGT HD LOW NKE SBUX MCD DIS NFLX PG KO PEP LULU
    CMG BAC WFC GS MS C SCHW BLK AXP V MA COF SPGI UNH JNJ PFE MRK ABBV LLY TMO ABT
    DHR BMY AMGN GILD CVS ISRG VRTX REGN MRNA BIIB XOM CVX COP SLB EOG PSX VLO MPC
    OXY HAL DVN FANG BA CAT DE GE HON LMT RTX UPS FDX UNP CSX NSC MMM EMR ETN PH GD
    NOC LIN APD SHW FCX NEM NUE DOW NEE DUK SO D AEP MARA RIOT MSTR SOFI AFRM RBLX
    U DKNG CVNA UPST IONQ RKLB LCID RIVN NIO F GM DAL AAL CCL NCLH GME AMC HOOD ROKU
    PINS SNAP TTD ZM DOCU CRWD ZS OKTA TWLO ROKU SPOT ABNB DASH RDDT""".split()
    tk = sorted(set(tk))
    print(f"  fetching {len(tk)} names ...", flush=True)

    frames = []
    for i in range(0, len(tk), 25):
        b = tk[i:i + 25]
        df = yf.download(b, start="2009-01-01", auto_adjust=True, progress=False,
                         group_by="ticker", threads=False)
        for t in b:
            try:
                s = df[t].dropna(how="all")
            except KeyError:
                continue
            if len(s) < 750:
                continue
            d = s.reset_index()
            d.columns = [str(c).lower() for c in d.columns]
            d["ticker"] = t
            frames.append(d[["date", "ticker", "open", "high", "low", "close", "volume"]])
        print(f"    {min(i+25, len(tk))}/{len(tk)}", flush=True)

    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"]).dt.tz_localize(None)
    px.to_parquet(p, index=False)
    return px


def features(g):
    """Everything knowable at the close of day t. Shifted at the end."""
    c, h, l, v = g["close"], g["high"], g["low"], g["volume"]
    r = c.pct_change(fill_method=None)
    f = pd.DataFrame(index=g.index)

    sig = r.rolling(60).std()
    f["sig"] = sig

    # --- volatility STATE -------------------------------------------------
    f["rv21_pct"] = (r.rolling(21).std()
                     .rolling(252, min_periods=120)
                     .apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True))
    f["vol_ratio"] = r.rolling(10).std() / r.rolling(60).std()
    # Bollinger width percentile — the classic "coiled spring" screen.
    bw = (c.rolling(20).std() * 2) / c.rolling(20).mean()
    f["bbw_pct"] = bw.rolling(252, min_periods=120).apply(
        lambda w: (w[:-1] < w[-1]).mean(), raw=True)

    # --- RANGE compression -----------------------------------------------
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    atr = tr.rolling(14).mean() / c
    f["atr_pct"] = atr.rolling(252, min_periods=120).apply(
        lambda w: (w[:-1] < w[-1]).mean(), raw=True)
    f["nr7"] = ((h - l) == (h - l).rolling(7).min()).astype(float)

    # --- LOCATION / trend -------------------------------------------------
    f["frm_hi"] = c / c.rolling(252).max() - 1
    f["frm_lo"] = c / c.rolling(252).min() - 1
    f["above200"] = (c > c.rolling(200).mean()).astype(float)
    f["mom63"] = c.pct_change(63, fill_method=None)
    f["mom21"] = c.pct_change(21, fill_method=None)

    # --- VOLUME -----------------------------------------------------------
    vz = (v - v.rolling(63).mean()) / v.rolling(63).std()
    f["vol_z"] = vz
    f["dollar_vol"] = (c * v).rolling(21).mean()

    # --- recent gap / jump history: does a mover keep moving? -------------
    f["big_days_63"] = (r.abs() > 2 * sig).rolling(63).sum()
    f["max_abs_21"] = r.abs().rolling(21).max() / sig

    return f.shift(1)


def main():
    # Created here, not at import. A directory conjured by a bare `import`
    # turns "market data not installed" into "installed but empty" for every
    # reader downstream, which is the harder failure to notice.
    os.makedirs(OUT, exist_ok=True)

    px = build_universe()
    print(f"  {px.ticker.nunique()} names, {len(px):,} rows, "
          f"{px.date.min().date()} -> {px.date.max().date()}\n")

    rows = []
    for t, g in px.groupby("ticker"):
        g = g.sort_values("date").set_index("date")
        f = features(g)
        c = g["close"]
        for H in HORIZONS:
            fwd_max = c.rolling(H).max().shift(-H) / c - 1
            fwd_min = c.rolling(H).min().shift(-H) / c - 1
            move = pd.concat([fwd_max.abs(), fwd_min.abs()], axis=1).max(axis=1)
            # Express the move in units of the stock's OWN sigma over H days.
            d = f.assign(ticker=t, H=H,
                         move_sig=move / (f["sig"] * np.sqrt(H)))
            rows.append(d.reset_index())
    d = pd.concat(rows, ignore_index=True).dropna(subset=["move_sig", "sig"])
    d = d[np.isfinite(d.move_sig)]
    d.to_parquet(os.path.join(OUT, "panel.parquet"), index=False)
    print(f"  {len(d):,} stock-days with a forward move measured\n")

    SCREENS = {
        "vol compressed (rv<20pct)": lambda x: x.rv21_pct < 0.20,
        "BB width <20pct": lambda x: x.bbw_pct < 0.20,
        "ATR <20pct": lambda x: x.atr_pct < 0.20,
        "NR7 today": lambda x: x.nr7 > 0,
        "vol EXPANDING (ratio>1.3)": lambda x: x.vol_ratio > 1.3,
        "near 52w high (<3%)": lambda x: x.frm_hi > -0.03,
        "deep in drawdown (<-30%)": lambda x: x.frm_hi < -0.30,
        "volume surge (z>2)": lambda x: x.vol_z > 2,
        "recent big days (>=3)": lambda x: x.big_days_63 >= 3,
        "had a 3sig day in 21d": lambda x: x.max_abs_21 > 3,
        "compressed + vol surge": lambda x: (x.rv21_pct < 0.20) & (x.vol_z > 2),
        "compressed + near high": lambda x: (x.rv21_pct < 0.20) & (x.frm_hi > -0.03),
        "drawdown + big days": lambda x: (x.frm_hi < -0.30) & (x.big_days_63 >= 3),
    }

    for H in HORIZONS:
        sub = d[d.H == H]
        print("=" * 104)
        print(f"HORIZON {H} trading days — P(max move >= N sigma), lift vs base rate")
        print("=" * 104)
        base = {s: (sub.move_sig >= s).mean() for s in SIGMAS}
        print("  BASE RATE   " + "   ".join(
            f"P({s}sig)={base[s]*100:5.2f}%" for s in SIGMAS))
        print(f"\n  {'screen':28s} {'n':>9s} " +
              " ".join(f"{'P('+str(s)+'sig)':>10s} {'lift':>6s}" for s in SIGMAS) +
              "   consistent?")
        for name, fn in SCREENS.items():
            m = fn(sub)
            s = sub[m.fillna(False)]
            if len(s) < 3000:
                continue
            line = f"  {name:28s} {len(s):9,d} "
            lifts = []
            for sg in SIGMAS:
                p = (s.move_sig >= sg).mean()
                lift = p / base[sg] if base[sg] > 0 else np.nan
                lifts.append(lift)
                line += f" {p*100:9.2f}% {lift:6.2f}"
            # Consistency of the 3-sigma lift across the three periods.
            ok = []
            for a, b in SPLITS.values():
                w = sub[(sub.date >= a) & (sub.date <= b)]
                ws = w[fn(w).fillna(False)]
                if len(ws) < 500:
                    ok.append(None); continue
                bp = (w.move_sig >= 3).mean()
                ok.append((ws.move_sig >= 3).mean() > bp if bp > 0 else False)
            tag = "YES" if all(o for o in ok if o is not None) and any(ok) else "no"
            print(line + f"   {tag}")
        print()


if __name__ == "__main__":
    main()
