# Is the Vendor's Secret Sauce Priced? Bloomberg vs a Reproducible Sentiment Score on Identical Text

- Student: Botushanski, Neill Liran
- Assignment: Project 2 (Dynamic Data Science) | Proposal A16-02 | Supervisor: Professor Hamid
- Brief and guide: `project_2.md`, `project_2_details.md` (see `docs/`)

## Question and hypothesis

Does the divergence between Bloomberg's proprietary news sentiment and a reproducible lexicon/transformer score on the
same headlines carry information for subsequent returns? Hypothesis: it is mostly noise, and adds nothing robust beyond
the reproducible score (an honest null on a "black-box premium"). S&P 500 single names, 2020-2025, daily.

## Status (2026-11-08): ready for the first supervisor checkpoint

- Bloomberg pull done on the RiskLab terminal on 2026-11-06 and copied unchanged to `data/raw_bloomberg/20261106/`
  (every hash matches). `News_Articles.csv` copied from the RiskLab drive to `data/raw_risklab/`.
- Validated, merged into a point-in-time panel (759,846 security-days, 2020-2025) and described. No hypothesis test yet.
- **Checkpoint 1 folder:** `checkpoint 1/` holds a frozen copy of the report, slides, code, outputs and manifests.
- **Checkpoint pack:** `outputs/diagnostics/checkpoint_1_pack.md` (the seven items, decisions, limitations, questions).
- **Consolidated report:** `reports/first_checkpoint_report.ipynb` (renders on GitHub, or open in Jupyter).
- Primary identical-text sample: the 188 headlines in `News_Articles.csv` (no Bloomberg headline export; decision D1).
- Still to add: copies of the three RiskLab vendor-sentiment files used as cross-checks (`design_decisions.md`, O4).

## Rebuild everything

From this folder: `python src/run_all.py` (about 2 minutes). It reruns 02 to 07 and the report from the raw files.

## Bloomberg pull: what to do at the terminal

1. Copy `bloomberg_pull/P2_Bloomberg_Pull.xlsx` to the terminal and open it in Excel with the Bloomberg add-in loaded.
2. Follow the README sheet inside the workbook: Field_Check, Pilot (and Pilot_Checks), Universe, Tickers, Static,
   Index_Daily, Market, News_Core, then the optional sheets. Refresh one sheet at a time (Bloomberg > Refresh > Refresh
   Worksheet); the workbook is in manual calculation so nothing is requested until you do.
3. Save as `P2_Bloomberg_Pull_YYYYMMDD.xlsx` and bring it back unchanged.
4. Here: put it in `data/raw_bloomberg/YYYYMMDD/` and run, from this folder,
   `python src/01a_freeze_bloomberg_pull.py data/raw_bloomberg/YYYYMMDD/P2_Bloomberg_Pull_YYYYMMDD.xlsx`.
   It hashes the workbook, writes one CSV per table into `tables/`, replaces the planned rows in
   `manifests/bloomberg_source_log.csv` and writes `outputs/diagnostics/01a_freeze_bloomberg_pull_summary.txt`.

If a field name turns out to be wrong in FLDS, change it in `src/00a_build_bloomberg_pull_workbook.py` and run
`python src/00a_build_bloomberg_pull_workbook.py` to rebuild the workbook, rather than editing formulas by hand.

## Folders

| Folder | What goes in it |
|---|---|
| `bloomberg_pull/` | The pull workbook (formulas only; built by `src/00a_...`) |
| `config/` | `project_config.yaml`: every value used by more than one script |
| `data/raw_bloomberg/` | One dated folder per terminal pull: the workbook as saved on the terminal plus `tables/` (immutable) |
| `data/raw_risklab/` | RiskLab copies: `News_Articles.csv` now; the three vendor-sentiment cross-check files to add (immutable) |
| `data/reference_from_drive/` | RiskLab catalogue (2026-09-18 copy from Project 1) and `data_paths.py` |
| `data/interim/`, `data/analytic/` | Derived data only |
| `manifests/` | `bloomberg_source_log.csv`, `data_manifest.csv`, `sample_attrition.csv` |
| `src/` | Scripts, numbered in run order (same scheme as Project 1); `common.py` holds shared paths; `run_all.py` runs them |
| `reports/` | The checkpoint report (notebook and HTML), the progress deck, and the presentation script (`presentation_script.md` and its PDF) |
| `outputs/` | `tables/`, `figures/`, `diagnostics/`, `models/` |
| `paper/` | Paper draft |

## Data

Bloomberg data and the RiskLab files are proprietary (no redistribution), so this repository holds the code,
configuration, manifests, design log, outputs and reports, but no data. The folders under `data/` are empty placeholders
that show where each file goes. Anyone with Bloomberg and RiskLab access can rebuild everything: run the pull described
above, copy `News_Articles.csv` into `data/raw_risklab/`, then run `python src/run_all.py`.

For the same reason, the public copy of the report leaves out the table that lists the RiskLab headlines, and
`outputs/diagnostics/news_articles_validation.csv` (a copy of those headlines with validation flags) is not included.
