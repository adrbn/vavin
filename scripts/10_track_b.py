#!/usr/bin/env python3
"""Track B: editable UFO sources, built with fontmake.

    python scripts/10_track_b.py --convert   # Glyphs -> UFO + designspace
    python scripts/10_track_b.py --restyle   # apply the x-height transform
    python scripts/10_track_b.py --build     # fontmake -> dist/ufo-build/
    python scripts/10_track_b.py --all

Track A (03_restyle.py) edits the compiled binary and is what ships today.
Track B exists because Track A's output is an approximation that needs a human
to finish it, and you cannot hand-correct a .ttf.

After --restyle you have `build/ufo/Vavin-*.ufo`. Open them in any UFO
editor - RoboFont, Glyphs, FontForge, or the free TruFont - fix the letters
listed under "Known limitations" in README.md, then --build.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vavin import config as C
from vavin.remap import VerticalRemap
from vavin.ufo_transform import apply_to_ufo, glyph_bounds

GLYPHS_SOURCE = C.SOURCES / "upstream_EBGaramond.glyphs"
GLYPHS_URL = (
    "https://raw.githubusercontent.com/octaviopardo/EBGaramond12/"
    "master/sources/EBGaramond.glyphs"
)
UFO_DIR = C.BUILD / "ufo"
UFO_BUILD = C.DIST / "ufo-build"


def banner(text: str) -> None:
    print(f"\n\033[1m{text}\033[0m")


def fetch() -> None:
    if GLYPHS_SOURCE.exists():
        print(f"  already present: {GLYPHS_SOURCE.name}")
        return
    C.SOURCES.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["curl", "-sSfL", "--max-time", "300", GLYPHS_URL, "-o", str(GLYPHS_SOURCE)],
        check=True,
    )
    print(f"  fetched {GLYPHS_SOURCE.name} ({GLYPHS_SOURCE.stat().st_size // 1024} kB)")


def convert() -> Path:
    """Glyphs -> UFO masters + designspace, via glyphsLib."""
    banner("=== converting Glyphs source to UFO ===")
    fetch()
    import glyphsLib

    UFO_DIR.mkdir(parents=True, exist_ok=True)
    for stale in UFO_DIR.glob("*.ufo"):
        shutil.rmtree(stale)

    font = glyphsLib.GSFont(str(GLYPHS_SOURCE))
    # Do NOT pass family_name here. glyphsLib uses it to *select* which
    # instances belong to the family, and the source's instances are all
    # named "EB Garamond", so asking for "Vavin" silently returns a
    # designspace with zero instances and `fontmake -i` then builds nothing.
    # Convert under the original name, rename in restyle().
    designspace = glyphsLib.to_designspace(font)

    path = UFO_DIR / f"{C.FAMILY_NAME_PS}.designspace"
    for source in designspace.sources:
        ufo_path = UFO_DIR / f"{C.FAMILY_NAME_PS}-{source.styleName.replace(' ', '')}.ufo"
        source.font.save(ufo_path, overwrite=True)
        source.path = str(ufo_path)
        source.filename = ufo_path.name
        source.familyName = C.FAMILY_NAME
        print(f"  master  {ufo_path.name}  ({len(source.font)} glyphs)")

    # Keep only the two styles we build, and rename them.
    designspace.instances = [
        inst for inst in designspace.instances if inst.styleName in C.STYLES
    ]
    seen = set()
    unique = []
    for inst in designspace.instances:
        if inst.styleName in seen:
            continue  # the source lists each instance twice
        seen.add(inst.styleName)
        inst.familyName = C.FAMILY_NAME
        inst.filename = f"instance_ufo/{C.ps_name(inst.styleName)}.ufo"
        inst.postScriptFontName = C.ps_name(inst.styleName)
        unique.append(inst)
    designspace.instances = unique
    designspace.write(path)
    print(f"  designspace  {path.name}  ({len(designspace.sources)} masters,"
          f" {len(designspace.instances)} instances)")
    return path


def restyle() -> None:
    """Apply the identical x-height transform to every UFO master."""
    banner("=== applying the x-height transform to the UFO masters ===")
    import ufoLib2

    paths = sorted(UFO_DIR.glob("*.ufo"))
    if not paths:
        print("!! no UFOs. Run --convert first.", file=sys.stderr)
        raise SystemExit(1)

    for path in paths:
        font = ufoLib2.Font.open(path)
        info = font.info

        # Measure from ink, exactly as Track A does, rather than trusting
        # info.xHeight - the Glyphs source declares 400 against a real 405.
        top = lambda n: glyph_bounds(font, font[n])[3]  # noqa: E731
        bottom = lambda n: glyph_bounds(font, font[n])[1]  # noqa: E731
        x_height = top("x")
        cap_height = top("H")
        ascender = max(top(n) for n in ("b", "d", "h", "k", "l"))
        descender = min(bottom(n) for n in ("p", "q", "y", "g"))

        target_x = C.X_TO_CAP_TARGET * cap_height * C.CAP_SCALE
        remap = VerticalRemap(
            x_height=x_height,
            ascender=ascender,
            descender=descender,
            x_scale=target_x / x_height,
            ascender_scale=C.ASCENDER_SCALE,
            pure_scale_headroom=C.PURE_SCALE_HEADROOM,
            blend_width=C.BLEND_WIDTH,
            terminal_depth=C.TERMINAL_DEPTH,
            blend_at_terminal=C.BLEND_AT_TERMINAL,
            descender_mode=C.DESCENDER_MODE,
            descender_scale=C.DESCENDER_SCALE,
        )
        print(f"\n  {path.name}")
        print(f"    x-height {x_height:.0f} -> {remap(x_height):.0f}"
              f"   cap {cap_height:.0f}   s={remap.s:.4f}   k={remap.k:.3f}")

        stats = apply_to_ufo(
            font,
            remap,
            cap_scale=C.CAP_SCALE,
            lc_x_scale=C.LC_X_SCALE,
            uc_x_scale=C.UC_X_SCALE,
            lc_sidebearing_delta=C.LC_SIDEBEARING_DELTA,
            mark_lift_ratio=C.MARK_LIFT_RATIO,
        )
        info.familyName = C.FAMILY_NAME
        info.copyright = C.COPYRIGHT
        info.openTypeNameLicense = (
            "This Font Software is licensed under the SIL Open Font License, "
            "Version 1.1."
        )
        info.openTypeNameLicenseURL = "https://openfontlicense.org"
        info.openTypeOS2Panose = None
        font.save(path, overwrite=True)
        print("    " + stats.report().splitlines()[2].strip())
        print(f"    saved {path.name}")


def build() -> None:
    banner("=== fontmake ===")
    designspace = UFO_DIR / f"{C.FAMILY_NAME_PS}.designspace"
    if not designspace.exists():
        print("!! no designspace. Run --convert --restyle first.", file=sys.stderr)
        raise SystemExit(1)

    UFO_BUILD.mkdir(parents=True, exist_ok=True)
    binary = C.ROOT / ".venv" / "bin" / "fontmake"
    cmd = [
        str(binary) if binary.exists() else "fontmake",
        "-m", str(designspace),
        "-o", "ttf",
        "-i",  # interpolate the named instances
        "--output-dir", str(UFO_BUILD),
        "--verbose", "WARNING",
    ]
    print("  " + " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(
            "\n  !! fontmake failed. This is normal on a first run against a\n"
            "     third-party source: EB Garamond's feature code and glyph set\n"
            "     are large, and fontmake is stricter than the binary route.\n"
            "     Track A in dist/ is unaffected and remains the shipping build.",
            file=sys.stderr,
        )
        raise SystemExit(result.returncode)
    for path in sorted(UFO_BUILD.glob("*.ttf")):
        print(f"  {path.name}  ({path.stat().st_size // 1024} kB)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--convert", action="store_true")
    ap.add_argument("--restyle", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if not any((args.convert, args.restyle, args.build, args.all)):
        ap.print_help()
        return 0
    if args.convert or args.all:
        convert()
    if args.restyle or args.all:
        restyle()
    if args.build or args.all:
        build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
