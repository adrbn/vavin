Vavin 1.0 is the first public release: nine static fonts in three families, derived from EB Garamond, with an
x-height of 0.72 of the cap height.

## In the zip

`Vavin-v1.0.zip` holds, for each of Vavin, Vavin Condensed and Vavin Display:

- `ttf/`: the full character set (Latin, Greek, Cyrillic; 2091 code points in the upright styles), for desktop use
- `app/`: a Latin subset that keeps the combining accents, for embedding in apps
- `web/`: WOFF2

plus `OFL.txt` and `FONTLOG.txt`.

## The families

| Family | Styles | x-height / cap |
|---|---|---:|
| Vavin | Regular, Italic, Bold, Bold Italic | 0.719 |
| Vavin Condensed | Regular, Italic, Bold | 0.719 |
| Vavin Display | Regular, Black | 0.758 |

EB Garamond's ratio is 0.620. Line height is 1.20 em in every family. Stroke contrast in Vavin Regular measures 2.29,
against 2.21 for EB Garamond.

## Quality

- `make check`: 315 checks pass across the nine fonts and their Latin subsets.
- FontBakery `check-universal` on the four Vavin styles, diffed against EB Garamond at the same weights: 7 findings
  inherited, 5 fixed, 1 introduced (`overlapping_path_segments`, a warning).

## Known limitations

Kerning was scaled rather than redrawn, Display's `f` and `R` want a look at poster sizes, and there is no variable
font. Details in [docs/TECHNICAL.md](https://github.com/adrbn/vavin/blob/main/docs/TECHNICAL.md#known-limitations).

## License

SIL Open Font License 1.1, with no Reserved Font Name. Copyright 2026 adrbn; EB Garamond copyright 2017 The EB
Garamond Project Authors.
