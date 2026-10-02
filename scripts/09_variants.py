#!/usr/bin/env python3
"""Build the same font at several lowercase widths and put them side by side.

    python scripts/09_variants.py

There is a genuine design decision hiding inside LC_X_SCALE, and it cannot be
settled by argument.

Raising the x-height scales the lowercase vertically by s (1.16 here). That
thickens every horizontal stroke by s while the vertical stems keep their
drawn weight, so stroke contrast drops by about 11%. Contrast is most of what
makes a Garamond look like a Garamond.

The fix is not subtle: scale the lowercase horizontally by the *same* factor.
Then it is a uniform scale - zero distortion of any kind, contrast preserved
exactly, the lowercase simply drawn one optical size larger. The cost is
width, and a much wider lowercase against unchanged capitals.

ITC Garamond is famously wide, so the wide end is arguably the more faithful
one. But "arguably" is not a reason to pick a default. This renders the
options at reading size so the choice is made by looking.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.ttLib import TTFont

from vavin import config as C

restyle = __import__("03_restyle")
proof = __import__("04_proof")
strokes = __import__("08_strokes")

VARIANTS = [
    (1.000, "as drawn", "narrowest. Contrast drops most; lowercase looks tight"),
    (1.035, "current default", "a nudge wider; the compromise"),
    (1.080, "wide", "halfway to a uniform scale"),
    (1.160, "uniform scale", "zero distortion, contrast preserved exactly"),
]

SAMPLE = "Le vaisseau glisse sur l'eau noire, et la ville s'endort"
WORD = "hamburgefonstiv"


def build_variant(x_scale: float) -> Path:
    """Build Regular only, at a given lowercase width, into build/variants/."""
    out_dir = C.BUILD / "variants"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"Vavin-x{x_scale:.3f}.ttf"
    if target.exists():
        return target

    original = C.LC_X_SCALE
    original_dist = C.DIST
    try:
        C.LC_X_SCALE = x_scale
        staged = restyle.transform_style("Regular", C.STYLES["Regular"], verbose=False)
        C.DIST = out_dir
        written = restyle.finish_family({"Regular": staged}, verbose=False)
        shutil.move(str(written[0]), target)
    finally:
        C.LC_X_SCALE = original
        C.DIST = original_dist
    return target


def main() -> int:
    ref = proof.upstream_static("Regular")
    sheet = proof.Sheet(
        "Lowercase width — LC_X_SCALE",
        "Raising the x-height thickens horizontals but not stems, so contrast "
        "drops. Scaling the width by the same factor cancels it exactly, at "
        "the cost of a much wider lowercase. Pick by looking.",
    )

    sheet.caption("EB Garamond, for reference")
    sheet.block("", proof.render(ref, SAMPLE, 30))
    sheet.block("", proof.render(ref, WORD, 74))
    sheet.rule()

    rows = []
    for x_scale, label, note in VARIANTS:
        path = build_variant(x_scale)
        font = TTFont(path)
        contrast = []
        for char in "onbdpqec":
            stem = strokes.stem_width(font, char, 470)
            hair = strokes.hairline(font, char)
            if stem and hair and hair < 190:
                contrast.append(stem / hair)
        mean = sum(contrast) / len(contrast) if contrast else 0.0
        width = font["hmtx"]["n"][0]
        # The other cost, and the one that argues against a uniform scale:
        # widening the lowercase thickens its stems, while the capitals are
        # untouched. Too much and the two look like different weights in
        # mixed setting.
        lc_stem = strokes.stem_width(font, "n", 470)
        uc_stem = strokes.cap_stem(font, 653)
        rows.append((x_scale, label, note, mean, width, lc_stem / uc_stem))

        sheet.caption(f"LC_X_SCALE {x_scale:.3f} — {label}. {note}")
        sheet.block("", proof.render(path, SAMPLE, 30))
        sheet.block("", proof.render(path, WORD, 74))
        sheet.rule()

    out = sheet.save(C.PROOF / "06-widths.png")

    ref_font = TTFont(ref)
    ref_contrast = []
    for char in "onbdpqec":
        stem = strokes.stem_width(ref_font, char, 405)
        hair = strokes.hairline(ref_font, char)
        if stem and hair and hair < 165:
            ref_contrast.append(stem / hair)
    ref_mean = sum(ref_contrast) / len(ref_contrast)
    ref_lc = strokes.stem_width(ref_font, "n", 405)
    ref_uc = strokes.cap_stem(ref_font, 653)
    ref_ratio = ref_lc / ref_uc

    print()
    print("  two costs pull in opposite directions:")
    print("    contrast  — how much of the Garamond hairline survives")
    print("    lc/uc stem — lowercase stem weight against the capitals'."
          " Drift here")
    print("                 makes mixed setting look like two weights.")
    print()
    print(f"  {'LC_X_SCALE':>11} {'label':<18} {'contrast':>9} {'vs src':>8}"
          f" {'lc/uc stem':>11} {'vs src':>8} {'n width':>8}")
    print("  " + "-" * 80)
    print(f"  {'—':>11} {'EB Garamond':<18} {ref_mean:>9.2f} {'—':>8}"
          f" {ref_ratio:>11.3f} {'—':>8} {ref_font['hmtx']['n'][0]:>8}")
    for x_scale, label, _, mean, width, ratio in rows:
        print(
            f"  {x_scale:>11.3f} {label:<18} {mean:>9.2f}"
            f" {(mean - ref_mean) / ref_mean * 100:>+7.0f}%"
            f" {ratio:>11.3f} {(ratio - ref_ratio) / ref_ratio * 100:>+7.0f}%"
            f" {width:>8}"
        )
    print()
    print(f"  {out.relative_to(C.ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
