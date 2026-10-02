"""Regenerates the README art in docs/assets/, set in Vavin itself.

    make readme-art            (or: .venv/bin/python docs/assets/make_svgs.py)

Every letter is the font's own outline (textpath.py: fontTools pens, HarfBuzz
shaping), because GitHub shows these files through <img>, where webfonts never
load. Motion is SMIL, which plays inside that sandbox; nothing uses scripts.
Every number drawn is measured from the fonts in dist/ when this runs.

Needs the built fonts (`make fonts specimen`) and, for the EB Garamond
comparison, the upstream source (`make upstream`). The Aura captures are the
two JPEGs in readme-src/; `--sources DIR` re-crops them from full-size PNGs
(2-home-raw.png, 6-library-raw.png).

Writes hero.svg, hero-light.svg, card-*.svg, btn-*.svg (with -fr variants).
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from textpath import Defs, Face, text, wrap

OUT = Path(__file__).resolve().parent
SRC = OUT / "readme-src"
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from vavin.metrics import measure  # noqa: E402

# One accent, the rubricator's vermilion of the specimen (oklch 51% .168 32),
# lifted for dark backgrounds. True white and GitHub's dark ground, nothing warm.
DARK = dict(bg="#0D1117", ink="#E6EDF3", muted="#8B949E", rule="#30363D", accent="#E14C2F")
LIGHT = dict(bg="#FFFFFF", ink="#121212", muted="#656D76", rule="#D0D7DE", accent="#B23219")
RUBRIC = LIGHT["accent"]
S = 8  # spacing unit: every gap is a multiple of it

STYLES = [("Vavin", "Regular"), ("Vavin", "Italic"), ("Vavin", "Bold"), ("Vavin", "Bold Italic"),
          ("Vavin Condensed", "Regular"), ("Vavin Condensed", "Italic"), ("Vavin Condensed", "Bold"),
          ("Vavin Display", "Regular"), ("Vavin Display", "Black")]
KEYS = ["r", "i", "b", "bi", "cr", "ci", "cb", "dr", "dk"]


def font_file(family: str, style: str) -> Path:
    base = family.replace(" ", "")
    return ROOT / "dist" / base / "ttf" / f"{base}-{style.replace(' ', '')}.ttf"


def eb_garamond() -> Path:
    path = ROOT / "build" / "EBGaramond-Regular-reference.ttf"  # the same file `make qa` uses
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        vf = TTFont(ROOT / "sources" / "upstream_EBGaramond[wght].ttf")
        instancer.instantiateVariableFont(vf, {"wght": 400}, inplace=False).save(path)
    return path


FACES = {(f, s): Face(font_file(f, s), k) for (f, s), k in zip(STYLES, KEYS)}
EB = Face(eb_garamond(), "e")
FACES[("EB Garamond", "Regular")] = EB
METRICS = {k: measure(face.tt) for k, face in FACES.items()}


def face(family="Vavin", style="Regular") -> Face:
    return FACES[(family, style)]


def ratio(family="Vavin", style="Regular") -> float:
    m = METRICS[(family, style)]
    return m.x_height / m.cap_height


def cap_size(family, style, cap_px) -> float:
    """The font size that gives this face a cap height of `cap_px`."""
    return cap_px / METRICS[(family, style)].cap_height * FACES[(family, style)].upm


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def svg(w, h, body, title, defs: Defs, extra_defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img"><title>{esc(title)}</title><defs>{defs.svg()}{extra_defs}</defs>{body}</svg>\n')


# --- SMIL ----------------------------------------------------------------------------------------------------
EASE = ".45 0 .25 1"


def anim(attr, kf, total, tag="animate", extra=""):
    """kf = [(t, value)] from 0 to total, eased between keys; equal values hold."""
    kf = [kf[0]] + [b for a, b in zip(kf, kf[1:]) if b[0] > a[0]]
    times = ";".join(f"{min(1, t / total):.4f}" for t, _ in kf)
    vals = ";".join(f"{v:g}" if isinstance(v, (int, float)) else str(v) for _, v in kf)
    return (f'<{tag} attributeName="{attr}" values="{vals}" keyTimes="{times}" dur="{total:g}s" '
            f'calcMode="spline" keySplines="{";".join([EASE] * (len(kf) - 1))}" repeatCount="indefinite"{extra}/>')


def steps(values, total, fade):
    """Hold each value for total/n seconds, easing into the next over `fade`; ends where it starts."""
    seg = total / len(values)
    kf = [(0, values[0])]
    for k, v in enumerate(values[1:] + values[:1], start=1):
        kf += [(k * seg - fade, values[k - 1]), (k * seg, v)]
    return kf


def visible(k, n, total, fade):
    """Opacity keyframes for the k-th of n states."""
    return steps([1 if j == k else 0 for j in range(n)], total, fade)


def layer(k, n, total, fade, body):
    if n == 1:
        return body
    op = "" if k == 0 else ' opacity="0"'
    return f'<g{op}>{anim("opacity", visible(k, n, total, fade), total)}{body}</g>'


def line(x1, x2, y, color, width=1.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="M{x1:g} {y:.2f}H{x2:g}" stroke="{color}" stroke-width="{width:g}"{d}/>'


# --- hero ----------------------------------------------------------------------------------------------------
HERO_STATES = [
    ("Vavin", "Regular", "for text, app UI and long reading"),
    ("Vavin", "Italic", "the italic, raised the same way"),
    ("Vavin", "Bold", "for emphasis and short titles"),
    ("Vavin Condensed", "Regular", "for headlines and dense setting"),
    ("Vavin Display", "Black", "for posters, set large"),
    ("EB Garamond", "Regular", "the source, at the same cap height"),
]


def hero(theme):
    c = LIGHT if theme == "light" else DARK
    W, P, T, F = 880, 6 * S, 18.0, 0.7
    word = "Vavin"
    labels = 17 * S  # room for the line labels on the right
    widest = max(face(f, s).width(word, cap_size(f, s, 1)) for f, s, _ in HERO_STATES)
    cap = min(19 * S, (W - 2 * P - labels) / widest)
    top = 7 * S
    base = top + cap
    cap_line = base + 6 * S  # caption baseline
    H = round(cap_line + 5 * S)
    d = Defs()
    n = len(HERO_STATES)
    small = face()

    def label(s, y, color, anchor="end"):
        return text(d, small, s, W - P, y, 13, color, anchor)[0]

    body = f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{2 * S}" fill="{c["bg"]}" stroke="{c["rule"]}"/>'
    body += line(P, W - P, top, c["rule"]) + label("cap-height", top - S, c["muted"])
    body += line(P, W - P, base, c["rule"]) + label("baseline", base - S, c["muted"])

    eb_y = base - ratio("EB Garamond") * cap
    eb_vis = [0 if f == "EB Garamond" else 1 for f, _, _ in HERO_STATES]
    body += (f'<g>{anim("opacity", steps(eb_vis, T, F), T)}{line(P, W - P, eb_y, c["muted"], 1, "3 4")}'
             f'{label("EB Garamond %.3f" % ratio("EB Garamond"), eb_y + 2 * S, c["muted"])}</g>')

    # The x-height line rides to each state's measured x-height; its label changes with it.
    ys = [base - ratio(f, s) * cap for f, s, _ in HERO_STATES]
    track = [(t, f"0 {v - ys[0]:.2f}") for t, v in steps(ys, T, F)]
    xlabels = "".join(layer(k, n, T, F, label(f"x-height {ratio(f, s):.3f}", ys[0] - S, c["accent"]))
                      for k, (f, s, _) in enumerate(HERO_STATES))
    body += (f'<g>{anim("transform", track, T, "animateTransform", " type=\"translate\"")}'
             f'{line(P, W - P, ys[0], c["accent"], 1.5)}{xlabels}</g>')

    for k, (f, s, note) in enumerate(HERO_STATES):
        name = f if f == "EB Garamond" else f"{f} {s}"
        art = text(d, face(f, s), word, P, base, cap_size(f, s, cap), c["ink"])[0]
        art += text(d, small, name, P, cap_line, 2 * S + 2, c["ink"])[0]
        art += text(d, small, note, W - P, cap_line, 15, c["muted"], "end")[0]
        body += layer(k, n, T, F, art)
    return svg(W, H, body, "The word Vavin cycling through Regular, Italic, Bold, Condensed and Display Black, then "
               "EB Garamond, with its x-height line rising from EB Garamond's 0.620 of the cap height to Vavin's 0.719",
               d)


# --- buttons -------------------------------------------------------------------------------------------------
ICONS = {
    "download": "M12 3.5v11.5M7 10.5l5 5 5-5M4.5 20h15",
    "code": "M8 7l-5 5 5 5M16 7l5 5-5 5M14 4.5l-4 15",
    "licence": "M7 3.5h7l4 4V20.5H6V3.5zM14 3.5V8h4M9 12h6M9 16h6",
}
BUTTONS = {  # key: (icon, English, French, primary)
    "download": ("download", "Download", "Télécharger", True),
    "specimen": ("Aa", "Specimen", "Spécimen", False),
    "how": ("code", "How it's made", "Fabrication", False),
    "license": ("licence", "License", "Licence", False),
}


def button(icon, label, primary):
    d = Defs()
    bold = face("Vavin", "Bold")
    size, h = 18, 44
    tw = bold.width(label, size)
    w = round(tw + 7 * S + 4)
    bg, fg, edge, ic = (RUBRIC, "#FFFFFF", RUBRIC, "#FFFFFF") if primary else ("#121212", "#F2F2F2", "#333333",
                                                                              DARK["accent"])
    body = f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{h / 2 - .5}" fill="{bg}" stroke="{edge}"/>'
    if icon in ICONS:
        body += (f'<path transform="translate(17 13) scale(.75)" d="{ICONS[icon]}" fill="none" stroke="{ic}" '
                 f'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')
    else:  # the specimen button's icon is the font itself
        body += text(d, face("Vavin", "Bold Italic"), icon, 26, 28, 20, ic, "middle")[0]
    body += text(d, bold, label, 44, 28, size, fg)[0]
    return svg(w, h, body, label, d)


def kofi(fr):
    """The Support pill, after liveloop's Ko-fi button: a cup and two lines."""
    d = Defs()
    top, sub = ("Offrir un café", "Soutenir sur Ko-fi") if fr else ("Buy me a coffee", "Tip the maker on Ko-fi")
    tw = max(face("Vavin", "Bold").width(top, 19), face().width(sub, 14))
    w, h = round(tw + 10 * S + 4), 64
    cup = ('<g transform="translate(34 34)" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" '
           'stroke-linejoin="round"><path d="M-11 -5H7V4A7 7 0 0 1 0 11H-4A7 7 0 0 1 -11 4Z" fill="#fff" '
           'fill-opacity=".18"/><path d="M7 -2H9.5A3.5 3.5 0 0 1 9.5 5H7"/><path d="M-6 -10.5Q-4 -12.5 -6 -14.5'
           'M-1 -10.5Q1 -12.5 -1 -14.5" stroke-width="2"/></g>')
    body = (f'<rect width="{w}" height="{h}" rx="{h / 2}" fill="{RUBRIC}"/>' + cup
            + text(d, face("Vavin", "Bold"), top, 60, 30, 19, "#fff")[0]
            + text(d, face(), sub, 60, 49, 14, "#fff", extra=' fill-opacity=".9"')[0])
    return svg(w, h, body, f"{top} on Ko-fi", d)


# --- cards (420 × 280, two to a row) -------------------------------------------------------------------------
CW, CH, M = 420, 280, 3 * S
C = DARK


def card(body, title, d: Defs, extra_defs=""):
    clip = f'<clipPath id="cc"><rect width="{CW}" height="{CH}" rx="{2 * S}"/></clipPath>'
    return svg(CW, CH, f'<g clip-path="url(#cc)"><rect width="{CW}" height="{CH}" fill="{C["bg"]}"/>{body}</g>'
                       f'<rect x=".5" y=".5" width="{CW - 1}" height="{CH - 1}" rx="{2 * S - .5}" fill="none" '
                       f'stroke="{C["rule"]}"/>', title, d, clip + extra_defs)


def fades(edge=3 * S):
    """Dissolve scrolling content into the card at its top and bottom."""
    g = (f'<linearGradient id="ft" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["bg"]}"/>'
         f'<stop offset="1" stop-color="{C["bg"]}" stop-opacity="0"/></linearGradient>'
         f'<linearGradient id="fb" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{C["bg"]}"/>'
         f'<stop offset="1" stop-color="{C["bg"]}" stop-opacity="0"/></linearGradient>')
    return g, (f'<rect width="{CW}" height="{edge}" fill="url(#ft)"/>'
               f'<rect y="{CH - edge}" width="{CW}" height="{edge}" fill="url(#fb)"/>')


PANGRAM = "Portez ce vieux whisky au juge blond qui fume"


def card_waterfall():
    d = Defs()
    sizes = [9, 10, 11, 12, 13, 14, 16, 18, 21, 24, 28, 32, 36, 42, 48, 56, 64, 72]
    rows, y = "", 0.0
    for size in sizes:
        y += size * 1.05 + S
        rows += text(d, face(), str(size), M, y, 11, C["accent"])[0]
        rows += text(d, face(), PANGRAM, M + 4 * S, y, size, C["ink"])[0]
    span = y + 2 * S
    speed = 28  # px per second, slow enough to read the small sizes
    T = span / speed
    scroll = anim("transform", [(0, "0 0"), (T, f"0 {-span:.1f}")], T, "animateTransform", ' type="translate"')
    scroll = scroll.replace('calcMode="spline"', 'calcMode="linear"').split(" keySplines")[0] + ' repeatCount="indefinite"/>'
    g, mask = fades(4 * S)
    body = f'<g>{scroll}<g transform="translate(0 {2 * S})">{rows}<g transform="translate(0 {span:.1f})">{rows}</g></g></g>'
    return card(body + mask, f"Waterfall: Vavin Regular from 9 to 72 px", d, g)


def card_xheight():
    d = Defs()
    word = "Bonheur"
    pair = [("Vavin", "Regular"), ("EB Garamond", "Regular")]
    cap = min(10 * S, (CW - 2 * M - 7 * S) / face().width(word, cap_size("Vavin", "Regular", 1)))
    top = (CH - 3 * S - cap) / 2  # centred above the caption
    base = top + cap
    small = face()
    body = line(M, CW - M, top, C["rule"]) + line(M, CW - M, base, C["rule"])
    vy, ey = base - ratio() * cap, base - ratio("EB Garamond") * cap
    body += line(M, CW - M, ey, C["muted"], 1, "3 4") + line(M, CW - M, vy, C["accent"], 1.5)
    body += text(d, small, f"{ratio():.3f}", CW - M, vy - S, 13, C["accent"], "end")[0]
    body += text(d, small, f"{ratio('EB Garamond'):.3f}", CW - M, ey + 2 * S, 13, C["muted"], "end")[0]

    def word_in(f, s, filled):
        size = cap_size(f, s, cap)
        k = size / face(f, s).upm
        paint = (f'fill="{C["ink"]}"' if filled else
                 f'fill="none" stroke="{C["muted"]}" stroke-width="{1.2 / k:.1f}"')
        return text(d, face(f, s), word, M, base, size, extra=" " + paint)[0]

    T, F = 8.0, 0.8
    for k, (front, back) in enumerate([pair, pair[::-1]]):
        art = word_in(*back, False) + word_in(*front, True)
        cap_txt = f"Filled: {front[0]}.  Outline: {back[0]}.  Same cap height."
        art += text(d, small, cap_txt, M, CH - M, 14, C["muted"])[0]
        body += layer(k, 2, T, F, art)
    return card(body, "The same word in Vavin and EB Garamond at the same cap height, one filled and one outlined, "
                      "with both x-heights marked", d)


def card_family():
    d = Defs()
    size, pitch = 22, 26
    T = 10.0
    body = ""
    for k, (f, s) in enumerate(STYLES):
        y = M + 20 + k * pitch
        a, w = text(d, face(f, s), f + " ", M, y, size, C["ink"])
        b = text(d, face(f, s), s, M + w, y, size, C["accent"])[0]
        start = 7.0 + 0.25 * k
        kf = [(0, 1), (6.4, 1), (6.9, 0), (start, 0), (start + 0.5, 1), (T, 1)]
        body += f'<g>{anim("opacity", kf, T)}{a}{b}</g>'
    return card(body, "The nine styles of the three families, each set in itself", d)


DIACRITICS = ["ÉÇĄŚŘŐ", "àêëïûñ", "ąęșțğå"]
LANGUAGES = "français · polski · čeština · magyar · română · türkçe · español"


def card_diacritics():
    d = Defs()
    f = face()
    size, pitch = 46, 8 * S
    cell = (CW - 2 * M) / 6
    step, T = 0.4, 0.4 * 18 + 2.4
    body, i = "", 0
    k = size / f.upm
    for r, row in enumerate(DIACRITICS):
        y = M + 7 * S + r * pitch
        for col, ch in enumerate(row):
            name = f.cmap[ord(ch)]
            parts = f.components(name)
            x = M + col * cell + (cell - f.tt["hmtx"][name][0] * k) / 2
            base, marks = parts[0], parts[1:]
            g = f'<g transform="translate({x:.2f} {y}) scale({k:.5f} {-k:.5f})">'
            g += f'<use href="#{d.ref(f, base[0], base[1], base[2])}" fill="{C["ink"]}"/>'
            t0 = i * step
            glow = anim("fill", [(0, C["ink"]), (t0, C["ink"]), (t0 + .3, C["accent"]), (t0 + 1.6, C["accent"]),
                                 (t0 + 2.0, C["ink"]), (T, C["ink"])], T)
            for m in marks:
                g += f'<use href="#{d.ref(f, *m)}" fill="{C["ink"]}">{glow}</use>'
            body += g + "</g>"
            i += 1
    langs = LANGUAGES
    while face().width(langs, 14) > CW - 2 * M:
        langs = langs.rsplit(" · ", 1)[0]
    body += text(d, face(), langs, M, CH - M, 14, C["muted"])[0]
    return card(body, "Accented letters from seven languages, their accents lighting up one after another", d)


PARAGRAPH = ("Rue Vavin, à Montparnasse, les cafés du carrefour ont vu passer des générations de lecteurs. "
             "Une page se lit à la terrasse comme sur l’écran d’un téléphone : ce qui compte alors, c’est la "
             "hauteur des minuscules. Plus l’œil est grand, plus la lettre reste nette quand le corps diminue, "
             "et plus la ligne se lit sans effort, même à quatorze pixels. "
             "Le reste tient au dessin : des empattements fermes, un contraste mesuré, des approches régulières.")


def card_paragraph():
    d = Defs()
    size, lead = 14, 20
    T, F = 9.0, 0.8
    body = ""
    for k, (f, s) in enumerate([("Vavin", "Regular"), ("EB Garamond", "Regular")]):
        art = ""
        for j, ln in enumerate(wrap(face(f, s), PARAGRAPH, size, CW - 2 * M)):
            art += text(d, face(f, s), ln, M, M + 2 * S + j * lead, size, C["ink"])[0]
        a, w = text(d, face(), f, M, CH - M, 15, C["accent"])
        art += a + text(d, face(), "  14 px on 20 px, same measure", M + w, CH - M, 15, C["muted"])[0]
        body += layer(k, 2, T, F, art)
    return card(body, "A French paragraph at 14 on 20 px, alternating between Vavin and EB Garamond", d)


def jpeg(path):
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def card_aura():
    d = Defs()
    sw, bezel, r = 232, 8, 30
    sh = CH  # the phone runs off the bottom of the card
    x, y = (CW - sw - 2 * bezel) / 2, 3 * S
    shots = [jpeg(SRC / "aura-home.jpg"), jpeg(SRC / "aura-library.jpg")]
    ih = sw * 489 / 464
    screen = "".join(layer(k, 2, 8.0, 0.9, f'<image href="{u}" width="{sw}" height="{ih:.1f}"/>')
                     for k, u in enumerate(shots))
    island = f'<rect x="{sw / 2 - 36}" y="10" width="72" height="21" rx="10.5" fill="#000"/>'
    body = (f'<rect x="{x}" y="{y}" width="{sw + 2 * bezel}" height="{sh}" rx="{r + bezel}" fill="#2C2C2F" '
            f'stroke="#4A4A4E"/>'
            f'<g transform="translate({x + bezel} {y + bezel})"><g clip-path="url(#scr)">'
            f'<rect width="{sw}" height="{sh}" fill="#000"/>{screen}{island}</g></g>')
    return card(body, "Aura on an iPhone: the Home and Library titles set in Vavin Condensed, real captures", d,
                f'<clipPath id="scr"><rect width="{sw}" height="{sh}" rx="{r}"/></clipPath>')


def make_sources(src: Path):
    from PIL import Image
    for name, out in (("2-home-raw.png", "aura-home.jpg"), ("6-library-raw.png", "aura-library.jpg")):
        im = Image.open(src / name).convert("RGB").crop((0, 0, 1206, 1270)).resize((464, 489), Image.LANCZOS)
        im.save(SRC / out, quality=80, optimize=True, progressive=True)


def main():
    if "--sources" in sys.argv:
        make_sources(Path(sys.argv[sys.argv.index("--sources") + 1]).expanduser())
    files = {
        "hero.svg": hero("dark"), "hero-light.svg": hero("light"),
        "card-waterfall.svg": card_waterfall(), "card-xheight.svg": card_xheight(),
        "card-family.svg": card_family(), "card-diacritics.svg": card_diacritics(),
        "card-paragraph.svg": card_paragraph(), "card-aura.svg": card_aura(),
        "btn-kofi.svg": kofi(False), "btn-kofi-fr.svg": kofi(True),
    }
    for key, (icon, en, fr, primary) in BUTTONS.items():
        files[f"btn-{key}.svg"] = button(icon, en, primary)
        files[f"btn-{key}-fr.svg"] = button(icon, fr, primary)
    for name, body in files.items():
        (OUT / name).write_text(body)
        print(f"{name:26} {len(body.encode()) / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
