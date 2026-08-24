"""Pass 1b: same monthly slice but with NO delta filter, so option PATHS
(needed for managed exits and daily delta-hedging) do not drop out when a leg
goes deep ITM/OTM. Strikes limited to +/-30% of the running spot proxy via delta
is avoided; instead we keep everything on monthly expirations with dte<=75.
"""
import sys
import pandas as pd
import pyarrow.parquet as pq

from idt import paths

SYM = sys.argv[1] if len(sys.argv) > 1 else "SPY"
SRC = f"opt_eod/{SYM}_options.parquet"  # path under DATA_ROOT, resolved at the read site
OUT = paths.data("opt_eod", f"{SYM}_monthly_full.parquet")

COLS = ["expiration", "strike", "type", "bid", "ask", "date",
        "implied_volatility", "delta", "vega", "volume", "open_interest"]


def main():
    f = pq.ParquetFile(paths.require_data(SRC))
    out = []
    for i in range(f.num_row_groups):
        df = f.read_row_group(i, columns=COLS).to_pandas()
        exp = df["expiration"]
        dow = exp.dt.dayofweek
        day = exp.dt.day
        monthly = ((dow == 4) & (day >= 15) & (day <= 21)) | ((dow == 5) & (day >= 16) & (day <= 22))
        dte = (exp - df["date"]).dt.days
        df = df.loc[monthly & (dte >= 0) & (dte <= 75)].copy()
        if len(df) == 0:
            continue
        df["dte"] = (df["expiration"] - df["date"]).dt.days
        df["type"] = df["type"].astype(str)
        out.append(df)

    res = pd.concat(out, ignore_index=True)
    res.to_parquet(OUT, index=False)
    print("WROTE", OUT, res.shape, res["date"].min(), res["date"].max())


if __name__ == "__main__":
    main()
