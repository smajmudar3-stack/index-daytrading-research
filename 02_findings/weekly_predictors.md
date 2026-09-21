# What predicts a stock over a week — measured on 1,845 names, seven years, real chains

**Status: CURRENT. Measured 2026-09-21.** The first cross-sectional measurement in this repo
of the inputs behind the weekly options book, and of the published options-implied
predictors, on the Dolt EOD chains (2019-05 → 2026-08, 114M quotes, 1,528 names a day).

## Why this was run

The weekly book's ledger, 2026-09-03 → 09-21, 129 closed cards:

| | n | mean P&L (% of risk) | win rate |
|---|---:|---:|---:|
| all closed | 129 | **−40%** | 21% |
| debit spreads | 91 | −56% | 10% |
| credit spreads | 38 | −4% | 47% |
| direction call right | 44 | −13% | — |
| direction call wrong | 73 | −57% | — |

The direction call was right **37.6%** of the time on 117 directional cards. Every voter
behind it is a price transform (`trend`), a human macro read (`desk_macro`), or a vendor
number served same-day with no history (`flow_lean`, `dp_buy_share`, `short_float_pct`,
`insider_open_buys`). None had ever been measured cross-sectionally at the horizon the book
holds. This measures what can be measured, and the literature's best candidates alongside.

## Method

- One observation per name per week (last session of each ISO week). 5-day forward returns
  never overlap; 10-day and 21-day use every 2nd and 4th week.
- Signal at close t; position at the OPEN of t+1; closed at the close of t+H.
- Universe at t: close ≥ $10, 20-day median dollar volume ≥ $10m, ATM round-trip spread ≤ 25%,
  at least 3 matched call/put pairs. 723,824 name-weeks pass.
- Spearman IC per date, Fama-MacBeth t over dates. Three time splits. Every feature signed so
  a POSITIVE IC means "as the paper says".
- 24 features × 3 horizons = 72 tests; expected max |t| under the null ≈ **2.9**.
- Prices split-adjusted from the Dolt split table; any residual ±60% day masked.

Reproduce: `05_studies/scripts/build_opt_panel.py` (dump), `05_studies/xsec_options_panel.py`
(features), `05_studies/xsec_predictors_test.py` (this table).

## Result: nothing clears the bar

5-day horizon, 344 weeks, 214,803 name-weeks. Sorted by t.

| feature | published sign | IC | t | A 2019-21 | B 2022-23 | C 2024-26 |
|---|:-:|---:|---:|---:|---:|---:|
| post-earnings drift (`pead1`) | + | +0.018 | +1.8 | +0.009 | +0.038 | +0.010 |
| one-week reversal (`ret5`) | − | +0.015 | +1.6 | +0.023 | +0.019 | +0.006 |
| days to cover | − | +0.010 | +1.5 | +0.004 | +0.011 | +0.009 |
| one-month reversal (`ret21`) | − | +0.010 | +1.1 | +0.015 | +0.009 | +0.007 |
| short float (`si_float`) | − | +0.007 | +0.9 | +0.026 | −0.004 | +0.012 |
| **call−put IV spread** (Cremers-Weinbaum) | + | +0.002 | +0.7 | +0.004 | +0.003 | −0.001 |
| ATM IV level | − | +0.007 | +0.5 | +0.018 | −0.017 | +0.016 |
| 12-1 momentum | + | +0.005 | +0.4 | −0.005 | +0.002 | +0.015 |
| put IV change, 21d (An et al.) | − | +0.003 | +0.4 | +0.016 | −0.003 | −0.003 |
| call IV change, 5d (An et al.) | + | +0.002 | +0.3 | −0.004 | −0.001 | +0.008 |
| 52-week high (George-Hwang) | + | +0.001 | +0.0 | −0.003 | −0.019 | +0.018 |
| borrow fee (`fee_rate`, 2022→) | − | −0.003 | −0.6 | — | −0.005 | −0.001 |
| 3-month momentum | + | −0.011 | −1.0 | −0.025 | −0.010 | −0.000 |
| **smirk** (Xing-Zhang-Zhao) | − | −0.006 | −1.3 | −0.007 | −0.002 | −0.008 |
| **risk reversal** (OTM call IV − OTM put IV) | + | −0.010 | −2.3 | −0.015 | −0.004 | −0.010 |

At 10 and 21 days the picture is the same: post-earnings drift reaches t = +2.6 at 10d and
+2.2 at 21d (positive in every split, 57–65% of weeks), days-to-cover t = +1.9 at 10d, and
everything else sits inside ±1.5 with signs that move between splits.

**The three options-implied predictors with the biggest literatures are dead in this data.**
The Cremers-Weinbaum spread is +0.002. The smirk has the WRONG sign in all three splits. The
risk reversal is the most "significant" thing in the table and it is backwards: names whose
OTM calls are rich against their OTM puts go on to underperform. That is consistent with
Muravyev, Pearson & Pollet (JFE 2025): those measures worked because they proxied the borrow
fee, and the fee is directly observable now — and the fee itself scores −0.003 here.

The borrow-fee family (short float, days to cover, fee) is the one thing with the documented
sign in most splits, and it is worth an IC of about 0.01 at a week. That matches this repo's
existing finding that short interest is monotone in horizon: −0.022 at 5d, −0.107 at 63d. It
is a quarterly signal being asked to do weekly work.

### A composite does not rescue it

Equal-weight rank composite of the three least-bad (post-earnings drift, days to cover, one-week
reversal), names with at least two of the three:

| horizon | IC | t | top decile finished UP | bottom decile finished DOWN | D10−D1 |
|---|---:|---:|---:|---:|---:|
| 5d | +0.017 | +2.0 | 52.4% | 48.9% | +14 bp |
| 10d | +0.019 | +2.3 | 53.6% | 48.0% | +25 bp |

A one-week direction call from the best available cross-sectional evidence is right about
52% of the time and is worth 14–25 basis points of stock. A weekly debit spread pays roughly
20% of its risk in bid-ask on the round trip. **There is no weekly direction edge in this
data large enough to buy options on.** The ledger's 37.6% was not bad luck on top of a real
edge; it was noise on top of none, in a month when the book was 58% long tech into a selloff.

## What this changes

1. `REQUIRE_MEASURED_BASIS` in `weekly_swing`: a card is refused unless at least one input
   that measured with a consistent sign at this horizon points its way — VIX backwardation,
   post-earnings drift, or the earnings premium read (itself unconfirmed in P&L, and labelled
   so). A "conviction" built from inputs that rank next week at IC 0.00–0.02 is a number, not
   a reason, and the refusal states the structure's measured cost against it.
2. The structure and the exit decide the book's P&L, not the direction. The ledger already
   says so (credit −4% vs debit −56%), and `xsec_vertical_test.py` / `xsec_straddle_test.py`
   measure it on seven years of real quotes — see `weekly_structure.md`. Debit spreads no
   longer carry a price stop.
3. Post-earnings drift is registered as `pead` at 0.10 and wired as a voter (`pead.py`),
   abstaining outside 14 sessions of a print. The four dead options-implied predictors are
   pinned at zero in the registry so they cannot be re-added from the papers.
4. The paid scan regenerates every 4 hours instead of every 4 minutes (`scan_all.py` had its
   gate in the wrong units), so the vendor voters actually load instead of 429-ing.

## What it does NOT establish

- This is a thinned chain (~11 strikes a side, 3 expiries). The Cremers-Weinbaum spread is an
  unweighted mean over ~5 matched pairs, not the open-interest-weighted average over the whole
  surface. A null on the thinned version is not a null on the full one — but the live engine
  reads a yfinance ladder that is no better, so it is the right null for this book.
- The Unusual Whales inputs (classified flow, dark pool, unusual activity) are NOT in this
  table because their endpoints serve no history from the live client. `scripts/
  uw_history_pull.py` pulls the ones that do, and `xsec_uw_test.py` will score them the same
  way once the quota allows the pull. Until then their weights are priors.
- Nothing here is about the macro overlay. A human macro read cannot be backtested from this
  repo's data; it is unmeasured, and it stays labelled so.
