# Research direction — short-horizon intraday direction, SPX/NDX

Written 2026-08-06, as the follow-on to `FINDINGS.md`. That document recorded what was killed with
our own data. This one asks a different question: **does anyone, anywhere, have published evidence
of a 10-minute-to-2-hour directional edge on an equity index, and can we get the data for it?**

The short answer is no, and the reason is now quantified rather than asserted.

Eight new analyses were run tonight on data already on disk, all in `scripts/`: three that measure
the cost hurdle and the move-size base rate, and five that test signals across three hypotheses.
Four of the five are negative — including the highest-prior candidate in the entire literature,
killed twice on two independent samples. The fifth partially replicated and turns out to be a
four-events-a-year calendar note.

**The four things worth reading if you read nothing else:**

1. **§0 — the edge budget.** A long ATM 0DTE option needs a **58.2%** directional hit rate to break
   even over 90 minutes, measured from real quotes. Delta-1 needs **51%**. For calibration: the best
   published intraday index signal in the literature achieved **54.4%** (§3), which would not have
   funded this system even if it still worked.
2. **§1a — the strongest kill.** The best-resourced order-flow-imbalance model in the literature
   (S&P 100, 10-deep book, cross-asset, 2017–2019) has **negative out-of-sample R²** at *one
   minute*, and its apparent profit comes from the same conditional-selection artefact
   `FINDINGS.md` already diagnosed. Order flow explains 71–87% of the *contemporaneous* move and
   forecasts nothing — which is also the whole story on market internals (§6).
3. **§5b — the framing correction.** No peer-reviewed paper claims GEX predicts the *sign* of
   intraday index returns. Every index-level gamma paper uses **|return|** as the dependent
   variable. Our realised/implied range result was right; it was being asked the wrong question.
4. **§2e — a second methodology lesson for `FINDINGS.md`.** An apparent cross-asset lead-lag with
   **t = 12.5** was entirely overlapping-window inflation; as non-overlapping bets it is a 50.5% hit
   rate and negative net. **Overlapping windows inflate t by ~√(overlap).** Add it to the standing
   checklist beside the conditional-accuracy rule — which, incidentally, now has **four published
   instances** to its name (§2c): Huth & Abergel's 60%, Moews & Ibikunle's 51.7%, Cont et al.'s
   positive PnL on negative R², and our own new-session-low result. It is the most reliable way to
   manufacture a false positive in this domain.

---

## 0. The number everything must be measured against

Before any signal hunting, here is the hurdle. Measured from `data/spxw/data_opt.parquet`
(1,919 sessions of real SPX spot and real SPXW bid/ask, 2016-09 → 2024-05).
Script: `scripts/edge_budget.py`, `scripts/option_drag.py`.

**How big is the move you are trying to catch?**

| horizon | E&#124;move&#124; | sd(move) | P(&#124;move&#124; > 0.30%) |
|---|---|---|---|
| 30 min | 0.149% | 0.231% | 11.2% |
| 60 min | 0.203% | 0.305% | 21.3% |
| 90 min | 0.242% | 0.366% | 26.8% |
| 120 min | 0.324% | 0.478% | 38.5% |

The 0.3%-in-2-hours target is **above the median move**. Only 27% of 90-minute windows and 38% of
2-hour windows produce a 0.3% *endpoint* move in either direction.

A fair objection: a real system exits on a **touch**, not at a fixed endpoint, and touch
probabilities are higher. Measured on SPY minute bars (highs/lows, entries every 30 minutes,
459 sessions):

| horizon | P(touch ±0.30%) | P(endpoint move ≥ 0.30%) |
|---|---|---|
| 30 min | 22.5% | 11.6% |
| 60 min | 38.1% | 20.4% |
| 120 min | 56.3% | 31.1% |

So over two hours the market touches ±0.30% more often than not — but that is **either direction**,
so unconditionally it touches *your* direction roughly 28% of the time, and on a fair number of
those it touches the other side first. Two cautions before this is read as encouraging: a
touch-exit strategy needs a stop, and the P&L is then entirely determined by the stop, not by the
touch rate; and "P(touch | I took the trade)" is precisely the class of conditional statistic that
`FINDINGS.md` §2 showed can be 60% while the expected return is exactly zero.

**What hit rate do you need, by instrument?** (90-minute hold, one trade/day)

| instrument | round-trip cost | break-even hit rate | for Sharpe 0.5 | for Sharpe 1.0 |
|---|---|---|---|---|
| SPY shares | 0.30 bp | 50.6% | 53.0% | 55.4% |
| ES futures | 0.50 bp | 51.0% | 53.4% | 55.8% |
| MES futures | 0.73 bp | 51.5% | 53.9% | 56.3% |
| **long ATM 0DTE call** | — | **58.2%** | — | — |
| **long ATM 0DTE put** | — | **53.8%** | — | — |

The 0DTE rows are **measured, not modelled**: buy the ATM call at the ask at 11:00, sell at the bid
at 12:30, fixed strike re-mapped across the moneyness grid, 1,395 sessions of real quotes. When the
direction is right the call returns **+38.4%**; when wrong, **−53.5%**. Break-even is 58.2%. The
quoted spread is only 3.8% of mid — *the spread is not the problem*. Theta plus the collapse of
delta when you are wrong is the problem. Puts are cheaper to be right with (53.8%) because downside
moves are larger; that is the leverage effect, already noted in `FINDINGS.md`.

**Three consequences, and they frame everything below:**

1. The 55% bar used in the `FINDINGS.md` indicator sweep was the correct bar **for options**. For
   delta-1 the bar is ~51%. That is a genuinely different question and it was never asked.
2. But relaxing the bar does not rescue the programme. A real, stable **53%** signal buys Sharpe
   ~0.3 traded once a day. You need ~55.5% for Sharpe 1.0. Relaxing the bar changes the
   *instrument*, not the conclusion.
3. **Nothing in the published literature offers 55% at 90 minutes on an index.** The best
   documented numbers, detailed below, are roughly 51% at *one minute* on *single stocks*, decaying
   to zero within 30 minutes. That is not a small gap. It is two different businesses.

---

## 1. Microstructure at tick resolution — the strongest negative result

This was the most-hoped-for avenue. It is the one with the clearest kill.

### 1a. State-of-the-art order-flow imbalance has NEGATIVE out-of-sample R² at one minute

**Cont, Cucuringu & Zhang, "Cross-Impact of Order Flow Imbalance in Equity Markets"**
(arXiv [2112.13213](https://arxiv.org/abs/2112.13213), first draft Dec 2021, revised 2023; numbers
below are read directly from the arXiv PDF).

- Sample: S&P 100 constituents, minute-level, 2017–2019. Multi-level (10-deep) order-flow
  imbalance, plus cross-asset OFI across all 100 names — far richer than anything we could build.
- **Contemporaneous** explanatory power is excellent: in-sample R² 71–87%. This is the number
  everyone quotes and it is why OFI has a reputation.
- **Predictive** power is the number that matters, and it is in their Table 8: out-of-sample R²
  for one-minute-ahead returns is **−0.10% to −0.37%**. Negative. The models forecast *worse than
  predicting zero*.
- They nonetheless report a positive "economic gain" (annualised PnL 0.43 for the best model). Read
  how it is constructed: it only trades when the forecast exceeds the bid-ask spread, sizes by
  forecast/vol, and — their words — *"the strategy ignores trading costs, as this is not the focus
  of our paper."* This is **exactly the conditional-statistic artefact `FINDINGS.md` diagnosed**:
  a selection filter on the signal manufactures a positive conditional statistic out of a model
  with negative unconditional skill.
- Their Figure 10 plots PnL against forecast horizon: 1, 3, 10, 30 minutes. It **declines
  monotonically** and by 30 minutes the cross-asset models have converged on the benchmark.

**Read:** if the best-resourced version of this signal has negative OOS R² at one minute and no
edge left at thirty, there is nothing here at ninety. This is the single most decisive citation in
this document.

### 1b. Deep-learning LOB predictability lives at sub-second horizons

**Lucchese, Pakkanen & Veraart, "The Short-Term Predictability of Returns in Order Book Markets:
a Deep Learning Perspective"** (arXiv [2211.13777](https://arxiv.org/abs/2211.13777), 2023).

The most careful large-scale study of "how far ahead can the order book see". Ten Nasdaq stocks,
L1/L2/L3 data, nine horizons, deep architectures (deepLOB, deepOF, deepVOL), Model Confidence Set
testing. Their conclusion, verbatim:

> "The predictability in price formation dynamics … was found to persist up to 50-300 order book
> updates ahead… **Such predictable horizons might vary from a few milliseconds to nearly half a
> second**, depending on the stock under consideration."

Two more things they say that matter for us:

> "we treat the mid-price as the 'true' price… but it is important to note that, by definition,
> **this is not a tradable price**."

> "in the high-frequency context, predictability is not always exploitable due to technological
> limitations and market microstructure issues."

**Read:** the literature that "works at tick resolution" works at *half a second*. It is a
market-making and latency signal. Extending it to 90 minutes is not a matter of more data.

### 1c. VPIN does not work, and the reason is a measurement artefact

**Andersen & Bondarenko, "Assessing Measures of Order Flow Toxicity and Early Warning Signals for
Market Turbulence"** (*Review of Finance* 19(1), 2015,
[doi:10.1093/rof/rfu041](https://doi.org/10.1093/rof/rfu041), full text
[here](https://academic.oup.com/rof/article-pdf/19/1/1/26311243/rfu041.pdf)).

E-mini S&P 500 futures with quote-matched trade classification as the benchmark. Findings:
the Bulk Volume Classification underlying VPIN is **inferior to a plain tick rule**; VPIN
"predicts volatility solely because increasing volatility induces systematic classification errors
in the BVC procedure"; conclusion — *"VPIN is unsuitable for capturing order flow toxicity or
signaling ensuing market turbulence."*

**Read:** do not build VPIN. It is a known artefact, and it was never a directional signal anyway
(at best a volatility warning, and not even that).

### 1d. The one honest positive — and why it is not for us

**Chinco, Clark-Joseph & Ye, "Sparse Signals in the Cross-Section of Returns"** (*Journal of
Finance* 74(1), 2019, [doi:10.1111/jofi.12733](https://doi.org/10.1111/jofi.12733); NBER working
paper [w23933](https://www.nber.org/papers/w23933)).

Real, careful, and positive: rolling LASSO on the full cross-section of lagged 1-minute returns,
250 randomly-selected stocks per day, Jan 2005 – Dec 2012. Annualised Sharpe **1.791** *net of the
full bid-ask spread and with look-ahead bias explicitly removed*, versus 0.123 for buy-and-hold.
The AR(3) benchmark strategy, despite higher raw out-of-sample fit (R̄² 7.4%), **loses money** after
the same adjustments — a clean demonstration that fit ≠ profit.

But look at what it requires: **8.6 trades per minute** across 250 names, one-minute holding
periods, and a total excess return of only 2.719%/yr (the Sharpe is high because the volatility is
tiny). This is a cross-sectional stat-arb book, not an index directional signal. It is also the
paper whose portfolio construction Cont/Cucuringu/Zhang borrowed in 1a — with much worse underlying
skill.

**Read:** the honest positive result in this literature is cross-sectional, minute-horizon, and
requires trading hundreds of names. It is not reachable from where we are, and it is not the trade
we want to make.

---

## 2. Cross-asset and lead-lag

### 2a. The decisive experiment: handicap the E-mini by 15 seconds

**Hasbrouck, "Intraday Price Formation in U.S. Equity Index Markets"** (*Journal of Finance* 58(6),
2003, [doi:10.1046/j.1540-6261.2003.00609.x](https://doi.org/10.1046/j.1540-6261.2003.00609.x)).
Abstract, verbatim: *"For the S&P 500 and Nasdaq-100 indexes, most of the price discovery occurs in
the E-mini market."*

The number that matters is not the headline ~90% information share — it is his **Table 7 delay
experiment**. Handicap the E-mini by **15 seconds** and its information share collapses to
**11–23%**. On 2000-era floor data, before co-location existed, the E-mini's entire informational
advantage was worth **single-digit seconds**. Twenty-six years of latency competition later, asking
whether it survives at five minutes is not a close question.

### 2b. Measured lead times today are all under ten milliseconds

| pair | measured lead | source |
|---|---|---|
| ES → SPY | **7 ms** median arbitrage duration (2011) | Budish, Cramton & Shim, *QJE* 130(4) 2015 |
| stock → stock | **<10 ms** (2021–22), down from "a few seconds" in 2000–05 | Anderson, *JBFE* 2022 |
| VIX futures → SPX futures | **3 ms** median, and only in one regime | Bangsgaard & Kokholm, *JFM* 67, 2024 |
| ES ↔ SPY cross-market spillover | "no longer than a second" | OFR WP 19-04 |

Budish, Cramton & Shim's line is the one to remember. ES and SPY are
*"nearly perfectly correlated over the course of an hour or a minute."* The correlation only breaks
down at **10 ms (0.10)** and **1 ms (0.008)**. There is no minute-scale lead to find, because at
minute scale the two instruments are the same price.

A methodological trap this exposes, and one we would have fallen into: **bin width determines the
answer.** The papers concluding "ETFs now dominate price discovery, futures are irrelevant" sample
at 1-minute bars — and Buckle et al. explicitly disavow their own information-share estimates as
*"inaccurate"* on correlation grounds. At 1-second resolution in 2019, ES and SPY are roughly even,
with SPY *learning from* ES. Sample coarsely enough and any lead-lag vanishes into a tie; that is a
measurement artefact, not evidence of a level playing field.

### 2c. Four papers report a real lead-lag and then report that it is not tradeable

This is the pattern, stated by the authors themselves:

- **Bangsgaard & Kokholm** (*JFM* 67, 2024,
  [doi:10.1016/j.finmar.2023.100851](https://doi.org/10.1016/j.finmar.2023.100851); open PDF via
  [Aarhus PURE](https://pure.au.dk/portal/en/publications/the-leadlag-relation-between-vix-futures-and-spx-futures)):
  VIX and SPX futures are *"too synchronized for the lead-lag relation to be traded with a
  profit."* They swept holding periods from **5 ms to 5 minutes** — profitable at the midquote,
  **negative at bid/ask on every single one**. The lead also only exists in high-volatility
  regimes, i.e. exactly when spreads are widest.
- **Huth & Abergel**: **60% directional accuracy**, and *"we cannot make any profit of this effect
  because of the bid/ask spread."*
- **Brooks, Rew & Ritson**: 0.25% gross against 1.7% costs at 10-minute bars.
- **Cont, Cucuringu & Zhang** (§1a): negative out-of-sample R².

Note that Huth & Abergel's 60% and Moews & Ibikunle's 51.7% at 30 minutes fail in **exactly the way
`FINDINGS.md` §2 documented** — a conditional directional accuracy that is not an expected return.
That is now four independent instances of the same error in the published literature and in our own
work. It is the single most reliable way to manufacture a false positive in this domain.

### 2d. VIX, credit, rates, FX: the causality runs the wrong way or the horizon is wrong

- **Direction of causality.** Bollerslev, Litvinova & Tauchen and Dufour, Garcia & Taamouti both
  find causality runs **returns → volatility for days**, with feedback *"negligible at all
  horizons."* VIX is a deterministic function of SPX option prices; expecting it to lead the index
  is expecting the shadow to lead the object.
- **VIX1D is mechanically useless.** Albers & Kestner: VIX1D rises on **95% of all days**, by an
  average **+28%/day**, purely from its weighting roll. Intraday changes *"provide almost no new
  information."*
- **VVIX**: Park's direct index test gives **t = 0.08**. **SKEW** loses all predictive power in
  controlled specifications.
- **Credit leads equity** is a **daily** literature, and Tolikas finds stocks lead CDS — the
  *opposite* direction to the folklore.
- **International lead-lag into the US open does not exist any more.** ES trades ~23 hours a day,
  so there is no stale SPX price at 09:30 for the Nikkei or DAX to lead into.
- **Frequently miscited as intraday, actually not:** Bennett, Cucuringu & Reinert (daily,
  Sharpe 0.62, **costs excluded by their own admission**), Lo & MacKinlay (weekly),
  Chordia & Swaminathan (daily).

### 2e. Tested tonight on our own data: no tradeable cross-ETF lead-lag

`scripts/leadlag_test.py` and `scripts/leadlag_trade.py`. SPY/QQQ/IWM/DIA aligned 1-minute closes,
459 sessions, 2024-09 → 2026-07 (174,190 aligned minutes).

Stage 1 — regress a target's next *h* minutes on a lead's past *k* minutes, **controlling for the
target's own past k minutes** (otherwise you are just measuring the target's own autocorrelation
leaking through a correlated asset). Something appeared: IWM → QQQ, k=30, h=60, partial
beta 0.067, **t = 12.5**. Nine of 45 cells had |t| > 6.

Stage 2 — the same signal as an actual trade, **non-overlapping bets only**, 3-way split, 1.0 bp
cost:

| split | n | hit rate | gross | net |
|---|---|---|---|---|
| train | 1,147 | 49.9% | +0.69 bp | −0.31 bp |
| validate | 574 | 52.6% | +0.91 bp | −0.09 bp |
| test | 574 | 49.8% | −0.46 bp | −1.46 bp |
| FULL | 2,295 | 50.5% | +0.46 bp | −0.54 bp |

The entire t = 12.5 was **overlapping-window inflation**. With 60-minute windows sampled every
minute, the effective sample is ~1/60th of the nominal one, and t-stats inflate by roughly √60 ≈ 7.7.
12.5 / 7.7 ≈ 1.6. That is the whole effect.

**Methodological note worth adding to `FINDINGS.md`: overlapping windows inflate t by ~√(overlap).
Any regression on overlapping intraday windows must be re-tested as non-overlapping bets before it
is believed.** This is the same class of error as the conditional-accuracy artefact.

### 2f. Read

**There is no published cross-asset lead-lag that is both at 5–30 minutes and survives costs.**
Every candidate resolves into one of four things: microsecond latency arbitrage; a contemporaneous
common response to news mislabelled as a lead; a real effect at daily-to-quarterly horizons; or
gross accuracy reported with costs switched off.

The megacap-single-stock variant needs tick data we do not have — and §1a already tested a far
richer version of exactly that hypothesis (cross-asset OFI across 100 large caps) and got negative
out-of-sample R² at one minute.

The one genuine 30-minute effect anyone found is **Kurov et al.'s pre-macro-announcement drift** in
ES and ZN. Its market-wide prize is roughly **$21M/year across ~7 releases** — that is the total
available to every participant combined, before costs, which puts a hard ceiling on what a retail
share of it could be worth.

*Sourcing caveats, recorded honestly.* Published-version Hasbrouck digits could not be retrieved
(Wiley blocks automated fetch); the working paper plus his own 2003 SAS output were substituted.
Bangsgaard & Kokholm's numeric returns are read from figures, with no Sharpe ratios given. Wallace
et al. and Chen/Chung/Lien rest on abstracts only; Albers 2025 full text and Liu & Faff were not
directly verified. **Genuine open gap: nobody has re-run Hasbrouck's exact 1-second design on
post-2015 ES/SPY data.** That is a real hole in the literature — but note it would tell us who leads
at one second, which is not a horizon we can trade.

---

## 3. The one real academic candidate — and it fails on our data

This is the most important new work in this document, because it is the only published,
**index-level**, out-of-sample-validated, 46-year intraday directional effect I could find, and
because it was never tested in `FINDINGS.md`.

### The claim

**Baltussen, Da, Lammers & Martens, "Hedging demand and market intraday momentum"** (*Journal of
Financial Economics* 142(2), 2021, 377–403,
[doi:10.1016/j.jfineco.2021.04.029](https://doi.org/10.1016/j.jfineco.2021.04.029); open PDF at
[pure.eur.nl](https://pure.eur.nl/ws/files/58145484/1_s2.0_S0304405X21001598_main.pdf)).
Extends **Gao, Han, Li & Zhou, "Market intraday momentum"** (*JFE* 129(2), 2018,
[doi:10.1016/j.jfineco.2018.05.009](https://doi.org/10.1016/j.jfineco.2018.05.009)).

- **Claim:** the return in the **last 30 minutes** (`rLH`) is positively predicted by the return
  over the **rest of the day** (`rROD`, previous close → 15:30).
- **Sample:** 60+ futures across equities, bonds, commodities, FX, **1974–2020**. Genuinely OOS:
  pooled out-of-sample R² **2.88%**, positive and significant for 14 of 17 equity contracts.
- **Effect size:** equity index futures timing strategy — annualised return 6.86%, vol 3.96%,
  **Sharpe 1.73**, success rate 55%. Stable across 1974–1999 and 2000–2020 subsamples.
- **Mechanism, and this is why it should have worked for us:** it is gamma hedging. Conditional on
  S&P 500 dealer **net gamma exposure < 0**, β = 6.63 (t = 4.78), R² = 3.58%. On positive-gamma
  days, β = 0.82 (t = 1.03) — *no effect at all*. We already compute exactly this regime
  (`data/squeeze_dix_gex.csv`, `gex_regime.py`).
- **Costs:** not modelled in the main results. They state that in S&P 500 futures, assuming one
  tick of cost, the net Sharpe remains positive.

### The test

`scripts/test_intraday_momentum.py` — real SPX spot at 15:30 and 16:00 from the SPXW panel,
611 sessions with a valid prior close, 2016-09 → 2024-05, 3-way chronological split:

| split | n | β (×100) | t | R² |
|---|---|---|---|---|
| train | 305 | +1.43 | +1.12 | 0.41% |
| validate | 153 | +1.29 | +0.54 | 0.20% |
| **test** | 153 | **−4.69** | **−2.06** | 2.73% |
| FULL | 611 | +0.63 | +0.65 | 0.07% |

Splitting on dealer gamma does not rescue it — on `gz<0` days the test-split β is **−5.66**.
The sign-based trade: train 55.5% hit / +4.29 bp on short-gamma days, **test 42.9% hit / −6.81 bp**.

`scripts/test_intraday_momentum_spy.py` — an independent check on 491 sessions of SPY 1-minute data,
**2024-07 → 2026-07**, a period after both the paper's sample and our SPXW panel:

| spec | full-sample β | t | R² | sign-trade hit |
|---|---|---|---|---|
| `rLH ~ rONFH` (Gao et al.) | +3.24 | +1.06 | 0.23% | 45.0% |
| `rLH ~ rROD` (Baltussen et al.) | +0.40 | +0.42 | 0.04% | 48.3% |

Sign flips between the two halves in every specification. On short-gamma days: 200 sessions,
50.0% hit, −1.60 bp.

### Read

The best-documented intraday directional effect in the literature **has decayed to nothing in the
0DTE era**. The paper's sample ends May 2020; Cboe's own product page
([cboe.com/tradable-products/0dte](https://www.cboe.com/tradable-products/0dte), verified, no date
given on the page) now states **"59% of SPX volume traded 0DTE"**. The proposed mechanism — dealers
short gamma must chase into the close —
is precisely the mechanism 0DTE flow changed, and dealer gamma now mean-reverts intraday rather
than accumulating into the close.

Also worth noting even if it *had* held: mean |last-half-hour move| is **18 bps** on SPX and 14 bps
on SPY. That is a delta-1 trade or nothing. It could never have funded a 0DTE option.

**Do not pursue. But do record the negative result — it is worth more than another literature
review, and it closes the highest-prior remaining hypothesis.**

One caveat in fairness to the paper: even in their own numbers the pooled coefficient is
β = 0.0414 — a 1% rest-of-day move forecasts **4.1 bps**, or 6.6 bps conditional on short gamma.
That was never a 30 bps signal. Note also that Baltussen et al. report a **negative** out-of-sample
R² (−1.40%) for Gao et al.'s more famous first-half-hour SPY specification, i.e. the 2018 result was
already partly superseded by the 2021 one before either was tested here.

### The ceiling this sets

It is worth being precise about what the *best* published index intraday signal actually delivered
in its own paper, because it calibrates everything. Gao, Han, Li & Zhou (2018), SPY, TAQ,
Feb 1993 – Dec 2013 ([WP PDF](https://smallake.kr/wp-content/uploads/2015/01/SSRN-id2440866.pdf)):

- in-sample R² **1.6%** (2.6% adding the 12th half-hour); **out-of-sample R² 1.7%**
- **hit rate 54.37%** against a 50.42% unconditional base rate
- gross **6.67%/yr**, σ 6.19%, **Sharpe 1.08**
- costs *were* modelled: ~2.52%/yr commission + 1.26%/yr spread = **3.78%/yr**, leaving **~3.07%/yr
  net** — costs eat **55% of the edge**, and that is SPY at 1,000 shares with a $4.99 commission
  executing into the closing auction where they argue the spread cost is zero

So the single best-documented intraday index signal in the literature is **54.4% on a 30-minute
horizon**, from price rather than internals, netting ~3%/yr in its own most favourable accounting —
and it does not replicate on our data in the modern era. Look back at §0: 54.4% is below the 55.4%
that SPY shares need for Sharpe 1.0, and far below the 58.2% a long 0DTE call needs to break even.
**Even the best published result in the field would not have funded this system.**

---

## 4. Auction and flow events

This was the most promising-looking untested area on the original list — published private
information with a short mechanical horizon, categorically different from a technical indicator. It
does not survive contact with the index-level numbers, and the reason is clean.

### 4a. The killer: idiosyncratic imbalances diversify away at the index level

**Bogousslavsky & Muravyev, "Who Trades at the Close? Implications for Price Discovery and
Liquidity"** (*Journal of Financial Markets* 66, Nov 2023, 100852; free working paper
[PDF](https://static1.squarespace.com/static/6310c0b9bb63a25599f4418c/t/634ffc92f81e226b2c30654f/1666186387645/who-trades-at-the-close_June2021.pdf)).
US common stocks, TAQ plus auction data, 2010–2018.

- Average absolute closing-auction price deviation from the 16:00 midquote: **8.12 bps** —
  against an average half-spread of **7.56 bps**. The deviation is essentially the half-spread. The
  price-impact component is only **0.55 bps**.
- **Aggregate (market-wide) price deviation is 0.93 bps.** Individual names deviate 8 bps; the
  index deviates under one. Idiosyncratic imbalances net out.
- Large caps: 2.66 bps. Small caps: 20.6 bps.
- **Reversal coefficient −0.85** (−0.95 adjusting for bid-ask bounce): the deviation is almost
  entirely temporary and reverts by 09:45 the next morning, with half the reversion inside a
  20-minute after-hours window.
- Disseminated imbalance *does* move prices: weighted price contribution jumps at 15:45 for NYSE
  names when dissemination begins. So the information is real — it is just already in the price
  within a minute, and at the index level it is worth under a basis point.
- Note: every paper in this literature restricts to CRSP share codes 10/11 and **excludes ETFs**.
  SPY and QQQ are not in any of these samples.

Closing-auction share of volume, for the record: 3.1% (2010) → 7.5% (2018) per Bogousslavsky &
Muravyev; **"about 10% of daily trading volume"** as of Goyal, Jegadeesh & Wu (2025).

### 4b. Does the published imbalance predict 15:50 → 16:00? Yes — and it is not tradeable

**Goyal, Jegadeesh & Wu, "Price Impact in Closing Auctions, Opening Auctions, and Continuous
Markets"** (*JFQA*, Dec 2025; free
[PDF](https://jfqa.org/wp-content/uploads/2026/01/25551_Price_Impact.pdf)). CRSP common stocks,
NYSE + Nasdaq, Jan 2012 – Dec 2021.

Price impact jumps at **15:46**, one minute after dissemination, and keeps building to 16:00 —
*"OI information leads to stock price movement."* Their own verdict, verbatim:

> "Bogousslavsky and Muravyev (2023) also find that this price jump reverses by open the next day
> and hence **it would be difficult for arbitrageurs to profit solely from this pattern**."

Useful operational detail from the same paper — the dissemination time has moved, which matters if
you ever backtest this: **15:45 NYSE / 15:50 Nasdaq** (Jan 2012 – Oct 2018), then **15:50 both**
(Apr 2019 – present).

A related caution: **Hu & Murphy, "Vestigial Tails? Floor Brokers at the Close in Modern Electronic
Markets"** (*Management Science* 72(5), 2025,
[doi:10.1287/mnsc.2023.00884](https://pubsonline.informs.org/doi/10.1287/mnsc.2023.00884)) shows
NYSE floor brokers can submit D-Quotes until 15:59:50 that are not in the disseminated imbalance
until late. **The published NYSE imbalance is structurally noisier than Nasdaq NOII.**

The one profitable strategy in this literature — Jegadeesh & Wu, *JFE* 143(3), 2022,
[doi:10.1016/j.jfineco.2021.12.003](https://doi.org/10.1016/j.jfineco.2021.12.003) — is a
**cross-sectional, single-stock, 3–5 day reversal**. Different business, hundreds of names,
institutional cost structure.

### 4c. Opening auction: too small to matter

From the same Goyal/Jegadeesh/Wu paper: *"Opening auctions are illiquid."* Median opening auction
volume is **0.92% of ADV**, and opening volume is only **5–10% of closing auction volume**.
Imbalances rarely exceed 1% ADV for large caps.

The strongest possible test of a pre-open shock is triple-witching, where index arbitrage runs 50×
normal. **Barclay, Hendershott & Jones** (*JFQA* 43(1), 2008; free
[PDF](https://business.columbia.edu/sites/default/files-efs/pubfiles/4055/rder%20consolidation%20price%20efficiency%20and%20extreme%20liquidity%20shocks.pdf))
find the opening trade is $15.05M/stock vs $1.45M normally and index-arb imbalance is $3.21M vs
$0.14M — and the **open-to-10:00 coefficient is 0.01 with s.e. 0.07, statistically zero**. Volume is
back to normal after 09:45. Their dependent variable is |return| throughout — volatility, not
direction.

**Read: no published evidence of directional predictability from pre-open imbalance into the first
30–60 minutes, and the largest available shock leaves nothing behind by 10:00.**

### 4d. Index rebalance: the effect has disappeared

**Greenwood & Sammon, "The Disappearing Index Effect"** (*Journal of Finance* 80(2), 2025, 657–698;
free [NBER PDF](https://www.nber.org/system/files/working_papers/w30748/w30748.pdf)). S&P 500
additions/deletions, 1980–2020:

| decade | addition effect | deletion effect |
|---|---|---|
| 1980s | +3.4% | −4.6% |
| 1990s | +7.6% | −16.6% |
| 2000s | +5.2% | −12.3% |
| **2010s** | **+0.8%** (indistinguishable from zero) | ~0 |

**Excluding Tesla, the average 2020 inclusion effect was −3 basis points.** And it disappeared
*despite* passive ownership continuing to grow — their explanation includes index funds
pre-announcing and executing in the closing auction, letting liquidity providers pre-position.

Bogousslavsky & Muravyev on the 207 S&P rebalance events in their sample: auction volume rises
**over 3,000%** and absolute deviation rises to ~21 bps — but *"the auction price deviation becomes
insignificant once the regression controls for turnover."* The 21 bps is the mechanical price of
executing a 3,000% volume spike, not a mispricing.

Also worth knowing operationally: **from 2026 the Russell reconstitution is semi-annual (June and
December), no longer annual** —
[LSEG schedule](https://www.lseg.com/en/media-centre/press-releases/ftse-russell/2026/russell-reconstitution-2026-schedule).

### 4e. ETF creation/redemption: no intraday signal, and the data is two days late

- **Box, Davis, Evans & Lynch** (*JFE* 141(3), 2021, 1078–1095;
  [record](https://ideas.repec.org/a/eee/jfinec/v141y2021i3p1078-1095.html)) run the direct
  minute-level test with a panel VAR and conclude **"ETF returns do not lead portfolio prices."**
  Arbitrage gaps originate in the underlying and are closed by ETF *quote* adjustment.
- **Petajisto** (*FAJ* 73(1), 2017; [PDF](http://petajisto.net/papers/etf28.pdf)): diversified US
  equity ETFs have 10–20 bps premium volatility, and a creation the size of a full day's ETF volume
  moves the premium **~1 bp by the close**. Inside the spread.
- **Brown, Davies & Ringgenberg** (*Review of Finance* 25(4), 2021, 937) find flow predictability
  concentrated in **levered and niche ETFs**; mature unleveraged ETFs — the SPY/QQQ bucket — show
  no one-month predictability. Monthly panel, costs not modelled.
- **Timing kills it regardless:** State Street's official SPY page showed shares outstanding
  "as of August 4, 2026" when checked on 2026-08-06 — a **two-business-day lag**. Share counts
  update at DTCC clearing, post-close at the earliest.

---

## 5. Options expiration mechanics — and the one thing that partially survived

### 5a. Pinning does not exist for cash-settled index options

**Golez & Jackwerth, "Pinning in the S&P 500 futures"** (*JFE* 106(3), 2012, 566–585; free
[PDF](https://kops.uni-konstanz.de/bitstreams/9a1772fe-3a5e-49f5-9a86-b2387ba8e167/download)),
1982–2009. ES futures settle within $0.25 of the nearest $5 strike on 13.56% of serial expirations
vs 10% expected. But verbatim:

> "**there is no pinning in the S&P 500 index itself due to expiration of SPX options on the S&P
> 500 index nor in the exchange traded fund on the S&P 500 (SPDR) due to expiration of its SPY
> options**."

Pinning requires a deliverable underlying. Cash settlement removes the mechanism. The famous
Ni, Pearson & Poteshman result (*JFE* 78(1), 2005) is a **single-stock** effect (≥16.5 bps), and
their own footnote cites Mayhew that for *index* expirations *"there is little evidence of a strong,
systematic price effect."*

### 5b. The gamma/vanna/charm literature predicts |return|, not sign

This is the most important framing correction available, given how much of this project's
infrastructure is built on GEX. Barbon & Buraschi, "Gamma Fragility"
([PDF](https://abarbon.com/assets/Barbon_Buraschi_2021_Gamma_Fragility.pdf)) — the index-level
dependent variable is **|Return|**: 1σ of gamma imbalance → 20 bps lower *absolute* return.
Ni, Pearson, Poteshman & White (*RFS* 34(4), 2021) — hedging explains ~13% of daily *absolute*
return in single stocks. Bollen & Whaley (*JF* 2004) — dependent variable is the implied vol
surface.

**No peer-reviewed paper claims GEX predicts the sign of intraday SPX returns.** This is exactly
consistent with `FINDINGS.md`: the realised/implied range finding (0.843× vs 1.139×, t = −13.2) is
real *and it is a variance result*. We were right about what gamma does. It was never a direction
signal, and the literature never said it was.

On 0DTE specifically: Dim, Eraker & Vilkov
([paper](https://westernfinance-portal.org/viewpaper?n=950096), SPX 2012–2023) find
*"intraday 0DTE trading volume shocks do not amplify recent past index returns"* — the
destabilisation story tests as a null. Bandi, Fusari & Renò (SSRN 4503344) report a 5.5-hour
return-prediction R² of **1.58%** against **21.20%** for the variance premium — 15× stronger for
volatility than for direction, in-sample and uncosted.

### 5c. Directly cautionary: what retail 0DTE directional traders actually earn

**Beckmeyer, Branger & Gayda, "Retail Traders Love 0DTE Options… But Should They?"** (Dec 2023;
[PDF](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf), verified and
quoted directly). Cboe trade data with retail trades identified from exchange-level developments.
Their abstract, verbatim:

> "between February 2021 and September 2023, retail investors lost **$241,000 on an average day**;
> since the introduction of a daily expiration calendar in May of 2022, this number has grown to
> average losses of **$350,000 per day**. We find that **single-leg trades, trades that require an
> upfront payment to be set up, and trades that use high-implied volatility options are responsible
> for these losses. In contrast, multi-leg trades and trades that capture the compensation for
> volatility and jump risks are significantly more profitable.**"

Read both halves. The first half describes exactly the instrument a 0.3%-target directional signal
puts you in — a single-leg debit trade — and it is the one our own measurement says needs a 58.2%
hit rate.

The second half is the most constructive sentence in this entire document, and it points at what
this project has *already* built rather than at something new. Defined-risk multi-leg structures
that harvest the volatility and jump risk premium are where the measurable compensation is. That is
the same conclusion as §5b (gamma is a variance signal), the same conclusion as `FINDINGS.md`
(realised/implied 0.843× vs 1.139×, t = −13.2, real), and the honest caveat is also already on
record: the condor as configured is approximately break-even on real quotes, because the market
prices the range correctly. The direction to push is **how that premium is harvested more
efficiently**, not whether to keep hunting direction.

### 5d. The one candidate that partially replicated

**Baltussen, Terstegge & Whelan, "The Derivative Payoff Bias"** (AFA 2025,
[SSRN 4562800](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4562800)). SPX/NDX/DJIA,
2003–2021. Third-Friday **AM settlement**: the index drifts up into the SOQ and reverts during the
session. Quarterly (triple witch): Thu close → Fri open **+26.4 bps (t = 4.36)**; Fri open → Fri
close **−37.2 bps (t = −3.54)**. Off-quarterly open→close is only −6.7 bps (t = −1.03,
insignificant). ES strategy **net of bid/ask: +24.2 bps per event, t = 3.47, Sharpe 0.80**, positive
in 16 of 19 years.

Caveat from its own AFA discussant — **Bogousslavsky**
([slides](https://bogousslavsky.github.io/files/AFA_2025_discussion.pdf)) — who replicates on SPY
and gets the 09:30→noon leg at **−13.5 bps (t = −3.18)**, not −37, and the overnight edge measured
to the 10:00 midquote at only **+7.99 bps (t = 1.94)**. Not out-of-sample past 2021.

**Tested on our own data** (`scripts/test_witching_drift.py`, SPX spot from the SPXW panel,
2016-09 → 2024-05; our first grid point is 10:00, so this is Bogousslavsky's weaker specification):

| day type | leg | n | mean | t |
|---|---|---|---|---|
| **quarterly witch** | 10:00 → close | **28** | **−37.20 bp** | **−1.97** |
| monthly, non-quarterly | 10:00 → close | 53 | +0.91 bp | +0.11 |
| all other days | 10:00 → close | 781 | +3.63 bp | +1.24 |

Difference vs baseline: **−40.8 bp, Welch t = −2.14, p = 0.041.** The quarterly session leg lands
almost exactly on the paper's −37.2 bps figure. **This is the only thing in this entire document
that replicated.**

But read the rest honestly:

- **It is decaying.** Split-half on the 28 events: first half −61.5 bp (t = −1.83), second half
  **−12.9 bp (t = −0.81)**.
- **n = 28.** Four events per year. p = 0.041 on 28 observations after a literature search is not
  a result you would bet on without more data.
- Our overnight leg is **−37 bp**, the opposite sign to the paper's +26.4 bp — but on n = 8, so it
  says nothing either way.
- **It is not a 10min–2hr signal.** −37 bps over a six-hour session, four times a year. As a
  delta-1 short it is a calendar overlay worth perhaps a few basis points a year on the book. It
  cannot support a 0DTE options system, and 4 events/year cannot support any system.

**Verdict: the only survivor, and it is a calendar note, not a strategy.** Worth adding to
`events.json` as a mild bearish tilt on quarterly witching Fridays. Not worth building around.

---

## 6. Market internals — closed by the literature, not by folklore

I went in expecting this to be the one genuinely open item and to recommend buying data. The
evidence says otherwise, and the reason is worth understanding rather than just accepting.

### 6a. There is no academic literature on $TICK, $TRIN or breadth thrust. At all.

Systematic title searches on OpenAlex (~250M works):

| title search | finance hits |
|---|---|
| "TICK index" | **0** — all 65 hits are *Ixodes*, the arachnid |
| "Arms index" | **1** — Arms's own 1988 trade book, miscatalogued under *Medical Entomology* |
| "advance-decline line" | 3, all 1968–1978 |
| "breadth thrust" | **0** |

GitHub: `NYSE+TICK` returns 28 repos, all ticker-symbol lists; `TRIN+index+trading` returns 0. The
entire online $TICK/$TRIN/$ADD corpus is SEO content and trading blogs. **This is folklore — not
"weakly supported", but untested in the refereed literature.**

The most methodologically disclosed practitioner study found ([thetrading.tools/nyse-tick](https://www.thetrading.tools/nyse-tick):
rolling 252-session z-score, 5-min bars, 7,079 sessions since 1998) reports its "bearish tilt" state
(n = 1,456) returning **+0.71% over the next 21 sessions against a +0.69% baseline**. Two basis
points, overlapping windows, no costs, no split — and the horizon is 5–21 *days*. The site itself
says "context, not a forecast."

### 6b. But the properly-measured version has been tested to death, and it is a null

$TICK is a crude, noisy, uptick-rule-contaminated proxy for market-wide order imbalance. Academics
measure that variable properly from TAQ. Three papers by the same canonical authors:

**Chordia, Roll & Subrahmanyam (2002), "Order imbalance, liquidity, and market returns,"** *JFE*
65(1), 111–130 ([PDF](https://www.cis.upenn.edu/~mkearns/finread/Chordia_buy-sell_orders.pdf)).
NYSE S&P 500 stocks, 1988–1998, 2,779 days. Verbatim:

> "Notwithstanding the daily serial dependence in both order imbalances and liquidity, **there is no
> evidence that they can predict one-day-ahead stock market returns**."

**Chordia, Roll & Subrahmanyam (2005), "Evidence on the speed of convergence to market
efficiency,"** *JFE* 76(2), 271–292
([WP](https://www.anderson.ucla.edu/documents/areas/fac/finance/11-01.pdf)). **The only paper at
exactly our horizon** — 5/10/15/30/60-minute intervals, 40 NYSE stocks, 1996 and 1998. Lagged
trade-count imbalance turns *negative* (contrarian) by 10 minutes and lives inside the spread;
lagged dollar imbalance is "insignificant beyond fifteen minutes"; larger orders "offer no genuine
arbitrage opportunities."

**Chordia, Roll & Subrahmanyam (2008), "Liquidity and market efficiency,"** *JFE* 87(2), 249–268
([WP](https://www.anderson.ucla.edu/documents/areas/fac/finance/21-05.pdf)). **The decisive
result.** All NYSE stocks, 1993–2002, 5-minute returns on lagged dollar imbalance, split by tick
regime:

| tick regime | all firms adj-R² | large firms adj-R² | large-firm t |
|---|---|---|---|
| eighths (1993 – 6/1997) | 0.0519 | 0.0393 | 50.11 |
| sixteenths (6/1997 – 1/2001) | 0.0055 | 0.0030 | 6.57 |
| **decimal (2001–2002)** | **0.0007** | **0.0004** | **1.58 (insignificant)** |

Their words: R² fell "from a peak of about 11% in the eighths regime to virtually zero by the end of
the sample period." That is **gross of costs, in 2002, before the HFT arms race**, on individual
stocks where imbalance is far more informative than at index level.

Put beside §1a — Cont/Cucuringu/Zhang's modern, 10-deep, cross-asset OFI with **negative**
out-of-sample R² at one minute — the picture is unambiguous. **Order flow explains 71–87% of the
*contemporaneous* move and forecasts nothing.** $TICK is a coarser version of the same variable: it
tells you what just happened, which you can already read off the price.

### 6c. Breadth indicators as a class have been tested, and fail after costs

**Fang, Qin & Jacobsen (2014), "Technical market indicators: An overview,"** *Journal of Behavioral
and Experimental Finance* 4, 25–56
([doi:10.1016/j.jbef.2014.09.001](https://doi.org/10.1016/j.jbef.2014.09.001)). **93** technical
market indicators — advance/decline lines, the Arms Index, short-term trading indices, short
interest, volatility indices — longest sample ~200 years, average 54 years:

> "We give these technical market indicators the benefit of the doubt, but even then we find little
> evidence that they predict stock market returns."

The funnel: 30 of 93 significant at a lenient 10% → 10 survive sub-sample checks → 8 survive
rolling-window stability → **none beats naïve buy-and-hold** once risk and transaction costs are
accounted for. The NYSE advances/declines/new-highs family got into the final ten and then failed
the economic test. (Daily-to-monthly frequency, not intraday — but that cuts against the indicators,
not for them.)

### 6d. Intraday put/call: the public series is specifically the part that does not work

**Pan & Poteshman (2006), "The Information in Option Volume for Future Stock Prices,"** *RFS* 19(3).
Low put/call stocks beat high by >40 bps next day and >1% over a week — but the signal comes from a
**proprietary CBOE dataset of volume initiated by buyers to open new positions**, and the authors
explicitly partition it and find the predictability lives in the **non-publicly-observable**
component. The public CBOE equity put/call ratio you can download is the residual that doesn't
predict. Corroborating: Gang, Huang, Song & Zhang (2020), *Quantitative Finance* — "the PCRs
implemented in many trading practices may be **misused**, because there is **no evidence that the
PCRs and index returns are correlated**."

### 6e. Retail/odd-lot imbalance: predicts, but is not profitable — and is mis-measured

- **Boehmer, Jones, Zhang & Zhang (2021),** *JF* 76(5) — the subpenny algorithm. Net-bought beats
  net-sold by ~10 bps over the *following week*. Cross-sectional, single stocks, weekly.
- **Barber, Lin & Odean (2023),** *JFQA* — "Resolving a Paradox: Retail Trades Positively Predict
  Returns but Are **Not Profitable**." Long-short on extreme retail-imbalance quintiles earns
  **−14.8% annualised** among heavily retail-traded stocks.
- **Barber, Huang, Jorion, Odean & Schwarz (2024),** *JF* 79(4) — placed 85,000 real trades to
  validate the BJZZ algorithm: it identifies 35% of trades as retail, **mis-signs 28% of them**, and
  yields uninformative imbalance for 30% of stocks.
- **O'Hara, Yao & Ye (2014), "What's Not There: Odd Lots and Market Data,"** *JF* 69(5) — odd lots
  are a median 24% of trades (60%+ in some names) and contribute **35% of price discovery**, yet
  were absent from the consolidated tape and TAQ. Omitting them "makes **sentiment measures
  unreliable**." **Historical $TICK and breadth series inherit exactly this bias**, which is a
  reason to distrust any long-history backtest of them even before the economics.

Also relevant, since it is often cited loosely: **Hendershott & Menkveld (2014), "Price pressures,"**
*JFE* 114(3) — price pressure averages 0.49% with a half-life of **0.92 days**, and is identified
from **proprietary NYSE specialist inventory data**, not recoverable from any public breadth series.

### 6f. Read

**Absence of evidence is unusually informative here.** $TICK is not an obscure variable academics
overlooked — it is a 60-year-old indicator that survives entirely on practitioner folklore, and the
properly-measured version of the same underlying quantity has been tested exhaustively with a null
result, most damningly at our exact 5–60 minute horizon and most recently with negative
out-of-sample R².

The internals are not *useless*. They are excellent **contemporaneous state descriptors**. They are
not predictive, and trading-blog writing conflates the two constantly. That conflation is the same
error as §1a's contemporaneous R² of 71–87% versus predictive R² of −0.1%.

**I therefore downgrade my own earlier recommendation.** This is not "the last open question worth a
session and possibly $880." It is closed on the literature. If you want the null in your own data —
a reasonable thing to want, given how much of this project's value has come from measuring rather
than assuming — spend **$4.50 on the IBKR test, not $880 on Kibot**, and timebox it.

---

## 7. Other things already known to be dead — do not re-open

**Pre-FOMC announcement drift.** Lucca & Moench (*Journal of Finance* 69(3), 2014,
[doi:10.1111/jofi.12196](https://doi.org/10.1111/jofi.12196)) documented ~0.5% equity excess return
in the 24 hours before scheduled FOMC announcements, 1994–2011. It is gone. Two independent
follow-ups confirm: *"The equity return during the pre-FOMC window declined from 0.5% on average per
FOMC meeting to roughly 0.1% in the out-of-sample period after 2011 and was no longer significant"*
(*Journal of Fixed Income* 28(4), 2019, [doi:10.3905/jfi.2019.28.4.060](https://doi.org/10.3905/jfi.2019.28.4.060));
and "The disappearing pre-FOMC announcement drift" (*Finance Research Letters* 2020,
[doi:10.1016/j.frl.2020.101781](https://doi.org/10.1016/j.frl.2020.101781)).

This is the pattern to internalise: **published index-level intraday effects decay after
publication.** Both of the two best candidates in the entire literature (pre-FOMC drift, intraday
momentum) are now dead, and one of them died on our own data tonight.

---

## 8. What actually works for profitable intraday participants

Asked bluntly, answered bluntly. The evidence is unambiguous and it is not about signals.

### Retail systematic intraday directional trading is not viable

**Barber, Lee, Liu, Odean & Zhang, "Do Day Traders Rationally Learn About Their Ability?"**
(Taiwan Stock Exchange, 1992–2006, 3.7 billion trade records — the largest such study;
[PDF](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf)):

> "On average, day traders lose **7 basis points** on their day trading **before costs** (t = −10.2).
> … trading costs more than triple the losses to **23.9 basis points per day**. Moreover, we observe
> reliably negative gross and net performance in all years but 1992."

> "In aggregate, day trading is a losing proposition; day trading is an industry that consistently
> and reliably loses money."

The companion study — Barber, Lee, Liu & Odean, "The cross-section of speculator skill: Evidence
from day trading" (*Journal of Financial Markets*, March 2014,
[doi:10.1016/j.finmar.2013.05.006](https://doi.org/10.1016/j.finmar.2013.05.006)) — identifies
*"a small subset of day traders (**less than 1% of the day trading population**) predictably earn
profits"* (quoted from the 2017 paper's own summary of it).
Note the crucial detail: day traders lose money **before costs**. They are not merely paying too
much friction — their directional calls are worse than random. This is what being on the other side
of an informed counterparty looks like in aggregate.

### What the profitable participants actually have

**Baron, Brogaard, Hagströmer & Kirilenko, "Risk and Return in High-Frequency Trading"**
(*JFQA* 54(3), 2019, [doi:10.1017/S0022109018001096](https://doi.org/10.1017/S0022109018001096);
[working paper PDF](https://www.cb.cityu.edu.hk/ef/doc/GRU/WPS/GRU%232017-018%20Baron%20et%20al.pdf)).
Regulator-supplied identified data, all Swedish equity venues, 16 HFT firms, Jan 2010 – Dec 2014:

- Median HFT firm: annualised **Sharpe 1.61**, four-factor alpha 9%.
- 90th-percentile firm: annualised **Sharpe 11.1**, four-factor alpha **89%**.
- The differentiator is **relative latency**, causally identified off two colocation upgrades:
  firms that improved their latency *rank* saw improved performance.
- *"new HFT entrants are typically slower, earn lower trading revenues, and are more likely to
  exit."* Revenue concentration is high and **non-declining** despite entry.

**Virtu Financial S-1, filed 2014-03-10** (primary source:
[SEC EDGAR](https://www.sec.gov/Archives/edgar/data/1592386/000104746914002070/a2218589zs-1.htm)):

> "As a result of our real-time risk management strategy and technology, we had only **one losing
> trading day** during the period depicted, a total of **1,238 trading days**."

Their own explanation is in the same document: diversification across thousands of instruments and
geographies, sub-millisecond risk management, and no single asset class over 30% of income. That is
a **liquidity-provision** business — thousands of tiny positive-expectancy round trips per day where
the edge per trade is a fraction of the spread — not a directional forecasting business.

### The honest synthesis

Profitable intraday trading is, in order of importance:

1. **Liquidity provision / market making** — earn the spread, manage inventory, never take a view.
   Requires being at the top of the queue, i.e. latency and colocation. Structurally closed to us.
2. **Latency** — the ES→SPY lead and the LOB signal are both real and both live inside one second.
   Hasbrouck's own delay experiment settles the magnitude: handicap the E-mini by 15 seconds and
   ~90% information share becomes 11–23%. Median ES/SPY arbitrage duration is **7 ms**.
   Structurally closed to us.
3. **Information** — order flow you can see and others cannot (internalised retail flow at the
   wholesalers, prime brokerage flow, client franchise). Structurally closed to us.
4. **Distant fourth: slower, riskier, capacity-constrained anomalies** — overnight drift, carry,
   trend. These *are* open to us. Notably, **all of them are multi-hour to multi-day, not intraday.**

We already found the item in bucket 4 that works: `MES_STRATEGY.md`, the overnight drift with a
trend + vol filter, Sharpe 1.65 (MES) / 2.18 (MNQ), positive in 21 of 22 years. That is not a
consolation prize. **A Sharpe of 1.65–2.18 is at or above the median HFT firm in the Baron et al.
sample**, achieved with no latency, no colocation and no data spend. It is the correct answer to
"how do people make money in this market" for someone in our position.

---

## 9. Data sources, if you still want to buy the null

Every item on the original list is now closed: microstructure (§1), lead-lag (§2), intraday
momentum (§3), auctions and rebalances (§4), expiration mechanics (§5), market internals (§6).

The internals are the only one where you might reasonably still want the null **in your own data**
rather than on someone else's authority — that instinct is what has made this project's findings
trustworthy, so it deserves a budget. This section is that budget. Read §6 first; then spend $4.50,
not $880.

### Data sources — all URLs checked 2026-08-06

**For market internals.** Good news: the data is cheaper and more available than expected. There is
**no free historical $TICK dataset anywhere** — GitHub, HuggingFace and Yahoo were all checked and
all fail (`^TICK` on Yahoo returns HTTP 404; the only GitHub repo with data holds 7 files from April
2014). That is a licensing problem, not a technical one: TICK is vendor-computed off licensed
exchange data. But three cheap paths exist:

| path | cost | what you get |
|---|---|---|
| **1. IBKR TWS API — do this first** | **$4.50/mo** | `Index('TICK-NYSE', 'NYSE')`, `secType='IND'`, plus `TRIN-NYSE`, `AD-NYSE`, `VOLD-NYSE`, at `barSizeSetting='1 min'`. Contract spec confirmed from working production code ([ib_tools](https://github.com/ClimberMel/ib_tools) `code/hist_data_index_multi.py`). The $4.50 is the US Equity & Options Add-On Streaming Bundle, non-professional — consistent across sources but IBKR's own pricing page 403s every fetch tool, so **treat as unverified**. History depth is the open question; one practitioner report says the IB feed only reaches 2014-02-04. |
| **2. Kibot — the best backfill** | **$880 one-time** | [1-minute indexes & indicators since 1998](http://www.kibot.com/historical-data/all-indexes-and-indicators-1-minute-intraday-data.html), lifetime access, 1,200+ series, gzip CSV. Coarser tiers: 30-min $180, 15-min $280, 5-min $580. |
| **3. Sierra Chart** | $26/mo | includes their Historical Data Service; support states `$TICK` at 1-min. Unexamined third option. |

**Kibot symbol quirk, worth knowing before you buy:** there is no literal `$TICK`, `$UVOL` or
`$VOLD` symbol. The reconstructions are exact, not proxies:

```
$TICK = $TINA − $TIND      ($TINA = NYSE issues ticks up, $TIND = ticks down)
VOLD  = $JVNT              (NYSE net volume)
UVOL  = $VINA              DVOL = $DVOL
TRIN  = $TRIN              ADD  = $ADD ($ADV minus $DECL); $ADV / $DECL also available
```

Caveat: every Kibot fact came from rendered page fetches (curl was blocked), and no free sample of
a breadth series was found. **Validate a sample before paying $880.**

**Recommended sequence:** spend five minutes and $4.50 asking IBKR for `durationStr='2 Y'` on
`TICK-NYSE`. Where the bars stop determines everything. If the history is deep enough, you are done
for $4.50/mo. If it is shallow, Kibot's $880 one-time backfill plus IBKR as the forward collector
is ~$880 + $54/yr, and that is the whole budget for settling this question permanently.

Other candidates, for completeness:

| source | URL | note |
|---|---|---|
| Polygon.io → Massive (Stocks) | https://polygon.io/pricing 301s to https://massive.com/pricing | Stocks Basic **$0/mo, 2 years of minute aggregates for all US equities**; Starter $29, Developer $79, Advanced $199. Lets you *build* A/D and up/down volume from constituents. Note their **Indices** product is separate ($49/$99) and sources CME/Cboe/Nasdaq — **no NYSE breadth** |
| HF Data Library | https://hfdatalibrary.com | free, CC BY 4.0, 1,391 US stocks/ETFs, 1-min OHLCV from Dec 2002. **Pre-March-2022 is full consolidated tape; post-March-2022 is IEX only (~2–3% of volume).** Excellent for building breadth 2002–2022 for free, unusable for volume-weighted breadth after |
| Cboe put/call CSVs (free, frozen) | `cdn.cboe.com/resources/options/volume_and_call_put_ratios/` → `pcratioarchive.csv` (1995-09→2003-12), `equitypc.csv` / `totalpc.csv` / `indexpc.csv` / `etppc.csv` (2006-11→2019-10-04), `vixpc.csv` (2006-02→2019-10-04) | verified HTTP 200 with real content; skip 2 header rows. **Gap 2004–2006, and frozen at 2019-10-04.** All daily — **no free intraday put/call exists anywhere** |
| algoseek | https://www.algoseek.com | Extended TAQ Minute Bars **$1,500/mo**, 90 fields/bar including a productised **retail flow** field — the closest thing to the odd-lot/retail-imbalance ask. Full TAQ $1,800/mo |
| Barchart | https://www.barchart.com/stocks/quotes/%24TICK | `$TICK`, `$TRIN`, `$ADVN` resolve; `$ADD` and `$UVOL` 404. ~10 yr of 1-min on Premier, capped 250 downloads/day. **Price unverified** — official URLs 404 and affiliate quotes range $19.99–$39.95/mo; do not trust any figure |
| Alpaca | https://alpaca.markets/data | free tier is IEX-only — **not usable** for breadth |
| Schwab / thinkorswim API | — | **ruled out.** Community client documents index symbols limited to `$DJI`/`$COMPX`/`$SPX`, no internals, minute bars retained ~48 days. `$TICK` exists in thinkScript, i.e. the desktop app, not the API |
| Yahoo Finance | — | **ruled out.** `^GSPC` 1-min works; `^TICK` returns HTTP 404 |
| FirstRate Data | https://firstratedata.com/ | cheap one-off historical intraday bundles |

**For auction imbalance (only if you ignore §4 and pursue it anyway):**

| source | URL | note |
|---|---|---|
| NYSE Pillar Order Imbalances spec v2.2k | https://www.nyse.com/publicdocs/nyse/data/Pillar_Order_Imbalances_Client_Specification_v2.2k.pdf | authoritative schedule: **NYSE closing imbalance publishes 15:50 → close, every second when changed**; core opening 08:00 → open |
| NYSE real-time pricing | https://www.nyse.com/publicdocs/nyse/data/NYSE_Market_Data_Pricing.pdf | **$500/mo access + $2,000/mo non-display** — ~$2,500/mo to feed an algo |
| NYSE TAQ Order Imbalances (historical) | https://www.nyse.com/market-data/historical/taq-order-imbalances | history from **2008-05-14**; price not published, routes to ICE |
| Nasdaq TotalView-ITCH 5.0 spec | http://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf | NOII (message type `I`) disseminates from **09:25** and **15:50**, every 10 s until 09:28/15:55 then every 1 s |
| **Free historical Nasdaq ITCH samples** | https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/ | ~12 free full-day ITCH 5.0 files 2019–2026, plus an NOII-only extract at `/NOII/`. Enough to prototype, nowhere near enough to backtest |
| Databento | https://databento.com/datasets/nyse-integrated · https://databento.com/pricing | best retail historical path — NYSE Integrated includes **auction imbalances from 2018-05-01**; imbalance-only tier from $1,000/mo. Their **$/GB historical rate is genuinely unpublished** (doc pages truncate, `metadata.list_unit_prices` needs auth), so any cost estimate is arithmetic rather than their number — the **$125 free credits** are the only way to price a job |
| Massive (ex-Polygon) imbalances | https://massive.com/pricing | NYSE Order Imbalances $49/mo — **real-time only, no history**, so useless for backtesting |
| LOBSTER | https://lobsterdata.com/ | reconstructs the *continuous* book from ITCH; **does not expose type `I` NOII messages** |
| IEX historical | https://iextrading.com/api/1.0/hist | free T+1 pcap, but IEX auction messages cover IEX-listed securities only — SPY is Arca-listed, QQQ is Nasdaq-listed. **Useless here** |

**Other free/cheap references:**

| source | URL | note |
|---|---|---|
| Cboe options statistics | https://www.cboe.com/us/options/market_statistics/historical_data/ | free daily put/call ratios and volume |
| Cboe equities statistics | https://www.cboe.com/us/equities/market_statistics/ | free |
| S&P index change announcements | https://press.spglobal.com/ | free press releases; the spglobal.com/spdji pages 403 |
| FTSE Russell recon schedule | https://www.lseg.com/en/media-centre/press-releases/ftse-russell/2026/russell-reconstitution-2026-schedule | free; **semi-annual from 2026** |
| Nasdaq-100 index info | https://indexes.nasdaq.com/ | free to read; machine-readable access needs a subscription |

Known-bad URLs, recorded so they are not retried: `nyse.com/market-data/real-time/order-imbalances`
(404), `nasdaqtrader.com/Trader.aspx?id=NOII` (404 — the working spec link is the ITCH PDF above),
`data.nasdaq.com/databases/NHMD` (404), `dtcc.com` ETF page (403), `spglobal.com/spdji` (403).

**Cheapest honest route to market internals:** do not buy a $TICK feed. Pull S&P 500 constituent
minute bars from Polygon/Massive — **the free tier gives 2 years, which is enough for a first
verdict** — and compute advance/decline, up/down volume and an uptick/downtick proxy directly. Full
control of the definition, no vendor lock-in, and **zero spend to find out whether it is worth
spending**. Only escalate to the $29 or $79 tier if the free-tier test shows something.

---

## 10. Ranked recommendations

Ranked by expected value. Note that #1 is a *stop* and #8 is the *start* — if you only act on two,
make it those two.

**1. Stop hunting for intraday direction. (Highest expected value, and it is negative-cost.)**
Every hour spent here has a measured expected value of zero, and now the mechanism is understood at
three levels: the target event happens only 27% of the time; the instrument needs 58% accuracy; and
the best literature offers 51% at one minute decaying to zero by thirty, with the best index-level
result ever published topping out at 54.4%. `FINDINGS.md` established this empirically. This
document establishes that the published literature does not contradict it — it agrees with it, at
every horizon, in every asset, with every data source we cannot afford as well as the ones we can.

**2. Fix the instrument, not the signal.** If any weak-but-real signal ever *is* found, express it
delta-1 (MES/ES/SPY), never in long 0DTE options. The difference in required hit rate is 51% vs
58%. Seven percentage points is larger than any edge realistically available. This also means: if
you re-run the `hunt_*.py` sweeps, re-run them with a 53% bar and a delta-1 cost model, not 55% and
options — but read consequence (2) in section 0 first, because it will not change the answer.

**3. Resolve the strongest remaining hypothesis in `FINDINGS.md` §4.1 — your own discretionary
selection — with ~30 real fills.** `graduation.by_strategy()` is already built for it. This costs
nothing but patience and is the only hypothesis here that a backtest structurally cannot see.

**4. Optional, timeboxed: buy the internals null in your own data for $4.50.** §6 closes this on the
literature — there is no academic $TICK/$TRIN/breadth literature at all, the properly-measured
version of the same variable has R² = 0.0004 (t = 1.58) at five minutes by 2002 *gross of costs*,
and 93 breadth indicators over an average 54-year sample beat nothing after costs. If you still want
it measured here rather than taken on authority — a defensible instinct, and the reason this
project's findings are worth trusting — then do the cheap version: ask the IBKR TWS API for
`durationStr='2 Y'` on `Index('TICK-NYSE','NYSE')` ($4.50/mo, five minutes) and see where the bars
stop. Then one session, judged against the base rate, 3-way split, **non-overlapping bets**, delta-1
costs, expected return not conditional accuracy. **Do not spend $880 on Kibot for this.**

**5. Add the quarterly-witching tilt to `events.json` and move on.** §5d is the only thing that
replicated: −37 bps from 10:00 to the close on triple-witching Fridays (n = 28, t = −1.97, p = 0.041
vs baseline), matching Baltussen/Terstegge/Whelan's published −37.2 bps. It is decaying by half
across our sample and it is four events a year over a six-hour session. Record it as a mild bearish
tilt; do not build around it, and do not express it in options.

**6. Do not build:** VPIN, tick-level OFI, cross-ETF lead-lag, **VIX/VIX-futures or credit/rates/FX
lead-lag**, market intraday momentum, closing or opening auction imbalance, index-rebalance trades,
ETF creation/redemption flow, opex pinning, public put/call ratios, retail/odd-lot imbalance,
pre-FOMC drift. All are killed in §1–§7 — two on our own data tonight, the rest in the literature
with their own authors' numbers. Particular note on five of them:
- **Auction imbalance** looked like the best remaining candidate and it is not close: the
  *aggregate* closing-auction price deviation is **0.93 bps** (§4a) because idiosyncratic
  imbalances diversify away, the stock-level deviation is smaller than the half-spread, and the
  papers that measured it say arbitrage is not profitable.
- **Cross-asset lead-lag is a millisecond phenomenon** (§2b). ES and SPY are *"nearly perfectly
  correlated over the course of an hour or a minute"* (Budish et al., *QJE* 2015); the correlation
  only breaks at 10 ms. The VIX-futures lead is **3 ms** and its own authors call the pair *"too
  synchronized for the lead-lag relation to be traded with a profit."*
- **Opex pinning** does not exist for cash-settled SPX or for SPY (§5a), on the authors' own words.
- **The public CBOE put/call ratio is specifically the part of the signal that does not work**
  (§6d). Pan & Poteshman's result comes from proprietary open-buy volume, and they explicitly show
  the predictability lives in the *non-publicly-observable* component.
- **GEX has never been a directional signal in the literature** (§5b). Every index-level paper uses
  **|return|** as the dependent variable. Our own realised/implied range result is real *and it is a
  variance result*. That is not a disappointment — it means the infrastructure is measuring the
  right thing and was being asked the wrong question.

**7. Grow the thing that works.** `MES_STRATEGY.md` (overnight drift, trend + vol filtered) delivers
Sharpe 1.65–2.18. That is at or above the median HFT firm in Baron et al. (2019) with none of their
infrastructure. The highest-return research direction available is not another intraday signal —
it is finding a *second* orthogonal multi-hour-to-multi-day sleeve to sit beside it.

**8. The one new research direction I would actually fund.** Beckmeyer/Branger/Gayda (§5c) find that
while retail single-leg directional 0DTE trades lose $350k/day in aggregate, *"multi-leg trades and
trades that capture the compensation for volatility and jump risks are significantly more
profitable."* We already have the two hard things this needs: a validated variance signal
(realised/implied 0.843× vs 1.139× on gamma regime, t = −13.2 over 15 years) and 1.37M rows of real
SPXW quotes to price any structure without a model. What we do not have is an efficient harvest —
the condor as configured gives the premium back at the wings. **The question worth a session is not
"which way will it go" but "what is the cheapest structure that monetises a correctly-forecast
range, given real bid/ask?"** That is a search over structures against data already on disk, with a
signal already validated, in the one direction the literature says pays.

---

## Scripts added by this session

All are standalone, use only data already on disk, and print their own conclusions.

| script | what it establishes |
|---|---|
| `scripts/edge_budget.py` | move-size distribution and required hit rate by instrument |
| `scripts/option_drag.py` | measured 0DTE break-even hit rate (58.2% call / 53.8% put) from real quotes |
| `scripts/test_intraday_momentum.py` | Baltussen et al. fails on SPX 2016–2024 (test-split β = −4.69) |
| `scripts/test_intraday_momentum_spy.py` | and fails independently on SPY 2024–2026 |
| `scripts/leadlag_test.py` | apparent cross-ETF lead-lag, t up to 12.5 |
| `scripts/leadlag_trade.py` | which is entirely overlapping-window inflation (50.5% hit, net negative) |
| `scripts/test_witching_drift.py` | the quarterly-witching session drift, the only partial replication (−37.2 bp, t = −1.97, n = 28, decaying) |
| `scripts/lit_search.py` | arXiv / Semantic Scholar / OpenAlex literature helper |
