# The measured stock signals as option structures: shares win

**Verdict (2026-10-19).** None of the three stock signals this repo measured as real
survives being expressed as an option. Held to an expiry near the signal's horizon, at the
ask in and the bid out, on seven years of real chains, every structure tested loses per
dollar of risk once the round trip is paid. The shares made money on the same dates. A
headline +100% on the stress long calls was 99% the top 5% of trades, most of them chains
quoted in pre-split units against split-adjusted prices; with those rows removed and the
rest clipped at 3x it is +4% with a median of −36%. The Plays desk therefore LEADS with
shares and prints the option legs beside each play with that structure's own measured
number, so the comparison is on the page.

Reproduce: `05_studies/play_structures_test.py` (writes `opt_panel/play_structures.parquet`,
~25 min, one chain year at a time); the clipped and filtered table is what
`04_live_system/plays.py --priors` prints.

## What was tested

Entries: the signals' own cohorts over 2018-02..2026-08 (surprise 725, ranker 2,117, stress
8,906, of which 1,399 in regime), joined to the Dolt chain panel at the first Friday on or
after the entry date, expiry nearest {95, 35, 21} DTE for {63, 21, 10}-session horizons.
Structures, strikes by Black-Scholes delta from the chain's own IV: 70/40 and 50/25 call
debit spreads, 60- and 80-delta long calls, 30/15 put credit spread (which priced on 2 rows
and is not reported), and the stock held over the same window. Every leg bought at the ask
and sold at the bid; P&L per dollar of max risk at expiry; splits A 2019–21, B 2022–23,
C 2024–26; `cost_pct` is the full round-trip bid-ask as a share of max risk.

## The table as the desk uses it

Rows with the long strike outside 0.5–1.5x spot removed (1,289 of 23,521: VEON at 812 with a
1-strike call and its kind), P&L clipped at −1..+3 per dollar of risk. "Shares" is the stock
over the same dates, risk = notional.

| signal | structure | n | mean | median | hit | A | B | C | bid-ask % risk |
|---|---|---|---|---|---|---|---|---|---|
| surprise | **shares** | 88 | **+7.4%** | +4.3% | 0.60 | — | +7.6 | +4.2 | 0.1 |
| surprise | long call 80Δ | 80 | +5.0% | −4.7% | 0.49 | — | +7.0 | −1.3 | 19 |
| surprise | long call 60Δ | 80 | −2.3% | −43% | 0.40 | — | −22 | −4.8 | 20 |
| surprise | call debit 70/40 | 76 | −5.2% | +3.5% | 0.51 | — | — | −14.8 | 41 |
| surprise | call debit 50/25 | 86 | −19% | −100% | 0.35 | — | — | −19 | 57 |
| ranker | **shares** | 1,380 | **+1.9%** | +0.8% | 0.53 | +1.7 | +2.3 | +1.8 | 0.1 |
| ranker | long call 80Δ | 1,265 | −5.2% | −18% | 0.41 | +2.1 | −8.4 | −7.9 | 12 |
| ranker | long call 60Δ | 1,265 | −8.0% | −59% | 0.35 | −0.2 | −12 | −10 | 11 |
| ranker | call debit 70/40 | 1,160 | −14% | −4.5% | 0.49 | −7.1 | −19 | −16 | 26 |
| ranker | call debit 50/25 | 1,335 | −25% | −100% | 0.32 | −14 | −31 | −27 | 34 |
| stress, VIX > 25 | **shares** | 764 | **+5.6%** | +3.1% | 0.60 | +6.6 | +3.7 | +6.2 | 0.1 |
| stress, VIX > 25 | long call 80Δ | 708 | +4.2% | −8.1% | 0.47 | +7.5 | 0.0 | +0.5 | 20 |
| stress, VIX > 25 | long call 60Δ | 708 | +4.7% | −36% | 0.42 | +8.8 | −1.3 | +2.7 | 21 |
| stress, VIX > 25 | call debit 70/40 | 569 | −4.9% | +11% | 0.56 | −1.9 | −6.1 | −15 | 38 |
| stress, all | **shares** | 3,881 | **+0.9%** | +0.6% | 0.52 | +0.9 | +0.8 | +0.9 | 0.1 |
| stress, all | long call 80Δ | 3,707 | −11% | −21% | 0.38 | −9.1 | −11 | −12 | 18 |
| stress, all | long call 60Δ | 3,707 | −15% | −59% | 0.33 | −13 | −16 | −15 | 16 |
| stress, all | call debit 70/40 | 3,132 | −16% | −6.5% | 0.48 | −15 | −15 | −17 | 32 |

Before the strike filter and the clip the stress long calls read +36% (all) and +99–108%
(in regime) with t 6.5–7.2. That number is on the record so nobody rediscovers it: 99% of
the total P&L came from the top 5% of trades, the largest 1,722x on a 50-cent VEON call
struck at 1 against a split-adjusted spot of 812. Trap 5 (a few prints driving a matrix)
and a data-units error at once.

## What it rules in and out

- **Out:** issuing the surprise, ranker or stress signal as a debit spread or a long call at
  the signal's horizon. The bid-ask alone is 12–57% of max risk; no cell is positive in all
  three splits with a median above −35%.
- **In:** the shares expression, which is already the live books. The Plays desk sizes it
  (RISK_PER_PLAY_USD notional), gives it a timeline and reasoning, and prints the 80-delta
  call priced off the live ladder next to it with its measured number, because the question
  "what if I want this as options" deserves the number rather than a refusal.
- **Open:** the 80-delta surprise call is +5% on 80 trades with a positive B and a flat C,
  a coin flip minus spread. If a later chain pull doubles the surprise sample it is the
  first cell to re-read. Take-profit exits (50% of width) were not tested: they need daily
  chain marks on a thinned panel. Recorded as a proposed branch on the strategy tree.

## Children on the tree

`play-structures-exit-rules` (take-profit at 50/75% of width vs hold), `play-structures-roll`
(roll the 80-delta call up at +50%), `covered-call-on-book` (sell a 30-delta monthly against
the surprise book's shares: the shares measured, the call premium is the open question).
