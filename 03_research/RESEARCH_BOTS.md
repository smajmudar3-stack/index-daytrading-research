I have comprehensive coverage across all angles (read ~16 READMEs in depth plus 2 validation studies). Here is the prioritized report.

---

# Options Trading Bot / Agent Research — Findings & What to Integrate

Reviewed ~60 repos across 10 search angles; read the 16 most credible in depth. Below are the ones worth stealing from, ranked by relevance to your Fable-5 board-reading 0DTE/swing agent, each with a concrete "how we'd use it." I flag hype vs. real honestly.

## Tier 1 — Directly applicable, high signal

**1. joncovington/MEICAgent** — *the sister project to yours* (0DTE Multiple-Entry Iron Condor agent, runs its decision loop inside Claude Code, talks to tastytrade via official SDK). This is the single most relevant repo found. Steal wholesale:
- **8-gate entry checklist** (any failure blocks): time window (no entries <10:00 or >14:30 ET), IV-rank floor, late-entry bias on borderline-IV days, VIX-banded short-strike delta *plus* hard floors (min % distance from spot, ceiling on actual call delta regardless of scan), dual credit floors (credit as % of width AND a fee-adjusted floor), **GEX regime gate (no new condors in negative-gamma regime)**, account-wide caps (max concurrent + max daily, shared across symbols), event blackouts (FOMC/quarterly/triple-witching force-close everything).
- **4 named risk profiles** (conservative→very-aggressive) that reallocate risk rather than just add it — each gate relaxation is offset by tighter stops and lower position caps. Switch with one command.
- **Settlement-aware exits**: cash-settled (SPX/XSP) left to expire; physically-settled (QQQ/IWM) force-closed before the bell; a missed close on a physical symbol escalates as an assignment-risk *failure*. **No profit-target exit** (they removed it as not part of MEIC — only per-side software stop + time force-close).
- **Adaptive per-side stops**: a stopped call spread doesn't force-close the untouched put spread.
- **Pre-registered paper-trading graduation gate**: ≥30 filled ICs, positive expectancy, ≥65% win rate, profit factor 1.3–4.0, bounded drawdown — runs all four profiles in parallel against the *same* live-quote snapshot on separate $100k virtual bankrolls, with tastytrade's *exact per-leg fee schedule* applied.
- *How we'd use it:* Adopt its entry-gate stack, per-side stop logic, settlement-aware exits, and the paper→live graduation gate almost verbatim as our agent's hard risk layer. Path: `github.com/joncovington/MEICAgent`, see `docs/risk-profiles.md`, `docs/paper-trading.md`, `CLAUDE.md`.

**2. sbauwow/schwagent** — mature LLM-overlay options/equities agent (Schwab). Best patterns:
- **Two-layer safety model**: global `DRY_RUN=true` master switch + per-strategy `LIVE_<name>=false` — a strategy trades only when *both* allow it. Default off.
- **Telegram approval + kill switch**: live trades show Approve/Reject inline buttons and block until you respond or timeout; `/kill` and `/resume` remote circuit breaker; `/risk` reports drawdown + rule status.
- **Swarm committee** (DAG of LLM agents): `bull advocate → bear advocate → risk officer → portfolio manager` for a position-sizing decision. Directly maps to structuring your board-reading agent as a debate with an explicit *risk-officer* veto seat.
- **Skills via progressive disclosure**: 23 `SKILL.md` methodology docs; only one-line summaries injected into the system prompt, full content loaded on demand (`llm.load_skill(...)`). Good token-economics pattern for your agent's playbook.
- **Backtest validation harness**: Monte Carlo + Bootstrap Sharpe CI + Walk-Forward before trusting a strategy.
- Pure-stdlib **options math module** (Black-Scholes greeks, IV bisection solver that returns None outside arbitrage bounds, multi-leg `strategy_metrics` for max profit/loss/breakevens) — no scipy.
- *How we'd use it:* the two-layer live gate, the Telegram approve/kill circuit breaker, and the bull/bear/risk-officer/PM committee structure are the three most valuable. Path: `github.com/sbauwow/schwagent`.

**3. milgar7969/alpaca-options-framework** — the best **execution/operational-hardening** reference (ships a real 0DTE SPY gamma strategy with a public dashboard incl. losing days). The "What the Documentation Doesn't Tell You" section is a checklist of production failure modes:
- **Quote-driven exits**: `_evaluate_exit()` fires on every option-quote tick (sub-50ms), not on a timer; `exit_pending` flag set before first `await` prevents duplicate exit orders under cooperative asyncio.
- **Peak-trailing stop**: track `peak_mid`; once mid ≥ entry×activate, trail at `peak_mid × trail_pct`. Plus fixed TP/stop multiples and a 3:25 ET time-stop.
- **Ghost sweeper**: polls REST every minute and force-closes any option position not tracked locally (defends against "cancelled buy still fills" races) — worst-case exposure ~60s.
- **Clean EOD exit**: after time-stop, verify account flat via REST (with retries) then `os._exit(0)` to avoid a WebSocket-teardown restart cascade.
- **Restart recovery**: on startup, reconstruct local state from REST positions.
- **Shadow-filter pattern**: run a new gate in observe-only mode (log what it *would* have blocked) before letting it gate live trades. Excellent way to validate your GEX/flow gates safely.
- *How we'd use it:* even though we're paper-tracked, adopt the ghost-sweeper reconciliation, quote-driven exit + peak-trailing stop, and especially the **shadow-filter pattern** for any new signal gate. Path: `github.com/milgar7969/alpaca-options-framework`.

**4. ferdousbhai/tasty-agent** (80★) — MCP server "let Claude manage your tastytrade portfolio." The **order-placement tool contract is the model for our execution tool**: `place_order` uses *quote-derived mid pricing only* (fetches live quotes for the exact resolved legs, computes signed net mid), validates the final limit against **bid/ask guardrails**, aligns prices to the broker's valid **tick grid** (fails before placement if tick data unavailable rather than submitting an invalid increment), supports `target_value` sizing and `dry_run`, and enforces **built-in rate limiting (2 req/s)**. Also `get_market_metrics` → IV rank/percentile/liquidity.
- *How we'd use it:* copy this exact tool signature/guardrail design for our agent's order tool (mid-pricing, bid/ask sanity check, tick alignment, dry-run, rate limit). Path: `github.com/ferdousbhai/tasty-agent`.

## Tier 2 — Validation & honesty checks (high priority given your DSR discipline)

**5. bettyguo/agent-backtest-lab** — a *statistical-audit harness for LLM trading agents* (not an execution engine). Provides leakage firewall (refuses `date > as_of`), retroactive-adjustment defense (refuses `Adj Close`), **PSR/DSR + multiple-testing correction**, calibration, backtest-overfitting probability, reward-hacking detection, and an honest net-of-cost scorecard against buy-and-hold / naive-momentum / random baselines. Cites the finding that rigorously-evaluated LLM trading agents' "advantages deteriorate markedly."
- *How we'd use it:* run our agent's paper track through this before believing any edge — it operationalizes exactly the DSR/PSR discipline in your memory. Path: `github.com/bettyguo/agent-backtest-lab`.

**6. marcusdrewry/gex-forward-returns** — a careful empirical study (Newey-West predictive regressions, SqueezeMetrics GEX+DIX+VIX, 2011–2026). **Key honest finding: GEX does NOT predict forward returns.** The weak univariate signal (low GEX → higher 1-mo return, t≈−2.0, R²≈1%) *flips sign and goes insignificant once you condition on VIX/realized vol* — it's the volatility risk premium in disguise, unstable across subperiods. GEX *is* a decent volatility/risk-regime gauge, but even that is mostly restating VIX on the market-wide series.
- *How we'd use it:* this validates your "no robust intraday edge" null. Treat dealer-gamma regime in the board strictly as a **risk/vol-regime filter (e.g., condition-gate condors, not a directional signal)**, never as an alpha source. Caveat the author notes: the post-2022 0DTE regime may behave differently and isn't captured by this market-wide series.

**7. emlama/gex-backtesting** — 513 days (2.3 GB) of enriched SPX 0DTE trade data (quote-matched trade-side classification) + notebooks running **pre-registered hypothesis tests with Fisher's exact, control experiments, and FDR correction** on whether gamma-concentration metrics (GCI/PGR/GDW/CAR/charm/vomma/zomma) predict late-day moves / PUT explosions. Methodologically honest (control experiments + FDR).
- *How we'd use it:* a ready free dataset + rigorous template to actually test our gamma-wall/flip signals before trusting them. Path: `github.com/emlama/gex-backtesting`.

## Tier 3 — Useful tactics / components

- **aicheung/0dte-trader** (94★, IBKR): clean spread execution primitives — stop-loss as a % of premium received (`-x 3.0` = stop at 300% of credit), profit-taking as % of credit (`-pt 0.5`), and an **auto-retry limit-order walk** that decrements price toward mid each interval to get multi-leg spreads filled across wide bid/ask. *Use:* the retry-walk fill logic and premium-multiple stop for our order tool.
- **cobriensr/Options-Strike-Calculator** (21★, theta-options.com): delta-ceiling recommendation backed by **9,102 days of VIX-to-SPX range data**, **skew-adjusted fat-tail PoP** for IC/BWB (not naive Black-Scholes PoP), and a **self-improving "lessons learned" pipeline** (weekly-curated lessons injected into the analyze prompt) with Claude vision reading flow charts. UW + Schwab + Databento. *Use:* the VIX-conditioned delta ceiling and skew-adjusted PoP for strike selection; the lessons-learned loop as a memory pattern.
- **corybill/IronCondorResearch**: backtests weekly ICs with short strikes set by z-score/historical-vol, testing which z-score maximizes P&L — a simple template for calibrating our IC width to a target PoP.
- **Matteo-Ferrara/gex-tracker** (207★): canonical *free* CBOE-scraped GEX methodology (assumes dealers long calls / short puts) — reference implementation if you want an independent GEX cross-check vs. Unusual Whales.
- **vidalabelpor/alpaca-options-trader**: clean module separation worth mirroring — dedicated `risk_engine/` (position monitoring, portfolio-greeks thresholds, **automated halts**) split from `strategy_modules/execution` (smart routing, anti-slippage, fill monitoring).
- **pipiku915/FinMem-LLM-StockTrading** (934★, ICLR workshop paper): the **layered-memory + character/profiling** architecture for an LLM trading agent (adjustable "cognitive span" for retention). *Use:* a design reference for giving your board-reading agent structured short/mid/long memory and a defined risk-persona — but note it's stock-trading and its live-edge claims are academic, not validated net-of-cost.
- **moremeds/unusual-whales-skill** & **moremeds/argon**: a Claude Code skill for UW analysis (GEX, VRP put-selling, defined-risk trade ideas) and an options-analytics cockpit — directly analogous to your board; worth reading for prompt/skill structure.
- **pattertj/LoopTrader** (128★): the classic extensible multi-strategy options-bot engine (broker abstraction, Telegram) — good architectural reference but explicitly "work in progress, not feature complete."

## Red flags — skip these (hype/scam tier)
- **Binary/pocket-option bots** (FlatrockITSolutions, pipinstallshan, TopTrenDev, irangarcia, rena-biaobock): binary options + keyboard-mimicking + "AI" — avoid entirely.
- **submartingaleoptions/submartingale-books**: name is literally a martingale (double-down) framing — the classic account-blowup pattern.
- **Sparnex13/trading-agent** ("$40 → $1000 in 30 days"), **ygwyg/MAHORAGA** (social-sentiment "learns and adapts"), **llSourcell/ChatGPT_Trading_Bot** (969★ but a YouTube demo), **nof1-tracker / copy-trading bots**: unrealistic claims or no risk controls / no validation.
- Most **crypto LLM "autonomous agent"** repos (ContestTrade, Helion, second-state/fintool, okx/agent-skills): high stars, but crypto-focused, execution-heavy, and none show honest net-of-cost validated options edges.

## Bottom line — the 6 things to integrate first
1. **MEICAgent's 8-gate entry stack + per-side stops + settlement-aware exits + paper-graduation gate** (closest fit to your system).
2. **schwagent's two-layer live gate + Telegram approve/kill circuit breaker + bull/bear/risk-officer/PM committee** structure for the agent's decision loop.
3. **tasty-agent's order-tool contract** (quote-derived mid, bid/ask guardrail, tick-grid alignment, dry-run, rate-limit) for execution.
4. **milgar's ghost-sweeper reconciliation, quote-driven peak-trailing exit, and shadow-filter pattern** for hardening.
5. **bettyguo/agent-backtest-lab** to audit the paper track (PSR/DSR, leakage, reward-hacking) — matches your existing DSR discipline.
6. **Honesty guardrail from gex-forward-returns + emlama**: use dealer-gamma strictly as a *risk/vol-regime gate*, not a return predictor — condition trades on it, don't bet direction on it.