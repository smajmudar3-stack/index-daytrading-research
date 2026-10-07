<!-- research brief, filed 2026-10-06; agent output verbatim. Companion to docs/briefs/memecoins.md
     and docs/briefs/memecoin-sniping.md, which cover pump.fun/Solana in depth. This brief asks
     the question those didn't: is BSC (four.meme), Base (Clanker/Zora) or Bonk's own launchpad
     (letsbonk.fun) a better retail venue than pump.fun, given 02_findings/memecoins.md's lead
     that BSC and Base rows in this repo's own 4,344-launch panel were the only positive-mean,
     ~40%-hit cells (n=25-87, gas unmodelled). Verdicts belong in 02_findings/ if acted on. -->

# Cross-launchpad memecoin trading: BSC, Base and Bonk against pump.fun (2026)

WebSearch was exhausted before this brief started; everything below is a direct fetch of a
primary page (vendor docs, a gas tracker, an arXiv paper, official GitHub repos) or is marked
**not verified**. Several official docs sites (four.meme, Clanker, Raydium LaunchLab, Moonshot,
DexScreener's chain-support page) are JS-rendered single-page apps or returned 403/404 to a
plain fetch — their `llms.txt` plaintext mirrors were also blocked. Where a number could not be
pulled from a primary source this session, it says so rather than filling in from memory.

## 1. Launchpad mechanics, fee structure and launch volume

| launchpad | chain | mechanism | fee (confirmed) | graduation | daily launches / graduation |
|---|---|---|---|---|---|
| **pump.fun** | Solana | bonding curve → PumpSwap | 1% + 0.5% router (`02_findings/memecoins.md`) | ~85 SOL raised (widely reported; not re-confirmed this session) | 0.198–0.63% graduate, falling ([arXiv 2607.02823](https://arxiv.org/abs/2607.02823v4), [arXiv 2602.14860](https://arxiv.org/html/2602.14860v1)); 68.7% die same-day ([CoinGecko](https://www.coingecko.com/research/publications/average-lifespan-of-pumpfun-tokens)) |
| **four.meme** | BSC | bonding curve → PancakeSwap | **not verified** — official docs (`four.meme`, `docs.four.meme`, `llms.txt`) all 403'd or didn't resolve on a plain fetch; widely reported elsewhere as ~1% but that figure is not confirmed here | **not verified** (BNB raised threshold not found in a reachable primary source) | This repo's own recorder: four.meme tokens are 5% of 4,344 DexScreener-feed launches since 2026-09-23 ([`02_findings/memecoins.md`](../../02_findings/memecoins.md)). No independent daily-count or graduation-rate figure found. |
| **letsbonk.fun / Bonk.fun** | Solana, via **Raydium LaunchLab** | "bonding-curve token launches. Configurable curves, creator fees, graduation" ([docs.raydium.io](https://docs.raydium.io/products/launchlab)) | **not verified** — the LaunchLab overview names "creator fees" but the fee-percentage sub-page wasn't reachable via plain fetch | **not verified** (threshold not reachable) | Not separately broken out in this repo's panel (folded into the 92% Solana share); GitHub shows dedicated bot tooling (`justFiveDev/bonkfun-launchlab-volume-bot`) confirming it's an active, separately-targeted venue on the *same* chain as pump.fun |
| **Moonshot** | Solana (built by the DEX Screener team) | **not verified** — moonshot.money is a marketing/app-download page with no mechanics; `docs.moonshot.money` does not resolve | **not verified** | **not verified** — "2M+ users" claimed on the landing page, no launch-volume figure |
| **Clanker** | Base (also Arbitrum, BNB, "and more") | direct ERC-20 deploy with "instant liquidity" — no bonding curve | **not verified** — docs index confirms a fee exists ("built-in fee rewards") but the percentage page didn't resolve via fetch; GitHub org repo (`Four-Meme/...` pattern doesn't apply here — official contracts not located) | **N/A** — liquidity is seeded directly, there is no curve-to-DEX migration event | **not verified** |
| **Zora (Creator/Content/Trend Coins)** | Base | **no bonding curve** — "dedicated Uniswap V4 pool with a custom hook" ([docs.zora.co/coins](https://docs.zora.co/coins)) | **Confirmed**: 1% trading fee on Creator/Content Coins, split across creator/referrer/protocol/LP, with 20% of fees locked as permanent pool depth; Trend Coins run a flat 0.01% fee, 100% to protocol. Anti-snipe tax decays from 99% over the first 10 seconds. | **N/A**, same reason as Clanker — Doppler-protocol seeded liquidity from block one | **not verified** |
| **Believe** | Solana, via Meteora DBC (per third-party bot repos, e.g. `m8s-lab/solana-sniping-bot`) | **not verified from an official source** — believe.app returned HTTP 402 to a plain fetch | **not verified** | **not verified** |
| **Boop** | Solana (inferred — "start ur cult" landing page gave no chain confirmation) | **not verified** — page is logo + tagline only | **not verified** | **not verified** |

The one hard number that *is* this repo's own: of 4,344 launches pulled from DexScreener's feed
since 2026-09-23, Solana is 92%, BSC 5%, Ethereum 2%, Base 1% (`02_findings/memecoins.md`).
That is a sample of one feed over two weeks, not a census, but it is measured, not quoted from
a vendor's marketing page — which is more than most of the launchpad-specific numbers above can
say. Four.meme, Clanker and Zora all wall their actual fee schedules behind JS-rendered app
shells or 403s; Zora is the one exception because its docs are plain static Markdown.

## 2. All-in cost of a $100 and $500 round trip (2026)

Gas is the one line that is cleanly confirmed and the one that most favors leaving Solana:

| chain | gas per swap (confirmed, 2026-10-06) | round-trip gas ($100 or $500, 2 swaps) |
|---|---|---|
| **BSC** | $0.008 at 0.05 Gwei ([bscscan.com/gastracker](https://bscscan.com/gastracker)) | ~$0.016 |
| **Base** | $0.003 at 0.005 Gwei ([basescan.org/gastracker](https://basescan.org/gastracker)) | ~$0.006 |
| **Solana** | priority fee + Jito tip: live tip floor 50th pct 0.0000041 SOL, 99th pct 0.0059 SOL network-wide ([bundles.jito.wtf](https://bundles.jito.wtf/api/v1/bundles/tip_floor), fetched for `docs/briefs/memecoin-sniping.md`); at a contested launch, tips commonly run $0.50–$5 | ~$0.01–$10, size-dependent and spikes hard under contention |

Gas is not the cost that kills a retail round trip on any chain — it's price impact against a
thin pool, and that is dominated by pool depth, not chain. `02_findings/memecoins.md`'s own
cost model (1% venue fee + 0.5% router each way, 2% slippage each way, plus impact =
order ÷ (liquidity ÷ 2) each way) gives **~20% round-trip cost at $100 on the median $3,000
Solana pool, ~45% at $500** — and that model's fee/slippage/impact assumptions were applied
uniformly; this session could not independently confirm four.meme's or Clanker's actual fee
percentage or typical pool depth at first sight, so the same model applied to BSC/Base rows in
the existing panel is **cost-estimated, not independently cost-verified** per the task's own
framing ("gas unmodelled"). What is confirmed is that gas itself — the one line genuinely
chain-specific — is 2–3 orders of magnitude cheaper on BSC and Base than a contested Solana
snipe, and negligible (low cents) compared to the 20%+ venue-fee-and-impact cost that dominates
on all three chains at $100–500 size. BSC and Base do not win on fees or liquidity (neither
confirmed); they win, by a wide and confirmed margin, on the one line that's actually measured.

## 3. Competition: are the same sniper/bundler rings active off Solana?

Yes, demonstrably, though the scale is not symmetric and no chain publishes a measured
"bot share of early buys" the way Solana's genesis-block snipe rate is measured there
(50%+ of pump.fun launches sniped in the creation block, 200+ bots inside the first 500ms —
[Pine Analytics](https://www.bitget.com/news/detail/12560604803448), [Dysnix](https://www.dysnix.com/blog/top-solana-sniper-bot),
both already cited in `docs/briefs/memecoin-sniping.md`). GitHub repo counts, fetched directly
this session, are the only quantifiable proxy found for the other two chains:

- **BSC / four.meme**: a mature, named ecosystem — `HarrierOnChain/Fourmeme-bot` ("Volume &
  Sniper Bot," open-source Rust), `BullyCio43/bsc-fourmeme-bot-copy-trade`,
  `devWorld335/bsc-fourmeme-bot` (explicitly a bundler: "bundle multiple buy transactions into
  coordinated executions... simulating organic participation"), plus a decade-old independent
  PancakeSwap sniper-bot line (`GlavinaNata/Pancakeswap-Sniper-Bot-BSC` and six more hits on one
  search) that predates four.meme and would retarget onto it trivially.
- **Base**: smaller but present — `0xlhc/ClankerSniper`, `harshshukla9/clanker-sniper`,
  `Akshat-cs/Base-sniper-bot`, `Imtiaz9400/eth-base-sniper-bot` (bundles a "Basechain New
  Tokens" scanner). No Zora-specific sniper repo surfaced.
- **Solana**, for scale comparison: the same style of search returns dozens of repos
  specifically for pump.fun, LaunchLab/bonk.fun and Believe/Meteora DBC, several naming
  commercial-grade features (gRPC feeds, multi-wallet bundling) the BSC/Base repos don't claim.

**Reading this honestly**: GitHub repo count is a tooling-maturity proxy, not a bot-share
measurement, and it is *not verified* as proportional to actual early-buy share on any chain.
What it does establish is that "move to BSC/Base to escape the bots" is not supported — bundler
and sniper tooling exists and is openly published for four.meme and Clanker specifically, by
name — only that nobody has published the equivalent of Pine Analytics' genesis-block study for
either chain. The absence of a published number is not evidence of absent competition.

## 4. Wallet PnL distribution per chain

**Not verified for any chain except Solana**, and even there only for pump.fun specifically.
The existing citations in `docs/briefs/memecoins.md` (29.6M wallets, 0.76% ever clear $1,000,
0.0033% clear $100k — [crypto.news/Dune](https://crypto.news/only-0-76-of-pump-fun-wallets-made-1000-or-more-cn-research/))
are Solana/pump.fun-only. No Dune dashboard for four.meme, Clanker, Zora or letsbonk.fun wallet
PnL was located this session — the three Dune protocol pages attempted (four-meme, clanker,
letsbonk) all returned HTTP 403 to a plain fetch (Dune's dashboards are a JS SPA; a plain fetch
cannot render the embedded charts regardless of whether the dashboard exists). This is a real
gap, not a null result: it means no retail trader can currently see their own odds on these
chains the way the Solana literature at least makes legible.

## 5. Rug and scam rates per chain

The one chain-by-chain breakdown found, [Midsummer Meme's Dream (arXiv 2507.01963)](https://arxiv.org/html/2507.01963),
is a **survivor sample** — 31,811 tokens that had already listed and traded for three months,
not all launches, so it cannot be compared directly to Solana's pump.fun-specific "98.6% die
below $1,000 liquidity" headline (that denominator is *all* launches, including instant deaths,
cited in `memecoins.md`). Within its own survivor population (BSC 7,493 of these with price
data, Solana 10,468, Ethereum 2,107, Base 620):

| chain | wash-trading (of chain's survivor n) | pump-and-dump (of chain's survivor n) | LP-inflation manipulation |
|---|---:|---:|---:|
| Solana | 1.75% | 0.52% | 0.11% |
| BSC | 0.69% | 0.04% | 0.15% |
| Ethereum | 1.38% | 0.05% | 0.47% |
| Base | 3.71% | 0.32% | 1.13% |

Solana's *survivors* showed the smallest 3-month median loss (26%, vs Ethereum's worst at
42%); BSC and Base 3-month median returns were not reported in the sections of the paper
reachable this session (**not verified**). Read this table as "which chain's listed tokens get
manipulated," not "which chain is safer to launch on" — Solana's enormous launch volume means
far more tokens never survive long enough to enter this sample at all, so its apparently-lower
wash/pump-and-dump rate here is conditioned on a much harsher upstream filter than Base's.
GoPlus's Security API documents a dedicated Solana endpoint plus a general EVM endpoint that
"appears to" cover BSC/Base/Ethereum together, but the docs page fetched this session did not
itemize per-chain field completeness — **not verified** beyond that generality. No Chainalysis
page with a chain-level pump-and-dump breakdown (as opposed to the existing aggregate 3.6%/
74,037-token 2024 figure already cited in `memecoins.md`) was reachable this session.

## 6. Do GMGN and DexScreener cover these chains the same way?

GMGN: confirmed via its own skills repo ([GMGNAI/gmgn-skills](https://github.com/GMGNAI/gmgn-skills))
that `token` / `market` / `portfolio` / `track` commands work across `sol` / `bsc` / `base` /
`eth` (plus `robinhood` / `arc` / `stable`), and that the risk-field family — honeypot,
`rug_ratio_score`, bundler/sniper/insider-hold rates, wash-trade flag, bonding-curve status —
is described generically rather than chain-gated. Whether every field is actually populated at
the same completeness on a BSC or Base token as on a Solana one is **not itemized in what was
fetched** — the fields exist in the schema; this session found no per-chain null-rate audit.
DexScreener's API reference, fetched directly, documents token/pair endpoints with liquidity,
volume, price-change and boost fields but the reachable excerpt did not enumerate a chain list
or confirm field parity across chains — **not verified** beyond DexScreener's general-purpose,
multi-chain reputation. Neither vendor's own docs state a BSC/Base-specific gap, but neither
states parity either; this is an open question, not a closed one.

## Verdict

**Measure BSC (four.meme) next, not Base, and not instead of the Solana recorder already
running.** Three things point there and nowhere else: (1) it is the only chain besides Solana
with a confirmed, mature, named sniper/bundler tooling ecosystem (§3), meaning its competitive
dynamics are at least structurally comparable to what's already measured on Solana rather than
an unknown; (2) its one hard cost number — gas at $0.008/swap, confirmed from BscScan today —
removes the single confirmed chain-specific cost line almost entirely, leaving venue fee and
pool depth (both currently unconfirmed for four.meme) as the only open questions a recorder can
actually answer; (3) it already produced this repo's best surviving-cost cell (71–87 trades,
+15–19% net at 1h, hit 0.36–0.39, positive in both weeks) on a sample explicitly flagged as too
small and gas-unmodelled — and gas turns out, now that it's measured, not to be the missing
piece. Base's Clanker/Zora row (+50%, n=25) is the more extreme number but rests on fewer
trades, and more of its mechanics (fee %, pool seeding depth) are confirmed-unknown than BSC's.
letsbonk.fun is not a reason to leave Solana — it is Raydium LaunchLab, same chain, same gas
profile, same (or a sibling) bot ecosystem as pump.fun; it's a second venue to record, not a
different cost environment.

**What a four.meme recorder needs, specifically:** (1) the actual platform + router fee and
typical first-sight pool depth, pulled from on-chain data rather than the walled docs, so the
cost model stops inheriting pump.fun's $3k-median-pool assumption unverified; (2) a repricing
cadence dense enough in the first 10 minutes to catch the BSC equivalent of genesis-block
sniping, since nothing here confirms four.meme's snipe timing matches Solana's; (3) the same
creator-history and bundler fields GMGN already exposes generically (§6), joined per-token so
the BSC rows can be scored the same way `memecoin_factors.py` scores Solana; (4) enough volume
to clear 60 sessions before anything is treated as a result — the current 71–87-trade BSC cell
is `study_guard`-sized for nothing yet.

No repository files were changed; nothing to verify.
