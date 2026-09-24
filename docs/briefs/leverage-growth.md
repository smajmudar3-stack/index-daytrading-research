# Leverage for growth: can $5,000 become $50,000 in 5 months?

Computed 2026-09-23, daily data 2010-01 through 2026-09-22 (SPY/QQQ/SSO/QLD/UPRO/TQQQ/TMF/^VIX/^VIX3M
via yfinance, adjusted close). Scripts and raw output live in this session's scratchpad
(`fetch_lev.py`, `lev_calc.py`, `mc.py`) and are reproducible with
`/Users/sahilmajmudar/index-daytrading/venv/bin/python3`. All backtests are gross of taxes;
ETF-level expense ratios are already embedded in adjusted close. A flat 5bp switch cost is
charged on every position change in the gated/filtered strategies; the buy-and-hold and HFEA
lines carry no trading cost beyond the ETF's own daily-reset drag.

## The ask, stated plainly

Turning $5,000 into $50,000 in 5 months is a 10x, which requires **+58.5%/month compounded for
five months straight** (10^(1/5)−1). The best single month SPY has produced in this entire
15-year sample is +12.7%. Nothing below gets remotely close, and the Monte Carlo section
quantifies exactly how far.

## 1-6: computed backtest table (daily, 2010-01 to 2026-09-22)

| # | Strategy | Start | CAGR | Vol | Sharpe | Max DD | Worst month | Best month |
|---|---|---|---|---|---|---|---|---|
| 1 | SPY buy & hold | 2010-01 | 14.20% | 17.1% | 0.86 | −33.7% | −12.5% | +12.7% |
| 1 | QQQ buy & hold | 2010-01 | 19.15% | 20.7% | 0.95 | −35.1% | −13.6% | +15.7% |
| 2 | UPRO buy & hold (3x SPY) | 2010-01 | 29.51% | 51.1% | 0.77 | −76.8% | −48.1% | +37.2% |
| 2 | TQQQ buy & hold (3x QQQ) | 2010-02 | 43.39% | 61.1% | 0.90 | −81.7% | −38.1% | +52.4% |
| 3 | UPRO + 200d SMA filter (cash below) | 2010-01 | 23.90% | 34.2% | 0.80 | −51.4% | −22.6% | +35.2% |
| 3 | TQQQ + 200d SMA filter (cash below) | 2010-02 | 32.62% | 45.8% | 0.85 | −56.2% | −36.7% | +35.2% |
| 4 | 55/45 UPRO/TMF, quarterly rebal (HFEA) | 2010-01 | 24.29% | 36.1% | 0.78 | −64.7% | −30.2% | +32.7% |
| 5 | SPY 2x (SSO) gated: contango + golden cross, else cash | 2010-01 | 15.15% | 21.4% | 0.77 | −37.6% | −14.4% | +15.8% |
| 5 | SPY 3x (UPRO) gated: contango + golden cross, else cash | 2010-01 | 21.36% | 32.0% | 0.77 | −51.4% | −21.1% | +24.1% |
| — | *ref:* SSO buy & hold, ungated | 2010-01 | 23.01% | 34.1% | 0.78 | −59.3% | −29.8% | +25.2% |
| 6 | 10%-vol-targeted SPY (daily, frictionless leverage, capped 3x) | 2010-02 | 10.24% | 11.4% | 0.91 | −14.8% | −8.7% | +9.9% |

Notes on methodology:
- **#3** gates the *actual* UPRO/TQQQ daily-reset product on whether the underlying index
  closed above its 200-day SMA the prior day (lagged one day, no look-ahead); cash (0%)
  otherwise. Filter was "on" 80.9% (SPY) / 81.0% (QQQ) of days.
- **#4** is the standard HFEA construction: 55% UPRO / 45% TMF, reset to target weights each
  calendar quarter-end. TMF (3x 20+yr Treasury) has been a drag, not a hedge, since 2022 — that
  year's bond selloff hit both legs at once, the well-known HFEA failure mode.
- **#5** replicates this repo's own methodology as closely as the requested assets allow: gate
  is `VIX/VIX3M < 1` (contango = "risk-on") **and** SPY above its 200-day SMA (golden-cross
  proxy), using actual SSO/UPRO rather than a synthetic 1x+1x overlay. Gate was "on" 78.0% of
  days. **This does not reproduce the repo's own 15.3%/11.5% headline** (see next section) — it
  produces 15.15%/21.36% CAGR for 2x/3x, both *below* plain SSO/UPRO buy-and-hold.
- **#6** targets 10% annualized realized vol off a 20-day trailing SPY estimate, daily
  rebalanced, capped at 3x, applied **frictionlessly** (no financing cost — flatters #6 versus
  reality, see "Not verified"). Average leverage deployed was 0.87x — SPY's own realized vol
  (≈17%) usually exceeds the 10% target, so the strategy spent most of its life underleveraged,
  which is why CAGR (10.24%) trails buy-and-hold despite a much smoother ride (Sharpe 0.91 vs
  0.86, max DD −14.8% vs −33.7%).

## Reconciling with our own measurement

The repo's own finding is index 1x + 1x overlay when VIX is backwardated inside a golden cross:
**15.3%/yr vs 11.5%/yr baseline, max DD 59%, 2006-2026**, with the 2020-2026 monthly sub-slice
hurting. That's a *different construction* than #5 in two ways that matter: (a) it adds a
second 1x sleeve on top of a full 1x holding (exposure ranges 1x→2x, never touching cash),
where #5 here *replaces* SPY with a real daily-reset ETF gated to 0x/2x or 0x/3x; and (b) it
spans 2006-2026, catching the 2008 crash's post-trough re-entry, while this table starts 2010.
The daily-reset compounding drag inside SSO/UPRO isn't present in a synthetic 1x+1x overlay —
that drag is exactly why #5's 2x/3x lines underperform their own ungated buy-and-hold here,
while the repo's internal 1x+1x line beat its 1x baseline. Both can be true at once:
**avoiding cash-drag via a synthetic overlay instead of a real leveraged-ETF product is doing
real work in the repo's own number**, and swapping in what a retail trader can actually buy
erodes a meaningful chunk of the edge. Worth flagging back to whoever owns that internal
finding: the 15.3% number may not survive contact with a real 2x/3x product.

## Monte Carlo: block bootstrap of monthly SPY returns, 10,000 paths, 5-month horizon

Bootstrap pool: 201 realized monthly SPY returns, 2010-01 to 2026-09 (mean +1.19%/mo, std
4.15%/mo, min −12.5%, max +12.7%). Each of 10,000 paths draws 5 months **with replacement**
from this pool (i.i.d. monthly block bootstrap, block = 1 month, the natural unit at a 5-month
horizon; doesn't capture intra-month autocorrelation or vol clustering — see caveats).
Leveraged monthly return = `L × spy_month − variance_drag`, where variance_drag approximates
daily-reset compounding cost as `0.5 × L × (L−1) × σ_daily² × 21` off the sample's realized
daily SPY vol (σ_daily = 1.075%, ≈17.1% annualized) — the same effect visible in the #2 vs #1
CAGR gap above, isolated here as a monthly constant.

| Leverage | Median 5-mo multiple | 10th pct | 90th pct | P(≥10x, i.e. $5k→≥$50k) | P(max drawdown ≥50% within 5mo) |
|---|---|---|---|---|---|
| 1x (SPY) | 1.06x | 0.94x | 1.18x | 0.00% (0/10,000) | 0.00% (0/10,000) |
| 3x | 1.13x | 0.77x | 1.57x | 0.00% (0/10,000) | 1.13% (113/10,000) |
| 5x | 1.13x | 0.55x | 1.94x | 0.00% (0/10,000) | 12.67% (1,267/10,000) |

The **highest** final multiple observed across all 10,000 five-month paths was **2.63x at 3x**
and **4.85x at 5x** — neither ever reaches 5x, let alone the 10x needed. Zero of 20,000
combined simulated paths (3x + 5x) hit $50,000 from $5,000 in 5 months. Approximate annualized
variance drag alone is 8.7%/yr at 3x and 29.1%/yr at 5x — at 5x, drag by itself exceeds SPY's
own long-run CAGR.

Probability of a margin-call-magnitude event (≥50% drawdown within the 5-month window) is
**1.1% at 3x and 12.7% at 5x** — non-trivial and rising fast with leverage, while the upside
case this plan is judged against essentially never happens. This drawdown estimate likely
*understates* real risk: at monthly resolution the simulation can't see an intra-month trough
like February 5, 2018 or April 2025, when 5x exposure could breach 50% drawdown and trigger an
actual margin call intra-month even in a month that closes flat or positive.

## Verdict against the two stated bars

| Bar | Best strategy computed | Result |
|---|---|---|
| $5,000 → $50,000 in 5 months (10x, 58.5%/mo) | Any leverage level tested (3x, 5x) | **Fails.** 0/10,000 paths at either leverage level; requires 4.6x the best single month SPY has produced in 15 years, repeated five times running. |
| 20%/year | #4 HFEA (24.3%), #3 UPRO+SMA (23.9%), #2 UPRO B&H (29.5%), #2 TQQQ B&H (43.4%) all clear it on CAGR alone | **Clears on CAGR, fails on drawdown-adjusted terms for most investors.** Every strategy that clears 20%/yr CAGR also carries a −51% to −82% historical max drawdown — money most people cannot hold through. Only #6 (vol-targeted, 10.2% CAGR) and #1 (buy-and-hold, 14-19% CAGR) stay under a 35% max DD, and neither clears 20%/yr. |

## Primary sources

- Ayres, I. & Nalebuff, B., *Lifecycle Investing* — young investors are underleveraged relative
  to their human capital and should use ~2x margin on equities early, delevering with age
  ("time diversification"). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1687272 (book
  site: https://www.lifecycleinvesting.net/). SSRN 403'd; landing-page summary didn't give the
  specific leverage ratio — treat as recalled context, not confirmed this session.
- Moreira, A. & Muir, T., "Volatility-Managed Portfolios," *JF* (2017). **Fetched successfully**
  via NBER working-paper mirror https://www.nber.org/papers/w22208 (SSRN copy exists but wasn't
  tried directly, given SSRN 403'd every other paper this session) — confirms the core finding: scaling
  exposure inversely to realized volatility "produce[s] large alphas, substantially increase[s]
  factor Sharpe ratios," taking less risk in recessions/crises while still earning high average
  returns, because vol changes aren't offset by proportional return changes. This is the
  theoretical basis for #6, whose computed result (better Sharpe, smaller drawdown, lower CAGR
  than buy-and-hold) is directionally consistent with the paper.
- Gayed, M., "Leverage for the Long Run." https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2741701
  (403'd, **not verified**: an intermarket risk-on/off signal gating leveraged equity exposure,
  similar in spirit to #3 and #5).
- Faber, M., "A Quantitative Approach to Tactical Asset Allocation."
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461 (403'd, **not verified**: a
  10-month SMA timing rule across five asset classes, reported to roughly match buy-and-hold
  return at meaningfully lower volatility/drawdown). The same logic in #3 above, tested on
  leveraged products specifically, *reduces* CAGR (23.9% vs 29.5% UPRO buy-and-hold) while
  cutting max DD (−51.4% vs −76.8%) — a risk-reducer, not a return-enhancer, once leverage is
  already in the mix.
- XIV termination, Feb 2018: Credit Suisse announced acceleration/early redemption of the
  VelocityShares Daily Inverse VIX ETN (XIV) after it lost ~96% after-hours on Feb 5, 2018
  ("Volmageddon"), final valuation ~Feb 20. SEC EDGAR filer record, Credit Suisse AG (CIK
  0001053092): https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001053092 —
  **not independently verified**: EDGAR and Wikipedia fetches failed after several attempts;
  recalled public record, not read this session. Most relevant precedent for the Monte Carlo's
  5x column: short-vol/high-leverage products can go from fine to ~4% of prior value in under
  24 hours, a tail a monthly-resolution simulation can't see.
- Robinhood margin rates (403'd) and Interactive Brokers margin rates (404'd): **neither
  verified this session**. Targets: https://robinhood.com/us/en/support/articles/margin-investing/,
  https://www.interactivebrokers.com/en/trading/margin-rates.php
- FINRA PDT rule change 2026 — **fetched and cross-confirmed twice** (direct fetch plus
  independent Wikipedia summary, consistent on every detail): Regulatory Notice 26-10,
  https://www.finra.org/rules-guidance/notices/26-10 — published Apr 20 2026, SEC accelerated
  approval Apr 14 2026, effective Jun 4 2026, broker phase-in to Oct 20 2027. It **eliminates**
  the day-trade-count PDT designation and flat $25,000 minimum-equity requirement, replacing
  them with continuous "intraday margin deficit" monitoring proportional to exposure; five
  straight business days of uncured deficit triggers a 90-day freeze on new shorts/added debit.
  Changes the backdrop for a $5,000 rapid-leverage plan: the old rule blocked pattern day
  trading below $25k outright; the new one polices margin sufficiency continuously instead —
  not necessarily looser, just a different constraint.

## Not verified

- Three of four SSRN abstracts (Ayres & Nalebuff, Gayed, Faber) returned HTTP 403 every time,
  including an alternate host for Faber's own site (`mebfaber.com`, connection refused). Only
  Moreira & Muir was independently confirmed, via the NBER mirror. The other three are described
  from training-data recollection, not a primary document read this session — treat their
  specific numeric claims as directionally right but unconfirmed.
- XIV termination sequence (dates, loss %, Credit Suisse's announcement) is recalled public
  record, not a primary filing read this session; several fetch attempts (SEC EDGAR, Wikipedia
  under two title guesses) failed to surface it directly.
- Robinhood and IBKR margin interest rates were not retrieved this session (both pages blocked);
  no current rate is quoted anywhere in this brief — don't infer a financing-cost number for a
  levered/margin build from this document.
- Strategy #6 is computed with **frictionless leverage** — no borrowing cost, no bid-ask on the
  leverage instrument. A real implementation would need to net out financing cost, which is
  exactly why the Robinhood/IBKR rate pages were in scope: #6's 10.2% CAGR is an upper bound, not
  a number bookable with $5,000 in a Robinhood account today.
- The Monte Carlo's variance-drag term is a constant approximation using whole-sample average
  daily SPY vol; it doesn't vary by simulated path (a high-vol bootstrap month should carry more
  drag than a low-vol one). This likely understates drag/risk on the worst simulated paths.
- `scripts/verify.py` was not run — it's this repo's offline gate for the live
  dashboard/backtest-harness codebase and has no bearing on a standalone research brief that
  touches none of that code; nothing in the repo's Python package was modified.
