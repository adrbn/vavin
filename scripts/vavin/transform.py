"""Applying the remap to a static TrueType font.

Order matters. Simple glyphs are transformed first, then composites are
adjusted, then bounds and metrics are recomputed - a composite's bounding box
is derived from its components, so it can only be recalculated once they are
final.

This module only touches `glyf`, `hmtx` and the composite component offsets.
Vertical metrics live in vmetrics.py, GPOS in positioning.py, names in
naming.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont

from .glyphsets import GlyphSets
from .remap import VerticalRemap

def _has_xy_offset(comp) -> bool:
    """Whether a component is positioned by offset rather than point matching.

    Do NOT test the ARGS_ARE_XY_VALUES flag bit here. fontTools does not
    preserve it on decompile - every component in EB Garamond reports
    flags=0x0004 with the bit clear - and recomputes it when compiling. The
    decompiled object carries `.x`/`.y` for offset components and
    `.firstPt`/`.secondPt` for point-matched ones, so that is the real test.
    """
    return hasattr(comp, "x") and not hasattr(comp, "firstPt")


@dataclass
class TransformStats:
    simple_lc: int = 0
    simple_uc: int = 0
    composites_lc: int = 0
    composites_uc: int = 0
    marks_lifted: int = 0
    point_matched_skipped: list[str] = field(default_factory=list)
    scaled_components_skipped: list[str] = field(default_factory=list)
    #: Per-glyph ink-top movement, so GPOS anchors can be moved by exactly the
    #: same amount as the composite components and the two spellings of an
    #: accented letter stay identical.
    base_lifts: dict[str, float] = field(default_factory=dict)

    def report(self) -> str:
        lines = [
            "  outline transform",
            "  " + "-" * 58,
            f"    lowercase simple glyphs remapped   {self.simple_lc}",
            f"    uppercase simple glyphs scaled     {self.simple_uc}",
            f"    lowercase composites adjusted      {self.composites_lc}",
            f"    uppercase composites adjusted      {self.composites_uc}",
            f"    mark components lifted             {self.marks_lifted}",
        ]
        if self.point_matched_skipped:
            lines.append(
                f"    !! point-matched composites skipped: "
                f"{len(self.point_matched_skipped)} "
                f"({', '.join(self.point_matched_skipped[:5])}...)"
            )
        if self.scaled_components_skipped:
            lines.append(
                f"    !! components with a 2x2 transform: "
                f"{len(self.scaled_components_skipped)} "
                f"({', '.join(self.scaled_components_skipped[:5])}...)"
            )
        return "\n".join(lines)


def _transform_simple(
    glyph,
    *,
    remap: VerticalRemap | None,
    y_scale: float,
    x_scale: float,
    x_shift: float,
    slant: float = 0.0,
) -> None:
    """Rewrite a simple glyph's coordinates in place.

    `remap` takes precedence over `y_scale`; pass one or the other.

    `slant` is tan(italic angle) and it is not optional for an italic. An
    upright ascender stem is a vertical line, and compressing y leaves a
    vertical line vertical - that is the whole reason the compression is
    invisible. An italic stem is a line leaning 17.2 degrees, and compressing
    y by k=0.32 without straightening it first takes that lean to 44 degrees:
    the stem visibly folds partway up.

    So the point is sheared upright, remapped, and sheared back by the same
    angle against its NEW height. A slanted straight line stays a slanted
    straight line at its original angle.
    """
    if glyph.numberOfContours <= 0:
        return
    coords = glyph.coordinates
    for i in range(len(coords)):
        x, y = coords[i]
        upright = x - y * slant
        new_y = remap(y) if remap is not None else y * y_scale
        coords[i] = (upright * x_scale + x_shift + new_y * slant, new_y)
    # glyf coordinates are int16. Rounding here rather than letting the
    # compiler choke keeps the error at half a unit on a 1000-unit em, which
    # is an order of magnitude below the rasteriser's resolution at any size
    # a reader will use.
    coords.toInt()


def snapshot_tops(glyf, names) -> dict[str, float]:
    """Record each glyph's ink top before anything is transformed."""
    tops = {}
    for name in names:
        glyph = glyf[name]
        if getattr(glyph, "numberOfContours", 0) != 0:
            top = getattr(glyph, "yMax", None)
            if top is not None:
                tops[name] = top
    return tops


def _is_top_mark(glyf, mark_name: str, x_height: float) -> bool:
    """Whether a mark rides above the letter rather than below it.

    A cedilla, ogonek or Vietnamese dot-below hangs under the baseline and
    must not move when the x-height rises - only the marks sitting on top of
    the letter follow it up.
    """
    if mark_name not in glyf:
        return False
    glyph = glyf[mark_name]
    y_min = getattr(glyph, "yMin", None)
    if y_min is None:
        return False
    return y_min >= 0.5 * x_height


def _base_lift(glyf, tops_before: dict[str, float], base_name: str) -> float:
    """How far the base glyph's ink top actually moved.

    Lifting every accent by one global constant is wrong, because the letters
    do not all move by the same amount: `dotlessi` tops out at the x-height
    and rises 65 units, but the shoulder of `n` overshoots to 430 and rises
    69. Using a constant silently eats the clearance on exactly the letters
    that had the least to spare. Measuring the base glyph's own movement
    preserves each accent's drawn clearance instead.
    """
    before = tops_before.get(base_name)
    if before is None:
        return 0.0
    glyph = glyf[base_name]
    after = getattr(glyph, "yMax", None)
    return 0.0 if after is None else after - before


def _lift_marks(
    glyph,
    *,
    glyf,
    sets: GlyphSets,
    mark_delta: float,
    x_height: float,
    x_scale: float,
    x_shift: float,
    stats: TransformStats,
    name: str,
) -> None:
    """Move the diacritics of a composite without touching their outlines."""
    for index, comp in enumerate(glyph.components):
        if not _has_xy_offset(comp):
            # Args are point indices; the component is anchored to a point on
            # the base glyph, which has already moved with it. Nothing to do,
            # but record it so the build log is honest about what it skipped.
            if name not in stats.point_matched_skipped:
                stats.point_matched_skipped.append(name)
            continue
        if getattr(comp, "transform", None) is not None:
            t = comp.transform
            if t != [[1, 0], [0, 1]] and name not in stats.scaled_components_skipped:
                stats.scaled_components_skipped.append(name)

        is_base = index == 0
        if is_base:
            # The base glyph's own outline already carries the x scale and the
            # sidebearing shift, so its offset must not be shifted again -
            # only scaled, in case it is non-zero (stacked Vietnamese forms).
            comp.x = otRound(comp.x * x_scale)
        else:
            if comp.glyphName in sets.marks and _is_top_mark(
                glyf, comp.glyphName, x_height
            ):
                comp.y = otRound(comp.y + mark_delta)
                stats.marks_lifted += 1
            comp.x = otRound(comp.x * x_scale + x_shift)


def _dependency_order(glyf, names: set[str]) -> list[str]:
    """Composites sorted so a glyph always follows the ones it is built on."""
    order: list[str] = []
    seen: set[str] = set()

    def visit(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        glyph = glyf[name]
        if glyph.isComposite():
            for comp in glyph.components:
                if comp.glyphName in names:
                    visit(comp.glyphName)
        order.append(name)

    for name in sorted(names):
        visit(name)
    return order


def apply(
    font: TTFont,
    sets: GlyphSets,
    remap: VerticalRemap,
    *,
    cap_scale: float,
    lc_x_scale: float,
    uc_x_scale: float,
    lc_sidebearing_delta: float,
    mark_lift_ratio: float,
    slant: float = 0.0,
) -> TransformStats:
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    stats = TransformStats()

    # Snapshot before anything moves, so pass 2 can ask each base glyph how
    # far it actually travelled rather than assuming a single global delta.
    # Composites are included: a Vietnamese stack like `uni1EDB` sits on
    # `ohorn`, which is itself a composite, so its lift is only knowable once
    # `ohorn` has been processed.
    tops_before = snapshot_tops(glyf, font.getGlyphOrder())

    # --- pass 1: simple glyphs -------------------------------------------
    for name in sorted(sets.lowercase_simple):
        _transform_simple(
            glyf[name],
            remap=remap,
            y_scale=1.0,
            x_scale=lc_x_scale,
            x_shift=lc_sidebearing_delta,
            slant=slant,
        )
        stats.simple_lc += 1

    if cap_scale != 1.0 or uc_x_scale != 1.0:
        for name in sorted(sets.uppercase_simple):
            _transform_simple(
                glyf[name],
                remap=None,
                y_scale=cap_scale,
                x_scale=uc_x_scale,
                x_shift=0.0,
                slant=slant,
            )
            stats.simple_uc += 1

    # Bounds must be current before pass 2 can measure how far each base
    # glyph moved.
    for name in sorted(sets.lowercase_simple | sets.uppercase_simple):
        glyf[name].recalcBounds(glyf)
        stats.base_lifts[name] = _base_lift(glyf, tops_before, name)

    # --- pass 2: composites, bases before dependents ----------------------
    do_uppercase = cap_scale != 1.0 or uc_x_scale != 1.0
    todo = set(sets.lowercase_composite)
    if do_uppercase:
        todo |= sets.uppercase_composite

    for name in _dependency_order(glyf, todo):
        glyph = glyf[name]
        base = glyph.components[0].glyphName if glyph.components else None
        is_lower = name in sets.lowercase_composite
        _lift_marks(
            glyph,
            glyf=glyf,
            sets=sets,
            mark_delta=_base_lift(glyf, tops_before, base) * mark_lift_ratio,
            x_height=remap.x_height,
            x_scale=lc_x_scale if is_lower else uc_x_scale,
            x_shift=lc_sidebearing_delta if is_lower else 0.0,
            stats=stats,
            name=name,
        )
        # Recalculate immediately: a composite stacked on this one needs its
        # final top to compute its own lift.
        glyph.recalcBounds(glyf)
        if is_lower:
            stats.composites_lc += 1
        else:
            stats.composites_uc += 1

    # --- pass 3: advance widths ------------------------------------------
    width_delta = 2.0 * lc_sidebearing_delta
    for name in sets.lowercase:
        advance, lsb = hmtx[name]
        hmtx[name] = (int(round(advance * lc_x_scale + width_delta)), lsb)
    if uc_x_scale != 1.0:
        for name in sets.uppercase:
            advance, lsb = hmtx[name]
            hmtx[name] = (int(round(advance * uc_x_scale)), lsb)

    # --- pass 4: bounds and sidebearings, across the WHOLE font -----------
    # Not just the glyphs we classified. A composite we never selected can
    # still inherit a changed outline through a component: the degree-Celsius
    # sign is built on `c`, the Greek iota-subscript on `iota`. Their stored
    # bounds and left sidebearings go stale, and a stale lsb makes the shaper
    # place the glyph a few units off. Recalculating everything in dependency
    # order costs a second and removes the whole class of bug.
    all_names = set(font.getGlyphOrder())
    for name in _dependency_order(glyf, all_names):
        glyf[name].recalcBounds(glyf)

    for name in all_names:
        glyph = glyf[name]
        advance, _ = hmtx[name]
        hmtx[name] = (advance, glyph.xMin if glyph.numberOfContours != 0 else 0)

    return stats
