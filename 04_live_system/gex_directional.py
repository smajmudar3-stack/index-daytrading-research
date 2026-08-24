"""gex_directional.py — Does the opening drive CONTINUE to the close (naked long call/put
edge) as a function of gamma regime? 0DTE era, SPY minute bars 2024-2026.

A naked long 0DTE call/put needs the underlying to keep moving IN your direction after you
enter — that's what beats theta. So the test that maps to what the user actually trades:

  1. 09:30 open, then read the 10:00 drive direction = sign(px_10:00 - open).
  2. "Enter" a naked option that way (call if up, put if down) at 10:00.
  3. CONTINUATION = (close - px_10:00)/px_10:00 * drive_direction.
       > 0  -> drive kept going = naked directional WINS (move beats theta)
       < 0  -> reversed/chopped = naked directional LOSES (theta + reversal)
  4. Split by prior-close gamma regime (SqueezeMetrics GEX, lag 1, no look-ahead).

Hypothesis from the regime study: low/negative gamma (dealers amplify) -> strong positive
continuation; high/positive gamma (dealers pin) -> weak/negative continuation (fade + chop).
Underlying follow-through is modeled (not option premium — no intraday option history), so read
this as WHICH DAYS the drive trends, i.e. when a naked directional trade has the wind at its back.
"""
import glob
import numpy as np
import pandas as pd
from scipy import stats

G = pd.read_csv("data/squeeze_dix_gex.csv", parse_dates=["date"]).sort_values("date")
G["gex_prev"] = G["gex"].shift(1)
G["gz"] = (G["gex_prev"] - G["gex_prev"].rolling(252, min_periods=60).mean()) \
          / G["gex_prev"].rolling(252, min_periods=60).std()
G["neg"] = G["gex_prev"] < 0
gmap = G.set_index(G["date"].dt.date)[["gex_prev", "gz", "neg"]]

ENTRY = pd.Timestamp("10:00").time()      # read the drive here
OPEN = pd.Timestamp("09:30").time()
CLOSE = pd.Timestamp("15:55").time()

rows = []
for f in sorted(glob.glob("data/minute/SPY/*.parquet")):
    m = pd.read_parquet(f)
    m = m.between_time("09:30", "16:00")
    for day, g in m.groupby(m.index.date):
        g = g.between_time("09:30", "15:59")
        if len(g) < 60:
            continue
        try:
            o = g.between_time("09:30", "09:31")["open"].iloc[0]
            e_slice = g.between_time("09:59", "10:01")
            c_slice = g.between_time("15:54", "15:59")
            if e_slice.empty or c_slice.empty:
                continue
            e = e_slice["close"].iloc[-1]
            c = c_slice["close"].iloc[-1]
        except Exception:
            continue
        drive = np.sign(e - o)
        if drive == 0:
            continue
        cont = (c - e) / e * drive            # continuation in the drive direction
        early_move = abs(e - o) / o           # how big the opening drive was
        rows.append({"date": day, "drive": drive, "cont": cont, "early_move": early_move,
                     "day_range": (g["high"].max() - g["low"].min()) / o})

D = pd.DataFrame(rows)
D["gex_prev"] = D["date"].map(lambda x: gmap["gex_prev"].get(x, np.nan))
D["gz"] = D["date"].map(lambda x: gmap["gz"].get(x, np.nan))
D["neg"] = D["date"].map(lambda x: gmap["neg"].get(x, False))
D = D.dropna(subset=["gz"]).reset_index(drop=True)
print(f"sample: {len(D)} 0DTE-era days, {D.date.min()} -> {D.date.max()}\n")

def line(lab, s):
    t, p = stats.ttest_1samp(s.dropna(), 0)
    win = (s > 0).mean() * 100
    print(f"  {lab:<34} continuation avg {s.mean()*100:+.3f}%  win {win:4.1f}%  t {t:+5.2f} p {p:.3f}  (n {len(s)})")

print("═══ Opening-drive CONTINUATION to close, by gamma regime ═══")
print("(positive = drive trended = naked directional option wins)\n")
line("ALL days", D["cont"])
line("NEGATIVE gamma (prior close)", D.loc[D["neg"], "cont"])
line("POSITIVE gamma", D.loc[~D["neg"], "cont"])

print("\n  by gamma z-quintile (Q1=lowest gamma=amplify ... Q5=highest=pin):")
D["q"] = pd.qcut(D["gz"], 5, labels=[1, 2, 3, 4, 5])
for q in [1, 2, 3, 4, 5]:
    line(f"Q{q}", D.loc[D["q"] == q, "cont"])

# only take the drive when it was a REAL drive (>0.15% by 10:00) — filters noise opens
print("\n═══ Same, but only when the 10:00 drive was decisive (>0.15%) ═══")
big = D[D["early_move"] > 0.0015]
line("decisive drive, NEG gamma", big.loc[big["neg"], "cont"])
line("decisive drive, POS gamma", big.loc[~big["neg"], "cont"])
line("decisive drive, Q1 (low gamma)", big.loc[big["q"] == 1, "cont"])
line("decisive drive, Q5 (high gamma)", big.loc[big["q"] == 5, "cont"])

D.to_csv("data/gex_directional_daily.csv", index=False)
print("\nwrote data/gex_directional_daily.csv")
