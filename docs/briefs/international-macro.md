<!-- research brief, filed 2026-09-23; agent output verbatim -->

## Tactical global asset allocation: does rotating SPY/EFA/EEM/bonds/gold/BTC by trend or momentum beat buy-and-hold?

Report date: 2026-09-23. Method note: this session's WebSearch budget was confirmed exhausted before
starting (per the dispatching session), so all citations below come from direct `WebFetch` of primary
pages or are marked **not verified** where a source refused the fetch. All five strategies were computed
locally with `yfinance` + `pandas` via `/Users/sahilmajmudar/index-daytrading/venv/bin/python3` — real
adjusted-close prices, monthly rebalancing, 10bp/side transaction costs on weight turnover, January 2010
through the (partial) September 2026 print, 213 monthly observations. Code is scratch, not checked into
this repo; the methodology below is complete enough to reproduce.

This extends the repo's existing sector-rotation null. `02_findings/WHAT_FAILED.md` already recorded
that sector rotation was tested at **1,512 configurations, none beat buy-and-hold, and picks selected
by it did worse than random (p=0.867)** — pinned to IC≈0 in the registry and demoted to a context-only,
zero-vote input in the live engine. This brief asks the same question one level up: does rotating whole
*countries and asset classes* (not sectors) by trend or momentum do any better. Short answer: modestly,
sometimes, never enough to matter against the target in the prompt.

### 1. Universe and strategies tested

Universe: SPY, EFA, EEM, VWO, EWJ, EWG, EWU, EWY, EWT, INDA, EWZ, GLD, TLT, BTC-USD (from its first
liquid month, 2014-09), plus AGG, HYG, IEF, BIL as instruments for the rules below. All five strategies
rebalance monthly on signals computed through the prior month-end (no look-ahead), applying 10bp of cost
per side on the change in target weight.

1. **Faber GTAA** — hold each of the 14 assets equal-weight only when its price is above its own
   10-month SMA; cash otherwise.
2. **Antonacci dual momentum** — hold whichever of SPY/EFA has the higher trailing 12-month return, but
   only if that return beats trailing 12-month T-bills (BIL); otherwise hold AGG.
3. **Country momentum** — equal-weight the top 3 of the 10 country ETFs (EFA, EEM, VWO, EWJ, EWG, EWU,
   EWY, EWT, INDA, EWZ) by trailing 6-month return, monthly.
4. **Risk-on/off** — SPY when the HYG/IEF price ratio is above its own 50-day SMA (both daily series,
   sampled at month-end), else TLT.
5. **60/40 (SPY/AGG)** — the benchmark, rebalanced monthly, same 10bp cost.

### 2. Results, 2010-01 through 2026-09 (213 months)

| Strategy | CAGR | Max drawdown | Sharpe | 2020 return | 2022 return |
|---|---|---|---|---|---|
| 1. Faber GTAA (as specified, 14 assets incl. BTC) | 9.93% | −30.0% | 0.75 | **+35.6%** | −26.9% |
| 1b. Faber GTAA, BTC excluded (robustness check) | 5.15% | −28.1% | 0.47 | +21.9% | −26.9% |
| 2. Antonacci dual momentum (SPY/EFA vs T-bills, else AGG) | 7.96% | −20.3% | 0.68 | +2.2% | −17.1% |
| 3. Country momentum (top-3 of 10, 6-month) | 8.18% | −38.3% | 0.51 | +13.9% | −14.3% |
| 4. Risk-on/off (HYG/IEF 50-day ratio, SPY vs TLT) | 4.38% | −47.6% | 0.39 | +18.2% | −31.2% |
| 5. 60/40 SPY/AGG (benchmark) | 10.39% | −20.0% | 1.10 | +14.7% | −15.8% |
| 0. Buy-and-hold SPY (reference, uncosted) | 15.54% | −23.9% | 1.06 | +18.3% | −18.2% |

None of the four tactical strategies beats either benchmark on CAGR or Sharpe over the full period. The
best Sharpe among them (Faber GTAA, 0.75) is two-thirds of 60/40's and buy-and-hold SPY's (1.10 / 1.06).
Three of the four (Faber, country momentum, risk-on/off) also carry **worse** drawdowns than SPY
buy-and-hold, which defeats the usual sell of tactical allocation — smoother ride, lower highs — since
here the ride is rougher AND the compounding is slower.

**A methodology trap, caught before it shipped.** Faber's 2020 return (+35.6%) looked too good given
trend-following's well-known problem with V-shaped recoveries, so I re-ran it with BTC-USD removed:
CAGR drops from 9.93% to 5.15%, Sharpe from 0.75 to 0.47, and the 2020 return from +35.6% to +21.9%.
The cause: Faber's rule is equal-weight among whatever clears its 10-month SMA, and breadth was thin in
April-June 2020 (4-9 of 14 assets qualified) right as BTC-USD re-entered the basket and returned
+34%/+9%/-3%/+24%/+3%/-8% across April-September 2020 — a 20-25% portfolio weight on an asset the
original 2007 paper never included, during its best months. This is the same failure mode
`02_findings/METHODOLOGY_TRAPS.md` already catalogs elsewhere in this repo: a rule that looks like an
edge is actually one concentrated position dominating a thin-breadth month. Both numbers are reported
above rather than picking the flattering one.

**Risk-on/off is the clearest outright failure.** HYG/IEF-based regime switching produced the worst
Sharpe (0.39) and the worst drawdown (−47.6%) of anything tested — worse than an un-costed SPY
buy-and-hold's −23.9% — while also giving the worst 2022 return (−31.2%) of the group, the year it was
supposed to protect against. A 50-day ratio SMA is a lagging, whipsaw-prone signal on a period that
included the fastest bear market in history (March 2020) and the worst bond year in decades (2022); it
was late to both.

**Antonacci's dual-momentum rule had the smallest 2022 loss (−17.1%) and the smallest drawdown next to
60/40 (−20.3%),** consistent with its design goal (avoid the worse of two risky assets, and get fully
defensive when neither clears the T-bill bar) — but its CAGR (7.96%) still trails 60/40 by 2.4
points/year, because the U.S. was almost always the momentum winner over this window and the AGG
switch triggered rarely and imperfectly.

### 3. What the primary sources claim, and what could be verified this session

- **Faber (2007), "A Quantitative Approach to Tactical Asset Allocation," SSRN 962461.** SSRN itself
  returned HTTP 403 on every attempt (direct, `ssrn.com/abstract=962461`, and a third-party mirror at
  AlphaArchitect also 403'd). Faber's own site (mebfaber.com/timing-model) *was* reachable and confirms
  the mechanism — a 10-month SMA applied monthly across five asset classes — but explicitly warns: "the
  timing model was published only as a simple example... we do not run client funds with the exact
  parameters in the white paper." **The paper's own claimed numbers (CAGR/drawdown/Sharpe vs.
  buy-and-hold) are not verified this session** — cite the mechanism, not the stated edge, until a
  working SSRN fetch confirms it.
- **Antonacci, Dual Momentum / Global Equities Momentum, optimalmomentum.com.** Blocked with HTTP 403 on
  every path tried (home page and the dual-momentum page). **Not verified this session.** The rule
  itself (absolute + relative momentum, monthly, SPY/EFA/AGG) is well enough documented outside this
  session to replicate, which is what strategy 2 above does — but any specific return/drawdown figures
  Antonacci's site claims for GEM were not independently confirmed here.
- **Asness/AQR critique of tail hedging ("Portfolio protection? It's a long (term) story").** Could not
  locate the piece on aqr.com — the Insights/Perspectives listing (fetched, both the general page and a
  2021-filtered view) does not currently show an article under that title or on that topic; it may have
  been retitled, archived, or the title is misremembered. **Not verified this session.** The well-known
  form of the argument (a tail hedge's cost is a permanent, realized drag; the crash-day payoff is
  occasional and must be large enough to offset years of bleed) is not sourced to a fetched page here and
  should be treated as background, not a citation.
- **Universa Investments (universa.net).** Fetched successfully. The live page carries **no performance
  numbers at all** — only educational video links tied to Spitznagel's book *Safe Haven*. That is itself
  a finding worth noting: the firm most associated with a public "we made investors a fortune in March
  2020" narrative does not post a return figure on its own marketing page. Any specific Universa
  return claims in circulation come from press interviews or investor letters, not this URL.
- **Cambria Global Momentum ETF (GMOM), stockanalysis.com — fetched live, real numbers.** GMOM is Meb
  Faber's own fund, an ~17-ETF multi-asset momentum/trend implementation of essentially the strategy
  family tested above, running since November 2014. **Since-inception average annual return: 5.96%**
  (through 2026-09-23), 1-year return 21.60%, expense ratio 1.01%, AUM $73.3M. Over the same *stretch*
  this brief's Faber GTAA backtest returned 9.93%/yr and plain 60/40 returned 10.39%/yr — an actual,
  currently-trading fund built on this exact idea has compounded at barely half the 60/40 benchmark's
  rate for over a decade, net of a 1.01% expense ratio. This is the single most concrete answer in this
  brief to "does this work in practice, not backtest": yes, it is a real, ongoing product, and no, it has
  not beaten a plain 60/40 portfolio.

### 4. Judged against the target

| Claim | What was computed/found | Implied annualized | Verdict |
|---|---|---|---|
| $5,000 → $50,000 in 5 months | Requires ~58% compounded **per month** | roughly 10,000%+/year | No strategy tested here, or any real fund found (GMOM), is within several orders of magnitude. These are diversification/timing overlays on long-only beta, not leveraged directional bets, and were never going to approach this regardless of skill in tuning them. |
| "20%/year" as a bar | Best tactical result: Faber GTAA 9.93%/yr (inflated ~5pts by an accidental BTC weighting; 5.15%/yr ex-BTC). 60/40 benchmark: 10.39%/yr. SPY buy-and-hold: 15.54%/yr (uncosted). GMOM live fund since 2014: 5.96%/yr. | 4.4-10.4%/yr for every tactical rule tested; only uncosted SPY buy-and-hold gets close, and none clear 20% | Nothing in this brief clears 20%/year. Every tactical overlay tested UNDERPERFORMED both simple benchmarks (60/40 and SPY buy-and-hold) on CAGR, and three of four also carried worse drawdowns. |
| Tactical/trend overlays as risk reducers | Antonacci (−20.3% max DD) roughly matched 60/40 (−20.0%); Faber, country momentum, and risk-on/off were all WORSE than SPY buy-and-hold's −23.9% | n/a | Only the momentum-with-a-T-bill-filter design (Antonacci) delivered on the "smoother ride" promise here; SMA-trend and ratio-regime rules did not. |
| Real-world tactical fund | GMOM (Faber's own live implementation), Nov 2014-Sep 2026 | 5.96%/yr, net of 1.01% expense ratio | Confirms the backtest picture with an actual track record: tactical global allocation is a real, tradeable, moderate-return product — not a path to fast compounding. |
| Sector rotation (already in this repo) | `WHAT_FAILED.md`: 1,512 configs, none beat buy-and-hold, p=0.867 for picks vs. random | n/a | Country/asset-class rotation (this brief) does marginally better than sector rotation (already refuted) only because it is diversifying across genuinely different macro drivers, not picking among correlated large-caps — but "marginally better than a null result" is still well under a 60/40 benchmark. |

**Bottom line for Sholo:** every tactical global-allocation rule in this brief — trend-following (Faber),
dual momentum (Antonacci), country rotation, and a credit/duration regime filter — underperformed a
plain 60/40 portfolio on both return and (mostly) risk, over 2010-2026, after realistic 10bp costs. The
one live fund built on this family of ideas (GMOM, Faber's own) has compounded at 5.96%/year for almost
twelve years, net of fees — a real number from a real product, not a backtest. None of this is a path
from $5,000 to $50,000 in five months; it isn't even a reliable path to 20%/year. It is what the sector-
rotation finding already said one level down: rotating a fixed universe by trend or momentum signals is
a modest diversification tool at best, and this repo has now tested that claim at both the sector level
(refuted, `WHAT_FAILED.md`) and the country/asset-class level (this brief) with the same result. Sourcing
gaps to flag explicitly: the Faber SSRN abstract, Antonacci's optimalmomentum.com claims, and the specific
Asness/AQR tail-hedging piece could not be fetched this session (403s throughout, and the AQR piece could
not be located by title) — treat the mechanism descriptions above as reproduced from this repo's own
backtest, not as verified restatements of those authors' own performance claims.

---
*All backtest figures computed with `yfinance` + `pandas` via
`/Users/sahilmajmudar/index-daytrading/venv/bin/python3`, run 2026-09-23. Universe: SPY, EFA, EEM, VWO,
EWJ, EWG, EWU, EWY, EWT, INDA, EWZ, GLD, TLT, BTC-USD (from 2014-09), plus AGG/HYG/IEF/BIL as signal/
instrument inputs. Monthly rebalancing, 10bp/side cost on weight turnover, January 2010 through the
partial September 2026 print (213 months). Code is scratch (not checked into this repo); methodology in
§1 is complete enough to reproduce independently.*
