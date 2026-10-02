"""Vertical metrics.

Get these wrong and the font looks fine in a proof and broken in the app.

There are three competing sets of numbers in every OpenType font:

  hhea.ascender / descender / lineGap    what Apple platforms read
  OS/2 sTypoAscender / Descender / LineGap   what the spec says to read
  OS/2 usWinAscent / usWinDescent        a clipping box on Windows

The policy here is the Google Fonts one, which is also the only sane choice
for an app:

  * hhea == sTypo, so every platform agrees on line height
  * lineGap == 0, so leading is controlled by the app, not the font
  * usWin* cover the real ink of the whole font, so nothing ever clips
  * fsSelection bit 7 (USE_TYPO_METRICS) set, so Windows honours sTypo

On iOS this matters directly:

    UIFont.lineHeight == hhea.ascender - hhea.descender + hhea.lineGap

so the numbers written here are the line height your SwiftUI Text views get
by default.
"""

from __future__ import annotations

from dataclasses import dataclass

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

USE_TYPO_METRICS_BIT = 1 << 7


@dataclass
class VerticalMetrics:
    typo_ascender: int
    typo_descender: int
    typo_line_gap: int
    win_ascent: int
    win_descent: int
    ink_top: int
    ink_bottom: int

    def report(self, upm: int) -> str:
        line_height = self.typo_ascender - self.typo_descender + self.typo_line_gap
        return "\n".join(
            [
                "  vertical metrics",
                "  " + "-" * 58,
                f"    hhea == sTypo asc/desc/gap   {self.typo_ascender} /"
                f" {self.typo_descender} / {self.typo_line_gap}",
                f"    usWinAscent / usWinDescent   {self.win_ascent} / {self.win_descent}",
                f"    real ink top / bottom        {self.ink_top} / {self.ink_bottom}",
                f"    USE_TYPO_METRICS             set",
                "",
                f"    line height  {line_height} units = {line_height / upm:.4f} em",
                f"    -> iOS UIFont.lineHeight at 17pt = {17 * line_height / upm:.2f} pt",
            ]
        )


def measure_ink_extremes(font: TTFont) -> tuple[int, int]:
    """The highest and lowest ink in the whole font, across every glyph."""
    glyph_set = font.getGlyphSet()
    top, bottom = 0, 0
    for name in font.getGlyphOrder():
        pen = BoundsPen(glyph_set)
        try:
            glyph_set[name].draw(pen)
        except Exception:
            continue
        if pen.bounds is None:
            continue
        top = max(top, pen.bounds[3])
        bottom = min(bottom, pen.bounds[1])
    return int(round(top)), int(round(bottom))


def compute_family(fonts: list[TTFont], *, line_height_em: float) -> VerticalMetrics:
    """One metric set for the whole family, derived from all styles' ink.

    Vertical metrics MUST be identical across every style of a family. If
    Regular and Bold disagree, the line height changes the moment a run of
    text is emboldened - paragraphs reflow, a SwiftUI list jumps as rows
    switch weight. Deriving them per style is the mistake; deriving them once
    from the union of every style's ink is the fix.

    The bounds come from `head.yMax`/`head.yMin` of the *compiled* font, which
    is what the rasteriser and the QA tools read, rather than from an
    in-memory pen that can disagree by a unit on composite glyphs.
    """
    upm = fonts[0]["head"].unitsPerEm
    ink_top = max(f["head"].yMax for f in fonts)
    ink_bottom = min(f["head"].yMin for f in fonts)

    # Split the requested line height around the baseline in the same
    # proportion as the font's own ink, so the text sits optically centred.
    total_ink = ink_top - ink_bottom
    target = int(round(line_height_em * upm))
    ascender = int(round(target * (ink_top / total_ink)))
    descender = ascender - target

    return VerticalMetrics(
        typo_ascender=ascender,
        typo_descender=descender,
        typo_line_gap=0,
        # usWin is a clipping box, not a line height: it must cover the
        # tallest and deepest ink in the *family*, or a glyph from one style
        # clips when set beside another.
        win_ascent=max(ascender, ink_top),
        win_descent=abs(min(descender, ink_bottom)),
        ink_top=ink_top,
        ink_bottom=ink_bottom,
    )


def apply(font: TTFont, vm: VerticalMetrics, *, x_height: int, cap_height: int) -> None:
    os2 = font["OS/2"]
    hhea = font["hhea"]

    hhea.ascender = vm.typo_ascender
    hhea.descender = vm.typo_descender
    hhea.lineGap = vm.typo_line_gap

    os2.sTypoAscender = vm.typo_ascender
    os2.sTypoDescender = vm.typo_descender
    os2.sTypoLineGap = vm.typo_line_gap
    os2.usWinAscent = vm.win_ascent
    os2.usWinDescent = vm.win_descent
    os2.fsSelection |= USE_TYPO_METRICS_BIT

    # These two are advisory but real software reads them - Adobe apps use
    # sxHeight for optical alignment, browsers use it for the `ex` unit and
    # for font fallback size-adjust. Upstream shipped 400/650 against a real
    # 405/653, so they are refreshed from measurement here.
    if hasattr(os2, "sxHeight"):
        os2.sxHeight = int(round(x_height))
    if hasattr(os2, "sCapHeight"):
        os2.sCapHeight = int(round(cap_height))


def validate(font: TTFont) -> list[str]:
    """Return a list of problems, empty if the metrics are coherent."""
    os2, hhea = font["OS/2"], font["hhea"]
    ink_top, ink_bottom = measure_ink_extremes(font)
    problems = []

    if hhea.ascender != os2.sTypoAscender:
        problems.append(
            f"hhea.ascender ({hhea.ascender}) != sTypoAscender ({os2.sTypoAscender}):"
            " line height will differ between macOS and Windows"
        )
    if hhea.descender != os2.sTypoDescender:
        problems.append(
            f"hhea.descender ({hhea.descender}) != sTypoDescender ({os2.sTypoDescender})"
        )
    if hhea.lineGap != 0 or os2.sTypoLineGap != 0:
        problems.append("lineGap is not 0: leading is baked into the font")
    if not os2.fsSelection & USE_TYPO_METRICS_BIT:
        problems.append("USE_TYPO_METRICS (fsSelection bit 7) is not set")
    if os2.usWinAscent < ink_top:
        problems.append(
            f"usWinAscent ({os2.usWinAscent}) < real ink top ({ink_top}):"
            " glyphs will clip on Windows"
        )
    if os2.usWinDescent < abs(ink_bottom):
        problems.append(
            f"usWinDescent ({os2.usWinDescent}) < real ink bottom ({abs(ink_bottom)}):"
            " descenders will clip on Windows"
        )
    return problems
