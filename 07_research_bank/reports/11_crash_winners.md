# 11 — Crash winners and strictly bounded structures

**Status:** complete · **Evidence quality:** high — price data measured live, not
recalled; unverified claims marked as such by the agent · **Relevance:** tells us
*which* instrument to hold and *when*, and settles the bounded-loss constraint

---

## The index put is the RELIABLE crash instrument — rarely the MAXIMAL one

Three of five events refute index-centric tail thinking:

| event | index put | the actual biggest multiple |
|---|---|---|
| **Feb 2018** | mediocre — SPY only −11.8% | **SVXY/XIV puts, VIX calls (100×+)** |
| **Mar 2020** | genuinely good, SPY −32.6% | **single-name cruise/airline puts** — CCL −82.2%, RCL −83.7% |
| **Mar 2023 SVB** | **≈ zero** — SPX fell low single digits | **SIVB / FRC / SCHW / KRE puts (10–100×)** |
| **Aug 2024** | poor — SPX −3% on the day | Nikkei puts, long JPY — and **not** VIX calls |
| **Apr 2025** | **excellent** — competitive with anything | index put won |

Measured drawdowns, Feb 19 → Mar 18–23 2020: SPY −32.6%, **CCL −82.2%**,
**RCL −83.7%**, UAL −78.4%, KRE −48.5%.

March 2023 is the cleanest refutation in the dataset: **SCHW fell 41.3% in five
sessions and KRE 31.1%, while SPX barely moved.** An SPX put made nothing.

### The August 2024 VIX trap — worth internalising

Spot VIX printed **65.73** intraday on 5 Aug 2024, a 2.8× on the prior close.

> **VIX options settle off VIX *futures*, not spot VIX** — and the 65.73 print was
> largely an artefact of stale, wide SPX opening quotes. Front futures never
> approached that level, so **VIX call holders did not capture the headline
> move.**

Anyone backtesting "buy VIX calls, VIX spiked 2.8×" against spot would compute a
fantasy.

**The cost of the non-obvious winner:** severe selection risk. For every CCL there
were names that fell 20%. You must be right about *which* thing breaks, not just
*that* something breaks.

---

## Frequency — and the windows are days, not months

Verified from the S&P 500 largest-daily-declines table: **days worse than −7.5%
since 1990 (~9,050 sessions): seven, in exactly two clusters** (four in 2008,
three in 2020). Only three days worse than −10% in all history.

| magnitude | frequency |
|---|---|
| drawdown ≥ 10% | ~5–6 per decade |
| drawdown ≥ 20% | ~1.5 per decade |
| drawdown ≥ 30% | ~1 per 12–15 years |
| **VIX ≥ 2× from a sub-20 base within a month** | **9 in 16 years ≈ 1 per 1.8 years** |

> A 30–50 delta option needs a move so large it is essentially a once-per-decade
> event. It is the **5–15 delta** option that 10xs on a routine ~1-per-2-years
> dislocation — at the cost of an **85–95% chance of expiring worthless each
> attempt.**

**Each window lasts 2–5 trading days.** Aug 2024: two. Apr 2025: four. Feb 2018:
three. In April 2025, holding one session too long cut the payoff by more than
half — VIX collapsed 52.33 → 33.62 in a single day on the tariff pause, alongside
the largest S&P gain since 2008 (+9.52%).

## The winners were NOT early

| | positioned for |
|---|---|
| **Ackman** — $27M premium → **$2.6bn, ~96×** | **~3 weeks** |
| Feb 2018 SVXY puts | 8 sessions from an all-time high |
| Aug 2024 / Apr 2025 windows | 2–4 days |

Note Ackman's instrument was **investment-grade CDS index protection**, not equity
puts — not retail-accessible. And even Universa, the canonical tail fund, holds
OTM puts on **the S&P 500 *and* individual financials** (Goldman, AIG) — not a
pure index book.

## The cost of being early disqualifies a standing hedge at $5k

Verified: a portfolio of **3.3% Universa + 96.7% passive S&P compounded at
12.3%/yr over the decade to Feb 2018**, versus ~8.6% for the index alone. The
instructive reading: **that 3.3% sleeve was near-totally consumed in most years
and paid for the whole decade in 2008 alone.**

A continuous ladder of 30-day ~10-delta SPX puts costs roughly **0.4–0.6% of
notional per month ≈ 5–7%/yr**, paying off in perhaps 5–10% of months.

> **If the entire $5k *is* the premium budget, continuous tail positioning is
> disqualified by arithmetic.** At ~100% loss per 30-day attempt the budget is
> gone in well under a year, and the ~1-per-2-years event will very likely not
> arrive inside that window.

**The frequency data argues for few, event-conditioned, large bets held for days
— not a standing hedge.** That independently reproduces the bold-play conclusion
from the martingale math.

---

## Strictly bounded structures — the constraint settled

### Tier A — truly bounded, zero assignment path

**European-style, cash-settled index options: SPX, XSP, NDX, RUT, VIX, NANOS.**

Cboe's own SPX spec, verified: *"European… Options can only be exercised at
expiration… eliminating early assignment risk"*, *"Positions settle directly to
cash at expiration without the need to deliver or receive unwanted shares."*

Long calls/puts, debit verticals and long butterflies on these have **max loss =
debit paid, full stop.**

> **Sizing note: SPX is $100 × index ≈ $650k notional per contract. For a $5k
> account, XSP (1/10th size) is the correct vehicle — and it keeps Section 1256
> 60/40 treatment.**

This converges exactly with report 10's tax finding. **XSP is simultaneously the
only structurally safe vehicle and the tax-advantaged one.**

### Tier B — bounded at expiry, but with a live assignment path

Long options and debit spreads on **American-style, physically settled** options
(SPY, QQQ, single names). Three real failure paths on a $5k account:

1. **Exercise-by-exception** — OCC auto-exercises any long option $0.01 ITM at
   expiry, delivering 100 shares you cannot pay for → Reg T call → forced
   liquidation at Monday's open. **A long option can cost more than premium this
   way.**
2. **Early assignment on the short leg** of a debit spread → short/long 100 shares
   overnight, margin call, broker auto-liquidation at market.
3. **Dividend-driven early exercise** on short calls.

Mitigation is behavioural, not structural: **close everything before expiration
day.**

### Tier C — DISQUALIFIED (can owe more than deposited)

- Naked short calls/puts — unbounded
- **Credit spreads / iron condors** — max loss = width − credit, which *exceeds
  premium received*, plus an assignment path
- **Box spreads on American options** — 1R0NYMAN: $5,000 principal, **>$57,000
  realised loss, $212,500 maximum exposure**
- **Ratio backspreads** — the net position is bounded, but that maximum
  *substantially exceeds premium paid* and needs margin collateral. Bounded ≠
  bounded-by-premium.
- Broken-wing butterflies — unequal wings create a one-sided tail
- **Options on futures** (CL, ES) — the April 2020 negative-oil episode showed a
  broker chasing a client for a debit balance

### The strongest structural safeguard

> **Cash account (no margin agreement, so borrowing is mechanically impossible)
> + European cash-settled index options only + never hold into expiration day.**
>
> That combination has **no mechanical path to a negative balance.**

---

## What this implies for the plan

1. **XSP, not SPY** — bounded by construction, and 60/40 taxed.
2. **5–15 delta**, not 30–50 — the latter needs a once-per-decade move.
3. **Event-conditioned, not standing** — the carry disqualifies a continuous
   ladder at this stake.
4. **Hold days, not months** — every window in the dataset was 2–5 sessions, and
   holding too long cost more than half the payoff in April 2025.
5. **Expect 85–95% of attempts to expire worthless** — that is the base rate for
   the delta band that can actually 10x.
