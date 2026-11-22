"""Download daily adjusted close prices from Yahoo Finance into the Optimo seed file.

Run once on a machine that can reach Yahoo Finance (your laptop or a Fabric notebook):

    pip install yfinance pandas
    python scripts/download_prices.py --tickers AAPL MSFT ORCL AMD --years 5

Output: seed/prices.csv in long format (symbol,date,adj_close) and seed/tickers.csv.
The S&P 500 benchmark (SPY) is always included and flagged as the benchmark.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

BENCHMARK = "SPY"
OUT_DIR = Path(__file__).resolve().parent.parent / "seed"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tickers", nargs="+", required=True, help="Yahoo symbols, max 10 per run in the app")
    parser.add_argument("--years", type=int, default=5, help="Years of history to download (default 5)")
    args = parser.parse_args()

    symbols = sorted({t.upper() for t in args.tickers} | {BENCHMARK})
    start = date.today() - timedelta(days=365 * args.years + 10)

    raw = yf.download(symbols, start=start.isoformat(), auto_adjust=False, progress=False, group_by="column")
    adj = raw["Adj Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Adj Close"]].rename(columns={"Adj Close": symbols[0]})

    prices = (
        adj.rename_axis("date")
        .reset_index()
        .melt(id_vars="date", var_name="symbol", value_name="adj_close")
        .dropna(subset=["adj_close"])
    )
    prices["date"] = pd.to_datetime(prices["date"]).dt.strftime("%Y-%m-%d")
    prices["adj_close"] = prices["adj_close"].round(6)
    prices = prices[["symbol", "date", "adj_close"]].sort_values(["symbol", "date"])

    # Basic data checks: report short histories and gaps so they can be fixed before seeding.
    counts = prices.groupby("symbol")["date"].agg(["count", "min", "max"])
    expected = counts["count"].max()
    for sym, row in counts.iterrows():
        flag = "" if row["count"] >= expected * 0.98 else "  <-- shorter history, check this ticker"
        print(f"{sym:8} {row['count']:5d} rows  {row['min']} to {row['max']}{flag}")

    names = {}
    for sym in symbols:
        try:
            names[sym] = yf.Ticker(sym).info.get("shortName") or sym
        except Exception:  # Yahoo metadata is unreliable; fall back to the symbol
            names[sym] = sym
    tickers = pd.DataFrame(
        {"symbol": symbols, "name": [names[s] for s in symbols], "currency": "USD", "is_benchmark": [s == BENCHMARK for s in symbols]}
    )

    OUT_DIR.mkdir(exist_ok=True)
    prices.to_csv(OUT_DIR / "prices.csv", index=False)
    tickers.to_csv(OUT_DIR / "tickers.csv", index=False)
    print(f"\nWrote {len(prices)} price rows and {len(tickers)} tickers to {OUT_DIR}")
    print("Note: currency is set to USD for all tickers. Check non-US listings before the demo.")


if __name__ == "__main__":
    main()
