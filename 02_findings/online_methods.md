# Every "online money-making" method, measured or placed

**Written 2026-09-22**, after the request to scour every market and every automated method
for a path from $5,000 to $50,000. This is the inventory: what was measured here, what it
returned on real prices after real costs, and what could not be measured and why. The
number to keep in mind is the target: 10× in three years is 115% a year; in five years,
58% a year. Nothing below is within a factor of three of that.

## Measured on real prices, this repo

| method | data | result | verdict |
|---|---|---|---|
| **Cross-exchange crypto arbitrage** (the viral "price errors across 50 markets") | 4 venues, BTC, 10-min probe + continuous recorder (`crypto_venue_recorder.py`) | 1,182 raw gaps in 2,496 checks (47%), largest 5.2 bp; **0 beat taker fees**; best net −32 bp | gaps exist, are a twentieth of a percent, and cost a third of a percent to cross. Dead for retail. |
| **Polymarket 5-minute crypto up/down vs spot** | order book + spot every 3 s (`polymarket_recorder.py`), scored by `polymarket_score.py` | recording since 2026-09-22 21:45 ET; ~150 windows a night per coin | **open** — first result the morning after; the 1-cent spread is 1% of notional per trade, which is the bar to clear |
| **Index put-writing, monthly, ATM** (CBOE PUT style) | SPY chain 2019-05 → 2026-06, sold at the bid, held to expiry | CAGR 4.2% vs SPY 10.0%; max DD −16% vs −25%; Sharpe 0.49 vs 0.66 | lower drawdown, less than half the return |
| **Index put-writing, 15-delta** | same | CAGR **4.7%**, max DD **−3.3%**, worst month −2.8%, 91% months positive, Sharpe 2.07 | a very smooth 5% a year. A yield, not a growth path. At 2× it is 3.2%. |
| **Covered calls, 30-delta** | same | CAGR 7.6% vs 10.0%; DD −20% vs −25% | gives up 2.8 points a year for a slightly softer ride |
| **0DTE index credit structures** (condors, flies, strangles…) | 147,350 real SPXW trades | every one negative, \|t\| > 9 | dead (`WHAT_FAILED.md`) |
| **Weekly single-name direction with options** | 214,803 name-weeks, 67,380 real-fill verticals | direction ~52%; spread costs 8–15% of risk per trade | dead (`weekly_predictors.md`, `weekly_structure.md`) |
| **Intraday / 0DTE scalping on the index** | ~340,000 tests, 1,919 sessions; vendor flow 103 sessions | null; flow worth 1–2 bp vs 5–10 bp round trip | dead (`INTRADAY_DIRECTION.md`, `uw_flow.md`) |
| **Earnings straddles** through the print | 12,035 | −35%/trade | dead |
| **Far-OTM lottery buying** | 10.5M purchases | −48% to −90% | dead |
| **"Unusual options activity" following** | vendor's own 2-year history, 286 names | IC ≈ 0, put/call contrarian | dead (`uw_flow.md`) |
| **Momentum / 52-week high / reversal, weekly** | 214,803 name-weeks | inside the noise bar | dead at a week |
| **Earnings-surprise drift, quarterly, stock** | 33,755 announcements | **+2.84% Q5−Q1 over 63 sessions, t 4.3, all splits**; long-only +4.7%/yr over SPY | **real, slow** — live as `swing_stock.py` |
| **Buyback / FCF tilt** | 104 months | t 3.4–3.5, strong 2022–23, flat 2024–26 | real, regime-dependent |
| **VIX-backwardation overlay on a 2× index position** | 2006–2026 | 15.3%/yr vs 11.5% buy-and-hold, DD 59% | **real** — the best growth path measured (`goal_feasibility.md`) |
| **Overnight-only holding** (Lou, Polk & Skouras) | 2,259 names, 1,910 sessions 2019–2026 | overnight (close→open) +12.0%/yr gross vs daytime +5.0%; **net of 10 bp a day: −13.0%/yr** | the gap is real and two trades a day eat it whole |
| **Statistical arbitrage** (Avellaneda-Lee residual reversion) | 2,275 names, 3.8M name-days | gross +1–2%/yr, Sharpe 0.3; net negative at every hold | dead for a retail-cost book (`statarb.md`) |
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
