# Rule Sets — 0DTE and Swing Options

**Built:** 2026-08-05 · **Scripts:** `backtest_0dte_rules.py`, `backtest_swing_rules.py`, `bt_options.py`
**Data:** 15y daily SPY/VIX/VIX9D + SqueezeMetrics DIX/GEX (2011-07 → 2026-07, 3,765 days);
2y SPY minute bars (494 sessions); 27y daily ETF panel for swing (1999 → 2026).

This document separates **validated & robust**, **suggestive**, and **rejected**. It ends with the
honest arithmetic on the $5,000 → $100,000 growth goal. Nothing here was tuned until it hit a target.

---

## 0. How the testing was done (read this before believing any number)

| Guard | What was done |
|---|---|
| Look-ahead | DIX/GEX/VIX/trend read at the **prior close**; trade opens at today's open. Intraday filters use only bars before the entry bar. |
| Out-of-sample | Anchored walk-forward: for each OOS year the parameter grid is scored on data strictly **before Jan 1** of that year, then traded through it unseen. Plus a "frozen rules" test that only counts 2020+ (treating 2011-2019 as the discovery sample). |
| Controls | Every signal result is printed next to an **unconditional control** (same structure, all days) and, for swing, next to random-pick and equal-weight controls. |
| Permutation | Signal labels shuffled 300-500× to get a null distribution. |
| Multiple testing | Deflated Sharpe with `n_trials` = the grid actually searched. |
| Costs | Per-leg half-spread charged both ways (1% of mid, 1¢ floor for SPY 0DTE; 2% / 2¢ for 35-DTE ETF options) + per-contract fees. |

### The one assumption you cannot escape
There are **no historical option chains** in this repo, so option prices are **modelled** (Black-Scholes
off a causal vol forecast). Two parameters carry all the risk, and every headline is reported across
both:

- **`vrp`** — how far implied sits above the honest vol forecast (the variance risk premium). Swept 1.00 → 1.30.
- **`AWARE`** — how much of the dealer-gamma effect the option market *already prices into same-day IV*.
  `AWARE=0` means the market is blind (best case for us); `AWARE=1` means it prices gamma in full.

**A random-entry sanity check passes:** at `vrp=1.10` a random 0DTE ATM call loses −22% and a random
0DTE condor makes +3.1%. If long premium were profitable at random, the model would be too cheap and
every result below would be inflated. It isn't.

---

## 1. VALIDATED & ROBUST

### 1.1 Dealer gamma predicts the intraday RANGE — and the market does not fully price it

This is the single strongest finding in the study and it is **model-free**.

Normalised range = (high − low) / open ÷ implied daily move, regressed on prior-close GEX z-score:

| Range normalised by | β(gz) | t | Sub-period t's (11-14 / 15-18 / 19-22 / 23-26) |
|---|---|---|---|
| our own causal vol forecast | −0.158 | **−15.2** | −7.8 / −3.6 / −8.8 / −5.4 |
| **VIX9D — a real market-implied price** | **−0.074** | **−9.9** | −5.6 / −2.3 / −6.1 / −3.7 |

Realised range as a multiple of the **VIX9D-implied** move, by GEX quintile:

| GEX z quintile | Q1 (low γ) | Q2 | Q3 | Q4 | Q5 (high γ) |
|---|---|---|---|---|---|
| realised / implied | **1.139** | 1.025 | 0.958 | 0.933 | **0.843** |

`Q5 vs Q1: t = −13.2, p = 1.3e-37.`

**Why this matters:** VIX9D is the shortest *listed, market-priced* implied vol there is. If the option
market already priced dealer gamma, this relationship would be zero. It is not, and it is significant
in every four-year sub-period across 15 years. So there is genuinely un-priced, harvestable volatility
on high-gamma days. This is a **volatility/range** prediction — exactly the use `RESEARCH_BOTS.md`
sanctions, and *not* a directional claim.

Downstream, model-free: iron-condor survival with strikes at ±1.25 forecast SD —
**60% on low-gamma days vs 81% on high-gamma days (t = +10.9).**
Model-free breakeven credit for a 1.25SD/1SD-wide condor: **9.6% of width on low-gamma days vs 4.2% on
high-gamma days** — you need less than half the credit to break even.

### 1.2 THE 0DTE RULE SET

> **Trade only the range, never the direction. Sell premium only when dealer gamma says the range will
> be small relative to what the option market is charging. Stand down otherwise.**

**Universe:** SPX (or XSP; SPY is the backtest proxy). Cash-settled index only.

**Entry gate — all must pass:**
1. **Gamma gate:** prior-close dealer GEX z-score (252-day, past-only) **> +0.5**. This is the whole edge. Fires ~81 days/yr (32% of sessions).
2. **Time window:** enter **10:30–13:00 ET**. Do not enter at the open (the opening drive is the least pin-like part of the day); do not enter after 14:00 (not enough credit left).
3. **Event blackout:** no new positions on FOMC days, CPI days, or quarterly triple-witching.
4. **Liquidity:** the four legs must be quotable inside a reasonable net bid/ask; price off the mid, never the ask.

**Structure:** 0DTE **iron condor**.
- Short strikes at **≈1.25 SD of the remaining-session implied move** (SD = ATM IV × √(minutes left / 390) × spot).
- Wings **≈1 SD wide** (in SPX points, that's roughly 1× the same distance again).
- Both sides symmetric. **Do not tilt bullish** — tested and it does not help (§3.4).

**Sizing:** risk **5% of account per condor** (risk = width − credit). Never more than one 0DTE condor
open at a time. Historical max drawdown at 5% is −8%; drawdown scales roughly linearly with the risk
fraction, so 20% risk implies ~−35%.

**Exits:**
- **Software stop at −0.5 × max risk** (i.e. when the position is down half of what you could lose).
  Per-side: a stopped call spread does **not** force-close the untouched put spread.
- No profit target. Cash-settled, so let it expire if untouched.
- Hard time-stop: flat by 15:55 if the product is not cash-settled.

**Stand-down rule:** if GEX z ≤ +0.5, **do not trade 0DTE at all that day.** In 2022 this rule fired
only 6 times all year — that is the feature, not a bug.

#### Honest out-of-sample performance (2016-01 → 2026-07, 853 trades, never tuned on)

At the **evidence-based** assumption cell (`AWARE = 0.35`, `vrp = 1.10`, stop −0.5R):

| Metric | Value |
|---|---|
| Trades | 853 (≈81/yr) |
| Avg return per trade (on capital at risk) | **+3.7%** |
| Win rate | 91% |
| Profit factor | 2.04 |
| t-stat | +7.4 |
| Deflated Sharpe (n_trials = 20) | 1.00 |
| Per-trade Sharpe, annualised | 2.29 |
| CAGR at 5% risk/trade | **16.2%** |
| Max drawdown at 5% risk/trade | **−8.1%** |
| Worst single trade | −50% of risk (the stop) |

**Full assumption matrix — average return per trade (%):**

| vrp \ AWARE | 0.0 (market blind) | 0.35 (evidence) | 0.5 | 1.0 (fully priced) |
|---|---|---|---|---|
| 1.00 | +3.10 | +1.79 | +1.10 | **−0.37** |
| 1.10 | +4.47 | **+3.75** | +3.24 | +1.48 |
| 1.20 | +5.50 | +4.85 | +4.44 | +3.10 |
| 1.30 | +6.03 | +5.76 | +5.62 | +4.34 |

**The honest band is +1.5% to +4.5% per trade → roughly 8-18% CAGR at 5% risk.** The strategy only
dies in the single most hostile corner (market fully gamma-aware *and* zero variance premium), which
the VIX9D evidence argues against.

**Robustness (no knife-edge fitting):**

| Short strike | 1.00 SD | 1.15 | 1.25 | 1.40 | 1.50 |
|---|---|---|---|---|---|
| avg/trade (AWARE 0.5) | +6.3% | +4.1% | +3.2% | +2.2% | +2.0% |

| Gamma gate | gz>−0.5 | gz>0 | gz>+0.25 | gz>+0.5 | gz>+0.75 | gz>+1.0 |
|---|---|---|---|---|---|---|
| avg/trade | +3.5% | +3.5% | +3.5% | +3.2% | +3.7% | +4.4% |
| trades/yr | 159 | 120 | 102 | 81 | 63 | 48 |

Every cell is positive. There is no spike to overfit to — it is a plateau.

**Year by year (5% risk/trade, evidence-based cell):**

| 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| +2.6% | +18.0% | +3.1% | +17.8% | +16.7% | +31.0% | +2.6% | +25.0% | +10.7% | +42.1% | +6.4% |

No losing year, because the gate stands the strategy down in bad-gamma regimes (2022: 6 trades).

**Independent confirmation on 494 days of real minute bars** (marked to the minute, real intraday path):

| Entry | Stop | gz > +0.5 | gz < −0.5 | max DD @10% risk |
|---|---|---|---|---|
| 11:00 | none | **+6.7%** | +3.3% | −14% / −21% |
| 11:00 | −0.5R | **+7.3%** | +3.6% | **−7%** / −14% |
| 13:00 | −0.5R | +6.8% | +3.6% | −7% / −14% |

The high-vs-low gamma contrast survives on real paths, and the −0.5R stop **halves the drawdown while
slightly improving the mean**. That is why the stop is in the rule.

---

## 2. SUGGESTIVE (real, but not sized on)

### 2.1 The DIX bullish-confluence directional signal
Prior-close DIX confluence ≥ 2 of 4 signals gives **+12.8 bp** open→close on the underlying,
**t = +3.04** over 15 years, and it is directionally consistent in all four sub-periods
(t = +2.13 / +1.07 / +1.64 / +1.99). **The signal is real.**

But it is not monetisable in 0DTE options (§3.1), and it adds nothing to a credit spread. Use it only
as *context* — e.g. as a discretionary reason to skew a condor's wing widths, or as an input to a
non-options position. Do not build a 0DTE trade on it.

### 2.2 Intraday price confirmation
On 494 minute-bar days, requiring price above the 30-minute VWAP **and** an up opening range roughly
**triples** the conditional move on confluence days (+13.9 bp → +36.1 bp). But n = 34 and t = 1.42.
Suggestive only; two years cannot validate a filter.

### 2.3 Condor entry timing
11:00 entry edged 09:35 and 13:00 on 494 days. A three-way choice on a small sample — treat
"midday, don't force the open" as the takeaway, not "11:00 exactly."

---

## 3. REJECTED (tested honestly, did not survive)

### 3.1 Buying 0DTE premium on the directional signal — **REJECTED**
The best directional signal in the repo, in the most favourable structure, 2020+:

| Structure | vrp 1.00 | 1.10 | 1.20 | vs all-days control |
|---|---|---|---|---|
| naked ATM call | −2.4% | **−11.3%** | −18.7% | +8.5pp |
| ATM/+1SD call debit spread | −4.8% | **−10.0%** | −15.4% | +7.8pp |

The signal genuinely helps (+8pp over an unconditional control, t ≈ +1.9) — **it just isn't nearly
enough.** A +13 bp expected move cannot pay for an option that costs ~0.37% of spot. Adding intraday
confirmation and stops improves it to −5% per trade. Still a loser. **Do not buy 0DTE calls or puts.**

### 3.2 "Below the gamma flip = buy premium" — **REJECTED**
This is the central claim of the existing `STRATEGY_0DTE.md`, and the data does not support it:

| Long structure on gz < −0.5 days | vrp 1.00 | 1.10 | 1.20 | gate value vs all days |
|---|---|---|---|---|
| straddle | +2.1% (t=0.56) | **−7.2%** | −14.9% | +14.9pp |
| strangle | +1.4% (t=0.16) | **−19.1%** | −36.0% | +24.2pp |

The gamma gate is *hugely* valuable here (+15 to +24pp over buying premium randomly) — but the base
is so negative that the gated version is still a loser at any realistic variance premium. **The correct
version of the rule is: on short-gamma days, stand down. Not "buy premium."** This is a direct
correction to the existing strategy doc.

### 3.3 DIX confluence as a premium-selling filter — **REJECTED**
Edge over the unconditional control: **+0.0 pp**. Permutation test (500 shuffles): **p = 0.494**.
Model-free check: the signal does not reduce the −1.5 SD downside breach rate (diff +0.3pp, t = +0.24).
Direction and premium-selling are orthogonal here.

### 3.4 Bullish tilt on the condor — **REJECTED**
Dropping the call side on confluence days changed the final rule by **−0.27 pp** per trade. Keep it symmetric.

### 3.5 Waiting for a better 0DTE directional entry — **REJECTED**
Entry at 09:30 / 09:45 / 10:00 / 10:30 on confluence days: +16.2 / +14.4 / +13.9 / +12.6 bp. The edge
decays with delay; there is no magic entry hour.

### 3.6 Sector-rotation relative strength (swing) — **EMPHATICALLY REJECTED**
Forward 21-day **excess** return of the top-K sectors vs SPY, OOS 2010+, across 9 lookback × K
combinations: every t between **−1.6 and +0.6**, most negative. With a regime filter: same.
The picks' absolute return (+0.6% to +1.15%) is at or below SPY's on the same days (+1.04%).

Option overlay, with controls (35-DTE debit spread, vrp 1.10):

| picks | SPY control | random-pick control | equal-weight control |
|---|---|---|---|
| **−7.4%** | +11.8% | −2.5% | −4.2% |

**The signal picks names that do worse than random.** Permutation test: **p = 0.867**.
Top-minus-bottom spread: **negative** (−1.9pp, t = −0.33). Anchored walk-forward over 18 configs:
**−6.3% per trade, DSR 0.00, equity ×0.01.** It never worked here (train era t = +0.82) and it
certainly does not work now.

### 3.7 Buying swing index calls / call debit spreads — **REJECTED as an edge**
This *looks* great per trade: SPY+QQQ 35-DTE debit spreads, weekly staggered, OOS 2010+ →
**+11.6% per trade, t = +5.9**, positive in all four sub-periods (+10.1 / +16.4 / +9.1 / +10.4%).

But that is **leveraged beta, not alpha**, and once you simulate it honestly — with overlapping
tranches, a cap on total simultaneous exposure, and Sharpe computed from *non-overlapping monthly*
aggregates (the naive weekly √52 annualisation is wrong and inflates it to 1.17) — it loses to simply
owning the index:

| | CAGR | max DD | Sharpe |
|---|---|---|---|
| debit-spread overlay (f=5%, ≤25% at risk) | 12.0% | −58% | **0.51** |
| debit-spread overlay (f=3%, ≤12% at risk) | 7.0% | −35% | 0.48 |
| **SPY buy & hold** | **14.3%** | **−34%** | **1.03** |

Lower return, half the Sharpe, worse drawdown. The −100%-per-trade tail forces small sizing, and
small sizing caps the CAGR below the underlying's. **Buying swing index calls is a worse way to own
equity beta than owning equity.** The `short_sd` "parameter" is monotone (wider = higher mean) — it is
a leverage dial, not an optimum.

### 3.8 Swing index put credit spreads (35-DTE VRP harvest) — **REJECTED**
The most-documented options edge in existence, tested the same way: weekly-staggered 35-DTE SPY put
credit spreads at −1SD/−1SD, closed at 14 DTE.

Per trade it looks fine (+2.1% to +2.5%, t = 3.2-4.7, 85% win). As a portfolio it is not:
**CAGR 4.2-7.0%, Sharpe 0.44-0.69, max DD −32% to −42%** — again beaten by SPY buy & hold on every
axis. Worse, the **2018-2021 sub-period averaged +0.03% per trade (t = 0.02)** — four dead years.
Deflated Sharpe **0.83**, below a 0.95 bar. Regime and VIX-term-structure gates both *hurt*.

**Why does the 0DTE version work and the 35-DTE version not?** Two reasons: (a) at 0DTE there is a
conditioning variable (dealer gamma) that provably is *not* in the implied vol, and at 35 DTE there is
no analogue; (b) frequency — 81 independent trades/yr vs ~12, so the small edge actually compounds
instead of being erased by one bad month.

---

## 4. THE SWING VERDICT

**There is no validated swing options rule set in this data.** Sector rotation is dead, long index
premium is worse than owning the index, and short index premium at 35 DTE does not beat buy-and-hold
and has a four-year dead period.

The only honest swing "rule" is: **own the index. If you want more, own more of it (or a modest
leveraged ETF), but do not pay option premium for the privilege.** SPY buy-and-hold over 2010-2026:
CAGR 14.3%, Sharpe 1.03, max DD −34%. Every option overlay tested made that strictly worse.

If a swing options sleeve is wanted anyway, the least-bad version is the put-credit-spread program in
§3.8 at small size — but it should be labelled a diversifier, not an edge, and it needs live-quote
validation before any capital.

---

## 5. THE GROWTH GOAL — honest arithmetic

**Target: $5,000 → $100,000 by 2026-11-19.**
That is 106 calendar days = **15.1 weeks** = a **20× multiple** = **+21.9% per week**, or **+4.04% per
trading day**, compounded, without a single break in the chain.

**What the validated 0DTE sleeve actually delivers:** 1.56 trades/week at +3.75% per trade on the
risked amount.

| Risk per trade | Weekly | Result on 2026-11-19 | Comment |
|---|---|---|---|
| 5% (backtested DD −8%) | +0.29% | **$5,226** | the sane setting |
| 10% | +0.59% | $5,463 | still reasonable |
| 25% | +1.47% | $6,234 | DD would be ~−40% |
| 50% | +2.94% | $7,757 | DD ~−80%; one bad streak ends it |
| **374%** | **+21.9%** | **$100,000** | **impossible — you cannot risk 3.7× your account** |

Full-Kelly on this edge is 172% of equity — i.e. Kelly itself says the position you'd need is larger
than the account. The swing sleeve is worse: it would need 189% risked per weekly entry, and with four
overlapping tranches that is **755% simultaneously at risk.**

### The plain statement
**$5,000 → $100,000 by 2026-11-19 is not achievable with any rule that survived this testing, and it
is not achievable by sizing up either — the required bet size exceeds the account.** The honest range
for the 15 weeks remaining is roughly **$5,200 (prudent) to $7,800 (aggressive to the point of
recklessness)** — i.e. **+4% to +55%**, not +1,900%.

Anything that claims otherwise is either taking bets where one loss is terminal, or is a curve-fit.

### What IS achievable
The 0DTE premium sleeve is a genuine, statistically real, ~81-trades-a-year machine with a
**+1.5% to +4.5% per-trade expectancy and a Sharpe near 2**. Run at 5-10% risk per trade it compounds
at roughly **16-35% a year with single-digit-to-teens drawdowns**. Run at an aggressive 25-50% it can
plausibly do **2-4× a year** — but with 40-80% drawdowns and real ruin risk, and only if the modelled
option pricing holds up against live quotes.

That is the honest ceiling. It is a good business. It is not a 20×-in-15-weeks business.

---

## 6. What must be validated before any real money

1. **Live option quotes.** Every P&L number here comes from a *model*. The single highest-value next
   step is to log real SPX 0DTE condor credits at 10:30-13:00 for 60 sessions and compare the actual
   credit-as-%-of-width against the model-free breakevens in §1.1 (4.2% high-gamma / 9.6% low-gamma).
   If real credits clear those, the edge is confirmed; if not, it is dead.
2. **Is same-day IV gamma-aware?** The VIX9D evidence says the market prices only ~a third of the
   gamma effect at the 9-day tenor. The 0DTE surface could be smarter. Measure directly: regress
   observed 0DTE ATM IV on prior-close GEX z, controlling for VIX. If β is strongly negative, the
   edge shrinks toward the AWARE=1 column.
3. **Shadow-mode the gate** (per `RESEARCH_BOTS.md`): run the GEX gate in observe-only mode, logging
   what it *would* have blocked, before letting it gate live trades.
4. **Slippage on the stop.** The −0.5R stop assumes you can exit there. On a gap or a fast tape you
   cannot. Budget for the un-stopped tail: without the stop the max drawdown roughly doubles.
5. **Paper-graduation gate before live:** ≥30 filled condors, positive expectancy, ≥85% win rate,
   profit factor 1.5-4.0, drawdown within 1.5× the backtested figure.

## 7. Biggest risks to the 0DTE rule set

- **Model risk dominates statistical risk.** DSR = 1.00 says the result is not a fluke *given the
  assumptions*; it says nothing about whether the assumptions are right. The vrp/AWARE matrix, not the
  DSR, is the real uncertainty statement.
- **Negative skew.** 91% win rate, and losers average about −50% of risk. Twelve consecutive
  max-losers is a −45% account at 5% risk. Position size for the tail, not the win rate.
- **Regime death.** The gamma effect is stable over 15 years, but 0DTE flow has grown enormously since
  2022 and the mechanism could be arbitraged away. Re-run the §1.1 regression quarterly; if the VIX9D
  β(gz) crosses zero, stop trading the rule.
- **Correlated tail.** A gap-through-the-wings day on a high-gamma read is exactly the scenario the
  gate says won't happen. It will happen. Cap concurrent exposure at one condor.
- **Concentration.** All the surviving edge is in one sleeve, one product, one mechanism. There is no
  diversifying second edge in this data — the swing work says so plainly.
