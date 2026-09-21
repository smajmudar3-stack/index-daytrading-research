"""xsec_options_panel.py — one row per (date, name) of options-implied features, from the
Dolt EOD chains dumped by 05_studies/scripts/build_opt_panel.py.

WHY THIS EXISTS. The weekly book's direction call was right 37.6% of the time on its first
117 closed cards (2026-09-03 .. 09-21). Every voter behind it is either a price transform,
a human macro read, or a same-day vendor number with no history. The published predictors
that actually work at a one-week horizon are OPTIONS-IMPLIED and cross-sectional -- the
call-put IV spread (Cremers & Weinbaum 2010), the smirk (Xing, Zhang & Zhao 2010), changes
in call/put IV (An, Ang, Bali & Cakici 2014), IV minus realised for the option's own return
(Goyal & Saretto 2009) -- and this repo has seven years of real chains to test them on.
This file computes those features; `xsec_predictors_test.py` scores them.

FEATURES (all from the SAME day's chain and closes, nothing forward-looking):
  atm_iv         mean of the nearest-to-50-delta call and put IV, expiry nearest 30d in [10,60]
  cw_spread      mean over matched strikes (0.8<=K/S<=1.2, both bids > 0) of call IV - put IV
  smirk          IV of the OTM put nearest K/S=0.95 (band 0.80..0.95) minus the ATM call IV
  rr25           IV(OTM call nearest K/S=1.05) - IV(OTM put nearest 0.95): the risk reversal
  term_slope     atm_iv(near) - atm_iv(far), far = expiry nearest 75d and >= near+14d
  atm_spread     (ask-bid)/mid averaged over the ATM call and put -- the cost of expressing anything
  straddle_pct   (ATM call mid + ATM put mid) / spot -- the market's expected move to that expiry
  near_dte       DTE of the near expiry

The chain is a thinned one (~11 strikes a side, 3 expiries out to 100d), so every band is a
"nearest to" rather than an exact strike. That is the same limitation the live engine has on a
yfinance ladder, which makes it the right data to test on.
"""
import glob
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
OUT = os.path.join(PANEL, "features.parquet")


def load_close():
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"), columns=["date", "act_symbol", "close"])
    px["act_symbol"] = px["act_symbol"].astype(str)
    return px


def _nearest(df, key, target, group=("date", "act_symbol")):
    """Row per group whose `key` is nearest `target`."""
    d = (df[key] - target).abs()
    idx = d.groupby([df[g] for g in group]).idxmin()
    return df.loc[idx.values]


def month_features(f, px):
    ch = pd.read_parquet(f)
    ch["act_symbol"] = ch["act_symbol"].astype(str)
    ch = ch.merge(px, on=["date", "act_symbol"], how="inner")
    ch = ch[(ch.close > 0) & (ch.bid >= 0) & (ch.ask > 0) & (ch.ask >= ch.bid)]
    ch["dte"] = (ch.expiration - ch.date).dt.days
    ch = ch[(ch.dte >= 5) & (ch.dte <= 100)]
    ch["mny"] = ch.strike / ch.close
    ch["mid"] = (ch.bid + ch.ask) / 2
    ch["iv"] = ch.vol.where((ch.vol > 0.02) & (ch.vol < 4.0))
    ch["adelta"] = ch.delta.abs()

    # expiry table per (date, symbol)
    ex = ch[["date", "act_symbol", "expiration", "dte"]].drop_duplicates()
    near_pool = ex[(ex.dte >= 10) & (ex.dte <= 60)]
    near = _nearest(near_pool, "dte", 30)[["date", "act_symbol", "expiration", "dte"]]
    near = near.rename(columns={"expiration": "near_exp", "dte": "near_dte"})
    ex2 = ex.merge(near, on=["date", "act_symbol"])
    far_pool = ex2[ex2.dte >= ex2.near_dte + 14]
    far = _nearest(far_pool, "dte", 75)[["date", "act_symbol", "expiration"]].rename(columns={"expiration": "far_exp"})

    key = ["date", "act_symbol"]
    n = ch.merge(near, on=key)
    n = n[n.expiration == n.near_exp]
    calls, puts = n[n.call_put == "Call"], n[n.call_put == "Put"]

    atm_c = _nearest(calls[calls.iv.notna()], "adelta", 0.5)[key + ["iv", "mid", "bid", "ask", "mny"]]
    atm_p = _nearest(puts[puts.iv.notna()], "adelta", 0.5)[key + ["iv", "mid", "bid", "ask", "mny"]]
    atm = atm_c.merge(atm_p, on=key, suffixes=("_c", "_p"))
    atm["atm_iv"] = (atm.iv_c + atm.iv_p) / 2
    atm["atm_spread"] = ((atm.ask_c - atm.bid_c) / atm.mid_c.replace(0, np.nan)
                         + (atm.ask_p - atm.bid_p) / atm.mid_p.replace(0, np.nan)) / 2
    atm["atm_iv_c"], atm["atm_iv_p"] = atm.iv_c, atm.iv_p
    feats = atm[key + ["atm_iv", "atm_iv_c", "atm_iv_p", "atm_spread"]].merge(near, on=key)

    # straddle cost as % of spot: ATM call mid + ATM put mid, at the strike nearest spot
    sc = _nearest(calls, "mny", 1.0)[key + ["mid", "strike"]]
    sp = puts.merge(sc[key + ["strike"]], on=key + ["strike"])[key + ["mid"]]
    st = sc.merge(sp, on=key, suffixes=("_c", "_p")).merge(px, on=key)
    st["straddle_pct"] = (st.mid_c + st.mid_p) / st.close
    feats = feats.merge(st[key + ["straddle_pct"]], on=key, how="left")

    # smirk (XZZ): OTM put nearest K/S 0.95 within [0.80, 0.95], minus ATM call IV
    op = puts[(puts.mny >= 0.80) & (puts.mny <= 0.95) & puts.iv.notna()]
    op = _nearest(op, "mny", 0.95)[key + ["iv"]].rename(columns={"iv": "otm_put_iv"})
    oc = calls[(calls.mny >= 1.05) & (calls.mny <= 1.20) & calls.iv.notna()]
    oc = _nearest(oc, "mny", 1.05)[key + ["iv"]].rename(columns={"iv": "otm_call_iv"})
    feats = feats.merge(op, on=key, how="left").merge(oc, on=key, how="left")
    feats["smirk"] = feats.otm_put_iv - feats.atm_iv_c
    feats["rr25"] = feats.otm_call_iv - feats.otm_put_iv

    # Cremers-Weinbaum: matched call/put pairs, unweighted (no OI in this chain)
    pr = calls[(calls.mny >= 0.8) & (calls.mny <= 1.2) & (calls.bid > 0) & calls.iv.notna()][key + ["strike", "iv"]]
    pp = puts[(puts.mny >= 0.8) & (puts.mny <= 1.2) & (puts.bid > 0) & puts.iv.notna()][key + ["strike", "iv"]]
    pair = pr.merge(pp, on=key + ["strike"], suffixes=("_c", "_p"))
    pair["d"] = pair.iv_c - pair.iv_p
    cw = pair.groupby(key).agg(cw_spread=("d", "mean"), cw_n=("d", "size")).reset_index()
    feats = feats.merge(cw, on=key, how="left")

    # term slope
    fr = ch.merge(far, on=key)
    fr = fr[(fr.expiration == fr.far_exp) & fr.iv.notna()]
    fc = _nearest(fr[fr.call_put == "Call"], "adelta", 0.5)[key + ["iv"]]
    fp = _nearest(fr[fr.call_put == "Put"], "adelta", 0.5)[key + ["iv"]]
    fa = fc.merge(fp, on=key, suffixes=("_c", "_p"))
    fa["far_iv"] = (fa.iv_c + fa.iv_p) / 2
    feats = feats.merge(fa[key + ["far_iv"]], on=key, how="left")
    feats["term_slope"] = feats.atm_iv - feats.far_iv
    return feats.drop(columns=["near_exp"])


def main():
    px = load_close()
    files = sorted(glob.glob(os.path.join(PANEL, "chain_*.parquet")))
    if len(sys.argv) > 1:
        files = [f for f in files if any(a in f for a in sys.argv[1:])]
    out, t0 = [], time.time()
    for f in files:
        fe = month_features(f, px)
        out.append(fe)
        print(f"{os.path.basename(f)} {len(fe):>7} rows {time.time()-t0:6.0f}s", flush=True)
    feats = pd.concat(out, ignore_index=True)
    dst = OUT if len(sys.argv) == 1 else OUT.replace(".parquet", "_partial.parquet")
    feats.to_parquet(dst, index=False)
    print("wrote", dst, feats.shape)
    print(feats.describe().T.to_string())


if __name__ == "__main__":
    main()
