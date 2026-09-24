# Commodities, precious-metal pairs, rate-timing and risk-parity: can it turn $5,000 into $50,000 in 5 months?

Verdict up front: no. Nothing computed below clears even the "20%/year" comparison bar, let alone the
58%/month implied by $5k→$50k in 5 months. Commodity ETFs bleed against their own futures through roll cost
and (for USO especially) regulatory position limits; simple mean-reversion pairs on gold/silver and
GDX/GLD lose money net of costs; a 10-month SMA on TLT/TMF is a real crisis-insurance rule (it saved TMF
from a -68.9% 2022) but produces low-single-digit CAGR, not growth; HFEA (55/45 UPRO/TMF) posted a strong
22.9%/year over 2010-2026 but that number is entirely a pre-2022 artifact — it drew down -69.7% from 2022
onward and is still underwater; and both risk-parity ETFs tested (RPAR, NTSX) trailed a plain 60/40
benchmark over their own lifetimes.

## 1. USO/UNG vs. their front-month futures — the roll-decay/tracking gap

Computed from `yfinance` daily adjusted closes (USO, UNG) vs. front-month futures (`CL=F`, `NG=F`),
2010-01-04 to 2026-09-22, `/Users/sahilmajmudar/index-daytrading/venv/bin/python3`, run 2026-09-23.

| Instrument | CAGR (full period) | Max drawdown |
|---|---|---|
| USO (adjusted) | -4.70% | -95.28% |
| CL=F (front-month future, price only) | +0.89% | -133.03%\* |
| **Gap (USO − CL=F)** | **-5.59 pts/yr** | |
| UNG (adjusted) | -25.10% | -99.31% |
| NG=F (front-month future, price only) | -4.02% | -83.73% |
| **Gap (UNG − NG=F)** | **-21.09 pts/yr** | |

\* CL=F's drawdown exceeds 100% because the June 2020 contract briefly traded at a *negative* price
(-$37.63 on 2020-04-20) during the COVID demand collapse — a data artifact of front-month futures, not
something an ETF experiences the same way.

The gap is not stable — it flips sign around USO's structural overhaul:

| Segment | USO CAGR | CL=F CAGR | Gap |
|---|---|---|---|
| 2010-01 to 2020-04 (USO held single front-month) | -23.94% | -13.23% | **-10.71 pts/yr** |
| 2020-05 to 2026-09 (USO spread across 6 contract months) | +37.45% | +27.73% | +9.71 pts/yr |

USO's own April 27, 2020 8-K (filed after CME imposed position limits on its front-month holdings during
the negative-oil-price episode) explains the mechanism directly: USO moved from concentrating in one
contract to holding "approximately 30%...in the July contract, approximately 15%...in the August
contract...September...October...December...and approximately 10%...in the June 2021 contract," extended
its roll window from 4 to 10 trading days, and told investors explicitly that "significant tracking
deviations can be anticipated to occur" and to "expect that there will be continued deviations between the
performance of USO's investments and the Benchmark Oil Futures Contract" (SEC EDGAR, filing
0001171200-20-000302, https://www.sec.gov/Archives/edgar/data/1327068/000117120020000302/i20277_uso-8k.htm
— fetched live). That single regulatory event is why "the roll-decay gap" is not one number: pre-2020 it
cost USO ~11 points/year against front-month oil; post-2020, spreading across the curve happened to help
during a contango-unwind/backwardation stretch. UNG's gap is large and one-directional throughout
(-16.75 pts/yr pre-2020, -29.04 pts/yr post-2020) — natural gas has run in persistent contango for most of this
window, so UNG's monthly roll into a more expensive forward contract is a structural drag with no
comparable regulatory offset.

## 2. Commodity/metals buy-and-hold and mean-reversion pairs

Buy-and-hold, adjusted close, 2010 (or PDBC's 2014-11-07 inception) to 2026-09:

| ETF | CAGR | Max DD | Sharpe |
|---|---|---|---|
| DBC | 2.56% | -66.14% | 0.23 |
| PDBC | 4.71% | -49.52% | 0.35 |
| GLD | 8.04% | -45.56% | 0.55 |
| SLV | 7.83% | -76.28% | 0.40 |
| GDX | 5.28% | -80.57% | 0.33 |

**Gold/silver ratio mean-reversion pair** (monthly z-score of the 12-month rolling GLD/SLV ratio; |z|>1
triggers a dollar-neutral long-the-cheap/short-the-rich position, 10bp/side round-trip costs, 2010-2026):
**CAGR -1.38%, max DD -25.05%, Sharpe -0.59**, across 55 position changes in 201 months. It loses money net
of costs.

**GDX-vs-GLD pair** (same construction): **CAGR -0.89%, max DD -27.97%, Sharpe -0.25**, 54 position changes.
Also a loser net of costs.

Both pair trades fail for the standard reason a naive z-score mean-reversion rule fails on a ratio with a
real trend component: the gold/silver ratio and the miners/bullion ratio have both drifted persistently
(silver structurally underperforming gold since 2011; miners structurally underperforming bullion for most
of the last decade on cost inflation and dilution), so "reversion" trades are repeatedly fighting a trend,
and 10bp/side costs on ~55 trades over 16 years are enough to turn a roughly-flat gross signal negative.

## 3. TLT/TMF: 10-month SMA and 12-month momentum timing, including 2022

| Rule | CAGR | Max DD | Sharpe | 2022 return |
|---|---|---|---|---|
| TLT buy&hold | 2.39% | -48.35% | 0.23 | -28.43% |
| TLT + 10-month SMA | 1.74% | -29.98% | 1.03 | **0.00%** (flat all year) |
| TLT + 12-month momentum | 1.28% | -32.76% | 0.81 | **0.00%** (flat all year) |
| TMF buy&hold | -4.01% | -93.29% | 0.13 | -68.93% |
| TMF + 10-month SMA | 3.07% | -54.17% | 1.08 | **0.00%** (flat all year) |
| TMF + 12-month momentum | -0.80% | -57.49% | 0.43 | **0.00%** (flat all year) |

Both timing rules correctly sat out all of 2022 (the signal turned bearish before the rate-hike drawdown
started and never re-triggered that calendar year), converting TMF's -68.9% into 0.0%. That is a genuine,
computed defensive result — trend-timing on long bonds would have avoided the entire 2022 bond crash. But
the Sharpe improvement comes overwhelmingly from drawdown avoidance, not return generation: 10-month-SMA
TLT still only compounds at 1.74%/year and TMF-with-timing at 3.07%/year over 16+ years. This is a
volatility-management tool, not a growth engine.

## 4. HYG-minus-IEF credit-spread signal for SPY

Signal: in SPY when the HYG/IEF price ratio is above its trailing 50-day mean (risk-on), else in IEF
(risk-off), 1-day-lagged, 10bp/side on regime switches, 2010-2026:

| | CAGR | Max DD | Sharpe |
|---|---|---|---|
| SPY buy&hold | 14.18% | -33.72% | 0.86 |
| HYG/IEF signal (SPY-or-IEF) | 5.90% | -39.71% | 0.56 |

323 switches over ~16.6 years (roughly one every 2.5 weeks) — this signal is too noisy at a 50-day lookback
to earn its transaction costs and whipsaws through exactly the kind of chop that erodes a mean-reversion-y
credit-spread indicator. It underperforms buy-and-hold on both return *and* drawdown. A slower-moving
average or a wider deadband might reduce switching, but as specified this is a clear loser relative to
simply holding SPY.

## 5. HFEA — 55/45 UPRO/TMF, quarterly rebalanced

| | CAGR | Max DD | Sharpe |
|---|---|---|---|
| Full period, 2010-01 to 2026-09 | **22.90%** | -70.72% | 0.86 |
| 2022-01 to 2026-09 (post rate-hike cycle) | **-7.32%** | -69.67% | -0.02 |
| 2022 calendar year alone | -63.35% | — | — |

The headline 22.9%/year is real and is also almost entirely a product of 2010-2021 — a period of falling
rates, near-zero volatility, and a triple-leveraged equity bull market feeding a triple-leveraged, negatively
correlated bond hedge. The moment rates rose fast in 2022, both legs fell together (UPRO because equities
fell, TMF because 30-year Treasuries fell harder than at any point in decades), and the strategy lost
-63.35% in a single calendar year and has not recovered: the 2022-to-now window is negative, with a max
drawdown of -69.67% that as of 2026-09-21 is still the running number (HFEA has not made a new high since
before 2022). This is the textbook regime-dependence risk with leveraged, rebalanced pair strategies: the
correlation assumption (stocks and bonds move opposite) is not a law, and when it breaks, 3x leverage on
both legs compounds the damage rather than hedging it.

## 6. RPAR and NTSX vs. 60/40, since each fund's inception

Benchmark: 60% SPY / 40% AGG, quarterly rebalanced, matched to each fund's own start date.

| Fund | Inception | CAGR | Max DD | Sharpe |
|---|---|---|---|---|
| RPAR | 2019-12-13 | 3.94% | -30.16% | 0.37 |
| 60/40 (same window) | — | 9.94% | -20.95% | 0.82 |
| NTSX | 2018-08-02 | 12.70% | -31.34% | 0.75 |
| 60/40 (same window) | — | 9.99% | -20.95% | 0.86 |

RPAR (risk-parity across equities, commodities, Treasuries and TIPS, per the fund's own page — Advanced
Research Risk Parity Index, "generate positive returns during growth, preserve capital during contraction,
preserve real returns during inflation," inception December 12, 2019, since-inception NAV return 4.31%/yr
as of 2026-08-31; https://www.rparetf.com/rpar, fetched live) trailed 60/40 by 6 points/year and took a
deeper drawdown — the fund's own bond-heavy, commodity-diversified construction was hurt badly by 2022's
simultaneous stock-and-bond selloff plus a smaller equity weight than 60/40 missing the subsequent rally.
NTSX (WisdomTree US Efficient Core — 90% notional S&P 500 exposure plus roughly 60% notional Treasury
futures overlay, marketed as "capital efficient" 90/60 leverage on a single share) beat 60/40 by ~3
points/year, which is broadly consistent with what a levered-but-diversified 90/60 sleeve should do in a
period that was net favorable to equities — but it also took a larger drawdown (-31.34% vs -20.95%) doing
it, which is the leverage showing up as intended, not a free lunch. **NTSX's own fund page
(wisdomtree.com) returned HTTP 403 on every URL tried this session (etf.com's NTSX page also 403'd) — the
strategy description above is from general knowledge of the fund's published structure, not a page fetched
this session. Not verified; re-fetch before relying on the structural claim.**

## 7. Literature cited

- **Gorton, Hayashi & Rouwenhorst (2013), "The Fundamentals of Commodity Futures Returns"** (NBER Working
  Paper 13249, published in *Review of Finance*): using 31 commodity futures 1969-2006, shows convenience
  yield/backwardation is a decreasing, non-linear function of inventory levels, and that basis and momentum
  strategies work because they proxy for inventory conditions — i.e., commodity risk premiums are real but
  time-varying and inventory-driven, not a constant carry. Rejects hedging-pressure as the primary driver.
  https://www.nber.org/papers/w13249 (fetched live). This is the academic case *for* commodities having a
  genuine, if inconsistent, risk premium — consistent with DBC/PDBC's positive-but-modest 2.6-4.7%/yr
  computed above, not with a fast compounding engine.
- **Levine, Ooi, Richardson & Sasseville (2018), "Commodities for the Long Run"** (AQR / *Financial Analysts
  Journal*): using 1877-2015 data, finds commodity futures index returns have been positive on average over
  the very long run, driven mostly by spot-price movements that vary with inflation and business-cycle
  regime, and that commodities add diversification value to a stock/bond portfolio.
  https://www.aqr.com/Insights/Research/Journal-Article/Commodities-for-the-Long-Run (fetched live). Same
  conclusion as Gorton et al.: real but modest and regime-dependent, which is exactly what DBC/PDBC's
  buy-and-hold numbers above show (2.6-4.7%/yr, nowhere near equity-like returns, let alone the target).
- **USO's April 27, 2020 Form 8-K** (SEC EDGAR, CIK 0001327068, accession 0001171200-20-000302): documents
  the CME-forced shift from front-month concentration to a spread across six contract months and a longer
  roll window, with USO's own warning that "significant tracking deviations can be anticipated." Direct,
  primary-source evidence for why the USO-vs-CL=F roll-decay gap in §1 flips sign at that date.
  https://www.sec.gov/Archives/edgar/data/1327068/000117120020000302/i20277_uso-8k.htm (fetched live).
- **RPAR fund page**: https://www.rparetf.com/rpar (fetched live) — strategy, inception, and NAV return
  figures used in §6.
- **NTSX fund page**: https://www.wisdomtree.com/investments/etfs/tactical/ntsx and the etf.com NTSX page
  both returned HTTP 403 this session and could not be fetched. **Not verified.**

## 8. Judged against the target

$5,000 → $50,000 in 5 months requires a compounded return of **58.49%/month** (computed:
(50,000/5,000)^(1/5) − 1). Annualized if sustained, that is on the order of tens of thousands of percent a
year — not a number any strategy in this repo, or in the cited academic literature, is within several
orders of magnitude of. For reference, 20%/year works out to only **1.53%/month**.

| Strategy tested | Computed CAGR | Verdict vs. 20%/yr bar | Verdict vs. 58%/month bar |
|---|---|---|---|
| USO/UNG buy-and-hold | -4.70% / -25.10% | Fails | Fails |
| DBC/PDBC/GLD/SLV/GDX buy-and-hold | 2.56% – 8.04% | Fails | Fails |
| Gold/silver ratio pair | -1.38% | Fails | Fails |
| GDX/GLD ratio pair | -0.89% | Fails | Fails |
| TLT/TMF + 10mo SMA or 12mo momentum | 1.28% – 3.07% | Fails | Fails |
| HYG/IEF credit-spread signal on SPY | 5.90% | Fails | Fails |
| SPY buy-and-hold (context) | 14.18% | Fails (close) | Fails |
| HFEA 55/45 UPRO/TMF, full period | 22.90% | Clears, but only pre-2022 | Fails, and now underwater |
| HFEA, 2022-2026 | -7.32% | Fails | Fails |
| RPAR since inception | 3.94% | Fails | Fails |
| NTSX since inception | 12.70% | Fails | Fails |

**Bottom line for Sholo:** every real, cost-inclusive number in this brief sits between -25%/year and
+23%/year, and the one number that clears 20%/year (HFEA's full-period 22.9%) only does so by averaging
over a regime that reversed hard in 2022 and hasn't recovered — the same strategy has lost money for four
straight years and change. Nothing here is a candidate for turning $5,000 into $50,000 in 5 months; that
target requires either extraordinary leverage with total-loss risk or an edge that does not appear anywhere
in this commodities/rates/risk-parity space. Sourcing gap to flag: NTSX's own fund page and etf.com both
403'd on every URL tried without a working web search — the NTSX structural description in §6 is unverified
this session and should be re-fetched before being relied on.

---
*All backtest figures computed with `yfinance` + `pandas` via
`/Users/sahilmajmudar/index-daytrading/venv/bin/python3`, run 2026-09-23, daily adjusted closes 2010-01-04
to 2026-09-22/23 (RPAR from 2019-12-13, NTSX from 2018-08-02, PDBC from 2014-11-07 — each fund's actual
inception). Pair trades: monthly z-score of the trailing-12-month ratio, |z|>1 entry threshold, dollar-neutral
legs, 10bp/side round-trip costs on every position change, 1-month execution lag. Timing rules: signal
computed at month-end, applied with a 1-month lag. HYG/IEF signal: daily, 50-day SMA of the price ratio,
1-day lag, 10bp/side on switches. HFEA and the 60/40 benchmarks: true quarterly calendar rebalancing
(re-weight to target at each new quarter's first trading day). Backtest code is scratch (not checked into
this repo) — computations are reproducible from the methodology described in each section.*
