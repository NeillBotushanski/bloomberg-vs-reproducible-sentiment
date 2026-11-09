"""03 Build signals: the vendor's daily news fields and the 188 headlines, with their information timing.
No outcome (return) is read here.

Timing facts used (FLDS, recorded on the terminal 2026-11-06; design_decisions.md section 5.2):
  * NEWS_SENTIMENT_DAILY_AVG and the story counts dated D are published 10 minutes before the US open on D
    and cover the previous 24 hours. A value dated D is therefore known at about 09:20 New York time on D.
  * Values also exist on weekday market holidays; none exist on Saturday or Sunday.
  * NEWS_HEAT_* fields update at local midnight on a different clock (not used for timing).

Outputs
  data/interim/vendor_news_signals.csv.gz   one row per security and value date, with first_tradable_day
  data/interim/articles_clean.csv           one row per headline, mapped to a Bloomberg ticker, with the
                                            candidate vendor dates and the conservative first tradable day
  outputs/diagnostics/03_build_signals_summary.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DIAG, INTERIM, NEWS_FIELDS, load_articles, load_news, load_securities, load_universe, trading_days, write_text  # noqa: E402

td = trading_days()
td_arr = td.values


def next_trading_day_on_or_after(dates: pd.Series) -> pd.Series:
    pos = np.searchsorted(td_arr, dates.values.astype("datetime64[ns]"), side="left")
    out = pd.Series(pd.NaT, index=dates.index, dtype="datetime64[ns]")
    ok = pos < len(td_arr)
    out[ok] = td_arr[pos[ok]]
    return out


def next_trading_day_after(dates: pd.Series) -> pd.Series:
    pos = np.searchsorted(td_arr, dates.values.astype("datetime64[ns]"), side="right")
    out = pd.Series(pd.NaT, index=dates.index, dtype="datetime64[ns]")
    ok = pos < len(td_arr)
    out[ok] = td_arr[pos[ok]]
    return out


# ------------------------------------------------------------------ vendor signals
news = load_news()
news["value_known_at"] = news["date"].dt.strftime("%Y-%m-%d") + " 09:20 America/New_York"
news["is_trading_day"] = news["date"].isin(td)
# A value dated on a holiday is known before that (closed) day; its first use is the next trading day's open.
news["first_tradable_day"] = next_trading_day_on_or_after(news["date"])
tone = news[["news_pos_sentiment_count", "news_neg_sentiment_count", "news_neutral_sentiment_count"]].sum(axis=1, min_count=3)
news["scored_story_count"] = tone
news["has_sentiment"] = news["news_sentiment_daily_avg"].notna()
cols = ["ticker_exch", "date", "is_trading_day", "first_tradable_day", "value_known_at", *NEWS_FIELDS,
        "scored_story_count", "has_sentiment"]
news[cols].to_csv(INTERIM / "vendor_news_signals.csv.gz", index=False, date_format="%Y-%m-%d",
                  compression={"method": "gzip", "mtime": 0})   # mtime 0: identical bytes on every rebuild

# ------------------------------------------------------------------ the 188 headlines
art = load_articles()
art.insert(0, "article_id", [f"A{i:03d}" for i in range(1, len(art) + 1)])   # file order, frozen
art["date"] = pd.to_datetime(art["Date"])
sec = load_securities()
uni = load_universe()
sec["root"] = sec["ticker_exch"].str.split(" ").str[0]
# Map the file's ticker to the Bloomberg exchange ticker that was an index member on the latest month-end before
# the headline date (point-in-time; one exchange ticker per company per snapshot, checked in 02).
snap_dates = np.array(sorted(uni["snapshot_date"].unique()), dtype="datetime64[ns]")
art_snap = snap_dates[np.searchsorted(snap_dates, art["date"].values.astype("datetime64[ns]"), side="left") - 1]
art["membership_snapshot"] = art_snap
members = uni.merge(sec[["ticker_exch", "root", "composite_id_bb_global"]], on="ticker_exch")
m = art.merge(members, left_on=["Company", "membership_snapshot"], right_on=["root", "snapshot_date"], how="left")
art["ticker_exch"] = m["ticker_exch"].values
art["composite_id_bb_global"] = m["composite_id_bb_global"].values
art["member_at_date"] = art["ticker_exch"].notna()
# Firms not matched by ticker root at that snapshot: fall back to any exchange ticker with that root (reported).
fallback = sec.drop_duplicates("root").set_index("root")["ticker_exch"]
art["ticker_exch_any"] = art["ticker_exch"].fillna(art["Company"].map(fallback))

# Candidate vendor dates. Publication time is unknown (the file has dates only). A story at time t on date d is in
# the value dated d if t <= 09:20, otherwise in the value dated the next weekday (none for Fri after 09:20 or Sat).
wd = art["date"].dt.weekday
art["vendor_date_if_before_0920"] = art["date"].where(wd < 5)          # Sat/Sun: no value dated that day
nxt = art["date"] + pd.to_timedelta(np.select([wd <= 3, wd == 4, wd == 5, wd == 6], [1, 3, 2, 1]), unit="D")
art["vendor_date_if_after_0920"] = nxt.where(wd.isin([0, 1, 2, 3, 6]))  # Fri after 09:20 and all of Sat: no value
art["vendor_window_note"] = np.select(
    [wd <= 3, wd == 4, wd == 5, wd == 6],
    ["Mon-Thu: value dated d (if before 09:20) or d+1 (after)",
     "Friday: value dated Fri (if before 09:20); after 09:20 no daily value covers it",
     "Saturday: no daily value covers it",
     "Sunday: Monday's value covers it only if after 09:20"], default="")
# Conservative return cutoff (supervisor, S2): the headline is assumed known only after the end of its date, so the
# first tradable moment is the open of the first trading day strictly after the file date.
art["first_tradable_day_conservative"] = next_trading_day_after(art["date"])
v = load_validation = pd.read_csv(DIAG / "news_articles_validation.csv", usecols=["Company", "Date", "domain", "url_date",
                                                                                   "flag_url_date_mismatch", "flag_weekend",
                                                                                   "flag_url_not_url"])
art = art.merge(v, on=["Company", "Date"], how="left")
out_cols = ["article_id", "Company", "Date", "Headline", "URL", "domain", "url_date", "ticker_exch", "ticker_exch_any",
            "composite_id_bb_global", "membership_snapshot", "member_at_date", "vendor_date_if_before_0920",
            "vendor_date_if_after_0920", "vendor_window_note", "first_tradable_day_conservative",
            "flag_url_date_mismatch", "flag_weekend", "flag_url_not_url"]
art[out_cols].to_csv(INTERIM / "articles_clean.csv", index=False, date_format="%Y-%m-%d")

lines = [
    "03_build_signals",
    f"vendor_news_signals.csv.gz: {len(news):,} security-days; {news['ticker_exch'].nunique()} securities; "
    f"{news['date'].min().date()} to {news['date'].max().date()}",
    f"  values dated on market holidays: {(~news['is_trading_day']).sum():,} (first_tradable_day = next trading day)",
    f"  rows with a sentiment value: {news['has_sentiment'].sum():,}",
    "",
    f"articles_clean.csv: {len(art)} headlines, {art['Company'].nunique()} firms",
    f"  mapped to an index member at the headline date: {art['member_at_date'].sum()} "
    f"(not a member: {', '.join((art.loc[~art['member_at_date'], 'Company'] + ' ' + art.loc[~art['member_at_date'], 'Date']).tolist()) or 'none'})",
    "  headlines by weekday: " + "; ".join(f"{k} {v}" for k, v in art["date"].dt.day_name().value_counts().items()),
    f"  no daily vendor value can contain the story if it was published after 09:20 on a Friday, or on a Saturday: "
    f"{int((wd == 4).sum())} Friday and {int((wd == 5).sum())} Saturday headlines are exposed",
]
write_text(DIAG / "03_build_signals_summary.txt", "\n".join(lines))
print("\n".join(lines))
