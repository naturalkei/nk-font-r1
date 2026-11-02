"""Rewrite the name table for an NK family member."""

from __future__ import annotations

from fontTools.ttLib import TTFont

from .config import RESERVED_NAMES

COPYRIGHT = (
    "Copyright 2026 naturalk (nk-font). "
    "Copyright 2020 The JetBrains Mono Project Authors. "
    "Copyright 2014-2025 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'."
)
LICENSE = "This Font Software is licensed under the SIL Open Font License, Version 1.1."
LICENSE_URL = "https://openfontlicense.org"
RIBBI = {"Regular", "Bold", "Italic", "Bold Italic"}


def set_names(
    font: TTFont,
    family: str,
    style: str,
    version: str,
    weight_class: int,
    copyright: str = COPYRIGHT,
) -> None:
    for word in RESERVED_NAMES:
        if word.lower() in family.lower():
            raise ValueError(f"family name contains reserved font name {word!r}")

    ps_family = family.replace(" ", "")
    ps_style = style.replace(" ", "")
    if style in RIBBI:
        legacy_family, legacy_style = family, style
    else:
        legacy_family, legacy_style = f"{family} {style}", "Regular"

    names = {
        0: copyright,
        1: legacy_family,
        2: legacy_style,
        3: f"{version};NK;{ps_family}-{ps_style}",
        4: f"{family} {style}" if style != "Regular" else family,
        5: f"Version {version}",
        6: f"{ps_family}-{ps_style}",
        13: LICENSE,
        14: LICENSE_URL,
        16: family,
        17: style,
    }
    table = font["name"]
    table.names = []
    for name_id, value in names.items():
        table.setName(value, name_id, 3, 1, 0x409)

    os2 = font["OS/2"]
    os2.usWeightClass = weight_class
    bold = "Bold" in style
    italic = "Italic" in style
    sel = os2.fsSelection & ~0b1100001  # clear ITALIC, BOLD, REGULAR
    sel |= (1 if italic else 0) | (0b100000 if bold else 0)
    if not bold and not italic:
        sel |= 0b1000000
    os2.fsSelection = sel
    font["head"].macStyle = (1 if bold else 0) | (2 if italic else 0)
    major, minor = (version.split(".") + ["0"])[:2]
    font["head"].fontRevision = float(f"{int(major)}.{int(minor):03d}")
