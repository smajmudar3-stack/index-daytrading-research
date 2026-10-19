"""play_structures_test.py — the measured stock signals, expressed as OPTION structures on
seven years of real chains, held to the horizon the signal was measured on. This is the
table the Plays desk prices from: for each signal and structure, the P&L per dollar of
risk, the hit rate, the payoff, and the time splits, at the ask when buying and the bid
when selling.

The signals (each measured positive in all three splits on the stock, 02_findings):
  SURPRISE   top 25 by earnings surprise among names that reported in the last 63
             sessions -> 63-session hold (+4.24%/quarter over SPY in shares)
  RANKER     top 25 by mean rank of surprise, residual momentum, 12-1 momentum among the
             same -> 21-session hold (+0.84%/4 weeks)
  STRESS     bottom 40 by the reversal composite (1-month, 1-week, Bollinger) -> 10-session
             hold; measured +2.59%/hold when VIX > 25; booked every week since 2026-10-01
             at Sholo's instruction, so both the in-regime and the all-weeks versions are
             priced here
The structures, all bullish (the signals are long-only), expiry nearest the horizon in
calendar days (10 sessions -> ~21 DTE, 21 -> ~35, 63 -> ~95), HELD TO EXPIRY so the
settlement is exact off the split-adjusted close (a time exit on a thinned chain is biased,
see xsec_vertical_test):
  call_debit_50_25   long the ~50-delta call, short the ~25-delta call   (the live book's shape)
  call_debit_70_40   long the ~70-delta, short the ~40-delta             (more intrinsic, less theta)
  long_call_60       the ~60-delta call alone                            (unlimited upside, all the theta)
  long_call_80       the ~80-delta call alone                            (stock replacement)
  put_credit_30_15   short the ~30-delta put, long the ~15-delta         (paid to be long)
  stock              the shares, for reference
P&L is reported per $ of MAX RISK (debit for debits, width minus credit for credits, the
share price for stock) so structures are comparable, and in $ per $1,000 of risk.
Costs are the quotes themselves: every leg bought at the ask, sold at the bid. The entry
also reports the bid-ask as a share of risk, which is the price of the structure before
anything happens.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS  # noqa: E402
from xsec_vertical_test import _nearest, load_chain, payoff  # noqa: E402

warnings.filterwarnings("ignore")
PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
SIGNALS = {"surprise": 63, "ranker": 21, "stress_all": 10, "stress_vix25": 10}
DTE_TARGET = {63: 95, 21: 35, 10: 21}
STRUCTS = [("call_debit_50_25", "Call", 0.50, 0.25), ("call_debit_70_40", "Call", 0.70, 0.40),
           ("long_call_60", "Call", 0.60, None), ("long_call_80", "Call", 0.80, None),
           ("put_credit_30_15", "Put", 0.30, 0.15)]


def entries():
    p = pd.read_parquet(os.path.join(PANEL, "signal_panel.parquet"),
                        columns=["date", "act_symbol", "sue", "resid_mom", "mom12_1", "rev1m", "rev1w", "bb_pos", "days_since", "vix", "close", "adv20"])
    p = p[(p.close >= 10) & (p.adv20 >= 10e6)]
    out = []
    rep = p[p.days_since <= 63].dropna(subset=["sue"])
    g = rep.groupby("date")
    s = rep.assign(r=g.sue.rank(ascending=False))
    out.append(s[s.r <= 25][["date", "act_symbol"]].assign(signal="surprise"))
    rk = rep.dropna(subset=["resid_mom", "mom12_1"]).copy()
    gg = rk.groupby("date")
    rk["score"] = (gg.sue.rank(pct=True) + gg.resid_mom.rank(pct=True) + gg.mom12_1.rank(pct=True)) / 3
    rk["r"] = rk.groupby("date").score.rank(ascending=False)
    out.append(rk[rk.r <= 25][["date", "act_symbol"]].assign(signal="ranker"))
    st = p.dropna(subset=["rev1m", "rev1w", "bb_pos"]).copy()
    gs = st.groupby("date")
    st["score"] = (gs.rev1m.rank(pct=True) + gs.rev1w.rank(pct=True) + gs.bb_pos.rank(pct=True)) / 3
    st["r"] = st.groupby("date").score.rank()
    bot = st[st.r <= 40][["date", "act_symbol", "vix"]]
    out.append(bot[["date", "act_symbol"]].assign(signal="stress_all"))
    out.append(bot[bot.vix > 25][["date", "act_symbol"]].assign(signal="stress_vix25"))
    e = pd.concat(out, ignore_index=True)
    # non-overlapping sampling: one entry date every horizon/5 weeks
    keep = []
    for sig, h in SIGNALS.items():
        d = e[e.signal == sig]
        dates = np.sort(d.date.unique())[::max(1, h // 5)]
        keep.append(d[d.date.isin(dates)])
    return pd.concat(keep, ignore_index=True)


def pick(ch, ent, dte_target):
    key = ["date", "act_symbol"]
    c = ch.merge(ent[key], on=key)
    lo, hi = int(dte_target * 0.6), int(dte_target * 1.6)
    ex = c[(c.dte >= lo) & (c.dte <= hi)][key + ["expiration", "dte"]].drop_duplicates()
    if ex.empty:
        return pd.DataFrame()
    ex = _nearest(ex, "dte", dte_target, key)[key + ["expiration"]]
    c = c.merge(ex, on=key + ["expiration"])
    rows = []
    for name, right, d_long, d_short in STRUCTS:
        cc = c[c.call_put == right]
        if cc.empty:
            continue
        lg = _nearest(cc, "adelta", d_long, key)[key + ["expiration", "dte", "strike", "bid", "ask", "delta", "call_put"]]
        if d_short is None:
            s = lg.rename(columns={"strike": "strike_l", "bid": "bid_l", "ask": "ask_l", "delta": "delta_l"})
            s["strike_s"] = np.nan
            s["net"] = s.ask_l
            s["max_risk"] = s.net
            s["cost_pct"] = (s.ask_l - s.bid_l) / s.net
            s = s[s.net > 0.05]
        else:
            sh = _nearest(cc, "adelta", d_short, key)[key + ["strike", "bid", "ask", "delta"]]
            s = lg.merge(sh, on=key, suffixes=("_l", "_s"))
            if name.startswith("call_debit"):
                s = s[s.strike_l < s.strike_s]
                s["net"] = s.ask_l - s.bid_s
                s["width"] = s.strike_s - s.strike_l
                s = s[(s.net > 0) & (s.net < s.width)]
                s["max_risk"] = s.net
                s["cost_pct"] = ((s.ask_l - s.bid_l) + (s.ask_s - s.bid_s)) / s.net
            else:                                             # put credit: short the higher strike
                s = s[s.strike_l < s.strike_s]                # long = lower (15d), short = higher (30d)
                s = s.rename(columns={"strike_l": "strike_lo", "bid_l": "bid_lo", "ask_l": "ask_lo", "delta_l": "delta_lo",
                                      "strike_s": "strike_hi", "bid_s": "bid_hi", "ask_s": "ask_hi", "delta_s": "delta_hi"})
                s["net"] = s.ask_lo - s.bid_hi                # pay the ask on the long, receive the bid on the short
                s["width"] = s.strike_hi - s.strike_lo
                s = s[(s.net < 0) & (s.width + s.net > 0)]
                s["max_risk"] = s.width + s.net
                s["cost_pct"] = ((s.ask_lo - s.bid_lo) + (s.ask_hi - s.bid_hi)) / s.max_risk
                s["strike_l"], s["strike_s"] = s.strike_lo, s.strike_hi
        s["struct"] = name
        rows.append(s)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def settle(t, px):
    cl = px[["date", "act_symbol", "close"]].sort_values("date")
    t = t.sort_values("expiration")
    t = pd.merge_asof(t, cl.rename(columns={"date": "expiration", "close": "spot_T"}), on="expiration", by="act_symbol",
                      direction="backward", tolerance=pd.Timedelta(days=4))
    t = t.merge(cl.rename(columns={"close": "spot_0"}), on=["date", "act_symbol"], how="left")
    pay = []
    for r in t.itertuples():
        if pd.isna(r.spot_T):
            pay.append(np.nan)
            continue
        if r.struct == "put_credit_30_15":
            # long the low put (+1), short the high put (-1)
            pay.append(max(0.0, r.strike_l - r.spot_T) - max(0.0, r.strike_s - r.spot_T))
        elif pd.isna(r.strike_s):
            pay.append(max(0.0, r.spot_T - r.strike_l))
        else:
            pay.append(payoff(r, r.spot_T))
    t["pay_T"] = pay
    t["pnl_risk"] = (t.pay_T - t.net) / t.max_risk
    t["stock_ret"] = t.spot_T / t.spot_0 - 1
    return t


def report(t, label):
    rows = []
    for struct, s in t.groupby("struct"):
        v = s.pnl_risk.dropna().clip(-1, 20)
        if len(v) < 30:
            continue
        win, loss = v[v > 0], v[v <= 0]
        row = {"structure": struct, "n": len(v), "mean %risk": v.mean() * 100, "median": v.median() * 100, "hit": (v > 0).mean(),
               "payoff": (win.mean() / -loss.mean()) if len(loss) else np.nan, "t": v.mean() / v.std() * np.sqrt(len(v)),
               "bid-ask %risk": s.cost_pct.median() * 100, "per $1k risk": v.mean() * 1000,
               "stock %": s.stock_ret.mean() * 100, "stock hit": (s.stock_ret > 0).mean()}
        for k, (a, b) in SPLITS.items():
            vv = s[(s.date >= a) & (s.date <= b)].pnl_risk.dropna().clip(-1, 20)
            row[k] = f"{vv.mean()*100:+.0f}% ({len(vv)})" if len(vv) >= 15 else "—"
        rows.append(row)
    print(f"\n{label}")
    if rows:
        print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:8.2f}"))


def main():
    pd.set_option("display.width", 250)
    e = entries()
    print("entries:", e.groupby("signal").size().to_dict(), f"{e.date.min().date()}..{e.date.max().date()}")
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"), columns=["date", "act_symbol", "close"])
    px["act_symbol"] = px.act_symbol.astype(str)
    from xsec_predictors_test import adjust_splits
    px = adjust_splits(px.assign(open=np.nan, high=np.nan, low=np.nan, volume=np.nan))[["date", "act_symbol", "close"]]
    months = sorted(f[6:13] for f in os.listdir(PANEL) if f.startswith("chain_"))
    out = []
    for yr in sorted({m[:4] for m in months}):
        ch = load_chain([m for m in months if m.startswith(yr)])
        if ch.empty:
            continue
        for sig, h in SIGNALS.items():
            ent = e[(e.signal == sig) & (e.date.dt.year == int(yr))]
            if ent.empty:
                continue
            t = pick(ch, ent, DTE_TARGET[h])
            if t.empty:
                continue
            t["signal"] = sig
            out.append(settle(t, px))
        del ch
        print(f"  {yr} done", flush=True)
    t = pd.concat(out, ignore_index=True)
    t.to_parquet(os.path.join(PANEL, "play_structures.parquet"), index=False)
    for sig in SIGNALS:
        s = t[t.signal == sig]
        if len(s):
            report(s, f"=== {sig.upper()}  ({SIGNALS[sig]}-session signal, expiry ~{DTE_TARGET[SIGNALS[sig]]} DTE, held to expiry, real ask/bid) ===")


if __name__ == "__main__":
    main()
