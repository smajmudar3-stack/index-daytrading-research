# Information diffusion — measured on every link this machine has

**Written 2026-09-24.** The claim: news reaches a stock's LINKED names first, so what
happened to the links last week predicts the stock next week. The literature
(`03_research/RESEARCH_DIFFUSION.md`) puts industry lead-lag at ~10–12%/yr gross and
customer momentum at ~18%/yr, all pre-2010, all in small, thinly traded names.
Study: `05_studies/diffusion_model.py`. Panel: 498,734 name-weeks, 1,471 S&P 1500 names,
155 GICS sub-industries, 447 weeks 2018-01 → 2026-08, close ≥ $10, 20-day dollar volume
≥ $10m, forward return in excess of SPY from the NEXT open, Spearman IC by week, three
splits, noise bar √(2 ln N).

## Verdict

**Null.** No diffusion channel measurable here predicts next week or next month after
costs, and the channels that look alive are weekly REVERSAL wearing a peer label. The
combined walk-forward model earns +0.17% a week gross on its top-minus-bottom decile at
87% weekly turnover: **−9.1%/yr net** of 10 bp a side. The monthly version is +2.6%/yr
net at t 1.3. Nothing enters the weekly vote; two registry entries record the null.

## What each channel showed

| channel | what was tested | 5-session IC (t) | splits A / B / C | reading |
|---|---|---|---|---|
| **A. Industry lead-lag** (Hou 2007) | same-sub-industry peers' past week, equal- and volume-weighted, BIG peers only (top tercile), sector versions | peers' return: **−0.011 to −0.016 (t −1.6 to −2.2)**; peer-minus-own gap: +0.012 (t 3.3) | gap: +0.020 / +0.005 / +0.004 | the gap's t is own-return reversal: residualised on the name's own week it is **−0.006 (t −1.2)**. The peer return itself points the WRONG way for diffusion (names move against their peers, not with them) |
| A, Hou's own test: SMALL half only | same, small names | gap +0.013 (t 3.2); big-peer return −0.012 (t −1.9) | +0.021 / +0.006 / +0.002 | same story; after big peers fall >3% small names make +0.12% the next week, after they rise >3% −0.05% — a reversal, decaying to nothing by 2024–26 |
| **B. Earnings transfer** (Foster 1981, Thomas-Zhang 2008) | for names that did NOT report this week or next: volume-weighted SUE and day-one reaction of same-sub-industry names that DID (82,658 name-weeks) | peer SUE **+0.019 (t 1.96)** vs noise bar 1.5; announcers' reaction −0.003 | +0.031 / −0.000 / +0.024 | positive (drift, not Thomas-Zhang's overreaction) but dead in 2022–23; long the top quintile: +0.18%/wk gross, **−0.02%/wk after a 20 bp round trip** |
| **C. Statistical peers** | 20 most-correlated names on the prior 252 sessions, refit monthly, past-only | peers' return −0.014 (t −1.3); gap +0.016 (t 3.3) | gap +0.026 / +0.013 / +0.008 | gap residualised on own return: −0.002 (t −0.3). Reversal again |
| **D. Cross-asset → sectors** | last week's oil / copper / gold / 10y / USD / HY spread / VIX against next week's sector-ETF excess, 2009–2026, 77 pairs | best oil→XLF t 3.0 | +0.23 / +0.08 / **−0.06** | 1 of 77 above the bar, and it flips sign in the latest split |
| **E. Industries lead the market** (Hong-Torous-Valkanov) | each sector's past month against SPY's next month, 22 tests | all negative; best XLU t −2.7 | — | 1 of 22 above the bar, in the wrong direction (a sector rally predicts a weaker index, i.e. monthly reversal) |
| **F. Combined, walk-forward** | Fama-MacBeth: average of the past 104 weeks' cross-sectional coefficients on A+B+C, applied to this week's ranks | IC +0.011 (t 1.4); decile spread +0.17%/wk gross | +0.017 / +0.012 / +0.002 | turnover 87%/week ⇒ **−9.1%/yr net**; adding peer SUE −9.7%/yr; 4-week hold +2.6%/yr net at t 1.3 |

## Why this differs from the papers

- **The sample.** Hou (1963–2001) finds the effect "predominantly" in small, neglected,
  low-coverage industries and driven by slow adjustment to bad news. This universe is the
  S&P 1500 above $10m a day — the names an option book can trade — where every name has
  coverage and an ETF that arbitrages its industry within the hour.
- **The decay.** Every split-A number (2019–21) is larger than split C (2024–26), usually by
  5–10×. McLean-Pontiff's 58% post-publication decay on a 2007 paper leaves little by 2024.
- **The links that carry the most in the literature are not here.** Principal customers
  (Cohen-Frazzini), supplier industries (Menzly-Ozbas), shared analysts (Ali-Hirshleifer),
  patents, headquarters: none of those maps is on this machine, and they are said out loud
  as not measured rather than proxied with correlation and called a customer link.
- **The horizon.** The one channel with a positive, all-split sign (peer earnings surprise →
  small non-announcers, IC +0.015 in every split, t 1.6) is real-looking and too small: a
  fifth of the round-trip cost at a week, and gone at 21 sessions (t −0.3).

## What it means for the book

The registry now carries `industry_lead_lag` and `peer_earnings_transfer` at weight 0 with
the `measured-null` tier, so a future session cannot wire "the sector moved, so this name
will" into the weekly vote without seeing this page. The peer-SUE channel is the only
candidate worth a second look if a customer-supplier map (10-K segment disclosures) is ever
added; on industry links alone it does not pay for its own trades.
