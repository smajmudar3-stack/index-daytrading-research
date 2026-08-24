# index-daytrading — complete bundle

Everything from `~/index-daytrading` in one place: 26 research reports, 98 Python
modules, 68 study harnesses, and a guide to 16 GB of market data.

Read in this order.

| folder | what's in it |
|---|---|
| **[01_START_HERE](01_START_HERE/)** | The rules the system trades by, and how to run it |
| **[02_findings](02_findings/)** | What the numbers actually said — including everything that failed |
| **[03_research](03_research/)** | 26 literature + repo sweeps (papers, GitHub, Taleb, UW API) |
| **[04_live_system](04_live_system/)** | The 53 modules behind the running dashboard |
| **[05_studies](05_studies/)** | The 113 backtests and hunts that produced the findings |
| **[06_data_guide](06_data_guide/)** | What's in the 16 GB, and how to query it |
| **[MANIFEST.md](MANIFEST.md)** | Every file, with line counts |

---

## The one-paragraph summary

Most of what was tested does not work, and the value of this repo is knowing
*which* parts don't. Every credit structure tested negative on real quotes
(|t| > 9 across 147,350 SPY trades). Far-OTM lottery buying lost 48–90%.
Earnings straddles lost 35% per trade (t = −95.7). There is no reliable
intraday directional edge. Three things did survive honest testing:
**short interest** (IC −0.107 at 63 days, and the sign is *negative* — the
opposite of the squeeze thesis), **VIX backwardation** (t = +3.9/+2.8/+2.1
across all three time splits), and **low dealer gamma** (8 of 8 directional
structures pay more there). The live system trades those three and refuses to
recommend anything the backtests say loses money.

## Start here if you only read one thing

**[02_findings/WHAT_WORKS.md](02_findings/WHAT_WORKS.md)** — the three surviving
signals and their measured strength.

**[02_findings/INTRADAY_DIRECTION.md](02_findings/INTRADAY_DIRECTION.md)** — the
full answer on intraday direction: the ~53% accuracy ceiling, the theta hurdle
that exceeds it, and the one dealer-gamma signal that clears it.

**[02_findings/METHODOLOGY_TRAPS.md](02_findings/METHODOLOGY_TRAPS.md)** — twelve
ways a backtest lies. Four of these produced fake winning strategies in this
repo before being caught. Check any new backtest against this list first.

## The live system

A FastAPI dashboard on **port 8094**, kept alive by launchd
(`com.gapscan.dashboard.plist`), with five tabs:

| tab | what it decides |
|---|---|
| 0DTE | SPX/NDX same-day structure, gated on dealer gamma regime |
| Gap & Go | Opening-range continuation |
| Swing | Days-to-2-weeks direction, weighted vote across 6 signals |
| Account & Risk | Sizing, ruin bounds, position limits |
| Black Swan | Far-OTM convexity candidates, only where spread ≤ 20% |

Every tab logs its calls to `scorecard.py`, which tracks hit rate, expectancy
and calibration per tab, so the weights can be re-estimated from live results
instead of staying at their fabricated priors.
