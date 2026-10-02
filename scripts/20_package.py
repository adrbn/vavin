#!/usr/bin/env python3
"""Zip the built fonts for a GitHub release.

    python scripts/20_package.py        # after `make fonts specimen`

Writes release/Vavin-v<major>.<minor>.zip:

    Vavin-v1.0/
      Vavin/ttf/            full character set, for desktop use
      Vavin/app/            Latin subset, for embedding in an app
      Vavin/web/            woff2
      VavinCondensed/...    the same three folders
      VavinDisplay/...
      OFL.txt
      FONTLOG.txt

The licence and the log travel inside the archive because the OFL requires
the licence to accompany every copy of the fonts.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vavin import config as C

RELEASE = C.ROOT / "release"
FOLDERS = {"ttf": "*.ttf", "app": "*-Latin.ttf", "web": "*.woff2"}


def files() -> list[tuple[Path, str]]:
    """(source, path inside the zip) for every file the release carries."""
    name = f"{C.FAMILY_NAME}-v{C.VERSION_MAJOR}.{C.VERSION_MINOR}"
    out = []
    for family, recipe in C.FAMILIES.items():
        folder = family.replace(" ", "")
        for sub, pattern in FOLDERS.items():
            found = sorted((C.DIST / folder / sub).glob(pattern))
            if len(found) != len(recipe["styles"]):
                raise SystemExit(f"!! {folder}/{sub}: {len(found)} files for "
                                 f"{len(recipe['styles'])} styles. Run `make fonts specimen`.")
            out += [(p, f"{name}/{folder}/{sub}/{p.name}") for p in found]
    out += [(C.ROOT / n, f"{name}/{n}") for n in ("OFL.txt", "FONTLOG.txt")]
    return out


def main() -> int:
    items = files()
    RELEASE.mkdir(exist_ok=True)
    target = RELEASE / f"{items[-1][1].split('/')[0]}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for src, arc in items:
            z.write(src, arc)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None and len(z.namelist()) == len(items)
    print(f"  {target.relative_to(C.ROOT)}  {len(items)} files, {target.stat().st_size // 1024} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
