# 08 — Prop firms: the first route that beats the 10% ceiling, and why that may not matter

**Status:** complete · **Evidence quality:** Topstep verified from primary source;
Apex/MFFU/Tradeify via PropFirmMatch (good secondary); **the decisive red flag is
unverified** · **Relevance:** the only route found that mathematically clears the
martingale ceiling

---

## The mathematical core — trailing vs static drawdown is *exponential*

This reframes the whole domain, and it is not the consistency rules:

| drawdown type | P(reach target) | decay |
|---|---|---|
| **static floor** at distance D, target M | **D / (D + M)** | linear |
| **trailing** drawdown D from running peak | **e^(−M/D)** | **exponential** |

At M/D = 12 (roughly $50k on a $150k account):

> static → **7.7%** · pure trailing → **6 × 10⁻⁶**
>
> **Four orders of magnitude.**

**Any firm whose drawdown trails all the way up is mathematically dead for this
purpose.** That is the whole game.

## Firm by firm

| firm | drawdown | daily loss limit | consistency | split | high variance? |
|---|---|---|---|---|---|
| **Apex** | trailing, **stops at start+$100** | **NONE (intraday)** | 50% at payout | **100%** | **YES** |
| MyFundedFutures | **STATIC** (floor never moves) | yes | none on funded Pro | 80/20 | yes on math, no on payout |
| Topstep | trailing, locks at start | optional | 50% / 40% | 90/10 | **NO** |
| Tradeify | trailing, EOD | yes | **20% → 30%** | 90/10 | **NO** |

**Topstep explicitly names our strategy as prohibited conduct**, verbatim:

> *"**Account Stacking** — Repeatedly trading aggressively, hitting the Maximum
> Loss Limit (MLL) in one account, then switching to another account and
> repeating."*

Also banned there: trading full size into scheduled news, and *"using software,
AI, ultra-high speed systems… that provides an unfair advantage"* — relevant to
an autonomous agent.

**The rules do not forbid high variance *inside* the account.** Apex will let you
put the entire threshold on one trade with no daily limit. What every firm
forbids is **high variance in the payout** — payout caps, winning-day counts and
cadence are the anti-convexity mechanism, not the consistency rules.

---

## The structural finding: 20 correlated accounts

Apex permits **up to 20 accounts with copy-trading across your own accounts.**

| structure | gross needed | % of account | **reward : risk** |
|---|---|---|---|
| Topstep $150k | $54,444 | 36.3% | 12.1 : 1 |
| Apex $150k single | $50,000 | 33.3% | 10.0 : 1 |
| **Apex 20 × $50k, copy-traded** | **$2,500 each** | **5.0% each** | **1.0 : 1** |

> Running twenty parallel accounts collapses the required reward:risk from
> **10:1 to 1:1**. You don't need one account to make an improbable run — you
> need twenty accounts to each make a coin-flip run.

Correlation is normally the enemy. Here it is **correct**, precisely because the
per-account payout is capped and the target is large.

## The threshold — the bar is astonishingly low

`p* = 1 − 0.9^(1/N)` is the per-attempt probability needed to beat 10%:

| N attempts | 3 | **10** | 20 | 28 |
|---|---|---|---|---|
| **p\* required** | 3.45% | **1.05%** | 0.53% | 0.38% |

**Estimated p ≈ 18% per Apex 20-account cycle** (driftless model: 35% through the
trailing phase × 86% on the locked floor × 60% surviving the winning-day
requirement). $5,000 buys ~2–3 cycles.

| assumption | P(success) |
|---|---|
| p = 18% × 3 cycles | **45%** |
| p = 10% × 3 cycles | 27% |
| **p = 5% (heavily pessimistic) × 3** | **14.3%** |

**It beats 10% at every pessimism level tested.**

### Why the ceiling doesn't apply

> **A $980 evaluation fee is a call-option premium on someone else's $50,000 of
> drawdown allowance** — roughly 50:1 free leverage with the downside
> contractually truncated at the fee.

The 10% martingale ceiling binds only when the payoff is funded by **your own
stake**. Here it isn't. That is the clean conceptual reason this route escapes a
bound nothing else has.

### Reality check

No futures firm publishes an audited pass rate. Industry consensus: **5–10%
evaluation pass rate, 2–5% ever receive a payout.** The driftless models give
18–30%. The gap is commissions (~$4.20 round-turn on ES; 500 RTs at 10 lots =
**$21,000 of drag**), overtrading, and not stopping the instant target is hit.
**Honest band: p = 10–25%.**

---

## ⚠️ The catch is the counterparty, not the market

**The payout is discretionary.** Verbatim from Apex's own risk disclosure:

> *"Apex offers simulated trading programs for educational, informational, and
> evaluation purposes only… **Reward payouts are discretionary** and subject to
> eligibility, compliance, and applicable tax laws."*

You are not a trader with a claim on profits. You are a customer of a simulation
who may, at the firm's option, be given a "reward."

- **Everything is simulated.** No real capital, no CFTC segregation, no SIPC, no
  FCM, no clearing member. Your $50,000 is an **unsecured payable from a private
  LLC**.
- **Effectively unregulated.** These firms are structured to avoid CFTC/NFA
  registration by asserting they offer only simulated trading.
- **Rules change unilaterally and retroactively.** Nothing prevents a firm adding
  a consistency rule or lowering a payout cap *after* you've earned the $50,000
  and *before* they pay it.

### The highest-value unverified item

The agent recalls — **and explicitly could not verify this session** — that in
2024 Apex mass-denied payouts and banned thousands of accounts, citing
**one-directional trading, trade copiers, and no-stop-loss usage**.

> **Every one of those is a feature of the 20-account correlated strategy.**

If accurate, that is a documented precedent of the firm voiding payouts for doing
exactly what makes the math work. **Verify this before any money moves — it is
the difference between a 30% plan and a 0% one.**

---

## The options angle is dead

- **No futures prop firm permits options.** Apex, Topstep, MFFU and Tradeify all
  route through Rithmic / Tradovate / ProjectX — **futures-only order routing**.
  There is no mechanism to submit an option spread.
- **No credible retail options prop firm exists** in the fee-for-attempt mould;
  those advertising are largely CFD-wrapper forex shops.
- **Traditional Series 57 prop** (T3, Bright, SMB) has genuine options
  permissions — but requires a licensing exam and **$5,000–$25,000 of capital
  that is at risk**. That destroys the bounded-cost property and returns you to
  the 10% ceiling.

**If prop capital is used, it must be futures.** Which conflicts with the stated
"it has to be options" constraint — a decision for the user, not a research
finding.

---

## Verdict

**The only route found that mathematically beats the 10% ceiling**, in one
specific configuration: Apex intraday accounts, twenty in parallel, copy-traded
to perfect correlation, each targeting one ~$2,500 capped payout. P ≈ **14–45%**
over the 2–3 cycles $5,000 buys.

**But you would be converting a 10% market gamble into a ~30% market gamble
multiplied by an unquantifiable, uninsurable probability that an unregulated
private company chooses to pay you.** The market risk is solved. The counterparty
risk is not, and it is not the kind of risk that can be modelled.

## Gaps

TakeProfit / Bulenox / Earn2Trade rule sets · any audited pass-rate statistic ·
**verification of the Apex 2024 denial episode** (highest value) · a systematic
sweep for options-enabled firms · the CFTC v. My Forex Funds outcome.
