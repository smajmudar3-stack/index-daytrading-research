"""pumpfun_recorder.py — every pump.fun launch at BIRTH, with everything the curve and the
creator expose, re-priced every minute for its first half hour and then more slowly for a
day. RECORDS ONLY. Buys nothing. The second memecoin recorder: the first
(`memecoin_recorder.py`, DexScreener's profile feed) sees a token minutes after launch and
re-prices it every ~20 minutes; this one sees it seconds after the mint, which is where
Sholo trades on GMGN and where every factor he can see on that screen is set.

WHAT IS RECORDED at first sight (pump.fun's public frontend API, `/coins` sorted by
creation; ~40 new mints a minute):
  mint, name, symbol, creator wallet, created_timestamp, seen_at (our latency),
  twitter / telegram / website present, reply_count, description length,
  virtual and real SOL reserves (the curve's state), usd_market_cap, complete (graduated),
  king_of_the_hill_timestamp, last_trade_timestamp,
  and the CREATOR's history as this recorder has seen it: how many mints by this wallet
  before, and how those ended (the one factor the literature says matters: deployer
  wallets that snipe their own launches).
WHAT IS RE-RECORDED: the bonding curve's own account, read straight from the Solana RPC
(`getMultipleAccounts`, 100 curves a call): virtual and real reserves, supply, the
`complete` flag — so price in SOL per token and the curve's fill are exact, and the read
cannot be rate-limited the way pump.fun's per-coin endpoint was (it returned 404 for every
mint on 2026-10-06 and the feed 429'd at 20-second polling). Marks at +1, +2, +3, +5, +10,
+15, +30 min, then +1, +2, +6, +12, +24 h; DexScreener's pair (price, liquidity, buys and
sells per window, volume, boosts) joined from +15 min once a pair exists.
`05_studies/memecoin_factors.py --pumpfun` scores it. Public endpoints, no key.
"""
import base64
import json
import struct
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from idt import db as _db
from idt import paths

DB = paths.state("pumpfun.db")
POLL_S = 30
PF = "https://frontend-api-v3.pump.fun"
RPC = "https://api.mainnet-beta.solana.com"
DS_TOKENS = "https://api.dexscreener.com/latest/dex/tokens/{addr}"
MARK_SCHEDULE = [60, 120, 180, 300, 600, 900, 1800, 3600, 7200, 21600, 43200, 86400]
DS_FROM_INDEX = 5                                            # DexScreener joined from the +15 min mark
MAX_TRACK = 86400 + 3600


def _get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (idt-recorder)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def con():
    c = _db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS mints (
        mint TEXT PRIMARY KEY, name TEXT, symbol TEXT, creator TEXT, created REAL, seen REAL,
        has_twitter INTEGER, has_telegram INTEGER, has_website INTEGER, desc_len INTEGER, reply0 INTEGER,
        vsol0 REAL, rsol0 REAL, mcap0 REAL, complete0 INTEGER, last_trade0 REAL,
        creator_prior_mints INTEGER, creator_prior_graduated INTEGER, creator_prior_dead INTEGER,
        curve TEXT, sol_usd0 REAL, vtok0 REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS marks (
        mint TEXT, ts REAL, age_s REAL, price_sol REAL, mcap_sol REAL, vsol REAL, rsol REAL, vtok REAL, complete INTEGER,
        ds_price REAL, ds_liq REAL, ds_fdv REAL, buys_m5 INTEGER, sells_m5 INTEGER, buys_h1 INTEGER, sells_h1 INTEGER,
        vol_m5 REAL, vol_h1 REAL, vol_h24 REAL, chg_m5 REAL, chg_h1 REAL, boost REAL)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_pm ON marks(mint, ts)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_cr ON mints(creator)")
    return c


def creator_history(c, creator, before):
    rows = c.execute("SELECT mint FROM mints WHERE creator=? AND created < ?", (creator, before)).fetchall()
    n = len(rows)
    grad = dead = 0
    for (mint,) in rows:
        last = c.execute("SELECT complete, rsol FROM marks WHERE mint=? AND price_sol IS NOT NULL ORDER BY ts DESC LIMIT 1", (mint,)).fetchone()
        if last:
            if last[0]:
                grad += 1
            elif last[1] is not None and last[1] < 2e9:          # under 2 real SOL on the curve: dead
                dead += 1
    return n, grad, dead


def rpc_curves(addresses):
    """{curve address: (vtok, vsol, rtok, rsol, supply, complete)} from one getMultipleAccounts
    call (100 max). The pump.fun bonding-curve account: 8-byte discriminator, five u64, one bool."""
    out = {}
    if not addresses:
        return out
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getMultipleAccounts",
                       "params": [addresses, {"encoding": "base64"}]}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=12) as r:
        res = json.loads(r.read().decode()).get("result", {}).get("value") or []
    for addr, acc in zip(addresses, res, strict=False):
        if not acc or not acc.get("data"):
            out[addr] = None
            continue
        raw = base64.b64decode(acc["data"][0])
        if len(raw) < 49:
            out[addr] = None
            continue
        vtok, vsol, rtok, rsol, supply = struct.unpack_from("<QQQQQ", raw, 8)
        out[addr] = (vtok, vsol, rtok, rsol, supply, int(raw[48]))
    return out


def ds_pair(mint):
    try:
        d = _get(DS_TOKENS.format(addr=mint))
    except Exception:                                         # noqa: BLE001
        return {}
    pairs = [p for p in (d.get("pairs") or []) if p.get("priceUsd")]
    if not pairs:
        return {}
    pairs.sort(key=lambda p: -float(((p.get("liquidity") or {}).get("usd") or 0)))
    p = pairs[0]
    tx, vol, chg = p.get("txns") or {}, p.get("volume") or {}, p.get("priceChange") or {}
    return {"ds_price": float(p["priceUsd"]), "ds_liq": float((p.get("liquidity") or {}).get("usd") or 0),
            "ds_fdv": p.get("fdv"), "buys_m5": (tx.get("m5") or {}).get("buys"), "sells_m5": (tx.get("m5") or {}).get("sells"),
            "buys_h1": (tx.get("h1") or {}).get("buys"), "sells_h1": (tx.get("h1") or {}).get("sells"),
            "vol_m5": vol.get("m5"), "vol_h1": vol.get("h1"), "vol_h24": vol.get("h24"),
            "chg_m5": chg.get("m5"), "chg_h1": chg.get("h1"), "boost": (p.get("boosts") or {}).get("active")}


def mark_batch(c, items, now):
    """items: [(mint, curve, created, with_ds)]. One RPC call for the curves, then DexScreener
    for the ones that asked for it."""
    curves = rpc_curves([it[1] for it in items])
    for mint, curve, created, with_ds in items:
        acc = curves.get(curve)
        if not acc:
            c.execute("INSERT INTO marks (mint, ts, age_s) VALUES (?,?,?)", (mint, now, now - created))
            continue
        vtok, vsol, rtok, rsol, supply, complete = acc
        price = (vsol / 1e9) / (vtok / 1e6) if vtok else None
        mcap = price * supply / 1e6 if price else None
        ds = ds_pair(mint) if with_ds else {}
        c.execute("INSERT INTO marks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (mint, now, now - created, price, mcap, vsol, rsol, vtok, complete,
                   ds.get("ds_price"), ds.get("ds_liq"), ds.get("ds_fdv"), ds.get("buys_m5"), ds.get("sells_m5"),
                   ds.get("buys_h1"), ds.get("sells_h1"), ds.get("vol_m5"), ds.get("vol_h1"), ds.get("vol_h24"),
                   ds.get("chg_m5"), ds.get("chg_h1"), ds.get("boost")))


def loop(max_secs=None):
    c = con()
    t0, n = time.time(), 0
    due = {}                                                   # mint -> (curve, created, index into MARK_SCHEDULE)
    backoff = 0.0
    while max_secs is None or time.time() - t0 < max_secs:
        now = time.time()
        feed = []
        if now >= backoff:
            try:
                feed = _get(f"{PF}/coins?offset=0&limit=50&sort=created_timestamp&order=DESC&includeNsfw=false")
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    backoff = now + 120                       # the feed throttles; wait two minutes, keep marking
            except Exception:                                 # noqa: BLE001
                pass
        new = 0
        for k in feed or []:
            mint, curve = k.get("mint"), k.get("bonding_curve")
            if not mint or not curve or c.execute("SELECT 1 FROM mints WHERE mint=?", (mint,)).fetchone():
                continue
            created = (k.get("created_timestamp") or 0) / 1000.0
            cp, cg, cd = creator_history(c, k.get("creator"), created)
            sol_usd = (k.get("usd_market_cap") / k.get("market_cap")) if k.get("market_cap") else None
            c.execute("INSERT OR IGNORE INTO mints VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (mint, k.get("name"), k.get("symbol"), k.get("creator"), created, now,
                       int(bool(k.get("twitter"))), int(bool(k.get("telegram"))), int(bool(k.get("website"))),
                       len(k.get("description") or ""), k.get("reply_count"), k.get("virtual_sol_reserves"),
                       k.get("real_sol_reserves"), k.get("usd_market_cap"), int(bool(k.get("complete"))),
                       (k.get("last_trade_timestamp") or 0) / 1000.0, cp, cg, cd, curve, sol_usd, k.get("virtual_token_reserves")))
            due[mint] = (curve, created, 0)
            new += 1
        # marks that are due, in RPC batches of 100
        batch = []
        for mint, (curve, created, i) in list(due.items()):
            if i >= len(MARK_SCHEDULE) or now - created > MAX_TRACK:
                del due[mint]
                continue
            if now - created >= MARK_SCHEDULE[i]:
                batch.append((mint, curve, created, i >= DS_FROM_INDEX))
                due[mint] = (curve, created, i + 1)
        for k in range(0, len(batch), 100):
            try:
                mark_batch(c, batch[k:k + 100], time.time())
            except Exception:                                 # noqa: BLE001
                pass
            time.sleep(0.3)
        c.commit()
        n += 1
        if n % 15 == 0:
            k = c.execute("SELECT COUNT(*) FROM mints").fetchone()[0]
            print(f"{datetime.now(timezone.utc):%H:%M:%S} polls={n} mints={k} tracking={len(due)} new_this_poll={new}", flush=True)
        time.sleep(max(0.0, POLL_S - (time.time() - now)))


if __name__ == "__main__":
    loop(float(sys.argv[1]) if len(sys.argv) > 1 else None)
