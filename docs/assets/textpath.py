"""Text to SVG outlines, set in the real fonts.

GitHub shows README images through <img>, where @font-face never loads. So
every word in the README art is the font's own outlines: each glyph is written
once into <defs> as a path in font units, and a line of text is a row of <use>
placed by HarfBuzz (kerning, ligatures and mark positioning from GPOS).

Without uharfbuzz it falls back to plain advance widths, which loses kerning
but keeps the art buildable.
"""

from __future__ import annotations

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

try:
    import uharfbuzz as hb
except ImportError:  # ponytail: no kerning without HarfBuzz; `make setup` installs it
    hb = None


class Face:
    def __init__(self, path, key: str):
        self.key = key  # short, unique per face: becomes the glyph id prefix
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(path)))) if hb else None

    def shape(self, s: str) -> list[tuple[str, int, int, int]]:
        """[(glyph name, x advance, x offset, y offset)] in font units."""
        if not s:
            return []
        if self.hb is None:
            hmtx = self.tt["hmtx"]
            names = [self.cmap.get(ord(c), ".notdef") for c in s]
            return [(n, hmtx[n][0], 0, 0) for n in names]
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf)
        return [(self.order[i.codepoint], p.x_advance, p.x_offset, p.y_offset)
                for i, p in zip(buf.glyph_infos, buf.glyph_positions)]

    def width(self, s: str, size: float) -> float:
        return sum(a for _, a, _, _ in self.shape(s)) * size / self.upm

    def outline(self, name: str, dx: float = 0, dy: float = 0) -> str:
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{round(v, 1):g}")
        self.glyphs[name].draw(TransformPen(pen, (1, 0, 0, 1, dx, dy)) if dx or dy else pen)
        return pen.getCommands()

    def components(self, name: str) -> list[tuple[str, int, int]]:
        """A composite's parts as (glyph, x, y); a plain glyph is its own single part."""
        glyph = self.tt["glyf"][name]
        if not glyph.isComposite():
            return [(name, 0, 0)]
        return [(c.glyphName, c.x, c.y) for c in glyph.components]


class Defs:
    """The glyphs one SVG uses, each written once."""

    def __init__(self):
        self.paths: dict[str, str] = {}

    def ref(self, face: Face, name: str, dx: float = 0, dy: float = 0) -> str | None:
        gid = f"{face.key}{face.order.index(name)}" + (f"_{dx:g}_{dy:g}" if dx or dy else "")
        if gid not in self.paths:
            d = face.outline(name, dx, dy)
            if not d:
                return None  # a space: nothing to draw
            self.paths[gid] = d
        return gid if gid in self.paths else None

    def svg(self) -> str:
        return "".join(f'<path id="{k}" d="{d}"/>' for k, d in self.paths.items())


def uses(defs: Defs, face: Face, s: str) -> tuple[str, int]:
    """The <use> row for `s` in font units, and its advance."""
    out, x = [], 0
    for name, adv, xo, yo in face.shape(s):
        gid = defs.ref(face, name)
        if gid:
            pos = f' x="{x + xo}"' if x + xo else ""
            pos += f' y="{yo}"' if yo else ""
            out.append(f'<use href="#{gid}"{pos}/>')
        x += adv
    return "".join(out), x


def text(defs: Defs, face: Face, s: str, x: float, y: float, size: float,
         fill: str | None = None, anchor: str = "start", extra: str = "") -> tuple[str, float]:
    """`s` set at `size` px with its baseline at y. Returns (svg, width in px)."""
    row, adv = uses(defs, face, s)
    k = size / face.upm
    w = adv * k
    x0 = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
    f = f' fill="{fill}"' if fill else ""
    return (f'<g transform="translate({x0:.2f} {y:.2f}) scale({k:.5f} {-k:.5f})"{f}{extra}>{row}</g>', w)


def wrap(face: Face, s: str, size: float, measure: float) -> list[str]:
    """Greedy line breaking on spaces, measured with the shaped widths."""
    lines, line = [], ""
    for word in s.split():
        trial = f"{line} {word}" if line else word
        if line and face.width(trial, size) > measure:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


if __name__ == "__main__":
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    face = Face(root / "dist/Vavin/ttf/Vavin-Regular.ttf", "r")
    # Kerning must reach the output: "AV" is tighter than A + V.
    plain = sum(face.tt["hmtx"][face.cmap[ord(c)]][0] for c in "AV")
    assert face.hb is None or sum(a for _, a, _, _ in face.shape("AV")) < plain, "no kerning"
    assert face.width("", 10) == 0
    assert wrap(face, "a b c", 10, 1) == ["a", "b", "c"]
    d = Defs()
    svg, w = text(d, face, "Vavin", 0, 0, 100)
    assert w > 0 and svg.count("<use") == 5 and len(d.paths) == 5
    print("textpath ok", "(HarfBuzz)" if face.hb else "(no HarfBuzz)", file=sys.stderr)
