<!-- research brief, filed 2026-10-06; agent output verbatim. Companion to docs/briefs/memecoins.md
     (graduation rates, sniper-economics overview, rug-detection accuracy) — this brief goes deeper
     on the infrastructure stack, bundle/dev-wallet detection tooling, and 2026 pump.fun fee mechanics
     that memecoins.md did not cover. Verdicts belong in 02_findings/ if anything here is acted on. -->

# Launch sniping, bundle detection and dev-wallet analysis on pump.fun (2026)

This is the infrastructure-and-tooling layer under `docs/briefs/memecoins.md`, which already
covers graduation rates (0.2–0.63%, falling), sniper economics (slot-0 landing, Jito tips,
fixed-hold PnL) and rug-detector accuracy (LROO, MemeTrans) at the top level. Here: what the
actual winning stack is built from, how bundle/dev-wallet detectors work and what they measure,
and whether any of it reaches a retail machine.

## 1. The sniper stack

**Detection latency is the whole game, and it is a ladder of paid infrastructure.** A Solana
validator produces a block every ~400ms; being in the genesis block or the next one is the
entire edge, because [Pine Analytics](https://www.bitget.com/news/detail/12560604803448)
found 50%+ of pump.fun launches are sniped in their creation block by the deployer's own
wallets, who then exit into you. [Dysnix](https://www.dysnix.com/blog/top-solana-sniper-bot)
measured 200+ competing bots inside the first 500ms of a typical launch, funnelling into
roughly 10 profitable exits — the rest lose the race. [RPC Fast](https://rpcfast.com/blog/how-to-launches-snipe-pump)
puts hard numbers on the ladder: co-located gRPC (Geyser) at <35ms lands slot 0 ~89% of the
time; a generic cloud RPC at ~220ms lands it <20%; a plain WebSocket subscription runs
150–300ms; polling an RPC endpoint for new accounts runs 100–500ms. Slot 0 vs slot 2 entry is
a 20–60% difference in curve price, because pump.fun's bonding curve moves fastest near its
~30 SOL virtual-reserve starting point (`initial_virtual_sol_reserves = 30_000_000_000`
lamports, confirmed directly from the `Global` account via the
[pump-fun/pump-public-docs](https://github.com/pump-fun/pump-public-docs) repo).

Geyser/gRPC (offered by Helius, Triton, Shyft, QuickNode) is a direct stream of validator
account-update events pushed to a subscriber, skipping the RPC layer's polling/subscription
overhead entirely — that's the structural reason it beats both WebSocket and polling, though
none of the vendor docs I could reach ([helius.dev](https://www.helius.dev), `docs.jito.wtf`)
publish a formal gRPC-vs-WebSocket latency table; the RPC Fast and Dysnix numbers above are the
only quantified comparison found, and RPC Fast sells the service it's measuring — **treat the
specific percentages as directional, not independent-lab-verified**.

**Jito bundles are how you pay to jump the free-for-all.** A bundle is an atomic set of
transactions submitted to Jito's block engine with a tip; bundles compete against each other
purely on tip size inside 50ms auction windows, grouped by which accounts they touch
([Jito docs](https://docs.jito.wtf/lowlatencytxnsend/)). The documented minimum tip is 1,000
lamports (~$0.0002), but Jito's own guidance for `sendTransaction` recommends splitting your
total budget 70/30 between priority fee and tip. Jito's docs explicitly do **not** publish a
landing-rate percentage — they describe the auction mechanism and tell you to look at the
live tip floor instead. I queried that live: `bundles.jito.wtf/api/v1/bundles/tip_floor`
returned (2026-10-06, snapshot, moves continuously): 25th pct 0.0000023 SOL, 50th pct
0.0000041 SOL, 75th pct 0.00001 SOL, 95th pct 0.0011 SOL, 99th pct 0.0059 SOL. That's the
*network-wide* floor across all bundle traffic, not launch-specific — the existing
`memecoins.md` brief's figure of 0.001–0.01 SOL for an ordinary snipe and 0.01–0.1 SOL for a
contested launch sits just above the 95th/99th percentile shown here, consistent with "pay
above the ambient floor to win a specific launch." OpenLiquid's vendor numbers (same brief)
put effective cost per *winning* snipe at $2.65–$7.75 after tips, fees and failed-transaction
burn — before counting the 60–80% of snipes that lose outright, which the same vendor admits
to.

**Cost per attempt, concretely:** priority fee + tip (often $0.50–$5 at contested launches) +
1% pump.fun protocol fee each way + curve slippage (several percent on a $100–500 buy against
30 SOL virtual reserves) + a non-trivial chance the transaction simply doesn't land and the
fee is still partially burned. None of this is optional infrastructure spend — co-located
gRPC services bill monthly ($100s–$1,000s) regardless of whether you win a given block.

## 2. Bundle detection

"Bundling" at launch means multiple wallets buy in the same atomic transaction or the same
Jito bundle, used by the deployer to scoop supply before public buyers can react, often
disguised as organic early demand. **[Trench.bot](https://trench.bot)** runs a "Bundle
Scanner" that flags wallets purchasing within the same ~0.4s block (one Solana slot) and
reports the supply share involved, wallet count, and what those wallets still hold; it also
ships a bubble-map visualizer at `trench.bot/bundles`. **GMGN's API** (confirmed via the
official [GMGNAI/gmgn-skills](https://github.com/GMGNAI/gmgn-skills) repo, 599 stars,
pitched as "500+ professional data dimensions") exposes this as discrete fields rather than a
single badge: `bundler_trader_amount_rate` (volume share from bundled/bot buys),
`sniper_count` (wallets that bought in the launch slot), `rat_trader_amount_rate` (insider/
sneak-wallet volume share), `fresh_wallet_rate`, `suspected_insider_hold_rate`, and a
`rug_ratio_score` plus honeypot and wash-trade flags. These are the literal fields behind the
"bundle %" badge GMGN's UI shows on a token card. A smaller open-source scanner,
[pumpscan](https://github.com/yksanjo/pumpscan) ("paste a mint, get a verdict in 15 seconds"),
packages the same idea — bundler detection, holder concentration, dev-wallet status — as a
single lookup.

**The measured outcome, from [MemeTrans (arXiv 2602.13480)](https://arxiv.org/html/2602.13480v1):**
across their labelled post-migration set, 28.13% of holders are bundled accounts holding
36.50% of total supply. Critically, bundle concentration is not noise: comparing their
risk-labelled tiers, bundle-adjusted median holding percentages run 24 points higher on
high-risk tokens, 9 points higher on medium-risk, and 6 points higher on low-risk than the
raw (non-bundle-adjusted) figures — bundling specifically inflates the apparent diffuseness of
ownership on the tokens that go on to perform worst. Separately, their temporal-convolutional
classifier for recurring sell-buy wash cycles (a related but distinct manipulation signature)
hit ~90% accuracy against 1,555 hand-labelled tokens, and among *pre-migration* transactions
generally, 21.4% were wash trades. No source I found publishes a clean "bundled token price
return vs non-bundled token price return at fixed hold" comparison — the bundle fraction is
used as an input feature to a risk score, not reported as its own forward-return cut, so
**this exact comparison is not verified** as a standalone number; the closest proxy is the
risk-tier concentration delta above.

## 3. Dev-wallet reputation

Pump.fun's on-chain program tracks a `creator` pubkey directly on the `BondingCurve` account
(confirmed in `pump-public-docs`), so creator-history tooling is a straightforward lookup
against that address across all its prior mints — no inference required, unlike bundle
clustering. [MemeTrans](https://arxiv.org/html/2602.13480v1) found "almost all" developers
buy in the same transaction as minting (pre-acquiring at the floor price tier by
construction), and that the first 10 buyers on high-risk tokens hold 17–19 percentage points
more supply than on low-risk tokens — the earliest wallets, disproportionately
insider/bundled, are the tell. The largest creator-history study,
[Kamat (arXiv 2607.02823, v4)](https://arxiv.org/abs/2607.02823v4) on 832,941 launches, found
an initial market cap above 30 SOL carries a graduation hazard ratio of 4.51 and that social
presence (Telegram, or all three of Telegram/X/website) raises graduation odds 8.9x and 17.5x
respectively — both correlate with a repeat, better-resourced deployer rather than a one-shot
scammer, though the paper's own corrigendum ([Zenodo v1.3](https://zenodo.org/records/21908375))
downgrades its predictive model to AUROC 0.46 out-of-sample, so **treat any single-feature
story about creator history predicting graduation as unconfirmed at scale**. The
reverse-engineered [orcACR bot](https://www.mikem.codes/if-you-aint-first-youre-last-2/) — the
one documented profitable retail-adjacent operation in `memecoins.md` — explicitly skips
creators with prior tokens, creators whose first buy exceeds 4 SOL, and creators funded by
other creators, which is a dev-wallet reputation filter used live rather than just measured
in a paper, and the one piece of evidence that filtering on it has positive expected value
(the bot nets ~100–200 SOL/day) — though its P&L is reverse-engineered from on-chain activity,
not vendor-disclosed, so **treat the profit figure as estimated, not audited**. I found no
dedicated "serial deployer" scoring product (no GitHub repo, no paper) separate from the
bundle/holder tools above — GMGN's `suspected_insider_hold_rate` and pumpscan's "dev wallet
status" field are the closest productized versions, and neither publishes the underlying
history logic. "Dev sold" push alerts are a standard Photon/BullX/GMGN front-end feature
(watch the creator address for an outbound sell from the vault or their holding wallet) but I
could not find written documentation of the detection logic or a measured false-positive rate
for any vendor — **unverified** beyond the feature existing.

## 4. Rug detection heuristics

The field's standard check-list, confirmed via the GitHub descriptions of multiple independent
rugcheck.xyz API wrappers (e.g. [aethernet404/rugcheck](https://github.com/aethernet404/rugcheck):
"0-100 rug risk score: mint authority, freeze authority, holder concentration, creator"), is:
mint authority retained (creator can print more supply), freeze authority retained (creator
can freeze your wallet), LP burned/locked status, top-10/top-20 holder concentration, and
sniper/bundle wallet share. GoPlus's Solana token-security API covers the same family of
checks but its specific field list could not be fetched (docs page unreachable this session).

**Published precision/recall is thin and inconsistent across tools.** [LROO (arXiv 2603.11324)](https://arxiv.org/html/2603.11324v1)
is the only paper that benchmarks named incumbents on a shared 1,000-token hand-labelled EVM
set: LROO ~60% accuracy, FORTA ~60%, CRPWarner ~20% — RugCheck, TokenSniffer and GoPlus
themselves are described only as "heuristic rule sets" with no disclosed accuracy; the paper
does not evaluate them directly, only cites them as the commercial category. LROO's own
TabPFN model claims 98.2% accuracy / 0.982 F1 / 0.997 ROC-AUC on that same small EVM set (1
false negative, 1 false positive total) — note this is EVM, not Solana, and the test set is
tiny. The best Solana-specific number remains `memecoins.md`'s citation of MemeTrans:
precision 0.85 / recall 0.83 for "high risk" on *post-migration* tokens, with an 84% base
rate of high-risk among survivors — meaning a detector that lets through 15% of migrations
still passes a thin, adversarially-selected residue. **No benchmark exists for pre-migration
(bonding-curve-stage) rug prediction**, which is the stage a sniper actually needs it for —
every published number scores tokens that already survived long enough to be labelled.

## 5. The sub-minute curve scalp

Buying early on the curve and selling into the first wave of demand is the only timeframe
where a non-insider retail trader could theoretically compete, because it doesn't require
beating the genesis-block snipers — it requires beating the *next* 30–120 seconds of buyers.
The only public fixed-hold dataset, [Money Leaves Clues](https://moneyleavesclues.substack.com/p/inside-the-economics-of-pumpfun-call)
(770 call-channel picks, already a favourably pre-selected sample, cited in full in
`memecoins.md`), shows why it still doesn't work at retail speed: a realistic 15-second entry
nets median +0.2% at 30 seconds, then goes negative — −6.2% at 1 minute, −10.5% at 5 minutes.
An "instant" (unrealistic, zero-latency) entry averages +552% at 30 seconds but has a median
of −4.0%, meaning the average is entirely carried by a small number of extreme winners that
no retail-latency trader lands. No separate "first-minute buyers" PnL dashboard beyond this
substack post was found. **Pump.fun's 2026 mechanism changes relevant to this trade**
(confirmed directly from commit history and raw doc files in `pump-fun/pump-public-docs`):
the flat 1% protocol fee (`fee_basis_points = 100`) was supplemented by a market-cap-tiered
dynamic fee schedule rolled out September 2025 (predates this brief's 2026 window but still
governs current fees — tiers are set by an on-chain `FeeConfig`, not a flat rate, and the
exact tier table is image-only (`fees.png`), not machine-readable in the repo). In 2026
specifically: a creator-fee mechanism shipped (May 2026, "coin creator fee" docs/examples)
charging an additional per-trade fee routed to a `creator_vault` PDA; "cashback" coins (which
routed the creator fee to buyers as a rebate) were **deprecated in September 2026** and
replaced by "holder rewards" coins, where the creator fee is instead distributed to
whoever currently holds the token rather than refunded to the trader who generated it or
paid to the creator. Net effect for a scalper: an extra fee layer exists on top of the 1%
protocol fee on recent coins, it is not disclosed anywhere except the coin's on-chain config,
and it no longer flows back to the buyer by default — a strict tightening of round-trip cost
versus the mechanics `memecoins.md`'s cost model assumed (1% + 0.5% router each way).

## 6. Volume bots, wash trading and trending manipulation

GMGN's API ships an explicit wash-trade flag and `rug_ratio_score` alongside the bundle fields
above (same [GMGNAI/gmgn-skills](https://github.com/GMGNAI/gmgn-skills) source), confirming
wash-trade detection is productized, not just academic — but the detection logic itself is
not published, only the output field. The strongest measured numbers on how much of the
visible tape is manufactured: MemeTrans's 21.4% wash-trade share of pre-migration transactions
and ~90% classifier accuracy for detecting sell-buy manipulation cycles (above); and, from the
companion `memecoins.md` brief's existing citations, [Midsummer Meme's Dream (arXiv 2507.01963)](https://arxiv.org/html/2507.01963)
found that of 707 tokens that gained over 100% in three months, 82.8% showed wash trading, LP
inflation or concentration red flags — i.e. the big "winners" DexScreener/GMGN trending lists
surface are disproportionately the manufactured ones. No Dune dashboard quantifying "% of
currently-trending tokens showing wash-trade signatures" in real time was located this
session (not verified). The practical detection method available to a retail trader without
a paid feed is indirect: cross-check a token's DexScreener volume against its GMGN
`bundler_trader_amount_rate`/`rat_trader_amount_rate` and wash-trade flag, or against
holder-count growth — genuine demand grows unique buyer count, wash trading inflates volume
without moving holder count.

## Verdict table

| tactic | latency/infra needed | documented edge | who measured | reachable from retail setup |
|---|---|---|---|---|
| Genesis-block/slot-0 snipe | co-located gRPC (Geyser), <35ms, $100s–$1,000s/mo | 89% slot-0 landing at co-location vs <20% generic cloud; 87% of deployer-wallet snipes profitable, but that's the deployer's own book | RPC Fast, Dysnix, Pine Analytics | No — infra cost and you're racing the deployer's own wallets, not other outsiders |
| Jito-bundle priority landing | Jito tip (0.001–0.1+ SOL contested) + fast RPC | No published landing-rate %; live tip floor 95th/99th pct ≈0.0011/0.0059 SOL network-wide | Jito docs, bundles.jito.wtf (live query) | With X — pay well above the live 99th-pct floor at a hot launch, no guarantee |
| Bundle detection before buying | GMGN/trench.bot lookup, free–cheap | 28% of holders / 36.5% of supply bundled on average; +24pp concentration on high-risk tokens specifically | MemeTrans (arXiv 2602.13480), trench.bot, GMGN fields | Yes — free API/UI lookups, use as a pre-trade filter, no latency need |
| Dev-wallet/creator-history filter | On-chain lookup of `creator` pubkey history, free | orcACR's live filter (skip repeat/funded creators) nets ~100–200 SOL/day (unaudited); Kamat's hazard ratios directionally support it but model AUROC fell to 0.46 out-of-sample | mikem.codes (orcACR writeup), Kamat arXiv 2607.02823 v4 | Yes to build, no confirmed edge at scale |
| Rug heuristic screen (mint/freeze authority, LP burn, holder %) | RugCheck/GoPlus API, free | No disclosed precision/recall from RugCheck/GoPlus; best proxy (MemeTrans, post-migration) precision 0.85/recall 0.83 on an 84% base rate; zero benchmarks pre-migration | LROO arXiv 2603.11324, MemeTrans arXiv 2602.13480 | Yes to run, no — doesn't cover the stage you'd trade on |
| Sub-minute curve scalp | Fast RPC/websocket, 15s+ entry realistic | Median +0.2% at 30s then negative (−6.2%/−10.5% at 1/5 min) on a favourably pre-selected sample; mean is a small-n tail | Money Leaves Clues (Substack, 770 picks) | No — negative median even on a cherry-picked sample |
| Wash-trade/trending-manipulation filter | GMGN API flags, free | 21.4% of pre-migration txns are wash trades; 82.8% of 3-month 100%+ gainers show manipulation signatures | MemeTrans, Midsummer Meme's Dream (arXiv 2507.01963) | Yes — use as an exclusion filter, doesn't require speed |

## Bottom line

Every piece of this stack that creates genuine edge (genesis-block landing, bundle
construction, serial-deployer exits) is either the deployer's own wallet or requires
co-located infrastructure spending that dwarfs a $5,000–$50,000 retail bankroll before a
single trade. Every piece that *is* reachable for free (bundle %, dev-wallet history, rug
heuristics, wash-trade flags) is a **filter, not a strategy** — it screens out bad trades,
it does not manufacture a good one, and none of the published studies show a positive
expected-value rule built purely from these free signals at the sub-minute horizon a sniper
needs. This is consistent with `02_findings/memecoins.md`'s measured verdict on this repo's
own 4,344-launch panel: momentum and visibility factors (the very things GMGN/DexScreener
surface) carry a *negative* IC at every horizon, and the one filter that nets positive
(age > 60 min AND liquidity ≥ $20k) explicitly throws away the sub-minute entry this brief
was asked to evaluate.
