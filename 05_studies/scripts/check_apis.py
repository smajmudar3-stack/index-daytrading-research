"""Probe what the Polygon and Tiingo keys can actually reach.

The whole greeks/option-pricing plan hinges on one question: can we get
HISTORICAL option quotes, or are we stuck modelling them? Modelled prices are
exactly what produced the retracted +3.7% condor edge, so this is worth
establishing before building anything on top.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

ENV = os.path.expanduser("~/quant-factory/.env")


def load_env():
    keys = {}
    with open(ENV) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip().strip('"').strip("'")
    return keys


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:  # noqa: BLE001
        return None, {"error": str(e)}


def main():
    env = load_env()
    pk = env.get("POLYGON_API_KEY", "")
    tk = env.get("TIINGO_API_KEY", "")
    print(f"polygon key: {'set (' + str(len(pk)) + ' chars)' if pk else 'MISSING'}")
    print(f"tiingo  key: {'set (' + str(len(tk)) + ' chars)' if tk else 'MISSING'}")
    print()

    print("=" * 70)
    print("POLYGON")
    print("=" * 70)

    probes = [
        ("equity daily aggs (SPY 2024)",
         f"https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/2024-01-02/2024-01-10?apiKey={pk}"),
        ("options contracts list (SPY)",
         f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker=SPY&limit=3&apiKey={pk}"),
        ("HISTORICAL option aggs (a 2024 SPY call)",
         f"https://api.polygon.io/v2/aggs/ticker/O:SPY240119C00470000/range/1/day/2023-11-01/2024-01-19?apiKey={pk}"),
        ("option snapshot chain (AAPL)",
         f"https://api.polygon.io/v3/snapshot/options/AAPL?limit=3&apiKey={pk}"),
        ("grouped daily (whole market 2024-06-03)",
         f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/2024-06-03?apiKey={pk}"),
        ("ticker list (active)",
         f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=3&apiKey={pk}"),
    ]
    for label, url in probes:
        st, body = get(url)
        status = body.get("status") or body.get("error") or ""
        n = body.get("resultsCount", body.get("count", len(body.get("results", []) or [])))
        msg = body.get("message", "")
        print(f"  [{st}] {label:42s} status={status} n={n}")
        if msg:
            print(f"        -> {str(msg)[:150]}")

    print()
    print("=" * 70)
    print("TIINGO")
    print("=" * 70)
    tprobes = [
        ("daily prices (AAPL)",
         f"https://api.tiingo.com/tiingo/daily/AAPL/prices?startDate=2024-01-02&endDate=2024-01-10&token={tk}"),
        ("metadata (AAPL)", f"https://api.tiingo.com/tiingo/daily/AAPL?token={tk}"),
        ("DELISTED ticker (survivorship check)",
         f"https://api.tiingo.com/tiingo/daily/FTCH/prices?startDate=2023-01-03&endDate=2023-01-10&token={tk}"),
    ]
    for label, url in tprobes:
        st, body = get(url)
        if isinstance(body, list):
            print(f"  [{st}] {label:42s} rows={len(body)}")
        else:
            print(f"  [{st}] {label:42s} {str(body)[:160]}")


if __name__ == "__main__":
    main()
