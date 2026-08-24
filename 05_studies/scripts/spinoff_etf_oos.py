"""Real-money out-of-sample test of the spinoff anomaly.

CSD = Invesco S&P Spin-Off ETF, launched 2006-12-15, tracks an index of recently
spun-off US companies. Compared against broad-market and size-matched benchmarks.
Returns are TOTAL returns (Yahoo adjusted close, dividends reinvested) and are
NET of the fund's expense ratio and its own internal trading costs -- i.e. this is
a genuine net-of-cost, investable track record, not a paper portfolio.
"""
import json, math, os, time, urllib.request
import statistics as st

SCRATCH = "/private/tmp/claude-501/-Users-sahilmajmudar/c703fa96-a221-4df1-a82d-b31b1bf84807/scratchpad"
TICKERS = ["CSD", "SPY", "IWM", "MDY", "IJR"]
P1, P2 = 1160000000, int(time.time())


def fetch(t):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}"
           f"?period1={P1}&period2={P2}&interval=1mo")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                d = json.load(r)
            res = d["chart"]["result"][0]
            ts = res["timestamp"]
            adj = res["indicators"]["adjclose"][0]["adjclose"]
            out = {}
            for a, b in zip(ts, adj):
                if b is not None:
                    out[time.strftime("%Y-%m", time.gmtime(a))] = float(b)
            return out
        except Exception as e:
            time.sleep(3 * (i + 1))
    return {}


def rets(px):
    ks = sorted(px)
    return {ks[i]: px[ks[i]] / px[ks[i - 1]] - 1 for i in range(1, len(ks))}


def stats(r, label):
    v = list(r.values())
    n = len(v)
    m = st.mean(v)
    s = st.stdev(v)
    cum = 1.0
    for x in v:
        cum *= (1 + x)
    yrs = n / 12
    cagr = cum ** (1 / yrs) - 1
    sharpe = (m / s) * math.sqrt(12)
    t = m / (s / math.sqrt(n))
    print(f"  {label:<6} n={n:<4} CAGR={cagr*100:+6.2f}%  vol={s*math.sqrt(12)*100:5.1f}%  "
          f"SR={sharpe:+.2f}  mean={m*100:+.3f}%/mo  t={t:+.2f}  cum={cum:.2f}x")
    return cagr, m, s


def alpha(ry, rx, ylab, xlab):
    ks = sorted(set(ry) & set(rx))
    y = [ry[k] for k in ks]
    x = [rx[k] for k in ks]
    n = len(ks)
    mx, my = st.mean(x), st.mean(y)
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / (n - 1)
    var = sum((a - mx) ** 2 for a in x) / (n - 1)
    beta = cov / var
    a = my - beta * mx
    resid = [b - (a + beta * c) for c, b in zip(x, y)]
    se = st.stdev(resid) / math.sqrt(n)
    print(f"  {ylab} vs {xlab:<4}: beta={beta:.2f}  alpha={a*100:+.3f}%/mo "
          f"({a*1200:+.2f}%/yr)  t(alpha)={a/se:+.2f}  n={n}")


def main():
    data = {}
    for t in TICKERS:
        px = fetch(t)
        if px:
            data[t] = rets(px)
            print(f"fetched {t}: {len(px)} monthly obs {min(px)}..{max(px)}")
        time.sleep(1)

    print("\n===== Full history (CSD inception onward) =====")
    csd = data["CSD"]
    common = sorted(csd)
    lo = min(common)
    for t in TICKERS:
        if t in data:
            r = {k: v for k, v in data[t].items() if k >= lo}
            stats(r, t)

    print("\n===== CAPM-style alpha of CSD vs benchmarks (full history) =====")
    for b in ["SPY", "IWM", "MDY", "IJR"]:
        if b in data:
            alpha(csd, data[b], "CSD", b)

    print("\n===== Sub-periods =====")
    for lab, a, z in [("2007-2014", "2007-01", "2014-12"),
                      ("2015-2024", "2015-01", "2024-12"),
                      ("2015-present", "2015-01", "2099-12")]:
        print(f"\n-- {lab}")
        sub = {t: {k: v for k, v in data[t].items() if a <= k <= z} for t in data}
        for t in TICKERS:
            if t in sub and len(sub[t]) > 12:
                stats(sub[t], t)
        for b in ["SPY", "IWM"]:
            if b in sub and len(sub["CSD"]) > 12:
                alpha(sub["CSD"], sub[b], "CSD", b)


if __name__ == "__main__":
    main()
