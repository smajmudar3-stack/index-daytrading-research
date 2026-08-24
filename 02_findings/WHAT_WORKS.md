# What actually survived testing

Three signals passed honest testing. Everything else is in
[WHAT_FAILED.md](WHAT_FAILED.md).

The bar for "survived" here: measured on out-of-sample data, corrected for
multiple testing, non-overlapping samples, and compared against the base rate
rather than against zero.

---

## 1. Short interest — the strongest signal found, and the sign is backwards

| horizon | IC (Spearman) | n |
|---|---:|---:|
| 21 days | −0.068 | 13,219 |
| 63 days | **−0.107** | 13,219 |

Monotone across every bucket. **The sign is negative.** High short float
predicts *lower* forward returns, not higher.

This is worth stating plainly because the intuitive story — heavy shorting is
squeeze fuel, therefore bullish — is what I assumed going in, and the data says
the opposite. Short sellers are, on average, right. The registry carries this at
weight 0.30 with direction −1.

## 2. VIX backwardation — the only signal that held across all three splits

t-statistics of +3.9, +2.8, +2.1 on train, validate and test respectively.

Most signals in this repo look strong on one split and vanish on the others.
This one degrades but never flips, which is what a real effect looks like.
Weight 0.30, direction +1.

## 3. Low dealer gamma — a regime filter, not a signal

**8 of 8** directional structures tested paid more in low-gamma regimes than
high-gamma ones. Not a direction call — a statement about when directional bets
get paid at all.

The practical consequence: in high gamma, price pins and directional structures
bleed; in low gamma, moves extend. The 0DTE tab uses this to choose *structure
type* (range-bound vs directional), which is separate from and additional to the
direction call.

---

## Partial credit

**Compressed volatility + volume surge** → 1.55× lift on P(3σ move) at 42 days,
measured across 158 names and 1,159,258 stock-days. Real, but 1.55× on a 3%
base rate is a 4.7% hit rate — it needs the convexity of options to pay, and
that reintroduces the spread problem below.

**Execution beats selection in far-OTM.** Far-OTM buying was −45.6% overall but
**+5.6%** once filtered to contracts with ≤20% bid-ask spread. The spread filter
mattered more than any signal tested for choosing *which* far-OTM to buy. This
is the single most useful thing learned about the Black Swan strategy.

**Delta band matters more than "cheapness."** Returns improve monotonically as
you move toward the money: −90% at the far tail, **+26.1% at 16–30 delta**. The
market overprices the ultra-far tail and underprices the 10–20 delta band. Buying
the cheapest contract is the worst version of the trade.

---

## The current weight registry

From `signal_weights.py`, the single source of truth. Tiers mark how much of
each weight is measured versus fabricated prior.

| signal | weight | dir | tier | basis |
|---|---:|---:|---|---|
| `trend` | 0.35 | + | measured-weak | |
| `flow_lean` | 0.35 | + | unmeasured | orthogonal, same-day only |
| `short_float_pct` | 0.30 | **−** | measured | IC −0.068 @21d, monotone |
| `vix_backwardation` | 0.30 | + | measured | t +3.9/+2.8/+2.1, all splits |
| `dp_buy_share` | 0.15 | + | unmeasured | orthogonal, same-day only |
| `insider_open_buys` | 0.10 | + | measured-weak | |
| `rate_beta` | 0.05 | + | risk-flag | |

**Hard zeros** — tested, found to carry no information, weight pinned at 0 so
they cannot leak back in: `iv_rel`, `iv_trend`, `oi_change_net`, `spread_rel`,
`gamma_direction`, `sector_rotation`, `dip_screen`, `cheap_iv`.

Unmeasured weights are priors, not results. `uw_calibrate.py` blends them toward
measured values as live results accumulate:
`w = (1−k)·prior + k·measured`, with sample-size shrinkage
`w ∝ IC × sqrt(n/(n+N₀))`, N₀ = 100.
