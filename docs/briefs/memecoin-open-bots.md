<!-- research brief, filed 2026-10-06; agent output verbatim. Companion to docs/briefs/memecoin-sniping.md
     (infra/latency ladder, bundle/dev-wallet detection, orcACR summary), memecoin-kol-calls.md
     (following a human's calls) and memecoin-copytrading.md (copying GMGN "smart money" wallets).
     Those cover whether a STRATEGY works; this one is narrower: what the OPEN-SOURCE CODE on GitHub
     actually encodes, and whether any of it ships a verifiable profit-and-loss. Method: gh CLI
     against the GitHub REST/search API (WebSearch was already exhausted this session; WebFetch
     used only for the one non-GitHub source, mikem.codes). Anything not directly confirmed from a
     fetched source is marked "not verified." Verdicts belong in 02_findings/ if anything here is acted on. -->

# Open-source Solana / pump.fun trading bots: what the code does, and who publishes real P&L

Audited 12 repos (ranked by stars within each search) plus five "AI-agent" projects and one
outside write-up (orcACR). None of the 12 publishes an audited equity curve. Several have
real, user-reported security problems in their own issue trackers — a different failure mode
than the "fake Claude bot" drainer tutorials already covered in `bot-claims-audit.md`, because
here the GitHub repo itself is the thing you run.

## The table

| Repo | Stars | Strategy encoded | Exit rule | Published P&L? | Verifiable? | Infra assumed / monthly cost | Issues verdict |
|---|---|---|---|---|---|---|---|
| [chainstacklabs/pumpfun-bonkfun-bot](https://github.com/chainstacklabs/pumpfun-bonkfun-bot) | 1,023 | Listens via `geyser`/`logs`/`blocks`/shreds for new pump.fun/letsbonk/StonkFun mints, buys with configurable slippage | Three modes in `bots/*.yaml`: `time_based` (`max_hold_time`, default 5s), `tp_sl` (`take_profit_percentage`/`stop_loss_percentage`), or `manual`. `extreme_fast_mode` skips the price check entirely and buys a fixed token amount | **No.** README says "NOT FOR PRODUCTION... for learning purposes only" | N/A, doesn't claim one | Needs a Geyser endpoint for the fast listener; "Public RPC nodes will not work for this workload" — paid Helius/Chainstack/Triton tier implied, exact $ not stated in-repo | Real engineering (issue #104: 13–15s RPC propagation delay before a new bonding curve is visible; #90 on tx-landing speed) plus **issue #106: a user reports a different repo, `easyemma/solana-pumpfun-bot`, stole their entire SOL balance the moment they funded the bot** — maintainers now run a GitHub Action to flag scam-bot comments in their own Issues tab |
| [mortdeus/solana-copy-sniper-mev-trading-bot](https://github.com/mortdeus/solana-copy-sniper-mev-trading-bot) | 4,475 | Node/Rust copy-trade + sniper, Jito shredstream, gRPC | Unstated in code structure shown; README leads with marketing | "Recent 0 Block Copy Trades & Results": **4 cherry-picked trades**, +$12.25/+$5.44/+$18.20/+$3.68, each with Solscan links | Partially — tx hashes resolve on-chain, but 4 trades is not a track record and nothing shows losing trades or total count | Implies Jito + gRPC/Geyser (paid) | **0 open issues on 4,475 stars** — the repo's git history starts 2013 (a reused/renamed old account, a common trick for apparent legitimacy), and the README's real content is "Message me on Telegram… Hire me for custom development." This is a lead-gen funnel, not a maintained tool |
| [coffellas-cto/Solana-Copy-Trading-Bot](https://github.com/coffellas-cto/Solana-Copy-Trading-Bot) | 411 | Copies a named target wallet's buys/sells via multiple relay races (Jito/nextBlock/BloxRoute/Temporal, "fastest wins") | Mirrors the target wallet's own sell, 0-1 block lag | 4 example tx pairs (1 token) showing the *target* wallet's "80-90% win rate," not the bot's own | On-chain tx links verify the copy mechanism works; the win-rate claim is about someone else's wallet, uncorroborated | Multiple paid tx-acceleration services simultaneously | Git history starts 2014 (same reused-repo pattern); description funnels to `t.me/up0rd0wn` |
| [ChainBuff/open-sol-bot](https://github.com/ChainBuff/open-sol-bot) | 403 | Telegram-bot UI over copy-trade + swap + wallet-tracker, Helius/Shyft APIs | Not documented in README; copy-trade mirrors tracked wallets | **No.** Explicit disclaimer: "a practice project for learning, not for production... author not responsible for losses" | N/A | Needs Helius/Shyft API key, MySQL, Redis, Docker | Real, substantive issues: pump.fun contract upgrades repeatedly broke bonding-curve/global-account parsing (#66, #65, #64), a buy/sell sign bug misclassified sells as buys (#60/#61), Jupiter routing bugs (#72). This is the most *honestly engineered* repo in the set — but it also gates real use behind an "activation code" (激活码) despite "完全开源" (fully open source) framing, and tells testers explicitly not to fund a real wallet |
| [TreeCityWes/Pump-Fun-Trading-Bot-Solana](https://github.com/TreeCityWes/Pump-Fun-Trading-Bot-Solana) | 215 | Scrapes pump.fun for new tokens with "favorable bonding curves," buys on detection | Scale-out TP: sell 50% at +25%, sell 75% of the remainder at the next +25%; stop-loss: sell all on a −10% market-cap move; sell 75% (keep 25% "moon bag") if bonding-curve progress hits a critical level | No | N/A | Selenium-driven scraping + Solana CLI, no paid infra required (which is also why it's slow) | **A real, independently reported vulnerability**: issue #9 (a security researcher) documents the bot POSTing users' plaintext private keys to `pumpapi.fun/api/trade` with TLS verification disabled; issues #5 and #7 are plain-language user reports ("THIS I SCAM DON'T USE IT IT SEND YOUR PRIVATE KEY!!!!"). Three independent sources on one repo agreeing is as close to confirmed as this medium gets |
| [bigmacman1129/solana-sniper-trading-mev-bot](https://github.com/bigmacman1129/solana-sniper-trading-mev-bot) | 190 | Raydium AMM v4 + pump.fun sniper, three executors (default/warp/Jito), cross-DEX arb | TP/SL + trailing stop + scale-out, buy cooldown, circuit breaker | No | N/A | Jito 5-region bundle fan-out, Jupiter routing — paid RPC/Jito implied | Closed #4: "Security Alert: API Key Exposure Detected." README funnels collaboration to a Telegram handle, same lead-gen pattern as mortdeus |
| [m8s-lab/solana-sniping-bot](https://github.com/m8s-lab/solana-sniping-bot) | 94 | Sniper across pump.fun, PumpSwap, Raydium LaunchLab, Meteora DBC | Not disclosed | No | N/A | Not disclosed | Closed #5 "Fix/security" — the same security-issue-title pattern recurs across this entire genre |
| [FLOCK4H/Dexter](https://github.com/FLOCK4H/Dexter) | 64 | **Dev-wallet reputation as the entry signal, implemented, not just discussed**: scores pump.fun creators by past-token performance, buys only from creators already on its leaderboard | Managed via a "Manage" TUI panel; numeric trigger not in the README excerpt fetched | No | N/A | Own mint-watching process + mainnet RPC; explicit `DRY_RUN`/`ALLOW_MAINNET_LIVE` gate | Low volume; notable only because it operationalizes the orcACR-style creator filter rather than just requesting it |
| [jcoulaud/pumpfun-sniping-bot](https://github.com/jcoulaud/pumpfun-sniping-bot) | 14 | **Inverted role**: the bot *creates* pump.fun tokens (OpenAI-generated name/art) with 70-80% of wallet balance, then waits for outside buyers | Sells the instant an external purchase lands; if nobody buys within `SELL_TIMEOUT_SECONDS` (default 20s), exits anyway | No | N/A | Helius + OpenAI + Replicate + Pinata APIs | One open issue ("Transactions fail"). README is candid: "making profit off the snipers, not regular traders" — an open-source instance of the deployer-side edge Pine Analytics measured (50%+ of launches sniped by the deployer's own wallets, `memecoin-sniping.md`) |
| [buddies2705/awesome-memecoin-trading](https://github.com/buddies2705/awesome-memecoin-trading) | 14 | Not a bot — a curated directory of 295+ tools | N/A | N/A | N/A | N/A | Documents two trends directly relevant here: (1) many of the "25+ trading bots" it lists carry "affiliate-direct links," i.e. the repo/referral monetizes regardless of user P&L; (2) "web terminals beat Telegram bots" in 2025 — Axiom, GMGN, Photon, Trojan displaced the Telegram-bot era on speed and analytics, which is consistent with finding almost no actively-starred "Telegram call-parsing" trading bot in GitHub search (see below) |
| 5 "AI-agent" repos: zetryn-ai/ai-agent, yashab-cyber/pumpfun, openpumpio/openclaw-agent, kevinxramirezx21-maker/Saturn, Reinasboo/Spectrolite | 0–6 | Each claims an "autonomous AI trading agent," "multi-model AI brain," "Kelly sizing," "5-layer scam shield," "BiLSTM-Transformer ensemble predictor" | Claimed, not demonstrated | No | No | Unspecified | All created/pushed in 2026, all under 7 stars, all with buzzword-dense READMEs and no issues, no PRs, no visible usage — the pattern is a marketing page shaped like a repo, not working software |

Notably absent from the search results: a dedicated, actively-starred "parse a Telegram call
channel and auto-buy" bot. The repos that mention Telegram use it as a *notification/control*
channel for a sniper or copy-trade bot (chainstacklabs, ChainBuff, mortdeus), not as the trading
signal itself. Following human calls is a strategy question covered in `memecoin-kol-calls.md`
(median token performance after a call, not a tooling gap); it is not a populated open-source
category.

## The one documented profitable bot: orcACR

The only write-up in this space with a plausible real edge is the reverse-engineered analysis
at [mikem.codes](https://www.mikem.codes/if-you-aint-first-youre-last-2/) (already summarized
at a higher level in `memecoin-sniping.md`; detail here). orcACR's entry filter, read directly
off the mint instruction within seconds of creation: skip any creator who has launched a coin
before, skip any creator whose first buy exceeds 4 SOL, skip any creator funded by another
known creator wallet — a dev-wallet reputation screen, enforced, not just scored. It traded
roughly 20% of new coins created. Exit is two rules, whichever fires first: **sell everything
immediately if the creator sells any of their own holdings**, or, absent that, hold ~20 seconds
and exit regardless. The authors' wallet-flow analysis estimated the operator was clearing
**100-200 SOL/day (~$10,000-$20,000/day as of May 2024)**. No wallet address is published for
independent verification and no exchange or broker statement exists — **this P&L is
unverified and should be treated as estimated, not audited**, same caveat as the companion brief.

## Scam and credibility patterns found directly in the repos

- **Reused old GitHub repos for apparent legitimacy.** mortdeus's top-starred repo (4,475 stars)
  and coffellas-cto's (411 stars) both show `created_at` dates of 2013 and 2014 respectively —
  years before pump.fun existed (launched 2024) — meaning an old, unrelated repository was
  renamed and repurposed. A repo's git-creation date is not evidence the *tool* is mature.
- **Zero-issue repos at high star counts are a red flag, not a sign of quality.** mortdeus's
  repo has 4,475 stars and 0 open issues; a genuinely used tool at that scale accumulates
  support requests. Combined with a README whose real call-to-action is a Telegram DM for paid
  custom development, the stars read as inorganic.
- **The GitHub issue tracker is itself a phishing surface.** chainstacklabs flags this
  explicitly: "The Issues section is regularly targeted by scam bots that try to redirect you to
  an external site and drain your funds," and ran a GitHub Action to tag the pattern. A user on
  that same tracker (#106) separately reported losing their full balance to a *different*,
  copycat repo the instant they funded the bot — the drainer-via-tutorial pattern from
  `bot-claims-audit.md`'s TRM Labs finding, here targeting GitHub stars instead of YouTube views.
- **A security report that is itself real, independently corroborated.** TreeCityWes's bot
  (215 stars) sends the user's private key in plaintext HTTP to a third-party domain
  (`pumpapi.fun`) with TLS verification disabled — reported by a named security researcher
  (issue #9) and independently confirmed in plain language by at least two other users (#5, #7).
  Unlike the "Jack Chain ecosystem" audit-spam issue filed near-identically on a different repo
  (bigmacman1129 #4), which reads like templated outreach, this one has corroborating victim
  reports and should be treated as real.
- **"Fully open source" with a paywall gate.** ChainBuff/open-sol-bot advertises itself as
  完全开源 ("completely open source") specifically so users keep custody of their own keys, yet
  gates real functionality behind an "activation code" (激活码) system and tells testers not to
  fund a real wallet on the public demo — a weaker, more defensible version of the
  freemium-into-custodial-Telegram-bot pattern `bot-claims-audit.md` found in the Polymarket
  "AI quant bot" network.

## Consensus: what the one real edge has, that the crowd mostly doesn't

Across every repo in this set, the only rule set tied to an estimated *positive* P&L
(orcACR) is a **creator-history filter enforced before entry, plus an exit keyed to the
creator's own behavior rather than price**. Two of the twelve open-source repos have begun
building exactly that: FLOCK4H/Dexter ships a creator leaderboard as its entry gate today, and
two unrelated repos (TreeCityWes #13, bigmacman1129 #3) have open feature requests for
"insider-cluster detection" — the same idea, requested but not yet shipped. Every other
widely-copied feature in this corpus — percentage TP/SL, trailing stops, scale-out, max-hold
timers, copy-trading a wallet — is a generic risk-management primitive with no bot in this set
showing it produced real profit; they are configuration knobs, not a demonstrated edge. The
honest summary for this repo's own swarm: a dev-wallet/creator-history gate is the one rule
with any real-world evidence behind it, and it is cheap to build (one on-chain lookup, no paid
latency infrastructure) — but even its own write-up is an unaudited on-chain reconstruction, not
a broker statement, so it should be tested on this repo's own GMGN tape before being trusted,
not assumed.
