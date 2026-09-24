<!-- research brief, filed 2026-09-23; agent output verbatim -->

## Retail trading base rates: what fraction of people who day-trade (or run a bot) actually make money

Report date: 2026-09-23. Method note: this session's web-search budget was confirmed exhausted
(direct test, see §1). Numbers below come from a PDF already extracted to a local scratch file
this repo keeps (Barber, Lee, Liu, Odean, Zhang 2017, "Do Day Traders Rationally Learn About Their
Ability?" — the Taiwan Stock Exchange paper, distinct from the "Cross-Section of Speculator
Skill" paper already cited in `bot-claims-audit.md` though the two share authors and a data set),
from direct `WebFetch` of primary or near-primary pages, or are marked **not verified** where a
source could not be reached (BIS's PDF returned only landing-page metadata on four attempts,
direct `curl` included; NFA, Reuters, Robbins Trading Co. and CoinDesk all 404'd or refused;
Collective2/Darwinex were not reachable in the time budget and are omitted rather than guessed).
This extends `bot-claims-audit.md` (Brazil/Chague et al. and Taiwan/Barber's *Cross-Section of
Speculator Skill* are already there) rather than re-deriving those two.

### 1. Base rates, by market

| Source | Population / period | Share profitable | Notes |
|---|---|---|---|
| Chague, De-Losso, Giovannetti 2020 ([SSRN 3423101](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101), Brazil mini-Ibovespa) | 19,646 first-time day traders, 2013–15 | 29.8% after 1 day → **3.0% after 300+ days** (n=1,551) | See `bot-claims-audit.md` §4. "No evidence of learning by day trading." |
| Barber, Lee, Liu, Odean, Zhang 2017, ["Do Day Traders Rationally Learn About Their Ability?"](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf) (Taiwan) | ~140,000 individuals day-trade/month, 1992–2006 | **~5%** of active day traders are "profitable" (10+ days' experience, positive lifetime profit); **under 3%** of all day traders are *predictably* profitable | Full detail in §2, extracted from the paper's text this session |
| Barber, Lee, Liu, Odean, [*Cross-Section of Speculator Skill*](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf) | 360,000/yr Taiwan day traders, 1992–2006 | **Fewer than 1%** outperform predictably | In `bot-claims-audit.md` §4; top 500 by prior-year rank earn 28.1 bps/day after fees |
| Bryzgalova, Pavlova, Sikorskaya, *JF* 2023 (US retail options) | Nov 2019–Jun 2021, >60% of options volume | Retail "lose money on average" | In `bot-claims-audit.md` §4; ~12.6% average bid-ask spread on the weeklies retail prefers |
| UK FCA 2016 CFD sample, cited by ESMA's 2018 EU-wide intervention | sample of CFD-firm client accounts | **82%** of clients lost money, average loss **£2,200** | Via [Wikipedia's CFD article](https://en.wikipedia.org/wiki/Contract_for_difference), which attributes this to the FCA; ESMA's own PDF pages returned 403/empty — **not independently verified against the primary FCA document** this session |
| eToro copy-trading [risk disclosure](https://www.etoro.com/copytrader/risk-warnings/) | ongoing, EU retail CFD accounts | **51%** of retail CFD accounts lose money | In `bot-claims-audit.md` §4 |
| BIS Bulletin 69, [Cornelli/Doerr/Frost/Gambacorta](https://www.bis.org/publications/bulletin-69-crypto-shocks-and-retail-losses), Feb 2023 (retail bitcoin) | major crypto platforms, Aug 2015–Dec 2022 | "**A majority** of crypto app users in nearly all economies made losses on their bitcoin holdings" | Exact percentage/country breakdown are in the 8-page PDF body, unreachable this session (landing-page metadata only, four attempts) — **not verified** beyond the qualitative finding |
| Jordan & Diltz 2003, *FAJ*, "The Profitability of Day Traders" | 324 accounts, one Houston prop firm, 1998–99 | Commonly cited as: a minority consistently profitable, most lost or broke even | **Not verified this session** — no fetchable copy reached; flagged, not guessed |
| Welch 2022, *JF*, "The Wisdom of the Robinhood Crowd" | Robinhood popularity data, 2020 | Commonly cited as: aggregate RH portfolio tracked the market better than the "meme-stock disaster" narrative implied | **Not verified this session** — SSRN returned 403 |
| Barber, Huang, Odean, Schwarz 2022, *JF*, "Attention-Induced Trading and Returns" | Robinhood users | Commonly cited as: attention-driven, crowded buying predicts **worse** subsequent returns | **Not verified this session** — NBER link resolved to an unrelated paper |
| CFTC/NFA retail forex quarterly disclosures | ongoing, US-regulated FX dealers | Dealers must publish the share of accounts profitable each quarter; commonly summarized as a minority | **Not verified this session** — nfa.futures.org 404'd |
| Robbins World Cup Trading Championship | decades of entrants, audited top finishers | Winners post four-digit % annual returns (Larry Williams, 1987, is the famous case) | **Tail-selection artifact, not a base rate** — publishes winners, not the field's loss rate. Site unreachable this session (DNS failure) |

### 2. What the Taiwan "rationally learn" paper adds, in its own numbers

This paper (extracted from a local PDF-to-text dump this session, not re-fetched) studies the same
Taiwan Stock Exchange population as the Cross-Section paper but over persistence and survival,
not just skill ranking:

- Day trading is ~20% of total TSE trading volume every year from 1995–2006, run by just under 1%
  of the adult population in an average month (~140,000 of ~16M adults).
- Across the sample, **the fraction of day traders classified "profitable" (10+ days' experience,
  positive lifetime profit) is consistently about 5%**; unprofitable traders are the majority and
  generate 72–80% of day-trading dollar volume.
- Of all day-trading volume, only **9.81%** comes from traders who are *predictably* profitable
  (profitable now and staying profitable), and those traders are **fewer than 3%** of the day-trading
  population on a given day.
- Persistence is high regardless of results: previously **unprofitable** traders with 50+ days'
  experience have a **95.3%** chance of trading again within 12 months; previously **profitable**
  traders with similar experience have **96.4%** — almost the same rate. Survival (still trading
  at all) is 44% at one year, 24% at two years, 15% at three years; "more than 75% of all day
  traders quit within two years."
- The paper's own conclusion: aggregate day-trading returns are negative and persistence in the
  face of losses is "inconsistent with models of rational learning" — traders are not quitting
  because they learned they're unskilled, and the ones who keep going after losses are not doing so
  because the evidence told them to.

### 3. What profitable retail traders have in common, across these papers

1. **A track record precedes the profit, it doesn't follow it.** In both Taiwan papers, traders
   who go on to earn money are identified by *past* performance over 40+ days of experience —
   profitability is a persistent trait of a small group, not a skill developed by trading more.
   The Cross-Section paper's top 500 (by prior-year rank) earn 28.1 bps/day after fees; the bottom
   cohort loses 34.2 bps/day. Neither paper shows an unprofitable trader converting to profitable
   through practice.
2. **They trade less, not more.** Both "profitable" and "unprofitable" persistent categories
   exclude occasional traders by construction (under 10 days' experience); volume is dominated by
   unprofitable traders (72–80% of $ volume) trading a lot, while predictable profitability rides
   on under 10% of volume.
3. **They survive selection, and persistence isn't the sign.** Fewer than 3% of day traders and
   under 1% of the wider population are ever predictably profitable, while unprofitable traders
   persist almost as long as profitable ones (95.3% vs. 96.4% chance of continuing) — so still
   trading after losses carries no information about being one of the few.
4. **Costs are the mechanism, not a footnote.** Every profitable/unprofitable gap here is measured
   *after* fees, spreads and taxes — Taiwan's 40bps round-trip costs, the ~12.6% average spread on
   US options weeklies, the FCA's £2,200 average CFD loss. Structurally expensive instruments
   (leveraged CFDs, cheap weekly options, high-frequency FX) select against retail mechanically,
   independent of any skill question.

### 4. The $5,000 → $50,000 in 5 months question

A 10x in 5 months (~105 sessions) is +2.22%/session compounded, every session, with zero
drawdown tolerance built into that math. Nothing above supports this as a plausible outcome:

- The best-documented persistently-skilled cohort — Taiwan's top 500 day traders, selected *after*
  a demonstrated winning year — earned **28.1 bps/day** after fees, compounding to roughly **+34%**
  over 105 sessions, not +900%. That is the ceiling this literature has measured for real,
  ranked, skill-selected traders — and even they are under 1% of everyone who attempts day trading.
- Closing that gap (+34% measured vs. +900% wanted) in five months means leverage or instrument
  choice (options, CFDs, leveraged crypto) — and every base rate here for those instruments (BPS
  options, FCA/ESMA CFDs, BIS bitcoin, eToro) shows retail losing money on them on average.
  Reaching for 10x mechanically means reaching for the worst base rates in this table.
- **Estimated probability $5,000 becomes $50,000 in 5 months: well under 1%**, realistically closer
  to ~0.1% or less (under 3% chance of being predictably profitable at all, and no documented
  cohort compounding anywhere near 2.2%/session for 105 straight sessions). This is a Fermi
  estimate built from the table above, not a number any paper states directly — **reasoned, not
  measured.**
- **Estimated probability the $5,000 is cut in half or worse: high, most plausibly 40–70%** if
  reaching for 10x requires meaningful leverage or short-dated options — based on the majority-loses
  rate across every leveraged/short-dated instrument measured here (CFDs 82%, options negative on
  average, crypto majority losing, eToro 51%), and the fact that chasing an extreme target
  mechanically means position sizes or instruments with fat downside tails. **Not a published
  number — this brief's own estimate, explicitly not verified.**

### 5. Bottom line

Every base rate here — Brazil, Taiwan (both papers), US retail options, EU CFDs, eToro, the
qualitative BIS crypto finding — points the same way: a small, stable minority (roughly 1–5%,
depending on the market and how strictly "predictably profitable" is defined) makes money after
costs, identifiable mostly by a track record that predates the profitable period being measured,
while the majority's losses concentrate in exactly the leveraged, short-dated instruments a trader
would need to turn $5,000 into $50,000 in five months. Nothing here describes a path from zero
track record to 10x in 5 months; it describes, repeatedly, the opposite — persistence without
learning, in a game costs are built to make the house's.
