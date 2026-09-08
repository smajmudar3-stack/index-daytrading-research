# Goal feasibility: $5,000 → $50,000, then ~15%/year

**Answer first, because it is the honest one and it is not what the goal assumes.**

The survivors support roughly **15%/year at a ~59% maximum drawdown**. That is the phase-two
goal met almost exactly. It is also the reason phase one does not work on the stated
timetable: at 15.3%/year, $5,000 reaches $50,000 in **16.2 years**. Not one, not three, not
five. Even the optimistic end of the edge's confidence interval takes 9.1 years.

Every route that compresses 16 years into 3 requires leverage the Monte Carlo prices as
ruin, and the leverage is not available anyway: Reg-T caps a held position at 2x, and the
only instruments that go beyond it are option structures this repo has already measured as
losing money.

This is verdict **(c)** from the spec: *the survivors do not support the goal, and the
realistic expectation is ~15%/year* — which is a good outcome, just not a fast one.

---

## 1. What the target actually demands

Arithmetic, so nothing in it can be wrong.

| horizon | required CAGR | leverage on the measured edge | the worst observed trade at that size |
|---|---:|---:|---:|
| 1 year | 900.0% | 70.6x | −1105% |
| 2 years | 216.2% | 28.2x | −441% |
| 3 years | 115.4% | 17.5x | −273% |
| 5 years | 58.5% | 9.9x | −155% |
| 10 years | 25.9% | 4.7x | −74% |
| 16.5 years | 15.0% | ~2x | −31% |

The last column is the whole story. A single trade of the size the three-year target needs
would end the account 2.7 times over, and that is not a tail scenario — it is the worst
trade that *actually happened* in the sample.

---

## 2. What survived, and what it is worth

`WHAT_WORKS.md` lists three survivors. Only one is a tradeable timing signal, and it was
rebuilt from raw closes here rather than taken on trust.

**VIX backwardation inside a golden cross**, rebuilt from ^VIX / ^VIX3M / SPY,
2006-07-17 → 2026-06-17:

| | |
|---|---:|
| non-overlapping trades | 56 over 19.9 years (**2.8/year**) |
| mean per trade | **+1.80%** |
| standard deviation | 4.96% |
| t-statistic | **+2.71** |
| 95% CI | [+0.50%, +3.10%] |
| win rate | 73.2% |
| worst / best | −15.7% / +11.3% |
| excess over the unconditional 21-day return | **+1.28pp** |

The rebuild reproduces the documented "+1.3 to +1.8pp" at +1.28pp, so the published number
is real and this analysis is measuring the same thing.

The other two survivors contribute no growth path:

- **Short interest** (IC −0.107 at 63d, n=13,219) is a *cross-sectional* ranking signal. It
  says which names underperform relative to each other, which needs a long/short book and a
  short locate. `data/swing/panel.parquet` carries OHLCV only, with no short-float column,
  so there is no series to bootstrap and no honest way to put a number on it here.
- **Low dealer gamma** is explicitly a regime *filter*. It changes which structure fits, not
  whether to be in the market. No standalone return series exists to compound.

---

## 3. The finding that decides everything: trade-level ≠ account-level

A +1.80% mean over 21 days sounds like it compounds. It fires **2.8 times a year**.

| configuration | CAGR | max drawdown | $5,000 becomes | time in market |
|---|---:|---:|---:|---:|
| SPY buy and hold | 11.51% | 55.2% | $44,795 | 100% |
| **signal only, cash otherwise** | **4.73%** | 33.7% | $12,666 | 23% |
| **always long, 2x while the signal is on** | **15.28%** | 58.8% | **$87,540** | 100% |
| always long, 3x while the signal is on | 17.61% | 76.1% | $130,857 | 100% |

**Traded on its own, the repo's best signal returns less than half of doing nothing.** Not
because the signal is wrong — it is right 73% of the time — but because being right 2.8
times a year cannot beat being invested 250 days a year. The account is in cash for 77% of
the sample and misses the drift that produces most of the return.

Its value is as an **overlay**: stay long, and add exposure when it fires. That is worth
**+3.77pp/year** over buy-and-hold, which matches the arithmetic (+1.28pp excess × 2.8
firings × 2x exposure ≈ +3.6pp).

> **A correction worth recording.** The first pass at this table reported the standalone
> configuration at 0.5%/year. That was an off-by-one in the hold mask — it counted the
> return *into* the entry day, which happens before entry, and missed the return into the
> exit day. `configurations()` now computes the same thing two ways, trade-level and
> path-level, and asserts they agree to 1e-6. They do, at 2.533x.

### The honest range

The per-trade edge has a 95% CI of [+0.50%, +3.10%]. Carried through at 2x exposure and 2.8
firings a year, the overlay's alpha is somewhere in [+2.8pp, +17.4pp]/year, so the plausible
CAGR band is **14.3% to 28.9%**.

| | CAGR | years to $50k |
|---|---:|---:|
| lower CI | 14.3% | **17.2** |
| point estimate | 15.3% | **16.2** |
| upper CI | 28.9% | **9.1** |

Even the top of the confidence interval does not reach $50,000 inside five years.

---

## 4. Monte Carlo — 10,000 paths from $5,000

Block bootstrap on the real trade series (block length 3, preserving clustering), a fitted
Student-t tail overlay on 15% of draws, and historical shock weeks (2018-02, 2020-03, 2022,
2024-08) injected at their historical frequency. Costs 10bp per trade per unit of leverage.

**Probability of reaching $50,000, standalone signal:**

| sizing | leverage | 1y | 2y | 3y | 5y | 10y | ruin @10y | P(50% DD) @10y |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| unlevered | 1.00x | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 2.4% |
| 0.25 Kelly | 1.16x | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 5.4% |
| Reg-T max | 2.00x | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 1.3% | 36.7% |
| 0.50 Kelly | 2.31x | 0.0% | 0.0% | 0.0% | 0.0% | 0.2% | 3.3% | 49.4% |
| full Kelly | 4.62x | 0.0% | 0.0% | 0.0% | 1.2% | **10.7%** | **47.4%** | 91.7% |

Full Kelly is the only sizing that reaches the target with any meaningful probability, and
it does so by coin-flipping the account: **10.7% chance of $50k against a 47.4% chance of
ruin**, with a 91.7% chance of a 50% drawdown along the way. It is also unreachable — 4.62x
on a 21-day hold is not available in a Reg-T margin account.

**Sensitivity at 0.5 Kelly over 10 years** — the numbers degrade the way published signals
actually degrade:

| scenario | P($50k) | ruin | median terminal |
|---|---:|---:|---:|
| as measured | 0.1% | 3.6% | $6,457 |
| edge shrunk 50% (post-discovery decay) | 0.0% | 8.1% | $4,088 |
| 2x costs | 0.1% | 4.0% | $6,051 |
| both | 0.0% | 9.2% | $3,826 |
| shocks at 2x historical frequency | 0.0% | 18.7% | $3,108 |

---

## 5. The safe path

Largest sizing that keeps ruin below 5% over 10 years: **2.25x**.

- ruin 3.3%
- P($50,000 in 10 years) **0.1%**
- median terminal equity **$6,661**
- median max drawdown 48%
- implied CAGR from the median path **2.9%** → **80 years to $50,000**

The standalone signal at survivable size is a 3%/year strategy. That is the direct answer to
"what sizing keeps ruin under 5%, and how long does that path take".

---

## 6. Phase two: ~15%/year from $50,000

| sizing | leverage | P(≥15%/yr over 5y) | over 10y | median max DD | ruin |
|---|---:|---:|---:|---:|---:|
| unlevered | 1.00x | 0.1% | 0.0% | 22.6% | 0.0% |
| 0.25 Kelly | 1.16x | 0.6% | 0.0% | 26.0% | 0.0% |
| Reg-T max | 2.00x | 14.1% | 4.8% | 43.6% | 1.6% |
| 0.50 Kelly | 2.31x | 20.4% | 9.0% | 49.8% | 3.6% |

Read against §3: the **2x overlay** configuration delivered 15.28%/year historically. The
Monte Carlo says that outcome is real but far from assured — roughly a one-in-five chance of
averaging 15%+ over five years, with a coin-flip chance of a ~50% drawdown on the way.

---

## 7. Small-account constraints — and why they are not the binding ones

Modelled as specified, and the conclusion is that they barely matter here:

- **PDT is irrelevant.** The surviving signal is a 21-day hold. A 21-day hold is not a day
  trade, so the 3-per-5-business-days limit never binds. PDT only constrains intraday
  strategies, and this repo measured ~340,000 intraday tests with a survivor count at or
  below what chance produces. There is no intraday edge for PDT to get in the way of.
- **Cash-account settlement is irrelevant** at 2.8 trades a year; T+1 never binds.
- **Micro futures (MES/MNQ) are irrelevant** for the same reason — they are an intraday
  vehicle for an intraday edge that does not exist here.
- **Contract granularity is fine.** The signal trades SPY, so $5,000 buys whole shares with
  no minimum-size problem. SPX is unreachable at $5k, but nothing here needs it.
- **Costs are small but not nothing.** At 10bp per trade and 2.8 trades a year the drag is
  ~0.3pp/year unlevered — material against a 3.8pp alpha, which is why the sensitivity table
  runs a 2x-cost case.
- **Leverage beyond 2x is unavailable, not merely aggressive.** Reg-T caps a held position at
  2x. Going further means options, and the option structures this repo measured are negative:
  debit spreads −11.12%/trade across 230,884 real-fill trades, long straddles −5.69%, long
  strangles −11.54%. Leveraging with an instrument that has a measured negative expectancy
  does not raise the CAGR, it lowers it and adds the ruin risk on top.

---

## 8. Decay monitoring, and when to cut

The edge rests on 56 trades. That is a small sample and it must be watched as such.

- **Track every firing.** Log entry date, exit date, realised 21-day return, against the
  unconditional 21-day return of the same window. `04_live_system/weekly_book.py` already
  does the equivalent for the weekly cards; the same discipline applies here.
- **Cut sizing in half** when the trailing 10 firings produce a mean below zero. Ten firings
  is ~3.5 years, so this is a slow alarm — that is inherent to a signal firing 2.8 times a
  year and is itself a reason not to size aggressively.
- **Stand the overlay down** when the trailing 20 firings' mean excess drops below +0.50pp,
  the lower bound of the current 95% CI. At that point the measured edge is no longer
  distinguishable from zero on its own evidence.
- **Re-examine on regime change.** VIX3M history starts in 2006, so the sample contains two
  major stress regimes (2008, 2020). A third with a different shape — a slow grind rather
  than a spike — is the scenario most likely to break the signal, because backwardation is a
  spike phenomenon.

---

## 9. What this means in one paragraph

The best thing this repo found is a volatility-term-structure overlay on a long index
position, worth about 3.8 percentage points a year over buy-and-hold, at the cost of a
drawdown in the high fifties. Run properly, that is a ~15%/year strategy — genuinely good,
and exactly the phase-two target. It reaches $50,000 from $5,000 in about 16 years. There is
no configuration in the tested set that reaches it in one, two, three or five years at a
survivable risk of ruin, and the fastest honest path to a bigger account is contributing
capital to it rather than trying to make $5,000 grow ten-fold by trading.

---

*Generated by `05_studies/engine_e_feasibility.py`. Runs only on validated survivors; the
goal never loosened a gate. Every growth number above is reported next to its probability of
ruin, as required.*
