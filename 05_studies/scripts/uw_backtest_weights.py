"""Backtest the UW inputs that HAVE history, so their weights are earned.

Of the four non-zero inputs, only two carry usable history:

    insider  /api/stock/{t}/insider-buy-sells   23 years (2003-2026)
    shorts   /api/shorts/{t}/interest-float/v2  monthly settlement history

Dark pool and classified flow return same-day data only, so they cannot be
backtested here and must stay on the forward-tracking path — this file does not
pretend otherwise.

Method mirrors the studies that produced the nulls, so results are comparable:
  * signal known at date t, return measured t+1 .. t+H (no overlap with entry)
  * measured as EXCESS over each name's own base rate, because equities drift
  * Spearman IC, since the signal only needs to rank outcomes
  * split three ways in time; a signal that works in one era is not a signal
"""
import os
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

import uw_client as uw  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = 5
UNIVERSE = """AAPL MSFT NVDA AMZN META GOOGL TSLA AVGO AMD INTC MU QCOM ADBE CRM
ORCL CSCO IBM NOW PANW SNOW UBER ABNB PLTR SMCI MRVL COIN PYPL WMT COST TGT HD
NKE SBUX MCD DIS NFLX PG KO PEP BAC WFC GS MS C SCHW AXP V MA UNH JNJ PFE MRK
ABBV LLY TMO ABT BMY AMGN GILD CVS ISRG VRTX REGN MRNA BIIB XOM CVX COP SLB EOG
OXY BA CAT DE GE HON LMT RTX UPS FDX UNP MMM NEE DUK SO MARA RIOT MSTR SOFI
AFRM RBLX DKNG CVNA UPST IONQ RKLB LCID RIVN F GM DAL AAL CCL GME HOOD ROKU
PINS SNAP TTD ZM CRWD ZS OKTA SPOT DASH""".split()


def prices():
    import yfinance as yf
    p = os.path.join(ROOT, "data", "bigmove", "prices.parquet")
    if os.path.exists(p):
        d = pd.read_parquet(p)
        return d.pivot(index="date", columns="ticker", values="close").sort_index()
    px = yf.download(UNIVERSE, start="2015-01-01", auto_adjust=True,
                     progress=False, threads=False)["Close"]
    return px


def fetch_insider(t):
    try:
        r = uw._rows(uw._get(f"/api/stock/{t}/insider-buy-sells", {}))
        out = []
        for x in r:
            try:
                out.append({"ticker": t, "date": pd.Timestamp(x["filing_date"]),
                            "buys": float(x.get("purchases") or 0),
                            "buy_notional": float(x.get("purchases_notional") or 0),
                            "sells": float(x.get("sells") or 0),
                            "sell_notional": float(x.get("sells_notional") or 0)})
            except Exception:
                continue
        return out
    except Exception:
        return []


def fetch_shorts(t):
    try:
        r = uw._rows(uw._get(f"/api/shorts/{t}/interest-float/v2", {}))
        out = []
        for x in r:
            try:
                out.append({"ticker": t, "date": pd.Timestamp(x["market_date"]),
                            "si_float": float(x.get("si_float") or 0) * 100,
                            "days_to_cover": float(x.get("days_to_cover") or 0),
                            "fee_rate": float(x.get("fee_rate") or 0)})
            except Exception:
                continue
        return out
    except Exception:
        return []


def ic_report(d, col, px, label):
    """Spearman IC of `col` against the forward H-day EXCESS return."""
    rows = []
    for t, g in d.groupby("ticker"):
        if t not in px.columns:
            continue
        s = px[t].dropna()
        base = s.pct_change(H, fill_method=None).shift(-H)   # every-day baseline
        mean_base = base.mean()
        for _, r in g.iterrows():
            after = s[s.index > r["date"]]
            if len(after) <= H:
                continue
            ret = float(after.iloc[H]) / float(after.iloc[0]) - 1
            rows.append({"ticker": t, "date": r["date"], "sig": r[col],
                         "exc": ret - mean_base})
    e = pd.DataFrame(rows).dropna()
    if len(e) < 60 or e.sig.nunique() < 3:
        return None
    out = {"input": label, "n": len(e),
           "ic": round(float(e.sig.corr(e.exc, method="spearman")), 4),
           "mean_exc": round(float(e.exc.mean()) * 100, 3)}
    # Era stability — a signal that only worked once is not a signal.
    for lab, (a, b) in {"2015-19": ("2015-01-01", "2019-12-31"),
                        "2020-22": ("2020-01-01", "2022-12-31"),
                        "2023-26": ("2023-01-01", "2026-12-31")}.items():
        w = e[(e.date >= a) & (e.date <= b)]
        out[lab] = round(float(w.sig.corr(w.exc, method="spearman")), 3) if len(w) > 40 else None
    return out


def main():
    print("Fetching insider history (23y) and short interest ...", flush=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        ins = [x for sub in ex.map(fetch_insider, UNIVERSE) for x in sub]
        sh = [x for sub in ex.map(fetch_shorts, UNIVERSE) for x in sub]
    ins, sh = pd.DataFrame(ins), pd.DataFrame(sh)
    print(f"  insider rows {len(ins):,} | shorts rows {len(sh):,}")
    px = prices()
    print(f"  prices {px.shape[0]:,} days x {px.shape[1]} names\n")

    res = []
    if not ins.empty:
        ins = ins[ins.date >= "2015-01-01"]
        # Net open-market buying, scaled — the direction insiders actually voted.
        ins["net_buy"] = ins.buys - ins.sells
        ins["net_notional"] = ins.buy_notional - ins.sell_notional
        for col, lab in (("net_buy", "insider_net_buys"),
                         ("net_notional", "insider_net_notional"),
                         ("buys", "insider_buys_only")):
            r = ic_report(ins[ins[col] != 0], col, px, lab)
            if r:
                res.append(r)
    if not sh.empty:
        for col, lab in (("si_float", "short_float_pct"),
                         ("days_to_cover", "days_to_cover"),
                         ("fee_rate", "borrow_fee")):
            r = ic_report(sh, col, px, lab)
            if r:
                res.append(r)

    print("=" * 92)
    print(f"MEASURED INFORMATION COEFFICIENT — {H}-day forward EXCESS return")
    print("=" * 92)
    print(f"  {'input':24s} {'n':>7s} {'IC':>8s} {'mean exc':>10s} "
          f"{'15-19':>7s} {'20-22':>7s} {'23-26':>7s}")
    for r in sorted(res, key=lambda x: -abs(x["ic"])):
        f = lambda k: f"{r[k]:+7.3f}" if r.get(k) is not None else "     --"
        print(f"  {r['input']:24s} {r['n']:7,d} {r['ic']:+8.4f} "
              f"{r['mean_exc']:+9.3f}% {f('2015-19')} {f('2020-22')} {f('2023-26')}")

    print("\n  A weight is earned only by an IC that is non-trivial AND holds sign")
    print("  across eras. Anything failing that stays at its prior and is flagged")
    print("  unmeasured, or goes to zero if it is measurably flat.")


if __name__ == "__main__":
    main()
