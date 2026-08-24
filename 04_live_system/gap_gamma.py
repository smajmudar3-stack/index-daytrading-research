"""gap_gamma.py — does the OVERNIGHT GAP interact with gamma regime to predict intraday direction?

Mechanism: in a LONG-gamma (pin) regime dealers fade moves → a gap should MEAN-REVERT (fade) intraday.
In a SHORT/low-gamma regime dealers amplify → a gap should CONTINUE. If real, this is a same-day
direction input: 'gapped up into high gamma → fade (bearish intraday); gapped up in low gamma → ride'.
Prior-close GEX (lag 1) = tradeable at the open. Target = open→close return.
"""
import numpy as np
import pandas as pd
from scipy import stats
import yfinance as yf

G = pd.read_csv("data/squeeze_dix_gex.csv", parse_dates=["date"]).sort_values("date")
spy = yf.download("SPY", start="2011-05-01", interval="1d", progress=False,
                  auto_adjust=True, multi_level_index=False).rename(columns=str.lower).reset_index()
spy.columns = [str(c).lower() for c in spy.columns]
spy["date"] = pd.to_datetime(spy["date"]).dt.tz_localize(None)

d = spy.merge(G, on="date", how="inner").sort_values("date").reset_index(drop=True)
d["gz"] = ((d.gex - d.gex.rolling(252, min_periods=60).mean()) / d.gex.rolling(252, min_periods=60).std()).shift(1)
d["prev_close"] = d["close"].shift(1)
d["gap"] = (d["open"] / d["prev_close"] - 1) * 100          # overnight gap %
d["oc"] = (d["close"] - d["open"]) / d["open"] * 100        # intraday open->close %
d = d.dropna(subset=["gz", "gap", "oc"]).reset_index(drop=True)
print(f"sample {len(d)} days\n")

# only meaningful gaps
sig = d[d["gap"].abs() > 0.15].copy()
sig["gap_dir"] = np.sign(sig["gap"])
sig["continue"] = sig["oc"] * sig["gap_dir"]      # >0 = gap continued, <0 = faded

print("Does gap CONTINUE (+) or FADE (-) intraday, by gamma regime?  (mean of oc*sign(gap))")
print(f"{'regime':<24}{'n':>6}{'continue%mean':>15}{'win(cont)':>11}{'t':>7}")
for lab, mask in [("HIGH gamma (gz>0.5, pin)", sig.gz > 0.5),
                  ("MID gamma (-.5..5)", sig.gz.between(-0.5, 0.5)),
                  ("LOW gamma (gz<-0.5)", sig.gz < -0.5),
                  ("NEG gamma (gex<0)", sig.gex < 0)]:
    s = sig[mask]["continue"]
    if len(s) < 20:
        print(f"{lab:<24}{len(s):>6}  too few"); continue
    t, p = stats.ttest_1samp(s, 0)
    print(f"{lab:<24}{len(s):>6}{s.mean():>+15.3f}{(s>0).mean()*100:>10.0f}%{t:>+7.2f}  p{p:.3f}")

# the tradeable read: sign of the predicted oc = gap_dir * (continue if low gamma else fade if high gamma)
print("\nImplied same-day direction rule test (predict oc sign):")
sig["pred"] = np.where(sig.gz > 0.5, -sig.gap_dir,          # high gamma -> fade the gap
                np.where(sig.gz < -0.5, sig.gap_dir, 0))    # low gamma -> ride the gap
act = sig[sig.pred != 0].copy()
act["hit"] = (np.sign(act.oc) == act.pred)
print(f"  n={len(act)}  directional-hit={act.hit.mean()*100:.0f}%  "
      f"avg oc in predicted dir={ (act.oc*act.pred).mean():+.3f}%  "
      f"t={stats.ttest_1samp(act.oc*act.pred,0)[0]:+.2f}")
print("  (baseline green rate ~54%; >56-57% hit with t>2 = a usable direction input)")
