import re, html, json

from idt import paths

def cells(r):
    cs = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, re.S)
    return [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in cs]


def main():
    # Relative to the cwd, which meant "only from one directory on one machine".
    raw = open(paths.require_data("scratch", "completed.html"),
               encoding="utf-8", errors="replace").read()

    # find google sheet source
    for m in set(re.findall(r'https://docs\.google\.com/[^\s"\'<>]+', raw)):
        print("SHEET URL:", html.unescape(m))
    for m in set(re.findall(r'key=[0-9A-Za-z_\-]{30,}', raw)):
        print("SHEET KEY:", m)

    # extract table_1
    tm = re.search(r'<table id="table_1".*?</table>', raw, re.S)
    tbl = tm.group(0)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbl, re.S)

    parsed = [cells(r) for r in rows]
    parsed = [p for p in parsed if p]
    hdr = parsed[0]
    body = parsed[1:]
    print("\nCOLUMNS:", hdr)
    print("DATA ROWS:", len(body))
    print("\nFIRST 6:")
    for r in body[:6]:
        print("  ", r)
    print("\nLAST 6 (oldest):")
    for r in body[-6:]:
        print("  ", r)

    # date span
    idx_ann = [i for i, h in enumerate(hdr) if "nnounce" in h]
    idx_ftd = [i for i, h in enumerate(hdr) if "rading" in h or "irst" in h]
    print("\nannounce col idx:", idx_ann, "first-trading col idx:", idx_ftd)
    yrs = sorted({c[-4:] for r in body for c in r if re.fullmatch(r'\d{2}/\d{2}/\d{4}', c)})
    print("years present:", yrs)

    # survivorship probe
    dead = [r for r in body if any(x in ("#N/A", "$0.00", "", "N/A") for x in r[-3:])]
    print("\nrows with missing/zero current price (acquired/delisted):", len(dead))
    for r in dead[:10]:
        print("  ", r)
    json.dump({"columns": hdr, "rows": body}, open("ssi_completed.json", "w"), indent=1)


if __name__ == "__main__":
    main()
