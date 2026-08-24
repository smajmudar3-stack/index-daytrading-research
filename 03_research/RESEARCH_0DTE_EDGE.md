# 0DTE Edge Research — What Could Actually Improve the Condor Sleeve

**Built:** 2026-08-05 · **Scope:** GitHub, SSRN/journals, vendor literature, plus a live option-chain
measurement taken during this research.
**Companion docs:** `RULES.md` (what we validated and rejected), `RESEARCH_BOTS.md` (prior repo survey).

This document is deliberately short on "maybes." Most of what is written about 0DTE management is
vendor marketing; §6 names it. Four findings are load-bearing, and two of them are uncomfortable.

---

## 0. The headline

Three things changed during this research:

1. **The data gap is closed, today, for $0.** A published academic replication package ships
   **1,380 real 0DTE days of SPXW bid/ask at 30-minute marks including 10:30–13:00**. Every modelled
   number in `RULES.md` can be re-derived from real quotes this week. This is the single
   highest-EV item in this document by a wide margin.
2. **Our cost model is fine; our *option pricing* model is not.** I measured a real SPXW chain
   (§2). Transaction costs are ~0.41% of risk — close to what we charge, and not the problem.
   But `bt_options.strike_iv` overstates the condor credit by **~1.6×** even with ATM IV pinned to
   the market, because its linear skew is qualitatively the wrong shape. Realistic expectancy is
   roughly **⅓ of the +3.7%/trade headline** — still positive, still requires the gate.
3. **There is a published, cost-modelled, 9.5-year study on real Cboe SPXW data that finds iron
   condors go from +0.77 gross Sharpe to −0.20 net.** It is not our strategy (unconditional, ATM-ish,
   no stop), so it is not a refutation. It is the null hypothesis we now have to beat, using its own
   free data.

Ranked action list is in §8.

---

## 1. TIER 0 — the null hypothesis we must beat

### 1.1 Vilkov (2026), "0DTE Trading Rules: Tail Risk, Implementation, and Tactical Timing"

- **Source:** SSRN 4641356, updated May 2026. Full replication package, MIT:
  `https://github.com/vilkovgr/0dte-strategies` · annotated paper:
  `https://github.com/vilkovgr/0dte-strategies/blob/main/docs/paper/paper-annotated.md`
- **Data:** Cboe 30-minute SPXW bars **with NBBO and sizes**, **Sept 2016 – Jan 2026**. Seven
  structure families. Overlaps our OOS window almost exactly.
- **Cost model — three layers, and this is the right way to do it:** (a) mid-quote, (b) each leg pays
  **half the observed bid-ask**, (c) plus 0.5 bp of underlying in slippage/fees. P&L is measured
  **spot-relative**, not as a % of premium — % of premium flatters short-premium strategies.
- **The claim:** conditional OOS (logistic, 252-day rolling, Apr 2019 → Feb 2026):

  | Family | Gross SR | **Net SR** |
  |---|---|---|
  | Put ratio spreads | 1.18 | **0.93** |
  | Top-3 basket | 1.12 | **0.82** |
  | **Iron butterfly / condor** | 0.77 | **−0.20** |
  | Straddle / strangle | 0.56 | **0.39** |

  Iron condors are the **only** family that flips negative on costs. Median realised VRP 10:00→close
  is **~0.0011% of underlying**. ES₁% runs 0.58–1.58% of underlying. Paper's conclusion:
  *"Unconditional 0DTE exposure is difficult to justify as a standing allocation once one accounts for
  realistic execution and downside capital usage."*
- **Why it is NOT a refutation of our rule** — the differences are material, and all in our favour:
  - **Unconditional.** Entered daily. Our gate fires on 32% of sessions and Baltussen (§3.1) says
    the excluded 68% is where trend days live.
  - **ATM-ish.** Constructed on an interpolated moneyness grid of **0.98–1.02 only** — i.e. the whole
    structure lives inside ±2% of spot. On a typical 0.85%-SD session that is ±2.35 SD total, so his
    "condor" is much closer to an iron butterfly than our 1.25SD/1SD geometry.
  - **No stop, held to 16:00.** No per-side stop, no exits.
  - **His GEX features are not our signal.** He tests OI-weighted gamma exposure at 10:00 ET as a
    continuous ML feature, explicitly *not* a dealer-inventory reconstruction, and not a binary
    prior-close z-score regime gate. Baltussen shows the signal lives in the sign split.
- **Honest read: real, unusually transparent, and the correct null.** Working paper, not peer-reviewed;
  its conditional-OOS "gross daily strategy return" is defined as `sign(p̂−0.5) × underlying return`,
  which is a directional bet on the index rather than on the structure — an odd construction I do not
  fully trust. But the unconditional cost arithmetic is sound and the data is public.
- **How it slots in:** it *is* the data (§7.1). Re-run our exact rule — GEX gate, 1.25SD/1SD,
  10:30–13:00, −0.5R stop — on his panel under his three-layer cost ladder. That single experiment
  either confirms the sleeve on real quotes or kills it.

---

## 2. TIER 0 — I measured a real chain, and the model is the problem, not the costs

I pulled a live SPXW chain during this research (Robinhood market-data, snapshot **2026-08-05 16:15 ET**,
expiry **2026-08-06**, SPX **7723.55**, VIX **15.81**). Working scripts: `/tmp/model_vs_market2.py`,
`/tmp/fit_smile.py`, `/tmp/condor_realquote.py`.

**Implied session move backed out of the real ATM price:** ATM 7725 call mid 26.10 →
σ_session = 26.10 / (0.3989 × 7723.55) = **0.847% = 65.4 SPX pts = 1 SD**. So the rule's geometry is
shorts at ±82 pts (7645 P / 7805 C) and wings 65 pts wide (7580 P / 7870 C). Quoted deltas at the
shorts: **−9.5 and +7.8** — the rule is picking ~8–10 delta shorts, which is what it should.

### 2.1 The good news: the cost model is defensible, and Vilkov's cost story does not transfer

| | half-spread, 4 legs, one way |
|---|---|
| **SPXW real** | 0.075 + 0.050 + 0.075 + 0.050 = **0.250 pts** = **0.41% of risk** |
| **SPY real** (same geometry, /10 notional) | 0.010 + 0.005 + 0.005 + 0.005 = **0.025 pts** = 0.39% of risk |
| **Our model on SPY** — `max(1% of mid, $0.01)` | **0.040 pts** = 0.62% of risk → **1.6× conservative** |

SPY 0DTE is genuinely penny-wide; SPXW ticks are 5c below $3 / 10c above. **Per unit of notional the
two cost the same**, and our backtest's SPY cost model *over*charges by ~60%. Transaction costs are
not what kills this structure. Caveat: after-hours snapshot, spreads at 16:15 are wider than midday,
so if anything this overstates the real cost.

### 2.2 The bad news: `strike_iv` is the wrong shape, and it inflates the credit ~1.6×

With the model's ATM IV **pinned to the market's own ATM IV** — so this is purely smile shape, not a
vrp disagreement:

| strike | type | SD | mkt mid | model | model/mkt |
|---|---|---|---|---|---|
| 7580 | put | −2.19 | 0.600 | 1.709 | **2.85×** |
| 7645 | put | −1.20 | 2.725 | 6.129 | **2.25×** |
| 7805 | call | +1.24 | 1.975 | 1.488 | 0.75× |
| 7870 | call | +2.24 | 0.350 | **0.005** | **0.01×** |

`strike_iv` is `m = 1 + 0.15 × sd`, a monotone **downward-sloping line**. The real 0DTE surface is a
**V-shaped smile that turns back up in the call wing** — observed IVs here: ATM 16.85%, 7805C 14.34%,
7870C **16.85%**, 7905C **19.20%**. Our model drives call IV to its 0.55×ATM floor and prices a
2.2-SD call wing at **essentially zero** when the market pays 0.35. Meanwhile it overprices OTM puts
2–3× because a lognormal has fatter near-tails than the real, highly-peaked 0DTE risk-neutral density.

**Net effect on the condor:**

| | credit | % of width | vs 4.2% high-γ breakeven | vs 9.6% low-γ breakeven |
|---|---|---|---|---|
| **MARKET** | 3.750 pts | **5.77%** | **+1.57pp** | −3.83pp |
| **MODEL** | 5.902 pts | **9.08%** | +4.88pp | −0.52pp |

**After the real 0.250-pt spread, the market's edge on a high-gamma day is +0.770 pts = +1.26% of
risk** — versus the **+3.75%** in `RULES.md`. n=1, one snapshot, gamma regime unknown, and the
4.2%/9.6% breakevens inherit our own vol-forecast error. But the direction is unambiguous and it is
exactly the `RULES.md` §6.1 test:

> **The market charges 5.77% of width. High-gamma days need 4.2%. Low-gamma days need 9.6%.**
> The thesis passes, the gate is *necessary* (unconditional selling loses), and the honest
> expectancy is roughly one third of the headline.

This also reconciles us with Vilkov: a small positive **conditional** edge is entirely consistent with
a negative **unconditional** one.

### 2.3 Drop-in fix

Fitting `m = iv(K)/iv_atm` on the 9 observed strikes, in the same coordinates `strike_iv` uses
(`sd = (S−K)/sig_move`):

```
m = 0.8755 + 0.0225*sd + 0.0372*sd^2        R² = 0.81, RMS 0.052
   (current linear skew=0.15 model:          RMS 0.269)
```

Five-fold better fit. It still under-fits ATM (the true 0DTE smile has a cusp at the money that a
smooth quadratic misses), so the better long-run answer is to **stop modelling the smile at all** and
use the real chains from §7. Calibrate the quadratic on ≥60 days before trusting it — one snapshot is
one snapshot.

---

## 3. TIER 1 — real, and worth acting on

### 3.1 The gate has top-journal support, and it *is* the trend-day filter

**Baltussen, Da, Lammers, Martens (2021), "Hedging demand and market intraday momentum,"
*Journal of Financial Economics* 142(1):377–403.**
`https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365` · PDF `academicweb.nd.edu/~zda/intramom.pdf`

- Sample: 60+ futures 1974–2020; the gamma test is S&P 500, **Jan 1996 – May 2020**, NGE from
  OptionMetrics 1996–2017 extended with **SqueezeMetrics** (our own data source) to 2020.
  2,930 negative-NGE days, 3,158 positive-NGE days.
- **Table 7** — last-half-hour return on rest-of-day return, split by prior-day NGE sign:

  | Regime | β | Newey-West t | Adj R² |
  |---|---|---|---|
  | NGE ≥ 0 (dealers long gamma) | 0.82 | 1.03 | **0.05%** |
  | NGE < 0 (dealers short gamma) | 6.63 | **4.78** | **3.58%** |

  Table 8 continuous version: `NGE × r_ROD` = **−123.04 (t = −3.42)**, survives a
  difference-in-difference against a shared time trend, holds using puts only.
- **Honest read: real.** JFE, 24 years, mechanical mechanism, cross-asset corroboration, DiD control.
  Caveats: the NGE proxy is crude (assumes MMs long all calls / short all puts, no OTC); sample ends
  May 2020 so it says nothing about the post-2022 daily-expiry regime; the conditional split is
  in-sample; and it supports the **sign** split, not our z > +0.5 threshold specifically.
- **Slots in as:** the citation for the gate — and, importantly, the answer to "do we need a separate
  trend-day detector?" **Largely no.** Trend days are a short-gamma phenomenon and the gate already
  excludes them. Do not build a second trend filter before testing whether it adds anything to GEX.

Mechanism corroboration, both stronger than the OI proxy:
- **Amaya, Garcia-Ares, Pearson, Vasquez (Cboe, Jan 2025), "0DTE Index Options and Market Volatility."**
  `https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf` — **proprietary
  Cboe trade records with each counterparty's trading capacity**, i.e. actual signed market-maker
  inventory, 1-minute, Jul 2020 – Jun 2023. Conditional variance is negatively related to lagged OMM
  gamma across two GARCH families. **But note the magnitude ceiling: the maximum gamma-induced effect
  is +3.3pp on annualised daily vol.** Our 0.843-vs-1.139 RV/IV spread is a much larger economic effect
  — see §5.2.
- **Adams, Fontaine, Ornthanalai (SSRN 4881008).** Natural experiment: SPXW Tue/Thu expiries did not
  exist before Apr/May 2022, so many pre-2022 sessions had *no* 0DTE at all. Finds a robust negative
  0DTE-availability → realised-vol relation, and crucially that the dampening comes from **longer-dated
  positions that have become 0DTE, not from same-day 0DTE trading.** This validates our choice of a
  prior-close, all-expiry GEX measure over same-day 0DTE gamma.
- **Dissent, for honesty:** Brogaard, Han, Won (SSRN 4426358) find 0DTE trading *increases* volatility
  (+9.10% relative to mean) using a volume-based IV. It is 1-vs-3 and the identification is weaker
  than the availability-based experiment, but the disagreement is real.

### 3.2 Entry timing: the evidence says move later, and it conflicts with our own 494 days

**Dim, Eraker, Vilkov (2024), "0DTEs: Trading, Gamma Risk and Volatility Propagation," SSRN 4692190.**
I extracted **Table 2** from the paper PDF directly. ATM 0DTE straddle returns to expiration by
30-min entry bar, **n ≈ 2,734 days, 01/2012 – 14/06/2023, gross of costs**:

| Entry | Buyer SR p.a. | ⇒ **Seller SR** | Buyer skew |
|---|---|---|---|
| 10:00 | −0.134 | +0.13 | 1.48 |
| **10:30** | +0.054 | **−0.05** | 2.03 |
| **11:00** | −0.097 | **+0.10** | 2.05 |
| 11:30 | −0.355 | +0.36 | 2.13 |
| 12:00 | −0.630 | +0.63 | 2.02 |
| 12:30 | −0.764 | +0.76 | 1.81 |
| **13:00** | −0.711 | **+0.71** | 1.69 |
| 13:30 | −0.762 | +0.76 | 1.70 |
| 14:00 | −0.490 | +0.49 | 1.89 |
| 14:30 | −1.090 | +1.09 | 1.62 |
| **15:00** | −1.349 | **+1.35** | 1.62 |
| 15:30 | −0.731 | +0.73 | 1.50 |

**Our 10:30–13:00 window front-loads into the deadest part of the session.** The seller's
risk-adjusted edge is ~zero at 10:30–11:00 and only becomes material from 11:30.

Supporting: **Almeida, Freire, Hizmeri, "0DTE Asset Pricing"** (SSRN 4701401; sample 6 Jan 2012 –
3 Jul 2023, 1,417 dates, Cboe 1-min bid/ask) find the **relative bid-ask spread is at its minimum and
most stable 10:00–14:00**, widening at both open and close. So gross edge rises through the day while
execution cost stays flat until 14:00 → **the net optimum is plausibly 12:00–14:00, not 10:30–13:00.**

**Honest caveats, and they matter:**
- These are **ATM straddles**, not 1.25-SD condors, and Almeida (§4.1) says ATM is precisely where the
  overpricing lives. The gradient may not transfer to OTM.
- **Gross of costs**, and buyer skew is **+1.5 to +2.1 at every hour** — the seller is short a fat left
  tail all day. The late-day "high Sharpe" comes with the fattest tails (max buyer return 36× at 15:00).
- Not monotone: 15:30 collapses to +0.73.
- **Vilkov's own paper directly contradicts this**, reporting "main qualitative findings are unchanged
  across entry times" for 10:00 / 13:00 / 15:00 / prior-16:00. Different metric (spot-relative P&L vs
  option return), so both can be true, but it is a genuine conflict.
- **Our own 494 minute-bar days say the opposite**: 11:00 entry +7.3% vs 13:00 +6.8%. That is n=494
  with maybe ~160 gated days and a 0.5pp difference — far too thin to settle it.

**Slots in as:** the cheapest high-value test we have. The Vilkov panel (§7.1) has real quotes on a
30-minute grid across the whole session for 1,380 days. Run 10:30 / 11:00 / 12:00 / 12:30 / 13:00 /
13:30 / 14:00 net of half-spread and settle it definitively.

### 3.3 Strike selection: three independent lines of evidence say move the shorts IN

- **Almeida, Freire, Hizmeri, Table 6.** Using Ritchken (1985) second-order stochastic-dominance
  price bounds: **ATM 0DTEs violate the risk-averse *upper* bound 65–70% (calls) / 70–77% (puts) of the
  time** — i.e. systematically too expensive. **OTM options violate the upper bound only 5–9%, and
  violate the *lower* bound 30–50%** — i.e. systematically too **cheap**. Only ~35% of all 0DTEs, and
  ~7% of ATM 0DTEs, satisfy risk-averse bounds. **Our 1.25-SD shorts sell the cheap part of the surface
  and buy an even cheaper part.**
- **Our own robustness table already says this.** `RULES.md` §1.2: short strike 1.00 SD → +6.3%,
  1.15 → +4.1%, 1.25 → +3.2%, 1.40 → +2.2%, 1.50 → +2.0%. Monotone: tighter is better.
- **My real-quote measurement agrees.** At ~1.0 SD by the market's own implied session move the
  credit is 5.77% of width and clears the high-gamma breakeven; push the shorts out to ~1.6 SD and the
  credit collapses to **2.47% of width**, which loses even on high-gamma days.

**Honest counter, and it is the same one we applied to §3.7 of `RULES.md`:** a monotone parameter is a
**leverage dial, not an optimum**. Tighter shorts mean a lower win rate, fatter losers, and a different
interaction with the −0.5R stop; Vilkov's ES₁% of 0.58–1.58% of underlying and his finding that
"left-tail risk dominates mean effects" both bite harder as you move in. **Test 0.9 / 1.0 / 1.1 SD on
real quotes with the stop active and look at the tail, not the mean.**

Also note: Almeida's own naive "write the ATM delta-hedged 0DTE call" benchmark returns Sharpe
**0.004–0.043 gross and −0.032 to +0.013 net** at every entry hour from 10:00 to 14:00. Even the
expensive part of the surface does not pay for naive execution. Their SSD-violation strategy gets
0.23–0.29 net — but that is a per-trade number and the physical density is estimated from a
1996-onward histogram with an imposed equity-premium floor, which is a real look-ahead risk. **Trust
their cross-sectional mispricing map; discard their strategy Sharpe.**

### 3.4 Event calendar: three concrete adds, four concrete deletes

**Knox, Londono, Samadi, Vissing-Jorgensen (Federal Reserve Board, Aug 2024), "Equity Premium Events."**
SSRN 4773692 · `https://www.business.rutgers.edu/sites/default/files/documents/mehrdad-samadi.pdf`
· live tool `pricingthecalendar.com`

Built on **end-of-day SPX option prices using the daily-expiration term structure, Oct 2016 – Dec 2023**
— i.e. on exactly our instrument. **Data-driven: they do not pre-specify which events matter.** The 39
most significant forward periods contain **13 FOMC, 9 CPI, 7 NFP**, the 2016 and 2020 presidential
elections, the 2018 and 2022 midterms, the 2017 French election and runoff, the 2021 Georgia runoff,
the 2019 Trump–Xi G-20 bilateral, and the **January 2018 FOMC minutes release**. Across the full
Bloomberg calendar, FOMC/CPI/NFP carry the largest abnormal macro premia (7.35 bp per forward period).

| Candidate | Evidence | Verdict |
|---|---|---|
| FOMC, CPI | Top-2 priced events | **Keep** (already in the rule) |
| **NFP** | 3rd-largest, 7 of the top 39 | **ADD** |
| **Elections / midterms** | Largest per-event abnormal premia | **ADD** (rare, cheap) |
| **FOMC minutes** | In the top 39; Gao et al. R² = **11.0%** on minutes days, the highest in their paper; 14:00 ET release lands inside our hold | **ADD** |
| PPI, retail sales, ISM, jobless claims | Not identified | **Do not filter** |
| Treasury auctions | Not identified | **Do not filter** |
| Month-end / quarter-end | Not identified | **Do not filter** |
| Jackson Hole | Not identified | **Do not filter** |
| Mega-cap earnings (NVDA) | No study; market implied ~1.05% SPX move for the post-NVDA session in Nov 2024, above CPI/NFP and near FOMC. Journalism, not research | **Add on priors**, ~4 dates/yr, too few to prove |

**Two corrections to conventional wisdom:**

- **Quarterly opex / triple witching may be backwards.** The only real academic work is
  **Golez & Jackwerth (2012), *JFE* 106(3):566–585**, which finds S&P 500 futures are pulled toward the
  ATM strike when options on the *futures* expire, but are **pushed *away*** from the carry-adjusted ATM
  strike right before **index** option expiry ("anti-cross-pinning"), ≥$115M notional shift per
  expiration. **For cash-settled index options — our instrument — the documented effect is dispersion,
  not pinning.** Our triple-witching blackout is right, but for the opposite reason to the one usually
  given. Every "opex is a good condor day because of pinning" claim is unsupported.
- **FOMC premium-selling is, unconditionally, *better* paid than usual.** **Wright (2020), NBER WP
  28306, "Event-Day Options"** (Jan 2011 – Mar 2020, Newey-West): event-day VRPs are positive and
  nearly all significant, and the VRP increase is **larger on FOMC days than on employment-report
  days**. About half the FOMC implied-variance increase is risk premium, not physical vol. **But the
  tail is asymmetric:** his probability-integral-transform test finds the realised stock-futures outcome
  was **never in the bottom two deciles** of the implied distribution on FOMC days, but **was in the top
  two deciles several times.** Reading: **on FOMC days the put wing is over-priced and the call wing is
  not.** Given our per-side architecture, an asymmetric FOMC rule (skip the call side, keep the put
  side) is at least defensible on evidence. The 14:00 statement landing inside our hold is still a
  perfectly good *execution* reason to stand down — just don't call it a pricing reason.

### 3.5 A cheap stand-down candidate that is orthogonal to GEX: first-30-minute realised vol

**Gao, Han, Li, Zhou (2018), "Market Intraday Momentum," *JFE* 129(2):394–414.** SPY TAQ,
1 Feb 1993 – 31 Dec 2013.

The headline (first half-hour predicts last half-hour, in-sample R² 1.6%, OOS 1.4–2.0%) is **not** what
matters to us, and I would discount it heavily: **Baltussen et al. report OOS R² of −1.71% for the Gao
first-half-hour predictor on equity futures**, i.e. it fails out of sample on their data, and the
sample ends in 2013.

**The conditioning result is the useful part, and it is a separate claim:** sorting days into terciles
by **first-half-hour realised volatility**, the intraday-momentum R² goes **0.6% → 1.0% → 3.3%**. Same
monotone pattern for first-half-hour volume. Recessions 6.6%. No-release 2.5% → MCSI 5.5% →
**FOMC minutes 11.0%**.

- **Why it is worth testing:** it is measured at 10:00, before our 10:30 entry; it is roughly
  orthogonal to prior-close GEX; and high first-hour vol → directional continuation into the close is
  precisely the trend-day risk a condor cares about.
- **Honest read:** plausible, from a top journal, cost-modelled (their timing strategy nets 6.52% p.a.
  after costs vs 7.96% before), but the tercile split is in-sample and the parent signal fails OOS
  elsewhere. **Test it as an *additional* gate on top of GEX and require it to add something.** Per
  §3.1 the gate may already be capturing most of this.

### 3.6 The diurnal variance clock — our strike sizing uses the wrong clock

**Todorov & Zhang, "Intraday volatility patterns from short-dated options," *Journal of Econometrics*
254 Part A (March 2026).** PDF: `kellogg.northwestern.edu/faculty/todorov/htm/papers/odp.pdf`
(I extracted the empirical section directly.)

- Estimates the deterministic intraday periodic volatility component **directly from 0DTE + 1DTE SPX
  options**, Cboe DataShop best bid/ask, **2 Jan 2018 – 31 Dec 2020**, Fridays, 5-min grid 9:35–15:55.
- Finding: *"the estimated intraday volatility pattern has the familiar **U-shape** with volatility
  being higher at market open and market close relative to the middle of the trading day."*
- **Why this matters to us:** our rule sizes strikes as
  `SD = ATM IV × √(minutes left / 390) × spot` — a **uniform-variance clock**. Under a U-shape that is
  wrong in a *time-of-day-dependent* direction. At 10:30 we have already passed the high-vol open, so
  √clock **over**states the remaining SD (strikes too far out, credit left on the table). At 13:00 the
  remaining session still contains the high-vol close, so √clock **under**states it (strikes too close,
  more breaches than intended). This interacts directly with the entry-timing question in §3.2 and is
  a plausible partial explanation for why 11:00 beat 13:00 in our 494-day test.
- **Fix costs nothing:** estimate η from our existing minute bars with a standard Andersen–Bollerslev
  return-based estimator, then replace "remaining clock minutes / 390" with **"remaining integrated
  diurnal variance / full-day diurnal variance."**
- **Honest read: real, peer-reviewed, and the U-shape itself is one of the most robust facts in
  market microstructure** (Wood et al. 1985; Harris 1986; Andersen & Bollerslev 1997; Bogousslavsky,
  *JF* 2016). The only uncertainty is magnitude, which we can measure ourselves.

---

## 4. TIER 2 — worth testing, lower confidence

### 4.1 Risk-neutral skewness / smile curvature at entry as a second conditioner

The only genuinely *new* un-priced conditioning variable I can defend. Rationale:
- **Bandi, Fusari, Renò, "0DTE Option Pricing"** (SSRN 4503344, → *Journal of Finance*; SPX 2014–2023)
  derive in closed form that ultra-short-tenor skew/kurtosis are driven by **leverage (price–vol
  correlation) and vol-of-vol**. It is a pricing paper with no strategy and no costs, but it is now the
  reference model for the 0DTE surface, and it says tail pricing is a first-order, measurable thing.
- Vilkov's model zoo found **10:00 implied variance and implied skewness** among the few conditioners
  that survived, and reports "clear regime heterogeneity" across them.
- Mechanically: dealer gamma tells you the range will be compressed; smile curvature tells you what the
  market is *charging* for a large move. The condor edge is the difference between the two. Conditioning
  on only one of them throws away half the information.
- **Cost: zero.** Bakshi–Kapadia–Madan risk-neutral skew/kurt off the free Cboe delayed chain (§7.3) at
  10:30, or off the Vilkov panel historically.
- **Honest read: untested speculation with good theoretical footing.** Treat as a research idea, not a
  finding.

### 4.2 Threats to reconcile before sizing up

These are not improvements; they are ways the existing result could be partly artefact.

1. **Is our GEX signal just VRP mean-reversion?** Dim/Eraker/Vilkov **Table IA.3**: the gamma *level*
   coefficient on realised VRP is **+0.310 (t = 1.29), insignificant.** The negative relation is
   **entirely** the interaction with **lagged VRP: −5.656 (t = −3.93)**, and driven by 2020–2023.
   Translation: high gamma may not lower VRP; it may *accelerate VRP mean-reversion*.
   **Test: interact GEX z with prior-day realised VRP. If the edge dies, we have partly rediscovered
   VRP mean-reversion rather than found a standing mispricing.**
2. **Is the 0.843 / 1.139 spread too big to be gamma?** The Cboe signed-inventory study caps the
   gamma-induced effect at **+3.3pp on annualised daily vol**. Our RV/IV ratio spread is a much larger
   economic effect. It is plausible our ratio is picking up **IV** differences (options are richer on
   high-gamma days) as much as **RV** differences — which would be fine for the trade but means the
   mechanism story is wrong.
3. **Time-of-day contamination in the denominator.** *"The daily rise and fall of the VIX1D: Causes and
   solutions of its overnight bias,"* *Finance Research Letters*, Mar 2024
   (`sciencedirect.com/science/article/pii/S1544612324002162`) documents a structural intraday drift in
   VIX1D from its dynamic near/next-term weighting. VIX9D has related time-of-day issues.
   **Confirm the reference IV in the §1.1 regression is sampled at the same time of day across gamma
   buckets.** If it is not, part of the 0.843/1.139 split is an artefact.
4. **Pre- vs post-May-2022 are different instruments.** SPXW was **M/W/F only** until Tue/Thu were added
   26 Apr / 11 May 2022. Our 2016–2026 OOS spans two regimes with different flow. Vilkov tested the
   break and found economically non-trivial P&L sign shifts that were statistically weak once clustered
   by date. **Split the sample and report both halves.**
5. **VIX1D as a free, direct measurement of AWARE.** `RULES.md` §6.2 asks whether same-day IV is
   gamma-aware. VIX1D is a listed, model-free 1-day implied variance computed in **business minutes**
   (405 per RTH session, per the Cboe methodology I read), and at the 16:00–16:15 print it is
   **entirely the next session's expiry**. So prior-close VIX1D is a clean market-implied forecast of
   tomorrow's session — the exact denominator §1.1 wants. **Free from Cboe/Yahoo, history back to
   13 May 2022 (~1,050 days).** Re-run the §1.1 regression with VIX1D instead of VIX9D. Short sample,
   one vol regime, and subject to threat #3 — but it directly attacks the biggest parameter in the
   assumption matrix at zero cost.

---

## 5. Management — the honest answer is "no evidence," and our current rules are right

I looked hard for real studies here. There are almost none. Reporting this honestly, as asked.

| Question | Best evidence found | Verdict |
|---|---|---|
| **Profit target on 0DTE** | **No study exists.** tastytrade's famous 21-DTE / 50%-max-profit work is built entirely on ~45-DTE entries and is a *gamma-avoidance* rule — citing it for 0DTE inverts its own logic. Closest real backtest: Spintwig's replication of ERN's short-SPY-put program (330 trades, Feb 2018 – Jun 2020, ~5-delta, published slippage table + commissions) found **"exiting at 50% max profit lowers returns."** | **Keep no-target.** Structural argument is decisive: we trade one condor at a time on a cash-settled instrument, so there is no redeployment benefit (capital frees itself at 16:00 regardless), and the tail is already handled by the stop. A target imposes 4 legs of certain spread on ~91% of trades to buy nothing. |
| **Stop loss on 0DTE credit spreads** | **No study with a real sample.** The ubiquitous "2–2.5× credit received" convention has zero supporting data anywhere. Vilkov explicitly does not test stops. | See below — this is the one place theory has something to say. |
| **Rolling the untested side** | **Zero evidence. Not weak — none.** Every source is content-marketing, and the representative "86% success rate" claim defines success to *include trader discretion on adjustments*, making it unfalsifiable by construction. | **Folklore. Do not implement.** Structurally it pays 4 legs of spread to *increase* short delta in the direction the market is already moving — a martingale dressed as "collecting more credit." |
| **MEIC (laddered condors)** | **No independent backtest exists.** Tammy Chambless's 20.7% CAGR / 4.31% max DD is a **live-trading testimonial**, not a backtest — no trade count, win rate, cost model or OOS period. Best "backtest" found anywhere: n=133, single configuration, no controls. Every amplifier sells backtesting software or alerts. | **Unproven, and the cost arithmetic is hostile:** 6 condors/day = **24 legs of entry friction daily** on a strategy whose entire unconditional prize is ~0.001% of spot. Variance reduction is second-order; cost multiplication is first-order and certain. |

### 5.1 The one real insight, and it is about our stop

**Kaminski & Lo (2014), "When Do Stop-Loss Rules Stop Losses?", *Journal of Financial Markets*
18:234–254.** Central analytical result: a stop-loss adds expected return **if and only if** the return
process exhibits **momentum**. Under a random walk there are *no* conditions under which it adds value.
Under **mean reversion, stops subtract value.**

Compose that with Baltussen Table 7: **our gate deliberately selects positive-gamma days, which is
exactly the regime where intraday momentum is measurably absent (β = 0.82, t = 1.03, R² = 0.05%).** By
construction we are stopping out inside a random-walk / mean-reverting regime, where theory predicts
the stop costs expectancy.

**The honest counter:** a 0DTE stop is not primarily a return-enhancement device, it is tail
truncation, and a tested short strike can traverse −0.5R to −4R in minutes. Our own 494 minute-bar days
show the stop **slightly improved the mean (+6.7% → +7.3%) and halved max drawdown (−14% → −7%)** —
so empirically it currently looks free. But n=494.

**This is the cheapest high-value experiment in this document:** re-run the 853 trades with the stop
disabled (both sides held to cash settlement, loss capped at wing width) and measure the
**expectancy-versus-tail exchange rate** rather than assuming it. If PF and mean/trade rise and only
the left tail worsens, it is a *sizing* decision, not a stop decision.

---

## 6. REJECTED — do not chase these

| Claim | Why it is dead |
|---|---|
| **Charm/vanna drift on 0DTE** | **Baltussen, Terstegge, Whelan, "The Derivative Payoff Bias"** (SSRN 4562800, AFA 2025) document a genuine, tradeable charm effect — MMs hold **net charm of −$26bn** at the average 3rd-Thursday close and must buy the index overnight; 27 bp gross → **24 bp net, SR > 1.3**. But they repeat the analysis on **p.m.-settled** contracts and find **"no such weekend reversal effect… an asymmetric reversal pattern exists only around a.m. settlement."** The effect is an artefact of the illiquid overnight window before a.m. settlement. **There is no published evidence of charm-driven drift on p.m.-settled 0DTE.** My own search for charm/vanna returned nothing but vendor blogs (menthorq, gexboard, zerogex, vcalgo, skylit, tradingvolatility) — none cites a paper. |
| **0DTE pinning to the big-OI strike** | **No academic paper on 0DTE pinning exists.** The literature (Ni/Pearson/Poteshman *JFE* 2005; Golez & Jackwerth *JFE* 2012) is a.m.-settled and/or single-name, and Golez–Jackwerth find the **opposite sign (anti-pinning)** for index options. Folklore. |
| **VIX term-structure / VVIX / VIX1D gates** | **Vilkov tested VIX-regime splits directly on 0DTE structures** and reports *"statistical strength remains limited for most strategies in this static design"* — he abandoned static regime splits. This is a direct null on exactly our question, and it is consistent with our 35-DTE rejection. One nuance: Bevilacqua & Hizmeri, *"Early Birds Get the Vol"* (Dec 2025) find **10:00 ET VVIX** strongly predicts **next-day** variance-asset returns (SR 1.5–2.9, OOS Clark-West, costs) — but they explicitly report **"a flat, insignificant relationship between intraday returns (10:00–16:00) and morning VVIX."** Their own null kills the same-session use. **Do not add.** |
| **Opening-range breakout / initial-balance extension** | **Mesfin (2026), arXiv:2605.04004** — 14 signal families, 5-min MNQ, **947 days 2021–2025**, walk-forward OOS, with **planted positive controls that WERE detected (t = 5.83, t = 5.15)**, proving the method had power. **No OHLCV intraday signal passed.** Gross 0.07–1.50 pts/trade vs 2 pts friction. The market-profile "IB < 33% of ADR → expect extension" and "Crabel: narrow OR → trending day 68%" numbers appear only in content farms and I could not source the 68% to Crabel at all. |
| **Overnight gap conditioning** | No direct study. The gap is already inside Gao/Baltussen's `r_ONFH` predictor, which is **inert under positive gamma** — i.e. redundant with our gate. And **Andersen, Bollerslev, Diebold (2007), "Roughing It Up," *REStat* 89(4)**: *"almost all of the predictability in daily, weekly and monthly return volatilities comes from the non-jump component"* — a gap is mechanically a jump, and jumps are distinctly **less** persistent. A big gap is a weak predictor of a wide session. Low priority. |
| **Sector rotation, DIX-as-filter, long 0DTE premium, bullish condor tilt** | Already rejected in `RULES.md`. Nothing found changes that. |

### Vendor marketing dressed as research — named

`thetaprofits.com` (MEIC articles wrapped in Option Omega / Trade Automation Toolbox / Trade Steward
affiliate links) · `greekslab.com` (a "proven rules" page containing **zero** backtest numbers, ending
in a CTA for their backtester — and note that search engines surfaced a "32 FOMC days June 2022–April
2026" study that **does not exist on the page**) · `gexmetrix.com`, `apexvol.com`, `ipresage.com`,
`fattail.ai` / `flyonthewall.ai`, `tradealgo.com`, `daystoexpiry.com`, `quantstrategy.io`,
`optionstradingiq.com`, `volatilitybox.com` — all publish specific-sounding percentages with no sample,
period or method; several read as AI-generated SEO content · `flashalpha.com`'s "+5,400% with a stop
loss vs −100% without" is **one cell of a 96-cell grid with no multiple-testing correction** · **Cboe's
own** "Zero-Day SPX Iron Condor Strategy: A Deep Dive" contains exactly **one illustrative trade**, and
Cboe lists the product.

**GitHub, flagged:** `thunderscarf/SPX_0DTE_Options_Selling_Public` (78% win rate / 0.97 Sharpe over
537 days — **no bid/ask, no slippage, no commissions anywhere**; discard the P&L, but its VIX1D
expected-move formula is cheap to test) · `sujoypaulhome/0dte-gex-backtest` (**47 trades over two
weeks**, 7 on estimated prices, no cost model — statistically meaningless; interesting only because
both its losers breached the GEX wall) · the `FlashAlpha-lab` "awesome list" ranks their own $1,499/mo
API above open source in every section.

---

## 7. DATA — the biggest gap, and it closes this week

Verified live during this research (HTTP 200 + content-length checked by me).

### 7.1 FREE, and it is close to perfect: `vilkovgr/0dte-strategies`

`https://github.com/vilkovgr/0dte-strategies` — MIT, git-LFS, no auth needed.
**`data/data_opt.parquet` — verified 263,270,747 bytes, HTTP 200.**

- **1,369,301 rows; 1,380 genuine 0DTE days, Sept 2016 → May 2024** (2022: 218 days, 2023: 248).
  **632,245 option rows inside the 10:30–13:00 window.**
- Schema: `quote_date, quote_time, option_type, mnes, mnes_rel, mid, intrinsic, tv, **bas**, sret,
  payoff, reth, reth_und, implied_volatility, delta, gamma, theta, vega, active_underlying_price,
  trade_volume, open_interest, bid_size, ask_size`.
- **`bas` is the bid-ask spread** → bid = `mid − bas/2`, ask = `mid + bas/2`, with sizes. Prices are
  normalised by spot; multiply by `active_underlying_price`.
- `quote_time` runs on a **30-minute grid from 10:00 to 16:00** — every entry time in §3.2.
- `data/data_structures.parquet` (12 MB) already ships **pre-built iron-condor legs** at
  10:00 / 13:00 / 15:00 / 16:00.
- **Limitations, honestly:** it is an **interpolated moneyness grid, 0.98→1.02 in 0.001 steps (±2%
  only)**, not the real 5-point strike ladder; 30-minute marks, not tick; and the shipped LFS panel
  **ends 2024-05-01** despite the README claiming Jan 2026. Delta coverage at 10:30 spans ~0.01–0.99,
  so our 8–10 delta shorts and 2-delta wings sit comfortably inside — **but a 1.25-SD short on a
  genuinely high-vol day can exceed ±2% and fall off the grid.** Check coverage before trusting any
  high-VIX subsample.

### 7.2 FREE, complementary coverage: `emlama/gex-backtesting`

Tarball verified live: `http://45.55.51.49/data/gex-spx-0dte-trades.tar.gz`, **2,467,782,656 bytes
(2.30 GiB), Last-Modified 2026-03-03, no auth.** 513 daily parquet files, **2024-01-02 → 2026-02-19**,
SPXW 0DTE only, **real strikes**, columns `ticker, sip_timestamp, price, size, strike, opt_type, bid,
ask, side, trade_date, conditions` — **every trade carries the NBBO at trade time** plus
at-bid/at-ask/mid side classification. ~400–900k trades/day. Polygon-derived.

Covers exactly the window Vilkov's panel does not. **Caveats:** the repo has **no LICENSE file** (all
rights reserved), it lives on one unlicensed DigitalOcean droplet — **mirror it now** — and because you
forward-fill NBBO from trades, staleness matters: inside ±1.5% of spot the median per-strike max gap is
19–50 s, but the +1.5–2.0% call wing degrades to a 357 s median gap and beyond ±2% it falls apart.
**Usable for shorts and near wings, thin for far wings.**

### 7.3 FREE forward collection, starting tonight

Two working options, both verified:

- **Cboe's own delayed chain, no auth:** `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json`
  — 14 MB, **31,788 contracts**, 15-minute delayed, with `bid, bid_size, ask, ask_size, iv,
  open_interest, volume, delta, gamma, vega, theta, rho, theo` plus the SPX level. **The 15-minute
  delay is a feature:** poll at 10:45 / 11:15 / 13:15 ET to capture the 10:30 / 11:00 / 13:00 NBBO.
  Filter to the 0DTE root and ±5% of spot → ~450 KB/day raw, **~15 MB/year as Parquet.** A cron job and
  a directory is the whole build.
- **The Robinhood MCP tools already wired into this environment.** I used them to pull live SPXW
  bid/ask/size/IV/greeks/OI/volume during this research (§2) — that is a working, free, authenticated
  path to exactly the snapshots `RULES.md` §6.1 asks for. Subject to ToS; the Cboe CDN is the safer
  primary and this is a good cross-check.

Note also: **`get_option_historicals` returns minute bars for expired SPXW contracts back to ~Nov 2024**,
but they are **mark-price OHLC with no bid/ask** — that validates a mid, which is the half we already
model, not the spread.

### 7.4 If the free data leaves gaps: **ThetaData Options Standard, $80, one month**

`thetadata.net/pricing`. Standard = **$80/mo, tick granularity, history from 2016-01-01.** The endpoint
that matters is **`bulk_at_time/option/quote`** — *"the last NBBO quote reported by OPRA at a specified
millisecond of the day,"* returning **every contract sharing a root and expiration**, with a
`start_date`/`end_date` range and `ivl=37800000` for 10:30 ET.

**Plan: buy one month, issue ~2,400 requests (800 days × 3 timestamps), pull the complete SPXW 0DTE
NBBO chain at 10:30/11:00/13:00 back to 2016 on the real strike ladder, cancel.** At 4 concurrent
requests that is an afternoon. Retail licence is personal-use only, no redistribution.

### 7.5 Everything else, ranked

| Source | Cost | What you get | Verdict |
|---|---|---|---|
| **Databento OPRA `cbbo-1m`** | **~$0** within the **$125 signup credit** | 1-min NBBO **from 2013-04-01**; no exchange licence for T+1 historical | Excellent if you like DBN. Whole SPXW chain, 800 days ≈ 37 GB ≈ ~$1.50 at the headline "from $0.04/GB" — but that rate is not OPRA-specific, so **run their cost estimator before committing** |
| **Cboe DataShop Option *Trades*, `^SPX`** | **$275/yr; $1,100 for 2022–25** | Every SPXW trade **with NBBO at trade time** + underlying bid/ask | The authoritative arbiter, and **half the price of the quote product**. Free sample, no login: `datashop.cboe.com/download/sample/215` |
| **Cboe DataShop Option *Quotes* 1-min, `^SPX`** | $550/yr; **$2,200 caps all history 2012–25** | Gold-standard interval NBBO + size | 5–27× ThetaData for the same job. `+Calcs` (IV+greeks) $846/yr. **Gotcha:** `underlying_bid/ask` for `^SPX` needs a Cboe Global Indices Feed licence, **from $1,000/mo** |
| **QuantConnect / AlgoSeek US Index Options** | **$0 in QC Cloud research** | SPXW incl. 0DTE, minute TradeBar **+ QuoteBar, from Jan 2012** | Strong free option if you'll work inside QC notebooks |
| **OptionsDX** | **$50/yr minutely; EOD free** | Real strikes, both sides, `C_BID/C_ASK/P_BID/P_ASK`, sizes, greeks | Ideal schema, **but 2010–2023 only — dead-ends before the daily-expiry era matures.** 2022+2023 minutely = $100 |
| **Polygon.io → Massive** | $199/mo Advanced for quotes | 5+ yr, NBBO, flat files | 2.5× ThetaData for the same job. Lower tiers have **no NBBO** |
| **ORATS** | $199/mo or **$1,500 one-time** | 1-min incl. bid/ask from Aug 2020 | SPX index coverage unconfirmed |
| **MarketData.app** | you already have credits | **End-of-day chains only** | **Cannot answer an intraday question** |
| **Alpaca** | $99/mo for OPRA | Options only **since Feb 2024**, **no index options** | Out for options. *But:* the free tier gives **SIP** stock bars for any window ≥15 min old — a cheap way to extend our 494-day minute-bar sample |
| **Tradier** | $10/mo | `timesales` caps at **20 days**, **no bid/ask** | Out for history; fine as a forward collector |
| **Schwab** | free w/ account | Current chains w/ bid/ask + greeks; **no historical snapshots** | Good forward collector |
| **OptionMetrics IvyDB Intraday** | institutional / WRDS | Snapshots at **10:00, 14:00, 15:45** only, from 2018 | Wrong timestamps, inaccessible |
| Hugging Face · Kaggle · DoltHub · FirstRate · Intrinio · Cboe free stats | — | Nothing intraday for SPX chains. Cboe's `spxpc.csv` hasn't updated since **2019-10-04** | Dead ends, confirmed |

Not reached: dxFeed, Barchart OnDemand, Nasdaq Data Link, CME DataMine, IBKR, Tastytrade.

---

## 8. What I'd actually do, in order

**This week — $0, and it settles almost everything**

1. **Pull `data_opt.parquet` and mirror the `emlama` tarball.** (§7.1, §7.2) Together: real SPXW bid/ask
   for 2016→2026 with only a small gap.
2. **Re-run our exact rule on real quotes** — GEX gate, 1.25SD/1SD, 10:30–13:00, −0.5R stop — under
   **Vilkov's three-layer cost ladder** (mid / +half-spread per leg / +0.5bp). This is the
   `RULES.md` §6.1 validation, and it simultaneously tests us against the strongest published
   counter-result. My single-snapshot estimate says expect roughly **+1.2% of risk per trade, not
   +3.7%**, and expect the gate to be load-bearing (5.77% of width beats the 4.2% high-gamma breakeven
   but loses to the 9.6% low-gamma one).
3. **Settle the entry-timing question** on the same panel: 10:30 / 11:00 / 12:00 / 12:30 / 13:00 /
   13:30 / 14:00, net of half-spread. Dim-Eraker-Vilkov says later is much better; Vilkov says it
   doesn't matter; our 494 days say 11:00. All three can't be right and the data is free. (§3.2)
4. **Start the Cboe CDN cron tonight** so we accumulate our own ground truth from here. (§7.3)

**Next — cheap, high-information**

5. **Fix `strike_iv`.** Replace the linear tilt with the quadratic in §2.3, calibrated on ≥60 days of
   real chains. Until then, treat every modelled credit as **~1.6× too rich** and every headline
   expectancy as **~3× too high**.
6. **Run the no-stop counterfactual** on the 853 trades. Kaminski-Lo × Baltussen predicts our −0.5R
   stop is expectancy-negative in the exact regime the gate selects. Measure the exchange rate. (§5.1)
7. **Test tighter shorts — 0.9 / 1.0 / 1.1 SD** — on real quotes, judging on the **tail**, not the mean.
   Three independent lines of evidence point inward; the counter-argument is that `short_sd` is a
   leverage dial, which is exactly the trap we called out in `RULES.md` §3.7. (§3.3)
8. **Calendar edits:** add **NFP**, **elections/midterms**, **FOMC-minutes days**, and (on priors) the
   session after **NVDA earnings**. Do **not** add PPI, Treasury auctions, month-end, or Jackson Hole —
   the Fed's own daily-expiry-option study says markets don't price them. (§3.4)
9. **Switch the §1.1 denominator to VIX1D** (free, from 2022-05-13) to measure AWARE directly, and
   **check the §1.1 reference IV is sampled at a consistent time of day** across gamma buckets. (§4.2)
10. **Replace the clock-time strike sizing with a diurnal-variance clock**, estimated from our own
    minute bars. (§3.6)

**Then — real but lower confidence**

11. Test a **first-30-minute realised-vol** stand-down at 10:00, and require it to add something over
    the GEX gate alone. (§3.5)
12. Interact **GEX z with prior-day realised VRP**; split the sample **pre/post 11 May 2022**. (§4.2)
13. Test **risk-neutral skewness/curvature at 10:30** as a second conditioner. (§4.1)

**Do not spend time on:** charm/vanna on p.m.-settled 0DTE, 0DTE pinning, VIX/VVIX term-structure
gates, opening-range/initial-balance classifiers, gap-size stand-downs, rolling the untested side,
profit targets, or MEIC.

---

## 9. The one-paragraph summary

The mechanism is real and has better academic support than we knew — Baltussen (*JFE* 2021) shows
intraday momentum exists **only** when dealers are short gamma (R² 3.58% vs 0.05%), and Cboe's own
signed-inventory study confirms the vol-dampening with actual market-maker positions. **The gate is
right, and it is already our trend-day filter.** But the P&L is softer than we thought: a real chain
says our option model overstates the condor credit by ~1.6× (the linear skew prices the call wing at
zero when the market pays for it), so honest expectancy is **~1.2% of risk per trade, not 3.7%** — and
a published 9.5-year study on real Cboe SPXW quotes finds unconditional condors at **−0.20 net Sharpe**.
Costs are *not* the problem; the pricing model is. The good news is that a free, MIT-licensed academic
data panel with **1,380 real 0DTE days of bid/ask at 30-minute marks** makes every one of these
questions answerable this week without buying anything.
