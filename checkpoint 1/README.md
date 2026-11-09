# Checkpoint 1: data and exploratory analysis

**Project 2 (A16-02):** Is the Vendor's Secret Sauce Priced? Bloomberg vs a Reproducible Sentiment Score on Identical Text
**Student:** Botushanski, Neill Liran | **Course:** MMF 1941 | **Supervisor:** Professor Hamid | **Prepared:** 2026-11-08

A frozen copy of everything presented at the first supervisor checkpoint. The working project is the parent folder
(`Project 2 - Dynamic Data Science`); this folder is not updated when the project changes.

## Folders

| Folder | What is in it |
|---|---|
| `1. Report` | `first_checkpoint_report.ipynb` (consolidated report; open in Jupyter) and `checkpoint_1_pack.md` (one-page summary) |
| `2. Slides` | `checkpoint_1_progress_update.pptx` (14 slides, speaker notes on each) and a `.pdf` copy; `Checkpoint 1 Presentation Script.pdf` (what to say on each slide, timings, likely questions) and its source text `presentation_script.md` |
| `3. Code` | Every script (`src/`), the configuration (`config/`) and the Bloomberg formula workbook used at the terminal (`bloomberg_pull/`) |
| `4. Outputs` | The tables, figures and diagnostics the report and slides are built from |
| `5. Design log and manifests` | `design_decisions.md`, the data manifest, the Bloomberg source log, sample attrition and the variable dictionary |

## The guide's seven checkpoint items

| # | Item | Where |
|---|---|---|
| 1 | Design-decision log | `5. Design log and manifests/design_decisions.md` |
| 2 | Data manifest | `5. Design log and manifests/data_manifest.csv` |
| 3 | Bloomberg pilot and field definitions | `4. Outputs/diagnostics/pilot_terminal_checks.csv`; `5. Design log and manifests/bloomberg_source_log.csv` |
| 4 | Sample-coverage table | `4. Outputs/tables/coverage_by_year.csv` (+ size, sector, headline tables); `5. Design log and manifests/sample_attrition.csv` |
| 5 | Ten hand-checked observations | `4. Outputs/diagnostics/hand_checks.csv` |
| 6 | Preliminary descriptive figure | `4. Outputs/figures/fig1_vendor_coverage.png` (+ Figures 2 and 3) |
| 7 | Unresolved data limitations | `1. Report/checkpoint_1_pack.md`, section 4 |

## Data and rebuilding

The raw data is not copied here: the Bloomberg pull (336 MB) and the RiskLab files are proprietary and stay in the
parent folder's `data/`. To rebuild every output, run `python src/run_all.py` from the parent folder (about 2.5 minutes;
needs Python with pandas, matplotlib, lxml and markdown, and Node with pptxgenjs). The code in `3. Code` is the
version that produced these files. The notebook finds the parent folder on its own, so Run All works from here too.

`SHA256SUMS.txt` lists the hash of every file in this folder as of 2026-11-08. In this public copy the HTML report and
`news_articles_validation.csv` are left out, the notebook's RiskLab headline table is cleared (proprietary data) and a
contact email is removed from the data manifest and notebook, so those entries will not match.
