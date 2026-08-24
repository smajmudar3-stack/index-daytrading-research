# Risk of Ruin and Position Sizing — Short-Premium Options in a $2,000–$5,000 Account

Research compiled 2026-08-06. Account context: ~$2k–$5k, Robinhood, options Level 3
(spreads permitted, naked selling prohibited).

All market data in this document is computed from **Cboe primary daily index files**
(`https://cdn.cboe.com/api/global/us_indices/daily_prices/{SPX,VIX,PUT,BXM,CNDR}_History.csv`,
downloaded 2026-08-06) or from **live Robinhood option quotes** captured 2026-08-06 18:16 UTC.
Computations are mine; scripts are reproducible. Secondary sources are cited with URLs.
Marketing/vendor sources are flagged.

---

## 0. Headline numbers

| Question | Answer |
|---|---|
| Full Kelly, 65% win / 1:1 | **30.0% of account at risk per trade** |
| Full Kelly, 85% win / 1:5 | **10.0% of account at risk per trade** |
| Full Kelly, live SPY 720/715 spread (honest params) | **9.6%**, and **negative** under mildly worse assumptions |
| Smallest position a $3,000 account can take in a 5-wide SPY spread | **15.5% of the account** — above full Kelly, unavoidably |
| Trades to prove the spread edge is real (t=2) | **6,182** ≈ **119 years** of weekly trades |
| Cboe PUT index: return vs 2008 drawdown | **+9.31%/yr** vs **−37.09%** |
| One max loss on the live spread | **12.9×** the credit = 12.9 winning months |
| Episodes since 2007 that max-loss a 6.4%-OTM monthly put spread | **5** (2008, 2018, 2020, 2024, 2025) |

**The structural problem:** a $3,000 account cannot buy a position small enough to be
survivable in the instruments available to it. The minimum tradeable unit is larger than
the mathematically correct bet.

---

## 1. Kelly for negative-skew payoffs

### 1.1 The correct formula for a bounded-loss structure

For a bet where you risk 1 unit and win `R` units with probability `p`, maximizing
`E[log W]` gives

```
f* = (p·R − (1−p)) / R  =  p − (1−p)/R
```

Here `f*` is the fraction of **bankroll placed at risk**, and for a credit spread the
"1 unit at risk" is the **max loss** = (width × 100) − credit. `R` = credit / max loss.

Equivalent and more revealing form:

```
p_breakeven = 1/(1+R)            f* = (1 + 1/R) · (p − p_breakeven)
```

The multiplier `(1 + 1/R)` is `df*/dp` — **the sensitivity of your bet size to your win-rate
estimate.** This is the crux of the whole problem.

The user's stated form `f* = (p·W − (1−p)·L)/(W·L)` is correct when W and L are expressed
as multiples of the same stake; setting L=1 (bounded max loss) recovers the above.

### 1.2 Profile 1 — 65% win rate, 1:1 payoff (symmetric/directional)

| quantity | value |
|---|---|
| breakeven win rate | 50.0% |
| edge per unit risked | +30.0% |
| SD per trade | 0.954 |
| t-stat per trade | 0.3145 |
| **trades for t = 2** | **40** |
| **full Kelly f\*** | **30.0% of account** |
| df*/dp | **2.0** |

Sizing vs assumed win rate:

| p | 0.75 | 0.70 | 0.65 | 0.60 | 0.55 | 0.50 |
|---|---|---|---|---|---|---|
| f* | +50% | +40% | +30% | +20% | +10% | 0% |

This profile is **well-behaved**: 40 trades gives a t-stat of 2, and a 5-point win-rate
error only moves the bet by 10 points. This is the profile you can actually validate.

### 1.3 Profile 2 — high win rate, negative skew (credit spreads)

| structure | breakeven p | actual p | margin | full Kelly | df*/dp | trades for t=2 |
|---|---|---|---|---|---|---|
| 85% win, 1:5 | 83.33% | 85.00% | **+1.67pp** | 10.0% | **6.0** | **1,836** |
| 90% win, 1:9 | 90.00% | 90.00% | **0.00pp** | **0.0%** | 10.0 | ∞ (no edge) |
| 92% win, 1:12.9 (live SPY quote) | 92.80% | 92.00% | **−0.80pp** | **negative** | 13.9 | no edge |
| 95% win, 1:19 | 95.00% | 95.00% | **0.00pp** | **0.0%** | 20.0 | ∞ (no edge) |

**Three things to notice:**

1. **The "90% win rate" iron condor sold at 10% of width has exactly zero edge by
   construction.** So does the 95%/1:19. The advertised win rate *is* the breakeven win
   rate. Every dollar of profit in these structures has to come from selling the option
   above its fair value — the win rate itself tells you nothing.

2. **`df*/dp` grows as the structure gets more skewed.** At 1:5 a 1pp win-rate error moves
   the correct bet by 6pp. At 1:12.9 it moves it by 13.9pp. Your entire edge (1.67pp of
   win rate in the 85% case) is smaller than the standard error of your win-rate estimate
   until you have ~450 trades.

3. **The Kelly fraction flips sign inside the error bars.** At 85%/1:5, if the true win
   rate is 83% rather than 85%, f* goes from +10% to **−2%** — the correct action is to
   take the other side.

Kelly vs assumed win rate, 1:5 structure:

| p | 0.88 | 0.86 | **0.85** | 0.84 | 0.8333 | 0.82 | 0.80 |
|---|---|---|---|---|---|---|---|
| f* | +28% | +16% | **+10%** | +4% | 0% | −8% | −20% |

### 1.4 Why full Kelly is indefensible here — Thorp's own results

Edward Thorp, *The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market*
(Ch. 9 in *Handbook of Asset and Liability Management* Vol. 1, 2006; text at
<https://wayback.archive-it.org/5456/20240920155724/https://www.eecs.harvard.edu/cs286r/courses/fall12/papers/Thorpe_KellyCriterion2007.pdf>),
Eq. (7.13):

> Prob(V(t, cf\*)/V₀ ≤ x for some t) = x^(2/c − 1)

where `c` is the multiple of full Kelly. Consequences, computed:

| Kelly multiple | P(ever −10%) | P(ever −25%) | **P(ever −50%)** | P(ever −75%) | P(ever −90%) |
|---|---|---|---|---|---|
| **1.00× (full)** | 90.0% | 75.0% | **50.0%** | 25.0% | 10.0% |
| **0.50× (half)** | 72.9% | 42.2% | **12.5%** | 1.6% | 0.10% |
| **0.25× (quarter)** | 47.8% | 13.4% | **0.78%** | 0.01% | ~0 |
| 0.125× | 20.6% | 1.3% | ~0 | ~0 | ~0 |

Thorp's own words on the tradeoff (p. 31):

> "The chance of ever losing half the starting capital is 1/2 for f = f\* but only 1/8 for
> f = f\*/2. My gambling and investment experience … suggests that most people strongly
> prefer the increased safety and psychological comfort of 'half Kelly' (or some nearby
> value), in exchange for giving up 1/4 of their growth rate."

Half Kelly retains **75% of the growth rate** and cuts P(−50% drawdown) from 50% to 12.5%.

On estimation error specifically, Thorp (§7.3, "The case for fractional Kelly"):

> "A disaster occurs when m_t = .5 m_e but we choose f = 1.5 f\*_e. This combines
> overbetting f\*_e by 50% with the overestimate of m_e = 2 m_t. Then g = −.75 and we will
> be ruined."

and

> "To the extent m_e is an uncertain estimate of m_t, it is wise to assume m_t < m_e and to
> choose f < f\*_e by enough to prevent g ≤ 0."

and (p. 33, on why he deliberately underbet):

> "using too large an f\* and overbetting is much more severely penalized than using too
> small an f\* and underbetting."

**Growth rate as a function of bet size, 85%/1:5 structure** (log units per trade):

| multiple of Kelly | 0.25× | 0.50× | 0.75× | **1.00×** | 1.25× | 1.50× | **2.00×** |
|---|---|---|---|---|---|---|---|
| g | +0.000442 | +0.000764 | +0.000961 | **+0.001028** | +0.000959 | +0.000747 | **−0.000134** |

At **2× Kelly the growth rate is negative** — you lose money almost surely despite having a
genuine positive edge. Half Kelly gives up 26% of growth; double Kelly gives up all of it
and more. The penalty is grossly asymmetric.

### 1.5 Kelly under fat tails

Wysocki, *Sizing the Risk: Kelly, VIX, and Hybrid Approaches in Put-Writing on Index
Options*, arXiv:2508.16598 (26 Aug 2025), <https://arxiv.org/pdf/2508.16598> — studies
exactly this problem on SPX put-writing and concludes that full Kelly "underestimates
downside risk for short volatility positions," recommending **20–50% of theoretical Kelly**.

The deeper objection: Kelly requires the **distribution**, not a win rate. For a
negative-skew payoff the answer is dominated by the left-tail probability — the one
parameter that a short sample cannot pin down. Section 2 quantifies this.

### 1.6 Drawdown-constrained sizing (the practical alternative)

Rather than estimating Kelly and dividing, invert Thorp's Eq. (7.13). To hold
P(ever drawing down to fraction `a`) ≤ `q`, solve `a^(2/c−1) = q`:

```
c = 2 / (1 + ln(q)/ln(a))
```

Examples: to keep P(−50% drawdown) ≤ 5%, `c = 2/(1 + ln0.05/ln0.5) = 0.35` → **35% of
Kelly**. To keep P(−30%) ≤ 5%, `c ≈ 0.22`. This is a defensible way to pick the fraction,
and it does not require you to trust your edge estimate — only your ordering of it.

---

## 2. The estimation problem

### 2.1 How many trades to distinguish positive from negative expectancy?

For the 85% / 1:5 structure: per-trade mean +0.0200 units, SD 0.4285 units,
**t per trade = 0.0467**.

```
n for t = 1.96 :  1,763 trades
n for t = 2.00 :  1,836 trades
```

At one trade per week that is **35 years**. At five per week, **7 years** — and only if the
trades are independent, which overlapping index positions never are.

Sampling error on the win rate, against a breakeven of 83.33%:

| n trades | SE(p̂) | 95% CI on p | contains breakeven? |
|---|---|---|---|
| 20 | 0.0798 | [0.694, 1.000] | **yes** |
| 50 | 0.0505 | [0.751, 0.949] | **yes** |
| 100 | 0.0357 | [0.780, 0.920] | **yes** |
| 200 | 0.0252 | [0.801, 0.900] | **yes** |
| 500 | 0.0160 | [0.819, 0.881] | **yes** |
| 1,000 | 0.0113 | [0.828, 0.872] | **yes** |
| **1,836** | 0.0083 | [0.834, 0.866] | **no** — finally |

### 2.2 How often does a genuinely losing strategy look like a winner?

Probability that cumulative P&L is positive after n trades, 1:5 structure:

| true p | E per unit | n=20 | n=50 | n=100 | n=250 | n=500 | n=1000 |
|---|---|---|---|---|---|---|---|
| 0.8000 | **−0.040** (clearly negative) | 41.1% | 30.7% | 19.2% | 8.7% | 3.0% | 0.3% |
| 0.8167 | **−0.020** | 48.7% | 41.9% | 32.6% | 24.3% | 17.3% | 8.4% |
| 0.8333 | 0.000 (breakeven) | 56.6% | 54.2% | 49.4% | 49.6% | 51.3% | 49.7% |

**A strategy with clearly negative expectancy shows a profit 31% of the time after 50
trades and 19% of the time after 100 trades.** A year of "it's working" is not evidence.

Streak math at p=0.85: P(zero losses in 20 trades) = 3.9%; median first loss arrives at
**trade 5**. Losses are not rare enough to be surprising — they are frequent enough to be
normalized, and the strategy still fails.

### 2.3 The peso problem, demonstrated on the live quote

I priced the **actual** SPY 720/715 Sep-18-2026 put spread (43 DTE) under five different
data-generating processes and ran 4,000,000 Monte Carlo paths of the exact payoff.
All five produce a plausible-looking high win rate. Only the first is profitable.

| scenario | P(profit) | mean/spread | SD | t/trade | trades for t=2 |
|---|---|---|---|---|---|
| **A.** no jumps, realized vol 15% vs 18.75% implied, 8% drift, **no friction** | 92.65% | **+$3.08** | $121.05 | 0.0254 | **6,182** (119 yr weekly) |
| **A′.** same, **with $4 friction** | 92.64% | **−$0.92** | $121.05 | −0.0076 | negative |
| **B.** realized vol = implied 18.75%, $4 friction | 87.45% | **−$26.06** | $157.42 | −0.166 | negative |
| **C.** jump-diffusion, 1 jump/yr, mean −10%, $4 friction | 89.47% | **−$17.74** | $147.81 | −0.120 | negative |
| **D.** 0.5 jumps/yr, mean −18%, $4 friction | 91.10% | **−$9.56** | $136.03 | −0.070 | negative |
| **E.** **0.1 jumps/yr (once a decade), mean −30%**, $4 friction | **92.43%** | **−$2.35** | $123.86 | −0.019 | negative |

**Compare A and E.** Win rates 92.65% vs 92.43% — a difference of 0.22 percentage points.
One makes money, one loses it. The only difference is a jump that arrives **once every ten
years**. No live track record of realistic length can tell them apart, and the win rate —
the statistic every retail options seller quotes — is completely uninformative about which
world you are in.

Note also that in scenario A, **the friction alone ($4 round-trip bid/ask) flips a positive
edge negative.**

### 2.4 The academic evidence: Broadie, Chernov & Johannes

Broadie, M., Chernov, M., & Johannes, M., *Understanding Index Option Returns*,
Review of Financial Studies 22(11), 2009. Working paper (18 June 2008):
<https://www.columbia.edu/~mnb2/broadie/Assets/EOR_20080618.pdf>

Sample: **August 1987 – June 2005, 215 monthly observations.**

Average monthly returns to **buying** S&P 500 puts (Table 2):

| moneyness K/S | 0.94 (6% OTM) | 0.96 | 0.98 | 1.00 (ATM) | 1.02 |
|---|---|---|---|---|---|
| avg monthly return | −56.8% | −52.3% | −44.7% | −29.9% | −19.0% |
| **standard error** | **14.2%** | 12.3% | 10.6% | 8.8% | — |

Their central finding, in their own words (abstract):

> "The most puzzling finding in the existing literature, the large returns to writing
> out-of-the-money puts, is not inconsistent (i.e., is statistically insignificant) relative
> to the Black-Scholes model or the Heston stochastic volatility model **due to the extreme
> sampling uncertainty associated with put returns.**"

And on the magnitude of that uncertainty — for the average 6% OTM put return over
**215 months**:

> "the (5%, 95%) confidence band is −65% to +28%."

That is the confidence interval on the *mean*, after eighteen years of monthly data. It
spans zero comfortably. Their summary:

> "Short samples and complicated option return distributions imply that standard statistics
> are so noisy that little can be concluded by analyzing option returns."

On the sensitivity to a single tail observation (footnote 11):

> "In simulations of the Black-Scholes model, excluding the largest positive return lowers
> average put option returns by about 15% for the 6% OTM strike. This outcome illustrates
> the potential sample selection issues and how sensitive option returns are to the rare but
> extremely large positive returns generated by events such as the crash of 1987."

Once they account for finite-sample distributions, the p-value for 6% OTM put returns
against Black-Scholes rises to **just over 8%** — and p-values for deep OTM puts increase
**by more than 10,000×** relative to naive t-tests.

**If eighteen years of clean monthly data by three Columbia/LBS finance professors cannot
establish that put-selling has an edge, a retail track record cannot either.**

### 2.5 Sample-period dependence, measured

Using Cboe SPX daily data, I ran the 6.4%-OTM / 7.05%-OTM 43-day put spread on
non-overlapping monthly cycles. Breakeven win rate = 92.80%. Results depend entirely on
where you start the sample:

| sample | cycles | win rate | max-loss rate | EV per spread | EV % of risk |
|---|---|---|---|---|---|
| **1975–2026 (full)** | 618 | 93.53% | **5.34%** | **+$6.47** | +1.39% |
| 1990–2026 | 438 | 93.61% | 4.79% | +$8.03 | +1.73% |
| **2010–2026** | 198 | 94.95% | **3.03%** | **+$15.80** | **+3.40%** |
| 2013–2026 | 162 | 94.44% | 3.09% | +$14.40 | +3.10% |

**A backtest starting in 2010 reports 2.4× the edge of the full sample** — because it
excludes 1987 and 2008. Subtract $4 of friction and the full-sample edge falls to +$2.47
while the 2010+ sample still shows +$11.80. Which number you believe determines whether you
size at 0% or 10% of the account.

*(Caveat: this is an illustrative constant-strike/constant-credit exercise on index prices,
not a true backtest — real credit varies with the vol regime. It is meant to show
sample-period sensitivity, not to estimate the edge.)*

---

## 3. Probability of ruin at each sizing

Monte Carlo, 60,000 paths × 200 trades. **Ruin defined as falling to 20% of starting
equity** — for a $3,000 account that is $600, below which you cannot post margin for even
one 5-wide SPY spread, so the strategy is over regardless.

### 3.1 Profile 1 — 65% win / 1:1 (full Kelly = 30%)

| risk per trade | × Kelly | **P(ruin)** | **P(−50% DD)** | median terminal multiple |
|---|---|---|---|---|
| **100%** | 3.33× | **100.00%** | 100.00% | 0.000× |
| **50%** | 1.67× | **67.38%** | 100.00% | 0.178× |
| **25%** | 0.83× | **8.39%** | 100.00% | 7,121× |
| **10%** | 0.33× | **0.02%** | 36.90% | 150.7× |
| 5% | 0.17× | 0.00% | 0.57% | 15.7× |
| 2% | 0.07× | 0.00% | 0.00% | 3.19× |
| 1% | 0.03× | 0.00% | 0.00% | 1.80× |

Note the trap at 25%: it has the highest median outcome of any row (7,121×) *and* an 8.4%
chance of ruin plus a **certainty** of a 50% drawdown. Median ≠ survivable.

### 3.2 Profile 2 — 85% win / 1:5 credit spread (full Kelly = 10%)

| risk per trade | × Kelly | **P(ruin)** | **P(−50% DD)** | median terminal multiple |
|---|---|---|---|---|
| **100%** | 10.0× | **100.00%** | 100.00% | 0.000× |
| **50%** | 5.0× | **90.44%** | 100.00% | 0.164× |
| **25%** | 2.5× | **38.40%** | 99.37% | 0.715× |
| **10%** (= full Kelly) | 1.0× | **0.63%** | 40.08% | 1.228× |
| 5% (half Kelly) | 0.5× | 0.00% | 2.20% | 1.165× |
| 2% | 0.2× | 0.00% | 0.00% | 1.075× |
| 1% | 0.1× | 0.00% | 0.00% | 1.039× |

### 3.3 Profile 3 — the live SPY quote, 92% win / 1:12.9 (Kelly is negative)

| risk per trade | **P(ruin)** | **P(−50% DD)** | median terminal multiple |
|---|---|---|---|
| **100%** | **100.00%** | 100.00% | 0.000× |
| **50%** | **89.77%** | 100.00% | 0.163× |
| **25%** | **41.61%** | 95.73% | 0.344× |
| **10%** | **0.33%** | 34.87% | **0.768×** |
| 5% | 0.00% | 1.17% | 0.897× |
| 2% | 0.00% | 0.00% | 0.963× |
| 1% | 0.00% | 0.00% | 0.982× |

**Every median is below 1.0.** When the structure has no edge, small sizing does not make
it profitable — it only makes the bleed slower. Prudent sizing is not a substitute for an
edge.

### 3.4 Consecutive-loss arithmetic

| risk per trade | losses to −50% | losses to −80% | P(that streak) at 15% loss rate |
|---|---|---|---|
| 100% | 1 | 1 | 1.5 × 10⁻¹ |
| 50% | 1 | 3 | 1.5 × 10⁻¹ / 3.4 × 10⁻³ |
| 25% | 3 | 6 | 3.4 × 10⁻³ / 1.1 × 10⁻⁵ |
| 10% | 7 | 16 | 1.7 × 10⁻⁶ / 6.6 × 10⁻¹⁴ |
| 5% | 14 | 32 | 2.9 × 10⁻¹² |
| 2% | 35 | 80 | 1.5 × 10⁻²⁹ |

At 50% per trade, **one loss halves the account.** At 100%, one loss ends it. The
independence assumption here is generous — in a crash, correlated positions lose together,
so the true streak probabilities are far higher than the table shows.

---

## 4. What margin does to a small account

### 4.1 The requirement

For a vertical credit spread the buying-power reduction is

```
BPR = (strike width × 100) − credit received  =  the maximum loss
```

This is **cash held, not borrowed** — it is fully collateralized. But it is the whole
position size, and it cannot be reduced.

A margin account is required for spreads, and FINRA Rule 4210 sets a **$2,000 minimum
equity** for a margin account. A $2,000 account is therefore at the absolute floor of
eligibility.

### 4.2 Live numbers, SPY = $769.21 (2026-08-06)

**One SPY option contract = 100 shares = $76,921 of notional.**

| account | notional per contract | as multiple of account |
|---|---|---|
| $2,000 | $76,921 | **38.5×** |
| $3,000 | $76,921 | **25.6×** |
| $5,000 | $76,921 | **15.4×** |

Actual quotes, SPY 2026-09-18 expiry (43 DTE), captured live:

| contract | bid | ask | IV | delta | open interest | volume |
|---|---|---|---|---|---|---|
| 720 put | 3.30 | 3.32 | 18.75% | −0.130 | 30,944 | 3,036 |
| 719 put | 3.22 | 3.24 | 18.86% | −0.127 | **2,869** | **37** |
| 715 put | 2.94 | 2.96 | 19.33% | −0.115 | 30,782 | 4,169 |

(Note the 719 strike has 1/10th the open interest and 1/100th the volume of the round
strikes — non-round strikes are not really tradeable.)

### 4.3 The granularity trap

| structure | credit | max loss | % of $2,000 | % of $3,000 | % of $5,000 |
|---|---|---|---|---|---|
| **720/715 (5-wide)** | $34–36 | **$464–466** | **23.2%** | **15.5%** | **9.3%** |
| **720/719 (1-wide)** | $6–8 | **$92–94** | **4.6%** | **3.1%** | **1.8%** |
| 10-wide | ~$150 | ~$850 | 42.5% | 28.3% | 17.0% |

Against the honest Kelly estimate of 9.55% (scenario A, the *optimistic* one):

| account | Kelly risk budget | 5-wide spreads that fits | actual minimum |
|---|---|---|---|
| $2,000 | $191 | **0.41 contracts** | 1 contract = 23.2% = **2.4× Kelly** |
| $3,000 | $286 | **0.62 contracts** | 1 contract = 15.5% = **1.62× Kelly** |
| $5,000 | $478 | **1.03 contracts** | 1 contract = 9.3% = 0.97× Kelly |
| $25,000 | $2,388 | 5.15 contracts | fine |

**You cannot trade 0.62 of a contract.** A $2k–$3k account taking a single 5-wide SPY
spread is at **1.6× to 2.4× full Kelly** — into the region where Thorp's math says growth
turns negative. There is no way to size down except by narrowing the spread.

### 4.4 Why narrowing doesn't rescue it — friction

The 1-wide gets you to 3.1% of a $3,000 account. But:

| structure | credit | round-trip bid/ask cost (2 legs × 2 ways × $1) | as % of credit |
|---|---|---|---|
| 5-wide at mid | $36 | $4 | **11.1%** |
| 5-wide crossing the spread | $34 | $4 | **11.8%** |
| **1-wide at mid** | **$8** | **$4** | **50.0%** |
| **1-wide crossing the spread** | **$6** | **$4** | **66.7%** |

Commissions on top (round trip, 1 spread = 2 contracts each way):

| broker | cost | % of $34 credit | % of $6 credit |
|---|---|---|---|
| **Robinhood** ($0 commission; ~$0.02/contract regulatory fees) | **~$0.08** | 0.2% | 1.3% |
| Schwab / Fidelity ($0.65/contract) | $2.60 | 7.6% | 43.3% |
| tastytrade ($1/contract open, $0 close) | $4.00 | 11.8% | 66.7% |

Robinhood's $0 commission is a genuine and material advantage at this account size — it is
the only reason the 1-wide is not immediately hopeless. **But the bid/ask cost of $4 is
unavoidable at any broker**, and against a $6–8 credit it consumes half to two-thirds of
the premium. Recall from §2.3 that $4 of friction alone flipped the *optimistic* scenario
from +$3.08 to −$0.92.

**This is the core small-account bind:** the 5-wide is affordable but too large (1.6–2.4×
Kelly); the 1-wide is correctly sized but its edge is entirely eaten by the spread. There
is no width that is both survivable and profitable at $3,000.

### 4.5 Capacity

| spreads held | capital at risk | % of $3,000 | credit collected | annualized if you never lose |
|---|---|---|---|---|
| 1 | $466 | 15.5% | $34 | 13.6% |
| 2 | $932 | 31.1% | $68 | 27.2% |
| 3 | $1,398 | 46.6% | $102 | 40.8% |
| 6 | $2,796 | 93.2% | $204 | 81.6% |

The right-hand column is the number that seduces people — and it is conditional on
**never taking a single loss**. One max-loss cycle at 6 contracts is −$2,796, i.e. −93% of
the account. See §5.

### 4.6 Pattern Day Trader rule — **this changed in 2026**

**FINRA Regulatory Notice 26-10** (published 20 April 2026), *"FINRA Adopts New Intraday
Margin Standards to Replace the Day Trading Margin Requirements"*:
<https://www.finra.org/rules-guidance/notices/26-10>
SEC approval: Exchange Act Release No. 105226 (14 April 2026), File No. SR-FINRA-2025-017.
**Effective 4 June 2026**, phase-in through 20 October 2027.

FINRA eliminated:
- the "pattern day trader" designation,
- the day-trade count test (4 trades in 5 days / 6% of total trades),
- **the $25,000 pattern day trader minimum equity requirement.**

Rule text: the amendments "eliminate paragraph (f)(8)(B) together with associated
provisions relating to the day trading margin requirements under paragraphs (b), (f)(10)
and (g)(13)."

**Replaced by:** an "intraday margin deficit" calculation per margin account when
IML-reducing transactions occur. No minimum equity amount is specified. Deficits must be
satisfied "as promptly as possible"; a **90-day freeze** applies if not satisfied by the
**fifth business day**; deficits below the lesser of 5% of account equity or $1,000 don't
trigger the freeze.

**Implication:** the $25k PDT barrier is gone as of June 2026, so a $3,000 account can now
day-trade without being flagged. This removes a *constraint*, not a *risk* — it makes it
easier to over-trade a small account, not safer. The $2,000 Reg T / Rule 4210(b) margin
account minimum still applies.

*(Verify current broker implementation — brokers are phasing this in through Oct 2027 and
may apply stricter house rules in the interim.)*

### 4.7 Robinhood-specific constraints

Options levels (<https://robinhood.com/us/en/support/articles/options-knowledge-center/>):

- **Level 2:** long calls/puts, covered calls, cash-secured puts.
- **Level 3:** adds long straddles/strangles, call and put debit/credit spreads,
  **condors and butterflies**.
- **Naked selling is prohibited at every level.** Robinhood's own language: *"Robinhood
  doesn't allow selling uncovered options, because there's no limit to the amount of money
  you could lose with some strategies."*

This is a real structural protection. It makes the XIV / Cordier / LJM failure mode
(§5.2, §5.3) unavailable to this account — losses are capped at the spread width.

**Forced close-out timing (confirmed from Robinhood's own API):** the SPY option chain
returns `sellout_time_to_expiration: 1800` seconds, and each contract carries an explicit
`sellout_datetime` — for the 2026-09-18 expiry that is **2026-09-18T19:45:00Z = 3:45pm ET**.
Robinhood's policy page states they "may attempt to sell the contract in the market for you
within the last 30 minutes before the market closes on the option's expiration date," and
that they "may take action on a position outside of that 30-minute window based on market
conditions."

**You do not control your own exit on expiration day.** In a fast market that is a forced
liquidation at the worst available price.

---

## 5. Documented blowups as loss-to-credit multiples

### 5.1 The defined-risk multiple

For the live SPY 720/715 spread: max loss $464 ÷ credit $36 = **12.9×**.

**One max-loss cycle erases 12.9 winning cycles = 1.07 years of flawless monthly premium
collection.**

| structure | credit | max loss | multiple | months of wins erased |
|---|---|---|---|---|
| SPY 5-wide, $36 credit (**live quote**) | $36 | $464 | **12.9×** | 12.9 |
| SPY 5-wide, $50 credit (10% of width) | $50 | $450 | 9.0× | 9.0 |
| SPY 5-wide, $100 credit (20% of width) | $100 | $400 | 4.0× | 4.0 |
| SPY 1-wide, $8 credit | $8 | $92 | 11.5× | 11.5 |
| SPY 10-wide, $150 credit | $150 | $850 | 5.7× | 5.7 |

**Note the pattern: the higher the win rate, the higher the loss-to-credit multiple.** They
are the same fact stated twice. You cannot get a high win rate and a low loss multiple.

### 5.2 Episodes that take that spread to max loss

All figures computed from Cboe `SPX_History.csv` and `VIX_History.csv`:

| episode | window | SPX peak-to-trough | trading days | 6.4%-OTM spread |
|---|---|---|---|---|
| **GFC** | 2007-10-09 → 2009-03-09 | **−56.78%** | 355 | **MAX LOSS (12.9×)** |
| **Feb 2018 Volmageddon** | 2018-01-26 → 2018-02-08 | **−10.16%** | **9** | **MAX LOSS (12.9×)** |
| **Mar 2020 COVID** | 2020-02-19 → 2020-03-23 | **−33.92%** | **23** | **MAX LOSS (12.9×)** |
| **Aug 2024 yen carry** | 2024-07-16 → 2024-08-05 | **−8.49%** | 14 | **MAX LOSS (12.9×)** |
| **Apr 2025 tariffs** | 2025-02-19 → 2025-04-08 | **−18.90%** | 34 | **MAX LOSS (12.9×)** |

**Five max-loss events in ~19 years ≈ one every 3.8 years**, each costing 12.9 months of
perfect premium collection. Note that 2018 and 2024 required only **−10.2% and −8.5%** —
you do not need a crash, just an ordinary correction.

VIX moves on those dates (Cboe primary data):

| date | VIX prior close | VIX close | change | intraday high |
|---|---|---|---|---|
| **2018-02-05** | 17.31 | **37.32** | **+115.60%** | 38.80 |
| 2018-02-06 | 37.32 | 29.98 | −19.67% | **50.30** |
| **2020-03-16** | 57.83 | **82.69** | **+42.99%** | 83.56 |
| 2020-03-18 | 75.91 | 76.45 | +0.71% | **85.47** |
| **2024-08-05** | 23.39 | **38.57** | **+64.90%** | **65.73** |
| 2008-11-20 | 74.26 | **80.86** | +8.89% | 81.48 |
| 2008-10-24 | 67.80 | 79.13 | +16.71% | **89.53** (all-time intraday high) |

**Confirmed from Cboe's own file: 2018-02-05 is the largest one-day percentage increase in
VIX close in the entire history of the index (since 1990).**

Top 5 one-day VIX increases ever: 2018-02-05 (+115.60%), 2024-12-18 (+74.04%),
2024-08-05 (+64.90%), 2007-02-27 (+64.22%), 2021-01-27 (+61.64%).

Highest VIX closes ever: 2020-03-16 (**82.69**), 2008-11-20 (80.86), 2008-10-27 (80.06).

SPX single-day: 2018-02-05 **−4.10%**; 2020-03-16 **−11.98%**; 2024-08-05 −3.00%.

### 5.3 The undefined-risk multiple: unbounded

**XIV (VelocityShares Daily Inverse VIX Short-Term ETN), February 2018.**
Primary source — Credit Suisse media release filed with the SEC, 6 February 2018:
<https://www.sec.gov/Archives/edgar/data/1053092/000095010318001572/dp86358_ex9901.htm>

> "Because the intraday indicative value of XIV on February 5, 2018 was equal to or less
> than twenty percent of the prior day's closing indicative value, an acceleration event has
> occurred."

> "On February 2, 2018, the closing indicative value was $108.3681."

Acceleration date **21 February 2018**; accelerated valuation date 15 February 2018.
Nasdaq suspended trading after the close on 15 February 2018 and instituted delisting
proceedings (Credit Suisse release, 14 February 2018:
<https://www.sec.gov/Archives/edgar/data/1053092/000095010318002069/dp86855_ex9901.htm>).

XIV's closing indicative value on 5 February 2018 is widely reported as **$4.22**, i.e.
**−96.1%** from $108.3681 **in one day**. *(The $108.3681 and the ≤20% trigger are from the
primary filing; the $4.22 is secondary reporting — treat the exact figure as
approximate, the ≥80% collapse is established by the filing itself.)*

**Loss-to-credit multiple: total. The position could not be exited.**

**LJM Preservation & Growth Fund, February 2018** — a *registered mutual fund* selling OTM
options on S&P 500 futures. Reported **−80% to −82% over two days** (5–6 February 2018);
liquidated effective 29 March 2018. SEC enforcement against LJM Funds Management, LJM
Partners, Anthony Caine and Anish Parvataneni: SEC Litigation Release
<https://www.sec.gov/enforcement-litigation/litigation-releases/lr-26338>, complaint
<https://www.sec.gov/files/litigation/complaints/2021/comp-pr2021-89.pdf>. Allegation:
fraudulently misleading investors and the board about risk management and portfolio risk.
Reported penalties: Caine $500,000 and a 3-year bar; Parvataneni $200,000 and a 1-year bar.
*(Loss percentages and AUM here are from secondary reporting; I was unable to verify them
against the fund's N-CEN/N-CSR filings within this session — flagged as UNVERIFIED.)*

**OptionSellers.com / James Cordier, November 2018** — naked short calls on NYMEX natural
gas. Natural gas futures rose ~18% on 14 November 2018 to a four-year high; roughly +34%
over three weeks. Reported: **~290 client accounts lost effectively everything, and many
owed additional debit balances to clearing broker INTL FCStone after liquidation** —
i.e. **losses exceeding 100% of account equity**. Total reported ~$150 million.
Reuters: <https://www.reuters.com/article/business/optionsellerscom-investors-hit-by-natgas-swings-intl-fcstone-idUSL2N1XU1BP/>;
FT: <https://www.ft.com/content/b7c525f6-ec44-11e8-89c8-d36339d835c0>;
CNBC: <https://www.cnbc.com/2018/11/21/a-risky-natural-gas-bet-gone-awry-leads-to-weepy-youtube-confessional.html>
*(Client counts and dollar totals are secondary reporting; CFTC/NFA case numbers
UNVERIFIED in this session.)*

**Loss-to-credit multiple: greater than infinity — you end owing money.**

**Robinhood's Level 3 restriction structurally prevents this failure mode for this
account.** That is the single most important protective feature available here.

---

## 6. Return vs drawdown: the benchmark indices

Computed from Cboe primary daily files, downloaded 2026-08-06. **Data-quality note:** the
pre-2007 PUT file and pre-2007 CNDR file contain multi-year gaps, so daily-frequency
volatility and pre-2007 drawdowns from these files are unreliable. Endpoint-to-endpoint
annualized returns are valid regardless of gaps; volatilities below are computed from
**monthly** data over the dense period only.

| index | file range | annualized return | ann. vol (monthly, dense period) | worst month |
|---|---|---|---|---|
| **PUT** (S&P 500 PutWrite) | 1991-03-04 → 2026-08-06 | **+9.31%** | 10.76% (since 2007) | **−17.65%** |
| **BXM** (S&P 500 BuyWrite) | 2002-03-22 → 2026-08-06 | **+6.17%** | 10.67% | **−15.01%** |
| **CNDR** (S&P 500 Iron Condor) | 1986-06-20 → 2026-08-06 | **+5.32%** | 7.02% | **−9.91%** |

### Maximum drawdowns

| index | **2008 GFC** | peak → trough | **Feb–Mar 2020** | peak → trough |
|---|---|---|---|---|
| **PUT** | **−37.09%** | 2008-05-19 (1029.68) → 2009-03-09 (647.73) | **−28.93%** | 2020-02-20 (2018.14) → 2020-03-23 (1434.38) |
| **BXM** | **−40.14%** | 2007-12-26 (859.35) → 2009-03-09 (514.37) | **−30.26%** | 2020-02-20 (1548.81) → 2020-03-23 (1080.18) |
| **CNDR** | −10.57% | 2008-09-25 → 2008-12-08 | −12.72% | 2020-01-07 → 2020-06-26 |
| SPX (ref) | **−56.78%** | 2007-10-09 → 2009-03-09 | **−33.92%** | 2020-02-19 → 2020-03-23 (23 days) |

Other episodes:

| index | Feb 2018 | Aug 2024 | Apr 2025 |
|---|---|---|---|
| PUT | −7.64% | −4.96% | −15.06% |
| BXM | −7.72% | −5.07% | −15.46% |
| CNDR | −8.30% | −3.23% | −10.25% |

### The ratio that matters

| index | annual return | 2008 DD | years of return wiped out | on **$3,000** |
|---|---|---|---|---|
| **PUT** | +9.31% | **−37.09%** | **5.2 years** | **+$279/yr vs −$1,113** |
| **BXM** | +6.17% | **−40.14%** | **8.6 years** | **+$185/yr vs −$1,204** |
| CNDR | +5.32% | −10.57% | 2.2 years | +$160/yr vs −$317 |

Recovery arithmetic: after PUT's −37.09% you need **+58.9%** to break even, which at
9.31%/yr takes **5.2 years of flawless compounding**. After BXM's −40.14% you need
**+67.1%**, which at 6.17%/yr takes **8.6 years**.

**These are the professionally-run, fully-collateralized, index-level versions of the
strategy — no leverage, no assignment risk, no bid/ask, no commissions, perfect execution.
They earn 5–9%/year and lose 30–40% in a crash.** A retail account trading the same
exposure with 1-contract granularity, retail fills and forced liquidations does strictly
worse.

*(BXM benchmark caveat: the Cboe file starts 2002-03-22 though the index is backdated to
1986/1988 in Cboe publications; Whaley (2002) is the founding study. Cboe-sponsored
performance studies by Wilshire and Fund Evaluation Group are **marketing-adjacent** and
should be treated with suspicion — they were commissioned by the exchange that lists the
products.)*

---

## 7. Assignment and pin risk on a small account

### 7.1 The mechanism

SPY options are **American-style, physically settled** on the ETF. The short leg can be
assigned at any time before expiration. Two classic triggers:

1. **Ex-dividend assignment on short ITM calls.** SPY pays quarterly with ex-dividend dates
   on the **third Friday of March, June, September and December** — the same day as standard
   monthly option expiration. Anyone holding a short ITM call into that date faces
   dividend-capture assignment.
2. **Deep ITM short puts** when remaining extrinsic value falls below the cost of carry.

### 7.2 What actually happens to a $3,000 account

**100 shares of SPY at $769.21 = $76,921.** That is **25.6× a $3,000 account.**

Robinhood's own policy page
(<https://robinhood.com/us/en/support/articles/expiration-exercise-and-assignment/>) — the
critical passage:

> "we can't process an early assignment before the end of the trading day, which means we
> can't exercise the long leg until the next trading day (at the earliest)."

And:

> "you'll likely be long or short the stock the following trading day, potentially resulting
> in an account deficit or margin call … [this can produce] a gain or loss that's greater
> than the theoretical max gain or loss."

**Read that last clause carefully. "Defined risk" is defined only at expiration, and only
if both legs resolve together.** If the short leg is assigned and the long leg is not yet
exercisable, you hold $76,921 of stock overnight in a $3,000 account. The long put still
exists and still has value, so the *economic* loss remains bounded — but the *account* is in
a large Reg T deficit, and the broker resolves that by liquidating, at its timing, not
yours.

Robinhood exercises long options **$0.01 or more in-the-money** at expiration if the account
can support it; otherwise they "may attempt to sell the contract in the market for you
within the last 30 minutes before the market closes." Do-not-exercise cutoff is 5:00pm ET.

### 7.3 Pin risk

If SPY closes at or very near your short strike, you do not learn until after hours whether
you were assigned. The OCC allocates exercise notices **randomly**. You can end the week
either flat or holding an unhedged 100-share position — a $76,921 exposure to Monday's
open, decided by a coin flip you don't see until Friday night.

FINRA's own findings on exactly this (below): Robinhood told customers both legs would
"automatically expire worthless, so you don't need to worry about checking the app," which
FINRA found **false** because the short option "could still be assigned (e.g., by going in
the money after hours)."

### 7.4 The documented case

**FINRA Letter of Acceptance, Waiver and Consent No. 2020066971201**, Robinhood Financial
LLC, 30 June 2021.
<https://www.finra.org/sites/default/files/2021-06/robinhood-financial-awc-063021.pdf>

Sanctions: censure, **$57,000,000 fine**, **$12,598,445.16 restitution** plus interest
(≈ $70M total — the largest financial penalty FINRA had ordered).

Findings directly on point (quoting the AWC):

> "Robinhood has allowed approximately 818,000 customers who had been approved for options
> trading—either 'Instant' customers or 'Gold' customers with margin 'disabled'—to make
> trades, such as options spreads, that could and often did automatically trigger the use of
> margin. For instance, the firm permitted those customers to enter into options spreads
> which, if assigned on the short leg, required the use of margin to satisfy the assignment."

> "Customer A, a 20-year-old 'Robinhood Gold' customer who had turned margin 'off,' took his
> own life in June 2020. In a note found after his death, he expressed confusion as to how
> he could have used margin to purchase securities upon assignment of the short leg of an
> options spread because, he believed, he had not 'turned on' margin in his account."

> "the day before Customer A died, Robinhood displayed to the customer a cash balance of
> –$730,165.72, even though the customer's account's actual cash balance was –$365,530.60.
> Customer A had incurred the –$365,530.60 balance after being assigned early on the short
> leg of an options spread transaction."

Another customer received a **$271,986.64 margin call** following an options assignment.
In total, **630 customers incurred losses of $5,731,520.67** from Robinhood's
misrepresentations about spreads.

This is the canonical case: a **defined-risk spread** in a small retail account produced a
mid-six-figure displayed deficit through ordinary early assignment. The maximum *economic*
loss was bounded; the *experience* was not.

### 7.5 Mitigation: XSP

Cboe **XSP (Mini-SPX)**: <https://www.cboe.com/tradable_products/sp_500/mini_spx_options/>
— 1/10th the size of SPX, **European-style** ("Options can only be exercised at expiration,
providing certainty and **eliminating early assignment risk**"), **cash-settled** ("without
the need to deliver or receive unwanted shares"), and eligible for **Section 1256 60/40 tax
treatment**.

**Important correction to a common belief:** XSP does **not** reduce notional versus SPY.
SPX closed at **7,709.96** on 2026-08-06 (Cboe `SPX_History.csv`), so XSP = 771.00 and one
contract is 771.00 × $100 = **$77,100** — within 0.2% of SPY's $76,921. The advantage of XSP
is **exercise style and settlement, not size.** It removes assignment and pin risk entirely.
It does not solve the granularity problem.

Cboe **Nanos** ($1 multiplier) — the product page
`https://www.cboe.com/tradable_products/sp_500/nanos/` now returns **HTTP 404**, consistent
with the product having been discontinued. Search results describing Nanos as active appear
to be stale SEO content. **Treat Nanos as unavailable; verify with the broker before
relying on it.**

Whether Robinhood supports XSP for this account needs to be confirmed directly — index
options approval may differ from equity options approval.

---

## 8. Conclusions

1. **The correct Kelly fraction for the live SPY credit spread is ~9.6% of the account
   under optimistic assumptions and negative under mildly pessimistic ones.** The estimate
   is not stable enough to size on.

2. **A $2,000–$3,000 account cannot size below full Kelly in a 5-wide SPY spread.** One
   contract is 15.5–23.2% of the account = 1.6–2.4× Kelly. Narrowing to a 1-wide fixes the
   sizing (3.1%) but the $4 round-trip bid/ask consumes 50–67% of the $6–8 credit. **There
   is no width that is simultaneously survivable and profitable at this account size.**

3. **Win rate is not evidence.** A 90%-win/1:9 condor has exactly zero edge by
   construction. Scenarios A and E in §2.3 differ by 0.22pp of win rate and by the sign of
   the expectancy. A clearly-losing strategy shows a profit 31% of the time after 50 trades.

4. **You cannot validate this strategy in a human lifetime.** 6,182 trades for t=2 on the
   optimistic scenario = 119 years of weekly trades. Broadie–Chernov–Johannes could not do
   it with 215 months of clean data and a (5%, 95%) band of −65% to +28%.

5. **The professionally-run version earns 5–9%/yr and draws down 29–40% in a crash.** On
   $3,000: +$279/year against −$1,113, needing 5.2 years to recover.

6. **Sizing discipline cannot manufacture an edge.** In §3.3, every median outcome is below
   1.0× at every sizing. Small size makes a negative-edge strategy lose slowly, not
   profitably.

7. **What sizing does buy** is survival while you find out. If the strategy is traded at
   all, **quarter-Kelly to half-Kelly** — which at these Kelly estimates means **2–5% of the
   account at risk per trade**, i.e. **$60–$150 on a $3,000 account** — keeps P(−50%
   drawdown) at 0.6–2.2% instead of 40%. That budget does not buy a 5-wide SPY spread.

8. **Two genuine structural protections exist here:** Robinhood's prohibition on naked
   selling (caps the failure mode below the XIV/Cordier/LJM catastrophe), and XSP's
   European cash settlement (eliminates assignment and pin risk). Neither solves the
   granularity problem.

9. **The PDT rule was eliminated effective 4 June 2026** (FINRA Reg Notice 26-10). This
   removes a constraint on small accounts; it does not reduce any risk in this document.

**On the 50%/week goal:** the arithmetic case against it is already made. What this research
adds is that the *only* structure that plausibly delivers a high win rate — short
premium — has an expected annual return in the single digits when run correctly, a
loss-to-credit multiple of ~13×, a crash drawdown of 30–40%, and a minimum position size
that a $3,000 account cannot fit under its own Kelly limit. The gap is not one of
optimization. It is roughly four orders of magnitude.

---

## Appendix: sources

**Primary market data** (downloaded 2026-08-06)
- Cboe daily index history: `https://cdn.cboe.com/api/global/us_indices/daily_prices/SPX_History.csv`
  (also `VIX_`, `PUT_`, `BXM_`, `CNDR_`)
- Live SPY equity and option quotes, 2026-08-06 18:16 UTC, via Robinhood

**Regulatory / primary filings**
- FINRA Regulatory Notice 26-10 (20 Apr 2026), PDT elimination — <https://www.finra.org/rules-guidance/notices/26-10>
  (SEC Rel. No. 105226, 14 Apr 2026; File No. SR-FINRA-2025-017)
- FINRA AWC No. 2020066971201, Robinhood Financial LLC (30 Jun 2021) — <https://www.finra.org/sites/default/files/2021-06/robinhood-financial-awc-063021.pdf>
- Credit Suisse XIV event acceleration, SEC EDGAR (6 Feb 2018) — <https://www.sec.gov/Archives/edgar/data/1053092/000095010318001572/dp86358_ex9901.htm>
- Credit Suisse XIV Nasdaq delisting, SEC EDGAR (14 Feb 2018) — <https://www.sec.gov/Archives/edgar/data/1053092/000095010318002069/dp86855_ex9901.htm>
- SEC Litigation Release LR-26338, LJM — <https://www.sec.gov/enforcement-litigation/litigation-releases/lr-26338> and <https://www.sec.gov/files/litigation/complaints/2021/comp-pr2021-89.pdf>

**Academic**
- Broadie, Chernov & Johannes, *Understanding Index Option Returns*, RFS 22(11) 2009; WP 18 Jun 2008 — <https://www.columbia.edu/~mnb2/broadie/Assets/EOR_20080618.pdf>
- Thorp, *The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market* (2006) — <https://wayback.archive-it.org/5456/20240920155724/https://www.eecs.harvard.edu/cs286r/courses/fall12/papers/Thorpe_KellyCriterion2007.pdf>
- MacLean, Thorp & Ziemba, *Good and Bad Properties of the Kelly Criterion*, Quantitative Finance 2010
- MacLean, Ziemba & Blazenko, *Growth versus Security in Dynamic Investment Analysis*, Management Science 38(11) 1992, 1562–1585
- Chopra & Ziemba, *The Effect of Errors in Means, Variances, and Covariances on Optimal Portfolio Choice*, JPM 19(2) Winter 1993
- Wysocki, *Sizing the Risk: Kelly, VIX, and Hybrid Approaches in Put-Writing on Index Options*, arXiv:2508.16598 (2025) — <https://arxiv.org/pdf/2508.16598>

**Broker / exchange documentation**
- Robinhood options levels — <https://robinhood.com/us/en/support/articles/options-knowledge-center/>
- Robinhood expiration/exercise/assignment — <https://robinhood.com/us/en/support/articles/expiration-exercise-and-assignment/>
- Cboe XSP (Mini-SPX) — <https://www.cboe.com/tradable_products/sp_500/mini_spx_options/>

**Secondary (loss figures not independently verified)**
- Reuters on OptionSellers.com — <https://www.reuters.com/article/business/optionsellerscom-investors-hit-by-natgas-swings-intl-fcstone-idUSL2N1XU1BP/>
- FT — <https://www.ft.com/content/b7c525f6-ec44-11e8-89c8-d36339d835c0>
- CNBC — <https://www.cnbc.com/2018/11/21/a-risky-natural-gas-bet-gone-awry-leads-to-weepy-youtube-confessional.html>

**Flagged as marketing-adjacent:** Cboe-commissioned performance studies of PUT/BXM by
Wilshire Associates and Fund Evaluation Group; any option-selling "win rate" statistics
published by brokers, trading educators, or newsletter vendors.

**Unresolved in this session:** exact LJM NAV series and AUM from SEC filings; CFTC/NFA case
numbers for Cordier/OptionSellers; SVXY's exact one-day loss and the ProShares −1x → −0.5x
leverage change date; Malachite Capital and Allianz Structured Alpha figures; Cboe's own
published PUT/BXM factsheet drawdown numbers for cross-checking mine.
