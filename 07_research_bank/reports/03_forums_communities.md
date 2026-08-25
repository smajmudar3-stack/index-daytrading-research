# 03 — Forums, communities, and what actually happens to people

**Status:** complete · **Evidence quality:** primary — Reddit archive API used to
recover deleted/scrubbed histories · **Relevance:** answers "how do these people
get rich" directly

---

## The number that closes the premium-selling question

tastytrade's own flagship study, *Strangle Return on Capital: 16Δ vs 30Δ*
(2005–2017):

> **0.07–0.08% return on capital per day — and the same regardless of delta.**

≈25%/yr on capital actually at risk. But tastytrade itself caps buying-power use
at 55–60%, so at a realistic ~35% allocation that is **~9%/yr on the account,
pre-tax** — which **underperformed SPY over the identical window** ($287,220 vs
$306,580), and that window excludes Feb 2018, March 2020 and 2022.

**Against the goal:** 30%/month needs ~0.87%/day on deployed capital. tastytrade
measures **0.07%**. A **12× gap**, closable only by leverage — which is precisely
what kills the accounts in the failure-mode section.

## 86% win rate, negative expectancy — on the vendor's own tool

A community member ran tastytrade's canonical spec (45 DTE, 16Δ strangle, close
at 50% or 21 DTE) through tastytrade's **own LookBack tool**: SPY, 2006–2021,
336 trades.

| | |
|---|---|
| win rate | **86%** |
| avg premium collected | $218.55 |
| **avg P/L per trade** | **−$2.61** |
| max drawdown | −$4,180 |

Adding a 200%-of-credit stop dropped the win rate to 82% and turned it *positive*
(+$3.73/trade) while cutting drawdown 73%.

## There is no optimal delta — the choice is noise

Independent backtest, 14 years of real SPY chains, 2010–2023, 167 monthly cycles:

| delta | win rate | 14y total P/L | worst month | winners erased |
|---|---|---|---|---|
| 5Δ | **95.8%** | $1,567 | −$6,632 | **110** |
| 16Δ | 78.4% | $2,155 | −$8,343 | 42 |
| 30Δ | 67.1% | $2,276 | −$9,045 | 26 |
| 40Δ | 61.4% | $2,164 | −$9,309 | 22 |

Win rate falls from 95.8% to 61.4% while **total profit barely moves** — the win
rate buys nothing. The entire best-to-worst spread ($1,304) is **9.7× smaller
than the standard error on any single column** (~$12,608); every pairwise t-stat
is under 0.6.

**Anyone selling you an optimal delta is reading noise.** And the small positive
depends on one year: remove 2022 and 16Δ falls from $2,155 to **$407**, while 5Δ
goes negative.

## The Wheel is long equity wearing a costume

spintwig, ORATS data, 2007–2024, 2,200+ SPY trades, 10 configurations:

> "Not a single strategy outperformed buy/hold on total return. **Four of the 10
> went negative.**" And: "the long underlying was accountable for about
> **94–99% of a strategy's total return**."

The options contributed 1–6%.

The most-upvoted wheel result ever posted — *"$390k in premiums collected"* on a
$750k account — has this as its own TLDR: **"The wheel cost me $575,947 in missed
profits."**

## The best honest long-run record found anywhere

*13 Years of Theta* — a CEO running portfolio-margin short strangles on
SPX/RUT/NDX since 2011, with a full year-by-year table:

| | his return | S&P 500 TR |
|---|---|---|
| 2022 | +60.04% | −18.11% |
| **2021** | **−24.05%** | +32.06% |
| 2020 | −3.45% | +15.39% |
| **13y compounded** | **365.6%** | **349.0%** |

His own summary: *"average return has been **15%, with a standard deviation of
26%**."* Thirteen years, portfolio margin, full-time attention → **a dead heat
with buy-and-hold at double the volatility.** He also discloses ~$75k lost purely
to auto-liquidations and operational errors.

---

## The failure mode — one sequence, repeated verbatim

1. **The strategy works.** 51 of 52 weeks. 86–96% win rates.
2. **The win streak is misread as skill, so leverage rises.** Nobody sizes up
   after losses; everybody sizes up after wins.
3. **A gap kills it, not a grind.** The 14-year data is explicit: the strangle
   *survived* 2022 (SPY −19%, strangle **+$1,748**) and *died* in March 2020
   (**−$7,101 in one cycle**). Slow bear markets are survivable. Fast gaps are not.
4. **Liquidity vanishes exactly when you need it** — you cannot exit at model
   prices.
5. **The loss is 20–110× a typical winner.** One March 2020 cycle erased 42
   average winning months at 16Δ; **110 at 5Δ.**

**Canonical case — 5 Aug 2024 yen-carry unwind.** A trader running −300 1-1-1 put
ladders on $300k NLV at −19k vega. VIX over 60, *"market makers went on strike,"*
buying power negative, 16 hours manually unwinding, had to phone IBKR and beg the
desk to work his last 50 contracts by hand. Final: **−103.5% YTD and a $5k margin
call** — he ended the day *owing money*.

Institutional version, identical: **OptionSellers.com**, ~$150M across 290
accounts, naked nat-gas options, gone in four days — clients ended up **owing the
clearing broker millions beyond their deposits**.

**Why this is not fixable by being careful:** the payoff is a capped, tiny,
high-frequency gain against an uncapped, enormous, low-frequency loss. Any
leverage sufficient to turn 0.07%/day into 30%/month guarantees the tail event is
terminal rather than survivable.

---

## Survivorship, documented rather than asserted

This is the strongest material in the report, because the communities documented
it on themselves.

**1. The deletion.** A doctor posting repeatedly about far-OTM naked puts with
**~$10M notional against a $1.5M portfolio-margin account**, who mocked anyone
mentioning greeks. Someone went looking for him in Nov 2024: account deleted, and
comment history **mass-overwritten with nonsense using a tool called Redact**
before deletion. *"This is as close as we're ever going to get to a confirmation
that things did not in fact go his way."*

**2. The silence.** *"3 years of running the wheel"* (Nov 2024, 577 upvotes):
$150k → $1.1M, *"outperforming the market around 3x consistently, 3–5% a month."*
His full posting history shows he **never posted about trading again** — while
staying active through August 2025 posting about Siberian cats, Hearts of Iron IV
and Cartier watches, straight through the April 2025 crash. The account lives.
The results stopped.

**3. The series that just ends.** *"The Journey to 100% Annual Returns"*, a weekly
SPX range-selling P/L series. 2024 close: **"96.46% RETURN, the ranges WON 51 of
52 weeks, average 99.61% per year over 4 years."** He posts Weeks 3, 4, 5 of
2025, then *"2025 Edition is now 8-0"* on 21 Feb 2025 — and **the weekly P/L
series stops permanently**, days before the April 2025 tariff crash. No Week 9.
No 2025 recap. No 2026 recap. He resumed posting charts in Aug 2025. He had also
migrated the series into **his own moderated subreddit** where the posts read
*"join us before you miss out."* **He sells access.** The verifiable P/L vanishes
at the first volatility event; the marketing continues.

> **The shape of the whole dataset: wins are posted as snapshots, losses are
> posted as post-mortems only by people who have already quit, and the middle —
> the guy who was up 40% and gave it back — is simply missing.**

## The one genuine high-return record, and what it actually is

The only trader found with a large continuous record and outsized returns:
**47% in 2025, $6.8M on ~$14.5M**. But his history also shows 27,500 RDDT shares,
a **$1.9M MNDY position down $737k**, and in his own words gains from *"being
heavy long on RDDT and GOOG with shares and calls."*

That is **concentrated leveraged long exposure to AI names in a bull market**,
partly expressed through short puts. Not a premium-selling edge, not repeatable
by rule — and 47%/yr is still **1/47th of 30%/month**.

---

## Verdict

**Nobody in these communities has documented 30%/month sustained with
verification.** Those claiming annualised rates near it are **selling Discord
access**, and their P/L series terminate at the first volatility event. Honest
long-run numbers cluster at **9–15%/yr with equity-like or worse drawdowns**.

## Caveat

WebSearch budget was exhausted before the agent started, and Reddit blocks direct
fetching — it worked via the Arctic Shift Reddit archive API (which is how the
deleted-author histories were recovered). Search engines began serving captchas
partway through, so coverage of Elite Trader, SpotGamma and academic WSB
literature is thin. That is the gap if a follow-up pass is wanted.
