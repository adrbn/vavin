#!/usr/bin/env python3
"""Visual proofs. Numbers are not evidence; a rendered line is.

    python scripts/04_proof.py              # all proofs into proof/
    python scripts/04_proof.py --open       # and open them

Produces:
    proof/01-comparison.png   upstream vs Vavin, same point size
    proof/02-waterfall.png    8 to 16 pt, the sizes that actually matter
    proof/03-normalised.png   both scaled to the SAME x-height, so the
                              comparison is about shape, not size
    proof/04-diacritics.png   the accents and the Vietnamese stacks, which
                              are what silently break when you move a x-height
    proof/specimen.html       for looking at it in a browser
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw, ImageFont

from vavin import config as C
from vavin.metrics import measure
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

LABEL_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Menlo.ttc",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
)

SPECIMEN_TEXT = (
    "Le vaisseau glisse sur l'eau noire, et la ville s'endort derriere lui."
)
PANGRAM = "Portez ce vieux whisky au juge blond qui fume"
ALPHABET_LC = "abcdefghijklmnopqrstuvwxyz"
ALPHABET_UC = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIACRITICS = "aeiou aeiou aeiou AEIOU  ete ou naitre  Nguyen Tien Dung  aaaaa"
DIACRITICS_REAL = (
    "éèêë áàâäã "
    "íìîï óòôöõ "
    "úùûü ç ñ ÉÀÊÔ "
    "ệểậu đống"
)

PARAGRAPH = (
    "Il y a dans toute typographie de labeur une tension entre ce qui se voit "
    "et ce qui se lit. Une lettre trop presente arrete l'oeil; une lettre trop "
    "discrete le laisse glisser sans prise. La hauteur d'x est le reglage "
    "principal de cette tension: elle decide de la quantite d'encre que le "
    "lecteur rencontre a chaque mot, et donc de la vitesse a laquelle il "
    "avance sans s'en rendre compte."
)


def label_font(size: int) -> ImageFont.FreeTypeFont:
    for path in LABEL_FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def render(
    font_path: Path,
    text: str,
    size: int,
    *,
    features: str | None = None,
    line_space: int = 0,
) -> Image.Image:
    """Shape and rasterise one block of text with HarfBuzz."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        out = Path(tmp.name)
    cmd = [
        "hb-view",
        f"--font-file={font_path}",
        f"--font-size={size}",
        "--output-format=png",
        f"--output-file={out}",
        "--margin=0",
        f"--line-space={line_space}",
        "--background=ffffff",
        "--foreground=111111",
    ]
    if features:
        cmd.append(f"--features={features}")
    cmd.append(text)
    subprocess.run(cmd, check=True, capture_output=True)
    image = Image.open(out).convert("RGB")
    out.unlink(missing_ok=True)
    return image


class Sheet:
    """A vertically stacked proof sheet with captions."""

    WIDTH = 1500
    PAD = 40

    def __init__(self, title: str, subtitle: str = "") -> None:
        self.rows: list[tuple[str, Image.Image | None, str]] = []
        self.title = title
        self.subtitle = subtitle

    def caption(self, text: str) -> None:
        self.rows.append((text, None, "caption"))

    def block(self, text: str, image: Image.Image) -> None:
        self.rows.append((text, image, "block"))

    def rule(self) -> None:
        self.rows.append(("", None, "rule"))

    def save(self, path: Path) -> Path:
        f_title = label_font(30)
        f_sub = label_font(16)
        f_cap = label_font(17)

        height = self.PAD * 2 + 46 + (26 if self.subtitle else 0)
        for text, image, kind in self.rows:
            if kind == "caption":
                height += 40
            elif kind == "rule":
                height += 26
            else:
                height += image.height + 34

        canvas = Image.new("RGB", (self.WIDTH, height), "white")
        draw = ImageDraw.Draw(canvas)
        y = self.PAD
        draw.text((self.PAD, y), self.title, font=f_title, fill="#111111")
        y += 40
        if self.subtitle:
            draw.text((self.PAD, y), self.subtitle, font=f_sub, fill="#888888")
            y += 26
        y += 12

        for text, image, kind in self.rows:
            if kind == "caption":
                draw.text((self.PAD, y + 10), text, font=f_cap, fill="#4a7ab8")
                y += 40
            elif kind == "rule":
                draw.line(
                    [(self.PAD, y + 12), (self.WIDTH - self.PAD, y + 12)],
                    fill="#dddddd",
                )
                y += 26
            else:
                if text:
                    draw.text((self.PAD, y), text, font=f_cap, fill="#999999")
                    y += 24
                usable = self.WIDTH - 2 * self.PAD
                if image.width > usable:
                    ratio = usable / image.width
                    image = image.resize(
                        (usable, int(image.height * ratio)), Image.LANCZOS
                    )
                canvas.paste(image, (self.PAD, y))
                y += image.height + 10

        # The height estimate above is deliberately generous - hb-view's
        # output height is not knowable before it runs. Crop the slack off
        # rather than shipping a sheet that is half empty.
        canvas = canvas.crop((0, 0, self.WIDTH, min(height, y + self.PAD)))

        path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(path)
        return path


def upstream_static(style: str) -> Path:
    """Cut a static instance of upstream EB Garamond to compare against."""
    C.BUILD.mkdir(parents=True, exist_ok=True)
    out = C.BUILD / f"EBGaramond-{style}-reference.ttf"
    if out.exists():
        return out
    font = instancer.instantiateVariableFont(
        TTFont(C.UPSTREAM_VF), {"wght": C.STYLES[style]["wght"]}, inplace=False
    )
    font.save(out)
    return out


def proof_comparison(ref: Path, new: Path) -> Path:
    sheet = Sheet(
        "1 - Same point size, side by side",
        "The whole point of the exercise: at an identical size, the larger "
        "x-height puts more ink on the line and reads bigger.",
    )
    for size in (13, 20, 34):
        sheet.caption(f"{size} px")
        sheet.block("EB Garamond (source)", render(ref, SPECIMEN_TEXT, size))
        sheet.block(f"{C.FAMILY_NAME} (result)", render(new, SPECIMEN_TEXT, size))
        sheet.rule()
    return sheet.save(C.PROOF / "01-comparison.png")


def proof_waterfall(ref: Path, new: Path) -> Path:
    sheet = Sheet(
        "2 - Waterfall at reading sizes",
        "9 to 17 px is where a text face is judged. If the large x-height is "
        "worth anything, this is where it shows.",
    )
    for size in (9, 10, 11, 12, 13, 15, 17):
        sheet.caption(f"{size} px")
        sheet.block("", render(ref, PANGRAM, size))
        sheet.block("", render(new, PANGRAM, size))
    return sheet.save(C.PROOF / "02-waterfall.png")


def proof_normalised(ref: Path, new: Path) -> Path:
    """Scale both to the same x-height so the comparison is about shape."""
    ref_prop = measure(TTFont(ref))
    new_prop = measure(TTFont(new))
    base = 60
    ref_size = base
    new_size = int(round(base * ref_prop.x_height / new_prop.x_height))

    sheet = Sheet(
        "3 - Normalised to the same x-height",
        f"EB Garamond at {ref_size}px vs {C.FAMILY_NAME} at {new_size}px, so "
        "both have identical x-heights. What is left is the real change: "
        "shorter ascenders and descenders relative to the body, wider "
        "lowercase, slightly lower stroke contrast.",
    )
    for text in (ALPHABET_LC, "bdhklfit pqyjg", ALPHABET_UC):
        sheet.block("EB Garamond", render(ref, text, ref_size))
        sheet.block(C.FAMILY_NAME, render(new, text, new_size))
        sheet.rule()
    return sheet.save(C.PROOF / "03-normalised.png")


def proof_diacritics(ref: Path, new: Path) -> Path:
    sheet = Sheet(
        "4 - Diacritics and stacked marks",
        "Raising an x-height without moving the accents is the classic way to "
        "break a font silently. Accents must clear the taller letters, and "
        "marks below the baseline must NOT have moved at all.",
    )
    for size in (22, 40):
        sheet.caption(f"{size} px - precomposed")
        sheet.block("EB Garamond", render(ref, DIACRITICS_REAL, size))
        sheet.block(C.FAMILY_NAME, render(new, DIACRITICS_REAL, size))
        sheet.rule()
    # Decomposed input exercises the GPOS mark anchors instead of the
    # precomposed composite glyphs - a different code path entirely.
    decomposed = "é à ô ü ñ ç ẹ"
    sheet.caption("40 px - decomposed, driven by GPOS mark anchors")
    sheet.block("EB Garamond", render(ref, decomposed, 40))
    sheet.block(C.FAMILY_NAME, render(new, decomposed, 40))
    return sheet.save(C.PROOF / "04-diacritics.png")


def proof_paragraph(ref: Path, new: Path, bold: Path) -> Path:
    sheet = Sheet(
        "5 - A paragraph, which is the only real test",
        "Set at 15px with the font's own line height.",
    )
    wrapped = _wrap(PARAGRAPH, 78)
    sheet.block("EB Garamond", render(ref, wrapped, 15, line_space=4))
    sheet.rule()
    sheet.block(f"{C.FAMILY_NAME} Regular", render(new, wrapped, 15, line_space=4))
    sheet.rule()
    sheet.block(
        f"{C.FAMILY_NAME} Bold", render(bold, _wrap(PANGRAM, 78), 15, line_space=4)
    )
    return sheet.save(C.PROOF / "05-paragraph.png")


def _wrap(text: str, width: int) -> str:
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return "\n".join(lines)


def write_html(new: Path, bold: Path) -> Path:
    C.PROOF.mkdir(parents=True, exist_ok=True)
    for src in (new, bold):
        shutil.copy(src, C.PROOF / src.name)
    html = f"""<!doctype html>
<meta charset="utf-8">
<title>{C.FAMILY_NAME} specimen</title>
<style>
  @font-face {{ font-family: "{C.FAMILY_NAME}";
    src: url("{new.name}") format("truetype"); font-weight: 400; }}
  @font-face {{ font-family: "{C.FAMILY_NAME}";
    src: url("{bold.name}") format("truetype"); font-weight: 700; }}
  body {{ margin: 0 auto; max-width: 46rem; padding: 4rem 2rem;
         font-family: "{C.FAMILY_NAME}", Georgia, serif;
         color: #16150f; background: #fbfaf7; }}
  h1 {{ font-size: 4rem; font-weight: 400; margin: 0 0 .2em; letter-spacing: -.01em; }}
  .meta {{ font: 400 .8rem/1.6 ui-monospace, Menlo, monospace; color: #8a8577;
          text-transform: uppercase; letter-spacing: .12em; }}
  .waterfall p {{ margin: .35em 0; line-height: 1.25; }}
  hr {{ border: 0; border-top: 1px solid #e2ded2; margin: 3rem 0; }}
  .body {{ font-size: 1.05rem; line-height: 1.55; }}
  .small {{ font-size: .8rem; line-height: 1.5; }}
  b {{ font-weight: 700; }}
</style>
<p class="meta">{C.FAMILY_NAME} &middot; {C.version_string()} &middot; SIL OFL 1.1</p>
<h1>{C.FAMILY_NAME}</h1>
<p class="body">{C.DESCRIPTION}</p>
<hr>
<div class="waterfall">
  <p style="font-size:48px">{PANGRAM}</p>
  <p style="font-size:32px">{PANGRAM}</p>
  <p style="font-size:24px">{PANGRAM}</p>
  <p style="font-size:18px">{PANGRAM}</p>
  <p style="font-size:14px">{PANGRAM}</p>
  <p style="font-size:11px">{PANGRAM}</p>
  <p style="font-size:9px">{PANGRAM}</p>
</div>
<hr>
<p class="body">{PARAGRAPH}</p>
<p class="body"><b>{PARAGRAPH}</b></p>
<hr>
<p class="small">{DIACRITICS_REAL}</p>
<p class="small">{ALPHABET_UC}<br>{ALPHABET_LC}<br>0123456789 &amp;@#$%&euro; .,;:!?</p>
"""
    path = C.PROOF / "specimen.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    if not shutil.which("hb-view"):
        print("!! hb-view not found. brew install harfbuzz", file=sys.stderr)
        return 1

    new = C.font_path("Regular")
    bold = C.font_path("Bold")
    if not new.exists():
        print("!! build first: python scripts/03_restyle.py", file=sys.stderr)
        return 1

    ref = upstream_static("Regular")
    made = [
        proof_comparison(ref, new),
        proof_waterfall(ref, new),
        proof_normalised(ref, new),
        proof_diacritics(ref, new),
        proof_paragraph(ref, new, bold),
        write_html(new, bold),
    ]
    for path in made:
        print(f"  {path.relative_to(C.ROOT)}")
    if args.open:
        subprocess.run(["open", *[str(p) for p in made]], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
