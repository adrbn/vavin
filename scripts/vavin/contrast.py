"""A directional contrast filter: thin the hairlines, thicken the stems.

Stroke contrast is the ratio of a stem's weight to a hairline's, and it is
most of what separates a display face from a text face. Raising it with an
affine transform is impossible: scaling x thickens the stems but also widens
the letter, and the two cannot be separated. That is the wall
`scripts/09_variants.py` runs into.

This does it properly, by moving each point along the outline's own normal by
an amount that depends on which way the outline is running there:

      outline running vertically  -> it is the side of a STEM
                                     push outward, the stem thickens

      outline running horizontally -> it is the top or bottom of a HAIRLINE
                                     push inward, the hairline thins

    offset(p) = N(p) * d * (|T.y| - |T.x|)

where T is the unit tangent and N the outward unit normal. The factor runs
smoothly from +1 on a vertical tangent to -1 on a horizontal one, so a curve
is treated correctly all the way round a bowl: thick at its sides, thin at its
top and bottom. That is exactly how a broad-nib pen behaves, which is why the
result still reads as a Garamond rather than as a distortion.

Two things this must get right:

* **Winding, and specifically that it is a per-GLYPH question.** The
  away-from-ink normal is (T.y, -T.x) on a counter-clockwise contour and the
  negative on a clockwise one - but a counter is deliberately wound opposite
  to its outer contour, so asking each contour about its own winding gives the
  counter a normal pointing into the ink. The outer wall of an `o` then
  thickens by d while its counter thins the same wall by d, cancelling
  exactly: the filter silently does nothing to o d b p q while working
  perfectly on n and c, which have no counter. The sign is taken once per
  glyph, from the largest contour.

* **Overlaps.** Pushing points outward makes the joins self-intersect. The
  result is passed through skia-pathops afterwards, without which the
  rasteriser fills the crossings black.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import removeOverlaps


@dataclass
class ContrastStats:
    glyphs: int = 0
    points: int = 0
    skipped_composites: int = 0
    depth: float = 0.0

    def report(self) -> str:
        return "\n".join(
            [
                "  contrast filter",
                "  " + "-" * 58,
                f"    depth                {self.depth:.1f} units",
                f"    glyphs filtered      {self.glyphs}",
                f"    points moved         {self.points}",
                f"    composites untouched {self.skipped_composites}"
                " (they inherit from their bases)",
            ]
        )


def _signed_area(points: list[tuple[float, float]]) -> float:
    total = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        total += x0 * y1 - x1 * y0
    return 0.5 * total


def _filter_contour(points: list[tuple[float, float]], depth: float, sign: float):
    """Offset one closed contour. `sign` comes from the glyph, not the contour.

    Deriving the normal's direction from each contour's OWN winding is the
    obvious thing to do and it is wrong. A counter is wound opposite to its
    outer contour on purpose - that is how the non-zero fill rule knows it is
    a hole - so a counter's own "outward" normal points *into* the ink, not
    away from it. Do that and the outer wall of an `o` thickens by d while its
    counter thins the same wall by d: exact cancellation, and the filter
    appears to do nothing on o d b p q while working perfectly on n and c,
    which have no counter.

    One sign per glyph, taken from the largest contour, gives every contour
    the geometrically correct direction precisely because the windings differ.
    """
    n = len(points)
    if n < 3:
        return points

    offsets: list[tuple[float, float]] = []
    for i in range(n):
        px, py = points[(i - 1) % n]
        cx, cy = points[i]
        nx, ny = points[(i + 1) % n]

        tx, ty = nx - px, ny - py
        length = math.hypot(tx, ty)
        if length < 1e-9:
            offsets.append((0.0, 0.0))
            continue
        tx, ty = tx / length, ty / length

        # Away-from-ink normal. `sign` is the glyph's, see the docstring.
        normal_x, normal_y = ty * sign, -tx * sign

        # +1 where the outline runs vertically (a stem), -1 where it runs
        # horizontally (a hairline), smooth in between.
        weight = abs(ty) - abs(tx)

        # Corner damping. At the tip of a serif the outline turns through a
        # sharp angle, the tangent estimate swings between two unrelated
        # directions, and offsetting the point by the full depth throws a
        # spike off the corner. Measuring how sharply the outline turns here
        # and fading the offset out through the turn keeps serifs crisp
        # instead of spiky. Smooth curves are unaffected: their turn per point
        # is small, so the damping factor stays at 1.
        damping = _corner_damping(points, i, n)
        offsets.append(
            (normal_x * depth * weight * damping, normal_y * depth * weight * damping)
        )

    # Smooth the offset FIELD along the contour, not the outline itself.
    #
    # Where a stem meets the serif that caps it, one point wants to move
    # outward (it reads as vertical) and the next inward (it reads as
    # horizontal). Applying those raw leaves a notch in the side of every
    # ascender. Averaging each offset with its neighbours spreads that
    # transition over a few points, which is what a designer's eye does
    # anyway. Smoothing the offsets rather than the positions means the
    # letter's own corners stay as sharp as they were drawn.
    smoothed = []
    for i in range(n):
        (ax, ay) = offsets[(i - 1) % n]
        (bx, by) = offsets[i]
        (cx_, cy_) = offsets[(i + 1) % n]
        smoothed.append((0.25 * ax + 0.5 * bx + 0.25 * cx_,
                         0.25 * ay + 0.5 * by + 0.25 * cy_))

    return [
        (points[i][0] + smoothed[i][0], points[i][1] + smoothed[i][1])
        for i in range(n)
    ]


#: Cosine of the turn angle below which a point counts as a corner. 0.35 is
#: about 70 degrees: gentle enough to leave the shoulder of an `n` alone,
#: sharp enough to catch a serif tip.
CORNER_COS = 0.35


def _corner_damping(points, i: int, n: int) -> float:
    """1 on a smooth run, falling to 0 at a sharp corner."""
    px, py = points[(i - 1) % n]
    cx, cy = points[i]
    nx, ny = points[(i + 1) % n]

    ax, ay = cx - px, cy - py
    bx, by = nx - cx, ny - cy
    la, lb = math.hypot(ax, ay), math.hypot(bx, by)
    if la < 1e-9 or lb < 1e-9:
        return 1.0
    cosine = (ax * bx + ay * by) / (la * lb)
    if cosine >= CORNER_COS:
        return 1.0
    if cosine <= -0.2:
        return 0.0
    return (cosine + 0.2) / (CORNER_COS + 0.2)


def measure_hairline(font: TTFont) -> float:
    """Median hairline across the round lowercase, in font units."""
    from .strokes import hairline  # local import: optional dependency

    values = [hairline(font, ch) for ch in "onbdpqec"]
    values = sorted(v for v in values if v)
    return values[len(values) // 2] if values else 0.0


def apply(
    font: TTFont, ratio: float, *, glyph_names=None, absolute: float | None = None
) -> ContrastStats:
    """Raise stroke contrast. `ratio` is a fraction of the font's own hairline.

    An absolute depth in font units is the wrong knob. The same 9 units that
    make a Regular sharp will close the counters of a Black, whose stems are
    twice as thick and whose counters are correspondingly smaller - measured
    on this family, a fixed depth took one `d` counter from 55 units to 2.8
    and the letter closed up. Scaling the depth to the weight the font
    actually has keeps the effect proportional.
    """
    stats = ContrastStats()
    depth = absolute if absolute is not None else ratio * measure_hairline(font)
    stats.depth = depth
    if depth <= 0:
        return stats

    glyf = font["glyf"]
    names = list(glyph_names or font.getGlyphOrder())

    for name in names:
        glyph = glyf[name]
        if glyph.numberOfContours <= 0:
            if glyph.isComposite():
                stats.skipped_composites += 1
            continue

        coords = glyph.coordinates
        ends = glyph.endPtsOfContours
        contours = []
        start = 0
        for end in ends:
            contours.append([tuple(coords[i]) for i in range(start, end + 1)])
            start = end + 1

        # The largest contour is the outer one; its winding tells us which way
        # is away from the ink, and that answer is then used for every contour
        # in the glyph including the counters.
        outer = max(contours, key=lambda c: abs(_signed_area(c)))
        sign = 1.0 if _signed_area(outer) > 0 else -1.0

        new_points: list[tuple[float, float]] = []
        for contour in contours:
            new_points.extend(_filter_contour(contour, depth, sign))

        for i, (x, y) in enumerate(new_points):
            coords[i] = (x, y)
        coords.toInt()
        stats.glyphs += 1
        stats.points += len(new_points)

    # Pushing points outward makes the joins cross. Without this the counters
    # of a b d g and every serif junction fill in solid.
    removeOverlaps(font, glyphNames=set(names), ignoreErrors=True)

    # Bounds moved, so the left sidebearings stored in hmtx are now stale.
    # A stale lsb makes the shaper place the glyph a few units off its own
    # ink, which is invisible in a proof and wrong everywhere else.
    hmtx = font["hmtx"]
    for name in names:
        glyph = glyf[name]
        glyph.recalcBounds(glyf)
        advance, _ = hmtx[name]
        hmtx[name] = (advance, glyph.xMin if glyph.numberOfContours != 0 else 0)
    return stats
