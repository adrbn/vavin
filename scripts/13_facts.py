#!/usr/bin/env python3
"""Print every number the README and docs/TECHNICAL.md quote, measured now.

    python scripts/13_facts.py

Nothing in the docs should be copied from an older doc. Change the build,
run this, and update the prose from its output.

Language counts come from Hyperglot, which is a separate tool:

    .venv/bin/hyperglot dist/Vavin/ttf/Vavin-Regular.ttf
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from vavin import config as C
from vavin.metrics import measure

strokes = __import__("08_strokes")

BOWLS = "onbdpqec"  # letters with a hairline on a vertical cut, as in 09_variants


def upstream(italic: bool = False, wght: int = 400) -> TTFont:
    src = C.UPSTREAM_VF_ITALIC if italic else C.UPSTREAM_VF
    return instancer.instantiateVariableFont(TTFont(src), {"wght": wght}, inplace=False)


def contrast(font: TTFont, x_height: float) -> float:
    ratios = []
    for char in BOWLS:
        stem = strokes.stem_width(font, char, x_height)
        hair = strokes.hairline(font, char)
        if stem and hair and hair < 0.4 * x_height:
            ratios.append(stem / hair)
    return sum(ratios) / len(ratios)


def ink_top(font: TTFont, char: str) -> float:
    gs = font.getGlyphSet()
    from fontTools.pens.boundsPen import BoundsPen
    pen = BoundsPen(gs)
    gs[font.getBestCmap()[ord(char)]].draw(pen)
    return pen.bounds[3]


def sidebearings(font: TTFont, char: str) -> float:
    name = font.getBestCmap()[ord(char)]
    advance, lsb = font["hmtx"][name]
    from fontTools.pens.boundsPen import BoundsPen
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    xmin, _, xmax, _ = pen.bounds
    return xmin + (advance - xmax)


def row(label: str, font: TTFont) -> dict:
    p = measure(font)
    cmap = font.getBestCmap()
    x = p.x_height
    facts = dict(
        x=x, cap=p.cap_height, ratio=x / p.cap_height,
        n=font["hmtx"][cmap[ord("n")]][0],
        contrast=contrast(font, x),
        lcuc=strokes.stem_width(font, "n", x) / strokes.cap_stem(font, p.cap_height),
        t=(ink_top(font, "t") - x) / x,
        sb_n=sidebearings(font, "n") / x, sb_o=sidebearings(font, "o") / x,
        glyphs=len(font.getGlyphOrder()), cps=len(cmap),
        hhea=f"{font['hhea'].ascent}/{font['hhea'].descent}",
        line=(font["hhea"].ascent - font["hhea"].descent + font["hhea"].lineGap) / p.upm,
        angle=font["post"].italicAngle,
    )
    print(f"  {label:<24} x {x:5.0f}  cap {p.cap_height:5.0f}  x/cap {facts['ratio']:.3f}"
          f"  n {facts['n']:4}  contrast {facts['contrast']:.2f}  lc/uc {facts['lcuc']:.3f}"
          f"  t {facts['t']:.3f}  sb n/o {facts['sb_n']:.3f}/{facts['sb_o']:.3f}"
          f"  hhea {facts['hhea']} ({facts['line']:.2f} em)  {facts['glyphs']} glyphs"
          f"  {facts['cps']} cp  angle {facts['angle']:g}")
    return facts


def main() -> int:
    print()
    ref = row("EB Garamond 400", upstream())
    row("EB Garamond Italic 400", upstream(italic=True))
    built = {}
    for family, recipe in C.FAMILIES.items():
        for style in recipe["styles"]:
            path = C.font_path(style, family)
            if not path.exists():
                print(f"!! build first: {path}", file=sys.stderr)
                return 1
            built[(family, style)] = row(f"{family} {style}", TTFont(path))

    reg = built[("Vavin", "Regular")]
    print()
    print(f"  Vavin Regular against EB Garamond 400")
    print(f"    x-height scale         x{reg['x'] / ref['x']:.4f}")
    print(f"    contrast               {ref['contrast']:.2f} -> {reg['contrast']:.2f}")
    print(f"    lc/uc stem             {ref['lcuc']:.3f} -> {reg['lcuc']:.3f}")
    print(f"    t above x-height       {ref['t']:.3f} -> {reg['t']:.3f} of the x-height")
    print(f"    sidebearings / x       n {(reg['sb_n'] / ref['sb_n'] - 1) * 100:+.1f}%"
          f"   o {(reg['sb_o'] / ref['sb_o'] - 1) * 100:+.1f}%")

    lean = abs(TTFont(C.UPSTREAM_VF_ITALIC)["post"].italicAngle)
    k = 0.318
    folded = math.degrees(math.atan(math.tan(math.radians(lean)) / k))
    print(f"    italic stem lean {lean:.1f} deg, compressed by k={k} unsheared -> {folded:.0f} deg")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
