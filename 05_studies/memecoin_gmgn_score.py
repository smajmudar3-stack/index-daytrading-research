"""memecoin_gmgn_score.py — scores what GMGN shows: copy-trading its smart-money and KOL
buys at a copier's latency, and its sixty launch fields as predictors. Reads
`04_live_system/gmgn_recorder.py`'s database; every return is settled on GMGN's own
candles (30-second bars for the copy trades, 1-minute for the launches).

COPY-TRADE REPLAY. For every smart-money / KOL BUY the recorder saw: the leader's price is
the trade's own price_usd; the COPIER's fill is the first 30-second bar's close at or after
trade_ts + LAG (30 s and 60 s, the two latencies a GMGN copy-trade or a human on the screen
can hope for); exits at +5 m, +15 m, +60 m from the copier's fill; net of 1% venue + 0.5%
router + 2% slippage each way (no impact term: these are tokens with a smart-money buy, so
liquidity is usually five figures; a 1%/side impact row is shown). Reported by source
(smart money vs KOL), by whether the leader was opening or adding (is_open_or_close), by
launchpad, by leader tag, and in two halves of the recording. The hit rate, the payoff,
the median, the capped mean, and the gap between the leader's price and the copier's.

LAUNCH FACTORS. For every token first seen in the trenches: the fields at first sight
against the 1-minute-candle return at +1 h and +24 h from the first bar after first sight.
Same scoring as memecoin_factors.py: fifths by factor, hit rate, payoff, IC, two halves,
the noise bar for the number of cells run.
"""
import os
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402

warnings.filterwarnings("ignore")
FEE, ROUTER, SLIP = 0.01, 0.005, 0.02
CAP = 20.0
N_TESTS = 0


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def load():
    c = sqlite3.connect(paths.state("gmgn.db"))
    tr = pd.read_sql("SELECT * FROM smart_trades", c)
    fs = pd.read_sql("SELECT * FROM first_seen", c)
    snaps = pd.read_sql("SELECT * FROM trench_snaps", c)
    kl = pd.read_sql("SELECT * FROM klines", c)
    c.close()
    return tr, fs, snaps, kl


def price_at(k, t, after=True, tol=None):
    """Close of the first bar at/after t (or last at/before). k: sorted DataFrame of one series."""
    if k.empty:
        return np.nan
    ts = k.t.values
    if after:
        i = np.searchsorted(ts, t, side="left")
        if i >= len(ts) or (tol and ts[i] - t > tol):
            return np.nan
        return k.c.values[i]
    i = np.searchsorted(ts, t, side="right") - 1
    if i < 0 or (tol and t - ts[i] > tol):
        return np.nan
    return k.c.values[i]


def copy_trades(tr, kl):
    k30 = {a: g.sort_values("t").reset_index(drop=True) for a, g in kl[kl.resolution == "30s"].groupby("address")}
    rows = []
    buys = tr[(tr.side == "buy") & tr.token.notna()]
    for r in buys.itertuples():
        k = k30.get(r.token)
        if k is None or len(k) < 5:
            continue
        d = {"tx": r.tx, "src": r.src, "tags": r.tags or "", "token": r.token, "symbol": r.symbol, "ts": r.ts, "seen": r.seen,
             "chain": getattr(r, "chain", "sol"),
             "lead_px": r.price_usd, "amount_usd": r.amount_usd, "opening": r.is_open_or_close, "launchpad": r.launchpad,
             "half": "A" if r.ts < buys.ts.min() + (buys.ts.max() - buys.ts.min()) / 2 else "B"}
        for lag in (30, 60):
            fill = price_at(k, r.ts + lag, after=True, tol=120)
            d[f"fill{lag}"] = fill
            d[f"gap{lag}"] = (fill / r.price_usd - 1) if (fill and r.price_usd) else np.nan
            for h in (300, 900, 3600):
                px = price_at(k, r.ts + lag + h, after=False, tol=180)
                d[f"r{lag}_{h}"] = (px / fill - 1) if (fill and px) else np.nan
        rows.append(d)
    return pd.DataFrame(rows)


def report_copy(d, label, impact=0.0):
    global N_TESTS
    if len(d) < 20:
        print(f"   {label:56s} n {len(d):4d} too few settled yet")
        return
    cost = 2 * (FEE + ROUTER + SLIP + impact)
    for lag in (30, 60):
        parts = []
        for h in (300, 900, 3600):
            g = d[f"r{lag}_{h}"].dropna().clip(upper=CAP)
            if len(g) < 15:
                parts.append(f"+{h//60:>2}m: n<15")
                continue
            net = (1 + g) * (1 - cost) - 1
            win, loss = net[net > 0], net[net <= 0]
            parts.append(f"+{h//60:>2}m n{len(g):4d} med {g.median()*100:+6.1f}% net {net.mean()*100:+6.1f}% hit {(net>0).mean():.2f} pay {(win.mean()/-loss.mean()) if len(loss) else np.nan:4.2f}")
            N_TESTS += 1
        gap = d[f"gap{lag}"].dropna()
        print(f"   {label:56s} lag {lag:2d}s | copier pays {gap.median()*100:+5.1f}% vs leader | " + " | ".join(parts))


def launch_factors(fs, snaps, kl):
    k1 = {a: g.sort_values("t").reset_index(drop=True) for a, g in kl[kl.resolution == "1m"].groupby("address")}
    first = snaps.sort_values("ts").drop_duplicates("address", keep="first").set_index("address")
    rows = []
    for r in fs.itertuples():
        k = k1.get(r.address)
        if k is None or len(k) < 3 or r.address not in first.index:
            continue
        p0 = price_at(k, r.ts, after=True, tol=300)
        if not p0:
            continue
        f = first.loc[r.address]
        d = {"address": r.address, "kind": r.kind, "ts": r.ts, "p0": p0}
        for h in (3600, 86400):
            px = price_at(k, r.ts + h, after=False, tol=1800)
            d[f"ret_{h}"] = (px / p0 - 1) if px else np.nan
        d["gone_1h"] = int(np.isnan(d["ret_3600"]))
        for col in ("creator_created_count", "creator_created_open_ratio", "bundler_trader_amount_rate", "top70_sniper_hold_rate",
                    "suspected_insider_hold_rate", "rat_trader_amount_rate", "rug_ratio", "smart_degen_count", "renowned_count",
                    "tg_call_count", "holder_count", "top_10_holder_rate", "fresh_wallet_rate", "progress", "market_cap", "volume_24h",
                    "buys_24h", "sells_24h", "image_dup", "twitter_dup", "is_wash_trading", "dexscr_ad"):
            d[col] = f.get(col)
        d["has_twitter"] = int(bool(f.get("twitter")))
        d["has_telegram"] = int(bool(f.get("telegram")))
        d["buy_sell_ratio"] = (f.get("buys_24h") or 0) / max((f.get("sells_24h") or 0) + 1, 1)
        rows.append(d)
    d = pd.DataFrame(rows)
    if d.empty:
        print("\nLAUNCH FACTORS: no settled launches yet")
        return d
    mid = d.ts.min() + (d.ts.max() - d.ts.min()) / 2
    d["half"] = np.where(d.ts < mid, "A", "B")
    global N_TESTS
    feats = [("creator_created_count", -1), ("creator_created_open_ratio", +1), ("bundler_trader_amount_rate", -1), ("top70_sniper_hold_rate", -1),
             ("suspected_insider_hold_rate", -1), ("rat_trader_amount_rate", -1), ("rug_ratio", -1), ("smart_degen_count", +1),
             ("renowned_count", +1), ("tg_call_count", +1), ("holder_count", +1), ("top_10_holder_rate", -1), ("fresh_wallet_rate", -1),
             ("progress", +1), ("market_cap", +1), ("volume_24h", +1), ("buy_sell_ratio", +1), ("image_dup", -1), ("twitter_dup", -1),
             ("is_wash_trading", -1), ("dexscr_ad", +1), ("has_twitter", +1), ("has_telegram", +1)]
    d["chain"] = d.address.map(fs.set_index("address").get("chain", pd.Series(dtype=object))).fillna("sol") if "chain" in fs else "sol"
    for kind in ("new_creation", "near_completion", "completed"):
        s = d[d.kind == kind]
        for y in ("ret_3600", "ret_86400"):
            x = s.dropna(subset=[y])
            if len(x) < 60:
                print(f"\n  {kind} -> {y}: n {len(x)} too few settled yet")
                continue
            by_chain = {ch: f"{g[y].median()*100:+.0f}% (n{len(g)})" for ch, g in x.groupby("chain")}
            print(f"\n  LAUNCH FACTORS, {kind} ({len(x)} tokens) -> {y}: base median {x[y].median()*100:+.1f}%, up {(x[y]>0).mean()*100:.0f}%, "
                  f"doubled {(x[y]>=1).mean()*100:.1f}%  by chain {by_chain}  [mean columns capped at {CAP:.0f}x; A/B halves]")
            out = []
            for f, sgn in feats:
                xx = x[[f, y, "half"]].dropna()
                if len(xx) < 60 or xx[f].nunique() < 2:
                    continue
                q = xx[f] if xx[f].nunique() <= 3 else pd.qcut(xx[f].rank(method="first"), 5, labels=False, duplicates="drop")
                top = xx[q == q.max()] if sgn > 0 else xx[q == q.min()]
                bot = xx[q == q.min()] if sgn > 0 else xx[q == q.max()]
                yt = top[y].clip(upper=CAP)
                win, loss = yt[yt > 0], yt[yt <= 0]
                ic = stats.spearmanr(xx[f] * sgn, xx[y])[0]
                out.append({"factor": f, "n": len(xx), "IC": ic, "t": ic * np.sqrt(len(xx)), "top_hit": (yt > 0).mean(),
                            "top_med%": top[y].median() * 100, "top_mean%": yt.mean() * 100, "payoff": (win.mean() / -loss.mean()) if len(loss) and loss.mean() < 0 else np.nan,
                            "bot_med%": bot[y].median() * 100, "A": top[top.half == "A"][y].clip(upper=CAP).mean() * 100, "B": top[top.half == "B"][y].clip(upper=CAP).mean() * 100})
                N_TESTS += 1
            if out:
                print("  " + pd.DataFrame(out).sort_values("t", ascending=False).to_string(index=False, float_format=lambda v: f"{v:8.2f}").replace("\n", "\n  "))
    return d


def main():
    pd.set_option("display.width", 250)
    tr, fs, snaps, kl = load()
    print(f"recorded: {len(tr):,} smart/KOL trades ({(tr.side=='buy').sum():,} buys) from {tr.maker.nunique()} wallets; "
          f"{len(fs):,} tokens first seen; {len(kl):,} candles; span {pd.to_datetime(tr.seen.min(), unit='s')} .. {pd.to_datetime(tr.seen.max(), unit='s')} UTC")
    ct = copy_trades(tr, kl)
    print(f"\nCOPY-TRADE REPLAY: {len(ct)} buys with 30-second candles settled (net of 1% + 0.5% + 2% slippage each way; mean columns capped at {CAP:.0f}x)")
    if len(ct):
        report_copy(ct, "ALL smart-money + KOL buys")
        report_copy(ct, "ALL, with 1%/side impact added", impact=0.01)
        for src in ("smartmoney", "kol"):
            report_copy(ct[ct.src == src], f"source = {src}")
        report_copy(ct[ct.opening == 0], "leader OPENING a position (is_open_or_close=0)")
        report_copy(ct[ct.opening == 1], "leader closing/reducing flagged as buy (=1)")
        for ch, g in ct.groupby(ct.chain.fillna("sol")):
            report_copy(g, f"chain = {ch}")
        for lp, g in ct.groupby(ct.launchpad.fillna("none")):
            report_copy(g, f"launchpad = {lp}")
        for tag in ("smart_degen", "kol", "renowned", "sniper", "arbitrager", "fresh_wallet", "bullx", "axiom", "photon", "gmgn"):
            report_copy(ct[ct.tags.str.contains(tag)], f"leader tag contains '{tag}'")
        big = ct[ct.amount_usd >= ct.amount_usd.quantile(0.75)]
        report_copy(big, "leader size top quartile")
        for h in ("A", "B"):
            report_copy(ct[ct.half == h], f"recording half {h}")
        ct.to_parquet(os.path.join(paths.DATA_ROOT, "gmgn_copy_panel.parquet"), index=False)
    lf = launch_factors(fs, snaps, kl)
    if len(lf):
        lf.to_parquet(os.path.join(paths.DATA_ROOT, "gmgn_launch_panel.parquet"), index=False)
    print(f"\nCELLS SCORED: {N_TESTS}; noise bar for the largest |t| under the null ~ {np.sqrt(2*np.log(max(N_TESTS,2))):.1f}")


if __name__ == "__main__":
    main()
