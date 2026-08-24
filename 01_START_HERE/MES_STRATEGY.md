# MES / MNQ overnight strategy — the real, robust S&P/Nasdaq futures edge

## The honest finding
There is NO robust *intraday* directional edge on the S&P/Nasdaq (tested this session: ORB
noise t=1.0, VWAP reversion/momentum lose, gaps, intraday direction a coin flip). The one
real edge is the **OVERNIGHT drift** — and futures (MES/MNQ) let you trade it directly.
Filtered by trend + volatility, it becomes one of the best simple systematic strategies
there is. It is NOT "insanely profitable" (fantasy) — it is ~10-18% CAGR on notional at a
Sharpe of 1.6-2.2, which is genuinely elite risk-adjusted return, and survivable.

## The rules (mechanical)
Each day at **~3:55pm ET (just before the RTH close):**
1. Is the index **above its 200-day moving average**? (SPX for MES, NDX for MNQ)
2. Is **VIX below its own 20-day average × 1.2** (i.e., volatility not spiking)?
- **If BOTH yes:** BUY 1 micro at the 4:00pm close, HOLD overnight, SELL at the next
  9:30am open. Then flat all day.
- **If either no:** stay flat / in cash overnight.
Never hold intraday — that's the coin flip. You are in the market ~14 hours, ~65-72% of nights.

## Backtested performance (2005-2026, after costs)
| | MES (S&P/SPY) | MNQ (Nasdaq/QQQ) |
|---|---|---|
| Sharpe | 1.65 | **2.18** |
| CAGR (on notional) | 10.2% | **18.0%** |
| Max drawdown | −10% | **−7%** |
| Nights in market | 70% | 72% |
| Positive years | **21 / 22** (only 2022 red, −2%) | similar |
- Robust: edge is stable across all vol-filter thresholds (not overfit); positive in every
  5-year sub-period; made money through 2008 (+0.1%) and 2020 (+36%).
- Vol-targeting did NOT help — keep it simple.

## MES/MNQ dollar terms & sizing (READ THIS)
- MES = $5/point (~$37k notional/contract at SPX ~7300). MNQ = $2/point.
- Est. ~$2,800/yr per MES contract; more per MNQ. Strong return on ~$1.5-2.5k margin.
- **The danger is leverage + overnight gaps.** A −7% notional drawdown = ~−$2,600 on 1 MES.
  On a small ($2.5k) account that is account-threatening. The filters cut gap risk but do NOT
  eliminate it — a surprise overnight event can gap several %. **Size so a −5% overnight gap
  is survivable**: on a small account that means 1 micro and treating it as real risk, or
  expressing the same edge in SHARES (SPY/QQQ) with no leverage.
- This has losing streaks and a worse-than-backtested tail is always possible. Never max-leverage.

## Why it's not "day trading" — and why that's the point
The edge is overnight, so this holds 4pm→9:30am and sits out the session. That's the opposite
of intraday scalping — and it's *why* it works: you stop feeding the intraday coin flip its
costs and only take the exposure that actually pays. Best "MES day-trader" upgrade = stop
day-trading the chop, harvest the overnight drift with a trend+vol filter.

## Files
mes_overnight.py, mes_refine.py (robustness + walk-forward), daily_edges.py / minute_edges.py
/ orb_proper.py / vwap_*.py (the intraday nulls that led here).

---

# FINAL: the MERGED multi-edge system (2026-07-31)

"How are day traders profitable?" — not a magic pattern, but a small real edge + asymmetric
R:R + risk management, over many occurrences. So we merged multiple real edges, weighted by
QUALITY (equal-weighting HURTS when one edge dominates), validated out-of-sample.

## The three components (all long-biased, uptrend-only)
- **75% — OVERNIGHT drift** (the anchor): at ~3:55pm ET, if index>200d SMA AND VIX<20d-avg×1.2,
  hold long overnight (buy 4pm close, sell 9:30am open). Sharpe ~2.2 alone.
- **15% — GAP-FADE** (the diversifier): if the market gapped DOWN >0.3% at the open while
  above the 200d SMA, buy the open and sell the close (fade the down-gap intraday). It is
  NEGATIVELY correlated to the overnight edge (−0.12), so it cuts drawdown.
- **10% — RSI-2 DIP-BUY** (Connors): when RSI(2)<10 and price>200d SMA, buy; exit when RSI(2)>60.
- **0% — trend-following**: the optimizer correctly threw it out (redundant, no marginal value).

## Performance (2005-2026, after costs; OOS-validated fitting on 2005-15, testing 2016-26)
- **MNQ/QQQ: Sharpe 2.30, CAGR 19.5%, maxDD −7.0%, 22/22 positive years.**
- MES/SPY: Sharpe 1.77, CAGR 11.2%, maxDD −9.3%, 21/22 positive years.
- Out-of-sample the merge beat the overnight-edge-alone on BOTH Sharpe and drawdown.

## Honest caveats (unchanged, and they matter)
- The anchor is OVERNIGHT — this is not pure intraday scalping; the gap-fade + dip-buy are the
  intraday/short-term pieces bolted onto it.
- Sharpe 2.3 is elite but comes from LOW volatility (short, filtered exposure), not huge returns
  (~20% CAGR on notional). Real-world fills/slippage will shave it.
- Leverage + overnight gap risk on futures is the ruin risk. −7% notional ≈ −$2.6k/MES. Size so
  a −5% surprise gap survives (1 micro, or run it unleveraged in SPY/QQQ shares). Never max-leverage.
- 22/22 positive years is backtest on notional; a worse-than-history tail is always possible.

## Files
multi_edge.py (the 4 edges + correlations), merge_optimize.py (OOS weight optimization),
final_system.py (locked 75/15/10 weights + by-year). Signals computable daily from close/VIX.
