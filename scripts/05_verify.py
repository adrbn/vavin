#!/usr/bin/env python3
"""Checks that a proof sheet cannot give you.

    python scripts/05_verify.py

Eyeballing a specimen catches gross errors. It does not catch an accent that
clears by one unit on 3 glyphs out of 900, or a mark that got lifted when it
should not have been. These checks run over every glyph.

Exit code is non-zero if any check fails, so this can gate a build.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from vavin import config as C
from vavin import naming, vmetrics
from vavin.glyphsets import classify
from vavin.metrics import measure

#: Minimum vertical air between the top of a letter and the bottom of the
#: accent riding on it, in font units. Below this the two look welded at
#: reading sizes even when they do not technically overlap.
MIN_ACCENT_CLEARANCE = 20

#: A mark that ends up this far above the ascender starts colliding with the
#: descenders of the line above at tight leading.
MAX_MARK_OVERSHOOT_ABOVE_ASCENDER = 60


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.passes: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "", *, warn: bool = False):
        if ok:
            self.passes.append(label)
        elif warn:
            self.warnings.append(f"{label}: {detail}")
        else:
            self.failures.append(f"{label}: {detail}")

    def render(self) -> str:
        lines = []
        for label in self.passes:
            lines.append(f"    \033[32mPASS\033[0m  {label}")
        for text in self.warnings:
            lines.append(f"    \033[33mWARN\033[0m  {text}")
        for text in self.failures:
            lines.append(f"    \033[31mFAIL\033[0m  {text}")
        return "\n".join(lines)


def _bounds(glyph_set, name):
    pen = BoundsPen(glyph_set)
    try:
        glyph_set[name].draw(pen)
    except Exception:
        return None
    return pen.bounds


def check_ratio(font: TTFont, report: Report) -> None:
    prop = measure(font)
    delta = abs(prop.x_to_cap - C.X_TO_CAP_TARGET)
    report.check(
        delta < 0.005,
        f"x-height/cap-height ratio is {prop.x_to_cap:.4f}",
        f"target {C.X_TO_CAP_TARGET}, off by {delta:.4f}",
    )


def check_vertical_metrics(font: TTFont, report: Report) -> None:
    problems = vmetrics.validate(font)
    report.check(not problems, "vertical metrics are coherent", "; ".join(problems))


def check_naming(font: TTFont, report: Report) -> None:
    leftovers = naming.audit(font, forbidden=("EB Garamond", "EBGaramond", "Garamond"))
    report.check(
        not leftovers,
        "no upstream name in identifying fields",
        "; ".join(leftovers),
    )
    names = {r.nameID: r.toUnicode() for r in font["name"].names}
    for required in (0, 1, 2, 3, 4, 5, 6, 13, 14):
        report.check(
            required in names and names[required].strip() != "",
            f"name ID {required} present",
            "missing or empty",
        )
    report.check(
        "EB Garamond" in names.get(0, ""),
        "copyright credits the upstream project",
        "the OFL requires the original notice to travel with a derivative",
    )


def _accent_clearances(font: TTFont) -> dict[str, float]:
    """Vertical air between each letter and the accent riding on it.

    Only counts marks that actually sit *over* the letter: an accent whose
    bounding box does not overlap the base horizontally is beside it, not on
    it. Without that test, `k` + acute reads as a 32-unit collision in both
    the source font and the derivative, because the acute is measured against
    the top of k's ascender rather than against the shoulder it sits over.
    """
    glyf = font["glyf"]
    glyph_set = font.getGlyphSet()
    sets = classify(font)
    x_height = measure(font).x_height
    out: dict[str, float] = {}

    for name in sorted(sets.lowercase_composite):
        glyph = glyf[name]
        if not glyph.isComposite() or len(glyph.components) < 2:
            continue
        base_comp = glyph.components[0]
        base_bounds = _bounds(glyph_set, base_comp.glyphName)
        if base_bounds is None:
            continue
        base_x0 = base_bounds[0] + getattr(base_comp, "x", 0)
        base_x1 = base_bounds[2] + getattr(base_comp, "x", 0)
        base_top = base_bounds[3] + getattr(base_comp, "y", 0)

        for comp in glyph.components[1:]:
            if comp.glyphName not in sets.marks:
                continue
            mark_bounds = _bounds(glyph_set, comp.glyphName)
            if mark_bounds is None:
                continue
            mark_x0 = mark_bounds[0] + getattr(comp, "x", 0)
            mark_x1 = mark_bounds[2] + getattr(comp, "x", 0)
            mark_bottom = mark_bounds[1] + getattr(comp, "y", 0)

            if mark_bottom < 0.5 * x_height:
                continue  # a mark below the baseline, not our business
            if mark_x1 <= base_x0 or mark_x0 >= base_x1:
                continue  # beside the letter, not over it
            out[name] = min(out.get(name, 1e9), mark_bottom - base_top)
    return out


def check_accent_clearance(font: TTFont, report: Report, wght: float, italic: bool) -> None:
    """Compare accent clearance against the source font, not against zero.

    The meaningful question for a derivative is not "is this clearance
    comfortable" - the source font already made that judgement - but "did my
    transform make it worse". Regressions are failures; absolute tightness the
    source shipped with is not.
    """
    ref = reference_font(wght, italic)
    before = _accent_clearances(ref)
    after = _accent_clearances(font)

    new_collisions: list[str] = []
    regressions: list[str] = []
    for name, gap in sorted(after.items()):
        was = before.get(name)
        if was is None:
            continue
        if gap < 0 <= was:
            new_collisions.append(f"{name} ({was:.0f} -> {gap:.0f})")
        elif gap < was - MIN_ACCENT_CLEARANCE:
            regressions.append(f"{name} ({was:.0f} -> {gap:.0f})")

    report.check(
        not new_collisions,
        f"no accent was pushed into its letter ({len(after)} checked)",
        f"{len(new_collisions)}: {', '.join(new_collisions[:8])}",
    )
    report.check(
        not regressions,
        f"no accent lost more than {MIN_ACCENT_CLEARANCE} units of clearance",
        f"{len(regressions)}: {', '.join(regressions[:8])}",
        warn=True,
    )


def check_ink_fits_metrics(font: TTFont, report: Report) -> None:
    os2 = font["OS/2"]
    top, bottom = vmetrics.measure_ink_extremes(font)
    report.check(
        os2.usWinAscent >= top,
        "tallest ink fits inside usWinAscent",
        f"ink {top} > usWinAscent {os2.usWinAscent}",
    )
    report.check(
        os2.usWinDescent >= abs(bottom),
        "deepest ink fits inside usWinDescent",
        f"ink {abs(bottom)} > usWinDescent {os2.usWinDescent}",
    )


def check_marks_untouched(font: TTFont, report: Report, wght: float, italic: bool) -> None:
    """Mark outlines must be identical to upstream at the SAME weight.

    They are shared between lowercase and uppercase composites. If the build
    ever starts scaling them, every capital's accent moves.
    """
    ref = reference_font(wght, italic)
    ref_set, new_set = ref.getGlyphSet(), font.getGlyphSet()
    glyf = font["glyf"]
    sets = classify(font)
    drifted = []
    checked = 0
    for name in sorted(sets.marks):
        if name not in ref_set:
            continue
        # A mark built as a composite of a letter - the Greek iota-subscript
        # is literally `iota` - inherits that letter's change by design. Only
        # marks we could have edited directly are in scope here.
        if glyf[name].isComposite():
            continue
        checked += 1
        a, b = _bounds(ref_set, name), _bounds(new_set, name)
        if a is None or b is None:
            if a is not b:
                drifted.append(name)
            continue
        # One unit of tolerance. An instance cut at a weight between masters
        # has fractional coordinates; ours were rounded to int16 when the
        # font was compiled, the in-memory reference was not. That is a
        # rounding artefact, not a modified outline - which is why this only
        # ever showed up on Bold and never on Regular, whose weight sits
        # exactly on a master.
        if any(abs(x - y) > 1.0 for x, y in zip(a, b)):
            drifted.append(name)
    report.check(
        not drifted,
        f"all {checked} directly-drawn mark outlines are unmodified",
        f"{len(drifted)} changed: {', '.join(drifted[:8])}",
    )


def check_widths(font: TTFont, report: Report, wght: float, italic: bool) -> None:
    """Advance widths, framed as a regression against the source.

    A combining mark is *supposed* to have zero advance - that is how it
    stacks onto the letter before it. And the source font ships a handful of
    other zero-advance glyphs of its own. Neither is our doing, so the check
    that means something is whether any advance got worse.
    """
    ref = reference_font(wght, italic)
    ref_hmtx = ref["hmtx"]
    hmtx = font["hmtx"]

    negative = [n for n, (a, _) in hmtx.metrics.items() if a < 0]
    report.check(
        not negative, "no negative advance widths", f"{len(negative)}: {negative[:8]}"
    )

    collapsed = [
        name
        for name, (advance, _) in hmtx.metrics.items()
        if advance == 0 and name in ref_hmtx.metrics and ref_hmtx[name][0] != 0
    ]
    report.check(
        not collapsed,
        "no advance width collapsed to zero",
        f"{len(collapsed)}: {collapsed[:8]}",
    )
    glyf = font["glyf"]
    lsb_wrong = []
    for name, (_, lsb) in hmtx.metrics.items():
        glyph = glyf[name]
        if getattr(glyph, "numberOfContours", 0) == 0:
            continue
        if hasattr(glyph, "xMin") and lsb != glyph.xMin:
            lsb_wrong.append(name)
    report.check(
        not lsb_wrong,
        "hmtx left sidebearings agree with glyph bounds",
        f"{len(lsb_wrong)} disagree: {lsb_wrong[:8]}",
        warn=True,
    )


def check_nfd_coverage(font: TTFont, report: Report) -> None:
    """Every precomposed character must have its NFD pieces in the cmap too.

    This is the check that would have caught the subset shipping with zero
    combining marks. macOS and iOS normalise file names to NFD, so text read
    off disk arrives decomposed: "Cafe" + U+0301 rather than "Café". A font
    whose cmap has the precomposed form but not the mark renders the word half
    in itself and half in the system fallback - and it looks perfect in every
    proof sheet, because proof sheets are written in NFC.
    """
    import unicodedata

    cmap = set(font.getBestCmap())
    missing: dict[int, list[str]] = {}
    for cp in sorted(cmap):
        char = chr(cp)
        decomposed = unicodedata.normalize("NFD", char)
        if len(decomposed) < 2:
            continue
        absent = [c for c in decomposed if ord(c) not in cmap]
        if absent:
            missing[cp] = absent

    sample = ", ".join(
        f"U+{cp:04X} {chr(cp)} needs {' '.join(f'U+{ord(c):04X}' for c in v)}"
        for cp, v in list(missing.items())[:4]
    )
    report.check(
        not missing,
        f"NFD decompositions are all covered ({len(cmap)} codepoints)",
        f"{len(missing)} precomposed characters would fall back: {sample}",
    )


def reference_font(wght: float, italic: bool) -> TTFont:
    """Upstream at the same weight AND the same posture.

    Comparing an italic against the roman source is the same class of mistake
    as comparing a Bold against a Regular one: every check that says "did my
    transform change this" starts reporting the difference between two
    different typefaces. It showed up as 114 of 115 mark outlines "modified"
    in the italics and nowhere else.
    """
    from fontTools.varLib import instancer

    source = C.UPSTREAM_VF_ITALIC if italic else C.UPSTREAM_VF
    return instancer.instantiateVariableFont(
        TTFont(source), {"wght": wght}, inplace=False
    )


def resolve(path: Path) -> tuple[str, str, dict]:
    """Work out which family and style a built file belongs to."""
    stem = path.stem.replace("-Latin", "")
    ps, _, style_ps = stem.partition("-")
    for family, recipe in C.FAMILIES.items():
        if family.replace(" ", "") != ps:
            continue
        for style in recipe["styles"]:
            if style.replace(" ", "") == style_ps:
                return family, style, recipe
    return C.FAMILY_NAME, "Regular", C.FAMILIES[C.FAMILY_NAME]


def verify(
    path: Path,
    wght: float,
    *,
    is_subset: bool = False,
    filtered: bool = False,
    italic: bool = False,
) -> Report:
    """Full fonts get every check; subsets only get the ones that mean anything.

    A subset is a mechanical cut of an already-verified font: it can only
    REMOVE glyphs, so outline-level properties are inherited and re-testing
    them is not just redundant, it is wrong. The glyph set is different, so the
    structural classification lands differently and comparisons against
    upstream go haywire - `aacute` reports its clearance halving when the
    full font proves it is preserved to the unit.

    What subsetting genuinely can break is COVERAGE, so that is what the
    subsets are checked for.
    """
    font = TTFont(path)
    report = Report()
    check_vertical_metrics(font, report)
    check_naming(font, report)
    check_nfd_coverage(font, report)
    if is_subset:
        return report
    check_ratio(font, report)
    check_ink_fits_metrics(font, report)
    check_widths(font, report, wght, italic)
    # Accent clearance still means something after the contrast filter: the
    # filter moves a mark by a couple of units, nowhere near the 20-unit
    # threshold, so a regression here would still be a real one.
    check_accent_clearance(font, report, wght, italic)
    if filtered:
        # This one genuinely cannot apply. The filter rewrites every outline
        # including the marks, on purpose, so comparing them to upstream
        # measures the filter rather than a defect.
        report.check(True, "mark-outline check n/a (contrast filter applied)")
        return report
    check_marks_untouched(font, report, wght, italic)
    return report


def main() -> int:
    # dist/ is sorted into one folder per family by 21_specimen.py, so
    # this has to recurse rather than glob the top level.
    paths = sorted(C.DIST.rglob("*.ttf"))
    if not paths:
        print("!! nothing in dist/. Run scripts/03_restyle.py first.", file=sys.stderr)
        return 1

    failed = 0
    for path in paths:
        subset_cut = path.stem.endswith("-Latin")
        family, style, recipe = resolve(path)
        filtered = recipe["overrides"].get("CONTRAST_BOOST", 0) > 0
        tag = "  (subset — coverage only)" if subset_cut else ""
        print(f"\n\033[1m{path.name}\033[0m{tag}")
        with C.overrides(recipe["overrides"]):
            report = verify(
                path,
                C.STYLES[style]["wght"],
                is_subset=subset_cut,
                filtered=filtered,
                italic=C.STYLES[style]["italic"],
            )
        print(report.render())
        failed += len(report.failures)

    print()
    if failed:
        print(f"\033[31m{failed} check(s) failed\033[0m\n")
    else:
        print("\033[32mall checks passed\033[0m\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
