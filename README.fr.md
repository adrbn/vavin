<div align="center">

<picture>
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/hero-light.svg">
  <img src="docs/assets/hero.svg" width="100%" alt="Le mot Vavin composé en Regular, Italic, Bold, Condensed et Display Black, puis en EB Garamond, entre la ligne des capitales et la ligne de base. Une ligne rouge marque la hauteur d'x de Vavin, 0,719 de la hauteur des capitales, une ligne pointillée celle d'EB Garamond, 0,620.">
</picture>

# Vavin

**Un Garamond à grand œil, pour lire sur écran.** Neuf polices libres en trois familles, dérivées d'EB Garamond,
dont les minuscules montent à 0,72 de la hauteur des capitales au lieu de 0,62.

<a href="https://github.com/adrbn/vavin/releases/latest"><img src="docs/assets/btn-download-fr.svg" alt="Télécharger" height="44"></a>&nbsp;
<a href="https://adrbn.github.io/vavin/"><img src="docs/assets/btn-specimen-fr.svg" alt="Spécimen" height="44"></a>&nbsp;
<a href="docs/TECHNICAL.md"><img src="docs/assets/btn-how-fr.svg" alt="Fabrication" height="44"></a>&nbsp;
<a href="#licence"><img src="docs/assets/btn-license-fr.svg" alt="Licence" height="44"></a>

[![License OFL-1.1](https://img.shields.io/badge/license-OFL--1.1-B23219?style=flat-square&labelColor=121212)](OFL.txt)
[![9 styles, 3 families](https://img.shields.io/badge/styles-9%20%C2%B7%203%20families-B23219?style=flat-square&labelColor=121212)](#les-familles)
[![x-height 0.72 of cap height](https://img.shields.io/badge/x--height-0.72%20of%20cap-B23219?style=flat-square&labelColor=121212)](docs/TECHNICAL.md#the-numbers)
[![503 Latin languages, 3247 glyphs](https://img.shields.io/badge/coverage-503%20Latin%20languages%20%C2%B7%203247%20glyphs-B23219?style=flat-square&labelColor=121212)](docs/TECHNICAL.md#the-numbers)
[![Latest release](https://img.shields.io/github/v/release/adrbn/vavin?style=flat-square&labelColor=121212&color=B23219&label=release)](https://github.com/adrbn/vavin/releases/latest)

<sub>Libre et open source · TTF, WOFF2 et sous-ensembles latins pour les apps · macOS, Windows, Linux, le web et iOS</sub>

[English](README.md) · Français

</div>

---

Vavin part d'EB Garamond, la reprise libre du romain de Claude Garamont par Georg Duffner et Octavio Pardo, et en
agrandit l'œil de 16 % sans déplacer les capitales ni les ascendantes. À corps égal, une ligne de Vavin se lit plus
grande et compose 6 % plus court, avec la même densité d'encre sur la page. Elle a été dessinée pour l'application
musicale [Aura](https://github.com/adrbn/aura) et chacun peut l'utiliser, la modifier et la redistribuer librement.

## À quoi elle ressemble

<table>
  <tr>
    <td width="50%"><img src="docs/assets/card-waterfall.svg" width="100%" alt="Le même pangramme en Vavin Regular, de 9 à 72 pixels, qui défile lentement"></td>
    <td width="50%"><img src="docs/assets/card-xheight.svg" width="100%" alt="Le mot Bonheur en Vavin et en EB Garamond à la même hauteur de capitales, l'un plein, l'autre en contour, avec les deux hauteurs d'x marquées : 0,719 et 0,620"></td>
  </tr>
  <tr>
    <td><img src="docs/assets/card-family.svg" width="100%" alt="Les neuf styles l'un sous l'autre, chacun composé en lui-même : Vavin Regular, Italic, Bold, Bold Italic, Condensed Regular, Italic, Bold, Display Regular et Black"></td>
    <td><img src="docs/assets/card-diacritics.svg" width="100%" alt="Capitales et minuscules accentuées du français, du polonais, du tchèque, du hongrois, du roumain, du turc et de l'espagnol, dont les accents s'allument tour à tour"></td>
  </tr>
  <tr>
    <td><img src="docs/assets/card-paragraph.svg" width="100%" alt="Un paragraphe en français en 14 sur 20 pixels, qui alterne entre Vavin et EB Garamond sur la même justification"></td>
    <td><img src="docs/assets/card-aura.svg" width="100%" alt="Un iPhone qui affiche l'application Aura, ses écrans Home et library titrés en Vavin Condensed"></td>
  </tr>
</table>

Les cartes sont en anglais, comme le reste des images du dépôt. Le spécimen complet, avec chaque style en direct dans
le navigateur, est sur **[adrbn.github.io/vavin](https://adrbn.github.io/vavin/)**.

## Installation

Téléchargez `Vavin-v1.1.zip` depuis la [dernière version](https://github.com/adrbn/vavin/releases/latest). Chaque
famille a trois dossiers : `ttf/` (jeu de caractères complet, pour l'ordinateur), `app/` (sous-ensemble latin, à
embarquer) et `web/` (WOFF2).

**macOS.** Ouvrez les fichiers `.ttf` et cliquez sur *Installer la police* dans Livre des polices, ou copiez-les dans
`~/Library/Fonts`.

**Windows.** Sélectionnez les fichiers `.ttf`, faites un clic droit et choisissez *Installer* (ou *Installer pour
tous les utilisateurs*).

**Linux.** Copiez les fichiers `.ttf` dans `~/.local/share/fonts` et lancez `fc-cache -f`.

**Web.** Servez les fichiers de `web/` et déclarez un `@font-face` par style :

```css
@font-face {
  font-family: "Vavin";
  src: url("fonts/Vavin-Regular.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: "Vavin";
  src: url("fonts/Vavin-Italic.woff2") format("woff2");
  font-weight: 400;
  font-style: italic;
  font-display: swap;
}

body { font-family: "Vavin", Georgia, serif; }
h1   { font-family: "Vavin Condensed", "Vavin", serif; }
```

Les noms de famille sont `Vavin`, `Vavin Condensed` et `Vavin Display`. Le gras a la graisse 700, le Display Black
la graisse 800.

**iOS et SwiftUI.** Ajoutez `Vavin-Regular-Latin.ttf` et `Vavin-Bold-Latin.ttf` du dossier `app/` à votre cible,
vérifiez qu'ils figurent dans *Build Phases → Copy Bundle Resources*, et listez leurs noms de fichier sous
`UIAppFonts` dans Info.plist. Appelez-les ensuite par leur nom PostScript, relativement à un style de texte pour que
Dynamic Type continue de fonctionner. [`ios/VavinFont.swift`](ios/VavinFont.swift) en fait une petite échelle
typographique :

```swift
Text("Écouter autrement").font(.custom("Vavin-Bold", size: 26, relativeTo: .title))
Text(body).font(.vavin(17, relativeTo: .body)).vavinLeading(1.40, size: 17)
```

Les sous-ensembles latins gardent les accents combinants, car iOS et macOS stockent les noms de fichier en forme
décomposée (`e` + U+0301).

## Les familles

| Famille | Styles | Pour | hauteur d'x / capitales |
|---|---|---|---:|
| **Vavin** | Regular, Italic, Bold, Bold Italic | le texte, les interfaces, la lecture longue | 0,719 |
| **Vavin Condensed** | Regular, Italic, Bold | les titres, les colonnes étroites | 0,719 |
| **Vavin Display** | Regular, Black | les titres et affiches, en grand corps | 0,758 |

Le rapport d'EB Garamond est de 0,620. Toutes les familles ont un interligne de 1,20 em et le jeu de caractères
d'EB Garamond : latin, grec et cyrillique, 2091 points de code dans les styles droits. Ce sont trois familles et non
une seule, car une famille OpenType ne relie que quatre styles (romain, italique, gras, gras italique) avant que les
applications se mettent à fabriquer de faux gras.

## Fabrication

Agrandir simplement les minuscules allongerait aussi les ascendantes et écraserait le contraste entre pleins et
déliés. La construction fait donc passer les hauteurs par une courbe continue : le corps de chaque minuscule est
agrandi d'un bloc, la compression est cachée dans la partie droite des fûts d'ascendantes, et les empattements sont
déplacés, pas redimensionnés. Les italiques sont redressés avant la transformation puis réinclinés. Un filtre
directionnel affine ensuite les déliés pour rendre le contraste, et chaque accent monte d'autant que sa propre lettre
de base a grandi.

Tout est scripté, du téléchargement d'EB Garamond jusqu'à l'archive de la version, et chaque chiffre de ce README est
mesuré par `scripts/13_facts.py`. La méthode, les mesures et les limites connues sont dans
**[docs/TECHNICAL.md](docs/TECHNICAL.md)** (en anglais).

## Compiler depuis les sources

Il faut [uv](https://docs.astral.sh/uv/) et HarfBuzz (`brew install harfbuzz`).

```bash
make setup      # .venv avec fontTools, fontmake, FontBakery, HarfBuzz
make upstream   # télécharge EB Garamond depuis google/fonts, sommes de contrôle vérifiées
make fonts      # construit les neuf polices et leurs sous-ensembles latins
make specimen   # range dist/ par famille, écrit les WOFF2 et les fichiers du spécimen
make check      # contrôles glyphe par glyphe sur chaque police
make qa         # FontBakery sur Vavin et sur EB Garamond, comparés
make zip        # release/Vavin-v1.1.zip
make readme-art # régénère les SVG de docs/assets/
```

`make serve` ouvre le spécimen sur <http://localhost:8731>. Les images du README sont tracées avec les contours des
polices construites : construisez les polices avant de les régénérer.

## Soutenir

Vavin est gratuite. Si elle vous est utile :

<a href="https://ko-fi.com/adrbn"><img src="docs/assets/btn-kofi-fr.svg" height="56" alt="Offrir un café sur Ko-fi"></a>

Une étoile sur le dépôt aide d'autres personnes à le trouver.

## Licence

Vavin est distribuée sous la [SIL Open Font License 1.1](OFL.txt). Vous pouvez l'utiliser dans tout projet,
commercial ou non, l'embarquer dans des applications et des documents, la modifier et la redistribuer. La seule
chose interdite est de vendre les polices seules. Copyright 2026 adrbn, avec le copyright d'EB Garamond conservé
comme la licence l'exige.

**« Vavin » est un nom de fonte réservé** (depuis la version 1.1) : vous pouvez modifier et redistribuer les polices,
mais une version modifiée doit porter un autre nom. L'OFL rend Vavin libre pour de bon : elle ne peut être ni placée
sous une autre licence ni vendue seule, car la licence d'EB Garamond s'étend à tout ce qui en dérive. Vavin dérive
d'EB Garamond seulement ; elle ne contient aucune donnée d'ITC Garamond ni d'aucune autre police propriétaire, et n'en reprend
qu'une proportion, qui est un fait et non un dessin protégé. [LEGAL.md](LEGAL.md) (en anglais) détaille les sources,
les obligations de la licence et la vérification du nom auprès des registres de marques.

## Crédits

- [EB Garamond](https://github.com/octaviopardo/EBGaramond12) de Georg Duffner et Octavio Pardo, sous SIL Open Font
  License 1.1, avec les glyphes de citation RCS de Deborah Khodanovich. Les contours de Vavin sont les leurs.
- Claude Garamont, dont EB Garamond reprend les romains du XVIᵉ siècle.
- Le nom vient de la rue Vavin, à Paris, qui descend vers le carrefour Vavin et ses cafés de Montparnasse.
- La carte *In Aura* est une vraie capture d'[Aura](https://github.com/adrbn/aura) sur la bibliothèque du
  développeur. Les textes français des cartes ont été écrits pour ce README.

<sub>Vavin n'est affiliée ni à ITC, ni à Monotype, ni à Google. Les marques citées appartiennent à leurs
propriétaires.</sub>
