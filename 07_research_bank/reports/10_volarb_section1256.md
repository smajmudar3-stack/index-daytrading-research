# 10 — Vol arb, dispersion, and the one statutory edge

**Status:** complete · **Evidence quality:** the tax finding is **statutory, not
empirical** — no decay, no model risk, no execution risk · **Relevance:** near
zero on strategy; the single highest-confidence number in the bank on tax

---

## The finding: Section 1256

Broad-based index options (**SPX, XSP, NDX, RUT, VIX**) are "nonequity options"
under 26 USC §1256 and are taxed **60% long-term / 40% short-term regardless of
holding period.** SPY, QQQ and single-stock options are **not** — they are 100%
short-term for a day trader.

The edge reduces to a clean identity (NIIT applies to both and cancels exactly):

> **After-tax edge = 0.6 × (ordinary rate − LTCG rate)**

### Applied to this exact goal — a $45,000 gain on a $5,000 stake

| bracket | tax via SPY options | tax via SPX/XSP | **saved** | **as % of the $5k stake** |
|---|---:|---:|---:|---:|
| 22% | $9,900 | $8,010 | **$1,890** | **37.8%** |
| 24% | $10,800 | $8,370 | **$2,430** | **48.6%** |
| 32% | $16,110 | $11,520 | **$4,590** | **91.8%** |
| 35% | $17,460 | $12,060 | **$5,400** | **108.0%** |

> **Trading the identical view in SPX/XSP rather than SPY returns between 38% and
> 108% of the entire starting stake — risk-free, purely as a tax consequence.**

No execution risk, no model risk, no edge decay. It is statutory.

### Three more 1256 features that matter specifically here

1. **No wash-sale rule.** §1091 covers "stock or securities"; 1256 contracts are
   marked to market instead, so the disallowance is inapplicable. A losing SPX
   position can be rebuilt immediately.
2. **Three-year loss carryback** (Form 6781 election). A 1256 loss can be carried
   *back* three years against prior 1256 gains for an immediate refund.
   Equity-option losses only carry forward against a $3,000/yr ordinary cap.
   **This asymmetry directly rewards the "total loss acceptable" framing.**
3. **Cash settlement + European exercise.** XSP/SPX **cannot be assigned early.**
   No pin risk, no overnight assignment of a $650k share position into a $5k
   account. That is a real, non-tax reduction in exactly the disqualifying tail
   report 09 identified.

**Caveats:** federal-only (most states don't distinguish LT/ST); §1092 straddle
rules can defer losses on offsetting positions.

---

## Everything else in this domain is the wrong shape

**Dispersion is dead for retail, and the paper says so.** Driessen, Maenhout &
Vilkov (*JF* 2009) find the correlation-risk strategy **"cannot be exploited with
realistic trading frictions"** — a top-tier journal, on institutional cost
assumptions, in a wider-spread era. A miniature version needs 40+ option legs;
round-trip friction is 300–600 bps against an edge worth 100–200 bps. **Costs are
2–4× the edge.**

DMV also settle a question worth knowing: **the correlation risk premium and the
index VRP are the same thing.** Single-stock variance risk premia are near zero;
essentially the entire index VRP is compensation for correlation risk. The index
is expensive *because correlation is expensive*.

**Gamma scalping is arithmetically impossible at $5k.** One XSP contract is
~$65,000 notional; at 0.5 delta you must hedge ~$32,500, and your finest
available hedge — one MES future — *is* $32,500. You can only hedge in 0.5-delta
chunks, which means running enormous residual delta and calling it a vol trade.
**Minimum viable account: $50–100k.** Even then, the SPX VRP (1–3 vol pts) is
comparable to the round-trip spread on the straddle itself (1–2 vol pts).

**Short VIX / VRP harvest** is mechanically possible and is *exactly* the
strategy that produces a 90%+ single-day loss. Wrong shape for "10x once," right
shape for "zero once."

## How vol sellers actually die — all four died in gaps, not grinds

- **XIV, 5 Feb 2018.** VIX closed **37.32, +103.99%**. Inverse VIX ETPs must *buy*
  VIX futures at the close in proportion to the day's move; that buying hit a
  thin 4:00–4:15pm book, pushing futures higher, which increased the required
  buy. **A mechanical feedback loop, not a fundamental repricing.** XIV fell ~96%,
  tripping Credit Suisse's 80% acceleration clause. **The rebalance rule killed
  it, not the vol move.**
- **LJM Preservation & Growth**, same two days: short SPX strangles, −80%+,
  liquidated. Short gamma into a gap with no capacity to wait.
- **Allianz Structured Alpha**, Feb–Mar 2020: **over $6 billion** lost;
  AllianzGI pleaded guilty to criminal securities fraud in 2022. Mechanism: the
  long tail hedges were **too far OTM to pay off at the speed the market actually
  moved** — calibrated to a slower crash.
- **Malachite Capital**, Mar 2020: short-vol book, closed.

> **Short convexity is short liquidity.** You are not paid for volatility — you
> are paid for accepting a forced-buyer position at the worst possible moment.

## Where the VRP is largest (the ranking tracks danger, not free money)

1. **Crypto/BTC — largest.** Consistent with report 06's +14% vs ~2% for SPX. But
   **BTC options are not 1256 contracts**, venues are thin, tails are fatter.
2. **Single-stock equity — near zero** after correlation adjustment. This is why
   dispersion works and why naked single-name premium selling doesn't.
3. **Index equity (SPX)** — 1–3 vol points, now heavily competed by 0DTE flow and
   covered-call ETF supply.
4. **Commodities** — real, but two-sided (April 2020 negative oil settlement).
5. **Rates/FX** — smallest.

---

## Could any of it reach 10x? No — and the shape is the reason

A Sharpe-1.0 strategy at 15%/yr needs **16.4 years** to 10x. A spectacular
Sharpe-2.0 book at 40% vol needs **7 years**. To 10x in a year you need ~+900%,
which at Sharpe 1.0 requires ~900% annualised volatility — a ~90% chance of ruin
along the way.

> Vol RV strategies are **high-hit-rate, low-payoff, left-tailed.**
> This goal requires **low-hit-rate, high-payoff, right-tailed.**
> They are opposite shapes.

**The only 10x-shaped trade in this domain is the inverse of everything above:**
be the counterparty to the vol sellers. Long far-OTM VIX calls or SPX put
butterflies when implied correlation and VIX carry are at extremes. On 5 Feb 2018
a **~$0.30 VIX call went to ~$8 — 25× in one afternoon.**

The agent's own honest probability, which it declined to dress up: such gaps
occur **once every 2–4 years**, you must hold the right strike in the right
expiry in the right week, and the position bleeds to zero every month you are
wrong. Buying monthly with 1/12 of the bankroll gives roughly **2–5% probability
of a 10x in a year, with clearly negative expected value.**

## This domain's actual contribution

**Near zero on strategy. ~5–12% of winnings on tax.**

If any other domain finds a genuine 10x-shaped trade, **route it through SPX/XSP
rather than SPY** and keep an extra $1,890–$5,400 on a $45,000 gain for free.
That is the finding most likely to survive scrutiny in the entire bank, because
it is statutory rather than empirical.

## Testable

1. **Implied-correlation regime test** — COR1M/COR3M vs forward 21-day realised
   correlation, 2010–2026. Enter when COR3M < 15th percentile. Tells you whether
   the *reverse* dispersion trade is attractive at today's low implied
   correlation.
2. **XSP vs SPY execution-cost census** — 30 days of NBBO on ATM 30-DTE. Decides
   whether the 5.4pp tax edge survives execution. Expected: yes for holds > ~1
   day, no for 0DTE churn.
3. **VIX roll with and without Feb 2018 / Mar 2020** — the gap between those two
   numbers is the entire honest story of the strategy.
