"""Render the checkpoint-1 presentation script (Markdown) as a printable PDF. Run from the project root:

    python src/build_presentation_script_pdf.py reports/presentation_script.md reports/checkpoint_1_presentation_script.pdf

Reads the small Markdown subset the script uses: '#' title (the next line is the byline), '##' sections, '###' slide
headings ending in '(time)', '|' tables, '-' bullets, '1.' numbered lines, `code` and plain paragraphs.
Uses Carlito (metric twin of the deck's Calibri) when installed, otherwise Helvetica. Output is byte-reproducible.
"""
import re
import sys
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

rl_config.invariant = 1                                     # fixed IDs and dates, so rebuilds are byte-identical

NAVY, TEAL, GREY, LIGHT, RULE = (colors.HexColor(h) for h in ("#172B3A", "#087E8B", "#5F6F7A", "#EEF2F4", "#D9E2E7"))
TITLE = "Checkpoint 1 Presentation Script"

CARLITO = Path("/usr/share/fonts/truetype/crosextra")
if (CARLITO / "Carlito-Regular.ttf").exists():
    for face, file in [("Body", "Regular"), ("Body-Bold", "Bold"), ("Body-Italic", "Italic"), ("Body-BoldItalic", "BoldItalic")]:
        pdfmetrics.registerFont(TTFont(face, str(CARLITO / f"Carlito-{file}.ttf")))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-BoldItalic")
    BODY, BOLD, ITALIC = "Body", "Body-Bold", "Body-Italic"
else:
    BODY, BOLD, ITALIC = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"

S = {
    "title": ParagraphStyle("title", fontName=BOLD, fontSize=24, leading=29, textColor=NAVY, spaceAfter=6),
    "byline": ParagraphStyle("byline", fontName=BODY, fontSize=11, leading=15, textColor=GREY, spaceAfter=14),
    "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=15, leading=19, textColor=TEAL, spaceBefore=16, spaceAfter=8,
                         keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName=BOLD, fontSize=12.5, leading=16, textColor=NAVY, spaceBefore=11, spaceAfter=4,
                         keepWithNext=1),
    "body": ParagraphStyle("body", fontName=BODY, fontSize=11.5, leading=16, textColor=NAVY, spaceAfter=7, alignment=TA_LEFT),
    "cell": ParagraphStyle("cell", fontName=BODY, fontSize=10, leading=13, textColor=NAVY),
    "head": ParagraphStyle("head", fontName=BOLD, fontSize=10, leading=13, textColor=colors.white),
}


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"`([^`]+)`", r'<font name="Courier" size="9.5">\1</font>', text)


def table(rows: list[list[str]]) -> Table:
    ncol = len(rows[0])
    widths = {4: [0.6, 3.6, 1.1, 1.1], 2: [2.3, 4.5]}.get(ncol, [6.8 / ncol] * ncol)
    data = [[Paragraph(inline(c), S["head"] if r == 0 else S["cell"]) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * inch for w in widths], repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def story_from(md: str) -> list:
    lines, out, i = md.splitlines(), [], 0
    para_style = S["body"]
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
        elif line.startswith("# "):
            out.append(Paragraph(inline(line[2:]), S["title"]))
            if i + 1 < len(lines) and lines[i + 1].strip():
                out.append(Paragraph(inline(lines[i + 1].strip()), S["byline"]))
                i += 1
            i += 1
        elif line.startswith("## "):
            out.append(Paragraph(inline(line[3:]), S["h2"]))
            i += 1
        elif line.startswith("### "):
            head = inline(line[4:])
            m = re.fullmatch(r"(.*) \((.*)\)", head)
            if m:
                head = f'{m.group(1)}  <font name="{BODY}" color="#087E8B">{m.group(2)}</font>'
            out.append(Paragraph(head, S["h3"]))
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out += [Spacer(1, 2), table(rows), Spacer(1, 10)]
        elif re.match(r"(- |\d+\. )", line):
            numbered = not line.startswith("- ")
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i]):
                items.append(ListItem(Paragraph(inline(re.sub(r"^(- |\d+\. )", "", lines[i].strip())), S["body"])))
                i += 1
            out.append(ListFlowable(items, bulletType="1" if numbered else "bullet", start="1" if numbered else None,
                                    leftIndent=18, bulletFontName=BOLD if numbered else BODY, bulletColor=TEAL,
                                    bulletFontSize=11 if numbered else 9))
        else:
            out.append(Paragraph(inline(line), para_style))
            i += 1
    while out and isinstance(out[-1], Spacer):             # a trailing spacer can spill onto an empty last page
        out.pop()
    return keep_slides_whole(out)


def keep_slides_whole(flow: list) -> list:
    """Hold each slide (heading and text) and each untitled section (heading and table) on one page, and keep a
    section heading with its first slide, so no page turn splits a slide or strands a heading."""
    grouped, block = [], []

    def close():
        if block:
            grouped.append(KeepTogether(list(block)))
            block.clear()

    for f in flow:
        name = getattr(getattr(f, "style", None), "name", "")
        if name in ("h2", "h3"):
            only_section_heading = len(block) == 1 and block[0].style.name == "h2"
            if not (name == "h3" and only_section_heading):
                close()
            block.append(f)
        elif name in ("title", "byline"):
            close()
            grouped.append(f)
        elif block:
            block.append(f)
        else:
            grouped.append(f)
    close()
    return grouped


class NumberedCanvas(rl_canvas.Canvas):
    """Draws 'page n of N' and the running title once the page count is known."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            w, _ = letter
            self.setStrokeColor(RULE)
            self.setLineWidth(0.6)
            self.line(0.85 * inch, 0.62 * inch, w - 0.85 * inch, 0.62 * inch)
            self.setFont(BODY, 9)
            self.setFillColor(GREY)
            self.drawString(0.85 * inch, 0.45 * inch, f"{TITLE} · Project 2 · MMF 1941")
            self.drawRightString(w - 0.85 * inch, 0.45 * inch, f"Page {self._pageNumber} of {n}")
            super().showPage()
        super().save()


def main(src: str, dst: str) -> None:
    md = Path(src).read_text(encoding="utf-8")
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(dst, pagesize=letter, leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            topMargin=0.8 * inch, bottomMargin=0.9 * inch, title=TITLE,
                            author="Neill Liran Botushanski", subject="MMF 1941 Project 2, checkpoint 1",
                            creator="src/build_presentation_script_pdf.py")
    doc.build(story_from(md), canvasmaker=NumberedCanvas)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
