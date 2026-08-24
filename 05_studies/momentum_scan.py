"""Scan liquid optionable names across NON-tech industries for the cleanest idiosyncratic
trend (momentum continuation = the most robust directional edge, and it doesn't hinge on
the Fed). Rank by trend quality + relative strength; flag beta (FOMC sensitivity)."""
import numpy as np
import yfinance as yf

UNIV = {
    "Energy": ["XOM","CVX","COP","OXY","SLB","MPC","PSX"],
    "Pharma/Health": ["LLY","UNH","JNJ","ABBV","MRK","PFE","ISRG","VRTX","REGN","BMY","GILD"],
    "Staples": ["PG","KO","PEP","COST","WMT","CL","MO","KMB"],
    "Industrials": ["CAT","DE","HON","UNP","GE","RTX","LMT","ETN","EMR"],
    "Financials": ["JPM","GS","V","MA","AXP","BRK-B","SCHW"],
    "Materials/Gold": ["FCX","NEM","LIN","SHW","NUE","GOLD"],
    "Utilities": ["NEE","DUK","SO","D"],
    "Cons.Disc": ["HD","NKE","SBUX","LOW","MCD","TJX"],
}
ALL = [(t, s) for s, ts in UNIV.items() for t in ts]


def line(r, tag=None):
    d = tag or ("UP" if r["up"] else ("DN" if r["dn"] else "  "))
    return ("  {tk:5} {sec:14} {d} ${last:>7} | m20 {m20:+5.1f}% m60 {m60:+6.1f}% "
            "m120 {m120:+6.1f}% | {fh:+5.1f}% frm 52wH | beta {beta}").format(
        tk=r["tk"], sec=r["sec"], d=d, last=r["last"], m20=r["m20"]*100, m60=r["m60"]*100,
        m120=r["m120"]*100, fh=r["frm_hi"]*100, beta=r["beta"])


def main():
    spy = yf.download("SPY", period="1y", interval="1d", progress=False, auto_adjust=True, multi_level_index=False)["Close"]
    spy_ret = spy.pct_change()

    rows = []
    for tk, sec in ALL:
        try:
            c = yf.download(tk, period="1y", interval="1d", progress=False, auto_adjust=True, multi_level_index=False)["Close"].dropna()
            if len(c) < 200:
                continue
        except Exception:
            continue
        last = float(c.iloc[-1])
        sma50 = float(c.tail(50).mean()); sma200 = float(c.tail(200).mean())
        m20 = last / float(c.iloc[-21]) - 1
        m60 = last / float(c.iloc[-61]) - 1
        m120 = last / float(c.iloc[-121]) - 1
        hi52 = float(c.max()); lo52 = float(c.min())
        frm_hi = last / hi52 - 1
        # beta to SPY (1y daily)
        r = c.pct_change().reindex(spy_ret.index).dropna()
        sr = spy_ret.reindex(r.index)
        beta = float(np.cov(r, sr)[0, 1] / np.var(sr))
        # trend score: aligned MAs + momentum, direction-agnostic magnitude
        up = (last > sma50 > sma200)
        dn = (last < sma50 < sma200)
        score = (m60 * 0.5 + m120 * 0.3 + m20 * 0.2)
        rows.append(dict(tk=tk, sec=sec, last=round(last, 2), m20=m20, m60=m60, m120=m120,
                         frm_hi=frm_hi, beta=round(beta, 2), up=up, dn=dn, score=score))

    ups = sorted([r for r in rows if r["up"]], key=lambda r: r["score"], reverse=True)[:8]
    dns = sorted([r for r in rows if r["dn"]], key=lambda r: r["score"])[:8]
    lowb = sorted([r for r in rows if (r["up"] or r["dn"]) and r["beta"] < 0.8],
                  key=lambda r: abs(r["score"]), reverse=True)[:8]
    print("=== STRONGEST UPTRENDS (last>50d>200d) ===")
    for r in ups: print(line(r, "UP"))
    print("\n=== STRONGEST DOWNTRENDS (last<50d<200d) ===")
    for r in dns: print(line(r, "DN"))
    print("\n=== LOWEST-BETA strong trends (least FOMC-sensitive, beta<0.8) ===")
    for r in lowb: print(line(r))


if __name__ == "__main__":
    main()
