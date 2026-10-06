# Memecoins, measured like the options: every factor, every cost, 4,344 launches

**Written 2026-10-06.** Sholo trades memecoins on GMGN and asked for the same testing the
options got, with automation as the goal. Data: `04_live_system/memecoin_recorder.py`,
every token on DexScreener's launch feed since 2026-09-23 at the price a retail wallet
first sees it, re-priced every ~20 minutes for a day. 4,344 launches (Solana 92%, BSC 5%,
Ethereum 2%, Base 1%; 43% still on the pump.fun curve at first sight, median liquidity
$3,000, median age at first sight 29 minutes). Study: `05_studies/memecoin_factors.py`;
panel in `DATA_ROOT/memecoin_factor_panel.parquet`. Two recording weeks are the time
splits (A / B). 27 factor cells were scored, so the largest |t| expected from noise is 2.6.
Costs: 1% venue fee + 0.5% router each way (pump.fun / PumpSwap / GMGN), 2% slippage each
way, and price impact of order ÷ (liquidity ÷ 2) each way, which at a $100 order on the
median $3k pool is 7% a side on its own.

## The base rate, which is the whole answer

| horizon | n | median | share up | doubled | 5× | down >50% |
|---|---:|---:|---:|---:|---:|---:|
| 30 min | 1,534 | **−23%** | 28% | 6.3% | 1.6% | 38% |
| 1 hour | 2,055 | −32% | 24% | 6.8% | 1.4% | 42% |
| 6 hours | 3,581 | −46% | 17% | 3.9% | 1.5% | 48% |
| 24 hours | 4,138 | **−64%** | 12% | 3.6% | 1.6% | 58% |

The best mark a token reached in its first 24 hours, the price a PERFECT exit could have
sold at, has a median of **−2%**: half of all launches never trade above the price a retail
wallet first sees them at, ever. The 24-hour return distribution: 5th percentile −99%, 25th
−88%, median −64%, 75th −12%, 90th +2%, 95th +45%, 99th +637%. One token in a hundred
pays 7×; that is the lottery ticket every screenshot is of.

**Buy every launch at first sight and sell at one hour: −3% gross on the capped mean and
−49% net at $100, −66% net at $500.** Hit rate 0.11. The sale is the problem: half the
pools cannot absorb $100 without moving 7% against you each way, and every exit pays it.

## The factors

Sign is the direction a trader would expect (more liquidity, more volume, a green 5-minute
candle, a younger token = better). IC is the rank correlation with the 1-hour forward return.

| factor at first sight | expected | IC (t) at 1h | best-fifth hit | best-fifth median | reading |
|---|---|---:|---:|---:|---|
| 5-min change (already green) | + | **−0.19 (−8.5)** | 0.18 | −72% | a green candle at first sight is the top; fade, not follow |
| 1-hour change | + | **−0.22 (−9.8)** | 0.24 | −73% | same, stronger |
| liquidity | + | −0.07 (−3.0) | 0.29 | −38% | no help on direction; everything for cost |
| 24h volume | + | −0.08 (−3.6) | 0.29 | −31% | the busiest tokens have already run |
| turnover (vol ÷ liq) | + | 0.00 | 0.24 | −16% | nothing |
| on the pump.fun curve | − | — | 0.00 net | −38% | **every on-curve buy at $100 is a net −89%**: the curve's own impact |
| **age at first sight** | − | **−0.42 (−19)** | 0.13 | −75% | the youngest fifth is the worst; survivorship, not timing: a token seen old is one that did not die |

After the first re-price (10–60 minutes in), with survivors only: early momentum (up >30%)
→ median −33% over the next hour (hit 0.17); the dip (down >30%) → median −5%, +3.5% mean,
−40% net (hit 0.09); liquidity growing with price → the best cell in the study at hit 0.32
and still −20% net on 50 names. Every early-path factor has the wrong sign: what went up
comes down, what the market crowded into is the exit.

## Where anything survived the cost

| rule | n | net at $100, 1h | hit | week A / B |
|---|---:|---:|---:|---|
| age > 60 min AND liquidity ≥ $20k (all of them graduated) | 144 | **+3.8%** | 0.34 | +5.4 / +1.1 |
| same, sold at 6h | 272 | −2.8% | 0.23 | +7.0 / −15.3 |
| same, sold at 24h | 297 | −13.4% | 0.18 | −14.2 / −12.3 |
| Ethereum launches (Uniswap) | 47–67 | +45% | 0.43–0.47 | one 50× token; gas at $100 size is 10–30% and is NOT in the cost model |
| BSC launches (PancakeSwap) | 71–87 | +15–19% | 0.36–0.39 | small; gas ~$0.10 so the number may be real |
| Base launches | 25 | +50% | 0.36 | too few |
| Raydium (graduated Solana) | 205 | −7.7% | 0.25 | the best Solana venue, still negative |

The one Solana rule that nets positive at an hour, liquid tokens an hour old, is +3.8% on
144 trades with a 0.34 hit rate, positive in both weeks, and negative at every longer hold.
That is a scalp with a one-in-three win rate on a set of tokens that then lose 13% by the
next day. The BSC and Ethereum rows are the only cells in the study with hit rates near
40% and positive means in both weeks; they are 50–90 tokens each, the Ethereum row is one
token, and gas is unmodelled. They are the lead the new recorder exists to measure.

## Exit rules do not rescue it

With the honest ordering (if both the take-profit and the stop were hit in the day, the
stop came first, since 20-minute marks cannot say which): +100% / −50% hits the target on
13.5% of launches and the stop on 60%, net −63%; +30% / −20%: target 26%, stop 74%, net
−54%. A tight target does not help because the loss side is a rug, not a drift.

## What this means for GMGN

- The screen's green candles, volume spikes and "trending" sorts are the top of the move
  on average: every momentum factor has a negative IC at every horizon in both weeks.
- The cost of being there is larger than any signal: at $100 on a $3k pool the round trip
  is ~20% before slippage; at $500 it is ~45%. Liquidity above $20k is the first filter
  and it cuts the universe to 13%.
- Nothing seen at first sight predicts the one-in-a-hundred 7×. The literature's finding
  (the memecoins brief, `docs/briefs/memecoins.md`) is that the winners are decided by who
  is in the first block, which is the deployer's own wallets at sub-100 ms latency; a
  retail wallet sees the token minutes later and buys their exit. This study measures the
  retail side of that trade and gets the number the literature predicts.

## What was built to go further

`04_live_system/pumpfun_recorder.py` records every pump.fun mint SECONDS after creation
(~40 a minute) with the curve state, creator wallet, socials, reply count, the creator's
history as seen so far (prior mints, how they ended), and re-prices at +1 … +30 minutes
then every 5 minutes to 6 hours and hourly to a day, joining DexScreener's buys/sells and
volume per window once a pair exists. That is every factor the GMGN screen shows. A week
of it is ~300,000 mints; `memecoin_factors.py --pumpfun` will score it the same way. If a
first-minute factor (creator history, socials, curve fill rate, buy/sell ratio) separates
the 0.2% that graduate from the rest at retail latency, it will show there; the paper
that tried this at scale (arXiv 2607.02823 v4) got AUROC 0.46 out of sample.

## On automation

Nothing in this repo places an order, and that stands. A GMGN/Jupiter execution path is
a few hundred lines and the easy part; what is missing is a rule with a positive expected
value at the costs above, and this study did not find one on Solana. If the pump.fun
recorder's first week shows one, it goes into a paper book with a ledger first, like every
other book here, and the ledger decides.
