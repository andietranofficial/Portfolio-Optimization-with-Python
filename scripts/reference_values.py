"""Print reference numbers for the Optimo engine tests, using the notebook's formulas.

    python scripts/reference_values.py --prices seed/prices.csv --tickers AMD AAPL MSFT ORCL --risk-free 0

Input: long-format CSV with columns symbol,date,adj_close (the format written by download_prices.py).
"""
import argparse

import numpy as np
import pandas as pd

TD = 252


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices", default="seed/prices.csv")
    ap.add_argument("--tickers", nargs="+", required=True)
    ap.add_argument("--risk-free", type=float, default=0.0)
    ap.add_argument("--amount", type=float, default=10_000)
    a = ap.parse_args()

    df = pd.read_csv(a.prices)
    px = df.pivot(index="date", columns="symbol", values="adj_close")[a.tickers].dropna().sort_index()
    n = len(a.tickers)
    print(f"Dates {px.index[0]} to {px.index[-1]}, {len(px)} days\n")

    # Equal weight, buy and hold (notebook steps 2-3)
    total = (px / px.iloc[0] * (1 / n) * a.amount).sum(axis=1)
    r = total.pct_change().dropna()
    print("Equal weight (buy and hold)")
    print(f"  cumulative return     {total.iloc[-1] / total.iloc[0] - 1:.6f}")
    print(f"  mean daily return     {r.mean():.8f}")
    print(f"  std daily return      {r.std():.8f}")
    print(f"  annualised Sharpe     {(r.mean() * TD - a.risk_free) / (r.std() * TD ** 0.5):.6f}\n")

    # Per-stock annualised stats and covariance (notebook step 5)
    sr = px.pct_change().dropna()
    mu, cov = sr.mean() * TD, sr.cov() * TD
    print("Per stock (annualised)")
    for t in a.tickers:
        print(f"  {t:8} return {mu[t]:.6f}  volatility {np.sqrt(cov.loc[t, t]):.6f}")
    print("\nCorrelation\n", sr.corr().round(4), "\n")

    w = np.full(n, 1 / n)
    print(f"Equal weight, covariance method: return {w @ mu.values:.6f}  volatility {np.sqrt(w @ cov.values @ w):.6f}\n")

    # Monte Carlo, 10,000 draws, NumPy seed 3 (as in the notebook)
    np.random.seed(3)
    W = np.random.random((10_000, n))
    W /= W.sum(axis=1, keepdims=True)
    ret = W @ mu.values
    vol = np.sqrt(np.einsum("ij,jk,ik->i", W, cov.values, W))
    sh = (ret - a.risk_free) / vol
    i = sh.argmax()
    print(f"Best Sharpe of 10,000 draws: {sh[i]:.4f}  return {ret[i]:.4f}  volatility {vol[i]:.4f}")
    print("  weights", dict(zip(a.tickers, W[i].round(4))))


if __name__ == "__main__":
    main()
