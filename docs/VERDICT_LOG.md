# Verdict log

**This is the only place a verdict is recorded. When two documents in this repo
disagree, this file wins.**

The research here changed its mind twice and nothing was ever retracted, only
annotated, so three answers to the same question shipped side by side as if all
three were current. That is what this file exists to stop. One entry per claim,
newest first. A claim leaves this repo's instructions the moment it is written
down here as REFUTED; it does not leave the repo, because how the conclusion
moved is worth keeping.

**Statuses**

| status | meaning |
|---|---|
| **CURRENT** | measured, survives, safe to act on within its stated limits |
| **SUPERSEDED** | the claim still holds, but an earlier *number* for it was wrong. Quote the newer one |
| **REFUTED** | measured and killed. Not an instruction anywhere, at any size |

**Rules for this file**

1. A verdict is recorded here first, then reflected in the docs and the code. Not
   the other way round.
2. Every entry names the measurement that changed it and the file that carries
   the evidence. An entry with no measurement is not an entry.
3. Nothing is deleted from this log. A reversal is a new entry, dated, above the
   old one.
4. Where a figure could not be sourced from a document in this repo, the entry
   says so in the open. It is never guessed.

---

## 2026-08-24: log created

Written during the repo audit (`docs/AUDIT.md` §2). No new measurement was taken
on this date. Every number below is quoted from the research documents already in
the repo, and the entries record the state those documents actually leave the
research in. Two documents were moved to `07_superseded/` on the same date
because they were still being read as instructions:
`01_START_HERE/STRATEGY_0DTE.md` and `01_START_HERE/RULES.md`.

---

## REFUTED: "below the gamma flip = buy premium"

**Dated:** 2026-08-05
**Claimed:** `01_START_HERE/STRATEGY_0DTE.md`, now `07_superseded/STRATEGY_0DTE.md`. Stated
under "The three questions it answers", question 1, verbatim:

> **Rule:** above the gamma flip = pin (sell premium / spreads); below the flip = trend (buy premium).

**Status: REFUTED.** Long premium on short-gamma days loses money at any realistic
variance risk premium.

**The measurement.** Long structures on `gz < −0.5` days, from `backtest_0dte_rules.py`:

| structure | vrp 1.00 | vrp 1.10 | vrp 1.20 | value of the gamma gate vs buying premium on all days |
|---|---|---|---|---|
| straddle | +2.1% (t = 0.56) | **−7.2%** | −14.9% | +14.9 pp |
| strangle | +1.4% (t = 0.16) | **−19.1%** | −36.0% | +24.2 pp |

The gate itself is genuinely valuable, worth +15 to +24 percentage points against
buying premium at random. The base rate underneath it is so negative that the
gated version still loses. Being right about *which days* does not rescue a trade
that is wrong about *what to do* on them.

**The replacement rule:** on short-gamma days, stand down. Not "buy premium."

**Evidence:** `07_superseded/RULES.md` §3.2 (the table above),
`07_superseded/STRATEGY_0DTE.md` (its original 2026-08-05 correction banner is kept
verbatim near the top), `02_findings/WHAT_FAILED.md`. `risk_gates.py` hard-rejects
0DTE premium buying.

---

## REFUTED: buying 0DTE premium on any directional signal

**Dated:** 2026-08-05
**Claimed:** the whole directional half of `STRATEGY_0DTE.md`: score the day, pick
a side, buy a naked call or put.

**Status: REFUTED.** −10% to −11% per trade at the evidence cell, and the best
directional signal in the repo in its most favourable structure does not change
the sign.

**The measurement.** The strongest directional signal available (prior-close DIX
confluence), 2020 onward:

| structure | vrp 1.00 | vrp 1.10 | vrp 1.20 | vs all-days control |
|---|---|---|---|---|
| naked ATM call | −2.4% | **−11.3%** | −18.7% | +8.5 pp |
| ATM / +1SD call debit spread | −4.8% | **−10.0%** | −15.4% | +7.8 pp |

The signal helps by about +8 pp over an unconditional control (t ≈ +1.9). It is
nowhere near enough: a +13 bp expected move cannot pay for an option costing
about 0.37% of spot. Adding intraday confirmation and stops improves it to −5%
per trade, which is still a loser.

**One honest qualification, recorded because it is in the research and must not be
lost.** `02_findings/FINDINGS.md` §3 notes that the −11%/trade figure is an
open-to-close number, and that the same +20 SPX point move is +44% on an ATM 0DTE
call sold after 15 minutes and −12% held to the close. So −11% is the wrong
number for a minutes-held scalp. That does not revive the claim: no
minutes-held version was ever measured positive here, and the intraday direction
hunt in `FINDINGS.md` §2 returned zero of thousands of combinations clearing 55%
on both train and validate. The verdict stands; the specific figure applies to the
open-to-close trade only.

**Evidence:** `07_superseded/RULES.md` §3.1, `02_findings/FINDINGS.md` §2 and §3,
`02_findings/WHAT_FAILED.md`.

---

## REFUTED: the 0DTE iron condor at +3.7% per trade, 91% win, t = +7.4

**Dated:** 2026-08-05/06
**Claimed:** `01_START_HERE/RULES.md` (now `07_superseded/RULES.md`) §1.2, filed
under the heading **"VALIDATED & ROBUST"**: prior-close dealer GEX z-score above
+0.5, sell a 0DTE iron condor, shorts at about 1.25 SD, wings about 1 SD, enter
10:30-13:00 ET, stop at −0.5 × max risk. Headline out-of-sample figures: 853
trades, **+3.7% per trade**, 91% win, profit factor 2.04, **t = +7.4**, deflated
Sharpe 1.00, CAGR 16.2% and max drawdown −8.1% at 5% risk per trade.
`01_START_HERE/ENGINE.md` was built around it and called it "exactly one
validated edge"; it now carries a dated pointer to this log instead.

**Status: REFUTED.** Every one of those P&L numbers came from a pricing model, not
from a price.

**What went wrong.** The P&L was produced by Black-Scholes with a **linear skew
approximation**. `RULES.md` said so itself in §0: "There are no historical option
chains in this repo, so option prices are modelled." The linear skew prices the
call wing at roughly zero when the market actually pays for it, so the model
overstated the condor credit by about **1.6×**. That inflation was the entire
edge.

**The re-measurement.** Re-run on **1,919 sessions of actual SPXW bid/ask**
(2016-09 to 2024-05), no pricing model anywhere:

| entry | shorts | n | win % | avg / trade | credit as % of width | t |
|---|---|---:|---:|---:|---:|---:|
| 10:30 | 0.5% | 859 | 72% | −0.71% | 21.7% | −0.39 |
| **11:00** | 0.5% | 853 | 73% | **−1.70%** | 19.8% | −0.99 |
| 12:00 | 0.7% | 796 | 86% | **+0.95%** | 11.0% | +0.82 |
| 13:00 | 0.5% | 832 | 79% | −0.60% | 13.7% | −0.45 |

Approximately break-even overall. The best cell is +0.95% at t = +0.82, which is
not significant, and there is no year-over-year consistency. **The 11:00 entry the
live system actually used measured −1.70%.**

**Independent corroboration.** Three separate lines agree and none of them is this
repo's own code:

- A live SPXW chain measured during `03_research/RESEARCH_0DTE_EDGE.md` puts
  honest expectancy at about **1.2% of risk per trade, not 3.7%**.
- Vilkov (SSRN 4641356), on real Cboe 30-minute SPXW NBBO bars 2016-09 to 2026-01.
  Two cells are quoted in this repo and both are negative net of costs: iron
  butterfly / condor at **Sharpe −0.96** (`03_research/RESEARCH_GITHUB_SWEEP.md`
  §1), and unconditional condors going from **+0.77 gross Sharpe to −0.20 net**
  (`03_research/RESEARCH_0DTE_EDGE.md` §0 and §1.1). That second one is not our
  strategy, since it is unconditional with no gate and no stop, so it is the null
  to beat rather than a refutation on its own.
- Cboe's own iron condor index **CNDR has returned −1.28%/yr net of T-bills for
  16.6 years** (2010-01 to 2026-08), Sharpe −0.18, alpha to SPX −2.74%/yr.
  `03_research/RESEARCH_CONDOR_BUTTERFLY.md` §0.

**What would change this back.** One thing, and it is already specified:
`RULES.md` §6.1 asks for **60 sessions of real SPX 0DTE condor credits** logged at
10:30-13:00 and compared against the model-free breakeven credits (4.2% of width
on high-gamma days, 9.6% on low). `rules.log_credit()` writes those rows. The
counter currently reads **0 of 60**. Until it finishes, the condor is unproven,
not validated, and it must not be sized as an edge.

**Evidence:** `02_findings/FINDINGS.md` §1 (the table above),
`02_findings/WHAT_FAILED.md`, `03_research/RESEARCH_0DTE_EDGE.md` §0,
`03_research/RESEARCH_CONDOR_BUTTERFLY.md` §0.

---

## REFUTED: premium selling as a strategy, on real quotes

**Dated:** 2026-08-06
**Claimed:** the general case underneath the condor rule: that selling defined-risk
option premium on an index harvests the variance risk premium.

**Status: REFUTED.** On real quotes, entering at the ask and exiting at the bid,
every credit structure tested is negative.

**The measurement.** `daily_engine.py`, **147,350 de-duplicated structure-trades**,
SPY 2008-2025, 26 structures × 4 DTE targets × 2 hold rules × 11 regimes:

| structure | win rate | avg / trade | t | worst trade |
|---|---:|---:|---:|---:|
| christmas tree call | 38.2% | **−23.42%** | −24.5 | −723% |
| call credit 30/16 | 54.7% | −16.47% | −10.9 | −6850% |
| iron condor 30/16 | 48.6% | −15.83% | −17.5 | −3111% |
| iron butterfly ATM | 45.9% | −13.83% | −20.1 | −425% |
| put credit 16/05 | 75.7% | −12.84% | −17.6 | −1300% |
| put credit 30/16 | 68.6% | −11.41% | −15.4 | −767% |
| iron condor 16/05 | 63.6% | −10.54% | −13.5 | −3111% |
| broken-wing fly (put) | 55.2% | −8.94% | −18.1 | −505% |
| short straddle | 57.1% | −4.44% | −18.3 | −135% |
| short strangle 30d | 61.2% | −4.19% | −18.1 | −127% |
| short strangle 16d | 68.7% | −3.79% | −17.7 | −130% |
| jade lizard | 65.2% | −2.88% | −18.0 | −89% |
| twisted sister | 54.6% | −0.32% | −9.4 | −27% |

**Every one negative, all with |t| > 9, the worst at t = −24.5.** Win rates of 63%
to 76% sit alongside deeply negative expectancy, which is the trap itself,
demonstrated on real fills rather than argued.

**The mechanism, and it is not subtle.** A four-leg structure crosses **eight
spreads round trip**, roughly 10% of capital at risk. The variance risk premium
that makes these strategies look profitable at mid-price is smaller than the
bid-ask spread you pay to get in and out. Fill at mid and you see an edge; fill at
the ask and exit at the bid and you see the opposite.

**Gating does not rescue it.** 1,001 structure × gate cells were tested, including
GEX and DIX z-scores, VIX percentile, VIX term structure, IV-minus-RV percentile,
breadth and trend. The best cell was `put credit 30/16` on DIX-high plus
VIX above the 67th percentile at +4.30%/trade, t = +3.49. The multiple-testing bar
for 1,001 trials is an expected best |t| of about **3.72** under the null, so the
best gate does not clear noise. **Zero of the top 15 gates are positive in all
three periods** (2008-13 / 2014-19 / 2020-25).

**Evidence:** `01_START_HERE/HANDOFF.md` §3 (the table above),
`02_findings/WHAT_FAILED.md`, replicated independently with separate code on the
same file in `03_research/RESEARCH_CONDOR_BUTTERFLY.md` §0 and §4.3.

---

## SUPERSEDED: the range finding stated at "t = −16"

**Dated:** 2026-08-05, superseded by the VIX9D measurement in the same session
**Claimed:** `07_superseded/STRATEGY_0DTE.md`, under "the GAMMA REGIME":
"15-year backtest (2011-2026), t = −16, stable EVERY year: low/negative-gamma days
average ~2.4% range vs high-gamma days ~0.7%."

**Status: SUPERSEDED.** The finding is real. That t-statistic is not the one to
quote, because it is measured against this repo's own volatility forecast rather
than against a price anyone can trade.

**Why the two numbers differ.** `RULES.md` §1.1 regresses normalised range on the
prior-close GEX z-score under two different normalisers:

| range normalised by | β(gz) | t |
|---|---:|---:|
| our own causal vol forecast | −0.158 | **−15.2** |
| VIX9D, a real market-implied price | −0.074 | **−9.9** |

The "−16" is the first row rounded. The number that matters is the second, because
VIX9D is a listed, market-priced implied volatility, so the effect measured against
it is the part the option market has *not* already priced. The headline
quintile figure against VIX9D is **t = −13.2**.

**Quote t = −13.2, and say what it is measured against.** Two t-statistics for one
claim on one page is how a reader stops trusting the page.

**Evidence:** `07_superseded/RULES.md` §1.1, `02_findings/FINDINGS.md` §1.

---

## CURRENT: dealer gamma predicts the intraday range, and it does not convert to profit

**Dated:** 2026-08-05, reaffirmed by the real-quote re-run of 2026-08-05/06
**Claim:** prior-close dealer gamma predicts the day's realised range relative to
what the option market charges for it, and the option market does not fully price
that.

**Status: CURRENT**, with a limit that is part of the finding and must travel with
it: **it does not convert into profit at real option prices.**

**The measurement.** Realised range as a multiple of the VIX9D-implied move, by
prior-close GEX z quintile, 2011-07 to 2026-07 (3,765 days):

| GEX z quintile | Q1 (low gamma) | Q2 | Q3 | Q4 | Q5 (high gamma) |
|---|---:|---:|---:|---:|---:|
| realised / implied | **1.139** | 1.025 | 0.958 | 0.933 | **0.843** |

**Q5 vs Q1: t = −13.2, p = 1.3e-37.** Significant in every four-year sub-period
across 15 years. Model-free downstream: iron-condor survival at ±1.25 forecast SD
is 60% on low-gamma days against 81% on high-gamma days (t = +10.9), and the
model-free breakeven credit is 9.6% of width on low-gamma days against 4.2% on
high-gamma days.

**The limit.** The range prediction is real and the profit is not. Re-run on real
SPXW bid/ask the condor built on top of this is approximately break-even (see the
condor entry above). `02_findings/FINDINGS.md` §1 states it plainly: the range
finding "is real. It simply does not convert to profit at market prices, which is
itself informative: the market has it priced." That sentence is the finding, not a
caveat on it.

**Therefore:** dealer gamma is a **risk and volatility regime gate**, never a
directional forecast and not on its own a licence to sell premium. No
peer-reviewed index-level gamma paper uses signed return as the dependent
variable; every one uses absolute return
(`03_research/RESEARCH_DIRECTION.md` §5b).

**Evidence:** `07_superseded/RULES.md` §1.1, `02_findings/FINDINGS.md` §1,
`02_findings/WHAT_WORKS.md` §3.

---

## CURRENT: the three signals that survived honest testing

**Dated:** carried forward from the 2026-08-05/06 results.
`02_findings/WHAT_WORKS.md` carries no date of its own; that is stated here rather
than guessed at.

**Status: CURRENT.** These three are what the repo actually has. The bar applied
was: measured out of sample, corrected for multiple testing, non-overlapping
samples, and compared against the base rate rather than against zero.

**1. Short interest, and the sign is backwards.**

| horizon | IC (Spearman) | n |
|---|---:|---:|
| 21 days | −0.068 | 13,219 |
| 63 days | **−0.107** | 13,219 |

Monotone across every bucket. The sign is **negative**: high short float predicts
*lower* forward returns. The squeeze thesis is the opposite of what the data says.
Carried in `signal_weights.py` at weight 0.30, direction −1.

**2. VIX backwardation, the only signal that held across all three splits.**
t = **+3.9 / +2.8 / +2.1** on train, validate and test. It degrades and never
flips, which is what a real effect looks like. Weight 0.30, direction +1.
Independently corroborated as the top-ranked swing candidate in
`03_research/RESEARCH_SWING_ACADEMIC.md`: VIX > VIX3M inside an uptrend, mean
+2.37% per 21-day hold, +1.51 pp over the base rate, positive in all three splits.

**3. Low dealer gamma as a regime filter, not a signal.** **8 of 8** directional
structures tested paid more in low-gamma regimes than high-gamma ones. It says
when directional bets get paid at all, not which way to bet.

**Partial credit, recorded so it is not re-proposed as more than it is:**
compressed volatility plus a volume surge gives a 1.55× lift on P(3σ move) at 42
days across 158 names and 1,159,258 stock-days, which on a 3% base rate is a 4.7%
hit rate; far-OTM buying is −45.6% overall but **+5.6%** filtered to contracts with
a bid-ask spread of 20% or less; and returns improve monotonically toward the
money, from −90% at the far tail to **+26.1% at 16-30 delta**.

**Evidence:** `02_findings/WHAT_WORKS.md`, `signal_weights.py` (the weight
registry is the single source of truth for the weights themselves).

---

## Claims retired earlier, kept here so they are not re-proposed

These were killed in the same 2026-08-05/06 work and are recorded in
`02_findings/WHAT_FAILED.md` and `07_superseded/RULES.md` §3. They are listed in
one block because none of them was ever a live instruction in the dashboard.

| claim | status | measurement | evidence |
|---|---|---|---|
| Far-OTM lottery buying, "$200 to $1M, only one has to hit" | REFUTED | −90% to −48% by distance, on 10,535,928 purchases held to expiry | `02_findings/WHAT_FAILED.md` |
| Earnings straddles | REFUTED | −35.03% per trade, t = −95.7 | `02_findings/WHAT_FAILED.md` |
| Any intraday directional edge on SPX or NDX | REFUTED | 56 features, 220 conditions, thousands of combinations: **zero** clear 55% on train and validate | `02_findings/FINDINGS.md` §2 |
| DIX confluence as a premium-selling filter | REFUTED | +0.0 pp over the control, permutation p = 0.494 | `07_superseded/RULES.md` §3.3 |
| Bullish tilt on the condor | REFUTED | −0.27 pp per trade | `07_superseded/RULES.md` §3.4 |
| Sector-rotation relative strength (swing) | REFUTED | picks do worse than random, permutation p = 0.867, −6.3%/trade walk-forward | `07_superseded/RULES.md` §3.6 |
| Buying swing index calls / call debit spreads | REFUTED as an edge | +11.6%/trade looks great and is leveraged beta: CAGR 12.0%, Sharpe 0.51 against SPY buy-and-hold 14.3% / 1.03 | `07_superseded/RULES.md` §3.7 |
| Swing index put credit spreads (35-DTE VRP harvest) | REFUTED | CAGR 4.2-7.0%, Sharpe 0.44-0.69, and 2018-2021 averaged +0.03%/trade (t = 0.02) | `07_superseded/RULES.md` §3.8 |
| MRNA +177% was predictable | REFUTED | 0 of 200 unusual-flow alerts fired; candidate signals showed 0.68-1.02× lift across 810,300 ticker-days | `02_findings/WHAT_FAILED.md` |
| $5,000 to $100,000 by 2026-11-19 | REFUTED | needs +21.9%/week, i.e. 374% of the account risked per trade; full Kelly on the modelled edge was already 172% | `07_superseded/RULES.md` §5 |

---

## Where the evidence lives

| file | what it is |
|---|---|
| `02_findings/FINDINGS.md` | the real-quote re-run that killed the condor, and the direction hunt |
| `02_findings/WHAT_WORKS.md` | the three surviving signals and the weight registry |
| `02_findings/WHAT_FAILED.md` | everything that was tested and lost |
| `02_findings/METHODOLOGY_TRAPS.md` | twelve ways a backtest lies. Four of them faked a win here |
| `01_START_HERE/HANDOFF.md` | the 147,350-trade premium-selling result, §3 |
| `03_research/` | 26 literature and repo sweeps. Inputs, not conclusions. `INDEX.md` carries a one-line verdict for each |
| `07_superseded/` | the two retired documents. Record only. Nothing in there is an instruction |
