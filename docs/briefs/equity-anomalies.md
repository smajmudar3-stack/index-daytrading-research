<!-- research brief, filed 2026-09-23; agent output verbatim -->

# Equity anomalies (momentum, short-term reversal) as a return source, 2026

**Bottom line:** momentum and short-term reversal are the two most heavily tested anomalies in
finance, and both show the pattern the literature calls post-publication decay. Momentum's
long-short spread had a real t-stat (2.07) from 1990-2014 and an insignificant one (0.52) from
2015-2025; its long-only edge *over the market* fell from t=2.12 to t=0.64 across the same split.
Short-term reversal's long-short spread was never significant in either period on this monthly
data (t=-0.23, then -0.28) before a cent of trading cost is deducted, and the literature says
costs erase most of what raw numbers show anyway. Nothing here is in range of 58%/month; nothing
here is comfortably in range of 20%/year on a risk-adjusted basis once you subtract what the
market itself returned. This is the same shape as every other systematic-equity finding this repo
has produced: real, small, decaying, and not a five-month plan.

## 1. What was computed and from what

Source data: Kenneth French's 10 decile portfolios sorted on prior 2-12 month return
(`10_Portfolios_Prior_12_2.csv`, momentum) and prior 1-month return
(`10_Portfolios_Prior_1_0.csv`, short-term reversal), both value-weighted monthly, CRSP-based,
1926/27-2026/07. Market return reconstructed from `F-F_Research_Data_Factors.csv` (Mkt-RF + RF).
Two windows: 1990-2014 (300 months) and 2015-2025 (132 months). For momentum, "long-short" is
decile 10 (winners) minus decile 1 (losers) — the textbook UMD construction. For short-term
reversal the anomaly is the *opposite* direction: buy losers, short winners, so "long-short" here
is decile 1 minus decile 10. "Long-only" is the anomaly's long leg (winners for momentum, losers
for reversal) minus the market return in the same months. All stats are on monthly % returns:
mean, t-stat on the mean, annualized return (geometric), annualized vol, Sharpe, and max drawdown
on the cumulative series. This is gross of all trading costs — French's portfolios rebalance
monthly with no cost adjustment, which matters most for short-term reversal (below).

Two AQR live/replicated series were pulled as a cross-check on French's academic construction:
the AQR US Large Cap Momentum Index (a long-only, investable momentum tilt, monthly since 1980)
and the USA legs of AQR's QMJ (quality) and BAB (betting-against-beta) long/short factors, which
aren't part of this brief's mandate but were in the provided files and corroborate the general
pattern.

## 2. Momentum (12-2)

| Metric | 1990-2014 | 2015-2025 |
|---|---:|---:|
| D10-D1 long-short: mean/mo | 0.98% | 0.39% |
| D10-D1: annualized (geo) | 7.5% | 0.0% |
| D10-D1: annualized vol | 28.4% | 29.6% |
| D10-D1: t-stat | **2.07** | **0.52** |
| D10-D1: Sharpe | 0.41 | 0.16 |
| D10-D1: max drawdown | -80.8% | -64.8% |
| D10 (winners) alone: ann. ret | 14.5% | 14.9% |
| D10 alone: Sharpe | 0.74 | 0.79 |
| Market: ann. ret / Sharpe | 9.8% / 0.70 | 13.3% / 0.89 |
| **D10 minus market (long-only edge)** | **4.6%/yr, t=2.12** | **1.6%/yr, t=0.64** |

The long-short spread's t-stat roughly quarters (2.07 → 0.52) and its annualized return goes to
essentially zero. The part that's easy to miss: decile 10 held outright still returns 14-15%/yr
with a *higher* Sharpe post-2015 (0.79 vs 0.74) than pre-2015 — but that's because the market
itself carried a 0.89 Sharpe in 2015-2025, the best fifteen years for buy-and-hold beta in this
data. The relevant number is the edge over what you'd have gotten doing nothing: it fell from
4.6%/yr at t=2.12 (real) to 1.6%/yr at t=0.64 (statistically indistinguishable from noise).
AQR's live, investable US Large Cap Momentum Index shows the same non-collapse in absolute terms
(10.98%/yr, Sharpe 0.69, 1990-2014 → 12.51%/yr, Sharpe 0.81, 2015-2025) — consistent with
momentum-tilted beta continuing to "work" exactly to the extent equities in general worked, which
is not the same claim as the anomaly having alpha left in it.

## 3. Short-term reversal (1-0)

| Metric | 1990-2014 | 2015-2025 |
|---|---:|---:|
| D1-D10 long-short (buy losers): mean/mo | -0.08% | -0.17% |
| D1-D10: annualized (geo) | -3.3% | -5.1% |
| D1-D10: t-stat | -0.23 | -0.28 |
| D1-D10: Sharpe | -0.05 | -0.08 |
| D1 (losers) alone: ann. ret / Sharpe | 4.2% / 0.29 | 11.5% / 0.50 |
| **D1 minus market (long-only edge)** | **-3.8%/yr, t=-0.78** | **≈0%/yr, t=0.29** |

Short-term reversal's raw long-short spread on monthly, value-weighted CRSP deciles was never
significant in either window — it's a coin flip with a slight negative tilt pre-2015 and the same
post-2015. This tracks a known feature of the literature, not a bug in the computation: reversal
is a *daily-turnover* effect (last week's losers bounce, not last month's), and monthly
rebalancing on monthly-formation deciles is close to the wrong instrument for it — see de Groot,
Huij & Zhou below. Buying the loser decile outright did fine as a diversified equity sleeve
(11.5%/yr Sharpe 0.50 in 2015-2025) but that is market beta plus small/junk tilt, not the
reversal effect isolated against the market (t=0.29, statistically zero).

## 4. What the literature says

- **[Open Source Asset Pricing](https://www.openassetpricing.com/)** (Chen & Zimmermann, hosting
  ~300 replicated cross-sectional signals; **[GitHub
  README](https://github.com/OpenSourceAP/CrossSection)**) exists specifically to let anyone
  check a predictor's return *after* the sample the original paper used. Its front page runs a
  published-vs-replicated t-stat comparison chart; the site's whole reason to exist is that
  published t-stats systematically overstate what a signal delivers going forward. It does not
  publish one summary decay percentage — that's the next paper.
- **McLean & Pontiff (2016 JF), "Does Academic Research Destroy Stock Return Predictability?"**
  ([DOI](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12365) — Wiley returned HTTP 403 this
  session, full text not independently re-verified here). The widely cited headline result,
  which this brief is repeating from established literature rather than a freshly pulled
  abstract: average returns decline out-of-sample even *before* publication (pure statistical
  overfitting), and decline further after publication, consistent with informed capital trading
  the anomaly away. Treat the exact percentage as "not verified this session."
- **Jensen, Kelly & Pedersen (2023 JF), "Is There a Replication Crisis in Finance?"** — confirmed
  via **[jkpfactors.com](https://jkpfactors.com/)**: the paper's own dataset covers 153
  characteristics/factors across 13 themes and 93 countries. Their headline argument (from
  established literature, not re-fetched full text this session) is more optimistic than
  McLean-Pontiff: applying a Bayesian, multiple-testing-aware framework, most published factors
  replicate in sign and are jointly significant even though many fail an individual t>3 hurdle —
  i.e., the "factor zoo" is smaller than it looks, but the bar for a single factor to be trusted
  in isolation is much higher than t>1.96.
- **Novy-Marx & Velikov (2016 RFS), "A Taxonomy of Anomalies and Their Trading Costs"**
  ([DOI](https://academic.oup.com/rfs/article-abstract/29/1/104/1844518), RFS 29(1):104-147,
  winner of the 2016 Fama-DFA Prize — confirmed via fetch, full abstract paywalled). Established
  finding: anomalies sort into low-turnover ones (value, quality-type) that survive realistic
  costs, and high-turnover ones — short-term reversal chief among them — that are severely
  impaired or wiped out by costs even though their gross numbers look attractive.
- **Gu, Kelly & Xiu (2020 RFS), "Empirical Asset Pricing via Machine Learning"** — full abstract
  fetched directly: "We demonstrate large economic gains to investors using machine learning
  forecasts, in some cases doubling the performance of leading regression-based strategies... We
  identify the best-performing methods (trees and neural networks)... All methods agree on the
  same set of dominant predictive signals, a set that includes variations on **momentum,
  liquidity, and volatility**" ([DOI](https://doi.org/10.1093/rfs/hhaa009)). Momentum survives as
  one of the few signals nonlinear ML still finds useful — relevant because it means the decay
  measured above is a decay in a *linear, decile-sorted* implementation, not proof the underlying
  information content is gone.
- **Barroso & Santa-Clara (2015 JFE), "Momentum has its Moments"**
  ([DOI](https://www.sciencedirect.com/science/article/abs/pii/S0304405X14002323), ScienceDirect
  403, not independently re-verified this session). Established finding: momentum's own realized
  variance forecasts its crash risk (1932, 2001, 2009), and scaling position size inversely to
  trailing momentum-portfolio variance roughly doubles its Sharpe ratio by cutting the left tail
  — directly relevant to the -80.8% and -64.8% max drawdowns on the raw D10-D1 spread above,
  which are almost certainly concentrated in exactly those crash windows.
- **de Groot, Huij & Zhou, "Another Look at Trading Costs and Short-Term Reversal Profits"**
  (Journal of Banking & Finance, 2012 — not fetched this session, URL guesses returned wrong
  content; cited from established literature). Their finding: gross short-term reversal profits
  in raw CRSP data look large and are concentrated in small, illiquid names; realistic
  transaction costs consume most to all of the profit, leaving little to nothing tradeable at
  size. This is consistent with, and explains, the near-zero raw t-stats found above even
  *before* costs — the effect this repo can see in French's value-weighted, monthly-rebalanced
  deciles was already the weak, liquid residue of a much noisier, cost-eaten daily effect.

## 5. Verdict

| Anomaly | Raw edge found | vs. $5k→$50k/5mo (58%/mo) | vs. 20%/yr |
|---|---|---|---|
| Momentum, long-short, 1990-2014 | +7.5%/yr, t=2.07 | No — 90+x too small, and this window is closed | No |
| Momentum, long-short, 2015-2025 | ~0%/yr, t=0.52 | No | No — statistically zero |
| Momentum, long-only edge over mkt, 2015-2025 | +1.6%/yr, t=0.64 | No | No |
| Short-term reversal, long-short, either window | negative or ~0, t≈-0.2 to -0.3 | No | No |
| Short-term reversal, after realistic costs (literature) | near zero to negative | No | No |

Judged against $5,000→$50,000 in five months, none of this clears the bar by any margin worth
discussing — a 58%/month compounding target needs roughly 2,000x the best monthly mean found here
(momentum D10 alone, 1.33%/mo, itself mostly beta). Judged against the more sober 20%/year target,
momentum's long-only decile *including market beta* got there in both windows (14.5%, 14.9%), but
the market alone nearly matched it in 2015-2025 (13.3%), so the anomaly-specific contribution —
the only part that's actually "the strategy" rather than "being long stocks" — never reached 20%
and lost its statistical significance in the exact window that would matter for a plan starting
today. Short-term reversal never had a significant raw edge in this data, and the literature says
what edge exists on paper is a trading-cost artifact rather than a tradeable one.

For context against this repo's own work: the earnings-surprise finding already on file
(Q5-Q1 +2.84% over 63 sessions, t=4.3, long-only +4.7%/yr over SPY) has a comparable t-stat to
momentum's *1990-2014* number and was measured recently — i.e., it currently looks like the
stronger and more current signal of the two, not because momentum is a bad idea, but because
what's left of momentum's spread today is the weak tail this brief just measured. Weekly
predictors already filed as null and stat-arb as net negative are the same story again: this
repo keeps finding the same thing from different angles, which is itself the finding.

**Not verified:** McLean & Pontiff, Novy-Marx & Velikov, Barroso & Santa-Clara, and de Groot/Huij/
Zhou headline figures are stated from established literature, not from a full-text abstract
fetched this session (Wiley, Oxford Academic, and ScienceDirect all returned HTTP 403; de Groot
et al.'s actual URL was not located within budget). The French-decile and AQR computations above
were run directly against the provided CSV/XLSX files with `venv/bin/python3` this session and
are fully reproducible from the scripts used (`anomaly_calc2.py`, `aqr_calc.py`).
