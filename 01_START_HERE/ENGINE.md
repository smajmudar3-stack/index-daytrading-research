# The Agentic Trading Engine

Autonomous options-trading agent wired to the funded Anthropic Platform account. The agent reads a live
market board, proposes trades, and a stack of deterministic gates decides whether any of them reach the
book. It is **paper-tracked**: no real orders are placed, by design.

Model: `claude-fable-5`, server-side fallback `claude-opus-4-8`. API key read from
`~/quant-factory/.env` (`ANTHROPIC_API_KEY`).

---

## The decision pipeline

A proposal must survive **every** stage. Most cycles produce nothing, which is the intended behaviour.

```
     board (gamma regime, periscopes, UW flow, rotation, growth plan, track record, lessons)
                                      │
                                      ▼
                    ①  ai_trader.decide()   — Fable 5 proposes decisions
                                      │
                                      ▼
                    ②  risk_gates.check_entry()   — deterministic vetoes
                        time window · event blackout · regime gate
                        daily caps · daily loss stop · conviction floor
                                      │
                                      ▼
                    ③  option_pricer.price_trade()   — are the strikes REAL?
                        live bid/ask · two-sided market · open interest
                        package-spread limit · same-strike collapse check
                                      │
                                      ▼
                    ④  sizing.size_trade()   — does it fit THIS account?
                        max loss × 100 vs the hard per-trade cap
                                      │
                                      ▼
                    ⑤  committee.review()   — adversarial second opinion
                        bear advocate → risk officer (holds a veto)
                                      │
                                      ▼
                              logged to the book
```

Then, every cycle and independent of the LLM, `ai_trader.manage_open()` runs the exits:
settlement-aware time stop → per-side stop for condors → gamma-flip invalidation → hard stop →
**peak-trailing stop** → scale at the wall.

---

## What the agent is actually allowed to trade

Out-of-sample testing (`RULES.md`) left exactly **one** validated edge, and killed most of what the
system was previously doing. `rules.py` encodes it and `risk_gates.py` enforces it.

**The edge:** prior-close dealer gamma predicts the intraday **range**, and the option market does not
fully price it — realised/implied range is 0.843× on high-gamma days vs 1.139× on low-gamma
(t = −13.2, measured against VIX9D, stable across all four sub-periods of 15 years). It is a *range*
forecast, never a direction forecast.

**The rule:** prior-close GEX z > +0.5 → sell a 0DTE iron condor, shorts ≈1.25 SD of the
remaining-session move, wings ≈1 SD, enter 10:30–13:00 ET, stop at −0.5× max risk, one at a time,
5% risk. Otherwise stand down. OOS 2016–2026: 853 trades, +3.7%/trade, 91% win, PF 2.04, t = +7.4.

**Rejected and now hard-blocked in `risk_gates.py`:**

| Rejected | Result |
|---|---|
| Buying 0DTE premium on any directional signal | −10% to −11%/trade |
| "Below the gamma flip = buy premium" | −7.2% (straddle), −19.1% (strangle) |
| DIX as a premium-selling filter | permutation p = 0.494 — noise |
| Sector-rotation relative strength (swing) | picks do *worse than random*, p = 0.867 |
| All swing option overlays | beaten by owning SPY on return, Sharpe **and** drawdown |

The retired "below the flip = buy premium" rule was the central claim of `STRATEGY_0DTE.md`; that
document now carries a correction notice at the top.

**Every backtest P&L is modelled** — there are no historical option chains in the repo. So
`rules.log_credit()` records what the market actually pays for this exact structure, one row per
session in the entry window, into `data/credit_log.jsonl`. After ~60 sessions that confirms or kills
the edge against real quotes. This is the single highest-value open validation step (`RULES.md` §6.1).

## Files

| File | Role |
|---|---|
| `ai_desk.py` | Desk strategist. `_distill()` builds the board every other module reads. `_key()` reads the API key. |
| `ai_trader.py` | The agent. `decide()` proposes (LLM); `manage_open()` runs exits (rules only, no LLM). |
| `rules.py` | The validated edge as executable code: gamma gate, condor construction, credit logging. |
| `risk_gates.py` | Hard pre-trade gate stack + shadow-filter mode + settlement-aware force-close. |
| `RULES.md` | The out-of-sample research: validated / suggestive / rejected, and the growth arithmetic. |
| `option_pricer.py` | Live option quotes, multi-leg pricing, liquidity guardrails. |
| `sizing.py` | Contracts from account + max loss, inside the hard cap. Affordability report. |
| `committee.py` | Bear advocate + risk-officer veto. |
| `graduation.py` | Pre-registered paper→live bar + honest projection vs the growth curve. |
| `lessons.py` | Self-improvement loop — reviews closed trades, injects lessons back into the prompt. |
| `growth_plan.py` | The milestone curve and aggression state, inside fixed risk caps. |
| `scan_all.py` | Cycle runner (launchd, every 5 min). |
| `gap_dashboard.py` | UI on **:8094** (`com.gapscan.dashboard`). |
| `RESEARCH_BOTS.md` | Research on production trading bots — the source of the risk-layer design. |

Data/audit artifacts in `data/`: `agent_trades.db`, `gate_log.jsonl`, `committee_log.jsonl`,
`graduation.json`, `affordability.json`, `lessons.json`, `events.json`.

---

## Broker reality (checked 2026-08-05)

**The scheduled agent is not connected to any broker, and cannot be as things stand.** There is no
Robinhood code in this repo, no order-placement path, and `DRY_RUN=True` / `LIVE_AGENT=False`. The
Robinhood connector exists only as an MCP tool inside a Claude chat session — a launchd cron job has no
access to it.

Beyond the wiring, the account permissions do not support the strategy:

| Account | Agent-accessible | Options level | Value |
|---|---|---|---|
| "Agentic" ••••9829 (cash) | **yes** | **level 2** — long calls/puts, covered calls, CSPs only | **$13.47** |
| Individual ••••6490 (margin) | no | level 3 — spreads permitted | $45,248 unsettled |

**Automation runs through Claude cloud routines, not launchd.** A launchd job on the Mac cannot reach the
Robinhood connector — but a *scheduled Claude cloud agent* can, because it runs with the user's
connectors attached. Three routines now carry the live path (see "Cloud routines" below). The local
engine remains the research/validation layer; the cloud routines are the execution layer.

Remaining blockers to live execution:
1. ~~A cron job cannot reach the connector~~ — solved by cloud routines.
2. The only agent-accessible account is **option level 2**, which cannot trade spreads. The validated
   strategy is a 4-leg iron condor.
3. **Multi-leg orders are not available on cash or retirement accounts** through the connector, and the
   agentic account is a *cash* account. An option-level upgrade does **not** remove this — it is the
   account type, not the permission level.
4. The account that *can* trade spreads (level 3, margin) is `agentic_allowed: false`.

Level 2 does permit long calls/puts — but that is precisely the strategy the research rejected at
−10% to −11% per trade, so the one thing the agent could legally automate here is the one thing it
should not do.

## Cloud routines (created 2026-08-05, all DISABLED pending level 3 + margin + funding)

Manage at https://claude.ai/code/routines — cron is UTC, and EDT is UTC−4 **only until 2026-11-01**;
after the DST change every expression below shifts an hour and must be corrected.

| Routine | ID | Cron (UTC) | ET |
|---|---|---|---|
| 0DTE Condor ENTRY | `trig_01GgCEvgYLAd4MQcYdDSLP7V` | `0 15 * * 1-5` | 11:00 |
| 0DTE Condor MANAGE | `trig_019qHRc968nodiMrbQyRhWLy` | `0 17,18,19 * * 1-5` | 13:00/14:00/15:00 |
| 0DTE Condor FLATTEN | `trig_018s1pm4BgebAtPQqPi3NwK3` | `45 19 * * 1-5` | 15:45 |

Routine minimum interval is 1 hour, so minute-level entry timing is not available in the cloud; 11:00 ET
was chosen because the research found it edged 09:35 and 13:00. Each routine's prompt is self-contained
(the cloud agent has no access to this repo) and carries: the no-naked-premium prohibition, the account
pre-flight, the GEX gate fetched from SqueezeMetrics, the structure/sizing maths, and review-before-place.

**Fallback if the account cannot be made margin:** `ticket.py` produces an exact
ready-to-place condor (legs, net-credit limit at the mid, quantity, max loss, stop) whenever every gate
agrees, and `ticket.py fill <credit> <contracts>` records the actual fill. Those recorded fills are what
convert the track record from modelled to measured — the single open question the research flagged.

## Hard constraints that are deliberately not negotiable

- **`DRY_RUN = True` and `LIVE_AGENT = False`** in `risk_gates.py`. Both must flip for real orders, and
  no order-placement code exists yet regardless.
- **Risk caps** in `growth_plan.RISK_CAP`: ≤12% risk per trade, ≤3 open, −25% daily stop. Being behind
  the growth curve relaxes *selectivity*, never these.
- **The graduation bar is pre-registered** in `graduation.BAR`. Moving it to make a result pass is a
  visible code change, which is the point.
- **Dealer gamma is a risk/volatility-regime gate, never a directional forecast.** The
  `gex-forward-returns` study finds GEX does not predict forward returns once you condition on
  VIX/realized vol. The agent's prompt says so and the risk officer is told to veto theses that
  smuggle it back in as alpha.

## Account-size reality

At a $5,000 account with a 12% cap ($600/trade):

| Instrument | One contract risks | Tradeable |
|---|---|---|
| SPX 25-wide 0DTE spread | ~$850 | **No** |
| NDX 100-wide 0DTE spread | ~$4,300 | **No** |
| SPY 2-wide 0DTE spread | ~$86 | Yes — ~5 contracts |
| QQQ 2-wide 0DTE spread | ~$86 | Yes — ~5 contracts |

The board is computed on SPX/NDX dealer gamma; the *expression* must be SPY/QQQ (SPY ≈ SPX/10,
QQQ ≈ NDX/41). `sizing.prompt_block()` tells the agent this, and the sizing gate enforces it.

## Known limitations

- Quotes come from yfinance, which is delayed and can be wider than a real broker's routable market.
  The package-spread thresholds in `option_pricer.py` (35% liquid / 60% equity) are **provisional**;
  every rejection logs its measured spread to `gate_log.jsonl` so they can be recalibrated from data.
- FOMC and CPI dates are **not** hardcoded — they must be entered in `data/events.json` from the
  official calendars. Triple-witching, monthly opex and NFP are computed and need no maintenance.
- P&L is real (premium in vs premium out) only for trades the pricer could value; the rest fall back to
  an underlying-move × leverage estimate. `graduation.stats()['measured_fraction']` reports the split
  and the dashboard shows it.
