"""Build the Bloomberg pull workbook for Project 2 (proposal A16-02).

Run from the project root:

    python src/00a_build_bloomberg_pull_workbook.py

It writes bloomberg_pull/P2_Bloomberg_Pull.xlsx: an Excel file of BDS/BDH/BDP formulas that
pull everything this project needs from a Bloomberg terminal. Nothing is pulled until the
formulas are refreshed on a terminal. Every date, field and option is set in the CONSTANTS
block below and mirrored in config/project_config.yaml, so the workbook can be rebuilt
identically if a field name has to change after FLDS checks.

Layout rules (the export script src/01a_freeze_bloomberg_pull.py relies on them):
  * Market, News_Core, News_Optional, Index_Daily: one block per security. Row 3 = slot
    number, row 4 = security, row 5 = "date" then the field names, row 6 = the BDH formula,
    which writes the date column and one column per field from row 6 down ("Dts=S", so each
    security carries its own dates and nothing depends on rows lining up).
  * Universe: one 600-row block per month-end snapshot; the side table (G:I) lists each
    snapshot's date, override string and first row.
  * Tickers: slot n is row n + 4.
"""
from __future__ import annotations

import calendar
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as col
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.workbook.properties import CalcProperties

# ----------------------------------------------------------------------------- CONSTANTS
OUT = Path("bloomberg_pull/P2_Bloomberg_Pull.xlsx")
BUILT_ON = "2026-11-03"

PULL_START = date(2019, 7, 1)    # 6-month warm-up before the study window (training-window scaling, lagged controls)
PULL_END = date(2026, 1, 30)     # ~1-month buffer after the study window (forward returns at short horizons)
STUDY_START = date(2020, 1, 1)   # approved sample: 2020-2025 daily (project_2.md)
STUDY_END = date(2025, 12, 31)
INDEX = "SPX Index"
N_SLOTS = 800                    # room for the union of S&P 500 members 2019-12 to 2025-12 (expected ~650-700)
UNIVERSE_BLOCK = 600             # rows reserved per month-end snapshot (S&P 500 has ~503-505 lines)

SNAPSHOTS = [date(y, m, calendar.monthrange(y, m)[1])
             for y in range(2019, 2026) for m in range(1, 13)
             if date(2019, 12, 31) <= date(y, m, calendar.monthrange(y, m)[1]) <= date(2025, 12, 31)]

MARKET_FIELDS = ["PX_OPEN", "PX_LAST", "TOT_RETURN_INDEX_GROSS_DVDS", "PX_VOLUME", "CUR_MKT_CAP"]
NEWS_CORE = ["NEWS_SENTIMENT_DAILY_AVG", "NEWS_PUBLICATION_COUNT"]
NEWS_OPT = ["NEWS_POS_SENTIMENT_COUNT", "NEWS_NEG_SENTIMENT_COUNT", "NEWS_NEUTRAL_SENTIMENT_COUNT",
            "NEWS_HEAT_PUB_DAVG", "NEWS_HEAT_READ_DMAX"]
STATIC = ["NAME", "ID_BB_GLOBAL", "ID_ISIN", "TICKER_AND_EXCH_CODE", "EQY_PRIM_EXCH", "MARKET_STATUS",
          "SECURITY_TYP", "CRNCY", "COUNTRY_ISO", "GICS_SECTOR_NAME", "GICS_INDUSTRY_GROUP_NAME",
          "GICS_INDUSTRY_NAME"]
EARN_FIELD = "EARN_ANN_DT_TIME_HIST_WITH_EPS"
UNIVERSE_FIELD = "INDX_MWEIGHT_HIST"
INDEX_SERIES = [("SPX Index", ["PX_OPEN", "PX_LAST"]), ("SPXT Index", ["PX_LAST"]), ("VIX Index", ["PX_LAST"])]

# BDH options. Prices are adjusted for splits/capital changes only (not for dividends); returns
# come from the total-return index. UseDPDF=N makes these options override the terminal's DPDF settings.
PRICE_OPTS = '"Dts=S","Days=T","Fill=B","Sort=A","CshAdjNormal=N","CshAdjAbnormal=N","CapChg=Y","UseDPDF=N"'
PRICE_OPTS_UNADJ = '"Dts=S","Days=T","Fill=B","Sort=A","CshAdjNormal=N","CshAdjAbnormal=N","CapChg=N","UseDPDF=N"'
# News: every calendar day (weekend stories kept), blank when there is no value (never carried forward).
NEWS_OPTS = '"Dts=S","Days=A","Fill=B","Sort=A"'
INDEX_OPTS = '"Dts=S","Days=T","Fill=B","Sort=A"'

# ----------------------------------------------------------------------------- STYLES
ARIAL = "Arial"
F_BASE = Font(name=ARIAL, size=10)
F_BOLD = Font(name=ARIAL, size=10, bold=True)
F_TITLE = Font(name=ARIAL, size=14, bold=True, color="1F3864")
F_SUB = Font(name=ARIAL, size=10, italic=True, color="595959")
F_HDR = Font(name=ARIAL, size=10, bold=True, color="FFFFFF")
F_INPUT = Font(name=ARIAL, size=10, color="0000FF")          # fixed input typed in by hand
F_LINK = Font(name=ARIAL, size=10, color="008000")           # pulls from another sheet
FILL_HDR = PatternFill("solid", fgColor="1F3864")
FILL_SUBHDR = PatternFill("solid", fgColor="D9E1F2")
FILL_USER = PatternFill("solid", fgColor="FFFF00")            # you fill this in at the terminal
FILL_BBG = PatternFill("solid", fgColor="FCE4D6")             # Bloomberg formula anchor
WRAP = Alignment(wrap_text=True, vertical="top")
DATE_FMT = "yyyy-mm-dd"


def put(ws, ref, value, font=F_BASE, fill=None, fmt=None, align=None):
    c = ws[ref]
    c.value = value
    c.font = font
    if fill:
        c.fill = fill
    if fmt:
        c.number_format = fmt
    if align:
        c.alignment = align
    return c


def title(ws, text, sub):
    put(ws, "A1", text, F_TITLE)
    put(ws, "A2", sub, F_SUB)


def header_row(ws, row, first_col, labels, fill=FILL_HDR, font=F_HDR):
    for i, lab in enumerate(labels):
        put(ws, f"{col(first_col + i)}{row}", lab, font, fill)


# ----------------------------------------------------------------------------- SHEETS
def readme(wb):
    ws = wb.active
    ws.title = "README"
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 120
    put(ws, "B1", "Project 2 (A16-02): Bloomberg pull workbook", F_TITLE)
    put(ws, "B2", "Is the vendor's secret sauce priced? Bloomberg vs a reproducible sentiment score on identical text. "
                  f"Built {BUILT_ON} by src/00a_build_bloomberg_pull_workbook.py.", F_SUB)
    lines = [
        ("h", "What this workbook pulls (end-of-day, daily and reference data only; nothing intraday)"),
        ("", f"Universe: S&P 500 members at {len(SNAPSHOTS)} month-ends ({SNAPSHOTS[0]} to {SNAPSHOTS[-1]}) from {UNIVERSE_FIELD}, so firms that left the index are included."),
        ("", "Static: identifiers (FIGI, ISIN, ticker and exchange), listing status, currency and GICS (current snapshot only)."),
        ("", f"Market: {', '.join(MARKET_FIELDS)} on trading days, {PULL_START} to {PULL_END}."),
        ("", f"News_Core: {', '.join(NEWS_CORE)} on every calendar day, same window."),
        ("", f"News_Optional: {', '.join(NEWS_OPT)}."),
        ("", "Index_Daily: SPX (open and close), SPXT (total return) and VIX.  Earnings_Optional: announcement dates and times with EPS."),
        ("h", "Before you start"),
        ("", "1. Open Excel on the terminal with the Bloomberg add-in loaded (Bloomberg tab visible). If formulas show #NAME?, the add-in is not loaded: restart Excel from the Bloomberg menu, then refresh."),
        ("", "2. The workbook is set to MANUAL calculation and does not recalculate when saved, so nothing is requested until you refresh a sheet. Leave it that way. Do not press Ctrl+Alt+F9 (that requests every sheet at once)."),
        ("", "3. Refresh one sheet at a time: click the sheet tab, then Bloomberg tab > Refresh > Refresh Worksheet (Shift+F9 also calculates only the active sheet). Wait until no cell shows '#N/A Requesting Data...', then save."),
        ("h", "Order of work"),
        ("", "Step 1  Field_Check: refresh. Run FLDS <GO> on AAPL UW Equity for every field and fill the yellow columns (verified, description, units and timing). Also search FLDS for the field IDs NW020 and RK074 (columns in RiskLab's Daily_Average_Sentiment_Score.csv)."),
        ("", "Step 2  Pilot: refresh. Then fill the yellow 'terminal value' cells on Pilot_Checks from HP <GO> (or GP). Every check should read PASS. If any reads CHECK, stop and fix the field or option before the full pull."),
        ("", "Step 3  Universe: refresh. Column J of the side table should show about 500 members for every snapshot."),
        ("", "Step 4  Tickers: copy Universe column B (from B6 down to the last row), paste as VALUES into Tickers B5, then Data > Remove Duplicates (column B only) and sort A to Z. Blank cells must end up at the bottom. Check cells: duplicates = 0, ' Equity' suffix = 0, count <= 800."),
        ("", "Step 5  Static: refresh.   Step 6  Index_Daily: refresh."),
        ("", "Step 7  Market: refresh (the largest sheet, one request per slot). Save when it finishes."),
        ("", "Step 8  News_Core: refresh. Save."),
        ("", "Step 9  News_Optional, then Earnings_Optional: only if Bloomberg has not shown a data-limit message."),
        ("", "Step 10 Pull_Log: fill one row per sheet as you go (date, times, who, terminal, any warnings)."),
        ("", "Step 11 File > Save As 'P2_Bloomberg_Pull_YYYYMMDD.xlsx' (the pull date). Bring that file back unchanged; it goes in data/raw_bloomberg/YYYYMMDD/ and src/01a_freeze_bloomberg_pull.py exports and hashes it."),
        ("", "Empty slots at the end of the Market and News sheets show '#N/A Invalid Security'. That is expected and harmless."),
        ("", "If Bloomberg shows a data-limit message: stop, note it in Pull_Log, save, and continue in the next session. Do not split or disguise requests to get around a limit."),
        ("h", "What this workbook cannot pull"),
        ("", "Headline text and story identifiers. Excel formulas return fields, not stories. The reproducible score needs the text, and RiskLab's News_Articles.csv holds 188 headlines. Professor Hamid (RiskLab) decides how this is handled; don't export headlines or build a workaround until he has replied."),
        ("", "Intraday data of any kind. Project rule: minute-level data comes only from C:\\risklab\\data\\intraday_data."),
        ("h", "Field names are candidates"),
        ("", "Confirm every mnemonic and its definition in FLDS <GO> for an equity before trusting the pull (Field_Check sheet). If a field is renamed, change it in src/00a_build_bloomberg_pull_workbook.py and rebuild, rather than editing formulas by hand."),
        ("h", "Colour key"),
        ("", "Blue text = fixed input typed in by hand.  Yellow cell = you fill this in at the terminal.  Peach cell = Bloomberg formula (the data spills down and right from it).  Green text = pulled from another sheet."),
    ]
    r = 4
    for kind, text in lines:
        if kind == "h":
            r += 1
            put(ws, f"B{r}", text, F_BOLD, FILL_SUBHDR)
        else:
            put(ws, f"B{r}", text, F_BASE, align=WRAP)
        r += 1


def config(wb):
    ws = wb.create_sheet("Config")
    title(ws, "Config", "Fixed inputs used by the formulas on other sheets. Change them in the build script, not here.")
    for c, w in zip("ABCD", (3, 26, 22, 95)):
        ws.column_dimensions[c].width = w
    header_row(ws, 3, 2, ["Setting", "Value", "Why"])
    rows = [
        ("Pull start", PULL_START, "Six months before the study window, for training-window scaling and lagged controls. Named range PullStart."),
        ("Pull end", PULL_END, "About one month after the study window, so short-horizon forward returns exist for 2025-12-31. Named range PullEnd."),
        ("Study start", STUDY_START, "Approved sample 2020-2025 daily (project_2.md). Not used by any formula; the export keeps the full pull."),
        ("Study end", STUDY_END, "As above."),
        ("Index", INDEX, "S&P 500. Named range IndexTicker, used by the Universe BDS formulas."),
        ("Universe snapshots", f"{len(SNAPSHOTS)} month-ends", f"{SNAPSHOTS[0]} to {SNAPSHOTS[-1]} ({UNIVERSE_FIELD} with END_DATE_OVERRIDE)."),
        ("Security slots", N_SLOTS, "Blocks prepared on each per-security sheet. Expected union of members: about 650 to 700."),
        ("Price BDH options", PRICE_OPTS.replace('"', ''), "Dates shown per security; trading days; blank on missing; split/capital-change adjusted only; DPDF settings ignored."),
        ("News BDH options", NEWS_OPTS.replace('"', ''), "Every calendar day so weekend stories are kept; blank when no value (no carry-forward)."),
        ("Universe block size", f"{UNIVERSE_BLOCK} rows", "Rows reserved per snapshot on the Universe sheet."),
    ]
    for i, (k, v, why) in enumerate(rows, start=4):
        put(ws, f"B{i}", k, F_BOLD)
        put(ws, f"C{i}", v, F_INPUT, fmt=DATE_FMT if isinstance(v, date) else None)
        put(ws, f"D{i}", why, align=WRAP)
    wb.defined_names["PullStart"] = DefinedName("PullStart", attr_text="Config!$C$4")
    wb.defined_names["PullEnd"] = DefinedName("PullEnd", attr_text="Config!$C$5")
    wb.defined_names["IndexTicker"] = DefinedName("IndexTicker", attr_text="Config!$C$8")


FIELD_INFO = {
    UNIVERSE_FIELD: ("Universe", "Universe", "Point-in-time index members and weights", "Bulk field: tested on Pilot. Confirm the override name END_DATE_OVERRIDE and that column 1 is 'TICKER EXCH' (e.g. AAPL UW)."),
    "NAME": ("Static", "Static", "Company name", ""),
    "ID_BB_GLOBAL": ("Static", "Static", "FIGI, the stable join key", "Confirm it stays fixed through ticker changes."),
    "ID_ISIN": ("Static", "Static", "ISIN, join key to non-Bloomberg data", ""),
    "TICKER_AND_EXCH_CODE": ("Static", "Static", "Current ticker and exchange", "Current value only; ticker history comes from the universe snapshots."),
    "EQY_PRIM_EXCH": ("Static", "Static", "Primary exchange", ""),
    "MARKET_STATUS": ("Static", "Static", "Listing status (active, delisted, acquired)", "Needed to resolve firms that left the index."),
    "SECURITY_TYP": ("Static", "Static", "Security type (common stock, REIT, ADR)", ""),
    "CRNCY": ("Static", "Static", "Pricing currency", "Expect USD for all; flag any other."),
    "COUNTRY_ISO": ("Static", "Static", "Country of domicile", ""),
    "GICS_SECTOR_NAME": ("Static", "Static", "GICS sector", "Current classification only. Do not use it to infer past sectors."),
    "GICS_INDUSTRY_GROUP_NAME": ("Static", "Static", "GICS industry group", "Current classification only."),
    "GICS_INDUSTRY_NAME": ("Static", "Static", "GICS industry", "Current classification only."),
    "PX_OPEN": ("Market", "Core", "Open price, split-adjusted", "Units: USD per share. Needed for open-to-close returns if the return cutoff decision requires them."),
    "PX_LAST": ("Market", "Core", "Close price, split-adjusted", "Units: USD per share. Check the adjustment against HP on the Pilot."),
    "TOT_RETURN_INDEX_GROSS_DVDS": ("Market", "Core", "Total-return index (dividends reinvested, gross)", "Primary source of daily returns. Confirm dividends are reinvested on the ex-date."),
    "PX_VOLUME": ("Market", "Core", "Daily volume", "Units: shares? Confirm composite vs primary exchange volume."),
    "CUR_MKT_CAP": ("Market", "Core", "Market capitalisation", "Units: full USD or millions? Record what FLDS says."),
    "NEWS_SENTIMENT_DAILY_AVG": ("News_Core", "Core", "Vendor daily news sentiment (the black-box score)", "KEY: scale; which stories count; the day boundary and time zone (midnight New York? GMT?); whether values are revised. This sets the return cutoff."),
    "NEWS_PUBLICATION_COUNT": ("News_Core", "Core", "Number of stories that day", "Same day boundary as the sentiment field? Bloomberg stories only or web too?"),
    "NEWS_POS_SENTIMENT_COUNT": ("News_Optional", "Optional", "Stories scored positive", ""),
    "NEWS_NEG_SENTIMENT_COUNT": ("News_Optional", "Optional", "Stories scored negative", "Candidate name: confirm in FLDS."),
    "NEWS_NEUTRAL_SENTIMENT_COUNT": ("News_Optional", "Optional", "Stories scored neutral", "Candidate name: confirm in FLDS."),
    "NEWS_HEAT_PUB_DAVG": ("News_Optional", "Optional", "News heat: publication intensity", "Candidate name: confirm in FLDS (optional extension in the brief)."),
    "NEWS_HEAT_READ_DMAX": ("News_Optional", "Optional", "News heat: readership intensity", "Candidate name: confirm in FLDS (optional extension in the brief)."),
    EARN_FIELD: ("Earnings_Optional", "Optional", "Earnings announcement dates, times and EPS", "Bulk field: tested on Pilot. Confirm the time zone of the announcement time."),
}


def field_check(wb):
    ws = wb.create_sheet("Field_Check")
    title(ws, "Field_Check", "Refresh, then confirm every field in FLDS <GO> on AAPL UW Equity. Yellow columns are yours to fill.")
    widths = [30, 18, 10, 44, 22, 11, 50, 50, 60]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[col(i)].width = w
    header_row(ws, 4, 1, ["Field (mnemonic)", "Sheet", "Tier", "What it is for", "Live test: AAPL UW Equity",
                          "FLDS verified (Y/N)", "FLDS description (paste)", "Units and timing per FLDS", "What to check"])
    r = 5
    for f, (sheet, tier, use, check) in FIELD_INFO.items():
        put(ws, f"A{r}", f, F_INPUT)
        put(ws, f"B{r}", sheet)
        put(ws, f"C{r}", tier)
        put(ws, f"D{r}", use, align=WRAP)
        if f in (UNIVERSE_FIELD, EARN_FIELD):
            put(ws, f"E{r}", "bulk field: see Pilot", F_SUB)
        else:
            put(ws, f"E{r}", f'=BDP("AAPL UW Equity",$A{r})', fill=FILL_BBG)
        for c in "FGH":
            put(ws, f"{c}{r}", None, fill=FILL_USER)
        put(ws, f"I{r}", check, align=WRAP)
        r += 1
    r += 1
    put(ws, f"A{r}", "Field IDs to look up", F_BOLD, FILL_SUBHDR)
    r += 1
    header_row(ws, r, 1, ["Field ID", "Found in", "", "Question", "", "Mnemonic per FLDS", "FLDS description (paste)", "", ""])
    for fid in ("NW020", "RK074"):
        r += 1
        put(ws, f"A{r}", fid, F_INPUT)
        put(ws, f"B{r}", "Daily_Average_Sentiment_Score.csv (RL-1EBA802A51B7)", align=WRAP)
        put(ws, f"D{r}", "Which mnemonic does this field ID belong to? Needed to map the local vendor file onto this pull.", align=WRAP)
        for c in "FG":
            put(ws, f"{c}{r}", None, fill=FILL_USER)
    ws.freeze_panes = "B5"


def block(ws, c0, security_cell_value, fields, formula, slot=None, start=None, end=None, font_sec=F_LINK):
    """Write one security block whose date column is c0. Returns the block width incl. spacer."""
    L0 = col(c0)
    if slot is not None:
        put(ws, f"{L0}3", slot, F_SUB)
    put(ws, f"{L0}4", security_cell_value, font_sec)
    put(ws, f"{L0}5", "date", F_HDR, FILL_HDR)
    for i, f in enumerate(fields, start=1):
        put(ws, f"{col(c0 + i)}5", f, F_HDR, FILL_HDR)
    put(ws, f"{L0}6", formula, fill=FILL_BBG)
    ws.column_dimensions[L0].width = 11
    for i in range(1, len(fields) + 1):
        ws.column_dimensions[col(c0 + i)].width = 14
    ws.column_dimensions[col(c0 + len(fields) + 1)].width = 2
    return len(fields) + 2


def bdh(sec_expr, c0, nfields, start, end, opts):
    first, last = col(c0 + 1), col(c0 + nfields)
    return f"=BDH({sec_expr},{first}$5:{last}$5,{start},{end},{opts})"


def row_labels(ws, labels=("", "", "Slot", "Security", "Fields", "Data")):
    ws.column_dimensions["A"].width = 10
    for i, lab in enumerate(labels, start=1):
        if lab:
            put(ws, f"A{i}", lab, F_BOLD)


def per_security_sheet(wb, name, fields, opts, sub):
    ws = wb.create_sheet(name)
    title(ws, name, sub)
    row_labels(ws)
    c0 = 2
    for slot in range(1, N_SLOTS + 1):
        tick = f"Tickers!$B${slot + 4}"
        disp = f'=IF({tick}="","",{tick}&" Equity")'
        width = block(ws, c0, disp, fields, bdh(f'{tick}&" Equity"', c0, len(fields), "PullStart", "PullEnd", opts), slot=slot)
        c0 += width
    ws.freeze_panes = "B6"
    return ws


def pilot(wb):
    ws = wb.create_sheet("Pilot")
    title(ws, "Pilot", "Two securities, ten trading dates, one known split (AAPL 4-for-1, effective 2020-08-31; NVDA 10-for-1, effective 2024-06-10). Refresh before the full pull.")
    labels = {4: "Block", 5: "Security", 6: "Start", 7: "End", 8: "Options", 9: "Fields", 10: "Data"}
    ws.column_dimensions["A"].width = 10
    for r, lab in labels.items():
        put(ws, f"A{r}", lab, F_BOLD)
    allnews = NEWS_CORE + NEWS_OPT
    specs = [
        ("P1 AAPL market, project settings", "AAPL UW Equity", date(2020, 8, 24), date(2020, 9, 4), MARKET_FIELDS, PRICE_OPTS),
        ("P2 AAPL prices, NOT split-adjusted", "AAPL UW Equity", date(2020, 8, 24), date(2020, 9, 4), ["PX_OPEN", "PX_LAST"], PRICE_OPTS_UNADJ),
        ("P3 NVDA market, project settings", "NVDA UW Equity", date(2024, 6, 3), date(2024, 6, 14), MARKET_FIELDS, PRICE_OPTS),
        ("P4 AAPL news, calendar days", "AAPL UW Equity", date(2020, 8, 24), date(2020, 9, 6), allnews, NEWS_OPTS),
        ("P5 NVDA news, calendar days", "NVDA UW Equity", date(2024, 6, 3), date(2024, 6, 16), allnews, NEWS_OPTS),
    ]
    c0 = 2
    positions = {}
    for lab, sec, s, e, fields, opts in specs:
        L0 = col(c0)
        put(ws, f"{L0}4", lab, F_BOLD)
        put(ws, f"{L0}5", sec, F_INPUT)
        put(ws, f"{L0}6", s, F_INPUT, fmt=DATE_FMT)
        put(ws, f"{L0}7", e, F_INPUT, fmt=DATE_FMT)
        put(ws, f"{L0}8", opts.replace('"', ''), F_SUB)
        put(ws, f"{L0}9", "date", F_HDR, FILL_HDR)
        for i, f in enumerate(fields, start=1):
            put(ws, f"{col(c0 + i)}9", f, F_HDR, FILL_HDR)
            ws.column_dimensions[col(c0 + i)].width = 14
        first, last = col(c0 + 1), col(c0 + len(fields))
        put(ws, f"{L0}10", f"=BDH(${L0}$5,{first}$9:{last}$9,${L0}$6,${L0}$7,{opts})", fill=FILL_BBG)
        ws.column_dimensions[L0].width = 11
        ws.column_dimensions[col(c0 + len(fields) + 1)].width = 2
        positions[lab[:2]] = (c0, fields)
        c0 += len(fields) + 2
    # P6 static fields for both pilot securities
    L0, L1, L2 = col(c0), col(c0 + 1), col(c0 + 2)
    put(ws, f"{L0}4", "P6 static fields", F_BOLD)
    put(ws, f"{L1}5", "AAPL UW Equity", F_INPUT)
    put(ws, f"{L2}5", "NVDA UW Equity", F_INPUT)
    header_row(ws, 9, c0, ["field", "AAPL", "NVDA"])
    for i, f in enumerate(STATIC, start=10):
        put(ws, f"{L0}{i}", f)
        put(ws, f"{L1}{i}", f"=BDP({L1}$5,${L0}{i})", fill=FILL_BBG)
        put(ws, f"{L2}{i}", f"=BDP({L2}$5,${L0}{i})", fill=FILL_BBG)
    ws.column_dimensions[L0].width = 26
    ws.column_dimensions[L1].width = 22
    ws.column_dimensions[L2].width = 22
    c0 += 4
    # P7 earnings bulk field
    L0 = col(c0)
    put(ws, f"{L0}4", "P7 AAPL earnings history (bulk)", F_BOLD)
    put(ws, f"{L0}5", "AAPL UW Equity", F_INPUT)
    put(ws, f"{L0}8", f"{EARN_FIELD}, Headers=Y", F_SUB)
    put(ws, f"{L0}10", f'=BDS(${L0}$5,"{EARN_FIELD}","Headers=Y")', fill=FILL_BBG)
    for i in range(8):
        ws.column_dimensions[col(c0 + i)].width = 14
    c0 += 9
    # P8 universe bulk field, one snapshot
    L0 = col(c0)
    put(ws, f"{L0}4", "P8 S&P 500 members on 2020-01-31 (bulk)", F_BOLD)
    put(ws, f"{L0}5", INDEX, F_INPUT)
    put(ws, f"{L0}6", "20200131", F_INPUT)
    put(ws, f"{L0}8", f"{UNIVERSE_FIELD}, END_DATE_OVERRIDE", F_SUB)
    put(ws, f"{L0}9", f"=COUNTA({L0}10:{L0}700)", F_BOLD)
    ws[f"{L0}9"].comment = Comment("Number of members returned. Expect about 505.", "build script")
    put(ws, f"{L0}10", f'=BDS(${L0}$5,"{UNIVERSE_FIELD}","END_DATE_OVERRIDE",${L0}$6)', fill=FILL_BBG)
    ws.column_dimensions[L0].width = 14
    ws.freeze_panes = "B10"
    return positions


def pilot_checks(wb, positions):
    ws = wb.create_sheet("Pilot_Checks")
    title(ws, "Pilot_Checks", "Compare pilot values with the terminal display. Type the terminal value in the yellow cell; every row should read PASS.")
    widths = [5, 46, 16, 28, 11, 16, 16, 14, 9, 56]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[col(i)].width = w
    header_row(ws, 4, 1, ["#", "Check", "Security", "Field", "Date", "Workbook value", "Terminal value",
                          "Difference", "Result", "Where to read it on the terminal"])

    def look(block_key, field, date_cell):
        c0, fields = positions[block_key]
        vc = col(c0 + 1 + fields.index(field))
        dc = col(c0)
        return f"=IFERROR(INDEX(Pilot!${vc}$10:${vc}$40,MATCH({date_cell},Pilot!${dc}$10:${dc}$40,0)),\"\")"

    terminal_rows = [
        ("AAPL close before the split, adjusted", "AAPL UW Equity", "P1", "PX_LAST", date(2020, 8, 28), "HP <GO> on AAPL UW Equity (default adjustment includes splits)"),
        ("AAPL close on the split date, adjusted", "AAPL UW Equity", "P1", "PX_LAST", date(2020, 8, 31), "HP <GO> on AAPL UW Equity"),
        ("AAPL close before the split, unadjusted", "AAPL UW Equity", "P2", "PX_LAST", date(2020, 8, 28), "HP <GO>, turn split adjustment off (should be about 4x row 1)"),
        ("NVDA close before the split, adjusted", "NVDA UW Equity", "P3", "PX_LAST", date(2024, 6, 7), "HP <GO> on NVDA UW Equity"),
        ("NVDA volume on the split date", "NVDA UW Equity", "P3", "PX_VOLUME", date(2024, 6, 10), "HP <GO> on NVDA UW Equity, volume column"),
        ("NVDA total-return index on the split date", "NVDA UW Equity", "P3", "TOT_RETURN_INDEX_GROSS_DVDS", date(2024, 6, 10), "HP <GO>, change the field to TOT_RETURN_INDEX_GROSS_DVDS"),
        ("AAPL vendor sentiment on 2020-08-31", "AAPL UW Equity", "P4", "NEWS_SENTIMENT_DAILY_AVG", date(2020, 8, 31), "GP <GO> (or HP) on AAPL UW Equity with the field NEWS_SENTIMENT_DAILY_AVG"),
    ]
    r = 5
    for i, (what, sec, blk, f, d, where) in enumerate(terminal_rows, start=1):
        put(ws, f"A{r}", i)
        put(ws, f"B{r}", what)
        put(ws, f"C{r}", sec)
        put(ws, f"D{r}", f)
        put(ws, f"E{r}", d, F_INPUT, fmt=DATE_FMT)
        put(ws, f"F{r}", look(blk, f, f"$E{r}"), F_LINK, fmt="#,##0.0000")
        put(ws, f"G{r}", None, fill=FILL_USER, fmt="#,##0.0000")
        put(ws, f"H{r}", f'=IF(OR(F{r}="",G{r}=""),"",F{r}-G{r})', fmt="#,##0.0000")
        put(ws, f"I{r}", f'=IF(H{r}="","",IF(ABS(H{r})<=0.005*MAX(ABS(G{r}),0.0001),"PASS","CHECK"))', F_BOLD)
        put(ws, f"J{r}", where, align=WRAP)
        r += 1
    # Checks computed inside the workbook (no terminal value needed)
    r += 1
    put(ws, f"B{r}", "Checks computed from the pilot itself", F_BOLD, FILL_SUBHDR)
    r += 1
    p1c0, p1f = positions["P1"]
    p4c0, _ = positions["P4"]
    tr = col(p1c0 + 1 + p1f.index("TOT_RETURN_INDEX_GROSS_DVDS"))
    px = col(p1c0 + 1 + p1f.index("PX_LAST"))
    dc = col(p1c0)
    computed = [
        ("Split factor: unadjusted / adjusted AAPL close on 2020-08-28 (expect 4.00)",
         '=IFERROR(F7/F5,"")', '=IF(F{r}="","",IF(ABS(F{r}-4)<0.01,"PASS","CHECK"))'),
        ("Total-return index has no jump across the split: index return minus price return, 2020-08-28 to 2020-08-31 (expect about 0)",
         f'=IFERROR((INDEX(Pilot!${tr}$10:${tr}$40,MATCH(DATE(2020,8,31),Pilot!${dc}$10:${dc}$40,0))/INDEX(Pilot!${tr}$10:${tr}$40,MATCH(DATE(2020,8,28),Pilot!${dc}$10:${dc}$40,0)))-(INDEX(Pilot!${px}$10:${px}$40,MATCH(DATE(2020,8,31),Pilot!${dc}$10:${dc}$40,0))/INDEX(Pilot!${px}$10:${px}$40,MATCH(DATE(2020,8,28),Pilot!${dc}$10:${dc}$40,0))),"")',
         '=IF(F{r}="","",IF(ABS(F{r})<0.001,"PASS","CHECK"))'),
        ("News block includes Saturday 2020-08-29 (Days=A keeps weekends)",
         f'=IF(ISNUMBER(MATCH(DATE(2020,8,29),Pilot!${col(p4c0)}$10:${col(p4c0)}$40,0)),"yes","no")',
         '=IF(F{r}="yes","PASS","CHECK")'),
    ]
    for what, fcalc, fres in computed:
        put(ws, f"B{r}", what, align=WRAP)
        put(ws, f"F{r}", fcalc, fmt="0.0000")
        put(ws, f"I{r}", fres.format(r=r), F_BOLD)
        r += 1
    r += 1
    put(ws, f"B{r}", "Tolerance: PASS if the workbook and terminal values differ by at most 0.5% (the terminal display rounds).", F_SUB)
    ws.freeze_panes = "A5"


def universe(wb):
    ws = wb.create_sheet("Universe")
    title(ws, "Universe", f"S&P 500 members at each month-end from {UNIVERSE_FIELD}. One {UNIVERSE_BLOCK}-row block per snapshot; column B holds only members.")
    for c, w in zip("ABCDEFGHIJ", (22, 16, 14, 3, 3, 5, 13, 18, 11, 16)):
        ws.column_dimensions[c].width = w
    header_row(ws, 4, 1, ["Snapshot", "Index member", "Percent weight"])
    header_row(ws, 4, 6, ["k", "Snapshot date", "END_DATE_OVERRIDE", "First row", "Members returned"])
    for k, d in enumerate(SNAPSHOTS):
        r0 = 6 + UNIVERSE_BLOCK * k
        sr = 6 + k
        put(ws, f"A{r0}", f"Snapshot {d.isoformat()}", F_BOLD)
        put(ws, f"B{r0}", f'=BDS(IndexTicker,"{UNIVERSE_FIELD}","END_DATE_OVERRIDE",$H${sr})', fill=FILL_BBG)
        put(ws, f"F{sr}", k)
        put(ws, f"G{sr}", d, F_INPUT, fmt=DATE_FMT)
        put(ws, f"H{sr}", d.strftime("%Y%m%d"), F_INPUT)
        put(ws, f"I{sr}", r0)
        put(ws, f"J{sr}", f"=COUNTA(B{r0}:B{r0 + UNIVERSE_BLOCK - 2})")
    last = 6 + len(SNAPSHOTS)
    put(ws, f"G{last + 1}", "Total member-rows", F_BOLD)
    put(ws, f"J{last + 1}", f"=SUM(J6:J{last - 1})", F_BOLD)
    put(ws, f"G{last + 2}", "Snapshots with < 495 members", F_BOLD)
    put(ws, f"J{last + 2}", f'=COUNTIF(J6:J{last - 1},"<495")', F_BOLD)
    ws[f"J{last + 2}"].comment = Comment("Should be 0 after the refresh. If not, a snapshot failed or returned errors.", "build script")
    ws.freeze_panes = "A5"


def tickers(wb):
    ws = wb.create_sheet("Tickers")
    title(ws, "Tickers", "Paste the de-duplicated Universe members (values only) into column B from B5, e.g. 'AAPL UW'. Every per-security sheet reads this list.")
    for c, w in zip("ABCDEFG", (6, 18, 22, 40, 3, 34, 10)):
        ws.column_dimensions[c].width = w
    header_row(ws, 4, 1, ["Slot", "Member (paste here)", "Bloomberg security", "Notes"])
    for slot in range(1, N_SLOTS + 1):
        r = slot + 4
        put(ws, f"A{r}", slot)
        put(ws, f"B{r}", None, fill=FILL_USER)
        put(ws, f"C{r}", f'=IF(B{r}="","",B{r}&" Equity")')
        put(ws, f"D{r}", None, fill=FILL_USER)
    end = N_SLOTS + 4
    checks = [
        ("Members pasted", f"=COUNTA(B5:B{end})"),
        ("Duplicates (must be 0)", f'=SUMPRODUCT((B5:B{end}<>"")*(COUNTIF(B5:B{end},B5:B{end})>1))'),
        ("Already end in ' Equity' (must be 0)", f'=COUNTIF(B5:B{end},"* Equity")'),
        ("Slots left", f"={N_SLOTS}-COUNTA(B5:B{end})"),
    ]
    for i, (lab, f) in enumerate(checks, start=4):
        put(ws, f"F{i}", lab, F_BOLD)
        put(ws, f"G{i}", f, F_BOLD)
    ws.freeze_panes = "A5"


def static(wb):
    ws = wb.create_sheet("Static")
    title(ws, "Static", "Reference fields for every slot (current values). GICS is today's classification and must not be read as history.")
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 20
    header_row(ws, 4, 1, ["Slot", "Security"] + STATIC)
    for i in range(len(STATIC)):
        ws.column_dimensions[col(3 + i)].width = 20
    for slot in range(1, N_SLOTS + 1):
        r = slot + 4
        tick = f"Tickers!$B{r}"
        put(ws, f"A{r}", slot)
        put(ws, f"B{r}", f'=IF({tick}="","",{tick}&" Equity")', F_LINK)
        for i in range(len(STATIC)):
            c = col(3 + i)
            put(ws, f"{c}{r}", f'=IF({tick}="","",BDP({tick}&" Equity",{c}$4))', fill=FILL_BBG if slot == 1 else None)
    ws.freeze_panes = "C5"


def index_daily(wb):
    ws = wb.create_sheet("Index_Daily")
    title(ws, "Index_Daily", f"Market-level series, trading days, {PULL_START} to {PULL_END}.")
    row_labels(ws)
    c0 = 2
    for sec, fields in INDEX_SERIES:
        c0 += block(ws, c0, sec, fields, f"=BDH({col(c0)}$4,{col(c0 + 1)}$5:{col(c0 + len(fields))}$5,PullStart,PullEnd,{INDEX_OPTS})",
                    font_sec=F_INPUT)
    ws.freeze_panes = "B6"


def earnings(wb):
    ws = wb.create_sheet("Earnings_Optional")
    title(ws, "Earnings_Optional", f"{EARN_FIELD} for every slot (bulk field, headers on). Refresh only after Market and News_Core, and only without data-limit warnings.")
    row_labels(ws)
    c0 = 2
    for slot in range(1, N_SLOTS + 1):
        tick = f"Tickers!$B${slot + 4}"
        L0 = col(c0)
        put(ws, f"{L0}3", slot, F_SUB)
        put(ws, f"{L0}4", f'=IF({tick}="","",{tick}&" Equity")', F_LINK)
        put(ws, f"{L0}6", f'=BDS({tick}&" Equity","{EARN_FIELD}","Headers=Y")', fill=FILL_BBG)
        c0 += 9
    ws.freeze_panes = "B6"


def pull_log(wb):
    ws = wb.create_sheet("Pull_Log")
    title(ws, "Pull_Log", "One row per sheet. Fill the yellow cells as you go; the grey columns count problems on each sheet's first data row.")
    heads = ["Sheet", "Refreshed on", "Start time", "End time", "Refreshed by", "Terminal / machine",
             "Still requesting", "Failed requests (#N/A)", "Data-limit message (Y/N)", "Notes"]
    widths = [18, 13, 10, 10, 16, 18, 15, 19, 18, 60]
    header_row(ws, 4, 1, heads)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[col(i)].width = w
    rng = {
        "Field_Check": "Field_Check!$E$5:$E$40",
        "Pilot": "Pilot!$10:$10",
        "Universe": "Universe!$B:$B",
        "Tickers": None,
        "Static": f"Static!$C$5:${col(2 + len(STATIC))}${N_SLOTS + 4}",
        "Index_Daily": "Index_Daily!$6:$6",
        "Market": "Market!$6:$6",
        "News_Core": "News_Core!$6:$6",
        "News_Optional": "News_Optional!$6:$6",
        "Earnings_Optional": "Earnings_Optional!$6:$6",
    }
    for r, (sheet, ref) in enumerate(rng.items(), start=5):
        put(ws, f"A{r}", sheet, F_BOLD)
        for c in "BCDEFIJ":
            put(ws, f"{c}{r}", None, fill=FILL_USER, fmt=DATE_FMT if c == "B" else ("hh:mm" if c in "CD" else None))
        if ref:
            put(ws, f"G{r}", f'=COUNTIF({ref},"*Requesting*")')
            put(ws, f"H{r}", f'=COUNTIF({ref},"#N/A*")')
        else:
            put(ws, f"G{r}", "n/a", F_SUB)
            put(ws, f"H{r}", "n/a", F_SUB)
    put(ws, "A17", "Example of a filled row (format only):", F_SUB)
    for c, v in zip("ABCDEFGHIJ", ["Market", "2026-11-05", "14:10", "14:55", "N. Botushanski", "RiskLab terminal 3", 0, 118, "N", "118 = empty slots 683-800 (invalid security), as expected"]):
        put(ws, f"{c}18", v, F_SUB)
    put(ws, "A20", "Press Shift+F9 on this sheet after a refresh to update the grey counts.", F_SUB)


def main():
    wb = Workbook()
    wb._named_styles["Normal"].font = Font(name=ARIAL, size=10)
    readme(wb)
    config(wb)
    field_check(wb)
    positions = pilot(wb)
    pilot_checks(wb, positions)
    universe(wb)
    tickers(wb)
    static(wb)
    index_daily(wb)
    per_security_sheet(wb, "Market", MARKET_FIELDS, PRICE_OPTS,
                       f"{', '.join(MARKET_FIELDS)}; trading days; split-adjusted prices; {PULL_START} to {PULL_END}.")
    per_security_sheet(wb, "News_Core", NEWS_CORE, NEWS_OPTS,
                       f"{', '.join(NEWS_CORE)}; every calendar day; blank when no stories; {PULL_START} to {PULL_END}.")
    per_security_sheet(wb, "News_Optional", NEWS_OPT, NEWS_OPTS,
                       "Optional: story counts by tone and news heat. Refresh after News_Core, only without data-limit warnings.")
    earnings(wb)
    pull_log(wb)
    # Manual calculation, no recalculation on load or save: nothing is requested until a sheet is refreshed.
    wb.calculation = CalcProperties(calcId=191029, calcMode="manual", fullCalcOnLoad=False, calcOnSave=False)
    for ws in wb.worksheets:
        ws.sheet_view.zoomScale = 90
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes); sheets: {', '.join(wb.sheetnames)}")


if __name__ == "__main__":
    main()
