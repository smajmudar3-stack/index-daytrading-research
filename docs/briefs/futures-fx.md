# Futures/FX trend-following and micro-futures: can it turn $5,000 into $50,000 in 5 months?

Verdict up front: no. Every computed and cited number below points the same way — trend-following on
managed-futures ETFs or a simple TSMOM/Donchian system returns single-digit-to-low-teens CAGR with real
drawdowns, and the account-size math on micro futures makes 1%-risk position sizing barely functional at
$5,000. The 58%/month implied by $5k→$50k in 5 months has no relationship to any number in this brief.

## 1. Managed-futures ETFs vs SPY, since each ETF's inception

Computed from `yfinance` daily adjusted closes, `venv/bin/python3`, run 2026-09-23.

| ETF | Inception | Years | CAGR | Max drawdown | Corr. to SPY (daily) | 2022 return |
|---|---|---|---|---|---|---|
| DBMF (iMGP DBi Managed Futures) | 2019-05-08 | 7.37 | 9.54% | -20.39% | 0.18 | +20.51% |
| KMLM (KFA Mount Lucas Managed Futures) | 2020-12-02 | 5.80 | 7.14% | -31.01% | -0.15 | +23.36% |
| CTA (Simplify Managed Futures) | 2022-03-08 | 4.54 | 9.20%* | -20.80% | -0.15 | +9.55%† |
| SPY, same window as DBMF | 2019-05-08 | 7.37 | 16.08% | -33.72% | — | -18.65% |
| SPY, same window as KMLM | 2020-12-02 | 5.80 | 15.32% | -24.50% | — | -18.65% |
| SPY, same window as CTA | 2022-03-08 | 4.54 | 16.24% | -22.09% | — | -18.65% |

\* CTA's inception is 2022-03-08, so the 2022 number is a partial year (Mar–Dec) — not a full calendar year.

**What this says:** managed-futures ETFs did exactly the job they're sold on — near-zero-to-negative
correlation to SPY, and all three were up 10–23% in the one year (2022) SPY lost 18.65%. That's the crisis-alpha
case, and it's real. It is not a source of returns that beats equities in isolation: every one of the three
trailed SPY's CAGR by 7–9 points over their own lifetimes, and each carries a real drawdown (KMLM -31%, DBMF
-20%, CTA -21%) even after fees. None of the three has existed through a full decade, so "since inception" is
a short, favorable-vol-regime sample, not a long-run verdict.

## 2. 12-month time-series momentum (TSMOM), monthly, 2010–2026

SPY, GLD, TLT, UUP, DBC, USO. Signal = sign of trailing 12-month return, computed at month-end and applied
with a 1-month lag (no look-ahead). Position sized by inverse trailing-36-month volatility (equal risk
weight, not equal dollar weight), then rebalanced monthly. Cost = 10bp per side applied to month-over-month
weight turnover.

| Variant | CAGR | Max drawdown | Ann. vol | Sharpe |
|---|---|---|---|---|
| TSMOM long/short (short when 12m return < 0) | 2.49% | -18.97% | 6.23% | 0.42 |
| TSMOM long/flat (flat when 12m return < 0) | 3.57% | -6.63% | 3.96% | 0.90 |
| Equal-weight buy & hold (same 6 ETFs) | 5.74% | -25.32% | — | — |
| SPY buy & hold | 14.34% | -23.93% | — | — |

**What this says:** the textbook TSMOM effect (Moskowitz/Ooi/Pedersen — see §4) shows up here as designed —
long/flat beats long/short (shorting bonds/FX added more whipsaw than edge over this sample) and both cut
drawdown sharply versus buying and holding the same six assets. But the return is low. 3.57%/year net of a
realistic 10bp cost is not a trading strategy for turning $5,000 into anything in months — it is a
diversification sleeve. UUP (a low-vol currency ETF) and TLT's post-2022 selloff dragged directly on this;
the sign rule is slow by construction and pays the cost of missing every V-shaped reversal.

## 3. 20-day Donchian breakout (Turtle-style), same six ETFs, 2010–2026

Daily bars. Long on a close above the prior 20-day high, short (or flat) on a close below the prior 20-day
low, position held until the opposite breakout. Same inverse-63-day-vol risk weighting, 10bp/side cost
applied to daily weight turnover.

| Variant | CAGR | Max drawdown | Ann. vol | Sharpe |
|---|---|---|---|---|
| Donchian long/short | -1.14% | -23.84% | 7.72% | -0.11 |
| Donchian long-only | 2.14% | -13.37% | 4.71% | 0.47 |

Turnover: ~56 signal flips/year across the 6-asset book (~18.6 units of one-way weight turnover per year),
so trading costs are not incidental — at 10bp/side they are a meaningful drag, and the long/short version is
a net loser after them. This matches the repo's own `02_findings/METHODOLOGY_TRAPS.md` pattern: a fast
breakout rule on daily bars generates enough whipsaw that transaction costs turn a plausible-looking signal
negative.

**Combined verdict on §2/§3:** the classic trend rules replicate published academic results in direction
(positive Sharpe, crisis convexity, long-only beats long/short by cutting bad shorts) but the *magnitude* on
this six-asset macro book is a few percent a year — nowhere near a fast-track to $50,000.

## 4. Academic and industry citations

- **Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum," Journal of Financial Economics** —
  https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum — AQR's own summary (fetched
  live) confirms the core result used above: strong positive predictability from a security's own past
  12-month return, tested on 58 futures/forward contracts across equity indices, currencies, commodities and
  bonds over more than 25 years, positive for *every* one of the 58 instruments on average. This is the paper
  §2's TSMOM rule is a direct simplification of.
- **Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following Investing" (AQR)** — could not be
  fetched this session (every AQR URL guessed for it 404'd; the correct current slug was not discoverable
  without web search). **Not verified.** From general knowledge, not confirmed live: the paper's headline is
  a trend-following index with positive average returns and a large positive skew across ~100+ years,
  including the 1929–32 crash and 2008, i.e. the same crisis-convexity property DBMF/KMLM/CTA showed in 2022
  above. Treat this citation's figures as unverified until re-fetched.
- **SG CTA Index (Societe Generale Prime Services)** — could not locate/fetch a live page this session (the
  guessed SG wholesale-banking URL 404'd, and no web search was available to find the correct current one).
  **Not verified.** Do not treat any SG CTA calendar-year figure in this brief as sourced — none is stated.
- **ESMA CFD/leveraged-product retail loss data** — https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors
  (fetched live): "NCAs' analyses on CFD trading across different EU jurisdictions shows that 74–89% of
  retail accounts typically lose money on their investments," with average per-client losses of €1,600 to
  €29,000. This is the regulatory basis for ESMA's 2018 CFD leverage caps.
- **Broker-level confirmation of the same pattern** — https://www.ig.com/uk/cfd-trading (fetched live): IG's
  own mandatory risk disclosure states "69% of retail investor accounts lose money when trading spread bets
  and CFDs with this provider." Leveraged short-horizon trading — which is what a $5k→$50k-in-5-months target
  requires — loses money for roughly seven in ten retail accounts even at a single large, well-capitalized
  broker.
- **Prop-firm payout statistics (Topstep / Apex)** — could not be fetched this session; every guessed URL
  returned 404/403 and no web search was available to find the live page. **Not verified — do not cite a
  specific pass/payout percentage from this brief.** The general, widely reported pattern (evaluation/combine
  pass rates in the single-digit-to-low-teens percent, and most funded accounts never reaching a second
  payout) is consistent with the ESMA/IG retail-CFD numbers above but is not independently confirmed here.

## 5. Micro-futures economics and minimum account size

**CME margin pages could not be fetched.** Every attempt (WebFetch and direct `curl`) on
cmegroup.com — MES, MNQ, MCL, MGC, MBT contract-spec pages — either timed out or returned an explicit block:
CME's own API returned "This IP address is blocked due to suspected web scraping activity... strictly
prohibited by CME Group's website Data Terms of Use." IBKR's commissions page (interactivebrokers.com)
returned HTTP 403 on every path tried. AMP Futures, NinjaTrader, TradeStation, Schwab, Cannon Trading,
Daniels Trading and Robinhood's futures pages all 404'd or 403'd on the URLs I could construct without a
working web search. **This section's margin figures are therefore not independently verified this session**
and should be re-checked against a live CME/broker page before being relied on.

One live figure that *did* come back: **Tradovate's published commission schedule**
(https://www.tradovate.com/pricing/, fetched live) lists an all-in commission of **$0.09 (Lifetime plan) to
$0.39 (Free plan) per contract** for "Micros & CME E-nano Index Futures," and day-trading margins as low as
$10–$20 per contract for the nano-sized (not micro) index contracts on that broker. That $10–20 figure is for
nano contracts (1/10th a micro's notional), not MES/MNQ/MCL/MGC/MBT, so it should not be read as micro-futures
margin.

Unverified order-of-magnitude figures, not to be treated as sourced: CME micros are commonly quoted with
day-trading margins roughly $50–$500/contract (MES/MNQ smallest, MCL/MGC mid, MBT largest/most volatile),
overnight SPAN initial margin several times higher. Commission is small — roughly $0.25–$0.85/side all-in,
consistent with the Tradovate figure above plus exchange/NFA fees other brokers bundle differently.

**Minimum account for a diversified 6-market system at 1% risk/trade:** a $5,000 account risking 1%/trade
risks $50/trade. A micro contract's typical one-ATR stop translates to real dollar risk per contract in the
tens to low hundreds of dollars (e.g. MES at a 15-point stop = $75/contract at $5/point; MCL at $0.50 =
$50/contract at $100/point; MBT can swing $50–150/contract on one ATR). A $5,000 account can size **at most
one micro contract in one or two of six markets at a time** under a 1% cap — several legs round to zero
contracts. A common practitioner rule of thumb — roughly $2,000–$3,000 of equity per micro contract held, to
keep margin usage and equity volatility survivable — implies a genuinely diversified 6-market system (one
contract per market simultaneously) wants **$12,000–$20,000**, not $5,000. This is a reasoned estimate, not a
fetched CME margin table, and should be re-verified against live CME/broker pages before sizing a real
account.

## 6. Judged against the target

| Claim | What was computed/found | Implied annualized | Verdict |
|---|---|---|---|
| $5,000 → $50,000 in 5 months | Requires ~58% compounded **per month** | ~(1.58)^12 - 1 ≈ tens of thousands of percent/year | No system in this brief, published academic trend result, or CTA index return is within several orders of magnitude of this. Consistent only with total-loss-risk leverage, not a repeatable edge. |
| "20%/year" as a bar | DBMF/KMLM/CTA since inception: 7–10%/yr. TSMOM long/flat: 3.6%/yr net. Donchian long-only: 2.1%/yr net. SPY buy&hold same windows: 14–16%/yr | 2–16%/yr computed here | None of the trend-following variants tested clears 20%/year; SPY buy-and-hold came closest of anything measured, and it isn't a futures/FX trend system. |
| Managed-futures ETFs as the vehicle | Real crisis-alpha (2022) and low/negative equity correlation, confirmed | 7–10%/yr with 20–31% drawdowns | A genuine diversifier, not a return engine and nowhere near the target. |
| Retail leveraged trading base rate | ESMA: 74–89% of retail CFD accounts lose money. IG's own disclosure: 69% lose money at one major broker | n/a | The base rate for retail traders attempting leveraged, short-horizon strategies is losing money, not compounding at extraordinary rates. |

**Bottom line for Sholo:** the computed numbers in this repo's own style — real backtests, real costs,
correlation and drawdown reported honestly — say managed futures and simple trend rules are legitimate,
modest-return diversifiers (2–10%/year, with real drawdowns), not a path to 58%/month. The account-size math
on micro futures also argues against running a "diversified 6-market system" on $5,000 at 1% risk — several
legs round to zero contracts. Sourcing gaps to flag explicitly: CME's own margin pages, IBKR's commission
page, the Hurst/Ooi/Pedersen century paper, the SG CTA Index page, and Topstep/Apex payout statistics could
not be fetched this session (CME actively blocks scraping; the rest 403/404'd on every URL guessed without a
working web search) — treat every figure in §5 and the two flagged citations in §4 as **not verified**, and
re-fetch before using them to size a live account.

---
*All ETF/backtest figures computed with `yfinance` + `pandas` via
`/Users/sahilmajmudar/index-daytrading/venv/bin/python3`, run 2026-09-23. Backtest code is scratch (not
checked into this repo) — computations are reproducible from the methodology described in §2/§3 (12-month
sign-rule TSMOM and 20-day Donchian breakout, both inverse-vol risk-weighted, 10bp/side costs on weight
turnover, monthly and daily respectively, 2010–2026).*
