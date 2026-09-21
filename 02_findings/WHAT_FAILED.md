# What failed

This is the larger and more useful half of the results. Each of these was tested
properly and lost money or showed no signal. They are recorded so they don't get
re-proposed.

---

## Credit structures — all of them, on real quotes

Tested 26 structures × 4 DTE targets × 2 hold rules × 11 regimes on **147,350
real-quote SPY trades**, entering at the ask and exiting at the bid.

**Every single credit structure had negative expectancy**, with |t| > 9. Iron
condors, iron butterflies, jade lizards, broken-wing butterflies, Christmas
trees, twisted sisters, strangles — all negative.

GEX and DIX gating did not rescue any of them. Neither did regime filtering.

The reason is not subtle: the variance risk premium that makes these strategies
look profitable at mid-price is smaller than the bid-ask spread you actually pay
to get in and out. Backtests that fill at mid show a positive edge. Backtests
that fill at the ask and exit at the bid show the opposite.

> A previously-reported "+3.7% condor edge" from an earlier session was
> **retracted** — it came from mid-price fills and a survivorship-filtered exit
> chain. See [METHODOLOGY_TRAPS.md](METHODOLOGY_TRAPS.md) traps 1 and 2.

## Far-OTM lottery buying

**10,535,928 option purchases** held to expiry, worthless counted as −100%.

Returns ran **−90% to −48%** depending on how far out you go. Cheaper contracts
were consistently worse. The volatility smile *is* the market's fat-tail
adjustment, and it is priced roughly right — actually overpriced at the extreme
tail.

Tails are genuinely fat: **11× / 177× / 9,914×** more frequent than Gaussian at
3σ / 4σ / 5σ. The tails are real. They are also already in the price.

The "$200 → $1M, only one has to hit" thesis does not survive contact with ten
million actual purchases. What partially rescues it is moving closer to the money
(16–30 delta) and filtering hard on spread — see [WHAT_WORKS.md](WHAT_WORKS.md).

## Earnings straddles

**−35.03% per trade, t = −95.7** across 12,035 ATM straddles, bought at the ask
and sold at the bid.

**CORRECTED 2026-08-25 — the number is right, the label was wrong.** This was
presented as evidence that implied volatility overprices earnings moves. It is
mostly evidence about **single-stock option spreads**.

Three things force that reading:

| check | result |
|---|---|
| return when IV **rose** into the exit | **−29.65%** (n = 3,545) |
| return when IV fell | −37.28% (n = 8,490) |
| Milian (2023, *JRFM*), same trade at **mid** | mean +0.48% (n.s.), **median −17.69%** |

A straddle buyer whose implied vol *rose* over a two-day hold with 15 DTE
remaining should not lose 30%. Theta over that window is worth roughly 6%. The
rest is the bid-ask, paid on **four legs** — call and put, in and out.

Against Milian's mid-price median of −17.69%, our −39.55% median implies roughly
**22 points of round-trip spread**. That is the finding: the IV-crush component
is real but is about half the size, and the other half is execution on
single-stock options.

**And the study tests the opposite trade from the paper it cites.** Its own
docstring quotes Gao, Xing & Zhang for a straddle held *"from one day BEFORE an
earnings announcement **to the announcement date**"* — then specifies *"EXIT the
first snapshot **after**."* GXZ exit **before** the release and capture the IV
ramp (+3.34%, *JFQA* 2018). We held through it and captured the crush.

**GXZ's actual trade — enter T−3, exit before the release — has never been
tested here.** See `07_research_bank/reports/04_event_driven.md`.

## Weekly single-name direction — every documented predictor, on real chains

Measured 2026-09-21 on 214,803 name-weeks (1,845 names, 2019–2026): the Cremers-Weinbaum
call–put IV spread (IC +0.002), the Xing-Zhang-Zhao smirk (wrong sign in all three splits),
the risk reversal (t −2.3, backwards), IV changes, momentum, the 52-week high and the borrow
fee all sit inside the multiple-testing noise bar at a one-week horizon. The best composite
calls the sign right 52% of the time. A 14-DTE vertical costs 8.4% (credit) to 14.5% (debit)
of its risk in bid-ask alone. There is no weekly direction edge large enough to buy options
on. [weekly_predictors.md](weekly_predictors.md), [weekly_structure.md](weekly_structure.md).

## Intraday direction

No robust intraday directional edge on SPX or NDX, across every combination
tested. The empirical result and the published literature agree. The vendor's
own per-minute signed options flow (103 sessions, 2026) is the one input that
looks like a small real effect — positive in every cell, one-sided hit rates —
and it is worth 1–2 bp a trade against a 5–10 bp round trip. [uw_flow.md](uw_flow.md).

The only intraday-adjacent effect that held up is **overnight drift** — and it is
too small to pay for options premium.

## Sector rotation

IC ≈ 0. Pinned to a hard zero in the registry.

## MRNA +177% — could it have been predicted?

Asked directly, tested directly. Answer: **no.**

- 0 of 200 unusual-flow alerts fired on MRNA before the move
- Implied volatility was *falling* into the event
- Across 810,300 ticker-days, the candidate pre-event signals showed lift of
  **0.68–1.02×** — that is, no better than chance, and several were worse

The move was information the market did not have. No signal in the data
anticipated it. This is the honest answer to "find what could have predicted
it," and it is why the Black Swan tab screens on *convexity and execution cost*
rather than on prediction.
