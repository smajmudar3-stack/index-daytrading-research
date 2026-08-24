# Unusual Whales API — Complete Surface Map & Integration Plan

**Researched:** 2026-08-19 · **Method:** OpenAPI spec (`/api/openapi`, 207 paths) + official docs +
UW's own AI skill files + **112 live probe calls against your real key** + WebSocket connection test.

Everything marked "verified" below was actually executed against your account. Every curl example in
this document was run and returned HTTP 200 unless explicitly noted.

---

## 0. TL;DR — what actually matters

| Finding | Detail |
|---|---|
| **Your tier** | Daily quota **30,000 requests**. Per-minute cap effectively unlimited (`1000000`). You are **below** "API Advanced". |
| **Your 45s cache is unnecessary** | You are using ~130 requests/day against a 30,000/day budget. You can widen usage by ~200x. |
| **Endpoints you can call** | **91 of 112 probed work today.** You use 6. |
| **You are on a deprecated endpoint** | `/api/stock/{ticker}/flow-alerts` (used by your `flow_alerts()`) is **deprecated and will be removed**. |
| **WebSocket** | **Tested: HTTP 401.** Requires the Advanced plan. Not available to you now. |
| **Kafka** | Requires "Startup + Kafka" tier, **$3,000/mo**. Not worth it for this dashboard. |
| **MCP server** | Exists at `https://unusualwhales.com/public-api/mcp`, but is undocumented publicly. UW instead ships **skill files** (see §6) which are more useful. |
| **Missing required header** | Your client omits `UW-CLIENT-API-ID: 100001`, which UW's own skill file says is mandatory. |
| **Biggest data gap you can close today** | `/api/option-trades?opening=true` — true opening-vs-closing trade classification. |

---

## 1. Authentication, headers, and conventions

```bash
export UW="your_token_here"

curl -s "https://api.unusualwhales.com/api/news/headlines?limit=2" \
  -H "Authorization: Bearer $UW" \
  -H "Accept: application/json" \
  -H "UW-CLIENT-API-ID: 100001"
```

**Rules verified from UW's own anti-hallucination skill file (`https://unusualwhales.com/skill.md`):**

- Base URL is always `https://api.unusualwhales.com`. Every path is prefixed `/api/`.
- **All endpoints are `GET`.** The single exception is `POST /api/alerts/configuration`.
- `Authorization: Bearer <token>` header only. **`?apiKey=` / `?api_key=` do not exist.**
- `UW-CLIENT-API-ID: 100001` is documented as required on all requests. (Your calls currently
  succeed without it, but add it — it is what UW's own reference client sends.)
- **There is no `/api/v1/` or `/api/v2/` prefix.** Versioning is per-endpoint suffix, e.g.
  `/api/shorts/{ticker}/interest-float/v2`.

### Parameter format conventions (the non-obvious ones)

| Convention | Format | Example |
|---|---|---|
| **List parameters** | Repeated **bracket** notation. Not comma-joined, not repeated bare. | `tags[]=ask_side&tags[]=bid_side` |
| **Exception: `tickers`** | `/api/market/correlations` uses a *comma-joined* `tickers` param, not brackets. | `?tickers=SPY,QQQ,IWM` |
| **Exception: `types`** | `/api/congress/unusual-trades` uses comma-joined `types`. | `?types=committee_conflict,low_marketcap` |
| **Dates** | ISO `YYYY-MM-DD`. Must be today or a past date; omit for last market day. | `date=2026-08-18` |
| **Timestamps** | `newer_than` / `older_than` accept Unix **seconds or milliseconds**. | `newer_than=1787172831590` |
| **Booleans** | Lowercase strings `true` / `false`. | `opening=true` |
| **Option symbols** | OCC format `{TICKER}{YYMMDD}{C|P}{strike*1000, 8 digits}` | `SPY260820P00765000` |
| **Index tickers** | Use `SPX` / `NDX` for GEX and IV. Use **`SPXW`** for the weekly/0DTE option tape and flow alerts. | see §3.1 |

### ⚠️ Response-shape hazards — this is your `flip_dist_pct` class of bug

These are verified against live responses and **will** crash a naive renderer:

1. **Numbers come back as JSON strings, not numbers.**
   `"price": "0.56"`, `"premium": "168.00"`, `"total_ask_side_prem": "111930"`, `"si_float": "0.0097..."`.
   Every numeric field must go through a `float()` coercion. Your existing `_f()` helper does this
   correctly — keep using it, and never do arithmetic on a raw field.

2. **`gamma_flip` is genuinely null for some tickers.** Verified live, same minute:
   ```
   /api/stock/SPY/gex-levels → {"call_wall":"775","gamma_flip":null,"gamma_magnet":"765","put_wall":"756"}
   /api/stock/SPX/gex-levels → {"call_wall":"7900","gamma_flip":"8096.64","gamma_magnet":"7900","put_wall":"7610"}
   ```
   The docs state explicitly: *"Any field may be `null` when there is no data for the date (or, for
   `gamma_flip`, no zero-crossing)."* A `flip_dist_pct = (spot - gamma_flip)/spot` computation is
   exactly what blows up here. **Guard every field of this object independently.**

3. **`/api/option-trades/multi-leg` returns mostly-null analytics.** Verified: `max_profit`,
   `max_loss`, `net_price`, `net_premium`, `net_delta`, `net_side`, `net_theta` were **all null** on
   live rows, while `strategy`, `strikes`, `leg_count`, `total_premium` were populated. Use the
   structural fields; treat the P&L fields as optional.

4. **`limit` is ignored on some endpoints.** `/api/short_screener?limit=3` returned **50** rows.
   `/api/insider/{ticker}/ticker-flow` returned 500. Never assume `len(rows) <= limit`.

5. **Empty-but-valid results.** `/api/darkpool/SPXW` returns `{"data": []}` (indices have no dark
   pool prints — they are not exchange-traded shares). `/api/socket` returns `{"data": []}`.

6. **Sparse fields on small caps.** `prev_iv`, `iv_change`, `sector`, `marketcap`, `stock_price`
   are frequently `null` on the small-cap names your black-swan scanner targets.

---

## 2. Rate limits and quotas — VERIFIED ON YOUR KEY

Every successful response carries usage headers. **There is no usage endpoint** — you read the
headers of any call you already make.

| Header | Your live value | Meaning |
|---|---|---|
| `x-uw-token-req-limit` | **30000** | Daily request cap for your token |
| `x-uw-daily-req-count` | 129 (after my probes) | Requests used today. **Resets 8:00 PM Eastern**, not midnight |
| `x-uw-req-per-minute-remaining` | **1000000** | Requests left this minute — effectively uncapped on your tier |
| `x-uw-minute-req-counter` | (absent/low) | Requests used this minute |
| `x-uw-req-per-minute-reset` | 60000 | Milliseconds until the minute window resets |

**Status codes:** `401` auth failure (**no `x-uw-*` headers returned** — this is why your lapsed-key
incident was invisible); `403` valid token, insufficient tier; `422` missing/invalid parameter *or*
a premium-gate message; `429` rate limited (per-minute headers **are** still present).

### What this means for your client

Your `_TTL = 45` cache was sized for an unknown ceiling. The real ceiling is **30,000/day with no
practical per-minute limit**. Concretely:

- A 6.5-hour session polling **every 30 seconds** across **20 endpoints** = 15,600 requests/day.
  Still only **52%** of quota.
- Recommendation: **drop the TTL to 10–15s for intraday flow endpoints** (market-tide, net-prem-ticks,
  net-flow/expiry, flow-per-strike-intraday) and **raise it to 3600s+** for daily-updating ones
  (oi-change, short interest, insider, congress, seasonality). Keep 45s as the default.
- **Do add a daily-budget guard**: parse `x-uw-daily-req-count` / `x-uw-token-req-limit` on every
  response and stop non-essential polling above 80%. This is cheap insurance and UW documents the
  exact thresholds.

---

## 3. Complete endpoint inventory

**207 documented paths.** Status column reflects **live probes against your key**:
✅ = verified 200 · 🔒 = tier-gated (403/422 gate message) · ⚠️ = deprecated · 📝 = needs a required param.

### 3.1 Options flow — the raw tape, sweeps, blocks, multi-leg, opening-vs-closing

| Path | Status | Key params | Returns / use |
|---|---|---|---|
| `/api/option-trades` | ✅ | `opening`, `volume_greater_oi`, `size_greater_oi`, `is_otm`, `tags[]`, `excluded_tags[]`, `min_premium`, `min_dte`/`max_dte`, `min_ask_perc`, `include_agg_trades`, `report_flag[]`, `trade_codes[]`, `exchanges[]`, `issue_types[]`, `sectors[]`, `min_size`, `min_volume`, `newer_than` | **The full transaction tape.** Per-print: side (`ask_vol`/`bid_vol`/`mid_vol`), all greeks, IV, OI, `tags:["ask_side","bullish","etf"]`, `multi_vol`, `exchange`, `theo`. **This is where real buy/sell-side classification lives.** Latest trading day only. |
| `/api/option-trades/flow-alerts` | ✅ | `limit`, `ticker_symbol`, `is_call`, `is_put`, `is_otm`, `min_premium`, `size_greater_oi` | Rule-based aggregations (`RepeatedHits`, `…AscendingFill`, `…DescendingFill`). Fields: `total_ask_side_prem`, `total_bid_side_prem`, **`all_opening_trades`**, `has_sweep`, `has_floor`, `has_multileg`, `volume_oi_ratio`. **Replaces your deprecated per-ticker call.** |
| `/api/stock/{ticker}/flow-alerts` | ⚠️ | `limit`, `is_ask_side`, `is_bid_side` | **DEPRECATED — will be removed.** This is what your `flow_alerts()` calls today. Migrate. |
| `/api/option-trades/flow-alerts/{id}` | ✅ | `id` (uuid) | Drill down into the individual prints that composed one alert. |
| `/api/option-trades/multi-leg` | ✅ | `limit` | Identified spreads: `strategy` (e.g. `put_vertical_spread`), `leg_count`, `strikes[]`, `ivs[]`, `all_opening_legs`, `direction`, `all_otm`. **Lets you exclude spread legs from directional flow.** |
| `/api/option-trades/multi-leg/{id}/legs` | ✅ | `id` | Individual legs of one multi-leg trade. |
| `/api/option-trades/full-tape/{date}` | ✅* | `date` path | **Bulk historical download.** Returns HTTP **302** to a signed URL for a gzipped full-market file (not JSON). $250/mo add-on for full market history. |
| `/api/option-trades/exchange-breakdown/{date}` | ✅ | `date` path | Volume split by exchange and trade code. |
| `/api/option-trades/optionable-tickers` | 🔒 | — | Requires **API Advanced**. |
| `/api/option-activity/unusual` | ✅ | `min_premium`, `max_dte`, `unusual`, `ticker_symbol`, `sectors[]`, `order` | "Unusual" preset over Hottest Chains: vol>OI, OTM, DTE≤60, ask-side≥50%, premium≥$10k. |
| `/api/screener/option-contracts` | ✅ | ~90 filters — see §4.3 | **Hottest Chains.** The most powerful screener in the API. |
| `/api/stock/{ticker}/flow-recent` | ✅ | `limit` | Recent flow for one ticker. |
| `/api/stock/{ticker}/flow-per-strike` | ✅ | `date` | Classified premium per strike (EOD). |
| `/api/stock/{ticker}/flow-per-strike-intraday` | ✅ | `date` | **Per-strike, per-minute** `call_premium_ask_side` / `..._bid_side`, `put_*`, `net_premium`. 1,764 rows for SPY; 2,360 for SPXW. |
| `/api/stock/{ticker}/flow-per-expiry` | ✅ | `date` | Same, bucketed by expiry. |
| `/api/stock/{ticker}/net-prem-ticks` | ✅ | `date` | *(you use this)* Per-minute net call/put premium + net delta. |
| `/api/stock/{ticker}/option-stance` | 📝 | **`stance` REQUIRED** — enum: `sell_premium`, `sell_vega`, `directional`, `leaps`, `cheapies` | Ranked contracts fitting a stance, with a `components` sub-score (`dte_fit`, `liquidity`, `greeks_fit`, `iv_regime`, `earnings_timing`), `pop`, `roc`. |
| `/api/option-contract/{id}/flow` · `/historic` · `/intraday` · `/volume-profile` | ✅ | `id` = OCC symbol | Single-contract lifecycle. |
| `/api/stock/{ticker}/option-contracts` · `/expiry-breakdown` | ✅ | | Contract lists and per-expiry breakdown. |

### 3.2 Dark pool and lit off-exchange prints

| Path | Status | Key params | Returns / use |
|---|---|---|---|
| `/api/darkpool/recent` | ✅ | `min_premium`, `max_premium`, `min_size`, `min_volume`, `date`, `limit`, `order`, `order_by` | Market-wide dark pool prints. Fields: `size`, `price`, `premium`, `executed_at`, **`nbbo_bid`/`nbbo_ask` + `nbbo_bid_quantity`/`nbbo_ask_quantity`**, `market_center`, `trade_code`, `ext_hour_sold_codes`, `trade_settlement`. |
| `/api/darkpool/{ticker}` | ✅ | same + `newer_than`/`older_than` | Per-ticker prints. **NBBO context lets you classify each print as above-ask (buyer aggression) or below-bid.** |
| `/api/darkpool/{ticker}/price-levels` | ✅ | `date` | `{price, dark_pool_volume, regular_volume}` — where off-exchange size actually concentrated. |
| `/api/stock/{ticker}/stock-volume-price-levels` | ✅ | `date` | `{price, lit_vol, off_vol}` at fine granularity (22,374 rows for SPY). Lit-vs-dark volume profile. |
| `/api/lit-flow/recent` · `/api/lit-flow/{ticker}` | ✅ | as darkpool | Exchange (lit) prints, same shape, includes `trade_code:"intermarket_sweep"`. |

> **Note:** `/api/darkpool/SPXW` and index tickers return `{"data": []}` — indices have no dark pool.
> Use `SPY` / `QQQ` as the tradable proxy for index dark pool positioning.

### 3.3 GEX / greeks / volatility

| Path | Status | Key params | Returns / use |
|---|---|---|---|
| `/api/stock/{ticker}/gex-levels` | ✅ | `date` | **One call replaces ~35 lines of your `gex_by_strike()`.** Returns `call_wall`, `put_wall`, `gamma_magnet`, `gamma_flip` precomputed by UW using the same method as their site. ⚠️ any field may be null. |
| `/api/stock/{ticker}/greek-exposure` | ✅ | `date`, `timeframe` | *(you use this)* |
| `/api/stock/{ticker}/greek-exposure/strike` | ✅ | `date` | *(you use this)* Static OI-based GEX per strike. |
| `/api/stock/{ticker}/greek-exposure/expiry` | ✅ | `date` | GEX bucketed by expiry — isolate the 0DTE contribution. |
| `/api/stock/{ticker}/greek-exposure/strike-expiry` | ✅ | `expiry` | Strike × expiry grid. |
| `/api/stock/{ticker}/spot-exposures` | ✅ | | **Per-minute** intraday gamma/charm/vanna time series (`*_per_one_percent_move_oi` / `_vol` / `_dir`). 493 rows/day. |
| `/api/stock/{ticker}/spot-exposures/strike` | ✅ | | Spot GEX per strike split by **`_oi` vs `_vol` vs `_bid`/`_ask`** — i.e. gamma from *flow* not just OI. |
| `/api/stock/{ticker}/spot-exposures/expiry-strike` | ✅ | `expiry` | v2 strike × expiry. |
| `/api/stock/{ticker}/spot-exposures/{expiry}/strike` | ⚠️ | | **DEPRECATED** — use `/expiry-strike` above. |
| `/api/stock/{ticker}/greek-flow` | ✅ | `date` | Per-minute `dir_delta_flow`, `dir_vega_flow`, `otm_dir_delta_flow`, `total_*`. Directional greek *flow*, not stock. |
| `/api/stock/{ticker}/greek-flow/{expiry}` | ✅ | | Same, one expiry. |
| `/api/group-flow/{flow_group}/greek-flow` | 📝 | `flow_group` enum: `airline`, `bank`, `basic materials`, `china`, `communication services`, `consumer cyclical`, `consumer defensive`, `crypto`, `cyber`, `energy`, `financial services`, `gas`, `gold`, `healthcare`, `industrials`, **`mag7`**, `oil`, `real estate`, `refiners`, `reit`, `semi`, `silver`, `technology`, `uranium`, `utilities` | Thematic-basket greek flow. **`mag7` and `semi` are directly useful for NDX.** |
| `/api/stock/{ticker}/greeks` | ✅ | | Greeks per strike & expiry. |
| `/api/stock/{ticker}/max-pain` | ✅ | | *(you use this)* |
| `/api/stock/{ticker}/interpolated-iv` | ✅ | | *(you use this)* |
| `/api/stock/{ticker}/iv-rank` | ✅ | | `iv_rank_1y`, `volatility`, `close`. |
| `/api/stock/{ticker}/volatility/realized` | ✅ | `timeframe` | Realized vol series. |
| `/api/stock/{ticker}/volatility/stats` · `/term-structure` | ✅ | | IV stats and term structure. |
| `/api/stock/{ticker}/volatility/variance-risk-premium` | ✅ | | IV − RV spread. |
| `/api/stock/{ticker}/volatility/anomaly` · `/character` | ✅ | | Vol anomaly score / regime character. |
| `/api/volatility/anomaly/top` | 📝 | **`direction` REQUIRED** — enum `short_vol`, `long_vol` | Market-wide vol anomaly ranking. |
| `/api/volatility/character/top` | ✅ | `limit` | |
| `/api/volatility/vix-term-structure` | 🔒 | | Requires the **volatility data add-on**. |
| `/api/stock/{ticker}/historical-risk-reversal-skew` | ✅ | | 25-delta skew history. |
| `/api/stock/{ticker}/nope` | ✅ | | Net Options Pricing Effect: `nope`, `nope_fill`, `call_delta`, `put_fill_delta`, `stock_vol` per minute. |
| `/api/stock/{ticker}/atm-chains` | 📝 | **`expirations[]` REQUIRED** | ATM chain per expiry. |
| `/api/stock/{ticker}/oi-per-strike` · `/oi-per-expiry` · `/option/volume-oi-expiry` | ✅ | `date` | OI distribution. |
| `/api/stock/{ticker}/option/stock-price-levels` | ✅ | | Option volume by underlying price level. |

### 3.4 Market-wide sentiment and breadth

| Path | Status | Key params | Returns / use |
|---|---|---|---|
| `/api/market/market-tide` | ✅ | `date`, **`otm_only`**, **`interval_5m`** | Market-wide net call/put premium per minute. UW's flagship sentiment series. |
| `/api/market/{sector}/sector-tide` | ✅ | `date` | Same for one sector (`Technology`, …). |
| `/api/market/{ticker}/etf-tide` | ✅ | `date` | Same for one ETF, **includes `underlying_price`**. |
| `/api/net-flow/expiry` | ✅ | **`expiration`** (`zero_dte`, `weekly`, …), **`moneyness`** (`otm`, `itm`, `all`), **`tide_type`** (`equity_only`, …), `date` | **0DTE-isolated net premium.** Powers unusualwhales.com/zero-dte. |
| `/api/market/top-net-impact` | ✅ | `date`, `limit`, `issue_types[]` | Tickers driving the tide: `{ticker, net_premium}`. |
| `/api/market/total-options-volume` | ✅ | | Market-wide volume / put-call. |
| `/api/market/oi-change` | ✅ | `date`, `limit`, `order` | **Biggest OI changes market-wide.** Non-index/non-ETF. Updates ~6:45am ET. |
| `/api/market/sector-etfs` | ✅ | | Sector ETF performance snapshot. |
| `/api/market/correlations` | 📝 | **`tickers` REQUIRED, comma-joined** | Cross-ticker correlation matrix. |
| `/api/market/economic-calendar` | ✅ | | Macro events. |
| `/api/market/fda-calendar` | ✅ | | **PDUFA / FDA catalyst dates — direct black-swan fuel for biotech small caps.** |
| `/api/market/insider-buy-sells` | ✅ | | Market-wide daily insider purchases vs sells notional. |
| `/api/market/movers` | 🔒 | | Requires **API Advanced**. |
| `/api/options-pulse/*` (4) | 🔒 | | Requires the **Nasdaq Options Pulse add-on**. |
| `/api/stock/{ticker}/options-volume` | ✅ | | Per-ticker volume + P/C ratio. |
| `/api/screener/stocks` | ✅ | ~60 filters | Ticker-level screener: `bullish_premium`, `bearish_premium`, `gex_ratio`, `gex_net_change`, `cum_dir_delta/gamma/vega`, `iv_rank`, `variance_risk_premium`, `implied_move_perc`, `relative_volume`, `avg_30_day_*`. |

### 3.5 Insider transactions

| Path | Status | Key params | Returns / use |
|---|---|---|---|
| `/api/insider/transactions` | ✅ | **`transaction_codes[]`** (`P`=purchase, `S`=sale), `min_value`, `max_value`, `is_officer`, `is_director`, `is_ten_percent_owner`, `common_stock_only`, `sectors[]`, `min_marketcap`, `max_marketcap`, `start_date`, `end_date`, `group`, `page` | Form 4 / Form 144 transactions. Fields: `owner_name`, `officer_title`, `transaction_code`, **`is_10b5_1`**, `shares_owned_before`/`after`, `amount` (signed), `marketcap`, `next_earnings_date`. |
| `/api/insider/{ticker}/ticker-flow` | ✅ | `limit`, `page` | Daily aggregate: `buy_sell`, `premium`, `volume`, `uniq_insiders`, and **`*_10b5` variants so you can strip scheduled 10b5-1 sales** from discretionary ones. |
| `/api/insider/{sector}/sector-flow` | ✅ | | Same, per sector. |
| `/api/insider/{ticker}` | ✅ | | Roster of insiders for a ticker. |
| `/api/stock/{ticker}/insider-buy-sells` | ✅ | | Per-ticker daily purchases/sells notional. |

### 3.6 Congressional / political trading

| Path | Status | Key params | Returns / use |
|---|---|---|---|
| `/api/congress/recent-trades` | ✅ | `limit`, `date`, `ticker` | `{name, ticker, txn_type, amounts:"$1,001 - $15,000", transaction_date, filed_at_date, member_type, issuer}`. |
| `/api/congress/late-reports` | ✅ | `limit`, `date`, `ticker` | Trades filed past the deadline. |
| `/api/congress/congress-trader` | ✅ | `name`, `ticker`, `date_from`, `date`, `page` | One member's history. |
| `/api/congress/politicians` | ✅ | `last_traded_within_months` | Roster + `trade_count`, `party`, `chamber`, `district`. |
| `/api/congress/unusual-trades*` (4) | 🔒 | `types` (`committee_conflict`, `first_person_to_trade`, `low_marketcap`, `unusual_industry`, `unusually_large_trade`, `fec_donation_conflict`) | **Premium endpoint** — contact dev@unusualwhales.com. |
| `/api/politician-portfolios/*` (5) | ✅ | | Disclosures, holders by ticker, portfolios. |
| `/api/potus/posts` · `/schedule` | ✅ | `limit` | Truth Social posts + presidential schedule. Event-risk feed. |

### 3.7 Short interest

| Path | Status | Key params | Returns / use |
|---|---|---|---|
| `/api/shorts/{ticker}/interest-float/v2` | ✅ | | `short_interest`, `total_float`, **`si_float`**, **`days_to_cover`**, **`fee_rate`** (borrow cost), `rebate_rate`, `short_shares_available`. 124 rows of history. |
| `/api/shorts/{ticker}/interest-float` | ⚠️ | | **DEPRECATED v1** — use `/v2`. |
| `/api/shorts/{ticker}/data` | ✅ | | Near-real-time borrow: `short_shares_available`, `fee_rate`, `rebate_rate` with timestamps (1,000 rows). |
| `/api/shorts/{ticker}/ftds` | ✅ | | Failures to deliver: `{date, quantity, price}`. Squeeze precursor. |
| `/api/shorts/{ticker}/volume-and-ratio` | ✅ | | Daily short volume ratio. **Note: top-level key is `si`, not `data`.** |
| `/api/shorts/{ticker}/volumes-by-exchange` | ✅ | | Short volume split by venue. |
| `/api/short_screener` | ✅ | | Market-wide short screen. **Ignores `limit`** (returned 50). |

### 3.8 Earnings

| Path | Status | Params | Use |
|---|---|---|---|
| `/api/earnings/afterhours` · `/premarket` | ✅ | `date`, `limit` | Today's reporters by session. |
| `/api/earnings/{ticker}` | ✅ | | Historical earnings reactions. |
| `/api/stock/{ticker}/earnings` | ✅ | `report_type` | Earnings history (fundamentals controller). |
| `/api/companies/{ticker}/earnings-estimates` | 🔒 | | **API Advanced.** |
| `/api/companies/{ticker}/transcripts/{quarter}` | 🔒 | | **API Advanced.** |

### 3.9 ETF / sector flows

| Path | Status | Use |
|---|---|---|
| `/api/etfs/{ticker}/in-outflow` | ✅ | **Creation/redemption flows** — real money into/out of SPY/QQQ/IWM (680 rows). |
| `/api/etfs/{ticker}/holdings` · `/weights` · `/exposure` · `/info` | ✅ | Constituents, sector/country weights, and (via `/exposure`) which ETFs hold a given name — useful for small-cap forced-flow. |
| `/api/stock/{sector}/tickers` | ✅ | Companies in a sector. |

### 3.10 Seasonality, news, and the rest

| Path | Status | Use |
|---|---|---|
| `/api/seasonality/market` · `/{ticker}/monthly` · `/{ticker}/year-month` · `/{month}/performers` | ✅ | Monthly return stats. `{month}` is an integer 1–12. |
| `/api/news/headlines` | ✅ | Headlines + Truth Social. Also the recommended lightweight call for a rate-limit health check. |
| `/api/stock/{ticker}/quote` · `/stock-state` · `/info` · `/ohlc/{candle_size}` | ✅ | Price data. `candle_size` e.g. `1d`, `1m`. |
| `/api/stock/{ticker}/technical-indicator/{function}` | ✅ | RSI/MACD/BBANDS/VWAP. Params `interval`, `time_period`, `series_type`. |
| `/api/stock/{ticker}/financials` · `/income-statements` · `/balance-sheets` · `/cash-flows` | ✅ | `report_type` param. |
| `/api/institutions` · `/latest_filings` · `/institution/{name}/holdings` · `/sectors` · `/{ticker}/ownership` | ✅ | 13F data. `/institution/{name}/activity` is ⚠️ **deprecated** → use `/activity/v2`. |
| `/api/stock/{ticker}/ownership` | 🔒 | **Enterprise only.** |
| `/api/alerts` · `/alerts/configuration` (GET+POST) · `/alerts/filters` · `/alerts/query/grammar` | ✅ | Your UW account's own alert configs. The only `POST` in the API. |
| `/api/crypto/*` (4), `/api/forex/*` (3), `/api/digital-currencies/*` (2), `/api/commodities/{name}`, `/api/economy/{indicator}` | ✅ | Other asset classes. |
| `/api/predictions/*` (9) | ✅ | Prediction-market (Polymarket-style) whales, smart money, liquidity. |
| `/api/private-markets/*` (9) | ✅ | Pre-IPO company data. |
| `/api/futures/*` (5) | 🔒 | **Advanced tier or `futures` add-on.** (ES/NQ futures flow — would be excellent for SPX/NDX, but gated.) |
| `/api/analytics/sliding` · `/analytics/window` · `/calendar/ipo` · `/companies/listings` | 🔒 | **API Advanced.** |
| `/api/companies/{ticker}/profile` · `/dividends` · `/splits` | 🔒 | **API Advanced.** |

---

## 4. Working curl examples

All of the following were **executed against your key and returned HTTP 200.** Set `export UW=<token>` first.

### 4.1 ⭐ True opening-vs-closing trade classification

```bash
# Opening trades only, hitting the ask, in common stock, ≥$100k premium
curl -s -G "https://api.unusualwhales.com/api/option-trades" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" \
  -d opening=true \
  -d 'tags[]=ask_side' \
  -d min_premium=100000 \
  -d 'issue_types[]=Common Stock' \
  -d limit=50
```

```bash
# Volume > OI, excluding bid-side prints, OTM, ≤60 DTE  (the classic "new position" screen)
curl -s -G "https://api.unusualwhales.com/api/option-trades" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" \
  -d volume_greater_oi=true \
  -d 'excluded_tags[]=bid_side' \
  -d min_premium=100000 -d max_dte=60 -d is_otm=true -d limit=50
```

**Verified response fields (note every number is a string):**
```json
{
  "option_chain_id": "SPY260820P00765000", "underlying_symbol": "SPY",
  "option_type": "put", "strike": "765", "expiry": "2026-08-20",
  "executed_at": "2026-08-19T20:15:00.001000Z",
  "price": "0.56", "size": 3, "premium": "168.00",
  "nbbo_bid": "0.56", "nbbo_ask": "0.57", "theo": "0.560000000000031",
  "ask_vol": 15482, "bid_vol": 20038, "mid_vol": 1555, "no_side_vol": 0,
  "multi_vol": 7920, "stock_multi_vol": 1,
  "volume": 37075, "open_interest": 2933,
  "tags": ["bid_side", "bullish", "etf"],
  "delta": "-0.2049347356049323", "gamma": "0.0586040265106923",
  "implied_volatility": "0.1204433752199205",
  "exchange": "XCBO", "trade_code": null, "issue_type": "ETF"
}
```

> **`opening` vs `volume_greater_oi` vs `size_greater_oi` — these are three different things:**
> `opening=true` is UW's own opening-trade determination. `volume_greater_oi=true` filters contracts
> where today's *cumulative* volume exceeds *yesterday's* OI (a proxy). `size_greater_oi=true`
> requires the *single print* to exceed OI (much stricter, rarer, higher conviction).
> The rigorous confirmation is next-morning OI change — see §4.5.

### 4.2 ⭐ Dark pool prints with NBBO context

```bash
# Market-wide dark pool blocks ≥ $5M
curl -s -G "https://api.unusualwhales.com/api/darkpool/recent" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" \
  -d min_premium=5000000 -d limit=50

# Per-ticker, ≥$1M, with pagination cursors
curl -s -G "https://api.unusualwhales.com/api/darkpool/NVDA" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" \
  -d min_premium=1000000 -d limit=100
```

**Verified response:**
```json
{"size": 7313, "ticker": "QQQ", "price": "718.9", "premium": "5257315.7",
 "executed_at": "2026-08-19T22:41:27Z", "volume": 35695392,
 "nbbo_bid": "718.87", "nbbo_ask": "718.9",
 "nbbo_bid_quantity": 53, "nbbo_ask_quantity": 600,
 "market_center": "L", "trade_code": null, "canceled": false,
 "ext_hour_sold_codes": "extended_hours_trade", "trade_settlement": "regular",
 "tracking_id": 10501276726015}
```

**Classification recipe:** `price >= nbbo_ask` → buyer-initiated; `price <= nbbo_bid` → seller-initiated;
between → passive/midpoint. Sum signed `premium` over the session for a net dark-pool positioning
score. `canceled: true` rows must be dropped.

### 4.3 ⭐ Small-cap big-move scanner (Hottest Chains)

```bash
curl -s -G "https://api.unusualwhales.com/api/screener/option-contracts" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" \
  -d min_premium=100000 \
  -d vol_greater_oi=true \
  -d is_otm=true \
  -d max_dte=45 \
  -d max_marketcap=3000000000 \
  -d min_ask_perc=0.6 \
  -d 'issue_types[]=Common Stock' \
  -d order=premium -d order_direction=desc -d limit=100
```

High-signal filters available here that you have nowhere else:
`min_days_of_oi_increases` (consecutive days OI grew), `min_days_of_vol_greater_than_oi`,
`min_ask_side_perc_7_day` (7-day persistence of ask-side buying), `min_sweep_volume_ratio`,
`min_floor_volume_ratio` (floor brokers = institutional), `min_volume_ticker_vol_ratio`,
`min_oi_change_perc`, `is_new`, `exclude_ex_div_ticker`.

**Verified row** returns `ask_side_volume`, `bid_side_volume`, `mid_volume`, `floor_volume`,
`sweep_volume`, `multileg_volume`, `cross_volume`, `ask_side_perc_7_day`, `days_of_oi_increases`,
`prev_oi`, `roc`, plus greeks. *(NOTE: `min_volume` default floor — contracts under 200 volume are never returned.)*

### 4.4 ⭐ 0DTE-isolated net premium (for the SPX/NDX panel)

```bash
curl -s -G "https://api.unusualwhales.com/api/net-flow/expiry" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" \
  -d expiration=zero_dte \
  -d moneyness=otm \
  -d tide_type=equity_only
```

Returns nested `data[0].data[]` (**note the double nesting**) of per-minute
`{timestamp, net_call_premium, net_put_premium, net_volume, underlying_price}`.
Top-level echoes `date`, `expiration`, `moneyness`, `tide_type`.

### 4.5 ⭐ OI change — did yesterday's volume become real positions?

```bash
# Market-wide biggest OI builds (updates ~6:45am ET)
curl -s -G "https://api.unusualwhales.com/api/market/oi-change" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" \
  -d limit=100 -d order=desc

# One ticker
curl -s "https://api.unusualwhales.com/api/stock/NVDA/oi-change" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001"
```

**Verified row** — this is the ex-post ground truth on opening trades:
```json
{"option_symbol": "AS260918C00040000", "underlying_symbol": "AS",
 "curr_oi": 46272, "last_oi": 5299, "oi_diff_plain": 40973,
 "oi_change": "7.7322136252123042",
 "days_of_oi_increases": 5, "days_of_vol_greater_than_oi": 1,
 "prev_ask_volume": 39300, "prev_bid_volume": 11734, "prev_mid_volume": 1762,
 "prev_multi_leg_volume": 2084, "prev_total_premium": "1850730.00",
 "volume": 52796, "trades": 1117, "avg_price": "0.3505...", "rnk": 3}
```
`prev_ask_volume` vs `prev_bid_volume` on a contract whose OI *actually grew* is the cleanest
"institutions opened a directional position" signal in the entire API.

### 4.6 Insider open-market purchases (not 10b5-1 scheduled sales)

```bash
curl -s -G "https://api.unusualwhales.com/api/insider/transactions" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" \
  -d 'transaction_codes[]=P' \
  -d min_value=250000 \
  -d common_stock_only=true \
  -d start_date=2026-08-01 \
  -d limit=100
```
Transaction codes: `P` = open-market purchase (the informative one), `S` = sale, `A` = award/grant,
`M` = option exercise, `F` = tax withholding. **Filter to `P` and `is_10b5_1=false`** — everything
else is compensation mechanics, not information.

### 4.7 Short interest / squeeze fuel

```bash
curl -s "https://api.unusualwhales.com/api/shorts/GME/interest-float/v2" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001"
```
```json
{"symbol":"AAPL","short_interest":141606163,"market_date":"2026-07-31",
 "total_float":14594180000,"si_float":"0.009702920136657215410526661998",
 "days_to_cover":"2.42","fee_rate":"0.2782","rebate_rate":"3.3518",
 "short_shares_available":10000000}
```
`si_float` is a **fraction, not a percent** (0.0097 = 0.97%). `fee_rate` is annualized borrow cost —
a spiking fee_rate with falling `short_shares_available` is the real squeeze precondition.

### 4.8 GEX levels in one call (replaces your hand-rolled math)

```bash
curl -s "https://api.unusualwhales.com/api/stock/SPX/gex-levels" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001"
# {"data":{"call_wall":"7900","gamma_flip":"8096.64","gamma_magnet":"7900","put_wall":"7610"}}
```

### 4.9 Per-strike intraday classified premium

```bash
curl -s "https://api.unusualwhales.com/api/stock/SPXW/flow-per-strike-intraday" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001"
```
```json
{"timestamp":"2026-08-19T13:30:53.555000Z","ticker":"SPY","strike":"680",
 "call_volume_ask_side":0,"call_volume_bid_side":0,
 "put_volume_ask_side":31,"put_volume_bid_side":62,
 "call_premium_ask_side":"0","put_premium_ask_side":"7707.00",
 "put_premium_bid_side":"11246.00","net_premium":"3539.00","trades":15}
```

### 4.10 Multi-leg spread identification

```bash
curl -s -G "https://api.unusualwhales.com/api/option-trades/multi-leg" \
  -H "Authorization: Bearer $UW" -H "UW-CLIENT-API-ID: 100001" -d limit=100
```
```json
{"strategy":"put_vertical_spread","leg_count":2,"strikes":["765","766"],
 "ivs":["0.1204","0.1160"],"ticker":"SPY","total_premium":"390.00",
 "all_otm":true,"all_opening_legs":false,"direction":"unknown","code":"mlat",
 "min_dte":1,"max_dte":1,"uniq_exchanges":["XCBO"],
 "max_profit":null,"max_loss":null,"net_premium":null,"net_delta":null,"net_side":null}
```
⚠️ All the `net_*`, `max_profit`, `max_loss` fields were **null** on live data. Use `strategy`,
`strikes`, `leg_count`, `total_premium`, `all_otm`.

### 4.11 Other validated calls

```bash
# Sector/thematic greek flow — mag7 is directly relevant to NDX
curl -s "https://api.unusualwhales.com/api/group-flow/mag7/greek-flow" -H "Authorization: Bearer $UW"

# Market tide, OTM-only, 5-minute bars
curl -s -G "https://api.unusualwhales.com/api/market/market-tide" -H "Authorization: Bearer $UW" \
  -d otm_only=true -d interval_5m=true

# Correlations (comma-joined, NOT brackets)
curl -s -G "https://api.unusualwhales.com/api/market/correlations" -H "Authorization: Bearer $UW" \
  -d tickers=SPY,QQQ,IWM

# Contract stance ranking (stance is REQUIRED)
curl -s -G "https://api.unusualwhales.com/api/stock/SPY/option-stance" -H "Authorization: Bearer $UW" \
  -d stance=directional

# Vol anomaly leaderboard (direction is REQUIRED)
curl -s -G "https://api.unusualwhales.com/api/volatility/anomaly/top" -H "Authorization: Bearer $UW" \
  -d direction=short_vol -d limit=25

# ETF creation/redemption flow
curl -s "https://api.unusualwhales.com/api/etfs/QQQ/in-outflow" -H "Authorization: Bearer $UW"

# FDA catalyst calendar
curl -s -G "https://api.unusualwhales.com/api/market/fda-calendar" -H "Authorization: Bearer $UW" -d limit=50

# Congress trades in one name
curl -s -G "https://api.unusualwhales.com/api/congress/recent-trades" -H "Authorization: Bearer $UW" \
  -d ticker=NVDA -d limit=50

# ATM chains (expirations[] is REQUIRED)
curl -s -G "https://api.unusualwhales.com/api/stock/SPY/atm-chains" -H "Authorization: Bearer $UW" \
  -d 'expirations[]=2026-08-21'
```

---

## 5. Streaming — WebSocket and Kafka

### 5.1 WebSocket — **TESTED: your key gets HTTP 401**

```python
# Result of live connection attempt with your token:
# WS ERROR: InvalidStatus server rejected WebSocket connection: HTTP 401
```

The docs confirm: *"Websocket access for personal use is only available through the **Advanced
plan**."* This is a hard tier gate, not a configuration problem.

**Connection contract** (for when/if you upgrade):

- **URL:** `wss://api.unusualwhales.com/socket?token=<YOUR_API_TOKEN>`
- **Auth:** token is a **query parameter**, not a Bearer header. (This is a Phoenix/Elixir socket.)
- **Join frame:** `{"channel":"option_trades","msg_type":"join"}`
- **Join ack:** `["option_trades",{"response":{},"status":"ok"}]`
- **Message envelope:** every message is a 2-element array `[<CHANNEL_NAME>, <PAYLOAD>]`.

**Channels:**

| Channel | Notes |
|---|---|
| `option_trades` / `option_trades:TICKER` | **6–10M records/day** on the unfiltered channel. |
| `flow-alerts` | Note the **hyphen** — inconsistent with the underscored channels. |
| `price` / `price:TICKER` | `{"ticker","close","time"(ms),"vol"}` |
| `gex` / `gex:TICKER` | Per-ticker gamma/charm/vanna per 1% move. |
| `gex_strike` / `gex_strike:TICKER` | Strike-level. |
| `gex_strike_expiry` / `gex_strike_expiry:TICKER` | Strike × expiry. |
| `periscope` / `periscope:TICKER` | MM greek exposures for **SPX, VIX, XSP, NANOS**. ⚠️ **Not available on enterprise or enterprise-startup plans** — retail Advanced only. |
| `market_tide` | Market tide + OTM tide. |
| `net_flow:TICKER` | Net call/put premium aggregates. |
| `interval_flow` | Per-interval sweeps/floors/multilegs/greek flow/IV — built for spike alerting. |
| `contract_screener` | Live Hottest Chains snapshots. |
| `lit_trades` / `off_lit_trades` | Lit and **dark pool** prints in real time. |
| `news` | Headlines + Truth Social. |
| `trading_halts` | **Halts / resumes / LULD pauses** — genuinely valuable for a black-swan scanner. |
| `custom_alerts` | Your own UW account alert configs. |
| `futures_trades` / `futures:ESU6` | Advanced tier or `futures` add-on. |

**Reconnect/heartbeat:** UW documents **no** application-level heartbeat or sequence numbers. Their
guidance is explicit and unusual — **the server drops messages on its side if your consumer falls
behind**. Required production pattern (from UW's own websocket skill):

- Receive loop does nothing but `queue.put_nowait(raw)`; a separate task parses and batch-writes.
- Bounded queue (`maxsize ≈ throughput × acceptable_lag_seconds`, they suggest ~50,000) with an
  explicit drop policy.
- Exponential-backoff reconnect loop that **re-sends all join frames** on reconnect.
- Log queue depth and drop counts — otherwise "server dropped it" and "I fell behind" are indistinguishable.
- Use `orjson`, not stdlib `json`, at these rates.

Reference implementations: `https://github.com/unusual-whales/api-examples` (`ws-multi-channel-multi-output`, Python and Node).

### 5.2 Kafka — **$3,000/mo tier, not documented publicly**

From the OpenAPI `info` block:

> *"Need Kafka streaming? Our **Startup + Kafka tier at $3,000/mo** adds real-time Kafka cluster
> access. Annual plan available at $30,000/yr (2 months free) with the same 1,000 req/min burst allowance."*

The marketing page `https://unusualwhales.com/public-api/kafka` is a client-side SPA with no
technical content, and there is no `skills/kafka.md` (404). **Broker addresses, SASL credentials,
topic names and schemas are provisioned per-customer** — they are not published. Contact
`oskar@unusualwhales.com`.

**Assessment: not worth it for this dashboard.** Kafka's value is a durable, replayable, ordered
full-market firehose for a data lake. Your dashboard consumes aggregates. The $250/mo
`full-tape/{date}` bulk download gives you historical transaction-level data for backtesting at
1/12th the price.

### 5.3 MCP server

An MCP endpoint is advertised at `https://unusualwhales.com/public-api/mcp`, but like the Kafka page
it is an SPA shell with no published transport, auth, tool list, or config schema, and there is no
`skills/mcp.md`.

**What UW actually ships instead — and what you should use — are Agent Skill files:**

| Skill | URL |
|---|---|
| Master API skill (anti-hallucination endpoint whitelist) | `https://unusualwhales.com/skill.md` |
| API usage / rate-limit monitor | `https://unusualwhales.com/skills/uw-api-usage-monitor-skill.md` |
| WebSocket consumption | `https://unusualwhales.com/skills/websocket.md` |
| Institutional / 13F data | `https://unusualwhales.com/skills/institutional.md` |
| Earnings vol scan (call calendars) | `https://unusualwhales.com/skills/uw-earnings-vol-scan-skill.md` |
| Building a local full-tape data lake | `https://unusualwhales.com/skills/uw-options-data-lake-skill.md` |

Since your repo already runs an agentic stack (`ai_desk.py`, `ai_trader.py`), dropping
`skill.md` into a skills directory is strictly better than an undocumented MCP endpoint — it
contains the explicit hallucination blacklist that prevents the agent from inventing `/api/options/flow`.

### 5.4 Tier summary

| Tier | Price | Gets you |
|---|---|---|
| **Your current tier** | — | 30,000 req/day, ~uncapped/min, 91 of the endpoints probed. **No WebSocket.** |
| API Advanced | see UW pricing | **WebSocket**, `/market/movers`, `/companies/*`, `/analytics/*`, `/calendar/ipo`, `/optionable-tickers`, futures |
| Startup | $750/mo ($7,500/yr) | 500 req/min, 80K/day, 90-day lookback, commercial use |
| Startup + Kafka | $3,000/mo ($30,000/yr) | Kafka cluster |
| Add-ons | — | Nasdaq Options Pulse; volatility (VIX term structure); futures; full-tape history ($250/mo) |
| Enterprise | custom | `/stock/{ticker}/ownership`, congressional unusual-trades, redistribution |

---

## 6. Deprecated endpoints — act on the first one

| Endpoint | Replacement |
|---|---|
| ⚠️ **`/api/stock/{ticker}/flow-alerts`** — **you use this today** | `/api/option-trades/flow-alerts?ticker_symbol={T}` — richer response incl. `all_opening_trades`, `has_sweep`, `has_floor`, `volume_oi_ratio` |
| ⚠️ `/api/shorts/{ticker}/interest-float` | `/api/shorts/{ticker}/interest-float/v2` |
| ⚠️ `/api/stock/{ticker}/spot-exposures/{expiry}/strike` | `/api/stock/{ticker}/spot-exposures/expiry-strike?expiry=…` |
| ⚠️ `/api/institution/{name}/activity` | `/api/institution/{name}/activity/v2` |

---

## 7. ⭐ THE RANKED RECOMMENDATION

Ranked by **information you do not already possess**, per your calibration: dealer-gamma regime does
not predict direction, credit structures are negative-EV, and IV-cheapness screens are
counterproductive. Everything below is deliberately weighted toward *order-flow provenance and
positioning* — data with no price/IV derivative in it — and away from more transforms of price and IV.

---

### #1 — `/api/option-trades` with `opening=true`
**Unlocks:** True opening-vs-closing classification on the raw print tape, plus per-print
`ask_vol`/`bid_vol`/`mid_vol` and `multi_vol`. This is the single largest information gap in your
current setup: your `summarize_flow()` infers direction from *alert-level* aggregate premium, which
cannot distinguish a fund opening a bullish position from one closing a bearish one — opposite
inferences from identical premium.
**Panel:** Rewrite `summarize_flow()` in `uw_client.py` to pull the tape with `opening=true` and
`excluded_tags[]=bid_side`, then aggregate signed premium. Feeds the swing-signal panel and the
periscope directional read.
**Integration note:** Replaces the inference in `summarize_flow()`; keep `_f()` string-coercion, and
subtract `multi_vol` to avoid counting spread legs as directional (see #8).

---

### #2 — `/api/darkpool/{ticker}` + `/api/darkpool/recent`
**Unlocks:** Institutional equity positioning executed off-exchange, with `nbbo_bid`/`nbbo_ask` on
every print so you can classify buyer- vs seller-initiated. This is an **entirely new data class**
for your dashboard — not a derivative of options, price, or IV. ~40–50% of US equity volume prints
off-exchange and you currently observe none of it.
**Panel:** New "Institutional Positioning" panel; also as a confirmation filter on swing signals.
**Integration note:** `price >= nbbo_ask` → buy-initiated, `<= nbbo_bid` → sell-initiated; sum signed
`premium` intraday; **drop `canceled: true` rows**; use SPY/QQQ as the index proxy (SPX returns empty).

---

### #3 — `/api/screener/option-contracts` (Hottest Chains)
**Unlocks:** A real engine for the small-cap black-swan scanner. ~90 server-side filters including
`max_marketcap`, `vol_greater_oi`, `min_ask_perc`, `min_days_of_oi_increases`,
`min_ask_side_perc_7_day`, `min_sweep_volume_ratio`, `min_floor_volume_ratio`. Today you would have
to fetch and filter client-side across thousands of names; this does it in one request.
**Panel:** Becomes the primary feed for `blackswan_panel.py` / `gap_scanner.py`.
**Integration note:** One call replaces an entire scan loop. `min_ask_side_perc_7_day` gives you
*persistence* of accumulation — a genuinely novel feature, not a price transform.

---

### #4 — `/api/market/oi-change` + `/api/stock/{ticker}/oi-change`
**Unlocks:** **Ex-post ground truth** on whether yesterday's volume actually became open positions,
with the prior day's `prev_ask_volume` vs `prev_bid_volume` attached. This is the confirmation layer
for #1: a contract whose OI genuinely grew *and* whose prior-day volume was ask-side is
unambiguous institutional accumulation. `days_of_oi_increases` gives multi-day persistence.
**Panel:** Premarket refresh of both the swing panel and the black-swan watchlist.
**Integration note:** Updates once daily ~6:45am ET — cache for the whole session (TTL 3600s+).
Perfect for a premarket build step in `build_snapshot.py`.

---

### #5 — `/api/shorts/{ticker}/interest-float/v2` + `/api/shorts/{ticker}/data` + `/ftds`
**Unlocks:** Short interest, `days_to_cover`, **`fee_rate`** (annualized borrow cost),
`short_shares_available`, and failures-to-deliver. Borrow-market stress is a well-documented driver
of violent upside moves in small caps and is completely absent from your stack. Notably, `/data`
gives near-real-time borrow availability, not just the twice-monthly SI print.
**Panel:** Squeeze-risk column on the black-swan scanner; a hard veto on short-side swing signals.
**Integration note:** `si_float` is a **fraction not a percent**. Rising `fee_rate` + falling
`short_shares_available` is the actual precondition; static high SI alone is not.

---

### #6 — `/api/insider/transactions` (+ `/api/insider/{ticker}/ticker-flow`)
**Unlocks:** Form 4 open-market insider purchases, filterable server-side by
`transaction_codes[]=P`, `min_value`, `is_officer`/`is_director`, and market cap — plus
`is_10b5_1` and `*_10b5` aggregates so you can **strip scheduled sales from discretionary ones**.
You have an EDGAR ingester in `quant-factory`, but this is real-time, pre-parsed, and filterable.
**Panel:** Conviction overlay on swing signals; small-cap accumulation flag on the scanner.
**Integration note:** Filter to `transaction_code == "P"` and `is_10b5_1 == false`. Everything else
(`A`, `M`, `F`, and most `S`) is compensation mechanics and carries no information.

---

### #7 — `/api/net-flow/expiry?expiration=zero_dte`
**Unlocks:** Net premium **isolated to contracts expiring today**, further separable by `moneyness`
and `tide_type`. Your `net-prem-ticks` call blends all expiries together, so 0DTE flow is diluted by
monthly positioning. This is classified flow (ask-vs-bid premium), not a price derivative.
**Panel:** Directly into the SPX/NDX 0DTE panel alongside gamma levels.
**Integration note:** Response is **double-nested** — `payload["data"][0]["data"]` is the minute
series. This is what powers unusualwhales.com/zero-dte.

---

### #8 — `/api/option-trades/multi-leg`
**Unlocks:** Identification of which prints are spread legs (`strategy`, `leg_count`, `strikes[]`).
This is a **correction to a live bug in your reasoning**, not just new data: your `summarize_flow()`
counts every alert as directional, so a put vertical registers as both "puts bought" and "puts sold"
and pollutes the lean. Live data confirms real prints carry `multi_vol: 7920` alongside `size: 3`.
**Panel:** A filter *upstream* of every flow-derived number in the periscope.
**Integration note:** Cross-reference by `option_chain_id`, or more cheaply set
`is_multi_leg=false` on `/api/option-trades` to exclude them at the source. ⚠️ The `net_*`,
`max_profit`, `max_loss` fields are null in practice — do not depend on them.

---

### #9 — `/api/stock/{ticker}/flow-per-strike-intraday`
**Unlocks:** Per-strike, per-minute premium **split into ask-side and bid-side** for calls and puts.
Your gamma levels are currently derived from open interest — i.e. positioning as of yesterday's
close. This shows where *today's* classified premium is actually landing on the strike ladder, which
is a different and fresher quantity.
**Panel:** Overlay on the SPX/NDX 0DTE gamma-level chart (use `SPXW` for the 0DTE ladder).
**Integration note:** ~1,700–2,400 rows/day/ticker; aggregate by strike before rendering. Pairs with
`/spot-exposures/strike`, which splits gamma into `_oi` vs `_vol` vs `_bid`/`_ask` — the flow-based
gamma decomposition you cannot compute yourself.

---

### #10 — `/api/darkpool/{ticker}/price-levels` + `/api/stock/{ticker}/stock-volume-price-levels`
**Unlocks:** Support/resistance derived from **where size actually traded**, split lit vs off-lit,
rather than from gamma. Given your finding that gamma levels don't predict direction, a
volume-at-price map is an independent and better-founded source of levels.
**Panel:** Replaces or cross-checks the gamma-derived levels in the 0DTE panel; entry/stop placement
for swings.
**Integration note:** `stock-volume-price-levels` returns `{price, lit_vol, off_vol}` at very fine
granularity (22k rows for SPY) — bucket into ~0.25% bins before plotting.

---

### Honorable mentions (real, but lower EV for *this* dashboard)

- **`/api/congress/recent-trades`** — you asked for it, so here is the honest assessment: the STOCK
  Act permits up to **45 days** between transaction and disclosure, and live data confirms it
  (`transaction_date: 2026-07-02` → `filed_at_date: 2026-08-17`). By publication the information is
  stale for any swing horizon. Worth a low-frequency contextual panel, not a signal. `/late-reports`
  is arguably the more interesting endpoint (it flags who is filing *even later* than required).
- **`/api/market/fda-calendar`** — scheduled binary catalysts for biotech small caps. Genuinely
  additive to a black-swan scanner, and cheap (one daily call).
- **`/api/group-flow/mag7/greek-flow`** — NDX is ~40% Mag7; thematic-basket greek flow is a cleaner
  NDX driver than index-level GEX.
- **`/api/etfs/{ticker}/in-outflow`** — real creation/redemption money, independent of options.
- **`/api/stock/{ticker}/gex-levels`** — not new information (you compute this), but it deletes ~35
  lines of `gex_by_strike()` and matches UW's site exactly. Do it for maintenance, not for edge.
- **WebSocket `trading_halts`** — the highest-value streaming channel for a black-swan scanner, but
  Advanced-tier gated.
- **Deliberately deranked:** `/iv-rank`, `/volatility/*`, `/interpolated-iv`, `/historical-risk-reversal-skew`,
  `/nope`, `/max-pain`. These are all further derivatives of price and IV — precisely the family you
  have already measured as non-predictive. More of them will not help.

---

## 8. Concrete changes to `uw_client.py`

1. **Migrate off the deprecated endpoint.** `flow_alerts()` → `/api/option-trades/flow-alerts?ticker_symbol={T}`.
   Gains `all_opening_trades`, `has_sweep`, `has_floor`, `volume_oi_ratio` for free.
2. **Add `UW-CLIENT-API-ID: 100001`** to the header dict in `_get()`.
3. **Parse rate-limit headers in `_get()`** and expose a `usage()` helper; gate non-essential calls
   above 80% of `x-uw-token-req-limit`. Note that a `401` returns **no** `x-uw-*` headers — that is
   the reliable signal that the subscription lapsed, and it would have caught your earlier incident
   directly rather than via the auth-fail counter.
4. **Make the TTL per-endpoint**, not global: 10–15s for intraday flow, 45s default, 3600s+ for
   oi-change / short interest / insider / seasonality. You have ~200x headroom on quota.
5. **Guard `gex-levels` field-by-field.** `gamma_flip` is legitimately null for SPY. This is the same
   failure mode as `flip_dist_pct`; a single `if not gex: return None` will not catch it.
6. **Coerce every numeric field.** The API returns numbers as JSON strings throughout. `_f()` already
   handles this — route all new fields through it.
7. **Exclude multi-leg volume from directional flow** before computing `lean` in `summarize_flow()`.

---

## 9. Sources

- OpenAPI spec (YAML, 207 paths): `https://api.unusualwhales.com/api/openapi`
- Docs, markdown: `curl -H "Accept: text/plain" https://api.unusualwhales.com/docs`
- Per-operation docs: `https://api.unusualwhales.com/docs/operations/{operationId}`
- Agent skills: `https://unusualwhales.com/skill.md` and `https://unusualwhales.com/skills/*.md`
- Examples repo: `https://github.com/unusual-whales/api-examples`
- Live verification: 112 probe calls + 32 parameter-validation calls + 1 WebSocket handshake against your key, 2026-08-19.
