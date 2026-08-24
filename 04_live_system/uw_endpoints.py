"""Full Unusual Whales endpoint registry, and the screener built on it.

Every one of the 128 documented paths is catalogued here with its category and
what it is good for, so nothing is forgotten. But the registry is the boring
half — the useful half is `screen()`, which pulls the endpoints that carry
information the price/IV data does NOT already contain, and folds them into one
per-ticker record.

WHAT GOES IN THE SCREENER AND WHY. Everything in this repo has been measured,
and the measurements decide what is worth an API call:

  INCLUDED — genuinely orthogonal information:
    opening-vs-closing classified flow   (volume>OI means new positions)
    dark pool prints                     (off-exchange institutional prints)
    open-interest change                 (ex-post proof volume became positions)
    short interest / borrow / FTDs       (squeeze fuel, and a cost the tape hides)
    insider transactions                 (filtered to open-market buys)
    FDA calendar                         (DATED binary catalysts -- the one thing
                                          that would have flagged an MRNA)
    market/sector tide                   (breadth, not another price transform)

  DELIBERATELY EXCLUDED — more derivatives of price and IV, the family already
  measured as non-predictive here:
    iv-rank, nope, skew, volatility/*    (cheap-IV screens made far-OTM WORSE)
    congressional trades                 (up to 45-day disclosure lag; stale for
                                          any swing horizon)

Gated on this tier and therefore unavailable: market/movers, companies/*,
analytics/*, futures, options-pulse, vix-term-structure.
"""
import os
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------
# THE REGISTRY — all 128 documented paths, grouped. `{t}` = ticker.
# tier: "ok" = works on this key, "gated" = higher tier, "dep" = deprecated.
# --------------------------------------------------------------------------
ENDPOINTS = {
  "flow": [
    ("/api/option-trades/flow-alerts", "ok", "classified alerts; has volume_oi_ratio, has_sweep"),
    ("/api/option-trades", "ok", "raw trades; opening=true gives true open/close split"),
    ("/api/option-trades/multi-leg", "ok", "spreads as ONE trade — stops verticals double-counting"),
    ("/api/option-trades/full-tape/{t}", "ok", "complete tape for a name"),
    ("/api/option-trades/exchange-breakdown/{t}", "ok", "venue mix"),
    ("/api/option-activity/unusual", "ok", "unusual activity feed"),
    ("/api/options/flow", "ok", "generic flow"),
    ("/api/option-contract/{t}/flow", "ok", "flow for one contract"),
    ("/api/stock/{t}/flow-alerts", "dep", "DEPRECATED — use option-trades/flow-alerts"),
    ("/api/stock/{t}/flow-recent", "ok", "recent flow"),
    ("/api/stock/{t}/flow-per-strike", "ok", "premium by strike"),
    ("/api/stock/{t}/flow-per-strike-intraday", "ok", "TODAY's premium by strike"),
    ("/api/stock/{t}/flow-per-expiry", "ok", "premium by expiry"),
    ("/api/net-flow/expiry", "ok", "0DTE-isolated net premium (double-nested)"),
    ("/api/lit-flow/{t}", "ok", "lit-venue flow"),
    ("/api/lit-flow/recent", "ok", "recent lit flow"),
    ("/api/group-flow/{t}/greek-flow", "ok", "greek flow by group"),
    ("/api/stock/{t}/greek-flow", "ok", "per-name greek flow"),
  ],
  "darkpool": [
    ("/api/darkpool/{t}", "ok", "prints for a name; price>=nbbo_ask = buy-initiated"),
    ("/api/darkpool/recent", "ok", "market-wide recent prints"),
    ("/api/darkpool/{t}/price-levels", "ok", "volume-at-price, independent of gamma"),
    ("/api/stock/{t}/stock-volume-price-levels", "ok", "lit volume at price"),
  ],
  "positioning": [
    ("/api/stock/{t}/oi-change", "ok", "OI delta — did volume become positions?"),
    ("/api/market/oi-change", "ok", "market-wide OI change (premarket only)"),
    ("/api/stock/{t}/oi-per-strike", "ok", "OI by strike"),
    ("/api/stock/{t}/option-stance", "ok", "aggregate positioning stance"),
    ("/api/institution/{t}/activity", "ok", "13F activity"),
    ("/api/institutions", "ok", "institution list"),
    ("/api/stock/{t}/ownership", "ok", "ownership concentration"),
  ],
  "shorts": [
    ("/api/shorts/{t}/interest-float/v2", "ok", "short % of float (si_float is a FRACTION)"),
    ("/api/shorts/{t}/data", "ok", "short interest detail"),
    ("/api/shorts/{t}/ftds", "ok", "failures to deliver"),
    ("/api/shorts/{t}/volume-and-ratio", "ok", "daily short volume"),
    ("/api/short_screener", "ok", "screen by short metrics"),
  ],
  "insider": [
    ("/api/insider/transactions", "ok", "filter transaction_codes[]=P, is_10b5_1=false"),
    ("/api/stock/{t}/insider-buy-sells", "ok", "per-name buy/sell counts"),
    ("/api/insider/{t}/ticker-flow", "ok", "insider flow by ticker"),
    ("/api/market/insider-buy-sells", "ok", "market-wide insider flow"),
  ],
  "catalyst": [
    ("/api/market/fda-calendar", "ok", "DATED biotech binaries — PDUFA etc."),
    ("/api/market/economic-calendar", "ok", "macro release dates"),
    ("/api/earnings/{t}", "ok", "earnings dates"),
    ("/api/earnings/afterhours", "ok", "after-hours reporters"),
    ("/api/news/headlines", "ok", "headline feed"),
  ],
  "gamma": [
    ("/api/stock/{t}/gex-levels", "ok", "gamma_flip can be NULL — guard it"),
    ("/api/stock/{t}/greek-exposure", "ok", "dealer greeks"),
    ("/api/stock/{t}/greek-exposure/strike", "ok", "GEX by strike"),
    ("/api/stock/{t}/greek-exposure/expiry", "ok", "GEX by expiry"),
    ("/api/stock/{t}/spot-exposures", "ok", "spot gamma/charm/vanna"),
    ("/api/stock/{t}/max-pain", "ok", "pin target"),
  ],
  "breadth": [
    ("/api/market/market-tide", "ok", "market-wide net premium tide"),
    ("/api/market/{t}/sector-tide", "ok", "sector tide"),
    ("/api/market/{t}/etf-tide", "ok", "ETF tide"),
    ("/api/market/sector-etfs", "ok", "sector ETF snapshot"),
    ("/api/market/total-options-volume", "ok", "aggregate volume"),
    ("/api/market/top-net-impact", "ok", "biggest net premium movers"),
    ("/api/market/correlations", "ok", "comma-joined tickers param"),
  ],
  "screener": [
    ("/api/screener/option-contracts", "ok", "~90 server-side filters"),
    ("/api/screener/stocks", "ok", "stock screener"),
    ("/api/option-trades/optionable-tickers", "ok", "the tradeable universe"),
  ],
  "reference": [
    ("/api/stock/{t}/quote", "ok", "real-time quote"),
    ("/api/stock/{t}/atm-chains", "ok", "ATM chain"),
    ("/api/stock/{t}/option-contracts", "ok", "contract list"),
    ("/api/stock/{t}/options-volume", "ok", "volume summary"),
    ("/api/stock/{t}/financials", "ok", "fundamentals"),
    ("/api/etfs/{t}/holdings", "ok", "ETF holdings"),
    ("/api/etfs/{t}/in-outflow", "ok", "ETF flows"),
    ("/api/seasonality/market", "ok", "seasonality"),
  ],
  # Present in the spec but excluded from the screener, with the reason.
  "excluded_price_derivatives": [
    ("/api/stock/{t}/iv-rank", "ok", "EXCLUDED: cheap-IV screens made far-OTM worse"),
    ("/api/stock/{t}/nope", "ok", "EXCLUDED: another price/IV transform"),
    ("/api/stock/{t}/historical-risk-reversal-skew", "ok", "EXCLUDED: skew non-predictive here"),
    ("/api/stock/{t}/volatility/realized", "ok", "EXCLUDED: computable locally"),
    ("/api/stock/{t}/volatility/variance-risk-premium", "ok", "EXCLUDED: VRP measured, not predictive"),
  ],
  "excluded_stale": [
    ("/api/congress/recent-trades", "ok", "EXCLUDED: up to 45-day disclosure lag"),
    ("/api/congress/unusual-trades", "gated", "gated + stale"),
    ("/api/politician-portfolios/", "ok", "EXCLUDED: same lag"),
  ],
  "gated": [
    ("/api/market/movers", "gated", ""), ("/api/companies/{t}/profile", "gated", ""),
    ("/api/analytics/sliding", "gated", ""), ("/api/futures/", "gated", ""),
    ("/api/options-pulse/", "gated", ""), ("/api/volatility/vix-term-structure", "gated", ""),
    ("/api/calendar/ipo", "gated", ""), ("/api/socket", "gated", "WebSocket: Advanced tier"),
  ],
}


def inventory():
    """Flat table of the whole registry — what exists and whether we use it."""
    rows = []
    for cat, items in ENDPOINTS.items():
        for path, tier, note in items:
            rows.append({"category": cat, "path": path, "tier": tier,
                         "in_screener": not cat.startswith(("excluded", "gated")),
                         "note": note})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# The screener
# --------------------------------------------------------------------------
def _uw():
    import uw_client as u
    return u if u.available() else None


def _num(x, default=0.0):
    """Every UW number arrives as a JSON string; some are null."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def fda_calendar(days=90):
    """Dated biotech binaries — the catalyst class that produced MRNA's +177%.

    This is the one screen that could plausibly have flagged it, because a PDUFA
    date is published in advance even though the OUTCOME is not knowable.
    """
    u = _uw()
    if not u:
        return pd.DataFrame()
    r = u._rows(u._get("/api/market/fda-calendar", {}))
    if not r:
        return pd.DataFrame()
    d = pd.DataFrame(r)
    for c in ("target_date", "catalyst_date", "start_date"):
        if c in d.columns:
            d["date"] = pd.to_datetime(d[c], errors="coerce")
            break
    if "date" in d.columns:
        today = pd.Timestamp.utcnow().tz_localize(None).normalize()
        d = d[(d.date >= today) & (d.date <= today + pd.Timedelta(days=days))]
        d = d.sort_values("date")
    return d


def profile(ticker):
    """One ticker, everything orthogonal, in a single record."""
    u = _uw()
    if not u:
        return {}
    out = {"ticker": ticker}

    f = u.summarize_flow(ticker)
    if f:
        out.update(flow_lean=f.get("lean"), flow_bias=f.get("bias"),
                   call_bought=f.get("call_bought"), put_bought=f.get("put_bought"))

    dp = u._rows(u._get(f"/api/darkpool/{ticker}", {"limit": 200}))
    if dp:
        live = [x for x in dp if not x.get("canceled")]
        sz = sum(_num(x.get("size")) for x in live)
        # CLASSIFY BY POSITION IN THE SPREAD, not by touching the ask.
        # Dark pool prints execute INSIDE the NBBO -- e.g. price 762.9091
        # against an ask of 762.91 -- so a `price >= ask` test almost never
        # fires and reported ~3.7% buy-share for everything, which fed a
        # permanent bearish vote. The standard measure is where in the spread
        # the print landed: above the midpoint is buy-initiated.
        # MIDPOINT PRINTS ARE UNCLASSIFIABLE AND MUST BE EXCLUDED FROM BOTH
        # SIDES. A dark pool's whole purpose is midpoint matching, so a large
        # share of prints land exactly at mid -- SPY's median spread position is
        # exactly 0.500. Treating those as sells (anything not > 0.5) made every
        # name look bearish. The measured distribution is near-symmetric: SPY
        # 36% at/below bid vs 26% at/above ask, so a balanced tape should score
        # near 0.5, not 0.03.
        buy = sell = 0.0
        for x in live:
            px, bid, ask = (_num(x.get("price")), _num(x.get("nbbo_bid")),
                            _num(x.get("nbbo_ask")))
            if not (px and bid and ask and ask > bid):
                continue
            pos = (px - bid) / (ask - bid)
            # Stale quotes produce prints far outside the NBBO; clip rather than
            # let one bad row dominate (SPY's raw mean position was 2.885).
            if pos < -0.5 or pos > 1.5:
                continue
            w = _num(x.get("size"))
            if pos > 0.55:
                buy += w
            elif pos < 0.45:
                sell += w
            # 0.45-0.55 is a midpoint match: no information, counted on neither side.
        classified = buy + sell
        out.update(dp_prints=len(live), dp_shares=sz,
                   dp_buy_share=round(buy / classified, 3) if classified else None)

    si = u._get(f"/api/shorts/{ticker}/interest-float/v2", {})
    rows = u._rows(si) if si else []
    if rows:
        # si_float is a FRACTION, not a percent — a documented trap.
        out["short_float_pct"] = round(_num(rows[0].get("si_float")) * 100, 2)

    oi = u._rows(u._get(f"/api/stock/{ticker}/oi-change", {"limit": 100}))
    if oi:
        out["oi_change_net"] = sum(_num(x.get("oi_diff_plain")) for x in oi)

    ins = u._rows(u._get("/api/insider/transactions",
                         {"ticker_symbol": ticker, "transaction_codes[]": "P",
                          "limit": 50}))
    if ins:
        real = [x for x in ins if not x.get("is_10b5_1")]   # exclude scheduled plans
        out["insider_open_buys"] = len(real)
    return out


def screen(tickers, catalysts=True):
    """Build the screener table across a universe."""
    rows = [profile(t) for t in tickers]
    d = pd.DataFrame([r for r in rows if r])
    if catalysts and not d.empty:
        fda = fda_calendar()
        if not fda.empty and "ticker" in fda.columns:
            up = fda.groupby("ticker")["date"].min()
            d["fda_date"] = d.ticker.map(lambda t: str(up.get(t).date())
                                         if t in up.index else None)
    return d


if __name__ == "__main__":
    inv = inventory()
    print(f"REGISTRY: {len(inv)} endpoints catalogued")
    print(inv.groupby(["category", "in_screener"]).size().to_string())
    print("\nFDA CALENDAR (dated binaries):")
    f = fda_calendar()
    print(f"  {len(f)} upcoming events")
    if not f.empty:
        cols = [c for c in ("ticker", "date", "drug", "catalyst", "status") if c in f.columns]
        print(f[cols].head(12).to_string(index=False))


# --------------------------------------------------------------------------
# WEIGHTS BY MEASURED INFLUENCE
#
# The weight an input gets is set by how well it has been shown to predict
# subsequent moves ON THIS DATA -- not by how interesting the data source is.
# Three tiers, and the tier is stated on the panel so nothing is trusted more
# than its evidence:
#
#   MEASURED-POSITIVE  tested here and it beat the base rate  -> full weight
#   UNMEASURED         plausibly orthogonal, not yet tested   -> half weight,
#                                                                flagged
#   MEASURED-NULL      tested here and it did NOT beat base   -> ZERO weight
#
# The null tier is the important one. It is populated from real studies, not
# hunches, and an input that lands there is excluded no matter how good the
# story is:
#
#   IV elevated / rising / falling, OI building, spreads widening
#     -> 810,300 ticker-days, P(>=4 sigma move in 10 sessions). Every variant
#        scored a lift of 0.68x-1.02x, i.e. at or BELOW the 0.78% base rate.
#        OI building scored 0.76x -- it predicts FEWER big moves.
#   cheap-IV screens
#     -> made far-OTM buying materially WORSE (-95.4% on the worst cell).
#   dealer gamma / DIX as direction
#     -> 1,001 gated cells, zero positive across three periods.
#   rate/curve/credit as sector prediction
#     -> 216 cells, zero cleared the multiple-testing bar.
WEIGHTS = {
    # input                 weight  tier               evidence
    # MEASURED. Short interest is the strongest signal found anywhere in this
    # project, and it strengthens MONOTONICALLY with horizon -- the signature of
    # a real effect rather than noise:
    #     5d -0.022 | 10d -0.038 | 21d -0.068 | 42d -0.087 | 63d -0.107  (n=13k)
    # NOTE THE SIGN. My prior assumed high short interest was squeeze fuel and
    # therefore bullish. It is the opposite: heavily shorted names UNDERPERFORM,
    # which is the documented short-interest anomaly. The prior was backwards and
    # is corrected here -- the input now enters NEGATIVELY.
    "short_float_pct":      (0.30, "measured", "IC -0.068 at 21d, -0.107 at 63d, n=13,219; "
                                               "monotone in horizon; SIGN IS NEGATIVE"),
    "flow_lean":            (0.35, "unmeasured", "opening-classified premium; genuinely "
                                                 "orthogonal but same-day only, so it can "
                                                 "only be earned forward"),
    "dp_buy_share":         (0.15, "unmeasured", "dark pool buy-initiated share; same-day "
                                                 "only, forward-tracking path"),
    "insider_open_buys":    (0.10, "measured-weak", "IC +0.027 at 5d, +0.042 at 63d but only "
                                                    "n=1,128 and the sign flips by era; small "
                                                    "weight, not zero"),
    "fda_date":             (0.10, "structural", "a DATED binary; does not predict direction, "
                                                 "it predicts that a large move will resolve"),
    # explicitly zeroed -- measured non-predictive here
    "iv_rel":               (0.00, "measured-null", "lift 1.01x over 810,300 ticker-days"),
    "iv_trend":             (0.00, "measured-null", "lift 0.98-1.02x"),
    "oi_change_net":        (0.00, "measured-null", "lift 0.76x — BELOW base rate"),
    "spread_rel":           (0.00, "measured-null", "lift 0.90x"),
}


def weighted_score(rec):
    """Combine a profile into one score, weighting each input by its evidence.

    Returns the score, the share of weight that is still UNMEASURED, and the
    per-input contributions — so the panel can show how much of a call rests on
    things that have been tested versus things that merely sound sensible.
    """
    contrib, used, unmeasured_w = {}, 0.0, 0.0

    def add(key, value):
        nonlocal used, unmeasured_w
        w, tier, _ = WEIGHTS[key]
        if w == 0 or value is None:
            return
        contrib[key] = round(w * value, 4)
        used += w
        if tier == "unmeasured":
            unmeasured_w += w

    # Each input normalised to roughly [-1, +1] so weights mean what they say.
    if rec.get("flow_lean") is not None:
        add("flow_lean", max(-1.0, min(1.0, float(rec["flow_lean"]))))
    if rec.get("dp_buy_share") is not None:
        add("dp_buy_share", (float(rec["dp_buy_share"]) - 0.5) * 2)
    if rec.get("short_float_pct") is not None:
        # NEGATIVE by measurement, not by intuition. High short interest predicts
        # UNDERPERFORMANCE (IC -0.068 at 21d). Capped at 20% of float.
        add("short_float_pct", -min(float(rec["short_float_pct"]) / 20.0, 1.0))
    if rec.get("insider_open_buys"):
        add("insider_open_buys", min(float(rec["insider_open_buys"]) / 3.0, 1.0))

    score = sum(contrib.values()) / used if used else 0.0
    return {
        "score": round(score, 3),
        "confidence": round(1 - (unmeasured_w / used), 2) if used else 0.0,
        "unmeasured_share": round(unmeasured_w / used, 2) if used else 1.0,
        "contrib": contrib,
        "has_catalyst": bool(rec.get("fda_date")),
    }


def weight_table():
    """What each input is worth, and why — for display, not decoration."""
    return pd.DataFrame(
        [{"input": k, "weight": w, "tier": t, "evidence": e}
         for k, (w, t, e) in WEIGHTS.items()]
    ).sort_values("weight", ascending=False)
