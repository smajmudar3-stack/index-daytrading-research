"""Black-Scholes, once.

There were at least four independent implementations in this repo: `condor._bs`,
`gex_periscope.bs_gamma`, `bt_options.bs` and `scripts/option_edge.bs`. Three of them
defaulted the risk-free rate to 0.04 and one to 0.045, so the same structure priced
differently depending on which module happened to price it. Nothing surfaced the
discrepancy, because nothing compared them.

That matters more here than in most places. The repo's central finding is that a
MODELLED option price overstated a credit by mispricing the wings, and that inflation
was the entire apparent edge: +3.7% per trade modelled, approximately break-even on
1,919 sessions of real bid/ask. When a model is the thing that misled you, having four
copies of it is not a style problem.

One implementation, one rate, one test. Works on scalars and on numpy arrays.
"""
import math

import numpy as np
from scipy.stats import norm

# The rate the live system uses. Kept as a named constant so a change is one visible
# edit rather than four silent ones, and so a test can assert the modules agree.
RISK_FREE = 0.04

# Floors. A zero or negative time or vol is not a price, it is an intrinsic value, and
# feeding either into the log/sqrt below produces a NaN that propagates silently into a
# panel. Both call sites had their own floors with different values.
MIN_T = 1e-6
MIN_IV = 1e-4


def _d1_d2(S, K, T, iv, r):
    T = np.maximum(T, MIN_T)
    iv = np.maximum(iv, MIN_IV)
    sqrt_t = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * iv * iv) * T) / (iv * sqrt_t)
    return d1, d1 - iv * sqrt_t


def price(S, K, T, iv, r=RISK_FREE, call=True):
    """Option price per one point of the underlying. Multiply by 100 for dollars.

    At or past expiry, or with no vol, returns intrinsic value rather than a model
    number, which is the correct answer and not a fallback.
    """
    if np.isscalar(T) and np.isscalar(iv) and (T <= 0 or iv <= 0):
        return float(max(0.0, (S - K) if call else (K - S)))
    d1, d2 = _d1_d2(S, K, T, iv, r)
    disc = np.exp(-r * np.maximum(T, MIN_T))
    if call:
        return S * norm.cdf(d1) - K * disc * norm.cdf(d2)
    return K * disc * norm.cdf(-d2) - S * norm.cdf(-d1)


def gamma(S, K, T, iv, r=RISK_FREE):
    """dDelta/dSpot per one point. Identical for calls and puts."""
    T = np.maximum(T, MIN_T)
    iv = np.maximum(iv, MIN_IV)
    d1, _ = _d1_d2(S, K, T, iv, r)
    return norm.pdf(d1) / (S * iv * np.sqrt(T))


def delta(S, K, T, iv, r=RISK_FREE, call=True):
    d1, _ = _d1_d2(S, K, T, iv, r)
    return norm.cdf(d1) if call else norm.cdf(d1) - 1.0


def ncdf(x):
    """Standard normal CDF. Kept because `condor` used an erf-based one and a caller
    may want it without pulling in scipy."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))
