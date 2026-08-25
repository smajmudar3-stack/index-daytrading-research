# Does the wing cost less than the tail it removes?

The question that decides whether premium selling is salvageable. The variance
premium is large and persistent — implied 19.2% against realized 13.6%, with
realized landing below implied on 88.5% of days — yet every credit structure
tested still lost money. If the tail is what eats the premium, a wing costing
less than the tail it removes would fix the strategy.

**Answer: the wing costs more than it pays. But that is not the end of it,
because the naked version is a ruin machine.**

---

## Design

Hold the short body **fixed** and vary only the wings, so the difference between
the two P&L distributions is the wing's entire economic effect with no
confounding from strike selection.

| leg | contract | fill |
|---|---|---|
| body | short 16-delta put + short 16-delta call | sold at **bid** |
| wings | long 5-delta put + long 5-delta call | bought at **ask** |

SPY, 25–40 DTE, **1,240 non-overlapping trades**, 2010–2025, held to expiry and
settled against the actual underlying close. Worthless legs expire worthless and
are counted — the survivorship filter that once produced 100% win rates here is
absent by construction.

---

## Result

| | naked strangle | iron condor | difference |
|---|---:|---:|---:|
| mean P&L | **+0.63** | +0.23 | −0.39 |
| median | +1.85 | +1.19 | −0.66 |
| std dev | 7.67 | 4.40 | −3.27 |
| **worst** | **−94.78** | **−43.38** | **+51.40** |
| 1st percentile | −27.29 | −19.66 | +7.62 |
| win rate | 78.9% | 75.0% | −3.9pp |
| Sharpe/trade | 0.082 | 0.053 | −0.029 |
| t vs zero | 2.88 | 1.87 | |

### The wing ledger

| | |
|---|---:|
| average wing premium paid | $0.973 |
| average wing payout received | $0.580 |
| **net cost of carrying wings** | **+$0.393** |
| wings paid out on | 6.2% of trades |
| average credit collected | $3.097 |
| wings as share of credit | **31.4%** |

A 5-delta wing paying out 6.2% of the time is exactly right, which is the
sanity check that the earlier version of this test failed.

**The wing costs $0.393 more than it returns.** That is consistent with the
far-OTM result elsewhere in this repo — buying cheap out-of-the-money options
returns −48% to −90%, and a protective wing is precisely that purchase. The tail
is not mispriced in the buyer's favour.

---

## But look at what the naked version actually is

Per contract (×100):

| | |
|---|---:|
| mean | +$63 |
| std dev | $767 |
| **worst single trade** | **−$9,478** |
| worst case as multiple of mean gain | **150×** |

On a $25,000 account, **2.6 contracts** of worst-case loss wipes it out. Full
Kelly on this distribution is 0.011% of capital per contract-unit — which is
another way of saying the edge is real but nowhere near large enough to carry
size.

So the honest framing is not "the wing is a bad trade." It is:

- **on expectancy**, the wing is negative: −$0.39 per structure
- **on survival**, the wing halves volatility (7.67 → 4.40) and cuts the worst
  case by $51.40, from −94.78 to −43.38

The wing converts a slightly-positive-expectancy ruin machine into a
barely-positive-expectancy bounded one. That is a **sizing decision, not an
expectancy decision** — and with t = 1.87 the hedged version is not
distinguishable from zero anyway.

---

## Why this differs from the earlier structure null

Elsewhere this repo found *every* credit structure negative at |t| > 9. Here the
naked strangle is mildly **positive** (+$0.63, t = 2.88). The difference is the
exit.

The earlier tests entered at the ask and exited at the bid, paying the spread
**twice**. This test holds to expiry, paying it **once** — the settlement is
intrinsic value, which costs nothing.

**That is a genuinely useful finding: for credit structures the exit spread is
roughly the entire edge.** Closing early on a $3.10 credit costs a meaningful
fraction of it. Holding to expiry avoids that, at the price of accepting the
full tail — which the numbers above show is a −$9,478 tail.

Commissions do not change this: two legs at ~$0.65 is ~$1.30 against a $63 mean,
so roughly 2% of the edge.

---

## What would change the answer

Not a better forecast — Section 2 of [VOLATILITY.md](VOLATILITY.md) shows the
market already forecasts volatility better than we can. The binding constraints
are:

1. **A cheaper tail hedge than a 5-delta wing.** At 31.4% of credit it is the
   dominant cost. Ratio spreads, further-out wings, or a portfolio-level hedge
   rather than a per-trade one are the candidates.
2. **Enough capital that a −$9,478 print is survivable at meaningful size.**
   This is the real constraint on the naked version and it is arithmetic, not
   strategy.

Caveats: t = 2.88 on 1,240 trades is marginal for a single pre-specified test
and would not survive a wide parameter search; this is one delta pair (16/5) and
one DTE band (25–40); and 2010–2025 contains no 1987-style gap, so the measured
worst case is a lower bound on the true tail, not an estimate of it.
