# 05 — Fourteen uncovered domains, prioritized

**Status:** complete · **Evidence quality:** ⚠️ **mostly unverified** — the
agent's search budget was exhausted before it began; only the two leveraged-ETF
papers were confirmed live. Everything else is a **hypothesis with a named place
to check it**. Treat accordingly.

---

## The single most important item: independent repeated trials

**#6 — Prop-firm capital as purchased convexity.** Not an options strategy, and
that is why the options-framed investigation missed it entirely.

Futures prop firms sell an evaluation for $50–$500 which, if passed, grants
$50k–$300k of *buying power* at an 80–90% profit split, with **no capital at risk
beyond the fee**. $5,000 buys **dozens of independent attempts**.

**Why this matters more than any edge on the list:** the martingale ceiling —
P($5k→$50k) = 10% — applies to *one* sequence of bets. N independent attempts at
bounded cost is a different problem entirely. And you don't need 10x: on a $150k
funded account at a 90% split, $50k of withdrawn profit is roughly a **37%
account move**, attempted many times.

**The killer question a researcher must answer:** do *any* firms' rules permit a
**high-variance path** to the target, or does trailing intraday drawdown plus
daily loss limits plus consistency rules structurally require low-variance
trading — which destroys exactly the convexity we want? Published pass rates run
single digits to low teens, and the rules are engineered that way on purpose.

---

## HIGH priority

### 1 — Reflexive crypto-treasury equities (the "DAT" complex)
Small-float companies whose business is holding a volatile asset financed by
converts and ATM issuance (MSTR archetype). Equity carries **1.5–3× realized beta
to the coin, plus a reflexive mNAV premium, plus listed options** — three layers
of convexity in one retail ticker.

**Why it escapes our own far-OTM null:** a 10x option return needs a ~40–50% coin
move, not 300%, so it lives at **20–40 delta where the −90% base rate does not
apply**.

**The decisive test, runnable in an afternoon:** is MSTR-type option IV *below*
(coin IV × realized beta)? That gap is the entire trade. Also test whether beta
**expands** in the tails (top/bottom decile of coin moves).

**Most likely failure:** IV already prices the beta — MSTR runs 70–120%.

### 2 — Prediction markets as an options market
Kalshi/Polymarket binaries are digital options; **Breeden-Litzenberger is a
theorem**, so a listed chain implies a price for every event contract and vice
versa. Two separately-populated markets pricing the same state.

**Structurally bounded downside** — a binary cannot go below zero, cannot be
assigned, has no margin path. A 3¢ contract resolving YES pays **33×**.

Note the fee structure is proportional to p×(1−p), which is punishing at 50¢ and
cheap at 3¢ — **materially favours the convexity trade over the arb trade**.

**Most likely failure:** the gap is real-measure vs risk-neutral, not free money;
options carry a legitimate variance premium that inflates tail probabilities.

### 3 — The option-writing ETF complex as a forced counterparty
Buffer/defined-outcome ETFs (Innovator, First Trust, AllianzIM), covered-call
ETFs (JEPI/QYLD/SPYI), and YieldMax single-stock overwriters **must transact
options on a published calendar regardless of price**.

**This is the rare domain where the counterparty files its positions with the
SEC** — N-PORT discloses exact FLEX strikes, expiries and notional; outcome
periods are in the prospectus.

**The implication, not the trade:** if YieldMax is structurally short upside
calls on a single name in size, upside IV there may be **depressed relative to
fair** — meaning our convexity purchase in #1 is subsidised by a price-insensitive
seller. Cross-reference N-PORT against OCC daily OI by series.

### 4 — Rates convexity: SOFR options and midcurve flies
**Cheapest listed convexity accessible for $5k.** Far-OTM SOFR options often cost
**$12.50–$50 each**. Rates are the one asset class where the distribution is
genuinely **bimodal and policy-driven** rather than diffusive, so the
lognormal-fitted price is wrong in an identifiable direction.

March 2020, March 2023 (SVB) and 2024 each produced documented **50–500×** moves
in specific strikes. Long-only futures options: Section 1256, no margin risk.

**Most likely failure:** timing. These expire worthless with very high frequency;
buying them continuously is a documented loser. The trade needs a *conditioning
signal*, and that is the hard part — not the instrument.

**Pure data exercise:** CME publishes every settlement daily. Measure the max
realized multiple by strike across each shock window.

### 5 — Structured-product dealer positioning
Korean ELS, Japanese uridashi, and US/European autocallables leave dealers with a
**known one-sided position** — short down-and-in puts whose gamma flips sign at
specific barriers. The 2015–16 HSCEI episode is the textbook case: knock-ins
forced a hedging spiral that fed back into the index.

**Value is informational:** it tells you *where a gap move is mechanically
amplified*, which is the most valuable input to any convexity purchase.

---

## MEDIUM priority

**7 — Options on leveraged/vol ETPs.** The only domain with **live-verified**
sources: Leung/Lorig/Pascucci ([arXiv:1404.6792](https://arxiv.org/abs/1404.6792))
gives the IV-scaling procedure across leverage ratios; Figueroa-López/Gong/Lorig
([arXiv:1608.07863](https://arxiv.org/abs/1608.07863)) gives short-time OTM LETF
expansions. Both exist *because naive pricing is wrong*. On 3× products the move
needed for a 10x is one-third the size.

**8 — New-listing windows.** Every new option class has days-to-months before the
surface is calibrated. IBIT options launched Nov 2024 with position limits far
below what BTC vol warranted — **and low limits keep large players out, which is
a genuine small-account advantage**. Clean event set from Cboe/Nasdaq circulars.

**9 — Non-US listed options** (KOSPI 200, TAIEX, HKEX via IBKR). Retail-dominated
flow. **Access is the likely dead end — resolve eligibility before any pricing
work.**

**10 — Stale-underlying options** (EWJ, FXI, EWZ, BABA). The option must price a
**scheduled discrete jump** at the home market's open, while the model treats it
as diffusive.

**11 — Warrants and non-option convex securities.** SPAC warrants, CVRs, rights.
**The one domain where P(10x) is fully computable** — construct the 2019–2026
warrant universe from EDGAR and measure the realized max-multiple distribution
directly. No options approval needed, cash account, bounded at purchase price.
*Caveat: 2020–21 was a specific regime and most warrants go to zero.*

**12 — Crypto-native venues and perp funding vs option skew.** Funding is a
directly observable high-frequency measure of leveraged positioning with **no
equity analogue**. The funding-vs-skew study is **free to run without venue
access** and may point back to IBIT/MSTR expressions. US access to Deribit
post-Coinbase is the open question.

---

## LOW priority

**13 — FX peg-break convexity.** Best mechanism on the list, worst retail access —
pegged-EM FX options need institutional prime brokerage. Also, pegs are defended
for years; Ackman held HKD and lost.

**14 — Cross-asset forensics: where the 100× actually was.** In March 2020 the
biggest payoff was *not* SPX puts — it was single-name puts on airlines/cruises
and VIX call spreads. **The asset that moves most is rarely the one whose options
were cheapest beforehand.** Risk: massive hindsight bias, and the ex-ante screen
is exactly the one our far-OTM null already destroyed.

---

## Dispatch order

**Falsify cheap first** — each answerable in under an hour, each can kill a domain
outright:
1. IBKR non-US options eligibility for a US resident (#9)
2. US access to Deribit post-Coinbase (#12)
3. Any accessible pegged-EM FX option (#13)
4. **Prop-firm drawdown rules — does any permit a high-variance path? (#6)**
5. **SPAC warrant max-multiple base rate (#11) — gives a real P(10x) number**

**Then the substantive work:** #1 → #2 → #3 → #4 → #5.

**Two structural notes from the agent:**

> #1, #3 and #5 are **one connected system** — forced option sellers (#3)
> manufacture the cheap upside convexity in reflexive names (#1), and
> structured-product barriers (#5) tell you where the downside gap is
> mechanically amplified. Dispatch them together.

> #6 is the only domain offering **independent repeated trials**, which for a
> P(10x) objective is worth more than any single edge.

## Verification caveat — read this before acting

Search budget was exhausted before this agent started; most WebFetch targets
returned 429/404. **Only the two arXiv LETF papers were verified live.**
Specifically flagged as at risk of being stale: Kalshi's current product list and
fees, Deribit US access, IBIT's launch surface, IBKR foreign-options eligibility,
and the BIS/FSS autocallable sources. Every domain names where to check it.
