"""06 Descriptive diagnostics for checkpoint 1: coverage, missingness, distributions, timing. Descriptive only:
no return is regressed on any signal and no forecast is evaluated (the guide forbids a primary test here).

Tables (outputs/tables):  coverage_by_year.csv, coverage_by_size_quintile.csv, coverage_by_sector.csv,
                          vendor_field_summary.csv, headline_coverage_by_firm.csv, headline_coverage_by_year.csv,
                          return_summary.csv
Figures (outputs/figures): fig1_vendor_coverage.png (the preliminary descriptive figure),
                           fig2_timing_window.png (the main data-quality risk), fig3_sentiment_distribution.png
Summary: outputs/diagnostics/06_descriptive_diagnostics_summary.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ANALYTIC, DIAG, FIGS, INTERIM, TABLES, trading_days, write_text  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
NAVY, ORANGE, GREY, GREEN = "#1F3864", "#C55A11", "#7F7F7F", "#548235"
layout_log: list[str] = []


def layout_check(fig, name):
    """Report drawn text that runs off the figure or overlaps other drawn text."""
    fig.canvas.draw()
    rnd = fig.canvas.get_renderer()
    texts = []
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tk in axis._update_ticks():                      # only ticks inside the view are drawn
                texts += [lab for lab in (tk.label1, tk.label2) if lab.get_visible() and lab.get_text()]
            if axis.label.get_text():
                texts.append(axis.label)
        texts += [t for t in (ax.title, ax._left_title, ax._right_title) if t.get_text()]
        if ax.get_legend():
            texts += list(ax.get_legend().get_texts())
    texts += [t for t in fig.texts if t.get_text()]
    if getattr(fig, "_suptitle", None) is not None:
        texts.append(fig._suptitle)
    texts = list({id(t): t for t in texts}.values())          # the suptitle is also in fig.texts
    tb, fb = fig.get_tightbbox(rnd), fig.bbox_inches
    issues = []
    if tb.x0 < fb.x0 - 0.01 or tb.y0 < fb.y0 - 0.01 or tb.x1 > fb.x1 + 0.01 or tb.y1 > fb.y1 + 0.01:
        issues.append(f"content extends beyond the figure: {tb} vs {fb}")
    boxes = [(t.get_text()[:30].replace("\n", " "), t.get_window_extent(rnd)) for t in texts]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a_, b_ = boxes[i][1], boxes[j][1]
            ov = max(0, min(a_.x1, b_.x1) - max(a_.x0, b_.x0)) * max(0, min(a_.y1, b_.y1) - max(a_.y0, b_.y0))
            if ov > 4:
                issues.append(f"overlap: '{boxes[i][0]}' / '{boxes[j][0]}'")
    layout_log.append(f"{name}: " + ("no text overflow or overlap" if not issues else "; ".join(issues[:12])))

p = pd.read_csv(ANALYTIC / "panel_security_day.csv.gz", parse_dates=["date"], low_memory=False)
p["has_sentiment"] = p["has_sentiment"].astype("boolean").fillna(False).astype(bool)
p["has_news_row"] = p["news_publication_count"].notna() | p["has_sentiment"]
p["has_scored"] = p["scored_story_count"].fillna(0) > 0
s = p["news_sentiment_daily_avg"]

# ------------------------------------------------------------------ T1 coverage by year
def cov(g):
    ss = g["news_sentiment_daily_avg"]
    return pd.Series({
        "trading_days": g["date"].nunique(),
        "avg_members_per_day": len(g) / g["date"].nunique(),
        "securities": g["ticker_exch"].nunique(),
        "security_days": len(g),
        "pct_with_vendor_row": g["has_news_row"].mean() * 100,
        "pct_with_sentiment": g["has_sentiment"].mean() * 100,
        "pct_with_scored_story": g["has_scored"].mean() * 100,
        "mean_publication_count": g["news_publication_count"].mean(),
        "median_publication_count": g["news_publication_count"].median(),
        "mean_scored_stories": g["scored_story_count"].mean(),
        "sentiment_mean": ss.mean(), "sentiment_sd": ss.std(),
        "sentiment_p05": ss.quantile(.05), "sentiment_p50": ss.median(), "sentiment_p95": ss.quantile(.95),
        "pct_sentiment_exactly_0": (ss == 0).mean() / ss.notna().mean() * 100 if ss.notna().any() else np.nan,
    })


t1 = p.groupby("year").apply(cov, include_groups=False)
t1.loc["2020-2025"] = cov(p)
t1.round(4).to_csv(TABLES / "coverage_by_year.csv")

# ------------------------------------------------------------------ T2 size quintiles (cap on the first trading day of each month)
p["month"] = p["date"].dt.to_period("M")
first = p.sort_values("date").groupby(["month", "ticker_exch"])["cur_mkt_cap_musd"].first().rename("cap_month_start")
p = p.join(first, on=["month", "ticker_exch"])
p["size_quintile"] = p.groupby("month")["cap_month_start"].transform(lambda x: pd.qcut(x, 5, labels=[1, 2, 3, 4, 5]))
t2 = p.groupby("size_quintile", observed=True).apply(lambda g: pd.Series({
    "security_days": len(g), "median_cap_musd": g["cap_month_start"].median(),
    "pct_with_sentiment": g["has_sentiment"].mean() * 100, "mean_publication_count": g["news_publication_count"].mean(),
    "mean_scored_stories": g["scored_story_count"].mean(), "sentiment_mean": g["news_sentiment_daily_avg"].mean()}),
    include_groups=False)
t2.index = ["Q1 (smallest)", "Q2", "Q3", "Q4", "Q5 (largest)"]
t2.round(4).to_csv(TABLES / "coverage_by_size_quintile.csv")

# ------------------------------------------------------------------ T3 sector (BICS, current classification)
t3 = p.groupby("bics_industry_sector").apply(lambda g: pd.Series({
    "securities": g["ticker_exch"].nunique(), "security_days": len(g), "pct_with_sentiment": g["has_sentiment"].mean() * 100,
    "mean_publication_count": g["news_publication_count"].mean(), "sentiment_mean": g["news_sentiment_daily_avg"].mean()}),
    include_groups=False).sort_values("security_days", ascending=False)
t3.round(4).to_csv(TABLES / "coverage_by_sector.csv")

# ------------------------------------------------------------------ T4 field summaries
fields = ["news_sentiment_daily_avg", "news_publication_count", "news_pos_sentiment_count", "news_neg_sentiment_count",
          "news_neutral_sentiment_count", "scored_story_count", "news_heat_pub_davg", "news_heat_read_dmax"]
t4 = p[fields].describe(percentiles=[.01, .05, .5, .95, .99]).T
t4.insert(0, "pct_missing", p[fields].isna().mean() * 100)
t4.round(4).to_csv(TABLES / "vendor_field_summary.csv")
r = p[["ret_cc_d0", "ret_oc_d0", "ret_cc_d1"]].describe(percentiles=[.01, .5, .99]).T
r.round(5).to_csv(TABLES / "return_summary.csv")

# ------------------------------------------------------------------ T5/T6 the 188 headlines
a = pd.read_csv(INTERIM / "articles_aligned.csv", parse_dates=["Date"])
a["year"] = a["Date"].dt.year
for c in ["member_at_date", "vendor_sent_same_day", "vendor_sent_next_weekday", "flag_url_date_mismatch", "flag_url_not_url"]:
    a[c] = a[c].astype(bool)
a["neither"] = ~(a["vendor_sent_same_day"] | a["vendor_sent_next_weekday"])
agg = dict(headlines=("article_id", "size"), first=("Date", "min"), last=("Date", "max"),
           member_at_date=("member_at_date", "sum"), vendor_value_same_day=("vendor_sent_same_day", "sum"),
           vendor_value_next_weekday=("vendor_sent_next_weekday", "sum"), no_vendor_value=("neither", "sum"),
           return_available=("ret_oc_first_tradable", lambda x: x.notna().sum()),
           date_or_url_flag=("flag_url_date_mismatch", "sum"))
t5 = a.groupby("Company").agg(**agg).sort_values("headlines", ascending=False)
t5.loc["All 19 firms"] = [len(a), a["Date"].min(), a["Date"].max(), a["member_at_date"].sum(), a["vendor_sent_same_day"].sum(),
                          a["vendor_sent_next_weekday"].sum(), a["neither"].sum(), a["ret_oc_first_tradable"].notna().sum(),
                          a["flag_url_date_mismatch"].sum()]
t5["first"] = pd.to_datetime(t5["first"]).dt.date
t5["last"] = pd.to_datetime(t5["last"]).dt.date
t5.to_csv(TABLES / "headline_coverage_by_firm.csv")
t6 = a.groupby("year").agg(headlines=("article_id", "size"), firms=("Company", "nunique"),
                           vendor_value_same_day=("vendor_sent_same_day", "sum"))
member_days = p.groupby("year").size()
t6["share_of_member_security_days_pct"] = t6["headlines"] / member_days * 100
t6.round(4).to_csv(TABLES / "headline_coverage_by_year.csv")
firms19 = set(a["ticker_exch"].dropna())
p19 = p[p["ticker_exch"].isin(firms19)]

# ------------------------------------------------------------------ Figure 1: coverage over time (preliminary descriptive figure)
m = p.groupby("month").agg(share_sent=("has_sentiment", "mean"), members=("ticker_exch", "size"),
                           scored=("scored_story_count", "median"), pub=("news_publication_count", "median"))
m.index = m.index.to_timestamp()
m19_tab = p19.groupby("month")["has_sentiment"].mean()
m19_tab.index = m19_tab.index.to_timestamp()
m.assign(share_sent_19_firms=m19_tab).rename_axis("month").to_csv(TABLES / "coverage_by_month.csv", date_format="%Y-%m")
fig, ax = plt.subplots(2, 1, figsize=(8.5, 6), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
ax[0].plot(m.index, m["share_sent"] * 100, color=NAVY, lw=1.8, label="All point-in-time S&P 500 members")
m19 = p19.groupby("month")["has_sentiment"].mean()
m19.index = m19.index.to_timestamp()
ax[0].plot(m19.index, m19 * 100, color=ORANGE, lw=1.2, ls="--", label="The 19 firms in News_Articles.csv")
ax[0].vlines(a["Date"], 0, 6, color=GREY, lw=0.6, label="Dates of the 188 headlines")
ax[0].set_ylim(0, 105)
ax[0].set_ylabel("% of security-days with a\nvendor sentiment value")
ax[0].legend(loc="lower right", frameon=False, fontsize=8)
ax[0].set_title("A. Coverage of Bloomberg NEWS_SENTIMENT_DAILY_AVG (monthly share of member security-days)", loc="left", fontsize=9)
ax[1].plot(m.index, m["pub"], color=NAVY, lw=1.5, label="Median publication count (all stories)")
ax[1].plot(m.index, m["scored"], color=GREEN, lw=1.5, label="Median scored stories (positive + negative + neutral)")
ax[1].set_ylabel("Stories per security-day")
ax[1].legend(loc="upper left", frameon=False, fontsize=8)
ax[1].set_title("B. Story counts behind the score (monthly medians)", loc="left", fontsize=9)
fig.suptitle("Figure 1. Vendor news coverage of the point-in-time S&P 500, 2020-2025 (daily, NYSE trading days)", x=0.01, ha="left",
             fontsize=10, fontweight="bold")
fig.text(0.01, 0.005, f"Sample: {len(p):,} security-days, {p['ticker_exch'].nunique()} securities, {p['date'].nunique()} trading days. "
         "Member = in the latest month-end snapshot before the day. Value dated D covers the 24h to 09:20 New York on D.\n"
         "Source: Bloomberg BDH pull 2026-11-06 (NEWS_SENTIMENT_DAILY_AVG NW020, NEWS_PUBLICATION_COUNT NW043, NW044-46); RiskLab News_Articles.csv.",
         fontsize=6.5, color=GREY)
fig.tight_layout(rect=(0, 0.05, 1, 0.96), h_pad=2.2)
layout_check(fig, "fig1_vendor_coverage")
fig.savefig(FIGS / "fig1_vendor_coverage.png")
plt.close(fig)

# ------------------------------------------------------------------ Figure 2: the timing window (main data-quality risk)
sig = pd.read_csv(INTERIM / "vendor_news_signals.csv.gz", parse_dates=["date"],
                  usecols=["date", "is_trading_day", "news_publication_count", "scored_story_count", "has_sentiment"])
sig = sig[sig["date"].between("2020-01-01", "2025-12-31")]
sig["kind"] = np.where(~sig["is_trading_day"], "Holiday\n(weekday)", sig["date"].dt.day_name().str[:3])
order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Holiday\n(weekday)"]
w = sig.groupby("kind").agg(pub=("news_publication_count", "mean"), scored=("scored_story_count", "mean"),
                            share=("has_sentiment", "mean")).reindex(order)
w.to_csv(TABLES / "vendor_counts_by_value_day.csv")
fig, ax = plt.subplots(1, 2, figsize=(9, 3.6), gridspec_kw={"width_ratios": [1.25, 1]})
x = np.arange(len(order))
ax[0].bar(x - 0.2, w["pub"], 0.4, color=NAVY, label="Publication count (all stories)")
ax[0].bar(x + 0.2, w["scored"], 0.4, color=GREEN, label="Scored stories")
ax[0].set_xticks(x, order)
ax[0].set_ylabel("Mean stories per security-day")
ax[0].legend(frameon=False, fontsize=7.5)
ax[0].set_title("A. Stories in the value dated each day\n(24h window to 09:20 New York)", loc="left", fontsize=9)
cat = np.select([a["neither"], a["vendor_sent_same_day"] & a["vendor_sent_next_weekday"], a["vendor_sent_same_day"]],
                ["No vendor value can contain it", "Two candidate values (ambiguous)", "Same-day value only"],
                "Next-weekday value only")
ct = pd.crosstab(a["Date"].dt.day_name().str[:3], cat).reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]).fillna(0)
ct.rename_axis("weekday").to_csv(TABLES / "headline_weekday_by_vendor_value.csv")
cols = {"Two candidate values (ambiguous)": ORANGE, "Same-day value only": NAVY, "Next-weekday value only": GREEN,
        "No vendor value can contain it": GREY}
bottom = np.zeros(len(ct))
for c, col in cols.items():
    if c in ct:
        ax[1].bar(ct.index, ct[c], bottom=bottom, color=col, label=c)
        bottom += ct[c].values
ax[1].set_ylabel("Headlines")
ax[1].legend(frameon=False, fontsize=7)
ax[1].set_title("B. The 188 headlines by weekday: which vendor\nvalue could contain the story", loc="left", fontsize=9)
fig.suptitle("Figure 2. Timing: Monday and holiday values cover one quiet day; Friday-after-09:20 and Saturday news fall in no value",
             x=0.01, ha="left", fontsize=9.5, fontweight="bold")
fig.text(0.01, 0.01, "2020-2025, all 635 securities' vendor rows. Headline publication times are unknown, so a weekday story can sit in "
         "the value dated that day (before 09:20) or the next weekday (after).", fontsize=6.5, color=GREY)
fig.tight_layout(rect=(0, 0.04, 1, 0.92))
layout_check(fig, "fig2_timing_window")
fig.savefig(FIGS / "fig2_timing_window.png")
plt.close(fig)

# ------------------------------------------------------------------ Figure 3: distribution of the vendor score
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
ax[0].hist(s.dropna(), bins=np.linspace(-1, 1, 81), color=NAVY)
ax[0].set_yscale("log")
ax[0].set_xlabel("NEWS_SENTIMENT_DAILY_AVG")
ax[0].set_ylabel("Security-days (log scale)")
ax[0].set_title(f"A. Distribution ({s.notna().sum():,} values; {(s == 0).mean() / s.notna().mean():.0%} exactly 0)", loc="left", fontsize=9)
mm = s.notna() & (p["scored_story_count"] > 0)
ratio = ((p["news_pos_sentiment_count"] - p["news_neg_sentiment_count"]) / p["scored_story_count"])[mm]
hb = ax[1].hexbin(ratio, s[mm], gridsize=50, bins="log", cmap="Blues", mincnt=1)
ax[1].set_xlabel("(positive - negative) / scored stories")
ax[1].set_ylabel("NEWS_SENTIMENT_DAILY_AVG")
rho = np.corrcoef(ratio, s[mm])[0, 1]
ax[1].set_title(f"B. Vendor score vs a simple count ratio (corr {rho:.2f})", loc="left", fontsize=9)
fig.colorbar(hb, ax=ax[1], label="log10 count")
fig.suptitle("Figure 3. The vendor score: point-in-time S&P 500 security-days, 2020-2025", x=0.01, ha="left", fontsize=10, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.93))
layout_check(fig, "fig3_sentiment_distribution")
fig.savefig(FIGS / "fig3_sentiment_distribution.png")
plt.close(fig)

# ------------------------------------------------------------------ summary
lines = ["06_descriptive_diagnostics (descriptive only; nothing estimated)", "",
         "Coverage by year:", t1.round(3).to_string(), "",
         "Coverage by size quintile (market cap at the start of each month):", t2.round(3).to_string(), "",
         "Vendor counts by the day the value is dated (2020-2025):", w.round(3).to_string(), "",
         "The 188 headlines:", t5.to_string(), "",
         f"Headlines with a vendor value on both candidate dates (ambiguous): {(a['vendor_sent_same_day'] & a['vendor_sent_next_weekday']).sum()}",
         f"Headlines' share of all member security-days 2020-2025: {len(a) / len(p) * 100:.4f}%",
         f"The 19 headline firms account for {len(p19):,} member security-days; headlines cover {len(a) / len(p19) * 100:.2f}% of them."]
lines += ["", "Figure layout check:", *layout_log]
write_text(DIAG / "06_descriptive_diagnostics_summary.txt", "\n".join(lines))
print("\n".join(lines))
