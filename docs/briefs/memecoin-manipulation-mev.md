<!-- research brief, filed 2026-10-06; agent output verbatim. Sibling to docs/briefs/memecoin-sniping.md
     (infra/latency/bundle-detection layer) and docs/briefs/memecoin-who-profits.md (who captures the
     money, at the wallet-cohort level). This brief is narrower: it isolates the two things a retail
     bot's feature set mistakes for organic signal — manufactured trending/volume, and MEV extraction —
     and asks whether either survives contact with costs. Verdicts belong in 02_findings/ if acted on. -->

# Manufactured momentum and MEV: what a retail bot reads as signal that isn't

A retail scanner watching DexScreener trending, GMGN's hot list, or pump.fun's board sees three
numbers it treats as demand: volume, buyer count, rank. All three are gameable by the people
selling into the scanner, and a fourth cost — MEV — sits on top of every fill regardless. This
brief traces each mechanism to a primary source and states plainly where no study exists yet,
rather than filling the gap with a plausible-sounding guess.

## 1. Volume bots and trending manipulation

DexScreener's own documentation does not hide the mechanism, it just doesn't quantify it.
[Trending](https://docs.dexscreener.com/trending.md) lists volume, liquidity, transactions,
unique makers, holders, page visitors and "community reactions" as inputs, then states "we keep
the special blend of our algorithm close to our chest" — no disclosed wash-trade filter, no
disclosed weighting. [Boosting](https://docs.dexscreener.com/boosting.md) and its
[terms](https://docs.dexscreener.com/privacy/boosting-terms-and-conditions.md) confirm boosts
are bought in packs lasting 12–24 hours, raise a token's "Trending Score," and at 500+ concurrent
boosts unlock a gold "Golden Ticker" badge — while explicitly disclaiming that "purchasing
Boosts does not guarantee that a token will trend or achieve a specific rank." Pricing itself is
not published in the docs (third-party reports of ~$300/24h exist but are **not verified** here).

Critically, GMGN's own API — confirmed from the field list in the public
[GMGNAI/gmgn-skills](https://github.com/GMGNAI/gmgn-skills) repo — ships this as machine-readable
fact rather than UI chrome: `dev.dexscr_ad` (bought a DexScreener ad), `dev.dexscr_boost_fee`
(paid for a boost), `dev.dexscr_update_link` (updated socials, a common pre-pump move),
`dev.dexscr_trending_bar` (literally: did this token appear in the trending bar). A retail bot
can poll these and know a token's visibility was purchased, which the trending page itself will
not tell you.

**The measured wash-trade share rises exactly as you filter toward "trending."** Three papers,
three different selection criteria, same direction: [arXiv 2609.10246](https://arxiv.org/abs/2609.10246)
(15M pump.fun tokens, full history) finds 17% of *all* trades are wash trades under its most
conservative atomic heuristic (WT1) — explicitly stated as a lower bound.
[MemeTrans (arXiv 2602.13480)](https://arxiv.org/html/2602.13480v1) finds 21.4% of
*pre-migration* transactions are wash trades — a tighter, earlier-stage slice, already higher.
[Midsummer Meme's Dream (arXiv 2507.01963)](https://arxiv.org/html/2507.01963) looked at the
slice that actually matters for a trending list — the 707 tokens that posted >100% three-month
returns — and found 586 of them (82.9%) show wash trading, "Liquidity Pool-Based Price
Inflation," or concentration anomalies (287 wash-trading, 40 LPI, 412 concentration specifically).
That paper states the mechanism in its own words: wash trading exists to inflate "ranking of a
meme coin on platforms such as DexScreener, which sorts tokens by trading volume" — DexScreener's
own sort key is the attack surface, named explicitly by an outside paper, not just inferred.

**Does rank predict anything after costs?** No study regresses trending rank or boost status
directly on forward, cost-adjusted returns — arXiv's abstract index for `"trending" AND
"memecoin"` and `"pump.fun" AND "attention"` both returned zero results. The closest adjacent
evidence runs negative: Kamat's graduation-prediction model, trained on a feature set that
includes early visibility signals, collapsed from 0.86 AUROC in-sample to 0.46 out-of-sample —
worse than a coin flip (`memecoin-sniping.md` §3, same paper). Combined with the 82.9% figure
above, the list that looks like "what's working" is, by direct measurement, disproportionately
the manufactured one. **This is an absence of evidence for a positive rank effect, not a
confirmed null** — nobody has run the regression either way, as far as this search reached.

## 2. The reflexive trade: buying the moment a token trends

No dedicated study on buying at trending-list entry was located (same zero-result arXiv queries
above). More tellingly, a direct GitHub search for a productized "boost-sniping" bot —
`dexscreener boost sniper` and `"boost sniper" solana` — returned **zero repositories** both
times. That is a genuine negative result, not a failure to look hard enough: the genesis-block
sniper stack (Geyser/gRPC, Jito bundles) is a named, documented ecosystem with vendors and blog
posts (`memecoin-sniping.md` §1); "snipe the boost" has no equivalent public footprint. Either
nobody has productized it, or it's private and unpublished. The nearest real data point is the
companion brief's call-channel study (Money Leaves Clues, 770 picks): a realistic 15-second
entry into an *already-visible, already-called* token nets a negative median return by one
minute. A trending-list entry is structurally later and more diffused across buyers than a
targeted call, so there is no mechanism by which it should do better — only evidence that a
faster, more concentrated version of the same trade already loses.

## 3. MEV: sandwich and arb bots, and the slippage trap

The companion brief already carries Helius's [Solana MEV Report](https://www.helius.dev/blog/solana-mev-report.md)
headline numbers (Vpe sandwich bot: 88.9% success, $13.43M/30 days; arbitrage bots: $142.8M/year
across 90.4M trades). What it adds here is the mechanism and a live measurement tool. Helius
states the attack plainly: "Memecoin traders are especially susceptible to sandwich attacks, as
they set high slippage tolerances when trading illiquid and highly volatile assets," and the
attacker's move is "an unprofitable front-run transaction, buying the asset to drive its price
to the worst execution level allowed by the victim's slippage settings." **Your slippage
tolerance is not a safety margin, it is the attacker's budget** — the wider you set it (which
memecoin traders must, to get filled at all on thin liquidity), the more there is to extract.

Helius's own report points to [sandwiched.me](https://sandwiched.me) as the live reference tool.
A snapshot pulled this session (2026-10-06 — a moving, unaudited live figure, not a peer-reviewed
one) showed 24 hours of 147,321 detected sandwich attacks, 66,412 distinct victims, 126.668 SOL
extracted and 701 active attacker accounts against 1.39B SOL in swap volume. The page has a
search function, but I could not confirm from the fetched text whether it supports a per-wallet
lookup — **unverified**. Absent that, the DIY proxy is logging your pre-trade quote at the block
height you submitted against your actual fill: a gap beyond your slippage setting minus the
pool's stated fee is the sandwich tax.

Jito's only disclosed mitigation is the `jitodontfront` sentinel account
([docs.jito.wtf](https://docs.jito.wtf/lowlatencytxnsend/)): include a pubkey starting with that
string and a bundle containing it only executes if your transaction is first. Jito's own text
concedes it "may help reduce sandwich attacks but is not guaranteed to do so and is not a
solution for all variations in transaction ordering, including any ordering conducted by third
parties" — it defends against Jito-bundle sandwiching specifically, not the broader surface.

## 4. Priority-fee and tip spikes around viral launches

The companion brief already has Jito's live tip-floor percentiles. Helius supplies the absolute
spike evidence: against an annual total of 3.75M SOL in tips across 3B+ bundles, a single day
(Nov 19, 2024) carried 60,801 SOL — roughly 1.6% of a full year's volume in one day — and daily
tipper accounts peaked near 938,000 on Dec 10, 2024, the same spike shape. Jito's own guidance
names the problem: "during high-demand periods, this minimum tip might not be sufficient to
successfully navigate the auction." The tip floor a bot calibrates from yesterday's API read is
reactive, not predictive — stale exactly when a viral launch makes it matter.

## 5. Dev sells into volume: no timing study found

I checked both available on-chain studies directly for a dev/creator sell-timing-vs-volume-spike
result and found neither measures it. [MemeTrans](https://arxiv.org/html/2602.13480v1) studies
pre-migration dev holding percentage and a fixed 20-minute post-migration price-collapse window —
not a sell-timing lag — though it states qualitatively that "early buyers accumulate substantial
token holdings during the launchpad sale and unwind them into DEX liquidity pools after
migration." [The Manipulation-as-a-Service paper (arXiv 2609.10246)](https://arxiv.org/abs/2609.10246)'s
"coordinated dump" heuristics (DP1: atomic, single transaction; DP2: up to a 24-hour window
between accumulation and sell) detect 4,402 dumps, median 7 senders (one case 312), $2.5–5M
extracted across a 1% sample — but this measures sender-coordination structure, not a lag against
a volume spike, and does not isolate creator wallets specifically from other coordinated sellers.
**This is a genuine gap: "dev sells into volume" is a plausible, commonly-asserted pattern with
no dedicated measurement behind it in the sources reachable this session.** The only live,
productized proxy is GMGN's `dev.creator_token_status` field (`hold`/`sell`), which a retail bot
can poll in real time as a kill switch — not something anyone has backtested as a timing signal.

## 6. Statistical tell-tales for exclusion filters

Confirmed field names from the GMGN token API (via `GMGNAI/gmgn-skills`): `bundler_trader_amount_rate`,
`rat_trader_amount_rate`, `sniper_count`, `fresh_wallet_rate`, `suspected_insider_hold_rate`,
`rug_ratio`, `is_wash_trading`, `dev.creator_token_status`, `dev.creator_open_count`,
`dev.dexscr_ad`, `dev.dexscr_boost_fee`, `dev.dexscr_trending_bar`, `dev.twitter_name_change_history`.
No literal `image_dup` field turned up this session — the closest analog is the Twitter
rename-history field. Treat image-duplicate detection as a real pumpscan/front-end feature
(per `memecoin-sniping.md` §3) but **not independently confirmed as a named GMGN field** here.

The evidence that these filters change outcomes, not just labels, is already established in the
sibling briefs: MemeTrans's risk-tier concentration delta (bundle-adjusted holding percentage
runs 24pp higher on high-risk tokens, 9pp medium, 6pp low than the raw figure) and orcACR's live
creator-history filter (skip repeat creators / large first buys / creator-funded wallets;
~100–200 SOL/day, unaudited). No backtest surfaced this session turning GMGN's fields directly
into a dollar P&L rule; they separate risk tiers, but aren't confirmed profitable as a standalone
filter.

## Verdict table

| pattern | how detected | measured effect | who measured | retail action |
|---|---|---|---|---|
| Trending-list gaming via wash volume | `is_wash_trading`, `dexscr_trending_bar` (GMGN); DexScreener sorts by volume (own docs) | 17% of all trades, 21.4% pre-migration, 82.9% of 3-month 100%+ gainers show manipulation | arXiv 2609.10246, 2602.13480, 2507.01963 | Treat "trending" as the manufactured subset, not the real one |
| Paid boosts/ads | `dev.dexscr_ad`, `dev.dexscr_boost_fee` (GMGN) | No guaranteed rank (DexScreener's own T&C); no outcome study found | docs.dexscreener.com, GMGN fields | Subtract paid visibility from any momentum read |
| "Boost-sniping" bots | — | 0 GitHub repos under two direct searches | this session (negative result) | Not a productized edge; don't assume one exists |
| Reflexive trending-list entry | — | No dedicated study; nearest proxy (call-channel realistic entry) already negative median at 1–5 min | companion brief, Money Leaves Clues | Unproven, likely negative by analogy |
| Sandwich attacks | sandwiched.me live feed; slippage = attack budget | 147,321 attacks/24h, 66,412 victims, 126.7 SOL extracted (live snapshot); Vpe bot 88.9% success/$13.43M/30d | Helius, sandwiched.me | Set slippage to the minimum that still fills; log fills to self-measure |
| Jito tip spikes on viral launches | `bundles.jito.wtf` tip-floor API | One day (60,801 SOL) ≈ 1.6% of a full year's (3.75M SOL) tip volume; floor is reactive | Helius MEV Report, Jito docs | Budget tip as % of position; expect the floor to be stale when it matters |
| Dev-sell-into-volume timing | `dev.creator_token_status` (GMGN); DP1/DP2 dump heuristics | No timing-lag study found — a genuine gap | MemeTrans, arXiv 2609.10246 (absence confirmed, not measured) | Poll as a real-time kill switch, not a backtested signal |
| Bundler/sniper/fresh-wallet/wash exclusion filters | GMGN API fields | 24pp/9pp/6pp concentration delta by risk tier; orcACR live filter ~100–200 SOL/day (unaudited) | MemeTrans, mikem.codes | Use as a pre-trade exclusion filter, not an alpha signal |

## Bottom line

Every number a retail scanner reads as organic demand — DexScreener's volume sort, GMGN's hot
list, pump.fun's board — is also the cheapest number to fake, and the one paper that checked the
"winners" (82.9% of 3-month 100%+ gainers) found manipulation signatures more often than not.
MEV is a separate, additive tax on top: sandwich bots extract real, measured millions using your
own slippage setting as their budget, and nobody has published a fix beyond tightening slippage
and routing through `jitodontfront`, which Jito itself does not call reliable. The free,
reachable layer for a retail bot is exclusion — GMGN's bundler/wash/sniper/boost fields filter
out the tokens most likely to be fake — not signal generation; no source found this session
turns any of these fields, or trending rank itself, into a positive-EV entry rule after costs.
Two items are explicit, named gaps rather than confirmed nulls: whether trending rank predicts
anything after costs, and whether dev wallets time sells to volume spikes. Both are plausible,
commonly asserted, and unmeasured in every source this session could reach.
