"""Greeks, option pricing, and structure selection for a swing-horizon view.

Two jobs:

  1. MEASURE THE REAL COST STACK. Pull live chains for the universe and record,
     by DTE bucket and delta bucket: bid-ask as a % of premium, implied vol,
     and IV-minus-realised (the volatility risk premium). These are empirical,
     not assumed -- every downstream EV number is charged with them.

  2. PICK THE STRUCTURE. Given a directional forecast (expected move and its
     uncertainty over N days), compute the expected P&L of every candidate
     structure/strike/expiry under a realistic terminal distribution, and rank
     them. This answers "which option is best priced for this view", which is
     a different question from "which way is the stock going".

HONESTY BOUNDARY, stated because the last edge in this repo died exactly here:
option P&L for any HISTORICAL backtest is MODELLED (no historical option quotes
are available on the current data plans). Live chain data is real. So the cost
and IV inputs below are measured from the real market, but a backtested option
return remains a model output and must never be quoted as a realised result.
"""
import math
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

from idt import paths

warnings.filterwarnings("ignore")

OUT = paths.data("swing")

SQRT2PI = math.sqrt(2 * math.pi)


# --------------------------------------------------------------------------
# Black-Scholes with greeks
# --------------------------------------------------------------------------
def _nd(x):
    return math.exp(-0.5 * x * x) / SQRT2PI


def _Nd(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs(S, K, T, sigma, r=0.045, kind="call"):
    """Price + the greeks that matter for a days-to-weeks options swing.

    theta is returned PER CALENDAR DAY (the number that actually bleeds the
    account) and vega per 1 vol point, because those are the units a trader
    reasons in.
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        intrinsic = max(0.0, (S - K) if kind == "call" else (K - S))
        return {"price": intrinsic, "delta": 0.0, "gamma": 0.0,
                "theta": 0.0, "vega": 0.0, "d1": 0.0, "d2": 0.0}

    v = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / v
    d2 = d1 - v

    if kind == "call":
        price = S * _Nd(d1) - K * math.exp(-r * T) * _Nd(d2)
        delta = _Nd(d1)
        theta = (-S * _nd(d1) * sigma / (2 * math.sqrt(T))
                 - r * K * math.exp(-r * T) * _Nd(d2))
    else:
        price = K * math.exp(-r * T) * _Nd(-d2) - S * _Nd(-d1)
        delta = _Nd(d1) - 1.0
        theta = (-S * _nd(d1) * sigma / (2 * math.sqrt(T))
                 + r * K * math.exp(-r * T) * _Nd(-d2))

    gamma = _nd(d1) / (S * v)
    vega = S * _nd(d1) * math.sqrt(T)

    return {
        "price": price,
        "delta": delta,
        "gamma": gamma,
        "theta": theta / 365.0,   # per calendar day
        "vega": vega / 100.0,     # per 1 vol point
        "d1": d1,
        "d2": d2,
    }


def implied_vol(price, S, K, T, r=0.045, kind="call", lo=0.01, hi=5.0):
    """Bisection IV. Robust beats fast here -- Newton fails on deep wings."""
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        p = bs(S, K, T, mid, r, kind)["price"]
        if p > price:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)


def strike_for_delta(S, T, sigma, target_delta, r=0.045, kind="call"):
    """Invert delta -> strike. Selecting by delta rather than by moneyness is
    the correct convention: it holds probability-of-profit roughly fixed as
    volatility and time change, which fixed percentage strikes do not."""
    lo, hi = S * 0.3, S * 3.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        d = bs(S, mid, T, sigma, r, kind)["delta"]
        if kind == "call":
            if d > target_delta:
                lo = mid
            else:
                hi = mid
        else:
            if abs(d) > abs(target_delta):
                hi = mid
            else:
                lo = mid
        if hi - lo < 1e-4:
            break
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------
# Structure EV under a forecast distribution
# --------------------------------------------------------------------------
def terminal_dist(S, mu, sigma_h, n=20001, span=6.0):
    """Lognormal terminal price grid given expected LOG return mu over the
    holding period and its stdev sigma_h. Returns (prices, probability mass).

    A fat-tailed distribution would be more honest still, but the practical
    effect at 5-10 days on liquid names is second-order compared with the
    cost stack, and adding a tail parameter invites fitting it.
    """
    z = np.linspace(-span, span, n)
    logret = mu + sigma_h * z
    prices = S * np.exp(logret)
    pdf = np.exp(-0.5 * z**2)
    pdf /= pdf.sum()
    return prices, pdf


def structure_ev(S, structures, mu, sigma_h, T_exit, sigma_iv, spread_pct, r=0.045):
    """Expected P&L of each candidate structure under the forecast.

    Positions are opened at the offered price (mid + half the measured spread
    against you) and CLOSED at the exit horizon at mid minus half the spread
    again -- i.e. the spread is paid twice, which is what actually happens.
    Exit is at T_exit remaining, not at expiry, because a swing trade is closed
    early; valuing at expiry ignores the residual extrinsic you get back and
    materially misstates long-premium structures.
    """
    prices, pdf = terminal_dist(S, mu, sigma_h)
    out = []

    for st in structures:
        legs = st["legs"]

        # Entry cost at mid, then slippage against us on every leg.
        entry_mid = 0.0
        for L in legs:
            g = bs(S, L["K"], L["T"], sigma_iv, r, L["kind"])
            entry_mid += L["qty"] * g["price"]
        slip = sum(abs(L["qty"]) * bs(S, L["K"], L["T"], sigma_iv, r, L["kind"])["price"]
                   for L in legs) * spread_pct / 2.0
        entry = entry_mid + slip   # debit structures cost more, credits collect less

        # Value at exit across the terminal distribution.
        vals = np.zeros_like(prices)
        for L in legs:
            t_left = max(L["T"] - (L["T"] - T_exit), T_exit) if T_exit > 0 else 0.0
            for i, Sx in enumerate(prices):
                g = bs(Sx, L["K"], t_left, sigma_iv, r, L["kind"])
                vals[i] += L["qty"] * g["price"]
        exit_slip = np.abs(vals) * spread_pct / 2.0
        vals = vals - exit_slip

        pnl = vals - entry
        ev = float((pnl * pdf).sum())
        pwin = float(pdf[pnl > 0].sum())

        # Risk denominator: for a debit it is the premium paid; for a defined
        # credit structure it is width minus credit.
        risk = abs(entry) if entry > 0 else st.get("max_loss", abs(entry))
        risk = max(risk, 1e-6)

        out.append({
            "name": st["name"],
            "entry": entry,
            "ev": ev,
            "ev_pct": ev / risk,
            "pwin": pwin,
            "risk": risk,
            "max_gain": float(pnl.max()),
            "max_loss": float(pnl.min()),
            "breakeven_win": None,
        })

    return pd.DataFrame(out).sort_values("ev_pct", ascending=False)


def breakeven_winrate(avg_win, avg_loss):
    """Win rate needed to break even given the payoff asymmetry.

    This is the number that kills most retail options plans: a credit spread
    that wins 1 and loses 4 needs 80% accuracy just to tread water, so a
    'my signal is right 65% of the time' plan loses money on it.
    """
    if avg_win <= 0 or avg_loss >= 0:
        return np.nan
    return abs(avg_loss) / (avg_win + abs(avg_loss))


def candidate_structures(S, T, sigma, direction="up", r=0.045):
    """Build the standard retail expression set for a directional view."""
    kind = "call" if direction == "up" else "put"
    opp = "put" if direction == "up" else "call"
    sgn = 1 if direction == "up" else -1

    K_atm = strike_for_delta(S, T, sigma, 0.50 * sgn if direction == "up" else -0.50,
                             r, kind)
    K_30 = strike_for_delta(S, T, sigma, 0.30 if direction == "up" else -0.30, r, kind)
    K_16 = strike_for_delta(S, T, sigma, 0.16 if direction == "up" else -0.16, r, kind)
    K_70 = strike_for_delta(S, T, sigma, 0.70 if direction == "up" else -0.70, r, kind)

    sts = [
        {"name": f"long {kind} 50d (ATM)", "legs": [
            {"K": K_atm, "T": T, "kind": kind, "qty": 1}]},
        {"name": f"long {kind} 30d (OTM)", "legs": [
            {"K": K_30, "T": T, "kind": kind, "qty": 1}]},
        {"name": f"long {kind} 70d (ITM)", "legs": [
            {"K": K_70, "T": T, "kind": kind, "qty": 1}]},
        {"name": f"{kind} debit spread 50/30", "legs": [
            {"K": K_atm, "T": T, "kind": kind, "qty": 1},
            {"K": K_30, "T": T, "kind": kind, "qty": -1}]},
        {"name": f"{kind} debit spread 70/30", "legs": [
            {"K": K_70, "T": T, "kind": kind, "qty": 1},
            {"K": K_30, "T": T, "kind": kind, "qty": -1}]},
    ]

    # The credit side: sell the opposite wing. Defined risk via a further wing.
    Ko_30 = strike_for_delta(S, T, sigma, 0.30 if opp == "call" else -0.30, r, opp)
    Ko_16 = strike_for_delta(S, T, sigma, 0.16 if opp == "call" else -0.16, r, opp)
    width = abs(Ko_30 - Ko_16)
    sts.append({
        "name": f"{opp} credit spread 30/16",
        "legs": [{"K": Ko_30, "T": T, "kind": opp, "qty": -1},
                 {"K": Ko_16, "T": T, "kind": opp, "qty": 1}],
        "max_loss": width,
    })
    return sts


# --------------------------------------------------------------------------
# Live chain measurement -- the real cost stack
# --------------------------------------------------------------------------
def measure_chains(tickers, max_names=40, dte_lo=14, dte_hi=60):
    """Pull live chains and measure spread %, IV, and IV-vs-realised.

    This is the empirical input that keeps the modelled backtest honest.
    """
    import yfinance as yf

    rows = []
    for i, tk in enumerate(tickers[:max_names], 1):
        try:
            t = yf.Ticker(tk)
            hist = t.history(period="3mo")
            if len(hist) < 40:
                continue
            S = float(hist["Close"].iloc[-1])
            rv = float(hist["Close"].pct_change().std() * math.sqrt(252))

            exps = t.options or []
            now = pd.Timestamp.utcnow().tz_localize(None).normalize()
            for e in exps:
                d = (pd.Timestamp(e) - now).days
                if not (dte_lo <= d <= dte_hi):
                    continue
                ch = t.option_chain(e)
                for df, kind in ((ch.calls, "call"), (ch.puts, "put")):
                    if df is None or df.empty:
                        continue
                    q = df[(df.bid > 0) & (df.ask > 0)].copy()
                    if q.empty:
                        continue
                    q["mid"] = (q.bid + q.ask) / 2
                    q["spread_pct"] = (q.ask - q.bid) / q.mid
                    q["moneyness"] = q.strike / S
                    q["dte"] = d
                    q["kind"] = kind
                    q["ticker"] = tk
                    q["rv"] = rv
                    rows.append(q[["ticker", "kind", "dte", "strike", "moneyness",
                                   "bid", "ask", "mid", "spread_pct",
                                   "impliedVolatility", "volume", "openInterest", "rv"]])
                break  # one expiry per name is enough for a cost estimate
            if i % 10 == 0:
                print(f"    ...{i} names", file=sys.stderr)
            time.sleep(0.15)
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def main():
    print("=" * 78)
    print("OPTION EDGE -- greeks, cost stack, structure selection")
    print("=" * 78)

    # Sanity-check the pricer against a known case.
    g = bs(100, 100, 30 / 365, 0.25)
    print(f"\n  BS check  S=100 K=100 30d iv=25%:")
    print(f"    price {g['price']:.2f}  delta {g['delta']:.3f}  gamma {g['gamma']:.4f}  "
          f"theta {g['theta']:.3f}/day  vega {g['vega']:.3f}/volpt")
    iv = implied_vol(g["price"], 100, 100, 30 / 365)
    print(f"    IV round-trip: {iv:.4f} (should be 0.2500)")

    print("\n  BREAK-EVEN WIN RATES (the bar each structure sets for the signal)")
    print(f"  {'structure':28s} {'avg win':>9s} {'avg loss':>9s} {'need':>7s}")
    examples = [
        ("long call (2:1 payoff)", 1.0, -0.5),
        ("long call (lottery 4:1)", 2.0, -0.5),
        ("debit spread (1:1)", 1.0, -1.0),
        ("credit spread (1:3)", 0.33, -1.0),
        ("credit spread (1:4)", 0.25, -1.0),
        ("iron condor (1:9)", 0.11, -1.0),
    ]
    for name, w, l in examples:
        print(f"  {name:28s} {w:+9.2f} {l:+9.2f} {breakeven_winrate(w, l):7.1%}")

    print("\n  This table is why a 60%-accurate signal is not automatically money:")
    print("  it clears a debit spread comfortably and fails a 1:3 credit spread badly.")


if __name__ == "__main__":
    main()
