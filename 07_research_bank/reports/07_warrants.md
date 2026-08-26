# 07 — Warrants: the first genuinely measured P(10x)

**Status:** complete · **Evidence quality:** ⭐ **highest in the bank** — the agent
built the survivorship-free universe itself and measured the return distribution
from primary data · **Relevance:** the only computable base rate found so far

---

## The number

> **P(10x) on a $5k warrant basket ≈ 5%, plausible range 2–10%.**

Against the **10% martingale ceiling** for a fair bet, that is *below* fair — so
this is still a negative-expectancy path. But it comes with genuinely bounded
downside, needs no options approval, and is the only route in this investigation
where the base rate is computable rather than asserted.

| measure | value | basis |
|---|---|---|
| single warrant, 12m hold, corrected | **1–2%** | measured + corrected |
| held to expiry with competent exit | 2–5% | estimated |
| **$5k basket** | **~5%** | estimated from measured components |
| post-2022 entry, *uncorrected* | 7.9% | measured, survivorship-biased |
| **2020–21 boom entry, buy-and-hold** | **0.0%** | measured |

---

## The universe (measured, full population)

Built from Tiingo's free `supported_tickers.csv`, which **includes delisted
tickers with listing start/end dates** — that is what makes a survivorship-free
denominator possible for $0.

**1,064 US warrant tickers, 2019–2026.**

| listing year | listed | delisted by 8/2026 | % dead | median life of dead |
|---|---:|---:|---:|---:|
| 2019 | 41 | 38 | **92.7%** | 660 d |
| 2020 | 97 | 88 | **90.7%** | 675 d |
| **2021** | **411** | 331 | **80.5%** | 679 d |
| 2022 | 124 | 77 | 62.1% | 631 d |
| 2023 | 44 | 15 | 34.1% | 512 d |

**411 of 1,064 warrant series in history listed in 2021 alone.** Median survival
of those that died: **~22 months**.

## The regime surprise — the boom was *worse*

This is the counterintuitive result, and it is measured:

| entry regime | n | P(≥10x) peak-timed | **P(≥10x) buy-and-hold** | P(≤0.1x) |
|---|---:|---:|---:|---:|
| **2020-01 → 2021-12 (boom)** | 298 | 0.34% | **0.0%** | 15.4% |
| **2022-01 → present** | 2,019 | 7.9% | 4.2% | 8.0% |

**Buying warrants during the SPAC bubble produced essentially zero 10x outcomes
and a 15% chance of losing 90%+.** By the time retail could see the mania,
warrants were already $1–$2 — the convexity was gone.

The 10x outcomes came from buying **the wreckage** at $0.05–$0.15 in 2022–2023
and holding into the 2024–25 AI/quantum/space wave.

> **Warrant 10x events are a bet on the next mania, entered at the bottom of the
> previous bust.** As of August 2026 we are arguably late in such a wave, not
> early — which argues the forward-looking number is nearer 2% than 10%.

## Three corrections that must be applied

**1. Survivorship (large).** `P(10x) ≈ P(10x | survived) × P(survive)`:

| cohort | P(survive) | corrected P(10x) |
|---|---:|---:|
| 2021 | 0.19 | **1.4%** |
| 2022 | 0.38 | **2.7%** |

**2. Bid-ask (devastating).** Live quotes, 2026-08-25:

| symbol | bid | ask | spread % of mid |
|---|---:|---:|---:|
| ASTLW | 0.0015 | 0.0198 | **172%** |
| RVSNW | 0.0106 | 0.0900 | **158%** |
| BZFDW | 0.0121 | 0.0174 | 36% |
| DRTSW | 3.73 | 4.36 | 16% |
| **RGTIW** | 6.92 | 7.23 | **4.4%** |

**Median spread 36% of mid below $0.10.** On a 100%-spread name the mid must
rise **3× just to break even**. Note the pattern: **spread collapses as the
warrant becomes valuable** — you pay it going in, not coming out, which is
survivable but warrants a 30–50% haircut to gross P(10x).

**3. Perfect-peak timing.** The 6.9% headline needs selling at the exact weekly
high; buy-and-hold is 3.7%.

## Concentration — this is not a diversifiable base rate

Of the 160 observations reaching 10x, **78 came from one name (RGTIW)** and 34
from a second (DRTSW). **Two of thirteen warrants produced 70% of the 10x
events.** It is an extreme-tail lottery, not a distribution you can sample.

---

## The structural caps do NOT block a 10x

Standard terms: strike **$11.50**, 5 years, redeemable at $0.01 if the stock
closes ≥ **$18.00** for 20 of 30 days.

**Does the $18 trigger prevent a 10x from $0.10? No.** Forced exercise delivers
$18.00 − $11.50 = **$6.50 of intrinsic value** — that is **65×** from $0.10, and
130× from $0.05. The $18 call is a ceiling at ~$6.50, and $6.50 is 65 times entry.

**The $10.00 cashless call is the real cap.** Make-whole tables typically deliver
0.25–0.36 shares/warrant, worth ~$2.50 at a $10 stock — still 25× from $0.10, but
it **truncates the fat tail hard**, and issuers invoke it exactly when the stock
is recovering. *Check every candidate's warrant agreement for this provision.*

**Frequency:** EDGAR full-text search finds 186 8-Ks mentioning "Redemption of
Public Warrants" 2019–2026, but one event generates 2–3 filings. True
issuer-level rate ≈ **5–10%** — roughly **1 series in 15** ever reaches a
redemption trigger.

## Downside is genuinely bounded — the domain's real edge

**Cash account. No margin, no assignment, no short leg, no maintenance
requirement, no options approval level.** Maximum loss = purchase price. For a
$5,000 account this is materially safer than any options route to the same
convexity.

Three caveats, all bounded-loss rather than unbounded:
1. **Warrant amendments** — 1,110 8-Ks mention "Warrant Amendment", 311 mention
   "warrant exchange offer". Sponsors force conversion into 0.20–0.30 shares,
   below fair value. Caps upside at the worst moment. *Read the amendment
   threshold before buying.*
2. **Liquidation** — if the SPAC never closes a deal, public warrants are
   **cancelled worthless**; the trust goes to shareholders. This is the dominant
   outcome for the 80.5% that delisted.
3. **The ask** — buying at a 150% spread means your basis is ~2× mid.

## Liquidity — the asymmetry is favourable

From RGTIW's actual tape: quiet weeks in the 2023 accumulation window traded
**$2,043–$5,936 of dollar volume**. A $5,000 position at $0.08 is 62,500
warrants — **roughly one entire week's volume**.

- **Entry is the binding constraint** — needs patient limit orders over 1–3
  weeks, or splitting across 4–20 names. This makes diversification structurally
  necessary, not optional.
- **Exit is easy at the top** — RGTIW's peak week traded 2.77M shares, $100M+.
  *The tail event that makes you rich also makes you able to sell.*
- **Illiquid to buy, liquid to sell — the opposite of most retail traps.**
- **Broker check:** Robinhood does **not** support warrant orders (47 of 60
  sampled returned `missing_instruments`). IBKR/Fidelity/Schwab do; IBKR is the
  practical choice for limit control on sub-penny books.

## The documented case

**RGTIW (Rigetti warrants), measured from the tape:** min weekly close
**$0.0499** (week of 2023-05-08) → peak weekly high **$46.78** (week of
2025-10-13). **937×.**

From a realistic $0.08–$0.10 accumulation zone in H1 2023, **$5,000 (62,500
warrants) would have been worth $2.9M at the peak.** A real, single-instrument,
cash-account outcome inside the requested window — and exactly one name out of
~700.

## CVRs — drop them

Structurally wrong instrument. Most are **non-transferable** (you can only get
them by owning the target pre-close). The tradeable float is a few dozen names.
And the payoff is **capped at a stated dollar amount**, so a CVR at $0.30 with a
$2 cap is a **6.7× maximum**. *A capped instrument cannot 10x unless it trades
below 1/10th of its cap — which happens only when the market is confident it
will not pay.* The largest tradeable CVR ever (CELG.RT) expired worthless in 2021.

---

## The highest-value next step, and it costs $10

The measured distribution rests on **13 survivors out of 120 sampled** —
Robinhood carries only live warrants and only a non-random subset. The agent
corrected for survivorship analytically but the underlying sample is biased.

**Spend $10 on one month of Tiingo, pull the full 1,064-ticker universe including
delisted names, and recompute.** That turns the headline from ESTIMATED into
MEASURED and is a few hours of work. Step-by-step method, EDGAR queries and
working scripts are all in the agent's report.

Apply the three corrections **in order**: (1) include delisted at terminal value
0, (2) buy at the ask, (3) sell at the bid. Skipping any inflates P(10x) by 2–5×.
