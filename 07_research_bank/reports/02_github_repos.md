# 02 — GitHub repos claiming high options returns

**Status:** complete · **Evidence quality:** fill code read directly from source
for the key verdicts · **Relevance:** identifies the one credible benchmark and
the calibration constant for fake results

---

## Headline

> Across every repo using **real bid/ask quotes with the spread charged on
> fills**, nothing produces anything close to 30%/month. The best-evidenced
> result in the entire search is **net Sharpe ~0.9 on ~4.8% of notional/year**.
> Every repo claiming multi-hundred-percent returns was pricing options with
> Black-Scholes on synthetic vol — **not one exception.**

---

## The credible benchmark: Vilkov 0DTE

`vilkovgr/0dte-strategies` (51★, MIT) — replication package for SSRN 4641356.
Cboe 30-min SPXW bars + ThetaData, **Sep 2016 – Jan 2026 (9.4 years)**, strict
expanding-window OOS from Apr 2019, date-clustered SEs, Benjamini-Hochberg
correction, ships a test that byte-compares generated tables to published ones.

| strategy | SR gross | **SR net** | net bps/day | hit rate |
|---|---|---|---|---|
| **put ratio spread** | 1.18 | **0.93** | 1.91 | 67% |
| top-3 basket | 1.12 | **0.82** | 1.36 | — |
| strangle/straddle | 0.56 | 0.39 | 1.20 | 72% |
| **iron butterfly/condor** | 0.77 | **−0.20** | −0.11 | 64% |
| risk reversal | 0.01 | −0.11 | −0.45 | 75% |

**The iron condor row is the cleanest refutation of the entire "0DTE income"
genre on the internet**, produced by someone with the data to prove it — and it
independently confirms our own `options-structure-null`.

Unconditional VRP at 10:00 ET: **0.0011% of spot** — "too small to monetize
after realistic frictions."

### The arithmetic that closes the 30%/month question

1.91 bps/day × 252 = **4.81% of notional/year** at net SR 0.93. Vilkov reports
daily 1% expected shortfall of 0.58–1.58% of underlying.

| target | required leverage | daily ES₁% as % of capital | verdict |
|---|---|---|---|
| 30%/year | ~6.2× | 3.6–9.8% | achievable, brutal to hold |
| 100%/year | ~21× | 12–33% | one bad day is career-ending |
| **30%/month** | **~75×** | **43–118%** | **ruin, typically within weeks** |

At 75× the *routine* 1-in-100 day wipes out half to all of capital. Not "risky
but possible" — mathematically guaranteed to blow up given enough trading days.

---

## The calibration constant for this entire genre

`oyzh888/0dte-options-strategy` claims **"Iron Condor: Sharpe 7.77, win rate
93.6%"** from an engine where **0DTE IV = VIX × 1.6** — a fixed multiplier that
*manufactures* a variance premium of exactly the needed size.

What makes it the most instructive repo found: **the same README, three
paragraphs earlier, states the lesson and then ignores it**:

> *"Bought ATM straddles using ML jump predictions. Looked great in simulation
> (Sharpe 13.64) but completely failed with real Alpaca options prices
> (Sharpe −20.9). Theta decay + bid/ask spreads eliminated any edge.
> **Lesson**: Simulated backtests with synthetic option prices are dangerously
> misleading."*

**Sharpe 13.64 → −20.9 on the same strategy when real quotes were substituted.**
A ~35-point swing attributable purely to synthetic pricing. Treat that as the
calibration constant.

## The worst offender, dissected

`randomwalkhan/Short-Term-Reversal-Strategy` (256★) claims **+690.85% return,
4.32 Sharpe**. Six independent fatal flaws:

1. **No option prices at all** — every option priced by Black-Scholes using
   20-day trailing realised vol from Yahoo daily closes.
2. **Uses realised vol as implied vol on the exact setup where the gap is
   widest** — buys 30-DTE ATM calls right after a large drop, when IV spikes.
   Systematically buys at a fabricated discount on every trade.
3. **`LIMIT_BUY_DISCOUNT_PCT = 0.10`** — enters 10% *below* its own theoretical
   mid. Negative slippage, hardcoded, as large as the profit target.
4. **Intra-bar look-ahead on both sides** — entry marked at the day's best price,
   exit at the day's best price, using bar extremes unknowable at decision time.
5. **One-year backtest**, 2025–26, on SOXL/TQQQ/UPRO/MSTR/COIN/PLTR.
6. **The universe IS the fitted parameter**, and their own README proves it:

| universe | return | Sharpe |
|---|---|---|
| qqq_only_filtered | **+552.91%** | 2.93 |
| spy_only_filtered | +36.28% | 0.73 |
| nasdaq_only_filtered | **−30.21%** | **−0.15** |

They selected the top row ex-post.

## A critical tooling warning

**`optopsy` (1,461★) defaulted to MID-PRICE fills until 2026-03-20.** Issue #249
changed it, reason given: *"The 'mid' default was overly optimistic."* Optopsy
has existed since ~2018.

> **Every optopsy result published anywhere before March 2026 — every blog post,
> every YouTube "I backtested iron condors" video, every fork — used mid-price
> fills and is worthless.** Pin ≥ v2.3.x, never pass `slippage="mid"`.

## Other honest sources worth knowing

- **`lambdaclass/options_portfolio_backtester`** (264★) — buy-at-ask/sell-at-bid
  is the *documented default*. Their own research is negative: the Spitznagel
  tail hedge is "**~neutral over full 1996–2025 — the article's strong result is
  a 2008-start effect**," and they document "**a +12pp false discovery caught by
  decomposition**." Also flags that 40–45% OTM strikes **are not listed** in the
  2000–2002 SPX chain, so dot-com backtests at that depth are coverage artifacts.
- **`YichengYang-Ethan/0dte-strategy`** — ask-in/bid-out fills, maintains a public
  kill-log. Key finding: a signal with **profit factor 1.67 on the underlying**
  lost **41% of its edge to a long-call wrapper and 95% to a debit spread.**

---

## Testable protocols extracted

**D1 — Vilkov conditional put ratio spread.** SPXW 0DTE, entry 10:00 ET, hold to
cash settlement. Moneyness K/S ∈ [0.98, 1.02] step 0.001. L2 logistic on
`P(net PnL > 0)`. **Hard mapping `w = sign(p − 0.5) ∈ {−1,+1}`** — the paper finds
hard ≥ soft, and **binary direction target ≫ return-magnitude target**. Target to
beat: net SR 0.93.

**D3 — Iron condor as an ENGINE CALIBRATION TEST.** Gross SR 0.77, net **−0.20**.
*If our engine reproduces a positive net iron condor Sharpe, our fill model is
broken.* Run this before trusting anything else the backtester says.

**D5 — Wrapper-cost decomposition.** Measure any signal on the underlying FIRST,
then measure what each option wrapper costs. Signal PF 1.67 → long call keeps
59% → debit spread keeps 5%. Most "the strategy failed" results are actually
"the wrapper ate it," and the two demand different fixes.

## Data sources and real pricing

| vendor | price | what you get |
|---|---|---|
| **lambdaclass `data-v1` mirror** | **free** | SPY 2008–25 EOD chains + Greeks, SHA-256 pinned |
| **Vilkov derived panels** | **free** | ~3.5M interpolated SPXW 0DTE obs, ~400MB LFS |
| **OptionsDX** | **free** | EOD chains 2010+, real bid/ask |
| **ThetaData Standard** | **$80/mo** | **every NBBO quote from OPRA, tick level, 8 yrs** |
| Massive Advanced | $199/mo | NBBO + trades + flat files |
| ORATS | $99–399/mo | ⚠️ quotes sampled **14 min before close** and "smoothed" — structurally optimistic for execution research |

**Recommendation: validate free on lambdaclass + Vilkov panels. Only if D1/D3
replicate, buy ThetaData Standard. Do not pay ORATS for execution research.**

## Caveats the agent flagged

WebSearch budget was exhausted before it started; everything came from the GitHub
API and direct WebFetch. So "has anyone replicated this?" is inferred from fork
activity only — weaker than desired. Fill code was read directly from source for
optopsy, lambdaclass, lumibot, randomwalkhan and oyzh888; those verdicts are
grounded in code, not READMEs.
