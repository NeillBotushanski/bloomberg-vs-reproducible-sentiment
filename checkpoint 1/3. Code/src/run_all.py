"""Rebuild every checkpoint-1 output from the raw files, in order. Run from the project root:

    python src/run_all.py
"""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
for script in ["02_raw_validation.py", "03_build_signals.py", "04_build_outcomes.py", "05_merge_analysis_panel.py",
               "06_descriptive_diagnostics.py", "07_hand_checks.py", "build_checkpoint_report.py",
               "build_progress_deck_data.py"]:
    print(f"\n=== {script}", flush=True)
    subprocess.run([sys.executable, str(SRC / script)], check=True, cwd=SRC.parent)

# The checkpoint-1 PowerPoint (node + pptxgenjs), then its theme colours.
DECK = "reports/checkpoint_1_progress_update.pptx"
print("\n=== build_progress_deck.js", flush=True)
subprocess.run(["node", str(SRC / "build_progress_deck.js"), "outputs/diagnostics/deck_data.json", DECK], check=True, cwd=SRC.parent)
subprocess.run([sys.executable, str(SRC / "apply_deck_theme.py"), DECK], check=True, cwd=SRC.parent)

# The presentation script, as a printable PDF.
print("\n=== build_presentation_script_pdf.py", flush=True)
subprocess.run([sys.executable, str(SRC / "build_presentation_script_pdf.py"), "reports/presentation_script.md",
                "reports/checkpoint_1_presentation_script.pdf"], check=True, cwd=SRC.parent)
