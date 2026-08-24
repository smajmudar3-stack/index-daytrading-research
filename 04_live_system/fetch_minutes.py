"""fetch_minutes.py — pull 1-minute bars from Polygon for additional symbols.

Purpose is NOT more parameter search. The rule is already fixed. This adds INDEPENDENT SAMPLES:
symbols the rule was never fit on. If the fade edge is real it should appear in other liquid index
ETFs; if it was a QQQ-specific artefact of 500 sessions, it will not. That is a genuine test, whereas
searching more combinations on the same QQQ data can only manufacture false positives.

The key comes from idt.keys and the bars land under DATA_ROOT (idt.paths). Both used to be
hardcoded: the key loader searched the original author's home directory first, and the output
path was relative to the CURRENT WORKING DIRECTORY, so the same command wrote a different
tree depending on where you ran it from.
"""
import os
import sys
import time
from datetime import date, timedelta

import requests

import uw_client                       # shared health vocabulary and retry policy
from idt import keys, paths

# Polygon's free tier is 5 requests a minute, so the pacing sleep below is part
# of the contract, not politeness. The retry budget is separate: it covers a
# request that fails, not the rate limit that governs requests that work.
PACE_S = 13
HTTP_TIMEOUT_S = 60.0                  # minute bars for a whole month are a big body


# Last failure, so status() can tell a rejected key from a dead service instead
# of both surfacing as "none" next to a month that simply had no data.
_LAST_FAILURE = {"state": None, "detail": "", "ts": 0.0}
_FAILURE_WINDOW_S = 900


def _note_failure(state, detail):
    _LAST_FAILURE.update({"state": state, "detail": str(detail)[:120], "ts": time.time()})
    print(f"fetch_minutes: {detail}")


def _note_success():
    _LAST_FAILURE.update({"state": None, "detail": "", "ts": 0.0})


def status():
    """This module's health, in the shape every outside-service module returns.
    See uw_client.STATES for what each state means."""
    svc = ("fetch_minutes", "polygon")
    if not keys.get("POLYGON_API_KEY"):
        return uw_client.service_status(
            *svc, uw_client.STATE_NO_KEY,
            "No POLYGON_API_KEY in the environment or in the repo .env. Minute bars for new symbols "
            "cannot be fetched; the ones already under data/minute still work.")
    f = _LAST_FAILURE
    if f["state"] and time.time() - f["ts"] < _FAILURE_WINDOW_S:
        return uw_client.service_status(*svc, f["state"], f"Last fetch failed: {f['detail']}.")
    return uw_client.service_status(*svc, uw_client.STATE_AVAILABLE,
                                    "Key present and no failed fetch in this process.")


def _get_json(url, label):
    """One Polygon GET, retried on the failures that can clear.

    Transport errors, 429 and 5xx are retried with bounded backoff; a 401 or 403
    is a rejected key and will be rejected identically every time, so it stops
    at once and is recorded as auth-failed rather than looking like a symbol
    with no data. Returns the decoded body, or None once it has given up."""
    def attempt():
        try:
            r = requests.get(url, timeout=HTTP_TIMEOUT_S)
        except requests.RequestException as e:
            raise uw_client.Transient(f"{type(e).__name__}: {str(e)[:80]}") from e
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError as e:
                # A 200 carrying non-JSON is a proxy or maintenance page, which
                # clears. Bounded by the attempt count either way.
                raise uw_client.Transient(f"malformed JSON on {label}: {str(e)[:60]}") from e
        if uw_client.retryable_status(r.status_code):
            raise uw_client.Transient(f"HTTP {r.status_code} on {label}")
        raise requests.HTTPError(f"HTTP {r.status_code} on {label}", response=r)

    try:
        body = uw_client.with_backoff(attempt, label=label)
    except requests.HTTPError as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        state = (uw_client.STATE_AUTH_FAILED if code in (401, 403)
                 else uw_client.STATE_OUTAGE)
        hint = (" — the Polygon key was rejected" if state == uw_client.STATE_AUTH_FAILED else "")
        _note_failure(state, f"{e}{hint}")
        return None
    except uw_client.Transient as e:
        _note_failure(uw_client.STATE_OUTAGE, f"gave up on {label} after "
                                              f"{uw_client.HTTP_ATTEMPTS} tries: {e}")
        return None
    _note_success()
    return body


def month_bars(sym, y, m, k):
    import pandas as pd                # imported here: a status() check must not need pandas

    start = date(y, m, 1)
    end = (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1))
    url = (f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/minute/"
           f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={k}")
    rows, url_next = [], url
    for _ in range(12):                       # follow pagination
        j = _get_json(url_next, f"{sym} {y}-{m:02d}")
        if j is None:
            # Partial pages are worse than none: a truncated month looks like a
            # thin trading month to every study that reads it later.
            return None
        rows += j.get("results") or []
        nxt = j.get("next_url")
        if not nxt:
            break
        url_next = nxt + f"&apiKey={k}"
        time.sleep(PACE_S)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df.t, unit="ms", utc=True).dt.tz_convert("America/New_York")
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close",
                            "v": "volume", "vw": "vwap", "n": "trades"})
    return df.set_index("ts")[["open", "high", "low", "close", "volume", "vwap", "trades"]]


def fetch(sym, months=24):
    k = keys.get("POLYGON_API_KEY")
    if not k:
        print(status()["detail"])
        return 0
    # Under DATA_ROOT, not under the current working directory. This is the one
    # place the repo may create a directory inside DATA_ROOT: it is fetching the
    # market data, not guessing at data that is missing.
    out_dir = paths.data("minute", sym)
    os.makedirs(out_dir, exist_ok=True)
    today = date.today()
    got = failed = 0
    for i in range(months):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        path = os.path.join(out_dir, f"{y}-{m:02d}.parquet")
        if os.path.exists(path):
            continue
        df = month_bars(sym, y, m, k)
        if df is None or df.empty:
            # "none" used to cover both an empty month and a failed request. The
            # difference matters: one is a market fact, the other is a fetch to
            # run again.
            if _LAST_FAILURE["state"] and time.time() - _LAST_FAILURE["ts"] < 60:
                failed += 1
                print(f"  {sym} {y}-{m:02d}: FETCH FAILED ({_LAST_FAILURE['detail']})")
            else:
                print(f"  {sym} {y}-{m:02d}: no bars returned")
            if _LAST_FAILURE["state"] == uw_client.STATE_AUTH_FAILED:
                print(f"  {sym}: stopping — the key is being rejected, so the remaining months "
                      "would fail the same way")
                break
            continue
        df.to_parquet(path)
        got += 1
        print(f"  {sym} {y}-{m:02d}: {len(df):,} bars")
        time.sleep(PACE_S)
    print(f"{sym}: wrote {got} months" + (f", {failed} failed" if failed else ""))
    return got


if __name__ == "__main__":
    st = status()
    print(f"polygon {st['state']}: {st['detail']}")
    for s in (sys.argv[1:] or ["IWM", "DIA"]):
        print(f"--- {s} ---")
        fetch(s)
