# The data stack for a real pump.fun / Solana memecoin backtest

**Written 2026-10-06.** Companion to `02_findings/memecoins.md` (the cost-honest result:
buying any launch nets −49% to −66% at realistic size) and `04_live_system/pumpfun_recorder.py`
(the free recorder already running here). This brief is the receipts for *why* that recorder
is built the way it is, and what it would take to go further — tick-level trades, wallet-level
replay, and a real execution cost model — without guessing at vendor terms. Every number below
is from the vendor's own docs, fetched 2026-10-06; where a page 404'd or wouldn't give a number,
it's marked **not verified** rather than filled in from memory.

## 1. Full historical trades per token (every swap: wallet, amount, slot)

| source | what it gives | history depth | rate limit | monthly cost |
|---|---|---|---|---|
| **Bitquery** | Per-tx DEX trades (side, wallet, amount), per-slot order, OHLCV (1s–1h), creation + curve state, holders. [Docs](https://docs.bitquery.io/docs/examples/Solana/Pump-Fun-API/) | Real-time `DEXTrades` keeps only a "recent window"; full history needs a separately-sold **archive dataset / Parquet export** — depth not stated. | Personal 30/min (3 concurrent), Pro 90/min (6), Scale 240/min (12). [Pricing](https://bitquery.io/pricing) | $29 (100k pts), $69 (1M pts), $199 (5M pts); overage ~$35–50/1M pts. |
| **Helius** enhanced-tx API | Parses raw txs into typed events incl. pump.fun swaps. New Parsed Events API free on paid plans through Sep 2026 (beta). | Bound by RPC retention; walk signatures yourself for full history. | Free 10 RPS/1M credits; Dev $49 = 50 RPS/10M (parsing 0.1 credit/msg); Biz $499 = 200 RPS/100M; Pro $999 = 500 RPS/200M. [Pricing](https://www.helius.dev/pricing) | $0–$999+. |
| Shyft, Birdeye, Solscan Pro, Dune, Flipside | All advertise pump.fun/Solana trade and wallet data (Shyft: parsed callbacks; Birdeye: trade list + a `wallet-portfolio` endpoint; Solscan Pro: wallet DeFi-activity; Dune/Flipside: decoded SQL tables). | **not verified** — see below | **not verified** | **not verified** |

Every pricing/endpoint page for Shyft, Birdeye, Solscan Pro and Dune 404'd or redirected
without resolving a number on direct fetch (2026-10-06); Flipside's pricing URL redirected to
an unrelated parked domain, which is itself worth noting — check whether the product has moved
before relying on it. Bitquery and Helius are the only two confirmed from primary docs today.
Read `docs.shyft.to`, `docs.birdeye.so` (data.birdeye.so), `pro-api.solscan.io`, `docs.dune.com`
and `docs.cielo.finance` directly before budgeting around any of them.

## 2. Real-time feeds

| source | what it streams | notes |
|---|---|---|
| **Helius LaserStream** | Managed Yellowstone/Dragon's Mouth gRPC Geyser feed. Mainnet needs Business ($499/mo) or Pro ($999/mo, +$400/mo bandwidth add-ons); Developer tier is devnet-only. [Pricing](https://www.helius.dev/pricing) | Confirmed. |
| **Triton One Yellowstone "Dragon's Mouth" gRPC** | Account writes, txs, (beta) pre-execution deshredded txs, slot/block notifications; up to ~400ms edge over polling RPC. [Docs](https://docs.triton.one/project-yellowstone/dragons-mouth-grpc-subscriptions) | No price published — **not verified**; sold commercially at `api.rpcpool.com`. |
| **Shyft Geyser gRPC** | Advertised as a Yellowstone provider alongside Helius/Triton. | **Not verified** (pricing 404'd). |
| **PumpPortal `subscribeNewToken` / `subscribeMigration`** | Free new-mint and migration events on one shared websocket. [Docs](https://pumpportal.fun/data-api/real-time) | This is what `pumpfun_recorder.py`'s 30s poll of `/coins` substitutes for — the socket would cut discovery latency to sub-second. |
| **PumpPortal `subscribeTokenTrade` / `subscribeAccountTrade`** | Per-swap trade events. [Docs](https://pumpportal.fun/data-api/real-time) | **Metered, not free**: 0.01 SOL / 10,000 events (≈$1.50–2 at 2026 SOL prices), wallet needs ≥0.02 SOL funded. "Free real-time trades" isn't true once you want the trade stream. |

## 3. Wallet-level: swap history and PnL

- **Helius**: walk a wallet's signatures via `getSignaturesForAddress` + enhanced parsing to rebuild every swap; no PnL field, you compute it. Confirmed to exist.
- **Solscan Pro, Birdeye (`wallet-portfolio`), Cielo**: all advertise wallet history/PnL in their docs navigation, but every pricing/endpoint page tried 401'd, 404'd, or returned no detail. Cielo confirmed only that API keys exist; whether it's a snapshot or full swap-by-swap history is **not verified** for any of the three.

None of these three gave a confirmed, complete "wallet swap history + realized PnL, priced"
answer today — read primary docs before building the wallet-replay stack in §6c on them.

## 4. Open-source backtesters and datasets

**Datasets (HuggingFace, confirmed by direct listing, not opened or schema-checked):**
`Slinky21/Pumpfun_v2_dataset` (1.62B rows, largest found), `Slinky21/Pumpfun_Memecoin_Corpus`
(63.7M), `loopholetape/pumpfun-launches` (990k, updated hours before this brief), `rincel/pumpfun`
(23.2M), `Pumpdotstudio/pump-fun-sentiment-100k` (193k, sentiment labels not price/trade data),
`akilx/pump-fun-point-in-time-forensics` and `-30days-forensic-trades` (90 / 125, case-study
scale), `muhammetakkurt/pump-fun-meme-token-dataset` (135, too small to use). Row counts are
HuggingFace's own listing, not verified for quality or survivorship bias.

**The ~750k-token academic dataset.** `memecoins.md` cites "arXiv 2607.02823 v4" at AUROC 0.46
out of sample — confirmed by direct fetch. It's a pre-registered logistic-regression study on
**749,816 unique pump.fun mints** from a V3 off-chain collector (12 May–10 June 2026), trained on
15 days and tested on a held-out 14. Development AUROC was **0.8594**; out-of-sample it collapsed
to **0.4642** (random), calibration slope 0.013. The paper's point is methodological: graduation
labels from an off-chain collector don't reliably measure the platform's real outcome, and models
trained on them don't generalize. This is the strongest evidence here that a backtest trusting a
vendor's "graduated" label, rather than the raw curve account state `pumpfun_recorder.py` reads
via `getMultipleAccounts`, is the trap, not the edge.

**GitHub repos** (found via code search, none vetted for correctness — names exist, nothing more
is confirmed): `charllysb/pumpfun-momentum-bot` (slippage modeling, claimed "honest" backtesting),
`cavalheiroeth/pumpfun-sniping-lab` (look-ahead-free backtesting claim), `prisyy/pumpsim-api`
(off-chain curve/PumpSwap simulator), `ReapFXS/ReapX-sniper` (Jito + backtest mode), and three
sniper-bot reverse-engineering repos (`web3daemon`, `Sorghobrayan-dotcom`, `Foreist` —
`solana-sniper-reverse-engineering`) relevant to the deployer/sniper wallet patterns that are the
real "first block" edge.

## 5. Execution APIs (described only, no code)

- **Jupiter Swap API**: aggregates Solana DEX routes via `/quote` → `/swap`
  (`inputMint`/`outputMint`/`amount`/`slippageBps` in, best route + price impact out). Supports
  an optional `platformFeeBps`/`feeAccount` for an integrator's own cut; no mandatory Jupiter fee
  seen in the docs fetched. The endpoint fetched (`/swap/v1/quote`, "Metis") is flagged by
  Jupiter itself as superseded by Swap V2 — don't build new work on it. Rate limits/key tiers
  **not stated** in the page fetched.
- **PumpPortal trade API**: **Lightning** (API-managed wallet, routes through Jito bundle
  relays) charges a confirmed **1% fee/trade**; **Local** (self-signed, PumpPortal just
  relays) charges a confirmed **0.5%/trade**. Both taken before slippage, separate from network
  and pump.fun bonding-curve fees.
- **GMGN's router**: Sholo's own screen — unofficial/reverse-engineered, not a published API,
  widely reported to sit behind Cloudflare. `memecoins.md` treats wiring a GMGN/Jupiter
  execution path as the easy, unsolved part. **Not independently verified** (no GMGN docs
  fetched).
- **Jito**: Solana's MEV/bundle layer. Confirmed: bundles need a **minimum 1,000-lamport tip**
  (often insufficient under load; live tip-floor at `bundles.jito.wtf/api/v1/bundles/tip_floor`),
  auctioned every 50ms on tip-per-compute-unit; for a plain `sendTransaction`, Jito's own
  guidance is a 70/30 priority-fee/tip split. This is the mechanism behind the sub-100ms
  "first block" snipe that, per `memecoins.md`, decides who gets the 7x and who buys the exit.

**Fee stack for a $100 round-trip:** PumpPortal Lightning 1% + venue ~1% + 2% modeled slippage
+ price impact (order ÷ half pool liquidity), each way. On the study's median $3k pool, impact
alone is ~7% a side — before any Jito tip, which affects whether the tx lands, not its price.

## 6. The free path, and the two paid stacks

**(a) Free recorder** — what `pumpfun_recorder.py` already is: PumpPortal's free new-mint/
migration feed (or the polled `/coins` this repo uses), public RPC `getMultipleAccounts` for
exact curve state, DexScreener for post-graduation price/liquidity/volume. **Can
reconstruct:** birth-to-24h price path, curve fill, graduation, every GMGN-screen factor.
**Cannot reconstruct:** individual swaps — no deployer/sniper wallet attribution beyond "minted
before," no fill-level slippage, no sub-30s resolution — so it cannot see the sub-100ms
first-block sniping the literature says decides the outcome. A recorder of outcomes, not
mechanism.

**(b) A $50/month stack.** Helius Developer ($49/mo: 10M credits, 50 RPS, enhanced-tx parsing,
webhooks) replaces the free RPC with a webhook instead of a poll, and gives parsed transactions
for wallet work within credit budget — still short of real-time trade-by-trade streaming
(needs LaserStream mainnet, $499/mo) or a paid PumpPortal trade-stream (cheap per-event but
billed in SOL from a funded wallet). Closes the reliable-curve-state gap; doesn't close
every-swap-every-wallet.

**(c) A wallet-replay backtest.** Needs per-swap, per-wallet, per-slot data, which nothing free
gives. Realistic minimum: Bitquery Pro ($69/mo, confirmed) or Helius Business ($499/mo,
confirmed) for parsed transactions, walked per creator and early-buyer wallet to find who was
in the first block; Bitquery's archive/Parquet export (price not published) or a self-run RPC
replay for depth beyond the live parsers' recent window. Label outcomes from the raw curve
account state, never a vendor's "graduated" flag — arXiv 2607.02823's AUROC collapse from 0.86
to 0.46 is a direct demonstration of what trusting a collector's label instead of the chain's
own data does to a backtest.

## Sources

- [Bitquery Pump.fun API docs](https://docs.bitquery.io/docs/examples/Solana/Pump-Fun-API/)
- [Bitquery pricing](https://bitquery.io/pricing)
- [Helius pricing](https://www.helius.dev/pricing)
- [Triton Yellowstone Dragon's Mouth gRPC docs](https://docs.triton.one/project-yellowstone/dragons-mouth-grpc-subscriptions)
- [PumpPortal real-time data API docs](https://pumpportal.fun/data-api/real-time)
- [PumpPortal trading API docs](https://pumpportal.fun/trading-api/)
- [PumpPortal fees](https://pumpportal.fun/fees)
- [Jupiter swap API quote reference](https://developers.jup.ag/docs/swap-api/get-quote)
- [Jito low-latency transaction send docs](https://docs.jito.wtf/lowlatencytxnsend/)
- [Jito](https://www.jito.wtf/)
- [arXiv 2607.02823](https://arxiv.org/abs/2607.02823)
- [HuggingFace datasets search: pump.fun](https://huggingface.co/datasets?search=pump.fun)
- [GitHub code search: pump.fun backtest](https://github.com/search?q=pump.fun+backtest&type=repositories)
- Birdeye, Solscan Pro, Shyft, Dune, Flipside, Cielo: pricing/endpoint pages either 404'd,
  401'd, or redirected to unresolved/unrelated content on 2026-10-06 (noted inline above as
  **not verified**); confirm directly at `docs.birdeye.so`, `pro-api.solscan.io`,
  `docs.shyft.to`, `docs.dune.com`, and `docs.cielo.finance` before budgeting.
