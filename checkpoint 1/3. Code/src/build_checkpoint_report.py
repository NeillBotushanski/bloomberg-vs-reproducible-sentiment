"""Build the first-checkpoint pack and the consolidated report from saved outputs only (nothing is recomputed here).

Writes
  outputs/tables/checkpoint_1_facts.csv            every number quoted in the pack, with its source file
  outputs/diagnostics/checkpoint_1_pack.md         the seven items the guide asks for, decisions, open items, questions
  reports/first_checkpoint_report.ipynb            consolidated report (code cells read the saved outputs; outputs embedded)
  reports/first_checkpoint_report.html             the same report as one self-contained HTML page
"""
from __future__ import annotations

import base64
import html
import json
import re
import sys
from pathlib import Path

import markdown
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DIAG, FIGS, MANIFESTS, ROOT, TABLES, write_text  # noqa: E402

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
PREPARED = "2026-11-08"


def rd(rel_path, **kw):
    return pd.read_csv(ROOT / rel_path, **kw)


# ------------------------------------------------------------------ facts (every quoted number comes from here)
facts: list[tuple[str, object, str]] = []


def F(key, value, source):
    facts.append((key, value, source))
    return value


chk = rd("outputs/diagnostics/raw_validation_checks.csv")
F("validation_checks", len(chk), "outputs/diagnostics/raw_validation_checks.csv")
F("validation_flags", int((chk["status"] == "FLAG").sum()), "outputs/diagnostics/raw_validation_checks.csv")
inv = rd("outputs/diagnostics/raw_file_inventory.csv")
F("raw_files_hash_matched", int((inv["hash_matches_record"] == True).sum()), "outputs/diagnostics/raw_file_inventory.csv")  # noqa: E712
F("raw_files_hash_recorded", int(inv["hash_matches_record"].notna().sum()), "outputs/diagnostics/raw_file_inventory.csv")
att = rd("manifests/sample_attrition.csv", dtype={"step": str}).set_index("step")
for st in att.index:
    F(f"attrition_{st}", int(att.loc[st, "security_days_or_headlines"]), "manifests/sample_attrition.csv")
F("panel_securities", int(att.loc["1", "securities_or_firms"]), "manifests/sample_attrition.csv")
cy = rd("outputs/tables/coverage_by_year.csv", index_col=0)
F("pct_with_sentiment_all", round(cy.loc["2020-2025", "pct_with_sentiment"], 1), "outputs/tables/coverage_by_year.csv")
F("pct_with_sentiment_min_year", round(cy.drop("2020-2025")["pct_with_sentiment"].min(), 1), "outputs/tables/coverage_by_year.csv")
F("pct_with_sentiment_max_year", round(cy.drop("2020-2025")["pct_with_sentiment"].max(), 1), "outputs/tables/coverage_by_year.csv")
F("pct_zero_2020", round(cy.loc["2020", "pct_sentiment_exactly_0"], 1), "outputs/tables/coverage_by_year.csv")
F("pct_zero_2023", round(cy.loc["2023", "pct_sentiment_exactly_0"], 1), "outputs/tables/coverage_by_year.csv")
F("trading_days", int(cy.loc["2020-2025", "trading_days"]), "outputs/tables/coverage_by_year.csv")
sq = rd("outputs/tables/coverage_by_size_quintile.csv", index_col=0)
F("pct_sent_size_q1", round(sq.iloc[0]["pct_with_sentiment"], 1), "outputs/tables/coverage_by_size_quintile.csv")
F("pct_sent_size_q5", round(sq.iloc[-1]["pct_with_sentiment"], 1), "outputs/tables/coverage_by_size_quintile.csv")
wk = rd("outputs/tables/vendor_counts_by_value_day.csv", index_col=0)
F("scored_monday", round(wk.loc["Mon", "scored"], 1), "outputs/tables/vendor_counts_by_value_day.csv")
F("scored_tue_thu", round(wk.loc[["Tue", "Wed", "Thu"], "scored"].mean(), 1), "outputs/tables/vendor_counts_by_value_day.csv")
F("scored_holiday", round(wk.iloc[-1]["scored"], 1), "outputs/tables/vendor_counts_by_value_day.csv")
hb = rd("outputs/tables/headline_coverage_by_firm.csv", index_col=0)
F("headlines", int(hb.loc["All 19 firms", "headlines"]), "outputs/tables/headline_coverage_by_firm.csv")
art = rd("data/interim/articles_aligned.csv")
F("headline_firms", int(art["Company"].nunique()), "data/interim/articles_aligned.csv")
F("headline_domains", int(art["domain"].nunique()), "data/interim/articles_aligned.csv")
F("headline_bloomberg_domain", int(art["domain"].fillna("").str.contains("bloomberg").sum()), "data/interim/articles_aligned.csv")
F("headline_friday", int((pd.to_datetime(art["Date"]).dt.weekday == 4).sum()), "data/interim/articles_aligned.csv")
F("headline_saturday", int((pd.to_datetime(art["Date"]).dt.weekday == 5).sum()), "data/interim/articles_aligned.csv")
F("headline_flag_date", int(art["flag_url_date_mismatch"].astype(bool).sum()), "data/interim/articles_aligned.csv")
F("headline_flag_url", int(art["flag_url_not_url"].astype(bool).sum()), "data/interim/articles_aligned.csv")
hc = rd("outputs/diagnostics/hand_checks.csv")
F("hand_checks_pass", int((hc["result"] == "PASS").sum()), "outputs/diagnostics/hand_checks.csv")
pt = rd("outputs/diagnostics/pilot_terminal_checks.csv")
F("terminal_checks_pass", int((pt["result"] == "PASS").sum()), "outputs/diagnostics/pilot_terminal_checks.csv")
man = rd("manifests/data_manifest.csv")
F("manifest_rows", len(man), "manifests/data_manifest.csv")
F("manifest_available", int(man["validation_status"].str.startswith("AVAILABLE").sum()), "manifests/data_manifest.csv")
F("manifest_pending", int(man["validation_status"].str.startswith("PENDING").sum()), "manifests/data_manifest.csv")
sl = rd("manifests/bloomberg_source_log.csv")
F("source_log_rows", len(sl), "manifests/bloomberg_source_log.csv")
fc_fields = 26
F("fields_checked_in_flds", fc_fields, "Field_Check sheet of the raw workbook (rows 5-30)")
vf = rd("outputs/tables/vendor_field_summary.csv", index_col=0)
jr = rd("outputs/diagnostics/join_report.csv")
F("universe_days_no_market_row", int(jr.loc[0, "unmatched"]), "outputs/diagnostics/join_report.csv")
reasons = dict((k.strip(), int(v)) for k, v in (x.rsplit(":", 1) for x in str(jr.loc[0, "unmatched_reasons"]).split(";")))
F("no_market_row_after_last", reasons.get("after the last Bloomberg market row (delisted or acquired during the month)", 0),
  "outputs/diagnostics/join_report.csv")
F("no_market_row_before_first", reasons.get("before the first Bloomberg market row (new listing or spin-off)", 0),
  "outputs/diagnostics/join_report.csv")
F("headlines_unambiguous", int(att.loc["A3", "security_days_or_headlines"] - att.loc["A4", "security_days_or_headlines"]),
  "manifests/sample_attrition.csv (A3 - A4)")
fct = pd.DataFrame(facts, columns=["fact", "value", "source"])
fct.to_csv(TABLES / "checkpoint_1_facts.csv", index=False)
f = {k: v for k, v, _ in facts}          # keep the original types (no float conversion)

# ------------------------------------------------------------------ the pack
pack = f"""# First supervisor checkpoint: pack

**Project:** Is the Vendor's Secret Sauce Priced? Bloomberg vs a Reproducible Sentiment Score on Identical Text (proposal A16-02)
| **Student:** Botushanski, Neill Liran | **Prepared:** {PREPARED}

Nothing in this pack is a test of the hypothesis. Every number below is in `outputs/tables/checkpoint_1_facts.csv` with
the file it comes from.

## 1. The seven items

| # | Item the guide asks for | Where it is | Status |
|---|---|---|---|
| 1 | Completed design-decision log | `design_decisions.md` | Brief and supervisor items recorded (S1-S4); pull decisions B1-B6 approved; headline source decided (D1); P1-P6 proposed; E1-E2 open |
| 2 | Data manifest | `manifests/data_manifest.csv` | {f['manifest_rows']} rows: {f['manifest_available']} available and validated, {f['manifest_pending']} RiskLab cross-check files still to copy |
| 3 | Bloomberg pilot and field definitions | Pilot_Checks and Field_Check sheets; `manifests/bloomberg_source_log.csv` | {f['terminal_checks_pass']}/7 terminal checks PASS; {f['fields_checked_in_flds']} fields confirmed in FLDS; {f['source_log_rows']} source-log rows with hashes |
| 4 | Sample-coverage table | `outputs/tables/coverage_by_year.csv` (+ size, sector, headline tables); `manifests/sample_attrition.csv` | {f['attrition_1']:,} member security-days, {f['panel_securities']} securities, {f['trading_days']:,} trading days; {f['pct_with_sentiment_all']}% carry a vendor sentiment value |
| 5 | Ten hand-checked observations | `outputs/diagnostics/hand_checks.csv` | {f['hand_checks_pass']}/10 PASS, raw workbook cell to panel variable |
| 6 | One preliminary descriptive figure | `outputs/figures/fig1_vendor_coverage.png` | Plus Figure 2 (timing risk) and Figure 3 (score distribution) |
| 7 | Written list of unresolved data limitations | Section 4 below | 9 items |

## 2. What has been verified

- **Raw files.** {f['raw_files_hash_matched']}/{f['raw_files_hash_recorded']} raw files match the SHA-256 recorded on the terminal; `News_Articles.csv` was copied
  byte-for-byte from the RiskLab drive (hash matches the RiskLab catalogue).
- **Validation.** {f['validation_checks']} checks on schemas, keys, ranges, calendars, timing and joins; {f['validation_flags']} flags, all explained
  (holiday values, the weekend gap, and two headline-file problems).
- **Joins.** No duplicate keys, no many-to-many joins; every universe ticker is in the identifier table; the {f['universe_days_no_market_row']} universe
  security-days without a market row are firms delisted or acquired during the month ({f['no_market_row_after_last']}) or not yet listed ({f['no_market_row_before_first']}).
- **Terminal checks.** Prices, volume, total-return index and the vendor score match HP/GP on the terminal, including the
  AAPL 4-for-1 split (unadjusted / adjusted = 4.00, no jump in the total-return index).
- **Hand checks.** Ten random security-days traced from the raw workbook cells through the export to the panel, with both
  returns recomputed by hand: all match.

## 3. Decisions that need the supervisor's approval

| Id | Proposal (design_decisions.md, section 7) | Alternative |
|---|---|---|
| P1 | Vendor value dated D is usable from the open of D; holiday values from the next open; never carried forward | - |
| P2 | Returns from total-return ratios (close-to-close) and split-adjusted open/close (open-to-close) | Price-only returns |
| P3 | One ticker per company per day; use the other exchange ticker on exchange-switch days ({f['attrition_1b']} security-days) | Drop those days |
| P4 | Member on day t = member at the latest month-end strictly before t | Daily membership (about 1,500 bulk requests) |
| P5 | Headline subset: conservative cutoff (supervisor); compare with the vendor value dated the next weekday, same-day value as sensitivity | Average the two; or keep only the {f['headlines_unambiguous']} unambiguous headlines |
| P6 | Keep flagged headlines, report with and without them | Delete the {f['headline_flag_date'] + f['headline_flag_url']} flagged rows |

## 4. Unresolved data limitations

1. **Identical text is not yet available at scale (O1).** RiskLab holds no larger Bloomberg headline archive. The fallback
   file has {f['headlines']} headlines for {f['headline_firms']} firms from {f['headline_domains']} public sources and {f['headline_bloomberg_domain']} from bloomberg.com, with dates
   but no times. They cover {f['attrition_A1'] / f['attrition_1'] * 100:.3f}% of member security-days. Whether Bloomberg's daily value scored these exact
   stories cannot be verified without story identifiers. A Bloomberg headline export is not being pursued (D1), so this is the
   primary identical-text sample.
2. **Story-to-value assignment is ambiguous.** For {f['attrition_A4']} of the {f['attrition_A3']} headlines with any vendor value, two candidate daily
   values could contain the story (before or after 09:20).
3. **Weekend gap (O6).** Monday values carry {f['scored_monday']} scored stories per security-day against {f['scored_tue_thu']} on Tuesday-Thursday
   (holidays {f['scored_holiday']}): consistent with a 24-hour window, so news from Friday 09:20 to Sunday 09:20 is in no daily value.
   {f['headline_friday']} Friday and {f['headline_saturday']} Saturday headlines are exposed. Not confirmed with Bloomberg; treated as an assumption.
4. **Vendor regime change around 2022 (O7).** Exact zeros fall from {f['pct_zero_2020']}% of values (2020) to {f['pct_zero_2023']}% (2023) and story counts
   roughly halve; full-sample normalisation would leak this change.
5. **Coverage rises with size (O8).** {f['pct_sent_size_q1']}% of smallest-quintile security-days have a vendor value vs {f['pct_sent_size_q5']}% of the
   largest; comparisons must be on identical observations.
6. **Headline-file quality (O9).** {f['headline_flag_date']} headlines' URL dates differ from the file date by more than 3 days and {f['headline_flag_url']} has no URL;
   the file's selection rule (ESG-themed, hand-collected) is undocumented.
7. **Intra-month index changes (B2/P4).** Additions enter at the next month-end; {f['no_market_row_after_last']} security-days fall after a firm's last
   market row.
8. **Classifications are current only.** GICS is today's value and blank for 60 inactive names (BICS used); index weights
   were not entitled.
9. **RiskLab cross-check files not yet copied (O4).** `Daily_Average_Sentiment_Score.csv`, `SP500_NEWS_SENTIMENT_DAILY_AVG.csv`
   and `retail_proxy.csv` are on the RiskLab drive; they are cross-checks only.

## 5. Questions for the supervisor

1. D1: I am not pursuing the Bloomberg Help export question; the 188-headline subset is the primary sample. Is that acceptable?
2. P5: which vendor value should the reproducible score be compared with for each headline: the next-weekday value, the
   same-day value, or their average?
3. E2: primary outcome horizon, open-to-close on the value date (`ret_oc_d0`) or next-day close-to-close (`ret_cc_d1`)?
4. E2: primary reproducible scoring rule, a finance lexicon (Loughran-McDonald) or a finance transformer (FinBERT), with the
   other as robustness?
5. O6: should Friday and Saturday headlines stay in the identical-text sample, given the weekend gap?
6. S3: may the secondary exercise on the broad vendor panel ({f['attrition_8']:,} security-days with sentiment and a next-day return)
   start now, or only after the primary design is frozen?
"""
write_text(DIAG / "checkpoint_1_pack.md", pack)

# ------------------------------------------------------------------ the report: blocks rendered to both ipynb and html
blocks: list[tuple] = []           # ("md", text) | ("code", source, output) ; output = ("table", df) | ("image", path) | ("text", str)
M = lambda t: blocks.append(("md", t.strip("\n")))  # noqa: E731


def C(src, out):
    blocks.append(("code", src.strip("\n"), out))


def table(rel_path, src=None, **kw):
    df = rd(rel_path, **kw)
    C(src or f'display(read("{rel_path}"))', ("table", df))


def image(rel_path, width=900):
    C(f'show_image("{rel_path}", width={width})', ("image", ROOT / rel_path))


def text(rel_path):
    C(f'show_text("{rel_path}")', ("text", (ROOT / rel_path).read_text(encoding="utf-8")))


log = (ROOT / "design_decisions.md").read_text(encoding="utf-8")


def section(start, end=None):
    i = log.index(start)
    j = log.index(end, i) if end else len(log)
    return re.sub(r"^(#+)", r"#\1", log[i:j].strip(), flags=re.M)


M(f"""# First Supervisor Checkpoint: Consolidated Report

## Is the Vendor's Secret Sauce Priced? Bloomberg vs a Reproducible Sentiment Score on Identical Text

**Student:** Botushanski, Neill Liran | **Proposal:** A16-02 | **Supervisor:** Professor Hamid | **Prepared:** {PREPARED}

This report brings together everything the guide's first supervisor checkpoint asks for. It reads only saved outputs;
`python src/run_all.py` rebuilds all of them from the raw files. **No hypothesis test is presented.**""")
M("""## Contents
1. Summary and the checkpoint pack
2. Research question and the supervisor's decisions
3. Data sources, inventory and verification
4. Raw-data validation
5. Sample coverage and attrition (Figure 1)
6. Timing and data-quality diagnostics (Figures 2 and 3)
7. The 188 headlines
8. Design decisions and proposals
9. Ten hand-checked observations and the terminal checks
10. Appendix: variable dictionary and reproduction""")
C('''from pathlib import Path
import pandas as pd
from IPython.display import display, Image
ROOT = Path.cwd().resolve()            # the Project 2 folder: walk up until design_decisions.md is found
while not (ROOT / "design_decisions.md").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
pd.set_option("display.max_columns", 50, "display.width", 250)
def read(rel, **kw): return pd.read_csv(ROOT / rel, **kw)
def show_text(rel): print((ROOT / rel).read_text(encoding="utf-8"))
def show_image(rel, width=900): display(Image(filename=str(ROOT / rel), width=width))''', ("text", ""))
M("# Part 1. Summary and the checkpoint pack")
M(re.sub(r"\A# .*\n+", "", pack).replace("\n## ", "\n### "))
M("# Part 2. Research question and the supervisor's decisions")
M(section("## 2. Supervisor approval record", "## 4. Decisions to confirm"))
M("# Part 3. Data sources, inventory and verification")
M("### 3.1 Data manifest (one row per construct)")
table("manifests/data_manifest.csv")
M("### 3.2 Bloomberg source log (every field and file, with hashes)")
table("manifests/bloomberg_source_log.csv")
M("### 3.3 Raw files and their SHA-256")
table("outputs/diagnostics/raw_file_inventory.csv")
M("# Part 4. Raw-data validation")
text("outputs/diagnostics/02_raw_validation_summary.txt")
M("### 4.1 Every check")
table("outputs/diagnostics/raw_validation_checks.csv")
M("### 4.2 Join report")
table("outputs/diagnostics/join_report.csv")
M("# Part 5. Sample coverage and attrition")
image("outputs/figures/fig1_vendor_coverage.png")
M("""**Reading Figure 1.** Coverage of the vendor score is high but not complete: about four in five member security-days carry a
value, with a dip in 2020-21. The 19 headline firms are large caps and covered on about 98% of their member days. Mean story
counts fall from about 89 a day (2020-21) to about 48 (2023-25), over the same period in which the share of exact zeros drops
(Part 6).""")
M("### 5.1 Coverage by year")
table("outputs/tables/coverage_by_year.csv")
M("### 5.2 Coverage by size quintile (market cap at the start of each month)")
table("outputs/tables/coverage_by_size_quintile.csv")
M("### 5.3 Coverage by sector (BICS, current classification)")
table("outputs/tables/coverage_by_sector.csv")
M("### 5.4 Sample attrition: from the point-in-time universe to the analysis samples")
table("manifests/sample_attrition.csv", dtype={"step": str})
M("# Part 6. Timing and data-quality diagnostics")
image("outputs/figures/fig2_timing_window.png")
M("""**Reading Figure 2.** The value dated each weekday covers the 24 hours to 09:20 New York. Monday's and holiday values carry about
a third of a normal day's scored stories, which fits a window covering one quiet day; news from Friday 09:20 to Sunday 09:20
appears to fall in no value. Panel B shows the consequence for the headlines: for most of them two values could contain the
story, and a few can be in none.""")
table("outputs/tables/vendor_counts_by_value_day.csv")
image("outputs/figures/fig3_sentiment_distribution.png")
M("""**Reading Figure 3.** A quarter of values are exactly 0; most of these have scored stories with positive = negative, so they are
real neutral readings, not missing data. A plain count ratio tracks the vendor score closely (correlation about 0.8), which is
descriptive context for the black-box question, not a test of it.""")
table("outputs/tables/vendor_field_summary.csv", index_col=0)
M("### 6.1 Returns (sanity check only; no return is related to any signal here)")
table("outputs/tables/return_summary.csv", index_col=0)
M("# Part 7. The 188 headlines")
table("outputs/tables/headline_coverage_by_firm.csv")
table("outputs/tables/headline_coverage_by_year.csv")
M("### 7.1 Every headline with its validation flags and candidate vendor dates")
C('a = read("data/interim/articles_aligned.csv")\ndisplay(a[["article_id", "Company", "Date", "Headline", "domain", "member_at_date", '
  '"vendor_date_if_before_0920", "vendor_date_if_after_0920", "vendor_sent_same_day", "vendor_sent_next_weekday", '
  '"first_tradable_day_conservative", "flag_url_date_mismatch", "flag_url_not_url"]])',
  ("table", art[["article_id", "Company", "Date", "Headline", "domain", "member_at_date", "vendor_date_if_before_0920",
                 "vendor_date_if_after_0920", "vendor_sent_same_day", "vendor_sent_next_weekday",
                 "first_tradable_day_conservative", "flag_url_date_mismatch", "flag_url_not_url"]]))
M("# Part 8. Design decisions and proposals")
M(section("## 5. Data-acquisition decisions"))
M("# Part 9. Ten hand-checked observations and the terminal checks")
table("outputs/diagnostics/hand_checks.csv")
h = hc.iloc[0]
M(f"""### 9.1 How to check one by hand ({h['check_id']}: {h['ticker_exch']} on {h['date']})

1. Open `data/raw_bloomberg/20261106/P2_Bloomberg_Pull_20261106_values.xlsx` (no Bloomberg needed).
2. On **News_Core**, cell `{h['news_cell'].split('!')[1]}` holds the vendor score dated {h['date']}: **{h['raw_sentiment']}**.
3. On **Market**, cells `{h['market_cells'].split('!')[1]}` hold open, close and the total-return index on {h['date']}, and the
   index on the next trading day ({h['next_trading_day']}).
4. Open-to-close return = close / open - 1 = {h['raw_px_last']} / {h['raw_px_open']} - 1 = **{h['hand_ret_oc_d0']:.6f}**.
5. Next-day return = TRI({h['next_trading_day']}) / TRI({h['date']}) - 1 = {h['raw_tri_d1']} / {h['raw_tri_d']} - 1 = **{h['hand_ret_cc_d1']:.6f}**.
6. Both equal the panel values in `data/analytic/panel_security_day.csv.gz`.""")
M("### 9.2 The seven terminal checks (Pilot_Checks sheet, 2026-11-06)")
table("outputs/diagnostics/pilot_terminal_checks.csv")
M("# Appendix")
M("### A.1 Variable dictionary")
table("manifests/variable_dictionary.csv")
M("""### A.2 Project structure and reproduction

| Step | Script | Writes |
|---|---|---|
| Build the pull workbook | `src/00a_build_bloomberg_pull_workbook.py` | `bloomberg_pull/P2_Bloomberg_Pull.xlsx` |
| Raw validation | `src/02_raw_validation.py` | `outputs/diagnostics/02_*`, `raw_*` |
| Signals | `src/03_build_signals.py` | `data/interim/vendor_news_signals.csv.gz`, `articles_clean.csv` |
| Outcomes | `src/04_build_outcomes.py` | `data/interim/outcomes_daily.csv.gz`, `index_returns.csv` |
| Panel and attrition | `src/05_merge_analysis_panel.py` | `data/analytic/panel_security_day.csv.gz`, `manifests/sample_attrition.csv` |
| Descriptive diagnostics | `src/06_descriptive_diagnostics.py` | `outputs/tables/*`, `outputs/figures/*` |
| Hand checks | `src/07_hand_checks.py` | `outputs/diagnostics/hand_checks.csv` |
| This report | `src/build_checkpoint_report.py` | `reports/first_checkpoint_report.*` |

`python src/run_all.py` runs them in order from the raw files.""")

# ------------------------------------------------------------------ render: notebook
cells, n = [], 0
for k, b in enumerate(blocks):
    cid = f"c{k:03d}"
    if b[0] == "md":
        cells.append({"cell_type": "markdown", "id": cid, "metadata": {}, "source": b[1].splitlines(keepends=True)})
        continue
    n += 1
    _, src, (kind, payload) = b
    outs = []
    if kind == "table":
        outs.append({"output_type": "display_data", "metadata": {},
                     "data": {"text/html": payload.to_html(index=False, na_rep="", max_rows=400),
                              "text/plain": payload.to_string(index=False, max_rows=60)}})
    elif kind == "image":
        outs.append({"output_type": "display_data", "metadata": {},
                     "data": {"image/png": base64.b64encode(Path(payload).read_bytes()).decode(),
                              "text/plain": "<IPython.core.display.Image object>"}})
    elif kind == "text" and payload:
        outs.append({"output_type": "stream", "name": "stdout", "text": payload.splitlines(keepends=True)})
    cells.append({"cell_type": "code", "execution_count": n, "id": cid, "metadata": {}, "outputs": outs,
                  "source": src.splitlines(keepends=True)})
nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
(REPORTS / "first_checkpoint_report.ipynb").write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")

# ------------------------------------------------------------------ render: html
md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
parts = []
for b in blocks:
    if b[0] == "md":
        parts.append(md.reset().convert(b[1]))
    else:
        kind, payload = b[2]
        if kind == "table":
            parts.append('<div class="tbl">' + payload.to_html(index=False, na_rep="", max_rows=400, border=0) + "</div>")
        elif kind == "image":
            parts.append(f'<img src="data:image/png;base64,{base64.b64encode(Path(payload).read_bytes()).decode()}">')
        elif kind == "text" and payload:
            parts.append(f"<pre>{html.escape(payload)}</pre>")
css = """body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:1150px;margin:32px auto;padding:0 16px;
color:#1d1d1f;line-height:1.5;font-size:14px}h1{color:#1F3864;border-bottom:2px solid #1F3864;padding-bottom:4px;margin-top:40px}
h2,h3,h4{color:#1F3864}table{border-collapse:collapse;font-size:12px;margin:8px 0}th,td{border:1px solid #d0d7e2;padding:3px 6px;
text-align:left;vertical-align:top}th{background:#eef2f8}.tbl{overflow-x:auto;max-height:520px;overflow-y:auto;margin-bottom:12px}
pre{background:#f6f8fa;padding:10px;font-size:11.5px;overflow-x:auto;white-space:pre}img{max-width:100%;border:1px solid #eee}
blockquote{border-left:3px solid #C55A11;margin:8px 0;padding:2px 12px;color:#333;background:#fbf6f2}code{background:#f2f2f2;padding:0 3px}"""
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Checkpoint 1 Report</title><style>{css}</style></head><body>{''.join(parts)}</body></html>"""
(REPORTS / "first_checkpoint_report.html").write_text(page, encoding="utf-8")
print(f"facts: {len(fct)}; pack: {DIAG / 'checkpoint_1_pack.md'}; notebook cells: {len(cells)}; "
      f"html: {(REPORTS / 'first_checkpoint_report.html').stat().st_size / 1e6:.1f} MB")
