# ETF and closed-end fund pricing gaps: can it turn $5,000 into $50,000 in 5 months?

Verdict up front: no. CEF discounts are real and currently wide on several large funds, but a
mechanical "buy the discount" rule net of costs is flat-to-negative on every pair tested here.
Plain-vanilla ETF arbitrage — what keeps SPY/HYG/LQD near NAV — is an
authorized-participant-only business that structurally excludes a $5,000 account; APs already
capture it. "Short both legs of a leveraged-ETF pair" is real in theory (small positive gross
return below) but is overwhelmed by real-world borrow costs, and even gross it has lost money
four years running. Nothing here clears 20%/year, let alone the ~58%/month the $5k→$50k/5mo
target requires.

## 1. CEF discount mean reversion

**Current discounts, fetched live from CEF Connect's own data API on 2026-09-23**
(`https://www.cefconnect.com/api/v3/DiscountCharter/fund/<TICKER>/1Y` — the JSON feed that
renders each fund's discount chart, pulled directly via `curl` after the rendered HTML page
repeatedly timed out through WebFetch):

| Fund | Category | Last | 1-yr mean | 1-yr range |
|---|---|---|---|---|
| PDI (PIMCO Dynamic Income) | Leveraged multi-sector bond | **-7.93%** | +6.15% | -7.93% to +16.77% |
| PTY (PIMCO Corp. & Income Opp.) | Leveraged corporate bond | **-0.72%** | +7.84% | -0.72% to +22.50% |
| GAB (Gabelli Equity Trust) | Leveraged equity | **-3.21%** | +0.78% | -6.88% to +11.35% |
| ADX (Adams Diversified Equity) | Unleveraged equity | **-2.08%** | -4.72% | -9.68% to -0.04% |
| BST (BlackRock Science & Tech) | Leveraged equity | **-3.10%** | -6.21% | -11.46% to -1.79% |

PDI/PTY carried the "PIMCO premium" for years (double-digit, up to +16.8%/+22.5%) and only
flipped to a discount in the last few weeks — the regime break that defeats a fixed threshold.
ADX/BST instead run *persistent* discounts (means -4.7%/-6.2%) rather than oscillating near
zero — the same non-mean-reverting-level problem that broke gold/silver and GDX/GLD in
`docs/briefs/commodity-rates.md` §2.

**Lee, Shleifer & Thaler (1991), "Investor Sentiment and the Closed-End Fund Puzzle,"** *Journal
of Finance* 46(1), pp. 75-109: CEF discounts move together across unrelated funds (a common
factor attributed to individual-investor sentiment, since CEFs are disproportionately
retail-held), correlate with small-cap/value performance, and narrow sharply around open-ending,
tenders, or liquidation — real but event-driven, not a clock. **Not verified this session:**
JSTOR and Wiley both blocked the abstract, and two NBER working-paper-number guesses both
resolved to an unrelated Freeman labor-economics paper; citation and mechanism are standard
literature facts, not text read live.

**Computed backtest** — 60-day trailing relative log return of CEF vs. same-asset-class ETF proxy
(SPY for equity CEFs, HYG for bond CEFs), z-scored against its own trailing 504-session mean/std,
long CEF / short ETF at z < -2, exit z > 0, 10bp/side per change, 1-day lag, 2010-2026 (2015 on
for PDI, 2017 on for BST, per inception):

| Pair | CAGR | Max DD | Sharpe | Trades | Time in mkt |
|---|---|---|---|---|---|
| ADX vs SPY | -0.52% | -12.86% | -0.14 | 18 | 12% |
| GAB vs SPY | -1.01% | -23.62% | -0.07 | 18 | 17% |
| PDI vs HYG | +2.46% | -30.36% | 0.30 | 19 | 10% |
| PTY vs HYG | -0.41% | -33.73% | 0.02 | 10 | 9% |
| BST vs SPY | -2.40% | -30.62% | -0.26 | 8 | 16% |

Buy-and-hold context, same window, dividends reinvested: ADX 13.39% (DD -37.17%, Sharpe 0.81),
GAB 11.44% (-46.92%, 0.62), PDI 9.02% (-46.47%, 0.59), PTY 9.96% (-46.55%, 0.57), BST 17.22%
(-46.04%, 0.76), SPY 14.20% (-33.72%, 0.86), HYG 5.18% (-22.03%, 0.66).

Four of five pairs lose money or are flat; PDI/HYG is the lone positive Sharpe (0.30) and still
trails SPY buy-and-hold by 11+ points/year. Same failure mode as the commodity pairs: the noisy
proxy (relative return to an ETF, since NAV isn't on `yfinance`) keeps fighting each fund's real,
sustained leverage- or sentiment-driven trend instead of reverting to it.

**Capacity for $5,000:** not the binding constraint. Three-month average dollar volume: PDI
~$46.3M/day, PTY ~$13.3M/day, ADX ~$7.1M/day, BST ~$4.4M/day, GAB ~$4.3M/day — $5,000 is
0.01-0.1% of one day's volume on every one. These are thin only at institutional size ($1.7B-
$6.5B funds trading a few million/day); the binding constraint is the flat-to-negative net edge,
not size.

## 2. ETF premium/discount "arbitrage" — why retail can't do it

Mechanism: authorized participants (APs — banks/market makers under contract with the sponsor)
create ETF shares by delivering the underlying basket, and redeem shares for the same basket.
Above NAV, an AP buys the basket, delivers it for new shares, sells the premium; below NAV, the
reverse — this flow is why liquid ETF premiums/discounts run a few basis points, not the price
of scarcity. **iShares' HYG product page, fetched live 2026-09-22**
(`https://www.ishares.com/us/products/239565/ishares-iboxx-investment-grade-corporate-bond-etf`):
premium/discount **0.13%**, 30-day median bid/ask spread **0.01%** — the AP mechanism doing its
job, no retail-accessible gap.

**March 2020:** large investment-grade bond ETFs including LQD traded at unusually wide
discounts to their stale reported NAV during the liquidity crunch, because the underlying bonds
weren't trading while the ETF, on-exchange, discovered a real, lower clearing price. **Not
verified this session:** four sources — NY Fed Liberty Street, the SEC's COVID-19 credit-market
report (too large to fetch), an ICI PDF (404), a BIS article (403) — all failed, and WebSearch is
exhausted; the widely-cited magnitude (LQD several percent below NAV for a few sessions) is a
recollection, not confirmed live. The mechanism point holds regardless: this was read as the ETF
price leading a stale bond market, not ETF failure — the opposite of a standing retail
opportunity — and it closed within days once the Fed announced bond-buying facilities.

This gap is captured by APs holding real inventory and a contractual create/redeem right, not by
an account trading shares on-exchange. No version of it is executable at $5,000.

## 3. Leveraged-ETF pair decay ("short both legs")

Idea: UPRO (3x long S&P 500) and SPXU (3x short) both lose value to daily-reset volatility drag
relative to a naive long-run 3x/-3x, so shorting both dollar-neutral, rebalanced daily, should
harvest that drag. **Computed, daily adjusted closes, 2010-01-04 to 2026-09-21:**

| | CAGR | Max DD | Sharpe |
|---|---|---|---|
| UPRO buy & hold | 29.52% | -76.82% | 0.77 |
| SPXU buy & hold | -40.88% | -99.99% | -0.78 |
| SPY buy & hold (context) | 14.21% | -33.72% | 0.86 |
| **Short 50/50 UPRO+SPXU, gross** | **+0.21%** | **-10.16%** | **0.16** |
| ...net of 2%/yr borrow (both legs) | -1.78% | -25.95% | -1.34 |
| ...net of 5%/yr borrow (both legs) | -4.68% | -55.05% | -3.59 |
| ...net of 10%/yr borrow (both legs) | -9.33% | -80.48% | -7.33 |

`yfinance` has no borrow-fee data, so those rows apply a flat annualized drag to the gross daily
return. The gross number is small and positive, consistent with the textbook decay story, but
three things break it live. **Borrow dominates immediately**: even a low 2%/yr (these go
hard-to-borrow, especially SPXU in extended bull runs) flips 16 years of gross gains negative.
**The decay isn't stable**: the gross pair earns +1-3%/yr through 2010-2017, spikes to +3.34% in
the 2020 vol shock, then runs negative in 2018 (-0.40%), 2019 (-0.89%), and every year 2023-2026
(-2.78%, -3.27%, -2.32%, -1.50%) — the recent low-vol grind is bad for this position even before
financing, since each leg carries its own fee and tracking error rather than being a frictionless
mirror. **It isn't tail-safe**: worst single day was only -1.64% (2020-03-17), reflecting one
path — a sustained, high-vol directional move is what this structure is most exposed to, and
margin on two short leveraged legs isn't guaranteed available in a crisis.

**Capacity for $5,000:** volume isn't the constraint (~$250-290M/day/leg), but this is the one
method a $5,000 account genuinely can't execute as priced — shorting needs margin (Reg T ~150%)
and locatable borrow on both legs, and retail brokers commonly restrict or price above the
2-10%/yr range used here, in exactly the low-vol grinds where the trade already loses gross.

## 4. Heartbeat trades and tax-loss effects — not tradeable

ETF heartbeat trades (a sponsor cycling AP creation/redemption near quarter-end to flush
appreciated securities from the basket — the real reason index ETFs rarely distribute capital
gains) and December CEF/ETF tax-loss flow are real but operate entirely inside the AP/sponsor
relationship or other investors' account-level tax decisions. No price gap a retail account can
observe and capture; noted for completeness only.

## 5. Judged against the target

$5,000 → $50,000 in 5 months requires **58.49%/month** compounded
((50,000/5,000)^(1/5) − 1, same calculation as `docs/briefs/commodity-rates.md` §8). 20%/year is
**1.53%/month**.

| Method | Computed CAGR | Max DD | Sharpe | Capacity @ $5k | vs 20%/yr | vs 58%/mo |
|---|---|---|---|---|---|---|
| CEF discount z-score (best: PDI/HYG) | +2.46% | -30.36% | 0.30 | Not constrained | Fails | Fails |
| CEF discount z-score (other 4 pairs) | -2.40% to -0.41% | -12.9% to -33.7% | -0.26 to 0.02 | Not constrained | Fails | Fails |
| CEF/ETF buy-and-hold (context) | 9.0% to 17.2% | -37% to -47% | 0.57-0.81 | Not constrained | Fails (close, BST) | Fails |
| ETF AP creation/redemption arb | n/a — retail-inaccessible | n/a | n/a | **Zero** (AP-only) | Fails | Fails |
| Short UPRO+SPXU pair, gross | +0.21% | -10.16% | 0.16 | Not constrained | Fails | Fails |
| Short UPRO+SPXU pair, net of borrow | -1.78% to -9.33% | -26% to -80% | -1.3 to -7.3 | **Constrained** (margin/borrow) | Fails | Fails |
| Heartbeat / tax-loss effects | n/a — not a retail trade | n/a | n/a | Zero | Fails | Fails |

**Bottom line for Sholo:** the one number here that clears any bar (PDI/HYG's +2.46% CAGR,
Sharpe 0.30) is a CEF-vs-ETF proxy relative-return rule, not a true discount rule — NAV isn't on
`yfinance`, so this used a same-asset-class ETF as a proxy, flagged so it isn't mistaken for a
discount-to-NAV signal — and even at face value it's a tenth of the 20%/year bar. Real ETF
arbitrage keeps SPY/HYG/LQD within basis points of NAV because APs capture it before a retail
order ever sees the gap; March 2020's wider bond-ETF discounts were a stale-NAV/price-discovery
event, not a standing opportunity, and that magnitude is unverified this session. The
leveraged-pair decay trade is gross-positive over 16+ years but flips negative the moment
realistic borrow is applied, and has lost money gross for four straight years into a low-vol
regime — exactly where it bleeds hardest. Nothing here is a candidate for the target.

**Sourcing gaps:** (1) Lee-Shleifer-Thaler's abstract — JSTOR/Wiley blocked, two NBER
working-paper guesses both wrong; citation is a literature fact, not read live. (2) March 2020
bond-ETF-discount magnitude — four sources failed (NY Fed, oversized SEC PDF, ICI 404, BIS 403),
WebSearch exhausted; re-fetch before quoting a number. (3) cefconnect.com's rendered pages timed
out via WebFetch; §1's data came from the JSON API behind those pages via direct `curl` — live,
primary-source, not cached.

---
*Computations: `/Users/sahilmajmudar/index-daytrading/venv/bin/python3`, `yfinance` 1.5.1 +
`pandas` 2.3.3, daily adjusted closes, run 2026-09-23. Leveraged pair: -50%/-50% notional in
UPRO/SPXU, rebalanced daily by construction; borrow-cost rows apply a flat annualized drag to the
daily gross return before compounding. CEF premium/discount series: `curl` direct to
`https://www.cefconnect.com/api/v3/DiscountCharter/fund/<TICKER>/1Y`, fetched 2026-09-23.
Scripts are scratch (not checked into this repo) — reproducible from the methodology described
in each section.*
