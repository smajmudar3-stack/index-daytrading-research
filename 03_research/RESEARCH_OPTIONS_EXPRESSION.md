# How To Express a Swing-Horizon Directional View in Options

**Question:** given a signal with modest directional accuracy at a 20–60 day horizon, which
option structure preserves the edge and which structures eat it — for a $2–5k Robinhood
account, level 3, on liquid ETFs and megacaps?

**Motivating fact:** a 57.9%-win-rate signal expressed as a call credit spread returned
*exactly zero*; a 60%-accurate signal on a long put returned −6.56%. Structure choice
destroyed the edge.

Everything below is **measured**, not cited, unless explicitly marked as literature:

- **Live pricing:** SPY/QQQ/IWM/XLF/XLE/NVDA/AAPL/XSP option chains pulled from the
  Robinhood API on **2026-08-06 14:08 ET**, expiry 2026-09-18 (43 DTE). SPY = 768.76.
- **Historical:** `data/opt_eod/SPY_options.parquet` — **24,681,665 contract-days** of SPY
  EOD chains with bid, ask, delta, IV, greeks, OI, **2008-01-02 → 2025-12-12**
  (5,990,568 rows after filtering to 15–75 DTE and bid > $0.05).

Scripts: `breakeven4.py` (model), `measure.py` (measurements), `addendum.py` (equivalence
and sizing tests), `backtest.py` + `sizing.py` (18-year realized backtest) — in the session
scratchpad.

### The answer, up front

**The signal is the problem, not the structure.** SPY rises over 43 days **67.1%** of the
time, so a 57.9–60% directional signal is worse than always guessing "up."

**A 60%-accurate direction-only signal can be expressed profitably in shares and in almost
nothing else.** Required accuracy, sign-only signal, at measured retail costs (§3):

| Shares | 0.80Δ call | 0.70Δ call | ZEBRA | debit spread | 0.50Δ call | 0.30Δ call | 0.16Δ call |
|---|---|---|---|---|---|---|---|
| **56.0%** | 63.2% | 64.2% | 63.3% | 61.9% | 67.0% | 72.0% | **79.0%** |

**Break-even accuracy falls monotonically as delta rises** — the lower the delta, the more
*magnitude* information you must supply, and a sign classifier supplies none. Shares are
also the only vehicle whose requirement is insensitive to the volatility-premium parameter
(±0.1pp vs ±22pp for a 0.16Δ call).

**And the short-premium side fails on risk, not on expectancy.** Actually trading a
25-delta put credit spread monthly for 18 years on real chains produced an **87% win rate,
+3.99%/trade, t = 1.82 — and a −100% drawdown at full size, losing to SPY buy-and-hold at
every position size tested.**

---

## 1. The finding that reframes the whole question

Before any structure question: **what is the base rate?**

Measured from 18 years of reconstructed SPY spot (put-call parity on the near-ATM strike),
overlapping windows:

| Horizon | P(SPY up) | mean return | median return | n |
|---|---|---|---|---|
| 21 calendar days (15 trd) | **65.5%** | +0.62% | +1.20% | 4,498 |
| 30 calendar days (21 trd) | **66.2%** | +0.87% | +1.55% | 4,492 |
| **43 calendar days (30 trd)** | **67.1%** | +1.24% | +1.97% | 4,483 |
| 60 calendar days (42 trd) | **70.4%** | +1.75% | +2.55% | 4,471 |

**A signal that is 57.9% or 60% accurate about direction is worse than a rule that
always says "up."** At the 43-day horizon the coin that always guesses up is right 67.1%
of the time.

This single fact explains the motivating puzzle better than any structure argument:

- The **call credit spread** is a bearish/neutral structure. Sold on a signal with no real
  edge, in a market that rises 67% of the time, it should return approximately zero to
  slightly negative. My model (§3) puts its break-even at **36.0% down-accuracy against a
  32.9% base rate** — i.e. an uninformative signal lands almost exactly on break-even.
  **The model reproduces the observed "exactly zero" result.**
- The **long put** is fighting the same 67/33 drift *and* paying the volatility premium
  *and* needing magnitude, not just direction. −6.56% is what that costs.

**Caveats on the base rate, stated honestly.** Windows overlap, so effective independent
n ≈ 4,483/30 ≈ 150 and the 95% CI on 67.1% is roughly **[59%, 75%]**. The sample
(SPY 145.58 → 682.43) is an exceptional 18-year bull run and embeds a realized equity
premium that is unlikely to repeat at that magnitude. A forward-looking base rate of
**60–63%** is more defensible. **Even at 60%, a 57.9% signal is not an edge.**

---

## 2. Two things called "win rate" that are not the same number

This is the core methodological error, and it is almost certainly the source of the
"67–80% break-even" figure in circulation.

For any OTM short-premium structure there are **three** distinct percentages:

| Quantity | 0.16Δ short / 0.05Δ wing iron condor | 0.30/0.16 put credit spread |
|---|---|---|
| (a) **Naive break-even** = maxloss/(maxloss+maxwin) | **87%** | **77%** |
| (b) **Structure win rate** at the base rate | **79%** | **78%** |
| (c) **Directional accuracy the signal needs** | **54.2%** | **60.0%** |

All three are correct answers to different questions. (a) treats the trade as a binary bet
at 6.5 : 1 odds — it is the number retail quotes, and it is **wrong as a signal
requirement**, because it ignores that the underlying stays inside the short strikes ~79%
of the time *with no signal at all*. (b) is the hit rate you would see in a P&L blotter.
(c) is the only one that is a requirement on your signal.

**This gap is almost certainly the source of the "an OTM credit spread needs 67–80%
accuracy" claim in circulation.** That figure is quantity (a) or (b). The actual
directional-accuracy requirement is **54–61%** — much lower — and the reason credit spreads
are still the wrong vehicle has nothing to do with break-even accuracy (§8–9).

**A 90% win rate with 1:9 payoff is exactly break-even, not a good strategy.** Win rate
carries no information about expectancy until you pair it with the payoff ratio and the
*unconditional* probability of the winning region.

---

## 3. THE BREAK-EVEN WIN RATE TABLE

**The question this answers:** *for each vehicle, how directionally accurate must a signal
be, at real retail costs, before it makes money?*

**Calibration — all measured, nothing assumed:**

- **Costs:** the measured SPY quoted-spread curve (2008-2025, 20–60 DTE, OI > 10, median
  % of mid), applied per leg by delta: far OTM (0.10–0.25Δ) **1.30%**, OTM (0.25–0.40Δ)
  **0.87%**, ATM (0.40–0.60Δ) **0.75%**, ITM (0.60–0.75Δ) **1.37%**, deep ITM (0.75–0.95Δ)
  **1.34%**. Half the half-spread crossed on entry *and* exit, plus $0.05/contract
  regulatory fees.
- **Base rate:** P(SPY up over 43 calendar days) = **67.1%**, measured (§1).
- **κ = 0.93** (realized/implied vol), between the measured mean 0.969 and median 0.862 (§7).
- **Pricing:** the arbitrage-free lognormal-mixture density fitted to live SPY quotes (§4).
  Strikes not directly quoted are priced from that same density, so the delta ladder is
  internally consistent.

**Two signal models bracket the honest answer.** *LOCATION* = the signal knows direction
**and** magnitude. *SIGN-ONLY* = the signal knows **only** the sign; conditional magnitude
is untouched — the realistic case for a classifier predicting the sign of the next 43-day
return. Where they differ, the truth is in between, and the gap is itself the finding.

**`vs base`** = break-even minus the 67.1% base rate. **Negative means the structure pays
with no signal at all. Positive means your signal must beat "always guess up" by that
much.** This is the column that matters.

### Bullish structures — what a signal must deliver

| Structure | Cap $ | MaxLoss:MaxWin | naive B/E | **B/E (location)** | **B/E (sign-only)** | **vs base** | friction |
|---|---|---|---|---|---|---|---|
| **Shares, long 100 SPY** | 76,876 | linear | — | **57.1%** | **56.0%** | **−11.1pp** | 0.00% |
| Long call 0.16Δ (805C) | 222 | 0.00:1 | 0% | 65.0% | **79.0%** | **+11.8pp** | 0.67% |
| Long call 0.30Δ (792C) | 504 | 0.00:1 | 0% | 64.1% | **72.0%** | **+4.9pp** | 0.44% |
| Long call 0.50Δ (778C) | 1,038 | 0.01:1 | 1% | 63.3% | **67.0%** | −0.1pp | 0.38% |
| Long call 0.70Δ (762C) | 1,977 | 0.01:1 | 1% | 62.6% | **64.2%** | −3.0pp | 0.69% |
| Long call 0.80Δ (751C) | 2,790 | 0.02:1 | 2% | 62.2% | **63.2%** | −3.9pp | 0.67% |
| ZEBRA (2×762C − 1×778C) | 2,920 | 0.02:1 | 2% | 62.3% | **63.3%** | −3.8pp | 1.06% |
| Call debit 762/792 (.70/.30) | 1,476 | 0.97:1 | 49% | 61.6% | **61.9%** | −5.2pp | 1.07% |
| Call debit 778/792 (.50/.30) | 537 | 0.62:1 | 38% | 62.2% | **63.5%** | −3.6pp | 1.15% |
| Put credit 762/745 (.30/.16) | 1,306 | 3.32:1 | 77% | 60.1% | **60.0%** | −7.1pp | 0.67% |
| Put credit 778/762 (.50/.30) | 947 | 1.45:1 | 59% | 61.5% | **61.6%** | −5.5pp | 1.16% |
| Call butterfly 778/792/805 | 258 | 0.23:1 | 18% | never +EV | **60.9%** | −6.3pp | **3.84%** |
| Iron condor .30 short/.16 wing | 1,027 | 1.53:1 | 60% | never +EV | 55.4% | — | 1.21% |
| Iron condor .16 short/.05 wing | 3,987 | 6.50:1 | 87% | never +EV | 54.2% | — | 0.18% |

### Bearish structures (accuracy = P(down); base rate for down = 32.9%)

| Structure | Cap $ | MaxLoss:MaxWin | naive B/E | **B/E (location)** | **B/E (sign-only)** | **vs base** | friction |
|---|---|---|---|---|---|---|---|
| Shares, short 100 SPY | 76,876 | linear | — | 42.9% | **44.0%** | **+11.1pp** | 0.00% |
| Long put 0.50Δ (778P) | 1,697 | 0.02:1 | 2% | 41.7% | **41.6%** | +8.7pp | 0.38% |
| Long put 0.30Δ (762P) | 1,038 | 0.01:1 | 1% | 43.4% | **43.0%** | +10.1pp | 0.44% |
| Long put 0.16Δ (745P) | 639 | 0.01:1 | 1% | 45.8% | **44.4%** | +11.5pp | 0.66% |
| Put debit 778/762 (.50/.30) | 664 | 0.71:1 | 41% | 39.9% | **39.9%** | **+7.0pp** | 1.65% |
| Call credit 792/805 (.30/.16) | 1,021 | 3.66:1 | 79% | 37.2% | **33.8%** | **+0.9pp** | 0.36% |

### The answer, stated plainly

**A 60%-accurate direction-only signal can be expressed profitably in shares, and in
almost nothing else.** Reading the sign-only column against a 60% signal:

| Clears 60% | Does not clear 60% |
|---|---|
| Shares (56.0%) | Every long call at 0.30Δ or lower (72–79%) |
| Put credit .30/.16 (60.0%) — but see §8–9 | Long call 0.50Δ (67.0%), 0.70Δ (64.2%), 0.80Δ (63.2%) |
| Iron condors (54–55%) — but they discard the signal | ZEBRA (63.3%), both debit spreads (61.9–63.5%) |
| | Butterfly (60.9%), put credit .50/.30 (61.6%) |

### How to read this table

1. **Break-even falls monotonically as delta rises.** Sign-only: 79.0% → 72.0% → 67.0% →
   64.2% → 63.2% as delta goes 0.16 → 0.80. **The lower the delta, the more magnitude
   information you must supply, and a sign classifier supplies none.** This independently
   reproduces the measured result that realized win rate rises monotonically with delta
   (cross-check below).
2. **Shares win, and win on robustness too.** Lowest break-even of any bullish structure,
   zero friction, and — critically — **almost completely insensitive to κ** (55.9–56.0%
   across κ ∈ [0.90, 0.97]), while the 0.16Δ call swings from 67.5% to 89.6% over the same
   range. When a conclusion depends on a parameter you cannot pin down, that is not a
   conclusion. Shares don't have that problem.
3. **The `vs base` column is the whole game.** Shares are −11.1pp: they pay with no signal
   at all, because the 67.1% base rate exceeds their 56.0% break-even. That gap *is* the
   equity risk premium. **Every** bearish structure is positive in that column — bearish
   swing trades start ~10pp in the hole.
4. **ZEBRA is a deep-ITM call with extra steps.** Net extrinsic ≈ 0 by construction, so its
   break-even (63.3%) lands essentially on top of the 0.80Δ call (63.2%) — but it costs
   $2,920 and carries 1.06% friction against the single call's 0.67%. **You pay an extra
   leg for no improvement.** Its real merit is delta ≈ 1.0 per contract; its real cost is
   that it is untradeable in a $3k account.
5. **The butterfly's problem is friction, not payoff.** 3.84% round-trip — the worst on the
   board — because it is three legs against a $258 capital base. It also *needs* the
   underlying to land near 792; under the location model, where the signal supplies drift
   but the butterfly caps the payoff exactly where the drift takes you, **it never breaks
   even at any accuracy.**
6. **Naive vs true break-even, again.** The 0.16/0.05 condor's naive figure is **87%**; its
   true break-even is **54.2%**; and it wins **79%** of the time at the base rate. Three
   different numbers, all "win rate." Only the middle one is a signal requirement (§2).
7. **Iron condors show "never +EV" under the location model** because they are short both
   tails: a directional signal shifts the distribution *out* of the profit zone. **Any
   directional information you have is destroyed by expressing it as a condor.**

### Cross-check against independently measured outcomes

Model-implied win rate versus win rates measured directly on real SPY quotes at a 21-day
hold:

| Delta | Measured (21-day hold) | Model (43 DTE to expiry) | Diff |
|---|---|---|---|
| 0.16 | 37% | 15% | −22 |
| 0.30 | 48% | 26% | −22 |
| 0.50 | 58% | 38% | −20 |
| 0.70 | 61% | 48% | −13 |
| 0.80 | 63% | 53% | −10 |

**The monotonic pattern reproduces exactly, and the level gap is the expected direction and
shape.** Holding to expiry surrenders all remaining extrinsic value, so the model's win
rates must sit below a 21-day hold — and the gap must *narrow* as delta rises, because
high-delta options carry less extrinsic to surrender. Both hold. This is a structural
validation of the model from data it never saw.

### Sensitivity to κ — the one parameter that matters

Sign-only break-even, by realized/implied vol ratio:

| Structure | κ=0.90 | **κ=0.93** | κ=0.97 |
|---|---|---|---|
| Shares | 56.0% | **56.0%** | 55.9% |
| Long call 0.16Δ | 89.6% | **79.0%** | 67.5% |
| Long call 0.30Δ | 78.1% | **72.0%** | 65.0% |
| Long call 0.50Δ | 70.3% | **67.0%** | 63.1% |
| Long call 0.80Δ | 64.4% | **63.2%** | 61.7% |
| ZEBRA | 64.4% | **63.3%** | 61.9% |
| Call debit .70/.30 | 62.4% | **61.9%** | 61.3% |
| Put credit .30/.16 | 59.3% | **60.0%** | 60.9% |
| Iron condor .16/.05 | 50.8% | **54.2%** | 58.5% |

**Low-delta long options are unusable as decision objects**: their requirement moves 22
percentage points across a κ range I cannot narrow further from 18 years of data. Shares
move 0.1pp.

### Costs are not the binding constraint

Re-running the entire table under the tightest observed spreads (the live 2026 snapshot),
the 2022-2025 median, and the full 2008-2025 median moves break-evens by **0–3pp** and
**changes no ordering**. Applying the measured stress-regime widening (**1.15×**, VIX>40 vs
VIX<15 — far milder than folklore) moves them by ~1pp. **The edge was not destroyed by
bid-ask.** It was destroyed by paying the volatility premium and by fighting a 67% base
rate. Costs decide *which* option, not *whether* options.

### One discrepancy, flagged not smoothed

The model puts the 0.16/0.05 iron condor at **+2.8%/trade** at the base rate; direct
measurement on real quotes at a 21-day hold puts it at **−10.5%/trade at a 63.6% win
rate**. **Prefer the measurement.** The model holds to expiry, so it never pays the exit
cost on four legs and never books a mid-trade loss; a 21-day hold pays eight crossings and
exits many trades at a mark-to-market loss that would have recovered by expiry. The
divergence is a good illustration of how much of a condor's theoretical edge lives in the
last three weeks — and how much of it a real holding period gives back.

---
## 4. Method, and why you can trust these numbers

Three iterations were required; the first two were wrong in instructive ways.

- **v1 — wrong.** Assumed a *flat* real-world vol against a *skewed* implied surface. This
  mechanically declares every OTM put overpriced and made put-selling and bear put debit
  spreads look spectacular. Discarded.
- **v2 — wrong.** Extracted the risk-neutral density from a fitted quadratic smile via
  Breeden-Litzenberger. The fitted smile turned out to be **arbitrageable**: total
  probability mass 1.0799 and E[S_T] = 828.91 against a forward of 771.39, a put-call
  parity violation of $3.76. A flat-vol unit test confirmed the BL machinery was correct
  and the *smile* was the problem. Discarded.
- **v3/v4 — used.** A **two-component lognormal mixture** fitted directly to the 8 observed
  option mid prices subject to the martingale constraint E[S_T] = forward. A mixture is a
  genuine probability distribution, so it is arbitrage-free by construction, and it
  reproduces index skew and fat tails.

**Fitted density** (relative SSE 5.2×10⁻⁴):

| regime | weight | mean log-ret | annualized vol |
|---|---|---|---|
| calm | 83.8% | +1.57% | 9.30% |
| stress | 16.2% | −6.79% | 20.85% |

Total annualized vol 14.96%, **skew −1.43** — close to the *realized* 30-day skew of
**−1.18** measured independently from the spot series. Repricing error vs market mids:
≤ $0.15 on 6 of 8 contracts.

**The real-world measure** scales log-returns about their mean by κ, which shrinks
dispersion (the variance risk premium) while **preserving skew and kurtosis** — so the
model does *not* assume the skew is pure premium. Rates implied from put-call parity at
the 770 strike: r = 4.00%, q = 1.10%.

**Null test (the validation that matters).** At κ = 1 with p set to the density's own
P(up), every structure must return ~0. Result: all 15 structures within **±1.8pp of
zero**, 12 of 15 within ±0.7pp. Residuals trace to the mixture's small pricing errors.
**Treat all break-even figures as ±1–2pp.**

---

## 5. The measured cost stack

### Bid-ask, measured from 5.99M SPY contract-days

Median quoted spread as % of mid, **2022–2025** (what you'd pay today):

| \|delta\| | 15–25 DTE | 25–35 DTE | 35–50 DTE | 50–75 DTE |
|---|---|---|---|---|
| <0.10 | 4.08% | 3.61% | 2.99% | 2.38% |
| 0.10–0.20 | 1.24% | 1.24% | **1.07%** | 0.91% |
| 0.20–0.30 | 0.90% | 0.92% | **0.80%** | 0.68% |
| 0.30–0.40 | 0.71% | 0.73% | **0.65%** | 0.55% |
| 0.40–0.55 | 0.56% | 0.58% | **0.52%** | 0.46% |
| 0.55–0.70 | 1.13% | 1.49% | 1.52% | 1.47% |
| 0.70–0.85 | 1.76% | 1.98% | **2.13%** | 2.09% |
| >0.85 | 0.97% | 1.12% | 1.05% | 1.03% |

Absolute median spread, 2022–25, 35–50 DTE: Δ<0.10 = **1¢**, Δ0.20–0.30 = **4¢**,
Δ0.40–0.55 = **5¢**, Δ0.70–0.85 = **59¢**, Δ>0.85 = **94¢**.

### The spread curve is U-shaped in delta — and why that matters

Both independent measurements of SPY agree on the shape:

| | far OTM | OTM | **ATM** | ITM | deep ITM |
|---|---|---|---|---|---|
| 20–60 DTE, OI>10, 2008-2025 | 1.30% | 0.87% | **0.75%** | 1.37% | 1.34% |
| 35–50 DTE, 2008-2025 (by delta bucket) | 1.71% | 1.20% | **0.83%** | 1.48% | 1.81% |

**Cheapest at-the-money, more expensive in both directions.** This matters because it
prices the two most commonly recommended "capital-efficient" structures — deep-ITM calls
and far-OTM lottery tickets — at roughly **1.8× the ATM cost**.

**Reconciling with Muravyev & Pearson (2020), "Options Trading Costs Are Lower Than You
Think."** They report cost patterns that are closer to monotonic with ITM cheapest, for
single-stock options. Three distinctions resolve it, and all three matter for how you use
my numbers:

1. **Quoted vs effective spread.** I measure the **quoted** spread — the worst case, what
   you pay crossing immediately. M&P's central contribution is that **effective** spreads
   for patient/algorithmic execution are far lower than quoted, because a large share of
   the quoted spread is transitory. **If you work limit orders, your real cost is
   materially below every number in this report** — which is why I model only 0.5 ×
   half-spread rather than the full crossing.
2. **Tick regime.** Single-stock options quote in **nickels above $3.00** (measured
   directly, below). With a binding minimum tick, %-spread falls mechanically as premium
   rises, producing a monotonic ITM-cheapest pattern. **SPY quotes in pennies at every
   price level**, so the tick never binds and the curve is shaped by liquidity and hedging
   cost instead — hence the U.
3. **Where the volume is.** The U tracks open interest and volume, not moneyness per se.
   Live SPY 43-DTE: the ATM 770C traded **1,972 contracts**; the 0.84Δ 730C traded **15**.
   Deep-ITM options are quoted defensively because nobody trades them, and because hedging
   a 0.84-delta option means moving 84 shares per contract.

**Practical consequence:** the U-shape is a property of penny-tick index options, and it
means "just buy deep ITM to get stock-like exposure" carries a real, measurable toll that
the single-stock literature would not lead you to expect.

**Four further conclusions, all counter to folklore:**

1. **SPY options are far cheaper to trade than commonly assumed.** A 25-delta 43-DTE SPY
   put has a 2¢ spread on a $6.36 mid = **0.31%**. Round-trip friction on a vertical
   spread is well under 1% of capital at risk. **Bid-ask is not what killed the edge.**
2. **Spread-as-%-of-premium falls as DTE rises**, because premium grows faster than the
   spread. Live SPY 25-delta puts: 15 DTE = **0.72%**, 43 DTE = **0.31%**, 71 DTE =
   **0.36%**. Short-dated options are *more* expensive per dollar of premium — a real
   argument for 30–60 DTE over weeklies that does not depend on any theta folklore.
3. **Deep-ITM options are the expensive ones.** Δ0.70–0.85 costs **2.13%** of mid and
   **59¢** absolute — 3–4× the ATM percentage cost and ~12× the absolute cents. This
   directly stress-tests the "use deep-ITM calls as a capital-efficient share substitute"
   recommendation (see §6).
4. **Secular tightening is dramatic.** Median spread in the 25–45 DTE / 15–35 delta
   premium-selling zone: **4.18% (2014) → 0.63% (2023) → 0.88% (2025)**. Any study of
   option strategy costs from before ~2019 materially overstates today's frictions.

### Tick regime — a real and under-appreciated constraint

From the live `min_ticks` fields:

- **SPY, QQQ, IWM, XSP:** penny ticks at *all* price levels.
- **XLF, XLE, NVDA, AAPL:** penny below $3.00, **nickel above $3.00**.

A nickel minimum tick on a $5 option is a 1% minimum half-spread. Measured live ATM
43-DTE spreads confirm the penalty:

| Underlying | contract | spread | % of mid | IV |
|---|---|---|---|---|
| SPY 768.76 | 770P (Δ−0.475) | $0.04 | **0.30%** | 13.61% |
| QQQ 715.23 | 715P (Δ−0.462) | $0.08 | 0.41% | 21.54% |
| IWM 298.80 | 299P (Δ−0.469) | $0.08 | 1.11% | 18.90% |
| NVDA 219.63 | 220P (Δ−0.465) | $0.15 | 1.24% | 41.27% |
| AAPL 312.22 | 310P (Δ−0.434) | $0.20 | 2.15% | 25.79% |
| **XLF 57.78** | 58P (Δ−0.493) | $0.09 | **7.79%** | 14.77% |

**Sector ETF options are 7–25× more expensive to trade than SPY in percentage terms.**
The XLF ATM put costs 7.79% of premium to cross *once*. Round-trip that is ~15% — it
consumes any plausible swing edge by itself. **Restrict to SPY/QQQ/IWM.** Megacap singles
are tolerable but 4–7× SPY's cost.

### XSP: the tax/assignment trade-off, quantified

XSP (cash-settled, Section 1256, no assignment risk) *is* tradeable on Robinhood with
penny ticks. But measured live: **XSP 770P spread $0.18 = 1.48% of mid, OI 250, volume
25** versus **SPY 770P at 0.30%, OI 10,868, volume 2,394**. XSP costs **~5× more** to
trade.

Also correcting a common misconception: **XSP is not smaller than SPY.** XSP ≈ 770 × 100
= $77,000 notional; SPY ≈ 768.76 × 100 = $76,876. They are the same size. XSP offers no
sizing advantage for a small account.

The 60/40 Section 1256 blend saves roughly 8–10 points of tax **on gains only**. Paying
~2.4pp of extra round-trip spread per trade to save ~10% of tax on profits is a losing
trade for anyone trading more than a few times a year — and at a $2–5k account size the
tax bracket makes the benefit smaller still. **On tax grounds alone, use SPY.**

**But tax is the weaker argument for XSP. Assignment is the strong one** — see below.

### Assignment and pin risk — the failure mode that voids "defined risk"

This is the one place where a $3,000 account can lose more than its stated max loss, and it
deserves more weight than the cost tables suggest.

- **SPY is the worst case for early assignment.** SPY pays quarterly dividends (~1.1%
  yield) and its **ex-dividend date falls on the third Friday of March/June/September/
  December — the same day as quarterly expiration.** Deep-ITM short calls whose remaining
  time value is below the ~$1.70–1.90 dividend get exercised en masse.
- **When early exercise of a short ITM call is rational:** when `D > P(K,T) + K·r·(T−t)` —
  the dividend exceeds the corresponding put's value plus interest saved by deferring the
  strike payment. Desk simplification: **dividend > remaining time value of the call**.
- **Assignment is random and unannounced.** Per OCC/OIC, "OCC randomly assigns exercise
  notices to its clearing members who, in turn, assign their customers." Notice arrives
  after the close. ([OCC/OIC Exercise & Assignment
  FAQ](https://www.optionseducation.org/referencelibrary/faq/options-exercise))
- **What assignment does to a $3,000 account:** 100 SPY ≈ **$77,000 notional**. Reg T
  initial requirement is 50% ≈ **$38,500** against $3,000 of equity — an instant ~$35k
  margin call with **no guaranteed grace period**; app brokers typically auto-liquidate at
  the next open. Between Friday-night assignment and Monday-morning liquidation you hold
  $77k of directional exposure against $3k of equity: **a 3.9% adverse gap wipes the
  account, and a larger gap leaves you owing the broker money.**
- **The critical nuance for spreads:** a vertical is defined-risk *only while the long leg
  is still there*. If you are assigned on the short leg at expiration and the long leg is
  OTM or goes unexercised, the "max loss" was never the max loss.

**Revised conclusion on XSP.** SPX and XSP options are **European-style and cash-settled —
no early assignment, no share delivery, ever.** That eliminates this entire failure mode
rather than managing it. Weigh honestly:

| | SPY | XSP |
|---|---|---|
| ATM 43-DTE spread (measured) | **0.30%** of mid | **1.48%** of mid |
| Extra cost per spread round trip | — | **~$29** on a 745/720-equivalent |
| Modeled E[$]/trade on that spread | +$42 | +$42 − $29 ≈ **+$13** |
| Assignment risk | real, quarterly, account-fatal | **none** |
| Section 1256 60/40 | no | yes |

The cost is severe — roughly a **70% haircut to expectancy**. The honest resolution is that
this trade-off is an argument *against selling spreads at this account size at all* (§9),
not an argument for one ticker over the other. **If you sell spreads anyway: either use
XSP and accept the cost, or use SPY and never hold a short ITM leg through the third
Friday of March, June, September or December.**

### Fees

Robinhood charges $0 commission on options; regulatory pass-throughs (OCC clearing, ORF,
SEC Section 31 on sells, FINRA TAF) total roughly **$0.03–0.08 per contract round trip**.
Modeled at $0.05. On a $500 option this is 0.01% — **negligible, and not the problem.**

---

## 6. Structure-by-structure verdict

### Shares — the benchmark that is hard to beat
Lowest break-even of any bullish structure (56–57%), −10.0pp versus base rate, insensitive
to the signal model, and ~0.001% round-trip cost. **The honest default.** Its only defect
is capital: 100 SPY = $76,876. Fractional shares on Robinhood solve this exactly —
$3,000 of SPY is the cleanest possible expression of a bullish swing view, with no theta,
no vega, no assignment, no expiry.

### Deep-ITM calls as a "capital-efficient share substitute" — partially refuted
This is a widely recommended substitute. Measured, it costs more than advertised:

- SPY 730C (Δ0.836): price **$4,604**, intrinsic $3,876, **extrinsic $728 = 15.8% of the
  premium**, decaying to zero over 43 days.
- That extrinsic is **0.95% of notional per 43 days = 8.0% annualized carry.**
- Round-trip bid-ask on Δ0.70–0.85 SPY calls: **2.13%** of mid (measured, 2022–25).
- Break-even accuracy **63.0–64.2%** versus **56.0–57.2%** for shares — a **~7pp penalty**.

The capital efficiency is real (84 share-equivalents of exposure for 6% of the cash) but
it is **rented at ~8%/yr, not free**. And at $4,614 it is **untradeable in a $3,000
account** anyway. Verdict: a legitimate tool for a *strong* signal in a *larger* account;
not a free linear substitute, and not available at this account size.

### Credit vs debit spreads — economically identical, confirmed
Direct test at **matched strikes** (770/745), same underlying, same expiry:

| Structure | Capital | net cash | TRUE B/E | E[R] @65% |
|---|---|---|---|---|
| Bull PUT CREDIT 770/745 | $1,800 | −$700 (credit) | **58.6%** | 6.3% |
| Bull CALL DEBIT 745/770 | $1,788 | +$1,788 (debit) | **57.9%** | 6.9% |

Identical payoff, break-evens **0.7pp apart** (financing plus the slightly different
spread actually crossed). **"Credit" versus "debit" is a cash-flow label, not an edge.**

This matters because it dissolves a popular illusion. In §3 the 0.30/0.16 put *credit*
spread (60.0%) shows a better break-even than the 0.50/0.30 call *debit* spread (63.5%) —
but those are **different strikes on different sides of spot**. The advantage comes
entirely from (a) strike placement below spot rather than above it, and (b) **selling the
rich side of the skew**. It has nothing to do with receiving a credit. Compare like with
like — the 0.50/0.30 call debit (63.5%) against the 0.50/0.30 put credit (61.6%) — and the
residual 1.9pp is skew and financing, not structure type.

### The skew is the largest single pricing fact — and it is directional
Measured live on SPY at 43 DTE:

| strike | delta | IV |
|---|---|---|
| 720P | −0.132 | **18.75%** |
| 730P | −0.169 | 17.58% |
| 745P | −0.249 | 15.89% |
| 770P | −0.475 | 13.61% |
| 770C | +0.534 | 12.97% |
| 790C | +0.292 | 11.72% |
| 810C | +0.111 | **11.21%** |

**A 25-delta put trades at 15.89% while a 29-delta call trades at 11.72% — a 4.17
volatility-point gap at comparable moneyness**, and 7.54 points from the 13-delta put to
the 11-delta call.

Consequence for structure choice: **selling call-side premium collects materially cheaper
volatility than selling put-side premium.** A bear call credit spread sells ~11–12% vol
against realized vol that has averaged ~15% (§7). This is a second, independent reason the
call credit spread returned zero: it was short the *cheap* wing while fighting a 67% up-drift.

### Long options
Break-evens of **63–79%** across the delta ladder (sign-only, κ=0.93), versus a 67.1% base
rate. Viable only with a signal carrying genuine **magnitude** information, and then only
at high delta. **Buy delta, not cheapness:** 0.80Δ needs 63.2%, 0.16Δ needs 79.0%, and the
ranking is monotone at every κ tested. Low-delta calls are additionally disqualified by
parameter sensitivity — their requirement swings 22pp across the plausible κ range (§3).

### Iron condors
Short both tails ⇒ structurally unable to express a directional view. Never +EV under the
location model here. If you have a directional signal, a condor discards it.

---

## 7. Volatility risk premium — measured, and smaller than advertised

From the same 18 years: 30–45 DTE ATM implied vol versus the **subsequent realized** vol
over the matching window.

| Horizon | n | mean IV | mean RV | IV − RV | κ mean | κ median | % of time RV > IV |
|---|---|---|---|---|---|---|---|
| 30 cal / 21 trd | 3,803 | 15.98% | 15.04% | **0.94 pts** | 0.945 | 0.853 | **31.0%** |
| 43 cal / 30 trd | 3,794 | 15.98% | 15.23% | **0.75 pts** | 0.969 | 0.862 | **30.3%** |
| 60 cal / 42 trd | 3,782 | 15.98% | 15.46% | **0.53 pts** | 0.994 | 0.869 | **30.8%** |

**The VRP at swing horizon is ~0.5–0.9 volatility points on average — not the 3–4 points
often quoted.** The mean κ of 0.97 versus median 0.86 reflects a right-skewed κ
distribution: most of the time you collect a little, occasionally you pay a lot.
**Realized exceeds implied 30% of the time.** The premium is real but thin, and it is
compensation for a genuine risk, not a free lunch.

(The commonly quoted 3–4 point figure is typically VIX versus subsequent realized in calm
regimes. This sample spans 2008, 2020 and 2022. It is the more honest number for a
strategy that must survive those.)

### Conditioning on IV level — the regime finding

κ (realized/implied) by starting-IV quintile, 43cal/30trd:

| quintile | mean IV | mean RV | κ mean | κ median | % RV > IV |
|---|---|---|---|---|---|
| Q1 lowest | 10.20% | 11.08% | **1.089** | 0.923 | **41.2%** |
| Q2 | 12.68% | 12.45% | 0.983 | 0.899 | 31.6% |
| Q3 | 14.60% | 13.82% | 0.948 | 0.852 | 26.4% |
| Q4 | 17.77% | 15.85% | **0.892** | 0.800 | **23.7%** |
| Q5 highest | 26.14% | 24.36% | 0.932 | 0.861 | 27.8% |

**Selling premium when IV is lowest is the worst trade on the board** — κ > 1, meaning
realized *exceeds* implied on average, and it does so 41% of the time. You are short cheap
volatility that tends to expand.

**The sweet spot is Q4 — elevated but not extreme IV** (κ 0.892). Note that Q5, the
highest-IV regime, is *worse* than Q4: that is when crashes actually happen. This is
evidence-based support for a *bounded* IV-rank filter — sell premium when IV is high, but
not when it is extreme — and it refutes the naive "always sell premium" and the naive
"sell more when IV is highest" rules alike.

**An honest tension I cannot fully resolve.** Israelov & Nielsen, "Still Not Cheap:
Portfolio Protection in Calm Markets" (*JPM* 41(4), 2015), study ten global equity indices
and conclude that **options remain expensive even when volatility is near all-time lows** —
low absolute option prices do not imply cheap options, because expected realized vol falls
too. That directly contradicts my Q1 row.

The reconciliation is in the mean-versus-median split, and it matters: in Q1 the **median**
κ is 0.923 — still below 1, so the *typical* outcome of selling in a calm market is still a
premium collected, consistent with Israelov. But the **mean** κ is 1.089, because calm
regimes are exactly where volatility can only expand, and the rare expansions are violent.
So both statements are true: **options are still expensive in calm markets in the median
sense, and selling them in calm markets still loses money on average.** For a small account
that cannot survive the tail, the mean is the number that matters. Treat any "sell premium
when IV rank is high" rule as **contested**, not established.

---

## 8. Historical validation — 18 years of actually trading these structures

The model is a model. So I traded the structures on the real chain data and compared.

**Rules (deliberately conservative):** entry on the first trading day of each month into
the most-listed expiry at 35–50 DTE; short put spread = sell the put nearest Δ−0.25, buy
the put nearest Δ−0.10, **credit = short bid − long ask (crossing the full spread, not
mid)**; long call = buy nearest Δ+0.50 **at the ask**; held to expiry; settled against
reconstructed spot. No look-ahead — strike selection uses entry-date data only.
**208 monthly trades, 2008-01-02 → 2025-12-01**, median short-leg delta −0.249.

### Short put spread — the model was right, and that is the problem

| Metric | Realized | Model predicted |
|---|---|---|
| Win rate | **87.0%** | ~84% at break-even |
| Mean return / trade | **+3.99%** of capital at risk | +EV (B/E 56–57% vs 67% base) |
| Median return | +12.38% | — |
| E/sd per trade | **0.126** | 0.094 |
| **t-stat of the mean** | **1.82** | — |
| Worst trade | **−100.0%** | — |

**The model's predictions were confirmed within tolerance.** And the strategy is still not
usable, for two reasons the expectancy calculation cannot show you:

1. **t = 1.82 after 208 trades and 18 years.** The positive mean return is **not
   statistically significant at the 5% level**. Eighteen years of monthly trading is not
   enough to establish that this strategy makes money. This is the estimation problem in
   its most concrete possible form — and it means *your own trading record will never tell
   you whether the edge is real*.
2. **Fully reinvested, the equity curve goes to 0.00×** — a −100% drawdown. Total losses
   occurred in 2008-09, 2008-11, 2010-04, and again in 2011, 2012 (−98.2%), 2015, 2018,
   2020, 2022. **Nine of eighteen years contained at least one trade that lost essentially
   the entire capital at risk.**

Year by year the pattern is the classic short-premium signature — long stretches of 90–100%
win rates (2016, 2017, 2019, 2021 all at 100%) punctuated by years where a single trade
erases several years of gains (2008: −22.6% mean; 2018: −9.1%; 2022: −9.0%).

### Position sizing decides everything — and nothing beats just owning SPY

Same realized 208-trade sequence (so loss *clustering* is real, not simulated),
$3,000 starting account, risking a fixed fraction of current equity per trade:

| Risk per trade | Final equity | CAGR | Max drawdown |
|---|---|---|---|
| 100% | **$0** | −100% | **−100% (wiped out)** |
| 50% | $5,786 | 3.7% | −88% |
| 25% | $11,437 | **7.8%** | −57% |
| 10% | $6,167 | 4.1% | −27% |
| 5% | $4,423 | 2.2% | −14% |
| 2% | $3,527 | 0.9% | −6% |
| **SPY buy-and-hold, no leverage** | **$28,105** | **13.3%** | **−48%** |

**One 25-delta spread in a $3,000 account is ~43% risk per trade — between the two worst
rows in the table.**

**SPY buy-and-hold dominates every single sizing of the credit-spread program on both
axes**: higher return (13.3% vs a best-case 7.8%) *and* shallower drawdown (−48% vs −57%).
There is no risk fraction at which selling put spreads was the better trade over these 18
years. That is the empirical answer to the structure question.

### Long ATM calls — positive, but not what it looks like

| Metric | Value |
|---|---|
| Win rate | 51.9% |
| Trades that expired worthless (−100%) | **36.5%** |
| Mean return / trade | +22.18% of premium, **t = 2.56** |
| sd | 125% |

The mean is positive and significant — consistent with the literature that index *calls*
earn positive returns (leveraged equity beta), while index *puts* are the anomaly. But the
fair comparison is per unit of exposure:

- Long ATM call P&L per trade, **as % of underlying notional: +0.454%**
- Simply holding SPY over the same windows: **+1.264%**
- **Buying ATM calls captured only 36% of the move it was exposed to.**

The other 64% was paid away in volatility premium and time decay. Sized at 10% of equity
the calls compound to $64,973 (18.7% CAGR) versus SPY's $28,105 — but with a **−71%
drawdown**, and any sizing at 25% or above is **wiped out**. That is leveraged beta in the
strongest equity bull market on record, not evidence of a superior structure.

---

## 9. Sizing and risk of ruin — where credit spreads actually fail

§3 showed credit spreads have the *best* break-even of any option structure. That is an
expectancy statement. It is not a recommendation, because expectancy is not the binding
constraint for a $3,000 account.

### Capital at risk in a $3,000 account
At the base rate with no signal edge, κ = 0.90 (this table predates the §3 recalibration;
the structures differ but the sizing conclusion is unchanged):

| Structure | Capital | % of $3k | max loss | P(near-max loss) | E[$]/trade |
|---|---|---|---|---|---|
| Shares, long 100 | $76,876 | 2563% | — | 0.00% | **untradeable** |
| Call Δ0.84 ITM | $4,614 | 154% | −$4,624 | 9.10% | **untradeable** |
| Call Δ0.53 ATM | $1,478 | 49% | −$1,480 | 34.85% | +$149 |
| Call Δ0.29 OTM | $558 | 19% | −$559 | 64.32% | +$50 |
| Debit spread 770/790 | $922 | 31% | −$924 | 34.71% | +$96 |
| Credit spread 745/720 (25w) | $2,201 | **73%** | −$2,202 | 7.21% | +$55 |
| Credit spread 745/730 (15w) | $1,294 | **43%** | −$1,295 | 8.97% | +$42 |
| Credit spread 730/720 (10w) | $908 | 30% | −$909 | 7.17% | +$11 |
| Iron condor | $1,801 | 60% | −$1,803 | 7.21% | −$2 |

**The granularity problem is fatal at this account size.** One SPY contract is ~$77k of
notional. A single 15-wide credit spread ties up **43% of a $3,000 account** and can lose
all of it. There is no way to size a 2%-risk position in a one-lot SPY option — the
minimum tradeable unit is larger than prudent risk. Shares and the deep-ITM call are
outright untradeable.

### Monte Carlo: 745/730 credit spread, $3,000 account
Per trade: **E = +$42.03, sd = $448.68, E/sd = 0.094.** Max loss −$1,295 with **8.97%
probability per trade.**

| Horizon | P(drawdown > 50% of account) | median final | 5th percentile | P(lose money) |
|---|---|---|---|---|
| 8 trades (~1 yr of 43-day holds) | **15.5%** | $3,139 | $1,128 | 26% |
| 24 trades (~3 yrs) | **29.2%** | $4,280 | **$142** | 28% |

A positive-expectancy strategy with a **29% chance of halving the account over three
years** and a 5th-percentile outcome of **$142** — near-total loss.

**And these figures are a floor, not an estimate** — the simulation assumes independent
trades, but every short put spread is the same trade (short the same left tail), so real
sequences cluster their losses. §8 confirms this with the actual realized sequence: the
real 18-year path wipes out at full sizing and draws down 88% at 50% sizing, both worse
than the independence assumption implies.

### The estimation problem — confirmed empirically
At E/sd ≈ 0.10–0.13 per trade, distinguishing a genuinely +EV credit-spread program from a
−EV one requires on the order of **1/0.126² ≈ 63 trades for one standard error**, and far
more for confidence. The realized backtest settles it: **208 trades over 18 years produced
t = 1.82 — still not significant at the 5% level.**

**You cannot validate this strategy from your own trading record within your lifetime as a
trader.** Eight trades a year means the 208-trade sample takes 26 years to accumulate. In
the meantime you will observe long runs of 87–100% win rates that feel exactly like skill.
This is the peso problem in concrete form.

### Kelly sizing, and why it is actively dangerous here

For a credit spread with credit `C`, max loss `L`, win probability `p`:

```
Break-even win rate   p* = L / (L + C)
Expected value        EV = pC − (1−p)L
Kelly fraction        f* = p − (1−p)·L/C
```

**Worked example.** A 5-wide spread sold for $1.00 (C=1, L=4) with a claimed p = 0.90:
p* = 0.80, EV = +$0.50/spread = +12.5% on capital at risk, and
**f\* = 0.90 − 0.10×4 = 0.50 — full Kelly says risk 50% of the account per trade.**
Anyone who computes that and believes it is one trade away from a 50% drawdown.

**The parameter you cannot estimate is the one it is most sensitive to.**
`dEV/dp = C + L = 5`, so **every 1 percentage point of win-rate error moves EV by 5% of the
credit; a 10-point overestimate of p turns a +12.5% edge into zero.** And p is precisely
the quantity backtests overstate, because the sample under-represents the tail.

Kelly's derivation assumes the distribution is **known**. When p̂ is uncertain, f* is itself
a random variable, and the growth curve is asymmetrically punishing: underbetting costs
growth linearly, but **betting 2×f\* gives exactly zero long-run growth, and beyond that
growth is negative no matter how positive the EV.** Thorp's continuous-time result gives
P(wealth ever falls to fraction x) = x under full Kelly, and x^(2/c−1) at fraction c:

| Kelly fraction | P(ever −50% drawdown) |
|---|---|
| Full | 50% |
| Half | 12.5% |
| Quarter | 0.78% |

**Caveat that matters here:** that result is a diffusion approximation — **it assumes no
jumps**, which is exactly the assumption that fails for short premium. Treat quarter-Kelly
as an upper bound, not a target. My §8 realized-sequence table is the jump-inclusive
version of this same calculation, and it is harsher.

### What actually happens: documented blowups

- **Feb 5, 2018 "Volmageddon."** VIX 17.31 → **37.32, +115.6% — the largest one-day move in
  VIX history** — on an SPX decline of only **−4.10%**. That asymmetry is the lesson: a 4%
  index move produced a 116% volatility move. XIV lost ~96% of indicative value and was
  terminated (final redemption ~$5.99 vs ~$99).
- **LJM Preservation & Growth Fund** — a *regulated mutual fund* selling SPX options, and
  the closest institutional analogue to a retail premium-seller. ~$812M AUM entering
  February 2018 → ~$160M; **−80%+ in the week ended Feb 7, 2018**; dissolved March 29, 2018.
  The SEC's own language: *"In February 2018, during a large spike in market volatility,
  the Funds suffered more than $1 billion in trading losses."* Charges were for
  **misrepresenting worst-case loss estimates and risk-management practices** — the fraud
  was the risk model, not the trading.
  ([SEC Lit. Release 26338](https://www.sec.gov/enforcement-litigation/litigation-releases/lr-26338))
  Penalties totalled ~$4.8M against >$1B lost: **enforcement is not a recovery mechanism.**
- **OptionSellers.com / James Cordier, Nov 2018.** Naked short natural-gas *calls*;
  ~290–300 clients, ~$150M lost, and critically **many ended owing money to the clearing
  broker** — losses exceeded deposited capital. This was *futures* options with SPAN margin
  and genuinely unlimited loss. **A defined-risk spread cannot do this** — which is the
  single strongest argument for spreads over naked, and the reason Robinhood's level 3
  (no naked short options at any level) is a feature, not a limitation.
- **March 2020.** VIX closed at an all-time high **82.69 (Mar 16)**, intraday **85.47
  (Mar 18)**; SPX **−33.92% in 23 sessions**.
- **Aug 5, 2024.** VIX intraday 65.73, closed +64.9%. Instructive counter-example: the Cboe
  PUT index drew down only **−4.96%** — this was a *volatility* event, not a
  premium-seller's ruin event. Not every VIX spike destroys short premium; the ones that
  do are accompanied by sustained index declines.

### The Cboe benchmarks, recomputed from primary data

From Cboe's own daily index CSVs (PUT_History.csv, BXM_History.csv):

| | **PUT** (PutWrite) | **BXM** (BuyWrite) | SPX |
|---|---|---|---|
| CAGR | 9.31% | 6.17% | — |
| **Max DD (GFC)** | **−37.09%** | −40.14% | −56.78% |
| **Max DD (COVID)** | −28.93% | −30.26% | −33.92% |
| **Monthly win rate** | **73.2%** | 68.9% | — |
| Daily skew / excess kurtosis | −0.70 / 34.4 | −0.71 / 30.4 | — |
| Worst month | 2008-10 **−17.7%** | −15.0% | — |
| **Return / max DD** | **0.25** | 0.15 | — |

**73% of months are winners and the strategy still loses 37% peak-to-trough.** In COVID,
PUT absorbed **85% of the crash** (−28.9% vs SPX's −33.9%) while structurally capping the
upside — the "downside protection" was about 5 percentage points. This is the same finding
as §8, from a completely independent 35-year dataset.

> **Metric warning.** Goetzmann, Ingersoll, Spiegel & Welch (2007, *RFS*),
> "Portfolio Performance Manipulation and Manipulation-Proof Performance Measures," shows
> the **Sharpe ratio is directly gameable by writing options**. Andrew Lo (2001, *FAJ*),
> "Risk Management for Hedge Funds," makes the same point with his "Capital Decimation
> Partners" example — a naked short-put fund with a superb Sharpe and embedded ruin.
> **Do not evaluate any of these structures on Sharpe.**

### Correlation: position count is not diversification

In a tail event every short-premium position loses simultaneously. Diversifying across
strikes, expiries and tickers gives you **effective n = 1 when it matters**. This is what
killed both LJM and OptionSellers, and it is why the §9 Monte Carlo (which assumes
independence) understates ruin relative to the §8 realized sequence.

### Regulatory note: the Pattern Day Trader rule no longer exists

Widely repeated advice about the $25,000 PDT minimum is **out of date as of 2026**:

- **FINRA Regulatory Notice 26-10** (April 20, 2026), *"FINRA Adopts New Intraday Margin
  Standards to Replace the Day Trading Margin Requirements,"* effective **June 4, 2026**,
  phase-in through **October 20, 2027**.
  ([RN 26-10](https://www.finra.org/rules-guidance/notices/26-10))
- The current text of [FINRA Rule
  4210](https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210) contains **zero
  occurrences of "pattern day trader" and zero of "25,000."** It now defines an *intraday
  margin level* based on IML-reducing transactions rather than counting round trips.
- **For swing trading this was never binding anyway:** a "day trade" required buying and
  selling the same security in the same session, so **overnight positions were never day
  trades.** Confirm your broker's phase-in status — firms have until Oct 2027.

---

## 10. What the evidence actually supports

**Evidenced by measurement here:**
- Base rate P(SPY up, 43d) = 67.1% [95% CI ~59–75%]. Any directional signal must be
  benchmarked against this, not 50%.
- VRP at 20–60 DTE ≈ 0.5–0.9 vol points; realized exceeds implied 30% of the time.
- VRP is *negative* (κ > 1) in the lowest IV quintile; best in Q4, not Q5.
- SPY option spreads: 0.3–1.1% of premium at 10–55 delta, 35–50 DTE. Deep ITM: 2.1%.
- Sector ETF options cost 7–25× SPY in percentage terms; XSP ~5×.
- Spread-as-%-of-premium *falls* with DTE — a genuine, cost-based argument for 30–60 DTE.
- Credit and debit spreads at matched strikes are the same trade (break-evens 0.7pp apart).
- Put-side IV exceeds call-side IV by ~4.2 vol points at comparable moneyness.

**Evidenced in the literature (independent of this analysis):**

- **A volatility risk premium exists, and it is concentrated at-the-money.** Bakshi &
  Kapadia (2003), *RFS* 16(2):527–566 — SPX options, 1988–1995, 36,237 call observations,
  daily-rebalanced delta hedges. Buying and delta-hedging loses ~0.05% of index level on
  average (~0.10% ATM); mean gain scaled by option price is **−12.18%**, significant across
  all moneyness and maturity buckets. Crucially: the average ATM loss (~$0.43/call) is
  **the same order of magnitude as the mean bid-ask spread (~$0.375)**. The premium is real
  and it is roughly one spread wide.
  [PDF](https://people.umass.edu/~nkapadia/docs/Bakshi_and_Kapadia_2003_RFS.pdf)
- **The premium scales ~linearly with time — no DTE is magic.** From the same paper's
  Table 1: delta-hedged gain is −0.06% of index over 14–30 days vs −0.13% over 31–60 days,
  i.e. ~0.003%/day either way. **There is no 45-day sweet spot in the data.**
- **Selling more often does not collect more premium.** Cboe's own indices, common sample
  Feb 2006–Dec 2015, **gross of all costs**: PUT (monthly ATM) returned 6.6%/yr, Sharpe
  0.52, max DD −33%; **WPUT (weekly ATM) returned 5.6%/yr, Sharpe 0.50, max DD −24%.**
  WPUT trades ~4× as often and delivered **100bp/yr less before any transaction costs.**
  This is same-vendor, same-methodology evidence against "sell more frequently to harvest
  more theta."
- **Expectancy rises with short-strike delta while win rate falls.** An independent
  8-year SPY backtest (18.3M simulated spreads, 22–45 DTE, $5-wide, **gross of costs**)
  reports P&L/trade of +$0.20 at 40Δ, +$0.13 at 30Δ, +$0.11 at 20Δ, +$0.11 at 10Δ, against
  win rates of 76.5% → 96.5%. Best risk-adjusted profile was the **highest** delta tested,
  not 16Δ. This independently corroborates my §3 finding that the Δ0.17 spread has a
  *worse* break-even than the Δ0.25 spreads.
- **Most covered-call/premium-selling return is equity beta, not volatility premium.**
  Israelov & Nielsen, "Covered Calls Uncovered," *FAJ* Nov/Dec 2015 — decomposes returns
  into passive equity, active equity, and short-vol components; the **dominant driver is
  passive equity beta**, and the embedded "active" equity exposure is uncompensated.
  Implication: benchmark premium-selling against a **beta-matched equity position**, not
  against cash. §8's finding that SPY buy-and-hold dominates the credit-spread program at
  every sizing is exactly this result showing up in the data.
- **Cboe benchmark caveat:** all Cboe index returns are **gross** — no commissions, no
  slippage, no market impact. Their headline result is that options-selling indices achieve
  *similar* returns to the S&P 500 with lower volatility — i.e. **the gain is risk
  reduction, not return enhancement** — and a Sharpe edge of 0.52 vs 0.46 is well inside
  what realistic costs consume.

**Folklore — widely repeated, not supported:**

- **"45 DTE entry / manage at 21 DTE / take 50% max profit."** The canonical
  [tastylive page](https://www.tastylive.com/concepts-strategies/managing-winners) cites
  **no backtest, no sample period, no underlying, no metrics** — the language is "we have
  found that 50% can be the sweet spot." The 21-DTE claim traces to a 2018 Market Measures
  episode whose parameters and results are not recoverable from the public record.
  **Conflict of interest, stated plainly: tastytrade/tastylive is a brokerage whose revenue
  scales with trade count, and all three rules mechanically increase round-trips.** The
  stated mechanism (enter where theta decay accelerates) is also incoherent — faster theta
  is compensated by faster gamma; in a fairly-priced world they offset exactly. Any real
  edge must come from IV > RV, not from calendar position.
- **"16 delta is optimal because it's ~1 standard deviation."** The 1-SD framing describes
  the strike; it is not an argument for edge. Every study that reports *expectancy* rather
  than win rate points the other way (above), as does §3. The 16Δ preference is a
  **win-rate** preference — it produces a long quiet equity curve punctuated by rare large
  losses, which is precisely the shape that defeats backtest-length intuition (§8).
- **"Buy cheap OTM calls for leverage."** The most expensive folklore in the table. A 0.16Δ
  call needs **79% sign-only accuracy** and costs 1.30% per crossing; a 0.30Δ call needs
  **72%**. Independently measured, 0.16Δ calls win **37%** of the time at a 21-day hold.
  Cheap in dollars, ruinous in required accuracy.
- **"ZEBRA gives you stock exposure without the cost."** It gives you delta ≈ 1.0 with
  near-zero net extrinsic, which is real — but §3 shows its break-even (63.3%) is
  indistinguishable from a plain 0.80Δ call (63.2%) while costing an extra leg (1.06% vs
  0.67% friction). **The extrinsic you avoid paying, you give back in spread.**
- **"High win rate means the strategy works."** Refuted in §2 and demonstrated in §8: 87%
  win rate, t = 1.82, and a −100% drawdown at full sizing.
- **"Only sell premium when IV rank is high."** *Contested* — see the tension noted in §7.

---

## 11. Recommendation

**For this account ($2–5k, Robinhood level 3, swing horizon):**

1. **First, fix the signal, not the structure.** A 57.9–60% directional signal is below the
   67% base rate. No structure rescues it. The structure question is premature until the
   signal beats the base rate — and the correct benchmark for any future signal is
   **accuracy vs 67%**, or better, **expectancy vs SPY buy-and-hold** (13.3% CAGR, −48% max
   DD over this sample). That is a demanding benchmark, and §8 shows a fully systematic
   credit-spread program fails to clear it at *every* position size.
2. **If the view is bullish: buy fractional SPY/QQQ shares.** Lowest break-even (56–57%),
   no theta, no vega, no assignment, ~0.001% round-trip cost, and perfectly sizeable at any
   dollar amount — which uniquely solves the granularity problem that makes every option
   structure lumpy in a $3k account. This is the honest default.
3. **Options earn their place only for:** (a) a genuinely *bearish* view, where shorting
   shares is impractical in a small cash account and a **0.50/0.30 debit put spread**
   (break-even 39.9%, capital $664, defined risk) is the cleanest expression; or (b) a view
   with real **magnitude** conviction, where a **0.70/0.30 call debit spread** (break-even
   61.9%, capital $1,476) converts that conviction into leverage. Note that (a) still
   requires beating a 32.9% base rate by ~7pp — a high bar.
   **If you must own a long call outright, buy delta, not cheapness: 0.70–0.80Δ requires
   63–64% accuracy; 0.16Δ requires 79%.** The ranking is monotone and it never reverses.
4. **Avoid:** far-OTM long options (need 76–95% accuracy under a sign-only signal), iron
   condors (structurally discard directional information), and sector-ETF options (7–25×
   SPY's cost; XLF ATM puts cost 7.79% of premium to cross *once*). **On XSP, split the
   decision:** for *long* option positions use SPY (5× cheaper, and assignment is not a
   risk when you are long). For *short* legs, XSP's European cash settlement eliminates an
   account-fatal failure mode (§5) and may be worth its cost — though the cleaner answer at
   this size is not to sell spreads at all.
5. **Credit spreads: no, not at this account size.** They have the best break-even of any
   option structure (56–57%) and the realized backtest confirms +3.99%/trade at an 87% win
   rate — and it does not matter. One 15-wide spread is 43% of a $3,000 account; the
   realized 18-year sequence **wipes out at full sizing, draws down 88% at 50% sizing, and
   at its best sizing (25%) returns 7.8% CAGR with a −57% drawdown versus SPY's 13.3% with
   −48%.** SPY buy-and-hold dominated on both axes at every size tested. Revisit above
   ~$25k, where sizing can be made proportionate — but revisit it against a beta-matched
   equity benchmark, not against cash.
6. **If selling premium anyway:** 30–60 DTE (cost-driven — spread-as-%-of-premium falls
   with DTE — *not* theta folklore), **put side** (4.2 vol points richer than the call
   side), **Δ0.25–0.30 rather than Δ0.16** (better break-even here, and corroborated by
   independent studies showing expectancy rises with delta while win rate falls), SPY only,
   and size at **≤10% of equity per trade** — the realized sequence shows −27% drawdown at
   10% and −88% at 50%.
7. **Do not use your own P&L to decide whether it works.** At E/sd ≈ 0.13, even 208 trades
   over 18 years produced only t = 1.82. Any run of winners you experience will be
   statistically indistinguishable from luck.

---

## 12. What would change these conclusions

- **A lower base rate.** These numbers rest on a 67.1% up-rate from an exceptional bull
  sample. At a 60% forward base rate, shares' advantage shrinks and bearish structures
  become less punitive. The `vs base` column should be recomputed against whatever base
  rate you believe.
- **A signal with magnitude information.** The gap between the LOCATION and SIGN-ONLY
  columns is the value of knowing *how far*, not just *which way*. If a signal predicts
  magnitude, long options and debit spreads improve sharply and the case for shares weakens.
- **A larger account.** Much of §9 is a granularity constraint, not a strategy critique.
  At $25k+ sizing can be made proportionate — but note that §8's finding that SPY
  buy-and-hold dominates at *every* sizing is scale-invariant, so the credit-spread
  conclusion does **not** automatically reverse. It has to be re-earned against a
  beta-matched equity benchmark.
- **κ.** Break-evens move ~1–3pp across κ ∈ [0.86, 1.00]. The qualitative ordering of
  structures is stable across that range; the ordering of *shares vs options* does not
  change at any κ tested.

### Known limitations
- Single-snapshot pricing for the break-even table (one day, one expiry, low-vol regime:
  SPY ATM IV 13.3% vs the 15.98% historical mean). Break-evens in a high-IV regime differ.
  The §8 backtest is not subject to this — it spans all regimes.
- Break-even table evaluates structures **held to expiry**. Early management (the "close at
  50%" rule) is not modeled; it would reduce tail exposure per unit time but costs another
  spread crossing, and this analysis cannot settle the net effect.
- Model precision ±1–2pp (from the null test). Differences smaller than that are noise.
- Base rate and VRP use overlapping windows; effective n is ~1/30th of the nominal n.
- Spot is reconstructed via put-call parity, not a dividend-adjusted price series. The
  §8 backtest's "buy-and-hold" benchmark therefore **excludes dividends**, making SPY's
  dominance over the credit-spread program if anything understated.
- The §8 backtest trades one entry per month at a fixed delta; it does not test entry
  timing, IV-rank filters, or roll management.
- Single underlying (SPY) and a single 18-year sample containing three crises but only one
  secular regime.

---

## Sources

**Primary data computed in this report**
- `data/opt_eod/SPY_options.parquet` — 24,681,665 SPY contract-days, 2008-01-02 → 2025-12-12.
- Live Robinhood option chains, 2026-08-06 14:08 ET (SPY, QQQ, IWM, XLF, XLE, NVDA, AAPL, XSP).
- Cboe daily index history CSVs: [PUT](https://cdn.cboe.com/api/global/us_indices/daily_prices/PUT_History.csv),
  [BXM](https://cdn.cboe.com/api/global/us_indices/daily_prices/BXM_History.csv),
  [VIX](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv).

**Academic**
- Bakshi & Kapadia (2003), "Delta-Hedged Gains and the Negative Market Volatility Risk
  Premium," *RFS* 16(2):527–566.
  [PDF](https://people.umass.edu/~nkapadia/docs/Bakshi_and_Kapadia_2003_RFS.pdf)
- Israelov & Nielsen (2015), "Covered Calls Uncovered," *FAJ* Nov/Dec 2015.
  [AQR](https://www.aqr.com/Insights/Research/Journal-Article/Covered-Calls-Uncovered)
- Israelov & Nielsen (2015), "Still Not Cheap: Portfolio Protection in Calm Markets,"
  *JPM* 41(4):108–120.
- Goetzmann, Ingersoll, Spiegel & Welch (2007), "Portfolio Performance Manipulation and
  Manipulation-Proof Performance Measures," *RFS*.
- Lo (2001), "Risk Management for Hedge Funds: Introduction and Overview," *FAJ*.
- Taleb (2020), *Statistical Consequences of Fat Tails*. [arXiv](https://arxiv.org/abs/2001.10488)

**Regulatory / primary documents**
- [SEC Litigation Release 26338 — SEC v. Caine et al. (LJM), July 1, 2025](https://www.sec.gov/enforcement-litigation/litigation-releases/lr-26338)
- [FINRA Regulatory Notice 26-10 — intraday margin standards replace PDT](https://www.finra.org/rules-guidance/notices/26-10)
- [FINRA Rule 4210 (current text)](https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210)
- [OCC/OIC — Options Exercise & Assignment FAQ](https://www.optionseducation.org/referencelibrary/faq/options-exercise)
- [Reuters — LJM fund lost 80%+ in week ended Feb 7, 2018](https://www.reuters.com/article/business/us-fund-that-lost-most-of-its-value-shuts-doors-to-new-investment-idUSKBN1FT0IB/)

**Flagged as conflicted or unverified**
- [tastylive, "Managing Winners"](https://www.tastylive.com/concepts-strategies/managing-winners)
  and [Market Measures 21-DTE episode (2018)](https://www.tastylive.com/shows/market-measures/episodes/risk-and-rewards-managing-winners-and-21-dte-10-05-2018)
  — **brokerage, revenue scales with trade count; no published data, parameters or metrics.**
- FlashAlpha SPY credit-spread backtest (delta/expectancy table in §10) — independent of
  the brokerages but **gross of all costs and assumes mid-quote fills**; single underlying,
  2017–2026, a sample containing no prolonged bear market.
- XIV/Volmageddon fine detail circulates largely via sites selling volatility strategies or
  courses; all VIX figures above were recomputed from Cboe's own CSV.
- OptionSellers.com detail circulates largely via plaintiff law firms soliciting claimants.
  No CFTC/NFA docket was located — **absence of evidence, not evidence of absence.**
- Cboe benchmark index returns are **gross** — no commissions, slippage or market impact.
- Robinhood's current published option-level definitions could not be retrieved (support
  page 404). Verify level 3 terms in-app before relying on them.
