"""Freeze a refreshed Bloomberg pull: hash it, export one CSV per table, and log it.

Usage, from the project root, after copying the workbook saved on the terminal into its own
dated folder (never edit that file):

    python src/01a_freeze_bloomberg_pull.py data/raw_bloomberg/20261105/P2_Bloomberg_Pull_20261105.xlsx

Steps
  1. SHA-256 of the workbook exactly as saved on the terminal. This is the raw file.
  2. Stop if any cell still shows "#N/A Requesting Data...": the file was saved before the refresh finished.
  3. Read the values Bloomberg wrote (openpyxl, data_only=True) and write a tables/ folder next
     to the workbook with one CSV per coherent table. Values are copied as they are: Bloomberg
     error text such as "#N/A N/A" is kept, blanks stay blank. Only the layout changes (blocks
     side by side become one long table).
  4. Hash every CSV and rewrite manifests/bloomberg_source_log.csv: planned rows are replaced by
     the rows for this pull; rows from earlier pulls are kept.
  5. Write outputs/diagnostics/01a_freeze_bloomberg_pull_summary.txt.

Nothing is cleaned, filtered or merged here. That happens in 02_raw_validation and later steps.
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

PER_SECURITY = {   # sheet -> (output file, terminal function, frequency, adjustment note)
    "Market": ("market_daily.csv", "BDH", "daily (trading days)",
               "prices split/capital-change adjusted only (CapChg=Y, CshAdjNormal=N, CshAdjAbnormal=N, UseDPDF=N); "
               "returns from TOT_RETURN_INDEX_GROSS_DVDS"),
    "News_Core": ("news_core_daily.csv", "BDH", "daily (calendar days)", "none; blank when no value (Fill=B)"),
    "News_Optional": ("news_optional_daily.csv", "BDH", "daily (calendar days)", "none; blank when no value (Fill=B)"),
    "Index_Daily": ("index_daily.csv", "BDH", "daily (trading days)", "none (index levels)"),
}
GRID_SHEETS = ["Field_Check", "Pilot", "Pilot_Checks", "Pull_Log", "Config"]
SOURCE_LOG_COLS = ["source_type", "provider", "terminal_function", "security_or_series_id", "field",
                   "field_description", "frequency", "start", "end", "currency", "units", "timezone",
                   "adjustment", "retrieval_date", "file_name", "file_hash", "notes"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def as_date(v):
    """Bloomberg dates arrive as datetimes (date-formatted cells) or as Excel serial numbers."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)) and 20000 < v < 80000:
        return from_excel(v).date()
    return v   # text such as '#N/A Invalid Security' is kept as it is


def cell_text(v):
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return as_date(v).isoformat()
    return v


def write_csv(path: Path, header, rows) -> int:
    n = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow([cell_text(x) for x in r])
            n += 1
    return n


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and float(v).is_integer()


def sheet_rows(wb, name):
    """All cell values of a sheet, every row padded to the same length (read-only mode can trim rows)."""
    rows = [list(r) for r in wb[name].iter_rows(values_only=True)]
    width = max((len(r) for r in rows), default=0)
    for r in rows:
        r.extend([None] * (width - len(r)))
    for r in rows[:3]:                      # slot numbers may come back as floats
        for j, v in enumerate(r):
            if is_num(v):
                r[j] = int(v)
    return rows


def read_tickers(wb):
    rows = sheet_rows(wb, "Tickers")
    out = {}
    for r in rows[4:]:
        if is_num(r[0]) and r[1] not in (None, ""):
            out[int(r[0])] = str(r[1]).strip()
    return out


def export_per_security(rows, tickers, out_path):
    """Blocks are found by the 'date' header in row 5; row 3 holds the slot (if any), row 4 the security."""
    r3, r4, r5 = rows[2], rows[3], rows[4]
    data = rows[5:]
    blocks = []
    for j, h in enumerate(r5):
        if h == "date":
            fields = []
            k = j + 1
            while k < len(r5) and r5[k] not in (None, "", "date"):
                fields.append(str(r5[k]))
                k += 1
            slot = r3[j] if isinstance(r3[j], int) else None
            sec = f"{tickers[slot]} Equity" if slot in tickers else (r4[j] if isinstance(r4[j], str) else "")
            blocks.append((j, slot, sec, fields))
    all_fields = list(dict.fromkeys(f for b in blocks for f in b[3]))
    stats = {"blocks": len(blocks), "with_data": 0, "failed": [], "empty_slots": 0, "rows": 0,
             "min": None, "max": None, "error_cells": Counter()}

    def gen():
        for j, slot, sec, fields in blocks:
            if slot is not None and slot not in tickers:
                stats["empty_slots"] += 1
                continue
            first = data[0][j] if data else None
            if not isinstance(as_date(first), date):
                stats["failed"].append(f"{sec} [{first}]")
                continue
            stats["with_data"] += 1
            for r in data:
                d = as_date(r[j]) if j < len(r) else None
                if d is None:
                    break
                vals = {f: (r[j + 1 + i] if j + 1 + i < len(r) else None) for i, f in enumerate(fields)}
                for v in vals.values():
                    if isinstance(v, str) and v.startswith("#"):
                        stats["error_cells"][v] += 1
                if isinstance(d, date):
                    stats["min"] = d if stats["min"] is None else min(stats["min"], d)
                    stats["max"] = d if stats["max"] is None else max(stats["max"], d)
                stats["rows"] += 1
                yield [slot if slot is not None else "", sec, d] + [vals.get(f) for f in all_fields]

    write_csv(out_path, ["slot", "security", "date"] + all_fields, gen())
    return all_fields, stats


def export_universe(rows, out_path):
    side = [r for r in rows[5:] if len(r) > 8 and is_num(r[5]) and is_num(r[8])]
    stats = {"snapshots": len(side), "per_snapshot": {}, "members": set()}

    def gen():
        for r in side:
            snap, first = as_date(r[6]), int(r[8])
            n = 0
            for rr in rows[first - 1:first - 1 + 598]:
                if rr[1] in (None, ""):
                    break
                n += 1
                stats["members"].add(str(rr[1]).strip())
                yield [snap, rr[1], rr[2]]
            stats["per_snapshot"][snap] = n

    write_csv(out_path, ["snapshot_date", "index_member", "percent_weight"], gen())
    return stats


def export_static(rows, tickers, out_path):
    header = [str(h) for h in rows[3][2:] if h not in (None, "")]

    def gen():
        for r in rows[4:]:
            if is_num(r[0]) and int(r[0]) in tickers:
                yield [int(r[0]), f"{tickers[int(r[0])]} Equity"] + r[2:2 + len(header)]

    n = write_csv(out_path, ["slot", "security"] + header, gen())
    return header, n


def export_earnings(rows, tickers, out_path):
    r3, data = rows[2], rows[5:]
    starts = [j for j, v in enumerate(r3) if isinstance(v, int)]
    heads = []
    for j in starts:
        if r3[j] in tickers and data and isinstance(data[0][j], str) and not data[0][j].startswith("#"):
            k = j
            while k < len(data[0]) and k < j + 8 and data[0][k] not in (None, ""):
                if data[0][k] not in heads:
                    heads.append(data[0][k])
                k += 1
    failed = []

    def gen():
        for j in starts:
            slot = r3[j]
            if slot not in tickers:
                continue
            hdr_row = data[0] if data else []
            if not hdr_row or not isinstance(hdr_row[j], str) or hdr_row[j].startswith("#"):
                failed.append(f"{tickers[slot]} Equity [{hdr_row[j] if hdr_row else None}]")
                continue
            local = []
            k = j
            while k < len(hdr_row) and k < j + 8 and hdr_row[k] not in (None, ""):
                local.append(hdr_row[k])
                k += 1
            for n, r in enumerate(data[1:], start=1):
                if r[j] in (None, ""):
                    break
                vals = dict(zip(local, r[j:j + len(local)]))
                yield [slot, f"{tickers[slot]} Equity", n] + [vals.get(h) for h in heads]

    n = write_csv(out_path, ["slot", "security", "row"] + heads, gen())
    return heads, n, failed


def export_grid(rows, out_path):
    def gen():
        for i, r in enumerate(rows, start=1):
            for j, v in enumerate(r, start=1):
                if v not in (None, ""):
                    yield [i, j, v]
    return write_csv(out_path, ["row", "col", "value"], gen())


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    wb_path = Path(argv[1]).resolve()
    root = Path.cwd()
    pull_dir = wb_path.parent
    tables = pull_dir / "tables"
    tables.mkdir(exist_ok=True)
    rel = lambda p: str(p.resolve().relative_to(root)) if p.resolve().is_relative_to(root) else str(p)

    wb_hash = sha256(wb_path)
    wb = load_workbook(wb_path, data_only=True, read_only=True)

    # 2. refuse a half-finished pull
    requesting = Counter()
    cache = {name: sheet_rows(wb, name) for name in wb.sheetnames}
    for name, rows in cache.items():
        for r in rows:
            for v in r:
                if isinstance(v, str) and v.startswith("#N/A Requesting"):   # Bloomberg's placeholder while waiting
                    requesting[name] += 1
    if requesting:
        sys.exit(f"STOP: cells still requesting data {dict(requesting)}. Refresh those sheets on the terminal, wait, save, and copy again.")

    tickers = read_tickers(wb)
    log = {}   # per-sheet retrieval dates from Pull_Log
    for r in cache["Pull_Log"][4:15]:
        if r and r[0]:
            log[r[0]] = as_date(r[1]) if r[1] not in (None, "") else None
    m = re.search(r"(20\d{6})", pull_dir.name)
    default_date = datetime.strptime(m.group(1), "%Y%m%d").date() if m else None
    descr = {}
    for r in cache["Field_Check"][4:]:
        if r and isinstance(r[0], str) and r[0].isupper() and len(r) > 6 and r[6]:
            descr[r[0]] = str(r[6])

    summary, entries = [], []

    def retrieved(sheet):
        d = log.get(sheet) or default_date
        return (d.isoformat() if isinstance(d, date) else str(d or "")), ("Pull_Log" if log.get(sheet) else "folder name")

    def add(sheet, func, sec_id, fields, freq, start, end, adjustment, path, notes):
        rd, rd_src = retrieved(sheet)
        entries.append({
            "source_type": "Bloomberg terminal, Excel add-in", "provider": "Bloomberg", "terminal_function": func,
            "security_or_series_id": sec_id, "field": "; ".join(fields),
            "field_description": "; ".join(f"{f}: {descr[f]}" for f in fields if f in descr),
            "frequency": freq, "start": start or "", "end": end or "",
            "currency": "USD expected; per security in static.csv (CRNCY)", "units": "see Field_Check (units and timing per FLDS)",
            "timezone": "dates as returned by Bloomberg; news day boundary per FLDS (Field_Check)",
            "adjustment": adjustment, "retrieval_date": rd, "file_name": rel(path), "file_hash": sha256(path),
            "notes": f"{notes} Retrieval date from {rd_src}. Exported from {wb_path.name} (sha256 {wb_hash[:12]}...).",
        })

    # 3. tables
    u = export_universe(cache["Universe"], tables / "universe_snapshots.csv")
    counts = list(u["per_snapshot"].values())
    pasted = set(tickers.values())
    summary.append(f"Universe: {u['snapshots']} snapshots, {min(counts) if counts else 0}-{max(counts) if counts else 0} members each, "
                   f"{len(u['members'])} distinct members.")
    summary.append(f"Tickers: {len(tickers)} pasted; in Universe but not pasted: {sorted(u['members'] - pasted)[:20]}; "
                   f"pasted but not in Universe: {sorted(pasted - u['members'])[:20]}.")
    dup = [t for t, c in Counter(tickers.values()).items() if c > 1]
    if dup:
        summary.append(f"WARNING duplicate tickers pasted: {dup}")
    snaps = sorted(u["per_snapshot"])
    add("Universe", "BDS", "SPX Index", ["INDX_MWEIGHT_HIST"], "monthly (month-end snapshots)",
        snaps[0].isoformat() if snaps else "", snaps[-1].isoformat() if snaps else "", "n/a",
        tables / "universe_snapshots.csv", "END_DATE_OVERRIDE = each month-end.")

    write_csv(tables / "tickers.csv", ["slot", "index_member", "security"],
              ([s, t, f"{t} Equity"] for s, t in sorted(tickers.items())))
    add("Tickers", "none (de-duplicated Universe members, pasted as values)", f"{len(tickers)} securities", ["index_member"],
        "static", "", "", "n/a", tables / "tickers.csv", "Request list used by every per-security sheet.")

    hdr, n = export_static(cache["Static"], tickers, tables / "static.csv")
    summary.append(f"Static: {n} securities x {len(hdr)} fields.")
    add("Static", "BDP", f"{n} securities (tickers.csv)", hdr, "static (current values on retrieval date)", "", "",
        "n/a; current classification only", tables / "static.csv", "Current snapshot; not point-in-time.")

    for sheet, (fname, func, freq, adj) in PER_SECURITY.items():
        fields, st = export_per_security(cache[sheet], tickers, tables / fname)
        summary.append(f"{sheet}: {st['with_data']} securities with data, {len(st['failed'])} failed, {st['empty_slots']} empty slots, "
                       f"{st['rows']:,} rows, {st['min']} to {st['max']}; error cells {dict(st['error_cells'])}; "
                       f"failed: {st['failed'][:15]}")
        if st["blocks"] and st["rows"] == 0:
            summary.append(f"  ({sheet} returned no data: not refreshed yet, or every request failed)")
        add(sheet, func, f"{st['with_data']} securities" if sheet != "Index_Daily" else "SPX Index; SPXT Index; VIX Index",
            fields, freq, st["min"].isoformat() if st["min"] else "", st["max"].isoformat() if st["max"] else "",
            adj, tables / fname, f"{len(st['failed'])} failed requests.")

    heads, n, failed = export_earnings(cache["Earnings_Optional"], tickers, tables / "earnings_optional.csv")
    summary.append(f"Earnings_Optional: {n:,} rows, columns {heads}, {len(failed)} failed: {failed[:10]}")
    add("Earnings_Optional", "BDS", "per security (tickers.csv)", ["EARN_ANN_DT_TIME_HIST_WITH_EPS"], "event", "", "",
        "n/a", tables / "earnings_optional.csv", f"Headers=Y. {len(failed)} failed requests.")

    for sheet in GRID_SHEETS:
        export_grid(cache[sheet], tables / f"{sheet.lower()}_cells.csv")
    summary.append(f"Grid copies (every non-empty cell): {', '.join(GRID_SHEETS)}.")

    # 4. source log
    log_path = root / "manifests" / "bloomberg_source_log.csv"
    old = []
    if log_path.exists():
        with log_path.open(newline="", encoding="utf-8") as fh:
            old = [r for r in csv.DictReader(fh)
                   if r.get("source_type") != "planned" and not r.get("file_name", "").startswith(rel(pull_dir))]
    wb_row = dict.fromkeys(SOURCE_LOG_COLS, "")
    wb_row.update({"source_type": "Bloomberg terminal, Excel add-in (raw workbook)", "provider": "Bloomberg",
                   "terminal_function": "BDS; BDP; BDH", "security_or_series_id": "see tables/",
                   "retrieval_date": retrieved("Market")[0], "file_name": rel(wb_path), "file_hash": wb_hash,
                   "notes": "Workbook exactly as saved on the terminal; built by src/00a_build_bloomberg_pull_workbook.py."})
    with log_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SOURCE_LOG_COLS)
        w.writeheader()
        for r in old + [wb_row] + entries:
            w.writerow({k: r.get(k, "") for k in SOURCE_LOG_COLS})

    # 5. summary
    diag = root / "outputs" / "diagnostics"
    diag.mkdir(parents=True, exist_ok=True)
    text = "\n".join([f"01a_freeze_bloomberg_pull  run {datetime.now():%Y-%m-%d %H:%M}",
                      f"workbook {rel(wb_path)}  sha256 {wb_hash}", ""] + summary +
                     ["", f"{len(entries) + 1} rows written to {rel(log_path)}."])
    (diag / "01a_freeze_bloomberg_pull_summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main(sys.argv)
