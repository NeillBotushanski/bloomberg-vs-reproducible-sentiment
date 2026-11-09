"""05 Merge the analysis panel: point-in-time S&P 500 security-days, vendor signal, outcomes. Audited joins.

Unit: security-day (exchange ticker; one ticker per company per snapshot, checked in 02), NYSE trading days
2020-01-02 to 2025-12-31.
Membership rule (proposed P4): a security is in the universe on trading day t if it was a member at the latest
month-end snapshot strictly before t.
Signal timing (proposed P1): the vendor value dated t is known at 09:20 New York on t. Outcome columns are attached
for later use and labelled by whether they are tradable from that time:
  ret_oc_d0  open(t) -> close(t)            tradable from the value dated t
  ret_cc_d1  close(t) -> close(t+1)         tradable (more conservative)
  ret_cc_d0  close(t-1) -> close(t)         NOT tradable: starts before the value is known (timing diagnostics only)
No model is estimated here.

Outputs: data/analytic/panel_security_day.csv.gz, manifests/sample_attrition.csv,
         outputs/diagnostics/join_report.csv, outputs/diagnostics/05_merge_analysis_panel_summary.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ANALYTIC, DIAG, INTERIM, MANIFESTS, STUDY_END, STUDY_START, load_securities, load_universe,  # noqa: E402
                    trading_days, write_text)

td_all = trading_days()
td = td_all[(td_all >= STUDY_START) & (td_all <= STUDY_END)]
uni = load_universe()
sec = load_securities()

# ------------------------------------------------------------------ membership
snaps = np.array(sorted(uni["snapshot_date"].unique()), dtype="datetime64[ns]")
cal = pd.DataFrame({"date": td})
cal["snapshot_date"] = snaps[np.searchsorted(snaps, cal["date"].values.astype("datetime64[ns]"), side="left") - 1]
panel = cal.merge(uni, on="snapshot_date", how="left")
panel = panel.merge(sec[["ticker_exch", "composite_id_bb_global", "bics_industry_sector", "gics_sector_name"]],
                    on="ticker_exch", how="left")
assert not panel.duplicated(["date", "composite_id_bb_global"]).any(), "a company appears twice on one day"
attr = [("1", "Universe security-days: members at the latest month-end before each NYSE trading day, 2020-01-02 to 2025-12-31",
         "P4 (proposed)", panel["ticker_exch"].nunique(), len(panel))]

# ------------------------------------------------------------------ outcomes
out = pd.read_csv(INTERIM / "outcomes_daily.csv.gz", parse_dates=["date"])
out = out.sort_values(["ticker_exch", "date"])
out["ret_cc_next"] = out.groupby("ticker_exch")["ret_cc"].shift(-1)
nxt = pd.Series(td_all[1:], index=td_all[:-1])
out["next_date"] = out.groupby("ticker_exch")["date"].shift(-1)
out.loc[out["next_date"].ne(out["date"].map(nxt)), "ret_cc_next"] = np.nan
# Exchange switches (proposed P3): for the 18 companies with two exchange tickers, if the snapshot's ticker has no market
# row on day t but the company's other ticker does (e.g. WMT UN -> WMT UW on 2025-12-09), use the other ticker that day.
have = set(zip(out.loc[out["px_last"].notna(), "ticker_exch"], out.loc[out["px_last"].notna(), "date"]))   # rows with a price
alts = sec.groupby("composite_id_bb_global")["ticker_exch"].agg(list)
panel["ticker_as_member"] = panel["ticker_exch"]
switch = 0
for i in panel.index[[(t, d) not in have for t, d in zip(panel["ticker_exch"], panel["date"])]]:
    for alt in alts[panel.at[i, "composite_id_bb_global"]]:
        if alt != panel.at[i, "ticker_exch"] and (alt, panel.at[i, "date"]) in have:
            panel.at[i, "ticker_exch"] = alt
            switch += 1
            break
attr.append(("1b", "... of which the company's other exchange ticker is used that day (exchange switch)", "P3 (proposed)",
             int(panel.loc[panel["ticker_exch"] != panel["ticker_as_member"], "composite_id_bb_global"].nunique()), switch))
o = out[["ticker_exch", "date", "ret_cc", "ret_oc", "ret_cc_next", "px_last", "cur_mkt_cap_musd", "dollar_volume_musd"]].rename(
    columns={"ret_cc": "ret_cc_d0", "ret_oc": "ret_oc_d0", "ret_cc_next": "ret_cc_d1"})
before = len(panel)
panel = panel.merge(o, on=["ticker_exch", "date"], how="left", indicator="_m_out")
span = out.groupby("ticker_exch")["date"].agg(first_mkt="min", last_mkt="max")
um = panel.loc[panel["_m_out"] == "left_only", ["ticker_exch", "date"]].join(span, on="ticker_exch")
reasons = np.select([um["date"] > um["last_mkt"], um["date"] < um["first_mkt"]],
                    ["after the last Bloomberg market row (delisted or acquired during the month)",
                     "before the first Bloomberg market row (new listing or spin-off)"], "gap inside the security's own series")
unmatched_reasons = pd.Series(reasons).value_counts()
join_rows = [{"join": "universe security-days -> outcomes_daily (ticker_exch, date)", "left_rows": before,
              "matched": int((panel["_m_out"] == "both").sum()), "unmatched": int((panel["_m_out"] == "left_only").sum()),
              "many_to_many": 0}]
attr.append(("2", "... with a Bloomberg market row", "", panel.loc[panel["_m_out"] == "both", "ticker_exch"].nunique(),
             int((panel["_m_out"] == "both").sum())))
attr.append(("3", "... with a close price on the day", "", panel.loc[panel["px_last"].notna(), "ticker_exch"].nunique(),
             int(panel["px_last"].notna().sum())))
attr.append(("4", "... with both same-day returns (ret_cc_d0 and ret_oc_d0)", "",
             panel.loc[panel[["ret_cc_d0", "ret_oc_d0"]].notna().all(axis=1), "ticker_exch"].nunique(),
             int(panel[["ret_cc_d0", "ret_oc_d0"]].notna().all(axis=1).sum())))

# ------------------------------------------------------------------ vendor signal dated t
sig = pd.read_csv(INTERIM / "vendor_news_signals.csv.gz", parse_dates=["date", "first_tradable_day"])
s = sig[sig["is_trading_day"]].drop(columns=["is_trading_day", "first_tradable_day", "value_known_at"])
before = len(panel)
panel = panel.merge(s, on=["ticker_exch", "date"], how="left", indicator="_m_sig")
join_rows.append({"join": "universe security-days -> vendor signal dated the same trading day", "left_rows": before,
                  "matched": int((panel["_m_sig"] == "both").sum()), "unmatched": int((panel["_m_sig"] == "left_only").sum()),
                  "many_to_many": int(len(panel) - before)})
# holiday values: count how many fall between the previous trading day and t (known before t's open, not merged)
hol = sig[~sig["is_trading_day"]].groupby(["ticker_exch", "first_tradable_day"]).size().rename("n_holiday_values_before")
panel = panel.merge(hol, left_on=["ticker_exch", "date"], right_index=True, how="left")
panel["n_holiday_values_before"] = panel["n_holiday_values_before"].fillna(0).astype(int)
has = panel["has_sentiment"].astype("boolean").fillna(False).astype(bool)
attr.append(("5", "Universe security-days with a vendor news row (any field)", "",
             panel.loc[panel["_m_sig"] == "both", "ticker_exch"].nunique(), int((panel["_m_sig"] == "both").sum())))
attr.append(("6", "... with a vendor sentiment value (NEWS_SENTIMENT_DAILY_AVG)", "", panel.loc[has, "ticker_exch"].nunique(),
             int(has.sum())))
attr.append(("7", "... with sentiment and a same-day open-to-close return (ret_oc_d0)", "",
             panel.loc[has & panel["ret_oc_d0"].notna(), "ticker_exch"].nunique(), int((has & panel["ret_oc_d0"].notna()).sum())))
attr.append(("8", "... with sentiment and a next-day close-to-close return (ret_cc_d1)", "",
             panel.loc[has & panel["ret_cc_d1"].notna(), "ticker_exch"].nunique(), int((has & panel["ret_cc_d1"].notna()).sum())))

# ------------------------------------------------------------------ the headline subset
art = pd.read_csv(INTERIM / "articles_clean.csv", parse_dates=["Date", "vendor_date_if_before_0920", "vendor_date_if_after_0920",
                                                                "first_tradable_day_conservative"])
art = art[art["Date"].between(STUDY_START, STUDY_END)]
a_attr = [("A1", "Headlines in News_Articles.csv dated 2020-2025", "", art["Company"].nunique(), len(art))]
mem = art["member_at_date"].astype(bool)
a_attr.append(("A2", "... firm was an S&P 500 member at the headline date", "", art.loc[mem, "Company"].nunique(), int(mem.sum())))
sent = sig.set_index(["ticker_exch", "date"])["has_sentiment"]


def lookup(t, d):
    return bool(sent.get((t, d), False)) if pd.notna(d) and isinstance(t, str) else False


art["vendor_sent_same_day"] = [lookup(t, d) for t, d in zip(art["ticker_exch"], art["vendor_date_if_before_0920"])]
art["vendor_sent_next_weekday"] = [lookup(t, d) for t, d in zip(art["ticker_exch"], art["vendor_date_if_after_0920"])]
either = art["vendor_sent_same_day"] | art["vendor_sent_next_weekday"]
bothv = art["vendor_sent_same_day"] & art["vendor_sent_next_weekday"]
a_attr.append(("A3", "... with a vendor sentiment value on at least one candidate date (d or next weekday)", "",
               art.loc[mem & either, "Company"].nunique(), int((mem & either).sum())))
a_attr.append(("A4", "... with a vendor value on both candidate dates (assignment of the story is ambiguous)", "",
               art.loc[mem & bothv, "Company"].nunique(), int((mem & bothv).sum())))
oc = out.set_index(["ticker_exch", "date"])["ret_oc"]
art["ret_oc_first_tradable"] = [oc.get((t, d), np.nan) if isinstance(t, str) else np.nan
                                for t, d in zip(art["ticker_exch"], art["first_tradable_day_conservative"])]
ok = mem & art["ret_oc_first_tradable"].notna()
a_attr.append(("A5", "... with a return from the open of the first trading day after the headline date (conservative cutoff)",
               "S2 (supervisor)", art.loc[ok, "Company"].nunique(), int(ok.sum())))
clean = ok & ~art["flag_url_date_mismatch"].astype(bool) & ~art["flag_url_not_url"].astype(bool)
a_attr.append(("A6", "... excluding headlines with a date or URL problem flagged in 02", "", art.loc[clean, "Company"].nunique(),
               int(clean.sum())))
art.to_csv(INTERIM / "articles_aligned.csv", index=False, date_format="%Y-%m-%d")

# ------------------------------------------------------------------ write
panel = panel.drop(columns=["_m_out", "_m_sig"])
panel["year"] = panel["date"].dt.year
panel.to_csv(ANALYTIC / "panel_security_day.csv.gz", index=False, date_format="%Y-%m-%d",
             compression={"method": "gzip", "mtime": 0})   # mtime 0: identical bytes on every rebuild
attrition = pd.DataFrame(attr + a_attr, columns=["step", "rule", "decision", "securities_or_firms", "security_days_or_headlines"])
# Each row is counted against an explicit parent row (not simply the row above).
parent = {"1b": "1", "2": "1", "3": "2", "4": "3", "5": "1", "6": "5", "7": "6", "8": "6",
          "A2": "A1", "A3": "A2", "A4": "A3", "A5": "A2", "A6": "A5"}
attrition["parent_step"] = attrition["step"].map(parent).fillna("")
cnt = attrition.set_index("step")["security_days_or_headlines"]
attrition["dropped_vs_parent"] = [cnt[p] - c if p else np.nan for p, c in zip(attrition["parent_step"], attrition["security_days_or_headlines"])]
attrition.loc[attrition["step"] == "1b", "dropped_vs_parent"] = np.nan    # a re-labelling, not a drop
attrition["notes"] = ""
attrition.loc[attrition["step"] == "8", "notes"] = "Main vendor-signal sample for later work; nothing is estimated at checkpoint 1."
attrition.loc[attrition["step"] == "A5", "notes"] = "Primary identical-text sample (S2 fallback; decision D1)."
attrition.to_csv(MANIFESTS / "sample_attrition.csv", index=False)
jr = pd.DataFrame(join_rows)
jr["unmatched_reasons"] = ["; ".join(f"{k}: {v}" for k, v in unmatched_reasons.items()), ""]
jr.to_csv(DIAG / "join_report.csv", index=False)
lines = ["05_merge_analysis_panel",
         f"panel_security_day.csv.gz: {len(panel):,} rows, {panel['ticker_exch'].nunique()} securities, {panel['date'].nunique()} trading days",
         f"  security-days with a holiday-dated vendor value just before them (not merged, counted): {(panel['n_holiday_values_before'] > 0).sum():,}",
         "", "Sample attrition:", attrition.to_string(index=False), "", "Join report:", pd.DataFrame(join_rows).to_string(index=False),
         "Universe security-days with no market row, by reason:", unmatched_reasons.to_string(),
         f"Securities in the snapshots but never in the 2020-2025 panel (their first membership is the 2025-12-31 snapshot): "
         f"{', '.join(sorted(set(uni['ticker_exch']) - set(panel['ticker_exch'])))}"]
write_text(DIAG / "05_merge_analysis_panel_summary.txt", "\n".join(lines))
print("\n".join(lines))
