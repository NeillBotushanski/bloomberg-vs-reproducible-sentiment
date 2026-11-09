"""Write the deck's own colours into its theme (pptxgenjs leaves Office's stock palette) and mend one chart fault.

    python src/apply_deck_theme.py reports/checkpoint_1_progress_update.pptx

* ppt/theme/theme1.xml: the colour scheme becomes the MMF 1941 palette below and the theme is named.
* chart XML: pptxgenjs writes <c:crossesAt val="autoZero"/>, which PowerPoint offers to repair; it becomes
  <c:crosses val="autoZero"/>.
The file is rewritten in place; every other part is copied byte for byte with a fixed timestamp.
"""
import re
import sys
import zipfile
from pathlib import Path

NAME = "MMF 1941 Project 2"
COLORS = {"dk1": "172B3A", "lt1": "FFFFFF", "dk2": "5F6F7A", "lt2": "EEF2F4", "accent1": "087E8B", "accent2": "C56A11",
          "accent3": "2E7D5A", "accent4": "B5473C", "accent5": "9DB4C0", "accent6": "D9E2E7", "hlink": "087E8B",
          "folHlink": "5F6F7A"}


def scheme_xml() -> str:
    body = "".join(f'<a:{k}><a:srgbClr val="{v}"/></a:{k}>' for k, v in COLORS.items())
    return f'<a:clrScheme name="{NAME}">{body}</a:clrScheme>'


def main(path: str) -> None:
    p = Path(path)
    zin = zipfile.ZipFile(p)
    items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    zin.close()
    tmp = p.with_suffix(".tmp")
    n_theme = n_cross = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in items:
            name = info.filename
            if name.endswith("/"):                      # folder entries break some cloud editors; files carry the paths
                continue
            if re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
                x = data.decode("utf-8")
                x, k = re.subn(r"<a:clrScheme\b[^>]*>.*?</a:clrScheme>", scheme_xml(), x, count=1, flags=re.S)
                x = re.sub(r'(<a:theme\b[^>]*\bname=")[^"]*(")', rf"\g<1>{NAME}\g<2>", x, count=1)
                n_theme += k
                data = x.encode("utf-8")
            elif name.startswith("ppt/charts/") and name.endswith(".xml"):
                x = data.decode("utf-8")
                x, k = re.subn(r'<c:crossesAt val="autoZero"\s*/>', '<c:crosses val="autoZero"/>', x)
                n_cross += k
                data = x.encode("utf-8")
            zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zi, data)
    tmp.replace(p)
    print(f"theme parts recoloured: {n_theme}; chart axes mended: {n_cross}")


if __name__ == "__main__":
    main(sys.argv[1])
