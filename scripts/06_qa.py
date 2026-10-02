#!/usr/bin/env python3
"""Run FontBakery on Vavin AND on upstream, and diff the two.

    python scripts/06_qa.py

A raw FontBakery report on a derived font is close to useless: most of what it
flags was already true of the source. EB Garamond ships with unreachable
glyphs, no ligature carets, no stylistic-set descriptions and a genuinely
incomplete case-mapping for archaic Greek and Latin letters. None of that is
ours to answer for.

What matters is the delta. This runs the same profile against both and reports
only what changed - which is the only list worth acting on.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from vavin import config as C

LINE = re.compile(r"^(?P<font>\S+?):\s+(?P<check>[\w/_]+):\s+(?P<level>FAIL|WARN)\s+\[(?P<codes>[^\]]*)\]")
VENV_BIN = C.ROOT / ".venv" / "bin" / "fontbakery"


def reference(style: str) -> Path:
    """A static cut of upstream at the same weight, to compare against."""
    C.BUILD.mkdir(parents=True, exist_ok=True)
    out = C.BUILD / f"EBGaramond-{style}-reference.ttf"
    if not out.exists():
        font = instancer.instantiateVariableFont(
            TTFont(C.UPSTREAM_VF), {"wght": C.STYLES[style]["wght"]}, inplace=False
        )
        font.save(out)
    return out


def run(paths: list[Path]) -> dict[str, set[str]]:
    """{check_name: {codes}} across all given fonts."""
    binary = str(VENV_BIN) if VENV_BIN.exists() else "fontbakery"
    proc = subprocess.run(
        [
            binary, "check-universal", "--no-progress", "-l", "WARN",
            "-C", "--succinct", *[str(p) for p in paths],
        ],
        capture_output=True,
        text=True,
    )
    found: dict[str, set[str]] = defaultdict(set)
    for line in proc.stdout.splitlines():
        match = LINE.match(line.strip())
        if match:
            found[f"{match['level']} {match['check']}"].update(
                c.strip() for c in match["codes"].split(",") if c.strip()
            )
    return dict(found)


def main() -> int:
    ours = sorted(
        # `make specimen` sorts dist/ into <family>/ttf/, so recurse.
        p for p in C.DIST.rglob(f"{C.FAMILY_NAME_PS}-*.ttf")
        if not p.stem.endswith("-Latin")
    )
    if not ours:
        print("!! build first: python scripts/03_restyle.py", file=sys.stderr)
        return 1

    refs = [reference(style) for style in C.STYLES]

    print("running FontBakery on upstream EB Garamond ...")
    before = run(refs)
    print("running FontBakery on Vavin ...")
    after = run(ours)

    inherited = sorted(set(before) & set(after))
    introduced = sorted(set(after) - set(before))
    fixed = sorted(set(before) - set(after))

    print()
    print("  inherited from EB Garamond - not ours to fix")
    print("  " + "-" * 60)
    for key in inherited:
        print(f"    {key:<42} {', '.join(sorted(after[key]))[:24]}")
    if not inherited:
        print("    (none)")

    print()
    print("  FIXED relative to upstream")
    print("  " + "-" * 60)
    for key in fixed:
        print(f"    {key}")
    if not fixed:
        print("    (none)")

    print()
    print("  INTRODUCED by this build - the only list that matters")
    print("  " + "-" * 60)
    for key in introduced:
        print(f"    \033[31m{key:<42} {', '.join(sorted(after[key]))}\033[0m")
    if not introduced:
        print("    \033[32m(none)\033[0m")

    print()
    return 1 if introduced else 0


if __name__ == "__main__":
    raise SystemExit(main())
