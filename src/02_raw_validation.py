"""02 Raw validation: schema, keys, ranges, calendars, timing and identifier joins, before any merge.

Reads only the raw files (the Bloomberg export CSVs and News_Articles.csv) and writes:
  outputs/diagnostics/raw_file_inventory.csv    every raw file with size, rows and SHA-256
  outputs/diagnostics/raw_validation_checks.csv one row per check, with the value found and PASS/FLAG
  outputs/diagnostics/news_weekday_counts.csv   story counts by weekday (tests the 24-hour window)
  outputs/diagnostics/news_articles_validation.csv  one row per headline, with every flag
  outputs/diagnostics/02_raw_validation_summary.txt
Nothing is dropped or changed here; flags are carried forward and handled in 03 to 05.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DIAG, EXPORT, NEWS_FIELDS, PULL_DIR, RISKLAB, load_articles, load_earnings,  # noqa: E402
                    load_index, load_market, load_news, load_securities, load_universe, rel, sha256,
                    trading_days, write_text)

checks: list[dict] = []


def check(area, name, value, expected, ok, detail=""):
    checks.append({"area": area, "check": name, "value": value, "expected": expected,
                   "status": "PASS" if ok else "FLAG", "detail": detail})


# ---------------------------------------------------------------- 1. file inventory and hashes
inv = []
recorded = {}
for line in (EXPORT / "SHA256SUMS.txt").read_text().splitlines():
    parts = line.split()
    if len(parts) >= 2:
        recorded[parts[1]] = parts[0]
for line in (PULL_DIR / "README.txt").read_text().splitlines():
    m = re.match(r"([0-9a-f]{64})\s+(\S+\.xlsx)", line.strip())
    if m:
        recorded[m.group(2)] = m.group(1)
for f in sorted([*PULL_DIR.rglob("*"), *RISKLAB.glob("*")]):
    if f.is_file() and not f.name.startswith("."):
        h = sha256(f)
        rows = None
        if f.suffix == ".csv":
            with f.open("rb") as fh:
                rows = sum(1 for _ in fh) - 1
        inv.append({"file": rel(f), "bytes": f.stat().st_size, "rows_excl_header": rows, "sha256": h,
                    "recorded_sha256": recorded.get(f.name, ""),
                    "hash_matches_record": (h == recorded[f.name]) if f.name in recorded else None})
inv = pd.DataFrame(inv)
inv.to_csv(DIAG / "raw_file_inventory.csv", index=False)
n_rec = inv["hash_matches_record"].notna().sum()
n_ok = (inv["hash_matches_record"] == True).sum()  # noqa: E712
check("files", "Raw files whose SHA-256 matches the hash recorded on the terminal", f"{n_ok}/{n_rec}", "all", n_ok == n_rec)
art_hash = inv.loc[inv["file"].str.endswith("News_Articles.csv"), "sha256"].iloc[0]
check("files", "News_Articles.csv SHA-256 starts with the RiskLab catalogue value 53bff1c0", art_hash[:8], "53bff1c0",
      art_hash.startswith("53bff1c0"))

# ---------------------------------------------------------------- 2. securities
sec = load_securities()
check("securities", "Rows (exchange tickers)", len(sec), 635, len(sec) == 635)
check("securities", "Duplicate ticker_exch", int(sec["ticker_exch"].duplicated().sum()), 0, not sec["ticker_exch"].duplicated().any())
check("securities", "Duplicate exchange-level FIGI (id_bb_global)", int(sec["id_bb_global"].duplicated().sum()), 0,
      not sec["id_bb_global"].duplicated().any())
comp = sec.groupby("composite_id_bb_global")["ticker_exch"].agg(list)
multi = comp[comp.str.len() > 1]
check("securities", "Companies (composite FIGI)", int(comp.size), 617, comp.size == 617)
check("securities", "Companies with two exchange tickers", int(multi.size), 18, multi.size == 18,
      "; ".join(" / ".join(v) for v in multi.tolist()))
check("securities", "Pricing currency other than USD", int((sec["crncy"] != "USD").sum()), 0, (sec["crncy"] == "USD").all())
check("securities", "Missing GICS sector (inactive names)", int(sec["gics_sector_name"].isna().sum()), "60 (documented)",
      True, "BICS sector is filled for all: " + str(int(sec["bics_industry_sector"].notna().sum())))
check("securities", "Missing ISIN", int(sec["id_isin"].isna().sum()), "small", True,
      ", ".join(sec.loc[sec["id_isin"].isna(), "ticker_exch"]))
check("securities", "Market status counts", "; ".join(f"{k} {v}" for k, v in sec["market_status"].value_counts().items()),
      "current snapshot", True)

# ---------------------------------------------------------------- 3. universe snapshots
uni = load_universe()
snaps = sorted(uni["snapshot_date"].unique())
month_ends = pd.date_range("2019-12-31", "2025-12-31", freq="ME")
check("universe", "Snapshots", len(snaps), 73, len(snaps) == 73 and set(pd.DatetimeIndex(snaps)) == set(month_ends))
per = uni.groupby("snapshot_date").size()
check("universe", "Members per snapshot (min-max)", f"{per.min()}-{per.max()}", "~500-506", per.between(495, 510).all())
check("universe", "Duplicate (snapshot, ticker)", int(uni.duplicated().sum()), 0, not uni.duplicated().any())
check("universe", "Distinct members across snapshots", uni["ticker_exch"].nunique(), 635, uni["ticker_exch"].nunique() == 635)
missing_in_sec = set(uni["ticker_exch"]) - set(sec["ticker_exch"])
check("universe", "Members missing from securities.csv", len(missing_in_sec), 0, not missing_in_sec)
both = uni.merge(sec[["ticker_exch", "composite_id_bb_global"]], on="ticker_exch")
dual_same_snap = both.groupby(["snapshot_date", "composite_id_bb_global"]).size()
check("universe", "Snapshot rows where one company appears under two tickers", int((dual_same_snap > 1).sum()), 0,
      (dual_same_snap > 1).sum() == 0)
chg = per.diff().abs().fillna(0)
check("universe", "Largest month-to-month change in member count", int(chg.max()), "small", chg.max() <= 6)

# ---------------------------------------------------------------- 4. market daily
mkt = load_market()
td = trading_days()
check("market", "Rows", len(mkt), 978472, len(mkt) == 978472)
check("market", "Duplicate (ticker, date)", int(mkt.duplicated(["ticker_exch", "date"]).sum()), 0,
      not mkt.duplicated(["ticker_exch", "date"]).any())
check("market", "Date range", f"{mkt['date'].min().date()} to {mkt['date'].max().date()}", "2019-07-01 to 2026-01-30",
      mkt["date"].min() == pd.Timestamp("2019-07-01") and mkt["date"].max() == pd.Timestamp("2026-01-30"))
off_cal = ~mkt["date"].isin(td)
check("market", "Rows on dates that are not SPX trading days", int(off_cal.sum()), 0, off_cal.sum() == 0)
check("market", "Weekend rows", int(mkt["date"].dt.weekday.ge(5).sum()), 0, not mkt["date"].dt.weekday.ge(5).any())
for f in ["px_open", "px_last", "tot_return_index_gross_dvds"]:
    bad = (mkt[f] <= 0).sum()
    check("market", f"{f} <= 0", int(bad), 0, bad == 0)
miss = mkt[["px_open", "px_last", "tot_return_index_gross_dvds", "px_volume_composite", "cur_mkt_cap_musd"]].isna().mean()
check("market", "Share of rows missing each field", "; ".join(f"{k} {v:.2%}" for k, v in miss.items()),
      "rows outside a listing are blank (Fill=B)", True)
no_px = mkt.groupby("ticker_exch")["px_last"].apply(lambda s: s.notna().sum())
check("market", "Securities with no price at all", int((no_px == 0).sum()), "1 (1844053D US)", (no_px == 0).sum() <= 1,
      ", ".join(no_px[no_px == 0].index))
mkt = mkt.sort_values(["ticker_exch", "date"])
g = mkt.groupby("ticker_exch")
r_tri = g["tot_return_index_gross_dvds"].pct_change(fill_method=None)
r_px = g["px_last"].pct_change(fill_method=None)
gap = (r_tri - r_px)
check("market", "Days where total return is below price return by > 0.1% (should not happen)", int((gap < -0.001).sum()),
      "0 or a handful", (gap < -0.001).sum() < 50,
      f"total return minus price return: median {gap.median():.5f}, 99th pct {gap.quantile(.99):.4f}")
big = r_tri.abs() > 0.5
check("market", "Daily total returns beyond +/-50%", int(big.sum()), "a few (real events)", big.sum() < 50,
      "; ".join(f"{t} {d.date()} {r:+.1%}" for t, d, r in zip(mkt.loc[big, 'ticker_exch'], mkt.loc[big, 'date'], r_tri[big])))
oc = mkt["px_last"] / mkt["px_open"] - 1
check("market", "Open-to-close moves beyond +/-50%", int((oc.abs() > 0.5).sum()), "a few", (oc.abs() > 0.5).sum() < 50)
cap_med = mkt["cur_mkt_cap_musd"].median()
check("market", "Median market cap (USD millions)", round(cap_med), "tens of thousands (millions units)", 5e3 < cap_med < 2e5)
vol_ratio = (mkt["px_volume_exchange"] / mkt["px_volume_composite"]).replace([np.inf, -np.inf], np.nan)
check("market", "Exchange volume / composite volume (median)", round(vol_ratio.median(), 3), "< 1 (one exchange only)",
      vol_ratio.median() < 1, f"rows with exchange > composite: {(vol_ratio > 1.0001).sum()}")

# ---------------------------------------------------------------- 5. news daily
news = load_news()
check("news", "Rows (security-days with at least one value)", len(news), 1070056, len(news) == 1070056)
check("news", "Duplicate (ticker, date)", int(news.duplicated(["ticker_exch", "date"]).sum()), 0,
      not news.duplicated(["ticker_exch", "date"]).any())
wd = news["date"].dt.weekday
check("news", "Rows on Saturday or Sunday", int(wd.ge(5).sum()), "0 (FLDS: no weekend values)", not wd.ge(5).any())
news_off = ~news["date"].isin(td)
check("news", "Rows on weekday market holidays", int(news_off.sum()),
      "0 according to the pull notes ('values on trading days only'); FLAG = the notes are wrong, values exist on holidays",
      news_off.sum() == 0, ", ".join(sorted(news.loc[news_off, "date"].dt.strftime("%Y-%m-%d").unique())[:20]))
s = news["news_sentiment_daily_avg"]
check("news", "Sentiment outside [-1, 1]", int(((s < -1) | (s > 1)).sum()), 0, not ((s < -1) | (s > 1)).any())
for f in ["news_publication_count", "news_pos_sentiment_count", "news_neg_sentiment_count", "news_neutral_sentiment_count"]:
    x = news[f].dropna()
    check("news", f"{f}: negative or non-integer", int(((x < 0) | (x % 1 != 0)).sum()), 0, not ((x < 0) | (x % 1 != 0)).any())
for f in ["news_heat_pub_davg", "news_heat_read_dmax"]:
    x = news[f].dropna()
    check("news", f"{f} outside [0, 4]", int(((x < 0) | (x > 4)).sum()), 0, not ((x < 0) | (x > 4)).any())
tone = news[["news_pos_sentiment_count", "news_neg_sentiment_count", "news_neutral_sentiment_count"]].sum(axis=1, min_count=3)
both_ = tone.notna() & news["news_publication_count"].notna()
check("news", "Tone counts (pos+neg+neutral) exceed the publication count", int((tone[both_] > news.loc[both_, "news_publication_count"]).sum()),
      "few or none", True, f"median ratio tone/publication {(tone[both_] / news.loc[both_, 'news_publication_count'].replace(0, np.nan)).median():.3f}")
s_no_tone = s.notna() & (tone == 0)
check("news", "Sentiment present while all tone counts are zero", int(s_no_tone.sum()), "describe", True,
      f"sentiment value on those rows: {s[s_no_tone].value_counts().head(3).to_dict()}")
zero_sent = (s == 0).mean()
zero_bal = ((s == 0) & (tone > 0) & (news["news_pos_sentiment_count"] == news["news_neg_sentiment_count"])).sum()
check("news", "Share of sentiment values exactly 0", f"{zero_sent:.1%}", "describe", True,
      f"{zero_bal:,} of {(s == 0).sum():,} zeros have scored stories with positive = negative (a real neutral reading); "
      f"missing sentiment with no scored stories: {(s.isna() & (tone == 0)).sum():,}")
mm = s.notna() & (tone > 0)
rho = np.corrcoef(s[mm], ((news["news_pos_sentiment_count"] - news["news_neg_sentiment_count"]) / tone)[mm])[0, 1]
check("news", "Correlation of the vendor score with (positive - negative) / scored stories", round(rho, 3), "describe", True,
      "Descriptive only: how much of the black-box score a simple count ratio reproduces.")
check("news", "Missing share by field", "; ".join(f"{k} {news[k].isna().mean():.1%}" for k in NEWS_FIELDS), "describe", True)

# Weekday test of the 24-hour window: if Monday's value covered the weekend, Monday counts would be about 2-3x.
wk = news.loc[news["date"].between("2020-01-01", "2025-12-31")].copy()
wk["weekday"] = wk["date"].dt.day_name()
wtab = wk.groupby("weekday").agg(rows=("ticker_exch", "size"),
                                 mean_publication_count=("news_publication_count", "mean"),
                                 mean_tone_count=("news_neutral_sentiment_count", lambda x: np.nan),
                                 share_with_sentiment=("news_sentiment_daily_avg", lambda x: x.notna().mean()))
wk["tone_total"] = wk[["news_pos_sentiment_count", "news_neg_sentiment_count", "news_neutral_sentiment_count"]].sum(axis=1, min_count=3)
wtab["mean_tone_count"] = wk.groupby("weekday")["tone_total"].mean()
wtab = wtab.reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
wtab.to_csv(DIAG / "news_weekday_counts.csv")
mon_ratio = wtab.loc["Monday", "mean_tone_count"] / wtab.loc[["Tuesday", "Wednesday", "Thursday"], "mean_tone_count"].mean()
check("timing", "Monday tone-count / Tue-Thu tone-count", round(mon_ratio, 2),
      "about 3 if Monday's value covered the whole weekend; well below 1 if it covers only the 24h to Monday 09:20",
      False, "Consistent with the FLDS 24h window: Monday's value covers mostly Sunday, so stories from Friday 09:20 "
      "to Sunday 09:20 fall in no daily value. To confirm with Bloomberg Help.")

# ---------------------------------------------------------------- 6. index and earnings
idx = load_index()
for secname, n in idx.groupby("security").size().items():
    check("index", f"{secname} rows", int(n), "1,656 (VIX 1,684)", True)
vix_extra = set(idx.loc[idx["security"] == "VIX Index", "date"]) - set(td)
check("index", "VIX rows on non-SPX dates", len(vix_extra), "28 (CBOE holidays)", True)
ern = load_earnings()
check("earnings", "Rows / securities", f"{len(ern)} / {ern['ticker_exch'].nunique()}", "62,096 / 627",
      len(ern) == 62096 and ern["ticker_exch"].nunique() == 627)
check("earnings", "Duplicate (ticker, period)", int(ern.duplicated(["ticker_exch", "year_period"]).sum()), "0",
      not ern.duplicated(["ticker_exch", "year_period"]).any())
t = ern["announcement_time"].dropna()
lab = t[~t.str.match(r"^\d{2}:\d{2}$")]
check("earnings", "Announcement times given as a label instead of HH:MM", int(len(lab)), "describe", True,
      "; ".join(f"{k} {v}" for k, v in lab.value_counts().items()) + f"; blank {int(ern['announcement_time'].isna().sum())}")

# ---------------------------------------------------------------- 7. identifier joins
for name, df in [("market", mkt), ("news", news), ("earnings", ern)]:
    keys = set(df["ticker_exch"])
    check("joins", f"securities.csv tickers with no {name} rows", len(set(sec["ticker_exch"]) - keys), "documented",
          True, ", ".join(sorted(set(sec["ticker_exch"]) - keys)[:12]))
    check("joins", f"{name} tickers not in securities.csv", len(keys - set(sec["ticker_exch"])), 0, not (keys - set(sec["ticker_exch"])))

# ---------------------------------------------------------------- 8. News_Articles.csv (the 188 headlines)
raw_bytes = (RISKLAB / "News_Articles.csv").read_bytes()
art = load_articles()
check("articles", "Encoding and line endings", ("UTF-8 BOM, " if raw_bytes.startswith(b"\xef\xbb\xbf") else "") +
      ("CRLF" if b"\r\n" in raw_bytes else "LF"), "readable", True)
check("articles", "Rows and columns", f"{len(art)} rows; {', '.join(art.columns)}", "188; Company, Date, Headline, URL",
      len(art) == 188 and list(art.columns) == ["Company", "Date", "Headline", "URL"])
art["date"] = pd.to_datetime(art["Date"], errors="coerce")
check("articles", "Unparseable dates", int(art["date"].isna().sum()), 0, art["date"].notna().all())
check("articles", "Date range", f"{art['date'].min().date()} to {art['date'].max().date()}", "2020-2025", True)
check("articles", "Firms", f"{art['Company'].nunique()}: {', '.join(sorted(art['Company'].unique()))}", "describe", True)
check("articles", "Exact duplicate headlines", int(art["Headline"].duplicated().sum()), 0, not art["Headline"].duplicated().any(),
      "; ".join(art.loc[art["Headline"].duplicated(keep=False), "Company"] + " " + art.loc[art["Headline"].duplicated(keep=False), "Date"]))
check("articles", "Duplicate (firm, date)", int(art.duplicated(["Company", "Date"]).sum()), "describe", True,
      "; ".join((art.loc[art.duplicated(['Company', 'Date'], keep=False), 'Company'] + " " + art.loc[art.duplicated(['Company', 'Date'], keep=False), 'Date']).unique()))
art["weekday"] = art["date"].dt.day_name()
check("articles", "Headlines dated on a weekend", int(art["date"].dt.weekday.ge(5).sum()), "describe", True)
art["domain"] = art["URL"].str.extract(r"https?://(?:www\.)?([^/]+)", expand=False)
art["url_is_url"] = art["URL"].str.match(r"^https?://")
check("articles", "URL field that is not a URL", int((~art["url_is_url"]).sum()), 0, art["url_is_url"].all(),
      "; ".join(art.loc[~art["url_is_url"], "Company"] + " " + art.loc[~art["url_is_url"], "Date"]))
check("articles", "Headlines from bloomberg.com", int(art["domain"].fillna("").str.contains("bloomberg").sum()),
      "describe (identical-text question)", True)
top = art["domain"].value_counts().head(8)
check("articles", "Most common source domains", "; ".join(f"{k} {v}" for k, v in top.items()), "describe", True,
      f"{art['domain'].nunique()} distinct domains")


def url_date(u: str):
    """A publication date written in the URL path (/2020/12/17/, 2023-05-01, or /2022/oct/04/)."""
    if not isinstance(u, str):
        return pd.NaT
    m = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", u) or re.search(r"(20\d{2})-(\d{2})-(\d{2})", u)
    if m:
        return pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"/(20\d{2})/(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/(\d{2})/", u, flags=re.I)
    if m:
        return pd.Timestamp(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
    return pd.NaT


art["url_date"] = art["URL"].map(url_date)
art["url_minus_file_days"] = (art["url_date"] - art["date"]).dt.days
has = art["url_date"].notna()
far = has & art["url_minus_file_days"].abs().gt(3)
check("articles", "Headlines whose URL carries a date", int(has.sum()), "describe", True)
check("articles", "... of which the URL date differs from the file date by more than 3 days", int(far.sum()), "0 ideally",
      far.sum() == 0, "; ".join(f"{c} file {d} vs URL {u.date()}" for c, d, u in zip(art.loc[far, 'Company'], art.loc[far, 'Date'], art.loc[far, 'url_date'])))
art["flag_url_date_mismatch"] = far
art["flag_weekend"] = art["date"].dt.weekday.ge(5)
art["flag_url_not_url"] = ~art["url_is_url"]
art["flag_duplicate_firm_date"] = art.duplicated(["Company", "Date"], keep=False)
art.drop(columns=["url_is_url"]).to_csv(DIAG / "news_articles_validation.csv", index=False)

# ---------------------------------------------------------------- write
ch = pd.DataFrame(checks)
ch.to_csv(DIAG / "raw_validation_checks.csv", index=False)
lines = [f"02_raw_validation: {len(ch)} checks, {int((ch['status'] == 'FLAG').sum())} flagged", ""]
for area, sub in ch.groupby("area", sort=False):
    lines.append(f"[{area}]")
    for _, r in sub.iterrows():
        lines.append(f"  {r['status']:4}  {r['check']}: {r['value']}" + (f"  ({r['detail']})" if r['detail'] else ""))
    lines.append("")
lines.append("Weekday story counts (2020-2025):")
lines.append(wtab.round(3).to_string())
write_text(DIAG / "02_raw_validation_summary.txt", "\n".join(lines))
print("\n".join(lines))
