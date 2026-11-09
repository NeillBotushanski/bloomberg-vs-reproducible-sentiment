# Design decisions log

**Project:** Is the Vendor's Secret Sauce Priced? Bloomberg vs a Reproducible Sentiment Score on Identical Text
**Student:** Botushanski, Neill Liran | **Proposal:** A16-02 (area A16, alternative data, news & NLP; category C6, data & applications)
**Log opened:** 2026-11-03 | **Last revised:** 2026-11-08 (D1 added)

## 1. How this log works

Same rules as Project 1. Every decision is recorded with the alternatives, the evidence, the reasoning, the date and the approver. Statuses:

- **FIXED BY BRIEF / SUPERVISOR.** Stated in `project_2.md`, `project_2_details.md` or a supervisor's message. I may not change it without approval.
- **DECIDED.** I made the choice on the date shown; supervisor approval recorded at the end of the entry (*pending* until given).
- **PROPOSED.** A choice I propose, with alternatives. Not final until the supervisor decides.
- **SUPERSEDED.** Replaced by a later entry; kept so the order of events stays visible.

Evidence rule: where I choose among alternatives I do not choose by comparing results. **As of 2026-11-08** the Bloomberg pull is frozen, validated and merged into a point-in-time panel, and only descriptive statistics have been computed (coverage, missingness, distributions, timing). No reproducible score has been built, no return has been regressed on any signal and no forecast has been evaluated.

## 2. Supervisor approval record

### 2.1 Reply on the headline data and the pull plan (received by 2026-11-06)

My message of 2026-11-03 asked whether RiskLab holds a larger headline archive, which fallback the supervisor preferred if not, and whether the proposed terminal pull (B1 to B6) was acceptable. Professor Hamid's reply, reproduced exactly as I received it:

> Our current RiskLab catalogue does not contain a larger Bloomberg headline archive suitable for an identical-text comparison. The other public-web news files are not the same Bloomberg-scored universe.
> Please preserve the identical-text comparison as the primary design. First confirm with Bloomberg Help whether headlines, identifiers, timestamps, and ticker mappings may be exported for this academic project. I guess uo can do F1 twice to talk to them. If permitted, begin with a small pilot. If not, use the 188-headline subset, clearly report its selection and coverage, and use a conservative return cutoff. Do not reframe the primary test as a broad same-firm-day comparison. For the reframing we can talk about it later. Not now.
> You may run the broader Bloomberg daily-sentiment analysis as a separate secondary exercise, but it cannot identify Bloomberg's incremental value on identical text.
> Your proposed terminal pull is otherwise approved. Keep 2020–2025 as the analysis period, using July 2019 and January 2026 only as buffers. Use point-in-time membership, total returns, story counts, and strict information-timing rules. The existing local sentiment files can serve as cross-checks. These are all fine. Thanks you doing great!

What it settles: S1 to S4 below; B1 to B6 approved; O1 has a fixed path; O4 resolved.

### 2.2 Fixed by the supervisor (2026-11-06)

- **S1 Identical text stays the primary design.** The primary test compares Bloomberg's score and the reproducible score on the same headlines. It is not reframed as a broad same-firm-day comparison; any reframing is a later conversation.
- **S2 Headline source, in order.** (1) Ask Bloomberg Help (HELP key twice) whether headlines, story identifiers, timestamps and ticker mappings may be exported for this academic project. (2) If permitted, start with a small pilot export. (3) If not, use the 188-headline subset of `News_Articles.csv`, report its selection and coverage, and use a conservative return cutoff.
- **S3 Secondary exercise allowed.** The broader analysis of Bloomberg's daily sentiment across the S&P 500 may be run as a separate, clearly labelled secondary exercise. It cannot identify Bloomberg's incremental value on identical text and is never presented as the primary test.
- **S4 Pull approved.** Analysis period 2020-2025; July 2019 and January 2026 are buffers only. Point-in-time membership, total returns, story counts and strict information-timing rules.

### 2.3 Decided by the student (2026-11-08)

- **D1 Headline source.** The Bloomberg Help question in S2 (step 1) is not being pursued; I treat it as optional. The primary
  identical-text sample is therefore the S2 fallback: the 188-headline subset of `News_Articles.csv`, with its selection and
  coverage reported and a conservative return cutoff (P5, P6). S2's wording named the Help question as the first step, so I
  will mention this choice to the supervisor at the first checkpoint. *Supervisor approval: pending.*

The first checkpoint still needs: this log, the data manifest, the Bloomberg pilot and field definitions, a coverage table, ten hand-checked observations, one descriptive figure and the list of unresolved data limitations (guide, "First supervisor checkpoint").

## 3. Fixed by the brief

- **F1 Question.** Does the divergence between Bloomberg's proprietary news sentiment and a reproducible lexicon/transformer score on the same headlines carry information for subsequent returns?
- **F2 Hypothesis.** The divergence is mostly noise: it does not robustly predict returns beyond the reproducible score (honest null on a "black-box premium").
- **F3 Unit, outcome, estimand.** Security-day; next-day or short-horizon stock return; incremental out-of-sample content of the vendor score on identical text, against the reproducible-score-only model.
- **F4 Sample.** S&P 500 single names, 2020-2025 daily.
- **F5 Methods.** Primary: returns on reproducible score + divergence, HAC/clustered SE, encompassing / Diebold-Mariano. Robustness: purged CV, reproducible-only vs reproducible+vendor features, deflated Sharpe ratio.
- **F6 Data rule.** Bloomberg only for end-of-day, daily, reference, document or event data. Every minute-level series comes from `C:\risklab\data\intraday_data`.

## 4. Decisions to confirm before estimation (from the guide; OPEN)

- **E1 Text universe, deduplication and return cutoff.** OPEN. The text universe is the 188-headline subset (S2 fallback, D1). If the 188-headline subset is used, the return cutoff must be conservative (S2); the exact rule depends on O2 and on whether the headlines carry timestamps.
- **E2 Reproducible scoring rule and primary forecast horizon.** OPEN. Candidates for the score: a finance lexicon (Loughran-McDonald) and a finance transformer (e.g. FinBERT); to be frozen before any return is computed.

## 5. Data-acquisition decisions (proposed 2026-11-03; approved by the supervisor, section 2.1)

These shape what is pulled from the terminal. None of them involves a result. They are implemented in `src/00a_build_bloomberg_pull_workbook.py` and `config/project_config.yaml`.

### B1. Pull window 2019-07-01 to 2026-01-30
- **Proposal:** pull six months before the study window and about one month after it. The study window (F4) does not change.
- **Why:** training-window rescaling (guide hint 3) and lagged controls need history before 2020-01-01; forward returns for late-December 2025 need January 2026.
- **Alternative:** pull exactly 2020-2025 (first months lose their lags; last days lose their outcomes).
- **Approval:** approved by Professor Hamid (reply in section 2.1, received by 2026-11-06).

### B2. Universe: point-in-time S&P 500 members at month-ends
- **Proposal:** `INDX_MWEIGHT_HIST` on `SPX Index` at the 73 month-ends from 2019-12-31 to 2025-12-31; request data for the union of members. A security-day enters the panel if the security was a member at the latest month-end before it (rule to confirm).
- **Why:** includes firms that left the index, so the sample is not survivor-only.
- **Alternatives:** today's constituents (survivorship bias); daily membership (about 1,500 bulk requests instead of 73).
- **Known limitation:** a firm added and removed within one month is missed; additions are seen with up to a month's delay.
- **Approval:** approved by Professor Hamid (reply in section 2.1, received by 2026-11-06).

### B3. Daily returns from the total-return index; prices split-adjusted only
- **Proposal:** daily returns from `TOT_RETURN_INDEX_GROSS_DVDS` (Bloomberg end-of-day). `PX_OPEN` and `PX_LAST` adjusted for splits and capital changes only (`CapChg=Y`, `CshAdjNormal=N`, `CshAdjAbnormal=N`, `UseDPDF=N`), so open-to-close and overnight returns can be formed if E1 needs them. First Rate one-minute stock files are used only for intraday timing checks and as a price cross-check (F6).
- **Alternatives:** returns from First Rate daily closes (the brief lists `intraday_data` for returns; dividends would need a separate source); dividend-adjusted prices.
- **To check on the pilot:** the AAPL 4-for-1 split (2020-08-31): unadjusted / adjusted close = 4.00, and no jump in the total-return index.
- **Approval:** approved by Professor Hamid (reply in section 2.1, received by 2026-11-06).

### B4. News fields on every calendar day, never carried forward
- **Proposal:** news fields are pulled with `Days=A` (weekends kept) and `Fill=B` (blank when there is no value). Weekend stories are later mapped to the next trading day under E1. Days with no stories stay missing; they are never filled with the previous day's sentiment.
- **Why:** carrying sentiment forward would invent news; dropping weekends would lose stories.
- **Approval:** approved by Professor Hamid (reply in section 2.1, received by 2026-11-06).

### B5. Field tiers
- **Proposal:** core = `NEWS_SENTIMENT_DAILY_AVG`, `NEWS_PUBLICATION_COUNT`, the five market fields, static identifiers and the universe. Optional = tone counts, the two NEWS_HEAT fields (an optional extension in the brief) and earnings announcements. Optional sheets are pulled only if no data-limit warning appears.
- **Approval:** approved by Professor Hamid (reply in section 2.1, received by 2026-11-06).

### B6. Static classifications are current snapshots
- **Proposal:** GICS, ticker and status from `BDP` are today's values and are not used to infer past values (guide). FIGI (`ID_BB_GLOBAL`) is the stable join key.
- **Approval:** approved by Professor Hamid (reply in section 2.1, received by 2026-11-06).

## 6. Implementation record: the 2026-11-06 terminal pull

Pulled on the RiskLab terminal (S/N 726910-173) on 2026-11-06 with `bloomberg_pull/P2_Bloomberg_Pull.xlsx`; copied unchanged
to `data/raw_bloomberg/20261106/` on 2026-11-08 (every SHA-256 matches the hashes recorded on the terminal). Source log:
`manifests/bloomberg_source_log.csv`. What differs from the plan in section 5, and why:

- **Index weights not entitled.** `INDX_MWEIGHT_HIST` returned membership but the weight column came back as Bloomberg's
  missing-number placeholder (-2.42E-14). Membership is all the design needs (B2); weights are not used.
- **Supplement pull.** `COMPOSITE_ID_BB_GLOBAL` (company-level FIGI), BICS sector/group/subgroup and composite (consolidated)
  volume were added in `P2_Bloomberg_Supplement_20261106.xlsx`, because `PX_VOLUME` on UN/UW tickers is one exchange only
  (median 31% of consolidated) and GICS is blank for 60 acquired or delisted names.
- **Units and anchors recorded from FLDS.** `CUR_MKT_CAP` from BDH is in USD millions (BDP gives full USD).
  `TOT_RETURN_INDEX_GROSS_DVDS` is anchored to the request start date, so only ratios are used (B3).
- **Universe size.** 73 snapshots, 503-506 members each, 635 exchange tickers = 617 companies (18 on two exchanges).
- **Field IDs mapped.** NW020 = `NEWS_SENTIMENT_DAILY_AVG`; RK074 = `HIST_CALL_IMP_VOL` (call implied volatility, not a
  sentiment field) in RiskLab's `Daily_Average_Sentiment_Score.csv`.
- **Pilot.** All seven terminal comparisons on Pilot_Checks passed (HP/GP vs workbook), including the AAPL 4-for-1 split.
  Check 3 (unadjusted close) was derived from HP's adjusted close x 4 because the HP settings dialog could not be operated
  remotely.

### 6.1 Timing facts (FLDS, 2026-11-06) and empirical checks (2026-11-08)

- `NEWS_SENTIMENT_DAILY_AVG` (NW020) and the story counts (NW043-NW046) dated D are published 10 minutes before the US open on
  D and cover the previous 24 hours. A value dated D is known at about 09:20 New York time on D. Range [-1, 1].
- No values are dated Saturday or Sunday. **Values do exist on weekday market holidays** (39,842 security-days), contrary to
  the pull notes ("values on trading days only"). `outputs/diagnostics/02_raw_validation_summary.txt`.
- **Weekend gap (empirical).** Monday's value carries about a third of the scored stories of a Tuesday-Thursday value
  (4.8 vs 14.5 per security-day; holidays 6.0). This fits the FLDS 24-hour window: Monday's value covers mostly Sunday, so
  stories published from Friday 09:20 to Sunday 09:20 fall in no daily value (O6). Not confirmed with Bloomberg; treated as a
  documented assumption.
- `NEWS_HEAT_*` fields update at local midnight (a different clock); they are not used for timing.
- Zeros are real readings: 212,063 of 241,488 zero sentiment values have scored stories with positive = negative; a missing
  value means no scored stories (181,360 such rows). Neither is filled.

## 7. Proposals for checkpoint 1 (PROPOSED 2026-11-08; none chosen by results)

Implemented in `src/03`-`src/05` so the checkpoint numbers can be produced; each can be changed before estimation.

### P1. Information timing of the vendor value
- **Proposal:** the value dated D is usable from the open of D. A value dated on a holiday is first usable at the next trading
  day's open; it is counted (`n_holiday_values_before`) but not merged into that day's value. No value is carried forward.
- **Outcome candidates that respect this timing:** `ret_oc_d0` (open D to close D) and `ret_cc_d1` (close D to close D+1).
  `ret_cc_d0` (close D-1 to close D) starts before the value is known; it is kept only for timing diagnostics.
- **Choice of primary horizon:** with E2, by the supervisor.

### P2. Return construction
- `ret_cc` = TRI_t / TRI_{t-1} - 1 when t-1 is the previous NYSE day; `ret_oc` = PX_LAST_t / PX_OPEN_t - 1 (split-adjusted,
  so the adjustment cancels); `ret_co` = (1 + ret_cc) / (1 + ret_oc) - 1 (dividends fall here).
- One return in 972,599 could not be formed because a trading day is missing in between.

### P3. One ticker per company per day; exchange switches
- **Proposal:** the unit is the exchange ticker that was the member in the snapshot; no snapshot lists a company twice
  (checked). When that ticker has no price on a day but the company's other exchange ticker does (EXPD, FISV and GRMN moved
  exchange mid-month), the other ticker is used for that day: 42 security-days.
- **Alternative:** drop those days (loses 42 security-days for three firms).

### P4. Daily membership rule
- **Proposal:** a security is in the universe on trading day t if it was a member at the latest month-end snapshot strictly
  before t (2019-12-31 for January 2020). This is point-in-time and uses no later information.
- **Known limitation (B2):** a firm added mid-month enters at the next month-end; 497 universe security-days fall after a
  firm's last Bloomberg market row (acquired or delisted during the month) and stay in the attrition table.

### P5. Aligning the 188 headlines (the primary identical-text sample, D1)
- **Conservative cutoff (supervisor, S2):** a headline is assumed known only after the end of its file date; its first tradable
  moment is the open of the first trading day strictly after that date.
- **Which vendor value contains the story:** publication times are unknown, so a weekday story sits in the value dated that day
  (if published before 09:20) or the next weekday (after). For 149 of the 182 headlines with any vendor value, both candidate
  values exist. Proposed rule, to freeze before scoring: compare against the value dated the next weekday (the later value
  must contain a story published on day d after 09:20, and the conservative cutoff already assumes after-hours), and report
  the same-day value as a sensitivity.
- **Alternative:** average the two candidate values; or drop the 149 ambiguous headlines (leaves 33).

### P6. Headline-file exclusions
- **Proposal:** keep every headline but flag: 2 Tesla headlines dated before Tesla joined the index (excluded from the member
  sample by P4), 3 headlines whose URL date differs from the file date by more than 3 days (GS 2023-01-10 vs 2023-01-27,
  KO 2020-08-28 vs 2020-12-17, TSLA 2024-03-31 vs 2024-05-31) and 1 with no URL (TSLA 2025-04-17). Results are reported with
  and without the flagged rows (guide: quantify, flag, sensitivity; never delete silently).

## 8. Open issues (for the first checkpoint)

- **O1 Identical text (critical).** RiskLab holds no larger Bloomberg headline archive (supervisor, 2.1), and the Bloomberg
  Help export question is not being pursued (D1), so the primary sample is the 188-headline subset. Facts about it: 188 headlines, 19 large-cap firms, 2020-01-15 to 2025-10-29, 95 source domains, none from
  bloomberg.com, dates only (no times). They cover 0.025% of member security-days (0.66% of the 19 firms' security-days).
  Whether Bloomberg's daily value actually scored these stories cannot be verified without story identifiers.
- **O2 Day boundary.** Resolved by FLDS (6.1): the 24 hours to 09:20 New York on D. The weekend consequence is O6.
- **O3 Ticker changes and delistings.** Resolved for the panel: composite FIGI links the 18 two-exchange companies, three
  mid-month exchange switches are handled by P3, and BICS replaces GICS for the 60 names with no current GICS.
- **O4 Role of the RiskLab vendor files.** Resolved (cross-checks only). Not yet copied into `data/raw_risklab/`: the three
  files are on Professor Hamid's Google Drive and too large to move through the connector (2.9 MB, 3.8 MB, 95 MB).
- **O5 Terminal download limit.** Resolved: the pull was completed on a terminal without the limit (S/N 726910-173).
- **O6 Weekend gap.** Stories from Friday 09:20 to Sunday 09:20 appear to fall in no daily value (6.1). This affects 27
  Friday and 3 Saturday headlines in the primary sample and the meaning of Monday's value. Not confirmed with Bloomberg; treated
  as a documented assumption.
- **O7 Vendor regime change around 2022.** The share of exact zeros falls from 41-47% (2020-21) to 11-16% (2022-24), the
  standard deviation peaks at 0.48 in 2022, and the median story count falls from about 33 to 18. Whether Bloomberg changed
  its model or its source set is unknown; it makes full-sample normalisation unsafe and supports training-window rescaling
  (guide hint 3).
- **O8 Coverage rises with size.** 75% of smallest-quintile security-days have a vendor value vs 95% of the largest. Any
  comparison of the vendor and reproducible scores must be on identical observations (guide hint 4).
- **O9 Headline-file quality and selection.** The 188 headlines look hand-collected and ESG-themed, from mixed public sources
  (Reuters 32, CNBC 11, Guardian 7, ESG Today 7, ...), with the date problems in P6. The selection rule behind the file is
  not documented.
