# Academic Literature Sweep — Options & Volatility Edges at Swing Horizons

**Date:** 2026-08-06
**Scope:** SSRN, arXiv q-fin, NBER, Fed working papers, JF/JFE/RFS/JFQA/RAPS/Management Science,
Chen & Zimmermann Open Source Asset Pricing (OSAP).
**Filter:** days-to-weeks horizon; signals that predict what options *price* (magnitude, vol, skew,
jump risk) preferred over signals that predict direction.

Every citation below was resolved to a DOI via Crossref. Every decay number in §2 was **measured
here** from the OSAP replication data, not quoted from a paper.

---

## 0. VERDICT FIRST

**Nothing in the option-implied cross-sectional predictor family survives for a retail account.**
Say it plainly: implied volatility spread, implied skew, and O/S are not tradeable edges for you.
Five of the nine are statistically dead post-2015 regardless of who is trading them; the two that are
clearly alive gross of costs (Yan's smile slope, and the IV-spread level) are precisely the two that
Muravyev, Pearson & Pollet (JFE 2025) decompose into the **stock borrow fee**, which requires a
short-selling channel and a securities-lending desk you do not have. The signal is real. It is not
available to you. Do not spend money on single-stock option data to chase it (§7).

The one specification with a *structural* argument for escaping the borrow-fee critique is the
**change** in the IV spread (§4.3) — because the borrow fee is persistent and first-differencing
removes it. That is a hypothesis I can motivate but not verify, and it still predicts direction, so
it does not clear your own bar of "must predict what options price."

What does clear that bar, and is testable on data you already hold, is a different family entirely:
**term-structure slope predicting straddle and variance-swap returns** (§4.1, §4.2). Two candidates,
both index-level, both untested in the specific configuration that matters (§5).

---

## 0b. The one-paragraph answer

The cross-sectional option-implied predictor family — implied volatility spread, implied skew, O/S
ratio — is **the family you asked me to prioritise, and it is the family that the 2024–2025
literature has just dismantled.** Muravyev, Pearson & Pollet (JFE 2025) show that roughly **two-thirds
of the predictability in all three signals is the stock borrow fee** leaking into OptionMetrics
implied volatilities that are computed with the borrow fee set to zero. What remains after removing
high-fee stocks "does not survive adjusting for reasonable estimates of institutional transactions
costs." Independently, my own measurement on the OSAP replication data shows that 5 of the 9
option-category signals are statistically dead in 2015–2024. These signals also predict *direction*,
which you have already established is dominated by shares.

The two candidates that actually pass — **predict an option-priced quantity, survive post-publication,
and are testable on the data you already hold** — are both term-structure signals: **Johnson (JFQA
2017) VIX term-structure SLOPE** and **Vasquez (JFQA 2017) IV term-structure slope**. Both predict
*straddle and variance-swap excess returns*, with a **sign that flips**. That last property is why
they are not redundant with your 1,001 regime-gated cells: those cells all gated a *fixed short-premium
structure*, and a signal whose sign flips cannot survive that test design (§5).

---

## 1. RANKED SHORTLIST

| # | Signal | Predicts | Survives decay? | Escapes borrow-fee critique? | Retail-tradeable? |
|---|--------|----------|-----------------|------------------------------|-------------------|
| 1 | **VIX term-structure SLOPE (PC2)** — Johnson JFQA 2017 | straddle / var-swap returns | untested OOS | **N/A — index, no shorting** | **Yes — test it** |
| 2 | **IV term-structure slope** — Vasquez JFQA 2017 | straddle returns | untested OOS | **N/A — index** | **Yes — test it** |
| 3 | **Δ(call IV − put IV)** — An/Ang/Bali/Cakici JF 2014 | stock direction | Yes, t=3.41 | **Plausibly — it's a change** (§4.3) | No — needs data you lack |
| 4 | **Smile slope** — Yan JFE 2011 | stock direction | Yes, t=4.17 | **No — same object MPP kills** | **No** |
| 5 | **ML on option characteristics** — Bali et al. RFS 2023 | option returns | net of costs in paper | partially | No — needs OptionMetrics |
| 6 | **IV − trailing HV** — Goyal & Saretto JFE 2009 | straddle returns | **No** (§4.6) | N/A — spread artifact instead | Index version only |
| 7 | **Vol-of-vol** — Baltussen et al. JFQA 2018 | stock direction | untested | N/A | Partially (^VVIX) |
| 8 | **IV spread (level)** — Cremers & Weinbaum JFQA 2010 | stock direction | **No** | **No — this is the borrow fee** | **No** |

Read the last two columns together: **every signal that both survived decay and predicts direction
fails the borrow-fee test or needs data you cannot get.** The only rows with a clean "yes" in the
final column are #1 and #2 — and neither predicts direction. That is the whole finding.

**Rejected outright:** Xing-Zhang-Zhao skew, Roll-Schwartz-Subrahmanyam / Johnson-So O/S,
Bali-Hovakimian realized-minus-implied, all 0DTE literature (§6).

---

## 2. MEASURED DECAY — original work, not quoted

I downloaded the OSAP replication portfolios (Chen & Zimmermann, *Critical Finance Review* 2022,
DOI `10.1561/104.00000112`) via the `openassetpricing` Python package and computed long-short returns
by period myself. This is the honest answer to "which option anomalies survive."

**Baseline across all 210 replicated signals (as-published portfolio construction):**

| Period | Mean LS return (%/mo) |
|---|---|
| In-sample (paper's own window) | 0.617 |
| Post-sample, pre-publication | 0.408 |
| Post-publication | 0.296 |
| 2015–2024 | 0.278 |

Post-publication decay **52%**; 2015–2024 decay **55%**. Only **28.6%** of signals have post-publication
t>2; only **14.3%** have 2015–2024 t>2. This closely reproduces McLean & Pontiff (JF 2016, DOI
`10.1111/jofi.12365`): 26% out-of-sample decline, **58% post-publication decline**, 97 predictors.

**The 9 OSAP option-category signals** (t-stats; `EW` = as-published equal-weight, `VW` = value-weighted
deciles — VW is the tradeability-relevant column):

| Signal | Paper | Paper t | IS t | Post-pub t | **Post-pub decay** | **2015–24 t (EW)** | **2015–24 t (VW)** | Verdict |
|---|---|---|---|---|---|---|---|---|
| `SmileSlope` | Yan 2011 JFE | 8.17 | 8.15 | 5.16 | −53% | **4.17** | **2.79** | **Alive gross — but see §4.4** |
| `dCPVolSpread` | An/Ang/Bali/Cakici 2014 JF | 6.77 | 7.39 | 3.41 | −49% | **3.41** | **2.05** | **Alive gross** |
| `CPVolSpread` | Bali & Hovakimian 2009 MS | 4.20 | 3.17 | 3.25 | −53% | 1.62 | **2.63** | Marginal; VW > EW |
| `dVolCall` | An et al. 2014 JF | 3.45 | 2.89 | 2.41 | −32% | 2.41 | 1.42 | Marginal |
| `skew1` | Xing/Zhang/Zhao 2010 JFQA | 2.19 | 3.13 | 1.20 | −72% | 0.82 | 0.14 | **Dead** |
| `OptionVolume1` (O/S) | Johnson & So 2012 JFE | 3.45 | 2.10 | 0.40 | −87% | 0.39 | −1.57 | **Dead** |
| `OptionVolume2` | Johnson & So 2012 JFE | 2.45 | 2.26 | −1.40 | **−133%** | −1.25 | 0.37 | **Dead / sign flipped** |
| `RIVolSpread` | Bali & Hovakimian 2009 MS | 2.90 | 2.16 | 0.57 | −85% | 0.22 | −0.37 | **Dead** |
| `dVolPut` | An et al. 2014 JF | 2.03 | 1.31 | 0.97 | −41% | 0.97 | −0.31 | **Dead** |

Aggregate post-publication decay for the option family is **−63.6%**, versus **−56.7%** for
non-option predictors — option signals decay *faster* than the average anomaly, which is what you
would expect if a meaningful part of the original effect was a spread/microstructure artifact that
tightening option markets progressively removed.

Also checked under `price > $5` and `ME > NYSE 20th pct` screens: only `SmileSlope` (t=3.06 / 3.18 in
2015–24) and `dCPVolSpread` (t=1.73 / 2.02) hold up. Everything else is a microcap artifact.

**Reproduce:** `pip install openassetpricing`; `OpenAP().dl_port('op'|'deciles_vw'|'ex_price5'|
'ex_nyse_p20_me', 'pandas')`; `SignalDoc.csv` from
`raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv`.
Working scripts left in the session scratchpad (`oap_pull.py`, `oap_decay.py`).

---

## 3. THE TWO PAPERS THAT KILL MOST OF THE FIELD

### 3.1 Muravyev, Pearson & Pollet — "Why does options market information predict stock returns?"
*Journal of Financial Economics* 172 (2025), DOI `10.1016/j.jfineco.2025.104153`.
SSRN 2851560. Replication package: `data.mendeley.com/datasets/n73cyx89gs`.

They examine exactly your priority-1 list: **volatility spread, volatility skew, O/S ratio**.

Mechanism: academic implied volatilities (OptionMetrics) are computed **treating the stock borrow fee
as zero**. When the true fee is non-zero it pushes call and put IVs in *opposite* directions, so the
measured IV spread is, by a Taylor expansion they derive, **proportional to the omitted borrow fee**.
The borrow fee is independently one of the strongest known return predictors. Hence option "information"
is largely a repackaged securities-lending signal.

Published-version statement of the headline result: *"When we adjust returns for the borrow fees, the
abnormal returns on the tenth decile spread-sorted and skew-sorted portfolios are only about
one-third as large, and not significantly different from zero."*

Quantitative results, verbatim from the working-paper text I retrieved and read:

- "abnormal stock return predictability from option signals **decreases by about two-thirds** after
  returns are adjusted for borrow fees."
- Fee-adjusted decile-10 spread-sorted abnormal return is **28%** of its pre-adjustment magnitude and
  **statistically insignificant**; skew-sorted is **36%**.
- Removing high-fee stocks entirely (only ~7% of observations): remaining abnormal returns are
  "**insignificant and less than 30% as large**."
- O/S: net-of-fee decile-10 abnormal return is **−6 bp/month**; on low-fee stocks, **−3 bp/month**.
- Weekly panel regressions, low-fee subsample: volatility spread coefficient falls to **33%** of full
  sample and is **insignificant**; skew to 56%; O/S to one-quarter.
- "The remaining limited evidence of abnormal returns for the strategies **does not survive adjusting
  for reasonable estimates of institutional transactions costs**" — they benchmark against Frazzini,
  Israel & Moskowitz (2018) ~20 bp round-trip at 1% of ADV, and note Novy-Marx & Velikov's ">50 bp"
  for value-weighted strategies.

**Implication for you:** signals #4 and #8 below are *levels* of the IV spread or skew and are
therefore directly in the blast radius. Note the one possible exception in §4.3.

**Why this is specifically fatal for a retail account.** The predictability lives almost entirely in
the **short leg** — decile 10, which is where the high-fee stocks concentrate. To harvest it you must
(a) locate and borrow hard-to-borrow stock, (b) pay the *ultimate-borrower* fee, which MPP note
exceeds the lender-received fee by a prime-broker markup of ~20–30%, and (c) do it at institutional
execution costs. A retail account pays a worse borrow rate than the hedge funds in MPP's sample and
frequently cannot locate the name at all. The residual long-side effect MPP measure is **6–10 bp per
month** — below any plausible retail cost floor. There is no version of this trade that works at your
size and access.

### 3.2 Duarte, Jones & Wang — "Very Noisy Option Prices and Inference Regarding the Volatility Risk Premium"
*Journal of Finance* 79 (2024) 3581–3621, DOI `10.1111/jofi.13365`.

"Microstructure biases in the estimation of expected option returns and risk premia are large, in some
cases **over 50 basis points per day**." Their finding cuts both ways and you should know both halves:

- **Against the literature:** any option-return anomaly computed on bid-ask *midpoints* — which is
  essentially all of them, including Goyal-Saretto — is biased by an amount that scales with the
  relative spread. Illiquid single-stock options with 20–40% relative spreads are the worst offenders.
- **Against your priors:** they argue the stylized fact that volatility is *not* priced in individual
  equity options "does not withstand scrutiny," and that the variance risk premium in stock options
  *is* negative once microstructure is handled. This is in genuine tension with the
  Driessen-Maenhout-Vilkov result you have been treating as settled. It does not change your trading
  conclusion (you cannot harvest it net of single-stock option spreads), but the theoretical claim is
  now contested, not settled.

---

## 4. CANDIDATES IN DETAIL

### 4.1 — #1 — VIX term-structure SLOPE (Johnson, JFQA 2017)
**Cite:** Travis L. Johnson, "Risk Premia and the VIX Term Structure," *JFQA* 52(6), 2017.
DOI `10.1017/s0022109017000825`. 106 citations.

**Abstract claim (verbatim):** "The shape of the VIX term structure conveys information about the price
of variance risk rather than expected changes in the VIX, a rejection of the expectations hypothesis.
The second principal component, **SLOPE**, summarizes nearly all this information, **predicting the
excess returns of synthetic S&P 500 variance swaps, VIX futures, and S&P 500 straddles for all
maturities** and to the exclusion of the rest of the term structure. SLOPE's predictability is
incremental to other proxies for the conditional variance risk premia, economically significant, and
inconsistent with standard asset pricing models."

**Signal definition (codeable):**
1. Build the daily VIX-family term structure. Johnson uses the full CBOE constant-maturity curve; the
   tradeable proxy from what you hold is `[^VIX9D, ^VIX, ^VIX3M]` (9d / 30d / 93d).
2. Standardise each tenor cross-sectionally *in the time series* (z-score each series on a rolling
   expanding window — **never full-sample**, that is the leakage trap).
3. PCA on the standardised levels. **PC1 = LEVEL, PC2 = SLOPE.** Sign-normalise SLOPE so that
   contango (upward-sloping) is positive.
4. `SLOPE_t` at the prior close is the predictor.

**Universe / horizon:** S&P 500 index variance, all maturities. Johnson's headline horizon is
monthly, and he shows it holds across the maturity curve.

**Why this is not what you already tested:** you used `^VIX/^VIX3M` as a **binary contango gate** and
as a raw ratio (`swing_signals.py:239-241`, `RESEARCH_SWING_REPOS.md` §1), and
`RESEARCH_CONDOR_BUTTERFLY.md` §7 gated a *fixed short-premium* condor on term-structure quintiles.
Johnson's claim is different in three ways that matter:
- **PC2, not the raw ratio.** PC2 is orthogonal to the level; the raw `VIX/VIX3M` ratio is
  contaminated by the level, which Johnson explicitly shows carries *no* predictive information.
- **Continuous and signed**, not a binary gate.
- **The sign flips.** SLOPE predicts *positive* variance-swap excess returns in some states. A signal
  that says "be long vega here, short vega there" is structurally incapable of showing up in a search
  that only ever gates a short-premium structure. Your 1,001-cell result does not speak to it.

**Caveats:** (a) The paper is 2017 with a sample ending mid-2010s; I found **no post-publication
replication**, so treat the OOS as untested — that is a real gap, not a clean bill of health. (b) The
2015–24 base rate in §2 says ~86% of published signals fail to clear t>2 in that window. Your prior
should be that this fails too. (c) Ex-ante multiple-testing bar in your repo is **t = 3.72** — hold it
to that.

**Test spec — runnable today:**
- **Data:** `data/swing/panel.parquet` (`^VIX9D`, `^VIX`, `^VIX3M`, `^VVIX`) +
  `data/opt_eod/SPY_options.parquet`. Overlap ≈ 2011–2025.
- **Dependent variable:** monthly SPY **delta-hedged straddle** excess return. Select the expiration
  nearest 30 DTE; pick the strike with `|delta - 0.5|` minimised for the call and the matching strike
  put; enter at `ask` for longs / `bid` for shorts (never mid — see §3.2); hold 21 calendar days or
  to expiry; delta-hedge daily at the underlying close using the chain's own `delta` column.
- **Predictor:** `SLOPE_t` (PC2, expanding-window z-scores) at the prior close.
- **Regression:** `r_{t+1} = a + b·SLOPE_t + c·LEVEL_t + e`, Newey-West with 21 lags. The paper's
  claim is `b` significant, `c` not.
- **Portfolio test:** quintile-sort on SLOPE, report mean straddle return by quintile plus a
  **monotonicity test** (rank correlation quintile→mean), not top-minus-bottom. `FINDINGS.md` §3
  already flags top-vs-bottom-only as fragile.
- **Costs:** use the real quoted spread. I measured your ATM SPY relative spread: **~2.0% of mid in
  2008–2018, falling to 0.46–0.81% in 2023–2025.** Charge full quoted spread on entry and exit.
- **Pre-register:** SPY is the test, **QQQ is the confirmation.** Sign and rough magnitude must
  replicate on QQQ or it is fitted (`FINDINGS.md` §2 precedent).
- **Bar:** |t| > 3.72 on SPY *and* correct sign on QQQ.

### 4.2 — #2 — IV term-structure slope → straddle returns (Vasquez, JFQA 2017)
**Cite:** Aurelio Vasquez, "Equity Volatility Term Structures and the Cross Section of Option Returns,"
*JFQA* 52(6), 2017. DOI `10.1017/s002210901700076x`. 94 citations.

**Abstract (verbatim):** "The slope of the implied volatility term structure is positively related to
future option returns. I rank firms based on the slope of the volatility term structure and analyze
the returns for straddle portfolios. Straddle portfolios with high slopes of the volatility term
structure outperform straddle portfolios with low slopes by an economically and statistically
significant amount. The results are robust to different empirical setups and are not explained by
traditional factors, higher-order option factors, or jump risk."

**Why it ranks high:** it is the cleanest published statement of "a signal predicts what options price,
not direction," and it independently corroborates #1 in the cross-section — two different literatures
converging on *term-structure slope predicts vega returns*.

**Signal:** `slope_t = ATM_IV(long tenor) − ATM_IV(short tenor)`. Vasquez uses monthly ATM IVs at
increasing maturities. Index time-series version: **`iv90 − iv30`**.

**Testable now — I have already built the inputs.** `scripts/build_iv_features.py` constructs and saves
`data/opt_eod/SPY_ivfeatures.parquet`, **4,371 daily rows, 2008-01-02 → 2025-12-12, zero NaNs** on the
term-structure columns:

| column | meaning | mean |
|---|---|---|
| `iv30`, `iv90` | ATM IV interpolated in total variance to 30d / 90d | 0.160 / 0.170 |
| `slope` | `iv90 − iv30` — **the Vasquez signal** | +0.0094 |
| `rv21`, `rv252` | trailing realized vol | 0.163 / 0.180 |
| `gs_spread` | `iv30 − rv252` — **the Goyal-Saretto signal** | −0.0193 |
| `gs_spread21` | `iv30 − rv21` | −0.0021 |
| `rr25` | 25-delta risk reversal (put IV − call IV) | +0.0599 |
| `cp_spread_atm` | ATM call IV − put IV | −0.0120 |
| `smirk` | 25d put IV − ATM call IV (Xing-Zhang-Zhao form) | +0.0382 |

ATM IV is the mean of the nearest-50-delta call and put; rows filtered to `bid>0`, `0.02<IV<3.0`,
`0.01<|delta|<0.99` — this last filter matters, **7.8% of SPY chain rows carry a filler
`implied_volatility = 0.01488`** on deep-ITM contracts and will poison any surface build if not
dropped.

**Test spec:** identical straddle-return construction as §4.1; predictor `slope_t`; same NW
regression, same quintile monotonicity test, same t=3.72 bar, same QQQ confirmation
(`data/opt_eod/QQQ_options.parquet`, 2011–2025). Run #1 and #2 in the same harness and also run them
jointly — if SLOPE (PC2 of VIX curve) and `iv90−iv30` are ~collinear you have one signal, not two.

### 4.3 — #3 — Δ(call IV − put IV): An, Ang, Bali & Cakici (JF 2014)
**Cite:** "The Joint Cross Section of Stocks and Options," *Journal of Finance* 69(5), 2014.
NBER w19590, DOI `10.3386/w19590`. OSAP acronym `dCPVolSpread`.

**Signal:** month-over-month **change** in (put IV − call IV), decile sort, monthly rebalance.

**Measured survival (§2):** post-publication **0.684%/mo, t=3.41**; 2015–2024 t=3.41 EW, **2.05 VW**,
2.02 under the NYSE-20th-percentile size screen. Second-strongest surviving option signal.

**The reason I rank it above Yan despite a lower t-stat:** it is a **change**, and the borrow fee is
highly **persistent**. Muravyev-Pearson-Pollet's mechanism says the *level* of the IV spread is
proportional to the borrow fee level; first-differencing removes the persistent component and leaves
mostly fee *innovations* plus genuine option-market information. MPP tested spread, skew and O/S —
**they did not test the change specification.** This is the one place in the cross-sectional family
where the 2025 critique has a plausible structural gap. That is a hypothesis, not a result, and it is
the thing I would most want checked if you ever acquire single-stock option data.

**Not testable on your data.** Requires a single-stock option panel (§7).

### 4.4 — #4 — Smile slope: Yan (JFE 2011)
**Cite:** Shu Yan, "Jump risk, stock returns, and slope of implied volatility smile," *JFE* 99(1),
2011, 216–233. DOI `10.1016/j.jfineco.2010.08.011`. OSAP acronym `SmileSlope`.

**Signal:** put IV minus call IV (OI-weighted, near-the-money), quintile sort, monthly rebalance.
Low put-minus-call predicts high returns.

**Measured survival:** the single best option signal in OSAP. Paper t=8.17, OSAP replication IS
t=8.15 — so the high t-stat is **not a replication artifact**. 2015–2024: **t=4.17 EW, 2.79 VW, 3.06
price>$5, 3.18 ME>NYSE20.** It survives every cut I applied.

**Why it is nevertheless #4 and not #1:** the signal *is* the Cremers-Weinbaum / Bali-Hovakimian IV
spread with a sign flip and a different weighting. MPP's borrow-fee decomposition applies to it by
construction even though MPP never name Yan. My strong prior is that a fee-adjusted replication of
Yan would lose ~two-thirds of its return, exactly as the spread and skew did. It also predicts
*direction*, which you have shown is better expressed in shares.

Yan's stated mechanism is **jump risk** — the smile slope proxies for the risk-neutral probability of
a negative jump. If that were the true mechanism it would be a *magnitude* signal and much more
interesting to you. The literature has not adjudicated jump-risk vs borrow-fee for this specific
signal. Genuine open question.

### 4.5 — #5 — Machine learning on option characteristics (RFS 2023)
**Cite:** Bali, Beckmeyer, Mörke & Weigert, "Option Return Predictability with Machine Learning and
Big Data," *Review of Financial Studies* 36(9), 2023. DOI `10.1093/rfs/hhad017`. 174 citations.

**Abstract (verbatim):** "Drawing upon more than 12 million observations over the period from 1996 to
2020, we find that allowing for nonlinearities significantly increases the out-of-sample performance
of option and stock characteristics in predicting future option returns. The nonlinear machine
learning models generate statistically and economically **sizable profits in the long-short portfolios
of equity options even after accounting for transaction costs**. Although option-based characteristics
are the most important standalone predictors, stock-based measures offer substantial incremental
predictive power... option return predictability is driven by informational frictions and option
mispricing."

**Why it is on the list:** it is the rare paper that (a) predicts *option* returns, (b) is
out-of-sample by construction, (c) is in a top-3 journal, and (d) **accounts for transaction costs**.
**Why it is #5:** 12M single-stock option observations from OptionMetrics is the entry ticket, and
Duarte-Jones-Wang (§3.2) applies with full force to any midpoint-based single-stock option return
study — including this one. Sample ends 2020.

### 4.6 — #6 — Goyal & Saretto (JFE 2009): IV minus trailing HV
**Cite:** *JFE* 94(2), 2009, 310–326. DOI `10.1016/j.jfineco.2009.01.001`. 365 citations.
Working paper text retrieved and read directly.

**Exact signal (verbatim from the paper):** "HV is calculated using the **standard deviation of daily
realized stock returns over the most recent twelve months** and IV is obtained from **one month to
maturity, at-the-money options**... we compute the stock's IV by taking the **average of the ATM call
and put implied-volatilities**." Sort into deciles on `HV − IV`, hold one month to expiry.

**Universe / sample:** OptionMetrics IvyDB, **January 1996 – December 2005**.

**Effect size:** straddle deciles run **−9.9% → +12.6% per month**; long-short **22.5%/mo, SD 31.4%,
monthly Sharpe 0.718**. Delta-hedged calls 2.1%/mo, puts 2.3%/mo.

**Flag as probable microstructure artifact.** A monthly Sharpe of 0.718 is **~2.49 annualised** on a
strategy trading the least liquid options in the universe. The paper's own robustness section is the
tell: with "an effective spread equal to the quoted spread" the long-short straddle return falls from
**22.5% to 7.5% per month** — i.e. **two-thirds of the gross effect is bid-ask spread**, and their
base case assumes effective/quoted ≈ 0.8 which is generous for single-stock options. They further
report the effect is *larger* in high-spread stocks (27.7% vs 18.2%), which is the signature of a
spread artifact rather than an edge. Duarte-Jones-Wang (JF 2024) is the formal statement of this
critique. OSAP's closest cousin `RIVolSpread` (Bali-Hovakimian realized-minus-implied) is **dead**:
2015–24 t = 0.22 EW, **−0.37 VW**.

**Still worth testing at index level, for one reason:** everything above is about single-stock option
spreads of 20–40%. Your SPY ATM relative spread is **0.46–0.81% in 2023–2025**. The artifact that
generates the published number cannot operate at that spread. So an index test is a genuinely clean
test of whether any signal survives once the artifact is removed — and it is cheap, because the
feature is already built (`gs_spread` in `SPY_ivfeatures.parquet`).

**Test spec:** predictor `gs_spread = iv30 − rv252` (paper-faithful: 252-day trailing HV), robustness
on `gs_spread21`. Same straddle-return dependent variable and harness as §4.1. **Expect this to fail**
— pre-register that expectation so a null is informative rather than disappointing.

### 4.7 — #7 — Vol-of-vol (Baltussen, van Bekkum & van der Grient, JFQA 2018)
**Cite:** "Unknown Unknowns: Uncertainty About Risk and Stock Returns," *JFQA* 53(4), 2018.
DOI `10.1017/s0022109018000480`. 145 citations.

**Abstract:** "Stocks with high uncertainty about risk, as measured by the **volatility of expected
volatility (vol-of-vol)**, robustly underperform stocks with low uncertainty about risk by **8% per
year**. This vol-of-vol effect is distinct from (combinations of) at least 20 previously documented
return predictors, survives many robustness checks, and holds in the United States and across
European stock markets."

**Signal:** rolling standard deviation of daily option-implied volatility (they use 30-day ATM IV over
a 1-month window). Cross-sectional version needs single-stock IV.

**Partial test available:** you hold **`^VVIX`** in `data/swing/panel.parquet`, and you can compute a
realized vol-of-vol directly from `iv30` in the feature file (`iv30.rolling(21).std()`). Use it as a
*conditioner* on #1/#2 rather than a standalone signal — the published effect is cross-sectional and
the index analogue is a different object. Low confidence; listed for completeness.

### 4.8 — #8 — Cremers & Weinbaum (JFQA 2010): the IV spread
**Cite:** *JFQA* 45(2), 2010, 335–367. DOI `10.1017/s002210901000013x`. 549 citations.

**Abstract (verbatim), including the authors' own decay admission:** "stocks with relatively expensive
calls outperform stocks with relatively expensive puts by **50 basis points per week**... The degree of
predictability is larger when option liquidity is high and stock liquidity low... **The degree of
predictability decreases over the sample period.** Our results are consistent with mispricing during
the earlier years of the study, **with a gradual reduction of the mispricing over time.**"

The authors documented decay *within their own 1996–2005 sample*, before publication. Twenty years
later, MPP has supplied the mechanism (borrow fees) and OSAP's `CPVolSpread` shows 2015–24 EW t=1.62.
**Listed as #8 to close it out, not to trade it.** Note the one oddity worth a footnote: `CPVolSpread`
is one of very few signals where **value-weighting beats equal-weighting** (2015–24 VW t=2.63 vs EW
1.62), which is the opposite of the usual microcap pattern and is consistent with the borrow-fee story
concentrating in large, heavily-shorted names.

---

## 5. WHY THIS IS NOT REDUNDANT WITH YOUR 1,001-CELL NULL

`RESEARCH_CONDOR_BUTTERFLY.md` §7 records: *"1,001 regime-gated cells — including GEX and DIX
z-scores, VIX percentile, VIX term structure, and IV-minus-RV — produced ZERO cells positive in all
three periods. The best cell reached t = +3.49, below the multiple-testing bar of 3.72."*

That is a strong and, I think, correct result **about the question it asked**. The question it asked
was: *does any state variable make a short-premium structure profitable?* Every cell held the
structure fixed (short vega) and varied the gate.

Johnson's SLOPE and Vasquez's slope make a different claim: the *sign* of the expected straddle
return varies with the signal. Under that hypothesis the correct test holds the **signal** fixed and
lets the **structure** flip — long vega in one quintile, short vega in the other. A sign-flipping
signal evaluated only in its short-vega half will show up as a mediocre gate and be discarded, which
is exactly what happened. So:

**The specific untested configuration is: continuous, signed, PC2-based term-structure signal driving
a long-or-short delta-hedged straddle on SPY, 2008–2025, priced at the real quoted spread.**

I want to be straight about the prior, though. Your own base rates (§2: 14.3% of published signals
clear t>2 in 2015–24), Dew-Becker & Giglio's zero option alphas over 15 years, and the fact that
Johnson (2017) has **no published post-publication replication** all point the same direction. Call it
20–25% that this clears t=3.72 on SPY with the correct sign on QQQ. It is worth one clean test
because the test is cheap and the features are built — not because it is likely.

---

## 6. REJECTED, WITH REASONS

| Candidate | Reason |
|---|---|
| **Xing, Zhang & Zhao (JFQA 2010) skew** — DOI `10.1017/s0022109010000220`, 656 cites, headline 10.9%/yr | OSAP 2015–24 **t=0.82 EW, 0.14 VW**. MPP: skew-sorted decile-10 falls to 36% of magnitude fee-adjusted. Dead twice over. |
| **Roll, Schwartz & Subrahmanyam O/S (JFE 2010)** — DOI `10.1016/j.jfineco.2009.11.004`; **Johnson & So (JFE 2012)** — DOI `10.1016/j.jfineco.2012.05.008` | OSAP `OptionVolume1` 2015–24 t=0.39 EW, **−1.57 VW**; `OptionVolume2` sign-flipped. MPP: net-of-fee **−6 bp/month**. Dead. |
| **Ge, Lin & Pearson (JFE 2016)** — DOI `10.1016/j.jfineco.2015.08.019` | Mechanism paper for O/S; superseded by MPP 2025 (same Pearson). Retained as context, not a signal. |
| **Bali & Hovakimian `RIVolSpread` (MS 2009)** | 2015–24 t = 0.22 EW, −0.37 VW. Dead. |
| **All 0DTE research** | **There is no peer-reviewed 0DTE literature.** Crossref returns only SSRN preprints: Brogaard/Han/Won (ssrn 4426358), Dim/Eraker/Vilkov "0DTEs: Trading, Gamma Risk and Volatility Propagation" (ssrn 4692190), Almeida/Freire/Hizmeri "0DTE Asset Pricing" (ssrn 4701401), Vilkov "0DTE Trading Rules" (ssrn 4641356), Adams et al. 2025 (ssrn 5641974). Citation counts 1–7. Your explicit filter was peer-reviewed; nothing passes it. Also note the SSRN 0DTE corpus now includes vendor-adjacent backtest papers (e.g. ssrn 7055179, an Option Alpha backtest compilation) — treat as marketing. |
| **Recent arXiv q-fin** | Swept `q-fin.PR` and `q-fin.TR` recent listings. **Nothing relevant.** q-fin.TR recent is automated market makers, execution, LLM trading agents, crypto; q-fin.PR is local-vol modelling, ESG, renewable PPAs. arXiv q-fin is not a productive source for options edges right now — do not spend time there. |
| **Sub-hourly / intraday VRP term structure** | Your SPXW panel is 30-min snapshots, **±2% moneyness only**, 0DTE — it cannot test tail, skew, or jump-risk signals, which all live outside ±2%. |

---

## 7. WHAT YOU CAN AND CANNOT TEST — explicit

**Data verified this session:**

| Asset | Coverage | Notes |
|---|---|---|
| `data/opt_eod/SPY_options.parquet` | 24.7M rows, **2008-01-02 → 2025-12-12** | Full chain, `bid/ask/IV/delta/gamma/theta/vega/volume/open_interest`. 13–35 expirations per date. 94.8% have `bid>0`. **7.8% carry filler `IV=0.01488` — must filter.** |
| `data/opt_eod/QQQ_options.parquet` | 15.3M rows, **2011-03 → 2025-12** | Same schema. Use as the confirmation set. |
| `data/spxw/data_opt.parquet` | 1.37M rows, 1,919 days **2016-09 → 2024-05** | 30-min snapshots 10:00–16:00, **moneyness 0.98–1.02 only**, 0DTE. `reth` column contains `inf` — broken, do not use. |
| `data/swing/panel.parquet` | 45 tickers, 1998–2026 | Includes **`^VIX`, `^VIX9D`, `^VIX3M`, `^VVIX`, `^SKEW`** — everything §4.1 needs. |
| `data/stocks/panel.parquet` | **74 tickers, OHLCV only** | **No options.** |
| `data/opt_eod/SPY_ivfeatures.parquet` | **NEW — built this session**, 4,371 rows 2008–2025 | `iv30, iv90, slope, rv21, rv252, gs_spread, gs_spread21, rr25, cp_spread_atm, smirk` |

**Testable today: #1, #2, #6, and #7 in partial form.** All are index-level and all inputs exist.

**Not testable: #3, #4, #5, #8.** Every cross-sectional option-implied signal needs a **single-stock
option panel with IV by strike and expiry**, which you do not have — `data/stocks/panel.parquet` is
OHLCV for 74 tickers. Do not attempt to proxy these from equity data; the signal *is* the option
surface.

**And note the second missing input:** even with single-stock chains you would still need **stock
borrow fee data** (Markit/IHS securities-lending, which is what MPP used and is not cheap) to
distinguish a real edge from the borrow-fee proxy. Without borrow fees you cannot tell whether you
have found #3/#4 or merely rediscovered the securities-lending market. **Given that the answer for
signals #4 and #8 is already known to be "mostly borrow fee," acquiring single-stock option data to
chase this family is, in my judgement, not worth the spend.**

---

## 8. RECOMMENDED SEQUENCE

1. **Build the straddle-return harness once.** SPY, 30-DTE ATM delta-hedged straddle, entry at
   ask/exit at bid, daily delta hedge off the chain's own `delta`, 2008–2025. Everything below reuses
   it. This is the reusable asset regardless of which signal wins.
2. **Run #1 (SLOPE) and #2 (`iv90−iv30`) jointly.** Check collinearity first. NW(21) regressions plus
   quintile monotonicity. Bar: |t| > 3.72 on SPY, correct sign on QQQ.
3. **Run #6 (`gs_spread`) in the same harness as a pre-registered expected null.** It costs one line
   and it settles Goyal-Saretto at index level for good.
4. **Stop if 2 and 3 both fail.** That would be a clean, well-powered negative on the whole
   term-structure family, and combined with §2 and §3 it closes the options-and-volatility literature
   as a source of edges for this book. Write it up as a null and move on — that is a real result.

---

## 9. SOURCES

**Primary — verified via Crossref DOI resolution:**
- Muravyev, Pearson & Pollet (2025), "Why does options market information predict stock returns?", *JFE* 172 — [10.1016/j.jfineco.2025.104153](https://doi.org/10.1016/j.jfineco.2025.104153)
- Duarte, Jones & Wang (2024), "Very Noisy Option Prices and Inference Regarding the Volatility Risk Premium", *JF* 79:3581-3621 — [10.1111/jofi.13365](https://doi.org/10.1111/jofi.13365)
- Johnson (2017), "Risk Premia and the VIX Term Structure", *JFQA* — [10.1017/s0022109017000825](https://doi.org/10.1017/s0022109017000825)
- Vasquez (2017), "Equity Volatility Term Structures and the Cross Section of Option Returns", *JFQA* — [10.1017/s002210901700076x](https://doi.org/10.1017/s002210901700076x)
- Bali, Beckmeyer, Mörke & Weigert (2023), "Option Return Predictability with Machine Learning and Big Data", *RFS* — [10.1093/rfs/hhad017](https://doi.org/10.1093/rfs/hhad017)
- Yan (2011), "Jump risk, stock returns, and slope of implied volatility smile", *JFE* 99:216-233 — [10.1016/j.jfineco.2010.08.011](https://doi.org/10.1016/j.jfineco.2010.08.011)
- An, Ang, Bali & Cakici (2014), "The Joint Cross Section of Stocks and Options", *JF* — [10.3386/w19590](https://doi.org/10.3386/w19590)
- Cremers & Weinbaum (2010), "Deviations from Put-Call Parity and Stock Return Predictability", *JFQA* 45:335-367 — [10.1017/s002210901000013x](https://doi.org/10.1017/s002210901000013x)
- Xing, Zhang & Zhao (2010), *JFQA* — [10.1017/s0022109010000220](https://doi.org/10.1017/s0022109010000220)
- Roll, Schwartz & Subrahmanyam (2010), "O/S", *JFE* — [10.1016/j.jfineco.2009.11.004](https://doi.org/10.1016/j.jfineco.2009.11.004)
- Johnson & So (2012), *JFE* — [10.1016/j.jfineco.2012.05.008](https://doi.org/10.1016/j.jfineco.2012.05.008)
- Ge, Lin & Pearson (2016), *JFE* — [10.1016/j.jfineco.2015.08.019](https://doi.org/10.1016/j.jfineco.2015.08.019)
- Goyal & Saretto (2009), "Cross-section of option returns and volatility", *JFE* — [10.1016/j.jfineco.2009.01.001](https://doi.org/10.1016/j.jfineco.2009.01.001)
- Cao & Han (2013), *JFE* — [10.1016/j.jfineco.2012.11.010](https://doi.org/10.1016/j.jfineco.2012.11.010)
- Baltussen, van Bekkum & van der Grient (2018), *JFQA* — [10.1017/s0022109018000480](https://doi.org/10.1017/s0022109018000480)
- Bakshi & Kapadia (2003), *RFS* — [10.1093/rfs/hhg002](https://doi.org/10.1093/rfs/hhg002)
- Cheng (2018), "The VIX Premium", *RFS* — [10.1093/rfs/hhy062](https://doi.org/10.1093/rfs/hhy062)
- Dew-Becker, Giglio, Le & Rodriguez (2017), "The price of variance risk", *JFE* — [10.1016/j.jfineco.2016.04.003](https://doi.org/10.1016/j.jfineco.2016.04.003)
- McLean & Pontiff (2016), *JF* — [10.1111/jofi.12365](https://doi.org/10.1111/jofi.12365)
- Chen & Zimmermann (2022), "Open Source Cross-Sectional Asset Pricing", *CFR* — [10.1561/104.00000112](https://doi.org/10.1561/104.00000112)

**Data / tools:**
- [openassetpricing.com](https://www.openassetpricing.com/) · [github.com/OpenSourceAP/CrossSection](https://github.com/OpenSourceAP/CrossSection) · `pip install openassetpricing`
- MPP replication package: [data.mendeley.com/datasets/n73cyx89gs](https://data.mendeley.com/datasets/n73cyx89gs)
- Goyal-Saretto working paper text: [ruf.rice.edu/~jgsfss/goyal_041808.pdf](https://www.ruf.rice.edu/~jgsfss/goyal_041808.pdf)

**0DTE preprints (none peer-reviewed):** ssrn `4426358`, `4692190`, `4701401`, `4641356`, `5641974`.
