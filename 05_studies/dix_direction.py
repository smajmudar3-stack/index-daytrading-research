"""dix_direction.py — Can DIX give DIRECTION on negative-gamma days? (GEX can't — proven.)

SqueezeMetrics' published thesis: DIX (Dark Index = share of volume executing as dark-pool BUYING)
is a bullish-accumulation gauge. Their headline combo: HIGH DIX + LOW/NEG GEX = bullish (institutions
buying into a volatile, dealer-amplified tape). GEX sizes the move; DIX may pick the side.

Test (DIX & GEX both from PRIOR close, lag 1 => known at today's open, zero look-ahead):
  target = today's OPEN->CLOSE return (what a naked directional 0DTE captures if entered near open)
  Does high prior-DIX predict a green day? Especially WITHIN the negative/low-gamma bucket where
  the move is big enough for a naked long to pay?
"""
import pandas as pd
from scipy import stats
import yfinance as yf

from idt import paths


def rpt(lab, sub):
    if len(sub) < 20:
        print(f"  {lab:<32} n={len(sub)} (too few)"); return
    hi = sub[sub["dix_z"] > 0.5]["oc"]; lo = sub[sub["dix_z"] < -0.5]["oc"]
    t, p = stats.ttest_ind(hi, lo, equal_var=False, nan_policy="omit")
    corr = sub[["dix_z", "oc"]].corr().iloc[0, 1]
    print(f"  {lab:<32} highDIX oc {hi.mean():+.3f}% (win {(hi>0).mean()*100:.0f}%, n{len(hi)}) | "
          f"lowDIX oc {lo.mean():+.3f}% (win {(lo>0).mean()*100:.0f}%, n{len(lo)}) | t {t:+.2f} p {p:.3f} | corr {corr:+.3f}")


def main():
    G = pd.read_csv(paths.require_data("squeeze_dix_gex.csv"), parse_dates=["date"]).sort_values("date")
    spy = yf.download("SPY", start="2011-05-01", interval="1d", progress=False,
                      auto_adjust=True, multi_level_index=False).rename(columns=str.lower).reset_index()
    spy.columns = [str(c).lower() for c in spy.columns]
    spy["date"] = pd.to_datetime(spy["date"]).dt.tz_localize(None)

    d = spy.merge(G, on="date", how="inner").sort_values("date").reset_index(drop=True)
    d["dix_prev"] = d["dix"].shift(1)                      # prior-close DIX = tradeable at open
    d["gex_prev"] = d["gex"].shift(1)
    d["dix_z"] = (d["dix_prev"] - d["dix_prev"].rolling(252, min_periods=60).mean()) / d["dix_prev"].rolling(252, min_periods=60).std()
    d["gz"] = (d["gex_prev"] - d["gex_prev"].rolling(252, min_periods=60).mean()) / d["gex_prev"].rolling(252, min_periods=60).std()
    d["neg"] = d["gex_prev"] < 0
    d["oc"] = (d["close"] - d["open"]) / d["open"] * 100   # today open->close %  (the naked-directional target)
    d["c2c"] = d["close"].pct_change().shift(-1) * 100      # next-day close-to-close (swing check)
    d = d.dropna(subset=["dix_z", "gz", "oc"]).reset_index(drop=True)
    print(f"sample {len(d)} days {d.date.min().date()}->{d.date.max().date()}\n")

    print("═══ DIX -> same-day open→close direction (naked 0DTE target) ═══")
    rpt("ALL days", d)
    rpt("NEGATIVE gamma days", d[d["neg"]])
    rpt("LOW gamma (gz<-0.5)", d[d["gz"] < -0.5])
    rpt("HIGH gamma (gz>+0.5)", d[d["gz"] > 0.5])

    print("\n═══ The SqueezeMetrics combo: high DIX & low gamma vs everything else ═══")
    combo = d[(d["dix_z"] > 0.5) & (d["gz"] < -0.5)]
    rest = d.drop(combo.index)
    t, p = stats.ttest_ind(combo["oc"], rest["oc"], equal_var=False)
    print(f"  high-DIX + low-GEX: oc {combo['oc'].mean():+.3f}% win {(combo['oc']>0).mean()*100:.0f}% (n{len(combo)})")
    print(f"  everything else:    oc {rest['oc'].mean():+.3f}% win {(rest['oc']>0).mean()*100:.0f}% (n{len(rest)})")
    print(f"  Welch t {t:+.2f} p {p:.3f}")

    print("\n═══ next-day close-to-close (swing horizon, for context) ═══")
    for lab, sub in [("high-DIX+low-GEX", combo), ("all", d)]:
        s = sub["c2c"].dropna()
        print(f"  {lab:<20} c2c {s.mean():+.3f}% win {(s>0).mean()*100:.0f}% (n{len(s)})")


if __name__ == "__main__":
    main()
