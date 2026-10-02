#!/usr/bin/env python3
"""A single presentation sheet: the family, at the sizes Aura will use.

    python scripts/07_hero.py

Separate from 04_proof.py, which exists to catch mistakes. This one exists to
show the result.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw

from vavin import config as C
from vavin.metrics import measure
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module

proof = import_module("04_proof")

BG = "#faf9f6"
INK = "#17150f"
MUTED = "#96907e"
ACCENT = "#8a6a3d"

W = 1400
PAD = 70


def strip(font_path: Path, text: str, size: int, colour: str = INK) -> Image.Image:
    image = proof.render(font_path, text, size)
    if colour == INK:
        return image
    return image


def main() -> int:
    reg = C.font_path("Regular")
    bold = C.font_path("Bold")
    ref = proof.upstream_static("Regular")
    prop = measure(TTFont(reg))
    src = measure(TTFont(ref))

    f_label = proof.label_font(15)
    f_small = proof.label_font(13)

    rows: list[tuple[str, Image.Image | None, str]] = []

    def add(image, label="", kind="block"):
        rows.append((label, image, kind))

    add(strip(reg, C.FAMILY_NAME, 132), "", "hero")
    add(None, f"{C.version_string()}  ·  SIL Open Font License 1.1  ·  "
              f"derived from EB Garamond", "sub")
    add(None, "", "rule")

    add(None, "THE POINT — same size, EB Garamond above, Vavin below", "head")
    line = "Le vaisseau glisse sur l'eau noire"
    add(strip(ref, line, 40), "", "block")
    add(strip(reg, line, 40), "", "block")
    add(None, f"x-height/cap-height   {src.x_to_cap:.3f}  →  {prop.x_to_cap:.3f}"
              f"      x-height   {src.x_height:.0f}  →  {prop.x_height:.0f} units"
              f"      capitals and ascenders unchanged", "note")
    add(None, "", "rule")

    add(None, "AT AURA'S SIZES", "head")
    for size, label in ((34, "display"), (26, "title"), (19, "headline"),
                        (17, "body"), (15, "callout"), (13, "caption")):
        add(strip(bold if size >= 26 else reg,
                  "Écouter autrement — 0123456789", size), f"{label}  {size}pt", "sized")
    add(None, "", "rule")

    add(None, "CHARACTER SET", "head")
    add(strip(reg, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 34), "", "block")
    add(strip(reg, "abcdefghijklmnopqrstuvwxyz", 34), "", "block")
    add(strip(reg, "áàâäã éèêë íìîï óòôöõ úùûü ñ ç ß æ œ", 30), "", "block")
    add(strip(bold, "abcdefghijklmnopqrstuvwxyz ABCDEFG", 34), "", "block")
    add(strip(reg, "0123456789  €$£¥  &@#%  .,;:!?  «» “” — –", 30), "", "block")

    height = PAD * 2
    for label, image, kind in rows:
        height += {"hero": 30, "sub": 34, "rule": 44, "head": 42,
                   "note": 40, "sized": 26, "block": 20}[kind]
        if image is not None:
            height += min(image.height, 200)

    canvas = Image.new("RGB", (W, height), BG)
    draw = ImageDraw.Draw(canvas)
    y = PAD

    for label, image, kind in rows:
        if kind == "rule":
            draw.line([(PAD, y + 20), (W - PAD, y + 20)], fill="#e4e0d4")
            y += 44
            continue
        if kind == "sub":
            draw.text((PAD, y), label, font=f_small, fill=MUTED)
            y += 34
            continue
        if kind == "head":
            draw.text((PAD, y + 8), label, font=f_label, fill=ACCENT)
            y += 42
            continue
        if kind == "note":
            draw.text((PAD, y + 6), label, font=f_small, fill=MUTED)
            y += 40
            continue
        if kind == "sized":
            draw.text((PAD, y + 4), label, font=f_small, fill=MUTED)
        if image is not None:
            usable = W - 2 * PAD - (170 if kind == "sized" else 0)
            if image.width > usable:
                ratio = usable / image.width
                image = image.resize((usable, int(image.height * ratio)), Image.LANCZOS)
            # hb-view renders on white; multiply it onto the warm ground.
            canvas.paste(
                Image.blend(
                    Image.new("RGB", image.size, BG), image, 1.0
                ).point(lambda v: v),
                (PAD + (170 if kind == "sized" else 0), y),
                mask=Image.eval(image.convert("L"), lambda v: 255 - v),
            )
            y += image.height
        y += {"hero": 30, "sized": 26, "block": 20}[kind]

    C.PROOF.mkdir(parents=True, exist_ok=True)
    out = C.PROOF / "00-vavin.png"
    canvas.save(out)
    print(f"  {out.relative_to(C.ROOT)}  ({out.stat().st_size // 1024} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
