# Macro & Cross-Asset Inputs for Swing-Horizon (5–21d) Equity/Sector Forecasts — Literature Review

**Date:** 2026-08-14
**Question asked:** my naive macro-signal grid (4 rate/credit signals × 18 sector ETFs × 3 horizons ×
3 periods) produced 36/216 cells positive in all three splits but **zero** clearing t = 3.24. Does the
literature have a *better specification* than the one I tested?
**Companion docs:** `RESEARCH_SWING_ACADEMIC.md` (swing-horizon edge survey),
`RESEARCH_PAPERS_SWEEP.md` (option-implied predictors), `FINDINGS.md` (intraday null),
`RESEARCH_DIRECTION.md`, `backtest-methodology-traps` memory.

---

## 0. VERDICT FIRST

**The literature does not contain a better specification of the thing you tested.** It contains
something narrower and more useful: a small number of *event-anchored* macro effects that survive,
and a clear explanation of why the *continuous* macro-signal family (level, change, or surprise of a
macro variable → next-week sector return) has no published support.

Three sentences that summarise the whole review:

1. **Every published validation of a macro *surprise* index against asset prices is
   contemporaneous, not predictive.** Scotti (JME 2016) regresses *same-day* FX returns on the
   *same-day* change in the surprise index. Caruso (IJF 2019) does the same. Nobody has published
   "CESI at t predicts equity returns at t+5". Your rate-beta result (KRE +1.087, XLRE −0.239) is
   structurally the *same kind of fact* as everything in the surprise-index literature: real
   sensitivity, no established forecast.
2. **The macro effects that do survive are all anchored to a scheduled event, and they are
   overnight, not multi-day.** The pre-announcement drift (Hu, Pan, Wang & Zhu, JFE 2021) is the
   single best-verified macro-timing effect in the literature and it is stable across subperiods —
   but it lives in a ~16-hour window, not a 5–21-day one.
3. **The one strong monetary-policy cross-sectional premium (Ozdagli & Velikov, JFE 2020) is
   constructed to be orthogonal to sector.** They put industry fixed effects *and* industry ×
   policy-surprise interactions in the estimation and then deliberately exclude industry from their
   index. So the best rate-conditioned cross-sectional result in finance is, by construction, not
   expressible in sector ETFs. That is a direct, decisive answer to your topic 4.

**Against your OSAP base rate** (post-pub mean = −0.122 + 0.61 × in-sample mean; 14.3% of published
predictors clear t>2 in 2015–2024), only **one** candidate below has the two properties that predict
survival: a *risk-premium* mechanism rather than a mispricing one, and documented stability in the
most recent subperiod the authors could measure. That is candidate #1.

**One candidate is actively falsified for your intended use:** the S&P 500 index-inclusion trade
(#2). Do not put money on the RDDT addition on the basis of "3× daily volume of forced buying."
The flow is real and has *grown*; the price effect went to zero anyway. That is the entire point of
Greenwood & Sammon.

---

## 0b. Verification status — read this before quoting any number

I lost web-search access partway through this review (session budget) and worked from the Crossref,
OpenAlex and Unpaywall APIs plus direct PDF retrieval. Every number below is tagged:

| Tag | Meaning |
|---|---|
| **[P]** | Read from the primary PDF/full text myself. Quote freely. |
| **[A]** | Read from the publisher's or repository's own abstract record. Directionally safe, no table-level detail. |
| **[S]** | Secondary — a number reported *about* this paper inside another paper I did read. Reliable but one step removed. |
| **[U]** | **Unverified.** I could not obtain the source. Treat as a lead, not a fact. |

---

## 1. ECONOMIC SURPRISE INDICES (CESI and academic equivalents)

### 1.1 What the literature actually establishes

**Scotti (2016), "Surprise and uncertainty indexes: Real-time aggregation of real-activity macro
surprises," *Journal of Monetary Economics* 82, 1–19.** DOI `10.1016/j.jmoneco.2016.06.002`.
Working paper: Fed IFDP 1093 (Nov 2013), retrieved and read in full. **[P]**

Construction (this is the codeable definition, and it is the academic sibling of Citi's CESI):

> "The indexes, on a given day, are weighted averages of the surprises or squared surprises from a
> set of macro releases, where the weights depend on the contribution of the associated real
> activity indicator to a business condition index à la Aruoba, Diebold, and Scotti (2009)."

Surprise for release *i* = (actual − Bloomberg median consensus) / (std dev of that series'
historical surprises). Weight = the release's loading in an ADS-style dynamic factor model. CESI
differs only in that it uses a rolling 3-month decaying sum with market-impact weights rather than
factor-model weights.

Critically, Scotti is explicit about *why* she uses Bloomberg consensus rather than a statistically
efficient forecast, and it is a sentence worth internalising:

> "financial markets react neither to my own private forecast nor yours; financial markets react to
> Bloomberg forecasts, which are public and everyone can see."

**And here is the finding.** Her asset-price validation (Table 5, July 2003 – Sept 2012, ~556
release days) is:

```
dlog(FX_t) = α + β · d(SurpriseIndex_t) + ε_t
```

*Same t on both sides.* Results: EUR/USD β = 0.362\*\*\*, R² = 0.022; GBP/USD β = 0.263\*\*\*, R² =
0.014; JPY/USD β = 0.418\*\*\*, R² = 0.031; CAD/USD β = −0.096, insignificant. **[P]**

There is no lagged specification anywhere in the paper. There is no equity test at all. The paper's
own framing of the contribution is that the index "preserves the properties of the underlying series
in affecting asset prices, with the advantage of being a parsimonious summary measure" — i.e. it is
offered as a *control variable*, not a signal.

**Caruso (2019), "Macroeconomic news and market reaction: Surprise indexes meet nowcasting,"
*International Journal of Forecasting* 35(4), 1725–1734.** DOI `10.1016/j.ijforecast.2018.12.005`.
Abstract read in full. **[A]** He builds a "Nowcasting Surprise Index" from nowcast-model forecast
errors and shows it "resembles the surprise indexes proposed in the recent literature or constructed
by practitioners." Conclusion: "recent cumulated news in macroeconomic data … accounts for a
non-negligible part of asset price behaviour." *Accounts for*, not *forecasts*. Contemporaneous again.

**Beber, Brandt & Luisi (2015), "Distilling the macroeconomic news flow," *JFE* 117(3), 489–507.**
DOI `10.1016/j.jfineco.2015.05.005`; NBER w19650 read in full. **[P]** Their claim is about
*nowcast accuracy*, not returns: "our procedure provides more timely and accurate forecasts of
future changes in economic conditions than other real-time forecasting approaches." I grepped the
NBER version for `Sharpe | trading strateg | asset alloc | transaction cost` and got **zero hits**.
Any return-predictability claim attributed to this paper is not in the working paper.

### 1.2 Why the surprise-index specification is *also* dangerous, not just unsupported

Two mechanical traps, both of which are in your `backtest-methodology-traps` memory:

- **Whole-sample standardisation = look-ahead.** Every surprise index divides each release's
  surprise by the standard deviation of that release's surprises. If you compute that std dev over
  the full sample, you have leaked. CESI additionally weights by *estimated market impact*,
  typically fitted over the whole history. A CESI backtest that uses the published index series is
  using a signal whose weights were fitted with your test period in it.
- **CESI is a decaying 3-month sum, so it is ~0.95 autocorrelated and mechanically mean-reverting.**
  A "high CESI predicts negative forward returns" result is the near-inevitable artefact of
  regressing a forward return on a bounded, mean-reverting series that is contemporaneously
  correlated with the *past* return. This is the same structure that generates spurious
  "overbought" results.

### 1.3 The one honest connection to your own result

Your desk notes contain surprises like "UMich 51.0 vs 54.5 expected." Note what Hu, Pan, Wang & Zhu
(2021) find for exactly that release — see §2, Table 1: the Consumer Sentiment Index (CSI) has a
pre-announcement return of **−4.03 bps, t = −0.88**, the *worst* of the eleven macro releases they
test. UMich is the single least informative announcement in the set. **[P]**

**Verdict on topic 1: NO. There is no published predictive specification. Downgrade to an
attribution/risk-sizing input, not a forecast input.**

---

## 2. MACRO ANNOUNCEMENT DRIFT / PRE-ANNOUNCEMENT DRIFT — **the one live candidate**

### 2.1 Lucca & Moench: the original, and its documented death

**Lucca & Moench (2015), "The Pre-FOMC Announcement Drift," *Journal of Finance* 70(1), 329–371.**
DOI `10.1111/jofi.12196`. Publisher PDF blocked; numbers verified from two independent papers that
replicate it. Effect: **+49 bps** cumulative S&P 500 excess return in the 24 hours before scheduled
FOMC announcements, Sept 1994 – March 2011, 131 meetings. Mean 0.492%, SE 0.107 → **t = 4.60**. **[S]**

**Gilbert, Kurov & Wolfe (2020), "The disappearing pre-FOMC announcement drift," *Finance Research
Letters* 40, 101781.** DOI `10.1016/j.frl.2020.101781`. Open access via PMC 7525326; read in full.
**[P]** The decay table:

| Period | Meetings | Mean pre-FOMC return | SE | implied t |
|---|---|---|---|---|
| Sept 1994 – Mar 2011 (Lucca–Moench sample) | 131 | **+0.492%** | 0.107 | **4.60** |
| Apr 2011 – Dec 2015 | 20 | **+0.445%** | 0.133 | 3.35 |
| Jan 2016 – Dec 2019 | 20 | **+0.092%** | 0.069 | **1.33** |

Wilcoxon rank-sum rejects equal central tendency between the two post-LM subperiods at the 1% level.
Their explanation is *not* arbitrage: it is that impact uncertainty fell. Average VIX dropped from
17.7 before the Dec-2015 ZLB liftoff to 14.7 after (difference significant at 1%), and the post-ZLB
dummy goes insignificant once VIX is included as a regressor.

This is a textbook post-publication decay case for your OSAP prior: published in JF in 2015, dead
from 2016. **Do not trade pre-FOMC.**

### 2.2 The part that did NOT die — Hu, Pan, Wang & Zhu

**Hu, Pan, Wang & Zhu (2021), "Premium for heightened uncertainty: Explaining pre-announcement
market returns," *JFE* 143(2), 909–937.** DOI `10.1016/j.jfineco.2021.09.015`. NBER w25817
(May 2019, rev. March 2021) retrieved and read in full. **[P]**

Their finding: the pre-FOMC drift is *not special*. The same overnight premium exists before NFP,
ISM and GDP — and unlike FOMC, it has **not** decayed.

**Signal definition (exactly codeable):** long S&P 500 futures from the previous trading day's 4:00 pm
close to 5 minutes before the scheduled release (8:25 am ET for NFP and GDP, 9:55 am ET for ISM);
flat otherwise.

**Table 1, Sept 1994 – May 2018, S&P 500 futures, returns in bps:** **[P]**

| Release | Time ET | Pre-ann. mean | t | σ | N | Post-ann. mean | t |
|---|---|---|---|---|---|---|---|
| **FOMC** | 14:00 | **27.14** | **5.95** | 62.9 | 190 | 1.68 | 0.23 |
| **NFP** | 08:30 | **10.10** | **3.63** | 43.4 | 243 | 1.51 | 0.21 |
| **ISM** | 10:00 | **9.14** | **2.10** | 72.5 | 277 | 11.39 | 1.85 |
| **GDP** | 08:30 | **7.46** | **2.08** | 54.7 | 233 | −5.76 | −0.93 |
| IP | 09:15 | 5.23 | 1.19 | 68.0 | 240 | 1.97 | 0.35 |
| Personal income | 08:30 | 3.50 | 0.94 | 58.3 | 244 | 2.26 | 0.35 |
| Housing starts | 08:30 | 2.46 | 0.69 | 53.9 | 230 | 1.31 | 0.20 |
| Initial claims | 08:30 | 1.56 | 0.95 | 53.8 | 1073 | 0.94 | 0.29 |
| PPI | 08:30 | −0.58 | −0.17 | 52.3 | 241 | 4.72 | 0.64 |
| CPI | 08:30 | −2.14 | −0.69 | 47.1 | 232 | −2.31 | −0.32 |
| **UMich CSI** | 09:55–10:00 | **−4.03** | **−0.88** | 68.7 | 226 | −1.57 | −0.30 |
| *Non-announcement close→open benchmark* | | **0.69** | 0.78 | 62.1 | 4976 | | |
| *All days close→open benchmark* | | 1.99 | 2.45 | 62.6 | 5965 | | |

Robustness to outliers: trimming the top and bottom 1% leaves NFP at 9.80, ISM at **10.31**, GDP at
6.09 bps. **[P]**

**Subperiod stability — Table 2, "All 4 Macro" (bps per event):** **[P]**

| Subperiod | Pre-ann. return | t |
|---|---|---|
| 1994–2000 | 16.00 | 4.22 |
| 2001–2010 | 15.22 | 4.54 |
| 2011–2018 | **7.63** | **2.62** |

And the split that matters most for you, in the authors' own words:

> "Separating the macro announcements into FOMC and non-FOMC (NFP, ISM, and GDP), the sub-period
> performance for FOMC remains large and significant pre-2011 and becomes insignificant during
> 2012–2018. By contrast, the performance of the non-FOMC macro announcements remains stable and
> significant across all three subperiods. In particular, during the last subperiod of 2012–2018,
> the pre-announcement return is on average **6.98 basis points and statistically significant** for
> the non-FOMC macro announcements, compared with the statistically insignificant 3.96 basis points
> for the FOMC announcements."

**Annualised:** pooling all four, 5.66%/yr realised over 44 announcement windows/yr, vs a 9.10%/yr
total market return realised over 252 days. Ex-FOMC: **3.41%/yr over ~36 windows/yr.** Post-2011,
FOMC's contribution collapses to 0.32%/yr while NFP+ISM+GDP hold at **2.51%/yr**. During 2000–2011,
when the market returned 1.97%/yr, the pre-announcement return was 6.54%/yr. **[P]**

**Mechanism (this is why I rank it #1):** it is a *compensated risk*, not a mispricing. Their model
prices the uncertainty about the *magnitude of the impending news' market impact*. The testable
signature is that VIX rises into the announcement and then falls **before** the release — the
premium is earned as impact uncertainty resolves pre-announcement. They verify this: post-announcement
returns are ~0 (FOMC 1.68 bps, t = 0.23) despite variance being ~3× larger (0.40 vs 1.02 bps in their
variance units). **A risk premium does not arbitrage away on publication.** That is the single best
argument any candidate in this document has against your −12 bps/month post-publication prior.

**Leakage flags I want on the record:**
- Their high-vs-low impact-uncertainty split yields **+68.23 bps** for the high group vs **−6.96 bps**
  for the low group. That is an *ex-post sort on realised ΔVIX*. Do not trade the conditional version.
  The unconditional 7–10 bps is the tradeable number.
- Their sample ends May 2018 and the WP circulated May 2019. There is **no post-publication evidence**
  yet. You have 2019–2026 to test it out of sample yourself — see Test 1.

### 2.3 Savor & Wilson

**Savor & Wilson (2013), "How much do investors care about macroeconomic risk? Evidence from
scheduled economic announcements," *JFQA* 48(2), 343–375**, DOI `10.1017/s002210901300015x`, and
**(2014), "Asset pricing: A tale of two days," *JFE* 113(2), 171–201**, DOI
`10.1016/j.jfineco.2014.04.005`. Both paywalled; I could not obtain either. **[U] for all
numbers.** What I can verify is only how Hu et al. characterise them: "Savor and Wilson (2013)
document significant positive stock market returns on the FOMC announcements … Interestingly, post
announcement, market returns are on average small and insignificant, despite the high variances it
causes." **[S]** The widely-cited "≈11.4 bps on announcement days vs ≈1.1 bps otherwise, 1958–2009"
figure is **[U]** — I did not verify it and you should not quote it.

Relevance to you: Savor–Wilson is an *announcement-day* (full-day) effect. Hu et al. show the return
is concentrated *pre*-release and that the post-release return is ~0. So Savor–Wilson is largely
subsumed. Use Hu et al.'s decomposition, not the day-level version.

**Verdict on topic 2: the FOMC version is DEAD (published 2015, gone from 2016). The NFP/ISM/GDP
version is ALIVE through 2018, has a risk-premium mechanism, and is testable on data you hold.
This is candidate #1.**

---

## 3. CROSS-ASSET LEAD-LAG AT THE WEEKLY HORIZON

You established there is no exploitable intraday lead-lag (lead times 3–10 ms). The weekly question
has a different answer, but not a strong one.

### 3.1 Cross-asset time-series momentum — the best-specified version

**Pitkäjärvi, Suominen & Vaittinen (2020), "Cross-asset signals and time series momentum," *JFE*
136(1), 63–85.** DOI `10.1016/j.jfineco.2019.02.011`. Publisher and repository copies both 403'd on
me; I read the author's own summary in his Aalto doctoral thesis (Aalto DOCTORAL THESES 53/2023,
retrieved in full). **[A]**

> "Using bond and equity data from twenty countries, we show that not only do past bond returns
> predict future bond returns, and past equity returns predict future equity returns—thus confirming
> the findings of Moskowitz, Ooi, and Pedersen (2012)—but **past bond returns also predict future
> equity returns, while past equity returns also predict future bond returns.** Moreover, we show
> that by using this cross-asset time series predictability, we can construct cross-asset time series
> momentum portfolios that outperform the standard time series momentum portfolios in our data set."

Attributed mechanism: **slow-moving capital in global bond and equity markets.**

**Effect sizes, t-stats and net-of-cost figures: [U].** I could not obtain the tables. Do not quote
a Sharpe for this.

**The specification gap between this and what you tested is large, and it matters.** You tested
`TLT 5-day return → sector return over 5/10/21 days`. TSM in this literature means a **12-month
(252-day) lookback with a 1-month hold**. You tested a lookback ~50× shorter than the published one.
Your null does not falsify their result; it tests a different signal.

**But** — see Test 4 — a US-only version of their test is statistically hopeless, and I want to be
blunt about that rather than hand you a test you will misread.

### 3.2 Futures open interest

**Hong & Yogo (2012), "What does futures market interest tell us about the macroeconomy and asset
prices?" *JFE* 105(3), 473–490.** DOI `10.1016/j.jfineco.2012.04.005`. NBER w16712 read in full. **[P]**
Abstract, verbatim:

> "Movements in commodity market interest predict commodity returns, bond returns, and movements in
> the short rate even after controlling for other known predictors. **To a lesser degree**, movements
> in open interest predict returns in currency, bond, and stock markets."

And in the body: "rising stock market interest predicts high stock returns, **although the statistical
evidence is [weak]**." Monthly horizon, 1965–2008, forecasting-regression R² ≈ 2.6% baseline rising to
higher with commodity open interest added. **[P]**

The strong result is *commodities predicting commodities*. The equity leg is explicitly the weak one,
it is monthly not weekly, it needs CFTC open-interest data you do not have wired up, and the sample
ends in 2008. **Skip.**

### 3.3 Credit → equity

**Gilchrist & Zakrajšek (2012), "Credit spreads and business cycle fluctuations," *AER* 102(4),
1692–1720.** DOI `10.1257/aer.102.4.1692`. Full text not obtained. **[U] for numbers.** What is
well established and safe to state: the excess bond premium (EBP) is a *quarterly-to-annual*
macroeconomic forecaster of real activity and, in the return-predictability literature, of the
*equity risk premium at business-cycle frequency*. Nobody claims a 5–21 day equity effect from it.
Your HYG/IEF 5-day change is a high-frequency proxy for a low-frequency object; the horizon mismatch
alone explains your null. EBP is published monthly by the Fed with a long lag — it is not a swing signal.

**Verdict on topic 3: one genuine published cross-asset lead-lag exists (bonds → equities, TSM
structure, 12-month lookback, monthly hold), but it is (a) a much longer signal horizon than yours,
(b) pooled across 20 countries, and (c) untestable with adequate power on US-only data. Everything
else at the weekly horizon is either weak, commodity-specific, or business-cycle frequency.**

---

## 4. SECTOR ROTATION CONDITIONED ON RATE REGIME / CURVE SHAPE

This is the thinnest literature of the six, and the way it is thin is informative.

### 4.1 The strongest result — and why it cannot help you

**Ozdagli & Velikov (2020), "Show me the money: The monetary policy risk premium," *JFE* 135(2),
320–339.** DOI `10.1016/j.jfineco.2019.06.012`. Boston Fed WP 16-27 retrieved and read in full. **[P]**

Abstract:

> "We create a parsimonious monetary policy exposure (MPE) index based on observable firm
> characteristics that are theoretically linked to how firms react to monetary policy. We find that
> stocks whose prices react more positively to expansionary monetary policy surprises earn lower
> average returns … A long-short trading strategy designed to exploit this effect achieves an
> annualized value-weighted return of **9.96 percent** with an associated **Sharpe Ratio of 0.93**
> between **1975 and 2015**."

Cost-aware, and unusually so — Velikov is the co-author of Chen & Velikov (2023), the paper that
frames your whole cost discipline. Their numbers: **[P]**

| Metric | Value |
|---|---|
| Gross long/short | 0.83%/mo, t = 5.92 |
| FF5 alpha | 0.49%/mo, t = 4.39 |
| Turnover | ~11%/mo (low) |
| Transaction costs (Novy-Marx–Velikov method) | **16 bps/mo** |
| **Net long/short** | **0.60%/mo, t = 2.46** |
| Expanding-window (OOS) FF5 alpha | 0.48%/mo |
| Novy-Marx–Velikov "generalised alpha" vs FF5 | 0.49%/mo, t = 2.80 |
| Comparison: VW momentum, same period, net | 0.19%/mo, **t = 0.43** |

Also: excluding FOMC day and day −1 entirely *strengthens* it (0.84%/mo, t = 6.23), so it is not the
pre-FOMC drift in disguise.

**Now the killer for your use case.** From their estimation design: **[P]**

> "Controls include meeting, industry, and rating fixed effects, as well as **interactions of the
> industry and rating fixed effects with the monetary policy surprises**."

> "**Other: We also control for industry effects but do not include this in our MPE index**, to
> [keep it parsimonious]."

> "…industry effects allow us to focus on cross-sectional differences in stock returns that go beyond
> differences in industry returns and keep our index parsimonious."

The monetary-policy risk premium they document is a **within-industry** premium. They netted out
exactly the variation that a sector-ETF rotation strategy is made of. There is no way to express this
with XLF/XLE/XLU. It requires ~500 single names, monthly rebalancing, and a short book.

### 4.2 The practitioner-adjacent literature

**Conover, Jensen, Johnson & Mercer (2005), "Is Fed policy still relevant for investors?" *Financial
Analysts Journal* 61(1), 70–79.** DOI `10.2469/faj.v61.n1.2685`. Paywalled; **not obtained — [U] for
all content.** What I can say without the paper: the family it belongs to (Jensen, Mercer & Johnson
1996 JFE; **Jensen & Mercer (2002), *Journal of Financial Research* 25(1), 125–139**, DOI
`10.1111/1475-6803.00008`) defines the monetary "regime" as the **direction of the last change in the
Fed discount rate**. That definition is not reproducible on modern data: after the January 2003
primary-credit reform the discount rate ceased to function as a stance signal and has not been used
as one since. Any modern reconstruction has to substitute a different regime variable, which means
you are not replicating their test — you are running a new one, with a new multiple-testing burden.
**Treat this literature as unusable for out-of-sample validation.**

### 4.3 What I searched for and did not find

I ran Crossref and OpenAlex over: `sector rotation interest rate regime out of sample`,
`yield curve slope predicts sector returns industry portfolios`, `monetary policy stance sector
returns predictability`, `sector rotation business cycle out of sample evidence`. **Zero relevant
peer-reviewed hits.** The result set was dominated by unrelated economics and medical papers — the
signature of a query with no literature behind it.

**Verdict on topic 4: there is no published out-of-sample evidence that rate-regime conditioning
improves sector selection. The one strong rate-conditioned cross-sectional premium is explicitly
constructed to be sector-neutral. Your falsification of plain sector-momentum rotation, plus your
216-cell null, is consistent with the literature — the literature just never made the claim.**

---

## 5. NOWCASTING / GDP-TRACKING MODELS AS EQUITY SIGNALS

**There is no paper showing GDPNow or the NY Fed Nowcast predicts equity returns.** What exists:

- **Beber, Brandt & Luisi (2015)** — better *nowcasts*, no return test (§1.1, **[P]**).
- **Caruso (2019)** — nowcast-model surprises ≈ market surprises, contemporaneous (§1.1, **[A]**).
- **Döpke, Hartmann & Pierdzioch, "Real-Time Macroeconomic Data and Ex Ante Predictability of Stock
  Returns," SSRN 2785236** — title indicates a *negative* real-time result. Not obtained. **[U]**

The correct benchmark for "can a macro variable forecast the equity premium at all" is:

**Goyal, Welch & Zafirov (2024), "A Comprehensive 2022 Look at the Empirical Performance of Equity
Premium Prediction," *Review of Financial Studies* 37(11), 3490–3557.** DOI `10.1093/rfs/hhae044`.
Publisher abstract, verbatim: **[A]**

> "Our paper reexamines whether 29 variables from 26 papers published after Goyal and Welch 2008, as
> well as the original 17 variables, were useful in predicting the equity premium in-sample and
> out-of-sample as of the end of 2021. … **More than one-third of these new variables no longer have
> empirical significance even in-sample. Of those that do, half have poor out-of-sample performance.
> A small number of variables still perform reasonably well both in-sample and out-of-sample.**"

That is 46 macro/valuation predictors, each individually published in a refereed journal, and the
survival rate is roughly a fifth — at *monthly-to-annual* horizons where macro variables have their
best shot. Your 5–21-day horizon is strictly harder. Their replication data (through 2025) is
downloadable free from Amit Goyal's site — useful if you ever want the canonical predictor panel.

**One genuine methodological advantage of GDPNow that I want to flag, since it's the only reason to
revisit this:** the Atlanta Fed publishes the **complete vintage/revision history** of GDPNow. That
means a point-in-time backtest is actually possible without an ALFRED subscription — which is *not*
true of most macro series and is the usual reason macro backtests leak. If you ever test it, you can
do so honestly. But you would be testing a hypothesis with zero literature prior, which raises your
required t-stat, not lowers it.

**Verdict on topic 5: NO. Skip.**

---

## 6. INDEX-INCLUSION / REBALANCE FLOW

### 6.1 The definitive paper

**Greenwood & Sammon (2024), "The Disappearing Index Effect," *Journal of Finance* 79(6).**
DOI `10.1111/jofi.13410`; NBER w30748 (Dec 2022) retrieved and read in full. **[P]**

Abstract, verbatim:

> "The abnormal return associated with a stock being added to the S&P 500 has fallen from an average
> of **3.4% in the 1980s and 7.6% in the 1990s to 0.8% over the past decade.** This has occurred
> despite a significant increase in the percentage of stock market assets linked to the index. A
> similar pattern has occurred for index deletions, with large negative abnormal returns on average
> during the 1980s and 1990s, but only **−0.6% between 2010 and 2020.**"

**Signal definition used:** total return = cumulative market-adjusted return from the last trading
day before the **announcement** to the first trading day after **implementation**. Mean
announcement→effective gap: 4.8 days for additions, 5.8 for deletions. **[P]**

**Full decade table:** **[P]**

| Decade | Addition effect (total) | Deletion effect (total) |
|---|---|---|
| 1980s | +3.42% | −4.6% |
| 1990s | **+7.6%** (peak) | −16.6% |
| 2000s | +5.21% | −12.3% |
| **2010–2020** | **+0.8% — statistically indistinguishable from zero** | **−0.6% — n.s.** |

Decomposition, additions: announcement-window return fell 3.4% (1980s) → 4.1% (2000s) → **1%** (late
2010s); implementation-day return ~2% (1980s) → 1% (2000s) → **~0** (late 2010s). The 2000–2009 vs
2010–2020 difference is highly statistically significant for total, announcement and implementation
returns separately. **[P]**

**The 2020 uptick is entirely Tesla.** Verbatim: "This is due to Tesla being added to the index in
November 2020, which, as a fraction of the S&P 500's total market capitalization, was the largest
addition of all time. **Excluding Tesla, the average inclusion effect in 2020 was −3 basis points.**" **[P]**

**Post-event reversion — this kills the short-the-reversal trade too:** **[P]**

> "In the 1990s and 2000s, there was a significant reversion in the month following the index change.
> … In the 2000s, the cumulative return peaks at 6 trading days after the announcement at 4.1%,
> reverting to 2% by 29 trading days … **Interestingly, there is very little reversion in the 2010s.
> The return peaks at 1.1% 1 trading day after the announcement and then stays near zero thereafter.**"

### 6.2 Why it died — and why "3× daily volume of forced buying" is not the argument you think

The flow got **bigger**, not smaller: net buying by S&P 500 trackers went from ~0% of shares
outstanding in the early 1990s to ~8% of shares outstanding. **[P]** Price impact went to zero anyway.
Greenwood & Sammon's diagnosis:

1. **Arbitrageurs front-run the index demand**, so the demand shock is absorbed before the effective
   date. Volume concentration around index events *rose*: in the 1990s, 15% of the total volume in
   the surrounding month occurred on the effective date; in the 2010s, **almost 30%**. **[P]**
2. **Migrations.** An index change is a "migration" when the stock moves from the S&P MidCap 400 to
   the S&P 500 — MidCap trackers sell while 500 trackers buy, so net demand is far smaller.
   Migrations went from ~40% of additions in the 1990s to **over 80%** today. And the returns diverge:
   in the mid-1990s migrations and direct additions returned 6.7% and 6.4%; by the late 2010s direct
   additions returned **2.2%** while migrations returned **−2.3%**. **[P]**
3. Trading costs fell — but Greenwood & Sammon explicitly note the timing doesn't line up ("most of
   the decline in average spreads occurred from the mid-1990s to the mid-2000s, while … a significant
   amount of the decline in the addition effect occurred from the mid-2000s to late 2010s"). **[P]**
4. Regressions of the effect on demand-shock size are positive and significant in the 1990s and 2000s
   and **turn negative and significant in the 2010s.** **[P]**

### 6.3 On RDDT specifically

I could not verify the addition. As of the current Wikipedia "Historical components of the S&P 500"
record, the most recent S&P 500 change is **2026-08-05 (FERG in, EA out**, following the PIF/Silver
Lake/Affinity acquisition of Electronic Arts**)**, and **RDDT does not appear anywhere in either the
current-constituents list or the change history.** If RDDT is going in on Aug 18, it is a
just-announced pending change that post-dates my sources. **[P] on the absence; [U] on the addition.**

Given that, three things follow from the paper rather than from RDDT specifics:

- **The announcement return is the only return, and it is ~1% and gone by the time the press release
  is public.** S&P DJI announces after the close; the stock gaps on the open. You cannot capture the
  1% unless you predicted the addition.
- **If RDDT is a direct addition (not a MidCap migration), it is in the better bucket** — 2.2% vs
  −2.3% in the late 2010s. But 2.2% is an average with an enormous cross-sectional standard deviation,
  measured on a sample ending in 2020, on an effect the same paper shows trending to zero.
- **There is no post-inclusion reversal to short.** The 2010s pattern is peak at +1.1% one day after
  announcement, then flat.

**Verdict on topic 6: documented, and documented to be DEAD. Expected edge ≈ 0. If you want to trade
RDDT, trade it on a thesis about Reddit, not on index flow.**

---

## 7. RANKED SHORTLIST WITH EXACT TEST SPECS

Ranking criterion: (published effect size, net of your costs) × (probability it is real, given the
OSAP base rate) × (testability on data you actually hold).

Your data: daily OHLC 2005–2026 for 56 tickers (all sector SPDRs, KRE/XRT/JETS/ITB/XHB/XME/SMH/IYT,
TLT/IEF/SHY/HYG/LQD, ^TNX/^FVX/^IRX, VIX complex); minute bars in `data/minute`; MES infrastructure
already built (`mes_dashboard.py`, `mes_signals.py`, `MES_STRATEGY.md`); yfinance; keyless FRED CSV.

Cost assumptions I used: SPY round trip ≈ 0.2–0.5 bps (1¢ spread on ~$640 + MOO/MOC slippage);
MES round trip ≈ 0.8–1.5 bps ($1.25 spread + ~$1.20 commission on ~$32k notional); liquid sector SPDR
round trip ≈ 2–4 bps; thin sector ETFs (JETS/XME/ITB/KRE) 5–10 bps.

---

### **#1 — Pre-announcement overnight drift, NFP / ISM / GDP (NOT FOMC)** — RUN THIS

**Why it's #1:** the only candidate with (a) a risk-premium mechanism rather than a mispricing one,
(b) documented stability in the authors' most recent subperiod (2012–2018, ex-FOMC 6.98 bps,
significant) while the *published, famous* sibling (pre-FOMC) died on schedule, and (c) a genuinely
untested 2019–2026 out-of-sample window that you own.

**Horizon caveat, stated plainly:** this is a ~16-hour hold, not 5–21 days. It does not answer your
swing question. It is the best macro-conditioned signal in the literature and it belongs in your
dashboard as an overlay, so I am ranking it first while being explicit that it is a different
horizon than you asked about.

**Signal (exactly codeable):**
```
For each trading day t:
  is_ISM[t]  = (t is the first business day of the month)              # ISM Mfg PMI, 10:00 ET
  is_NFP[t]  = (t is a BLS Employment Situation release day)           # 08:30 ET
  is_GDP[t]  = (t is a BEA GDP release day)                            # 08:30 ET
  is_FOMC[t] = (t is a scheduled FOMC statement day)                   # 14:00 ET — CONTROL, not signal

  r_on[t] = Open_SPY[t] / Close_SPY[t-1] - 1          # close-to-open, daily data
```
Position: long SPY (or 1 MES) at the close of t−1, exit at the open of t, on ISM/NFP/GDP days only.
Exclude any day that is also an FOMC day (Hu et al. do this).

**Window purity — this is the one thing to get right:**
- **ISM releases at 10:00 ET, so the 9:30 open is entirely pre-announcement. This is a clean test on
  daily data with zero contamination.** Start here.
- NFP and GDP release at 08:30 ET, so SPY's 9:30 open *includes* the ~1 hour post-release move. The
  post-announcement mean is ≈0 (Table 1: NFP +1.51 bps t=0.21, GDP −5.76 t=−0.93), so your estimate
  stays approximately unbiased — but σ roughly doubles (43→~95 bps), which is a large power cost.
  **If you want the clean NFP/GDP window, use your minute bars or MES: prior 16:00 → 08:25 ET.** That
  is the version worth building.

**Power arithmetic — do this before you run it, so you know what a null means:**

| Variant | N (2005–2026) | Assumed effect | σ | SE | Expected t |
|---|---|---|---|---|---|
| ISM alone, daily close→open (clean) | ~252 | 9 bps | 72 bps | 4.5 bps | **~2.0** |
| NFP alone, daily close→open (contaminated) | ~252 | 10 bps | ~95 bps | 6.0 bps | ~1.7 |
| Pooled ISM+NFP+GDP, daily close→open | ~750 | 8 bps | ~85 bps | 3.1 bps | **~2.6** |
| Pooled, **minute/MES clean 16:00→ann−5min** | ~750 | 8 bps | ~55 bps | 2.0 bps | **~4.0** |

**Read that table carefully. The daily-data version is underpowered — a t of 1.8 would be
uninformative, not a null.** The minute-bar version is the one that can actually resolve this.

**Pass bar.** This is one pre-specified hypothesis with a strong published prior and a stated
mechanism, not a 216-cell grid. **t > 2.5 on the pooled clean window, AND positive in each of
2005–2013 / 2014–2019 / 2020–2026.** Additionally, as a specification check that your event dates and
window are right, **you must reproduce the FOMC decay**: pre-FOMC should be strongly positive
2005–2015 and ≈0 from 2016. If it isn't, your event calendar is wrong and nothing else you measure is
trustworthy.

**Net-of-cost:** at 8 bps/event × ~36 events/yr = 2.9%/yr gross; MES round trip ~1 bp × 36 = 0.36%/yr;
**net ≈ 2.5%/yr on the notional you deploy overnight.** Sharpe is the binding constraint, not the mean:
σ ≈ 55 bps/event × √36 ≈ 3.3%/yr → **Sharpe ≈ 0.75 on deployed notional, ~14% of calendar nights.**
That is a real but small overlay, not a strategy.

**Event dates without an API key:**
- ISM: first business day of the month. Deterministic — no data source needed. **Start with this.**
- NFP: BLS Employment Situation. The "first Friday" heuristic is right ~85% of the time; the true rule
  is the third Friday following the end of the reference week. Get the real dates or your ~15% of
  mislabeled events will attenuate the estimate toward zero.
- GDP: BEA advance/second/third estimates, ~end of month. Needs the BEA schedule.
- FOMC: `fraser.stlouisfed.org/title/677` (the source Hu et al. cite) or `federalreserve.gov`.

**Leakage flags:** if you get t > 5 on daily data, you have a bug — most likely you are using
`Adj Close` (which back-adjusts dividends and will contaminate close-to-open) or your event dates are
shifted by one day so you are capturing the announcement-day full return.

---

### **#2 — Rate betas as an EXPOSURE map, not a forecast** — ADOPT, don't test

**This is a reframing of a result you already have, and it is the highest-value thing in this
document that costs you nothing.**

Your measured betas (KRE +1.087, XLF +0.950, XLE +0.956, XLP +0.232, XLU +0.083, XLRE −0.239) are
stable across three periods. Stability is exactly the property a *hedging* tool needs and is not the
property a *forecast* needs. The literature's structure is identical: Scotti's surprise index is
validated contemporaneously and offered as a control variable; the announcement-premium literature
prices the *risk*, not the direction.

**Codeable use:** the dashboard already produces directional views from other signals. When a view is
rate-linked, the beta vector tells you which instrument expresses it with the most leverage per unit
of idiosyncratic noise:
```
expression_score[s] = |beta_rate[s]| / resid_vol[s]      # signal-to-noise of the rate expression
hedge_ratio[s]      = beta_rate[s]                       # for neutralising unwanted rate exposure
```
XLRE at −0.239 is the only sign flip you measured and is therefore the natural *pair* leg against
KRE/XLF for a rate view — a spread trade whose market beta largely cancels.

**No new test required. No multiple-testing cost. Do not let this turn into a forecast.**

---

### **#3 — Stock-bond correlation regime, as a conditioner on your existing grid** — RUN, expect a null

**Why it's here:** the single most defensible "better specification" the literature suggests for your
grid is not a different macro variable — it is the recognition that the *sign of the equity-rate
relationship is itself regime-dependent* (the inflation-regime vs growth-regime stock-bond correlation
switch, sharply visible 2021–2026 vs 2000–2020). A pooled 2006–2026 regression averages across a sign
flip and will find nothing by construction. That is a *real* specification error in your test, and it
is the only one I found.

**Signal:**
```
rho[t]    = corr(daily SPY returns, daily TLT returns) over trailing 252 days, as of t-1
regime[t] = 'inflation' if rho[t] > 0 else 'growth'
```
Then re-run your existing 216-cell grid **separately within each regime**, keeping the same excess-
over-unconditional-drift construction.

**Honest expectation and the arithmetic that produces it:** this doubles your test count from 216 to
432, so a Bonferroni-style bar rises from t = 3.24 to **t ≈ 3.40**. Simultaneously it roughly halves
the effective sample per cell, cutting each |t| by ~√2. Your best worst-split t was +1.58. **√2 ×
1.58 = 2.2 at absolute best, against a bar of 3.40.** So: run it, because the sign-flip logic is
sound and you should know the answer, but **pre-commit to the null.** The value here is closing the
question, not finding an edge.

**Pre-registration requirement:** write the 432 cells and the t = 3.40 bar into the script header
*before* you look at output. Report the full distribution of t-stats, not the max.

---

### **#4 — Cross-asset TSM at the published horizon (bonds → equities)** — RUN, but read the power warning

**Signal (the published structure, not your 5-day version):**
```
signal[t]   = sign( IEF total return over trailing 252 trading days, as of t-1 )
position[t] = signal[t] × SPY,  held 21 trading days, non-overlapping
```
Benchmark against own-asset TSM (`sign(SPY 252-day return)`) to test the paper's actual claim, which
is that the *cross*-asset version beats the *own*-asset version.

**Power warning, and it is severe.** 2005–2026 with non-overlapping 21-day holds gives you ~250
observations, but the 252-day signal is ~0.98 autocorrelated, so your *effective* independent
observations are closer to **20 regime episodes**. The published result pools 20 countries precisely
to escape this. A US-only test has expected |t| ≈ 1.0–1.5 *even if the effect is exactly as published.*

**Therefore: this test cannot produce a positive result you should believe, and cannot produce a null
you should believe either.** Run it only to confirm the sign is not *negative*, and treat anything
else as uninformative. If you want a real test you need international bond/equity data (yfinance can
give you EWJ/EWG/EWU/EWA and their local bond proxies, which gets you maybe 6 countries — still
short of 20, but it changes the power calculation materially). **That is the actual follow-up if you
care about this one.**

**Do not use overlapping windows to inflate N.** That is the classic way this specific test produces
a fake t-stat of 3.

---

### **#5 — Measure the CURRENT index-inclusion effect yourself** — RUN ONCE, to close the question

**Purpose: to stop you trading RDDT on a dead effect, and to give you your own number rather than
Greenwood & Sammon's 2020 cutoff.**

**Spec:**
```
Universe: S&P 500 additions 2015-01-01 .. 2026-08-01
For each addition with announcement date a and effective date e:
    CAR = prod(1 + r_stock[a-1 .. e+1]) / prod(1 + r_SPY[a-1 .. e+1]) - 1
Report: mean, t, median, and the 2015-2019 vs 2020-2026 split.
Also split direct additions vs S&P MidCap 400 migrations (check prior index membership).
```
Addition list: `en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500` (parse the changes
table), or diff SPY's published holdings file month over month. Prices from yfinance.

**Prior from Greenwood & Sammon:** +0.8% for 2010–2020, not distinguishable from zero; −3 bps in 2020
excluding Tesla; direct additions +2.2% vs migrations −2.3% in the late 2010s; and no post-event
reversion in the 2010s.

**Decision rule, pre-committed:** trade index additions only if the 2021–2026 mean total CAR exceeds
**2% with t > 3**, *and* the direct-addition subsample is the one carrying it. Given the paper's
trend and the ~80% migration share, I put the probability of that at well under 10%.

**Leakage flag specific to this test:** if you compute CAR from the *effective* date rather than the
day before the *announcement*, you will find a spuriously clean result on a window that was never
tradeable — the announcement gap is the whole effect and it happens overnight after an
after-the-close press release.

---

### **#6 — Economic surprise indices** — DO NOT BUILD AS A FORECAST

No published predictive specification exists (§1). Build the **attribution** version instead, which
is what the literature actually supports and which improves the dashboard honestly:

```
Daily, for each sector s:
    explained[s,t] = beta_rate[s] * d10y[t] + beta_credit[s] * d(HYG/IEF)[t]
    residual[s,t]  = r[s,t] - explained[s,t]
```
Display "XLF +1.4%, of which +1.1% is the rate move" rather than "rates fell, so buy XLF." This turns
a stable, verified contemporaneous fact into a dashboard feature without pretending it is a forecast.

For **event-risk sizing** — a second legitimate use — Hu et al.'s Table 1 gives you the empirical
ranking of which releases actually move the index: FOMC ≫ NFP > ISM > GDP ≫ IP, PI, HST, claims, PPI,
CPI, and **UMich CSI is dead last (−4.03 bps, t = −0.88)**. Use that to size down into NFP and ISM
mornings, and to stop treating a UMich miss as news.

---

### **#7 — GDPNow / NY Fed Nowcast** — SKIP

No literature. Goyal, Welch & Zafirov (2024) show that of 46 *individually published* equity-premium
predictors, more than a third fail in-sample by 2021 and half the survivors fail out-of-sample — at
monthly-to-annual horizons, which are macro's best case. Your 5–21-day horizon is strictly harder.
Combined with your OSAP prior (a zero-edge signal is *expected* to lose 12 bps/month), an untested
macro nowcast signal has negative expected value before costs.

The only thing worth remembering: GDPNow's published vintage history means that *if* you ever test
it, you can do so point-in-time without leakage. That is a reason it would be a clean test, not a
reason it would be a positive one.

---

## 8. WHAT I'D ACTUALLY DO WITH THIS

1. **Build the ISM close-to-open test today.** Zero new data, deterministic event dates, ~252 events,
   and it either survives or it doesn't. It is the cheapest informative test in this document.
2. **If ISM survives, build the clean minute-bar window** (16:00 → ann−5min) for NFP+ISM+GDP. That is
   the version with the power to reach t ≈ 4, and it is the version you would trade in MES.
3. **Ship the rate-beta exposure map into the dashboard** as an attribution panel. No test needed, no
   multiple-testing cost, and it converts a verified fact into a visible feature.
4. **Run the regime-conditioned grid once, pre-registered, and write down the null** so this question
   stops recurring.
5. **Do not trade RDDT on index flow.** Run test #5 if you want your own number, but the published
   answer is unambiguous.

**The honest summary of the six topics you asked about:** one live candidate at the wrong horizon
(pre-announcement drift), one dead effect that looks alive because the flow is visible
(index inclusion), one strong result deliberately built to be sector-neutral (monetary policy risk
premium), one plausible effect that is untestable with your data's power (cross-asset TSM), and two
with no predictive literature at all (surprise indices, nowcasts). That is a low yield, but it is
the same yield the OSAP base rate predicts, and it is consistent with your own 216-cell null rather
than in tension with it.

---

## 9. FULL CITATION LIST WITH VERIFICATION STATUS

| # | Citation | DOI | Status | Source used |
|---|---|---|---|---|
| 1 | Hu, Pan, Wang & Zhu (2021), "Premium for heightened uncertainty," *JFE* 143(2) 909–937 | `10.1016/j.jfineco.2021.09.015` | **[P]** | NBER w25817 PDF, full text |
| 2 | Greenwood & Sammon (2024), "The Disappearing Index Effect," *JF* 79(6) | `10.1111/jofi.13410` | **[P]** | NBER w30748 PDF, full text |
| 3 | Ozdagli & Velikov (2020), "Show me the money," *JFE* 135(2) 320–339 | `10.1016/j.jfineco.2019.06.012` | **[P]** | Boston Fed WP 16-27 PDF, full text |
| 4 | Gilbert, Kurov & Wolfe (2020), "The disappearing pre-FOMC announcement drift," *FRL* 40 101781 | `10.1016/j.frl.2020.101781` | **[P]** | PMC 7525326, full text |
| 5 | Scotti (2016), "Surprise and uncertainty indexes," *JME* 82 1–19 | `10.1016/j.jmoneco.2016.06.002` | **[P]** | Fed IFDP 1093 PDF, full text |
| 6 | Beber, Brandt & Luisi (2015), "Distilling the macroeconomic news flow," *JFE* 117(3) 489–507 | `10.1016/j.jfineco.2015.05.005` | **[P]** | NBER w19650 PDF, full text |
| 7 | Hong & Yogo (2012), "What does futures market interest tell us…," *JFE* 105(3) 473–490 | `10.1016/j.jfineco.2012.04.005` | **[P]** | NBER w16712 PDF, full text |
| 8 | Goyal, Welch & Zafirov (2024), "A Comprehensive 2022 Look…," *RFS* 37(11) 3490–3557 | `10.1093/rfs/hhae044` | **[A]** | Publisher abstract via OpenAlex |
| 9 | Caruso (2019), "Macroeconomic news and market reaction," *IJF* 35(4) 1725–1734 | `10.1016/j.ijforecast.2018.12.005` | **[A]** | RePEc abstract |
| 10 | Pitkäjärvi, Suominen & Vaittinen (2020), "Cross-asset signals and TSM," *JFE* 136(1) 63–85 | `10.1016/j.jfineco.2019.02.011` | **[A]** | Author's Aalto thesis summary; **tables not obtained** |
| 11 | Lucca & Moench (2015), "The Pre-FOMC Announcement Drift," *JF* 70(1) 329–371 | `10.1111/jofi.12196` | **[S]** | Numbers replicated in #4 and footnoted in #1 |
| 12 | Savor & Wilson (2013), *JFQA* 48(2) 343–375 | `10.1017/s002210901300015x` | **[U]** | Characterised in #1 only; **do not quote figures** |
| 13 | Savor & Wilson (2014), "Asset pricing: A tale of two days," *JFE* 113(2) 171–201 | `10.1016/j.jfineco.2014.04.005` | **[U]** | Not obtained |
| 14 | Conover, Jensen, Johnson & Mercer (2005), "Is Fed policy still relevant?" *FAJ* 61(1) 70–79 | `10.2469/faj.v61.n1.2685` | **[U]** | Not obtained; signal definition obsolete post-2003 |
| 15 | Jensen & Mercer (2002), *J. Financial Research* 25(1) 125–139 | `10.1111/1475-6803.00008` | **[U]** | Not obtained |
| 16 | Gilchrist & Zakrajšek (2012), "Credit spreads and business cycle fluctuations," *AER* 102(4) | `10.1257/aer.102.4.1692` | **[U]** | Not obtained; wrong frequency regardless |
| 17 | Ai & Bansal (2018), "Risk preferences and the macroeconomic announcement premium," *Econometrica* 86(4) | `10.3982/ecta14607` | **[U]** | Theory paper; mechanism only |
| 18 | Fisher, Martineau & Sheng (2022), "Macroeconomic attention and announcement risk premia," *RFS* 35(11) | `10.1093/rfs/hhac011` | **[U]** | OA per Unpaywall but publisher blocked retrieval |
| 19 | McLean & Pontiff (2016), "Does academic research destroy stock return predictability?" *JF* 71(1) | `10.1111/jofi.12365` | **[U]** | Base-rate context only |
| 20 | Chen & Zimmermann (2022), "Open Source Cross-Sectional Asset Pricing," *Critical Finance Review* 11(2) | `10.1561/104.00000112` | **[U]** | Your existing OSAP prior |
| 21 | Döpke, Hartmann & Pierdzioch (2016), "Real-time macroeconomic data and ex ante predictability" | `10.2139/ssrn.2785236` | **[U]** | Title-level lead only |

**Method note.** Web search was unavailable for this review (session budget exhausted). Literature
discovery was done via the Crossref REST API, OpenAlex, and Unpaywall; full texts were retrieved from
NBER, the Federal Reserve Board, the Boston Fed, PubMed Central and institutional repositories.
Publisher sites (Elsevier, Wiley, Oxford, SSRN, JSTOR) blocked automated retrieval, which is why
items 12–21 are unverified. Any of those could be resolved with normal browser access; items 12 and
14 are the two most worth chasing if you want to close the remaining gaps in topics 2 and 4.
