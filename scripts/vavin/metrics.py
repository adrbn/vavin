"""Measuring a font's real proportions.

Everything here reads *ink*, not declared metadata. OS/2 sxHeight and
sCapHeight are frequently stale or rounded in shipped fonts; the bounding box
of a flat-topped 'x' is the ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

# Probe glyphs are chosen to be *flat-topped*, so their yMax is the height
# itself with no overshoot, and we take the MEDIAN rather than the max so one
# stylistic outlier cannot drag the reading.
#
# Measured on EB Garamond, this matters a lot:
#   T reaches 694 and A 686 against a real cap-height of 653, because their
#   apexes deliberately overshoot. Putting T in this list reports the cap
#   height 6% too high and every derived scale factor is then wrong.
#   Likewise z (416) and u (415) sit above the real x-height of 405.

#: Flat-topped lowercase. x is the definition of the x-height.
XHEIGHT_PROBES = ("x", "v", "w", "y")
#: Flat-topped capitals. Deliberately excludes T, A, Z, F, O, S, C, G.
CAPHEIGHT_PROBES = ("H", "I", "E", "L", "U")
#: Tallest lowercase ascenders. 'l' and 'b' are flat or nearly flat on top.
ASCENDER_PROBES = ("b", "d", "h", "k", "l")
#: Deepest lowercase descenders.
DESCENDER_PROBES = ("p", "q", "y", "g")
#: Round letters, to read the overshoot.
ROUND_LC_PROBES = ("o", "e", "c")
ROUND_UC_PROBES = ("O", "C", "G")


@dataclass
class Proportions:
    """Ink-measured vertical proportions, in font units."""

    upm: int
    x_height: float
    cap_height: float
    ascender: float
    descender: float  # negative
    lc_overshoot: float
    uc_overshoot: float

    # declared metadata, for comparison
    os2_x_height: int | None
    os2_cap_height: int | None
    hhea_ascender: int
    hhea_descender: int
    hhea_line_gap: int
    typo_ascender: int
    typo_descender: int
    typo_line_gap: int
    win_ascent: int
    win_descent: int
    use_typo_metrics: bool

    @property
    def x_to_cap(self) -> float:
        return self.x_height / self.cap_height

    @property
    def x_per_em(self) -> float:
        return self.x_height / self.upm

    @property
    def cap_per_em(self) -> float:
        return self.cap_height / self.upm

    @property
    def asc_per_em(self) -> float:
        return self.ascender / self.upm

    @property
    def desc_per_em(self) -> float:
        return self.descender / self.upm

    @property
    def ink_extent(self) -> float:
        """Total lowercase ink height, ascender top to descender bottom."""
        return self.ascender - self.descender

    def as_dict(self) -> dict:
        d = asdict(self)
        d.update(
            x_to_cap=round(self.x_to_cap, 4),
            x_per_em=round(self.x_per_em, 4),
            cap_per_em=round(self.cap_per_em, 4),
            asc_per_em=round(self.asc_per_em, 4),
            desc_per_em=round(self.desc_per_em, 4),
        )
        return d


def _glyph_bounds(font: TTFont, glyph_set, char: str) -> tuple | None:
    """Bounding box of the glyph that renders `char`, or None."""
    cmap = font.getBestCmap()
    name = cmap.get(ord(char))
    if name is None or name not in glyph_set:
        return None
    pen = BoundsPen(glyph_set)
    glyph_set[name].draw(pen)
    return pen.bounds  # (xMin, yMin, xMax, yMax) or None for blank glyphs


def _median(values: list[float]) -> float:
    vs = sorted(values)
    n = len(vs)
    return vs[n // 2] if n % 2 else 0.5 * (vs[n // 2 - 1] + vs[n // 2])


def _median_top(font: TTFont, glyph_set, chars) -> float | None:
    """Median yMax over the probes - robust to a single overshooting letter."""
    tops = []
    for ch in chars:
        b = _glyph_bounds(font, glyph_set, ch)
        if b:
            tops.append(b[3])
    return _median(tops) if tops else None


def probe_spread(font: TTFont, chars) -> dict[str, float]:
    """Per-probe yMax, so an anomalous glyph is visible rather than averaged in."""
    glyph_set = font.getGlyphSet()
    out = {}
    for ch in chars:
        b = _glyph_bounds(font, glyph_set, ch)
        if b:
            out[ch] = b[3]
    return out


def _max_top(font: TTFont, glyph_set, chars) -> float | None:
    tops = []
    for ch in chars:
        b = _glyph_bounds(font, glyph_set, ch)
        if b:
            tops.append(b[3])
    return max(tops) if tops else None


def _min_bottom(font: TTFont, glyph_set, chars) -> float | None:
    bottoms = []
    for ch in chars:
        b = _glyph_bounds(font, glyph_set, ch)
        if b:
            bottoms.append(b[1])
    return min(bottoms) if bottoms else None


def measure(font: TTFont) -> Proportions:
    """Measure a TTFont. For a variable font this reads the default instance."""
    glyph_set = font.getGlyphSet()
    upm = font["head"].unitsPerEm

    # Median for the two heights that drive every scale factor in the build.
    # Max for the ascender, because b d h k l genuinely align and we want the
    # tallest, and min for the descender for the same reason.
    x_height = _median_top(font, glyph_set, XHEIGHT_PROBES)
    cap_height = _median_top(font, glyph_set, CAPHEIGHT_PROBES)
    ascender = _max_top(font, glyph_set, ASCENDER_PROBES)
    descender = _min_bottom(font, glyph_set, DESCENDER_PROBES)
    round_lc = _max_top(font, glyph_set, ROUND_LC_PROBES)
    round_uc = _max_top(font, glyph_set, ROUND_UC_PROBES)

    missing = [
        n
        for n, v in (
            ("x-height", x_height),
            ("cap-height", cap_height),
            ("ascender", ascender),
            ("descender", descender),
        )
        if v is None
    ]
    if missing:
        raise ValueError(f"could not measure {', '.join(missing)}: probe glyphs absent")

    os2 = font["OS/2"]
    hhea = font["hhea"]

    return Proportions(
        upm=upm,
        x_height=x_height,
        cap_height=cap_height,
        ascender=ascender,
        descender=descender,
        lc_overshoot=(round_lc - x_height) if round_lc else 0.0,
        uc_overshoot=(round_uc - cap_height) if round_uc else 0.0,
        os2_x_height=getattr(os2, "sxHeight", None),
        os2_cap_height=getattr(os2, "sCapHeight", None),
        hhea_ascender=hhea.ascender,
        hhea_descender=hhea.descender,
        hhea_line_gap=hhea.lineGap,
        typo_ascender=os2.sTypoAscender,
        typo_descender=os2.sTypoDescender,
        typo_line_gap=os2.sTypoLineGap,
        win_ascent=os2.usWinAscent,
        win_descent=os2.usWinDescent,
        use_typo_metrics=bool(os2.fsSelection & (1 << 7)),
    )


def format_report(prop: Proportions, title: str) -> str:
    """Human-readable proportions table."""
    u = prop.upm
    pct = lambda v: f"{v / u:>7.4f} em"  # noqa: E731
    lines = [
        f"  {title}",
        f"  {'-' * max(len(title), 58)}",
        f"  units per em          {u}",
        "",
        "  ink-measured",
        f"    x-height            {prop.x_height:>7.0f}  {pct(prop.x_height)}",
        f"    cap-height          {prop.cap_height:>7.0f}  {pct(prop.cap_height)}",
        f"    ascender (bdhkl)    {prop.ascender:>7.0f}  {pct(prop.ascender)}",
        f"    descender (pqyg)    {prop.descender:>7.0f}  {pct(prop.descender)}",
        f"    lowercase overshoot {prop.lc_overshoot:>7.0f}",
        f"    uppercase overshoot {prop.uc_overshoot:>7.0f}",
        "",
        f"    x-height / cap-height   {prop.x_to_cap:.3f}   <-- the number that matters",
        f"    total ink extent        {prop.ink_extent:.0f} ({prop.ink_extent / u:.3f} em)",
        "",
        "  declared metadata",
        f"    OS/2 sxHeight       {prop.os2_x_height}",
        f"    OS/2 sCapHeight     {prop.os2_cap_height}",
        f"    hhea asc/desc/gap   {prop.hhea_ascender} / {prop.hhea_descender} / {prop.hhea_line_gap}",
        f"    typo asc/desc/gap   {prop.typo_ascender} / {prop.typo_descender} / {prop.typo_line_gap}",
        f"    usWinAscent/Descent {prop.win_ascent} / {prop.win_descent}",
        f"    USE_TYPO_METRICS    {prop.use_typo_metrics}",
        "",
        f"    iOS UIFont.lineHeight = {prop.hhea_ascender - prop.hhea_descender + prop.hhea_line_gap}"
        f" units = {(prop.hhea_ascender - prop.hhea_descender + prop.hhea_line_gap) / u:.3f} em",
    ]
    return "\n".join(lines)
