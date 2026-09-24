<!-- research brief, filed 2026-09-23; agent output verbatim -->

# Special situations (merger arb, odd-lot tenders, spinoffs, SPACs, index adds, splits,
# airdrop farming) for a $5,000 account, 2026

**Bottom line:** "special situations" is a grab-bag of seven unrelated trades united only by
not being a directional bet on the market. Measured against $5,000→$50,000 in five months
(58%/month compounding) and against a plain 20%/year, every one fails the first by 100-2,600x
and five of the seven fail the second too. The two that could clear 20%/year on a good year
(odd-lot tenders, airdrop farming) are one-time lump payouts on a $5k base, not a repeatable
annual rate, and shrink to a few hundred dollars once the hours are counted. The live,
$5k-sized versions of merger arb (MNA, 2.63%/yr CAGR since 2010) and spinoffs (CSD, 13.09%/yr
since 2010, mostly beta, -57.5% drawdown) are measured directly below on real fund history.

## 1. What was computed

`MNA` (IndexIQ Merger Arbitrage ETF) and `CSD` (Invesco S&P Spin-Off ETF) daily adjusted closes
were pulled via `yfinance` against `SPY`, common window 2010-01-04 to 2026-09-21 (4,203
sessions, 16.68yrs, `auto_adjust=True` so dividends are included). CAGR is geometric; Sharpe
uses rf=0 (conservative for both, applied equally); max drawdown is peak-to-trough on daily
cumulative return. 10bp/side costs are irrelevant here per the brief's instruction — MNA/CSD
are single buy-and-hold ETF positions, not daily-turnover baskets.

| Metric | MNA (merger arb) | CSD (spinoffs) | SPY |
|---|---:|---:|---:|
| Total return, 2010-2026 | 54.1% | 678.2% | 816.8% |
| CAGR | **2.63%** | **13.09%** | 14.21% |
| Annualized vol | 7.42% | 22.47% | 17.06% |
| Sharpe (rf=0) | 0.39 | 0.66 | 0.86 |
| Max drawdown | -16.7% | -57.5% | -33.7% |

Confirmed against `stockanalysis.com`: MNA 1yr +2.82%, since-inception avg. annual +2.73%; CSD
1yr +39.00%, since-inception avg. annual +9.71% (from 2006 inception). Both sources agree in
direction and rough magnitude despite different start dates and averaging methods.

## 2. Merger arbitrage

Mitchell & Pulvino (2001), "Characteristics of Risk and Return in Risk Arbitrage," *JoF* 56(6)
— **not verified**: Wiley returned 403, a guessed NBER mirror resolved to an unrelated paper.
Cited from established literature: risk arbitrage earns a small, positive premium with
equity-like returns in normal markets and sharp negative skew when deal-spread risk coincides
with market stress (1987, 2008) — consistent with MNA's own low-vol, low-CAGR, small-drawdown
shape even unconfirmed firsthand. MNA is the direct answer to what merger arb pays a $5k
account: 2.63%/yr, Sharpe 0.39, diversified across live deals, 0.78%/yr expense ratio eating
roughly a third of the gross premium. A $5k account running the book directly (long target,
short acquirer on stock deals; hold to close on cash deals) skips the fee but can't diversify
away single-deal-break risk across enough simultaneous deals on $5k, and each deal needs its
terms read from the proxy.

## 3. Odd-lot tender offers

**Not verified**: `sec.gov/investor/pubs/oddlot.htm`, `sec.gov/answers/oddlot.htm`,
`investor.gov`, and Investopedia all returned 403/404/unreachable. Stated from general
knowledge: a company buys back shares from holders of under 100 shares (a "round lot") at a
fixed price, to cut per-holder servicing costs or drop below the ~300-500 holder threshold that
lets it deregister under Exchange Act §12(g). Mechanically: buy 99 or fewer shares of a name
going private, tender odd-lot, and — unlike round-lot tenders, which prorate when oversubscribed
— odd-lot holders are typically guaranteed a full fill. **No documented 2024-2026 example with a
per-account cap was located** — needs an EDGAR full-text search of `SC TO-I` filings not run
within this session's budget. Capacity is small by construction: 99 shares of a $10-40 stock is
a $1,000-4,000 one-time position, and the edge (a few percent tender premium) is a lump payout,
not a rate. Needs hours to find the situation, then weeks of waiting for nothing to happen.

## 4. Spinoffs

Cusatis, Miles & Woolridge (1993), "Restructuring Through Spinoffs," *JFE* — **not verified**
(publisher and SSRN mirrors 403). Cited from established literature: spinoffs and especially
their parents outperform matched benchmarks for up to three years, concentrated in situations
that precede a later acquisition of the spun-off unit, explained by forced index-fund selling
of the new unindexed shares unwinding over months. CSD is the direct measurement: 13.09%/yr,
actually below SPY's 14.21% over the identical window, worse Sharpe (0.66 vs 0.86) and a much
deeper drawdown (-57.5% vs -33.7% — spinoffs skew smaller-cap and more volatile). The premium
the 1993 paper describes, if it still exists, isn't visible at the diversified-basket level CSD
holds; 33 years of post-publication trading is the same McLean-Pontiff decay this repo already
found for momentum. A $5k account isolating the mechanism directly (buy the spinoff before
index addition, hold 3-12 months) is more targeted than CSD but needs picking names and reading
the Form 10.

## 5. SPAC arbitrage

Klausner & Ohlrogge (2020, Stanford Law & Econ Olin WP 559, later drafts add Ruan), fetched
directly: SPAC costs are "subtle, opaque, and far higher than previously recognized" — the
median SPAC retains only $6.67 in cash per $10 share by merger completion, and post-merger
prices decline in proportion to that dilution. That's the case against buying SPACs
post-merger, not the arbitrage meant here. The retail version: buy SPAC shares near the $10
trust value pre-deal and either redeem at the vote (trust value + accrued interest, ≈ the
T-bill rate the trust earns) or hold through a merger you like. Trust yield tracks T-bills by
construction, so the edge over just holding T-bills is the occasional SPAC trading a few cents
below trust — small, and mostly competed away since SPAC issuance collapsed after the 2021
mania. At $5k this is "own T-bills, occasionally pick up 20-50bp" — not distinguishable from
cash.

## 6. Index additions

Greenwood & Sammon, "The Disappearing Index Effect" — **not verified** (guessed NBER number
resolved to an unrelated paper; correct URL not located within budget). Cited from established
literature, and consistent with this repo's momentum finding: the S&P inclusion-day pop that
was 3-8% in 1990s-2000s literature has shrunk near zero as index flows became anticipated and
front-run well before the addition date. A $5k account buying on the announcement (after close,
effective days later) would have missed most of the edge even in the era it was largest —
market makers priced the anticipated buying in same-session.

## 7. Stock splits

No specific recent paper was located within budget; **not verified**. Stated from established
literature: splits have no mechanical value but carry a small positive announcement-day return
and modestly better subsequent 1-year performance than non-splitting peers, attributed to
management's signal that the pre-split price is expected to keep rising, not to the split
itself. A weak, noisy, long-only effect with no clean $5k execution edge — the market prices the
announcement pop before a retail order can act on it.

## 8. Crypto airdrop / points farming

No airdrop-statistics dashboard or report was fetched successfully; **not verified**. Stated
from general background knowledge: airdrop value per wallet is heavily right-skewed (early,
well-connected wallets captured most of 2023-2024's largest drops — Arbitrum, Optimism, Jito,
Celestia — while the median farmed wallet's claim across most 2024-2025 airdrops has been
reported in industry summaries as commonly under $50-200), and every major protocol now runs
Sybil detection against bot-like farming patterns. The labor is real (bridging funds, executing
qualifying transactions across chains, weeks to months ahead of an undated, unconfirmed token
event); the payout is a lottery-shaped, ordinary-income-taxable one-time drop trending down in
expected value as detection improves. Closer to this repo's gambling and prediction-markets
briefs than an investment edge.

## 9. Verdict

| Method | Live/measured edge | Capacity at $5k | Hours | vs 58%/mo (5mo→$50k) | vs 20%/yr |
|---|---|---|---|---|---|
| Merger arb (MNA, measured) | 2.63%/yr CAGR, Sharpe 0.39, -16.7% DD | Full $5k, one ticker | ~0/mo, buy-and-hold | No — needs ~2,600x | No |
| Odd-lot tenders | Few-% one-time premium, guaranteed fill <100sh | $1k-4k, event-gated | Hours to find + weeks waiting | No — lump sum, not a rate | Situational, not reliable |
| Spinoffs (CSD, measured) | 13.09%/yr, below SPY's 14.21%, -57.5% DD | Full $5k, one ticker | ~0/mo, buy-and-hold | No — needs ~450x | No — trails its benchmark |
| SPAC arbitrage | ≈T-bill + a few bp on stale trusts; pool shrunk since 2022 | Full $5k, few live candidates | Hours/wk scanning | No | No — ≈ cash |
| Index additions | 3-8% historically, ≈0 now (not verified) | No retail entry window left | Minimal | No | No |
| Stock splits | Small, noisy, pre-priced (not verified) | Full $5k if attempted | Minimal | No | No, edge is doubtful |
| Airdrop farming | Skewed, likely <$200 median, declining (not verified) | Effort-capped, not $-capped | Tens of hrs over months | No | Only ignoring hours |

Against $5,000→$50,000 in five months, nothing here comes close — the best measured annual
figure (CSD's 13.09%, which trails its own benchmark) needs roughly 450x compounding, and the
situation-specific edge net of plain equity exposure is thinner than that in every case
examined. Against 20%/year, both measured live funds fall short, and every unverified method is
either structurally small (odd-lot tenders, SPAC arb), decayed to near-zero (index additions),
or a declining one-time lottery rather than a repeatable rate (airdrop farming). Same shape as
every other honest finding in this repo: small, real in a few cases, and not a five-month plan.

**Not verified:** Mitchell & Pulvino (2001) — Wiley 403, NBER guess wrong paper. Cusatis, Miles
& Woolridge (1993) — publisher/SSRN 403. SEC's odd-lot description and any 2024-2026 documented
example with a dollar cap — sec.gov/investor.gov 403/404, Investopedia unreachable. Greenwood &
Sammon, "The Disappearing Index Effect" — guessed NBER number wrong paper, correct URL not
found. A recent stock-split paper — none fetched. Airdrop per-wallet statistics — no dashboard
fetched, that paragraph is background knowledge, not a session-verified source. MNA and CSD
performance ARE independently confirmed twice (stockanalysis.com and this session's `yfinance`
pull, above) and Klausner & Ohlrogge's SPAC abstract is directly fetched and confirmed via
Stanford Law School's publication page.
