"""04 Build outcomes: daily returns from the Bloomberg market table. No signal is read here.

Definitions (security i, trading day t; prices split-adjusted, TRI = TOT_RETURN_INDEX_GROSS_DVDS):
  ret_cc   close(t-1) -> close(t), total return  = TRI_t / TRI_{t-1} - 1  (only if t-1 is the previous NYSE day)
  ret_oc   open(t)    -> close(t), price return  = PX_LAST_t / PX_OPEN_t - 1
  ret_co   close(t-1) -> open(t), total return   = (1 + ret_cc) / (1 + ret_oc) - 1  (dividends land here)
The TRI level is anchored to the request start date (FLDS RT116), so only ratios are used.

Outputs: data/interim/outcomes_daily.csv.gz, data/interim/index_returns.csv,
         outputs/diagnostics/04_build_outcomes_summary.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DIAG, INTERIM, load_index, load_market, trading_days, write_text  # noqa: E402

td = trading_days()
prev_td = pd.Series(td[:-1], index=td[1:])            # previous NYSE trading day for each trading day

mkt = load_market().sort_values(["ticker_exch", "date"]).reset_index(drop=True)
g = mkt.groupby("ticker_exch", sort=False)
lag_date = g["date"].shift(1)
lag_tri = g["tot_return_index_gross_dvds"].shift(1)
consecutive = lag_date.eq(mkt["date"].map(prev_td))   # no missing trading day in between
mkt["ret_cc"] = np.where(consecutive, mkt["tot_return_index_gross_dvds"] / lag_tri - 1, np.nan)
mkt["ret_oc"] = mkt["px_last"] / mkt["px_open"] - 1
mkt["ret_co"] = (1 + mkt["ret_cc"]) / (1 + mkt["ret_oc"]) - 1
mkt["dollar_volume_musd"] = mkt["px_last"] * mkt["px_volume_composite"] / 1e6
keep = ["ticker_exch", "date", "ret_cc", "ret_oc", "ret_co", "px_open", "px_last", "tot_return_index_gross_dvds",
        "px_volume_composite", "dollar_volume_musd", "cur_mkt_cap_musd"]
mkt[keep].to_csv(INTERIM / "outcomes_daily.csv.gz", index=False, date_format="%Y-%m-%d",
                 compression={"method": "gzip", "mtime": 0})   # mtime 0: identical bytes on every rebuild

idx = load_index()
piv = idx.pivot(index="date", columns="security", values="px_last")
ix = pd.DataFrame(index=td)
ix["spxt_ret_cc"] = piv["SPXT Index"].reindex(td).pct_change(fill_method=None)
spx = idx[idx["security"] == "SPX Index"].set_index("date")
ix["spx_ret_oc"] = (spx["px_last"] / spx["px_open"] - 1).reindex(td)
ix["vix_close"] = piv["VIX Index"].reindex(td)
ix.index.name = "date"
ix.to_csv(INTERIM / "index_returns.csv", date_format="%Y-%m-%d")

broken = (~consecutive & mkt["tot_return_index_gross_dvds"].notna() & lag_tri.notna()).sum()
lines = ["04_build_outcomes",
         f"outcomes_daily.csv.gz: {len(mkt):,} rows, {mkt['ticker_exch'].nunique()} securities",
         f"  ret_cc available: {mkt['ret_cc'].notna().sum():,}; ret_oc: {mkt['ret_oc'].notna().sum():,}",
         f"  returns not formed because a trading day is missing in between: {int(broken):,}",
         "  ret_cc quantiles (1%, 50%, 99%): " + ", ".join(f"{q:.4f}" for q in mkt['ret_cc'].quantile([.01, .5, .99])),
         "  ret_oc quantiles (1%, 50%, 99%): " + ", ".join(f"{q:.4f}" for q in mkt['ret_oc'].quantile([.01, .5, .99])),
         f"index_returns.csv: {len(ix)} trading days"]
write_text(DIAG / "04_build_outcomes_summary.txt", "\n".join(lines))
print("\n".join(lines))
