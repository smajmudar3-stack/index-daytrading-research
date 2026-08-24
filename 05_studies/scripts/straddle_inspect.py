"""Inspect the real EOD option chain parquet files."""
import pyarrow.parquet as pq
import pandas as pd

from idt import paths

P = "opt_eod/SPY_options.parquet"  # path under DATA_ROOT, resolved at the read site
U = "opt_eod/SPY_underlying.parquet"


def main():
    f = pq.ParquetFile(paths.require_data(P))
    print("SCHEMA:")
    print(f.schema_arrow)
    print("num_row_groups:", f.num_row_groups, "rows:", f.metadata.num_rows)

    # first row group sample
    b = next(f.iter_batches(batch_size=20000))
    df = b.to_pandas()
    print("\nSAMPLE HEAD:")
    print(df.head(10).to_string())
    print("\ndtypes:\n", df.dtypes)
    print("\ndate range in first batch:", df["date"].min(), df["date"].max())

    un = pd.read_parquet(paths.require_data(U))
    print("\nUNDERLYING schema:", un.dtypes.to_dict())
    print(un.head())
    print(un.tail())
    print("underlying rows:", len(un))


if __name__ == "__main__":
    main()
