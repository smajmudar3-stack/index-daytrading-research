"""mes_signals.py — live signals for the merged MES/MNQ system -> data/mes_snapshot.json.

Three components (for SPY=MES and QQQ=MNQ), with the OVERNIGHT edge as the precise headline:
  OVERNIGHT (75%): at ~3:55pm ET hold long overnight IF price>200d SMA AND VIX<20d-avg*1.2.
  GAP-FADE  (15%): if today gapped down >0.3% while >200d SMA -> buy open / sell close.
  DIP-BUY   (10%): if RSI(2)<10 while >200d SMA -> buy, exit when RSI(2)>60.
Shows exact numbers + margin-to-threshold so you can see how FIRM each signal is.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf

from idt import paths

ET = ZoneInfo("America/New_York")

# One resolver, because the two halves of this pair used to disagree. This file
# lived in 05_studies/ and wrote its snapshot next to itself, while
# mes_dashboard.py read 04_live_system/data/ — so the dashboard showed nothing no
# matter how often the signals ran. Both ends now read paths.STATE_ROOT.
OUT = os.path.join(paths.STATE_ROOT, "mes_snapshot.json")
PAIRS = [("SPY", "MES", "S&P 500", 5.0), ("QQQ", "MNQ", "Nasdaq 100", 2.0)]


def rsi(c, n=2):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100/(1 + up/(dn+1e-12))


def phase():
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return "weekend"
    hm = now.hour*60 + now.minute
    if hm < 9*60+30:
        return "pre_open"
    if hm < 9*60+45:
        return "open"
    if hm < 15*60+45:
        return "session"
    if hm < 16*60:
        return "pre_close"     # THE overnight-decision window
    return "post_close"


def compute(etf, fut, name, dollar):
    d = yf.download(etf, period="1y", interval="1d", progress=False, auto_adjust=False,
                    multi_level_index=False).rename(columns=str.lower)
    vix = yf.download("^VIX", period="3mo", interval="1d", progress=False, auto_adjust=False,
                      multi_level_index=False).rename(columns=str.lower)["close"]
    try:
        price = float(yf.Ticker(etf).history(period="1d")["Close"].iloc[-1])
        vix_now = float(yf.Ticker("^VIX").history(period="1d")["Close"].iloc[-1])
    except Exception:
        price = float(d["close"].iloc[-1]); vix_now = float(vix.iloc[-1])

    closes = d["close"].copy()
    closes.iloc[-1] = price                              # use live price as today's forming close
    sma200 = float(closes.tail(200).mean())
    above200 = price > sma200
    sma_margin = (price/sma200 - 1) * 100                # % above/below the 200d line

    vix_20 = float(vix.tail(20).mean())
    vix_thr = vix_20 * 1.2
    vix_ok = vix_now < vix_thr
    vix_margin = (vix_thr - vix_now) / vix_thr * 100     # % below threshold (headroom)

    overnight = above200 and vix_ok
    # firmness: how far both conditions are from flipping (min of the two margins, when ON)
    firmness = min(abs(sma_margin), abs(vix_margin)) if overnight else None

    r2 = float(rsi(closes, 2).iloc[-1])
    dip = (r2 < 10) and above200

    prev_close = float(d["close"].iloc[-2])
    today_open = float(d["open"].iloc[-1])
    gap = (today_open/prev_close - 1) * 100
    gap_fade = (gap < -0.3) and above200

    return {
        "etf": etf, "fut": fut, "name": name, "dollar": dollar,
        "price": round(price, 2), "sma200": round(sma200, 2), "above200": above200,
        "sma_margin": round(sma_margin, 2),
        "vix_now": round(vix_now, 2), "vix_20avg": round(vix_20, 2), "vix_thr": round(vix_thr, 2),
        "vix_ok": vix_ok, "vix_margin": round(vix_margin, 1),
        "OVERNIGHT": overnight, "firmness": round(firmness, 2) if firmness is not None else None,
        "rsi2": round(r2, 1), "DIP_BUY": dip,
        "gap": round(gap, 2), "GAP_FADE": gap_fade,
    }


def run():
    ph = phase()
    now = datetime.now(ET)
    out = {"as_of": now.strftime("%Y-%m-%d %H:%M:%S ET"), "epoch": now.timestamp(),
           "phase": ph, "signals": []}
    for etf, fut, name, dollar in PAIRS:
        try:
            out["signals"].append(compute(etf, fut, name, dollar))
        except Exception as e:
            out["signals"].append({"etf": etf, "fut": fut, "name": name, "error": str(e)[:80]})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=2, default=str)
    print(f"mes signals written {out['as_of']} phase={ph}")
    return out


if __name__ == "__main__":
    run()
