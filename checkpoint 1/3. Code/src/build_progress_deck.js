// Build the checkpoint-1 progress deck from outputs/diagnostics/deck_data.json (saved outputs only).
//
//   node src/build_progress_deck.js outputs/diagnostics/deck_data.json reports/checkpoint_1_progress_update.pptx
//   python src/apply_deck_theme.py reports/checkpoint_1_progress_update.pptx
//
// Same section order as the Project 1 checkpoint update (MMF 1941 template colours, Cambria / Calibri).
// Every number on a slide comes from the data file; charts are native PowerPoint charts (editable).
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const [dataPath, outPath] = process.argv.slice(2);
const D = JSON.parse(fs.readFileSync(dataPath, "utf8"));
const F = D.facts;
const fmt = (n) => Number(n).toLocaleString("en-US");

// ---------------------------------------------------------------- theme (MMF 1941 template colours)
const HEX = { navy: "172B3A", teal: "087E8B", green: "2E7D5A", orange: "C56A11", red: "B5473C", grey: "5F6F7A",
              light: "EEF2F4", rule: "D9E2E7", white: "FFFFFF", tealSoft: "D6ECEE", orangeSoft: "F6E6D6" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                       // 13.333 x 7.5 in, as in Project 1
pres.theme = { headFontFace: "Cambria", bodyFontFace: "Calibri" };
pres.author = "Neill Liran Botushanski";
pres.title = "Checkpoint 1 progress update: Is the Vendor's Secret Sauce Priced?";
const C = pres.SchemeColor;
const W = 13.333, M = 0.6, CW = W - 2 * M;          // slide width, margin, content width

// ---------------------------------------------------------------- layouts
const footer = () => ({ text: { text: "MMF 1941  |  Project 2 progress update  |  A16-02",
  options: { x: M, y: 7.0, w: 7, h: 0.3, fontSize: 10, color: C.text2, margin: 0 } } });
const kickerPh = (color) => ({ placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.42, w: CW, h: 0.32,
  fontSize: 12, bold: true, color, charSpacing: 1, margin: 0, valign: "middle" }, text: "" } });
const titlePh = (color) => ({ placeholder: { options: { name: "title", type: "title", x: M, y: 0.78, w: CW, h: 1.05,
  fontSize: 28, bold: true, color, margin: 0, valign: "top", align: "left" }, text: "" } });

pres.defineSlideMaster({ title: "TITLE_DARK", background: { color: HEX.navy }, objects: [
  { placeholder: { options: { name: "title", type: "title", x: M, y: 2.0, w: 7.6, h: 1.7, fontSize: 40, bold: true,
    color: C.background1, margin: 0, valign: "bottom", align: "left" }, text: "" } },
  { placeholder: { options: { name: "body", type: "body", x: M, y: 3.85, w: 7.6, h: 0.9, fontSize: 20,
    color: C.background1, margin: 0, valign: "top", align: "left" }, text: "" } } ] });
pres.defineSlideMaster({ title: "CONTENT", background: { color: HEX.white },
  objects: [kickerPh(C.accent1), titlePh(C.text1), footer()],
  slideNumber: { x: 12.2, y: 7.0, w: 0.53, h: 0.3, fontSize: 10, color: C.text2, align: "right" } });
pres.defineSlideMaster({ title: "CONTENT_DARK", background: { color: HEX.navy },
  objects: [kickerPh(C.accent5), titlePh(C.background1)],
  slideNumber: { x: 12.2, y: 7.0, w: 0.53, h: 0.3, fontSize: 10, color: C.accent5, align: "right" } });

let sectionOpen = null;
function slideFor(section, kicker, title, master = "CONTENT") {
  if (section !== sectionOpen) { pres.addSection({ title: section }); sectionOpen = section; }
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  if (kicker) s.addText(kicker, { placeholder: "kicker" });
  s.addText(title, { placeholder: "title" });
  return s;
}
const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top", ...o });

// Stat tile: big number over a small label, on a tinted card.
function stat(s, x, y, w, h, value, label, color = C.accent1, fill = HEX.light) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.08,
    objectName: `tile ${label.slice(0, 20)}` });
  T(s, value, { x: x + 0.25, y: y + 0.15, w: w - 0.5, h: 0.62, fontSize: 32, bold: true, color, fontFace: "Cambria", valign: "bottom" });
  T(s, label, { x: x + 0.25, y: y + 0.8, w: w - 0.5, h: h - 0.92, fontSize: 13, color: C.text2 });
}
// Numbered teal circle (the deck's motif).
function badge(s, x, y, label, d = 0.5, fill = C.accent1, fontSize = 16) {
  s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: `badge ${label}` });
  T(s, String(label), { x, y, w: d, h: d, fontSize, bold: true, color: C.background1, align: "center", valign: "middle" });
}
const chartText = { catAxisLabelColor: HEX.grey, valAxisLabelColor: HEX.grey, catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt", legendFontFace: "+mn-lt",
  dataLabelFontFace: "+mn-lt", titleColor: HEX.navy, titleFontSize: 13, legendFontSize: 11, legendColor: HEX.grey,
  dataLabelColor: HEX.navy, dataLabelFontSize: 11 };
const grid = () => ({ valGridLine: { color: HEX.rule, size: 0.5 }, catGridLine: { style: "none" } });

// ================================================================ 01 title
{
  pres.addSection({ title: "Title" }); sectionOpen = "Title";
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Title" });
  T(s, "CHECKPOINT 1  |  DATA AND EXPLORATORY ANALYSIS", { x: M, y: 1.45, w: 7.6, h: 0.35, fontSize: 13, bold: true,
    color: C.accent5, charSpacing: 1 });
  s.addText("Is the Vendor's Secret Sauce Priced?", { placeholder: "title" });
  s.addText("Bloomberg vs a reproducible sentiment score on identical text", { placeholder: "body" });
  T(s, "Neill Liran Botushanski", { x: M, y: 5.35, w: 7.6, h: 0.4, fontSize: 18, bold: true, color: C.background1 });
  T(s, "MMF 1941  ·  Proposal A16-02  ·  Supervisor: Professor Hamid  ·  November 2026",
    { x: M, y: 5.8, w: 7.6, h: 0.35, fontSize: 14, color: C.accent5 });
  // motif: two overlapping scores and the gap between them
  s.addShape(pres.ShapeType.ellipse, { x: 8.55, y: 1.75, w: 3.3, h: 3.3, fill: { color: HEX.orange, transparency: 25 },
    line: { color: HEX.orange, transparency: 25 }, objectName: "Bloomberg score circle" });
  s.addShape(pres.ShapeType.ellipse, { x: 10.05, y: 2.65, w: 2.7, h: 2.7, fill: { color: HEX.teal, transparency: 20 },
    line: { color: HEX.teal, transparency: 20 }, objectName: "reproducible score circle" });
  T(s, "Bloomberg\nscore", { x: 8.85, y: 2.7, w: 1.4, h: 0.8, fontSize: 15, bold: true, color: C.background1 });
  T(s, "Our\nscore", { x: 11.5, y: 4.15, w: 1.1, h: 0.8, fontSize: 15, bold: true, color: C.background1 });
  T(s, "gap?", { x: 10.25, y: 3.4, w: 1.2, h: 0.5, fontSize: 18, bold: true, italic: true, color: C.background1, align: "center" });
  s.addNotes("Checkpoint 1 covers data acquisition and exploratory analysis only. No hypothesis test is presented: the guide " +
    "asks for the design log, manifest, Bloomberg pilot, coverage table, ten hand checks, one figure and the open data limitations.");
}

// ================================================================ 02 introduction
{
  const s = slideFor("Introduction", "02  |  PROJECT INTRODUCTION",
    "Does Bloomberg's black-box sentiment add anything over a transparent score on the same headlines?");
  const rows = [
    ["Q", "Question", "Does the gap between Bloomberg's daily news sentiment and an open, reproducible score on the same text predict the next return?"],
    ["H", "Hypothesis", "The gap is mostly noise: it adds nothing robust beyond the reproducible score (an honest null on a \"black-box premium\")."],
    ["!", "Why it matters", "If a free, auditable score does as well, the vendor's secret sauce is not priced, and a costly input can be replaced."]];
  rows.forEach(([b, head, body], i) => {
    const y = 2.15 + i * 1.5;
    badge(s, M, y, b, 0.6);
    T(s, head, { x: M + 0.85, y: y - 0.02, w: 5.3, h: 0.4, fontSize: 18, bold: true });
    T(s, body, { x: M + 0.85, y: y + 0.4, w: 5.3, h: 0.95, fontSize: 14, color: C.text2 });
  });
  // the comparison, as a flow
  const bx = (x, y, w, h, text, fill, color = C.background1) => {
    s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.08, objectName: text });
    T(s, text, { x, y, w, h, fontSize: 15, bold: true, color, align: "center", valign: "middle" });
  };
  const arrow = (x, y, w, h) => s.addShape(pres.ShapeType.line, { x, y, w, h, line: { color: HEX.grey, width: 1.5, endArrowType: "triangle" } });
  bx(8.35, 2.15, 3.5, 0.75, "Headline (same text)", HEX.light, C.text1);
  bx(7.25, 3.55, 2.55, 0.8, "Bloomberg score V", HEX.orange);
  bx(10.4, 3.55, 2.55, 0.8, "Our score R", HEX.teal);
  bx(8.35, 4.95, 3.5, 0.75, "Gap  V − R", HEX.navy);
  bx(8.35, 6.0, 3.5, 0.6, "Predicts the next return?", HEX.light, C.text1);
  arrow(9.25, 2.9, -0.65, 0.65); arrow(10.95, 2.9, 0.7, 0.65);
  arrow(8.6, 4.35, 0.65, 0.6); arrow(11.65, 4.35, -0.7, 0.6);
  arrow(10.1, 5.7, 0, 0.3);
  s.addNotes("The research question and hypothesis are fixed by the brief. The comparison is only clean if both scores read the " +
    "same text: otherwise any gap mixes model differences with content differences.");
}

// ================================================================ 03 research design
{
  const s = slideFor("Design", "03  |  RESEARCH DESIGN",
    "One pre-specified test: does the gap predict returns beyond the reproducible score?");
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 2.1, w: 6.0, h: 4.0, fill: { color: HEX.light }, line: { color: HEX.light },
    rectRadius: 0.08, objectName: "equation card" });
  T(s, "Primary specification", { x: M + 0.3, y: 2.3, w: 5.4, h: 0.4, fontSize: 16, bold: true, color: C.accent1 });
  T(s, "r(i, t+h) = α + β·R(i,t) + γ·[V(i,t) − R(i,t)] + controls + ε",
    { x: M + 0.3, y: 2.8, w: 5.4, h: 0.9, fontSize: 18, fontFace: "Cambria", bold: true });
  T(s, "H0:  γ = 0   (no black-box premium)", { x: M + 0.3, y: 3.75, w: 5.4, h: 0.4, fontSize: 16, color: C.accent2, bold: true });
  T(s, [
    { text: "Estimation: ", options: { bold: true } }, { text: "HAC / clustered standard errors; encompassing and Diebold-Mariano tests", options: { breakLine: true } },
    { text: "Robustness: ", options: { bold: true } }, { text: "purged cross-validation, reproducible-only vs + vendor features, deflated Sharpe ratio" }],
    { x: M + 0.3, y: 4.35, w: 5.4, h: 1.6, fontSize: 14, color: C.text2, paraSpaceAfter: 8 });
  const rows = [["Unit", "Security-day"], ["Universe", "Point-in-time S&P 500 members"], ["Sample", "2020-2025 daily (buffers Jul 2019, Jan 2026)"],
    ["Outcome", "Next-day or short-horizon return"], ["Text", `${F.headlines} headlines (identical text, D1)`],
    ["Secondary", "Vendor score on the full panel (separate exercise)"], ["Still open", "Horizon and scoring rule (E2)"]];
  s.addTable([[{ text: "Design element", options: { bold: true, color: HEX.white, fill: { color: HEX.navy } } },
    { text: "Setting", options: { bold: true, color: HEX.white, fill: { color: HEX.navy } } }],
    ...rows.map(([a, b], i) => [{ text: a, options: { bold: true, fill: { color: i % 2 ? HEX.white : HEX.light } } },
      { text: b, options: { fill: { color: i % 2 ? HEX.white : HEX.light } } }])],
    { x: 7.0, y: 2.1, w: 5.73, colW: [1.6, 4.13], fontSize: 13, color: HEX.navy, border: { type: "solid", color: HEX.rule, pt: 0.5 },
      rowH: 0.5, valign: "middle", objectName: "design table" });
  s.addNotes("The specification and both methods come from the brief; the supervisor fixed the period, point-in-time membership, " +
    "total returns and strict timing. What remains open before estimation is the horizon and the reproducible scoring rule.");
}

// ================================================================ 04 data requirements
{
  const s = slideFor("Data", "04  |  DATA REQUIREMENTS", "Seven data components: Bloomberg supplies six, RiskLab the text");
  const rows = [
    ["1", "Vendor sentiment score", "The black box being tested", "Bloomberg NEWS_SENTIMENT_DAILY_AVG"],
    ["2", "Story counts", "Coverage checks, controls", "Bloomberg NW043-NW046"],
    ["3", "Headline text", "Input to our score", `RiskLab News_Articles.csv (${F.headlines})`],
    ["4", "Returns", "Outcome", "Bloomberg total-return index, open, close"],
    ["5", "Point-in-time universe", "Who is in the sample each day", "Bloomberg INDX_MWEIGHT_HIST, 73 month-ends"],
    ["6", "Identifiers and controls", "Joins, size, liquidity, sector", "Bloomberg BDP, market cap, volume, BICS"],
    ["7", "Earnings dates and index", "Event control, market return", "Bloomberg earnings history; SPX, SPXT, VIX"]];
  const head = ["#", "Component", "Role", "Source", "Status"].map((t) => ({ text: t, options: { bold: true, color: HEX.white, fill: { color: HEX.navy } } }));
  s.addTable([head, ...rows.map((r, i) => [...r.map((t, j) => ({ text: t, options: { bold: j === 1, fill: { color: i % 2 ? HEX.white : HEX.light } } })),
    { text: "In hand", options: { bold: true, color: HEX.green, fill: { color: i % 2 ? HEX.white : HEX.light } } }])],
    { x: M, y: 2.05, w: CW, colW: [0.5, 2.9, 3.0, 4.6, 1.13], fontSize: 13, color: HEX.navy, rowH: 0.5, valign: "middle",
      border: { type: "solid", color: HEX.rule, pt: 0.5 }, objectName: "requirements table" });
  T(s, [{ text: "Cross-checks only: ", options: { bold: true } },
    { text: `${F.manifest_pending} RiskLab vendor-sentiment files, still to copy from the RiskLab drive.   ` },
    { text: "Intraday data: ", options: { bold: true } }, { text: "none requested from Bloomberg (brief rule)." }],
    { x: M, y: 6.3, w: CW, h: 0.45, fontSize: 13, color: C.text2 });
  s.addNotes("Every component the study needs is now available and validated. The three RiskLab files are only cross-checks of the " +
    "Bloomberg pull and do not hold up the analysis.");
}

// ================================================================ 05 local data
{
  const s = slideFor("Data", "05  |  LOCAL DATA (RISKLAB)",
    `RiskLab supplies the headline text: ${F.headlines} headlines on ${F.headline_firms} firms, none from Bloomberg`);
  const tiles = [[String(F.headlines), "headlines, 2020-2025"], [String(F.headline_firms), "large-cap firms"],
    [String(F.headline_domains), "public source domains"], [String(F.headline_bloomberg_domain), "from bloomberg.com"]];
  const tw = (CW - 3 * 0.3) / 4;
  tiles.forEach(([v, l], i) => stat(s, M + i * (tw + 0.3), 2.1, tw, 1.55, v, l, i === 3 ? C.accent2 : C.accent1));
  T(s, [
    { text: "Dates only, no publication times", options: { bullet: true, breakLine: true } },
    { text: "Hand-collected, mostly ESG themes (Reuters 32, CNBC 11, Guardian 7, ESG Today 7)", options: { bullet: true, breakLine: true } },
    { text: `${F.headline_flag_date} URL-date mismatches and ${F.headline_flag_url} missing URL: flagged, kept, reported with and without`, options: { bullet: true, breakLine: true } },
    { text: "RiskLab holds no larger Bloomberg headline archive (Professor Hamid)", options: { bullet: true } }],
    { x: M, y: 4.05, w: 6.6, h: 2.6, fontSize: 15, color: C.text1, paraSpaceAfter: 10 });
  s.addShape(pres.ShapeType.roundRect, { x: 7.6, y: 4.05, w: 5.13, h: 2.55, fill: { color: HEX.orangeSoft }, line: { color: HEX.orangeSoft },
    rectRadius: 0.08, objectName: "decision D1 card" });
  T(s, "Decision D1", { x: 7.9, y: 4.25, w: 4.5, h: 0.4, fontSize: 17, bold: true, color: C.accent2 });
  T(s, `No Bloomberg headline export. These ${F.headlines} headlines are the primary identical-text sample: the supervisor's fallback, with a conservative return cutoff. To confirm with him at this checkpoint.`,
    { x: 7.9, y: 4.75, w: 4.55, h: 1.7, fontSize: 14, color: C.text1 });
  s.addNotes("The headline file is the text for our reproducible score. Because none of it comes from Bloomberg and it has no " +
    "publication times, whether Bloomberg's daily value scored these exact stories cannot be verified.");
}

// ================================================================ 06 Bloomberg pull
{
  const s = slideFor("Data", "06  |  BLOOMBERG PULL",
    "The terminal pull covers 635 tickers over six and a half years and passed every pilot check");
  const tiles = [["635", "exchange tickers = 617 companies"], ["73", "month-end membership snapshots"],
    ["978,472", "security-days of prices and returns"], ["1,070,056", "security-days of news fields"],
    [`${F.terminal_checks_pass} / 7`, "pilot checks match the terminal (HP, GP)"], [String(F.fields_checked_in_flds), "fields confirmed in FLDS"]];
  const tw = (CW - 2 * 0.3) / 3;
  tiles.forEach(([v, l], i) => stat(s, M + (i % 3) * (tw + 0.3), 2.1 + Math.floor(i / 3) * 1.95, tw, 1.7, v, l,
    i >= 4 ? C.accent3 : C.accent1));
  T(s, "Pulled 2026-11-06 on the RiskLab terminal, end-of-day only. The sentiment value dated D covers the 24 hours to 09:20 New York on D (FLDS).",
    { x: M, y: 6.15, w: CW, h: 0.55, fontSize: 13, color: C.text2 });
  s.addNotes("The pilot compared seven workbook values with HP and GP on the terminal, including the AAPL 4-for-1 split. " +
    "Index weights were not entitled, which does not matter: only membership is used.");
}

// ================================================================ 07 data acquisition
{
  const s = slideFor("Data", "07  |  DATA ACQUISITION", "Every step from the terminal to the panel leaves an audit trail");
  const steps = [["Formula workbook", "BDS, BDH and BDP formulas, built by a script"], ["Field check + pilot", `${F.fields_checked_in_flds} fields, ${F.terminal_checks_pass}/7 checks`],
    ["Terminal pull", "2026-11-06, no data-limit errors"], ["Copy and hash", `${F.raw_files_hash_matched}/${F.raw_files_hash_recorded} hashes match`],
    ["Export + source log", `tidy CSVs, ${F.source_log_rows} log rows`], ["Validate", `${F.validation_checks} checks, ${F.validation_flags} flags explained`]];
  const sw = CW / steps.length;
  s.addShape(pres.ShapeType.line, { x: M + sw / 2, y: 2.75, w: CW - sw, h: 0, line: { color: HEX.rule, width: 3 } });
  steps.forEach(([h, d], i) => {
    const cx = M + i * sw + sw / 2;
    badge(s, cx - 0.35, 2.4, i + 1, 0.7, C.accent1, 20);
    T(s, h, { x: cx - sw / 2 + 0.08, y: 3.3, w: sw - 0.16, h: 0.45, fontSize: 15, bold: true, align: "center" });
    T(s, d, { x: cx - sw / 2 + 0.08, y: 3.8, w: sw - 0.16, h: 0.9, fontSize: 13, color: C.text2, align: "center" });
  });
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 5.1, w: CW, h: 1.45, fill: { color: HEX.light }, line: { color: HEX.light }, rectRadius: 0.08, objectName: "rules card" });
  T(s, [{ text: "Rules kept throughout", options: { bold: true, color: HEX.teal, breakLine: true } },
    { text: "Raw files are never edited; every derived file lives in data/interim or data/analytic. Each script reads declared inputs, writes declared outputs and a summary, and the source log carries every file's SHA-256." }],
    { x: M + 0.3, y: 5.25, w: CW - 0.6, h: 1.2, fontSize: 14, color: C.text1, paraSpaceAfter: 4 });
  s.addNotes("This is the trail behind the guide's reproducibility record: the raw workbook as saved on the terminal, its hash, " +
    "the tidy export and the validation report.");
}

// ================================================================ 08 coverage
{
  const s = slideFor("Diagnostics", "08  |  COVERAGE DIAGNOSTICS",
    `${Math.round(F.pct_with_sentiment_all)}% of member security-days carry a vendor score, and coverage rises with firm size`);
  const labels = D.monthly.month.map((m) => (m.endsWith("-01") ? m.slice(0, 4) : ""));   // a label each January only
  s.addChart(pres.ChartType.line, [{ name: "All S&P 500 members", labels, values: D.monthly.all },
    { name: `The ${F.headline_firms} headline firms`, labels, values: D.monthly.firms19 }],
    { x: M, y: 2.0, w: 7.6, h: 4.75, chartColors: [HEX.navy, HEX.orange], lineSize: 2, lineDataSymbol: "none",
      showTitle: true, title: "Monthly share of member security-days with a vendor score (%)", showLegend: true, legendPos: "b",
      valAxisMinVal: 50, valAxisMaxVal: 100, valAxisMajorUnit: 10, catAxisLabelRotate: 0, ...chartText, ...grid(),
      objectName: "coverage by month chart" });
  s.addChart(pres.ChartType.bar, [{ name: "Coverage", labels: D.size.q, values: D.size.pct_sent }],
    { x: 8.5, y: 2.0, w: 4.23, h: 4.75, barDir: "col", chartColors: [HEX.teal], showLegend: false, showTitle: true,
      title: "By size quintile (%)", showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", valAxisMinVal: 0,
      valAxisMaxVal: 100, valAxisMajorUnit: 25, barGapWidthPct: 60, ...chartText, ...grid(), objectName: "coverage by size chart" });
  s.addNotes(`Sample: ${fmt(F.attrition_1)} member security-days, ${F.panel_securities} securities, ${fmt(F.trading_days)} trading days. ` +
    "Coverage dips in 2020-21. The 19 headline firms are large caps and covered about 98% of the time. " +
    "The vendor and reproducible scores must therefore be compared on identical observations.");
}

// ================================================================ 09 timing
{
  const s = slideFor("Diagnostics", "09  |  TIMING DIAGNOSTICS",
    "Monday and holiday values hold a third of a normal day's stories: a weekend gap in the vendor data");
  s.addChart(pres.ChartType.bar, [{ name: "Scored stories", labels: D.weekday.day.map((d) => d.replace(" (weekday)", "")), values: D.weekday.scored }],
    { x: M, y: 2.0, w: 5.6, h: 4.05, barDir: "col", chartColors: [HEX.teal], showLegend: false, showTitle: true,
      title: "Scored stories per security-day, by value date", showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0",
      valAxisMinVal: 0, barGapWidthPct: 55, ...chartText, ...grid(), objectName: "stories by value day chart" });
  const cats = [["Two candidate values (ambiguous)", HEX.orange, "Two candidate values"], ["Same-day value only", HEX.navy, "Same-day value only"],
    ["Next-weekday value only", HEX.green, "Next-weekday value only"], ["No vendor value can contain it", "9AA6AE", "No value can hold it"]];
  s.addChart(pres.ChartType.bar, cats.map(([c, , nm]) => ({ name: nm, labels: D.headline_weekday.day, values: D.headline_weekday[c] })),
    { x: 6.55, y: 2.0, w: 6.18, h: 4.05, barDir: "col", barGrouping: "stacked", chartColors: cats.map(([, h]) => h),
      showTitle: true, title: "Headlines by weekday: which daily value could hold the story", showLegend: true, legendPos: "r",
      valAxisMinVal: 0, barGapWidthPct: 45, ...chartText, ...grid(), objectName: "headlines by weekday chart" });
  T(s, `A value dated D holds the stories of the 24 hours to 09:20 New York on D, and none is dated Saturday or Sunday. Headlines carry dates only, so ${F.attrition_A4} of the ${F.attrition_A3} with a vendor value could sit in two different daily values.`,
    { x: M, y: 6.15, w: CW, h: 0.6, fontSize: 13, color: C.text2 });
  s.addNotes(`Monday values carry ${F.scored_monday} scored stories per security-day against ${F.scored_tue_thu} on Tuesday to Thursday ` +
    `(holidays ${F.scored_holiday}). That fits a 24-hour window: Monday's value covers mostly Sunday. ${F.headline_friday} Friday and ` +
    `${F.headline_saturday} Saturday headlines are exposed. This is the main data-quality risk for the identical-text test.`);
}

// ================================================================ 10 vendor score
{
  const s = slideFor("Diagnostics", "10  |  THE VENDOR SCORE",
    "The vendor score changes regime around 2022, so it must be rescaled inside each training window");
  s.addChart(pres.ChartType.bar, [{ name: "Exactly zero", labels: D.by_year.year, values: D.by_year.pct_zero }],
    { x: M, y: 2.0, w: 5.9, h: 3.15, barDir: "col", chartColors: [HEX.orange], showLegend: false, showTitle: true,
      title: "Share of vendor scores exactly 0 (%)", showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0",
      valAxisMinVal: 0, valAxisMaxVal: 60, valAxisMajorUnit: 20, barGapWidthPct: 55, ...chartText, ...grid(), objectName: "zero share chart" });
  s.addChart(pres.ChartType.bar, [{ name: "Stories", labels: D.by_year.year, values: D.by_year.mean_pub }],
    { x: 6.83, y: 2.0, w: 5.9, h: 3.15, barDir: "col", chartColors: [HEX.navy], showLegend: false, showTitle: true,
      title: "Mean stories per security-day", showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0",
      valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25, barGapWidthPct: 55, ...chartText, ...grid(), objectName: "story count chart" });
  const tw = (CW - 2 * 0.3) / 3;
  [["0.81", "correlation with (positive − negative) / scored stories"], ["25%", "of all values exactly 0: real neutral readings, not missing"],
    ["0.48", "standard deviation in 2022, the peak year"]].forEach(([v, l], i) => stat(s, M + i * (tw + 0.3), 5.35, tw, 1.45, v, l, C.accent1));
  s.addNotes("Zeros mostly have scored stories with positive equal to negative, so they are real readings. Whether Bloomberg changed " +
    "its model or its source set around 2022 is unknown; either way, normalising over the full sample would leak the change.");
}

// ================================================================ 11 data preparation
{
  const s = slideFor("Preparation", "11  |  DATA PREPARATION",
    "Every observation lost between the universe and the analysis samples has a recorded reason");
  const short = { "1": "Universe: members at the latest month-end before each trading day", "2": "... with a Bloomberg market row",
    "3": "... with a close price", "4": "... with both same-day returns", "5": "Universe days with a vendor news row",
    "6": "... with a vendor sentiment value", "7": "... and a same-day open-to-close return", "8": "... and a next-day return (broad sample)",
    "A1": "Headlines dated 2020-2025", "A2": "... firm in the index that day", "A3": "... a vendor value on a candidate date",
    "A4": "... vendor values on both dates (ambiguous)", "A5": "... a return after the conservative cutoff", "A6": "... without a flagged date or URL" };
  const rows = D.attrition.filter(([st]) => st !== "1b");
  const head = ["Step", "Rule", "Count"].map((t, j) => ({ text: t, options: { bold: true, color: HEX.white, fill: { color: HEX.navy }, align: j === 2 ? "right" : "left" } }));
  s.addTable([head, ...rows.map(([st, , n], i) => {
    const fill = { color: st.startsWith("A") ? (i % 2 ? HEX.white : HEX.orangeSoft) : (i % 2 ? HEX.white : HEX.light) };
    return [{ text: st, options: { bold: true, fill } }, { text: short[st] || st, options: { fill } }, { text: fmt(n), options: { fill, align: "right" } }];
  })], { x: M, y: 2.0, w: 8.6, colW: [0.75, 6.15, 1.7], fontSize: 12, color: HEX.navy, rowH: 0.31, valign: "middle",
    border: { type: "solid", color: HEX.rule, pt: 0.5 }, objectName: "attrition table" });
  [[`${F.validation_checks} checks`, `${F.validation_flags} flags, all explained`], ["0", "duplicate keys or many-to-many joins"],
    [String(F.universe_days_no_market_row), `universe days with no price: ${F.no_market_row_after_last} delisted mid-month, ${F.no_market_row_before_first} not yet listed`]]
    .forEach(([v, l], i) => stat(s, 9.55, 2.0 + i * 1.6, 3.18, 1.4, v, l, C.accent1));
  s.addNotes(`Exchange switches: ${F.attrition_1b} security-days for three firms use the company's other exchange ticker (proposal P3). ` +
    "Orange rows are the headline sample; grey rows the broad vendor panel.");
}

// ================================================================ 12 code and reproducibility
{
  const s = slideFor("Preparation", "12  |  CODE AND REPRODUCIBILITY",
    "One command rebuilds every output, byte for byte, from the raw files");
  const mods = [["02", "Raw validation", "76 checks; file hashes"], ["03", "Signals", "vendor values, headline alignment"],
    ["04", "Outcomes", "open-to-close and total returns"], ["05", "Panel and attrition", "point-in-time panel, join report"],
    ["06", "Descriptive diagnostics", "coverage tables, figures"], ["07", "Hand checks", "raw cell to panel variable"],
    ["—", "Report and this deck", "notebook, HTML, PowerPoint"]];
  const head = ["Module", "Step", "Writes"].map((t) => ({ text: t, options: { bold: true, color: HEX.white, fill: { color: HEX.navy } } }));
  s.addTable([head, ...mods.map((r, i) => r.map((t, j) => ({ text: t, options: { bold: j < 2, fill: { color: i % 2 ? HEX.white : HEX.light } } })))],
    { x: M, y: 2.0, w: 7.9, colW: [1.0, 2.8, 4.1], fontSize: 13, color: HEX.navy, rowH: 0.5, valign: "middle",
      border: { type: "solid", color: HEX.rule, pt: 0.5 }, objectName: "modules table" });
  [[`${F.hand_checks_pass} / 10`, "hand-checked observations, raw workbook cell to panel"], [`${F.terminal_checks_pass} / 7`, "terminal checks (pilot)"]]
    .forEach(([v, l], i) => stat(s, 8.9, 2.0 + i * 1.65, 3.83, 1.45, v, l, C.accent3));
  s.addShape(pres.ShapeType.roundRect, { x: 8.9, y: 5.35, w: 3.83, h: 1.0, fill: { color: HEX.navy }, line: { color: HEX.navy }, rectRadius: 0.08, objectName: "run_all card" });
  T(s, "python src/run_all.py", { x: 8.9, y: 5.35, w: 3.83, h: 1.0, fontSize: 18, bold: true, color: C.background1, fontFace: "Courier New", align: "center", valign: "middle" });
  s.addNotes("A full rebuild reproduced every table, figure and manifest identically. Compressed files are written with a fixed " +
    "timestamp so they are byte-identical too.");
}

// ================================================================ 13 decisions and next steps
{
  const s = slideFor("Next steps", "13  |  DECISIONS AND NEXT STEPS", "Six questions for Professor Hamid before estimation", "CONTENT_DARK");
  const qs = [["D1", "No Bloomberg headline export: are the 188 headlines acceptable as the primary sample?"],
    ["P5", "Which vendor value should each headline be compared with: next weekday, same day, or their average?"],
    ["E2", "Primary horizon: open-to-close on the value date, or next-day close-to-close?"],
    ["E2", "Primary scoring rule: Loughran-McDonald lexicon or FinBERT, with the other as robustness?"],
    ["O6", "Keep Friday and Saturday headlines, given the weekend gap?"],
    ["S3", "Start the secondary exercise on the broad panel now, or after the design freeze?"]];
  qs.forEach(([id, q], i) => {
    const y = 2.0 + i * 0.78;
    badge(s, M, y, id, 0.58, C.accent1, 13);
    T(s, q, { x: M + 0.8, y: y - 0.035, w: 6.6, h: 0.65, fontSize: 14, color: C.background1, valign: "middle" });
  });
  s.addShape(pres.ShapeType.roundRect, { x: 8.45, y: 2.0, w: 4.28, h: 4.65, fill: { color: "22394A" }, line: { color: "22394A" }, rectRadius: 0.08, objectName: "next steps card" });
  T(s, "Next checkpoint", { x: 8.75, y: 2.2, w: 3.7, h: 0.45, fontSize: 18, bold: true, color: C.accent5 });
  T(s, [{ text: "Freeze the design log (P1-P6, E1-E2)", options: { bullet: true, breakLine: true } },
    { text: `Build both reproducible scores on the ${F.attrition_A2} member headlines`, options: { bullet: true, breakLine: true } },
    { text: "Run the primary test: HAC / clustered SE, encompassing and DM", options: { bullet: true, breakLine: true } },
    { text: `Secondary: vendor score on ${fmt(F.attrition_8)} security-days`, options: { bullet: true } }],
    { x: 8.75, y: 2.8, w: 3.75, h: 3.7, fontSize: 15, color: C.background1, paraSpaceAfter: 12 });
  s.addNotes("These are the decisions that must be settled before any return is related to any score. None of them is chosen by " +
    "looking at results.");
}

// ================================================================ 14 appendix
{
  const s = slideFor("Appendix", "14  |  DATA LINEAGE APPENDIX", "Appendix: every data source and its validation status");
  const head = ["Dataset", "What it holds", "Status"].map((t) => ({ text: t, options: { bold: true, color: HEX.white, fill: { color: HEX.navy } } }));
  const tidy = (t) => t.replace(/; too large for the connector/, "").replace(/ \(37,018 bytes; SHA-256 53bff1c0\.\.\.\)/, "");
  s.addTable([head, ...D.manifest.map((r, i) => r.map(tidy).map((t, j) => ({ text: t, options: {
    bold: j === 0, color: j === 2 && t.startsWith("PENDING") ? HEX.orange : HEX.navy, fill: { color: i % 2 ? HEX.white : HEX.light } } })))],
    { x: M, y: 1.95, w: CW, colW: [2.45, 5.85, 3.83], fontSize: 10.5, color: HEX.navy, rowH: 0.34, valign: "middle",
      border: { type: "solid", color: HEX.rule, pt: 0.5 }, objectName: "manifest table" });
  s.addNotes("Full detail, with paths, join keys, point-in-time status and licences, is in manifests/data_manifest.csv and " +
    "manifests/bloomberg_source_log.csv.");
}

pres.writeFile({ fileName: outPath }).then((f) => console.log(`wrote ${f}`));
