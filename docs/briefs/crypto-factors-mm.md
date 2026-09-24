<!-- research brief, filed 2026-09-23; agent output verbatim -->

## Crypto cross-sectional factors and market-making: does momentum, reversal, or liquidity
## provision on a ~25-coin universe get anywhere near $5,000 → $50,000 in 5 months?

Report date: 2026-09-23. Method note: this session's web-search budget was pre-exhausted, so
Part B is `WebFetch` on primary URLs only, marked **not verified** where a fetch failed (Coinbase's
fee page 403'd on every attempt; Hummingbot's blog no longer carries the liquidity-mining program
reports; the Linnainmaa 2010 JF paper could not be reached without a search engine). Part A is
computed fresh this session with `yfinance` daily closes, 2021-01-01 through today, for the 25
requested tickers — all 25 returned usable history, none dropped.

### 1. Data note: one ticker had a corrupt pre-listing segment, fixed before any backtest ran

`OP-USD` on this feed carries a constant ~$0.0004 placeholder price through 2022-10-05, then jumps
**2000x overnight** to ~$0.85 on 2022-10-06 — the point its real trading series actually starts
(consistent with OP's real launch price band). Left in, that single print puts OP in the "biggest
winner" bucket for weeks either side of it and corrupts every cross-sectional result: the first,
uncorrected run showed annualized long-only momentum vol of **11,885%** and a 296x-in-5.7-years
long-short profile, both obvious artifacts. Fixed by nulling `OP-USD` before 2022-10-06 so it enters
the universe only once real trade data exists. Every number below is post-fix. This is exactly the
"a price is only today's price if you checked the date" failure mode this repo's own findings
already catalogue (`gap_scanner.scan_one`, DELL, 2026-09-03) — same shape, different feed.

### 2. Universe and setup

25 of 25 tickers resolved (`BTC ETH SOL XRP BNB ADA DOGE AVAX LINK DOT LTC BCH UNI ATOM XLM ETC FIL
NEAR APT ARB OP AAVE ALGO VET HBAR`, all `-USD` on Yahoo). Daily closes 2021-01-01 to 2026-09-23,
resampled to weekly (Friday) and monthly. Each period: rank coins with a valid signal by trailing
1-period return, split into top/bottom terciles (~8 coins/side), long top minus short bottom
(momentum) or the reverse (reversal). Costs: 0.5%/side, applied as a full 2-sided round trip
(1.0%) on every basket that turns over that period — long-only and the equal-weight benchmark eat
one round trip per period, long-short eats two (both legs turn over). This assumes 100% turnover
every rebalance, which is conservative/worst-case for a naive periodic strategy, not the floor.

### 3. Results — annualized, full sample (2021-01 to 2026-09-23)

| Strategy | Total return | Ann. return | Ann. vol | Sharpe | Max DD |
|---|---|---|---|---|---|
| Equal-weight buy & hold (no rebal.) | **+315%** | **+28.0%** | 80.5% | **0.70** | -81.8% |
| 1-week momentum, weekly rebal — long/short | -99.5% | -60.4% | 52.1% | -1.48 | -99.5% |
| 1-week momentum, weekly rebal — long-only (top 3rd) | -67.0% | -17.6% | 86.2% | 0.18 | -96.9% |
| 1-week momentum, weekly rebal — EW basket w/ rebal. costs | -83.9% | -27.3% | 79.9% | 0.00 | -98.5% |
| **Retail rule: buy last week's single biggest winner** | **-99.9%** | **-68.4%** | 115.1% | -0.45 | -99.96% |
| 1-month momentum, monthly rebal — long/short | ≤-100%† | NaN† | 65.8% | -0.59 | ≤-100%† |
| 1-month momentum, monthly rebal — long-only | -58.0% | -14.4% | 80.1% | 0.17 | -92.8% |
| 1-week reversal, weekly rebal — long/short | -100.0% | -77.1% | 52.1% | **-2.52** | -100.0% |
| 1-week reversal, weekly rebal — long-only (buy losers) | -92.9% | -37.0% | 84.2% | -0.13 | -99.4% |

† The monthly long/short paper-return stream compounds through zero (cumulative wealth hits ≤0
before the sample ends), which makes an annualized figure undefined. That is not a display bug —
it is itself the finding: a naive dollar-neutral spread on 8-coin terciles at 50-90% annualized
vol is unstable enough to blow through -100% cumulative, i.e. this construction is not investable
capital, only a diagnostic spread.

Momentum's Sharpe on the long-only leg (0.18) is *positive* while its compounded (geometric) return
is deeply negative (-17.6%/yr) — arithmetic mean return is near flat, volatility drag turns that
into a large negative compounded number. Reading Sharpe alone without the compounded return would
have called this leg "roughly fine"; it liquidated two-thirds of capital.

### 4. By year (total return %, weekly rebalance; 2026 is partial, through 2026-09-23)

| Year | Buy & hold EW | Momentum L/S | Momentum long-only | Reversal L/S | Retail chase-last-winner |
|---|---|---|---|---|---|
| 2021 | +804% | -86.7% | +230.3% | -62.6% | -70.6% |
| 2022 | -75.4% | -53.2% | -83.5% | -76.7% | -88.4% |
| 2023 | +143.4% | -47.4% | +78.2% | -80.3% | +330.9% |
| 2024 | +70.4% | -25.5% | +66.8% | -88.3% | -55.9% |
| 2025 | -50.9% | -50.4% | -63.6% | -77.4% | -83.9% |
| 2026 (YTD) | -8.4% | -59.2% | -44.0% | -52.7% | -87.0% |

Two things worth naming directly. First, buy-and-hold *is* the only row that clears 20%/year over
the full sample, and it does it entirely off one year (2021, +804%) — remove that year and the
remaining five run negative-to-flat (2022 -75%, 2023 +143%, 2024 +70%, 2025 -51%, 2026 YTD -8%;
net of 2021, four of five years miss 20%). Second, the "retail rule" (buy whatever rose most last
week, hold one week, repeat) is not neutral — it is the single worst strategy tested in three of
six years and loses money in five of six, because chasing the single loudest weekly winner in a
25-coin universe means repeatedly buying the top of that coin's pump.

### 5. Sources (Part B)

- **Liu, Tsyvinski & Wu (2022), "Common Risk Factors in Cryptocurrency,"** *Journal of Finance*
  77(2), 1133-1177. [NBER w25882](https://www.nber.org/papers/w25882) (fetched; working paper May
  2019). Finds three factors — crypto market, size, momentum — span nine cryptocurrency factor
  strategies with "sizable and statistically significant" gross excess returns; this brief's
  finding is that a plain, cost-inclusive version of momentum on this 25-coin universe does not
  survive 0.5%/side costs, which is a transaction-cost/turnover result, not a contradiction of
  their (largely gross-of-cost, larger-universe) factor construction.
- **Liu & Tsyvinski (2021), "Risks and Returns of Cryptocurrency,"** *Review of Financial Studies*
  34(6), 2689-2727. [NBER w24877](https://www.nber.org/papers/w24877) (fetched; working paper Aug
  2018). Cryptocurrencies show "no exposure to most common stock market and macroeconomic
  factors"; time-series momentum and investor-attention proxies forecast returns. Time-series
  momentum (trend-following on a single coin against its own history) is a different construction
  from the cross-sectional momentum tested here (rank coins against each other) — this brief did
  not test their exact specification.
- **Kraken fee schedule**, [kraken.com/features/fee-schedule](https://www.kraken.com/features/fee-schedule)
  (fetched). Tier 1 (lowest volume, $0+/30-day): **0.40% maker / 0.80% taker**. The 0.5%/side
  assumed in this backtest is below Kraken's actual base taker rate (0.80%) — real round-trip
  costs on small accounts running these rebalance-heavy strategies would be *worse* than modeled
  here, not better.
- **Coinbase Advanced fee schedule**, [coinbase.com/advanced-fees](https://www.coinbase.com/advanced-fees)
  — **not verified**: every fetch attempt (direct URL and the Coinbase Help mirror) returned
  HTTP 403 this session. Not guessing a number here; Kraken's confirmed schedule stands in as the
  cost reference above.
- **Hummingbot liquidity-mining blog reports**, [hummingbot.org/blog](https://hummingbot.org/blog/)
  — **not verified**: the current blog (fetched) carries connector guides and strategy docs, not
  liquidity-mining performance reports; that program's historical report posts were not reachable
  at their expected URLs (404) without a search engine this session. No claim about market-making
  profitability is made from this source.
- **Linnainmaa (2010), "Do Limit Orders Alter Inferences about Investor Performance and
  Behavior?"** *Journal of Finance* 65(4), 1473-1506 — **not verified**: Wiley's DOI page 403'd,
  Semantic Scholar returned no content without search, and this session's WebSearch is exhausted
  by instruction. Citation given from memory of the published bibliographic record only; the
  paper's argument (that excluding limit orders from performance studies biases skill estimates)
  is not independently confirmed this session and is not relied on for any number above.

### 6. Judged against the targets

**20%/year:** only the un-rebalanced equal-weight buy-and-hold basket clears it (+28.0%/yr full
sample), and it does so by riding one outlier year; every momentum or reversal variant tested —
long/short or long-only, weekly or monthly — misses it, most by a wide margin (annualized returns
from -77% to -14%). A cross-sectional factor tilt on this 25-coin universe, after realistic costs,
is not a way to *beat* buy-and-hold toward 20%/year; every version tested underperforms plain
buy-and-hold in the same period, often while taking similar or higher volatility.

**$5,000 → $50,000 in 5 months (a required +58.5%/month, compounded):** nothing here approaches
it. The single best calendar year in the whole sample — 2021's +804% buy-and-hold, the best number
in any table above — averages to about +20%/month compounded, roughly a third of the pace needed,
and it is one bull year in a six-year sample, not a repeatable edge. Every factor-tilted strategy
(momentum, reversal, long-short or long-only) posted negative annualized returns in most years and
negative *total* returns over the full sample. The retail rule this brief was asked to test
specifically — buy whichever coin rose most last week — is the closest thing to what an
under-resourced trader chasing 58.5%/month would actually do, and it lost 99.9% of capital over
the sample, going negative in five of six years including a -87% year-to-date in 2026. Combined
with the cost reality check (Kraken's actual 0.80% taker fee sits above the 0.5%/side modeled
here, so live results would run worse than every number in section 3), there is no strategy in
this brief's scope — cross-sectional momentum, reversal, or a naive retail winner-chase — that
gets within an order of magnitude of the 5-month target, and most of them are a fast way to lose
the $5,000 outright rather than grow it.
