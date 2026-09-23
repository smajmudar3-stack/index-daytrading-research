"""kalshi_recorder.py — record the same event on two venues, side by side, and flag every
moment a YES on one plus a NO on the other costs less than a dollar after fees.
RECORDS ONLY. Places nothing.

THE CLAIM. "Kalshi and Polymarket misprice the same event by 2–5% and a bot can lock it
in." Public evidence is anecdotal (docs/briefs/prediction-markets.md): no measured dataset
exists, the same event can resolve on different sources, and a US person cannot open the
polymarket.com leg at all. So the measurement is the whole point, and it must be on the
SAME window, with both venues' fees, at the prices a taker would actually pay.

PAIRS RECORDED, every TICK_S seconds:
  15-minute Bitcoin up/down   Kalshi KXBTC15M-<window>  vs  Polymarket btc-updown-15m-<ts>
                              (same 15-minute window; Kalshi settles on a 60 s CF Benchmarks
                              average, Polymarket on a 60 s Chainlink TWAP — near, not equal)
  daily Bitcoin above-strike  Kalshi KXBTCD-<date>-T<strike>  vs  Polymarket
                              bitcoin-above-on-<date> strikes  (matched later by strike and
                              resolution time; recorded raw here)

Per tick: best YES bid/ask on each venue (Kalshi's book lists YES bids and NO bids, so the
YES ask is 1 − best NO bid), depth at those levels, and the two-legged "arb" costs:
    cost_A = yes_ask_kalshi + no_ask_poly  (buy YES on Kalshi, NO on Polymarket)
    cost_B = yes_ask_poly  + no_ask_kalshi
each with taker fees added: Kalshi 0.07·p(1−p) per contract, Polymarket 0.07·p(1−p) per
share (their crypto feeRate). An arb exists when a cost is < 1.00; the scorer counts how
often, how large, and how deep. Public endpoints, no keys, ~4 requests a tick.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from idt import db as _db
from idt import paths

DB = paths.state("kalshi_pairs.db")
TICK_S = 5
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
FEE_K = 0.07      # Kalshi taker: fee = 0.07 * p * (1-p) per contract
FEE_P = 0.07      # Polymarket crypto taker feeRate, same shape


def _get(url, timeout=6):
    req = urllib.request.Request(url, headers={"User-Agent": "idt-recorder/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def fee(p, rate):
    return rate * p * (1 - p) if p is not None else None


def con():
    c = _db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS pairs (
        ts REAL, kind TEXT, window_end TEXT, p_end TEXT, strike REAL, k_ticker TEXT, p_slug TEXT,
        k_yes_bid REAL, k_yes_ask REAL, k_yes_bid_sz REAL, k_yes_ask_sz REAL,
        p_yes_bid REAL, p_yes_ask REAL, p_yes_bid_sz REAL, p_yes_ask_sz REAL,
        cost_a REAL, cost_b REAL, cost_a_fee REAL, cost_b_fee REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS resolutions (
        kind TEXT, window_end TEXT, strike REAL, k_ticker TEXT, p_slug TEXT,
        k_result TEXT, p_yes_final REAL, checked_at REAL, PRIMARY KEY (kind, window_end, strike))""")
    return c


def kalshi_book(ticker):
    b = _get(f"{KALSHI}/markets/{ticker}/orderbook?depth=5").get("orderbook_fp") or {}
    yes = [(float(p), float(q)) for p, q in (b.get("yes_dollars") or [])]
    no = [(float(p), float(q)) for p, q in (b.get("no_dollars") or [])]
    yb = max(yes, default=(None, None))
    nb = max(no, default=(None, None))
    ya = (round(1 - nb[0], 4) if nb[0] is not None else None)
    return yb[0], ya, yb[1], nb[1]


def poly_book(token):
    b = _get(f"{CLOB}/book?token_id={token}")
    bids = [(float(x["price"]), float(x["size"])) for x in b.get("bids", [])]
    asks = [(float(x["price"]), float(x["size"])) for x in b.get("asks", [])]
    bb = max(bids, default=(None, None)); ba = min(asks, default=(None, None))
    return bb[0], ba[0], bb[1], ba[1]


_PM = {}


def poly_market(slug):
    if slug in _PM:
        return _PM[slug]
    try:
        rows = _get(f"{GAMMA}/markets?slug={urllib.parse.quote(slug)}")
        m = rows[0] if rows else None
        ids = json.loads(m["clobTokenIds"]) if m else None
        _PM[slug] = {"yes": ids[0], "end": m.get("endDate")} if ids else None
    except Exception:                                         # noqa: BLE001
        _PM[slug] = None
    return _PM[slug]


def kalshi_open(series):
    try:
        return _get(f"{KALSHI}/markets?limit=50&status=open&series_ticker={series}").get("markets") or []
    except Exception:                                         # noqa: BLE001
        return []


def record(c, now, kind, window_end, p_end, strike, k_ticker, p_slug, p_token):
    try:
        kyb, kya, kybs, kyas = kalshi_book(k_ticker)
        pyb, pya, pybs, pyas = poly_book(p_token)
    except Exception:                                         # noqa: BLE001
        return
    p_no_ask = (1 - pyb) if pyb is not None else None          # buying NO on Polymarket = selling YES at bid
    k_no_ask = (1 - kyb) if kyb is not None else None
    cost_a = (kya + p_no_ask) if (kya is not None and p_no_ask is not None) else None
    cost_b = (pya + k_no_ask) if (pya is not None and k_no_ask is not None) else None
    cost_a_fee = (cost_a + fee(kya, FEE_K) + fee(p_no_ask, FEE_P)) if cost_a is not None else None
    cost_b_fee = (cost_b + fee(pya, FEE_P) + fee(k_no_ask, FEE_K)) if cost_b is not None else None
    c.execute("INSERT INTO pairs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (now, kind, window_end, p_end, strike, k_ticker, p_slug, kyb, kya, kybs, kyas, pyb, pya, pybs, pyas,
               cost_a, cost_b, cost_a_fee, cost_b_fee))


def loop(max_secs=None):
    c = con()
    t0, n = time.time(), 0
    daily_pairs, daily_at = [], 0.0
    while max_secs is None or time.time() - t0 < max_secs:
        now = time.time()
        # 15-minute window: the Kalshi contract whose close_time is the current window's end
        ws = int(now // 900) * 900
        end_iso = datetime.fromtimestamp(ws + 900, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        k15 = [m for m in kalshi_open("KXBTC15M") if m.get("close_time") == end_iso]
        pm = poly_market(f"btc-updown-15m-{ws}")
        if k15 and pm:
            record(c, now, "15m", end_iso, pm.get("end"), k15[0].get("floor_strike"), k15[0]["ticker"], f"btc-updown-15m-{ws}", pm["yes"])
        # daily strikes, refreshed every 10 minutes
        if now - daily_at > 600:
            daily_pairs = []
            kd = kalshi_open("KXBTCD")
            for m in kd:
                ct = m.get("close_time") or ""
                strike = m.get("floor_strike")
                if not strike or not ct:
                    continue
                day = datetime.strptime(ct[:10], "%Y-%m-%d")
                ev_slug = f"bitcoin-above-on-{day.strftime('%B').lower()}-{day.day}-{day.year}"
                try:
                    ev = _get(f"{GAMMA}/events?slug={ev_slug}")
                    mkts = (ev[0].get("markets") or []) if ev else []
                except Exception:                             # noqa: BLE001
                    mkts = []
                # nearest Polymarket strike (their strikes are round thousands; Kalshi's end in .99)
                best = None
                for pmk in mkts:
                    try:
                        s = float(str(pmk.get("groupItemTitle") or "").replace(",", "").replace("$", "").replace("k", "000"))
                    except ValueError:
                        continue
                    if best is None or abs(s - strike) < abs(best[0] - strike):
                        best = (s, pmk)
                # EXACT STRIKES ONLY. Kalshi "T85999.99" means above 85,999.99, i.e. at or above
                # 86,000, which is Polymarket's "above 86k". A 300-dollar tolerance paired
                # 86,249.99 with 86k and flagged a 5% "arb" between two different contracts.
                if best and abs(best[0] - round(strike + 0.01)) <= 1.0:
                    try:
                        ids = json.loads(best[1]["clobTokenIds"])
                        daily_pairs.append((ct, best[1].get("endDate"), strike, m["ticker"], best[1]["slug"], ids[0]))
                    except (KeyError, ValueError, TypeError):
                        continue
            daily_at = now
        for ct, pe, strike, kt, ps, tok in daily_pairs:
            record(c, now, "daily", ct, pe, strike, kt, ps, tok)
        c.commit()
        n += 1
        if n % 60 == 0:
            k = c.execute("SELECT COUNT(*), SUM(cost_a_fee < 1 OR cost_b_fee < 1), MIN(cost_a_fee), MIN(cost_b_fee) FROM pairs").fetchone()
            print(f"{datetime.now(timezone.utc):%H:%M:%S} ticks={n} rows={k[0]} arb_after_fee={k[1] or 0} "
                  f"min_cost={min(x for x in k[2:] if x is not None) if any(k[2:]) else None}", flush=True)
        time.sleep(max(0.0, TICK_S - (time.time() - now)))


if __name__ == "__main__":
    loop(float(sys.argv[1]) if len(sys.argv) > 1 else None)
