# 09 — Capacity-constrained edges: the thesis is half right, and the wrong half is fatal

**Status:** complete · **Evidence quality:** high — primary literature, worked
arithmetic · **Relevance:** **kills** the direction report 01 identified as most
promising

---

## The finding

> There is a capacity **ceiling** that keeps institutions out of small niches —
> that part is real and documented. But every genuine small-capacity options edge
> also has a capacity **FLOOR**, set by three things that do not scale down: the
> **$0.65/contract commission**, the **100-share multiplier**, and the **bid-ask
> on multi-leg combos**.
>
> The exploitable window is roughly **$100k to a few million**.
> **$5,000 is below the floor, not inside the window.**

In several cases the edge is **arithmetically negative at $5k and positive at
$500k** — the opposite of what report 01 predicted.

### The structural reason, stated plainly

> An edge survives at small size because it is too small in **dollars** for
> anyone big to bother with. **"Too small in dollars" and "large in percent" are
> nearly incompatible.**

Medallion's 4.3%/month is not what a $5k Medallion would earn. A small account
earns the same *percentage* only if the edge scales down — and fixed per-contract
costs mean it does not. Shleifer & Vishny explain why the mispricing persists;
they do not imply retail can harvest it, because their arbitrageurs are
constrained by **withdrawals**, not by commissions.

---

## The table that settles it: hard-to-borrow conversions

Ofek, Richardson & Whitelaw (JF 2004) measure the borrow specialness embedded in
put-call parity: conditional on being "special," annualized rebate spread is
**mean −1.57%, median −0.46%**. Crucially, redone **at bid/ask instead of
midpoints, violations are "significantly reduced in number"** — the paper telling
you the mispricing is mostly inside the spread.

A conversion on 100 shares of a $50 stock consumes **$5,000 — the entire account,
one position.** Round-trip commissions ≈ $7.

| borrow rate | gross/month | **net of $7** | net %/mo | months to 10x |
|---|---:|---:|---:|---:|
| 0.46% (OWR median) | $1.92 | **−$5.08** | −0.10% | **never** |
| 1.57% (OWR mean) | $6.54 | **−$0.46** | −0.01% | **never** |
| 20% (genuinely HTB) | $83.33 | $76.33 | 1.53% | 152 |
| 100% (GME-class) | $416.67 | $409.67 | 8.19% | 29 |

**At the rates the literature documents, the trade loses money at $5k after
commissions.** The same trade at $500,000 nets 1.4%/yr and is worth doing. That
is the capacity floor in one table.

Even the 100%-borrow case needs **29 consecutive months** of GME-class squeezes —
and there is roughly **one such episode per year, market-wide, lasting weeks**.

---

## The rest, briefly

**Box spreads — no edge, disqualifying tail.** van Binsbergen, Diamond &
Grotteria (JFE 2022): box-implied rates have a standard error of **1–3 basis
points**, and bid-ask spreads **do not predict deviations**. There is no
arbitrage. Bharadwaj & Wiggins: *"arbitrage profit insufficient to cover
transaction costs."* The alternate name is "alligator spread" because the four
legs eat the profit.

And the tail is *this exact stake*: the 2019 WSB box-spread case — **$5,000 of
principal, −$57,000 realized, $212,500 peak exposure.** A documented instance of
a $5k options account owing $52k more than it had. **Disqualified.**

**Dividend play — capacity-constrained in the wrong direction.** Pool, Stoll &
Whaley: >50% of options that should be exercised are not, worth $491M over ten
years — but *"market makers capture the lion's share."* The winner is whoever has
the lowest per-contract fee, which is an MM with fee caps, not a customer paying
$0.65 × 2 legs. Needs thousands of contracts.

**Pin risk — 16.5 bp.** Ni, Pearson & Poteshman. That needs **1,152 sequential
occurrences** at ~12 expirations/year = **96 years**. And trading it converts a
bounded position into unhedged weekend stock exposure.

**Retail price improvement — a discount on a tax, not an edge.** Bryzgalova,
Pavlova & Sikorskaya (JF 2023): quoted spread **12.6%**, effective spread on
retail trades **6.6%** — so price improvement recovers about half. But 6.6%
effective is a **3.3% half-spread per side**, "orders of magnitude higher than in
equities." Retail lost **$2.1bn** net; delta-hedged **$2.2bn**; fully hedged
**$4.5bn** — so it is cost, not directional luck. **Indirect costs $6.4bn vs
$887M of commissions: the hidden cost is ~7× the visible one.** Exchange rebates
of $0.02–$0.17/contract go to the **broker/wholesaler, not you**.

### What that cost does to compounding

You need a **gross** edge above 6.6% per round trip just to break even:

| gross edge/trade | net | trades to 10x |
|---|---:|---:|
| 5% | −1.6% | **never** |
| 10% | 3.4% | 69 |
| 20% | 13.4% | 18 |

A repeatable 15–20% gross edge per options round-trip is not an anomaly; it is a
fantasy.

---

## Two hard gates a $5,000 account cannot pass

- **Portfolio margin requires $100,000+** (FINRA 4210; brokers enforce
  $110k–$125k). Every strategy above is priced under **Reg T**, the expensive
  regime.
- **PDT requires $25,000.** Note FINRA's new intraday margin rules took effect
  **4 June 2026** with a firm transition period to **20 Oct 2027**, so brokers
  may be on either standard — confirm with yours.

## Disqualifying tails — all violate the bounded-loss constraint

1. **Short box on American-style options** — the 1R0NYMAN case.
2. **Any short box** if the broker liquidates on a margin excursion; the payoff
   is only certain *at expiry*.
3. **Conversion with early assignment on the short call** — overwhelmingly likely
   on HTB and pre-dividend names, which is exactly when Jensen & Pedersen show
   rational early exercise happens.
4. **Pin risk** — ITM by $0.01 triggers exercise-by-exception.
5. **Dividend-play assignment** — you choose which longs to exercise; you do not
   choose which shorts get assigned.
6. **Naked puts on HTB names** to harvest specialness — short exactly the assets
   most likely to crash.

> The generalisation: every one of these is "riskless" only while all legs stay
> intact, and **American-style early exercise is precisely the event that breaks
> legs**. Small-capacity options edges are systematically edges with left tails
> larger than the stake.

## Could any compound to 10x? No.

Every evidenced capacity edge sits in the **0.1%–2% per-occurrence** band, which
needs **116–1,152 sequential wins**. And the capacity floor means a $5k account
holds **one position at a time**, so occurrences are **serial, not parallel** —
you cannot substitute breadth for magnitude.

Reinforcing decay: McLean & Pontiff — published predictors return **26% less
out-of-sample, 58% less post-publication**. Novy-Marx & Velikov — trading costs
of **20–57 bp/month**, "often exceeding half the strategies' gross spreads."
Both cut *against* small accounts, which pay the highest per-dollar costs.

---

## The agent's recommendation

> **Deprioritise this entire branch.** The capacity hypothesis was the right
> question to ask and the answer is a clean negative. If the goal is genuinely
> P(10x) on a stake you can afford to lose, the honest structure is a small
> number of **high-convexity, bounded-loss bets — long options where the loss is
> capped at premium** — accepting that expected value is negative and P(10x) is
> low but nonzero. **That is a different research direction, and it should not be
> dressed up as an edge.**

## Two gaps, flagged as unevidenced rather than ruled out

- **OCC contract adjustments** after mergers/special dividends/spinoffs — OCC's
  info-memo servers return **403 to programmatic access**, and no published
  literature establishes the edge. Mechanism is sound in principle; unverified.
- **Options on newly listed / IPO names** — no literature found at all.
