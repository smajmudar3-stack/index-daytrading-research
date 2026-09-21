"""xsec_vertical_test.py — the weekly book's trade, replayed on seven years of real chains.

The ledger's first 129 closed cards lost 40% of risk on average. Three things could be
wrong and the ledger cannot separate them: the DIRECTION call (right 37.6%), the STRUCTURE
(debit spreads -56%/card against credit spreads -4%), and the EXIT RULE (a -50% stop on a
9-DTE debit spread, hit on 70% of cards, and even direction-right cards averaged -12.6%).
This replays each of those choices on the Dolt chains, at the ask when buying and the bid
when selling, so they can be judged one at a time.

For every (week, name) in the cross-sectional panel with a direction from a chosen signal:
  structure   debit vertical  : long the ~50-delta strike, short the ~25-delta strike
              credit vertical : short the ~30-delta strike, long the ~15-delta strike
              (bullish -> calls for the debit / puts for the credit; bearish mirrored)
  expiry      nearest to 14 DTE in [7, 28]  (the live book uses 5-16)
  exits       expiry   : payoff off the split-adjusted close on the expiry date. Exact.
              5d / 10d : close at the chain marks (sell at bid, buy at ask) on the first
                         chain day >= t+H where BOTH legs are quoted. The chain is thinned,
                         so ~half the contracts drop out; those trades report as NaN for
                         that rule, never as a win.
  reported    P&L as a % of MAX RISK (debit for a debit spread, width-credit for a credit
              spread), so a $1 and a $10 spread count the same.

INVARIANTS CHECKED, because a payoff sign flip once produced a Sharpe of 35.6 here:
  a ~25-delta short call should finish in the money roughly 25% of the time;
  a debit spread's best case is (width - debit) and its worst is -debit, both per trade.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
TARGET_DTE, DTE_LO, DTE_HI = 14, 7, 28


def _nearest(df, key, target, group):
    d = (df[key] - target).abs()
    idx = d.groupby([df[g] for g in group]).idxmin()
    return df.loc[idx.values]


def load_chain(months):
    out = []
    for m in months:
        f = os.path.join(PANEL, f"chain_{m}.parquet")
        if os.path.exists(f):
            out.append(pd.read_parquet(f))
    ch = pd.concat(out, ignore_index=True)
    ch["act_symbol"] = ch.act_symbol.astype(str)
    ch["call_put"] = ch.call_put.astype(str)
    ch["dte"] = (ch.expiration - ch.date).dt.days
    ch["adelta"] = ch.delta.abs()
    return ch[(ch.ask > 0) & (ch.ask >= ch.bid)]


def pick_legs(ch, entries):
    """entries: DataFrame[date, act_symbol, side(+1/-1)]. Returns one row per entry per
    structure with both legs priced at entry."""
    key = ["date", "act_symbol"]
    c = ch.merge(entries, on=key)
    ex = c[(c.dte >= DTE_LO) & (c.dte <= DTE_HI)][key + ["expiration", "dte"]].drop_duplicates()
    ex = _nearest(ex, "dte", TARGET_DTE, key)[key + ["expiration"]]
    c = c.merge(ex, on=key + ["expiration"])
    rows = []
    for struct, right_of_side, d_long, d_short in (
            ("debit", {1: "Call", -1: "Put"}, 0.50, 0.25),
            ("credit", {1: "Put", -1: "Call"}, 0.15, 0.30)):
        cc = c[c.call_put == c.side.map(right_of_side)]
        lg = _nearest(cc, "adelta", d_long, key)[key + ["expiration", "strike", "bid", "ask", "delta", "call_put", "side"]]
        sh = _nearest(cc, "adelta", d_short, key)[key + ["strike", "bid", "ask", "delta"]]
        s = lg.merge(sh, on=key, suffixes=("_l", "_s"))
        s = s[s.strike_l != s.strike_s]
        s["struct"] = struct
        s["net"] = s.ask_l - s.bid_s                # pay the ask, receive the bid
        s["width"] = (s.strike_l - s.strike_s).abs()
        if struct == "debit":
            s = s[s.net > 0]
            s["max_risk"] = s.net
        else:
            s = s[(s.net < 0) & (s.width + s.net > 0)]
            s["max_risk"] = s.width + s.net         # width minus credit
        rows.append(s)
    return pd.concat(rows, ignore_index=True)


def payoff(row, spot):
    def leg(k, right, q):
        intrinsic = max(0.0, spot - k) if right == "Call" else max(0.0, k - spot)
        return q * intrinsic
    return leg(row.strike_l, row.call_put, +1) + leg(row.strike_s, row.call_put, -1)


def settle(trades, ch, px):
    key = ["act_symbol"]
    # expiry: the last close at or before the expiration date
    cl = px[["date", "act_symbol", "close"]].sort_values("date")
    t = trades.sort_values("expiration")
    t = pd.merge_asof(t, cl.rename(columns={"date": "expiration", "close": "spot_T"}),
                      on="expiration", by="act_symbol", direction="backward",
                      tolerance=pd.Timedelta(days=4))
    t["pay_T"] = [payoff(r, s) if pd.notna(s) else np.nan for r, s in zip(t.itertuples(), t.spot_T)]
    t["pnl_expiry"] = (t.pay_T - t.net) / t.max_risk
    # time exits at chain marks
    ch_s = ch[["date", "act_symbol", "expiration", "strike", "call_put", "bid", "ask"]]
    for h in (5, 10):
        t["exit_after"] = t.date + pd.Timedelta(days=int(h * 7 / 5))
        for lab in ("l", "s"):
            m = ch_s.rename(columns={"strike": f"strike_{lab}", "date": "mdate",
                                     "bid": f"xbid_{lab}", "ask": f"xask_{lab}"})
            t = t.sort_values("exit_after")
            m = m.sort_values("mdate")
            t = pd.merge_asof(t, m, left_on="exit_after", right_on="mdate",
                              by=["act_symbol", "expiration", f"strike_{lab}", "call_put"],
                              direction="forward", tolerance=pd.Timedelta(days=4))
            t = t.drop(columns=["mdate"])
        # unwind: sell the long at the bid, buy the short back at the ask
        close_net = t.xbid_l - t.xask_s
        t[f"pnl_{h}d"] = (close_net - t.net) / t.max_risk
        t = t.drop(columns=["exit_after", "xbid_l", "xask_l", "xbid_s", "xask_s"])
    return t


def report(t, label):
    print(f"\n--- {label}: {len(t):,} trades ---")
    rows = []
    for struct in ("debit", "credit"):
        s = t[t.struct == struct]
        for rule in ("pnl_expiry", "pnl_5d", "pnl_10d"):
            v = s[rule].dropna()
            v = v.clip(-1.0, 20)
            if len(v) < 30:
                continue
            rows.append({"struct": struct, "exit": rule[4:], "n": len(v), "mean %": v.mean() * 100,
                         "median %": v.median() * 100, "win": (v > 0).mean(),
                         "t": v.mean() / v.std() * np.sqrt(len(v))})
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:8.2f}"))


def main():
    pd.set_option("display.width", 250)
    panel = pd.read_parquet(os.path.join(PANEL, "xsec_panel.parquet"))
    panel["act_symbol"] = panel.act_symbol.astype(str)
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"))
    px["act_symbol"] = px.act_symbol.astype(str)
    px = px[px.act_symbol.isin(set(panel.act_symbol))]

    from xsec_predictors_test import universe, weekly, adjust_splits  # noqa: E402
    px = adjust_splits(px)
    u = weekly(universe(panel), 1)
    sig = sys.argv[1] if len(sys.argv) > 1 else "cw_spread"
    sign = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    u = u[u[sig].notna()].copy()
    u["rank"] = u.groupby("date")[sig].rank(pct=True)
    top = u[u["rank"] >= 0.9].assign(side=int(sign))
    bot = u[u["rank"] <= 0.1].assign(side=int(-sign))
    ent = pd.concat([top, bot])[["date", "act_symbol", "side"]]
    print(f"signal {sig} sign {sign:+.0f}: {len(ent):,} entries over {ent.date.nunique()} weeks")

    months = sorted({d.strftime("%Y-%m") for d in ent.date.unique()})
    months = sorted(set(months) | {(pd.Timestamp(m + "-01") + pd.offsets.MonthBegin(1)).strftime("%Y-%m") for m in months})
    ch = load_chain(months)
    trades = pick_legs(ch, ent)
    trades = settle(trades, ch, px)
    # invariants
    sc = trades[(trades.struct == "debit") & trades.spot_T.notna()]
    itm_short = np.where(sc.call_put == "Call", sc.spot_T > sc.strike_s, sc.spot_T < sc.strike_s).mean()
    print(f"invariant: debit spread's ~25-delta short leg finished ITM {itm_short*100:.1f}% of the time "
          f"(mean |delta| at entry {sc.delta_s.abs().mean():.2f})")
    print(f"invariant: debit pnl_expiry range [{trades[trades.struct=='debit'].pnl_expiry.min():.2f}, "
          f"{trades[trades.struct=='debit'].pnl_expiry.max():.2f}] of max risk (must be >= -1)")
    report(trades, "ALL entries (signal-selected, both sides)")
    report(trades[trades.side == 1], "bullish entries")
    report(trades[trades.side == -1], "bearish entries")
    # the direction call alone: did the signal's side match the sign of the underlying move?
    tr = trades.drop_duplicates(["date", "act_symbol"]).merge(
        px[["date", "act_symbol", "close"]].rename(columns={"close": "spot0"}), on=["date", "act_symbol"])
    tr["mv"] = (tr.spot_T / tr.spot0 - 1) * tr.side
    print(f"\ndirection: side matched the move to expiry {(tr.mv > 0).mean()*100:.1f}% "
          f"(n={tr.mv.notna().sum():,}), mean signed move {tr.mv.mean()*100:+.2f}%")
    for k, (a, b) in {"A 2019-21": ("2019-01-01", "2021-12-31"), "B 2022-23": ("2022-01-01", "2023-12-31"),
                      "C 2024-26": ("2024-01-01", "2026-12-31")}.items():
        s = trades[(trades.date >= a) & (trades.date <= b)]
        if len(s) > 100:
            report(s, k)
    trades.to_parquet(os.path.join(PANEL, f"vertical_{sig}.parquet"), index=False)


if __name__ == "__main__":
    main()
