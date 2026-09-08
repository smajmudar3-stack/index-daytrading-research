# Research reports

26 sweeps of academic papers, GitHub repos, and vendor documentation. **These are
inputs, not conclusions.** The conclusions that survived testing are in
[`../02_findings/`](../02_findings/), and the verdict on any individual claim is in
[`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md). Most of what is proposed in
these documents did not survive.

**The verdict column is the point of this file.** Each line is taken from the
document's own conclusion, so you can tell which sweeps produced something that is
still in force without opening 26 reports. Verdicts written 2026-08-24.

> ⚠️ **This file is partly hand-written.** `05_studies/scripts/build_indexes.py`
> generates the "what it does" column from each document's own opening line. The
> **verdict** column is not generated and cannot be. If you re-run that script,
> merge the verdicts back in rather than letting it overwrite them.

**Tags**

| tag | meaning |
|---|---|
| 🟢 **FEEDS A LIVE FINDING** | something in here is still in force |
| 🔧 **ADOPTED** | its output is built into the live system |
| 🔴 **NULL** | it closed a line of inquiry. This is the most common outcome and the most valuable |
| 📘 **REFERENCE** | operational or cost facts, not an edge claim |

---

## The 0DTE and premium-selling core

| file | verdict |
|---|---|
| `RESEARCH_0DTE_EDGE.md` | 🟢 **This is the sweep that killed the +3.7% condor.** Measuring a real SPXW chain showed the repo's option pricer overstates the condor credit by **~1.6×** because its linear skew is the wrong shape, putting honest expectancy at **~1.2% of risk per trade, not 3.7%**. Costs were never the problem; the pricing model was. It also located the free academic replication package (1,380 real 0DTE days of SPXW bid/ask) that made the full re-test possible. |
| `RESEARCH_CONDOR_BUTTERFLY.md` | 🔴 **NULL, and it independently replicates our own.** Separate code on the same file reproduces the negative condor and butterfly results. On real quotes the best weekly-condor cell anywhere is **+0.15%/trade at t = +0.27** on non-overlapping entries, and allowing overlap is what manufactured the t-statistic. All 36 0DTE butterfly cells are negative. Cboe's own **CNDR index: −1.28%/yr for 16.6 years**; **BFLY: −5.32%/yr**. The condor question is closed. |
| `RESEARCH_STRADDLE_STRANGLE.md` | 🔴 **NULL. No structure gets a yes.** The closest is the delta-hedged short ATM straddle at **+4.31% of premium, t = +1.53**, which still loses to owning SPY on Sharpe (0.30 vs 0.64) and decays monotonically across sub-periods. The naked short strangle is the account-killer: **worst month −2523% of credit**, and three of 213 months destroyed half of all profit ever earned. |
| `RESEARCH_EXOTIC_STRUCTURES.md` | 🔴 **NULL, six of seven.** ZEBRA, box, twisted sister, jade lizard, broken-wing butterfly, gamma scalping, christmas tree. Only the **ZEBRA** survives, and only as an expression tool for a directional signal this repo does not have. It is statistically indistinguishable from a 0.80-delta call (**−$2.12/trade, t = −0.31**) and **shares beat both** (−$87/trade, t = −3.95). |
| `RESEARCH_BLOWUPS.md` | 📘 **REFERENCE, and the sizing input nothing else supplies.** Size on the **loss-to-credit multiple, not the move**: a −4.10% day cost a 1-day strangle **19× credit**; March 2020 reached **35.5×**. **The VIX level is not a risk filter** (the worst 21-day inversion in 36 years started at VIX 13.68, the 23rd percentile). Defined risk with too thin a credit is barely safer than naked. |

## Direction, and why there is none

| file | verdict |
|---|---|
| `RESEARCH_DIRECTION.md` | 🟢 **Confirms the intraday null from the literature and supplies the mechanism.** Measured lead times are **≤10 ms** on every axis (ES→SPY 7 ms, VIX→SPX futures 3 ms), so at a 5-to-30-minute horizon the effect is not small, it is absent. Four separate papers self-report failure after costs. The number to carry: **a long ATM 0DTE option needs a 58.2% hit rate over 90 minutes just to break even**, and the best published intraday index signal ever managed 54.4%. Also settles the framing: **no peer-reviewed paper claims GEX predicts the sign** of an index return, only the magnitude. |
| `RESEARCH_OPTIONS_EXPRESSION.md` | 🟢 **The signal is the problem, not the structure.** SPY rises over 43 days **67.1%** of the time, so a 58-60% directional signal is worse than always guessing up. Break-even accuracy falls monotonically as delta rises: **56.0% in shares** against **79.0% on a 0.16-delta call**. If you ever do have a sign-only signal, express it in shares. |
| `RESEARCH_MOVE_PREDICTION.md` | 🔴 **NULL. Nothing beats implied volatility** as a forecast of single-stock move magnitude at 1-6 weeks: squeeze, IV rank, HV−IV, short interest, unusual flow, attention, vol-of-vol are each already priced, disproven or folklore. Far-OTM single-stock calls are **−45.6% at the ask (n = 123,107, t = −7.13)** and go to **+5.6% (t = +0.98)**, i.e. indistinguishable from zero, once filtered to ≤20% spread. **The entire negative expectancy is the bid-ask spread.** |

## The tail / black swan line

| file | verdict |
|---|---|
| `RESEARCH_BLACKSWAN.md` | 🔴 **NULL, and "not a close call" in its own words.** Heavily traded deep-OTM calls average **−116 bp per day** (Duarte-Jones-Wang, *JF* 2024), and Boyer-Vorkink measure **10-50% per week** between low- and high-skewness option portfolios at midpoint. **Seven conditioning candidates were tested and not one clears t ≥ 4 with costs.** The mechanism (probability weighting) is a demand story, so it will not decay. Budget it as consumption, not as a sleeve. |
| `RESEARCH_TALEB.md` | 🔴 **NULL, and it removes the strategy's best-known authority.** Taleb's work does not support buying scattered cheap far-OTM options; it contains the specific argument against it. **His own tail trade is entered for a net credit** (OTM bought, financed by selling ATM), which inverts the cash flow of the trade that claims to copy it. **Empirica, his and Spitznagel's own fund running exactly this, closed in 2004** after a quiet market bled it out. |

## Swing, macro and cross-sectional

| file | verdict |
|---|---|
| `RESEARCH_SWING_ACADEMIC.md` | 🟢 **Produced one of the three surviving signals.** VIX backwardation inside an uptrend (VIX > VIX3M and MA50 > MA200) is the top-ranked candidate: **+2.37% mean per 21-day hold, +1.51 pp over the base rate, positive in all three splits, stronger out of sample than in Nagel's original**. Its structural finding is the more valuable half: four independent literatures decompose the same way, and **volatility is forecastable while expected returns are not, so build sizing rules rather than direction rules.** |
| `RESEARCH_MACRO_SWING.md` | 🔴 **NULL for the continuous-macro family.** Every published validation of a macro surprise index against asset prices is **contemporaneous, not predictive**. The macro effects that survive are anchored to a scheduled event and live in a ~16-hour window, not a 5-to-21-day one. The one strong monetary-policy cross-sectional premium is constructed to be orthogonal to sector, so it cannot be expressed in sector ETFs at all. |
| `RESEARCH_SWING_REPOS.md` | 🔴 **NULL, from the other side.** The two most rigorously built repos in the space **both publish a null on sector momentum rotation**, the strategy most people want to trade. One reports momentum net Sharpe 0.53 against equal-weight 0.56 and SPY 0.50, alpha **−0.20%/yr, t = −0.15**. What survives are regime and defence overlays, not return-seeking rotation. |
| `RESEARCH_SWING_REPOS_MACRO.md` | 🔴 **NULL, and the failure has a shape.** No public repo has a macro-conditioned swing strategy that survives scrutiny and shows an edge. **The three repos that handle macro vintages correctly all report a null; every repo reporting a large edge has a specific, locatable bug** (2024 mega-caps run from 2009; same-day close in both signal and return). Convergent corroboration of our own null from three independent codebases. |
| `RESEARCH_PAPERS_SWEEP.md` | 🔴 **NULL for the family it was commissioned to find.** The option-implied cross-sectional predictors (IV spread, implied skew, O/S ratio) have just been dismantled: **roughly two-thirds of the predictability is the stock borrow fee** leaking into implied vols computed with the fee set to zero, and **5 of 9 are statistically dead in 2015-2024**. The two that are alive gross need a securities-lending desk. Two term-structure candidates survive and remain untested. |
| `RESEARCH_SPINOFFS.md` | 🔴 **NULL, and the most decisively dead thing here.** In-sample **t = 2.43** against a t ≥ 4 bar, **107% post-publication decay**, **rank 206 of 207** predictors for 2015-2024, and a **19.7-year live ETF with exactly zero alpha (t = −0.00)**. The headline mechanism, forced index-fund selling, has been measured collapsing from 7.4% to under 1%. Its own recommendation: close this line of inquiry. |
| `RESEARCH_SPINOFF_REPOS.md` | 🔴 **NULL on the edge, solved on the data.** Built a free, scriptable, survivorship-bias-free-by-construction registry of **741 US SpinCo registrations, 1994-2026** from EDGAR Form 10-12B, which is 3-7× the sample of every published attempt. Then: **two independent pre-registered studies already killed spinoff drift**, one finding the small-cap tail materially negative. The problem is not account size, it is that the effect is not there. |

## Costs, fees and execution

| file | verdict |
|---|---|
| `RESEARCH_COSTS.md` | 📘 **REFERENCE, and it corrects a widely-cited number.** SPY friction at 20-60 DTE is **~1% of a vertical's credit**, and the academic 3-5% estimates describe pre-2007 SPX and present-day single stocks, not SPY. Single stocks run **6-18× worse** (median 4.51% ATM, up to 13.66%). Sector SPDRs are not SPY substitutes (XLK 13.89%). **Never leg a spread, and assume you fill at the touch, not the mid.** |
| `RESEARCH_FEES.md` | 📘 **REFERENCE, and it settles what to model.** A 1-lot SPY iron condor opened and closed costs about **$0.36 all-in** in fees, which is 0.45-0.90% of a typical credit. Crossing the eight legs costs **$8-$16**, i.e. 20-45× the entire regulatory stack. **Model slippage, not fees**, if you only have budget for one. |
| `RESEARCH_MANAGEMENT.md` | 🔴 **NULL for the folklore, with one structural keeper.** Profit target at 50% and at 25%, rolling, and the 2× credit stop are **folklore or unevidenced** as return rules; hold-to-expiry is the evidenced default; close-at-21-DTE is real but as a **risk** rule only. Every rule in circulation traces to a publisher paid by the brokerage it recommends. The keeper: **carry drift flips sign between short and long premium, so management logic must flip too**. A time stop is defensible on the long side and a profit target is not. |
| `RESEARCH_RUIN_SIZING.md` | 🟢 **Sizing constraint that still binds.** Full Kelly on the live SPY spread is **9.6% and negative under mildly worse assumptions**, while the smallest position a $3,000 account can take is **15.5%**. There is no width that is simultaneously survivable and profitable at this account size. **Win rate is not evidence** (a 90%-win/1:9 condor has exactly zero edge by construction), and proving the edge to t = 2 would need **6,182 trades, about 119 years**. |

## Repo and vendor sweeps

| file | verdict |
|---|---|
| `RESEARCH_BOTS.md` | 🔧 **ADOPTED. The one sweep whose output is running.** The live risk layer is lifted from it: the multi-gate entry stack, per-side stops that do not force-close an untouched spread, settlement-aware exits, the two-layer `DRY_RUN` plus per-strategy live switch, the bear-advocate / risk-officer committee, and the pre-registered paper-to-live graduation bar. It also supplies the honesty guardrail this repo lives by: **use dealer gamma strictly as a risk and volatility regime gate, never as a return predictor.** |
| `RESEARCH_GITHUB_SWEEP.md` | 🟢 **Closed the condor question from outside.** Found `vilkovgr/0dte-strategies` (Vilkov, Frankfurt School, SSRN 4641356) on real Cboe 30-minute SPXW NBBO bars 2016-09 to 2026-01, reporting **iron butterfly/condor at Sharpe −0.96** net: two researchers, two datasets, same answer. Also **triple-confirmed the GEX/DIX null** and opened the free DoltHub single-stock chain source. And: **every profitable options result in the sweep traces to a specific broken line**, the best being a repo that marks spreads with a function taking no time-to-expiry argument. |
| `RESEARCH_GITHUB_RETURNS.md` | 🔴 **NULL, at scale.** 1,233 distinct repos found, ~90 audited at source level, and **not one pairs a large positive return claim with a methodology that survives reading the code**. The two claims that do survive are Sharpe 0.38-0.72 and arguably still nulls. The best natural experiment in the sweep: the same strategy, same months, **mid-marked self-simulation +431% against real broker fills −3.42%/trade**. The spread flipped the sign. |
| `RESEARCH_REALCHAIN_REPOS.md` | 🔴 **NULL on the engines, and it caught two live data defects.** The most-recommended backtest engine's `iron_condor()` **silently ignores its own short-delta and wing-width arguments**, so every caller gets a random four-leg structure, and it has **no options margin model at all** (credit strategies sized by credit received, so ~15-20× over-levered by default). On our own data: the EOD chain **cannot test 0DTE intraday entries** and its `mark` column is corrupt (deviations up to $100,000 from mid). Use bid/ask, never `mark`. |
| `RESEARCH_UW_API.md` | 📘 **REFERENCE, and directly actionable.** **91 of 112 probed endpoints work on the current key; 6 are used.** The daily quota is 30,000 requests against roughly 130 used, so the 45-second cache is unnecessary and usage could widen ~200×. **`flow_alerts()` is on a deprecated endpoint** that will be removed, the mandatory `UW-CLIENT-API-ID` header is missing from our client, and WebSocket returns HTTP 401 on this plan. |

---

**26 files.**
