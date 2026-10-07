<!-- research brief, filed 2026-10-06; agent output verbatim. Companion to 02_findings/memecoins.md
     (exit-rule section) and docs/briefs/memecoin-sniping.md. Verdicts belong in 02_findings/ if
     anything here is acted on. -->

# Memecoin exits, sizing and ruin: the half of "lock in 5-200%" that is about selling

`02_findings/memecoins.md` already tested two exit ladders on this repo's own 4,344-launch
panel and both lost money net of cost: **+100%/−50% hits the target 13.5% of the time and the
stop 60%, net −63%; +30%/−20% hits target 26%, stop 74%, net −54%.** This brief asks whether
the published/open-source exit tooling does any better, what the underlying path statistics
say about why fixed-ladder exits keep failing, and what position sizing a fat-tailed,
mostly-losing distribution actually tolerates on a $5,000 account.

## 1. What the published and open-source exits actually are

| rule | source | mechanics | reported outcome |
|---|---|---|---|
| 50%-at-+25%, 75%-of-rest-at-+25% ladder, moonbag | [TreeCityWes/Pump-Fun-Trading-Bot-Solana](https://github.com/TreeCityWes/Pump-Fun-Trading-Bot-Solana) | Sells 50% of position on a +25% market-cap move, then 75% of the remainder on the next +25% move; keeps a 25% "moon bag"; stop-loss sells everything on a −10% move; sells 75% and moonbags 25% if the bonding-curve progress nears its own completion threshold | No P&L log or win rate published — README has no results section |
| Configurable TP/SL, no ladder | [slycompiler/fssb-fast-solana-sniper-bot](https://github.com/CryptoTechZoo/fssb-fast-solana-sniper-bot) | `TAKE_PROFIT=200%` / `STOP_LOSS=90%` env vars, single-shot (not staged); `AUTO_SELL_DELAY` can force a time-based exit at 0ms (sell immediately on buy confirmation) | README states explicitly "no guarantee the token will be sold at a profit or even sold at all" — no backtest or live log |
| Sell-on-first-external-buy / 20s timeout | [jcoulaud/pumpfun-sniping-bot](https://github.com/jcoulaud/pumpfun-sniping-bot) | This is a *deployer*-side bot, not a buyer-side one: it mints its own token, then sells into the first outside wallet that buys, or after a fixed 20-second timeout if nobody does | Logs a `profit_log.json` schema but no populated results file was reachable; this is the "sell on first bite" pattern seen from the other side of the trade this whole repo studies |
| Dev-sell trigger + 20s time stop | [orcACR, reverse-engineered by mikem.codes](https://www.mikem.codes/if-you-aint-first-youre-last-2/) | "Immediately sell all coins if the creator sold any of theirs"; separately, a "copy-block" pattern enters and exits ~20 seconds later regardless of creator behavior | Aggregate ~100–200 SOL/day (~$10–20k/day) attributed to the bot's whole strategy, not isolated to the exit rule; **estimated from on-chain activity, not vendor-disclosed — unaudited** |
| Fixed-ladder TP/SL on this repo's own panel | `02_findings/memecoins.md` | +100%/−50% and +30%/−20%, tested against 20-minute-resolution marks with honest ordering (stop wins ties) | +100/−50: net **−63%**; +30/−20: net **−54%**, both on the full 4,344-launch panel |
| Manual sell only (no automated ladder found) | [Trojan](https://docs.trojanonsolana.com/telegram-bot-user-guide/trading-on-the-bot/selling-tokens.md), [BullX ToS](https://bullx.gitbook.io/bullx) | Trojan's own docs describe only a manual sell button with a preset percentage and slippage setting; BullX's gitbook page reachable this session was Terms of Use only | **Not verified**: both bots are widely advertised (Telegram UI, screenshots) as having take-profit/trailing-stop/limit-sell order types, but no official doc page describing the mechanics was reachable this session |

The honest reading: nobody with a public results section runs a ladder that beats the base
rate. The one bot with a credible, repeatedly-cited profit number (orcACR) isn't exiting on
price at all — it exits on the creator's own wallet activity or a flat 20-second clock, and
its edge (per the sniping brief already in this repo) is in entry filtering, not the sell
rule. The ladders that *are* published (TreeCityWes, FSSB) ship with no results, which given
this repo's measured −54% to −63% net on the same shape of rule, is not surprising — a
retail-latency trader could run either tool for months without ever knowing if it's a
winning rule, because nobody logs the denominator.

## 2. The path statistics that decide exit design

A ladder only works if price drifts predictably between entry and the target; memecoin paths
don't drift, they jump and then collapse, which is why fixed percentage triggers get skipped
past or never reached:

- **Time to graduation (not peak, but the closest measured timing stat) is a median of 4.4
  minutes** on 655,770 pump.fun tokens ([arXiv 2602.14860](https://arxiv.org/html/2602.14860v1),
  Marino et al.), right-skewed — most of whatever move happens, happens almost immediately.
- **92.22% of tokens with at least 30 swaps show at least one "4-sigma dump"** — a log-return
  below a 4-sigma lower control limit, the paper's own statistical definition of a crash — and
  these cluster at specific points in the bonding curve rather than being evenly spread
  through a token's life (same paper, Section VIII). The paper does not quantify dump *speed*
  in seconds, and does not report what fraction of pumps retrace to breakeven — **both marked
  not verified**, that data does not appear to exist publicly at the resolution needed.
- **Post-migration collapse is front-loaded and severe**: on 41,470 migrated (survivor) tokens,
  [MemeTrans](https://arxiv.org/html/2602.13480v1) (arXiv 2602.13480) finds 60.26% fall to
  0–20% of their migration price and a further 12.70% to 20–40%, inside a 20-minute window —
  over 73% below 40% of migration price within 20 minutes of the point most ladders would be
  waiting to trail a winner. MemeTrans does not report a specific breakeven-retrace percentage
  either; that framing from the task brief (a precise "winners that retrace to breakeven"
  statistic) could not be located in this paper and is **not verified**.
- **Deployer-wallet exits, which is what retail is actually trading against, are measured in
  seconds to low minutes**: Pine Analytics (cited in `docs/briefs/memecoins.md` §2) found 55%
  of sniper-wallet exits land within 1 minute and 85% within 5 minutes of a launch — this is
  the closest public number to "how fast a rug executes," and it says the floor is already
  gone by the time a human-latency ladder would even register the first take-profit tier.
- **The only public fixed-hold dataset**, [Money Leaves Clues](https://moneyleavesclues.substack.com/p/inside-the-economics-of-pumpfun-call)
  (770 call-channel picks, a favourably pre-selected sample), shows a realistic 15-second entry
  nets median +0.2% at 30 seconds, then **−6.2% at 1 minute, −10.5% at 5 minutes, −27.6% median
  for a subscriber entering 30 seconds after the call and exiting at 5 minutes**. The author
  tested fixed-time exits only for measurement, not as a recommended strategy, and does not
  report what share of tokens ever return to the entry price.

The shape across every source is consistent: whatever upside exists resolves in well under a
minute, before a retail-latency trader's sell order would even confirm, and the downside is a
near-vertical drop rather than a gradual fade a trailing stop could catch mid-way. That is a
structural argument against ladders and trailing stops specifically — they're built for
assets that drift, and this asset jumps.

## 3. Sizing math for a fat-tailed, mostly-losing book

Using the task's framing — 90% of trades lose 50–100% (midpoint ≈ 75%), 1% of trades pay a
10x (b = 10), and ignoring the remaining 9% for a clean two-outcome Kelly derivation — the
Kelly-optimal fraction for a bet returning `(1+b)` with probability `p` and `(1−l)` with
probability `q=1−p` is **f\* = p/l − q/b**:

f\* = 0.01/0.75 − 0.99/10 = 0.0133 − 0.0990 = **−0.086**

Negative Kelly means the bet has negative expected value at these odds (EV per dollar staked =
p·b − q·l = 0.10 − 0.7425 = **−0.6425**), and the mathematically correct answer is to not take
the bet, not to size it small. This lines up with this repo's own measured 24-hour distribution
(`02_findings/memecoins.md`): median −64%, only 1.6% double, 95th percentile +45%, 99th
percentile +637% — the same heavy-left/thin-right shape, and an unfiltered buy-every-launch
rule nets −49% to −66% once $100–$500 of real slippage and fees are applied.

**Ruin isn't a probability here so much as a clock.** For a position sized at fraction `f` of
a $5,000 account, the expected per-trade log-growth rate is `g(f) = p·ln(1+fb) + q·ln(1−fl)`.
With the same 1%/10x, 99%/−75% parameters, `g(f)` is negative for every `f > 0` and gets worse
as `f` grows — there is no position size, however small, at which repeated betting is expected
to grow the account, because the house edge (not metaphorical — pump.fun's own 1%+ fee layer is
part of `l`) is baked into every trade:

| position size (% of $5k) | $ per trade | expected trades to a 90% drawdown | what it corresponds to in this repo's cost model |
|---:|---:|---:|---|
| 1% | $50 | ≈ 354 | smallest size that still clears most pools' minimum liquidity for a quote |
| 2% | $100 | ≈ 175 | this repo's own $100 benchmark size — round-trip friction ~20% on a median $3k pool |
| 5% | $250 | ≈ 68 | |
| 10% | $500 | ≈ 33 | this repo's own $500 benchmark size — round-trip friction ~45% |
| 20% | $1,000 | ≈ 15 | |
| 50% | $2,500 | ≈ 7 | |

These are expected-value trade counts from the log-growth drift, not a full ruin-probability
simulation, and the 1%-per-trade chance of a 10x means any individual run can last much longer
or end much sooner — but the drift itself is negative at every size shown, so "diversifying"
across more small bets does not fix anything; the law of large numbers just converges faster
on the same negative mean. **Many small bets only help once the per-trade EV is positive** —
exactly the repo's finding that a filter (age > 60 min, liquidity ≥ $20k) gets EV to +3.8% at a
0.34 hit rate for a narrow, nets-positive-in-both-weeks slice of the universe, and even that
rule goes negative again by the 6-hour and 24-hour mark.

## 4. Fee drag on a high-turnover exit style

Every exit, successful or not, pays the round trip twice over the life of a scalped position:
1% pump.fun protocol fee + 0.5% router fee each way (buy and sell) is 3% fixed before any
price impact; add ~2% slippage each way and price impact of order size ÷ (liquidity/2), which
`02_findings/memecoins.md` measures at ~7% a side on a $100 order against the median $3,000
pool — **~20% round trip at $100, ~45% at $500**. `docs/briefs/memecoin-sniping.md` adds that a
2026 creator-fee layer now sits on top of the 1% protocol fee on many coins, not disclosed
anywhere but the coin's on-chain config, and no longer rebated to the buyer (the "cashback"
mechanism was deprecated September 2026). Solana priority fees and Jito tips add $0.50–$5 per
attempted transaction at contested launches (`memecoin-sniping.md` §1) — immaterial at $500
size, material at the $50–100 sizes the ruin table above says are the only sizes that survive
more than a couple hundred trades. A ladder or trailing stop that fires multiple partial sells
(the TreeCityWes 50%-then-75%-of-rest pattern) pays this full drag on each leg, which is why a
scheme that looks fine on a mid-price chart can still lose money even when it's directionally
right.

## 5. Behavioural evidence on retail exits

No on-chain disposition-effect study specific to pump.fun or memecoin traders was found this
session — **not verified**, and this looks like an actual gap in the literature rather than a
search failure: neither the MemeTrans paper, the Manipulation-as-a-Service paper (arXiv
2609.10246), nor the jondar Dune dashboard split holding time or sell speed by whether a
position was up or down. The closest proxy, from `docs/briefs/memecoin-who-profits.md`: on
CoinGecko's 2026 data, the share of pump.fun wallets with *realized* profit rose to 57–73% by
early 2026, but 65% of those winners realized only $1–$500 — consistent with retail cashing
out small winners quickly, which is one half of a disposition pattern, but there is no
matching public number for how long losers are held before being abandoned or going to zero,
so the full disposition claim stays unconfirmed.

## Bottom line

Every exit rule with a public results section that actually measures outcomes — this repo's
own ladder test — loses money net of cost, and every rule that claims a profit (orcACR) isn't
exiting on price at all, it's exiting on the deployer's own wallet behavior or a flat clock.
The path data explains why: upside resolves in under a minute and downside is near-vertical,
which is the wrong shape for a trailing stop or a staged take-profit to catch. The sizing math
says the same thing from a different angle — at the fat-tailed odds this market actually pays,
Kelly is negative, meaning no position size compounds this book, and "many small bets" is not
a fix for negative EV, it's a way to lose the same amount more smoothly. The one lever that
measurably worked in this repo's own data wasn't an exit rule at all — it was a pre-entry
filter (age, liquidity) that changed which trades were taken in the first place.
