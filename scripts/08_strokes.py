#!/usr/bin/env python3
"""Measure stroke weights and contrast, upstream against the result.

    python scripts/08_strokes.py

"Scaling y thickens the horizontals" is easy to assert and hard to be right
about. This measures it.

Method: flatten the outline to line segments and intersect it with a scanline
analytically. A horizontal scanline through a stem gives the vertical stroke
weight; a vertical scanline through a bowl gives the horizontal one. Contrast
is the ratio.

Deliberately NOT done by rasterising: hb-view crops to the ink bounding box,
so the same scanline index lands on different features in two fonts of
different heights, and the numbers come out nonsense - stems appearing to
halve when nothing touched them.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from vavin import config as C
from vavin.metrics import measure

FLATTEN_STEPS = 24


class SegmentPen(BasePen):
    """Flattens an outline into straight segments."""

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.segments: list[tuple[tuple, tuple]] = []
        self._start = None
        self._current = None

    def _moveTo(self, pt):
        self._start = self._current = pt

    def _lineTo(self, pt):
        self.segments.append((self._current, pt))
        self._current = pt

    def _curveToOne(self, p1, p2, p3):
        p0 = self._current
        prev = p0
        for i in range(1, FLATTEN_STEPS + 1):
            t = i / FLATTEN_STEPS
            u = 1 - t
            point = (
                u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
            )
            self.segments.append((prev, point))
            prev = point
        self._current = p3

    def _closePath(self):
        if self._current and self._start and self._current != self._start:
            self.segments.append((self._current, self._start))
        self._current = self._start


def outline(font: TTFont, char: str) -> list[tuple[tuple, tuple]]:
    name = font.getBestCmap().get(ord(char))
    glyph_set = font.getGlyphSet()
    pen = SegmentPen(glyph_set)
    glyph_set[name].draw(pen)
    return pen.segments


def crossings_at_y(segments, y: float) -> list[float]:
    """x coordinates where the outline crosses a horizontal line."""
    xs = []
    for (x0, y0), (x1, y1) in segments:
        if (y0 <= y < y1) or (y1 <= y < y0):
            xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
    return sorted(xs)


def crossings_at_x(segments, x: float) -> list[float]:
    """y coordinates where the outline crosses a vertical line."""
    ys = []
    for (x0, y0), (x1, y1) in segments:
        if (x0 <= x < x1) or (x1 <= x < x0):
            ys.append(y0 + (x - x0) * (y1 - y0) / (x1 - x0))
    return sorted(ys)


def spans(values: list[float]) -> list[float]:
    """Ink run lengths between alternate crossings."""
    return [values[i + 1] - values[i] for i in range(0, len(values) - 1, 2)]


def stem_width(
    font: TTFont, char: str, height: float, fraction: float = 0.5
) -> float | None:
    """Vertical stroke weight, on a horizontal cut at `fraction` of `height`.

    `fraction` matters more than it looks. Cutting `H` at mid cap-height runs
    straight along its crossbar, so the two stems and the bar read as one
    continuous span and the "stem width" comes out as the width of the whole
    letter. Cut it at 0.85 instead and the two stems are separate.
    """
    runs = spans(crossings_at_y(outline(font, char), height * fraction))
    return max(runs) if runs else None


def cap_stem(font: TTFont, cap_height: float) -> float | None:
    """Capital stem weight, measured on H clear of its crossbar."""
    runs = spans(crossings_at_y(outline(font, "H"), cap_height * 0.85))
    return min(runs) if runs else None


def hairline(font: TTFont, char: str) -> float | None:
    """Horizontal stroke weight: the thin part of a bowl, cut vertically."""
    segments = outline(font, char)
    xs = [p[0] for seg in segments for p in seg]
    centre = 0.5 * (min(xs) + max(xs))
    runs = spans(crossings_at_x(segments, centre))
    return min(runs) if runs else None


def main() -> int:
    reg = C.font_path("Regular")
    C.BUILD.mkdir(parents=True, exist_ok=True)
    ref_path = C.BUILD / "EBGaramond-Regular-reference.ttf"
    if not ref_path.exists():
        instancer.instantiateVariableFont(
            TTFont(C.UPSTREAM_VF), {"wght": 400}, inplace=False
        ).save(ref_path)

    ref, new = TTFont(ref_path), TTFont(reg)
    a, b = measure(ref), measure(new)
    y_scale = b.x_height / a.x_height

    print(f"\n  x-height {a.x_height:.0f} -> {b.x_height:.0f}  (x{y_scale:.4f})")
    print(f"  configured LC_X_SCALE {C.LC_X_SCALE}")
    print(f"\n  predicted: vertical stems x{C.LC_X_SCALE:.4f},"
          f" horizontals x{y_scale:.4f},"
          f" contrast x{C.LC_X_SCALE / y_scale:.4f}"
          f" ({(C.LC_X_SCALE / y_scale - 1) * 100:+.1f}%)\n")

    print(f"  {'':<7} {'--- EB Garamond ---':>27}  {'--- Vavin ---':>27}")
    print(f"  {'glyph':<7} {'stem':>7} {'hair':>7} {'contr':>7}"
          f"  {'stem':>7} {'hair':>7} {'contr':>7}   {'contrast':>9}")
    print("  " + "-" * 78)

    contrast_changes = []
    # Only letters with a bowl or a shoulder: a vertical cut through `l` or
    # `i` finds no horizontal stroke at all, just the full height of the stem,
    # and averaging that in poisons the result.
    for char in "onbdpqech":
        stem_a = stem_width(ref, char, a.x_height)
        stem_b = stem_width(new, char, b.x_height)
        hair_a = hairline(ref, char)
        hair_b = hairline(new, char)
        if not all(v and v > 1 for v in (stem_a, stem_b, hair_a, hair_b)):
            continue
        if hair_a > 0.4 * a.x_height:  # no horizontal stroke on this scanline
            continue
        ca, cb = stem_a / hair_a, stem_b / hair_b
        change = (cb - ca) / ca * 100
        contrast_changes.append(change)
        print(
            f"  {char:<7} {stem_a:>7.1f} {hair_a:>7.1f} {ca:>7.2f}"
            f"  {stem_b:>7.1f} {hair_b:>7.1f} {cb:>7.2f}   {change:>+8.1f}%"
        )

    if contrast_changes:
        mean = sum(contrast_changes) / len(contrast_changes)
        print("  " + "-" * 78)
        print(f"  mean contrast change across {len(contrast_changes)} glyphs:"
              f" {mean:+.1f}%")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
