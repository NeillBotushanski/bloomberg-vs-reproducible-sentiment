# First supervisor checkpoint: pack

**Project:** Is the Vendor's Secret Sauce Priced? Bloomberg vs a Reproducible Sentiment Score on Identical Text (proposal A16-02)
| **Student:** Botushanski, Neill Liran | **Prepared:** 2026-11-08

Nothing in this pack is a test of the hypothesis. Every number below is in `outputs/tables/checkpoint_1_facts.csv` with
the file it comes from.

## 1. The seven items

| # | Item the guide asks for | Where it is | Status |
|---|---|---|---|
| 1 | Completed design-decision log | `design_decisions.md` | Brief and supervisor items recorded (S1-S4); pull decisions B1-B6 approved; headline source decided (D1); P1-P6 proposed; E1-E2 open |
| 2 | Data manifest | `manifests/data_manifest.csv` | 12 rows: 9 available and validated, 3 RiskLab cross-check files still to copy |
| 3 | Bloomberg pilot and field definitions | Pilot_Checks and Field_Check sheets; `manifests/bloomberg_source_log.csv` | 7/7 terminal checks PASS; 26 fields confirmed in FLDS; 42 source-log rows with hashes |
| 4 | Sample-coverage table | `outputs/tables/coverage_by_year.csv` (+ size, sector, headline tables); `manifests/sample_attrition.csv` | 759,846 member security-days, 630 securities, 1,508 trading days; 82.0% carry a vendor sentiment value |
| 5 | Ten hand-checked observations | `outputs/diagnostics/hand_checks.csv` | 10/10 PASS, raw workbook cell to panel variable |
| 6 | One preliminary descriptive figure | `outputs/figures/fig1_vendor_coverage.png` | Plus Figure 2 (timing risk) and Figure 3 (score distribution) |
| 7 | Written list of unresolved data limitations | Section 4 below | 9 items |

## 2. What has been verified

- **Raw files.** 11/11 raw files match the SHA-256 recorded on the terminal; `News_Articles.csv` was copied
  byte-for-byte from the RiskLab drive (hash matches the RiskLab catalogue).
- **Validation.** 76 checks on schemas, keys, ranges, calendars, timing and joins; 4 flags, all explained
  (holiday values, the weekend gap, and two headline-file problems).
- **Joins.** No duplicate keys, no many-to-many joins; every universe ticker is in the identifier table; the 499 universe
  security-days without a market row are firms delisted or acquired during the month (497) or not yet listed (2).
- **Terminal checks.** Prices, volume, total-return index and the vendor score match HP/GP on the terminal, including the
  AAPL 4-for-1 split (unadjusted / adjusted = 4.00, no jump in the total-return index).
- **Hand checks.** Ten random security-days traced from the raw workbook cells through the export to the panel, with both
  returns recomputed by hand: all match.

## 3. Decisions that need the supervisor's approval

| Id | Proposal (design_decisions.md, section 7) | Alternative |
|---|---|---|
| P1 | Vendor value dated D is usable from the open of D; holiday values from the next open; never carried forward | - |
| P2 | Returns from total-return ratios (close-to-close) and split-adjusted open/close (open-to-close) | Price-only returns |
| P3 | One ticker per company per day; use the other exchange ticker on exchange-switch days (42 security-days) | Drop those days |
| P4 | Member on day t = member at the latest month-end strictly before t | Daily membership (about 1,500 bulk requests) |
| P5 | Headline subset: conservative cutoff (supervisor); compare with the vendor value dated the next weekday, same-day value as sensitivity | Average the two; or keep only the 33 unambiguous headlines |
| P6 | Keep flagged headlines, report with and without them | Delete the 4 flagged rows |

## 4. Unresolved data limitations

1. **Identical text is not yet available at scale (O1).** RiskLab holds no larger Bloomberg headline archive. The fallback
   file has 188 headlines for 19 firms from 95 public sources and 0 from bloomberg.com, with dates
   but no times. They cover 0.025% of member security-days. Whether Bloomberg's daily value scored these exact
   stories cannot be verified without story identifiers. A Bloomberg headline export is not being pursued (D1), so this is the
   primary identical-text sample.
2. **Story-to-value assignment is ambiguous.** For 149 of the 182 headlines with any vendor value, two candidate daily
   values could contain the story (before or after 09:20).
3. **Weekend gap (O6).** Monday values carry 4.8 scored stories per security-day against 14.5 on Tuesday-Thursday
   (holidays 6.0): consistent with a 24-hour window, so news from Friday 09:20 to Sunday 09:20 is in no daily value.
   27 Friday and 3 Saturday headlines are exposed. Not confirmed with Bloomberg; treated as an assumption.
4. **Vendor regime change around 2022 (O7).** Exact zeros fall from 47.2% of values (2020) to 12.7% (2023) and story counts
   roughly halve; full-sample normalisation would leak this change.
5. **Coverage rises with size (O8).** 74.6% of smallest-quintile security-days have a vendor value vs 94.9% of the
   largest; comparisons must be on identical observations.
6. **Headline-file quality (O9).** 3 headlines' URL dates differ from the file date by more than 3 days and 1 has no URL;
   the file's selection rule (ESG-themed, hand-collected) is undocumented.
7. **Intra-month index changes (B2/P4).** Additions enter at the next month-end; 497 security-days fall after a firm's last
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
6. S3: may the secondary exercise on the broad vendor panel (622,570 security-days with sentiment and a next-day return)
   start now, or only after the primary design is frozen?
