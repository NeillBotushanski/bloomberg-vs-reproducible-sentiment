"""Shared paths, constants and loaders for the Project 2 scripts.

Every script imports from here, so a path or a date is defined once. Values that are decisions
(study window, pull window) come from config/project_config.yaml.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config" / "project_config.yaml").read_text(encoding="utf-8"))

PULL_DIR = ROOT / "data" / "raw_bloomberg" / "20261106"          # the 2026-11-06 terminal pull, unchanged
EXPORT = PULL_DIR / "P2_Bloomberg_Export_20261106"                # tidy CSVs made on the terminal from the workbooks
RAW_WORKBOOK = PULL_DIR / "P2_Bloomberg_Pull_20261106.xlsx"      # the official raw file (formulas + cached values)
RISKLAB = ROOT / "data" / "raw_risklab"                           # RiskLab copies (News_Articles.csv)
INTERIM = ROOT / "data" / "interim"
ANALYTIC = ROOT / "data" / "analytic"
MANIFESTS = ROOT / "manifests"
DIAG = ROOT / "outputs" / "diagnostics"
TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"
for d in (INTERIM, ANALYTIC, DIAG, TABLES, FIGS):
    d.mkdir(parents=True, exist_ok=True)

STUDY_START = pd.Timestamp(CFG["sample"]["study_start"])         # 2020-01-01 (fixed by the brief)
STUDY_END = pd.Timestamp(CFG["sample"]["study_end"])             # 2025-12-31
PULL_START = pd.Timestamp(CFG["bloomberg_pull"]["pull_start"])   # 2019-07-01 (buffer)
PULL_END = pd.Timestamp(CFG["bloomberg_pull"]["pull_end"])       # 2026-01-30 (buffer)

NEWS_FIELDS = ["news_sentiment_daily_avg", "news_publication_count", "news_pos_sentiment_count",
               "news_neg_sentiment_count", "news_neutral_sentiment_count", "news_heat_pub_davg",
               "news_heat_read_dmax"]
MARKET_FIELDS = ["px_open", "px_last", "tot_return_index_gross_dvds", "px_volume_exchange",
                 "cur_mkt_cap_musd", "px_volume_composite"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    """Path relative to the project root, for logs and tables."""
    return str(Path(path).resolve().relative_to(ROOT))


def load_securities() -> pd.DataFrame:
    return pd.read_csv(EXPORT / "securities.csv", dtype=str, keep_default_na=False, na_values=[""])


def load_universe() -> pd.DataFrame:
    return pd.read_csv(EXPORT / "universe_snapshots.csv", parse_dates=["snapshot_date"])


def load_market() -> pd.DataFrame:
    return pd.read_csv(EXPORT / "market_daily.csv", parse_dates=["date"])


def load_news() -> pd.DataFrame:
    return pd.read_csv(EXPORT / "news_daily.csv", parse_dates=["date"])


def load_index() -> pd.DataFrame:
    return pd.read_csv(EXPORT / "index_daily.csv", parse_dates=["date"])


def load_earnings() -> pd.DataFrame:
    return pd.read_csv(EXPORT / "earnings_history.csv", dtype={"announcement_time": str},
                       parse_dates=["announcement_date"])


def load_articles() -> pd.DataFrame:
    """RiskLab News_Articles.csv exactly as stored (UTF-8 with BOM, CRLF)."""
    return pd.read_csv(RISKLAB / "News_Articles.csv", encoding="utf-8-sig", dtype=str)


def trading_days() -> pd.DatetimeIndex:
    """NYSE trading days, taken from the SPX Index rows Bloomberg returned (Days=T)."""
    idx = load_index()
    return pd.DatetimeIndex(sorted(idx.loc[idx["security"] == "SPX Index", "date"].unique()))


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
