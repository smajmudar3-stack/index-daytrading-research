# Brief: Volatility ETPs (UVXY / SVXY / SVIX / VXX) — short-vol carry, contango timing, and the "$5k to $50k in 5 months" claim

**Status: not verified against real option/futures quotes.** This brief uses yfinance
**daily adjusted equity closes** for the ETPs themselves (UVXY, SVXY, SVIX, VXX) and for
^VIX / ^VIX3M, not the underlying VIX futures term structure the ETPs actually roll. ETP
total return already embeds the fund's real rebalancing, borrow, and roll cost, which is
good, but the VIX/VIX3M ratio used as the timing signal is an *index* ratio, not the ETP's
own futures basis — a proxy, not the fund's actual roll yield. 10 bp/side friction is
charged on every signal flip. Dates: 2011‑01‑03 to 2026‑09‑22. UVXY/SVXY have full history
from inception (Oct 2011); SVIX only exists from Mar 2022; VXX in its current (post‑2018)
structure only from Jan 2018 — used as a cross‑check on strategy 2, not the primary vehicle.

## 1. Buy-and-hold

| Vehicle | Period | CAGR | Max DD | Worst day | Worst month | Sharpe | Total return |
|---|---|---|---|---|---|---|---|
| UVXY | 2011–17 | −91.3% | −100.0% | −26.7% | −55.8% | −1.37 | −100.0% |
| UVXY | 2018–19 | −49.8% | −91.0% | −33.4% | −35.3% | −0.05 | −74.8% |
| UVXY | 2020–23 | −71.6% | −99.9% | −23.2% | −48.3% | −0.55 | −99.3% |
| UVXY | 2024–26 | −60.7% | −94.6% | −31.6% | −37.6% | −0.37 | −92.1% |
| UVXY | Full | −80.2% | −100.0% | −33.4% | −55.8% | −0.81 | −100.0% |
| SVXY | 2011–17 | +66.9% | −67.9% | −26.4% | −46.8% | 1.14 | +2,336% |
| SVXY | 2018–19 | −64.4% | −93.1% | −83.0%¹ | −89.6%¹ | −0.60 | −87.3% |
| SVXY | 2020–23 | +12.2% | −62.2% | −19.5% | −38.9% | 0.50 | +58.5% |
| SVXY | 2024–26 | +7.9% | −46.4% | −21.4% | −18.2% | 0.40 | +23.0% |
| SVXY | Full | +12.8% | −95.2% | −83.0%¹ | −89.6%¹ | 0.57 | +504.0% |
| SVIX | 2020–23² | +71.0% | −39.4% | −16.5% | −24.9% | 1.22 | +155.1% |
| SVIX | 2024–26 | −9.7% | −79.3% | −38.9% | −39.1% | 0.22 | −24.3% |
| SVIX | Full (2022–26) | +15.9% | −79.3% | −38.9% | −39.1% | 0.57 | +93.2% |

¹ SVXY's −83% single day is Feb 5 2018: Cboe/ProShares cut SVXY's leverage from −1.0x to
−0.5x *after* Volmageddon specifically because the fund nearly wiped out the way XIV did.
² SVIX inception is Mar 2022, so it has no 2011–19 data; its "2020–23" row is really
2022‑03‑30 to 2023‑12‑31 only, not comparable to the other rows' full periods.

UVXY's −100% full-sample total return is the honest, split-adjusted number: buy-and-hold
long vol has been close to a total loss since 2011, the entire reason short-vol carry trades
exist. SVXY's +2,336% for 2011–17 is real but flattered by a single calm, pre-Volmageddon
regime — the same fund lost 87% in 2018–19, net of the Feb 2018 event and the leverage cut
that followed it.

## 2. Short vol only when VIX/VIX3M < 1.0 (contango), flat otherwise

Signal decided on the prior day's close (no lookahead), traded next day, 10 bp per side on
every flip. Full-history vehicle is short UVXY (available since 2011); VXX row is a
cross-check from 2018 on.

| Strategy | Period | CAGR | Max DD | Worst day | Worst month | Sharpe |
|---|---|---|---|---|---|---|
| Short UVXY, contango-only | 2011–17 | +109.4% | −77.9% | −43.9% | −52.4% | 1.25 |
| Short UVXY, contango-only | 2018–19 | −35.0% | −84.1% | −27.4% | −49.6% | −0.02 |
| Short UVXY, contango-only | 2020–23 | +43.4% | −78.6% | −50.2% | −40.0% | 0.90 |
| Short UVXY, contango-only | 2024–26 | +2.5% | −71.0% | −35.5% | −44.3% | 0.46 |
| Short UVXY, contango-only | Full | +42.1% | −85.7% | −50.2% | −52.4% | 0.89 |
| Short VXX, contango-only (X-check) | 2018–19 | −17.6% | −62.5% | −16.7% | −35.9% | −0.02 |
| Short VXX, contango-only (X-check) | 2020–23 | +45.8% | −58.0% | −33.7% | −26.7% | 0.93 |
| Short VXX, contango-only (X-check) | 2024–26 | +5.3% | −52.0% | −24.1% | −31.3% | 0.38 |

The contango filter is on ~92% of all trading days (backwardation is rare), so this is close
to "always short vol, occasionally step aside." It steps aside correctly for all of March
2020 — the ratio was in backwardation every single day that month, so the strategy shows an
exact 0.0% return while buy-and-hold UVXY returned +155.5%. That is the filter's real value:
it goes flat *during* a spike, not before one. It does not protect against a spike that
starts from contango and flips overnight — see Feb 2018 below.

## 3. Same signal with a "5% OTM VIX call hedge," approximated as a capped daily loss

**Approximation stated plainly:** a real 5% OTM VIX call costs an ongoing premium (a
permanent drag) and would not perfectly cap the position's loss (VIX call payoffs are convex
in *VIX*, not linear in the ETP's daily P&L, and settle differently than a same-day stop).
What is modeled here is cruder and far more generous: the short-UVXY position's daily return
is simply floored at −15%, with **no premium charged at all**. That is not a real hedge — it
is a free stop-loss, and the table below shows why the distinction matters:

| Cap on daily loss | Full-period CAGR | Full-period total multiple |
|---|---|---|
| None (strategy 2 baseline) | +42.2% | 191x |
| −20% | +88.4% | 12,700x |
| −15% (headline row below) | +146.1% | 686,000x |
| −10% | +330.2% | 2.85 billion x |
| −8% | +533.8% | 924 billion x |
| −5% | +1,395.8% | astronomical |

| Strategy (−15% cap) | Period | CAGR | Max DD | Worst day | Sharpe |
|---|---|---|---|---|---|
| Hedged short UVXY | 2011–17 | +310.5% | −67.3% | −15.1% | 1.89 |
| Hedged short UVXY | 2018–19 | +5.8% | −60.6% | −15.1% | 0.48 |
| Hedged short UVXY | 2020–23 | +150.6% | −60.8% | −15.0% | 1.49 |
| Hedged short UVXY | 2024–26 | +36.9% | −55.4% | −15.0% | 0.80 |
| Hedged short UVXY | Full | +145.8% | −67.3% | −15.1% | 1.45 |

**This table is not a credible estimate of a real hedged strategy.** The cap only ever
removes losses and never removes a day of gains, so tightening it manufactures unlimited
compounding for free — the same shape as the traps `02_findings/METHODOLOGY_TRAPS.md`
already documents. Tail days worse than −15% happened on 94 of 3,764 days (2.5%); a real
OTM call would offset a handful of those, cost money on the other 3,670, and the honest
strategy-3 CAGR sits between row 2's 42% and this table's fantasy numbers — closer to row 2,
since tail insurance on a 100%+ implied-vol name is expensive and this backtest charges none.

## 4. VRP signal: short vol when VIX exceeds trailing 20-day realised SPY vol by > 3 points

| Strategy | Period | CAGR | Max DD | Worst day | Worst month | Sharpe |
|---|---|---|---|---|---|---|
| VRP short UVXY | 2011–17 | +58.8% | −90.2% | −43.8% | −64.4% | 1.00 |
| VRP short UVXY | 2018–19 | −66.6% | −94.8% | −66.2% | −82.8% | −0.47 |
| VRP short UVXY | 2020–23 | +12.4% | −86.5% | −50.2% | −58.4% | 0.65 |
| VRP short UVXY | 2024–26 | −7.0% | −74.4% | −58.4% | −38.4% | 0.41 |
| VRP short UVXY | Full | +6.7% | −98.6% | −66.2% | −82.8% | 0.61 |

The VRP filter is on 62% of days and flips ~27x/year (vs. ~13x/year for the contango
filter), so it pays roughly 2x the friction, and it is a spread-level signal that cannot
distinguish "elevated but calm" from panic — VIX minus realised vol stays elevated *during*
a crash because realised vol only catches up with a lag. It stayed short into the 2018
blowup (−66.6% for 2018–19, its worst period) instead of stepping aside like the contango
filter.

## Episodes (named as their own rows, per the brief)

| Episode | Window | Buy&hold UVXY | Buy&hold SVXY | Contango-filter (2) | "Hedged" −15% cap (3) | VRP filter (4) |
|---|---|---|---|---|---|---|
| Feb 2018 "Volmageddon" | 2/1–2/28 | +48.2% | −89.6% | −20.9% | −2.9% | −82.8% |
| Mar 2020 COVID | 3/1–3/31 | +155.5% | −38.9% | **0.0%** (flat all month) | **0.0%** (flat all month) | −58.4% |
| Aug 2024 yen-carry unwind | 8/1–8/8 | +49.7% | −22.8% | −44.7% | −27.1% | −38.4% |

Feb 2018 should discipline any confidence in the contango filter: the ratio was still in
contango (0.915) as late as Jan 31, and the position only flipped flat with a one-day lag
*after* the spike — the signal reacted to Volmageddon, it did not anticipate it. Strategy
2's 20.9% loss is that one-day lag compounding on an instrument that moved 96%+ intraday.
Mar 2020 looks good only because the ratio happened to already be in backwardation before
the drawdown started — a timing coincidence, not a lead indicator (VIX3M reacts to the same
information VIX does, just averaged over a longer window).

## Sources

Checked this session with WebFetch only (WebSearch budget was exhausted, so no way to
discover correct URLs beyond guessing). Reporting exactly what worked, per this repo's rule
against implying verification that did not happen.

- **Credit Suisse XIV acceleration notice (Feb 2018): not verified.** SEC EDGAR search
  returned HTTP 503, a guessed accession number resolved to an unrelated Broadwind Energy
  filing, and Wikipedia's XIV-specific URLs 404'd (`/wiki/XIV` resolves to the Roman numeral
  14). The widely reported facts (not re-confirmed here) — Credit Suisse announced Feb 6,
  2018 that XIV's indicative value had fallen >80% intraday on Feb 5, triggering acceleration,
  with final redemption near $4.22 vs. a $99.11 prior close — line up with the one fact this
  session *did* independently confirm, from `en.wikipedia.org/wiki/VIX`: "On February 5, 2018,
  the VIX closed 37.32 (up 103.99% from previous close)."
- **Simon & Campasano, "The VIX Futures Basis: Evidence and Trading Strategies" (Journal of
  Futures Markets, 2014): not verified.** SSRN (`papers.ssrn.com/sol3/papers.cfm?abstract_id=2489222`)
  and the Wiley DOI page (`10.1002/fut.21642`) both returned HTTP 403. The paper's widely-cited
  finding — the VIX futures basis predicts futures returns, and shorting in contango earns a
  positive premium that reverses sharply in backwardation spikes — is directionally consistent
  with what this backtest found independently (strategy 2's Sharpe is positive in every period
  except 2018–19), which is not a substitute for reading the paper.
- **Cboe VPD / VPN index pages: not verified.** Both dashboard URLs returned 404 or a
  JS-rendered shell with no extractable methodology text.
- **Volatility Made Simple / Trading The Odds: not verified.** Trading The Odds returned a
  TLS certificate error; no working Volatility Made Simple URL could be found without search.
- **Robinhood's leveraged/inverse ETP restrictions: not verified.** Guessed support-article
  URLs 404'd; the general support page fetched but its ETP-specific content is JS-loaded and
  not visible to WebFetch.

## Verdict

| Claim | This backtest's answer |
|---|---|
| $5,000 → $50,000 in 5 months (900% cumulative, ~58%/month compounded) | **No strategy here comes close over any real rolling 5-month window.** Best-ever trailing 5-month window, full sample: buy-and-hold UVXY +200% (early 2012, a regime that will not repeat — the fund actively imploding), contango-filter short UVXY +326%, the free-stop-loss "hedged" fantasy version +371%, VRP filter +389%. All are far short of 900%, all require picking the single best window out of 180 months, and every strategy also has a >70% max drawdown somewhere in that same sample. Individual months above 58% do happen (up to 10-11 times out of 180) but not consecutively and not predictably — treating one good month as a run rate is the error `WHAT_WORKS.md` already warns against. |
| ~20%/year, sustainably | **Plausible only for the contango-filtered strategies, pre-cost-of-real-tail-hedging.** Full-period CAGR: short UVXY contango-only +42%, short VXX contango-only (2018+) +16%. Both are dragged down by 2018–19 and both carry max drawdowns near −80% — not a 20%-a-year risk profile, but a strategy that occasionally loses most of its capital and needs years to recover. Buy-and-hold SVXY manages +12.8% CAGR with a −95% max drawdown along the way. None of these are a 20%/year *low-volatility* product; they are a 20%/year *average* sitting on top of Volmageddon-sized drawdowns. |

**Bottom line:** the carry is real and directionally matches the literature (short vol in
contango has positive expectancy over calm stretches), but every version tested here pays
for it with 60-100% drawdowns that hit exactly when a real account would be forced to
de-risk or get margin-called, and the "hedged" version that looks like it solves that
problem only does so because the loss cap in this backtest is free — a real OTM VIX call is
not. Judged against a 58%/month target this is not close by any measure tested; judged
against 20%/year it is achievable on paper only by a trader who can survive an ~80%
drawdown without covering — a different, much harder claim than "20% a year."
