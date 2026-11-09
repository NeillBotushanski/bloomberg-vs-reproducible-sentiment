"""Collect, from saved outputs only, every number and table the checkpoint-1 slides show: outputs/diagnostics/deck_data.json.
src/build_progress_deck.js turns that file into reports/checkpoint_1_progress_update.pptx.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DIAG, ROOT  # noqa: E402


def rd(rel, **kw):
    return pd.read_csv(ROOT / rel, **kw)


facts = {r.fact: r.value for r in rd("outputs/tables/checkpoint_1_facts.csv").itertuples()}
facts = {k: (int(v) if float(v).is_integer() else float(v)) for k, v in facts.items()}
cm = rd("outputs/tables/coverage_by_month.csv")
cy = rd("outputs/tables/coverage_by_year.csv", index_col=0).drop("2020-2025")
sq = rd("outputs/tables/coverage_by_size_quintile.csv", index_col=0)
wk = rd("outputs/tables/vendor_counts_by_value_day.csv", index_col=0)
hw = rd("outputs/tables/headline_weekday_by_vendor_value.csv", index_col=0)
att = rd("manifests/sample_attrition.csv", dtype={"step": str})
man = rd("manifests/data_manifest.csv")
data = {
    "facts": facts,
    "monthly": {"month": cm["month"].tolist(), "all": (cm["share_sent"] * 100).round(1).tolist(),
                "firms19": (cm["share_sent_19_firms"] * 100).round(1).tolist(),
                "pub_median": cm["pub"].round(1).tolist(), "scored_median": cm["scored"].round(1).tolist()},
    "by_year": {"year": [str(y) for y in cy.index], "pct_sent": cy["pct_with_sentiment"].round(1).tolist(),
                "pct_zero": cy["pct_sentiment_exactly_0"].round(1).tolist(), "sd": cy["sentiment_sd"].round(3).tolist(),
                "mean_pub": cy["mean_publication_count"].round(1).tolist()},
    "size": {"q": ["Q1 small", "Q2", "Q3", "Q4", "Q5 large"], "pct_sent": sq["pct_with_sentiment"].round(1).tolist()},
    "weekday": {"day": [d.replace("\n", " ") for d in wk.index], "pub": wk["pub"].round(1).tolist(),
                "scored": wk["scored"].round(1).tolist()},
    "headline_weekday": {"day": hw.index.tolist(), **{c: hw[c].astype(int).tolist() for c in hw.columns}},
    "attrition": att[["step", "rule", "security_days_or_headlines"]].astype({"security_days_or_headlines": int}).values.tolist(),
    "manifest": man[["dataset_id", "construct", "validation_status"]].values.tolist(),
}
(DIAG / "deck_data.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
print(json.dumps(data, separators=(",", ":")))
