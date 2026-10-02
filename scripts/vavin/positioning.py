"""GPOS surgery: mark anchors and kerning.

Two things break silently when you raise an x-height and forget GPOS.

**Mark anchors.** Precomposed glyphs (`eacute`) are composites and were fixed
in transform.py. But typing `e` + U+0301 composes dynamically through the
`mark` feature, which positions the accent using an anchor stored on the base
glyph. If that anchor stays at the old x-height the accent lands inside the
letter. Vietnamese and any decomposed input hit this immediately.

**Kerning.** Kern values are design distances. Widen the lowercase and they
are proportionally wrong.

Anchor policy: an anchor above 0.8x the source x-height is a *top* anchor and
is lifted by exactly the same amount as the mark components in the composites,
so dynamic and precomposed spellings land identically. Anything lower is a
bottom or side anchor and follows the outline remap, which pins the baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

from fontTools.ttLib import TTFont

from .glyphsets import GlyphSets
from .remap import VerticalRemap


@dataclass
class PositioningStats:
    anchors_moved: int = 0
    kern_values_scaled: int = 0
    lookup_types_seen: tuple = ()

    def report(self) -> str:
        return "\n".join(
            [
                "  positioning (GPOS)",
                "  " + "-" * 58,
                f"    base anchors moved                 {self.anchors_moved}",
                f"    kerning values rescaled            {self.kern_values_scaled}",
                f"    lookup types present               "
                f"{', '.join(str(t) for t in self.lookup_types_seen)}",
            ]
        )


def _iter_subtables(gpos):
    """Yield (lookup_type, subtable), resolving extension lookups."""
    if gpos is None or not hasattr(gpos.table, "LookupList"):
        return
    for lookup in gpos.table.LookupList.Lookup:
        for sub in lookup.SubTable:
            if lookup.LookupType == 9:  # extension positioning
                yield sub.ExtensionLookupType, sub.ExtSubTable
            else:
                yield lookup.LookupType, sub


def _move_anchor(anchor, *, remap, mark_delta, x_height, x_scale, x_shift) -> bool:
    if anchor is None:
        return False
    y = anchor.YCoordinate
    anchor.YCoordinate = int(
        round(y + mark_delta if y >= 0.8 * x_height else remap(y))
    )
    anchor.XCoordinate = int(round(anchor.XCoordinate * x_scale + x_shift))
    return True


def adjust(
    font: TTFont,
    sets: GlyphSets,
    remap: VerticalRemap,
    *,
    lc_x_scale: float,
    lc_sidebearing_delta: float,
    mark_lift_ratio: float,
    base_lifts: dict[str, float] | None = None,
) -> PositioningStats:
    stats = PositioningStats()
    gpos = font.get("GPOS")
    if gpos is None:
        return stats

    lifts = base_lifts or {}
    fallback_delta = remap.x_height_delta
    x_height = remap.x_height
    seen = set()

    def move(anchor, glyph_name):
        if glyph_name not in sets.lowercase:
            return
        # Same per-glyph lift the composites got, so `e` + U+0301 and the
        # precomposed `eacute` put the accent in exactly the same place.
        delta = lifts.get(glyph_name, fallback_delta) * mark_lift_ratio
        if _move_anchor(
            anchor,
            remap=remap,
            mark_delta=delta,
            x_height=x_height,
            x_scale=lc_x_scale,
            x_shift=lc_sidebearing_delta,
        ):
            stats.anchors_moved += 1

    for ltype, sub in _iter_subtables(gpos):
        seen.add(ltype)

        # --- 4: mark-to-base. Move the BASE anchors only; the mark glyphs
        #        themselves are never touched anywhere in this pipeline.
        if ltype == 4 and getattr(sub, "BaseArray", None) is not None:
            glyphs = sub.BaseCoverage.glyphs
            for rec, name in zip(sub.BaseArray.BaseRecord, glyphs):
                for anchor in rec.BaseAnchor:
                    move(anchor, name)

        # --- 5: mark-to-ligature
        elif ltype == 5 and getattr(sub, "LigatureArray", None) is not None:
            glyphs = sub.LigatureCoverage.glyphs
            for attach, name in zip(sub.LigatureArray.LigatureAttach, glyphs):
                for comp in attach.ComponentRecord:
                    for anchor in comp.LigatureAnchor:
                        move(anchor, name)

        # --- 3: cursive attachment
        elif ltype == 3 and getattr(sub, "EntryExitRecord", None) is not None:
            glyphs = sub.Coverage.glyphs
            for rec, name in zip(sub.EntryExitRecord, glyphs):
                move(rec.EntryAnchor, name)
                move(rec.ExitAnchor, name)

        # --- 2: pair positioning, i.e. kerning
        elif ltype == 2:
            stats.kern_values_scaled += _scale_pair_pos(sub, lc_x_scale)

        # --- 1: single positioning
        elif ltype == 1:
            stats.kern_values_scaled += _scale_value(
                getattr(sub, "Value", None), lc_x_scale
            )

    stats.lookup_types_seen = tuple(sorted(seen))
    return stats


def _scale_value(value, factor: float) -> int:
    """Scale the horizontal fields of a ValueRecord. Returns how many moved."""
    if value is None:
        return 0
    moved = 0
    for field in ("XAdvance", "XPlacement"):
        current = getattr(value, field, None)
        if current:
            setattr(value, field, int(round(current * factor)))
            moved += 1
    return moved


def _scale_pair_pos(sub, factor: float) -> int:
    moved = 0
    fmt = getattr(sub, "Format", None)
    if fmt == 1 and getattr(sub, "PairSet", None) is not None:
        for pairset in sub.PairSet:
            for rec in pairset.PairValueRecord:
                moved += _scale_value(getattr(rec, "Value1", None), factor)
                moved += _scale_value(getattr(rec, "Value2", None), factor)
    elif fmt == 2 and getattr(sub, "Class1Record", None) is not None:
        for c1 in sub.Class1Record:
            for c2 in c1.Class2Record:
                moved += _scale_value(getattr(c2, "Value1", None), factor)
                moved += _scale_value(getattr(c2, "Value2", None), factor)
    return moved


def scale_legacy_kern(font: TTFont, factor: float) -> int:
    """Some fonts still carry a `kern` table. Keep it consistent with GPOS."""
    if "kern" not in font or factor == 1.0:
        return 0
    moved = 0
    for table in font["kern"].kernTables:
        for pair, value in list(table.kernTable.items()):
            table.kernTable[pair] = int(round(value * factor))
            moved += 1
    return moved
