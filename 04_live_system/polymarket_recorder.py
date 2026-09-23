"""polymarket_recorder.py — record Polymarket's 5-minute crypto up-or-down markets against
live spot, every few seconds, forever. RECORDS ONLY. Places nothing.

THE CLAIM BEING MEASURED. A widely shared post says a bot "spots price errors before
humans notice" between BTC spot and Polymarket and turned $68 into $750,000. The testable
version: during a 5-minute "Bitcoin Up or Down" window, does the YES price on Polymarket's
order book lag the spot move -- so that with, say, 60 seconds left and BTC already +0.2%
against the window's open, YES can still be bought below the probability it deserves?

Polymarket resolves these on a Chainlink TWAP against the price at the START of the
window (market description), so the recorder logs, every TICK_S seconds, for BTC/ETH/SOL:
    the window (slug, start, end), seconds left, the YES token's best bid and ask and
    book depth at those levels, and spot from Coinbase and Binance.US.
After a window closes it reads the market's final outcome prices back from the API and
stores the resolution. `polymarket_score.py` then asks: at each (seconds-left, spot-vs-
open) cell, what was the YES ask, and what fraction resolved YES? The gap between the
two, minus the spread, is the whole "edge". Nothing here fits anything.

Runs detached (see launchd plist / nohup). ~5 requests every 3 seconds, all public,
no keys.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from idt import db as _db
from idt import paths

DB = paths.state("polymarket_5m.db")
TICK_S = 3
ASSETS = {"btc": "BTC-USD", "eth": "ETH-USD", "sol": "SOL-USD"}
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
CB = "https://api.exchange.coinbase.com/products/{p}/ticker"
BUS = "https://api.binance.us/api/v3/ticker/bookTicker?symbol={s}"


def _get(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": "idt-recorder/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def con():
    c = _db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS ticks (
        ts REAL, asset TEXT, window_start INTEGER, secs_left REAL,
        yes_bid REAL, yes_ask REAL, yes_bid_size REAL, yes_ask_size REAL, last_trade REAL,
        cb_bid REAL, cb_ask REAL, bus_bid REAL, bus_ask REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS windows (
        asset TEXT, window_start INTEGER, slug TEXT, yes_token TEXT, no_token TEXT,
        first_spot REAL, first_ts REAL, last_spot REAL, last_ts REAL,
        resolved TEXT, yes_final REAL, checked_at REAL,
        PRIMARY KEY (asset, window_start))""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_ticks ON ticks(asset, window_start)")
    return c


_MARKETS = {}


def market(asset, ws):
    key = (asset, ws)
    if key in _MARKETS:
        return _MARKETS[key]
    slug = f"{asset}-updown-5m-{ws}"
    try:
        rows = _get(f"{GAMMA}/markets?slug={urllib.parse.quote(slug)}")
    except Exception:                                         # noqa: BLE001
        return None
    if not rows:
        return None
    m = rows[0]
    try:
        ids = json.loads(m["clobTokenIds"])
    except (KeyError, ValueError, TypeError):
        return None
    _MARKETS[key] = {"slug": slug, "yes": ids[0], "no": ids[1] if len(ids) > 1 else None}
    return _MARKETS[key]


def book(token):
    b = _get(f"{CLOB}/book?token_id={token}")
    bids = [(float(x["price"]), float(x["size"])) for x in b.get("bids", [])]
    asks = [(float(x["price"]), float(x["size"])) for x in b.get("asks", [])]
    bb = max(bids, default=(None, None))
    ba = min(asks, default=(None, None))
    return bb[0], ba[0], bb[1], ba[1], (float(b["last_trade_price"]) if b.get("last_trade_price") else None)


def spot(asset):
    out = [None] * 4
    try:
        j = _get(CB.format(p=ASSETS[asset]))
        out[0], out[1] = float(j["bid"]), float(j["ask"])
    except Exception:                                         # noqa: BLE001
        pass
    try:
        j = _get(BUS.format(s=ASSETS[asset].replace("-", "")))
        out[2], out[3] = float(j["bidPrice"]), float(j["askPrice"])
    except Exception:                                         # noqa: BLE001
        pass
    return out


def resolve(c, now):
    """Read back outcomes for windows that ended > 3 minutes ago and are not yet resolved."""
    for r in c.execute("SELECT asset, window_start, slug FROM windows WHERE resolved IS NULL "
                       "AND window_start + 300 < ? AND (checked_at IS NULL OR checked_at < ?)",
                       (now - 180, now - 120)).fetchall():
        asset, ws, slug = r
        try:
            # `?slug=` alone EXCLUDES closed markets, so a finished window came back as an
            # empty list and `resolved` stayed NULL forever. Ask for closed ones explicitly.
            rows = _get(f"{GAMMA}/markets?slug={urllib.parse.quote(slug)}&closed=true")
            m = rows[0] if rows else {}
            prices = json.loads(m.get("outcomePrices") or "[]")
            yes_final = float(prices[0]) if prices else None
            closed = bool(m.get("closed")) or (yes_final is not None and yes_final in (0.0, 1.0))
            res = ("up" if yes_final >= 0.5 else "down") if (closed and yes_final is not None) else None
        except Exception:                                     # noqa: BLE001
            res, yes_final = None, None
        c.execute("UPDATE windows SET resolved=?, yes_final=?, checked_at=? WHERE asset=? AND window_start=?",
                  (res, yes_final, now, asset, ws))


def loop(max_secs=None):
    c = con()
    t0 = time.time()
    n = 0
    while max_secs is None or time.time() - t0 < max_secs:
        now = time.time()
        ws = int(now // 300) * 300
        for asset in ASSETS:
            m = market(asset, ws)
            if not m:
                continue
            try:
                yb, ya, ybs, yas, lt = book(m["yes"])
            except Exception:                                 # noqa: BLE001
                continue
            cbb, cba, bb, ba = spot(asset)
            mid = ((cbb + cba) / 2) if (cbb and cba) else ((bb + ba) / 2 if (bb and ba) else None)
            c.execute("INSERT INTO ticks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (now, asset, ws, ws + 300 - now, yb, ya, ybs, yas, lt, cbb, cba, bb, ba))
            c.execute("INSERT OR IGNORE INTO windows (asset, window_start, slug, yes_token, no_token, "
                      "first_spot, first_ts) VALUES (?,?,?,?,?,?,?)",
                      (asset, ws, m["slug"], m["yes"], m["no"], mid, now))
            if mid:
                c.execute("UPDATE windows SET last_spot=?, last_ts=? WHERE asset=? AND window_start=?",
                          (mid, now, asset, ws))
        if n % 20 == 0:
            resolve(c, now)
        c.commit()
        n += 1
        if n % 100 == 0:
            print(f"{datetime.now(timezone.utc):%H:%M:%S} ticks={n} windows="
                  f"{c.execute('SELECT COUNT(*) FROM windows').fetchone()[0]}", flush=True)
        time.sleep(max(0.0, TICK_S - (time.time() - now)))


if __name__ == "__main__":
    loop(float(sys.argv[1]) if len(sys.argv) > 1 else None)
