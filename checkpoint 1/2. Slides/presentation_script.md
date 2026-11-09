# Checkpoint 1 Presentation Script

Neill Liran Botushanski · MMF 1941 · Project 2 (A16-02) · 2026-11-08

## How to use this script

The talk runs about 12 minutes for slides 1 to 13, leaving time for questions; slide 14 is shown only if asked. Every number below matches the deck (`checkpoint_1_progress_update.pptx`).

| Slide | Title | Time | Elapsed |
| --- | --- | --- | --- |
| 1 | Title | 0:30 | 0:30 |
| 2 | Project introduction | 1:00 | 1:30 |
| 3 | Research design | 1:00 | 2:30 |
| 4 | Data requirements | 0:45 | 3:15 |
| 5 | Local data (RiskLab) | 1:00 | 4:15 |
| 6 | Bloomberg pull | 0:45 | 5:00 |
| 7 | Data acquisition | 0:45 | 5:45 |
| 8 | Coverage diagnostics | 1:00 | 6:45 |
| 9 | Timing diagnostics | 1:15 | 8:00 |
| 10 | The vendor score | 1:00 | 9:00 |
| 11 | Data preparation | 1:00 | 10:00 |
| 12 | Code and reproducibility | 0:45 | 10:45 |
| 13 | Decisions and next steps | 1:15 | 12:00 |
| 14 | Data lineage appendix | if asked | |

- Round big numbers when speaking ("about 760,000"); the exact figures are on the slides.
- Slide 9 is the key finding: slow down there and point at the Monday bar.
- Slide 13 is where Professor Hamid decides things: leave the questions on screen and stop talking.

## Slides 1 to 3: the question and the design

### Slide 1 · Title (0:30)

Good morning. I'm Neill Botushanski, and this is my first checkpoint for Project 2: Is the vendor's secret sauce priced?

The project compares Bloomberg's own news-sentiment score with a score anyone can reproduce, built from the same headlines. Today covers the data and the exploratory analysis only. As the guide asks for this checkpoint, there is no hypothesis test yet.

### Slide 2 · Project introduction (1:00)

Bloomberg sells a daily news-sentiment score for every company. It's a black box: we can't see how it's built.

I can build my own score from the same headlines with an open method, a finance word list or a model like FinBERT. Subtract my score from Bloomberg's, and the gap, V minus R, is whatever Bloomberg adds on top.

The test is whether that gap predicts the next return. My hypothesis is that it mostly doesn't: the gap is noise. If a free, auditable score does as well, the secret sauce isn't priced.

The diagram on the right is the whole project: the same headline, two scores, the gap, and whether it predicts returns.

### Slide 3 · Research design (1:00)

Formally, I regress the return on my score, R, and on the gap, V minus R, with controls. The coefficient that matters is gamma, on the gap. The null is gamma equals zero: no black-box premium.

Standard errors are HAC and clustered, and encompassing and Diebold-Mariano tests check whether the vendor score adds forecasting power. As robustness, a purged cross-validation model compares features with and without the vendor score, judged on the deflated Sharpe ratio.

The table summarises the setup: security-days, point-in-time S&P 500 members, 2020 to 2025, with a buffer either side. Two choices are still open, the horizon and the scoring rule. I'll come back to them at the end.

## Slides 4 to 7: the data

### Slide 4 · Data requirements (0:45)

The study needs seven data components. Six come from Bloomberg: the vendor score itself, the story counts, returns, index membership, identifiers and controls, and earnings dates with index series. The seventh, the headline text, comes from RiskLab.

All seven are now in hand. The only thing outstanding is three RiskLab files I'll use to cross-check the Bloomberg pull, and they don't hold anything up. As the brief requires, nothing intraday came from Bloomberg.

### Slide 5 · Local data, RiskLab (1:00)

RiskLab's headline file has 188 headlines on 19 large-cap firms, from 95 different public sources: Reuters, CNBC, the Guardian and so on. None of them is from Bloomberg, and they have dates but no publication times. They look hand-collected and mostly about ESG.

Three have a date that doesn't match the date in their link, and one has no link at all. I've flagged those rather than deleted them, and I'll report results with and without them.

You confirmed RiskLab has no larger Bloomberg headline archive. So I've made these 188 headlines the primary identical-text sample, with the conservative return cutoff you asked for. That's decision D1, and I'd like to confirm it with you today.

### Slide 6 · Bloomberg pull (0:45)

I pulled the Bloomberg data on the RiskLab terminal on November 6th. It covers 635 exchange tickers, which is 617 companies, because some trade on two exchanges, across 73 month-end membership snapshots. That's about 978,000 security-days of prices and returns, and just over a million of news fields.

Before the full pull I ran a pilot. All seven checks matched the terminal screens, including Apple's four-for-one split, and 26 fields were confirmed in FLDS.

One FLDS fact matters a lot: the sentiment value dated D covers the 24 hours to 9:20 New York time on D. So it is known before that day's open.

### Slide 7 · Data acquisition (0:45)

This slide is the audit trail. A script built the Bloomberg workbook; I checked the fields, ran the pilot, and pulled the data. Then I copied it over and checked every file's hash against the ones recorded on the terminal: 11 out of 11 matched.

The workbook was exported to tidy files with a source log, and the data then went through 76 validation checks. Raw files are never edited, and every derived file lives in its own folder.

## Slides 8 to 10: what the data shows

### Slide 8 · Coverage diagnostics (1:00)

Now the exploratory results. 82 percent of member security-days have a Bloomberg sentiment value.

The left chart shows it by month. Coverage sits in the low seventies in 2020 and 2021, then jumps above 85 percent from late 2021. The orange line is the 19 firms in the headline file: they're large caps and covered almost every day.

The right chart shows coverage rising with firm size, from 75 percent in the smallest fifth to 95 percent in the largest. So the two scores must be compared on exactly the same observations, or differences in coverage would contaminate the comparison.

### Slide 9 · Timing diagnostics (1:15)

This is the most important data-quality finding.

The left chart counts the scored stories behind the value dated each weekday. Tuesday to Friday, it's about 13 to 15 per company-day. Monday is 4.8, and holidays are 6.

That fits a 24-hour window. Monday's value only covers Sunday morning to Monday morning. So stories published between Friday 9:20 and Sunday 9:20 appear in no daily value at all.

The right chart shows what that means for the headlines. They have dates but no times, so a weekday headline could sit in that day's value, if published before 9:20, or in the next day's. For 149 of the 182 headlines with a vendor value, both candidates exist, so the matching is ambiguous. The few weekend headlines fall into no value. My proposed rule for this is P5, which I'll come back to.

### Slide 10 · The vendor score (1:00)

The score itself changes over time. In 2020, nearly half of all values are exactly zero; from 2022 it's 11 to 16 percent. Over the same period, stories per company-day fall from about 89 to about 48.

I don't know whether Bloomberg changed its model or its sources. Either way, the score must be rescaled inside each training window, not over the full sample, or the change would leak into the test.

Two more facts. Most zeros are genuine neutral readings, not missing data. And a simple ratio of positive minus negative stories already correlates 0.81 with the vendor score: useful context for the black-box question, though not a test of it.

## Slides 11 to 14: the sample, the code and the decisions

### Slide 11 · Data preparation (1:00)

This table follows the sample down from the full universe. The point-in-time universe is about 760,000 security-days, and almost all of them have prices and returns. About 623,000 have a vendor sentiment value, and 622,570 also have a next-day return: that's the broad sample.

The orange rows are the headline sample. Of 188 headlines, 186 are from firms in the index that day, 182 have a vendor value on a candidate date, and 149 of those are ambiguous.

On the right: 76 validation checks, with four flags, all explained; no duplicate keys or many-to-many joins. The 499 days with no price are firms acquired or delisted during the month, plus two not yet listed.

### Slide 12 · Code and reproducibility (0:45)

Everything is scripted. Each module reads declared inputs and writes declared outputs, and one command, run_all, rebuilds every table, figure, the report and this deck from the raw files. A full rebuild reproduced every output byte for byte.

I also hand-checked ten random observations, tracing each value from the raw Bloomberg cell to the final panel and recomputing the returns by hand. All ten match, on top of the seven terminal checks from the pilot.

### Slide 13 · Decisions and next steps (1:15)

To finish, six questions for you. None of them should be decided by looking at results.

1. D1: are you happy with the 188 headlines as the primary sample, without a Bloomberg export?
2. P5: for each headline, should I compare with the next-weekday vendor value, the same-day value, or their average?
3. The primary horizon: open-to-close on the value date, or next-day close-to-close?
4. The primary scoring rule: Loughran-McDonald or FinBERT, with the other as robustness?
5. Should Friday and Saturday headlines stay in, given the weekend gap?
6. Can I start the secondary exercise on the broad panel now?

For the next checkpoint, I'll freeze the design, build both reproducible scores on the 186 member headlines, and run the primary test. Thank you; I'm happy to take questions.

### Slide 14 · Data lineage appendix (only if asked)

This lists every data source and its status. Nine are available and validated. The three RiskLab cross-check files are still to be copied from the RiskLab drive.

## Likely questions

| Question | Answer |
| --- | --- |
| Why not export Bloomberg's own headlines? | I chose not to pursue the export (D1) and use the 188-headline fallback you approved. An export can be added later without changing the pipeline. |
| Aren't 186 headlines too few to find anything? | Yes, the power is low. A null result will be reported as "no evidence at this sample size", with confidence intervals, not as proof of no premium. |
| How do you know Bloomberg scored these exact stories? | I can't verify it without Bloomberg story IDs; it's limitation 1 in the pack. I'll state it plainly and report the timing ambiguity (P5) as a sensitivity. |
| Why is the return cutoff conservative? | The headlines have no times, so I assume each is known only after the end of its date and trade from the next open. |
| Why month-end membership rather than daily? | It's point-in-time and takes 73 requests instead of about 1,500. Firms added mid-month enter at the next month-end, and the 497 days after a delisting are recorded in the attrition table. |
| Can the broad panel answer the question instead? | No. It tests whether the vendor score predicts returns, but without identical text it can't separate Bloomberg's model from its choice of stories. It runs as the secondary exercise only. |
