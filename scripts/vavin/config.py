"""Central configuration for the Vavin typeface build.

Every tunable lives here. Nothing else in the pipeline hardcodes a number.

Vavin is derived from EB Garamond (SIL OFL 1.1, no Reserved Font Name
declared upstream). It is NOT derived from, and shares no outline data with,
ITC Garamond or any other proprietary font. See ../../LEGAL.md.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

FAMILY_NAME = "Vavin"
#: ASCII, no spaces - used to build PostScript names (Vavin-Regular).
FAMILY_NAME_PS = "Vavin"

VERSION_MAJOR = 1
VERSION_MINOR = 0

DESIGNER = "adrbn"
DESIGNER_URL = "https://github.com/adrbn"
PROJECT_URL = "https://github.com/adrbn/vavin"
VENDOR_ID = "AURA"  # 4 chars max, OS/2 achVendID

COPYRIGHT = (
    f"Copyright 2026 adrbn ({PROJECT_URL}). "
    f"Derived from EB Garamond, "
    f"Copyright 2017 The EB Garamond Project Authors "
    f"(https://github.com/octaviopardo/EBGaramond12)."
)

DESCRIPTION = (
    f"{FAMILY_NAME} is an old-style serif with an unusually large x-height, "
    "built for sustained reading at small optical sizes on screen. It is a "
    "modification of EB Garamond, released under the SIL Open Font License."
)

#: Styles we can build. Maps our style name -> the weight coordinate on the
#: upstream variable font's `wght` axis, and which of the two upstream sources
#: (roman or italic) it is cut from.
STYLES = {
    "Regular": dict(wght=400, weight_class=400, bold=False, italic=False),
    "Italic": dict(wght=400, weight_class=400, bold=False, italic=True),
    "Bold": dict(wght=700, weight_class=700, bold=True, italic=False),
    "Bold Italic": dict(wght=700, weight_class=700, bold=True, italic=True),
    "Black": dict(wght=800, weight_class=800, bold=False, italic=False),
}

#: The three families we ship, and the parameters each overrides.
#:
#: They are separate FAMILIES, not styles of one family, and that is not a
#: stylistic choice: an OpenType family can carry only the four RIBBI styles
#: (regular / italic / bold / bold italic) before style linking breaks and
#: applications start synthesising fake bolds. A condensed cut and a display
#: cut each need their own family name.
FAMILIES = {
    "Vavin": dict(
        styles=["Regular", "Italic", "Bold", "Bold Italic"],
        # Raising the x-height thickens the horizontals and not the stems, so
        # stroke contrast falls 7.6% - the one real cost of the whole
        # operation, and the only one of the four "known limitations" that
        # survived being measured. A light pass of the directional filter
        # gives it back.
        overrides=dict(CONTRAST_BOOST=0.05),
        description=(
            "an old-style serif with an unusually large x-height, for sustained "
            "reading at small optical sizes on screen"
        ),
    ),
    "Vavin Condensed": dict(
        styles=["Regular", "Italic", "Bold"],
        # ITC Garamond's condensed cut is the elegant one - narrow, tall,
        # more letters to the line.
        #
        # Narrowing LOWERS stroke contrast, it does not raise it. Vertical
        # stems scale with x, so condensing to 0.80 thins them from 70 to 56
        # units while the hairlines, which scale with y, stay at 35: measured
        # contrast falls from 2.21 to 1.51 and the letters read flat, almost
        # monoline. The contrast filter is what puts it back - which is the
        # whole reason that filter is not display-only.
        overrides=dict(
            LC_X_SCALE=0.80,
            UC_X_SCALE=0.84,
            LC_SIDEBEARING_DELTA=-2,
            CONTRAST_BOOST=0.13,
        ),
        description=(
            "a narrow cut for headlines and dense setting, where a tall "
            "x-height on a condensed body reads sharper than either alone"
        ),
    ),
    "Vavin Display": dict(
        styles=["Regular", "Black"],
        # For posters. The x-height goes higher still, the fit tightens, and
        # a directional contrast filter thins the horizontals while thickening
        # the stems - see contrast.py. Unusable at 10pt by design.
        overrides=dict(
            X_TO_CAP_TARGET=0.76,
            LC_X_SCALE=1.02,
            UC_X_SCALE=1.0,
            LC_SIDEBEARING_DELTA=-10,
            CONTRAST_BOOST=0.24,
            # An x-height of 0.76 of the cap leaves almost nothing for the
            # ascender: at ASCENDER_SCALE 1.0 the solver returns k=0.044,
            # meaning the stem of b d h k l is crushed to 4% of its height and
            # the letter becomes a serif sitting on nothing. Letting the
            # ascenders grow 5% restores k to a workable 0.33, and long
            # ascenders over a huge x-height is the display look anyway.
            ASCENDER_SCALE=1.05,
        ),
        description=(
            "a high-contrast cut for display sizes: hairlines cut back, stems "
            "thickened, spacing tightened, meant to be set large"
        ),
    ),
}

#: Directional contrast filter strength, as a FRACTION of the font's own
#: hairline rather than an absolute number of units. 0 disables it.
#:
#: Absolute was the wrong knob: 9 units sharpens a Regular nicely and closes
#: the counters of a Black, whose stems are twice as thick. A ratio keeps the
#: effect proportional to the weight it is applied to. 0.24 takes the hairline
#: down by about half and roughly doubles stroke contrast.
#: Only the display cut turns this on. See contrast.py for the mechanism.
CONTRAST_BOOST = 0.0

# --------------------------------------------------------------------------
# The design target
# --------------------------------------------------------------------------
# These are PROPORTIONS, not outlines. Proportions of a 1975 typeface are not
# protected by US copyright and any EU design right on them expired decades
# ago. We reproduce a *ratio*, we copy no data. See ../../LEGAL.md.
#
# Reference ratios (x-height / cap-height), from published specimens:
#   Classic Garamond revivals (EB Garamond, Adobe Garamond)  ~0.60 - 0.64
#   Times New Roman                                          ~0.66
#   ITC Garamond Book                                        ~0.72 - 0.75
#   Helvetica                                                ~0.73
#
# 0.72 sits at the bottom of the ITC range. Going higher is possible but the
# lowercase starts to lose the Garamond skeleton: the bowls flatten and the
# counters swell. Raise this only after looking at a proof at 9pt.
X_TO_CAP_TARGET = 0.72

#: Uppercase vertical scale. 1.0 = caps untouched.
#: Lowering caps slightly (0.96-0.98) is the cheap half of the ratio: it buys
#: you a higher x/cap ratio without distorting a single lowercase letter.
#: Default 1.0 because the brief says explicitly not to touch the capitals.
CAP_SCALE = 1.0

#: Ascender scale. 1.0 = the ascenders of b d h k l land exactly where they
#: started, so the font's overall vertical footprint barely moves.
ASCENDER_SCALE = 1.0

#: Descender handling.
#:   "uniform"  - descenders scale with the x-height (s x). Zero distortion at
#:                the bowl-to-tail join of p q y, but the font gets deeper.
#:   "compress" - descenders are pulled back toward DESCENDER_SCALE. Shallower
#:                font, but the joins need hand-correction afterwards.
DESCENDER_MODE = "uniform"
DESCENDER_SCALE = 0.95  # only used when DESCENDER_MODE == "compress"

#: Lowercase width. Applied to lowercase only; capitals keep their drawn
#: width. This knob is a genuine design decision with two costs pulling
#: against each other - run `python scripts/09_variants.py` to see it, which
#: also produces proof/06-widths.png.
#:
#: Raising the x-height scales the lowercase vertically by 1.16, so every
#: horizontal stroke thickens by 1.16 while the stems keep their drawn weight:
#: stroke contrast drops, and contrast is most of what makes a Garamond look
#: like a Garamond. Widening by the same factor cancels that exactly - it
#: becomes a pure uniform scale, zero distortion - but it thickens the stems
#: too, and the capitals were not touched.
#:
#:   LC_X_SCALE    contrast    lowercase stem / capital stem    n width
#:   (EB Garamond)     2.21                            0.874        528
#:   1.000            -15%                     0.874    +0%          536
#:   1.035            -11%                     0.912    +4%          554
#:   1.080             -8%                     0.949    +9%          578
#:   1.160             -1%                     1.024   +17%          620
#:
#: 1.160 is ruled out by the third column, not the second: at 1.024 the
#: lowercase stems come out HEAVIER than the capitals', which no roman does.
#: 1.080 recovers a third of the lost contrast, keeps the lowercase lighter
#: than the capitals, and gives the wide proportions the brief asked for.
LC_X_SCALE = 1.08
UC_X_SCALE = 1.0

#: Extra sidebearing added to every lowercase glyph, in units per em/1000.
#: Positive = looser tracking. The x-height rise eats optical space, so a
#: little compensation helps. Keep small; real spacing work happens in the UFO.
LC_SIDEBEARING_DELTA = 4

# --------------------------------------------------------------------------
# Shape of the vertical remap
# --------------------------------------------------------------------------
# The remap is defined by a *slope profile* which is integrated to produce the
# mapping. This guarantees monotonicity (an outline can never fold onto
# itself) and C1 continuity (no kinks). See remap.py for the mathematics.
#
# The whole point of the profile is to put all the compression where it cannot
# be seen: in the straight part of an ascender stem. The x-height body is a
# pure uniform scale, and the ascender terminal is a pure translation.
#
#   slope
#     s  |___________
#        |           \                        s = x-height scale factor
#        |            \____________           k = solved so the ascender lands
#     k  |                         \              back on target
#     1  |                          \______
#        +---------------------------------- y
#        0        P   P+B      T  T+B2
#
# Measured on EB Garamond Regular: x-height 405, ascender 705 (b d h k l),
# n/m/r shoulder overshoot to 430, t reaches 475.

#: How far above the x-height the *pure uniform scale* zone extends, in font
#: units. Must clear the arch overshoot of n/m/r (25 units) and ideally the
#: top of t (70 units above the x-height) so neither gets squashed.
PURE_SCALE_HEADROOM = 90

#: Width of the blend band where the slope falls from s to k. Too narrow and
#: you get a visible crease at the shoulder; too wide and it eats the shoulder.
BLEND_WIDTH = 70

#: Depth of the ascender terminal - the serif and its bracket - measured down
#: from the top of the ascender. Everything inside this band is translated
#: rigidly (slope 1), never compressed, so serifs keep their drawn shape.
TERMINAL_DEPTH = 70

#: Blend band for the terminal transition.
BLEND_AT_TERMINAL = 40

#: Sanity bounds on the solved stem-compression slope k. Below the lower bound
#: the ascender stems are being crushed hard enough that the join to the bowl
#: of b/d/p/q will need hand-correction; the build warns rather than fails.
K_SLOPE_WARN_BELOW = 0.25

#: How much of its own letter's rise each diacritic follows, as a ratio.
#:
#: The lift is computed PER GLYPH, from how far that letter's ink top actually
#: moved - not from one global constant. This matters: `dotlessi` tops out at
#: the x-height and rises 65 units, while the shoulder of `n` overshoots to
#: 430 and rises 69. A single constant silently eats the clearance on exactly
#: the letters that had the least to spare.
#:
#: 1.0 therefore preserves every accent's drawn clearance exactly. Lower it to
#: tighten accents deliberately - real large-x-height faces do, because there
#: is less room up there - but check proof/04-diacritics.png afterwards.
#:
#: Mark outlines are never touched, only the composite's component offset and
#: the matching GPOS anchor, so a mark cannot be distorted and the shared
#: uppercase accents cannot move.
MARK_LIFT_RATIO = 1.0

# --------------------------------------------------------------------------
# Vertical metrics policy
# --------------------------------------------------------------------------
# Google Fonts' rule, which is also the sanest choice for an iOS app:
#   - hhea ascender/descender == OS/2 sTypoAscender/sTypoDescender
#   - lineGap == 0 everywhere
#   - usWinAscent/usWinDescent cover the real ink so nothing clips on Windows
#   - fsSelection bit 7 (USE_TYPO_METRICS) set
#
# On iOS, UIFont.lineHeight = hhea.ascent - hhea.descent + hhea.lineGap, so
# these numbers directly drive line spacing in your SwiftUI views.
LINE_HEIGHT_EM = 1.20  # target default line height, in em

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "sources"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
#: Proof sheets live in documentation/, which is where the Google Fonts
#: repo layout expects a family's specimen images to be.
PROOF = ROOT / "documentation"

UPSTREAM_VF = SOURCES / "upstream_EBGaramond[wght].ttf"
UPSTREAM_VF_ITALIC = SOURCES / "upstream_EBGaramond-Italic[wght].ttf"


def ps_name(style: str, family: str | None = None) -> str:
    """PostScript name, e.g. 'Vavin-Regular', 'VavinCondensed-Italic'."""
    base = (family or FAMILY_NAME).replace(" ", "")
    return f"{base}-{style.replace(' ', '')}"


@contextmanager
def overrides(values: dict):
    """Temporarily apply a family's parameter overrides to this module.

    The pipeline reads its parameters from module globals, which is fine for
    one family and wrong for three. Rather than thread a settings object
    through every function, each family's build runs inside this, and the
    values are restored afterwards even if the build raises - otherwise a
    failed condensed build would silently poison the display build that
    follows it in the same process.
    """
    previous = {key: globals()[key] for key in values}
    globals().update(values)
    try:
        yield
    finally:
        globals().update(previous)


def font_path(style: str, family: str | None = None) -> Path:
    """Where a built font lives.

    21_specimen.py sorts dist/ into one folder per family, so nothing may
    assume the flat layout the build itself writes. Everything downstream asks
    here instead, and gets the sorted path if it exists and the flat one if the
    build has just run and not been sorted yet.
    """
    family = family or FAMILY_NAME
    name = f"{ps_name(style, family)}.ttf"
    sorted_path = DIST / family.replace(" ", "") / "ttf" / name
    return sorted_path if sorted_path.exists() else DIST / name


def version_string() -> str:
    return f"Version {VERSION_MAJOR}.{VERSION_MINOR:03d}"
