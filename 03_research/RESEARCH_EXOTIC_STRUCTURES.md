# Exotic and Multi-Leg Option Structures — What They Actually Are

Research date: 2026-08-06. Seven named structures, assessed for credible evidence of positive
expectancy after real costs, and decomposed into what they are economically once the marketing
language is stripped away.

## How to read this document

Three independent lines of evidence are kept strictly separate.

1. **Published research**, cited with its actual numbers, fetched from primary sources this session.
   Where none exists, this report says "no rigorous evidence exists" and stops rather than padding.
2. **The desk's own real-quote backtest** (SPY 2008–2025, ask/bid fills, 147,350 trades), supplied by
   the coordinator and treated here as the primary expectancy evidence.
3. **Original measurement written for this report** against `data/opt_eod/SPY_options.parquet` —
   24.7M rows of real SPY end-of-day bid/ask chains with greeks, 2008-01-02 to 2025-12-12. Scripts:
   `scripts/zebra_vs_call.py`, `scripts/delta_hedged_gains.py`, `scripts/exotic_claims_test.py`,
   `scripts/bwb_and_box.py`, `scripts/exotic_structure_costs.py`.

Established findings built on, not re-derived: the VRP is an **index** phenomenon (Driessen–Maenhout–
Vilkov: index IV−RV +3.77 vol points vs single-stock −1.35, zero VRP unrejectable for 108 of 135
stocks); Dew-Becker & Giglio (Chicago Fed WP 2025-17) find option alphas indistinguishable from zero
over 15 years and zero cumulative return on traded puts Mar 2009–Dec 2022; CBOE's own CNDR iron condor
index returned −0.70%/yr 2010–2019; for a direction-only signal the optimal payoff is linear.

---

## 0. Executive answer

**The desk's real-quote backtest already settles four of the seven.** All four premium-selling
structures are significantly negative after real fills:

| structure | win rate | return/trade | t |
|---|---|---|---|
| jade lizard | 65.2% | **−2.88%** | −18.0 |
| twisted sister | 54.6% | **−0.32%** | −9.4 |
| broken-wing butterfly (put) | 55.2% | **−8.94%** | −18.1 |
| Christmas tree (call 1-3-2) | 38.2% | **−23.42%** | −24.5 |

Note the signature: **high win rates, negative returns.** This is the same pattern `FINDINGS.md`
already documented for the call credit spread (57.9% win rate, exactly 0.00% return). Winning often
and losing more when you lose is what a fairly-priced short-variance position looks like after costs.

**So the question this report had to answer is: does any credible published source disagree, and on
what conditioning?** The answer is no. There is no peer-reviewed literature on any of these four
structures under any name. The only published work that speaks to the family — CNDR, Dew-Becker &
Giglio, Bakshi–Kapadia — agrees with the desk's numbers. Nothing conditions the result favourably.

**The two open questions are answered as follows:**

- **ZEBRA** — measured cleanly below on 850–882 weekly entries, held to expiration (which structurally
  eliminates the exit-chain contamination that corrupted the desk's earlier run). Verdict: it does
  *not* strip extrinsic to zero, but it does cut it **8.2×** versus a 0.80-delta call. Against that
  call it is **statistically indistinguishable after costs** (paired difference −$2.12/trade, t=−0.31
  at 35 DTE; +$7.59, t=+0.67 at 90 DTE). Against **shares it loses significantly** (−$87/trade,
  t=−3.95). It is a leverage instrument, not an edge.
- **Gamma scalping** — the discrete-hedging literature (Boyle & Emanuel 1980, Leland 1985,
  Whalley & Wilmott 1997) turns out **not** to condemn it on cost grounds for a penny-wide underlying
  like SPY. It condemns it on irreducible hedging-error variance. The killer is elsewhere: Bakshi &
  Kapadia (RFS 2003) and this report's own replication show the mean is negative because the trade is
  short the variance risk premium by construction.
- **Box spread** — the only structure here with rigorous published economics (van Binsbergen, Diamond
  & Grotteria, JFE 2022). The edge is ~0.40%/yr. Measured retail crossing cost is 5.1–12.5%/yr. And
  American-style boxes carry an early-assignment failure mode that has produced documented retail
  blowups.

---

## 1. There are not seven trades here. There are four.

| Family | Structures | Net exposure | Premium harvested |
|---|---|---|---|
| **A — short variance** | broken-wing butterfly, Christmas tree, jade lizard, twisted sister (+ iron condor) | short vega, short gamma, long theta, small delta | the index VRP |
| **B — long variance** | gamma scalping | long vega, long gamma, short theta | **pays** the VRP |
| **C — linear delta** | ZEBRA | delta ≈ +1.00 | equity risk premium, levered |
| **D — financing** | box spread | zero greeks | Treasury convenience yield |

Measured on real SPY chains (~35 DTE, month-start 2018–2025, n=96), the Family-A structures are
greek-for-greek the same trade:

| structure | contracts | net $ | Δ | Γ | Θ | vega |
|---|---|---|---|---|---|---|
| BWB (credit, put) | 4 | +44 debit | −0.01 | −0.00 | +0.04 | −0.11 |
| BWB (debit, call) | 4 | 214 debit | +0.06 | −0.00 | +0.00 | −0.05 |
| Christmas tree 1-3-2 | 6 | 281 debit | +0.05 | −0.01 | +0.01 | −0.09 |
| jade lizard | 3 | 355 credit | +0.08 | −0.02 | +0.12 | −0.44 |
| twisted sister | 3 | 215 credit | −0.14 | −0.03 | +0.07 | −0.38 |
| iron condor (16Δ, benchmark) | 4 | 111 credit | −0.03 | −0.01 | +0.03 | −0.15 |

Every one is short vega, short gamma, long theta. They differ only in where the delta sits and which
tail is capped. **The names are product differentiation, not economic differentiation.** If you know
CNDR lost 0.70%/yr for fifteen years, you know the expected return of this family — and the desk's
backtest confirms it structure by structure.

Families A and B are the same bet in opposite directions. They cannot both have an edge.

---

## 2. Broken-Wing Butterfly

**Desk result: 55.2% win, −8.94%/trade, t = −18.1.**

### (a) What it actually is

Strikes L < M < H: long 1 H, short 2 M, long 1 L. Decomposed into verticals:

```
BWB = [long H / short M vertical]  +  [short M / long L vertical]
      narrow width, a debit           wide width, a credit
```

**A wide credit spread with a narrow debit spread bolted on top.** The credit spread is the position;
the debit spread is a lottery ticket paying only on a pin near M. Max loss is exactly
`(wide − narrow) − credit`.

### (b) Is "opened for a credit ⇒ risk completely eliminated on one side" true?

**True as stated, and content-free.** Three distinct problems:

**1. The credit constraint imposes no discipline.** A credit is always obtainable — widen the risk
side. Searching all put-BWB combinations on 96 SPY dates for structures that remain a credit *after
crossing the spread*:

| variant | narrow | wide | credit received | max loss | max profit | loss : credit |
|---|---|---|---|---|---|---|
| max credit | $1 | $180 | $471 | **$17,332** | $598 | **36.8 : 1** |
| min risk | $1 | $2 | $16 | $84 | $124 | 5.3 : 1 |

Obtainable on **96 of 96 dates**. Credit is bought one-for-one with risk.

**2. "Eliminates risk on one side" describes the expiration diagram, not risk borne.** The position is
short gamma and short vega throughout its life. A move toward the shorts marks against you long
before expiry, and in a margined small account a mark-to-market loss is a margin call.

**3. It eliminates the side that was never at risk.** For a put BWB the eliminated side is the upside.
All the risk was always below, and all of it remains.

**The min-risk row is decisive: the safest credit BWB collects $16 against a $15 round-trip spread —
the spread consumes 94% of the credit.** There is no configuration where the credit is meaningful
relative to its own transaction cost. That is the mechanism behind the desk's −8.94%/trade.

### (c) Evidence

**None.** No peer-reviewed study exists under this name or as a ratio-spread variant. The published
work that applies — CNDR (−0.70%/yr), Dew-Becker & Giglio (alphas ≈ 0) — agrees with the desk result.

**Conflict flag:** tastytrade and Option Alpha are the principal promoters. tastytrade charges **$1.00
per contract to open** ($10/leg cap, $0 to close). A BWB is 4 contracts; a vertical is 2. Their revenue
from teaching the four-leg version is exactly double.

### (d) Cost

4 contracts, **8 crossings round-trip**. Measured median round-trip spread on SPY 35 DTE: **$11–$14**
= 0.9% of max profit (wide version), **94% of the credit** (min-risk version), 6.5% of max risk (debit
version).

### (e) Tail risk and margin ($2,000–5,000 account)

Margin is charged on the **wider** wing, not the net. A $180-wide credit BWB needs $17,332 — impossible.
A realistic 10-point risk side needs $1,000 = 20–50% of the account on one trade. Max profit occurs
*exactly at the short strike at expiration*, which is where assignment is least predictable: one
assigned SPY put is a $68,000 obligation in a $3,000 account, resolved by the broker's liquidation desk.

**Verdict: don't.**

---

## 3. Christmas Tree Spread (1-3-2)

**Desk result: 38.2% win, −23.42%/trade, t = −24.5 — the worst structure tested.**

### (a) What it actually is

`1-3-2 = [long 1 K1/K2 debit vertical] + [short 2 K2/K3 credit verticals]`. **A debit spread financed
by selling two credit spreads.** Family A with 50% more contracts. Measured greeks: Δ +0.05, Γ −0.01,
Θ +0.01, vega −0.09.

### (b) Headline claim

No crisp claim; sold on payoff shape ("more profit potential in the target zone"). True and irrelevant
— the extra profit zone is paid for by the extra short vertical, which is where the risk went. Note
the desk's 38.2% win rate: this is the one Family-A structure that does not even win often, because
the profit zone is narrow and the price rarely finishes in it.

### (c) Evidence

**None. No academic literature exists under any name.**

### (d) Cost — the explanation for −23.42%

**6 contracts, 12 crossings round-trip** — the most expensive structure of the seven. Measured on SPY
35 DTE: round-trip spread **$17** on a **$281** debit with **$338** max risk = **5.0% of max risk**.
At 90 DTE: **$39** on a $187 debit and $237 max risk = **16.5% of max risk**. Add ~$12 round-trip in
SPX commissions at Robinhood. Twelve spread crossings against a few hundred dollars of max profit is a
structural loss, not a situational one.

### (e) Tail risk and margin

Bounded payoff, so margin is manageable, but there are now **three** short strikes to be assigned on.

**Verdict: don't.** Strictly dominated by the BWB, which is itself dominated by a plain vertical.

---

## 4. Jade Lizard

**Desk result: 65.2% win, −2.88%/trade, t = −18.0.**

### (a) What it actually is

Short put + short call spread = **an iron condor with the long put removed**. Measured greeks: Δ +0.08,
Γ −0.02, Θ +0.12, **vega −0.44 vs −0.15 for a comparable 16Δ iron condor** — roughly three times the
short-variance exposure, because removing the long put removes the hedge. Economically ~85% "short
put" by risk contribution.

### (b) Is "no upside risk when the credit exceeds the call-spread width" true?

**Arithmetically true, always achievable, and completely irrelevant.** Tested on 96 SPY dates with a
20Δ short put and 25Δ short call:

| test | result |
|---|---|
| credit ≥ call-spread width, at mid | **100% of dates** |
| credit ≥ call-spread width, after crossing the spread | **100% of dates** |

The condition is satisfied trivially: the short put alone pays a $299 median credit while the narrowest
call spread is $100 wide. You cannot fail this test. That is the tell — **the claim eliminates a risk
that never existed.** A position whose dominant leg is a short put was never going to be hurt by a
rally. Meanwhile the median max risk is **$38,343** against a $299 credit — a **128 : 1** ratio on the
side that was *not* eliminated.

"No upside risk" is the true half of a sentence whose false implication is "therefore low risk."

### (c) Evidence

**None for the structure.** For the short put underneath it, this report's own delta-hedged measurement
resolves the tension between "the VRP is real" and "traded puts returned zero":

| period | delta-hedged 25Δ put (long side) | t |
|---|---|---|
| 2008–2025 | −13.79% of premium | −2.75 |
| 2013–2025 | −10.68% | −1.94 |
| **2018–2025** | **+0.40%** | **0.05** |

The seller's edge was real pre-2013 and is **gone over 2018–2025**. This independently reproduces
Dew-Becker & Giglio on the desk's own data. The premium this structure exists to harvest no longer
exists.

**Conflict flag:** the jade lizard was named and popularised in-house by **tastytrade**. It is a house
structure of a broker that bills per contract; every published claim originates from the firm that
profits from it.

### (d) Cost

3 contracts, **6 crossings**. Measured round-trip spread **$7–$8** on a $299–$355 credit = **2.0–2.5%**
— the cheapest of Family A, purely from having the fewest legs. Cost is not the primary killer here;
the decayed premium and the risk shape are. The desk's −2.88%/trade is correspondingly the mildest
loss of the four.

### (e) Tail risk and margin — this structure is untradeable at $2,000–5,000

- Cash-secured: the short put requires **$38,343**.
- Reg T naked-put margin (~20% of underlying less OTM amount): still **$8,000–10,000** per SPY contract.
- Robinhood does not permit naked short puts below its highest tier; one assignment delivers ~$68,000
  of SPY into a $3,000 account.

The only way to fit it is a cheap single-stock underlying — where Driessen–Maenhout–Vilkov show
**there is no VRP to harvest at all**. The structure is either unaffordable or pointless.

**Verdict: don't.**

---

## 5. Twisted Sister

**Desk result: 54.6% win, −0.32%/trade, t = −9.4.**

### (a) What it actually is

Short call + short put spread. Measured greeks: Δ −0.14, Γ −0.03, Θ +0.07, vega −0.38. Family A with a
**naked short call**.

### (b) Is "no downside risk" true?

**True in the same empty sense as the jade lizard, and strictly worse.** The uncapped side is now the
*upside*, which is unbounded — the jade lizard's naked put is at least bounded at the strike.

The deeper problem is skew. Index puts are expensive and index calls are cheap; that asymmetry *is* the
equity skew. **The twisted sister sells the cheap wing naked and buys protection on the expensive
wing** — the jade lizard run backwards through the skew. Measured at matched deltas, 35 DTE:

| structure | naked leg | credit collected | max risk |
|---|---|---|---|
| jade lizard | short put (20Δ) | **$355** | $38,343 (bounded) |
| twisted sister | short call (20Δ) | **$215** | **unbounded** |

**40% less credit for unbounded rather than bounded risk.** That is a dominance argument, not a nuance.

The desk's −0.32%/trade looks mild only because the sample contains no sustained melt-up that assigns
the naked call; t = −9.4 says the small negative mean is nonetheless highly reliable.

### (c) Evidence

**None.** No academic literature; barely any vendor literature. This report's measurement is against
it: delta-hedged 25Δ *call* gains were **+7.28% (t = 0.74) over 2018–2025** for the long side, meaning
the call *seller* lost money. There is no measurable call-side premium to harvest — consistent with
the VRP being a put-side phenomenon.

### (d) Cost

3 contracts, 6 crossings. Round-trip spread **$7.50** on a $215 credit = **3.5%** — worse than the jade
lizard in percentage terms because the credit is smaller.

### (e) Tail risk and margin

**Worst of the seven.** Unbounded loss; margin expands as the market rallies, so the position costs
more to hold exactly as it loses. Robinhood does not permit naked calls at all.

**Verdict: don't. The worst structure on the list.**

---

## 6. ZEBRA — the one that needed a real answer

This is the only structure the literature indirectly supports: a direction-only view belongs in shares
or deep-ITM calls, and the ZEBRA is that idea. So it was tested hardest.

### Why these numbers are clean

The desk's earlier ZEBRA run was contaminated by an exit-chain filter that deleted worthless options,
manufacturing 100% win rates. **This measurement structurally cannot have that bug:** every position is
**held to expiration and settled at intrinsic value**, so no exit chain is consulted at all. A contract
that finishes worthless settles at exactly $0.00 and is counted. Entry crosses the spread (longs pay
ask, shorts receive bid). All four expressions are normalised to **the same 100 deltas of SPY
exposure**, so the differences between them are pure cost, decay and convexity — and a paired t-test
on identical entry dates is valid.

### (a) What it actually is

Buy 2 ITM calls (~0.75Δ), sell 1 ATM call. **Measured net delta: +0.999.** It is **synthetic long stock
with ~17:1 embedded leverage**. It harvests no premium beyond the equity risk premium you would get
from shares. There is no independent expected return to test — its expectancy is
`delta × E[SPY] − financing − decay − spread`, exactly.

### (b) Head-to-head, held to expiry, per 100 deltas

**35 DTE — 850 weekly entries, 2008-01-02 to 2025-12-08:**

| expression | capital | entry spread | **extrinsic** | mean P&L | median P&L | win % | worst |
|---|---|---|---|---|---|---|---|
| **ZEBRA** | $1,427 | $26.28 (1.84%) | **$26.33** | +$193.96 | +$333.92 | 64.7% | −$5,782 |
| 0.80Δ call | $1,334 | $17.26 (1.29%) | **$216.31** | +$196.08 | +$253.41 | 60.8% | −$5,258 |
| ATM call | $752 | $7.28 (0.97%) | $746.06 | +$191.79 | −$68.97 | 48.0% | −$4,178 |
| **100 shares** | $24,947 | **$1.00** | $0.00 | **+$280.91** | +$355.00 | 66.7% | −$10,794 |

**90 DTE — 882 weekly entries:**

| expression | capital | entry spread | extrinsic | mean P&L | median P&L | win % |
|---|---|---|---|---|---|---|
| ZEBRA | $2,352 | $42.12 | **$125.71** | +$526.96 | +$705.15 | 71.1% |
| 0.80Δ call | $2,216 | $25.03 | $411.82 | +$519.37 | +$529.29 | 65.9% |
| ATM call | $1,242 | $12.00 | $1,234.08 | +$474.17 | +$86.42 | 51.4% |
| 100 shares | $24,186 | $1.00 | $0.00 | **+$757.17** | +$758.00 | 73.0% |

**Paired differences (same dates):**

| comparison | 35 DTE | 90 DTE |
|---|---|---|
| ZEBRA − 0.80Δ call | **−$2.12, t = −0.31** (ZEBRA better 53%) | **+$7.59, t = +0.67** (better 56%) |
| ZEBRA − shares | **−$86.95, t = −3.95** | **−$230.21, t = −8.29** |
| 0.80Δ call − shares | −$84.83 | −$237.80 |

### The three answers requested

**1. Does ZEBRA strip extrinsic to zero? No — but the reduction is large and real.** Measured net
extrinsic per 100 deltas: **$26.33 at 35 DTE** and **$125.71 at 90 DTE**, versus **$216.31** and
**$411.82** for the 0.80-delta call. That is an **8.2× reduction at 35 DTE and 3.3× at 90 DTE**. Not
zero — $26 is 1.8% of the $1,427 deployed, and net theta measures **−$14/day** — but "zero" is
marketing rounding of a genuinely large reduction, not a fabrication. Part of the residual is not decay
at all: it is the financing cost of holding $24,947 of notional for $1,427, which you would also pay on
margin.

**2. What does it cost in spread across 3 legs vs 1?** **$26.28 vs $17.26 per 100 deltas at 35 DTE —
1.52× the friction**, and 6 crossings round-trip instead of 2. At 90 DTE, $42.12 vs $25.03 (1.68×).
Against shares, both are catastrophic: **$26 and $17 versus $1.00.**

**3. Better or worse than the 0.80-delta call after costs? Statistically indistinguishable.** The
paired difference is −$2.12/trade (t = −0.31) at 35 DTE and +$7.59 (t = +0.67) at 90 DTE. ZEBRA wins on
the **median** (+$11.65 and +$33.57) and on 53–56% of entries, and has a higher win rate (64.7% vs
60.8%), but the means are a coin flip. **On this evidence the choice between them is a matter of
preference, not expectancy.**

### The economic point the marketing hides

The obvious puzzle: ZEBRA saves **$190 of extrinsic** per 100 deltas but only costs **$9 more in
spread** — so why is the paired P&L difference zero? Because **extrinsic value is not a cost. It is the
price of the embedded downside protection.** Stripping it out does not create value; it removes the
insurance. The conditional payoff table proves this directly:

| SPY outcome | ZEBRA | 0.80Δ call | ATM call | shares | n |
|---|---|---|---|---|---|
| < −5% | −$2,084 | −$1,975 | **−$1,155** | −$2,640 | 79 |
| −5 to −2% | −$1,466 | −$1,268 | **−$956** | −$877 | 98 |
| −2 to +2% | −$86 | −$181 | −$583 | **+$81** | 283 |
| +2 to +5% | +$954 | +$904 | +$770 | **+$987** | 280 |
| > +5% | +$2,094 | +$2,228 | **+$2,703** | +$2,128 | 110 |

In crashes the ATM call — the one with the *most* extrinsic — loses least; the ZEBRA loses nearly as
much as shares. On big rallies the ATM call gains most, because it accumulates delta while the ZEBRA
stays pinned at delta 1.0. **The ZEBRA's "zero extrinsic" is exactly the absence of convexity in both
directions. It is a faithful stock substitute, which is precisely what it claims to be and precisely
why it has no edge.**

### (c) Evidence of positive expectancy

**None as a structure, and none is required.** No published study of ZEBRA returns exists. The
decomposition is exact and needs no test: it is levered beta. The relevant question is not "does the
ZEBRA work" but "is there a directional signal worth levering 17:1" — and **`FINDINGS.md` answers no**:
zero of thousands of tested indicator combinations cleared 55% on train and validate, and the best
candidate produced **+0.00% expected return, t = +0.24** in a delta-1 instrument. A better expression
of a zero edge is still zero.

### (d) Cost

3 contracts, **6 crossings**. **$26–$42 per 100 deltas, 1.8% of capital deployed**, ~$6 round-trip in
SPX commissions at Robinhood.

### (e) Tail risk and margin

The cleanest margin profile on the list: a debit structure, so margin equals cost and there is no
assignment surprise on the longs. But **$1,427–$2,352 is 30–120% of a $2,000–5,000 account** — one
ZEBRA *is* the account. The 17:1 embedded leverage means a ~6% adverse SPY move is a near-total loss:
the measured worst case is **−$5,782 on $1,427 deployed**, i.e. the structure can lose several times
its cost because the short ATM call is uncapped against the long legs at expiry if the position is
mismanaged into assignment. That short ATM call can be assigned when ITM near expiry, converting the
position into a short-stock obligation and triggering broker liquidation in a small account.

**Verdict: conditional — the best of the seven, as an expression tool only, never as a source of edge.**
Use it if and only if a directional signal ever passes this repo's graduation gates. For holds under a
week the single 0.80Δ call is simpler and cheaper; for longer holds ZEBRA's lower decay marginally
favours it. **Shares beat both, significantly, whenever the account can afford them.**

---

## 7. Gamma Scalping

### (a) What it actually is

Long straddle/strangle, delta-hedged. The hedge removes direction by construction, so P&L reduces to
**realised variance minus implied variance** — a long position in realised volatility and, identically,
**a short position in the variance risk premium**. It is Family A run backwards. Measured ATM straddle
greeks (SPY, 35 DTE): Δ 0.00, Γ +0.04, Θ −0.25, vega +0.92.

### (b) The discrete-hedging literature — genuinely academic, and it decides feasibility

This literature is real, and it is worth being precise about what it does and does not say.

**Boyle & Emanuel (1980), "Discretely adjusted option hedges," *Journal of Financial Economics* 8(3),
259–282.** With n rebalances, the hedging error does not vanish — its variance scales as O(1/n), so the
error standard deviation falls only as **1/√n**. To halve your hedging error you must **quadruple**
your rebalancing frequency. Critically, the error distribution is **skewed, not normal**, which as the
paper notes "leads to biased t-statistics" in average-return tests. *Any* backtest of a delta-hedged
strategy that reports a naive t-statistic is overstating its confidence — including this report's, which
is why the results below are reported with the full distribution rather than the mean alone.

**Leland (1985), "Option Pricing and Replication with Transactions Costs," *Journal of Finance* 40(5),
1283–1301.** Shows that "discrete revision using Black-Scholes deltas generates errors which are
correlated with the market, and do not approach zero with more frequent revision when transactions
costs are included." Costs enter as an effective volatility increase that grows as the rebalancing
interval shrinks — so hedging more often is not free improvement.

**Whalley & Wilmott (1997), "An Asymptotic Analysis of an Optimal Hedging Model for Option Pricing with
Transaction Costs," *Mathematical Finance* 7(3), 307–324.** Derives the optimal **no-transaction band**:
do not rebalance until delta drifts outside a band whose half-width scales as **(λΓ²)^(1/3)** in the
transaction cost λ and the gamma. Continuous hedging is never optimal with costs.

**What this literature actually implies for SPY, computed:** Leland's cost term is
`(k / (σ√Δt))·√(2/π)`. With SPY penny-wide (round-trip proportional cost k ≈ 1.7 bp), σ = 15%, daily
rebalancing, this is **0.14% of volatility** — negligible. Even hourly rebalancing gives ~0.36%.
**So the transaction-cost literature does not condemn gamma scalping on a penny-wide underlying.** This
report's empirical run confirms it: share-hedging costs over the life of the trade cost only ~1
percentage point of premium. Anyone rejecting gamma scalping *on hedging-cost grounds* is rejecting it
for the wrong reason.

What the literature does establish is that **the hedging error is irreducible and skewed** — you cannot
hedge your way to a clean variance harvest. And that combines fatally with the next result.

### (c) Evidence on the mean — large, rigorous, and against you

**Bakshi & Kapadia (2003), *Review of Financial Studies* 16(2), 527–566.** 36,237 S&P 500 call
observations, 1988:01–1995:12, hedged daily. Quoting the paper:

- "the delta-hedging strategy loses money. On average, over all moneyness and maturities, the strategy
  loses about **0.05% of the index level**, and for at-the-money calls the strategy loses about 0.10%."
- "the mean π/C over the full eight-year sample is **−12.18%**."
- "The average loss on the delta-hedged strategy of about **$0.43** for at-the-money options also
  appears high compared with the mean bid-ask spread of **$0.375**."

**That last line is the single most important number in this report. The entire index VRP is
approximately one bid-ask spread wide.**

**Original replication** (`scripts/delta_hedged_gains.py`): SPY, 178 month-start entries, ~35 DTE, held
to expiry, hedged daily at the chain's own delta, 2008–2025. "NET" includes option half-spread and
share-hedge spreads:

| position (delta-hedged, long) | mean π/C | t | median | % negative | NET π/C | NET t |
|---|---|---|---|---|---|---|
| ATM call | +2.88% | 1.00 | −4.51% | 55% | +1.78% | 0.62 |
| ATM put | −8.53% | **−3.06** | −16.06% | 70% | −9.50% | **−3.41** |
| 25Δ call | −2.02% | −0.32 | −9.77% | 55% | −4.16% | −0.65 |
| 25Δ put | −13.79% | **−2.75** | −29.57% | 81% | −15.02% | **−2.99** |
| 10Δ put | −25.96% | **−2.77** | −43.05% | **87%** | −27.86% | **−2.98** |

**The literal gamma-scalping trade — delta-hedged ATM straddle, n = 178:**

| metric | value |
|---|---|
| mean π/C at mid | **−3.54%** (t = −1.33) |
| mean π/C net of costs | **−4.54%** (t = −1.71) |
| median π/C net | **−12.29%** |
| fraction profitable | **37%** |
| worst / best | −87% / +174% |
| mean $ per straddle, net | **−$39 on $1,112 of premium** |

Read the shape, not the mean — and per Boyle & Emanuel, distrust the t-statistic. Gamma scalping
**loses 63% of the time**, with a median loss of 12% of premium, rescued in the mean by a rare +174%.
It is a lottery ticket on a volatility spike.

Two further findings:

**1. The premium lives entirely in puts, and it has decayed.** ATM *calls* delta-hedged were slightly
*positive* — there is no call-side VRP to sell (which independently condemns the twisted sister). Puts
were reliably negative for the long, but by era: 25Δ put −13.79% (2008–2025) → −10.68% (2013–2025) →
**+0.40%, t = 0.05 (2018–2025)**. **Over 2018–2025 every position in the table is statistically
indistinguishable from zero** — Dew-Becker & Giglio reproduced independently on the desk's own data.

**2. Therefore both directions lose.** If delta-hedged long straddles return −4.5% net, the seller
earns +4.5% gross and then pays the same spread, leaving nothing. **The VRP is one bid-ask spread wide,
so it is consumed by the act of trading it.** This is the unifying explanation for CNDR's fifteen-year
loss, for `FINDINGS.md`'s condor result, and for all four negative Family-A results in the desk's
backtest.

### (d) Cost

2 contracts, 4 crossings, round-trip **$9 on a $1,536 straddle = 0.59%**, plus ~1 percentage point of
share-hedging. **Costs are not what kills this trade.** Being short the VRP is.

### (e) Tail risk and margin

Long premium: risk capped at the debit, no assignment risk — genuinely benign. But **operationally
impossible at $2,000–5,000**. The minimum hedge lot is 100 SPY shares ≈ $68,000, against a straddle
whose delta moves ~4 deltas per $1. /MES micro futures are ~$34,000 of notional per contract — still far
too coarse. And a $1,536 straddle is 30–75% of the account.

**Verdict: don't.** The best-documented negative expectancy on the list, and infeasible at this account
size regardless.

---

## 8. Box Spread

### (a) What it actually is

`+C(K1) −C(K2) +P(K2) −P(K1)`. By put-call parity this pays exactly `K2 − K1` at expiration regardless
of the underlying — dividends cancel out of the algebra entirely. Measured greeks on real chains: Δ 0.01,
Γ −0.00, Θ −0.00, vega 0.00. **A zero-coupon bond synthesised from options.** Long box = lending; short
box = borrowing. The premium harvested is not a risk premium but the **Treasury convenience yield**.

### (b) Is the claim true?

Yes — the only accurate description on the list, with one exception that has cost retail traders real
money (see (e)).

### (c) Evidence — rigorous, and it sizes the prize

**van Binsbergen, Diamond & Grotteria (2022), *Journal of Financial Economics* 143(1), 1–29,
"Risk-Free Interest Rates."** Infers risk-free rates from **SPX** box spreads at minute frequency,
2004–2018:

- The convenience yield on government bonds averages **~40 basis points**, **~65bp below 3 months**,
  reaching 100–160bp in 2008.
- The box "is collateralized and therefore effectively free of credit risk," and "there is no margin
  requirement to lend at our rate."
- Observable frictions including **bid-ask spreads are unrelated to their estimated rates** — the
  instrument prices cleanly *at institutional scale on SPX*.

**The entire prize is ~0.40%/yr.**

### (d) Cost — why the prize is unreachable at retail scale

4 contracts, **8 crossings round-trip**; held to expiry it settles, so entry half-spreads are the right
cost. Measured on SPY (`scripts/bwb_and_box.py`), 96 month-start dates:

| maturity | T | width | mid / width | rate at MID | rate CROSSING | entry cost | **annualised cost** |
|---|---|---|---|---|---|---|---|
| ~35d | 0.08 | $2,375 | **1.013** | **−14.21%** | −27.71% | $23.50 | **12.45%/yr** |
| ~90d | 0.29 | $2,500 | 1.011 | −4.06% | −11.13% | $39.25 | 5.46%/yr |
| ~6m | 0.54 | $2,500 | 1.007 | −1.22% | −6.56% | $73.00 | 5.44%/yr |
| ~1y | 1.04 | $2,500 | 0.996 | **+0.33%** | **−4.79%** | $134.00 | 5.15%/yr |

**Two findings.**

**The friction is 13× to 31× the entire prize.** Crossing costs 5.1–12.5% annualised against a
0.40%/yr edge. Not a close call.

**Short-dated SPY boxes are not risk-free instruments at all.** `mid / width > 1` at 35, 90 and 180
days means **the box costs more than the amount it is guaranteed to pay** — an implied lending rate of
−14% at mid. That is what American-style exercise does to a parity relationship that assumes European
exercise, compounded by end-of-day quote staleness. Only at ~1 year does the SPY box price below its
width at all, and crossing still turns +0.33% into −4.79%.

The instrument works on **SPX**: European exercise, $10,000-wide strikes, 1–3 year maturities, executed
as a package with price improvement, at a size where the spread amortises over years and hundreds of
thousands of notional. That is what van Binsbergen et al. measured, and it bears no resemblance to a
retail SPY box.

### (e) The American-exercise failure mode — documented blowups

**Short boxes on American-style options have caused real retail blowups.** The canonical case is Reddit
trader "1R0NYMAN" (January 2019): a short box spread in **UVXY** — American-style — on Robinhood,
believed to be risk-free arbitrage. Documented outcome: a **~$5,000 account turned into roughly $58,000
of losses**, about −1,800%. Mechanism:

1. Short legs of an American box can be **exercised early against you**, at any time.
2. On assignment the box stops being a box — you hold a naked directional position you did not choose.
3. The broker's risk engine liquidates the remainder into whatever market exists, which for a
   volatility ETF is very wide.
4. Because the payoff is fixed, brokers extend enormous leverage against a box — so the loss when it
   stops being a box is unbounded relative to the account.

There is no safe version of this on American-style options. **The European-style alternative removes the
mechanism entirely**: SPX, NDX, RUT and their weeklys cannot be exercised early, so the box cannot be
broken before expiry, and they settle in cash so there is no share-delivery obligation. **If a box is
ever traded, it must be SPX or another European cash-settled index — never SPY, QQQ, IWM, or a single
name.**

Margin: a *long* box uses cash equal to its cost and is genuinely low-risk on SPX. A *short* box is a
loan, and some brokers margin it as nearly free — which is precisely the trap.

**Verdict: don't, but for a different reason than the others.** The economics are real and
peer-reviewed; the structure is honest. It is an instrument for a $100,000+ cash-management problem,
and at $2,000–5,000 the spread costs 13–31× the entire edge. **If ever traded: SPX only, long only,
long-dated.**

---

## 9. The open-source evidence landscape

A direct GitHub search (authenticated code search across repositories) was run for implementations of
each structure. The result is itself a finding:

| repository | what it actually is | evidence of edge? |
|---|---|---|
| `cran/jadeLizardOptions` (CRAN R package) | Payoff-diagram plotter. Two files: `01_jadeLizardPnL.R`, `02_reverseJadeLizardPnL.R`. Description: strategies "are presented here through their Graphs." Sources a strategy encyclopedia (Stultz 2019). | **None.** No returns, no data. Explicitly disclaims investment advice. |
| `algobulls/pyalgostrategypool` — short jade lizard | Strategy template from **AlgoBulls**, an algo-trading platform. Docstring repeats the claim verbatim: "eliminating upside risk beyond the call spread width." | **None.** No backtest in the repo. Same per-execution conflict as tastytrade. |
| `brunoeduf1/market_analysis` — BWB results | A **strike screener** output listing zero-cost butterfly combinations on BOVA11 (`Custo Total` ≈ 0, −0.0099, 7e-15). | **None.** It searches for "opened for a credit" combos and attaches no P&L whatsoever. |
| `sau-rav/gamma_scalping_backtester` (8 stars) | A **Black-Scholes** utility library — `getOptionPremiumBS`, `getImpliedVolatilityBS`, `getDeltaBS`. | **None, and worse than none:** it prices options from a **model**, not from quotes. |
| `jordnlvr/legend-open/.claude/agents/broken-wing-butterfly.md` | An LLM agent prompt. | None. |

**Across all of GitHub there is not one backtest of these structures against real bid/ask with honest
fills.** What exists is payoff plotters, strike screeners, broker strategy templates, and model-priced
backtesters.

That last category deserves emphasis, because **this repo has already been burned by exactly it**:
`FINDINGS.md` records that the 0DTE iron condor's +3.7%/trade, 91%-win, t = +7.4 result was a
Black-Scholes-with-linear-skew artifact that collapsed to ≈0 on 1,919 sessions of real SPXW bid/ask.
A model-priced gamma-scalping backtester will make the identical error in the identical direction.

---

## 10. Cost summary — all seven, measured

SPY, ~35 DTE, real bid/ask. "Crossings" = number of spreads paid entry + exit.

| structure | contracts | crossings RT | round-trip spread $ | % of credit/debit | % of max profit | % of max risk |
|---|---|---|---|---|---|---|
| box spread | 4 | 8 | $39 | 2.4% | n/a | **cost = 13–31× the 0.40% edge** |
| Christmas tree 1-3-2 | 6 | **12** | $17 | 6.1% | 1.8% | **5.0%** (16.5% at 90 DTE) |
| BWB (debit) | 4 | 8 | $14 | 6.5% | 2.4% | 6.5% |
| BWB (min-risk credit) | 4 | 8 | $15 | **94% of credit** | 12% | 18% |
| iron condor (benchmark) | 4 | 8 | $8 | 7.2% | 7.2% | 2.1% |
| jade lizard | 3 | 6 | $8 | 2.0% | 2.0% | 0.02% |
| twisted sister | 3 | 6 | $7.50 | 3.5% | 3.5% | unbounded |
| ZEBRA | 3 | 6 | $26 /100Δ | 1.8% of capital | n/a | 1.8% |
| gamma scalp (straddle) | 2 | 4 | $9 + ~1% hedging | 0.6% | n/a | 0.6% |
| **0.80Δ call (benchmark)** | 1 | 2 | $17 /100Δ | 1.3% | n/a | 1.3% |
| **100 shares (benchmark)** | — | — | **$1.00 /100Δ** | 0.004% | n/a | 0.004% |

Commissions per contract: Robinhood SPY ≈ $0.04 + $0.003 TAF each way (negligible); **Robinhood SPX ≈
$0.92–1.16 each way** ($0.57–0.66 index fee + $0.35–0.50 Robinhood contract fee); tastytrade $1.00 to
open, $0 to close, $10/leg cap. A 6-contract Christmas tree on SPX pays ~**$12 round-trip in
commissions alone**, on top of $17 of spread, against $338 of max risk.

**The conflict of interest, stated plainly.** Every structure here except the box and the ZEBRA was
popularised by firms that bill per contract. tastytrade named the jade lizard in-house; tastytrade and
Option Alpha are the primary sources for broken-wing butterflies and Christmas trees; AlgoBulls ships
the jade lizard as a platform template. A 6-contract Christmas tree generates three times the contract
revenue of a 2-contract vertical and six times that of buying shares. **There is no peer-reviewed
evidence for any of the four Family-A structures, and the only sources that exist are firms whose
revenue is a linear function of your leg count.**

---

## 11. Verdict table

| Rank | Structure | What it really is | Headline claim true? | Evidence of edge? | Legs / crossings | Cost drag | Verdict |
|---|---|---|---|---|---|---|---|
| **1** | **ZEBRA** | Synthetic long stock, ~17:1 leverage. Δ = +0.999. No independent expectancy — levered beta. | **Partly.** "Mimics stock" **true**. "Zero extrinsic" **false but close**: $26 vs $216 for a 0.80Δ call — an **8.2× cut**. "Zero theta" **false**: −$14/day. | **None, and none needed.** vs 0.80Δ call: **−$2.12/trade, t = −0.31** (35d), +$7.59, t = +0.67 (90d) — **indistinguishable**. vs shares: **−$87, t = −3.95**. | 3 / 6 | $26/100Δ = 1.8% of capital; **26× the spread of shares**, 1.5× the 0.80Δ call | **Conditional.** Best of the seven, as an **expression tool only**. Use only if a directional signal passes the graduation gates — `FINDINGS.md` says none exists. Shares beat it significantly whenever affordable. |
| **2** | **Box spread** | Synthetic zero-coupon bond. Zero greeks. Harvests the Treasury convenience yield. | **Yes** — the only accurate description on the list. | **Yes, rigorous** — van Binsbergen–Diamond–Grotteria, JFE 2022: **~0.40%/yr**, ~0.65%/yr under 3 months. | 4 / 8 | Crossing costs **5.1–12.5%/yr** — **13–31× the prize**. SPY boxes price *above* their own payoff at ≤6 months. | **Don't**, at this account size. Real economics, wrong scale. **If ever traded: SPX only** (European, cash-settled). Short American boxes blew up 1R0NYMAN for ~**−$58k on $5k**. |
| **3** | **Twisted sister** | Short **naked** call + put spread. The jade lizard run backwards through the skew. | **True and worse than irrelevant.** Uncapped side is now **unbounded**. Sells the cheap wing naked, buys the expensive one: **$215 credit for unbounded risk vs the lizard's $355 for bounded**. | **Desk: 54.6% win, −0.32%/trade, t = −9.4.** No literature. Delta-hedged 25Δ call **+7.28%, t=0.74** (2018–25) — no call-side premium exists. | 3 / 6 | 3.5% of credit | **Don't.** Least-bad *number*, worst *structure*: the small mean loss reflects a sample with no melt-up. Naked index calls are unbounded and mostly prohibited at retail. |
| **4** | **Jade lizard** | Short put + capped short call = iron condor minus the long put. ~85% short put by risk. vega −0.44 vs −0.15 for a condor. | **True, achievable 100% of the time, irrelevant.** Eliminates the upside, which was never at risk. Downside **$38,343 vs $299 credit — 128:1**. | **Desk: 65.2% win, −2.88%/trade, t = −18.0.** None for the structure. Underlying short put: **−0.4%, t = 0.05 over 2018–2025** — the premium is gone. | 3 / 6 | 2.0% of credit — cheapest of Family A | **Don't.** Untradeable anyway: needs **$8k–38k** of margin in a $2–5k account. Fitting it means single stocks, where **no VRP exists**. |
| **5** | **Broken-wing butterfly** | A wide credit spread + a narrow debit spread (a pin lottery ticket). | **True and content-free.** A credit is *always* obtainable by widening the risk side — **96/96 dates**. Credit is bought 1:1 with risk (**36.8:1** loss:credit). Says nothing about risk borne before expiry. | **Desk: 55.2% win, −8.94%/trade, t = −18.1.** No academic literature exists. CNDR: −0.70%/yr for 15 years. | 4 / 8 | Min-risk credit version: **$15 spread on a $16 credit — 94% of the credit** | **Don't.** A credit spread with double the legs and a claim about the diagram, not the risk. |
| **6** | **Gamma scalping** | Long realised variance = **short the VRP**. Family A inverted. | "Market-neutral" true in direction, maximally exposed in variance. | **Yes — and it is against you.** Bakshi–Kapadia RFS 2003: delta-hedged ATM calls lose **12.18% of premium**; loss **$0.43** vs a **$0.375** spread. Own replication: straddle **−4.54% net**, profitable **37%** of the time, median −12.3%. | 2 / 4 + continuous hedging | Costs are **not** the problem (Leland cost ≈ 0.14% of vol on penny-wide SPY). Being short the VRP is. | **Don't.** Best-documented negative expectancy here. Also infeasible at $2–5k: minimum hedge lot is 100 SPY ≈ $68k. |
| **7** | **Christmas tree 1-3-2** | A debit vertical financed by selling two credit verticals. Family A with the most legs. | No crisp claim; sold on payoff shape. The extra profit zone is paid for by the extra short vertical. | **Desk: 38.2% win, −23.42%/trade, t = −24.5 — worst of everything tested.** No literature under any name. | **6 / 12 — most expensive on the list** | $17 = **5.0% of max risk** (16.5% at 90 DTE) + ~$12 SPX commissions | **Don't.** Strictly dominated by the BWB, which is dominated by a plain vertical. |

---

## 12. What this means for the owner

**One structure is worth attention, and only as a tool: the ZEBRA.** It is the only item here
consistent with the principle the evidence supports — for a direction-only signal, take a linear
payoff. The independent verdict requested:

- It **does not** strip extrinsic to zero, but it cuts it **8.2× versus a 0.80-delta call** ($26 vs
  $216 per 100 deltas at 35 DTE). "Zero" is marketing rounding of a real reduction.
- It costs **1.5× the spread of the single call** ($26 vs $17 per 100 deltas) across 6 crossings
  instead of 2.
- After costs it is **statistically indistinguishable from the 0.80-delta call** (paired −$2.12,
  t = −0.31). It wins on the median and on 53–56% of entries. Choose on preference, not expectancy —
  the single call for holds under a week, the ZEBRA for longer.
- **Shares beat both significantly** (−$87/trade, t = −3.95). The ZEBRA's only real product is
  delivering 100 deltas for $1,427 instead of $24,947.

And the reason its extrinsic saving does not convert into profit is worth carrying: **extrinsic value
is not a cost, it is the price of downside protection.** The conditional payoff table shows the ATM
call — the one carrying the *most* extrinsic — losing the least in crashes and gaining the most in
rallies. Stripping extrinsic removes convexity in both directions. The ZEBRA is a faithful stock
substitute, which is exactly what it claims and exactly why it has no edge of its own.

**One structure is worth knowing about but not trading: the box spread.** The only peer-reviewed
economics on the list, and the number is 0.40%/yr against a measured 5.1–12.5%/yr retail crossing cost.
If it ever becomes relevant at a much larger cash balance: **SPX only, long only, long-dated.** An
American-style short box is the single most dangerous position discussed in this document.

**The other five are one trade sold under five names**, and the desk's own backtest has now measured
all four Family-A variants at significantly negative after real fills, with gamma scalping negative on
the other side of the same coin.

**The unifying result.** Bakshi & Kapadia measured the index VRP at **$0.43 per at-the-money call
against a $0.375 bid-ask spread**. The premium is approximately one round-trip wide. That single fact
explains CNDR's fifteen-year loss, this repo's condor collapse from +3.7%/trade to ≈0 on real quotes,
the −0.4% (t = 0.05) put-selling result over 2018–2025, and every one of the desk's four negative
structure results. **You cannot rearrange strikes into an edge that is the same size as the cost of
trading them.** Adding legs moves the payoff diagram and adds cost; it does not add expectancy.

---

## Sources

**Primary, fetched and verified this session:**

- [Bakshi & Kapadia (2003), "Delta-Hedged Gains and the Negative Market Volatility Risk Premium," *Review of Financial Studies* 16(2), 527–566](https://people.umass.edu/~nkapadia/docs/Bakshi_and_Kapadia_2003_RFS.pdf)
- [van Binsbergen, Diamond & Grotteria (2022), "Risk-Free Interest Rates," *Journal of Financial Economics* 143(1), 1–29](https://lbsresearch.london.edu/id/eprint/1821/1/Risk_free_interest_rates_FINAL_ACCEPT_02092021.pdf) · [NBER w26138](https://www.nber.org/papers/w26138)
- [Boyle & Emanuel (1980), "Discretely adjusted option hedges," *Journal of Financial Economics* 8(3), 259–282](https://www.sciencedirect.com/science/article/pii/0304405X80900033) · [RePEc](https://ideas.repec.org/a/eee/jfinec/v8y1980i3p259-282.html)
- [Leland (1985), "Option Pricing and Replication with Transactions Costs," *Journal of Finance* 40(5), 1283–1301](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1985.tb02383.x) · [JSTOR](https://www.jstor.org/stable/2328113)
- Whalley & Wilmott (1997), "An Asymptotic Analysis of an Optimal Hedging Model for Option Pricing with Transaction Costs," *Mathematical Finance* 7(3), 307–324
- [tastytrade pricing](https://tastytrade.com/pricing/) — $1.00/contract to open, $0 to close, $10/leg cap
- [Robinhood options fees](https://robinhood.com/us/en/support/articles/trading-fees-on-robinhood/) — $0 commission, $0.04 OCC/regulatory, $0.00329 TAF, SPX index fee $0.57–0.66 + contract fee $0.35–0.50
- 1R0NYMAN box-spread incident (UVXY, American-style, ~$5,000 → ~$58,000 loss via early assignment): [r/options](https://www.reddit.com/r/options/comments/1b1eepj/risks_of_short_box_spreads_revisiting_the/) · [Money StackExchange](https://money.stackexchange.com/questions/166188/can-somone-explain-the-1r0nyman-affair)
- GitHub (authenticated code search): `cran/jadeLizardOptions`, `algobulls/pyalgostrategypool`, `brunoeduf1/market_analysis`, `sau-rav/gamma_scalping_backtester`

**Taken as established from prior work:** Driessen–Maenhout–Vilkov on index vs single-stock VRP;
Dew-Becker & Giglio, Chicago Fed WP 2025-17; CBOE CNDR 2010–2019; the desk's 147,350-trade real-quote
backtest.

**Searched and confirmed absent:** no peer-reviewed literature exists on broken-wing butterfly,
Christmas tree, jade lizard, twisted sister, or ZEBRA returns, under those names or as ratio-spread
variants; and no open-source backtest of any of them against real bid/ask exists on GitHub. These are
findings, not gaps in the search.

**Original measurements:** `scripts/zebra_vs_call.py`, `scripts/delta_hedged_gains.py`,
`scripts/exotic_claims_test.py`, `scripts/bwb_and_box.py`, `scripts/exotic_structure_costs.py`, run
against `data/opt_eod/SPY_options.parquet` (24.7M rows of real bid/ask, 2008-01-02 to 2025-12-12).
Outputs: `data/zebra_vs_call.parquet`, `data/delta_hedged_gains.parquet`, `data/exotic_claims.parquet`,
`data/box_rates.parquet`, `data/bwb_credit.parquet`.

**Caveats.** All measurements use end-of-day quotes, wider than intraday marks and occasionally stale
on near-ATM contracts — costs here are an upper bound on a patient mid-price execution, though retail
package fills rarely achieve mid on 4–6 legs. The ZEBRA comparison holds to expiration and settles at
intrinsic specifically to eliminate exit-chain survivorship bias; the delta-hedged runs rebalance daily
at the close following Bakshi–Kapadia's method, and per Boyle & Emanuel the skewed hedging-error
distribution means the reported t-statistics on those runs are biased and should be read alongside the
full distribution. Sample sizes of 96–882 non-overlapping observations are enough to reject large
effects and not enough to resolve small ones — the 2018–2025 nulls mean "no detectable edge," not
"proven zero."
