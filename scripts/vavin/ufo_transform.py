"""The same x-height transform, applied to UFO sources instead of binaries.

Track A (transform.py) edits a compiled TrueType font. It is fast, it works
today, and it is what ships. But you cannot open a .ttf in a type editor and
fix a curve by hand, and this transform *will* need hand correction.

Track B converts the upstream Glyphs source to UFO, applies the identical
remap, and leaves you with editable masters that fontmake can build. It is the
route to a real typeface rather than a good approximation.

The UFO model is cleaner for this job in two ways:

* Accent placement is expressed as named **anchors** on the glyph (`top`,
  `bottom`), not as GPOS tables that have to be rewritten. Move the `top`
  anchor and both the precomposed glyph and the mark feature follow.
* Components carry a proper affine transformation, so nothing depends on
  guessing whether a composite uses offsets or point matching.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from .remap import VerticalRemap

#: Anchors that ride on top of the letter and must follow the x-height.
TOP_ANCHORS = ("top", "topright", "topleft", "_top", "ogonek_top")
#: Anchors pinned to the baseline or below; these must not move.
BOTTOM_ANCHORS = ("bottom", "_bottom", "bottomright", "bottomleft", "ogonek")


@dataclass
class UFOStats:
    lowercase: int = 0
    uppercase: int = 0
    components_adjusted: int = 0
    anchors_moved: int = 0
    kerning_scaled: int = 0
    skipped: list[str] = field(default_factory=list)

    def report(self) -> str:
        return "\n".join(
            [
                "  UFO transform",
                "  " + "-" * 58,
                f"    lowercase glyphs remapped   {self.lowercase}",
                f"    uppercase glyphs scaled     {self.uppercase}",
                f"    component offsets adjusted  {self.components_adjusted}",
                f"    anchors moved               {self.anchors_moved}",
                f"    kerning pairs rescaled      {self.kerning_scaled}",
            ]
        )


def classify_ufo(font) -> tuple[set[str], set[str], set[str]]:
    """(lowercase, uppercase, marks) by Unicode category, as in glyphsets.py."""
    lower, upper, marks = set(), set(), set()
    for glyph in font:
        for cp in glyph.unicodes or ():
            try:
                category = unicodedata.category(chr(cp))
            except ValueError:
                continue
            if category == "Ll":
                lower.add(glyph.name)
            elif category in ("Lu", "Lt"):
                upper.add(glyph.name)
            elif category in ("Mn", "Mc", "Me", "Sk"):
                marks.add(glyph.name)
    # A glyph that carries a `_top` anchor is a mark by construction: that is
    # how a UFO says "this attaches to something above".
    for glyph in font:
        if any(a.name and a.name.startswith("_") for a in glyph.anchors):
            marks.add(glyph.name)
    lower -= marks
    upper -= marks
    return lower, upper, marks


def glyph_bounds(font, glyph):
    """Bounds of a glyph across UFO libraries.

    defcon exposes `glyph.bounds`; ufoLib2 needs `glyph.getBounds(layer)`
    because a composite cannot be measured without the layer to resolve its
    components against. Supporting both keeps this usable from either.
    """
    bounds = getattr(glyph, "bounds", None)
    if bounds is not None:
        return bounds
    getter = getattr(glyph, "getBounds", None)
    if getter is None:
        return None
    try:
        return getter(font.layers.defaultLayer)
    except TypeError:
        return getter()


def _ink_top(font, glyph) -> float | None:
    bounds = glyph_bounds(font, glyph)
    return None if bounds is None else bounds[3]


def apply_to_ufo(
    font,
    remap: VerticalRemap,
    *,
    cap_scale: float,
    lc_x_scale: float,
    uc_x_scale: float,
    lc_sidebearing_delta: float,
    mark_lift_ratio: float,
) -> UFOStats:
    """Transform one UFO master in place."""
    stats = UFOStats()
    lower, upper, marks = classify_ufo(font)

    tops_before = {}
    for name in lower | upper:
        top = _ink_top(font, font[name])
        if top is not None:
            tops_before[name] = top

    # --- outlines ---------------------------------------------------------
    for name in sorted(lower):
        _transform_glyph(
            font[name],
            remap=remap,
            y_scale=None,
            x_scale=lc_x_scale,
            x_shift=lc_sidebearing_delta,
        )
        font[name].width = font[name].width * lc_x_scale + 2 * lc_sidebearing_delta
        stats.lowercase += 1

    if cap_scale != 1.0 or uc_x_scale != 1.0:
        for name in sorted(upper):
            _transform_glyph(
                font[name],
                remap=None,
                y_scale=cap_scale,
                x_scale=uc_x_scale,
                x_shift=0.0,
            )
            font[name].width = font[name].width * uc_x_scale
            stats.uppercase += 1

    # --- anchors and components ------------------------------------------
    for name in sorted(lower):
        glyph = font[name]
        before = tops_before.get(name)
        after = _ink_top(font, glyph)
        lift = 0.0 if before is None or after is None else (after - before)
        lift *= mark_lift_ratio

        for anchor in glyph.anchors:
            if anchor.name in TOP_ANCHORS or (anchor.name or "").startswith("top"):
                anchor.y += lift
                anchor.x = anchor.x * lc_x_scale + lc_sidebearing_delta
                stats.anchors_moved += 1
            elif anchor.name in BOTTOM_ANCHORS:
                anchor.y = remap(anchor.y)
                anchor.x = anchor.x * lc_x_scale + lc_sidebearing_delta
                stats.anchors_moved += 1

        for component in glyph.components:
            if component.baseGlyph in marks:
                x, y = component.transformation[4], component.transformation[5]
                component.transformation = (
                    *component.transformation[:4],
                    x * lc_x_scale + lc_sidebearing_delta,
                    y + lift,
                )
                stats.components_adjusted += 1

    # --- kerning ----------------------------------------------------------
    if lc_x_scale != 1.0:
        font.kerning.update(
            {pair: round(value * lc_x_scale) for pair, value in font.kerning.items()}
        )
        stats.kerning_scaled = len(font.kerning)

    # --- font-level metrics ----------------------------------------------
    info = font.info
    if info.xHeight:
        info.xHeight = round(remap(info.xHeight))
    if info.capHeight:
        info.capHeight = round(info.capHeight * cap_scale)

    return stats


def _transform_glyph(glyph, *, remap, y_scale, x_scale, x_shift) -> None:
    """Rewrite one glyph's outline. Components are handled by the caller."""
    for contour in glyph:
        for point in contour:
            point.y = remap(point.y) if remap is not None else point.y * y_scale
            point.x = point.x * x_scale + x_shift
