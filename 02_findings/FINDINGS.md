# What Was Actually Established — 2026-08-05/06

A full session of edge-hunting for intraday 0DTE direction. This is the honest record, written so the
same ground does not get re-searched and so nothing here gets quoted at a level of confidence it does
not deserve.

---

## The headline

**No exploitable short-horizon directional edge was found in SPX/NDX, and the mechanism is now
understood rather than merely unmeasured.** Every apparent edge either failed to replicate, or
replicated and was exactly offset by the cost of expressing it.

Separately, and importantly: **the previously "validated" iron-condor edge does not survive real
option quotes.** That finding invalidates the central claim the dashboard was making all week.

---

## 1. The condor edge was a pricing-model artefact

`RULES.md` reported +3.7%/trade, 91% win, t=+7.4 for the 0DTE iron condor gated on prior-close dealer
gamma. Those P&L numbers came from Black-Scholes with a **linear skew approximation**.

Re-run on **1,919 sessions of actual SPXW bid/ask** (2016-09 → 2024-05, no pricing model anywhere):

| entry | shorts | n | win% | avg/trade | credit % of width | t |
|---|---|---|---|---|---|---|
| 10:30 | 0.5% | 859 | 72% | −0.71% | 21.7% | −0.39 |
| **11:00** | 0.5% | 853 | 73% | **−1.70%** | 19.8% | −0.99 |
| 12:00 | 0.7% | 796 | 86% | **+0.95%** | 11.0% | +0.82 |
| 13:00 | 0.5% | 832 | 79% | −0.60% | 13.7% | −0.45 |

Best cell is +0.95%/trade at t=+0.82 — not significant. The 11:00 entry the live system used is
**negative**. No year-over-year consistency. The model overstated the credit by mispricing the wings,
and that inflation *was* the entire edge.

**Status: the condor is approximately break-even. Do not quote +3.7%.** `rules.py` and the dashboard
carry corrections.

The underlying *range* finding still holds — realised/implied 0.843× on high-gamma days vs 1.139× on
low, t = −13.2 over 15 years. It is real. It simply does not convert to profit at market prices, which
is itself informative: the market has it priced.

---

## 2. The direction hunt — what was tested and what it showed

| avenue | scale | result |
|---|---|---|
| Technical indicators, all combinations | 56 features, 220 conditions, thousands of combos, 3-way split | **0** combinations clear 55% on train AND validate |
| Cross-symbol replication of the best rule | QQQ / SPY / IWM, no re-tuning | works on QQQ only (1 of 3) — fitted |
| Real 0DTE order flow | 16,152 obs, 1,919 sessions, traded greeks in $ | **null**; `flow_z` sign flips between splits |
| Candlestick + price-action library | ~30 patterns, edge measured over base rate | **0** patterns hold ≥+4pp on all three splits |
| New-low continuation | 1,919 sessions, plateau across 4 thresholds × 3 horizons | 54–62% "accuracy" → **zero** return (see below) |
| Intraday IV skew + real gamma profile | 18,071 bars, 1,919 sessions, 30m/60m/90m | **null** once look-ahead removed; nothing stable >3bp |

### The most instructive failure

New session low on an expanding 30-min bar looked excellent: 54–62% directional accuracy, stable
across all three time splits *and* all four move thresholds — a plateau in two dimensions, on 1,919
sessions spanning 2016–2024. It cleared the 60% target at 0.32%/90m.

Traced through four instruments, it is worth nothing:

| expression | win% | avg | note |
|---|---|---|---|
| short delta-1 (no theta, no skew) | 47.6% | **+0.00%** (t=+0.24) | the decisive test |
| long put (real quotes) | 34% | −6.56% | skew + theta |
| put debit spread | 37% | −11.5% | worse |
| call credit spread | 57.9% | **−0.00%** (t=−1.72) | wins more often, exactly offset |

**Why the 60% was illusory:** the accuracy metric was *conditional on a clean move occurring*. Of bars
where a clean one-sided move happened, 54–62% went down — genuinely true. But most signal bars produce
no clean move, and once those are included (as they must be, since you are in the trade) expected
return is zero. **A conditional accuracy statistic is not an expected return.** This is the single most
important methodological lesson of the session.

The call credit spread is the cleanest illustration of market efficiency found here: 57.9% win rate,
exactly zero return. You win more often and win less, by precisely the offsetting amount.

---

## 3. Methodology notes worth keeping

- **Two-way splits are not enough** after heavy searching. A `gz>med + rvol>med` rule showed 61.5% on a
  train/test split; under train/validate/test it collapsed, and adjacent holding periods (25m, 30m)
  fell to 42.9% while 20m held. Adjacent-cell collapse is the signature of noise.
- **Judge patterns against the base rate, not 50%.** Clean fast moves are down 54–59% of the time
  (leverage effect), so any bearish pattern scores ~58% for free.
- **Fixed strike, not fixed moneyness.** Tracking `mnes_rel` across bars silently follows a *different*
  contract as spot moves; it produced an impossible 3.9% win rate before being caught.
- **`groupby.transform("mean")` on a session is look-ahead.** Z-scoring intraday IV against the *whole
  day's* mean produced a +14.2bp forward return at **t = +15.64** — which is absurd for an efficient
  market and was pure leakage: IV high relative to the full-day average mechanically implies the rest
  of the session was calmer, i.e. the market recovered. Re-run with an **expanding, shifted** mean and
  std, the effect vanishes entirely and nothing is stable at any horizon. Any intraday normalisation
  must use `expanding().mean().shift(1)`, never a whole-group transform. **A t-stat above ~10 on
  intraday index direction should be treated as a bug report, not a discovery.**
- **Holding period changes everything.** The same +20 SPX point move is +44% on an ATM 0DTE call sold
  after 15 minutes and −12% held to the close. Open-to-close backtests say nothing about a
  minutes-held strategy — the −11%/trade figure quoted early in the session was the wrong number for
  the trade actually being made.

---

## 3b. The literature independently confirms the empirical null — and explains it

A separate deep literature review (`RESEARCH_DIRECTION.md`, ~970 lines, primary sources verified) was
run against exactly this question. It reaches the same conclusion by a completely different route, and
supplies the mechanism the backtests could only observe.

**Measured lead time today is ≤10 milliseconds on every axis:**

| pair | lead | source |
|---|---|---|
| ES futures → SPY | 7 ms median arb duration (was 97 ms in 2005) | Budish, Cramton & Shim 2015 *QJE* |
| stock → stock (megacaps) | <10 ms by 2021-22 (was seconds in 2000-05) | Anderson 2022 *JBFE* |
| VIX futures → SPX futures | **3 ms** median, and only in the high-VIX regime | Bangsgaard & Kokholm 2024 *JFM* |

At a 5–30 minute horizon the effect is not small, it is **mathematically absent**. Budish et al. state
the instruments are "nearly perfectly correlated over the course of an hour... or a minute."

**Four separate papers self-report failure after costs** — this is not my inference:
- Bangsgaard & Kokholm: *"the two markets are too synchronized for the lead-lag relation to be traded
  with a profit"* (holding periods swept 5 ms → 5 min, both midquote and bid/ask fills).
- Huth & Abergel 2014 *J.Empirical Finance*: *"We reach 60% of accuracy when forecasting the next
  midquote variation of the lagger... HOWEVER, WE CANNOT MAKE ANY PROFIT OF THIS EFFECT BECAUSE OF THE
  BID/ASK SPREAD."* **This is precisely the result found here** — 60% directional accuracy, zero money.
  It is a published, peer-reviewed instance of the same trap.
- Brooks, Rew & Ritson 2001: 10-min FTSE spot/futures, gross 15.6%/mo → *"none of the active trading
  strategies can outperform the benchmark passive strategy"*; 0.25% gross vs 1.7% costs.
- Cont, Cucuringu & Zhang 2023 *Quantitative Finance*: order-flow imbalance gives ~87% CONTEMPORANEOUS
  in-sample R², and **negative out-of-sample R² at 1 minute ahead for every model tested** (−0.10% to
  −0.37%, all worse than forecasting zero). That 87% → below-zero gap is the entire field in two
  numbers, and it independently corroborates the null order-flow result found here on 16,152 bars.

**The structural reason VIX cannot predict SPX intraday:** causality runs returns → volatility, for
*days*. Bollerslev, Litvinova & Tauchen 2006 (tick S&P futures, 7.1M transactions): the reverse
cross-correlations are "generally negligible" and there is "little or no evidence for a delayed
volatility feedback effect." Dufour, Garcia & Taamouti 2012: "the volatility feedback effect is found
to be negligible at all horizons." VIX is a deterministic function of SPX option prices, so a lagged
VIX is stale contemporaneity, not a lead.

**How fast the lead decayed, quantified.** Hasbrouck 2003 (*JF*) measured price discovery between the
E-mini, the pit contract and the ETF at **1-second** bins over 64 days in 2000: ES information share
**~85–94%** vs SPY **~1–4%** (NQ ~84–88% vs QQQ ~6–9%) — his own phrase, "roughly 90% of the price
discovery." But his artificial-delay experiment is the number that matters:

| handicap applied to ES | ES information share |
|---|---|
| 0 s | 0.730 – 0.874 |
| 5 s | 0.452 – 0.752 |
| 10 s | 0.214 – 0.469 |
| **15 s** | **0.114 – 0.225** |

**Delay the E-mini by fifteen seconds and its dominance is gone** — even in 2000, on floor-era data,
the edge was worth single-digit seconds. Budish's 7 ms (2011) and Anderson's <10 ms (2021-22) are the
same decay curve, twenty years on. Garrison, Jain & Paddrik (OFR WP 19-04) find ES/SPY spillovers
"generally short lived, lasting no longer than a second."

**A third trap, and it is the one most likely to bite us: BIN WIDTH DETERMINES THE ANSWER.**
Several papers report that ETFs now dominate price discovery and futures are "insignificant" — Buckle
et al. 2018 puts SPY at 30.5% vs ES at 3.5%. That result is sampled at **1-minute bars**, and the
authors disavow it themselves: their innovation correlations are 0.86–0.95 and they write that "the
estimated upper and lower bounds are far apart for most cases, indicating the instability of the model
estimation" and "it would be safe to conclude that the IS results were inaccurate." At 1-minute
sampling a several-second lead is invisible *by construction*.

The honest arc is therefore **not** "futures used to lead, now ETFs do." It is: ES ~90% at 1-second
resolution in 2000, worth seconds even then; roughly even with SPY at 1-second by 2019 (Manchester
2023 thesis, all 252 days of 2019 — though the error-correction still shows "the SPY market is
learning from the E-mini"); and every claim of ETF dominance comes from bin widths too coarse to see
the effect. **Any lead-lag claim without a stated bin width is uninterpretable.** This is the same
class of error as the two found in our own work — conditional accuracy mistaken for expected return,
and a whole-session `transform` used as a past-only normaliser.

**Two further traps to watch for in anything cited in future:**
- *Daily-to-intraday bait-and-switch.* Bennett-Cucuringu-Reinert (Sharpe 0.62) is **daily** CRSP data,
  not intraday, and excludes costs on 2.4bp/day returns. Lo-MacKinlay is weekly; Chordia-Swaminathan,
  Park/VVIX, Bevilacqua/SKEW, Bollerslev VRP are all daily-to-quarterly. All are routinely miscited.
- *Contemporaneity dressed as lead-lag.* Andersen/Bollerslev/Diebold/Vega: stock, bond and FX futures
  respond to macro news near-instantaneously, so cross-asset intraday co-movement is a common response,
  not a lead. This is the single most common way these backtests fool people.

The one genuine minutes-scale cross-asset effect (Kurov et al. 2019 *JFQA*: pre-announcement drift
starting ~30 min before release) is worth ~$21M/yr **market-wide across all informed traders**, and
requires detecting the drift rather than knowing the surprise.

## 4. Open questions — the only things that could still change the answer

1. **The owner's own discretionary selection.** Every backtest fires a mechanical trigger on ~65% of
   sessions; a person takes a handful. If the edge is in *which* setups get skipped, no backtest here
   can see it. `graduation.by_strategy()` splits RANGE vs DIRECTIONAL and is ready for real fills.
   ~30 trades would answer it. **This is the strongest remaining hypothesis.**
2. **Tick-level order flow.** What was tested was 30-minute aggregates. `emlama/gex-backtesting` has
   free quote-matched trade-side classification (513 days, 2024–2026). `uw_archive.py` now captures UW
   flow every cycle going forward.
3. **The direction-research agent** did not finish (session limit) and can be resumed.

---

## 5. Data acquired this session

- `data/spxw/data_opt.parquet` — **1.37M rows**, 1,919 sessions of real SPXW quotes, 2016-09 → 2024-05,
  30-min grid, 41 moneyness buckets: mid, bid-ask, IV, full greeks, OI, and traded greeks in dollars.
  This is the single most valuable asset added — it makes modelled P&L unnecessary for any future test.
- `data/minute/IWM/` — 8 months, for cross-symbol replication.
- `data/uw_flow.jsonl` — order-flow archive, accumulating from now.
