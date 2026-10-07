<!-- research brief, filed 2026-10-06; agent output verbatim. Companion to docs/briefs/memecoins.md
     (launch base rates), memecoin-sniping.md (sniper latency ladder) and memecoin-data-stack.md
     (vendor API pricing, confirmed 2026-10-06) — this brief is narrowly about copying GMGN-labeled
     "smart money" wallets after the fact, not running your own sniper bot. Verdicts belong in
     02_findings/ if anything here is acted on. WebSearch was unavailable this session (budget
     exhausted) — everything below is either fetched directly from a primary URL or marked
     "not verified". -->

# Copy-trading GMGN "smart money" wallets as a retail strategy (2026)

This sits under `docs/briefs/memecoins.md` (base rates: median 24h return −64%, 1-in-100
launches pay 7x+) and `memecoin-sniping.md` (the latency ladder: slot-0 landing needs <35ms
co-located gRPC; a retail WebSocket runs 150-300ms). The question here is narrower: instead of
sniping launches yourself, you follow a wallet GMGN has already labeled a winner and copy its
trades. **Research note: this session's WebSearch quota was exhausted before any query ran, so
everything below came from direct WebFetch on primary URLs (GMGN's own docs, vendor pricing
pages, two blog write-ups of a real sniper bot) plus Bing's result snippets, which mostly
returned off-topic noise for crypto-specific queries. Several asks in the brief (Dune PnL
dashboards for copy-trading specifically, Nansen/Arkham ROI claims, a dedicated academic paper
on copy-trading, exact fee percentages for Photon/BullX/Trojan/Axiom) could not be located this
way and are marked "not verified" rather than filled in from memory.**

## 1. What GMGN's labels mean, and how they're computed

Fetched directly: [docs.gmgn.ai](https://docs.gmgn.ai)'s own "[Track Smart Money](https://docs.gmgn.ai/index/track-smart-money.md)"
page says only "GMGN has big data on smart money, after follow smart money, you can receive
real-time trading dynamics of smart money" — no threshold, lookback window, or minimum trade
count is published. The "[GMGN Sniper Bot](https://docs.gmgn.ai/index/gmgn-tg-sniper-bot-sol.md)"
page defines no criteria for what makes a wallet a "sniper" either; it only documents the bot's
own slippage modes (auto / turbo / anti-MEV) and a configurable priority fee, with "turbo mode"
traded off against "anti-MEV RPC," which it says is "slightly slower." **GMGN does not publish
its labeling methodology anywhere I could reach.** That itself is a finding: unlike Nansen,
which sells manually-curated entity labels, GMGN's "smart money," "KOL," "sniper," and "fresh
wallet" tags are presented as algorithmic outputs with no disclosed formula, no audit, and no
way for a user to verify a tag is still accurate.

What is independently confirmable about the underlying behavior: [Pine Analytics, via
BlockBeats](https://www.bitget.com/news/detail/12560604803448), measured 15,000+ pump.fun
launches and found over 50% sniped in the genesis block by 4,600 wallets funded by 10,400
deployer wallets — 87% of those snipes were profitable, 55% exited within 1 minute, 85% within
5. That is almost certainly the population GMGN's "sniper" tag is pointing at: wallets whose
edge is literally being first, not trading skill that transfers to a follower. "Fresh wallet"
in this industry's general usage (confirmed by [Solidus Labs](https://www.soliduslabs.com/reports/solana-rug-pulls-pump-dumps-crypto-compliance),
which documents "developer-associated background checks" and "influencer and KOL tracking" as
a compliance-tooling category, though without GMGN specifics) means a wallet with no or minimal
prior history — used by snipers and insiders specifically because it carries no reputation to
flag. "KOL" is industry shorthand for a wallet tied to a public crypto-influencer identity, a
manual/community link rather than an algorithmic one. None of this is GMGN confirming its own
math; it's the surrounding ecosystem's known behavior patterns that the labels most likely
describe.

## 2. Copy-trading mechanics and latency

Confirmed by fetching GMGN's own fee page via search snippet: **GMGN charges 1% on trade
value**, consistent with the platform's general reputation as "Trades Cost 1%." Mechanically,
every copy-trading tool in this category — GMGN, Photon, BullX NEO, Trojan, Axiom, Banana Gun —
has to *see* the leader's transaction land on-chain before it can mirror it; there is no way to
act earlier, because these tools watch a public wallet's confirmed activity, not its intent.
[Dysnix's sniper-bot latency ladder](https://www.dysnix.com/blog/top-solana-sniper-bot) (built
for launch-sniping, but the physics is identical for copy-trading) puts total round-trip time
at 430-680ms for an amateur RPC setup, 140-270ms mid-tier, and ~50ms for co-located production
infrastructure, with first-10-transaction confirmation rates of 22% / 58% / 92% respectively.
A retail copier running GMGN's web app or a Telegram bot sits at the amateur-to-mid tier: by the
time the copy fires, the leader's fill is already a confirmed past event and at least one more
Solana slot (~400ms) has usually passed, often several as the bot detects, decides, and submits
its own transaction with its own priority fee / Jito tip competing for block space.

**The front-running problem is concretely documented, just not under the word "front-running."**
[mikem.codes' reverse-engineering of the orcACR sniper bot](https://www.mikem.codes/if-you-aint-first-youre-last-2/)
— the same wallet type GMGN would likely tag "smart money" or "sniper" given its ~100-200
SOL/day profile — describes "copy-block trades," where the bot enters a position and exits
around 20 seconds later **regardless of whether the wallet it was trading alongside had sold**.
The post is explicit that the strategy "relied solely on data from the initial mint instruction,
as any other method would be too slow." A retail copier watching that wallet through GMGN would
need to detect the buy, decide to copy, and get a transaction landed, inside that ~20-second
window, competing against 150-680ms of its own latency plus its own slippage and tip — and even
a successful copy buys *after* the move the leader was capturing and sells into a price the
leader already exited. This is the mechanism: the "smart money" edge is being first, and a
copier is structurally never first. Costs stack on top: GMGN's 1% each way, slippage (GMGN's
own "auto/turbo" settings imply it's routinely non-trivial on thin pump.fun liquidity — this
repo's own pump.fun recording found ~7% one-way price impact on a $100 order against a median
$3,000 pool, in `02_findings/memecoins.md`), and a priority fee or Jito tip to land the copy
transaction at all during the exact burst of activity that triggered the signal. **Exact
latency and fee numbers for Photon, BullX, Trojan, and Axiom specifically — not just the general
Solana-bot physics above — could not be confirmed this session; their app domains returned
403s to direct fetch and search snippets for them returned unrelated results. Not verified.**

## 3. Published measurements of copy-trade (and underlying wallet) returns

No source found this session publishes a return distribution for *copying* a smart-money
wallet specifically (i.e., the copier's P&L net of latency and fees, as opposed to the
leader's). What is published is the underlying population's P&L, which upper-bounds any
copier's result since the copier can only do worse:

- **[crypto.news, citing a Dune dashboard](https://crypto.news/only-0-76-of-pump-fun-wallets-made-1000-or-more-cn-research/)**, Aug 2024: 29.6M wallets, 37.6% profitable, only 0.76% ever made $1,000+, 0.046% $10k+, 0.0033% $100k+.
- **[Cointelegraph, citing Dune](https://cointelegraph.com/news/pump-fun-crypto-traders-majority-do-not-realize-profits-dune-data)**, Jan 2025: 13.55M wallets, 0.412% above $10k, 293 wallets (0.00217%) above $1M.
- **[CoinGecko](https://www.coingecko.com/research/publications/pump-fun-traders-are-making-a-comeback)**, May 2026: realized-profit share rose from 30-45% (Feb-Dec 2025) to 57-73% (Feb-Apr 2026) — on realized trades only, and 65% of winners made $1-$500, i.e. the improvement is mostly tiny wins, not better big trades.
- **[Lookonchain, via TradingView](https://www.tradingview.com/news/cointelegraph:8e276a1b6094b:0-suspected-insider-wallets-net-20m-on-solana-s-focai-memecoin-launch/)**: 15 wallets turned $14,600 into $20M on one launch (Focai) — the kind of wallet a "smart money" scraper would flag after the fact, from a sample size of one event, with the obvious reading that these are the deployer's own wallets, not repeatable skill.
- **No Dune dashboard, Pine Analytics report, Chainalysis publication, Nansen blog post, or Arkham claim specifically measuring copy-trade or smart-money-follower returns was located. Not verified** — this is the single biggest gap in the public record on this topic as far as this session's tools could reach.

**Decay after listing is a logical certainty given the mechanism in §2, not an independently
measured number.** If a wallet's edge is "first into every launch," publicizing it (via a
GMGN/Nansen smart-money tag) adds followers who buy right after it, which — per the
copy-block pattern above — the original wallet has every incentive to sell into. I could not
find a published before/after study quantifying this decay for any named wallet. **Not
verified as a measured figure; verified only as the mechanically expected direction.**

## 4. Known scams built on copy-trading

- **Wash trading / fake PnL as a broader pattern**: [arXiv 2507.01963](https://arxiv.org/html/2507.01963) found that of 707 tokens that gained >100% over three months, 82.8% showed wash trading, LP inflation, or holder concentration — the same mechanisms that would fabricate a wallet's apparent track record if applied to a wallet's own trade history rather than a token's chart.
- **Bundled wallets**: [arXiv 2602.13480 (MemeTrans)](https://arxiv.org/html/2602.13480v1) found 28% of holders on migrated tokens were bundled wallets controlling 36.5% of supply — the same tooling (many wallets controlled by one actor, trading against each other) that would let an operator manufacture a "winning" wallet to advertise for copy-trading by routing profitable fills to it and losses elsewhere.
- **Fake-bot drainer scams** (adjacent, not copy-trading itself but same audience): [TRM Labs](https://www.trmlabs.com/resources/blog/fake-ai-trading-bots-are-getting-victims-to-build-their-own-drainers) documented 310k YouTube views across fake "build your own trading bot" tutorials that got 224 victims to compile a drainer contract themselves, stealing 274.6 ETH (~$517k). [Scam Sniffer](https://drops.scamsniffer.io/over-4-million-stolen-by-multiple-solana-wallet-drainers/) documents Solana wallet-drainer-as-a-service operations at scale.
- **No source found this session specifically documenting a "fake smart-money wallet sold as a copy-trading signal" scam on GMGN by name.** Given bundled-wallet tooling is confirmed to exist and be used at scale (above), and GMGN's labeling criteria are undisclosed (§1), the scam is structurally easy to run; **a named, documented instance is not verified**.

## 5. What it would take to measure this ourselves

`docs/briefs/memecoin-data-stack.md` (filed same day) already fetched vendor pricing directly
and is the authority here; summary relevant to wallet-level work:

| source | wallet trade history | confirmed pricing/limits |
|---|---|---|
| **Helius** | Enhanced Transactions API parses a wallet's full tx history (walk `getSignaturesForAddress`); Parsed Events API free on paid plans through Sep 2026 (beta) | Free: 1M credits/10 RPS. Dev $49: 10M credits/50 RPS. Business $499: 100M/200 RPS. Pro $999: 200M/500 RPS. [Pricing](https://www.helius.dev/pricing) |
| **Solscan Pro** | `account transactions (enhanced)`, `account defi activities`, `account portfolio` endpoints exist | Free tier exists for some endpoints; paid-tier numbers not resolved on direct fetch — **not verified** |
| **Bitquery** | Per-tx DEX trades with wallet/amount/slot | Personal $29 (100k pts, 30/min), Pro $69 (1M pts, 90/min), Scale $199 (5M pts, 240/min) — confirmed in memecoin-data-stack.md |
| **Birdeye, Shyft** | Both advertise wallet-portfolio / trade-history endpoints in nav | Pricing pages 404'd/redirected on direct fetch both sessions — **not verified** |

None of these give a *copier's* realized fill — they give the leader's on-chain trade. Measuring
copy-trading specifically requires simulating the copier's execution against the pool state
some latency Δ after the leader's confirmed slot (the same executable-price-simulation approach
`02_findings/memecoins.md` already built for launch-sniping), sweeping Δ from 150ms to 3s to
find where the edge, if any, disappears.

## Verdict table

| strategy variant | best documented return | sample size | who measured it | latency needed | retail $5k verdict |
|---|---|---|---|---|---|
| Copy a GMGN "smart money"-tagged wallet, GMGN web/Telegram | none published for the *copier* | 0 (no copy-trade study found) | — (not verified) | <1s to not lose the whole move; confirmed infra ladder needs ~50ms-680ms, retail sits at the bad end | **Reject.** No positive-EV study exists; the underlying wallets' edge (being first) is structurally non-transferable to a follower (§2's copy-block mechanism) |
| Copy a genesis-block "sniper" wallet | 87% of snipes profitable, but that's the *leader's* return, exiting within 1-5 min | 15,000+ launches, 4,600 wallets | [Pine Analytics/BlockBeats](https://www.bitget.com/news/detail/12560604803448) | sub-second; a copier arrives after 55-85% of these positions are already closed | **Reject.** The number is unreachable by anyone watching the wallet rather than running the same first-block infrastructure |
| Follow raw "smart money" wallet population, unfiltered | 0.76% of all wallets ever clear $1,000 lifetime | 29.6M wallets | [Dune via crypto.news](https://crypto.news/only-0-76-of-pump-fun-wallets-made-1000-or-more-cn-research/) | n/a (this is the underlying population, not a copy-trade result) | **Reject.** Even picking a winner from this pool after the fact (survivorship) says nothing about its forward return once followed |
| Treat a "KOL"-tagged wallet as a signal | no public ROI figure | — | — (not verified; Nansen/Arkham claims not located) | n/a | **Reject** for lack of any measured number, pending verification |

**Bottom line for $5,000:** every piece of this that is independently measurable (sniper exit
speed, wallet-population win rates, GMGN's own non-disclosure of its labeling math, the
copy-block pattern in a real reverse-engineered bot) points the same direction — the label is
describing speed and position in a race the copier isn't running. No source located this
session, including Dune, Pine Analytics, Chainalysis, or academic work, publishes a positive
net-of-cost return for *copying* a tagged wallet after the fact. Consistent with the rest of
this repo's memecoin findings (`02_findings/memecoins.md`: −49% to −66% net on buying any
launch at $100-500), the honest label for this strategy today is **unmeasured and mechanically
unfavorable**, not merely "not yet profitable" — there is no published study to point to even
as a counter-example.
