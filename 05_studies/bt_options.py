"""bt_options.py — shared, causal option-P&L machinery for the rule backtests.

We have NO historical option chains. So option prices are MODELLED, and the model is built to be
*honest and conservative* rather than flattering:

  1. Implied vol is derived from a CAUSAL volatility forecast (EWMA of realised moves, floored by a
     VIX-derived term) known at the PRIOR close, then multiplied by a VARIANCE-RISK-PREMIUM factor
     `vrp` >= 1.0.  vrp is the single most important assumption: it is *why* long premium loses on
     average.  Every result is reported across a vrp grid so the reader can see the sensitivity.
  2. Skew: 0DTE/short-dated index puts trade at higher IV than calls.  A one-parameter skew tilt is
     applied so credit spreads / condors are not priced with an unrealistically flat surface.
  3. Costs: per-leg half-spread = max(spread_pct * mid, spread_floor) charged on ENTRY and EXIT,
     plus a per-contract fee.  Cheap OTM options are therefore correctly punished.

Everything here is pure functions of inputs available before the trade.  No look-ahead.
"""
from __future__ import annotations

import math as _math

import numpy as np
import pandas as pd

SQRT252 = np.sqrt(252.0)
MINUTES_PER_SESSION = 390.0

# ----------------------------------------------------------------------------- Black-Scholes (r=q=0)
_INV_SQRT2 = 1.0 / np.sqrt(2.0)


def _norm_cdf(x):
    """Standard normal CDF.  N(x) = 0.5*(1+erf(x/sqrt(2)))."""
    return 0.5 * (1.0 + _math.erf(float(x) * _INV_SQRT2))


def bs(S, K, T, sigma, call=True):
    """Black-Scholes price, r=q=0.  T in years.  Returns intrinsic when T<=0 or sigma<=0."""
    S = float(S); K = float(K); T = float(T); sigma = float(sigma)
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0) if call else max(K - S, 0.0)
    v = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * v * v) / v
    d2 = d1 - v
    if call:
        return S * _norm_cdf(d1) - K * _norm_cdf(d2)
    return K * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def bs_delta(S, K, T, sigma, call=True):
    if T <= 0 or sigma <= 0:
        itm = (S > K) if call else (S < K)
        return (1.0 if call else -1.0) * (1.0 if itm else 0.0)
    v = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * v * v) / v
    return _norm_cdf(d1) if call else _norm_cdf(d1) - 1.0


# ----------------------------------------------------------------------------- vol surface
def strike_iv(atm_iv, S, K, sig_move, skew=0.15, floor_mult=0.55, cap_mult=2.5):
    """Simple linear-in-standard-deviations skew tilt.

    sig_move = expected absolute move of the underlying over the option's life, in price terms
    (S * sigma * sqrt(T)).  One SD below spot raises IV by `skew` (fractionally); one SD above
    lowers it by `skew`.  Clipped to [floor_mult, cap_mult] x ATM.
    """
    if sig_move <= 0:
        return atm_iv
    sd = (S - K) / sig_move          # >0 for puts (K<S), <0 for calls
    m = 1.0 + skew * sd
    return atm_iv * float(np.clip(m, floor_mult, cap_mult))


# ----------------------------------------------------------------------------- costs
class Costs:
    """Per-leg transaction cost model.  Prices are per share (option quote convention)."""

    def __init__(self, spread_pct=0.010, spread_floor=0.01, fee_per_contract=0.05):
        self.spread_pct = spread_pct        # half-spread as fraction of mid
        self.spread_floor = spread_floor    # half-spread floor, in quote dollars
        self.fee = fee_per_contract / 100.0  # per share

    def buy(self, mid):
        return mid + max(self.spread_pct * mid, self.spread_floor) + self.fee

    def sell(self, mid):
        return max(0.0, mid - max(self.spread_pct * mid, self.spread_floor) - self.fee)


# ----------------------------------------------------------------------------- causal vol forecast
def causal_vol_forecast(oc_ret: pd.Series, vix: pd.Series, span=20, vix_frac=0.55):
    """Forecast of TODAY's open->close sigma, using only data through the PRIOR close.

    oc_ret : today's open->close return series (fractional)   [we shift it, so no leak]
    vix    : VIX close series                                  [we shift it, so no leak]
    vix_frac: fraction of the VIX daily-equivalent sigma that the *day session* accounts for.
              Fitted on the TRAIN window only by the caller; 0.55 is a reasonable prior.
    """
    mad = oc_ret.abs().shift(1).ewm(span=span, min_periods=10).mean()
    ewma_sig = mad / 0.7978845608                      # E|X| = sigma*sqrt(2/pi) for a normal
    vix_sig = (vix.shift(1) / 100.0) / SQRT252 * vix_frac
    return np.maximum(ewma_sig, vix_sig)


def fit_vix_frac(oc_ret: pd.Series, vix: pd.Series) -> float:
    """Ratio of realised open->close sigma to VIX daily-equivalent sigma.  Fit on TRAIN only."""
    realised = oc_ret.std()
    vix_sig = ((vix.shift(1) / 100.0) / SQRT252).mean()
    if not np.isfinite(realised) or vix_sig <= 0:
        return 0.55
    return float(np.clip(realised / vix_sig, 0.3, 1.0))


# ----------------------------------------------------------------------------- structures
def round_strike(x, inc=1.0):
    return round(x / inc) * inc


def price_leg(S, K, T, atm_iv, sig_move, call, skew):
    iv = strike_iv(atm_iv, S, K, sig_move, skew=skew)
    return bs(S, K, T, iv, call=call)


def long_option(S0, S1, T0, atm_iv, sig_move, call, costs: Costs, skew=0.15, moneyness_sd=0.0,
                strike_inc=1.0, T1=0.0):
    """Buy a single option at S0, close/expire at S1.  Returns (debit, pnl, ret_on_debit, K)."""
    K = round_strike(S0 + (moneyness_sd * sig_move if call else -moneyness_sd * sig_move), strike_inc)
    mid0 = price_leg(S0, K, T0, atm_iv, sig_move, call, skew)
    entry = costs.buy(mid0)
    if entry <= 0:
        return None
    mid1 = price_leg(S1, K, T1, atm_iv, sig_move, call, skew) if T1 > 0 else (
        max(S1 - K, 0.0) if call else max(K - S1, 0.0))
    exit_ = costs.sell(mid1) if T1 > 0 else max(0.0, mid1 - (0.0 if mid1 <= 0 else 0.0))
    # at true expiry there is no spread to cross for cash-settled index options
    pnl = exit_ - entry
    return dict(debit=entry, pnl=pnl, ret=pnl / entry, K=K, risk=entry)


def vertical(S0, S1, T0, atm_iv, sig_move, costs: Costs, call=True, debit=True,
             short_sd=1.0, width_sd=1.0, skew=0.15, strike_inc=1.0, T1=0.0, min_width=1.0):
    """Two-leg vertical.

    debit=True  -> buy the near strike (ATM), sell `short_sd` SDs out          (directional long)
    debit=False -> sell the `short_sd` strike, buy `short_sd+width_sd` further (credit spread)
    Returns dict with net premium, max risk, pnl, ret on risk.
    """
    if debit:
        Kl = round_strike(S0, strike_inc)
        Ks = round_strike(S0 + short_sd * sig_move if call else S0 - short_sd * sig_move, strike_inc)
        if call and Ks <= Kl:
            Ks = Kl + max(min_width, strike_inc)
        if (not call) and Ks >= Kl:
            Ks = Kl - max(min_width, strike_inc)
        long_mid0 = price_leg(S0, Kl, T0, atm_iv, sig_move, call, skew)
        short_mid0 = price_leg(S0, Ks, T0, atm_iv, sig_move, call, skew)
        net_entry = costs.buy(long_mid0) - costs.sell(short_mid0)
        if net_entry <= 0:
            return None
        width = abs(Ks - Kl)
        pay = (max(S1 - Kl, 0.0) - max(S1 - Ks, 0.0)) if call else (max(Kl - S1, 0.0) - max(Ks - S1, 0.0))
        pnl = pay - net_entry
        return dict(net=net_entry, risk=net_entry, width=width, pnl=pnl,
                    ret=pnl / net_entry, Kl=Kl, Ks=Ks, maxwin=width - net_entry)
    else:
        Ks = round_strike(S0 + short_sd * sig_move if call else S0 - short_sd * sig_move, strike_inc)
        Kl = round_strike(Ks + width_sd * sig_move if call else Ks - width_sd * sig_move, strike_inc)
        if call and Kl <= Ks:
            Kl = Ks + max(min_width, strike_inc)
        if (not call) and Kl >= Ks:
            Kl = Ks - max(min_width, strike_inc)
        short_mid0 = price_leg(S0, Ks, T0, atm_iv, sig_move, call, skew)
        long_mid0 = price_leg(S0, Kl, T0, atm_iv, sig_move, call, skew)
        credit = costs.sell(short_mid0) - costs.buy(long_mid0)
        width = abs(Kl - Ks)
        risk = width - credit
        if credit <= 0 or risk <= 0:
            return None
        pay = (max(S1 - Ks, 0.0) - max(S1 - Kl, 0.0)) if call else (max(Ks - S1, 0.0) - max(Kl - S1, 0.0))
        pnl = credit - pay
        return dict(net=credit, risk=risk, width=width, pnl=pnl, ret=pnl / risk,
                    Ks=Ks, Kl=Kl, credit_pct=credit / width)


def iron_condor(S0, S1, T0, atm_iv, sig_move, costs: Costs, short_sd=1.0, width_sd=1.0,
                skew=0.15, strike_inc=1.0):
    p = vertical(S0, S1, T0, atm_iv, sig_move, costs, call=False, debit=False,
                 short_sd=short_sd, width_sd=width_sd, skew=skew, strike_inc=strike_inc)
    c = vertical(S0, S1, T0, atm_iv, sig_move, costs, call=True, debit=False,
                 short_sd=short_sd, width_sd=width_sd, skew=skew, strike_inc=strike_inc)
    if p is None or c is None:
        return None
    credit = p["net"] + c["net"]
    width = max(p["width"], c["width"])
    risk = width - credit
    if risk <= 0:
        return None
    pnl = p["pnl"] + c["pnl"]
    return dict(net=credit, risk=risk, width=width, pnl=pnl, ret=pnl / risk,
                credit_pct=credit / width, Kps=p["Ks"], Kcs=c["Ks"])


# ----------------------------------------------------------------------------- statistics
def sharpe(x, periods=252):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return 0.0
    return float(x.mean() / x.std(ddof=1) * np.sqrt(periods))


def psr(sr_hat, n, sr_bench=0.0, skew_=0.0, kurt=3.0):
    """Probabilistic Sharpe Ratio (Bailey & Lopez de Prado).  sr_hat/sr_bench are PER-OBSERVATION."""
    from scipy import stats
    if n < 5:
        return np.nan
    denom = np.sqrt(max(1e-12, 1 - skew_ * sr_hat + (kurt - 1) / 4.0 * sr_hat ** 2))
    z = (sr_hat - sr_bench) * np.sqrt(n - 1) / denom
    return float(stats.norm.cdf(z))


def deflated_sharpe(returns, n_trials, periods=252):
    """DSR: PSR against the expected max Sharpe of `n_trials` independent random strategies."""
    from scipy import stats
    x = np.asarray(returns, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return np.nan, np.nan, np.nan
    sr_obs = x.mean() / x.std(ddof=1)              # per-observation
    sk = float(stats.skew(x)); ku = float(stats.kurtosis(x, fisher=False))
    # expected max of N standard normals scaled by the cross-sectional sd of trial Sharpes.
    # Conservative default: assume trial Sharpes have sd equal to the sampling sd 1/sqrt(n).
    gamma = 0.5772156649
    e = 1.0 / np.sqrt(n)
    if n_trials <= 1:
        sr0 = 0.0
    else:
        sr0 = e * ((1 - gamma) * stats.norm.ppf(1 - 1.0 / n_trials)
                   + gamma * stats.norm.ppf(1 - 1.0 / (n_trials * np.e)))
    d = psr(sr_obs, n, sr_bench=sr0, skew_=sk, kurt=ku)
    return d, sr_obs * np.sqrt(periods), sr0 * np.sqrt(periods)


def max_dd(equity):
    e = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(e)
    return float(np.min(e / peak - 1.0))


def summarize(rets, label="", periods=252, n_trials=1, risk_frac=None, verbose=True):
    """rets = per-trade return on capital-at-risk.  If risk_frac given, also build an equity curve
    where each trade risks `risk_frac` of current equity."""
    r = np.asarray([x for x in rets if np.isfinite(x)], dtype=float)
    out = {"label": label, "n": len(r)}
    if len(r) < 5:
        if verbose:
            print(f"  {label:<38} n={len(r)}  (too few)")
        return out
    from scipy import stats
    t, p = stats.ttest_1samp(r, 0.0)
    wins = r > 0
    gp = r[wins].sum(); gl = -r[~wins].sum()
    out.update(avg=r.mean(), med=float(np.median(r)), win=wins.mean(), t=float(t), p=float(p),
               pf=(gp / gl if gl > 0 else np.inf),
               avg_win=(r[wins].mean() if wins.any() else 0.0),
               avg_loss=(r[~wins].mean() if (~wins).any() else 0.0))
    if risk_frac:
        eq = np.cumprod(1.0 + risk_frac * r)
        out["equity_mult"] = float(eq[-1]); out["maxdd"] = max_dd(eq)
    dsr, sr_ann, sr0 = deflated_sharpe(r, n_trials, periods=periods)
    out.update(dsr=dsr, sr_per_trade_ann=sr_ann, sr_haircut=sr0)
    if verbose:
        s = (f"  {label:<38} n={len(r):>4}  avg {r.mean()*100:+6.1f}%  win {wins.mean()*100:4.0f}%  "
             f"PF {out['pf']:4.2f}  t {t:+5.2f}  DSR {dsr:.2f}")
        if risk_frac:
            s += f"  eq x{out['equity_mult']:.2f}  DD {out['maxdd']*100:.0f}%"
        print(s)
    return out
