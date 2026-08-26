# 15 — Forced sellers and reflexive convexity: falsified, and backwards

**Status:** complete · **Evidence quality:** high — N-PORT XML pulled directly,
live quotes measured · **Relevance:** kills the branch, and **corrects report
14's crypto input**

---

## The hypothesis inverted on its central mechanism

The thesis: YieldMax-style funds are naked sellers of upside calls, manufacturing
cheap convexity we could buy.

**They sell CALL SPREADS.** Written and purchased contracts are **identical at
every fund** — net zero:

| fund | expiry | written | purchased | **net** |
|---|---|---:|---:|---:|
| MSTY | 05/01/26 | 59,665 | 59,665 | **0** |
| NVDY | 05/01/26 | 68,150 | 68,150 | **0** |
| TSLY | 05/01/26 | 21,819 | 21,819 | **0** |

MSTY's actual April structure — short the near strike, **long the far one**:

```
WRITTEN:   162.5(-3,500)  175(-12,500)  177.5(-31,165)
PURCHASED: 172.5(+6,000)  182.5(+12,500)  185(+31,165)
```

> They **buy** the 10–15 delta wing — precisely the convexity this project
> needs. A price-insensitive buyer sitting on it makes it **richer, not
> cheaper.** There was never cheap convexity to inherit.

**The flow is genuinely large** — MSTY wrote 4.4× the entire MSTR weekly OI into
one expiry. It is simply pointed the other way.

## The measured IV effect is one fifth of the spread

| tenor | OTM leg | skew vs ATM |
|---|---|---|
| **09/04 (YieldMax expiry)** | K130 δ.317 | **+2.80** |
| 01/15/27 control | K180 δ.301 | +2.95 |

**0.15–0.25 vol points flatter.** Sign is right; magnitude is nil.

Economic size: vega 0.0574 × 0.25 = **$0.014** on a $1.775 option. The bid-ask on
that option is **$0.07**. **The spread is 5× the entire alleged edge.**

And the raw smile is smooth, monotone and convex across all strikes — **no kink
anywhere.** A $900M fund transacting 4× the weekly's OI leaves no visible print.
Dealers have fully pre-positioned.

## The MSTR test fails decisively — and the sign is inverted

| | |
|---|---|
| BTC DVOL | 40.3 |
| MSTR beta to IBIT | 1.41 (1yr), 1.59 (60d) |
| **coin IV × beta** | **64.1%** |
| **observed MSTR 20–30Δ call IV** | **78–80%** |

MSTR trades **14–16 vol points ABOVE** coin IV × beta. The gap the thesis needed
is not absent — it is **inverted**.

**Tail beta does not expand:** 1.23 (bottom 5%) to 1.43 (top 5%) against a 1.41
baseline. **Flat.** The third of the "three layers of convexity" does not exist.

## ⚠️ The killer — and it corrects report 14

Over 2025-08-01 → 2026-08-25:

| | |
|---|---|
| IBIT | **−30.4%** |
| beta-implied MSTR | −40.0% |
| **MSTR actual** | **−65.4%** |
| **residual alpha** | **−42.3% in 12 months** |

That is mNAV de-rating — a persistent negative drift stacked on beta that no vol
model prices. **The reflexive premium is a SHORT convexity term for a call buyer,
not a long one.**

> **This contradicts report 14's key input.** Report 14 ranked crypto-linked names
> highest at **4.85%** P(10×) *because it assumed a 30%/yr drift*, citing the
> Almeida 66%/yr Bitcoin premium. The realised crypto complex delivered **−30% to
> −65%** over the past year. **That input must be re-examined, and report 14's
> crypto ranking should be treated as unsupported until it is.**

## Scoring the four claims

| claim | result |
|---|---|
| forced flow is large vs listed OI | **TRUE** — 4.4× a weekly's OI |
| flow is short the upside we want | **FALSE** — it *buys* the wing |
| upside call IV is depressed | **FALSE** — 0.2 vol pts, ⅕ of the spread |
| MSTR IV < coin IV × beta | **FALSE** — 14–16 pts *above* |
| beta expands in the tails | **FALSE** — 1.23–1.43 vs 1.41 |

## Two independent confirmations of our own priors

The agent's risk-neutral P(10×) on real MSTR asks peaks at **15–30 delta** and
collapses at 2.8 delta — reproducing both established results from a completely
different method.

## Verdict: kill the branch

The headline 3.4% does **not** beat 1.39%, because it is not the same kind of
number — those are risk-neutral probabilities computed from each option's *own*
IV, which is circular. Ours was **measured**. And MSTR carries −42% measured
annual alpha to its own beta, so deflating puts it at or below 1.39%.

**The one asset worth keeping:** YieldMax publishes exact strikes and contract
counts **daily and free** at `yieldmaxetfs.com/our-etfs/msty/` — a live feed of a
$900M mechanical participant's book. EDGAR's 60-day lag was never needed.

## Unverified

Innovator/AllianzIM buffer ETFs not pulled (FLEX claim is reasoning, not
measurement) · Korean ELS and uridashi not reached · autocallable barrier data is
parseable (9,636 424B2 filings/quarter) but has **zero coverage of reflexive-equity
names**, so it is weeks of engineering with no tradeable cluster in our universe.
