<!-- research brief, filed 2026-10-06; agent output verbatim. Sibling to docs/briefs/memecoin-sniping.md
     (infra stack, bundle/dev-wallet detection) and 02_findings/memecoins.md (this repo's own 4,344-launch
     panel). This brief is the curve-math and graduation-play layer: what "near-completion", "king of the
     hill" and curve-position arbitrage actually measure, and whether any of it clears costs. Verdicts
     belong in 02_findings/ if anything here is acted on. -->

# Bonding-curve and graduation plays, 2026

## 1. The curve math, confirmed from source

Pump.fun's bonding curve is Uniswap-V2-style constant product on *virtual* reserves, confirmed
directly from `Global`/`BondingCurve` account fields in
[pump-fun/pump-public-docs](https://github.com/pump-fun/pump-public-docs)
(`PUMP_PROGRAM_README.md`): initial virtual SOL reserves 30,000,000,000 lamports (30 SOL),
initial virtual token reserves 1,073,000,000,000,000 (1.073B at 6 decimals = 1.073B actual
tokens), initial **real** token reserves 793,100,000,000,000 (793.1M actual tokens) against a
total supply of 1B. A curve is `complete` — the on-chain field the docs actually gate on —
the instant `real_token_reserves` hits zero, i.e. all 793.1M curve-side tokens have been sold.

The docs don't spell out the SOL figure, but it's exactly recoverable from their own constants:
k = 30 × 1,073,000,000 ≈ 32.19B. At completion, virtual token reserves have fallen by 793.1M
to 279.9M, so virtual SOL reserves = k ÷ 279.9M ≈ 115.0 SOL. Real SOL raised = 115.0 − 30 =
**85.0 SOL** — which is the widely-quoted graduation number and matches the "115 SOL
deterministic threshold" an independent paper derives the same way (Section VI,
[arXiv 2602.14860](https://arxiv.org/html/2602.14860v1), "Predicting the success of new
crypto-tokens: the Pump.fun case" — note: that's the real title; it is not the MemeTrans paper
despite covering adjacent ground). "Progress" shown in every front-end is just real SOL raised
÷ 85. At completion, the curve's real SOL and real tokens seed a PumpSwap pool and the program
migrates automatically.

**PumpSwap's post-migration fee is confirmed at 25 bps per trade** (`PUMP_SWAP_README.md`):
`lp_fee_basis_points = 20`, `protocol_fee_basis_points = 5`, nothing on deposit/withdraw. The
bonding-curve-side fee has changed shape twice in 2026. A creator-fee mechanism shipped
2025-05-12 11:00 UTC (`PUMP_CREATOR_FEE_README.md`), paid into a `creator-vault` PDA seeded on
the creator address — but the doc states the *global default* `creator_fee_basis_points` is
currently **0**, so this is infrastructure that exists and can be set above zero per launch,
not a fee charged on every coin by default (I could not confirm from the docs what share of
launches set it nonzero — **not verified**). Then in 2026, "cashback" coins (creator fee
rebated to the buyer who generated it) were deprecated — `create_v2` now rejects
`is_cashback_enabled=true` — and replaced by "holder rewards" coins
(`HOLDER_REWARDS_README.md`): "there is nothing for the creator to claim: the creator fee goes
to holders" currently holding the token, not the trader who paid it. Net effect for any curve
play below: round-trip cost is 1% protocol fee + whatever nonzero creator fee the specific coin
set, and on a holder-rewards coin that fee no longer comes back to you even partially.

## 2. The near-completion / migration-pump play

The thesis — buy at 70–95% progress, hold through graduation, sell into the PumpSwap pump —
is measured, and it loses. [MemeTrans (arXiv 2602.13480)](https://arxiv.org/html/2602.13480v1)
tracked `min_price_ratio` (the lowest price hit within a window, over the migration price) for
41,470 tokens that migrated Dec 2024–Mar 2025. Their own Table 6, 20-minute window: **60.26%
(24,988/41,470) fall below 0.2× the migration price; another 12.70% fall in [0.2×, 0.4×)** —
combined, "more than 73% of memecoins experience a price drop to below 40% of their migration
price" within 20 minutes. The specific "84% below 0.3×" framing in this brief's prompt does not
match anything in the paper's published table — the 0.3× line falls inside their combined
[0.2,0.4) bucket, which isn't broken out further, so **that exact figure is not verified**; the
closest confirmed numbers are the 60.26%/73% above. MemeTrans documents heavy early-buyer
concentration going into migration (bundled accounts hold 36.5% of supply on average; the
first 10 buyers hold 17 points more supply on high-risk tokens than low-risk ones) but does not
isolate a "dev dumped exactly at migration" statistic — the paper's framing is pre-migration
accumulation, not the migration tick itself (**not verified** as a standalone number).
Migration-sniping bots exist and are trivial to find — five GitHub repos turned up
(`solana_pumpswap_migration_bot`, `PumpFun-Migration-Sniper`, etc., 0–9 stars each) — and **none
publish P&L, backtest numbers, or win rate**. This matches the sibling brief's finding for
genesis-block sniping: the only disclosed-ish profitable operation found anywhere in this
research (orcACR, ~100–200 SOL/day, reverse-engineered not audited) is a pre-launch filter, not
a migration play.

## 3. "King of the hill" and trending effects

Neither is in the on-chain program — confirmed by grep of `PUMP_PROGRAM_README.md`: no mention
of "king of the hill," trending, or featured-token logic anywhere in the instruction or account
docs. Both are front-end ranking features (pump.fun's homepage, DexScreener/GMGN "trending"
sorts) with no published on-chain threshold and, as far as this session could find, **no
dedicated academic measurement of their own price effect** — not verified either way. The
closest real numbers, already measured by sources this repo has: Midsummer Meme's Dream
(arXiv 2507.01963, cited in `memecoins.md`) found 82.8% of the 707 tokens that gained >100% in
three months showed wash trading, LP inflation, or concentration flags — i.e. the tokens that
*become* trending are disproportionately manufactured. And this repo's own panel
(`02_findings/memecoins.md`) found 24-hour volume carries IC −0.08 (t=−3.6) against 1-hour
forward return — the busiest, most visible tokens have already run. Both point the same way:
visibility is a lagging, not leading, indicator, consistent but not a direct test of the "king
of the hill" slot itself.

## 4. Curve-position arbitrage (buy at 10 SOL, sell at 40 SOL)

[arXiv 2602.14860](https://arxiv.org/html/2602.14860v1) is built almost exactly to answer this.
On 655,770 tokens created Sep 1–Oct 1 2025 (4,338 graduated, 0.66%), they model graduation
probability conditional on current virtual-SOL-in-curve, `p_std(vSol)`, and derive the
breakeven boundary for a naive hold directly from the curve's own convexity: **profitable
requires `p(vSol) > vSol² / 115²`** — i.e. the probability of reaching graduation from here has
to beat the mechanical price markup you're already paying by entering later on the curve. Their
headline result: **the measured baseline `p_std(vSol)` lies below that breakeven curve across
the range, "hence it is not possible to make profits with a buy-and-hold strategy based only on
vSol"** (their Section VI.1). Conditioning on extra signals moves some of the curve toward
breakeven but not cleanly past it: tokens with >70% non-bot trades beat the baseline; tokens
that reach a given SOL level in few trades (10–50) do much better than ones take >1,000 trades
to get there; the top-10 historical creators' tokens are the one slice that "even exceeds the
economic breakeven curve" at high vSol, but thinly supported. Read straight: "buy 10 SOL, sell
40 SOL" understates its own cost, because the curve's convexity between those two points is
exactly what the breakeven line already prices in — before 1%+ fees and your own order's price
impact are even added.

## 5. Cross-launchpad comparison

This is the weakest-sourced section. FourMeme's own docs (`four.meme`, `docs.four.meme`) and
Clanker's contracts repo both returned 403/404/DNS failures to WebFetch this session; Zora's
Coins docs page covers hook-migration mechanics but not fee splits or a graduation threshold.
No cross-launchpad graduation-rate dataset (Dune or academic) was reachable either —
**the whole FourMeme/Zora/Clanker/Bonk graduation-rate comparison asked for is not verified
this session**, not because it doesn't exist but because the primary sources this session could
reach didn't carry it. What this repo *does* have, measured directly rather than cited: its own
4,344-launch panel (`02_findings/memecoins.md`) shows Base launches net +50% and BSC launches
net +15–19% at $100/1h, against graduated-Solana (Raydium) at −7.7%, Ethereum +45% on one
50× token — but these are post-listing retail returns on 25–87-token samples, not launchpad
graduation rates, and the brief itself flags gas as unmodelled and the Ethereum row as one
token. It's directionally suggestive that non-Solana venues look less picked-over, not proof of
a cross-launchpad edge.

## 6. Open-source bot with disclosed P&L

None found for any curve-position or migration play. The five migration-sniper repos surfaced
above are all unaudited scripts with zero disclosed results. The only profit figure anywhere in
this research program that isn't purely a backtest statistic is orcACR's reverse-engineered
~100–200 SOL/day (sibling brief), and that's a pre-launch creator-history filter, unrelated to
curve position or graduation timing.

## Verdict table

| play | entry condition | measured outcome | sample | who measured | retail verdict |
|---|---|---|---|---|---|
| Near-completion / migration pump | buy 70–95% progress, hold through graduation | 60.26% of migrations fall below 0.2× migration price within 20 min; 73% below 0.4× | 41,470 migrated tokens | MemeTrans, arXiv 2602.13480 | No — the modal outcome at the exact moment you'd be holding for is a crash, not a pump |
| Curve-position arbitrage (buy low-SOL, sell high-SOL) | enter at X SOL locked, exit at Y SOL locked pre-graduation | baseline graduation probability lies below the curve's own convexity-implied breakeven at every vSol level; only thin, creator-history-conditioned slices cross it | 655,770 launches, Sep–Oct 2025 | arXiv 2602.14860 | No — the "cheap now, pump later" framing ignores that the convexity you're riding is exactly what the breakeven line already prices |
| King of the hill / trending visibility | buy a token after it's featured/trending | no direct on-chain mechanic or dedicated study found; proxy: 82.8% of 3-month 100%+ gainers show manipulation flags; this repo's own 24h-volume IC is −0.08 | 707 tokens (proxy study); 4,344 launches (this repo) | Midsummer Meme's Dream arXiv 2507.01963; `02_findings/memecoins.md` | No — every available proxy says visibility lags, it doesn't lead |
| Migration-sniping bots | land a buy in the migration block/slot | 5 public repos, zero disclosed P&L or win rate | n/a | GitHub (this session) | Unverified / no — no retail-reachable evidence of edge either way |
| Cross-launchpad graduation rate (Bonk/Moonshot/FourMeme/Base vs pump.fun) | pick the launchpad with a better graduation rate or post-grad return | not reachable this session (403/404 on FourMeme, Clanker, Zora fee docs; no cross-platform dataset found) | — | not verified | Unverified — don't act on an unconfirmed cross-platform edge |
| Non-Solana venue listing (BSC/Base/ETH) as a proxy for "less picked over" | buy shortly after listing on a non-Solana venue | net +15–50% at $100/1h, but 25–87-token samples, gas unmodelled, one 50× token carrying the ETH row | 25–87 tokens/venue | `02_findings/memecoins.md` (this repo) | Weak/no — directionally interesting, not a backed rule yet |

## Bottom line

Every number this session could actually pin down argues against trading the curve or the
graduation moment as a strategy. The curve math is exact and confirmed from the program's own
account fields (30 SOL / 1.073B virtual, 793.1M real, 85 SOL real to graduate, 25 bps on
PumpSwap after). Every *outcome* measurement built on top of that math — MemeTrans's
post-migration collapse rate, arXiv 2602.14860's breakeven-vs-probability result, this repo's
own volume IC — says the same thing from a different angle: by the time a retail trader can
observe "70% progress" or "trending" or "just migrated," the number that mattered (who bought
in the genesis block, whether the dev set a nonzero creator fee, whether the volume is wash
trading) has already been decided by someone else. The one piece of real, repo-native evidence
that doesn't point this direction — non-Solana venues posting positive nets in
`02_findings/memecoins.md` — is also the thinnest sample (25–87 tokens) and the one this session
could not corroborate with any outside launchpad data, because that data wasn't reachable. No
new trade, filter, or automation follows from this brief; it closes the curve/graduation branch
the way the rest of `02_findings/memecoins.md` closed the others.
