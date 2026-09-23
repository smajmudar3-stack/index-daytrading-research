<!-- research brief, filed 2026-09-22; agent output verbatim; verdicts copied to 02_findings/online_methods.md -->

No further fetches are needed; every section now has at least one primary source with numbers. Here is the report.

---

# Memecoin launch trading as an automated profit source (US retail, 2026)

## 1. Survival and return distribution of new launches

**Graduation (bonding curve to DEX) is the only "success" outcome that is measured at scale, and it keeps falling.**

- [arXiv 2602.14860](https://arxiv.org/html/2602.14860v1) (Marino et al.): 655,770 pump.fun tokens, Sep–Oct 2025, 4,338 graduated = **0.63%**. Median time-to-graduation 4.4 minutes. Among tokens with enough history, **92.22% show at least one 4-sigma dump**. The paper's own conclusion: the graduation probability conditional on curve state "lies below the breakeven curve", so buy-and-hold on curve position alone has negative expected return.
- [arXiv 2607.02823](https://arxiv.org/abs/2607.02823v1) (Kamat): 832,941 launches, May–Jun 2026, graduation **0.198%** (CI 0.189–0.208%), a 3.18x decline in eight months. Telegram present: 1.485% vs 0.166% without (8.9x). All three socials: 1.919% vs 0.110%. Initial mcap above 30 SOL: hazard ratio 4.51. **Read the caveat before using it:** by v4 the paper is retitled ["Auditing Collector-Generated Graduation Labels… Measurement Error and Temporal Non-Generalization"](https://arxiv.org/abs/2607.02823v4). The collector saw only ~2.77 minutes of each token's life ([Zenodo v1.3 corrigendum](https://zenodo.org/records/21908375)), "TIMEOUT" did not establish non-graduation, and the predictive model went from AUROC 0.86 in development to **0.46 on the held-out fortnight** (CI includes 0.5). This is a first-sight recorder failing on exactly the design we are running.
- [DEXTools](https://www.dextools.io/news/pump-fun-graduation-collapse-solana-fees-2026) reports the rate at **0.26% in mid-June 2026**; [Solana Compass](https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex) reports 42,000 launches in one day, 11.9M lifetime, 96 tokens ever above $1M mcap, 18 above $10M.
- [CoinGecko lifespan study](https://www.coingecko.com/research/publications/average-lifespan-of-pumpfun-tokens): 18.67M tokens (Jan 2024–Jun 2026), death = last curve trade. **68.67% die the same day, 80.37% within one day**, 4.55% trade past 90 days.
- [arXiv 2512.11850](https://arxiv.org/abs/2512.11850): pump.fun was 71% of all Solana mints in Q4 2024, <2% reached a major DEX.
- [Solidus Labs](https://www.soliduslabs.com/reports/solana-rug-pulls-pump-dumps-crypto-compliance): of 7M+ pump.fun tokens with ≥5 trades, **98.6% ended below $1,000 liquidity**; 93% of 388k Raydium pools showed soft-rug patterns, median sweep $2,832. Note this is a collapse rate, not a proven-fraud rate. [Chainalysis](https://www.chainalysis.com/blog/crypto-crime-2024-pump-and-dump/) flags a narrower 3.6% of 2024 launches (74,037 tokens) as pump-and-dump by strict criteria; both numbers are true of different definitions.
- [MemeTrans, arXiv 2602.13480](https://arxiv.org/html/2602.13480v1): of 41,470 tokens that *did* migrate (the survivors), **84.13% fell below 0.3x migration price within 20 minutes or scored as manipulated**; 28% of holders were bundled wallets holding 36.5% of supply.
- [Midsummer Meme's Dream, arXiv 2507.01963](https://arxiv.org/html/2507.01963): 31,811 listed (older, survivor) tokens across BSC/Solana/ETH/Base: three-month returns split 34% down (median −28%), 32% flat/inactive, 34% up (median +21%); of the 707 that gained >100%, **82.8% show wash trading, LP inflation or concentration**.

No public Dune dashboard publishes a per-launch return distribution at fixed hold times across all launches. The closest is [jondar's dashboard](https://dune.com/jondar/pumpfun) (frozen Mar 2025): 25% of tokens still active after 1 day, 13% after 7, 7% after 30.

## 2. Sniping economics

- **Who is in the first block.** [Pine Analytics via BlockBeats](https://www.bitget.com/news/detail/12560604803448): 15,000+ launches since Mar 2025, **over 50% sniped in the genesis block**, 4,600 sniper wallets funded by 10,400 deployers, 15,000 SOL net profit, **87% of snipes profitable, 55% exited within 1 minute, 85% within 5 minutes**, 90% exit in 1–2 sells, active 14:00–23:00 UTC. These are the deployer's own wallets; an outside buyer is their exit.
- **Competition.** [Dysnix](https://www.dysnix.com/blog/top-solana-sniper-bot): 200+ bots in the first 500 ms of a typical launch; funnel of 200 attempts → ~10 profitable exits. [RPC Fast](https://rpcfast.com/blog/how-to-launches-snipe-pump): co-located Frankfurt gRPC (<35 ms) lands slot 0 ~89% of the time; generic cloud at 220 ms lands slot 0 **<20%**; WebSocket 150–300 ms, polling 100–500 ms. Slot 0 vs slot 2 is a 20–60% entry-price difference on the curve.
- **Costs.** Jito tips 0.001–0.01 SOL for snipes ([OpenLiquid](https://openliquid.io/tools/pumpfun-sniper-bot/)), 0.01–0.1 SOL for launch bundles; tip floor rises 10–50x around viral launches; live percentiles at bundles.jito.wtf/api/v1/bundles/tip_floor. Default slippage 15%. Pump.fun charges 1% each way; tool fees 0.5–1%. Vendors' own effective cost per winning trade: $2.65–$7.75 before losses. Pump.fun's curve starts with ~30 SOL virtual reserves, so a $500 buy at creation moves price by several percent on its own.
- **Peak timing and fixed-hold returns.** The only public fixed-hold study is [Money Leaves Clues](https://moneyleavesclues.substack.com/p/inside-the-economics-of-pumpfun-call) on 770 call-channel picks (a favourable, pre-selected sample): median token age at call 2.9 minutes; "instant" entry/30 s exit averaged +552% but **median −4.0%**; a realistic 15 s entry gave median **+0.2% at 30 s, −6.2% at 1 min, −10.5% at 5 min, −10.7% at 10 min**, before fees. The average is a tail nobody at retail latency captures. Even a sniper vendor admits "most profitable snipers lose money on 60–80% of individual snipes" ([OpenLiquid](https://openliquid.io/tools/pumpfun-sniper-bot/)).

## 3. Verified trader P&L

- [crypto.news / Dune, Aug 2024](https://crypto.news/only-0-76-of-pump-fun-wallets-made-1000-or-more-cn-research/): 29.6M wallets, 37.6% profitable, 59.9% losing; **0.76% ever made $1,000+, 0.046% $10k+, 0.0033% $100k+**.
- [Cointelegraph / Adam Tehc, Jan 2025](https://cointelegraph.com/news/pump-fun-crypto-traders-majority-do-not-realize-profits-dune-data): 13.55M wallets, 0.412% above $10k, 0.048% above $100k, 293 wallets (0.00217%) above $1M.
- [CoinGecko, May 2026](https://www.coingecko.com/research/publications/pump-fun-traders-are-making-a-comeback): share of wallets with realised profit was 30–45% from Feb 2025 to Dec 2025 and rose to 57–73% in Feb–Apr 2026, but on realised trades only (bagholders excluded) and 65% of the winners made $1–$500.
- Concentration: [Focai](https://www.tradingview.com/news/cointelegraph:8e276a1b6094b:0-suspected-insider-wallets-net-20m-on-solana-s-focai-memecoin-launch/), 15 wallets, $14,600 in, 60.5% of supply, $20M out (Lookonchain). The [reverse-engineered orcACR bot](https://www.mikem.codes/if-you-aint-first-youre-last-2/) made ~100–200 SOL/day buying ~20% of all new coins with sub-second co-located infrastructure, holding ~20 s, and skipping creators with prior tokens, creator buys over 4 SOL, or creators funded by other creators. That is the profit pool; 200 other bots are chasing it.

## 4. Rug and honeypot detection

RugCheck, TokenSniffer and GoPlus publish no precision/recall; [LROO (arXiv 2603.11324)](https://arxiv.org/html/2603.11324v1) notes none provide reproducible evaluation and measures existing detectors at ~20–60% accuracy on 1,000 hand-labelled EVM tokens, its own TabPFN at 98% (small, EVM-only, hand-labelled). [MemeTrans](https://arxiv.org/html/2602.13480v1) is the best Solana number: precision 0.85, recall 0.83 for "high risk" on post-migration tokens, cutting losses 56% in simulation. But with an 84% base rate of high-risk, a detector that passes 15% of migrations still leaves a thin, adversarial residue, and pre-migration (where a sniper acts) there is no benchmark at all.

## 5. Sniper-bot ecosystem

Open-source repos ([TreeCityWes](https://github.com/TreeCityWes/Pump-Fun-Trading-Bot-Solana), [jcoulaud](https://github.com/jcoulaud/pumpfun-sniping-bot), [cutupdev](https://github.com/cutupdev/Solana-Pumpfun-Sniper-Bot), [slycompiler](https://github.com/slycompiler/pumpfun-sinperbot)) publish strategy logic and demo PnL logs, never an audited or wallet-addressed track record. The jcoulaud repo's stated edge is the tell: it *creates* tokens and "sells into sniper buys". Commercial vendors quote 10–15% of bots profitable and 70% per-snipe loss rates as normal. No vendor I found publishes a signed wallet with verifiable history.

## 6. US legal, tax and practical constraints

- DEX access is KYC-free and lawful for a US person; the SEC's Feb 27 2025 staff statement treats memecoins as non-securities, and the DeFi broker rule was repealed under the CRA (Apr 2025), so **no 1099-DA from DEXs but every swap is still reportable** ([IRS 1099-DA instructions](https://www.irs.gov/instructions/i1099da), [TokenTax](https://tokentax.co/blog/memecoins-tax)). Gains are short-term (up to 37%), wash sale does not apply, basis is per-wallet since 2025. A bot doing 200 swaps a day produces ~36,000 taxable events in five months.
- A pending ~$500M class action alleges pump.fun insiders front-ran users ([Coinedition](https://coinedition.com/pump-fun-2026-prediction-935m-revenue-battles-500m-lawsuit-and-98-6-rug-pull-crisis/)); no US geoblock so far.
- [TRM Labs, Sep 2026](https://www.trmlabs.com/resources/blog/fake-ai-trading-bots-are-getting-victims-to-build-their-own-drainers): nine AI-narrated "build a Claude arbitrage bot" YouTube tutorials, 310k views, 224 victims, 274.6 ETH ($517k), median 1 ETH; the fake compiler swaps in a drainer contract, no phishing link involved. [Scam Sniffer](https://drops.scamsniffer.io/over-4-million-stolen-by-multiple-solana-wallet-drainers/) and [DeepStrike](https://deepstrike.io/blog/crypto-wallet-drainer-statistics) document Solana drainer-as-a-service (CLINKSINK etc.). Any bot must run from a hot wallet holding only its float, on code you compiled yourself.

## Verdict

**Expected value per launch, retail latency (DexScreener first sight, 150–500 ms, no co-location):** negative. Stack the measured pieces: entry after the genesis-block insiders (50%+ of launches) and after the 200-bot slot-0 scramble; 2% platform fees, 1–5% curve impact each way on $100–500 size, tip and failed-tx burn; the deployer-funded snipers exit 55% within 1 min and 85% within 5 min into you; the favourable call-channel sample shows −6% to −11% median at 1–10 minutes before those costs. My estimate is **−8% to −15% of stake per launch** for an unfiltered buy-at-first-sight rule, and roughly **−3% to +2%** for a heavily filtered rule (Telegram present, creator with no prior tokens, creator buy <4 SOL, no genesis-block buys, initial mcap >30 SOL), which passes perhaps 2–5% of launches. The upside is in a ~1–3% tail of 5x+ outcomes, so the mean is unknowable from small samples and the median trade loses.

**Variance:** per-trade standard deviation on the order of 100%+ of stake; monthly PnL dominated by whether one or two tails were caught. **Capacity:** $100–500 per launch before your own impact on a 30-SOL curve becomes the trade; at 100 filtered launches/day that is ~$20k/day turnover with ~5% friction, i.e. about $1,000/day of cost to overcome before any edge.

**$5,000 to $50,000 in five months** needs ~1.55%/day compounded on the whole book, net of friction that runs ~5% per round-trip on a negative-EV base. Not plausible for a retail-latency bot. The documented winners (orcACR, deployer-funded snipers, Focai insiders) are either co-located infrastructure spending five figures on tips and RPC, or the deployer. What a retail bot can plausibly do is lose $5,000 slowly with a nonzero chance of one lucky 20x that makes the log look like skill.

## What a rigorous measurement must record (beyond first-sight price and 24h repricing)

1. **Detection lag per launch**: creation slot timestamp vs your first-sight timestamp. 2607.02823 died on a 2.77-minute window it did not know it had.
2. **Executable, not observed, prices**: simulate a fixed buy ($100/$250/$500) against the curve's virtual reserves at first sight (1% fee, impact, tip), and a sell at each horizon the same way. Report the all-launch distribution net of that.
3. **Dense sampling in the first 10 minutes** (every 5–15 s). 85% of insider exits and the median call all happen before 5 minutes; hourly repricing measures the corpse.
4. **Genesis-block facts**: number of buys in the creation slot, whether those wallets were funded by the deployer, bundle share, top-10 holder share, creator's prior token count and buy size, socials present, initial mcap. These are the only features with measured hazard ratios.
5. **Platform-side outcome labels**: graduation via the migration event, rug via LP removal / freeze / dev sell, never via timeout.
6. **Execution environment**: Jito tip floor and failed-transaction rate at the time, hour in UTC.
7. **Pre-registered thresholds and a `study_guard`-style sample floor**: a 1–3% tail needs 10k+ launches before the mean is even estimable, and the mean is the entire question.

No repository files were changed; nothing to verify.
