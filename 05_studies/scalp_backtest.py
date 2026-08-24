"""scalp_backtest.py — does the WALL-FADE scalp work, conditioned on gamma regime?

Thesis: on HIGH-gamma (pin) days dealers dampen moves → price reverts to VWAP → fading extensions
(short the pop / long the dip) is profitable. On LOW/short-gamma days moves trend → fading LOSES.
Earlier UNCONDITIONED VWAP mean-reversion lost hard (t=-6..-7.5); the scalp only makes sense if the
HIGH-gamma subset flips positive. Uses 2y SPY/QQQ minute bars (w/ VWAP) + prior-close GEX regime.

Event = a minute where |price-VWAP|/VWAP > threshold. Fade P&L over the next H minutes:
  fade_ret = -sign(deviation) * forward_return   (profit if price reverts toward VWAP), minus cost.
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

from idt import paths


THR = 0.0015          # 0.15% from VWAP = "extended"
H = 15                # forward horizon, minutes
COST = 0.0003         # ~3bps round-trip scalp cost (futures/tight options)


def rpt(lab, s):
    if len(s) < 50:
        print(f"  {lab:<26} n={len(s)} too few"); return
    t, p = stats.ttest_1samp(s, 0)
    bps = s.mean() * 1e4
    print(f"  {lab:<26} n={len(s):>6}  mean {bps:+6.1f}bps  win {(s>0).mean()*100:4.0f}%  t {t:+6.2f}  p {p:.3f}")


def main():
    G = pd.read_csv(paths.require_data("squeeze_dix_gex.csv"), parse_dates=["date"]).sort_values("date")
    G["gz"] = ((G.gex - G.gex.rolling(252, min_periods=60).mean()) / G.gex.rolling(252, min_periods=60).std()).shift(1)
    gz = G.set_index(G["date"].dt.date)["gz"]

    rows = []
    for f in sorted(glob.glob(paths.require_data("minute", "SPY") + "/*.parquet")):
        m = pd.read_parquet(f).between_time("09:35", "15:45")
        if "vwap" not in m.columns:
            continue
        for day, g in m.groupby(m.index.date):
            z = gz.get(day, np.nan)
            if np.isnan(z) or len(g) < 60:
                continue
            px = g["close"].values; vw = g["vwap"].values
            dev = (px - vw) / vw
            for i in range(len(g) - H):
                if abs(dev[i]) > THR:
                    fwd = (px[i + H] - px[i]) / px[i]
                    fade = -np.sign(dev[i]) * fwd - COST      # fade profit net of cost
                    rows.append((day, z, dev[i], fade))

    D = pd.DataFrame(rows, columns=["day", "gz", "dev", "fade"])
    print(f"{len(D)} fade events across {D.day.nunique()} days\n")

    print("WALL-FADE scalp P&L per event (net of 3bps), by gamma regime:")
    rpt("ALL", D.fade)
    rpt("HIGH gamma (gz>0.5)", D[D.gz > 0.5].fade)
    rpt("MID (-0.5..0.5)", D[D.gz.between(-0.5, 0.5)].fade)
    rpt("LOW gamma (gz<-0.5)", D[D.gz < -0.5].fade)
    rpt("very HIGH (gz>1)", D[D.gz > 1.0].fade)

    print("\nInterpretation: HIGH-gamma fade should be POSITIVE (t>2) for the pin-scalp to be real;")
    print("LOW-gamma fade should be negative (trend). If HIGH-gamma isn't clearly +, the scalp is NOT validated.")


if __name__ == "__main__":
    main()
