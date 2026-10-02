#!/usr/bin/env python3
"""Measure the real proportions of any font, and of the upstream source.

Usage:
    python scripts/01_measure.py                    # measure upstream EB Garamond
    python scripts/01_measure.py path/to/font.ttf   # measure anything
    python scripts/01_measure.py a.ttf b.ttf        # measure several, side by side

For a variable font, pass --wght to pick an instance (default 400).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from vavin import config
from vavin.metrics import format_report, measure


def load(path: Path, wght: float | None) -> TTFont:
    font = TTFont(path)
    if "fvar" in font and wght is not None:
        axes = {a.axisTag for a in font["fvar"].axes}
        if "wght" in axes:
            font = instancer.instantiateVariableFont(font, {"wght": wght}, inplace=False)
    return font


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="*", type=Path)
    ap.add_argument("--wght", type=float, default=400.0)
    args = ap.parse_args()

    paths = args.fonts or [config.UPSTREAM_VF]

    props = []
    for p in paths:
        if not p.exists():
            print(f"!! not found: {p}", file=sys.stderr)
            return 1
        font = load(p, args.wght)
        prop = measure(font)
        props.append((p, prop))
        label = p.name
        if "fvar" in TTFont(p):
            label += f"  @ wght={args.wght:g}"
        print()
        print(format_report(prop, label))

    print()
    print("  target")
    print("  " + "-" * 58)
    print(f"    X_TO_CAP_TARGET     {config.X_TO_CAP_TARGET:.3f}  (config.py)")
    for p, prop in props:
        need = config.X_TO_CAP_TARGET * prop.cap_height * config.CAP_SCALE
        s = need / prop.x_height
        print(
            f"    {p.name[:36]:<36}  x-height {prop.x_height:.0f} -> {need:.0f}"
            f"   scale s = {s:.4f}  ({(s - 1) * 100:+.1f}%)"
        )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
