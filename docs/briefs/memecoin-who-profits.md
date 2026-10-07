<!-- research brief, filed 2026-10-06; agent output verbatim. Extends docs/briefs/memecoins.md
     (launch survival, sniping economics, retail EV) and docs/briefs/retail-base-rates.md
     (day-trading base rates generally) rather than repeating either. -->

# Who actually profits in Solana memecoins — the "numbers argument" tested

**Question tested:** Sholo's claim that "because of numbers, Twitter, copy trading, there has got
to be a way; good traders lock in 5-200% per trade within seconds." This brief inventories every
quantified source on who gets the money, by what mechanism, and whether a $5,000 account at
~100ms retail latency can reach that cohort. `docs/briefs/memecoins.md` already covers launch
survival rates and sniping cost structure in depth — this brief does not re-derive those, only
cites them where needed for the profit-concentration argument.

## 1. Wallet-level PnL: the denominator the leaderboards hide

The clearest numbers remain the ones in `memecoins.md` §3: of 29.6M pump.fun wallets (Aug 2024
Dune data via [crypto.news](https://crypto.news/only-0-76-of-pump-fun-wallets-made-1000-or-more-cn-research/)),
37.6% were ever profitable, but only **0.76% ever made $1,000+, 0.046% ever made $10k+, and
0.0033% ever made $100k+**. A later Dune pull ([Cointelegraph, Jan 2025](https://cointelegraph.com/news/pump-fun-crypto-traders-majority-do-not-realize-profits-dune-data))
on 13.55M wallets found **293 wallets total (0.00217%)** had ever cleared $1M. These are the
base rate the rest of this brief sits on top of: roughly 1 wallet in 30,000 ever reaches
six figures, lifetime, not per trade.

Two new data points sharpen the concentration story. [LIBRA](https://www.theblock.co/news/business/2025-02-19-traders-of-solana-based-libra-memecoin-lost-251-million-nansen-342266)
(the Feb 2025 Milei-endorsed token) is the best single-event case study Nansen has published:
of wallets with an absolute gain/loss over $1,000, **86% lost money, totaling $251M lost against
$180M won** by the other 14%. The single largest winner, "one of the most successful snipers,"
realized **$6.5M** — and the wallet was funded directly by a Bybit deposit and a second wallet
tagged as a trading-bot user, i.e. infrastructure, not luck. Separately, a Sep 2026 paper on
Solana "AI agent" treasury tokens — a distinct but structurally identical population to memecoins
([arXiv 2605.29174](https://arxiv.org/abs/2605.29174)) — measured 925,323 holders across 11
treasuries and found the **top 1% of wallets captured 81.4% of all gains ($1.81B)** while
token holders collectively lost **$191.7M**, with negative median returns on every platform.
No public Dune dashboard publishes an all-time, all-wallet PnL histogram (the closest, frozen
dashboards, are noted in `memecoins.md`), but every slice that exists — 2024 pump.fun, 2025
LIBRA, 2026 agent tokens — lands on the same shape: a thin top percentile takes most of the
pool, and that percentile is funded, bot-run, or insider-adjacent, not a larger population of
skilled discretionary retail traders.

## 2. The profitable cohorts, named, and what they actually are

- **Deployer-funded sniper wallets.** `memecoins.md` §2 already has the full Pine Analytics
  numbers (4,600+ sniper wallets, 87% win rate, funded by 10,400 deployers). Re-fetched here for
  the mechanism: [Pine Analytics](https://www.bitget.com/news/detail/12560604803448) states
  explicitly that extraction requires "pre-signed transactions, off-chain coordination, or
  shared infrastructure between deployer and buyer," and that without it "independent retail
  traders... become liquidity exits instead of profiteers." This is not a cohort an outside
  wallet can opt into; it requires being the deployer or being paid by one.
- **Coordinated sniper rings.** [arXiv 2607.02795](https://arxiv.org/abs/2607.02795) (June 2026,
  166,098 launches, 1.58M buyer observations) detected **1,012 persistent wallet cohorts** (2,965
  addresses) that repeatedly buy together in the first 30 minutes of new launches. Contamination-
  adjusted, they produce a real but small **+16.1% lift in buyer count**, while their lift in
  actual SOL inflow is **+6.3%, statistically indistinguishable from zero** — meaning the
  "coordination edge" is mostly about making a launch look busier to outside buyers, not about
  capturing outsized inflow themselves. 7% of matched launches had zero non-cohort buyers in the
  first 30 minutes at all.
- **Manipulation-as-a-Service operators.** [arXiv 2609.10246](https://arxiv.org/abs/2609.10246)
  (15M pump.fun tokens, full history) is the most granular breakdown available: **17% of all
  trades are wash trades**; the **top 1% of creator address clusters produced 58.6% of all
  coins**; coordinated "dump" events extracted **$2.5–5M** across a 1% sample (median 7
  coordinated senders per dump, one case with 312); **10% of all coins (1.49M) are automated
  copycats** of successful launches, graduating at 0.86% vs. 9.20% for originals. These are
  repeat, tool-using operators, identifiable by address clustering, not discretionary traders.
- **Social/KOL monetizers.** The same paper found 23.5% of all coins were created in response to
  a tweet or Truth Social post, and that **31 posts (top 0.002%) generated ≥$1M in extractable
  value each, accounting for 83.4% of all post-attributable profit** — one post produced an
  estimated $113.6M. The mechanism is: an account with reach launches or calls a token, early
  buyers (often the account's own other wallets) exit into the attention it generates, and the
  followers who bought on the post are the exit liquidity. This is the "Twitter" half of
  Sholo's claim, and the data shows it concentrates in a couple dozen accounts a cycle, not a
  skill any follower can replicate by watching them.
- **MEV searchers and sandwich/arb bots.** Jito-routed activity, measured in
  [Helius's Solana MEV Report](https://www.helius.dev/blog/solana-mev-report.md): in 2024, Jito
  processed 3B+ bundles for 3.75M SOL in tips (Jito keeps a 5% cut). A single sandwich program
  ("Vpe bot") ran 1.55M attacks over 30 days at an **88.9% success rate for $13.43M total profit
  (avg $8.67/attack)**, paying $4.63M of it back in tips. Arbitrage bots detected over a year
  cleared **$142.8M across 90.4M transactions (avg $1.58/trade, max single arb $3.7M)**. This is
  real, large, and systematic — but it runs on co-located infrastructure racing for same-slot
  execution, the same latency requirement `memecoins.md` already measured as unreachable at
  retail latency (slot-0 landing <20% of the time off a generic cloud RPC, vs. ~89% co-located).
- **Launchpad fee revenue.** The only cohort collecting money with zero variance: pump.fun's own
  1% per-side fee on every trade, which Coinedition projected toward **~$935M of 2026 revenue**
  (`memecoins.md` §6) even as graduation rates and volume collapsed — the house takes its cut
  regardless of who wins the trade.

## 3. Leaderboards (GMGN, Kolscan, Cielo): survivorship by construction

[Kolscan](https://kolscan.io/)'s own stated listing bar is "**$100k+ PnL in recent months**" —
the leaderboard's inclusion criterion is itself profitability, so by design it cannot show a
loser, and it displays no win-rate or hold-time aggregate, only individual transaction logs per
wallet. No independent methodology paper auditing GMGN/Kolscan/Cielo PnL accuracy (wash-trade
inflation, bundler self-trades, or mid-price vs. fill-price marking) was found this session —
that audit does not appear to exist publicly, which is itself a finding: the leaderboards people
cite as "proof good traders exist" have never been checked against the manipulation patterns
§2 just quantified (17% wash trades, bundled creator clusters, coordinated dumps) on the exact
wallets they rank. Given that profile wallets self-select into these boards only after already
clearing six figures, and the broader population shows roughly 1 in 30,000 wallets ever doing
that lifetime (§1), the leaderboard is observationally a photograph of the top 0.003%, relabeled
as a demonstration that the method works.

## 4. Individual stories, and the base rate against them

- **"Naseem," $1.09M → $100M+ on TRUMP** ([Bubblemaps via The Block](https://www.theblock.co/news/web3/2025-02-18-crypto-analytics-platform-bubblemaps-claims-one-trader-turned-1-million-into-109-million-trading-trump-memecoin-341664)):
  spotted an official Meteora pool address interacting with the TRUMP-USDC pair *one day before*
  the public launch, bought $1M+ in the first second of trading, paid an **$84,000 priority fee**
  to guarantee execution, and split funds across 9+ wallets. Pre-launch pool detection plus a
  five-figure priority fee is not a $5,000-account strategy; it is the same slot-0 infrastructure
  problem `memecoins.md` already measured.
- **Top Dune-ranked pump.fun wallet, ~$40M** ([The Block, Mar 2025](https://www.theblock.co/news/web3/2025-03-06-top-pump-fun-traders-profits-near-40-million-as-solana-memecoin-volumes-shrink-345046)):
  identity, method, trade count and win rate are all undisclosed — the number is a dashboard
  total, not an audited strategy.
- **SIAS deployer, ~$600K** ([Bubblemaps via The Block](https://www.theblock.co/news/ecosystems/2026-02-11-cry-me-a-river-x-1m-article-winner-accused-of-profiting-600k-from-solana-memecoin-rug-pulls-389385)):
  alleged insider who deployed the token, accumulated through satellite wallets, and sold into
  retail before collapse to zero — fraud, not a tradeable edge, and unproven besides.
- **LIBRA sniper, $6.5M**: Bybit- and bot-funded wallet, inside the 14% that won on a single
  presidential-endorsement event most retail couldn't have anticipated or front-run.

Every on-chain-receipted story above required one of: advance knowledge of an unannounced pool,
five-figure priority fees, multi-wallet bot funding from an exchange, or outright insider
deployment. None involved a documented case of a $5,000 account, no infrastructure edge, winning
this way from a cold start — which is consistent with, not an exception to, the 1-in-30,000 base
rate in §1.

## 5. Systematic strategy studies, out of sample

No public, peer-reviewed or vendor study was found that backtests a systematic memecoin strategy
and reports genuinely out-of-sample returns at retail (150–500ms, no co-location) latency with a
positive result. The closest attempts, already detailed in `memecoins.md`, both failed on the OOS
test specifically: the "Money Leaves Clues" 770-call-channel study showed average returns of
+552% driven entirely by an unreachable instant-fill tail, while the realistic 15-second-entry
median was **−6.2% at 1 minute and −10.5% at 5 minutes**; and the graduation-prediction model in
[arXiv 2607.02823v4](https://arxiv.org/abs/2607.02823v4) went from AUROC 0.86 in-sample to **0.46
on a held-out fortnight** — worse than a coin flip. The coordinated-cohort paper in §2 is the
closest thing to a "strategy that works," and even there the measurable edge (SOL inflow lift)
rounds to zero once contamination is removed; only the optical buyer-count lift survives.

## 6. Who profits — table

| Who | Mechanism | Evidence | Size (measured) | $5k retail @ ~100ms reachable? |
|---|---|---|---|---|
| Deployer-funded snipers | Pre-funded wallet buys in genesis block | Pine Analytics, 4,600+ wallets, 87% win rate | 15,000 SOL net | No — requires deployer relationship/pre-signed tx |
| Coordinated sniper rings | Repeat multi-wallet first-30-min buying | arXiv 2607.02795, 1,012 cohorts | +16.1% buyer lift, ~0% real inflow lift | No, and the real edge is near zero anyway |
| Wash-trade / dump operators | Fabricated volume, coordinated exit dumps | arXiv 2609.10246, 15M tokens | $2.5–5M per dump sample; 17% of all trades | No — needs many controlled wallets, repeat tooling |
| KOL/social monetizers | Post reach drives buying; insiders exit into it | arXiv 2609.10246; LIBRA, TRUMP cases | 31 posts = 83.4% of post profit; $109M, $40M, $6.5M individual cases | No — needs an audience or advance pool knowledge |
| MEV searchers / sandwich & arb bots | Same-slot execution via Jito bundles | Helius MEV Report | $13.4M/30d (sandwich bot), $142.8M/yr (arb) | No — needs co-location, slot-0 landing <20% off generic RPC |
| Launchpad (pump.fun) | 1% fee both sides, every trade | Coinedition, ~$935M 2026 projected revenue | Guaranteed, zero variance | N/A — not a trading strategy |
| Leaderboard-listed "top trenchers" | Survivorship: $100k+ PnL required to be listed | Kolscan FAQ | Unverified win rate/hold time published | No — the board is the output, not a replicable input |
| Unfiltered retail buy-at-first-sight | None — buys after all of the above have already acted | `memecoins.md` verdict | −8% to −15%/launch estimated EV | This is the only cohort a $5k/100ms account actually joins |

## Honest answer: is it possible?

Not the way the claim frames it. "Numbers, Twitter, copy trading" describes the *mechanism by
which other people's money moves*, not a mechanism a $5,000 account at ordinary retail latency
can join: every measured profitable cohort above is defined by something retail structurally
lacks — deployer access, multi-wallet bot funding, pre-launch information, five-figure priority
fees, co-located same-slot execution, or an audience to sell into — and the one cohort retail
*can* join (buying after sight on a public feed) is the one with negative measured expected value
in every study found, including the two most favorable-sampled ones (call channels, coordinated-
cohort "lift"). The leaderboards that make this look achievable are built, by their own stated
listing criteria, to only ever display winners, so they are not evidence the game is winnable by
more people than the roughly 1-in-30,000 who have ever cleared six figures doing it — they are a
photograph of that 1-in-30,000, cropped to hide everyone else.
