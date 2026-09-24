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
| **Signal accuracy sweep: 68 factors by hit rate and payoff** (momentum, patterns, earnings-day behaviour, options-implied, fundamentals, regimes, LightGBM) | 643,687 name-weeks, 2,200 names, 2018–2026, 1/2/4/13-week horizons (`signal_accuracy.py`) | top-decile hit rate 0.45–0.51 for EVERY factor and model at every horizon; payoff 1.05 at a week → 1.36 at a quarter; earnings surprise the only factor beyond the noise bar everywhere; LightGBM on all 68 with market state: −3.7%/yr net at a week, +6.8%/yr at a quarter; the named earnings-day patterns are within ±0.3% and 50/50 | the edge is in win SIZE at a quarter, never in frequency; the stock book's cohort widened to 63 sessions on this (+4.24%/quarter, all splits) — `02_findings/signal_accuracy.md` |
| **Information diffusion / peer lead-lag** (Hou, Cohen-Frazzini, Thomas-Zhang, Hong-Torous-Valkanov) | 498,734 name-weeks, 1,471 S&P 1500 names, 155 GICS sub-industries, 2018–2026, six channels: industry big→small, same-industry earnings transfer, statistical peers, cross-asset→sector (77 pairs), industries→market (22), and a walk-forward combined model (`diffusion_model.py`) | peers' past week predicts the name NEGATIVELY (IC −0.011 to −0.016); every "gap" signal is own-return reversal (residual IC −0.006); peer earnings surprise +0.019 (t 2.0) but −0.02%/wk after costs; combined model +0.17%/wk gross at 87% turnover = **−9.1%/yr net** | dead in liquid names; `02_findings/diffusion.md` |
| **Kalshi vs Polymarket same-event gaps** | live pair recorder (`kalshi_recorder.py`, `kalshi_score.py`): 15-min BTC windows on both venues, daily strikes; resolutions on both venues joined in | 5 h, 21 windows, 3,310 ticks: quotes identical at mid (median gap 0.000); a two-leg YES-here/NO-there cost under $1.00 after both fees on **11% of ticks**, almost all inside the last two minutes (30–36% of those ticks), deepest $0.568 with 13 contracts of depth ($5.62 gross); settled at what it actually paid the sub-$1 ticks average **+1.4c per $1 pair** (+2.8c in the last two minutes). The two venues resolve against DIFFERENT references (CF Benchmarks 60 s average vs Chainlink spot at the open), so a locked dollar is not locked — 0 of 20 windows disagreed so far, and a flat-tape window will | a real few-cent gap on a few dozen contracts for a few seconds before expiry, on a venue a US person cannot open (polymarket.com); needs a week of resolutions to size the disagreement risk. Not a $5k→$50k path. |
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

Each agent brief is filed verbatim as it lands.
The verdict rows, with the brief that carries the sources:

| branch | brief | verdict |
|---|---|---|
| Prediction markets | `prediction-markets.md` | no verified track record; the peer-reviewed converter arbitrage pays **$0.08 a trade** by 2026 with the top ten addresses taking 75%; the $8.2M "edge" was settlement manipulation, now closed by TWAP; Kalshi's own 15-min "buy the leader" test: 0.67c edge vs 1.55c fee; polymarket.com is close-only for US IPs |
| Memecoins | `memecoins.md` | graduation 0.63% → 0.20%; deployer-funded snipers exit 85% within 5 min into you; retail-latency EV −8 to −15% per launch; 0.76% of wallets ever made $1,000 |
| Crypto derivatives | `crypto-derivatives.md` | funding carry ~4%/yr in 2025–26 on US-legal venues before the forgone cash rate; CME basis below T-bills; MEV taken by 19 firms; the one audited 30%+ bot decayed 4–5× in a year |
| Options income | `options-income.md` | CBOE PUT 7.6%/yr and BXM 6.6% for 2018–25 vs SPY 14.3%; retail 0DTE lost $70M over two years, $50M of it costs; pre-earnings straddle +1% at mid, **−9% at bid/ask**; a 0.9-delta SPY LEAPS costs $21,500, so a $5k account cannot lever with options |
| Sports betting | `sports-betting.md` | value betting 2.5–3% a bet until the account is limited in 3–12 weeks; Polymarket NBA arbitrage capacity ~$770 a month; Kalshi makers on favourites +2.6% after fees, unscaled; 2026's 90% loss-deduction rule punishes high-turnover play |
| Yields and alt-data | `yields-altdata.md` | best documented retail yield is a covered-call ETF at 8–16% that trails its index; every advertised yield above 15% has a recorded principal loss; index option alphas indistinguishable from zero since ~2010 (Chicago Fed 2025); alt-data signals halve after publication |
| Futures and FX | `futures-fx.md` | managed-futures ETFs since inception 7–10%/yr (DBMF +20.5% in 2022, corr 0.18 to SPY) — real crisis diversification, half the index's return; 12-month time-series momentum across six ETFs 2010–2026 with 10 bp/side: 2.5–3.6%/yr; 20-day Donchian: 2.1% long-only, −1.1% long/short (turnover eats it); a diversified 6-market micro-futures system needs ~$12–20k at 1% risk; 69–89% of retail leveraged accounts lose |
| Leverage and growth paths | `leverage-growth.md` | Monte Carlo (10,000 monthly block-bootstrap paths of SPY): **0 of 10,000 paths reach 10× in 5 months at 3× or 5× leverage**; best path 4.85×; P(50% drawdown in 5 months) 1.1% at 3×, 12.7% at 5×. UPRO/TQQQ buy-and-hold and HFEA clear 20%/yr on CAGR with −51% to −82% drawdowns. Rebuilt on real SSO/UPRO, the VIX-gated overlay UNDERPERFORMS plain leveraged-ETF buy-and-hold (daily-reset drag) — the synthetic 1×+1× version in `goal_feasibility.md` is not buyable as an ETF |
| Calendar and macro-event effects | `calendar-macro.md` | computed on SPY 2010–2026: turn-of-month t 0.65, pre-FOMC drift null in every sub-period (133 meetings), overnight carry +7.3%/yr gross → **−17.9%/yr net** at 10 bp/day, month-end rebalance null; one live oddity, opex Fridays −49%/yr annualised vs +18% other Fridays (t −3.3) worth ~2.3%/yr gross if traded 12×/yr — nothing near 20%/yr after costs |
| Equity anomalies | `equity-anomalies.md` | on the French decile data: momentum long-short t 2.07 (1990–2014) → **0.52 (2015–2025)**, long-only edge over the market ~1.6%/yr at t 0.6; short-term reversal never significant gross of costs; GKX machine-learning gains concentrate in microcaps and vanish after costs |
| Retail base rates | `retail-base-rates.md` | ~5% of active day traders ever profitable, <3% predictably; unprofitable traders keep trading at the same rate as profitable ones; 82% of UK CFD clients lose (avg £2,200); Fermi estimate for $5k→$50k in 5 months by trading: **well under 1%**, halving: 40–70% |
| Bot claims audit | `bot-claims-audit.md` | TRM: $517K drained by nine "Claude bot" tutorials; the viral dashboards are Artifacts renders; the one open-source bot that published real trades made **+$11.51**; 97% of persistent Brazilian day traders lose; a real 10× in 5 months has no verified precedent |
| Crypto factors and market-making | `crypto-factors-mm.md` | 25 coins 2021–2026 (yfinance, 0.5%/side; Kraken's real taker is 0.8%): cross-sectional 1-week and 1-month momentum and 1-week reversal all lose (long/short momentum Sharpe −1.48, reversal −2.52); "buy last week's winner" −68%/yr; only equal-weight buy-and-hold clears 20%/yr and all of it is 2021 (+804%); a real OP-USD data bug found and fixed first |
| Volatility ETPs | `vol-etp.md` | UVXY buy-and-hold −100% split-adjusted; SVXY +504% total but −87% in 2018–19; short vol when VIX/VIX3M<1: 16–42%/yr with ~−80% drawdowns and a one-day lag into Feb 2018 (−21% that month); VRP-signal version 6.7%/yr; the "capped daily loss = hedge" version manufactures 686,000× and is flagged as a methodology trap; best 5-month window in 15 years 200–390%, not 900% |
| Commodities and rates | `commodity-rates.md` | USO −5.6 and UNG −21 pts/yr vs their futures 2010–2026 (USO flips sign at the April 2020 roll change); DBC/PDBC/GLD/SLV/GDX 2.6–8%/yr; gold/silver and GDX/GLD pairs lose net; TLT/TMF trend rules sat out 2022 but compound at 1–3%/yr; HFEA 22.9%/yr full period, −63% in 2022 and −70% from peak since |
| Informed cloning | `informed-cloning.md` | NANC 22.7%/yr vs SPY 20.3% since 2023 (KRUZ 18.2%, GVIP 25% on that window but 16.2% over its own 2016–2026 life); correlation 0.82–0.96 to SPY, closet index plus a side bet; literature edge (+82–85 bp/month) belongs to the original real-time transactor and this repo already measured the lagged clone as null (insider net buys IC −0.004) |
| International and macro allocation | `international-macro.md` | 213 months computed: Faber GTAA 9.9%/yr (5.2% once a BTC-weight artifact is removed), dual momentum 8.0%, country momentum 8.2%, HYG/IEF risk switch 4.4%, vs 60/40 10.4% and SPY 15.5%; Faber's own live fund GMOM 6.0%/yr since 2014; none beat 60/40 on return or Sharpe |
| Promotions and bonuses | `promo-bonus.md` | verified: Public.com 1% uncapped transfer match, bank bonuses $450–$900 each, 4.38% FDIC-cap savings; realistic 5-month extraction **$3,300–$7,500** for 40–80 hours, taxed as ordinary income, with clawback windows, card-velocity limits and closure risk; a 65–150% gain, 7–15× short of the target |
| Online gambling | `gambling.md` | card counting is the only verified positive edge (0.5–1.5%, ~$50/hour) and is engineered out online (per-round reshuffle, continuous shufflers); regulated online poker in 6 states with active solver/bot bans; casino bonus hunting a one-time $1–4k; the 2026 90% loss-deduction cap taxes gross churn (Tax Foundation's break-even $1M-wagered example owes $37,000) |
| Income routes | `income-routes.md` | the only measured way $5k becomes $50k in 5 months is adding ~$9k/month; freelance AI/automation work (Upwork/Toptal/direct) is the one route with a medium chance of that by month 5 (median $3–7k/month still ramping), a narrow direct consulting offer second; WorldQuant BRAIN caps near $2.7k/month at its top tier; Numerai is the only route that deploys the $5k and returns tens of dollars with burn risk |
| LLM and news signals | `llm-news.md` | the only disclosed backtest (Lopez-Lira & Tang, GPT-4 on headlines) made 34 bp/day gross with Sharpe decaying 6.5 → 1.2 from 2021Q4 to 2024 and unprofitable above 20 bp round trip; FinBERT/FinGPT report classification scores, no returns; EDGAR posts filings 1–3 minutes after receipt, so retail is behind every machine feed; computed on 450 earnings events 2023–2026 the median 1-day move is 1.1% and 5-day 2.3%, so direction, not cost, is the binding problem |
| Special situations | `special-situations.md` | computed since 2010: merger-arb ETF MNA 2.6%/yr (Sharpe 0.39), spinoff ETF CSD 13.1%/yr with a −57% drawdown, both under SPY's 14.2%; SPAC trusts return cash (median $6.67 of $10 retained at merger, Klausner-Ohlrogge); odd-lot tenders are structurally small, index-add effects decayed, airdrop farming a declining one-time lottery |
| Microcaps and runners | `microcap.md` | pumped small caps spike then reverse within a week (Renault 2018), the buyer's loss goes to the promoter; IWC/IWM 11%/yr vs SPY 14% since 2010 (no size premium); fading a +20% day on 794 events 2024–2026: median next day **−1.1% gross, −2.1% net**, 33–35% win rate, 24% of trades lose more than 10% overnight (hand-curated basket, not survivorship-free) |
| Non-market arbitrage | `non-market-arb.md` | fee schedules verified: Amazon 5–45% referral, StockX ~12% all-in, eBay 13.6% + fixed, ticket resale 15–25% and bot-buying tickets is a federal crime (BOTS Act); manufactured spend is a closing, adversarial route; GPU rental and FBA are the only routes where capital scales the return, at single to low double digits a month at best with real labour |
| Crypto intraday | `crypto-intraday.md` | 142 rule and seasonality tests on hourly BTC/ETH 2024-09 to 2026-09: none clear the noise bar (√(2 ln 142) ≈ 3.2; best ETH mean-reversion t −2.4 and the sign says extremes extend); US open, Asia open, weekend and funding-hour effects flat; every rule negative net of Kraken's real $5k-account taker fee (0.60%, not 0.26%); the best two rules flip sign between sample halves; buy-and-hold beat every rule |
| ETF and CEF gaps | `etf-cef.md` | closed-end fund discounts pulled live (PDI/PTY just flipped from double-digit premiums to discounts; ADX/BST discounts persistent and non-reverting); a 60-day relative-return reversion rule on five funds 2010–2026 at 10 bp/side: four of five lose or flat, best PDI/HYG +2.5%/yr (Sharpe 0.30); ETF premium/discount held to 0.13% by authorised participants, nothing for retail; shorting both UPRO and SPXU +0.2%/yr gross, negative at any borrow rate, gross-negative every year 2023–2026 |

All twenty-six briefs are filed (2026-09-23 night). Not one branch reaches the $5k→$50k
target or, after costs, a repeatable 20% a year; the slow index and quarterly-stock effects
measured earlier on this page remain the only positive, repeatable returns found.

