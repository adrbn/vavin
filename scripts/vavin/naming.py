"""Renaming a derived font, completely.

The half-done rename is the classic way to ship a broken OFL derivative: you
change name ID 1 and 4, the font installs as "Vavin", and name ID 3 still
says "EB Garamond" so the OS caches it under the old identity and two fonts
fight over the same slot.

The only reliable method is to *delete every name record* and write a fresh
set. That is what this module does. It also rebuilds STAT, because a static
instance cut from a variable font carries a STAT table whose AxisValue records
point at name IDs that no longer exist after the purge.

On the Reserved Font Name rule, see ../../LEGAL.md - EB Garamond does not
declare one, so renaming is a choice here rather than an obligation, but it is
still the right choice and the mechanics are identical either way.
"""

from __future__ import annotations

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont

WINDOWS = (3, 1, 0x409)  # platformID, platEncID, langID

OFL_LICENSE_DESCRIPTION = (
    "This Font Software is licensed under the SIL Open Font License, "
    "Version 1.1. This license is available with a FAQ at: "
    "https://openfontlicense.org"
)
OFL_LICENSE_URL = "https://openfontlicense.org"

# OS/2 fsSelection bits
FS_ITALIC = 1 << 0
FS_BOLD = 1 << 5
FS_REGULAR = 1 << 6
FS_USE_TYPO_METRICS = 1 << 7

# head.macStyle bits
MAC_BOLD = 1 << 0
MAC_ITALIC = 1 << 1


def build_name_records(
    *,
    family: str,
    style: str,
    ps_name: str,
    version: str,
    copyright_: str,
    description: str,
    designer: str,
    designer_url: str,
    vendor_url: str,
    vendor_id: str,
) -> dict[int, str]:
    """The complete name table for one style.

    Name IDs 16/17 (typographic family/subfamily) are only written for a
    style outside the RIBBI four, such as Display Black. Such a style gets its
    own legacy family ("Vavin Display Black", subfamily "Regular"), or Windows
    would see two "Vavin Display Regular" fonts and hide one. Including 16/17
    on RIBBI styles only confuses older Windows applications.
    """
    ribbi = style in ("Regular", "Italic", "Bold", "Bold Italic")
    typographic = {} if ribbi else {16: family, 17: style}
    return typographic | {
        0: copyright_,
        1: family if ribbi else f"{family} {style}",
        2: style if ribbi else "Regular",
        3: f"{version.replace('Version ', '')};{vendor_id};{ps_name}",
        4: f"{family} {style}",
        5: version,
        6: ps_name,
        # 7 (trademark) is intentionally omitted: we assert no trademark, and
        # inheriting the upstream's would be wrong.
        8: designer,
        9: designer,
        10: description,
        11: vendor_url,
        12: designer_url,
        13: OFL_LICENSE_DESCRIPTION,
        14: OFL_LICENSE_URL,
    }


def rename(
    font: TTFont,
    *,
    family: str,
    style: str,
    ps_name: str,
    version: str,
    font_revision: float,
    copyright_: str,
    description: str,
    designer: str,
    designer_url: str,
    vendor_url: str,
    vendor_id: str,
    weight_class: int,
    is_bold: bool,
    is_italic: bool = False,
) -> list[str]:
    """Rewrite identity end to end. Returns a list of leftover references."""
    records = build_name_records(
        family=family,
        style=style,
        ps_name=ps_name,
        version=version,
        copyright_=copyright_,
        description=description,
        designer=designer,
        designer_url=designer_url,
        vendor_url=vendor_url,
        vendor_id=vendor_id,
    )

    name = font["name"]
    name.names = []  # purge, do not patch
    for name_id, value in records.items():
        name.setName(value, name_id, *WINDOWS)

    os2 = font["OS/2"]
    os2.usWeightClass = weight_class
    os2.achVendID = vendor_id[:4].ljust(4)
    # fsType 0 = installable embedding. Anything else contradicts the OFL,
    # which permits embedding without restriction.
    os2.fsType = 0

    os2.fsSelection &= ~(FS_BOLD | FS_REGULAR | FS_ITALIC)
    if is_bold:
        os2.fsSelection |= FS_BOLD
    elif not is_italic:
        os2.fsSelection |= FS_REGULAR
    if is_italic:
        os2.fsSelection |= FS_ITALIC
    os2.fsSelection |= FS_USE_TYPO_METRICS

    head = font["head"]
    head.fontRevision = font_revision
    head.macStyle &= ~(MAC_BOLD | MAC_ITALIC)
    if is_bold:
        head.macStyle |= MAC_BOLD
    if is_italic:
        head.macStyle |= MAC_ITALIC

    _rebuild_stat(font, family, style, weight_class, is_italic)

    # buildStatTable adds its own axis and value name records, and they land
    # on the Mac platform as well as Windows. Modern practice - and the Google
    # Fonts spec - is to ship no platform 1 records at all: they are legacy,
    # they double the table, and their encoding is a source of mojibake.
    # Strip them after STAT, not before, or they come straight back.
    font["name"].names = [r for r in font["name"].names if r.platformID != 1]

    return audit(font, forbidden=("EB Garamond", "EBGaramond", "Garamond"))


def _rebuild_stat(
    font: TTFont, family: str, style: str, weight_class: int, is_italic: bool
) -> None:
    """A static instance still carries STAT pointing at purged name IDs.

    The italic has to be declared on its own `ital` axis. Folding it into the
    weight axis - a value named "Bold Italic" on wght - is what FontBakery's
    STAT_strings check calls `bad-italic`, and it is genuinely wrong: an
    application reading STAT to build a family menu would then offer "Bold
    Italic" as a weight alongside "Bold", instead of as a posture.
    """
    if "fvar" in font:
        return  # not our business for a variable font

    # The weight axis carries the weight alone: "Bold Italic" is Bold on wght
    # and Italic on ital.
    weight_name = style.replace("Italic", "").strip() or "Regular"

    axes = [
        {
            "tag": "wght",
            "name": "Weight",
            "values": [
                {
                    "value": weight_class,
                    "name": weight_name,
                    # 0x2 = ElidableAxisValueName: "Regular" should not show
                    # up in a composed style name.
                    "flags": 0x2 if weight_name == "Regular" else 0x0,
                }
            ],
        },
        {
            "tag": "ital",
            "name": "Italic",
            "values": [
                {
                    "value": 1 if is_italic else 0,
                    "name": "Italic" if is_italic else "Roman",
                    "flags": 0x0 if is_italic else 0x2,
                }
            ],
        },
    ]
    try:
        buildStatTable(font, axes, elidedFallbackName=2)
    except Exception:
        # A broken STAT is worse than none on a small static family.
        if "STAT" in font:
            del font["STAT"]


#: Name IDs that *identify* the font. These must never carry the upstream
#: name. Everything else (0 copyright, 10 description, 13 license) not only
#: may but SHOULD mention it - the OFL requires the original copyright notice
#: to travel with the derivative, and the OFL FAQ explicitly allows saying
#: "based on X" in the description.
IDENTIFYING_NAME_IDS = (1, 2, 3, 4, 6, 16, 17, 18, 20, 21, 22, 25)


def audit(font: TTFont, *, forbidden: tuple[str, ...]) -> list[str]:
    """Find any surviving reference to a name we are not allowed to ship.

    Only the identifying name IDs are checked. Attribution in the copyright
    and description strings is required by the licence, not a leak.
    """
    hits = []
    for record in font["name"].names:
        if record.nameID not in IDENTIFYING_NAME_IDS:
            continue
        try:
            value = record.toUnicode()
        except Exception:
            continue
        for needle in forbidden:
            if needle.lower() in value.lower():
                hits.append(f"name ID {record.nameID}: {value!r} contains {needle!r}")

    if "CFF " in font:
        cff = font["CFF "].cff
        for font_name in cff.fontNames:
            for needle in forbidden:
                if needle.lower() in font_name.lower():
                    hits.append(f"CFF fontName {font_name!r} contains {needle!r}")

    return hits
