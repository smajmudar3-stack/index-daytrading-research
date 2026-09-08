"""Intraday VWAP MOMENTUM — trade WITH the extension (the mirror of the losing fade).

Enter in the direction of the stretch when price pushes k*sigma from session VWAP; stop
if it falls back through VWAP (tight); let winners run to the close. If intraday moves
persist (the fade lost with t~-7), this should be net positive. Costs 3 bps round trip.
Also test in R-multiples (risk = entry->VWAP distance) since that's how you'd size it.
"""
import glob
import numpy as np
import pandas as pd

from idt import paths

RT = 0.0003


def load_minute(tk):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(paths.require_data("minute", tk) + "/*.parquet"))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index = df.index.tz_convert("America/New_York")
    df = df.between_time("09:30", "15:59")
    df["day"] = df.index.date
    return df


def vwap_momentum(df, k=1.5, entry_from="09:45", entry_to="14:30", one_trade=True):
    rets, Rs = [], []
    for day, g in df.groupby("day"):
        if len(g) < 60:
            continue
        tp = (g["high"] + g["low"] + g["close"]) / 3
        vwap = (tp * g["volume"]).cumsum() / g["volume"].cumsum().replace(0, np.nan)
        dev = g["close"] - vwap
        sig = dev.expanding(min_periods=15).std()
        z = dev / sig
        in_pos = 0; entry = 0.0; vw_at = 0.0
        for ts, c, zz, vw in zip(g.index, g["close"], z, vwap):
            if np.isnan(zz):
                continue
            t = ts.strftime("%H:%M")
            if in_pos == 0 and entry_from <= t < entry_to:
                if zz >= k:
                    in_pos, entry, vw_at = 1, c, vw
                elif zz <= -k:
                    in_pos, entry, vw_at = -1, c, vw
            elif in_pos != 0:
                back_to_vwap = (in_pos == 1 and c <= vw) or (in_pos == -1 and c >= vw)
                eod = t >= "15:58"
                if back_to_vwap or eod:
                    r = in_pos * (c / entry - 1) - RT
                    rets.append(r)
                    risk = abs(entry - vw_at) / entry
                    if risk > 0:
                        Rs.append((in_pos * (c / entry - 1) - RT) / risk)
                    in_pos = 0
                    if one_trade:
                        break
    return pd.Series(rets), pd.Series(Rs)


def report(name, r, R):
    r = r.dropna()
    if len(r) < 20:
        print(f"  {name:32} n={len(r)} too few"); return
    exp = r.mean(); wl = (r > 0).mean()
    g = r[r > 0].sum(); l = -r[r < 0].sum(); pf = g / l if l > 0 else np.inf
    t = r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0
    expR = R.mean() if len(R) else 0
    print(f"  {name:32} exp {exp*100:+.3f}%  {expR:+.3f}R  win% {wl*100:4.1f}  PF {pf:4.2f}  "
          f"t {t:+4.1f}  ~{r.mean()*len(r)/2*100:+.0f}%/yr  n={len(r)}")


def main():
    for tk in ["QQQ", "SPY"]:
        df = load_minute(tk)
        print(f"\n===== {tk}  ({df['day'].nunique()} sessions) — VWAP MOMENTUM (trade with the stretch) =====")
        for k in (1.0, 1.5, 2.0):
            r, R = vwap_momentum(df, k=k, one_trade=True)
            report(f"k={k}, 1 trade/day", r, R)
        r, R = vwap_momentum(df, k=1.5, one_trade=False)
        report("k=1.5, multi-trade/day", r, R)


if __name__ == "__main__":
    main()
