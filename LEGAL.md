# Legal basis for Vavin

This file records the reasoning behind the project so it can be checked, and
so the constraints stay visible when the work is picked up again months later.

**None of this is legal advice.** It is a documented, conservative reading. If
Vavin ever becomes commercially important to you, have a lawyer read it.

---

## 1. What Vavin is made of

Vavin is a modification of **EB Garamond**, by Georg Duffner and Octavio
Pardo, released under the **SIL Open Font License 1.1**, which explicitly
permits modification and redistribution.

    sources/upstream_EBGaramond[wght].ttf
    from https://github.com/google/fonts/tree/main/ofl/ebgaramond
    upstream source: https://github.com/octaviopardo/EBGaramond12

Every outline in Vavin descends from that file. Nothing else.

## 2. What Vavin is NOT made of

No data of any kind was taken from ITC Garamond or any other proprietary font.
No file was opened, decompiled, traced, auto-traced, or measured with a tool.
The pipeline in `scripts/` reads exactly one font: the EB Garamond binary
above. You can verify this - `grep -rn "TTFont(" scripts/` shows every font
this project ever opens.

This matters because a font file is a **computer program**, and copying it is
copyright infringement in essentially every jurisdiction. ITC Garamond is
© Adobe / Monotype and ships with `fsType 4`; its EULA forbids modification.
That door stays shut.

**If you are tempted later: don't.** Not "just to measure it", not "just to
check a curve". The moment a proprietary outline touches this project the
whole thing becomes unpublishable, and the provenance argument above - which
is currently airtight and verifiable - collapses.

## 3. Why copying the *proportions* is nevertheless fine

Three separate reasons, any one of which would be enough:

**Typeface designs are not copyrightable in the United States.** The design of
a typeface - the shapes of the letters as an industrial design - is excluded
from copyright protection. 37 CFR § 202.1(e) refuses registration of "typeface
as typeface". *Eltra Corp. v. Ringer*, 579 F.2d 294 (4th Cir. 1978) upheld
that refusal. What US law does protect is the **font software**: the program,
the outline data, the hinting. Hence the sharp line in sections 1 and 2.

**Any European design right on a 1975 design has long expired.** ITC Garamond
was designed by Tony Stan in 1975. Registered Community Designs last a maximum
of 25 years; unregistered ones, 3 years. Both ran out decades ago. Some
European countries do grant copyright to typefaces as works of applied art,
with terms running from the author's death - Tony Stan died in 1988 - so in
those jurisdictions a term may still be running on the *design*. This is the
one genuinely soft spot in the analysis, and it is why Vavin reproduces a
*ratio* derived from published specimen figures rather than any curve.

**A ratio is a fact, not an expression.** `X_TO_CAP_TARGET = 0.72` in
`scripts/vavin/config.py` is a number, taken from published descriptions of
ITC Garamond's proportions. Facts are not protected by copyright anywhere.

## 4. The name

**"ITC Garamond" is a trademark.** Trademark is entirely separate from
copyright: it protects the name in commerce, has no expiry as long as it is
used and defended, and would not be affected by anything in section 3.

The rules Vavin follows:

- The family is **Vavin**. No "Garamond" anywhere in any identifying name.
- The description never claims to be a version, clone, revival or replacement
  of ITC Garamond. It says what it is: a large-x-height modification of EB
  Garamond.
### The name was screened, and the first one failed

The family was called **Mazarine** until 15 August 2026. A catalogue check
(Google Fonts, locally installed fonts) found nothing, but a catalogue check
is not a trademark search. The real search killed it:

- **A2 Mazarin**, a commercial Garamond-inspired typeface from A2-TYPE
  (Henrik Kubel, 2017, 14 styles), descended from the Stephenson Blake recut
  of 1926. Same product category, same design lineage, one letter apart.
- **MAZARINE**, a live French word mark held by Mazarine — the Paris creative
  group, €182m turnover — registered in **Nice class 9**, which is exactly
  where downloadable font software sits, plus classes 16 and 42.

Renamed to **Vavin**, screened the same way in the
[WIPO Global Brand Database](https://branddb.wipo.int) (76m records, 89
offices) before adoption:

| Term | Records | Live in class 9 / 16 / 42 |
|---|---:|---|
| mazarine | 76 | **yes — class 9, 16, 42, owned by Mazarine** |
| vavin | 14 | none on "Vavin" alone; one class 16 (homeware), "OPTIC VAVIN" class 9 is eyewear |

No typeface named Vavin was found on MyFonts, Fontsinuse or in general search.

**What is still outstanding.** A WIPO screening is not a clearance opinion.
It reads word marks, not figurative ones, and it cannot judge likelihood of
confusion. Before any commercial use beyond a free OFL release, have a French
*conseil en propriété industrielle* run a real availability search in classes
9 and 42. Budget a few hundred euros; it is cheap next to a rename after
launch, which is what section 4 just cost.

**Screen any future rename the same way** — `branddb.wipo.int`, classes 9, 16
and 42, plus a search for the bare word with "typeface" and "font".

Do not describe Vavin as "ITC Garamond-like" in App Store copy or on a
website. Comparative reference in a technical document such as this one is
nominative fair use; marketing copy is where trademark problems start.

## 5. The Reserved Font Name rule - and why it does not bite here

The OFL lets an author reserve the font's name, so that modified versions
cannot pass themselves off as the original. The mechanism is a phrase in the
**copyright line at the top of `OFL.txt`**:

    Copyright (c) 2015, Some Author (email), with Reserved Font Name "Foo".

If that phrase is present, OFL clause 3 forbids using "Foo" in the name of any
modified version, full stop.

**EB Garamond does not declare one.** Its `OFL.txt` opens:

    Copyright 2017 The EB Garamond Project Authors
    (https://github.com/octaviopardo/EBGaramond12)

No `with Reserved Font Name` clause. The phrase appears exactly once in the
file, at line 34, inside the licence's own **definitions** section - that is
the OFL boilerplate explaining what an RFN *is*, not a declaration that there
is one. (`sources/upstream_OFL.txt`, verify with
`grep -n "Reserved Font Name" sources/upstream_OFL.txt`.)

Google Fonts drops RFNs from the families it maintains, for exactly this
reason: an RFN makes a font hard to fork and re-host.

**So renaming is a choice here, not an obligation.** It is still the right
choice:

1. Two different fonts named "EB Garamond" with different metrics fighting
   over the same name in a font cache is a genuine mess for users.
2. You want your own identity for Aura anyway.
3. It removes any argument that you are misrepresenting the upstream authors'
   work - which is the RFN's purpose even when it is not enforced.

### Vavin's own Reserved Font Name

From version 1.1, Vavin **does** declare one: `OFL.txt` opens with
`Copyright 2026 adrbn (https://github.com/adrbn/vavin), with Reserved Font
Name "Vavin".`, and the same phrase is in name ID 0 of every font. Under OFL
clause 3, a modified version may no longer use "Vavin" in its name. Anyone may
still fork, change and redistribute the fonts; they must call the result
something else. The copyright holder of a modification may add an RFN for
their own work; EB Garamond declared none, so there is no upstream name to
respect beyond renaming, which section 4 already did.

Version 1.0 was released on 2 October 2026 without an RFN. Copies of 1.0
keep the terms they were released under: the OFL is irrevocable for what it
has already granted. The RFN binds 1.1 and everything after it.

### What the OFL does not allow, even with an RFN

The RFN protects the **name**, not the fonts. Two things are out of reach for
any font derived from EB Garamond, whatever its copyright holder wants:

- **Another licence.** Clause 5: a modified version must be distributed
  entirely under the OFL. Vavin cannot be relicensed as a commercial font.
- **Selling the fonts themselves.** Clause 1: the font software may not be
  sold by itself. Bundling with real software (an app such as Aura) is
  allowed; selling a font next to a token program to get around clause 1 is
  not, per the OFL FAQ.

A paid, proprietary typeface would need outlines that do not come from EB
Garamond: a new design, drawn from scratch.

## 6. What the OFL requires of Vavin

Since Vavin is a Modified Version of OFL software:

| Requirement | Where it is satisfied |
|---|---|
| Ship under the OFL, same licence | `OFL.txt` |
| Keep the original copyright notice | `OFL.txt` header, and name ID 0 in every font |
| Include the licence with the fonts | `OFL.txt` in the repo and the release |
| Do not sell the fonts by themselves | They are free; bundling inside Aura is fine and expressly permitted |
| No name conflict with an RFN | None declared upstream; renamed anyway |

Note the fourth row: the OFL forbids selling the *fonts* on their own. It has
never forbidden bundling them in a commercial application. Aura can be a paid
app with Vavin embedded, and you owe nobody anything for it.

The attribution in name ID 0 is deliberate and required - `scripts/05_verify.py`
has a check that **fails the build if the copyright stops crediting the EB
Garamond project**. The audit that scans for leftover upstream names skips the
copyright and description fields for exactly this reason: attribution there is
the obligation, not the leak.

## 7. Verifying the claims in this file

    grep -n "Reserved Font Name" sources/upstream_OFL.txt   # only the definition, line 34
    grep -rn "TTFont(" scripts/                             # every font this project opens
    python scripts/05_verify.py                             # naming + attribution checks
