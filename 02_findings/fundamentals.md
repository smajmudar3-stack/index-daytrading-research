# Company-specific factors — earnings surprise, cash flow, buybacks, dilution

**Status: CURRENT. Measured 2026-09-21** on the Dolt earnings and statement tables joined to
the option-panel universe (close ≥ $10, dollar volume ≥ $10m), prices split-adjusted,
returns in EXCESS of SPY from the next session's open. Reproduce:
`05_studies/xsec_fundamentals_test.py`.

The one-line verdict: **these are one-to-three-month STOCK effects.** None of them says
anything at five days, so none of them belongs in the weekly options vote, and every one
of them is worth more as a tilt on the index overlay than as an option trade.

## 1. Earnings surprise size (post-earnings-announcement drift)

SUE = (reported EPS − consensus) / price on the announcement day. 33,755 announcements,
1,962 names, 223 weeks, 2020-01 → 2026-07. Quintiles within each week's cohort of
announcers; the spread is a same-week comparison, t over weeks.

| horizon | Q5 (best beat) − Q1 (worst miss) | t | weeks > 0 | A 2019-21 | B 2022-23 | C 2024-26 |
|---|---:|---:|---:|---:|---:|---:|
| 5 sessions | +0.14% | 0.7 | 52% | −0.53% | +0.55% | +0.31% |
| 10 sessions | +0.23% | 0.8 | 55% | −0.96% | +0.85% | +0.63% |
| 21 sessions | +0.75% | 2.0 | 58% | −0.05% | +0.86% | +1.25% |
| **63 sessions** | **+2.84%** | **4.3** | **63%** | +2.39% (t 1.6) | +2.95% (t 2.6) | +3.10% (t 3.4) |

Bernard & Thomas (1989) reproduced: the drift is real, it is the SIZE of the surprise, and
it takes a quarter to play out. At a week it is nothing. This is the strongest effect found
in this whole exercise and it is a 63-day stock effect, which is why `pead` in the weekly
vote stays at 0.10 (that is the sign-of-reaction version at 5 days, IC 0.018) and why the
surprise itself is registered at the quarterly horizon, not the weekly one.

## 2. Capital allocation and quality, monthly cross-sections

Quarterly statements lagged 60 days from period end (the table carries period end, not the
filing date; unlagged it is look-ahead). Rank IC per month-end against the next 21 and 63
sessions' excess return. 104 months, ~2,100 names. 18 tests, noise bar |t| ≈ 2.4.

| feature | sign | IC @21d | t | IC @63d | t | A | B | C 2024-26 |
|---|:-:|---:|---:|---:|---:|---:|---:|---:|
| **buyback yield** (net repurchases / mcap) | + | +0.028 | 3.4 | +0.028 | 3.5 | +0.011 | **+0.084** | −0.011 |
| **FCF yield** (2022→ only) | + | +0.038 | 3.0 | +0.055 | 3.5 | — | +0.059 | +0.007 |
| net share issuance | − | +0.018 | 2.2 | +0.025 | 3.0 | +0.036 | **+0.078** | −0.015 |
| margin change, y/y (gross / net) | + | +0.007 | 1.0 | +0.008 | 1.3 | ≈0 | ≈0 | +0.025 to +0.037 |
| net margin, sales growth, dividend yield | + | ≤ +0.009 | < 1.1 | ≤ +0.009 | < 1 | | | |
| gross margin | + | −0.003 | −0.3 | −0.010 | −1.2 | | −0.061 | |

Three clear the bar: buyback yield, FCF yield, and (negatively) net issuance — the same
family, "is the company returning cash or raising it", and the published sign (Ikenberry et
al; Pontiff & Woodgate 2008). But read the splits: the family did its work in 2022–23 (the
value year) and went flat to negative in 2024–26. A factor that pays in one regime and not
the next is a regime, not a constant. Margin improvement shows the opposite pattern:
nothing until 2024–26, when it is the one that works. That is growth-versus-value in a
table, and it is why neither gets a large fixed weight.

## What this changes

- `signal_weights` gains `sue` (earnings surprise, 63-day) and `capital_return` (buyback
  yield / FCF yield / net issuance, 21–63-day) as measured entries with **horizon tags**, and
  `combine()` is not the place they act: the weekly vote must not consume a quarterly signal
  (the registry already says this about short interest). They are for the index overlay's
  stock tilt, which is the next thing to build: hold the 2× index per `goal_feasibility.md`,
  and overweight the top surprise / top capital-return names in the stock sleeve.
- Nothing here changes the weekly options book, and nothing here is a 0DTE input.
- **Built 2026-09-22:** `04_live_system/swing_stock.py` is the live version — the top
  quintile of the last ten sessions' reporters by surprise/price, in shares, 63-session
  hold, with a ledger filled at the next open and marked against SPY. Its record is the
  forward test of §3's +4.7%/yr.
- **2026-09-24, from `signal_accuracy.md`:** the LONG-ONLY leg of this effect, measured on
  weekly cohorts of the last ten sessions' reporters (the book's first rule), is +1.2% a
  quarter overall and −0.6% in 2024–26; the +2.84% above is the Q5−Q1 SPREAD and the short
  side carries much of it. Widening the cohort to every name inside its 63-session drift
  window and taking the 25 largest surprises gives +4.24% a quarter (t 2.3), positive in all
  three splits, bottom-25 leg ≈ 0. `swing_stock.py` uses that rule now.

## What it does NOT establish

- The SUE quintiles' absolute excess returns are all negative except Q5 because an
  equal-weighted mid-cap cohort lagged SPY over 2020–2026; the SPREAD is the result.
- Free-cash-flow coverage starts in 2022 in this table, so its A split is empty.
- No transaction costs are charged; at monthly turnover in liquid names that is ~10–20 bp a
  month against a 63-day spread of 2.8%, which does not change the answer.

## 3. Compounded as a portfolio — the "any horizon, any stock" answer

`05_studies/xsec_portfolio_test.py`: top decile of each signal, equal weight, rebalanced
monthly, held next-open to month-end, 15 bp a side on actual turnover, 2× row levered at a
6% borrow. 2019-01 → 2026-06.

| portfolio (top decile, long only) | CAGR 1× | max DD | CAGR 2× | max DD 2× | excess over SPY | t |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 14.8% | −20% | 20.9% | −41% | — | — |
| earnings surprise | 17.8% | −27% | 21.8% | −54% | +4.7%/yr | 0.9 |
| 12-1 momentum | 16.4% | −24% | 20.0% | −49% | +3.1%/yr | 0.6 |
| composite (surprise + buyback + FCF + issuance + momentum) | 15.9% | −30% | 21.1% | −56% | +1.8%/yr | 0.5 |
| capital return alone | 10.6% | −44% | 8.3% | −78% | +0.3%/yr | 0.1 |

The 2.8% quarterly Q5−Q1 spread is real, but LONG-ONLY against a 15%-a-year SPY it is
worth 2 to 5 points a year before the t-stat, at 50–60% monthly turnover, with a deeper
drawdown and a lower Sharpe than the index. $5,000 becomes $14,000–$21,000 over the seven
and a half years, against $14,000–$21,000 in SPY at the same leverage. **There is no
combination of the measured factors, at any horizon, on any stock, that compounds faster
than about 20% a year at 2×, and that path carries a 50%-plus drawdown.** At 21% a year,
$5,000 reaches $50,000 in twelve years. This agrees with `goal_feasibility.md` from the
other direction.

## 4. The engine as one portfolio, 2020–2026 (`05_studies/engine_combo_test.py`)

Monthly, 78 months, the surprise sleeve at 0/25/50/100% of equity with the rest in SPY,
with and without the 2× overlay (signal on at 6 of 78 month-ends), 15 bp/side, 6% borrow.

| configuration | CAGR | max DD | worst month | Sharpe | years to 10× |
|---|---:|---:|---:|---:|---:|
| SPY | 14.5% | −20% | −12% | 0.88 | 17 |
| SPY, 2× when the signal is on | 13.9% | −25% | −25% | 0.72 | 18 |
| 50% sleeve, 1× | 16.4% | −19% | −19% | 0.85 | 15 |
| **100% sleeve, 1×** | **17.8%** | −27% | −27% | 0.78 | **14** |
| 100% sleeve, 2× when on | 11.2% | −54% | −54% | 0.51 | 22 |

Two things to read. **The overlay hurt in this window**: with only six firings in 78 months
and one of them the March 2020 crash, 2× when on cost 0.6 points a year at monthly
granularity (its measured 2006–2026 result is a daily rule over 56 firings; this is a lower
bound on the same window, and a warning that the overlay's edge is a long-run average with
a fat left tail). **The sleeve helps at every weight** but its excess is +4.7%/yr at t 0.9,
and its excess is slightly negatively correlated with the signal (−0.19). The honest
expectation for the whole paper engine is 15–18% a year with a 20–30% drawdown: fourteen
to seventeen years to 10×. Nothing in the combination changes the answer to five months.

> **2026-09-23, from `docs/briefs/leverage-growth.md`:** rebuilt on real SSO/UPRO products the
> VIX-gated overlay underperforms plain leveraged-ETF buy-and-hold (daily-reset drag). The
> 15.3%/yr figure is a synthetic 1×+1× daily overlay; implementing it needs margin on SPY, not
> a leveraged ETF. `index_overlay.py` models margin (6% borrow), which is the right instrument.
