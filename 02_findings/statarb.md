# Statistical arbitrage — the hedge-fund quant trade, on 2,275 names, 2018–2026

**Status: CURRENT. Measured 2026-09-22.** Reproduce: `05_studies/statarb_test.py`.

The trade: strip the market and sector out of every name's daily return (60-day regression
on SPY and the 11 sector ETFs), fit the leftover to a mean-reverting process, and bet that
names whose residual has fallen furthest below its own mean come back while those furthest
above go down. Dollar-neutral, ~275 positions, rebalanced every 1, 3 or 5 sessions. This is
Avellaneda & Lee (2010), the canonical quant-equity strategy of the 2000s, whose own paper
reports its Sharpe falling from ~1.4 (1997–2002) to ~0.9 (2003–2007) as it was crowded.
3,791,244 name-days of s-scores; entries at the next open; costs 5 bp a side on actual
turnover, which is generous for names this liquid.

| hold | turnover / rebalance | gross | gross Sharpe | net of 5 bp/side | net Sharpe | A 2018–21 | B 2022–23 | C 2024–26 (net) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 day | 58% | −0.8%/yr | −0.19 | **−8.0%/yr** | −1.98 | −6.3% | −10.1% | −9.1% |
| 3 days | 101% | +1.8%/yr | +0.38 | −2.5%/yr | −0.53 | +0.6% | −3.2% | −5.9% |
| 5 days | 125% | +1.4%/yr | +0.31 | −1.7%/yr | −0.39 | +0.3% | −1.2% | −5.8% |

**Gross, the residual reversion is barely there: 1 to 2 percent a year, Sharpe 0.3–0.4,
declining from the first split to the third. Net of a retail-sized cost it is negative at
every holding period.** The 2000s trade is fully arbitraged at the daily horizon for anyone
paying more than a basis point or two, which is everyone outside a market-making firm. Its
decay is exactly what its authors predicted and what McLean & Pontiff (2016) measure for
published anomalies generally.

This is the "hedge-fund quant math" leaf. The math is not the edge; the edge, where it
exists, is cost and infrastructure, and the firms that have it keep the 1 to 2 percent.
