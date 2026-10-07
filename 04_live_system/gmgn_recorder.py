"""gmgn_recorder.py — GMGN's own data, recorded: every smart-money and KOL trade as it
prints, every token in the trenches with GMGN's sixty risk and structure fields, every
signal, and the 30-second / 1-minute candles needed to settle all of it later.
RECORDS ONLY. Trades nothing; holds no private key.

WHY. Sholo trades on GMGN and copies what its screen shows: smart-money buys, KOL buys,
"trenches" launches sorted by smart-degen count, the bundler / sniper / insider rates, the
rug ratio, the dev's launch history. Every one of those is a factor that can be scored the
way the options were — IF it is recorded at the moment it was visible and settled at the
price a copier would have paid seconds later. GMGN's read API (gmgn-cli, read-only key)
exposes all of it; its website is Cloudflare-gated to scripts and useless for this.

Every POLL_S seconds, on Solana:
  trenches   new_creation / near_completion / completed, 80 each: one row per token per
             poll with the full field set as JSON and the key fields as columns
             (creator_created_count, creator_created_open_ratio, bundler_trader_amount_rate,
             top70_sniper_hold_rate, suspected_insider_hold_rate, rat_trader_amount_rate,
             rug_ratio, smart_degen_count, renowned_count, tg_call_count, is_wash_trading,
             holder_count, progress, market_cap, volume, buys/sells, twitter/telegram/dup
             flags, image_dup, fresh_wallet_rate, dexscr paid flags, ...)
  smartmoney, kol   the newest trades: maker, tags, token, side, price, size, open/close
  signal     GMGN's own alerts (price spikes, smart-money buys, large buys ...)
and, on a queue, the candles that settle them:
  every smart-money / KOL BUY: 30-second candles for the hour after the trade (the copier's
  fill at +30 s / +60 s and the path to +1 h), fetched once the hour has passed;
  every near_completion / completed token at first sight, and one in SAMPLE_EVERY of the
  new_creation tokens: 1-minute candles at +1 h and +24 h after first sight.
Rate budget: the free key is a 5/5 leaky bucket; trenches weight 2, kline 2, the trade
lists 1. One poll is ~5 weight; the kline queue is throttled to KLINE_PER_MIN calls.
`05_studies/memecoin_gmgn_score.py` scores it.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

from idt import db as _db
from idt import paths

DB = paths.state("gmgn.db")
CLI = "gmgn-cli"
CHAIN = "sol"
POLL_S = 60
KLINE_PER_MIN = 20
SAMPLE_EVERY = 4
KEY_FIELDS = ["creator", "creator_created_count", "creator_created_open_count", "creator_created_open_ratio", "creator_balance_rate",
              "creator_token_status", "bundler_trader_amount_rate", "top70_sniper_hold_rate", "suspected_insider_hold_rate",
              "rat_trader_amount_rate", "rug_ratio", "smart_degen_count", "renowned_count", "bot_degen_count", "tg_call_count",
              "callout_count", "is_wash_trading", "holder_count", "top_10_holder_rate", "fresh_wallet_rate", "progress",
              "market_cap", "liquidity", "price", "volume_24h", "net_buy_24h", "buys_24h", "sells_24h", "swaps_24h",
              "twitter", "telegram", "website", "twitter_dup", "image_dup", "dexscr_ad", "dexscr_boost_fee", "cto_flag",
              "launchpad", "launchpad_platform", "created_timestamp", "open_timestamp", "complete_timestamp", "exchange"]


def cli(*args, timeout=40):
    r = subprocess.run([CLI, *args, "--raw"], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError((r.stderr or r.stdout or "no output")[:200])
    return json.loads(r.stdout)


def con():
    c = _db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS trench_snaps (
        ts REAL, address TEXT, kind TEXT, symbol TEXT, """ + ", ".join(f"{k} TEXT" if k in ("creator", "creator_token_status", "twitter", "telegram", "website", "launchpad", "launchpad_platform", "exchange") else f"{k} REAL" for k in KEY_FIELDS) + """, raw TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_ts_addr ON trench_snaps(address, ts)")
    c.execute("""CREATE TABLE IF NOT EXISTS first_seen (address TEXT PRIMARY KEY, ts REAL, kind TEXT, price REAL, market_cap REAL, sampled INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS smart_trades (
        tx TEXT PRIMARY KEY, seen REAL, ts REAL, src TEXT, maker TEXT, tags TEXT, token TEXT, symbol TEXT, side TEXT,
        price_usd REAL, amount_usd REAL, is_open_or_close INTEGER, launchpad TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_st_token ON smart_trades(token, ts)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_st_maker ON smart_trades(maker, ts)")
    c.execute("""CREATE TABLE IF NOT EXISTS signals (seen REAL, ts REAL, token TEXT, signal_type TEXT, raw TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS klines (address TEXT, resolution TEXT, t REAL, o REAL, h REAL, l REAL, c REAL, v REAL,
                 PRIMARY KEY (address, resolution, t))""")
    c.execute("""CREATE TABLE IF NOT EXISTS kline_jobs (id INTEGER PRIMARY KEY, address TEXT, resolution TEXT, t_from REAL, t_to REAL,
                 due REAL, why TEXT, done INTEGER DEFAULT 0, err TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_kj ON kline_jobs(done, due)")
    return c


def _num(x):
    if isinstance(x, bool):
        return float(x)
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def record_trenches(c, now):
    d = cli("market", "trenches", "--chain", CHAIN, "--limit", "80")
    n_new = 0
    for kind in ("new_creation", "near_completion", "completed"):
        for t in d.get(kind) or []:
            addr = t.get("address")
            if not addr:
                continue
            vals = []
            for k in KEY_FIELDS:
                v = t.get(k)
                vals.append(v if k in ("creator", "creator_token_status", "twitter", "telegram", "website", "launchpad", "launchpad_platform", "exchange") else _num(v))
            c.execute(f"INSERT INTO trench_snaps VALUES ({','.join('?' * (5 + len(KEY_FIELDS)))})",
                      (now, addr, kind, t.get("symbol"), *vals, json.dumps(t)[:6000]))
            if not c.execute("SELECT 1 FROM first_seen WHERE address=?", (addr,)).fetchone():
                n_new += 1
                sampled = int(kind != "new_creation" or (n_new % SAMPLE_EVERY == 0))
                c.execute("INSERT INTO first_seen VALUES (?,?,?,?,?,?)", (addr, now, kind, _num(t.get("price")), _num(t.get("market_cap")), sampled))
                if sampled:
                    for h in (3600, 86400):
                        c.execute("INSERT INTO kline_jobs (address, resolution, t_from, t_to, due, why) VALUES (?,?,?,?,?,?)",
                                  (addr, "1m", now - 120, now + h, now + h + 60, f"{kind}+{h}"))
    return n_new


def record_trades(c, now):
    n = 0
    for src in ("smartmoney", "kol"):
        try:
            d = cli("track", src, "--chain", CHAIN, "--limit", "100")
        except Exception:                                     # noqa: BLE001
            continue
        for t in d.get("list") or []:
            tx = t.get("transaction_hash")
            if not tx or c.execute("SELECT 1 FROM smart_trades WHERE tx=?", (tx,)).fetchone():
                continue
            tok = t.get("base_address")
            bt = t.get("base_token") or {}
            mi = t.get("maker_info") or {}
            c.execute("INSERT OR IGNORE INTO smart_trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (tx, now, _num(t.get("timestamp")), src, t.get("maker"), ",".join(mi.get("tags") or []), tok, bt.get("symbol"),
                       t.get("side"), _num(t.get("price_usd")), _num(t.get("amount_usd")), t.get("is_open_or_close"), bt.get("launchpad")))
            n += 1
            if t.get("side") == "buy" and tok:
                ts = _num(t.get("timestamp")) or now
                c.execute("INSERT INTO kline_jobs (address, resolution, t_from, t_to, due, why) VALUES (?,?,?,?,?,?)",
                          (tok, "30s", ts - 60, ts + 3600, ts + 3660, f"{src}_buy"))
    return n


def record_signals(c, now):
    try:
        d = cli("market", "signal", "--chain", CHAIN)
    except Exception:                                         # noqa: BLE001
        return 0
    items = d if isinstance(d, list) else (d.get("list") or d.get("signals") or [])
    n = 0
    for s in items or []:
        if not isinstance(s, dict):
            continue
        tok = s.get("token_address") or s.get("address") or (s.get("token") or {}).get("address")
        c.execute("INSERT INTO signals VALUES (?,?,?,?,?)", (now, _num(s.get("timestamp")), tok, str(s.get("signal_type")), json.dumps(s)[:3000]))
        n += 1
    return n


def run_klines(c, now, budget):
    jobs = c.execute("SELECT id, address, resolution, t_from, t_to FROM kline_jobs WHERE done=0 AND due<=? ORDER BY due LIMIT ?",
                     (now, budget)).fetchall()
    for jid, addr, res, t_from, t_to in jobs:
        try:
            d = cli("market", "kline", "--chain", CHAIN, "--address", addr, "--resolution", res,
                    "--from", str(int(t_from)), "--to", str(int(t_to)))
            for k in d.get("list") or []:
                c.execute("INSERT OR IGNORE INTO klines VALUES (?,?,?,?,?,?,?,?)",
                          (addr, res, _num(k.get("time")) / 1000.0, _num(k.get("open")), _num(k.get("high")), _num(k.get("low")),
                           _num(k.get("close")), _num(k.get("volume"))))
            c.execute("UPDATE kline_jobs SET done=1 WHERE id=?", (jid,))
        except Exception as e:                                # noqa: BLE001
            c.execute("UPDATE kline_jobs SET done=-1, err=? WHERE id=?", (str(e)[:200], jid))
        time.sleep(0.6)
    return len(jobs)


def loop(max_secs=None):
    c = con()
    t0, n = time.time(), 0
    while max_secs is None or time.time() - t0 < max_secs:
        now = time.time()
        try:
            nt = record_trenches(c, now)
        except Exception as e:                                # noqa: BLE001
            nt = f"err {str(e)[:60]}"
        ntr = record_trades(c, now)
        ns = record_signals(c, now) if n % 5 == 0 else 0
        c.commit()
        nk = run_klines(c, now, KLINE_PER_MIN)
        c.commit()
        n += 1
        if n % 5 == 0:
            tot = c.execute("SELECT (SELECT COUNT(*) FROM first_seen), (SELECT COUNT(*) FROM smart_trades), (SELECT COUNT(*) FROM klines), "
                            "(SELECT COUNT(*) FROM kline_jobs WHERE done=0)").fetchone()
            print(f"{datetime.now(timezone.utc):%H:%M:%S} polls={n} tokens={tot[0]} smart_trades={tot[1]} klines={tot[2]} "
                  f"kline_queue={tot[3]} | this poll: new_tokens={nt} trades={ntr} signals={ns} klines={nk}", flush=True)
        time.sleep(max(0.0, POLL_S - (time.time() - now)))


if __name__ == "__main__":
    loop(float(sys.argv[1]) if len(sys.argv) > 1 else None)
