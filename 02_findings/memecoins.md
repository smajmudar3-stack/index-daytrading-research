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

## What the research swarm added (2026-10-06, `docs/briefs/memecoin-*.md`)

Five briefs on the strategies Sholo named, each with sources: **copy-trading** (no
published measurement of copier returns exists; the one reverse-engineered profitable bot
exits ~20 s after entry, before a copier's order lands), **KOL and Telegram calls** (the one
fixed-hold study: median negative at every horizon from 30 s; LIBRA's followers −$250M
against one cluster's +$87M), **sniping** (slot-0 needs sub-35 ms co-location; the largest
creator-history model is AUROC 0.46 out of sample; no rug detector publishes precision at
the curve stage), **the data stack** (tick and wallet history is paid; GMGN's read API is
free and is now recorded), and **who profits** (1 in 30,000 wallets ever clears $100k; every
profitable cohort is the deployer, a bundler, a KOL selling to followers, an MEV searcher or
the platform). The verdict rows are in `online_methods.md`. Batch two added **curve and graduation plays**
(graduation probability sits below the breakeven curve at every curve position; 60% of
migrations lose 80% within 20 minutes — the 84%-below-0.3× figure quoted above in the
options-era brief does not match the paper and is withdrawn), **manufactured momentum and
MEV** (wash share rises toward the top of every trending list, 17% → 21% → 83% of the
"winners"; the slippage setting is the sandwich attack surface, 147k attacks in one day),
and **exits and sizing** (the one profitable bot exits on a dev-sell or a 20-second clock;
at the measured distribution the Kelly fraction is negative, so the correct position size
is zero until the distribution changes). Batch three: **cross-chain** (gas is the only clean
chain difference and it is negligible on BSC; four.meme is the venue to measure next, and the
GMGN recorder covers BSC and Base since 2026-10-07) and **open-source bots** (twelve repos,
no audited P&L anywhere; one posts users' private keys to a third party; the only rule tied
to any real profit is the creator-history filter, which the GMGN trenches fields
`creator_created_count` / `creator_created_open_ratio` make testable on our own tape).

**What is now being measured that was not before.** `gmgn_recorder.py` records every
smart-money and KOL trade GMGN shows, every trenches token with GMGN's own sixty risk fields
(bundler rate, sniper hold, insider hold, rug ratio, creator history, smart-degen count,
Telegram-call count, wash flag …), its signals, and the 30-second and 1-minute candles that
settle them. `05_studies/memecoin_gmgn_score.py` replays every smart-money buy at a copier's
30 s and 60 s latency and scores every trenches field as a predictor — the copy-trade
backtest that no one has published, on GMGN's own tape. First results after a day.

## The GMGN tape: copy-trading smart money, replayed (first 17 hours, 2026-10-07)

`gmgn_recorder.py` + `memecoin_gmgn_score.py`. 28,478 smart-money and KOL trades from
1,363 wallets on Solana, BSC and Base; 2,405 BUYS settled on GMGN's own 30-second candles.
The copier's fill is the first candle close 30 s or 60 s after the leader's timestamp;
exits at +5, +15 and +60 minutes; net of 1% venue + 0.5% router + 2% slippage each way.

| cell | n | +5 min net | hit | +15 min net | +60 min net |
|---|---:|---:|---:|---:|---:|
| **all smart-money + KOL buys, 60 s lag** | 1,484 | **−16.6%** | 0.14 | −29.3% | −29.9% |
| smart money only | 1,232 | −17.2% | 0.13 | −30.7% | −32.3% |
| KOL only | 252 | −13.5% | 0.15 | −21.7% | −17.3% |
| leader opening a new position | 726 | −11.5% | 0.13 | −20.5% | −21.3% |
| leader adding / flagged as reduce | 758 | −21.4% | 0.15 | −37.6% | −40.2% |
| Solana | 1,325 | −16.9% | 0.14 | −30.4% | −30.8% |
| BSC | 98 | −15.3% | 0.07 | −22.6% | −15.6% |
| Base | 61 | −11.3% | 0.25 | −17.5% | −34.0% |
| pump.fun tokens | 948 | −21.2% | 0.12 | −36.4% | −46.0% |
| Raydium LaunchLab (Bonk) tokens | 180 | −0.2% | 0.28 | −14.2% | +10.1% (n 77, hit 0.45) |
| leader tagged `fresh_wallet` | 78 | −39.1% | 0.14 | −48.6% | −50.2% |
| leader tagged `bullx` | 76 | +0.6% | 0.30 | −9.4% | +4.1% (n 22) |

**The copier does not even pay more than the leader: the median fill 60 s later is 2.3%
BELOW the leader's price, and 3.9% below on Solana.** The smart-money buy is the local top:
the token is already falling by the time anyone copying it can act, and keeps falling for
an hour. The first 325 settled trades (the first hour) had shown smart money +6–8% net at
five minutes; by 2,405 it is −17%, which is what a one-hour sample of a fat-tailed loser
looks like. The one cell above water, Raydium-LaunchLab tokens held an hour (+10% on 77
trades, hit 0.45), is a single cell out of 150 scored (noise bar t ≈ 3.2) with nothing at
5 or 15 minutes, and goes into the next re-score, not into a book.

**The paper book.** `memecoin_book.py` was fixed on this day's first numbers before the
17-hour result came in: copy every GMGN smart-money buy on Solana, fill at +60 s, sell at
+5 min, $100, 7% round trip. Its first 38 settled trades: hit 0.05, mean −57%, median
−33%, P&L −$2,154 on $3,800 risked. It keeps running every five minutes because a rule
fixed in advance and left alone is the only kind of evidence that cannot be argued with;
it is on the Markets page as "Memecoin paper book".

## The birth tape: every pump.fun mint from its first minute (first day, 2026-10-07)

`pumpfun_recorder.py` + `memecoin_pumpfun_score.py`. 9,361 mints seen a median 18 seconds
after creation; 5,511 with a curve price at +1 minute (the first moment a wallet outside
the creation block can act); the dev's own first buy known for 31% (PumpPortal creates).
Prices are the curve's own (virtual SOL ÷ virtual tokens, read from the chain), so there is
no venue to disagree with; cost is the trader's exact impact on the curve plus 1.5% a side.

- **Half of all mints never trade again after minute one.** At +10 minutes 50.9% sit at
  exactly their +1-minute price. Of the half that move at all, 13% are up. The best curve
  price a mint ever reaches after +1 minute has a median of **+0%** and a 75th percentile
  of **+0%**; the 95th is +20%. 1.69% graduated in the sample (1,331 `complete` flags
  across 9,361 mints), against the literature's 0.2–0.6%; the recorder sees the busiest
  hours of the day over-represented.
- **Money arriving early is the worst sign.** Real SOL on the curve at +1 minute has IC
  −0.63 to −0.73 against every later return (t −31 to −39): the mints that attract 5+ SOL
  in the first minute are the bundled ones, and they lose 32% by +10 minutes, 37% by an
  hour. A high starting market cap reads the same way (IC −0.3).
- **Creator history and socials predict GRADUATION, not return.** A creator's first launch
  graduates 3.05% of the time against 0.59% for a repeat creator and 0.44% for a serial
  one; three socials 3.8% against 1.1% for none; a dev first buy in the top fifth 4.9%
  against 0.3% in the bottom. But the graduates' own median return from the +1-minute
  price is −2% at an hour and +12% at six: graduation is survival, not profit, from where
  a retail wallet gets in.
- **Every rule from the +1-minute price is net negative at $100**: every mint −19%, first
  launch only −15%, dev buy ≤ 1 SOL −16%, the orcACR filter (first launch, dev buy ≤ 4 SOL,
  a social) −8% to −13%, all three socials −7%. Hit rates 0.02–0.05.
- **The one cell that looked above water was trap 6.** The first draft scored "a mint whose
  curve price rose ≥ 50% between +1 and +2 minutes, sold at +10" from the +1-minute price,
  which includes the wave itself, and read +13% net on 51 mints. Measured from the +2-minute
  price, where the signal is first known, the same rule is **−45% net, hit 0.06** (the paper
  book's Rule B, 49 signals, both halves negative). The study now carries returns from +2
  for any rule conditioned on the second minute. Nothing in the first minute of a pump.fun
  launch, measured at the moment it is visible, nets positive at $100.

## On automation

Nothing in this repo places an order, and that stands. A GMGN/Jupiter execution path is
a few hundred lines and the easy part; what is missing is a rule with a positive expected
value at the costs above, and this study did not find one on Solana. If the pump.fun
recorder's first week shows one, it goes into a paper book with a ledger first, like every
other book here, and the ledger decides.
