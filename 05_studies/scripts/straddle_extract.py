"""Pass 1: stream the 24.7M-row SPY (and QQQ) EOD chain and keep a compact slice:
   monthly (third-Friday) expirations, DTE <= 75, |delta| in [0.03, 0.97].
Writes data/opt_eod/<SYM>_monthly_slice.parquet
"""
import sys
import pandas as pd
import pyarrow.parquet as pq

from idt import paths

SYM = sys.argv[1] if len(sys.argv) > 1 else "SPY"
SRC = f"opt_eod/{SYM}_options.parquet"  # path under DATA_ROOT, resolved at the read site
OUT = paths.data("opt_eod", f"{SYM}_monthly_slice.parquet")

COLS = ["expiration", "strike", "type", "bid", "ask", "date",
        "implied_volatility", "delta", "gamma", "vega", "theta",
        "volume", "open_interest"]


def main():
    f = pq.ParquetFile(paths.require_data(SRC))
    out = []
    nrows = 0
    for i in range(f.num_row_groups):
        df = f.read_row_group(i, columns=COLS).to_pandas()
        nrows += len(df)
        exp = df["expiration"]
        dow = exp.dt.dayofweek
        day = exp.dt.day
        monthly = ((dow == 4) & (day >= 15) & (day <= 21)) | ((dow == 5) & (day >= 16) & (day <= 22))
        dte = (exp - df["date"]).dt.days
        keep = monthly & (dte >= 0) & (dte <= 75)
        df = df.loc[keep].copy()
        if len(df) == 0:
            continue
        ad = df["delta"].abs()
        df = df.loc[(ad >= 0.03) & (ad <= 0.97)].copy()
        df["dte"] = (df["expiration"] - df["date"]).dt.days
        df["type"] = df["type"].astype(str)
        out.append(df)
        print(f"rg {i+1}/{f.num_row_groups} scanned={nrows} kept={sum(len(d) for d in out)}", flush=True)

    res = pd.concat(out, ignore_index=True)
    res.to_parquet(OUT, index=False)
    print("WROTE", OUT, res.shape)
    print(res["date"].min(), res["date"].max())


if __name__ == "__main__":
    main()
