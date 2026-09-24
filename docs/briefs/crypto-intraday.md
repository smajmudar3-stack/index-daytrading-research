<!-- research brief, filed 2026-09-23; agent output verbatim -->

# Crypto intraday strategies on a US-legal retail venue: seasonality, momentum, breakout,
# mean-reversion, funding-time — does any of it clear costs, or 58%/month, or 20%/yr?

Report date: 2026-09-23. Method note: this session's `WebSearch` budget was pre-exhausted, so all
web verification below is `WebFetch` on primary URLs, with one retry on a 403 before marking
**not verified**. Part A (the backtest) is computed fresh this session with `yfinance` hourly bars,
`period="730d"` (2024-09-25 to 2026-09-24 UTC), BTC-USD and ETH-USD, using
`/Users/sahilmajmudar/index-daytrading/venv/bin/python3`. This brief does not repeat
`docs/briefs/crypto-derivatives.md` (funding carry, CME basis, VRP, MEV, cross-exchange arb — all
struck out there) or `docs/briefs/crypto-factors-mm.md` (25-coin cross-sectional momentum/reversal
— also struck out, at daily/weekly frequency); this one is the hourly, single-asset, intraday
layer under both.

## 1. Fee reality check — the task's 0.26%/side Kraken assumption does not hold at $5,000

Fetching Kraken's live fee schedule (`kraken.com/features/fee-schedule`, fetched via `curl` with a
browser user-agent after the AI-summarized `WebFetch` gave an inconsistent read on the first pass)
gives the actual spot maker/taker tiers by trailing-30-day volume:

| Tier | 30-day volume | Maker | Taker |
|---|---|---|---|
| 1 | $0+ | 0.40% | **0.80%** |
| 2 | $2.5K+ | 0.30% | **0.60%** |
| 3 | $10K+ | 0.22% | 0.38% |
| 4 | $25K+ | 0.20% | 0.35% |
| 5 | $50K+ | 0.15% | 0.30% |
| 6 | $100K+ | 0.12% | **0.25%** |
| 7 | $250K+ | 0.10% | 0.22% |

A $5,000 account with no trading history sits in **Tier 2 at 0.60% taker**, not 0.26%. Tier 6
(0.25%, the closest match to the task's 0.26%) needs $100K of trailing 30-day *volume* —
reachable from a $5,000 book only through turnover, not account size (the rules below trade
8,000–17,000 times over two years, which would clear that on churn alone). So 0.26%/side is
optimistic for week one and roughly right once a bot self-funds its way up the tier ladder. All
net figures below use 0.26%/side (0.52% round trip) as instructed; **read the net column as a
best case, not a floor** — early on, the real cost is 0.60–0.80%/side, 2.3–3x worse.

Coinbase Advanced's fee page (`help.coinbase.com/.../fees` and `coinbase.com/advanced-fees`)
**403'd on both attempts**, consistent with `crypto-derivatives.md`'s and
`crypto-factors-mm.md`'s prior sessions — **not verified** independently this session; the
0.6%/side figure in the task and those two priors is taken as given.

## 2. The backtest: every rule tested, gross and net, 2024-09 to 2026-09

Universe: BTC-USD, ETH-USD hourly bars, `yfinance`, 17,462–17,465 bars each, UTC natively
(verified: index tz is `UTC`, not exchange-local). All rules hold one bar (1h) after signal;
"trade" = enter this bar, exit next bar, so cost is a full round trip (2 × 0.26% = 52bp) on every
active bar, no netting across consecutive same-direction signals — conservative/worst-case, same
convention as `crypto-factors-mm.md`.

**34 distinct rule/ticker combinations were tested** (momentum and reversal at 1h/4h/24h lookback,
long-short and long-only = 24; breakout of the prior-24h high/low, long-short and long-only = 4;
mean-reversion z-score band, long-short and long-only = 4; funding-time = 2), plus **74
seasonality descriptive tests** (24 hours × 2 tickers, 7 weekdays × 2, weekend/weekday × 2, US/Asia
open × 2, funding pre/post × 2). Total **142 tests**, so the multiple-testing noise bar is
`sqrt(2·ln(142)) ≈ 3.15`. No t-stat in this report — gross or seasonal — reaches 3.15. The single
closest, ETH's mean-reversion band, gets to 2.38.

| Rule | Ticker | N trades | Gross bp/trade | t (gross) | Net bp/trade (Kraken 0.52% RT) | t (net) |
|---|---|---:|---:|---:|---:|---:|
| momentum 1h, long-short | BTC | 17,463 | -0.19 | -0.51 | -52.2 | -144.0 |
| momentum 1h, long-short | ETH | 17,459 | 0.46 | 0.86 | -51.5 | -95.9 |
| momentum 1h, long-only | BTC | 8,828 | -0.03 | -0.06 | -52.0 | -103.1 |
| momentum 1h, long-only | ETH | 8,872 | 0.46 | 0.63 | -51.5 | -70.6 |
| reversal 1h, long-short | BTC | 17,463 | 0.19 | 0.51 | -51.8 | -142.9 |
| reversal 1h, long-short | ETH | 17,459 | -0.46 | -0.86 | -52.5 | -97.6 |
| reversal 1h, long-only | BTC | 8,635 | 0.34 | 0.66 | -51.7 | -99.2 |
| reversal 1h, long-only | ETH | 8,587 | -0.46 | -0.59 | -52.5 | -66.3 |
| momentum 4h, long-short | BTC | 17,459 | 0.07 | 0.19 | -51.9 | -143.2 |
| momentum 4h, long-short | ETH | 17,454 | 0.71 | 1.31 | -51.3 | -95.4 |
| momentum 4h, long-only | BTC | 8,873 | 0.22 | 0.44 | -51.8 | -102.7 |
| momentum 4h, long-only | ETH | 8,892 | 0.71 | 1.00 | -51.3 | -72.3 |
| reversal 4h, long-short | BTC | 17,459 | -0.07 | -0.19 | -52.1 | -143.6 |
| reversal 4h, long-short | ETH | 17,454 | -0.71 | -1.31 | -52.7 | -98.0 |
| reversal 4h, long-only | BTC | 8,586 | 0.09 | 0.17 | -51.9 | -99.5 |
| reversal 4h, long-only | ETH | 8,562 | -0.71 | -0.87 | -52.7 | -64.9 |
| momentum 24h, long-short | BTC | 17,440 | 0.04 | 0.11 | -52.0 | -143.2 |
| momentum 24h, long-short | ETH | 17,436 | -0.27 | -0.50 | -52.3 | -97.1 |
| momentum 24h, long-only | BTC | 9,023 | 0.20 | 0.42 | -51.8 | -108.0 |
| momentum 24h, long-only | ETH | 8,909 | -0.24 | -0.33 | -52.2 | -73.7 |
| reversal 24h, long-short | BTC | 17,440 | -0.04 | -0.11 | -52.0 | -143.4 |
| reversal 24h, long-short | ETH | 17,436 | 0.27 | 0.50 | -51.7 | -96.1 |
| reversal 24h, long-only | BTC | 8,417 | 0.13 | 0.24 | -51.9 | -94.6 |
| reversal 24h, long-only | ETH | 8,527 | 0.30 | 0.37 | -51.7 | -63.5 |
| breakout of prior 24h high/low, long-short | BTC | 1,708 | 1.08 | 0.73 | -50.9 | -34.4 |
| breakout of prior 24h high/low, long-short | ETH | 1,539 | 3.42 | 1.45 | -48.6 | -20.6 |
| breakout, long-only | BTC | 896 | 0.54 | 0.27 | -51.5 | -26.0 |
| breakout, long-only | ETH | 848 | **5.33** | **1.89** | -46.7 | -16.5 |
| mean-reversion z-score>\|2\|, long-short | BTC | 2,177 | -0.62 | -0.48 | -52.6 | -41.1 |
| mean-reversion z-score>\|2\|, long-short | ETH | 2,173 | **-4.61** | **-2.38** | -56.6 | -29.2 |
| mean-reversion, long-only (buy dips only) | BTC | 1,105 | -1.18 | -0.65 | -53.2 | -29.3 |
| mean-reversion, long-only (buy dips only) | ETH | 1,026 | -2.80 | -0.90 | -54.8 | -17.6 |
| funding-time, long the hour before 00/08/16 UTC | BTC | 2,183 | -0.04 | -0.04 | -52.0 | -50.4 |
| funding-time, long the hour before 00/08/16 UTC | ETH | 2,182 | 0.12 | 0.08 | -51.9 | -33.8 |

Every net column is deeply, "significantly" negative — but that significance is an artifact, not
a finding: with 8,000–17,000 one-bar trades, a constant 52bp cost against a near-zero gross edge
produces t-stats of -20 to -144 almost by construction (52bp is ~1,400x the typical per-trade
standard error at this sample size). **The only number worth reading per row is gross t vs. the
3.15 noise bar**, and nothing clears it.

Two rows are the closest to real. **ETH mean-reversion** (short above +2 z, buy below -2 z on a
24h band) shows gross t=-2.38 — but the *negative* sign means the band **loses** money as a
mean-reversion rule: ETH's 24h extremes keep extending rather than reverting over this sample
(anti-mean-reversion, consistent with a trend-dominated 2024-26). **ETH 24h breakout** (long-only)
has the best raw gross edge, t=1.89, +5.3bp/trade before cost — but 848 trades in 2 years is thin,
and it needs to clear both the 52bp round-trip cost and the 3.15 noise bar (it clears neither).

### Seasonality (condensed — full 24-hour table omitted, none clear the bar)

| Effect | Ticker | Mean bp | t | N |
|---|---|---:|---:|---:|
| Hour 23 UTC (worst hour, both assets) | BTC | -3.39 | -2.39 | 728 |
| Hour 23 UTC | ETH | -4.77 | -2.30 | 728 |
| Thursday (worst weekday, ETH) | ETH | -3.33 | -2.30 | 2,497 |
| Hour 21 UTC (best hour, ETH) | ETH | +5.59 | 2.12 | 729 |
| US open (13:00–15:00 UTC) | BTC | ~flat | <1.4 | 1,456 |
| US open (13:00–15:00 UTC) | ETH | ~flat | <1.0 | 1,456 |
| Asia open (00:00–02:00 UTC) | BTC / ETH | ~flat | <1.0 | 1,456 |
| Weekend vs. weekday | BTC / ETH | ~flat, no gap | <0.7 | full sample |
| Funding-time pre/post (00/08/16 UTC) | BTC / ETH | ~flat | <0.9 | ~4,300 |

The single most extreme reading across all 142 tests (BTC hour 23 UTC, t=-2.39) is below the 3.15
noise bar. "US open" and "Asia open" — the two effects retail crypto folklore names most often —
show no detectable edge in either direction on this sample. The weekend effect (crypto trades
7 days a week, so "weekend" here means Saturday/Sunday UTC calendar days, not a closed market) is
flat too.

## 3. Out-of-sample: split the sample in half, check the two best-looking rules both ways

First half: 2024-09-25 to ~2025-09-25 (n≈8,730/asset). Second half: ~2025-09-25 to 2026-09-24.

| Rule | Ticker | Half | Gross bp/trade | t (gross) |
|---|---|---|---:|---:|
| ETH mean-reversion, long-short | ETH | first | -2.60 | -0.87 |
| ETH mean-reversion, long-short | ETH | second | -6.54 | **-2.62** |
| BTC mean-reversion, long-short | BTC | first | +1.30 | 0.70 |
| BTC mean-reversion, long-short | BTC | second | -2.47 | -1.39 |
| breakout 24h, long-only | BTC | first | -2.20 | -0.82 |
| breakout 24h, long-only | BTC | second | +3.89 | 1.32 |
| breakout 24h, long-only | ETH | first | +3.55 | 0.95 |
| breakout 24h, long-only | ETH | second | +7.62 | 1.76 |
| momentum 4h, long-only | BTC | first | +0.32 | 0.43 |
| momentum 4h, long-only | BTC | second | +0.12 | 0.18 |

Neither survives a clean split. ETH mean-reversion flips from weak (t=-0.87) to the sample's
strongest single reading (t=-2.62) between halves — same sign both times, but the magnitude
doubling is instability, not confirmation, and it stays short of the noise bar even at its
strongest. BTC mean-reversion flips sign entirely (+0.70 → -1.39). Breakout-long on ETH is
directionally consistent (weak positive both halves) but never significant alone. A real effect
should hold size and sign across a split; here sign wobbles and size swings 2-8x.

## 4. Sources

- **Kraken fee schedule**, [kraken.com/features/fee-schedule](https://www.kraken.com/features/fee-schedule)
  (fetched via `curl` with a browser UA; the table above is parsed straight from the page's own
  HTML). Confirms the task's 0.26%/side is below the $5,000-account rate (0.60% Tier 2) and only
  matches once ~$100K/30-day volume accrues (Tier 6, 0.25%).
- **Coinbase Advanced fees**, `help.coinbase.com/.../fees` and `coinbase.com/advanced-fees` —
  **not verified**: both 403'd, third time this repo has hit that wall on Coinbase's fee pages
  (see `crypto-derivatives.md`, `crypto-factors-mm.md`). Task's 0.6%/side figure taken as given.
- **Binance spot fee schedule**, [binance.com/en/fee/schedule](https://www.binance.com/en/fee/schedule)
  (fetched). Base (VIP 0) tier: 0.10%/0.10% maker/taker, no negative maker rebate at any published
  tier — offered here as the maker-rebate reference the task asked for; Binance itself is not a
  US-legal venue and is out of scope for execution.
- **Auer, Cornelli, Doerr, Frost & Gambacorta, "Crypto trading and Bitcoin prices: evidence from a
  new database of retail adoption,"** BIS Working Paper 1049, Nov 2022.
  [bis.org/publ/work1049.htm](https://www.bis.org/publ/work1049.htm) (fetched). Retail crypto
  adoption tracks price momentum (app downloads and active users rise with BTC price, skewed
  male/under-35); the paper's headline number is that **roughly three-quarters of retail Bitcoin
  investors are estimated to have lost money** on their holdings. This is the "who wins" evidence
  the task asked for — not intraday-specific, but directly on point: it is a base-rate finding
  about retail crypto participation generally, not this brief's specific rule set, and it is
  consistent with (not proof of) the zero-edge intraday results above.

## 5. Verdict

**58%/month:** nothing here is close. Every one of the 34 rules loses 46-57bp per trade net of the
instructed cost, on thousands of trades a year — not underperformance, a slow bleed. The single
best gross signal (ETH 24h breakout, +5.3bp/trade, ~1.2 trades/day) would need ~10x its own edge
just to clear the 52bp round-trip cost, and it isn't distinguishable from noise even before costs
(t=1.89 vs. a 3.15 bar).

**20%/year:** also no. No rule produces a positive net expectancy at any horizon tested, so
actually running any of them compounds losses, not gains. The only way this data touches 20%/yr
is not trading — buy-and-hold BTC/ETH over this same window beat every rule here, echoing
`crypto-factors-mm.md`'s finding that the un-rebalanced benchmark beat every cross-sectional tilt
too. That's evidence against active intraday trading as the mechanism, not for it.

**Overall:** hourly BTC/ETH momentum, reversal, breakout, mean-reversion-band, time-of-day/day-of-
week seasonality, and funding-time effects all show gross edges indistinguishable from zero once
142 tests are judged against the honest multiple-testing bar, and every one of them is
economically dead the moment Kraken's real 52bp+ round-trip cost is applied — a cost that, at a
fresh $5,000 account, actually starts even worse (104-160bp round trip at Tier 1-2) than the
0.52% this report used throughout at the task's instruction. The "US open," "Asia open," and
weekend effects that retail crypto commentary treats as folklore are flat in this data. Nothing in
this brief clears either target; nothing in it is worth automating as-is.
