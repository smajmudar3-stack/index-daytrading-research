# The vendor's options flow — what has been measured, and what is queued

**Status: PARTIAL. Intraday measured 2026-09-21 on 103 sessions; the daily and weekly test
is queued behind the API quota.**

## Intraday: per-minute signed flow on the index proxies

`uw_archive.py` has recorded Unusual Whales `net-prem-ticks` (per-minute net call premium,
net put premium, net delta, ask- and bid-side volume) and 1-minute bars for SPY, QQQ and IWM
since 2026-04-24. This is the vendor's own buy/sell classification — the input the SPXW flow
study (`hunt_flow.py`, null on 1,919 sessions) never had.

Five signals from flow at or before minute t, normalised past-only within the session,
sampled every 30 minutes, against the forward 30/60/120-minute return. 45 tests, so the
noise bar is about |t| = 2.8. Reproduce: `05_studies/uw_intraday_flow_test.py`.

| | Spearman, 30m | Spearman, 60m | best t | P(up \| flow+) / P(dn \| flow−) at 60m |
|---|---:|---:|---:|---|
| SPY, net premium since the open | +0.053 | +0.071 | 2.3 | 57.5% / 51.2% |
| QQQ, net delta since the open | +0.055 | +0.062 | 2.0 | 56.2% / 51.9% |
| IWM, net premium since the open | +0.064 | +0.067 | 2.2 | 54.6% / 54.7% |
| last-30-minute flow, any name | −0.02 to +0.04 | | 1.4 | ~50% both ways |
| ask/bid volume imbalance, any name | ≈ 0 | | 0.7 | ~50% both ways |

**Reading.** Nothing clears the bar. But the cumulative-since-open measures are positive in
all nine name × horizon cells at 30 and 60 minutes, survive dropping the largest day, and
the hit rate is one-sided (flow-positive sessions go on up more often than flow-negative
ones go on down) — which is what a small real effect looks like rather than a volatility
artefact. It is worth **1 to 1.8 bp per trade gross**. A round trip on SPY options costs
5–10 bp of notional. So: suggestive, ten times too small to trade, and it stays on the
recording path. 103 sessions is not enough to say more; re-run at 250.

The last-30-minute flow and the ask/bid imbalance carry nothing at all, which matches
Cont, Cucuringu & Zhang (2023): order-flow imbalance is contemporaneous, not predictive.

## Daily and weekly: queued

`05_studies/scripts/uw_history_pull.py` pulls, for 300 names, the vendor's daily
`options-volume` (call/put volume and premium, bullish/bearish premium), `nope`, dealer
greek exposure, IV rank, realised vol, term structure, 25-delta risk reversal, off-exchange
short volume, short interest, insider counts, plus the **classified flow alerts** (ask/bid
premium split, opening trades, sweeps, volume/OI — the vendor's "unusual activity") and
dark-pool prints, paged back in time. The pull is parked behind the 30,000-a-day quota,
which the fixed scan gate will no longer exhaust; it starts itself when a call returns 200.
Scoring follows `xsec_predictors_test.py` exactly: one observation a week, rank IC, three
splits, the noise bar stated. Until it runs, `flow_lean` and `dp_buy_share` remain priors.
