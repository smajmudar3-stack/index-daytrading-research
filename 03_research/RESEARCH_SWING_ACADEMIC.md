# Swing-Horizon Academic Edge Survey (2 days – 8 weeks, US equities/ETFs, options-expressible)

**Date:** 2026-08-06
**Scope:** Academic literature review for tradeable edges at the 2-day-to-8-week horizon, expressible
in liquid US equity/ETF options from a small retail account.
**Companion:** `FINDINGS.md` (the intraday/0DTE null result). This document is the swing-horizon
sequel and should be read as continuous with it.

> **⚡ If you read only one section, read [§F](#section-f--conditional-reversal--dip-buying-the-live-hypothesis)
> and the [RANKED SHORTLIST](#ranked-shortlist).** §F contains the base-rate test that reframes the
> dip-buying result and identifies the one signal that survives it. Reproducible via
> `scripts/base_rate_check.py`.

---

## READ THIS FIRST — the three numbers that frame everything

Before any individual strategy, three primary-source results bound what is achievable. They are the
reason this report's conclusions are conservative.

**1. Chen & Velikov (2023, JFQA 58(3), 968–1004) — "Zeroing In on the Expected Returns of Anomalies."**
Verified from the published PDF. 204 long-short stock-market anomalies. They account for (i) effective
bid–ask spreads, (ii) post-publication decay, (iii) the post-2000 modern trading era. The chain, verbatim
from the paper:

> in-sample gross **68 bps/month** → after total trading costs incl. cost mitigation **44 bps** →
> after post-publication decay **9 bps** → restricting to the modern (post-2005) sample: **"the average
> anomaly's expected return is a measly 4 bps per month. The strongest anomalies net, at best, 10 bps
> after controlling for data mining. Several methods for combining anomalies net around 20 bps."**

They add: *"Expected returns are negligible despite cost mitigations that produce impressive net returns
in-sample and the omission of additional trading costs, like price impact."* Their Table 7 finds size,
B/M and **momentum are all unprofitable net** in the modern sample; momentum nets **12 bps/month**
1998–2013.
**Implication:** cross-sectional equity anomaly trading is, in expectation, ~0.05–0.20%/month gross of
options costs. An option overlay's bid–ask alone is an order of magnitude larger than that. **Any
strategy whose edge is "a published cross-sectional anomaly, expressed in options" is dead on arrival.**
URL: https://www.cambridge.org/core/services/aop-cambridge-core/content/view/945133D5A3ECEEAF466AEE91551FD225/S0022109022000874a.pdf/zeroing-in-on-the-expected-returns-of-anomalies.pdf

**2. Broadie, Chernov & Johannes (2009, RFS) — "Understanding Index Option Returns."**
Verified from the Columbia working-paper PDF (June 2008 revision). S&P 500 **futures** options,
**Aug 1987 – Jun 2005, 215 monthly observations, one-month options held to expiration.**
The single most important sentence for anyone about to sell options:

> the (5%, 95%) confidence band for the average 6%-OTM monthly put return, simulated under
> Black-Scholes with 215 observations, is **−65% to +28%**.

i.e. 18 years of monthly data cannot distinguish a hugely profitable put-selling program from a
hugely unprofitable one. Their headline result: *"the large returns to writing out-of-the-money puts
is not inconsistent (i.e., is statistically insignificant) relative to the Black-Scholes model or the
Heston stochastic volatility model due to the extreme sampling uncertainty associated with put returns."*
p-value for 6% OTM puts ≈ 8%.
**But** market-neutral portfolios *are* significant (their Table 6, monthly returns to the LONG side):

| Portfolio | Data avg %/mo | BS expected %/mo | BS p-val | SV expected | SV p-val |
|---|---|---|---|---|---|
| ATM straddle (ATMS) | **−15.7** | +1.1 | ~0.0% | +1.4 | ~0.0% |
| Crash-neutral straddle (CNS) | −9.9 | +2.2 | 0.8% | +2.2 | 0.9% |
| Put spread (PSP) | −21.2 | −11.1 | **12.5%** | −13.1 | **17.1%** |

Realized monthly vol in-sample ≈ **15% annualized**, ATM IV ≈ **17%** — a ~2-vol-point wedge, and
they note it *had not vanished* in the last two years of their sample.
**Implication:** the statistically real object is the **market-neutral variance premium** (short
straddle / delta-hedged short vol), not directional put selling and not put spreads. Note the paper
explicitly *ignores margin* and *ignores transaction costs*.
URL: https://www.columbia.edu/~mnb2/broadie/Assets/EOR_20080618.pdf

**3. The decay decomposition — McLean & Pontiff vs Chen & Zimmermann.**
- McLean & Pontiff (2016, JF 71(1), 5–32), 97 predictors: portfolio returns are **26% lower
  out-of-sample** and **58% lower post-publication**; they attribute **32 pp (58−26)** to
  publication-informed trading. https://onlinelibrary.wiley.com/doi/10.1111/jofi.12365
- Chen & Zimmermann (2023, "Publication Bias in Asset Pricing Research", arXiv:2209.13623) decompose
  the ~50% post-publication decline: Empirical-Bayes shrinkage implies **only ~12 pp is publication
  bias**; the remaining **~38 pp is a genuine decline in expected returns** (arbitrage capital / crowding).
  They also find **almost all findings replicate**, predictability persists OOS, and the false discovery
  rate is **<10%**. https://arxiv.org/pdf/2209.13623
- Hou, Xue & Zhang (2020, RFS 33(5), 2019–2133), 452 anomalies with NYSE breakpoints + value weighting:
  **65% fail |t| > 1.96**; at the multiple-testing hurdle of 2.78, **82.1% fail**. (NBER WP version:
  447 anomalies, 64% insignificant; 85% at t>3.) https://www.nber.org/papers/w23394

**Reconciling 2 and 3:** HXZ and Chen–Zimmermann disagree about *replication* (the difference is
microcap weighting), but they agree on the practical point: whatever survives is small, and roughly
half of it is gone after publication. Combined with Chen–Velikov, the honest prior for any *published,
well-known* cross-sectional signal is that its net expected return at a retail scale is indistinguishable
from zero.

**Cost asymmetry that kills most of this for options.** Muravyev & Pearson (2020, RFS 33(11), 4973–5014),
"Options Trading Costs Are Lower than You Think," is the *optimistic* paper on option costs: they find
options prices are predictable at high frequency and traders who time executions pay **less than 40% of
the conventional (quoted-spread) cost measure**; the overall average effective spread is **~25% smaller**
than conventional estimates. Note that even this optimistic result requires *active execution timing* —
it is not what you get sending a market order.
URL: https://academic.oup.com/rfs/article-abstract/33/11/4973/5732665

---

## SECTION A — Cross-sectional momentum, industry/sector rotation, factor momentum

### A1. Classic cross-sectional stock momentum (Jegadeesh–Titman) — NOT usable here
- **Signal:** rank stocks on cumulative return over months t−12 to t−2 (skip the most recent month);
  long top decile, short bottom decile.
- **Horizon:** formation 6–12 months, **holding 1–6 months**. Monthly rebalance. Monthly bin width.
- **Novy-Marx (2012, JFE 103(3), 429–453), "Is momentum really momentum?"**: the predictive power
  comes from performance **12 to 7 months prior**, not recent performance; recent returns are "largely
  irrelevant after controlling for performance at intermediate horizons," with an abrupt drop-off at 12
  months. This "echo" is *stronger* among the largest, most liquid stocks — the only ones a retail
  options account can trade. https://www.sciencedirect.com/science/article/abs/pii/S0304405X11001152
- **Net-of-cost verdict:** Chen & Velikov Table 7 — momentum nets **12 bps/month** 1998–2013 and is
  **unprofitable** in the modern sample. Frazzini, Israel & Moskowitz ("Trading Costs of Asset Pricing
  Anomalies," and the 2018 "Trading Costs" paper using $1.7tn of live AQR executions across 21 markets)
  argue costs are "an order of magnitude smaller than previous studies suggest" and that size/value/
  momentum remain implementable — **flag: the authors run a fund that sells these strategies, and their
  cost estimates are for a sophisticated institutional execution desk, not a retail account.** Chen &
  Velikov reconcile the two and still find momentum unprofitable.
  https://pages.stern.nyu.edu/~afrazzin/pdf/Trading%20Cost%20of%20Asset%20Pricing%20Anomalies%20-%20Frazzini,%20Israel%20and%20Moskowitz.pdf
- **Retail-options verdict: REJECT.** Requires ~100+ names both sides, monthly turnover, and a 12-bp/month
  gross edge. The option overlay cost is 10–50× the edge. Not expressible.

### A2. Industry / sector momentum (Moskowitz & Grinblatt 1999) — likely DEAD post-2000
- **Signal:** form 20 industry portfolios on 2-digit SIC; rank on past-return; long top 3 industries,
  short bottom 3.
- **Horizon:** MG's headline result is **short-horizon** — 1-month and 6-month formation, 1-month holding.
  This is notable because *individual stocks* reverse at the 1-month horizon while *industries* continue.
  Sample **Jul 1963 – Jul 1995**, NYSE/AMEX/Nasdaq. They report industry momentum survives controls for
  size, B/M, individual-stock momentum, cross-sectional mean dispersion, and microstructure.
  https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00146
- **Post-publication:** this is a textbook decay case. Ehsani & Linnainmaa (2022, JF 77(4), 1877–1919)
  show industry momentum is subsumed by **factor momentum**; their companion paper (Arnott et al. 2019)
  shows short-term industry momentum "stems from factor momentum." Secondary sources report that
  **industry momentum "stops working" around the year 2000** while factor momentum does not.
  ⚠️ *I was unable to open the primary text asserting the exact post-2000 industry-momentum break
  (Springer paywall + rate limits). Treat the "dead after 2000" claim as strongly indicated but
  UNVERIFIED against primary text.*
  Similarly, a secondary summary of "Market states and momentum in sector exchange-traded funds"
  (Journal of Asset Management, 2014) states **"in the post-2000 period, there is no momentum in sector
  ETFs."** ⚠️ **UNVERIFIED against primary text** — abstract not retrievable within this session.
  https://link.springer.com/article/10.1057/jam.2014.24
- **Costs:** the same secondary source reports that introducing **1 bp/trade** cost in a sector-ETF
  momentum grid reduced profitable configurations from **42 to 13 out of 240** — i.e. the result is
  cost-fragile at a cost level ~100× smaller than a retail option round-trip.
- ⚠️ **Vendor-backtest red flag:** Quantpedia's "Sector Momentum – Rotational System" page is cited
  around the web with **~21% annualized, Sharpe 1.6, max drawdown −7.5%**. A long-only US-equity sector
  strategy with a −7.5% maximum drawdown spanning 2008 is **not physically plausible**. Per rule 6,
  treat as a probable specification/leakage artifact, not a discovery. **Do not use these numbers.**
- **✅ SETTLED NEGATIVE — confirmed on own data (2026-08).** A sweep of **3,536 sector-rotation
  configurations** found **40 survived train (1998–2011) + validate (2012–2019), and NONE beat SPY
  buy-and-hold on validate or on test (2020–2026).** An independent audit found the two best-built
  open-source projects in this space **also publish a null on sector momentum rotation.** This now
  agrees with (i) the secondary report of no sector-ETF momentum post-2000, (ii) Ehsani-Linnainmaa's
  subsumption of industry momentum into factor momentum, and (iii) the 1-bp cost fragility above.
  **Four independent lines, one conclusion. Do not revisit.**
- **Retail-options verdict: REJECT** as a standalone edge. Closed.
- ⚠️ **One distinction worth preserving:** this null is about *cross-sectional sector MOMENTUM
  (rotation)*. It says nothing about *conditional sector REVERSAL*, which is the opposite sign and
  which Nagel (2012) reports is profitable **specifically when VIX is high** — see **§F7**. Do not let
  the rotation null close off the reversal test.

### A3. Factor momentum — the strongest surviving momentum result, but not options-expressible
- **Ehsani & Linnainmaa (2022, JF 77(4), 1877–1919), "Factor Momentum and the Momentum Factor."**
  Verified from NBER WP 25551. 20 major published factors (French/AQR/Stambaugh libraries).
  **Signal:** time-series — long each factor with positive trailing 12-month return, short each with
  negative. **Holding: 1 month.**
  - The average factor earns **52 bps/month following a year of gains vs 2 bps following a year of
    losses; difference t = 4.67** (WP text; the published JF version reports 51 bps vs 6 bps).
  - The time-series factor-momentum strategy earns **4.2% annualized, t = 7.04**.
    ⚠️ **Per rule 6, flag t = 7.04.** It is not necessarily a bug — a 1-month-rebalanced, 20-asset,
    long-short, low-vol strategy over ~50 years can legitimately reach this — but a t of 7 on a
    published factor is exactly the profile that later shrinks. The paper's own conditioning result
    shows why: the effect is **71 bps/month (t=4.79) in low-sentiment states vs 18 bps (t=1.32) in
    high-sentiment states**, i.e. it is regime-dependent, not stationary.
  - **Mechanism (stated):** factor returns are positively autocorrelated; momentum "aggregates the
    autocorrelations found in all other factors." They link it to slow-moving capital (Duffie 2010)
    and Baker–Wurgler sentiment — values diverge from, then converge to, fundamentals.
  - **Crash property:** stock momentum "crashes when these autocorrelations break down." So this
    inherits momentum-crash risk.
  https://www.nber.org/system/files/working_papers/w25551/w25551.pdf
- **Independent practitioner replication — Falck, Rej & Thesmar (CFM, 2020), arXiv:2009.04824,
  "Is Factor Momentum More than Stock Momentum?"** 72 documented signals, US data, dollar-neutral and
  dynamically market-hedged. Their equal-risk factor average has **Sharpe 0.96** (a sanity check on
  their replication). Factor momentum, both cross-sectional and directional, has **Sharpe ≈ 1**.
  Two findings matter enormously here:
  1. *"Consistent with many investment strategies becoming crowded over time, we find that average
     risk-adjusted performance tends to taper off in the late 2000s."* — independent confirmation of decay.
  2. **The only factor momentum that is not just stock momentum lives in the LAST MONTH of returns.**
     *"After controlling for stock momentum and factor exposure, statistically significant Sharpe ratios
     only belong to implementations which include the last month of returns."* And their conclusion:
     *"stocks exhibit mean reversion at monthly time scale. This is not true for factor momentum, as
     factor returns are persistent at all time scales."*
  https://arxiv.org/pdf/2009.04824
- **Why this matters for a 2-day-to-8-week trader:** it is the cleanest statement in the literature that
  **at your exact horizon, single stocks mean-revert while portfolios/factors trend.** That is a
  structural fact about your window, not a strategy.
- **Costs:** ⚠️ **Neither paper reports net-of-cost factor-momentum returns.** CFM discusses price impact
  theoretically (§ on flows) but does not publish a net Sharpe. State this as an open hole.
- **Retail-options verdict: REJECT as directly tradeable** (requires trading 20–72 long-short factor
  portfolios = thousands of stock legs). **ACCEPT as a prior**: the sign of predictability at your
  horizon differs between single names (reversal) and baskets (continuation).

### A4. Short-horizon reversal — the effect that actually lives in your window
- **Signal:** rank on prior 1-week or 1-month return; **buy losers, sell winners.** (Jegadeesh 1990,
  Lehmann 1990.) Formation 5 to 21 trading days; **holding 5 to 21 trading days.** This sits squarely
  inside 2 days–8 weeks.
- **The classic negative:** Avramov, Chordia & Goyal (2006) — reversal is concentrated in **small,
  illiquid, high-turnover stocks**, and contrarian profits are **smaller than likely transaction costs**.
  https://www.efmaefm.org/0efmameetings/efma%20annual%20meetings/2011-Braga/papers/0259.pdf
- **The modern decomposition — Dai, Medhat, Novy-Marx & Rizova (Jan 2023), "Reversals and the Returns
  to Liquidity Provision."** Verified from the primary PDF. **Jan 1973 – Dec 2021**, extreme quintiles,
  **NYSE breaks, value-weighted, monthly rebalance.** Table 2 Panel A, average monthly excess returns:

  | REV | PEAD | IMOM | IRR | IRRX |
  |---|---|---|---|---|
  | **0.31% [t=1.68]** | 0.53% [t=5.45] | 0.68% [t=3.57] | 0.74% [t=5.40] | **1.08% [t=9.35]** |

  Definitions, exactly codeable:
  - **REV** = sort on prior month's raw return, buy losers / short winners. **Value-weighted, this is
    NOT statistically significant (t = 1.68).** That is a well-sourced negative on naive reversal.
  - **IRR** = sort on prior month's return *in excess of the value-weighted return of the firm's
    Fama-French 49 industry*. 0.74%/mo, t = 5.40.
  - **IRRX** = IRR further adjusted by subtracting the **3-day CAR around the firm's most recent
    earnings announcement**. 1.08%/mo, t = 9.35.
  - **IMOM** = long/short the top/bottom **ten** FF49 industries on prior month's VW industry return.
    0.68%/mo, t = 3.57 — this is Moskowitz–Grinblatt short-horizon industry momentum, and it is
    *positive over 1973–2021 in this specification*, which sits in tension with the "dead after 2000"
    claim in A2. **Neither claim is settled; the DMNR sample pools 49 years and does not subperiod it.**
  - Panel B: REV regressed on IRRX/PEAD/IMOM gives **adj. R² = 87%**, α = 0.13% (t=1.73). i.e.
    **naive reversal is mechanically long liquidity-provision reversal but short PEAD and short industry
    momentum, and those two short legs eat almost all of its return.** This is the cleanest explanation
    in the literature for why simple mean-reversion backtests disappoint.
  ⚠️ **Flag per rule 6: t = 9.35 on IRRX.** It is a 588-month value-weighted series so it is not
  facially impossible, but a t of 9 in a published anomaly is the profile that shrinks hardest. Note
  also that 3 of 4 authors are **Dimensional Fund Advisors employees** and Novy-Marx consults for DFA.
  - **Horizon detail from their Figure 1:** reversal is **complete within ~2 weeks for high-turnover
    stocks** but keeps growing for weeks longer in low-turnover stocks; higher volatility → faster and
    initially stronger reversal. Bin width: daily cumulative from formation.
- **Mechanism (stated, and it is the best one in this report after the variance premium):** you are paid
  an **inventory-risk / liquidity-provision** premium for absorbing uninformed order-flow imbalance.
  Volatility ∝ inventory risk; turnover ∝ inverse inventory duration. Nagel (2012) shows reversal
  profitability tracks **aggregate market volatility (VIX)** — a usable conditioning variable.
- **THE AUTHORS' OWN VERDICT ON TRADEABILITY, verbatim:** *"Actively exploiting these reversals is
  certainly less profitable, as even liquidity providers incur transaction costs, but investors can
  benefit from incorporating short-run reversals into their rebalancing process."* They pitch it as an
  **execution/rebalancing screen for a diversified manager**, not a standalone strategy. They report
  **no net-of-cost returns.**
- **Retail-options verdict: REJECT for options; interesting for shares only.** The horizon matches your
  window and the mechanism is sound, but (a) the authors themselves decline to claim it is actively
  tradeable, (b) it is a 100+ name value-weighted quintile spread — a 5-name retail version has
  idiosyncratic variance many multiples of the ~1%/month signal, (c) the signal is *strongest* in
  high-volatility, low-turnover names, which have the widest option spreads. **The one usable takeaway
  is negative and valuable: do not trade naive 1-month reversal (t=1.68 VW), and if you build any
  mean-reversion signal, neutralize it against industry momentum and PEAD or you are unknowingly short
  both.**

---

## SECTION B — Volatility risk premium and options-native edges

**This is the only focus area where the edge is natively an option, the mechanism is a genuine risk
premium, and the horizon (21–45 days) matches the swing window. It is also the area with the most
severe measurement problems. Both are true.**

### B0. How big is the VRP, really, and over what horizon?
| Source | Measure | Horizon | Sample | Gap |
|---|---|---|---|---|
| Bollerslev–Tauchen–Zhou (2009, RFS 22:11) | IV vs **past-month** RV | 30d | 1990–2007 | ~20.0% IV vs ~13.4% RV → **6.6 vol pts** |
| Bondarenko / Cboe (2019) | VIX vs **subsequent** SPX RV | 30d | 1990–2018 | 19.3% vs 15.1% → **4.2 vol pts** |
| Broadie–Chernov–Johannes (2009) | ATM IV vs RV | 30d | 1987–2005 | 17% vs 15% → **2 vol pts** |
| Dubinsky et al. (2019) | earnings-day implied vs realized | 1 day | 2000–2015 | 8.22% vs 7.42% → **0.8 vol pts (~11% rel.)** |

⚠️ **A coding trap worth stating loudly:** BTZ define **VRP_t ≡ IV_t − RV over the PAST month [t−1,t]**,
not IV minus *subsequent* RV. It is a contemporaneously observable proxy. If you code IV_t − RV_{t+1}
you have built a different, non-tradable-at-t variable. Most secondary citations get this wrong.
The BCJ-vs-Bondarenko gap (2 vs 4.2 points) is mostly measurement convention (ATM IV vs VIX, which
includes skew) — **do not read it as a time trend.**
BTZ: https://public.econ.duke.edu/~boller/Published_Papers/rfs_09.pdf
Cboe/Bondarenko: https://cdn.cboe.com/resources/education/research_publications/PutWriteCBOE19_v14_by_Prof_Oleg_Bondarenko_as_of_June_14.pdf

### B1. Naked put-writing (Cboe PUT index) — REJECT, decayed to zero edge
Bondarenko (2019), the **index sponsor's own study**:
- **Jun 1986 – 2018:** PUT CAGR **9.54%** vs SPX 9.80%; SD **9.95%** vs 14.93%; **Sharpe 0.65 vs 0.49**;
  **max DD −32.7%** vs −50.9%; longest drawdown **40 months**. Avg annual gross premium collected 22.1%.
- **2006–2018 subsample:** PUT Sharpe **0.50**, WPUT 0.40, **SPX 0.51**. **The put-write Sharpe advantage
  is exactly zero in the modern subsample.** This is the best-documented post-publication decay result
  in this entire report, and it comes from the party with every incentive to report the opposite.
- **PPUT** (protective put): Sharpe **0.33**, max DD **−38.9%** — *worse* drawdown than plain put-writing.
  Consistent with Israelov, "Pathetic Protection" (JAI Winter 2019): protective puts are an inefficient
  way to cut drawdown vs simply holding less equity.
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2934538

### B2. The statistical-significance problem — BCJ, restated because it governs everything
See the header. **Deep-OTM put returns, put-spread returns, and (in the BCJ extension) several other
short-vol payoffs are statistically indistinguishable from a Black-Scholes null across ~200 monthly
observations.** The (5%,95%) band on the mean 6%-OTM put return is **−65% to +28%**. Only the
**market-neutral** portfolios (ATM straddle −15.7%/mo, crash-neutral straddle −9.9%/mo, both p≈0–1%)
are significant. **Practical rule: if your short-vol structure has meaningful net delta, you cannot
prove it works and neither could 18 years of data.**

### B3. Israelov & Nielsen — the decomposition that should reframe how you think about premium selling
**"Covered Calls Uncovered," FAJ 71(6), 2015.** BXM-mimicking backtest, **25 Mar 1996 – 31 Dec 2014**,
annualized:

| | Covered call | Passive equity | **Short vol** | Equity timing |
|---|---|---|---|---|
| Excess return | 5.9% | 3.5% | **1.9%** | 0.5% |
| Volatility | 11.4% | 8.5% | **1.9%** | 4.8% |
| Sharpe | 0.52 | 0.41 | **0.98** | 0.10 |
| Risk contribution | 100% | 67% | **7%** | 26% |
| Beta to S&P | 0.62 | 0.52 | **0.03** | 0.07 |
| Alpha to S&P | 1.7% | — | **1.7%** | −0.0% |

**Of the 5.9% covered-call excess return: 59% is equity beta, 32% is true vol premium, 8% is
uncompensated equity-timing (t=0.4 — literally zero return for 26% of the risk). Only 7% of the RISK
is short-vol risk.** Delta-hedging away the timing leg lifted Sharpe **0.37 → 0.52** and cut vol
11.4% → 9.2%.
**Implication: an unhedged covered call, short put, or naked strangle is ~90% a levered equity bet
wearing a vol-premium costume.** To actually harvest the premium you must delta-hedge — which for a
small retail account means frequent underlying trades and more slippage.
https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/Covered-Calls-Uncovered.pdf

### B4. VRP TIMING — and the sign is the opposite of retail folk wisdom ⭐
**This is the single most actionable finding in the report.**

**First, what BTZ does and does not say.** BTZ's VRP predicts **EQUITY returns**, not vol-strategy
returns. Table 2, adjusted R² and Hodrick(1992) t-stats on S&P 500 excess returns, 1990–2007:

| Horizon | 1m | **3m** | 6m | 9m | 12m | 15m | 18m+ |
|---|---|---|---|---|---|---|---|
| Adj R² | 1.07% | **6.82%** | 5.42% | 2.30% | 1.23% | 1.00% | ~0 |
| t-stat | 1.76 | **2.86** | 2.15 | 1.36 | 1.00 | 0.94 | ~0 |

Peaks at the **quarterly** horizon, dead by 12 months, **insignificant at 1 month (t=1.76)**. It is a
stock-market timing signal that happens to use option data. **It says nothing about when to sell
straddles**, and citing it as a short-vol timing signal is a miscitation.

**Second, the actual vol-timing paper: Yang (2024), "Volatility-Managed Volatility Trading."**
Signal: portfolio weight **f_t = −c / vol_t**. Predictive regressions of next-month variance-swap
return, **Jan 1990 – Nov 2023**, Newey-West(3):

| Predictor X_t | β | t | In-sample R² | **OOS R²** |
|---|---|---|---|---|
| Realized vol | 9.82 | 2.00 | 1.4% | **3.26%** |
| VIX | 9.79 | **1.42** | 0.86% | **2.63%** |
| GARCH(1,1) | 16.63 | 2.47 | 2.21% | **4.61%** |

**The sign is everything.** Positive β means *higher volatility today → higher next-month
variance-swap return → LOWER realized VRP for the seller.* **The correct rule is to scale DOWN short
vol after volatility spikes, not up.** This directly contradicts the near-universal retail heuristic
"sell premium when IV rank is high," and it independently corroborates **Bakshi & Kapadia (2003, RFS,
SPX 1988–1995)**, who found delta-hedged option underperformance is **greater at higher volatility**
(avg loss ≈ $0.43 on ATM calls; ~72% of non-deep-ITM calls have negative delta-hedged gains).
Note **VIX alone is the weakest predictor and is insignificant (t=1.42)**; GARCH is strongest.
Sharpe improvements: variance swaps 1.54 → 1.75; VIX futures 0.61 → 0.78; **straddles with margin
0.51 → 0.62.**
⚠️ **Flag: the 1.54 constant-weight variance-swap Sharpe is not a tradable number** — synthetic swap
rates from option strips at mid-quotes, no bid-ask, no margin. **Use 0.51 (straddles, margin-adjusted)
as the realistic anchor.** The authors concede the analysis is largely ex-post: *"ex-post findings do
not automatically suggest a straightforward method to enhance ex-ante timing strategies."*
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4761614

### B5. VIX term-structure / basis roll — best-documented cost accounting, but pre-Volmageddon
**Simon & Campasano (2014, J. Derivatives 21:3).**
**Signal, exactly codeable:** daily roll = **(front VIX future − spot VIX) / business days to
settlement**. **Short** VIX futures when daily roll **≥ 0.10** vol pts/day; **exit** below **0.05**;
hedge with mini-S&P futures.
**Sample Jan 2007 – Dec 2011. Holding period: 62 short trades, average life 6.4 days** — squarely in
the swing window.
**Results, AFTER costs (bid-ask ~0.06 VIX points, full spread paid, plus brokerage — honest accounting):**
mean P&L **$792/contract, p = 0.003**, win:loss ≈ 2:1, **bottom decile −$1,045**, **Sortino 1.26**
(hedged) vs 0.88 unhedged (unhedged mean $861 but bottom decile −$1,973). **Roll P&L was $831 — the
roll accounts for essentially all the profit.** Basis in contango 78%/91% of the time (front/second).
They report **Sortino, not Sharpe**, explicitly "owing to the frequently non-normal P&L distributions."
Predictive regressions explain only ~10% of VIX futures return variation.
**Mechanism:** hedging demand steepens the curve beyond rational expectations.
**⚠️ Post-publication: 2018 and 2024 are both out of sample and both were catastrophic for this trade.
Treat the published Sortino as a pre-Volmageddon number.**
https://www.efmaefm.org/0efmameetings/efma%20annual%20meetings/2013-Reading/papers/VIX%20paper_EFMA.pdf

### B6. The tails — why win rate is the wrong metric here
- **5 Feb 2018:** VIX 17.31 → 37.32 (+116%) in one session; **XIV lost ~96% and was terminated.**
  Mechanism (Augustin, Cheng & Van den Bergen, FAJ 2021): a rebalancing feedback loop — falling AUM
  forced VIX-futures *buying*, pushing futures higher, shrinking AUM further.
  https://www.bis.org/publ/qtrpdf/r_qt1803t.htm
- **5 Aug 2024:** VIX **+180% to ~65** pre-market, largest one-day spike on record.
  https://www.bis.org/publ/bisbull95.htm
- Israelov & Nielsen's covered-call backtest: **skew −1.7, kurtosis 8.7, upside beta 0.46 vs downside
  beta 0.86.**
- **The asymmetry that matters:** PUT's −32.7% max drawdown is a *deleveraged, cash-secured* number.
  **Levered short vol went to zero twice in six years.** A short-vol program can win 85–90% of months
  and have negative expectancy; conditional accuracy is not expectancy (rule 3).

### B7. Dispersion / correlation risk — well-documented NEGATIVE for retail
**Driessen, Maenhout & Vilkov (2009, JF 64:3), "The Price of Correlation Risk."**
S&P 100 + all components, **Jan 1996 – Dec 2003, 30-calendar-day horizon.**
- Average **implied correlation 46.7% vs realized 28.7% — an 18 pp gap**, the largest single premium
  in this review. Implied correlation explains **35%** of variation in future realized correlation.
- **Individual variance risk is NOT priced in their sample.** The *entire* index variance premium is
  attributable to the correlation risk premium. Mechanism: index options are expensive because
  correlation spikes in crashes; single-name options are roughly fair.
- Index put returns −7%/mo (ITM) to −39%/mo (OTM); delta-0.4 put −25%/mo. Model attributes −27%, of
  which **−16% is correlation risk premium and −11% is the plain equity premium.**
- **The published abstract's own verdict:** the correlation risk premium **"cannot be exploited with
  realistic trading frictions, providing a limits to arbitrage interpretation."**
  https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2009.01467.x
- **Retail feasibility: effectively zero.** A faithful trade is 200+ legs plus continuous delta-hedging
  on 101 underlyings. A 10-name proxy re-introduces enormous basis risk to the exact thing you are
  trying to isolate — and since DMV find single-name variance risk is *not* priced, you pay spread on
  the long leg for nothing. **REJECT.**

### B8. ⚠️⚠️ THE COST SECTION THAT INVALIDATES MOST PUBLISHED OPTION RESULTS
**Read this before believing any option backtest, including your own.**

**(a) Santa-Clara & Saretto (2009, J. Financial Markets 12:391–417).** SPX 1985–2002 (returns),
OptionMetrics 1996–2002 (spreads). Headline **mid-price** Sharpes reach **1.69** for a near-maturity
short strangle; Coval–Shumway's zero-beta short straddle shows 3.15%/week, **SR 1.19**. Then costs:
- Dollar-volume-weighted **round-trip** bid-ask: **3.9% (calls), 5.1% (puts)** of midpoint.
- Near-maturity ATM **~5.5%** round trip. Near-maturity 5% OTM call **11.8%**; 5% OTM put **9.2%**.
  Far-maturity equivalents 4.3% / 4.5%.
- Impact: short-put mean returns fall **4.0–6.9%**. Near-maturity 10% OTM put → **Sharpe −0.153**.
  Near-maturity straddle → **Sharpe −0.182**. **Far-maturity straddle AND strangle Sharpes turn negative.**
- **Margin** "forces investors out of trades precisely when they are losing money," caps notional, and
  forces extra round trips.
  https://conference.nber.org/confer/2005/bfs05/saretto.pdf

**(b) Goyenko & Zhang (2019), "Option Returns: Closing Prices are not What You Pay." THE MOST DAMAGING
FINDING IN THIS REPORT.** Delta-hedged returns computed from **4pm OptionMetrics mid-quotes are ~60 bps
per DAY higher** than the same returns computed from **1pm** mid-quotes — in **both** 2004–2010 and
2011–2017, and the gap widens with earlier quotes. The bias is a **gamma premium** market makers embed
in closing quotes to compensate for overnight inventory risk. Using earlier-hour quotes makes returns
*"similarly negative"* across all contracts, **erasing the index-vs-equity-option and
trading-vs-non-trading return puzzles.**
**60 bps/day is roughly 150% annualized.** Bakshi–Kapadia's delta-hedged loss, and much of the
delta-hedged VRP literature built on OptionMetrics closing mids, may be **substantially a marking
artifact rather than a harvestable premium.**
> **This is the same failure mode that killed your iron-condor result in `FINDINGS.md`** — there a
> Black-Scholes-with-linear-skew model inflated the credit and *was* the entire edge. Here the
> literature has an analogous, systematic, and much less well-known version. **Any backtest built on
> end-of-day option mids inherits this bias in full.**
https://ruslangoyenko.com/wp-content/uploads/2019/11/Option-Returns-Nov-18-2019-FINAL.pdf

**(c) The one optimistic counterweight:** Muravyev & Pearson (2020, RFS) — effective spreads are
**29.6% of the quoted half-spread for execution-timing traders** (58.4% for all traders). This is real
and it is your lever: **patient limit orders are worth ~2–3× the entire edge on most of these trades.**

---

## SECTION C — Post-earnings-announcement drift and the earnings announcement premium

**Headline: classic SUE-based PEAD is dead in every stock you can trade options on. The only earnings
edges with a pulse are (a) price-based drift, too small for options, and (b) an options-native earnings
jump-risk premium that is real but thin.**

### C1. Classic SUE-based PEAD — REJECT (well-sourced negative)
- **Signal:** SUE = (actual quarterly EPS − seasonal-random-walk-with-drift expectation) / SD of past
  forecast errors over prior 20 quarters. Decile sort, long D10 / short D1.
- **Horizon:** hold **60 trading days (~3 months)** from day +2. Bin width: deciles, equal-weighted in
  the original work. Foster, Olsen & Shevlin (1984) reported ~25% annualized abnormal, **gross of costs**,
  on a universe including tiny NYSE/AMEX names. Bernard & Thomas (1989, JAR 27, 1–36): the D10−D1 SUE
  spread was positive in **41 of 48 quarters, 1974–1985**.
- **Mechanism (the best-stated in the earnings literature):** investors price seasonally-differenced
  quarterly earnings as a random walk when autocorrelations are actually positive at lags 1–3 and
  negative at lag 4. This generated the falsifiable prediction that drift concentrates on the *next
  three* announcement dates — confirmed by Bernard–Thomas.
- **THE KILL SHOT — Martineau (2022), "Rest in Peace Post-Earnings Announcement Drift,"
  *Critical Finance Review* 11(3-4), 613–646.** Sample **1984–2019**, I/B/E/S, 312,462 announcements.
  Dependent variable **BHAR[2,60]** — exactly the classic window. Regressed on analyst-surprise decile
  rank, **all-but-microcap** stocks:

  | Period | Coefficient | N |
  |---|---|---|
  | 1984–1990 | 0.003*** | 21,870 |
  | 1991–1995 | 0.003*** | 25,793 |
  | 1996–2000 | 0.001 (ns) | 36,430 |
  | 2001–2005 | 0.002** | 34,217 |
  | 2006–2010 | **−0.001 (ns)** | 31,108 |
  | 2011–2015 | **0.000** | 31,424 |
  | 2016–2019 | **−0.002**\** | 25,479 |

  R² is 0.000–0.004 throughout — even in the good years the signal explained almost nothing.
  The return didn't get arbitraged away in the drift window; **it got pulled forward into the event**:
  announcement-window **BHAR[0,1] rose from 0.002 (1984–1990) to 0.012 (2016–2019)** for non-microcaps —
  prices are now **~6× more responsive on the announcement date**. Verdict: **PEAD is non-existent for
  large stocks since ~2006** and gone for microcaps since ~2016.
  ⚠️ Table values verified against a full-text mirror, not the journal PDF.
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607
- **Corroboration:** Chordia, Subrahmanyam & Tong (2014, JAE) — anomaly profits attenuate over time,
  **concentrated in liquid NYSE/AMEX stocks**, attributed to hedge-fund AUM, short interest, turnover.
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2029057
- **Retail-options verdict: REJECT.** The universe where it lived (microcaps) has no tradeable option
  chains; the universe with chains has had no drift for two decades.

### C2. Price-based drift (Abr) — the one survivor, but not options-expressible
- **Signal:** cumulative abnormal return over **[−1, +1]** around the most recent earnings announcement,
  minus the value-weighted market. Decile sort, **NYSE breakpoints, value-weighted.**
- **Hou, Xue & Zhang (2020), Table 3 Panel A, Jan 1967 – Dec 2016, monthly, NYSE-VW, gross of costs:**

  | Signal | 1-mo hold | 6-mo hold | 12-mo hold |
  |---|---|---|---|
  | **Sue** (earnings surprise) | 0.46%/mo, t=3.48 | 0.16%, **t=1.44** | 0.08%, **t=0.73** |
  | **Abr** (CAR around announcement) | **0.70%/mo, t=5.45** | **0.33%, t=3.41** | **0.23%, t=2.99** |
  | **Re** (analyst revisions) | 0.75%, t=3.18 | 0.47%, t=2.24 | 0.24%, t=1.30 |

  Equal-weighted all-stock Sue is 1.34% / 0.64% / 0.24% (t = 10.33 / 5.3 / 2.15) — a **3–8× inflation
  from microcaps alone. That gap is the anomaly.** Abr clears even the HXZ multiple-testing hurdle of 2.78.
- **Tension to resolve:** HXZ's sample ends 2016 and pools 50 years; Martineau's final window (2016–2019)
  is negative. ⚠️ **Abr's post-2016 status is UNVERIFIED — no primary OOS test was located. This is the
  single most decision-relevant open question in this section.** Chen–Zimmermann's Open Source Asset
  Pricing dataset (https://www.openassetpricing.com/data/) would settle it directly and is downloadable.
- **Costs:** ⚠️ HXZ report **raw gross returns and net nothing.** Monthly-rebalanced decile long/short
  ≈ 200%/month two-sided turnover; at a generous 15 bp round-trip in large caps ≈ 30 bp/month against
  70 bp gross. A few-position retail version captures only a fraction of a decile spread.
- **Retail-options verdict: REJECT for options.** A 0.7%/month decile spread is a fraction of a single
  option round-trip. Shares or nothing.

### C3. Earnings announcement premium — REJECT (likely dead post-2004)
- **Lamont & Frazzini (2007), NBER WP 13090.** Verified from the NBER PDF.
  **Signal (exactly codeable):** on the last trading day of month t−1, go long every stock *expected* to
  announce in month t (predicted from last year's announcement month, restricted to firms with exactly 4
  announcements in the prior 12 months — 93% accurate), short every stock not expected to announce.
  **Hold one month, rebalance monthly.**
  **1973–2004, value-weighted, monthly bins, gross of costs:** **61 bp/month (~7%/yr), t > 5,
  annualized Sharpe 0.94** (vs 0.70 for momentum over the same period). Fiscal-year-end variant 72 bp/mo;
  subperiods 40–92 bp/mo, all reject zero. **Strong in large caps.** Their own caveat: *"before considering
  trading costs."* They also note a substantial **pre-event run-up plus post-announcement drift**, so a
  20-day window is more informative than a 3-day window.
  **Mechanism:** attention-driven retail buying — highest imputed small-investor buying in high-premium
  stocks, concentrated where past announcement-period volume was high.
  https://www.nber.org/system/files/working_papers/w13090/w13090.pdf
- **Post-publication:** Heitz, Narayanamoorthy & Zekhnini, "The Disappearing Earnings Announcement
  Premium" — the premium **has disappeared in the US in recent years**, attributed to the 2004 Form 8-K
  Disclosure Regulation shifting it from earnings windows to 8-K filing windows. It remains robust
  internationally (Barber et al., JFE 2013). ⚠️ **Magnitudes and exact break date UNVERIFIED (SSRN 403).**
  https://www.ssrn.com/abstract=3296537
- **Verdict: REJECT** on the published US numbers.

### C4. Earnings straddles — the two results retail lore conflates
These are about **different windows** and both are real.

**(a) BUY the straddle INTO earnings, close BEFORE the print — positive.**
Xing & Zhang, "Anticipating Uncertainty: Straddles around Earnings Announcements," *JFQA* 53(6), 2018.
Sample **1996–2010**, OptionMetrics, individual stocks, delta-neutral ATM straddles.
- Unconditionally, holding straddles loses: **−0.19%/day, −2.08%/week, −16.21%/month.**
  ⚠️ **Reported t = −42.35. Per rule 6, this is not a credible time-series t-stat** — it is a pooled
  panel with heavily overlapping, cross-correlated observations. The *sign* is reliable; the *t* is not.
  Read every t-stat in this literature the same way.
- Straddles opened **5, 3, or 1 trading days before** the scheduled announcement and closed **on the
  announcement date or one day after** earn **+0.31% to +2.30%**; the 1-day-before version is **+2.3%**.
- **Mechanism:** investors underestimate the uncertainty build-up ahead of the event.
- **The catch:** the effect is strongest in **smaller firms, low analyst coverage, high past jump
  frequency, and WIDE BID-ASK SPREADS** — i.e. precisely the names where you cannot execute. A secondary
  source reports the result survives half-quoted-spread frictions only for 4–10 DTE options and falls
  when restricted to tighter-spread names; ⚠️ **that netting is UNVERIFIED against primary text.**
  Post-2010 OOS is **unverified**.
  https://www.ruf.rice.edu/~yxing/straddle_201305_03.pdf

**(b) HOLD the straddle THROUGH earnings — loses ~8%. This is the real "IV crush," and it is smaller
than lore claims.**
Dubinsky, Johannes, Kaeck & Seeger, "Option Pricing of Earnings Announcement Risks," *RFS* 32(2), 2019,
646–687. Verified from the publisher PDF. Sample **2000–2015**, actively traded firms.
- Average option-implied earnings-day volatility **8.22%** vs realized announcement-day volatility
  **7.42%** — a premium of **80 bp of vol**, i.e. **~11% relative overpricing**, *not* the 2× that retail
  content implies.
- ATM straddles **opened before the EAD and closed the next day: average −8%, median −10%**,
  bootstrap-significant. ⚠️ **The paper does not net bid–ask spreads on this.**
- **Codeable estimator, straight from the paper:** σ(t,T) = √(σ² + (σ_j^Q)²/T), where σ_j^Q is the
  earnings jump vol backed out of the **downward-sloping pre-announcement IV term structure.** Their
  worked example: σ=25%, jump vol 7.3% → 2-week IV ≈ 44% but 6-week IV only 32%.
- **Mechanism (and it is a risk premium, not free money):** earnings jump vol correlates ~60% with
  equity beta and premiums concentrate in bellwethers — you are paid to absorb **non-diversifiable jump
  risk**. Consistent with Barth & So (TAR 89(5), 2014).
  https://research.vu.nl/ws/portalfiles/portal/108247883/Option_Pricing_of_Earnings_Announcement_Risks.pdf

**Cost anchor for both:** Muravyev & Pearson (RFS 33(11), 2020) — effective spreads are **29.6% of the
quoted half-spread for execution-timing traders** (58.4% for all traders). So assume **~0.3–0.6× the
quoted half-spread per leg** for a patient limit-order retail trader. A short straddle is 4 legs round
trip; on a liquid single-name weekly with a 2–3% quoted half-spread relative to straddle price that is
**~3–7% of straddle value against an 8–10% gross edge. The margin is real but thin and is entirely
consumed by sloppy execution.**

**Retail-options verdict on C4:** **(a) is the only structure in this entire report whose horizon
(2–5 days) natively matches your window AND whose natural expression is an option.** Rank it accordingly,
with the caveat that its published concentration in wide-spread names is a direct threat to it.
**(b) is tradeable only defined-risk** (iron condor / iron butterfly), sized on the assumption that you
will occasionally lose several multiples of the credit, and conditioned on the DJKS σ_j^Q term-structure
estimator versus that firm's own historical announcement-move distribution — **not on raw IV rank.**

---

## SECTION D — Time-series momentum, trend, and regime conditioning

**Verdict up front: the 2-day-to-8-week directional trend hypothesis on SPY/QQQ/sector SPDRs is a
WELL-SOURCED NEGATIVE. Three independent lines of evidence converge on it.**

### D1. Moskowitz-Ooi-Pedersen (2012, JFE 104, 228–250) — and its two killers
**Signal (their Eq. 5), exactly codeable:**
`r_TSMOM[t,t+1] = sign(r[t−12,t]) × (40% / σ[t−1]) × r[t,t+1]`
where σ is an EWMA of squared daily returns, **center of mass 60 days**, ×261 to annualize, lagged to t−1.
**Horizon: 12-month lookback, 1-MONTH holding period** (k=12, h=1), overlapping portfolios averaged
Jegadeesh-Titman style. **Universe: 58 futures** (24 commodities, 12 cross-currency pairs, 9 developed
equity index futures, 13 government bond futures). Data 1965–2009; headline factor uses **1985–2009**.
**Performance:** ~12% annualized vol; **Sharpe > 1** ("roughly 2.5× the Sharpe of the equity market");
alpha **1.58%/month (t = 7.99)** vs MSCI World/SMB/HML/UMD. All 58 contracts positive Sharpe, 52
significant at 5%. 1966–1985 pseudo-OOS Sharpe 1.1.
⚠️ **COSTS: NOT ADDRESSED AT ALL. Their Figure 2 is literally labeled "Gross sharpe ratio."**
⚠️ It loads **0.28 on UMD (t=6.78)** and **0.66 on MOM-Everywhere (t=9.74)** — **not orthogonal to
cross-sectional momentum.**
https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf

**KILLER 1 — Huang, Li, Wang & Zhou (2020, JFE 135, 774–794), "Time series momentum: Is it there?"**
Same data, 55 assets, extended to **1985:01–2015:12**:
- **Asset-by-asset: only 8 of 55 assets have a significant slope at 10%, only 3 at 5%.** 47 of 55 have
  |t| < 1.65. **Average in-sample R² = 0.39%.** 31% of assets have *negative* slopes.
- **Out-of-sample (2000–2015, Campbell-Thompson R²_OS): average −0.67%, only 3 of 55 significant.**
- **The pooled t = 4.34 — but bootstrapped 5% critical values are 4.83 (nonparametric) and 12.53
  (parametric). Both EXCEED 4.34. The pooled t-stat is not evidence.** (Over-rejection sources:
  heterogeneous means bias the pooled slope without fixed effects (Hjalmarsson 2010); persistent
  predictor → Stambaugh size distortion; heterogeneous vol + vol-scaling worsens it.)
- **The placebo that settles it:** a "TSH" strategy that buys an asset if its *historical sample mean*
  is positive — **requiring no predictability whatsoever** — performs **virtually identically to TSMOM**.
  The alpha differential is indistinguishable from zero. Lewellen's predictive slope, which should be
  1.0 under true predictability, is **0.08**.
- Both TSMOM and the placebo earn from the **long leg**; short legs are insignificant.
https://ink.library.smu.edu.sg/context/lkcsb_research/article/7520/viewcontent/Time_series_momentum_JFE_sv.pdf

**KILLER 2 — Goyal & Jegadeesh (2018, RFS 31, 1784–1824).** TS strategies take a **time-varying net long
position** while CS strategies are zero-net. The TS-vs-CS difference for individual stocks is *"mainly
due to time-varying long positions that the TS strategy takes in the aggregate market and, consequently,
do not have any implications for the behavior of individual asset prices."* Across international asset
classes, scaled **CS strategies significantly OUTPERFORM** similarly scaled TS strategies.
⚠️ **Abstract-level verification only; full text not obtained.**

**Combined: TSMOM ≈ (cross-sectional momentum) + (a market-timed net long) + (most futures have positive
unconditional drift). None of those three is "trend."**

### D2. Your window sits in the REVERSAL zone — and every momentum paper says so procedurally
The sign map for **US single stocks**: **reversal at 1 week–1 month** (Jegadeesh 1990; Lehmann 1990),
**momentum at 3–12 months**, reversal at 3–5 years.

**The strongest confirmation is procedural, from Daniel & Moskowitz (2016, JFE 122, 221–247):** they form
momentum on **t−12 to t−2 with a one-month gap explicitly "to avoid the short-term reversals shown by
Jegadeesh (1990) and Lehmann (1990)."** **Every credible momentum paper deliberately skips exactly your
window. That is not an accident.** https://www.kentdaniel.net/papers/published/jfe_16.pdf

At the **index** level (where reversal is weaker), **MOP's own Table 2 Panel C — equity index futures
only — gives an alpha t-stat of 1.05 for a 1-month lookback / 1-month hold, versus 3.77 at the 12-month
lookback. The short lookback is the weakest cell in their own equity panel.**

### D3. ⭐ Fast trend is dead even at ZERO cost — the decisive modern evidence
**Kurth, Eisler, Rej & Bouchaud, "Is Trend Still Your Friend?" (arXiv 2607.01550, July 2026).**
~100 liquid futures, 1995–2025:

| Signal horizon | Pre-2009 Sharpe | Post-2008 Sharpe |
|---|---|---|
| **5 days** | 0.84 | **0.12** |
| 50 days | 0.70 | 0.40 |

**This holds with ZERO costs and ZERO execution lag — it is signal death, not cost death.** Proposed
mechanism: trend was sustained by a self-reinforcing price-impact loop; post-2008 HFT market-making
broke it on small-tick contracts. **Equity indices and currencies lost trend entirely; yields and
commodities retained it. Your universe is on the wrong side of that split.**
⚠️ **PREPRINT, not peer-reviewed. Weight accordingly — but note it agrees with D1 and D2.**

### D4. Post-publication decay, documented by the strategy's own industry
From **AQR's "Trend Following in Focus" (Sept 2018)**, SG Trend Index (live, net-of-fee, 10 largest CTAs):
- **Jan 2000 – Mar 2009: +9.2%/yr. Apr 2009 – Jun 2018: +1.0%/yr.** (MOP was published **December 2011**.)
- Annual: 2009 −4.8%, 2010 +13.1%, 2011 −7.9%, 2012 −3.5%, 2013 +2.7%, 2014 +19.7%, 2015 0.0%,
  2016 −6.1%, 2017 +2.2%, 2018H1 −5.3%.
- **SG Trend CAGR since Jan 2000 inception: 4.90%** through Jun 2025; **trailing 12m to Jun 2025:
  −15.05%**; YTD 2026 as of Aug 6: +6.40%.
- AQR's counter-argument: opportunity set (few large moves), not crowding — industry AUM fell from
  $211B (2008) to $124B (2018) while futures open interest rose. **Fair, but it is a post-hoc explanation
  of an ex-ante 9-to-1 decline.** These are net-of-2/20, which overstates decay vs a gross backtest — but
  Bouchaud et al.'s **gross, cost-free** result points the same way.

### D5. Faber's 10-month SMA — real, but mislabeled
**Faber (2007/2013), "A Quantitative Approach to Tactical Asset Allocation."** Rule: **monthly close
only**; long if close > 10-month SMA, else cash. S&P 500 total return, **1901–2012**:

| | S&P 500 | Timing |
|---|---|---|
| CAGR | 9.32% | 10.18% |
| Volatility | 17.87% | **11.97%** |
| Sharpe | 0.32 | **0.55** |
| MaxDD | −83.46% | **−50.29%** |

**The honest verdict, from Faber's own text: ARITHMETIC mean returns are 11.26% (B&H) vs 11.22%
(timing) — statistically identical. The entire CAGR gain is variance-drag reduction. The SMA rule
predicts VOLATILITY, not returns.** It is a risk-reduction device wearing a return-prediction costume.
Turnover < 1 round trip/year, invested ~70% of the time; **taxes, commissions, slippage excluded.**
https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf
- **Zakamulin's critique:** "Revisiting the Profitability of Market Timing with Moving Averages" (*IRF*
  2018) shows Glabadanidis's spectacular MA results came from **look-ahead bias**; corrected, MA
  performance is *"indistinguishable from the performance of the buy-and-hold strategy."* His
  "Real-Life Performance..." (*JAM* 2014) does rolling/expanding-window OOS with realistic costs and
  concludes performance *"is highly overstated, to say the least."* His 1870–2010 study shows **all
  MA-family rules are the same weighted average of past price changes** — so testing 10-month vs 200-day
  vs EMA vs crossover is **testing one hypothesis many times**, and the "optimal" lookback is a data-mined
  parameter. ⚠️ **Exact Sharpe tables UNVERIFIED; qualitative conclusions from his own abstracts.**

### D6. Volatility management — the one survivor, and exactly why it survives
**Moreira & Muir (2017, JF 72, 1611–1644), "Volatility-Managed Portfolios."**
Signal: **f[σ,t] = (c / σ̂²[t−1]) × f[t]**, where σ̂²[t−1] is realized variance of **daily returns in the
prior month**. Market portfolio: **annualized alpha 4.9%, appraisal ratio 0.33, ~25% increase in
buy-and-hold Sharpe.** They claim robustness to realistic costs and leverage constraints, and note it
*"works just as well if implemented through **options** to achieve high embedded leverage."*
https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf

**THE CRITIQUE — Cederburg, O'Doherty, Wang & Yan (2020, JFE 138, 95–117).** 103 strategies:
- **Direct Sharpe comparison: vol-managed wins 53, unmanaged wins 50. A coin flip.** Only **8 of 103**
  show a statistically significant Sharpe improvement, concentrated in momentum-related strategies.
- Spanning regressions do replicate MM (77/103 positive alphas, 23 significant) — **but the implied
  trade requires the ex-post optimal weight on scaled and unscaled legs, which is not knowable in real
  time.**
- **Real-time OOS (training sample, risk aversion 5, leverage cap 5): LOWER certainty-equivalent return
  than the plain portfolio in 72 of 103 cases.** Vol-managed market Sharpe **0.42 vs 0.46** for simply
  holding the market. Cause: **structural instability** in the spanning regressions.
- **⭐ THE NUMBER THAT SETTLES IT:** MM's 4.63% market spanning alpha decomposes into a
  lagged-vol→**RETURN** component of **−0.24%** and a lagged-vol→**CURRENT VOL** component of **+4.87%**.
  **Essentially 100% of the "alpha" is variance forecastability; 0% is return forecastability.**
https://www.lehigh.edu/~xuy219/research/COWY.pdf

**Barroso & Santa-Clara (2015, JFE 116, 111–120):** constant-vol scaling of momentum "virtually
eliminates crashes and nearly doubles the Sharpe ratio."
**Daniel & Moskowitz (2016), verified, 1927–2013:** Jul+Aug 1932 loser decile **+232%** vs winner +32%;
Mar–May 2009 loser **+163%** vs winner +8%. **In bear markets the momentum portfolio's up-beta is −1.51
vs down-beta −0.70 (t of difference 4.5) — momentum is a written call.** Their dynamic strategy scales
WML so conditional vol ∝ conditional Sharpe; **more than doubles** static momentum's Sharpe, reaching
**annualized Sharpe 1.19**. ⚠️ **This is single-stock cross-sectional momentum, NOT index trend. It does
not transfer to SPY.**

### D7. ⭐ The effective-sample-size problem that kills all regime conditioning
⚠️ No primary source on **VIX term-structure regime timing OOS** was obtained. **Treat as a gap, not as
evidence either way.**
**But the structural objection is arithmetic and decisive.** Monthly 1990–2025 = **432 observations**,
which sounds fine. Bear regimes in that window: 1990, 2000–02, 2007–09, 2011, 2018Q4, 2020, 2022 —
**about 6–7 INDEPENDENT episodes.** A rule that "only earns its keep in bear markets" has **n ≈ 6**.
**Daily data does not help: 500 overlapping days inside the 2008 bear market is ONE draw, not 500.**
With n ≈ 6 you cannot distinguish a 0.5 Sharpe from zero, and you certainly cannot *fit a threshold*
(which VIX level? which SMA length?) without burning the sample.
**This explains the asymmetry cleanly:** realized-volatility conditioning works because vol clusters at
*daily* frequency → hundreds of effective observations + a clean mechanism. **Regime/bear-market
conditioning fails because it has a handful.** Cederburg et al.'s diagnosis — *structural instability in
the spanning regressions* — is exactly the symptom you would expect.

### D8. What this means in options
- MOP: **no cost analysis at all.** Faber: costs excluded (but turnover is trivial, so it probably does
  survive in ETFs — it just has no return alpha to begin with). Bouchaud et al.: fast-trend decay is
  present **at zero cost**. Cederburg et al.: vol management fails OOS **before** you charge anything.
- ⚠️ **A trap specific to options:** MOP's TSMOM **already has a long-straddle payoff** — coefficient on
  market-return-squared **1.99 (t=3.88)**, market beta −0.01 (t=−0.17). **Buying options to express trend
  means paying the convexity premium twice.**
- **The only coherent options expression the literature supports** is the one Moreira-Muir explicitly
  endorse: use options for **embedded leverage on a long core, and modulate SIZE, not direction.**
  Concretely: **60–90 DTE, 60–70 delta calls or deep call spreads** (maximizing delta per unit
  theta/vega), with total portfolio delta-notional set **∝ c/σ̂²[t−1]** using trailing 21-day realized
  variance. **Expect drawdown reduction, not return** — and expect the real-time version to deliver
  roughly Cederburg's **0.42 vs 0.46**, i.e. nothing.

### D9. Section D scorecard
| Edge | Signal | Hold | Universe | Published | Costs | OOS verdict |
|---|---|---|---|---|---|---|
| TSMOM (MOP) | sign(12m ret) × 40%/σ | 1 mo | 58 futures | Sharpe >1, α 1.58%/mo t=7.99, 1985–2009 | **None** | **FAILED.** pooled t=4.34 vs boot crit 4.83/12.53; R²_OS −0.67%; = no-predictability placebo. SG Trend 9.2%→1.0%/yr |
| Fast trend (5–50d) | 5–50d price trend | days–wks | ~100 futures | Sharpe 0.84 (5d) pre-2009 | **Zero-cost test** | **FAILED.** 0.84 → 0.12 post-2008 |
| Faber 10m SMA | close > 10m SMA | monthly | S&P 500 | Sharpe 0.32→0.55, 1901–2012 | Excluded (<1 RT/yr) | **REAL BUT MISLABELED** — arith. 11.26 vs 11.22. Vol reduction only |
| Vol-managed market | c/σ̂²[t−1], 21d RV | 1 mo | Any factor | α 4.9%, AR 0.33, +25% Sharpe | Claimed robust | **FAILED REAL-TIME.** 53–50 coin flip; CER worse 72/103; 0.42 vs 0.46 |
| Dynamic momentum (D-M) | scale WML by cond. Sharpe/vol² | 1 mo | Single-stock XSMOM | Sharpe 1.19, 1927–2013 | Not addressed | Strongest survivor — but **cross-sectional single stocks, not index trend** |

---

## SECTION E — Seasonality, factor timing, credit/macro spreads

**Verdict up front: of ~12 candidates, ZERO survive (HLZ t>3.0) × (post-publication OOS) × (net of
retail option cost) at a 2-day-to-8-week horizon. Two are worth keeping as risk-gates, never as alpha.**

### E0. The base-rate argument you must apply before reading any of this
With 250 trading days × 12 months × weekday × week-of-month × holiday-adjacency × FOMC-relative
windows, the space of testable calendar bins is easily **10³–10⁴**. At α=0.05 that produces hundreds of
"discoveries" by chance. Harvey, Liu & Zhu (2016, RFS 29(1)) reviewed 316 published factors and
recommend a hurdle of **t > 3.0**. HXZ: **85% of 447 anomalies fail t > 3.0.**
**Default rule: any calendar effect not clearing t > 3.0 on OUT-OF-SAMPLE data is noise.**
Of the five seasonal effects below, exactly one ever cleared t > 3.0 — and it no longer does.
https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF

### E1. Turn-of-the-month — the strongest calendar effect ever found, and it is now gone
**McConnell & Xu, "Equity Returns at the Turn of the Month," FAJ 64(2), 2008.** Verified from primary text.
**Signal, exactly codeable:** long the CRSP value-weighted index from the close of the **second-to-last**
trading day of month M; hold days **−1, +1, +2, +3**; exit at the close of the **3rd trading day** of
month M+1. **Four trading days.** Window notation (−1, +3).

| Sample | VW TOM daily | VW other-16-days daily | Difference | t |
|---|---|---|---|---|
| 1926–1986 | 0.16% | 0.01% | 0.15% | **7.07** |
| 1987–2005 | — | — | 0.15% | **3.78** |
| 1987–mid-1996 | — | — | 0.17% | 3.63 |
| mid-1996–2005 | — | — | 0.14% | **2.00** |
| Feb 1998–Dec 2005 | — | — | 0.12% | **1.50** |

**The decay is visible inside the original paper.** Effect present in 31 of 35 countries; not concentrated
in small caps, quarter-ends, or January. Magnitude ≈ **55–65 bp per 4-day window**, 12 windows/year.
- **Post-publication OOS:** a 2024-era re-test finds the classic (−1,+3) window has **no statistically
  significant effect in recent US data** and has "largely disappeared over the past decade." A wider
  (−3,+3) window retains ~**5–12 bp** with a consistent downtrend since ~2015; at 5 bp one-way costs,
  TOM strategies *reduce* CAGR vs buy-and-hold in the US. Dzhabarov & Ziemba (2010) found the effect
  shifted **earlier** in the calendar — consistent with front-running.
  ⚠️ The re-test is a practitioner newsletter (QuantSeeker), not peer-reviewed. **Directionally
  corroborated by the in-sample decay above, but the exact 5–12 bp figure is UNVERIFIED.**
- **Mechanism: none survives.** Ogden (1990, JF 45(4)) proposed month-end concentration of
  wages/dividends/coupons. But **McConnell & Xu explicitly test and reject the flow mechanism** — no TOM
  pattern in trading volume or in TrimTabs net equity-fund flows. **A puzzle with no surviving mechanism
  is a puzzle you should not bet on** (rule 5).
- **Cost math:** a 4-day SPY move has σ ≈ 16%/√63 ≈ **2.0%**. A 55 bp edge is ~0.27σ → per-window
  Sharpe ~0.27, ~0.95 annualized *before costs* (consistent with published backtests). In options: a
  30–45 DTE, 0.65-delta SPY call held 4 days bleeds ~2–3% of premium to theta ≈ 5–8 bp of notional,
  plus ~3–8 bp round-trip spread → **options consume 10–15 bp of a 55 bp gross edge.** At today's
  5–12 bp the trade is **strictly negative in options and ~zero in ETF form.**
- **Verdict: REJECT.** Historically real, currently arbitraged.
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=917884

### E2. Halloween / Sell-in-May — REJECT on effective sample size alone
Bouman & Jacobsen (2002, AER 92(5), 1618–1635): 1970–1998, 37 countries, winter (Nov–Apr) > summer
(May–Oct) in 36/37. **The fatal problem is that an ANNUAL effect over 1970–1998 is 29 observations.**
Maberly & Pierce (2004, *Econ Journal Watch*): the US result is driven by **Oct 1987 and Aug 1998
(LTCM)**; dummy them out and US significance vanishes. Jacobsen et al. (JIMF 2021) extend to 300+ years
and 65 markets claiming persistence — but multi-century data with overlapping regimes does not fix a
**2-observations-per-year information rate.**
**Also untradeable by construction:** an 8-week maximum holding period cannot express a 6-month seasonal.
**REJECT.**

### E3. January / turn-of-year — REJECT
Always a micro/small-cap tax-loss-selling effect. Russell 2000 January averaged **+4.37%** pre-1993;
over the following 30 years it deteriorated to a slight average loss. S&P 500 January returns since 1990
are indistinguishable from any other month. Residual survives only in microcaps where round-trip costs
are 50–200 bp and there are no option chains. **Irrelevant for SPY/QQQ/megacaps.**

### E4. Pre-FOMC announcement drift — TEXTBOOK McLean-Pontiff DEATH, confirmed against primary text
**Lucca & Moench (2015, JF 70(1)), "The Pre-FOMC Announcement Drift."**
**Signal:** long S&P 500 from **2:00pm ET the day before** a scheduled FOMC announcement to **2:00pm ET
on announcement day. 24-hour holding period.**
**In-sample Sept 1994 – Mar 2011, 131 meetings: mean +0.492% (SE 0.107), t ≈ 4.6** — roughly **80% of
the annual equity premium** earned in 131 days.
**OOS, verified from Kurov et al., "The disappearing pre-FOMC announcement drift," *Finance Research
Letters*:**

| Period | Type | Mean | SE | n |
|---|---|---|---|---|
| Sep 1994–Mar 2011 | all | **+0.492%** | 0.107 | 131 |
| Apr 2011–Dec 2015 | with presser | +0.445% | 0.133 | 20 |
| **Jan 2016–Dec 2019** | **with presser** | **+0.092%** | 0.069 | 20 |
| Apr 2011–Dec 2018 | no presser | **−0.051%** | 0.141 | 30 |
| Jan 2016–Dec 2019 | ordinary non-announcement days | +0.054% | 0.031 | — |

**The 2016–2019 pre-FOMC return (0.092%) is statistically indistinguishable from an ordinary day
(0.054%).** Authors attribute the death to lower uncertainty (mean VIX 17.7 pre-liftoff vs 14.7 post);
adding VIX makes the post-liftoff dummy insignificant.
⚠️ Note **each OOS bin has n=20** — even the "still worked" 2011–2015 bin is one bad meeting from
insignificance. Since 2022 **all** FOMC meetings have pressers, so the only relevant subsample is the
dead one. **REJECT.**
https://pmc.ncbi.nlm.nih.gov/articles/PMC7525326/

### E5. FOMC cycle / even-week effect — fails HLZ even IN-sample, and flips sign OOS
**Cieslak, Morse & Vissing-Jorgensen (2019, JF 74(5), 2201–2248), "Stock Returns over the FOMC Cycle."**
**Exact definition, verified:** day 0 = FOMC announcement day. **Week 0 = days −1 to +3; week 2 = days
9–13; week 4 = days 19–23; week 6 = days 29–33.** (Odd weeks: 1 = days 4–8, 3 = 14–18, 5 = 24–28.)
**In-sample 1994–2016:** even-week days earn **+12 bp/day** more than odd-week days. Week 0 **+14.1
bp/day**; weeks 2/4/6 **+10.9 bp/day**. Strategy A (always long) 8.48% excess/yr, 19% vol, Sharpe 0.45;
Strategy B (even weeks only) **Sharpe 0.92**, +3.67pp excess, vol down ~⅓; $1 → **$15.22** vs $7.68.
**OOS — Ali Uppal, "Does the FOMC Cycle Still Drive Stock Returns?", daily % excess returns:**

| Dummy | 1994–2013 (IS) | 2014–2016 | **2017–2023** | **2014–2023** |
|---|---|---|---|---|
| Week 0 | 0.136*** (t=2.76) | 0.174* (1.92) | **−0.139 (t=−1.58)** | **−0.045 (−0.67)** |
| Weeks 2,4,6 | 0.0993*** (2.65) | 0.176*** (2.67) | **−0.0077 (−0.13)** | **0.0475 (1.02)** |
| N | 5214 | 783 | 1824 | 2607 |

**The week-0 coefficient flips sign in 2017–2023 on n=1824 — a real sample, not a small one.** Uppal
further shows the proposed mechanism (informal leaks after biweekly Board of Governors meetings)
**ceased after 2004**, when meetings stopped being biweekly — precisely when the effect begins weakening.
**In-sample t of 2.76 and 2.65 already fail the HLZ 3.0 hurdle. REJECT.**
https://aliuppal.me/files/Ali_Uppal_CB_Cycles.pdf

### E6. Factor timing — essentially no expected-return signal clears the bar, and none exists at 8 weeks
- **Asness, "The Siren Song of Factor Timing" (JPM 42(5), 2016):** timing on factors' own value spreads
  is **"very weak historically"**; some long-term-power tests are "exaggerated and/or inapplicable."
  Recommendation: "sin a little." He flags **signal fragility** — book-to-price says value is cheap while
  sales-to-price says it is near normal. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2763956
- **Asness, Chandra, Ilmanen & Israel (JPM 2017), "Contrarian Factor Timing is Deceptively Difficult":**
  the sharper point — **value-spread factor timing is itself a value bet**, so in a portfolio that
  already holds value it *reduces* diversification and detracts. "Intermittent and sub-optimal exposure
  compared to static allocation."
- **The strongest pro-timing result — Haddad, Kozak & Santosh (2020, RFS 33(5)), "Factor Timing":**
  market-neutral factors "strongly and robustly predictable," "substantial improvement over static."
  ⚠️ **Discount heavily:** in-sample, **no transaction costs**, highly persistent predictors on
  overlapping monthly horizons (Stambaugh bias → inflated t-stats), large predictor search space.
- **Horizon killer:** value spreads mean-revert over **3–7 years** → perhaps **6–12 independent
  observations** in a 40-year sample. **At a 2-day-to-8-week horizon these signals do not move at all.
  There is no factor-timing trade in your window. REJECT.**

### E7. Momentum volatility-scaling — the one timing result that works, and why
- **Barroso & Santa-Clara (2015, JFE):** scale momentum to a constant **12% target vol** using the
  realized variance of daily momentum returns over the prior **126 days**. **Roughly doubles the Sharpe**
  and virtually eliminates momentum crashes.
- **Daniel & Moskowitz (2016, JFE 122(2)), "Momentum Crashes":** dynamic scaling on forecast mean *and*
  variance "approximately doubles the alpha and Sharpe ratio of a static momentum strategy."
  https://www.nber.org/system/files/working_papers/w20439/w20439.pdf
- **WHY this survives when expected-return timing does not:** it times the **second moment**. Volatility
  is forecastable with **R² of 40–60%** at daily-weekly horizons; expected returns are forecastable with
  R² ≈ 0. These are not comparable problems. *This is the single most important asymmetry in the whole
  timing literature.*
- **Not implementable as stated** (hundreds of names, monthly rebalance, shorting). **The transferable
  result is a SIZING RULE, not alpha: size inversely to forecast volatility.** This is the same
  conclusion Yang (2024) reaches independently for short-vol (B4).

### E8. Credit / macro spreads — right idea, wrong horizon by an order of magnitude
- **Gilchrist & Zakrajšek (2012, AER 102(4), 1692–1720), excess bond premium (EBP)** = the component of
  corporate credit spreads orthogonal to expected default risk.
  **Horizon, verified from Faust, Gilchrist, Wright & Zakrajšek (NBER w16725): forecasts are run at
  h = 0, 1, 2, 3, 4 QUARTERS.** Gains are "5 to 10 percent reductions in RMSFE at horizon zero," and the
  authors state predictive power is *"modest at best and deteriorates rapidly as the forecast horizon
  extends beyond the very near term."* The Fed's operational use is a **12-month-ahead recession
  probability**. EBP is also published **monthly with a lag**.
  **There is no evidence of EBP predictive content at 2 days to 8 weeks. REJECT as swing alpha.**
- **CDS:** stock returns predict CDS spread *changes*; **CDS spread changes do NOT predict stock returns.**
  Only the CDS *term-structure slope* predicts, and that is a firm-level cross-sectional monthly signal
  (Han, Subrahmanyam & Zhou, JFE 2018), not an index-timing signal.
- **HY spread → equity direction: no reliable evidence.** HY spread → equity **volatility: yes, but
  decaying** — correlation between HY OAS and forward 30-day SPY realized vol was Pearson **0.789 in
  2000–2007** but only **0.258 from 2014 onward.** ⚠️ These correlation figures are from secondary
  sources; **UNVERIFIED.**
- **HYG/SPY "divergence" (4–6 week reversals): blogs and TradingView only, no peer-reviewed work with
  stated bin widths or costs. Treat as folklore.**
- **TED spread is functionally dead** — the series terminated with LIBOR discontinuation in 2022.

### E9. ⚠️ Goyal-Welch — the single most important negative result for any macro-signal swing strategy
**Welch & Goyal (2008, RFS 21(4), 1455–1508); Goyal, Welch & Zafirov (2024, RFS 37(11), 3490–3557),
"A Comprehensive Look at the Empirical Performance of Equity Premium Prediction II."**
29 new variables from 26 post-2008 papers plus the original 17, tested through 2020/2021.
Verified from Welch's own results deck:
- **"Tally V (−2020): 0 out of 17 Monthly Freq"** — **ZERO** of the 17 original monthly predictors have
  both in-sample and out-of-sample performance surviving to 2020. Only 3/17 retain even in-sample
  significance.
- More than **one-third of the 29 NEW variables are no longer significant even in-sample**; of those
  that are, **half fail out-of-sample.**
- **Investment test: 45/45 underperformed unconditional buy-and-hold** on an untilted, unscaled dollar
  basis. **20 of 45 lost money in absolute terms.** Only 9/45 beat the unconditional Sharpe when
  z-scaled; 14/45 when both z-scaled and equity-tilted — about what chance predicts.
- Original GW 2008 monthly **OOS R² is NEGATIVE for essentially every predictor (≈ −0.5% to −2%)**: the
  rolling historical mean beats them.
- Welch's own conclusion slide: *"We cannot reliably predict stock returns forward-looking for top-1000
  stocks,"* followed by *"I doubt the intellectual integrity of our collective research enterprise here."*
- **And all of this is at MONTHLY-to-ANNUAL horizons, where signal-to-noise is at its BEST. At 2-day-to-
  8-week horizons it is strictly worse.**
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3929119 · https://www.ivo-welch.org/research/presentations/gwz-apr22.pdf

### E10. Section E scorecard
| Edge | Horizon | Published stat | OOS status | HLZ t>3? | Net of retail option cost | Verdict |
|---|---|---|---|---|---|---|
| Turn-of-month (−1,+3) | 4 days | 0.15%/day diff, t=7.07 (1926–2005) | 5–12 bp, downtrend since 2015 | IS yes, now no | Negative | **REJECT** |
| Halloween | 6 months | 29 annual obs | Outlier-driven | No | N/A (horizon) | **REJECT** |
| January | 1 month | Microcap only | Dead in large caps since ~1990 | No | Negative | **REJECT** |
| Pre-FOMC drift | 24 hours | +49 bp, t≈4.6 (1994–2011) | +9.2 bp, n=20, ≈ ordinary day | No | Negative | **REJECT** |
| FOMC even-week | 5 days | +12 bp/day, SR 0.92 | Sign flips 2017–23 | **No, even IS** | Negative | **REJECT** |
| Value-spread factor timing | 1–5 yrs | "very weak" (Asness) | Detracts in multi-style | No | N/A (horizon) | **REJECT** |
| Momentum vol-scaling | 1 month | ~2× Sharpe | Holds | Yes (2nd moment) | Not retail-implementable | **ADAPT AS SIZING RULE** |
| EBP / credit spreads | **1–4 quarters** | 5–10% RMSFE gain at h=0 | Holds, macro only | Yes (macro) | No swing content | **REJECT as alpha** |
| HY OAS → forward vol | 30 days | ρ 0.79 → 0.26 post-2014 | Decaying | Marginal | Free (it's a gate) | **KEEP AS RISK-GATE** |
| Any Goyal-Welch predictor | 1 month | Various | **0/17 survive; 45/45 lose to B&H** | No | Negative | **REJECT** |

---

## SECTION F — ⭐ CONDITIONAL REVERSAL / DIP-BUYING (the live hypothesis)

This section addresses the surviving empirical result directly: **SPY dip-buying at a 21-day horizon,
conditioned on market health, winning 64–70% across train/validate/test.**

### F1. ⛔ FIRST — the base rate. The reported win rates are NOT above it.

I computed this directly on `data/swing/panel.parquet` (SPY, 1998-01-02 → 2026-08-06, 7,192 rows).
Script: `scripts/base_rate_check.py`. Horizon = 21 trading days, forward close-to-close.

**UNCONDITIONAL SPY 21-day win rate — this is what you must beat:**

| Split | n | **Base-rate win%** | Base-rate mean 21d return |
|---|---|---|---|
| train 1998–2011 | 3,523 | **60.1%** | +0.46% |
| valid 2012–2019 | 2,012 | **69.5%** | +1.18% |
| test 2020–2026 | 1,636 | **68.8%** | +1.33% |
| ALL 1998–2026 | 7,171 | **64.7%** | +0.86% |

**SPY simply goes up over any 21 trading days about 65% of the time, and about 69% of the time in the
last two splits.** A 21-day directional signal that wins 64–70% has demonstrated nothing.

**Now the conditional versions, with edge measured AGAINST the split's own base rate:**

| Condition | Split | n | win% | Δwin vs base (pp) | mean 21d | **Δmean vs base (pp)** |
|---|---|---|---|---|---|---|
| above50 + dip3 | train | 690 | 63.6 | +3.6 | +0.57% | **−0.10** |
| above50 + dip3 | valid | 466 | 65.7 | **−3.8** | +1.00% | **−0.19** |
| above50 + dip3 | test | 395 | 68.1 | **−0.7** | +0.97% | **−0.36** |
| golden + dip3 | train | 874 | 68.5 | +8.5 | +1.24% | +0.78 |
| golden + dip3 | valid | 705 | 67.8 | **−1.7** | +1.21% | +0.03 |
| golden + dip3 | test | 532 | 68.8 | **0.0** | +1.45% | +0.12 |
| above50 only | all splits | 4,775 | 65.0 | +0.3 | +0.64% | **−0.22** |

**`above50 + dip3` has a NEGATIVE mean-return edge in all three splits.** Its win rate is at or below
the base rate in validate and test. **The trend filter is the problem, not the dip:** conditioning on
"above the 50-day MA" *lowers* the forward 21-day mean return in every single split (−0.22, −0.28,
−0.33 pp) — you are buying after the move has already happened.

This is the **exact failure mode already documented in `FINDINGS.md`**: *"New-low continuation: 54–62%
directional accuracy → zero return."* Same trap, opposite direction. **Conditional accuracy is not
expected return (rule 3).** A 21-day horizon has a high base rate by construction; any long-only signal
inherits it.

### F2. ✅ What DID survive: the VIX-backwardation conditional — and it has a named mechanism

The one condition with a **positive mean-return edge in all three splits** is
`backward + golden` (VIX > VIX3M, i.e. term-structure inversion, **within** a golden-cross uptrend):

| Split | n | win% | Δwin vs base | mean 21d | **Δmean vs base** | median |
|---|---|---|---|---|---|---|
| train 1998–2011 | 119 | 72.3 | **+12.2** | **+1.83%** | **+1.37** | +2.07% |
| valid 2012–2019 | 110 | 70.9 | **+1.4** | **+2.38%** | **+1.19** | +2.64% |
| test 2020–2026 | 86 | 68.6 | −0.2 | **+3.11%** | **+1.78** | +5.53% |
| ALL | 315 | 70.8 | +6.1 | **+2.37%** | **+1.51** | +2.92% |

**The win rate adds nothing (+6pp pooled, ~0 in test). The MEAN RETURN roughly triples.** That is the
correct signature of a real risk premium: **you are not right more often, you are paid more when you
are right.** Note this is the opposite of what an over-fit accuracy signal looks like, and it is the
only result in this document with that shape.

Adding `dip3` on top does **not** improve it (test: 62.1% win, +0.59 edge vs +1.78 without). **The dip
is not the signal. The volatility spike is.**

### F3. This is Nagel (2012) — and the mechanism is liquidity provision under funding constraints

**Nagel, "Evaporating Liquidity," RFS 25(7), 2005–2039 (2012).** Verified from NBER WP 17653.
- **Signal:** each day, average of five reversal strategies weighting stocks proportional to the
  **negative of market-adjusted returns on days t−1 … t−5**, scaled to $1 long / $1 short, daily
  rebalance, hedged to conditional market beta. **Sample 1998–2010** (starts 1998 to avoid the Nasdaq
  spread-reform regime break).
- **Core result, verbatim:** *"the expected return from liquidity provision is strongly time-varying and
  highly predictable with the VIX index. Expected returns and conditional Sharpe Ratios increase
  enormously along with the VIX during times of financial market turmoil."*
- Magnitude: reversal returns ≈ **1%/day** during LTCM 1998 and the 2000–01 Nasdaq decline, fell to
  **<0.2%/day** by 2007, then "virtually exploded" during 2008–09 to above LTCM levels. Expected returns
  rose **~ten-fold from 2006 levels** during the crisis, tracking VIX.
- **Conditional Sharpe rises too**, not just the mean — the risk premium itself increases.
- **⭐ The finding that maps directly onto sector ETFs:** reversal strategies built from **industry
  portfolios** — which are *"not profitable in 'normal' times"* — **earn substantial returns and high
  Sharpe ratios when VIX is high**, ~0.20%/day. Nagel attributes this to market makers being averse to
  absorbing *correlated* industry-level order imbalances.
- **Mechanism (a genuine constraint story, rule 5 satisfied):** high VIX tightens market-maker funding
  and risk-management constraints (Brunnermeier–Pedersen 2009; Adrian–Shin 2010), liquidity supply
  withdraws, and the price of immediacy rises. VIX proxies for intermediary risk-bearing capacity.
- **⚠️ THE COST CAVEAT, and it is severe:** *"the mean returns are only about half as big when
  quote-midpoints are used"* instead of transaction prices. **Half of the headline reversal profit is
  bid-ask bounce that only a liquidity SUPPLIER (resting limit orders) captures.** If you cross the
  spread you are the liquidity demander and you pay it. Nagel reports transaction-price returns.
- **Downside risk:** returns are positively skewed; no three-month period 1998–2010 lost money
  *"before costs of carrying out the trades."*
https://www.nber.org/papers/w17653

**Corroborating: Hameed, Kang & Viswanathan (2010, JF 65(1), 257–293), "Stock Market Declines and
Liquidity."** Negative market returns decrease stock liquidity, especially when funding markets are
tight; commonality in liquidity intensifies during declines; there are *"economically significant
returns to supplying liquidity following periods of large drop in market valuations."* Market makers
can finance less in the repo market against inventory. **Same mechanism, triggered by drawdown rather
than VIX.** ⚠️ Verified at abstract level only.
https://people.duke.edu/~viswanat/Stock_Market_Declines_and_Liquidity_JF2009_FinalwithInternetAppendix.pdf

**Why VIX backwardation specifically is the right trigger:** VIX > VIX3M means the market is pricing
more risk over the next 30 days than the next 90 — an acute, expected-to-be-transient stress. That is
precisely the state in which intermediary constraints bind and immediacy is most expensive. It is a
sharper proxy for Nagel's state variable than the VIX *level*, which is contaminated by slow-moving
regime shifts.

### F4. Post-publication decay — the honest picture
- Nagel's sample ends **2010**; the paper published **2012**. **My computation above is a genuine
  post-publication OOS test of the conditioning logic:** the `backward+golden` mean-return edge is
  **+1.37 (1998–2011) → +1.19 (2012–2019) → +1.78 (2020–2026) pp**. It has **not decayed.**
- ⚠️ **But be careful about what that does and does not show.** My test is the *index-level, long-only*
  version. It shares Nagel's *conditioning variable* and *mechanism* but not his *strategy* (he runs a
  market-neutral cross-sectional book). The persistence is genuine evidence, but it is evidence for
  "buying the index during a VIX inversion inside an uptrend pays a premium," not for Nagel's alpha.
- The cross-sectional short-term reversal literature broadly **has** decayed: Chen & Velikov's modern
  net numbers (header, item 1) and Section A4's finding that plain value-weighted 1-month reversal is
  **t = 1.68, not significant** over 1973–2021.
- **Structural reason to expect this one to persist:** it is compensation for bearing risk when
  intermediary capital is constrained. That premium cannot be arbitraged away by more capital — the
  whole point is that capital is *unavailable* in exactly those states. This is the strongest a-priori
  case for persistence in this document.

### F5. Effective sample size — the honest limit ⚠️
`backward+golden` has **n = 315 overlapping daily signals across 1998–2026**. But 21-day forward windows
overlap heavily, and the signals **cluster into volatility episodes**. The genuinely independent count
is roughly **the number of distinct VIX-inversion episodes inside uptrends — on the order of 20–35 over
28 years.** From `scripts/base_rate_check.py`: the `above50+dip3` condition's 690/466/395 signals
correspond to only ~165/96/78 non-overlapping 21-day windows, and clustering makes even that optimistic.

**With n ≈ 25 independent episodes you can establish "this is probably real and positive." You cannot
fit a threshold** (which VIX/VIX3M ratio? which trend filter? which holding period?) **without
consuming the entire sample.** Keep the rule fixed and crude — `VIX > VIX3M` and `MA50 > MA200`, no
tuned parameters. Any optimization here is the same mistake as the 3,536-configuration sector sweep.

### F6. Raw underlying-return edge (as requested — expression left to you)
For `backward + golden`, entry at close, exit 21 trading days later, SPY:
- **Mean +2.37%, median +2.92%, win rate 70.8%, pooled 1998–2026, n=315 overlapping.**
- **Excess over the unconditional 21-day base rate: +1.51 pp mean, +6.1 pp win rate.**
- Per-split excess mean: **+1.37 / +1.19 / +1.78 pp** — positive in all three, and the *only* condition
  tested with that property.
- ⚠️ **Gross of all costs.** SPY share round-trip is ~1–2 bp, so at the share level the edge is
  essentially intact. That is the number to build on.
- ⚠️ **This is a LONG-ONLY, LONG-BIASED signal in a rising asset.** Roughly +0.86 pp of the +2.37%
  is just the base drift. The genuine conditional component is the **+1.51 pp excess**, and *that* is
  what any structure must clear.

### F7. Verdict on Section F
**The dip-buying framing is wrong; the volatility-stress framing is right.**
- ❌ `above50+dip3`, `golden+dip3`: **REJECT.** Win rates are at/below base rate; mean-return edge is
  zero-to-negative. These are base-rate artifacts.
- ✅ `backward+golden` (VIX term-structure inversion inside an uptrend): **STRONGEST CANDIDATE IN THIS
  ENTIRE REPORT.** Positive mean-return edge in all three splits, un-decayed across a genuine
  post-publication OOS window, and it matches a named, well-cited, mechanism-backed literature (Nagel
  2012; Hameed-Kang-Viswanathan 2010) that predicts *specifically* that the premium should be
  un-arbitrageable.
- ⚠️ **Two caveats that must travel with it:** (i) effective n ≈ 20–35 independent episodes — do not
  tune it; (ii) Nagel's "half the profit is bid-ask bounce" warning means **be the liquidity supplier**
  — enter with resting limit orders, never by crossing the spread into a panic.
- 🔬 **The untested extension worth the most:** Nagel's **industry-portfolio** reversal result — dead in
  normal times, alive when VIX is high, ~0.20%/day. You already have XLB/XLC/XLE/XLF/XLI/XLK/XLP/XLRE/
  XLU/XLV/XLY in `data/swing/panel.parquet`. **Testing sector-ETF reversal CONDITIONED ON VIX
  BACKWARDATION is the single highest-value next experiment** — and note it is *not* the sector
  momentum rotation already ruled out, it is the opposite sign and it is conditional.

### F8. Residual momentum (Blitz, Huij & Martens) — real, but it is a RISK result, not a return result
**Blitz, Huij & Martens (2011), *Journal of Empirical Finance* 18(3), 506–521.** Verified from the
accepted manuscript.
**Signal, exactly codeable:**
1. Each month, for every stock with a complete 36-month history, estimate over a **36-month rolling
   window (t−36 … t−1)**: `r_i,t − rf = α_i + β1·RMRF_t + β2·SMB_t + β3·HML_t + ε_i,t`.
2. Compute the **12−1M residual return** (months t−12 … t−2, skipping t−1), **standardized by the
   standard deviation of the residuals over that same period.** Exclude the estimated α.
3. Rank, equal-weight top/bottom deciles, long-short, overlapping-portfolio holding.

**Results, CRSP NYSE/AMEX/Nasdaq, returns Jan 1930 – Dec 2009, annualized, 1-month holding:**

| | Return | Volatility | **Sharpe** | P(return>0) | Alpha | t(α) |
|---|---|---|---|---|---|---|
| Total return momentum | 10.26% | 22.70% | **0.45** | 63% | 7.98% | — |
| **Residual momentum** | **11.20%** | **12.49%** | **0.90** | 66% | 10.85% | 8.35 |
| Residual, 3M holding | 10.01% | 11.57% | 0.86 | 66% | 9.84% | — |
| Residual, 6M holding | 7.57% | 10.30% | 0.73 | 65% | — | — |

**⭐ Read the table carefully: the RETURN is barely different (11.20 vs 10.26). The VOLATILITY is nearly
HALVED (12.49 vs 22.70). Residual momentum does not earn more — it removes the time-varying
Fama-French factor exposure that makes conventional momentum crash.** Sharpe doubles entirely through
the denominator.
**This is the same structural result as Faber's SMA (D5), Moreira-Muir/Cederburg (D6), and
Barroso-Santa-Clara (E7): every "improvement" that survives in this literature is a SECOND-MOMENT
improvement. Nothing reliably improves the first moment.** That is now four independent confirmations.

**Assessment against your criteria:**
- **Horizon: FAILS.** Formation is 12−1 months and holding is 1–12 months. It **explicitly skips month
  t−1** to avoid short-term reversal — i.e. it deliberately excludes your 2-day-to-8-week window.
  **There is no days-to-weeks version of residual momentum in this paper.**
- **Costs: NOT NETTED.** No transaction-cost analysis. Authors argue costs matter less because profits
  are not concentrated in small caps, and show a large-cap robustness check that is *"not materially
  different"* — but they never compute a net return. Equal-weighted deciles over 1930–2009 is exactly
  the microcap-weighting issue Hou-Xue-Zhang flag.
- **Post-publication: not favorable.** Chen & Velikov find momentum nets **12 bps/month 1998–2013** and
  is unprofitable in the modern sample; Section A4 finds Ehsani-Linnainmaa subsume it into factor
  momentum. ⚠️ **No dedicated post-2011 OOS test of residual momentum specifically was located.**
- **⚠️ Vendor conflict:** all three authors are **Robeco**, which sells residual-momentum products.
- **Retail verdict: REJECT.** Requires 36-month rolling FF3 regressions on the full CRSP cross-section
  and 200+ equal-weighted positions rebalanced monthly. Wrong horizon, no net-of-cost evidence,
  un-implementable at retail scale. **The transferable idea — neutralize a signal against its factor
  exposures before trading it — is worth keeping, and it is the same lesson as A4's IRR/IRRX.**
https://repub.eur.nl/pub/22252/ResidualMomentum-2011.pdf

---

# SYNTHESIS AND RANKED SHORTLIST

## The one-paragraph answer
Of ~30 candidate edges surveyed across the eight requested focus areas, **almost everything published
as a cross-sectional equity anomaly is dead at retail scale** — Chen & Velikov put the average anomaly's
modern net expected return at **4 bps/month**. Three things survive scrutiny, and they share a common
shape: **they are all compensation for bearing risk when someone else's capital is constrained, and
they all pay you more per unit of being right rather than making you right more often.** Everything
that instead promised a higher *hit rate* turned out to be a base-rate artifact — including the
dip-buying result, where SPY's unconditional 21-day win rate is already 64.7%.

## The single most important structural finding
**Four independent literatures — Faber's SMA (D5), Moreira-Muir vs Cederburg (D6), Barroso-Santa-Clara
(E7), and Blitz-Huij-Martens residual momentum (F8) — all decompose the same way: the entire
"improvement" is second-moment (volatility) forecastability, and the first-moment (return)
contribution is approximately ZERO.** Cederburg et al. quantify it exactly: Moreira-Muir's 4.63% alpha
= **−0.24%** from return-forecasting + **+4.87%** from volatility-forecasting.
**Volatility is forecastable (R² 40–60% daily). Expected returns are not (Goyal-Welch OOS R² ≈ 0,
0 of 17 predictors surviving, 45/45 losing to buy-and-hold).**
**Consequence: build sizing rules, not direction rules.** Every hour spent hunting a directional signal
is spent against a literature-wide null; every hour spent on risk-scaling is spent with the grain.

## RANKED SHORTLIST
Ranked by (survives costs) × (survives post-publication) × (implementable at retail on liquid ETFs/megacaps).

### 🥇 1. VIX-backwardation entry inside an uptrend (`VIX > VIX3M` AND `MA50 > MA200`)
- **Signal:** at the close, if VIX > VIX3M and SPY's 50-day MA > 200-day MA, go long SPY. Exit 21
  trading days later. No tuned parameters.
- **Raw underlying edge:** mean **+2.37%** / median +2.92% / win **70.8%** per 21-day hold (n=315,
  1998–2026). **Excess over base rate: +1.51 pp mean.** Per split: **+1.37 / +1.19 / +1.78 pp** —
  positive in all three, no decay.
- **Costs:** SPY round-trip ~1–2 bp. **Edge survives essentially intact in shares.**
- **Post-publication:** Nagel's sample ends 2010; 2012–2026 is genuine OOS and the edge is *stronger*.
- **Mechanism:** liquidity provision under binding intermediary funding constraints (Nagel 2012;
  Hameed-Kang-Viswanathan 2010; Brunnermeier-Pedersen 2009). **Structurally resistant to arbitrage** —
  the premium exists precisely because capital is unavailable in that state.
- **Weaknesses:** effective n ≈ 20–35 independent episodes — **do not tune it.** Long-biased. Nagel's
  warning: **be the liquidity supplier, use resting limit orders, never cross into a panic.**

### 🥈 2. Sector-ETF reversal conditioned on high VIX  🔬 *untested — highest-value next experiment*
- **Signal:** when VIX is elevated / VIX > VIX3M, buy the worst-performing sector SPDRs of the prior
  1–5 days, sell the best; hold days-to-weeks.
- **Published:** Nagel (2012) — industry-portfolio reversal is *"not profitable in normal times"* but
  earns ~**0.20%/day** with high Sharpe when VIX is high.
- **Why it ranks here:** you already have all 11 sector SPDRs 1998–2026 in `data/swing/panel.parquet`.
  Sector ETF spreads are 1–3 bp. **It is the opposite sign to the rotation strategy you already
  falsified, and it is conditional — the null on rotation does not touch it.**
- **Caveat:** halve Nagel's headline for the quote-midpoint/transaction-price gap before believing it.

### 🥉 3. Volatility-scaled position sizing (as an overlay on 1 and 2, not a strategy)
- **Signal:** portfolio delta-notional ∝ `c / σ̂²[t−1]`, σ̂² = realized variance of the prior 21 daily returns.
- **Evidence:** Moreira-Muir (JF 2017) claim +25% Sharpe; **Cederburg et al. (JFE 2020) show the
  standalone real-time version FAILS (0.42 vs 0.46; worse CER in 72/103 cases).**
- **So: do not trade it as alpha.** Use it only to size positions you are taking for another reason.
  Expect drawdown reduction, not return. Corroborated independently by Yang (2024) for short vol:
  **scale DOWN after volatility spikes** — note this *conflicts* with #1's entry trigger, so let #1
  set direction and let this set size, and reconcile deliberately.

### 4. Short ATM straddle / delta-hedged short vol on SPX — real premium, brutal execution
- **Evidence:** BCJ — long ATM straddle **−15.7%/month**, p≈0, 1987–2005 (so short earns it);
  IV 17% vs RV 15%. Israelov-Nielsen: the true vol premium is Sharpe **0.98** but only **7% of the risk**.
- **Why it is only 4th:** Cboe PUT's Sharpe advantage is **exactly zero post-2006** (0.50 vs SPX 0.51);
  Santa-Clara-Saretto show near-maturity straddle Sharpe goes to **−0.182** after real spreads; and
  **Goyenko-Zhang's 60 bps/day closing-mid bias** may account for much of the published delta-hedged
  premium. **You already killed one condor result on exactly this failure mode.**
- **If traded: defined-risk only, and never size it on IV rank.**

### 5. Buying straddles INTO earnings, closing BEFORE the print
- **Signal:** open delta-neutral ATM straddle 1–5 days pre-announcement, close on/just after the
  announcement date. **+0.31% to +2.30%** (1-day version +2.3%), Xing-Zhang, 1996–2010.
- **Only structure in the report whose horizon (2–5 days) natively matches your window and whose
  natural expression IS an option.**
- **Killer caveat:** published concentration is in **small firms with WIDE spreads** — exactly where you
  cannot execute. Post-2010 OOS unverified.

### ⛔ REJECTED (well-sourced negatives — do not re-litigate)
| Edge | Why it dies |
|---|---|
| **Dip-buying on trend filters** (`above50+dip3`, `golden+dip3`) | Win rate = base rate (64.7% uncond.); **mean-return edge negative in all 3 splits**. `above50` *lowers* forward return |
| **Sector momentum rotation** | 3,536-config sweep: 0 beat B&H on validate/test; 2 independent repos null; 1-bp cost fragility |
| **Cross-sectional stock momentum** | Nets 12 bps/mo 1998–2013, unprofitable modern (Chen-Velikov) |
| **Residual momentum** | Wrong horizon (skips t−1 by design), never netted, Robeco conflict, subsumed by factor momentum |
| **PEAD (SUE-based)** | Martineau: coefficient ~0 since 2006, **−0.002 in 2016–2019**. Dead in every optionable name |
| **Earnings announcement premium** | Disappeared post-2004 Form 8-K regulation |
| **TSMOM / trend** | Pooled t=4.34 vs bootstrap crit 4.83–12.53; R²_OS −0.67%; equals a no-predictability placebo; SG Trend 9.2%→1.0%/yr; **fast trend Sharpe 0.84→0.12 at ZERO cost** |
| **Turn-of-month** | 0.15%/day (t=7.07) in-sample → 5–12 bp and falling; negative net in options |
| **Pre-FOMC drift** | +49 bp (t=4.6) → **+9.2 bp**, indistinguishable from an ordinary day |
| **FOMC even-week cycle** | **Sign flips** 2017–2023; fails HLZ t>3 even in-sample |
| **Halloween / January** | 29 annual obs; outlier-driven; microcap-only |
| **Factor timing (value spreads)** | Asness: "very weak"; 6–12 independent obs; **does not move at an 8-week horizon** |
| **Credit spreads / EBP** | Predictive at **1–4 QUARTERS**, not 2–8 weeks. Keep HY OAS as a risk-gate only |
| **Dispersion / correlation** | 18pp premium is real but authors state it **"cannot be exploited with realistic trading frictions"**; 200+ legs |
| **Naked OTM put selling** | BCJ: **statistically insignificant**; (5%,95%) band −65% to +28% on 215 months |

## Methodology rules — how each was applied
1. **Horizon + bin width stated** for every result above. The two most common miscitations found:
   BTZ's VRP predicts **equity returns at a QUARTERLY horizon** (not vol-strategy returns, not monthly);
   EBP predicts at **1–4 quarters** (not weeks).
2. **Net-of-cost:** flagged explicitly. **MOP, HXZ, Ehsani-Linnainmaa, Blitz et al., Moreira-Muir,
   Nagel (midpoint), BCJ (margin+spreads) all report GROSS.** Where netted, results usually flip.
3. **Conditional accuracy vs expected return:** this killed the headline dip-buying result (§F1) and
   governs short-vol (85–90% win rates, negative-expectancy tails).
4. **Post-publication decay:** McLean-Pontiff 58%; Chen-Zimmermann decompose it as ~12 pp publication
   bias + ~38 pp genuine decline. Applied to every candidate.
5. **Mechanism required:** the top 2 candidates have one (intermediary funding constraints). Turn-of-
   month was rejected partly because McConnell-Xu **tested and rejected** its own proposed flow mechanism.
6. **Implausible t-stats flagged:** Ehsani-Linnainmaa **t=7.04**; DMNR IRRX **t=9.35**; Xing-Zhang
   **t=−42.35** (pooled overlapping panel — sign reliable, t is not); MOP **t=7.99** (gross, no costs).

## Verified vs unverified
**Verified against primary text:** Hou-Xue-Zhang; McLean-Pontiff; Chen-Zimmermann; **Chen-Velikov**;
**Broadie-Chernov-Johannes**; Ehsani-Linnainmaa; Falck-Rej-Thesmar; **Dai-Medhat-Novy-Marx-Rizova**;
Lamont-Frazzini; **Nagel**; **Blitz-Huij-Martens**; Dubinsky et al.; Muravyev-Pearson; Novy-Marx (echo);
Faber; Daniel-Moskowitz; Huang-Li-Wang-Zhou; McConnell-Xu; Lucca-Moench + Kurov; Cieslak-Morse-
Vissing-Jorgensen + Uppal; Goyal-Welch-Zafirov.
**⚠️ UNVERIFIED / secondary — do not act on without checking:** the "industry momentum stops working
~2000" break; "no momentum in sector ETFs post-2000" (Springer paywall); Dai et al. large-cap net
recent-decade claim; Heitz et al. announcement-premium disappearance magnitudes; Xing-Zhang post-2010
OOS; Zakamulin's exact Sharpe tables; Goyal-Jegadeesh full text; HY OAS↔vol correlations (0.789/0.258);
turn-of-month 5–12 bp re-test (practitioner newsletter); Kurth et al. (**preprint, not peer-reviewed**).
**My own computation:** §F1/F2/F6 base rates and conditional edges are computed from
`data/swing/panel.parquet` via `scripts/base_rate_check.py` — reproducible, but note SPY 1998–2026 is
a single 28-year path with ~25 independent stress episodes.

## What I would do next, in order
1. **Test sector-ETF reversal conditioned on VIX backwardation** (§F7) — data already on disk, opposite
   sign to the falsified rotation strategy, direct Nagel prediction.
2. **Re-run `backward+golden` with resting-limit-order fills**, not close-to-close, to see how much of
   the +1.51 pp is liquidity-supply premium you can actually capture vs. bounce you must pay.
3. **Download Chen-Zimmermann's Open Source Asset Pricing data** (https://www.openassetpricing.com/data/)
   and settle the one genuinely open question in this report: **is `Abr` (price-based PEAD) still alive
   post-2016?** It is the only anomaly that cleared HXZ's t>2.78 hurdle at a 6–12 month hold.
4. **Do NOT** tune the F2 rule, revisit sector rotation, or build anything on a win-rate metric.
