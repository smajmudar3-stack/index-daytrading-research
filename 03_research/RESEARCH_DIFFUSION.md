# Information diffusion — the literature, the links, and what this machine can test

**Written 2026-09-24.** The claim: news reaches some stocks before others, so what happened
to a name's LINKED names last week tells you what happens to the name next week. This is
the one family of "what moves a stock" ideas that is (a) cross-sectional, (b) documented at
a weekly horizon, and (c) not already refuted in this repo. The measurement is
`05_studies/diffusion_model.py`; the verdict is `02_findings/diffusion.md`.

## The papers, with what they actually claim

Abstracts pulled from the OpenAlex API on 2026-09-24 (publisher pages 403 scripted
requests). Numbers are the papers' own, on US data ending before 2010 unless noted.

| paper | link that carries the news | horizon | claimed size | what it hinges on |
|---|---|---|---|---|
| Hou 2007, *RFS* "Industry information diffusion and the lead-lag effect" | BIG firms lead SMALL firms **in the same industry** | weekly | the classic Lo-MacKinlay lead-lag, shown to be intra-industry | "driven by sluggish adjustment to **negative** information"; strongest in small, less competitive, neglected industries; tied to small firms' drift after big firms' earnings |
| Hong, Lim & Stein 2000, *JF* "Bad news travels slowly" | analyst coverage | months | momentum profits fall sharply with size; strongest in low-coverage names, and mostly for past LOSERS | information diffuses gradually; bad news slowest |
| Cohen & Frazzini 2008, *JF* "Economic links and predictable returns" | principal CUSTOMER (from 10-K disclosures) | monthly | long-short alpha **>150 bp/month** | investors' attention constraints; needs the customer-supplier map |
| Menzly & Ozbas 2010, *JF* "Market segmentation and cross-predictability" | supplier and customer INDUSTRIES (input-output tables) | monthly | cross-predictability that falls with analyst coverage and institutional ownership | investor specialisation |
| Hong, Torous & Valkanov 2007, *JFE* "Do industries lead stock markets?" | INDUSTRY portfolios lead the MARKET | 1–2 months | a number of industries predict the market | industries that forecast economic activity forecast the index |
| Thomas & Zhang 2008, *JAR* "Overreaction to intra-industry information transfers?" | EARLY announcer's earnings → late announcers in the industry | event | late announcers' reaction to the early report is **negatively** related to their reaction to their own report | the market OVER-estimates the transfer and corrects when the peer reports |
| Foster 1981, *JAE* | same, the original | event | peers move on an announcer's release | — |
| Lee, Sun, Wang & Zhang 2019, *JFE* "Technological links" | shared PATENT classes | monthly | a technology-momentum alpha that survives industry and customer momentum | needs patent data |
| Parsons, Sabbatucci & Titman 2020, *RFS* "Geographic lead-lag" | co-HEADQUARTERED firms in different sectors | monthly | **5–6%/yr** risk-adjusted, "half that observed for industry lead-lag effects" | shared analysts, not scrutiny |
| Ali & Hirshleifer 2020, *JFE* "Shared analyst coverage" | firms covered by the SAME ANALYSTS | monthly | a connected-firm momentum that subsumes industry, customer, technology and geographic momentum | the unifying link is who writes about both names |

Read together: the literature's own numbers put industry lead-lag at roughly 10–12%/yr
risk-adjusted (Parsons et al. say geography's 5–6% is half of it), customer momentum at
~18%/yr, all gross, all long-short, all pre-2010, and all concentrated in small, thinly
traded, low-coverage names — exactly the names a $5,000 account trading options cannot
touch. McLean & Pontiff (2016) put the post-publication decay of a typical published
anomaly at ~58%.

## What is on this machine and what is not

| link | available? | how |
|---|---|---|
| industry (GICS sector and sub-industry) | **yes** — S&P 1500, 11 sectors, 155 sub-industries | `opt_panel/gics.parquet`, fetched 2026-09-24 |
| big vs small within industry | **yes** — by 20-day dollar volume | the price panel |
| early earnings announcers and their surprise | **yes** — the calendar and consensus/reported EPS | `earnings.parquet`, `eps_history.parquet` |
| statistical peers (co-movement) | **yes** — top-20 correlation on the prior 252 sessions | computed, past-only |
| cross-asset (oil, copper, gold, 10y, USD, HY credit, VIX) → sectors | **yes** — public daily series | yfinance |
| principal customers (Cohen-Frazzini) | **no** — needs 10-K segment disclosures | not measured |
| supplier/customer industries (Menzly-Ozbas) | **no** — needs BEA input-output tables mapped to names | not measured |
| analyst coverage / shared analysts | **no** | not measured |
| patents, headquarters | **no** | not measured |

## The tests

`diffusion_model.py`, one observation per name per week (last session of each ISO week),
forward 5- and 21-session return in excess of SPY from the next open, close ≥ $10 and
20-day dollar volume ≥ $10m, Spearman IC by week, three time splits (A 2019–21, B 2022–23,
C 2024–26), the noise bar √(2 ln N) stated per table.

- **A. Industry lead-lag.** Same-sub-industry peers' past-week return excluding the name
  (equal- and dollar-volume-weighted), the BIG-peer version (top tercile by volume), the
  gap to the name's own return, and the sector versions. Hou's test proper is the IC on
  the SMALL half only.
- **B. Earnings transfer.** For names that did not report this week or next: the
  volume-weighted surprise (SUE) and announcement-day reaction of same-sub-industry names
  that reported this week. Thomas-Zhang predicts a NEGATIVE IC (overreaction); Foster and
  Hou predict positive drift.
- **C. Statistical peers.** The 20 most-correlated names, refit monthly on past data only;
  their past-week return and the gap to own.
- **D. Cross-asset.** Last week's move in each asset against next week's sector-ETF excess
  return, 2010–2026, 77 pairs.
- **E. Industries lead the market.** Each sector ETF's past month against SPY's next month.
- **F. The combined model.** Fama-MacBeth walk-forward: at each week, average the past 104
  weeks' cross-sectional coefficients on A+B+C (only weeks whose forward return is already
  known), apply to this week's ranks; IC, and the decile spread gross and net of 10 bp a
  side at the turnover it actually generates. This is the number the swing book would use.

Results: `02_findings/diffusion.md`.
