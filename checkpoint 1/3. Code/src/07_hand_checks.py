"""07 Ten hand-checked observations: trace each value from the raw terminal workbook to the final panel variable.

Selection rule (frozen before looking): a simple random sample of 10 security-days, seed 20261108, from panel rows
that have a vendor sentiment value, a same-day open-to-close return and a next-day close-to-close return.

For each observation the script reads the cached cell values straight out of the raw workbook
(P2_Bloomberg_Pull_20261106.xlsx, streamed XML, no Excel or Bloomberg needed), then compares:
  raw workbook cell  ->  export CSV (market_daily / news_daily)  ->  panel variable  ->  recomputed by hand here
Also exported: the seven terminal checks from the Pilot_Checks sheet (workbook value vs HP/GP on the terminal).

Outputs: outputs/diagnostics/hand_checks.csv, outputs/diagnostics/pilot_terminal_checks.csv,
         outputs/diagnostics/07_hand_checks_summary.txt
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ANALYTIC, DIAG, RAW_WORKBOOK, load_market, load_news, load_securities, rel, trading_days, write_text  # noqa: E402

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SEED, N = 20261108, 10
MARKET_W, NEWS_W = 7, 4                   # block widths in the pull workbook (date + fields + spacer)


def col_letter(i: int) -> str:
    s = ""
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def shared_strings(z: zipfile.ZipFile) -> list[str]:
    out = []
    with z.open("xl/sharedStrings.xml") as fh:
        for _, si in etree.iterparse(fh, tag=NS + "si"):
            out.append("".join(t.text or "" for t in si.iter(NS + "t")))
            si.clear()
    return out


def sheet_path(z: zipfile.ZipFile, name: str) -> str:
    wbx = z.read("xl/workbook.xml").decode()
    rid = re.search(rf'<sheet [^>]*name="{re.escape(name)}"[^>]*r:id="([^"]+)"', wbx).group(1)
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    tgt = re.search(rf'<Relationship [^>]*Id="{rid}"[^>]*Target="([^"]+)"', rels) or \
        re.search(rf'<Relationship [^>]*Target="([^"]+)"[^>]*Id="{rid}"', rels)
    return "xl/" + tgt.group(1).lstrip("/").replace("xl/", "")


def read_columns(z, sheet: str, cols: set[int], sst: list[str]) -> dict[tuple[int, int], object]:
    """Stream one worksheet and keep only the cells in the given columns: {(row, col): value}."""
    keep = {}
    with z.open(sheet_path(z, sheet)) as fh:
        for _, row in etree.iterparse(fh, tag=NS + "row"):
            r = int(row.get("r"))
            for c in row.iterfind(NS + "c"):
                ref = c.get("r")
                letters = ref.rstrip("0123456789")
                ci = col_index(letters)
                if ci in cols:
                    v = c.find(NS + "v")
                    if v is None:
                        is_ = c.find(NS + "is")
                        val = "".join(t.text or "" for t in is_.iter(NS + "t")) if is_ is not None else None
                    elif c.get("t") == "s":
                        val = sst[int(v.text)]
                    elif c.get("t") in ("str", "e", "inlineStr"):
                        val = v.text
                    else:
                        val = float(v.text)
                    keep[(r, ci)] = val
            row.clear()
    return keep


def excel_serial(d: pd.Timestamp) -> float:
    return float((d - pd.Timestamp("1899-12-30")).days)


# ------------------------------------------------------------------ the sample
p = pd.read_csv(ANALYTIC / "panel_security_day.csv.gz", parse_dates=["date"], low_memory=False)
elig = p[p["has_sentiment"].astype("boolean").fillna(False).astype(bool) & p["ret_oc_d0"].notna() & p["ret_cc_d1"].notna()]
sample = elig.sample(N, random_state=SEED).sort_values("date").reset_index(drop=True)
sec = load_securities().set_index("ticker_exch")
sample["slot"] = sample["ticker_exch"].map(sec["slot"]).astype(int)
td = trading_days()
nxt = pd.Series(td[1:], index=td[:-1])
sample["next_day"] = sample["date"].map(nxt)

# ------------------------------------------------------------------ read the raw workbook
z = zipfile.ZipFile(RAW_WORKBOOK)
sst = shared_strings(z)
mcols = {(2 + (s - 1) * MARKET_W) + k for s in sample["slot"] for k in range(6)}
ncols = {(2 + (s - 1) * NEWS_W) + k for s in sample["slot"] for k in range(3)}
mk = read_columns(z, "Market", mcols, sst)
nw = read_columns(z, "News_Core", ncols, sst)


def find_row(cells, c0, serial):
    for (r, c), v in cells.items():
        if c == c0 and r >= 6 and isinstance(v, float) and v == serial:
            return r
    return None


mkt = load_market().set_index(["ticker_exch", "date"])
news = load_news().set_index(["ticker_exch", "date"])
rows = []
for i, o in sample.iterrows():
    t, d, d1, slot = o["ticker_exch"], o["date"], o["next_day"], o["slot"]
    m0, n0 = 2 + (slot - 1) * MARKET_W, 2 + (slot - 1) * NEWS_W
    hdr_ok = (mk.get((3, m0)) == float(slot) and mk.get((5, m0 + 1)) == "PX_OPEN" and mk.get((5, m0 + 3)) == "TOT_RETURN_INDEX_GROSS_DVDS"
              and nw.get((3, n0)) == float(slot) and nw.get((5, n0 + 1)) == "NEWS_SENTIMENT_DAILY_AVG")
    r_d, r_d1 = find_row(mk, m0, excel_serial(d)), find_row(mk, m0, excel_serial(d1))
    rn = find_row(nw, n0, excel_serial(d))
    raw_open, raw_last, raw_tri = mk.get((r_d, m0 + 1)), mk.get((r_d, m0 + 2)), mk.get((r_d, m0 + 3))
    raw_tri1 = mk.get((r_d1, m0 + 3))
    raw_sent = nw.get((rn, n0 + 1))
    csv_sent = news.loc[(t, d), "news_sentiment_daily_avg"]
    csv_open, csv_last, csv_tri = mkt.loc[(t, d), ["px_open", "px_last", "tot_return_index_gross_dvds"]]
    csv_tri1 = mkt.loc[(t, d1), "tot_return_index_gross_dvds"]
    hand_oc = raw_last / raw_open - 1
    hand_cc1 = raw_tri1 / raw_tri - 1
    checks = {
        "sentiment: raw = csv = panel": np.isclose(raw_sent, csv_sent, rtol=0, atol=1e-12) and np.isclose(csv_sent, o["news_sentiment_daily_avg"], atol=1e-12),
        "open/close/TRI: raw = csv": all(np.isclose(a, b, rtol=1e-12) for a, b in [(raw_open, csv_open), (raw_last, csv_last), (raw_tri, csv_tri), (raw_tri1, csv_tri1)]),
        "ret_oc_d0: hand = panel": np.isclose(hand_oc, o["ret_oc_d0"], rtol=1e-9, atol=1e-12),
        "ret_cc_d1: hand = panel": np.isclose(hand_cc1, o["ret_cc_d1"], rtol=1e-9, atol=1e-12),
        "membership snapshot before the date": pd.Timestamp(o["snapshot_date"]) < d,
        "workbook block header matches the slot": hdr_ok,
    }
    rows.append({
        "check_id": f"H{i + 1:02d}", "ticker_exch": t, "date": d.date(), "next_trading_day": d1.date(), "slot": slot,
        "market_cells": f"Market!{col_letter(m0)}{r_d}:{col_letter(m0 + 3)}{r_d} and {col_letter(m0 + 3)}{r_d1}",
        "news_cell": f"News_Core!{col_letter(n0 + 1)}{rn}",
        "raw_sentiment": raw_sent, "panel_sentiment": o["news_sentiment_daily_avg"],
        "raw_px_open": raw_open, "raw_px_last": raw_last, "raw_tri_d": raw_tri, "raw_tri_d1": raw_tri1,
        "hand_ret_oc_d0": hand_oc, "panel_ret_oc_d0": o["ret_oc_d0"],
        "hand_ret_cc_d1": hand_cc1, "panel_ret_cc_d1": o["ret_cc_d1"],
        "snapshot_date": pd.Timestamp(o["snapshot_date"]).date(),
        "result": "PASS" if all(checks.values()) else "FAIL: " + ", ".join(k for k, v in checks.items() if not v),
    })
hc = pd.DataFrame(rows)
hc.to_csv(DIAG / "hand_checks.csv", index=False)

# ------------------------------------------------------------------ the seven terminal checks from the pilot
pc = read_columns(z, "Pilot_Checks", set(range(1, 11)), sst)
pt = []
for r in range(5, 12):
    pt.append({"check": int(pc[(r, 1)]), "what": pc.get((r, 2)), "security": pc.get((r, 3)), "field": pc.get((r, 4)),
               "date": (pd.Timestamp("1899-12-30") + pd.Timedelta(days=pc[(r, 5)])).date(),
               "workbook_value": pc.get((r, 6)), "terminal_value": pc.get((r, 7)), "result": pc.get((r, 9)),
               "where_read": pc.get((r, 10))})
pt = pd.DataFrame(pt)
pt.to_csv(DIAG / "pilot_terminal_checks.csv", index=False)

lines = ["07_hand_checks", f"raw workbook: {rel(RAW_WORKBOOK)}", f"selection: seed {SEED}, {N} draws from {len(elig):,} eligible rows", "",
         hc[["check_id", "ticker_exch", "date", "news_cell", "raw_sentiment", "hand_ret_oc_d0", "hand_ret_cc_d1", "result"]].to_string(index=False),
         "", f"PASS: {(hc['result'] == 'PASS').sum()} of {len(hc)}", "",
         "Terminal checks recorded on the Pilot_Checks sheet (2026-11-06):", pt[["check", "security", "field", "date", "workbook_value",
                                                                                 "terminal_value", "result"]].to_string(index=False)]
write_text(DIAG / "07_hand_checks_summary.txt", "\n".join(lines))
print("\n".join(lines))
