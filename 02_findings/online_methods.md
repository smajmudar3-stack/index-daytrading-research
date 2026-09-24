# Every "online money-making" method, measured or placed

**Written 2026-09-22**, after the request to scour every market and every automated method
for a path from $5,000 to $50,000. This is the inventory: what was measured here, what it
returned on real prices after real costs, and what could not be measured and why. The
number to keep in mind is the target: 10× in three years is 115% a year; in five years,
58% a year. Nothing below is within a factor of three of that.

## Measured on real prices, this repo

| method | data | result | verdict |
|---|---|---|---|
| **Cross-exchange crypto arbitrage** (the viral "price errors across 50 markets") | 4 venues, BTC, 10-min probe + continuous recorder (`crypto_venue_recorder.py`) | 12,653 raw gaps over 17 h (continuous recorder), largest 49 bp in a spike; **0 beat taker fees**; best net −14 bp | gaps exist, are a twentieth of a percent, and cost a third of a percent to cross. Dead for retail. |
| **Polymarket 5-minute crypto up/down vs spot** | 191 resolved windows (BTC/ETH/SOL), order book vs spot every 3 s, 2026-09-22/23 (`polymarket_recorder.py`, `polymarket_score.py`) | "buy the side ahead" with ≤60 s left: 70% win, avg cost 0.75, **−21% of premium**; ≤120 s: 86% win, −7.5%; ≤240 s: +4.5% (t 0.6) — all BEFORE the 1.56% taker fee | priced at 3-second polling; the documented edge is sub-second oracle latency, now fee-taxed. Recorder keeps running for a larger sample. |
| **Memecoin launch sniping** | 137 DexScreener launches at first sight, re-priced for a day (`memecoin_recorder.py`, `memecoin_score.py`) | buy every launch equal-weight: **−5.8% at 5 min, −6.2% at 30 min, −18.7% at 1 h, −34.4% at 6 h**; 42% down >50% by 6 h, 0% doubled; median pool $17k | dead at retail latency, as the literature says (69% die day one, <2% graduate) |
| **Index put-writing, monthly, ATM** (CBOE PUT style) | SPY chain 2019-05 → 2026-06, sold at the bid, held to expiry | CAGR 4.2% vs SPY 10.0%; max DD −16% vs −25%; Sharpe 0.49 vs 0.66 | lower drawdown, less than half the return |
| **Index put-writing, 15-delta** | same | CAGR **4.7%**, max DD **−3.3%**, worst month −2.8%, 91% months positive, Sharpe 2.07 | a very smooth 5% a year. A yield, not a growth path. At 2× it is 3.2%. |
| **Covered calls, 30-delta** | same | CAGR 7.6% vs 10.0%; DD −20% vs −25% | gives up 2.8 points a year for a slightly softer ride |
| **0DTE index credit structures** (condors, flies, strangles…) | 147,350 real SPXW trades | every one negative, \|t\| > 9 | dead (`WHAT_FAILED.md`) |
| **Weekly single-name direction with options** | 214,803 name-weeks, 67,380 real-fill verticals | direction ~52%; spread costs 8–15% of risk per trade | dead (`weekly_predictors.md`, `weekly_structure.md`) |
| **Intraday / 0DTE scalping on the index** | ~340,000 tests, 1,919 sessions; vendor flow 103 sessions | null; flow worth 1–2 bp vs 5–10 bp round trip | dead (`INTRADAY_DIRECTION.md`, `uw_flow.md`) |
| **Earnings straddles** through the print | 12,035 | −35%/trade | dead |
| **Pre-earnings straddle, the paper's way** (buy T−3, sell before the print; Gao-Xing-Zhang) | 26,063 events, 1,908 names, 2020–2026, real chains (`gxz_straddle_test.py`) | at MID: **+3.17%** (t 22), reproducing the paper's +3.34%; at real ask/bid: **−32.9%**; liquid names only (spread ≤5%, n=706): −4.6% (t −9) against +2.4% at mid | the effect is real and the spread is larger than it in every liquidity tier |
| **Far-OTM lottery buying** | 10.5M purchases | −48% to −90% | dead |
| **"Unusual options activity" following** | vendor's own 2-year history, 286 names | IC ≈ 0, put/call contrarian | dead (`uw_flow.md`) |
| **Momentum / 52-week high / reversal, weekly** | 214,803 name-weeks | inside the noise bar | dead at a week |
| **Earnings-surprise drift, quarterly, stock** | 33,755 announcements | **+2.84% Q5−Q1 over 63 sessions, t 4.3, all splits**; long-only +4.7%/yr over SPY | **real, slow** — live as `swing_stock.py` |
| **Buyback / FCF tilt** | 104 months | t 3.4–3.5, strong 2022–23, flat 2024–26 | real, regime-dependent |
| **VIX-backwardation overlay on a 2× index position** | 2006–2026 | 15.3%/yr vs 11.5% buy-and-hold, DD 59% | **real** — the best growth path measured (`goal_feasibility.md`) |
| **Overnight-only holding** (Lou, Polk & Skouras) | 2,259 names, 1,910 sessions 2019–2026 | overnight (close→open) +12.0%/yr gross vs daytime +5.0%; **net of 10 bp a day: −13.0%/yr** | the gap is real and two trades a day eat it whole |
| **Statistical arbitrage** (Avellaneda-Lee residual reversion) | 2,275 names, 3.8M name-days | gross +1–2%/yr, Sharpe 0.3; net negative at every hold | dead for a retail-cost book (`statarb.md`) |
| **Information diffusion / peer lead-lag** (Cohen-Frazzini, Hong-Stein, "connected stocks") | 2,126 names, 92 month-ends, statistical peers re-estimated monthly (`xsec_diffusion_test.py`) | peers' last-month return: IC −0.006; peer-minus-own gap: D10−D1 **+0.11%/month, t 0.25**; sector momentum +0.023 (t 1.5) | dead in liquid names 2019–2026 |
| **Kalshi vs Polymarket same-event gaps** | live pair recorder (`kalshi_recorder.py`, `kalshi_score.py`): 15-min BTC windows on both venues, daily strikes | first hours: the 15-min window quotes identically on both venues (0.041/0.042 vs 0.04/0.05); the daily strikes resolve at 5pm ET on Kalshi and noon on Polymarket, so their gap is time, not mispricing | recording; scored on same-resolution pairs only |
| **Sector rotation** | 1,512 configurations | none beat buy-and-hold | dead |
| **Spinoffs** | event study | see `RESEARCH_SPINOFFS.md` | small |

## Not measurable from here, and why

| method | why not, and what it is |
|---|---|
| **Perpetual-futures funding-rate carry** (long spot, short perp, collect funding) | the one crypto "yield" with a real mechanism, 5–15% a year in normal regimes, more in manias; the venues that pay it (Binance, Bybit, Hyperliquid) are not open to US persons and Robinhood has no perps. Not 10×. |
| **Prediction-market cross-venue arbitrage** (Polymarket vs Kalshi on the same event) | both APIs are public and reachable (checked 2026-09-22); the same-event matching is manual work and Kalshi's fee is ~7% of profit; gaps of a few cents exist and close in minutes. A recorder is the next step if the Polymarket result is not null. |
| **Sports-betting arbitrage / matched betting** | needs multiple licensed books and account longevity; books limit winners within weeks. Not automatable at scale, and not an investment. |
| **Grid bots, DCA bots, "AI signal" bots** | a grid bot is a short-volatility position with a stop that does not exist; it earns in ranges and loses the range's worth in one trend. No edge, only a shape. |
| **Copy trading / social leaders** | survivorship: the leaders you can see are the ones that have not blown up yet. The measured decay of published signals (McLean & Pontiff) is the relevant fact. |
| **MEV / on-chain arbitrage** | real, and taken by bots that pay validators for ordering; a retail script is last in the queue by construction. |
| **Leveraged-ETF decay shorting** (short TQQQ and SQQQ) | a real drift, offset by borrow fees of 5–30% a year on the inverse product and unbounded loss on a trend day. Not available in a small Robinhood account. |
| **Index rebalancing / ETF flow front-running** | documented and small (tens of bp per event); the data (constituent changes with dates) is not on this machine. |
| **Insider "sources"** | non-public information is a crime and was not sought. Legal Form 4 buys are a voter already and measured near zero at a week. |

## The answer

There is no automated method, in any market reachable from a US retail account, that
compounds $5,000 to $50,000 in one to five years on the evidence collected here. Every
fast method is a coin flip paying a toll, a gap smaller than the fee to cross it, or a
short-volatility position that pays until it does not. The slow methods are real and add
up to roughly **15 to 20 percent a year at 2× leverage with a 50 to 60 percent drawdown**:
the index overlay, the earnings-surprise stock book on top of it, and a put-write sleeve
if smoothness is worth 5 points of return. That is a twelve-to-sixteen-year path.

The recorders keep running. If Polymarket's odds turn out to lag spot by more than the
spread, that row changes and this file will say so.

## What the research swarm added (2026-09-22/23, briefs in `docs/briefs/`)

Seven of twenty-six agent briefs finished before the session cap; each is filed verbatim.
The verdict rows, with the brief that carries the sources:

| branch | brief | verdict |
|---|---|---|
| Prediction markets | `prediction-markets.md` | no verified track record; the peer-reviewed converter arbitrage pays **$0.08 a trade** by 2026 with the top ten addresses taking 75%; the $8.2M "edge" was settlement manipulation, now closed by TWAP; Kalshi's own 15-min "buy the leader" test: 0.67c edge vs 1.55c fee; polymarket.com is close-only for US IPs |
| Memecoins | `memecoins.md` | graduation 0.63% → 0.20%; deployer-funded snipers exit 85% within 5 min into you; retail-latency EV −8 to −15% per launch; 0.76% of wallets ever made $1,000 |
| Crypto derivatives | `crypto-derivatives.md` | funding carry ~4%/yr in 2025–26 on US-legal venues before the forgone cash rate; CME basis below T-bills; MEV taken by 19 firms; the one audited 30%+ bot decayed 4–5× in a year |
| Options income | `options-income.md` | CBOE PUT 7.6%/yr and BXM 6.6% for 2018–25 vs SPY 14.3%; retail 0DTE lost $70M over two years, $50M of it costs; pre-earnings straddle +1% at mid, **−9% at bid/ask**; a 0.9-delta SPY LEAPS costs $21,500, so a $5k account cannot lever with options |
| Sports betting | `sports-betting.md` | value betting 2.5–3% a bet until the account is limited in 3–12 weeks; Polymarket NBA arbitrage capacity ~$770 a month; Kalshi makers on favourites +2.6% after fees, unscaled; 2026's 90% loss-deduction rule punishes high-turnover play |
| Yields and alt-data | `yields-altdata.md` | best documented retail yield is a covered-call ETF at 8–16% that trails its index; every advertised yield above 15% has a recorded principal loss; index option alphas indistinguishable from zero since ~2010 (Chicago Fed 2025); alt-data signals halve after publication |
| Calendar and macro-event effects | `calendar-macro.md` | computed on SPY 2010–2026: turn-of-month t 0.65, pre-FOMC drift null in every sub-period (133 meetings), overnight carry +7.3%/yr gross → **−17.9%/yr net** at 10 bp/day, month-end rebalance null; one live oddity, opex Fridays −49%/yr annualised vs +18% other Fridays (t −3.3) worth ~2.3%/yr gross if traded 12×/yr — nothing near 20%/yr after costs |
| Equity anomalies | `equity-anomalies.md` | on the French decile data: momentum long-short t 2.07 (1990–2014) → **0.52 (2015–2025)**, long-only edge over the market ~1.6%/yr at t 0.6; short-term reversal never significant gross of costs; GKX machine-learning gains concentrate in microcaps and vanish after costs |
| Retail base rates | `retail-base-rates.md` | ~5% of active day traders ever profitable, <3% predictably; unprofitable traders keep trading at the same rate as profitable ones; 82% of UK CFD clients lose (avg £2,200); Fermi estimate for $5k→$50k in 5 months by trading: **well under 1%**, halving: 40–70% |
| Bot claims audit | `bot-claims-audit.md` | TRM: $517K drained by nine "Claude bot" tutorials; the viral dashboards are Artifacts renders; the one open-source bot that published real trades made **+$11.51**; 97% of persistent Brazilian day traders lose; a real 10× in 5 months has no verified precedent |

The remaining nineteen branches (equity anomalies, leverage paths, retail base rates, futures/FX,
crypto factors, informed cloning, calendar effects, LLM news, special situations, vol ETPs,
ETF/CEF gaps, microcaps, commodities, gambling, income routes, promos, non-market arbitrage,
international macro, crypto intraday) were cut off by the session cap; `docs/CONTINUATION.md`
lists them for re-run.
