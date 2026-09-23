# The vendor's options flow — what has been measured, and what is queued

**Status: CURRENT. Intraday measured 2026-09-21 on 103 sessions; daily and weekly measured
2026-09-22 on two years of the vendor's own history.**

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

## Daily and weekly: measured, and null

`05_studies/scripts/uw_history_pull.py` pulled, for the 300 most liquid optionable names,
every vendor endpoint that returns dated history: two years of daily `options-volume`
(call/put volume, ask- and bid-side volume, net call and put premium), a year of dealer
greek exposure (gamma, delta, vanna, charm), a year of the vendor's own implied-versus-
realised volatility, and insider purchase/sale counts by filing date. Joined to the Dolt
panel's split-adjusted forward returns and universe, one observation per name per week,
2024-08 → 2026-08. Reproduce: `05_studies/xsec_uw_test.py`. 48 tests; noise bar |t| ≈ 2.8.

| feature (signed as published) | horizon | weeks | IC | t | 1st half | 2nd half |
|---|---|---:|---:|---:|---:|---:|
| signed option volume, same day (`lean`) | 5d | 96 | −0.003 | −0.4 | −0.009 | +0.003 |
| signed option volume, 5-day mean | 5d | 96 | +0.008 | +0.9 | +0.009 | +0.006 |
| net call − put premium, same day | 5d | 96 | −0.007 | −0.8 | −0.013 | −0.000 |
| put/call ratio, 5-day (− sign expected) | 5d | 96 | **−0.020** | −1.9 | −0.033 | −0.008 |
| option / stock volume (Johnson-So) | 5d | 96 | +0.012 | +0.8 | +0.001 | +0.023 |
| dealer net gamma / delta / vanna | 5d | 44 | −0.01 to −0.02 | < 0.8 | | |
| change in dealer gamma, 5d | 10d | 21 | +0.042 | +1.3 | +0.050 | +0.034 |
| vendor IV − RV | 5d | 44 | +0.028 | +1.2 | +0.044 | +0.011 |
| insider net purchases, 30 days | 5d | 52 | −0.004 | −0.1 | −0.023 | +0.015 |
| signed option volume, same day | 21d | 24 | −0.032 | −1.8 | −0.050 | −0.015 |

**Nothing clears the bar, and the two most-cited flow measures lean the wrong way.** The
vendor's buyer-initiated call-minus-put volume — the closest public proxy to Pan &
Poteshman's open-buy ratio and the input `flow_lean` carried at 0.40, the largest weight in
the vote — ranks next week at IC −0.003 and next month at −0.032. The put/call ratio is
contrarian: names with heavy put volume did slightly BETTER (t −1.9 against the published
sign). Dealer greeks say nothing about direction, which repeats the repo's earlier
`gamma_direction` null on the index. The one mildly positive line, a five-day change in
dealer gamma at 10 days (t 1.3, both halves positive), is worth watching and nothing more.

**What this changes.** `flow_lean` goes to weight 0 as a measured null: two years, 20,746
name-weeks, IC ≈ 0, sign not stable. It had been served at the ceiling (0.45) on a prior
plus a calibration built from overlapping rows. Dark pool stays an unmeasured prior at 0.10,
because the vendor's dark-pool endpoint paged back one day, not a year. Insider stays at
0.06: the count-based vendor series measured null, but the live voter uses the filing-level
opportunistic filter, a different construction, and its own history is what will judge it.

**Not yet testable.** The classified flow ALERTS (sweeps, opening trades, ask-side premium
— the "unusual activity" product) came back six weeks deep, and the Dolt forward returns
end 2026-08-06, so they do not overlap. Re-pull in three months and this table gets a row.
