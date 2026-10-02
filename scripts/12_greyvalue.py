#!/usr/bin/env python3
"""Measure the colour of a page: how much ink a paragraph actually puts down.

    python scripts/12_greyvalue.py

Sidebearing ratios say whether spacing was preserved arithmetically. They do
not say whether the page LOOKS right, because raising the x-height adds ink to
the letter without adding any white beside it. A face can keep every
sidebearing in proportion and still set too dark.

Method: render the same paragraph in each font at a size normalised so every
font has the SAME x-height in pixels - otherwise a bigger x-height trivially
means more ink and the comparison says nothing - then count the ink.

Two numbers come out:

  coverage   ink pixels / total pixels of the text block. The page's colour.
  set width  how much horizontal room the same words need. Economy.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from vavin import config as C
from vavin.metrics import measure

#: Normalise every font to this x-height in pixels before comparing.
TARGET_X_PX = 42

#: ONE line, deliberately. A multi-line block measures leading as much as
#: letterfit: Vavin sets on 1.20 em against EB Garamond's 1.305, so at an equal
#: x-height its lines sit 21% closer and the block reads 22% darker even if
#: every letter and every sidebearing were identical. That is a real difference
#: but it is a line-height decision, not a spacing one, and mixing the two
#: hides whichever you were trying to measure.
LINE = "une tension entre ce qui se voit et ce qui se lit"


def render(path: Path, size: float) -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        out = Path(tmp.name)
    subprocess.run(
        [
            "hb-view", f"--font-file={path}", f"--font-size={size:.2f}",
            "--output-format=png", f"--output-file={out}", "--margin=0",
            "--background=ffffff", "--foreground=000000", LINE,
        ],
        check=True, capture_output=True,
    )
    image = Image.open(out).convert("L")
    out.unlink(missing_ok=True)
    return image


def ink_amount(image: Image.Image) -> float:
    """Total ink, in pixel-equivalents."""
    return sum((255 - p) for p in image.tobytes()) / 255.0


def main() -> int:
    C.BUILD.mkdir(parents=True, exist_ok=True)
    ref_path = C.BUILD / "EBGaramond-Regular-reference.ttf"
    if not ref_path.exists():
        instancer.instantiateVariableFont(
            TTFont(C.UPSTREAM_VF), {"wght": 400}, inplace=False
        ).save(ref_path)

    fonts = [("EB Garamond", ref_path)]
    for family, recipe in C.FAMILIES.items():
        for style in recipe["styles"]:
            if style != "Regular":
                continue
            p = C.font_path(style, family)
            if p.exists():
                fonts.append((family, p))

    print(f"\n  every font set to an identical x-height of {TARGET_X_PX} px,")
    print("  so more ink means darker colour, not bigger type\n")
    print(f"  {'font':<20} {'size':>7} {'density':>9} {'vs source':>10} {'set width':>10}")
    print("  " + "-" * 62)

    base_cov = base_w = None
    for label, path in fonts:
        prop = measure(TTFont(path))
        size = TARGET_X_PX * prop.upm / prop.x_height
        image = render(path, size)
        # Ink per unit of set width: the density of the line itself, with
        # leading taken out of the question entirely.
        density = ink_amount(image) / image.width
        if base_cov is None:
            base_cov, base_w = density, image.width
            print(f"  {label:<20} {size:>7.1f} {density:>8.2f}  {'—':>9} {image.width:>9}px")
        else:
            print(
                f"  {label:<20} {size:>7.1f} {density:>8.2f}"
                f" {(density - base_cov) / base_cov * 100:>+9.1f}%"
                f" {image.width:>9}px  ({(image.width - base_w) / base_w * 100:+.1f}%)"
            )

    print()
    print("  density = ink per pixel of set width, at an identical x-height:")
    print("  the colour of the line with leading and size taken out.")
    print("  Past about +5% a line reads visibly darker.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
