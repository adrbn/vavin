# How Vavin is made

The technical record of the project: how the x-height is raised, what was
measured, what is still imperfect, and how the build is laid out. The
[README](../README.md) covers installing and using the fonts.

Every number on this page comes from the current build. Rebuild, then run
`.venv/bin/python scripts/13_facts.py`, which prints all of them; language
counts come from `.venv/bin/hyperglot`.

Vavin is a modification of **EB Garamond**. It is **not** derived from ITC
Garamond and contains no data from it: only the *proportion* is borrowed, and
a proportion is a fact rather than a protected expression. The reasoning, and
the limits it imposes, are in [LEGAL.md](../LEGAL.md). Read that before
changing anything about the name or the sources.

## Contents

- [The numbers](#the-numbers)
- [Quick start](#quick-start)
- [How the x-height is raised](#how-the-x-height-is-raised)
- [Configuration](#configuration)
- [Known limitations](#known-limitations)
- [Verification](#verification)
- [Repository layout](#repository-layout)
- [Using it in Aura](#using-it-in-aura)
- [Publishing](#publishing)

---

## The numbers

| Family | Styles | For |
|---|---|---|
| **Vavin** | Regular, Italic, Bold, Bold Italic | text, app UI, long reading |
| **Vavin Condensed** | Regular, Italic, Bold | headlines, dense setting |
| **Vavin Display** | Regular, Black | posters, set large only |

Nine static fonts. They are three separate families rather than one, because
an OpenType family carries only the four RIBBI styles before style linking
breaks and applications start synthesising fake bolds.

|                        | EB Garamond | Vavin | Condensed | Display |
|------------------------|------------:|------:|----------:|--------:|
| x-height               |         405 |   468 |       467 |     490 |
| cap-height             |         653 |   651 |       649 |     646 |
| **x-height / cap**     |   **0.620** | **0.719** | **0.719** | **0.758** |
| stroke contrast        |        2.21 |  2.29 |      2.05 |    3.24 |
| advance of `n`         |         528 |   578 |       418 |     519 |

Regular weights. Units per em: 1000. Heights are measured from ink, not from
the OS/2 table: upstream declares `sxHeight 400` and `sCapHeight 650` against
a real 405 and 653. Stroke contrast is the mean stem-to-hairline ratio over
`o n b d p q e c`, the method of `scripts/09_variants.py`. The other styles
land within a unit or two: x/cap is 0.717 to 0.720 across the text and
condensed styles and 0.756 in Display Black.

Line height is 1.20 em in every family, with a zero line gap. The `hhea`
ascender and descender are 879 / −321 for Vavin, 903 / −297 for Condensed and
894 / −306 for Display. EB Garamond's are 1007 / −298, a 1.30 em line.

The upright styles carry EB Garamond's full set: 3247 glyphs and 2091 code
points (Latin, Greek, Cyrillic). The italics carry 3075 glyphs and 1972 code
points. Hyperglot 0.8.1 finds 503 Latin-script and 83 Cyrillic-script
languages supported by Vavin Regular, 416 and 83 by Vavin Italic, and 345 by
the Latin app subset.

---

## Quick start

```bash
make setup      # .venv + toolchain (needs uv, and brew install harfbuzz)
make upstream   # fetch EB Garamond from google/fonts, checksum-verified
make fonts      # all nine fonts + Latin subsets
make specimen   # sort dist/ by family, emit woff2, wire up specimen/
make serve      # the specimen at http://localhost:8731
make check      # per-glyph checks on every built font
make qa         # FontBakery on Vavin AND upstream, diffed
make install    # into ~/Library/Fonts
make zip        # release/Vavin-v1.0.zip
make readme-art # the SVGs in docs/assets/
```

Output:

```
dist/Vavin/            ttf/   full character set, 507–564 kB each
                       app/   Latin subset, 259–272 kB: embed these in an app
                       web/   woff2, 173–195 kB
dist/VavinCondensed/   same
dist/VavinDisplay/     same
```

The `app/` subsets drop Greek and Cyrillic but **keep the combining marks**,
which is not optional: macOS and iOS normalise file names to NFD, so a track
title read off disk arrives as `Cafe` + U+0301. Without the marks the word
renders half in Vavin and half in the system font.

---

## How the x-height is raised

This is the part worth understanding, because it is where a naive approach
ruins the letters.

**The naive move** is to scale the lowercase by *s* about the baseline. It
raises the x-height, and it also multiplies the ascenders by *s* so the font
grows, thickens every horizontal stroke by *s* while the vertical stems stay
put, and flattens the contrast that makes a Garamond a Garamond.

**The usual fix**, a piecewise-linear y-map with a breakpoint at the
x-height, leaves a visible crease wherever an outline crosses the breakpoint.

**What this does instead** is define a *slope profile* `g(y)` and integrate it:

```
f(y) = ∫₀ʸ g(t) dt
```

Because `g > 0` everywhere, `f` is strictly increasing: an outline can never
fold onto itself. Because `g` is continuous, `f` is C¹: no kinks. And because
we choose where `g` dips, we choose which part of the letter absorbs the
change:

```
slope
 1.161 │────────────╮                     ← pure uniform scale
       │             ╰──╮                    the body of the letter
 0.318 │                ╰────────╮        ← compressed stem
 1.000 │                          ╰─────  ← rigid translation
       └──────────────────────────────── y
       0          495  565    635  675
```

| Zone | What lives there | What happens |
|---|---|---|
| 0 → 495 | bowls, shoulders, counters, the whole x-height body, descenders | **pure uniform scale.** Not distorted, just bigger. Exact to 10⁻⁶ units. |
| 565 → 635 | the straight middle of an ascender stem | **compressed by 0.318.** Compressing a straight vertical line changes nothing about its shape, which is precisely why all the compression is put here. |
| 675 → | the ascender serif and its bracket | **translated, not scaled.** Serifs keep their drawn weight. |

`k = 0.318` is solved numerically so that `f(705) = 705` exactly: the
ascenders land back where they started and the font's vertical footprint
barely moves. The upper edge of the pure-scale zone clears the arch overshoot
of `n m r` (430) and the top of `t` (475), so neither gets squashed.

The one real cost: scaling `y` by 1.161 thickens *horizontal* strokes by 16%
while `LC_X_SCALE` thickens the stems by only 1.08, so stroke contrast would
drop by about 7% (`scripts/08_strokes.py` measures −6.6% with the x-height
scale actually achieved, 1.1565). That would move toward ITC Garamond, which
is lower-contrast than a classic Garamond, as a side effect rather than a
design decision. The contrast filter below now compensates for it; see
[Known limitations](#known-limitations).

### Italics

The remap cannot be applied vertically to an italic. An upright ascender stem
is a vertical line, and compressing `y` leaves a vertical line vertical,
which is the entire reason the compression is invisible. An italic stem leans
17.2°, and compressing it by `k = 0.318` without straightening it first takes
that lean to **44°**: the stem visibly folds partway up.

So each point is sheared upright, remapped, and sheared back by the same angle
against its *new* height. A slanted straight line stays a slanted straight
line, at its original angle.

### Raising contrast without changing width

Condensing the lowercase to 0.80 thins its stems from 70 to 56 units while
the hairlines, which scale with `y`, do not thin at all. Mean contrast falls
from 2.21 to 1.51 and the letters read almost monoline. No affine transform
can fix that: scaling `x` thickens the stems but also widens the letter, and
the two cannot be separated.

[`contrast.py`](../scripts/vavin/contrast.py) does it properly, moving each
point along the outline's own normal by an amount that depends on which way
the outline runs there:

```
offset(p) = N(p) · d · (|T.y| − |T.x|)
```

+1 where the outline runs vertically (the side of a stem: push outward). −1
where it runs horizontally (the top of a hairline: push inward). Smooth in
between, so a bowl is treated correctly all the way round: thick at its
sides, thin at its top. That is what a broad-nib pen does, which is why the
result still reads as a Garamond. With it, Condensed Regular measures 2.05.

Three things it has to get right, each of which failed first:

1. **Winding is a per-glyph question, not per-contour.** A counter is wound
   opposite to its outer contour on purpose, so its own "outward" normal
   points *into* the ink. Ask each contour and the outer wall of an `o`
   thickens by `d` while its counter thins the same wall by `d`: exact
   cancellation. The filter silently did nothing to `o d b p q` and worked
   perfectly on `n` and `c`, which have no counter.
2. **The depth must scale with the weight.** A fixed 9 units sharpens a
   Regular and closes the counters of a Black, whose stems are twice as
   thick; in an early build one `d` counter went from 55 units to 2.8 and the
   letter shut. The depth is a fraction of the font's own hairline instead.
3. **The offset field needs smoothing.** Where a stem meets its serif, one
   point wants to move out and the next in, which leaves a notch in the side
   of every ascender. Averaging each offset with its neighbours spreads the
   transition; smoothing the *offsets* rather than the *positions* keeps the
   letter's drawn corners sharp.

### Accents

Diacritics are never scaled. Mark outlines are shared between the lowercase
and uppercase composites, so touching `acutecomb` to suit a taller x-height
would shove every capital's accent out of place. Instead:

- the composite's **component offset** is moved, and
- the matching **GPOS anchor** is moved by the same amount,

so `é` and `e` + U+0301 land identically. The lift is computed **per glyph**
from how far that letter's ink top actually moved: `dotlessi` tops out at the
x-height and rises 65 units, while the shoulder of `n` overshoots to 430 and
rises 69. A single global constant silently eats the clearance on exactly the
letters that have the least to spare; measuring each base glyph preserves
every accent's drawn clearance. Marks *below* the baseline (cedilla, ogonek,
the Vietnamese dot below) do not move at all.

---

## Configuration

Everything tunable is in [`scripts/vavin/config.py`](../scripts/vavin/config.py).
Nothing else hardcodes a number.

| Knob | Default | Effect |
|---|---|---|
| `FAMILY_NAME` | `Vavin` | changes every name field; one edit, then rebuild |
| `X_TO_CAP_TARGET` | `0.72` | the whole point. 0.75 is ITC's upper end; past that the bowls flatten |
| `CAP_SCALE` | `1.0` | lowering caps to 0.96–0.98 buys ratio without touching a single lowercase letter |
| `ASCENDER_SCALE` | `1.0` | ascenders land exactly where they started |
| `DESCENDER_MODE` | `uniform` | `compress` shortens descenders but distorts the `p q y` bowl-to-tail join |
| `LC_X_SCALE` | `1.08` | lowercase width. Trades stroke contrast against lowercase-vs-capital stem weight; `scripts/09_variants.py` measures both |
| `LC_SIDEBEARING_DELTA` | `4` | tracking compensation, in units |
| `MARK_LIFT_RATIO` | `1.0` | 1.0 preserves each accent's drawn clearance exactly |
| `LINE_HEIGHT_EM` | `1.20` | becomes `UIFont.lineHeight` on iOS |
| `CONTRAST_BOOST` | `0.05` text, `0.13` cond., `0.24` display | hairline thinning as a fraction of the font's own hairline |

Per-family overrides live in `FAMILIES` in the same file: Condensed sets the
lowercase width to 0.80, the capitals to 0.84 and the sidebearing delta to −2;
Display targets a ratio of 0.76 with a lowercase width of 1.02, a sidebearing
delta of −10 and `ASCENDER_SCALE` 1.05. A family's build runs inside
`config.overrides(...)`, which restores the globals afterwards even if the
build raises; otherwise a failed condensed build would poison the display
build that follows it in the same process.

After changing anything: `make fonts check proof` and **look at
`documentation/03-normalised.png`**. The numbers will happily report success
on a font whose letters have been ruined.

---

## Known limitations

Being straight about this: **the output is a very good starting point, not a
finished typeface.** But every claim below is measured, by
`scripts/08_strokes.py`, `scripts/09_variants.py`, `scripts/12_greyvalue.py`
and `scripts/13_facts.py`. When the measurements first ran, one limitation
this section listed was real and has since been fixed, and three turned out
to be false. They are kept at the bottom rather than quietly deleted, because
being wrong in a documented way is the point of measuring.

1. **Lowercase now 9% heavier than the capitals, relatively.** The lowercase
   stem to capital stem ratio moved from 0.874 to 0.954 when the lowercase was
   widened to 1.08. Still below 1.0, so the lowercase stays lighter than the
   capitals as it must, but the gap narrowed. The proper fix is to redraw the
   capitals, not to rescale anything.
2. **Kerning.** Values were scaled by `LC_X_SCALE`. The tight pairs
   (`Ta Vo we`) should be checked by eye.
3. **The display cut's terminals.** The contrast filter smooths its offset
   field, which keeps serifs crisp, but `f` and `R` still want a look at
   poster sizes.
4. **No variable font.** Nine statics. The remap would have to rewrite `gvar`
   deltas, which is a different and much larger job.
5. **One FontBakery warning of our own.** `overlapping_path_segments` is the
   only finding the build introduces relative to upstream (see
   [Verification](#verification)). It does not affect rendering, but the
   outlines in question should be cleaned in Track B.

### Fixed since it was listed

- *"Stroke contrast is down 7.6% and needs hand correction."* It was, and it
  did, so the directional contrast filter was pointed at the text family at a
  light setting (`CONTRAST_BOOST = 0.05`, about 2 units). Measured contrast is
  now **2.29 against the source's 2.21**: the loss is not merely recovered,
  it is slightly over-corrected.

### Three things this section used to claim, which measurement disproved

- *"`t` and `f` look stubby."* They do not. `t` keeps its height above the
  x-height to within 0.6% (0.173 → 0.174 of the x-height), because the
  pure-scale zone extends to 495 and `t` tops out at 475. `f` behaves exactly
  like `b d h k l`, which is the intended effect and not a defect.
- *"The bowl-to-stem joins of `b d p q` want redrawing."* The joins sit around
  the x-height, well inside the pure-scale zone, so they are a uniform scale
  of the original and undistorted. The compression starts at 495, above every
  one of them.
- *"Spacing is a blunt instrument and needs a real pass."* Measured, it does
  not. In proportion to the x-height, the sidebearings of `n` came out 4.9%
  looser and those of `o` 1.2% tighter: the rhythm is the source's. The
  number that actually matters, ink per unit of set width at an identical
  x-height, lands within **0.4%** of EB Garamond. The page colour is the
  source's. The same measurement shows Vavin setting **6.0% shorter** for the
  same words at the same apparent size, which is the whole point of a large
  x-height and is now a measured claim rather than a hope. (Condensed: +3.2%
  ink density, 29.1% shorter. Display: +10.2%, 19.4% shorter.)

Inherited from upstream and *not* introduced here: incomplete case-mapping for
archaic Greek and Latin letters, no ligature caret positions, no
stylistic-set descriptions, unreachable glyphs. `make qa` proves the
distinction by running FontBakery against both and diffing.

---

## Verification

Three independent layers, because each catches what the others miss.

**`make check`**: 22 checks per full font and 13 per Latin subset, over every
glyph, 315 passing in all. Ratio, vertical metric coherence, ink inside
`usWin*`, complete renaming, attribution present, mark outlines unmodified,
advance widths, sidebearings, and accent clearance compared *against
upstream* rather than against zero (347 accented glyphs per full font). That
last framing matters: the useful question for a derivative is not "is this
clearance comfortable", since the source already judged that, but "did I
make it worse".

**`make qa`**: FontBakery `check-universal` on the four Vavin styles and on
upstream instanced at the same weights, diffed. Current state:

```
inherited from EB Garamond      7  (1 FAIL, 6 WARN)
FIXED relative to upstream      5  (family/win_ascent_and_descent, name/italic_names,
                                    opentype/fsselection, opentype/italic_angle,
                                    opentype/mac_style)
INTRODUCED by this build        1  (WARN overlapping_path_segments)
```

`make qa` exits non-zero while anything is introduced, on purpose.

**`make proof`**: six sheets in `documentation/`. `01-comparison` is the same
point size side by side; `03-normalised` scales both to an identical x-height
so the comparison is about shape rather than size, which is the one to study;
`04-diacritics` exercises precomposed *and* decomposed spellings, since they
travel through completely different code paths.

---

## Repository layout

```
vavin/
├── scripts/
│   ├── 00_fetch_upstream.sh    the only download this project makes
│   ├── 01_measure.py           measure any font's real proportions
│   ├── 03_restyle.py           Track A: the shipping build
│   ├── 04_proof.py             proof sheets
│   ├── 05_verify.py            per-glyph checks
│   ├── 06_qa.py                FontBakery, diffed against upstream
│   ├── 07_hero.py              a one-page presentation sheet
│   ├── 08_strokes.py           stroke weights and contrast
│   ├── 09_variants.py          the lowercase-width trade-off, measured
│   ├── 10_track_b.py           Track B: Glyphs → UFO → fontmake
│   ├── 12_greyvalue.py         page colour: ink per set width
│   ├── 13_facts.py             every number the docs quote
│   ├── 20_package.py           the release zip
│   ├── 21_specimen.py          sort dist/, woff2, specimen assets
│   └── vavin/
│       ├── config.py           every tunable number
│       ├── metrics.py          ink measurement
│       ├── remap.py            the vertical map
│       ├── contrast.py         the directional contrast filter
│       ├── strokes.py          stem and hairline measurement
│       ├── glyphsets.py        glyph classification
│       ├── transform.py        outlines, composites, widths
│       ├── positioning.py      GPOS anchors and kerning
│       ├── vmetrics.py         vertical metrics
│       ├── naming.py           identity, RFN-safe
│       └── ufo_transform.py    the same remap, for UFO sources
├── specimen/                   the specimen site (GitHub Pages)
├── docs/                       this page, release notes, README art
├── ios/VavinFont.swift         SwiftUI integration
├── sources/                    upstream licence and metadata; binaries fetched
├── dist/                       built fonts (not committed)
├── documentation/              proof sheets (generated, not committed)
└── OFL.txt  FONTLOG.txt  LEGAL.md
```

### Two tracks

**Track A** (`03_restyle.py`) edits the compiled binary with fontTools. Fast,
works today, produces what ships.

**Track B** (`10_track_b.py`) converts the upstream Glyphs source to UFO
masters, applies the identical remap, and builds with fontmake. Slower and
rougher, and it exists for one reason: you cannot open a `.ttf` in a type
editor and fix a curve. Everything in "Known limitations" needs Track B. It
downloads the 9 MB Glyphs source from
[octaviopardo/EBGaramond12](https://github.com/octaviopardo/EBGaramond12) on
first use.

```bash
make ufo          # build/ufo/Vavin-*.ufo
# ... hand-correct in RoboFont / Glyphs / FontForge / TruFont ...
make ufo-build    # dist/ufo-build/
```

---

## Using it in Aura

[Aura](https://github.com/adrbn/aura) sets its titles in Vavin Condensed.
Copy [`ios/VavinFont.swift`](../ios/VavinFont.swift) into the project and
follow the three-step setup in its header comment. The short version:

1. Add `Vavin-{Regular,Bold}-Latin.ttf` to the target, and check they
   appear in **Build Phases → Copy Bundle Resources**, which is the step
   everyone forgets.
2. List the **file names** in `UIAppFonts` in Info.plist.
3. Call the **PostScript names**: `Vavin-Regular`, `Vavin-Bold`.

```swift
Text("Écouter autrement").font(.auraTitle)
Text(body).font(.auraBody).vavinLeading(1.40, size: 17)
```

Use `Font.custom(_:size:relativeTo:)`, provided by the `.aura*` scale, so
Dynamic Type keeps working. A plain `Font.custom(_:size:)` ignores the user's
text-size setting, which is an accessibility regression the moment you adopt
a custom face.

Both styles share one vertical metric set on purpose (`hhea` 879 / −321, line
gap 0, `USE_TYPO_METRICS` set), so `UIFont.lineHeight` is 1.20 em in Regular
and Bold alike and emboldening a run cannot reflow the paragraph around it.

The OFL requires the licence to travel with the software: ship `OFL.txt` in
the bundle and surface `Vavin.licenceNotice` in the acknowledgements screen.

`ios/VavinDemo/` is a small test harness: copy the two Latin subsets into its
`Sources/` and run `xcodegen` there.

---

## Publishing

```bash
make release      # rebuild, check, then release/Vavin-v1.0.zip
```

To submit to Google Fonts: open an issue on
[google/fonts](https://github.com/google/fonts) using the **Font Addition**
template, pointing at a tagged release. Their onboarding runs FontBakery's
`googlefonts` profile, which is stricter than the `universal` profile
`make qa` runs: expect notes about the specimen images and `METADATA.pb`,
which this repository does not generate.

The name was screened in the WIPO Global Brand Database before adoption
([LEGAL.md §4](../LEGAL.md#4-the-name)). A screening is not a clearance
opinion: before any commercial use beyond a free OFL release, LEGAL.md
recommends a professional availability search in classes 9 and 42.
