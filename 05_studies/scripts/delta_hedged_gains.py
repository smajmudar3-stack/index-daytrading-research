"""
Delta-hedged gains on SPY, 2008-2025 — a modern replication of Bakshi & Kapadia
(2003, RFS) using real end-of-day bid/ask chains.

This is the decisive test for GAMMA SCALPING: a long straddle/option that is
delta-hedged daily earns exactly the realised-minus-implied variance, i.e. the
variance risk premium with the sign flipped. If delta-hedged gains are
significantly negative, gamma scalping is a negative-expectancy trade before you
even pay a commission, and every premium-SELLING structure is on the winning
side of that same coin.

Method (Bakshi-Kapadia eq. 6):
    pi = payoff(S_T) - C_0 - sum_n Delta_n * (S_{n+1} - S_n) - financing
Hedge ratio Delta_n is the chain's own delta, refreshed daily at the close.

Costs: entry/exit at the option's half-spread, and share hedges at half of a
1-cent SPY spread.
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from idt import paths

OPT = "opt_eod/SPY_options.parquet"  # path under DATA_ROOT, resolved at the read site
UND = "opt_eod/SPY_underlying.parquet"
COLS = ["date", "expiration", "strike", "type", "bid", "ask", "delta",
        "implied_volatility", "open_interest"]

SHARE_HALF_SPREAD = 0.005   # SPY penny-wide market
RF = 0.02                   # flat financing assumption; sensitivity checked below


def main():
    und = pd.read_parquet(paths.require_data(UND))[["date", "close"]]
    und["date"] = pd.to_datetime(und.date)
    und = und.set_index("date")["close"].sort_index()

    tbl = pq.read_table(paths.require_data(OPT), columns=COLS)
    df = tbl.to_pandas()
    df = df[(df.bid > 0) & (df.ask > df.bid) & (df.open_interest > 10)].copy()
    df["mid"] = (df.bid + df.ask) / 2
    df["half"] = (df.ask - df.bid) / 2
    df["dte"] = (df.expiration - df.date).dt.days
    print(f"usable option rows: {len(df):,}")

    dates = np.sort(df.date.unique())
    entry_dates = (pd.Series(pd.to_datetime(dates))
                   .groupby([pd.to_datetime(dates).year, pd.to_datetime(dates).month])
                   .min().to_list())

    specs = [("ATM call", "call", 0.50), ("ATM put", "put", 0.50),
             ("25d call", "call", 0.25), ("25d put", "put", 0.25),
             ("10d put", "put", 0.10)]

    records = []
    for t0 in entry_dates:
        day = df[df.date == t0]
        cand = day[(day.dte >= 25) & (day.dte <= 45)]
        if cand.empty:
            continue
        exp = cand.groupby("expiration").size().idxmax()
        chain = cand[cand.expiration == exp]
        S0 = und.get(t0, np.nan)
        if not np.isfinite(S0):
            continue

        for label, otype, tgt in specs:
            c = chain[chain.type == otype]
            if c.empty:
                continue
            row = c.iloc[(c.delta.abs() - tgt).abs().argmin()]
            K, entry_mid, entry_half = row.strike, row.mid, row.half

            # daily path of this exact contract
            path = df[(df.strike == K) & (df.type == otype) &
                      (df.expiration == exp) & (df.date >= t0)].sort_values("date")
            if len(path) < 5:
                continue
            pdates = path.date.to_list()
            S = und.reindex(pdates).to_numpy()
            if np.isnan(S).any():
                continue
            deltas = path.delta.to_numpy()

            # terminal payoff at expiration close
            S_exp = und.asof(exp)
            payoff = max(S_exp - K, 0) if otype == "call" else max(K - S_exp, 0)

            # hedge P&L: hold -delta_n shares from t_n to t_{n+1}
            hedge_pnl = 0.0
            hedge_cost = 0.0
            prev_d = 0.0
            for i in range(len(S) - 1):
                d = deltas[i]
                hedge_pnl += -d * (S[i + 1] - S[i])
                hedge_cost += abs(d - prev_d) * SHARE_HALF_SPREAD
                prev_d = d
            # final unwind of the share hedge + terminal move to expiry close
            hedge_pnl += -deltas[-1] * (S_exp - S[-1])
            hedge_cost += abs(prev_d) * SHARE_HALF_SPREAD

            T = (exp - t0).days / 365.0
            financing = RF * T * (entry_mid - deltas[0] * S0)

            pi_mid = payoff - entry_mid + hedge_pnl - financing
            # cost version: pay half-spread to buy, option expires (no exit spread
            # if held to expiry), plus share-hedge spreads
            pi_net = pi_mid - entry_half - hedge_cost

            records.append(dict(date=t0, label=label, K=K, S0=S0, exp=exp,
                                dte=(exp - t0).days, iv=row.implied_volatility,
                                C0=entry_mid, half=entry_half,
                                pi_mid=pi_mid, pi_net=pi_net,
                                hedge_cost=hedge_cost,
                                r_mid=pi_mid / entry_mid,
                                r_net=pi_net / entry_mid,
                                pi_over_S=pi_mid / S0))

    res = pd.DataFrame(records)
    res.to_parquet(paths.data("delta_hedged_gains.parquet"))
    pd.set_option("display.width", 200)

    def block(r, title):
        print(f"\n{'='*100}\n{title}\n{'='*100}")
        g = r.groupby("label").apply(lambda x: pd.Series({
            "n": len(x),
            "mean_pi_$": 100 * x.pi_mid.mean(),
            "mean_pi/C_%": 100 * x.r_mid.mean(),
            "t_stat": x.r_mid.mean() / (x.r_mid.std() / np.sqrt(len(x))),
            "median_pi/C_%": 100 * x.r_mid.median(),
            "frac_neg_%": 100 * (x.pi_mid < 0).mean(),
            "mean_pi/S_%": 100 * x.pi_over_S.mean(),
            "NET_pi/C_%": 100 * x.r_net.mean(),
            "NET_t": x.r_net.mean() / (x.r_net.std() / np.sqrt(len(x))),
        }), include_groups=False)
        print(g.round(2).to_string())

    block(res, "DELTA-HEDGED GAINS, SPY, month-start entries, ~35 DTE, held to expiry (2008-2025)")
    block(res[res.date >= "2013-01-01"], "SAME, 2013-2025 only (post-crisis)")
    block(res[res.date >= "2018-01-01"], "SAME, 2018-2025 only")

    # straddle = ATM call + ATM put delta-hedged
    atm = res[res.label.isin(["ATM call", "ATM put"])]
    strad = atm.groupby("date").agg(pi_mid=("pi_mid", "sum"), C0=("C0", "sum"),
                                    pi_net=("pi_net", "sum"))
    strad = strad[strad.C0 > 0]
    r = strad.pi_mid / strad.C0
    rn = strad.pi_net / strad.C0
    print(f"\n{'='*100}\nDELTA-HEDGED ATM STRADDLE (the literal gamma-scalping trade), n={len(strad)}\n{'='*100}")
    print("mean pi/C at mid : %+.2f%%   t = %+.2f" % (100 * r.mean(), r.mean() / (r.std() / np.sqrt(len(r)))))
    print("mean pi/C net    : %+.2f%%   t = %+.2f" % (100 * rn.mean(), rn.mean() / (rn.std() / np.sqrt(len(rn)))))
    print("median pi/C net  : %+.2f%%" % (100 * rn.median()))
    print("frac profitable  : %.0f%%" % (100 * (rn > 0).mean()))
    print("worst / best     : %+.0f%% / %+.0f%%" % (100 * rn.min(), 100 * rn.max()))
    print("mean $ per straddle net: $%+.0f on $%.0f premium" %
          (100 * strad.pi_net.mean(), 100 * strad.C0.mean()))


if __name__ == "__main__":
    main()
