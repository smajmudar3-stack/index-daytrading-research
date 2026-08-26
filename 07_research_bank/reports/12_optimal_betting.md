# 12 — Optimal betting to a target: the master formula, and a challenge to report 08

**Status:** complete · **Evidence quality:** highest — theorems with citations,
every prior number in the bank reproduced exactly from closed form ·
**Relevance:** unifies the whole project, and contradicts report 08

---

## The master formula

> **P(10×) = 10^−(1+D)**, where **D = expectancy burned ÷ log-progress required**

Discrete and continuous, gambling and finance, all collapse to this. D = 0 gives
the 10% ceiling.

| D | 0 | 0.05 | 0.10 | 0.25 | 0.50 | 1.00 | 2.00 |
|---|---|---|---|---|---|---|---|
| **P** | **10.00%** | 8.91% | 7.94% | 5.62% | 3.16% | 1.00% | 0.10% |

It reproduces every earlier number exactly. At e = −15%: n=1 → D=0.0706 → **8.500%** ✓;
n=10 → **1.969%** ✓; n=20 → **0.388%** ✓.

The discrete closed form: **P = (1+e)ⁿ / G**, valid while G^(1/n) ≥ 1+e. Maximise
(1+e)ⁿ — so **n=1 if e<0, n→∞ if e>0**. The crossover is visible in one line.

## The crossover is at exactly zero expectancy — no interior threshold

**Pestien & Sudderth (1985), *Math. Oper. Res.* 10(4)**, verbatim:

> *"To maximize the probability of reaching 1, the player should choose the
> parameters so as to maximize **μ/σ²** … This implies that bold (timid) play is
> optimal for subfair (superfair), continuous-time red-and-black."*

The governing quantity is **drift-to-variance** — *not* Sharpe, *not* Kelly.

> **μ < 0 → maximise σ² (bold) · μ > 0 → minimise σ² (timid) · μ = 0 → indifferent**

There is no "if edge > 2% then grind." It is the sign of arithmetic drift, full
stop. That makes the 10% ceiling a **knife-edge**: infinitesimally negative
expectancy makes fewer-and-bigger strictly optimal; infinitesimally positive makes
more-and-smaller strictly optimal.

**Bold play's conditions are narrow** — it fails with a house limit (Heath, Pruitt
& Sudderth 1972), with minimum wagers or integer fortunes (Ethier 2001), and it
is *an* optimum, not *the* optimum.

---

## The free improvement: use spreads, not naked calls

**Föllmer & Leukert, "Quantile hedging" (*Finance and Stochastics* 1999).**
Maximise P(X_T ≥ b) subject to a budget, over **all** attainable payoffs.

By **Neyman–Pearson**, the optimal payoff is **X* = b·1_A** — a **digital**. You
spend capital on the states that deliver probability most cheaply and buy
*nothing* elsewhere.

> Allowing continuous payoffs does **not** soften bold play — it **vindicates**
> it. Any payoff delivering >b in some state wastes budget (you aren't paid for
> overshoot). Any payoff delivering 0<X<b wastes budget entirely (**partial
> credit is worth nothing against a hard target**).

**Practical translation:** a far-OTM naked call is a *poor* digital — it overshoots
and you pay for tail you don't need. The efficient synthetic is a **tight call
spread struck so max value ≈ your per-bet target.** Strictly cheaper for the same
success set, and the freed capital raises P proportionally.

**This is the one improvement available with no edge required.**

It also explains why "take profits at 2×" and "cut losses at −50%" are *both*
wrong here: step utility is **convex below the target**, so every
risk-management instinct is calibrated to the wrong utility function.

---

## Browne's formula — Sharpe and time → P(10x)

**Browne (1999), *Adv. Appl. Prob.* 31:** the optimal policy for reaching a goal
by a deadline *is* buying a European digital.

> **P\* = Φ( Φ⁻¹(x/b) + S·√T )**

| Sharpe | 3 mo | 1 yr | 4 yr | 25 yr |
|---|---|---|---|---|
| **−0.30** | 7.61% | 5.69% | 2.99% | 0.27% |
| **0.00** | **10.00%** | **10.00%** | **10.00%** | **10.00%** |
| +0.30 | 12.89% | 16.32% | 24.78% | 58.65% |
| +0.50 | 15.11% | 21.72% | 38.91% | 88.85% |
| +1.00 | 21.72% | 38.91% | 76.38% | 99.99% |

This is the **upper bound over all dynamic strategies** in a complete market, and
the 10% ceiling falls out as the S=0 special case.

## Does more time help? Exactly zero at zero edge

Time enters **only** through S·√T. At S=0 it is worth **precisely nothing,
forever**. At S<0 it strictly hurts.

For the infinite-horizon version, **T does not appear at all** —
`P(ever 10×) = G^−(1+2c/σ²)`. The only thing that matters is **expectancy burned
per unit of variance purchased**.

> There is no "let it ride and eventually it'll spike." That intuition holds for
> a *log*-driftless process, not a *wealth*-driftless one. Volatility drag is
> exactly the gap.

---

## ⚠️ This contradicts report 08 — and the argument is strong

**The theorem:** if attempt *i* risks capital cᵢ with Σcᵢ = $5,000, optional
stopping gives pᵢ ≤ cᵢ/50,000, so

> **Σpᵢ ≤ 5,000/50,000 = 0.10**

**Splitting your own capital into repeated attempts can never beat 10% and always
does slightly worse** — the floor is 1−e^(−0.1) = **9.516%**.

So repeated attempts help *only* if someone else supplies the capital — which is
report 08's prop-firm claim. **But this agent then prices it:**

> At q = 2.96% per attempt, expected payout is 0.0296 × $50,000 = **$1,480
> against a $500 fee. No prop firm survives selling $1,480 of expectancy for
> $500.** The fair fee at q is $50,000q — a $500 fee is fair only if
> **q = 1.0%, exactly at the frontier.** Firms price *above* fair value, so the
> true q < 1.0% and the structure sits **below 10%**.

Report 08's barrier estimate overstates q because it ignores: trailing drawdown
from high-water mark rather than a fixed floor; challenge time limits;
consistency rules that **specifically forbid the bold play the math demands**;
the trader's own negative expectancy after spreads; and payout caps.

**Reconciliation:** report 08 computed q from the *rules*; report 12 computes it
from the *firm's survival constraint*. Both cannot be right. The arbitrage
argument is the more fundamental of the two — a business cannot durably sell
$1,480 of expectancy for $500 — so **report 08's 14–45% should be treated as an
upper bound that is very likely wrong**, unless the firm is genuinely mispricing.

That is an **edge claim about the counterparty**, not a structural free lunch.
And report 08's own unverified 2024 payout-denial episode is exactly what a firm
does when it discovers it has mispriced.

---

## The barbell is dominated here — and why

Split α into convexity, (1−α) into cash. The cash leg can never contribute to
the goal, so `P_max = αx/(b−(1−α)x)`:

| α | 5% | 20% | 50% | 80% | **100%** |
|---|---|---|---|---|---|
| P_max | 0.55% | 2.17% | 5.26% | 8.16% | **10.00%** |

**Monotonically dominated.** The barbell optimises a different objective —
long-run survival plus repeated convexity. This problem states the opposite
premises: total loss acceptable, not repeatable, one shot.

> **Your $5,000 *is already* the convex leg of a barbell whose safe leg is
> everything you own outside this account. The barbell is already constructed at
> the household level. Do not barbell the barbell** — it costs a factor of 1/α in
> success probability.

---

## The practical answer

Modelling e(m) = −(s + k·(ln m)²) — friction plus the measured far-OTM penalty —
gives an interior optimum:

> **n\* = ln G · √(k/s) · · · m\* = e^√(s/k) · · · P = 10^−(1+2√(sk))**

| s (round trip) | k (OTM penalty) | m\* | n\* | P(10×) |
|---|---|---|---|---|
| 3% | 0.02 | 3.40× | 1.9 | 8.93% |
| 5% | 0.02 | 4.86× | 1.5 | 8.64% |
| 5% | 0.05 | 2.72× | 2.3 | 7.94% |
| 10% | 0.05 | 4.11× | 1.6 | 7.22% |

### The prescription

1. **1 to 3 bets, each targeting ~2.2× to 10×.** Two bets at ~3.2× is the robust
   centre. Never more than 4–5.
2. **Synthetic digitals, not naked calls** — tight call spreads struck at target.
   Same success set, strictly lower cost, strictly higher P. Free.
3. **All-or-nothing on the whole account per bet.** No stop-losses (partial
   credit is worth zero), no profit-taking below target, no position sizing.
4. **Realistic outcome: P(10×) ≈ 6–9%** against a hard ceiling of 10%.
5. **The only lever that raises the ceiling is real positive expectancy — and it
   raises it fast.** S=+0.5 for a year → 21.7%; S=+1.0 → 38.9%. Everything else
   is rearranging deck chairs between 6% and 10%. **And if you have S>0 the
   entire prescription inverts:** stop being bold, size small, grind.
