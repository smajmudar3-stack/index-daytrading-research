# Corporate Spinoffs as a Tradeable Anomaly — Evidence Review

**Date:** 2026-08-14
**Question:** Is the corporate spinoff anomaly real today, at what horizon, at what magnitude net of costs, and can a $1,000–3,000-per-position retail account capture it?

**Verdict up front: NO. Do not trade this.**

The spinoff anomaly is one of the most thoroughly dead anomalies I have examined. It fails on
every independent test available:

1. Its **in-sample t-stat was only 2.43** — far below the t ≥ 4.0 bar, and weaker than
   momentum (3.74), size (3.07) or accruals (4.71) in the same reference library.
2. **Post-publication it decayed 107%** — i.e. to slightly *negative*.
3. In **2015–2024 it is significantly negative** (t = −2.07) and ranks **206th of 207**
   predictors in the Open Source Asset Pricing library.
4. A **real-money ETF has been running this exact strategy since December 2006** and has
   delivered an alpha of **exactly zero** (t = −0.00) against a size-matched benchmark, while
   underperforming the S&P 500 outright.
5. The only robustly surviving effect is the **~3% announcement-day pop**, which is not
   capturable — it is realised in the gap on the announcement, before anyone can act.
6. The headline mechanism (**forced index-fund selling**) has independently been shown to have
   **disappeared** — the S&P 500 index effect fell from 7.4% in the 1990s to under 1% today.

Two of these six are original computations run for this report and are reproducible from the
scripts in `scripts/`.

---

## 0. Methodology and provenance notes

Every number below is tagged with horizon, benchmark, weighting, and whether it is gross or net.

**What I verified directly:** the Open Source Asset Pricing (OSAP) signal documentation and its
full monthly return panel (raw CSV, downloaded and analysed here); the abstracts of McLean &
Pontiff (2015), Chen & Velikov (2022), Hou-Xue-Zhang (2017), Kothari & Warner (1997),
Bessembinder-Cooper-Zhang (2018), Chen & Zimmermann (2019), Veld & Veld-Merkoulova (2008),
Greenwood & Sammon (2024), Mitchell & Pulvino (2001), Kiesel et al. (2022), and several
post-2010 spinoff papers; and ~19.7 years of daily/monthly ETF price history.

**What I could NOT verify and have marked as such:**

- **Cusatis, Miles & Woolridge (1993, JFE)** — fully paywalled (Elsevier 403, no repository
  copy, `is_oa: false`). I use OSAP's hand-collected record of the paper's own Table 3B instead,
  which is a good but second-hand source.
- **Desai & Jain (1999, JFE)** — same; abstract elided by publisher on both Semantic Scholar and
  OpenAlex. **I do not quote specific numbers from it.**
- **McConnell & Ovtchinnikov (2004)** — published in the *Journal of Investment Management*,
  which is not indexed in OpenAlex or Semantic Scholar and is paywalled. **I could not retrieve
  it at all.** I therefore make no claim about its specific findings. This is a genuine gap;
  see §2.4 for why it does not change the conclusion.
- **Documented spinco bid-ask spreads** — I found no paper I could open that reports measured
  effective spreads specifically for spun-off entities. See §5 for how I handle this.

**Funding/publisher note.** The canonical spinoff papers are conventional academic work in
Elsevier's *JFE* with no disclosed sponsor. The two most decisive sources against the anomaly
have notably *disinterested* provenance: OSAP is maintained by **Andrew Y. Chen, an economist at
the Federal Reserve Board**, and Tom Zimmermann (Cologne) — a public, non-commercial replication
project with no product to sell. Greenwood & Sammon is Harvard Business School / *Journal of
Finance*. Conversely, the most bullish item found (Pfister & Kendzia 2023, "Outperforming the
S&P 500 through Investment Plays") is an **unrefereed Preprints.org manuscript with 2 citations**
and is given no weight.

**Search caveat.** The web-search budget for this session was exhausted at the outset, so the
literature sweep was conducted via the OpenAlex and Semantic Scholar APIs plus direct fetches
rather than keyword search engines. Coverage of indexed journal literature is good; coverage of
grey literature and practitioner research is thinner than I would like.

---

## 1. The canonical results: parent and spun-off entity

### 1.1 Cusatis, Miles & Woolridge (1993), *Journal of Financial Economics*

The founding paper. Per OSAP's hand-collected record of the original (Table 3B, Panel I-24):

| Field | Value |
|---|---|
| Sample period | 1965–1988 |
| Sample size | 140 spinoffs |
| Holding horizon | **24 months** |
| Benchmark | **Matched-firm-adjusted returns** (size/industry matched control firm) |
| Weighting | Value-weighted |
| Reported return | **≈2.08%/month equivalent** — i.e. ~50% cumulative over 24 months |
| **t-statistic** | **2.43** |
| Gross or net? | **GROSS.** No transaction costs, no spreads, no price impact. |

OSAP's own summary line reads `t=2.3 in event study`, and its notes state the test is an
*"event study [with] nonstandard data"* using *"matched-firm-adjusted returns... for only 140
spinoffs."*

**Flag: this t-stat fails the stated bar by a wide margin.** 2.43 is not a marginal miss against
t ≥ 4.0 — it is roughly the level at which, given the number of anomalies tested across the
literature, one expects a substantial share of pure false positives. For calibration, from the
same SignalDoc: Accruals t = 4.71, Momentum t = 3.74, Size t = 3.07. Spinoff is the weak sibling.

**Second flag: matched-firm-adjusted buy-and-hold returns over 24–36 months are precisely the
methodology that Kothari & Warner (1997, JFE) showed to be broken.** Their simulations found
long-horizon abnormal-return tests are *"severely misspecified,"* with *"rejection frequencies
using parametric tests sometimes exceed[ing] 30% when the significance level of the test is 5%."*
That is a six-fold inflation of the false-positive rate. A nominal t of 2.43 under a test whose
true size is 30% rather than 5% is not evidence of anything. Fama (1998) made the same argument
from the bad-model-problem side.

**OSAP's own replication-quality grade for this signal is `4_lack_data` — the worst rating on
their scale** (versus `1_good` for momentum, size and accruals). Their note explains why:

> "OP uses CCH Capital Changes Reporter, but we use CRSP acquisition file. More importantly OP
> excludes about 75% of spinoffs because they are not 'pure' spinoffs, but we do not in order to
> keep a reasonable amount of stocks."

This matters in both directions and I want to be fair about it: OSAP's proxy is broader and
noisier than CMW's hand-collected pure-spinoff sample, so OSAP's null result is *not* a clean
refutation of CMW on its own. It is one of three independent strands, and the other two (the
meta-analytic literature in §2.1 and the live ETF in §2.3) do not share this weakness.

### 1.2 Desai & Jain (1999), *Journal of Financial Economics*

Sample 1990s-era, focus-increasing versus non-focus-increasing spinoffs; the standard citation
for "focus-increasing spinoffs outperform." **The publisher elided the abstract on every index I
could reach and the paper is paywalled, so I am not quoting its point estimates.** What can be
said is that it uses the same long-horizon BHAR methodology as CMW and is therefore exposed to
the same Kothari-Warner misspecification critique. Its 363 citations make it influential, not
correct.

### 1.3 Veld & Veld-Merkoulova (2008/2009) — the meta-analysis

*International Journal of Management Reviews*. This is the single most useful source in the whole
review because it aggregates rather than adds to the pile. Verified abstract:

> "Meta-analysis is used to summarize the findings of **26 event studies** on spin-off
> announcements. A **significantly positive average abnormal return of 3.02%** is found during
> the event window... The second part of the paper overviews studies on the long-run stock price
> performance of spin-offs. **Even though early studies find a long-run superior performance,
> this effect is no longer found in later studies that use more refined statistical tests.**"

That final sentence is the answer to the user's question 3, written by the field's own reviewers
in 2008 — before McLean-Pontiff, before OSAP, before the replication crisis literature. The
long-run drift did not survive better statistics. The announcement effect did.

Also from the same abstract, and relevant to mechanism: returns are higher for larger spinoffs,
for tax/regulatory-friendly divestments, and for focus-improving spinoffs; and — a detail that
should worry anyone building a trading rule — *"spin-offs that are later completed are associated
with lower abnormal returns than non-completed spin-offs."* The announcement pop is largest for
the deals that never happen.

### 1.4 Post-2010 evidence

| Study | Sample | Finding |
|---|---|---|
| **Chemmanur, Krishnan & Nandy (2012)**, "Corporate Divestitures: Spin-Offs vs. Sell-Offs" | 322 spin-offs, 3,280 sell-offs, 1980–2006 | Spin-offs have *more positive announcement effects* than sell-offs, **but firms that sell off "exhibit a greater improvement in their post-divestiture long-term operating and stock return performance compared to those that spin off."** The long-run drift is *weaker* for spinoffs than for the alternative transaction. |
| **Sponsored vs. conventional spin-offs (2010)**, *Financial Management* | 57 sponsored spin-offs, 1994–2005 | Stock performance **"significantly negative over a three-year period following the spin-off date."** |
| **"Value-creation through spin-offs: Australian evidence" (2017)**, *Australian Journal of Management* | ASX-listed | 3-day announcement CAR **+2.93%** (significant) — closely replicating Veld's 3.02%. Long-run: only *"some evidence"* of positive excess return to 24 months, concentrated in focus-increasing deals. Non-US, small sample. |
| **Lim & Choi (2026)**, "When 'Split' Is Not Enough: Hedge Fund Activism and the Long-Run Performance of Spin-offs", SSRN | — | **Could not retrieve (SSRN 403). Unverified.** Title implies a conditional/qualified result. |

The pattern across post-2010 work: the **announcement effect replicates consistently at ~3%**;
the **long-run drift does not replicate, reverses, or survives only as a conditional
sub-sample effect** in small non-US samples.

---

## 2. Has it decayed? — the decisive question

### 2.1 The general prior

- **McLean & Pontiff (2015, *Journal of Finance*)**, 97 predictors, verified abstract: *"Portfolio
  returns are 26% lower out-of-sample and 58% lower post-publication... We estimate a 32%
  (58%−26%) lower return from publication-informed trading."* Critically for this case:
  **"Post-publication declines are greater for predictors with higher in-sample returns, and
  returns are higher for portfolios concentrated in stocks with high idiosyncratic risk and low
  liquidity."** The spinoff signal is a high-in-sample-return, low-liquidity, high-idio-vol
  signal — the exact profile that decays hardest.
- **Chen & Velikov (2022, *JFQA*)**, 204 anomalies, verified abstract: net of effective bid-ask
  spreads, post-publication effects, and the post-2000 trading era, *"the average anomaly's
  expected return is a measly **4 bps per month**. The strongest anomalies net, at best, 10 bps...
  Several methods for combining anomalies net around 20 bps."* And explicitly: this is *"despite
  cost mitigations that produce impressive net returns in-sample and **the omission of additional
  trading costs, like price impact**."*
  *(Note: the brief cited 8 bps/month; the published JFQA figure is 4 bps. The published number
  is worse than the prior assumed.)*
- **Hou, Xue & Zhang (2017/2020)**, 447 anomalies, verified abstract: *"With microcaps alleviated
  via New York Stock Exchange breakpoints and value-weighted returns, **286 anomalies (64%)**...
  are insignificant at the conventional 5% level. Imposing the cutoff t-value of three raises the
  number of insignificance to **380 (85%)**."*

### 2.2 Direct test: the spinoff signal in the OSAP panel

I downloaded the Chen-Zimmermann OSAP monthly long-short return panel (212 predictors, Oct 2025
release) and computed the spinoff signal's performance by era. **This is value-weighted**, per
the original paper's specification, and is **gross of all trading costs**.

Script: `scripts/osap_spinoff_decay.py`

| Window | n (months) | Mean | t-stat | Annualised | Sharpe |
|---|---|---|---|---|---|
| **OP in-sample 1965–1988** | 288 | **+0.396%/mo** | **+2.19** | +4.7% | +0.45 |
| Post-sample, pre-publication 1989–1993 | 60 | +0.239%/mo | +0.69 | +2.9% | +0.31 |
| **Post-publication 1994–2024** | 372 | **−0.029%/mo** | **−0.16** | −0.4% | −0.03 |
| Modern era 2005–2024 | 240 | −0.072%/mo | −0.39 | −0.9% | −0.09 |
| **2015–2024** | 120 | **−0.603%/mo** | **−2.07** | **−7.2%** | −0.66 |

**Decay: 107.4% of the in-sample mean.** The signal did not merely weaken; it crossed zero.

Applying the fitted decay relationship from the brief (post-publication mean = −0.122 + 0.61 ×
in-sample mean) to this signal's in-sample mean of +0.396%/mo predicts +0.119%/mo. **The realised
post-publication mean of −0.029%/mo came in even below that already-pessimistic forecast.**

**Library-wide calibration check.** Computing the same statistics across all 212 predictors for
2015–2024 reproduces the stated prior almost exactly, which validates both the data and the
method:

| Statistic | This computation | Stated prior |
|---|---|---|
| Share with t > 2 | **14.5%** | 14.3% |
| Share with t > 3 | **3.4%** | 3.4% |
| Median t | +0.70 | — |
| Mean return | +0.305%/mo | — |

**And in that 2015–2024 cross-section, the Spinoff signal ranks 206th out of 207.** It is the
second-worst predictor in the entire library. Not "decayed to zero" — actively harmful.

Full-sample (1926–2024) long-short: +0.218%/mo, t = +1.84. Even pooling a century of data, it
does not clear t = 2.

**Portfolio breadth** (`scripts/osap_spinoff_ports.py`): the spinoff leg holds a median of 63
names, 76 in the 2010s and 122 in the 2020s. Note this is OSAP's *broad* proxy; true pure
spinoffs are far fewer.

### 2.3 Direct test: the real-money ETF

This is the cleanest out-of-sample evidence available anywhere, and I have not seen it cited in
the academic debate.

**CSD — the Invesco S&P Spin-Off ETF — has been trading since 15 December 2006.** It holds an
index of recently spun-off US companies. It is exactly this anomaly, packaged and traded with
real money for **19.7 years**. Its returns are **total returns net of the fund's expense ratio
and its own internal trading costs** — a genuine investable net-of-cost track record, not a paper
portfolio.

Script: `scripts/spinoff_etf_oos.py` (236 monthly observations, Dec 2006 – Aug 2026, Yahoo
adjusted closes).

**Full history:**

| Fund | CAGR | Vol | Sharpe | Mean | t | Growth of $1 |
|---|---|---|---|---|---|---|
| **CSD (spinoffs)** | **+10.22%** | **22.4%** | **+0.55** | +1.031%/mo | +2.45 | 6.78× |
| SPY (S&P 500) | +11.04% | 15.4% | +0.76 | +0.976%/mo | +3.37 | 7.84× |
| IWM (Russell 2000) | +8.60% | 20.4% | +0.51 | +0.865%/mo | +2.26 | 5.07× |
| MDY (S&P MidCap 400) | +9.75% | 18.3% | +0.60 | +0.920%/mo | +2.67 | 6.23× |
| IJR (S&P SmallCap 600) | +9.49% | 20.0% | +0.56 | +0.927%/mo | +2.46 | 5.95× |

**Alpha, full history:**

| Regression | Beta | Alpha | t(alpha) |
|---|---|---|---|
| CSD vs SPY | 1.25 | −0.190%/mo (−2.28%/yr) | −0.88 |
| CSD vs IWM | 0.99 | +0.176%/mo (+2.11%/yr) | +0.95 |
| **CSD vs MDY** | 1.12 | **−0.000%/mo (−0.00%/yr)** | **−0.00** |
| CSD vs IJR | 1.00 | +0.105%/mo (+1.26%/yr) | +0.55 |

**Against a size-matched mid-cap benchmark, the alpha is zero to three decimal places.** Against
small-cap benchmarks it is positive but nowhere near significant (t ≈ 0.5–1.0). Against the S&P
500 it is negative. And the fund took **22.4% volatility to earn less than the S&P 500's 15.4%**
— a Sharpe of 0.55 against 0.76.

Adding back the expense ratio (~0.65%/yr) to get a gross figure moves the MDY alpha to roughly
+0.65%/yr with a t-stat around +0.25. Still nothing.

**2015–2024 sub-period** (the era the brief cares about):

| Regression | Beta | Alpha | t(alpha) |
|---|---|---|---|
| CSD vs SPY | 1.33 | −0.664%/mo (−7.96%/yr) | −2.23 |
| **CSD vs IWM** | 1.03 | **−0.002%/mo (−0.02%/yr)** | **−0.01** |

CSD returned +7.34% CAGR versus SPY's +13.00% over 2015–2024. The size-matched alpha is dead
zero. This **independently corroborates the OSAP panel result** using entirely different data,
a different construction method, real money, and real costs.

### 2.4 On the McConnell & Ovtchinnikov gap

I could not retrieve this paper. It is the one requested source I failed to obtain. I note that
its non-retrieval does not materially affect the conclusion: whatever it found in 2004, the
question of whether the effect survived is settled by the 2015–2024 evidence in §2.2 and §2.3,
both of which post-date it by two decades and both of which say no. If it found the effect was
robust, it has since been falsified; if it found the effect was fragile, it agrees with
everything else here.

---

## 3. WHERE in the event window is the return?

**Plainly: the only surviving effect is at the announcement, and the long drift is the part that
died.** This is the answer that determines usability, so it deserves to be unambiguous.

| Window | Effect | Status |
|---|---|---|
| **Announcement (−1 to +1 days)** | **+3.02%** (Veld meta-analysis, 26 studies); +2.93% (Australia 2017) | **Robust and replicated — but not capturable** |
| Ex-date / distribution | No reliable documented effect found | — |
| **Drift, 6–36 months post-spinoff** | Originally ~50% over 24 months (CMW, t=2.43, gross) | **Dead.** Not found in later studies with better statistics (Veld); 107% decayed and negative in OSAP; zero alpha in the live ETF over 19.7 years |

**Why the ~3% announcement pop is not tradeable.** It is measured over a window that *begins
before the announcement*. The return is realised in the opening gap on the news. To capture it
you would have to hold the parent *before* an unannounced spinoff — i.e. predict the
announcement. That is not a swing trade; it is either a fundamental-research position held for
an unknown period at unknown cost, or it is trading on material non-public information.

Worse, Veld's meta-analysis found the announcement return is *larger for spinoffs that are never
completed*. So the pop is not paying you for the eventual economic restructuring at all — which
undercuts the entire efficiency/focus rationale for expecting a subsequent drift.

**Direct consequence for the stated use case:** the original claim was a **24–36 month drift**.
Even if it were still alive — and it is not — a days-to-weeks swing trader could capture roughly
1/24th to 1/36th of it per month of holding, against a bid-ask spread paid in full on entry and
exit. That is structurally hopeless before the decay evidence is even considered. **This anomaly
is horizon-incompatible with the account in question regardless of whether it is real.**

---

## 4. Mechanism — which explanations survived?

### 4.1 Forced institutional selling — **FALSIFIED as a return source**

This is the mechanism most often cited by practitioners: index funds must dump the spinco because
it is not in their benchmark, creating temporary price pressure and a subsequent rebound.

The premise is real; the profit is not. The general phenomenon is the **index effect**, and
**Greenwood & Sammon (2024, *Journal of Finance*)** measured what happened to it (verified
abstract):

> "The abnormal return associated with a stock being added to the S&P 500 has **fallen from an
> average of 7.4% in the 1990s to less than 1% over the past decade**. This has occurred **despite
> a significant increase in the share of stock market assets linked to the index**. A similar
> pattern has occurred for index deletions, with large negative abnormal returns during the 1990s
> but an average return of only **0.1% between 2010 and 2020**... We document a **similar decline
> in the index effect among other families of indices**."

This is the mechanism's own gold-standard test, and it is devastating for the spinoff story
specifically. The forced-selling channel got *weaker* even as indexation got *larger*, because
liquidity provision around predictable flows became competitive. If the flow effect has collapsed
for the single most telegraphed, largest-dollar forced-trading event in the market — S&P 500
addition and deletion — there is no basis for believing it persists for spinoffs, which are
smaller, more numerous, and equally well telegraphed.

Relatedly, **Goyal, Urban & Zhao (2025, *Journal of Accounting Research*)** found that index
inclusion does not improve price informativeness: *"bid-ask spreads, price impact measures,
post-earnings announcement drift, and the implied cost of equity remain unchanged."*

### 4.2 Analyst neglect / information asymmetry — **partially survives as economics, not as alpha**

**Chemmanur & He (2016, *Journal of Corporate Finance*)**, "Institutional trading, information
production, and corporate spin-offs," documents institutional information production around
spinoffs (abstract not retrievable; existence and topic verified). The information-asymmetry story
is coherent and there is evidence that spinoffs resolve it. But resolving information asymmetry
predicts a *one-time re-rating*, which is the announcement effect — not a persistent drift, and
not one an outsider can trade.

**Insider trading evidence** (Charoenwong, Ding & Pan, 2023, *IJBF*, verified abstract) supports
undervaluation as a motive: insider purchases rise in the four quarters *before* a spinoff
announcement, and *"only firms with abnormal net insider purchases exhibit significant improvement
in their long-run market and operating performance after a spinoff."* This is the most interesting
surviving conditional result in the review — but note what it requires: identifying abnormal
insider buying *pre-announcement*. That is a Form 4 signal, not a spinoff signal, and the user has
already tested Form 4 strategies (see `MEMORY.md` → Quant Factory Insider, which failed DSR).

### 4.3 Improved incentives and focus — **survives as real economics, does not generate alpha**

The strongest-supported mechanism, and the one with the least trading value.

- **Daley, Mehrotra & Sivakumar (1997, JFE)**: value creation is concentrated in *cross-industry*
  spinoffs, and — importantly — *"the operating performance improvement is associated with the
  continuing rather than the spunoff entity."* The parent improves, not the spinco. This is the
  opposite of the practitioner folklore that the spinco is the thing to buy.
- **Feldman (2015, *Strategic Management Journal*)**: spinoffs genuinely improve incentive
  alignment for spinco managers, though parent managers mostly just get paid more.
- **"The effects of corporate spin-offs on productivity" (2014, JCF)**: real productivity effects
  exist.

Spinoffs really do create value. But **an efficiently priced value-creating event produces no
abnormal return** — the market capitalises it at announcement, which is exactly the +3% we
observe. Real economic improvement and tradeable alpha are different claims, and only the first
one is supported.

### 4.4 Verdict on mechanism

Every proposed channel either (a) predicts only an announcement-window re-rating, which is what
the data show and which is uncapturable, or (b) predicts forced-flow mispricing, which has been
directly measured and found to have collapsed. **No mechanism survives that predicts a capturable
post-event drift.**

---

## 5. Cost and implementability

### 5.1 Is it a microcap artifact?

This is the sharpest version of the question, and here the evidence is unusually clean because
**two independent tests with opposite weighting schemes both return zero**:

- The **OSAP test is value-weighted** (per the original paper's specification, confirmed in
  SignalDoc: `Stock Weight: VW`). Post-publication: −0.029%/mo, t = −0.16.
- **CSD is a modified-equal-weight index fund** of actual spinoffs, and its size-matched alpha is
  −0.000%/mo, t = −0.00.

So the failure is **not** a weighting artifact, and it is **not** the usual "works only in
microcaps" story either — it simply is not there under either construction. Note that this is
*stronger* evidence than the typical Hou-Xue-Zhang failure mode: HXZ showed 65% of anomalies die
when you *switch* to NYSE breakpoints and value weights. Spinoffs die under both.

That said, the microcap concern remains relevant to why the *original* result appeared: CMW's
sample of 140 spinoffs from 1965–1988, matched-firm-adjusted with a 24-month BHAR, is exactly the
kind of small-sample, small-cap, long-horizon design that Kothari-Warner showed produces
30%-false-positive-rate tests.

### 5.2 Costs

I could not find a paper reporting measured effective bid-ask spreads specifically for spun-off
entities, and I will not invent one. What can be established:

- **Chen & Velikov (2022)** is the governing result: net of *effective* spreads and
  post-publication effects, the average anomaly earns **4 bps/month**, and the best earn 10 bps —
  **before price impact**. An anomaly whose gross post-publication return is already **−3 bps/month**
  does not survive any cost model, because there is nothing to subtract costs from.
- **McLean & Pontiff (2015)** specifically found decay is *worse* for low-liquidity, high-idio-vol
  predictors. Spincos are the archetype.
- The live ETF result already **includes** real costs. CSD's zero alpha is a *net* number. That
  sidesteps the whole spread-estimation problem: a professional manager with institutional
  execution, running this strategy with real money for 19.7 years, netted zero. A retail account
  will do worse than that manager, not better.

### 5.3 The retail account specifically

At **$1,000–3,000 per position**, the structural problems compound:

1. **Wrong horizon.** The claimed effect was a 24–36 month drift. A swing trader holding
   days-to-weeks captures a small fraction of any drift while paying the full round-trip spread.
2. **Spread dominance.** A newly spun-off small-cap commonly trades at spreads of tens of basis
   points to over 1% in its first weeks — the period of maximum "forced selling." On a $2,000
   position, a 0.75% round trip is ~$15. To overcome that you need the position to move ~0.75%
   in your favour *before* any edge accrues. *(Spread magnitude here is my structural estimate,
   not a verified published figure — flagged accordingly.)*
3. **Insufficient breadth.** US pure spinoffs run on the order of 20–50 per year. A strategy that
   fires a few times a month cannot accumulate a statistically meaningful track record within any
   reasonable evaluation period — you would need decades to distinguish a real 2%/yr edge from
   noise at 22% volatility.
4. **Concentration risk.** With few events and 22.4% annualised volatility (CSD's realised
   figure), position-level outcomes are dominated by idiosyncratic variance, not by any edge.
5. **The edge is zero.** Points 1–4 would matter if there were something to capture. There isn't.

**A retail account cannot capture this, because there is nothing to capture.** The binding
constraint is not costs or size — it is that the expected gross return is already negative.

---

## 6. Related event-driven variants

| Variant | Current evidence | Verdict for this account |
|---|---|---|
| **Merger arbitrage** | Mitchell & Pulvino (2001, *JF*), 4,750 mergers 1963–1998: **+4%/yr excess return after transaction costs** — the strongest verified net figure in this review. But: returns are *"positively correlated with market returns in severely depreciating markets but uncorrelated in flat and appreciating markets... similar to those obtained from selling uncovered index put options."* | **No.** The 4%/yr is gross of the tail: it is compensation for short-put risk — you collect small premiums and occasionally lose badly on deal breaks. This is the same payoff shape as the credit-structure strategies already found to be negative-expectancy (`MEMORY.md` → Options Structure Null). Sample ends 1998; no verified post-2000 replication found. Deal spreads are now measured in low single digits and competed by dedicated funds. |
| **SPAC arbitrage** | Kiesel et al. (2022, *European Financial Management*), 236 deSPACs 2012–2021: announcement **+7.4%**, then **−14.1% at 1 year, −18.0% at 2 years** for public investors. Dambra et al. (2023, *The Accounting Review*): SPAC revenue forecasts attract *retail* trading and *"positively predict future operating underperformance, stock underperformance, and class action lawsuits."* | **No — and note the direction.** Post-announcement SPAC returns are strongly *negative*. The documented winners are sponsors and redeeming pre-merger holders; the documented losers are retail buyers post-announcement. The one honest structure (buy below trust, redeem) is a cash-like yield trade requiring size and operational infrastructure. |
| **Index-inclusion flow** | Greenwood & Sammon (2024, *JF*): **7.4% → <1%** for additions; deletions **→ 0.1%**. Declining across index families. | **No.** Explicitly and quantitatively dead. This is the single best-documented anomaly death in the modern literature. |
| **Post-bankruptcy equities** | Could not retrieve Eberhart/Altman/Aggarwal or any recent replication. Maksimovic & Phillips (1998, *JF*) addresses asset efficiency, not returns. | **Unverified — no basis for a view.** Also structurally unsuitable: post-emergence equities are illiquid, often OTC, with complex capital structures and legal claims that require specialist diligence. |
| **Rights offerings** | No verified current evidence found. | **Unverified.** Rare in US markets. |

**Cross-cutting caution.** Bessembinder, Cooper & Zhang (2018, *RFS*) tested eight documented
corporate-event anomalies — credit downgrades, IPOs, SEOs, M&A, dividend initiations, repurchases,
splits, analyst downgrades — and found *"the apparently abnormal returns in the months after these
events are substantially reduced or eliminated when compared to characteristic-based benchmarks."*
The event-driven category as a whole is largely a benchmark artifact. Spinoffs are not an
exception within a healthy category; they are a typical member of a category that mostly
evaporates under correct benchmarking.

**The honest counterweight.** **Jensen, Kelly & Pedersen (2023, *JF*)**, "Is There a Replication
Crisis in Finance?", argues the pessimistic reading is overdone: *"The majority of asset pricing
factors (i) can be replicated; (ii) can be clustered into 13 themes... (iii) work out-of-sample in
a new large data set covering 93 countries."* Chen & Zimmermann (2019, *RAPS*) similarly find
publication bias explains only −12.3% of in-sample returns, concluding that post-publication decay
reflects genuine *arbitrage of real mispricing* rather than the effects having been fake. I take
both seriously. Note, however, that **both cut against the spinoff case rather than for it**: if
decay is real arbitrage rather than statistical illusion, then a signal that has been public since
1993, packaged in a retail ETF since 2006, and is currently the 206th of 207 predictors, has been
thoroughly arbitraged. Either reading lands in the same place.

---

## 7. Conclusion

**Is the spinoff anomaly real today?** No.

- In-sample **t = 2.43**, versus a required bar of **t ≥ 4.0** — it never met the standard.
- Post-publication decay of **107%**; 2015–2024 mean **−0.603%/mo, t = −2.07**.
- **Rank 206 of 207** predictors in the OSAP library for 2015–2024.
- A **19.7-year live ETF** produced **−0.000%/mo alpha (t = −0.00)** against a size-matched
  benchmark, net of real costs, while underperforming the S&P 500 with 45% more volatility.
- The mechanism most often invoked — forced index-fund selling — has been **directly measured to
  have collapsed** (7.4% → <1%).

**At what horizon?** The only surviving effect is the **~3% announcement-window pop**, which
requires holding the parent before an unannounced spinoff and is therefore not capturable. The
originally claimed effect was a **24–36 month drift** — structurally useless for a days-to-weeks
swing trader even in the counterfactual where it were still alive.

**At what magnitude net of costs?** **Zero to negative.** Gross post-publication return is already
−3 bps/month; the live net-of-cost implementation is 0 bps of alpha. There is no positive number
to subtract costs from.

**Can a $1,000–3,000-per-position retail account capture it?** **No.** Not because of costs or
account size, but because the edge does not exist. A well-resourced professional manager has been
running exactly this strategy with real money since 2006 and has produced no alpha.

**Recommendation: close this line of inquiry.** This is a clean, well-sourced negative and it is
worth what it cost — it is now the fourth documented null in this research program (alongside
intraday direction, options structure, and insider swing), and the evidence here is considerably
more decisive than in the other three. Three independent strands (a public replication library, a
19.7-year live fund, and the field's own meta-analysis) agree, and the headline mechanism has been
independently falsified.

The one genuinely open thread, if anything is to be pursued: the insider-trading conditional
(Charoenwong et al. 2023) — that only spinoffs preceded by abnormal net insider *purchases* show
long-run improvement. But that is a Form 4 signal wearing a spinoff costume, the Form 4 line has
already been tested and failed DSR in this program, and it inherits the same fatal 24-month
horizon. I would not spend more on it.

---

## Reproducibility

| Script | Purpose |
|---|---|
| `scripts/osap_spinoff_decay.py` | In-sample vs post-publication vs 2015–2024 decay of the OSAP Spinoff predictor; library-wide calibration |
| `scripts/osap_spinoff_ports.py` | Portfolio-leg composition and breadth by decade |
| `scripts/spinoff_etf_oos.py` | Real-money out-of-sample test via the CSD spin-off ETF vs SPY/IWM/MDY/IJR |
| `scripts/openalex_lit.py`, `scripts/openalex_gap.py`, `scripts/lit_search.py` | Literature retrieval via OpenAlex and Semantic Scholar APIs |

**Data sources.** Chen & Zimmermann, *Open Source Cross-Sectional Asset Pricing* (Critical Finance
Review, 2022), October 2025 release — `SignalDoc.csv`, `PredictorLSretWide.csv` (212 predictors),
and the full portfolio-sort panel, obtained from openassetpricing.com and the
`OpenSourceAP/CrossSection` GitHub repository. ETF price history from the Yahoo Finance chart API
(monthly adjusted closes, dividends reinvested).

## Key references

- Cusatis, Miles & Woolridge (1993), "Restructuring through spinoffs: The stock market evidence," *JFE* — [doi:10.1016/0304-405X(93)90009-Z](https://doi.org/10.1016/0304-405x(93)90009-z) *(paywalled; not directly verified)*
- Desai & Jain (1999), "Firm performance and focus," *JFE* — [doi:10.1016/S0304-405X(99)00032-X](https://doi.org/10.1016/s0304-405x(99)00032-x) *(paywalled; not directly verified)*
- Veld & Veld-Merkoulova (2008), "Value creation through spin-offs: A review of the empirical evidence," *IJMR* — [doi:10.1111/j.1468-2370.2008.00243.x](https://doi.org/10.1111/j.1468-2370.2008.00243.x)
- McLean & Pontiff (2015), "Does Academic Research Destroy Stock Return Predictability?" *JF* — [doi:10.1111/jofi.12365](https://doi.org/10.1111/jofi.12365)
- Chen & Velikov (2022), "Zeroing In on the Expected Returns of Anomalies," *JFQA* — [doi:10.1017/S0022109022000874](https://doi.org/10.1017/s0022109022000874)
- Hou, Xue & Zhang (2017), "Replicating Anomalies," NBER w23394 — [doi:10.3386/w23394](https://doi.org/10.3386/w23394)
- Greenwood & Sammon (2024), "The Disappearing Index Effect," *JF* — [doi:10.1111/jofi.13410](https://doi.org/10.1111/jofi.13410) (open working-paper version: [NBER w30748](https://doi.org/10.3386/w30748))
- Kothari & Warner (1997), "Measuring long-horizon security price performance," *JFE* — [doi:10.1016/S0304-405X(96)00899-9](https://doi.org/10.1016/s0304-405x(96)00899-9)
- Bessembinder, Cooper & Zhang (2018), "Characteristic-Based Benchmark Returns and Corporate Events," *RFS* — [doi:10.1093/rfs/hhy037](https://doi.org/10.1093/rfs/hhy037)
- Mitchell & Pulvino (2001), "Characteristics of Risk and Return in Risk Arbitrage," *JF* — [doi:10.1111/0022-1082.00401](https://doi.org/10.1111/0022-1082.00401)
- Kiesel, Klingelhöfer, Schiereck & Vismara (2022), "SPAC merger announcement returns and subsequent performance," *EFM* — [doi:10.1111/eufm.12366](https://doi.org/10.1111/eufm.12366)
- Jensen, Kelly & Pedersen (2023), "Is There a Replication Crisis in Finance?" *JF* — [doi:10.1111/jofi.13249](https://doi.org/10.1111/jofi.13249)
- Chen & Zimmermann (2019), "Publication Bias and the Cross-Section of Stock Returns," *RAPS* — [doi:10.1093/rapstu/raz011](https://doi.org/10.1093/rapstu/raz011)
- Chemmanur, Krishnan & Nandy (2012), "Corporate Divestitures: Spin-Offs vs. Sell-Offs"
- Daley, Mehrotra & Sivakumar (1997), "Corporate focus and value creation: evidence from spinoffs," *JFE* — [doi:10.1016/S0304-405X(97)00018-4](https://doi.org/10.1016/s0304-405x(97)00018-4)
- Charoenwong, Ding & Pan (2023), "Insider Trading and Corporate Spinoffs," *IJBF* — [doi:10.32890/ijbf2023.18.2.1](https://doi.org/10.32890/ijbf2023.18.2.1)
