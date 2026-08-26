# Synthesis — 13 reports, one answer

**The research phase is complete. All 14 domains banked.**

---

## The master formula everything reduces to

> **P(10×) = 10^−(1+D)** where **D = expectancy burned ÷ log-progress required**

Discrete and continuous, gambling theory and portfolio theory, all collapse to
this (report 12). D = 0 gives exactly 10%.

## Three numbers that bound the problem

| | value | source |
|---|---:|---|
| **martingale ceiling** — fair bet, optimal play, any strategy | **10.00%** | optional stopping |
| **zero-edge retail reality** — actual σ, no optimal stopping | **1.47%** | report 13 |
| **realistic with friction** — s ≈ 4–8%, measured OTM penalty | **6–9%** | report 12 |

The gap between 10% and 1.47% is **suboptimal play plus negative expectancy.**
Closing it is worth more than any signal in this entire project.

## The crossover, and why it decides the whole design

**Pestien & Sudderth (1985):** maximise **μ/σ²** — drift-to-*variance*, not
Sharpe, not Kelly.

> **μ < 0 → maximise variance (bold, few bets)**
> **μ > 0 → minimise variance (timid, many bets)**
> **Crossover at exactly zero. No interior threshold.**

Since retail options carry **negative** μ after a 12.6% quoted spread
(28.7% OTM), the design is forced: **few, large, bold.**

Three independent confirmations of the same conclusion:

| finding | domain |
|---|---|
| with e<0, fewer bets is strictly better | theory (12) |
| **"repetition, not variance, is what the literature condemns"** — every catastrophe study conditions on 300+ days | empirical (13) |
| every crash window lasted **2–5 sessions**; the winners were **not early** | forensic (11) |

---

## What to actually do

### 1. The vehicle: XSP

Three reports converged on it independently.

| property | why | source |
|---|---|---|
| European, cash-settled | **no early assignment, no exercise-by-exception** — the only structure with no mechanical path to a negative balance | 11 |
| **Section 1256, 60/40** | worth **$1,890–$5,400** on a $45k gain = **38–108% of the entire stake**, risk-free | 10 |
| no wash-sale rule | rebuild a loser immediately | 10 |
| 3-year loss carryback | **directly rewards "total loss acceptable"** | 10 |
| 1/10th SPX notional | ~$65k/contract, sized for $5k | 11 |

**The tax finding is the highest-confidence item in the bank because it is
statutory rather than empirical** — no decay, no model risk, no execution risk.

### 2. The structure: synthetic digitals, not naked calls

**Föllmer & Leukert (1999):** by Neyman–Pearson, the optimal payoff for a
fixed-multiple goal is a **digital**. A naked OTM call overshoots — you pay for
tail beyond the target and don't get paid for it.

> Use a **tight call spread struck so max value ≈ per-bet target.** Same success
> set, strictly lower cost, strictly higher P. **This is the one free improvement
> available with no edge required.**

Corollary: **no stop-losses, no profit-taking below target.** Partial credit is
worth zero against a hard goal; step utility is convex below it.

### 3. The count: 1–3 bets, ~2.2× to 10× each

Two bets at ~3.2× is the robust centre. Never more than 4–5 (report 12).

### 4. The delta: 15–25Δ — and deep OTM is SIX TIMES WORSE

Report 14 settles this with a base-rate table. **At 1Δ, P(10×) is 0.34% against
2.09% at 16Δ.** The arithmetic: 10× requires `S_T ≥ K + 10·C₀`, so going further
OTM raises K but collapses C₀ — **the required move is U-shaped, minimised at
12–20Δ.**

**Optimal delta is a monotone function of the target:** 2×→50Δ, 10×→**16–25Δ**,
100×→2–5Δ. Deep OTM is right only if you want 50×+.

| vehicle | P(10×) at optimum |
|---|---:|
| **crypto-linked, 180d** | **4.85%** |
| small-cap | 3.30% |
| high-beta single name | 2.09% |
| **index (SPX/QQQ)** | **1.53%** |

### 4b. ⚠️ Report 14 CONTRADICTS reports 10/11 on the vehicle

10 and 11 converged on **XSP** (Section 1256 + bounded structure). Report 14 says
**index options are the structurally worst 10× vehicle** — indices have negative
skew, single names have positive idiosyncratic skew.

**Resolution: the probability difference dominates the tax benefit.** Section 1256
is worth 38–108% of the stake **but only on gains you actually realise.** Trading
a 1.53% vehicle to save tax is paying a 3× probability penalty for a conditional
benefit.

> **Single names for the bet. XSP only if the thesis is genuinely index-level.**

Report 11's bounded-loss requirement is satisfiable another way: **long calls in a
cash account are bounded at premium on any underlying** — just close before
expiration day to avoid exercise-by-exception.

### 4c. The old finding, now correctly scoped

| study | far wing | moderate |
|---|---|---|
| ours, 10.5M purchases | −90% | **+26.1% at 16–30Δ** |
| Almeida, 7.8M Deribit trades | small beyond ±60% | **38.7% of premium in [+20%,+60%]** |

But report 11 qualifies this for tails specifically: **5–15Δ is what 10×s on a
~1-per-2-year dislocation**, at an 85–95% worthless rate. The reconciliation:
16–30Δ maximises *expectancy*; 5–15Δ maximises *P(10×)*. **They are different
optimisations** and this goal wants the second.

### 5. Do NOT barbell

`P_max = αx/(b−(1−α)x)` is monotonically increasing in α. The safe leg cannot
contribute to the goal.

> **Your $5,000 is already the convex leg of a barbell whose safe leg is
> everything you own outside this account. Do not barbell the barbell** — it
> costs a factor of 1/α.

---

## What is closed

| route | verdict |
|---|---|
| capacity/small-account arbitrage | **dead** — $5k is below the capacity FLOOR; HTB conversions are negative at $5k, positive at $500k |
| dispersion, gamma scalping | dead — DMV: "cannot be exploited with realistic frictions"; gamma scalping needs $50–100k |
| credit structures, standing tail hedge | dead — wrong shape, and carry burns $5k in <1yr against a 1-per-2yr event |
| far-OTM lottery tickets | dead — −90% to −48% over 10.5M purchases |
| index rebalancing, M&A directional | dead |
| CVRs | structurally incapable — capped payoff cannot 10× |

## The unresolved conflict

**Report 08 says the Apex 20-account structure gives 14–45%. Report 12 says it
cannot exceed 10%**, because at q = 2.96% the firm would be selling $1,480 of
expectancy for a $500 fee. The fair fee implies **q = 1.0% — exactly at the
frontier** — so a profitable firm sits below it.

**Report 12's arbitrage argument is more fundamental** and should be treated as
correct unless the firm is genuinely mispricing. Report 08's own unverified 2024
payout-denial episode is what a firm does when it discovers it has mispriced.

**Highest-value outstanding item in the entire bank:** verify that episode. It is
the difference between a 30% plan and a 0% one. Note also that **no futures prop
firm permits options**, so this route conflicts with the stated constraint anyway.

---

## The honest bottom line

**P(10×) ≈ 5–7% single-shot, 8–10% across 4–5 uncorrelated positions** — against
a hard ceiling of 10% and a retail reality of 1.47%. **P(total loss) at the
optimum is 91–94%.**

Two independent derivations agree: report 12's friction model gives 6–9%, report
14's base-rate table gives 5–7% single / 8–10% diversified.

Nothing found beats a fair coin. The entire contribution of 13 research reports
is to move you from **1.47% toward 9%** — by minimising friction, taking few
bets, using digitals instead of naked calls, choosing the tax-advantaged and
structurally-bounded vehicle, and refusing to barbell.

**That is a ~6× improvement in your odds, and it is real.** It is not an edge.

The only thing that raises the ceiling above 10% is **genuine positive
expectancy**, and it raises it fast — S=+0.5 for a year gives 21.7%, S=+1.0 gives
38.9%. **And if that ever exists, the entire prescription inverts:** stop being
bold, size small, grind.


---

## The last thing report 14 established

> **The 10× move is not rare in high-vol names — roughly 0.3–0.5 times per name
> per year. What is rare is being positioned before it.**
> **P(10×) is a timing problem, not an existence problem.**

Every name in a deliberately *non*-winner-selected basket (ROKU, SNAP, PTON, LYFT)
had 2–3 windows over 8.5 years where a 16Δ 60-DTE call would have 10×'d.

And the selection-bias trap was measured: an ex-post winners basket runs **2× the
honest basket** at moderate thresholds and **5× at extremes.** Anchor on the
honest one.

**Two configurations were foreseeable ex ante**, which is the closest thing to a
signal in this entire project:
- **GME** — short interest >100% of float, extreme borrow fees, and **IV still
  moderate** in early Dec 2020. A screenable configuration.
- **MSTR ×4** — a levered Bitcoin proxy with a known 60%+/yr underlying premium,
  repeating four separate times.

Both are the **vol-compression + genuine-drift** screen, which is exactly what
report 14's Setup 1 encodes and what falsification test #1 should attack first.
