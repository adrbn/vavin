"""Deciding which glyphs get the lowercase treatment.

The classification is driven by Unicode category, not by glyph names, so it
picks up Greek and Cyrillic lowercase for free and cannot be fooled by a
naming convention we did not anticipate.

Two traps this avoids:

* Small capitals must NOT be treated as lowercase. They are cap-height
  objects; scaling them with the lowercase would leave them shorter than the
  letters they sit beside. They are unencoded (`A.sc`, `a.smcp`), so a
  category-driven seed set excludes them automatically - but variants of real
  lowercase glyphs (`a.alt`, `g.ss01`) DO need the treatment, hence the
  suffix walk with an explicit smallcaps blocklist.

* Combining marks must never be scaled. Their outlines are shared between
  lowercase and uppercase composites, so touching `acutecomb` to suit a taller
  x-height would push every capital's accent out of place. They are moved by
  editing the *composite's component offset* instead.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from fontTools.ttLib import TTFont

#: Name suffixes that mark a glyph as a small capital or a size variant rather
#: than a true lowercase variant. This is a first filter only - the real test
#: is geometric, see VARIANT_YMAX_TOLERANCE.
SMALLCAP_SUFFIXES = {
    "sc", "smcp", "c2sc", "small",
    "sups", "subs", "sinf", "numr", "dnom", "ordn",
    "superior", "inferior",
}

#: How far a suffixed variant's top may sit from its base glyph's top and
#: still count as the same vertical class, in font units.
#:
#: Name-based filtering alone is not enough. EB Garamond spells the ordinal
#: superscript `a.sups` as a composite of `a.ordn`, which is itself named as a
#: plain variant of `a`. A suffix blocklist has to anticipate every naming
#: convention; comparing bounding boxes does not. `a` tops out at 414 and
#: `a.ordn` far above it, so the geometric test rejects it whatever it is
#: called - and accepts `a.01`, a genuine stylistic alternate, which tops out
#: at the same height.
VARIANT_YMAX_TOLERANCE = 50

#: Unicode general categories treated as combining/spacing marks.
MARK_CATEGORIES = {"Mn", "Mc", "Me", "Sk"}


@dataclass
class GlyphSets:
    lowercase_simple: set[str] = field(default_factory=set)
    lowercase_composite: set[str] = field(default_factory=set)
    uppercase_simple: set[str] = field(default_factory=set)
    uppercase_composite: set[str] = field(default_factory=set)
    marks: set[str] = field(default_factory=set)
    untouched: set[str] = field(default_factory=set)

    @property
    def lowercase(self) -> set[str]:
        return self.lowercase_simple | self.lowercase_composite

    @property
    def uppercase(self) -> set[str]:
        return self.uppercase_simple | self.uppercase_composite

    def report(self) -> str:
        return "\n".join(
            [
                "  glyph classification",
                "  " + "-" * 58,
                f"    lowercase   {len(self.lowercase):>5}"
                f"   ({len(self.lowercase_simple)} simple,"
                f" {len(self.lowercase_composite)} composite)",
                f"    uppercase   {len(self.uppercase):>5}"
                f"   ({len(self.uppercase_simple)} simple,"
                f" {len(self.uppercase_composite)} composite)",
                f"    marks       {len(self.marks):>5}   (outlines never touched)",
                f"    untouched   {len(self.untouched):>5}"
                f"   (figures, punctuation, symbols, small caps)",
            ]
        )


def _is_smallcap_variant(name: str) -> bool:
    return any(part in SMALLCAP_SUFFIXES for part in name.split(".")[1:])


def _base_name(name: str) -> str:
    return name.split(".")[0]


def _category_seeds(font: TTFont) -> tuple[set[str], set[str], set[str]]:
    """Seed sets straight from the cmap and Unicode categories."""
    lower, upper, marks = set(), set(), set()
    for cp, name in font.getBestCmap().items():
        try:
            cat = unicodedata.category(chr(cp))
        except ValueError:
            continue
        if cat == "Ll":
            lower.add(name)
        elif cat in ("Lu", "Lt"):
            upper.add(name)
        elif cat in MARK_CATEGORIES:
            marks.add(name)
    return lower, upper, marks


def _ymax(glyf, name: str) -> float | None:
    """Top of a glyph's ink, or None for a blank or missing glyph."""
    if name not in glyf:
        return None
    glyph = glyf[name]
    if getattr(glyph, "numberOfContours", 0) == 0:
        return None
    return getattr(glyph, "yMax", None)


def _same_vertical_class(glyf, name: str, base: str) -> bool:
    """Whether a variant sits at the same height as the glyph it derives from."""
    a, b = _ymax(glyf, name), _ymax(glyf, base)
    if a is None or b is None:
        return False
    return abs(a - b) <= VARIANT_YMAX_TOLERANCE


def _resolve_base(glyf, name: str, depth: int = 0) -> str | None:
    """Follow a composite down to the glyph its first component points at."""
    if depth > 8 or name not in glyf:
        return None
    glyph = glyf[name]
    if not glyph.isComposite():
        return name
    if not glyph.components:
        return None
    return _resolve_base(glyf, glyph.components[0].glyphName, depth + 1)


def classify(font: TTFont) -> GlyphSets:
    glyf = font["glyf"]
    order = font.getGlyphOrder()
    lower_seed, upper_seed, mark_seed = _category_seeds(font)

    # Unencoded marks. The `*comb` naming convention catches most of them.
    for name in order:
        if _base_name(name).endswith("comb"):
            mark_seed.add(name)

    # The rest are found structurally: a glyph that is only ever used as a
    # trailing component of a composite, and never as a base, is a mark -
    # whatever it happens to be called.
    used_as_base: set[str] = set()
    used_as_trailing: set[str] = set()
    for name in order:
        glyph = glyf[name]
        if not glyph.isComposite() or not glyph.components:
            continue
        used_as_base.add(glyph.components[0].glyphName)
        for comp in glyph.components[1:]:
            used_as_trailing.add(comp.glyphName)
    for name in used_as_trailing - used_as_base:
        if name not in lower_seed and name not in upper_seed:
            mark_seed.add(name)

    # Mark variants reached only through GSUB - `uni030C.cap` is the flatter
    # caron the `ccmp` feature swaps in over a capital, and never appears as a
    # component of anything. They inherit their base's mark status.
    for name in order:
        if "." in name and _base_name(name) in mark_seed:
            mark_seed.add(name)

    # Suffix walk: a.alt inherits from a, but A.sc inherits from nothing, and
    # a.ordn inherits from nothing because it does not sit at the x-height.
    lower, upper = set(lower_seed), set(upper_seed)
    for name in order:
        if "." not in name or _is_smallcap_variant(name):
            continue
        base = _base_name(name)
        if base not in lower_seed and base not in upper_seed:
            continue
        if not _same_vertical_class(glyf, name, base):
            continue
        (lower if base in lower_seed else upper).add(name)

    marks = {n for n in mark_seed if n in glyf}
    lower -= marks
    upper -= marks

    sets = GlyphSets(marks=marks)
    for name in order:
        if name in marks:
            continue
        glyph = glyf[name]
        composite = glyph.isComposite()
        if name in lower:
            (sets.lowercase_composite if composite else sets.lowercase_simple).add(name)
        elif name in upper:
            (sets.uppercase_composite if composite else sets.uppercase_simple).add(name)
        else:
            sets.untouched.add(name)

    # A composite whose base resolves into the lowercase set belongs there too,
    # even if its own codepoint is not Ll (Vietnamese stacked forms, some
    # Cyrillic). Its marks then need lifting with the x-height.
    for name in list(sets.untouched):
        glyph = glyf[name]
        if not glyph.isComposite():
            continue
        base = _resolve_base(glyf, name)
        if base in sets.lowercase_simple:
            sets.untouched.discard(name)
            sets.lowercase_composite.add(name)
        elif base in sets.uppercase_simple:
            sets.untouched.discard(name)
            sets.uppercase_composite.add(name)

    return sets


def is_mark_component(sets: GlyphSets, glyph_name: str) -> bool:
    return glyph_name in sets.marks
