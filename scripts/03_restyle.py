#!/usr/bin/env python3
"""Build the Vavin families from upstream EB Garamond.

    python scripts/03_restyle.py                    # everything
    python scripts/03_restyle.py --family Vavin  # one family
    python scripts/03_restyle.py --subset           # also emit Latin-only cuts

Pipeline, per style:

    instantiate  cut a static instance out of the upstream variable font
                 (roman or italic, whichever the style is drawn from)
    classify     decide which glyphs are lowercase, uppercase, marks
    remap        raise the x-height (see remap.py), shearing italics upright
                 first so their slanted stems do not fold
    contrast     display cut only: thin the hairlines, thicken the stems
    positioning  move GPOS base anchors, rescale kerning
    vmetrics     one coherent metric set, shared across the whole family
    naming       purge and rewrite the identity
    verify       re-measure what actually landed on disk
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from vavin import config as C
from vavin import contrast, naming, positioning, transform, vmetrics
from vavin.glyphsets import classify
from vavin.metrics import measure
from vavin.remap import VerticalRemap

#: What an app actually needs. Everything else is weight in the bundle.
#:
#: U+0300-036F, the combining diacritical marks, are NOT optional however
#: obviously "precomposed" your text looks. macOS and iOS normalise file names
#: to NFD, so a track read off disk arrives as "Cafe" + U+0301, not "Café".
#: Without the combining marks in the cmap the text system falls back to the
#: system font for that run and the word renders half in one face and half in
#: another. Leaving them out cost 0 bytes of apparent trouble and broke every
#: accented title; scripts/05_verify.py now fails the build if any precomposed
#: character in the subset lacks its decomposition.
SUBSET_UNICODES = (
    "U+0000-00FF,U+0100-017F,U+0180-024F,"  # Latin + Latin-1 + Ext-A + Ext-B
    "U+0259,U+0292,U+0300-036F,"            # schwa, ezh, combining diacritics
    "U+1E00-1EFF,"                          # Latin Extended Additional, Vietnamese
    "U+2000-206F,U+20A0-20BF,U+2100-214F,"  # punctuation, currency, letterlike
    "U+2190-21BB,U+2212,U+2215,U+FEFF,U+FFFD"
)
SUBSET_FEATURES = (
    "kern,liga,clig,calt,ccmp,mark,mkmk,locl,ordn,frac,onum,lnum,pnum,tnum,"
    "sups,subs,zero,case,dnom,numr,aalt,salt,ss01,ss02,ss03"
)


def banner(text: str) -> None:
    print(f"\n\033[1m{text}\033[0m")


def source_for(spec: dict) -> Path:
    return C.UPSTREAM_VF_ITALIC if spec["italic"] else C.UPSTREAM_VF


def transform_style(family: str, style: str, spec: dict, *, verbose: bool) -> Path:
    """Phase 1: outlines, positioning and widths. Metrics come later.

    Vertical metrics deliberately are NOT set here. They must be identical
    across a whole family, which is only knowable once every style of it has
    been transformed, so they are applied in phase 2.
    """
    print(f"\n  \033[1m{family} {style}\033[0m")

    font = TTFont(source_for(spec))
    font = instancer.instantiateVariableFont(
        font, {"wght": spec["wght"]}, inplace=False, updateFontNames=False
    )
    font.recalcBBoxes = True

    # An italic's stems lean; the remap has to be applied along that lean or
    # they fold. tan of the angle is what the shear needs.
    slant = math.tan(math.radians(-font["post"].italicAngle)) if spec["italic"] else 0.0

    before = measure(font)
    target_x = C.X_TO_CAP_TARGET * before.cap_height * C.CAP_SCALE
    remap = VerticalRemap(
        x_height=before.x_height,
        ascender=before.ascender,
        descender=before.descender,
        x_scale=target_x / before.x_height,
        ascender_scale=C.ASCENDER_SCALE,
        pure_scale_headroom=C.PURE_SCALE_HEADROOM,
        blend_width=C.BLEND_WIDTH,
        terminal_depth=C.TERMINAL_DEPTH,
        blend_at_terminal=C.BLEND_AT_TERMINAL,
        descender_mode=C.DESCENDER_MODE,
        descender_scale=C.DESCENDER_SCALE,
    )
    print(
        f"    source x {before.x_height:.0f} cap {before.cap_height:.0f}"
        f" ratio {before.x_to_cap:.3f}"
        f"  ->  s={remap.s:.4f} k={remap.k:.3f}"
        + (f" slant={math.degrees(math.atan(slant)):.1f}deg" if slant else "")
    )
    if remap.k < C.K_SLOPE_WARN_BELOW:
        print(f"    !! stem compression k={remap.k:.3f} below"
              f" {C.K_SLOPE_WARN_BELOW}: ascender stems are being crushed")

    sets = classify(font)
    stats = transform.apply(
        font,
        sets,
        remap,
        cap_scale=C.CAP_SCALE,
        lc_x_scale=C.LC_X_SCALE,
        uc_x_scale=C.UC_X_SCALE,
        lc_sidebearing_delta=C.LC_SIDEBEARING_DELTA,
        mark_lift_ratio=C.MARK_LIFT_RATIO,
        slant=slant,
    )
    positioning.adjust(
        font,
        sets,
        remap,
        lc_x_scale=C.LC_X_SCALE,
        lc_sidebearing_delta=C.LC_SIDEBEARING_DELTA,
        mark_lift_ratio=C.MARK_LIFT_RATIO,
        base_lifts=stats.base_lifts,
    )
    positioning.scale_legacy_kern(font, C.LC_X_SCALE)

    if C.CONTRAST_BOOST > 0:
        cstats = contrast.apply(font, C.CONTRAST_BOOST)
        print(f"    contrast filter  ratio {C.CONTRAST_BOOST:g}"
              f" -> depth {cstats.depth:.1f}u"
              f"  {cstats.glyphs} glyphs, {cstats.points} points")

    C.BUILD.mkdir(parents=True, exist_ok=True)
    staging = C.BUILD / f"{C.ps_name(style, family)}.stage.ttf"
    font.save(staging)

    after = measure(TTFont(staging))
    delta = abs(after.x_to_cap - C.X_TO_CAP_TARGET)
    print(
        f"    result x {after.x_height:.0f} cap {after.cap_height:.0f}"
        f" ratio {after.x_to_cap:.4f}"
        f"  {'OK' if delta < 0.006 else f'OFF BY {delta:.4f}'}"
    )
    return staging


def finish_family(family: str, staged: dict[str, Path], *, verbose: bool) -> list[Path]:
    """Phase 2: one set of vertical metrics for the family, then identity."""
    fonts = {style: TTFont(path) for style, path in staged.items()}
    for font in fonts.values():
        font.recalcBBoxes = True

    vm = vmetrics.compute_family(list(fonts.values()), line_height_em=C.LINE_HEIGHT_EM)
    upm = next(iter(fonts.values()))["head"].unitsPerEm
    print(f"\n    metrics  hhea {vm.typo_ascender}/{vm.typo_descender}"
          f"  win {vm.win_ascent}/{vm.win_descent}"
          f"  line height {(vm.typo_ascender - vm.typo_descender) / upm:.3f} em"
          f"  (shared by {', '.join(fonts)})")

    C.DIST.mkdir(parents=True, exist_ok=True)
    written = []
    for style, font in fonts.items():
        spec = C.STYLES[style]
        prop = measure(font)
        vmetrics.apply(font, vm, x_height=prop.x_height, cap_height=prop.cap_height)

        leftovers = naming.rename(
            font,
            family=family,
            style=style,
            ps_name=C.ps_name(style, family),
            version=C.version_string(),
            font_revision=C.VERSION_MAJOR + C.VERSION_MINOR / 1000.0,
            copyright_=C.COPYRIGHT,
            description=C.FAMILIES[family]["description"],
            designer=C.DESIGNER,
            designer_url=C.DESIGNER_URL,
            vendor_url=C.PROJECT_URL,
            vendor_id=C.VENDOR_ID,
            weight_class=spec["weight_class"],
            is_bold=spec["bold"],
            is_italic=spec["italic"],
        )
        if leftovers:
            print(f"\n    !! upstream name survived: {leftovers}")
            raise SystemExit(1)

        # The transform changes advance widths, so upstream's value is stale.
        font["OS/2"].recalcAvgCharWidth(font)
        out = C.DIST / f"{C.ps_name(style, family)}.ttf"
        font.save(out)
        problems = vmetrics.validate(TTFont(out))
        flag = "OK" if not problems else "  !! " + "; ".join(problems)
        print(f"    {out.name:<34} {out.stat().st_size // 1024:>4} kB   {flag}")
        written.append(out)
    return written


def make_subset(path: Path) -> Path:
    out = path.with_name(path.stem + "-Latin.ttf")
    subset.main([
        str(path),
        f"--unicodes={SUBSET_UNICODES}",
        f"--layout-features+={SUBSET_FEATURES}",
        "--name-IDs=*",
        "--notdef-outline",
        "--recommended-glyphs",
        f"--output-file={out}",
    ])
    saved = 100 * (1 - out.stat().st_size / path.stat().st_size)
    print(f"    {out.name:<34} {out.stat().st_size // 1024:>4} kB   (-{saved:.0f}%)")
    return out


def build_family(family: str, *, subset_too: bool, verbose: bool) -> list[Path]:
    recipe = C.FAMILIES[family]
    banner(f"=== {family} " + "=" * max(0, 46 - len(family)))
    with C.overrides(recipe["overrides"]):
        staged = {
            style: transform_style(family, style, C.STYLES[style], verbose=verbose)
            for style in recipe["styles"]
        }
        written = finish_family(family, staged, verbose=verbose)
        if subset_too:
            for path in written:
                make_subset(path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--family", action="append", choices=list(C.FAMILIES))
    ap.add_argument("--subset", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    for path in (C.UPSTREAM_VF, C.UPSTREAM_VF_ITALIC):
        if not path.exists():
            print(f"!! upstream missing: {path}\n   run scripts/00_fetch_upstream.sh",
                  file=sys.stderr)
            return 1

    families = args.family or list(C.FAMILIES)
    total = []
    for family in families:
        total += build_family(family, subset_too=args.subset, verbose=not args.quiet)

    banner("done")
    print(f"  {len(total)} fonts across {len(families)} families"
          f" in {C.DIST.relative_to(C.ROOT)}/\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
