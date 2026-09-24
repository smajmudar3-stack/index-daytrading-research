# Signal accuracy — 68 factors scored by hit rate and payoff, 1 to 13 weeks

**Written 2026-09-24.** Sholo's brief: forget the dollar target, get the signal right —
"momentum and market factors", "sometimes after earnings there's a sell-off the next day",
"everything related to stock market moves and patterns". Either a high hit rate, or a lower
one whose wins are large. Study: `05_studies/signal_accuracy.py`. Panel: 643,687 name-weeks,
2,200 optionable names, 447 weeks 2018-01 → 2026-08, close ≥ $10 and $10m/day, forward
return in excess of SPY from the next open, one observation per name per week (sampled
every h/5 weeks so the 4- and 13-week horizons do not overlap), three time splits (A
2019–21, B 2022–23, C 2024–26), noise bar √(2 ln N) at N = 59 features per table ≈ 2.9.

## The answer in one table

Hit rate = share of names in the best tenth by the factor that beat SPY over the hold.
Payoff = average win ÷ average loss in that tenth.

| horizon | best hit rate of any factor | typical hit rate | best payoff | factors beyond the noise bar |
|---|---|---|---|---|
| 1 week | 0.505 (FCF yield) | 0.49 | 1.08 | surprise (SUE) t 3.9, buyback yield 3.6, down-day streak 3.2, FCF yield 3.1 |
| 2 weeks | 0.51 | 0.49 | 1.10 | SUE 3.9, buyback 2.8, 25-delta risk reversal |
| 4 weeks | 0.49 | 0.47–0.48 | 1.17 (12-1 momentum) | SUE only, t 3.8 |
| 13 weeks | 0.50 (SUE) | 0.45–0.48 | 1.29 (SUE, 12-month momentum) | SUE only, t 3.5 |

**No factor, pattern or model on this machine calls the direction of an individual stock
right more than about half the time, at any horizon.** The edge that exists is in the size
of the wins, not their frequency: at 13 weeks the best tenth by earnings surprise wins 17.4%
when it wins and loses 13.5% when it loses (payoff 1.29), and that asymmetry is what makes
its average positive. Earnings surprise is the only factor beyond the noise bar at every
horizon and positive in every split. Everything else that survives is either a fundamental
(buyback and FCF yield, positive in all splits at 1–4 weeks, t 2–3.6) or a short-horizon
reversal (last week's return, Bollinger position, RSI, the down-day streak: t 2–3.2 at one
week, sign "buy what just fell", too small to pay a round trip).

## Momentum and market factors, since they were asked for

- **12-1 momentum**: IC +0.024 at 4 weeks (t 1.2), +0.033 at 13 weeks (t 1.0), positive in
  all three splits at 4 and 13 weeks, hit rate 0.46–0.48, payoff 1.17–1.27. Real-looking,
  inside the noise bar on this sample, and the best tenth still underperforms SPY as often
  as it beats it.
- **Residual momentum** (own return with the market stripped out): the strongest price
  factor here, IC +0.040 at 4 weeks (t 2.0), +0.052 at 13 weeks (t 1.7), positive in all
  splits. Also inside the bar.
- **50/200-day stack, price vs 200-day, 52-week high, up-days**: all positive, all t < 1.5.
- **Market regime as a switch.** Split by SPY's 12-month return: in BEAR markets the
  reversal factors jump (last-month return t 2.7, Bollinger t 2.0, hit rates 0.52–0.54 —
  the best hit rates anywhere in the study, on 16–18 dates) and momentum disappears; in
  BULL markets only surprise survives. Split by VIX: with VIX in its top 30%, the
  earnings-reaction factors and one-week reversal clear t 2.3–2.7; with VIX low, nothing
  does. Regimes change WHICH factor works; none of them makes any factor exceed ~54%.
- **The models.** LightGBM (nonlinear, refit every 26 weeks, market state as inputs,
  trained only on realised weeks) and Fama-MacBeth (linear) on all 68 factors:

| model | horizon | IC (t) | top-decile hit | payoff | net of 15 bp/side | splits A / B / C net |
|---|---|---|---|---|---|---|
| Fama-MacBeth | 1 wk | −0.002 (−0.3) | 0.485 | 1.05 | **−8.2%/yr** | −10.7 / −0.5 / −11.4 |
| LightGBM | 1 wk | +0.019 (2.2) | 0.498 | 1.08 | **−3.7%/yr** | −10.5 / +1.7 / −4.1 |
| Fama-MacBeth | 4 wk | +0.005 (0.4) | 0.473 | 1.17 | +1.4%/yr | +0.3 / −3.8 / +6.9 |
| LightGBM | 4 wk | +0.022 (1.3) | 0.484 | 1.18 | +3.5%/yr | +6.0 / +3.3 / +2.2 |
| LightGBM | 13 wk | +0.044 (2.1) | 0.482 | 1.36 | **+6.8%/yr** | +8.8 / −1.6 / +11.6 |

The nonlinear model with 68 inputs and the market state does what the single best input
does: nothing at a week, a few points a year at a quarter, hit rate under 50%. Its top
inputs by use are the market state itself (SPY 12-month, VIX), then gap frequency,
miss-but-rallied, beta and the fundamentals — the same families the tables rank.

## The earnings-day patterns, asked for by name

35,014 earnings reactions, excess over SPY, in percent:

| reaction day | n | day 2 | days 3–5 | days 6–21 | days 22–63 |
|---|---:|---:|---:|---:|---:|
| gap **< −10%** | 2,375 | −0.15 | −0.22 | −0.09 | +0.03 |
| −10 to −5% | 4,107 | +0.02 | −0.07 | +0.06 | −0.58 |
| −2 to +2% | 10,850 | −0.06 | −0.16 | −0.28 | −0.71 |
| +5 to +10% | 4,083 | +0.09 | −0.04 | −0.19 | −0.30 |
| gap **> +10%** | 2,477 | +0.07 | −0.32 | **+0.41** | **+0.49** |

- **"After earnings there's a sell-off the next day."** Not on average. Day 2 after a
  >10% gap up is +0.07%, day 2 after a >10% gap down is −0.15% (t −1.7); 50/50 either way.
  The day-2 return as a factor is t 2.5 at one week, +0.06% in the best tenth — a real
  but tiny continuation, not a fade.
- **"Beat but sold off" (11,577 cases):** days 6–21 −0.00%, days 22–63 −0.29%. The market
  does not give the beat back; the name just drifts like everything else.
- **"Miss but rallied" (3,136):** days 22–63 −1.06%. The rally does not hold.
- **Run-up into the print then a big move:** ran up and gapped up: +0.26% over days 6–21,
  +0.59% over 22–63; ran up and gapped down: −0.24% / +0.45%. Nothing a trade can use.
- **Move larger than the straddle implied (>2×):** up: days 6–21 **+0.75%** (n 181), then
  −2.6% over 22–63; down: −0.33% then −1.35%. Small samples, opposite signs by window.
- The only earnings pattern that pays is the one already in the book: a large surprise
  keeps drifting for a quarter, and the best tenth's hit rate is still 0.50.

## What this changes in the stock book

The book's exact rule — names that reported in the last **10** sessions, top fifth by
surprise, held 63 sessions — re-measured on weekly cohorts:

| cohort window | pick rule | 13-week excess, all | A / B / C | hit |
|---|---|---:|---|---:|
| 10 sessions | top quintile | +1.21% (t 0.6) | +3.60 / +0.87 / **−0.57** | 0.445 |
| 10 sessions | top 25 names | +0.77% | +3.29 / +0.16 / **−0.89** | 0.447 |
| 21 sessions | top 25 names | +1.80% (t 1.1) | +4.72 / −0.01 / +0.91 | 0.455 |
| **63 sessions** | **top 25 names** | **+4.24% (t 2.3)** | **+8.98 / +0.12 / +3.79** | 0.487 |
| 63 sessions | top 25, 4-week hold | +1.36% (t 2.3) | +2.83 / +0.10 / +1.22 | 0.502 |

The long-only leg of the surprise effect has been weak since 2022 when the cohort is only
the last two weeks' reporters, because a fifth of ~60 names is not an extreme surprise.
Ranking every name still inside its 63-session drift window and taking the 25 largest
surprises picks from ~1,200 reporters, and that version is positive in all three splits
with a payoff of 1.6. The bottom-25 leg is ~0 either way, so this is not a long/short
result wearing a long-only label. The `+2.84% Q5−Q1` in `fundamentals.md` stands; it was a
spread, and the long side alone needs the wider window. `swing_stock.py` now uses
`COHORT_SESSIONS = 63` with the 25-name cap. This is one change to a horizon the drift
was already measured on, not a search over parameters; the 10-session result is kept here
so the change can be judged against it as the ledger fills.

## Per-name weights, tested and rejected (2026-09-24)

Sholo's design was to weight each factor by how much it has moved THAT stock.
`05_studies/per_name_weights_test.py` fit a ridge regression per name on the name's own
past (at least two years of its own months, forward returns known at the time) and
ranked on the prediction, against one set of weights for everyone and an unweighted
composite, same ten factors, four-week hold:

| weights | dates | IC (t) | top-decile hit | payoff | net/yr | IC by split |
|---|---:|---:|---:|---:|---:|---|
| equal weight, no fitting | 110 | **+0.034 (2.6)** | 0.485 | 1.12 | +0.4% | +0.035 / +0.046 / +0.032 |
| pooled, Fama-MacBeth | 98 | +0.014 (1.0) | 0.478 | 1.09 | −0.9% | −0.005 / +0.053 / +0.005 |
| **per-name, ridge on own past** | 85 | +0.015 (0.9) | 0.482 | 1.12 | +1.8% | +0.016 / +0.029 / +0.004 |
| blend of the two | 85 | +0.020 (1.2) | 0.479 | 1.09 | −0.8% | +0.002 / +0.055 / +0.006 |

The per-name weight's sign agreed with the pooled sign on 36–65% of names depending on
the factor — a coin flip — so a name's "own" weights are its own past accidents. Equal
weights on the inputs that survived is the rule; this matches Lewellen (2015).

## The swing ranker

What the weekly swing panel now produces, in shares, alongside the options cards: every
name that reported in the last 63 sessions, ranked on the mean rank of earnings surprise,
residual momentum and 12-1 momentum, the top 25 issued weekly and held 21 sessions.
Measured on the same panel (non-overlapping 4-week dates): **+0.84% over SPY per hold, hit
rate 0.49, wins 1.24× losses, 54% of cohorts positive, 42% turnover, +9.3%/yr net; splits
+0.87 / +0.79 / +0.87.** Surprise alone is +1.10% on average and +0.12 in 2022–23; the
three-input rule is the smaller, steadier one. At 63 sessions it is +3.71%/hold (t 2.4),
75% of cohorts positive. Live: `04_live_system/swing_ranker.py`; ledger; desktop ping
when a cohort is issued. The stress book rides on the same panel and, on the day it
issues, is the decision on the Today page.

## Plain reading

Nothing here predicts an individual stock's direction more than about half the time. What
can be measured is that certain groups of names, held for a quarter, win bigger than they
lose: the biggest earnings surprises first, then cash-returning companies, then residual
momentum. That is a 5–10%-a-year-over-the-index edge with a coin-flip hit rate, which is
what every published factor is once you pay to trade it. The models do not change that; the
regimes change which factor is on, not how often it is right.
