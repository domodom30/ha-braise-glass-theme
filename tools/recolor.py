"""Déclinaison de Braise Glass dans une autre teinte.

Le thème source est pensé autour de l'orange « braise ». Une variante est obtenue
en faisant tourner la teinte des couleurs de marque (orange, rouge, or) et des
neutres chauds (charbon, cendre, textes) dans l'espace OKLCH : la luminosité
perçue est conservée, donc les contrastes WCAG restent du même ordre.

Ne sont PAS recolorées :
  • les couleurs hors de la bande chaude (bleus, verts, violets, roses…) ;
  • les couleurs fonctionnelles listées dans PROTECTED_VALUES (alerte ambre,
    erreur…), pour qu'une alerte ne ressemble jamais à un état « allumé » ;
  • les variables de PROTECTED_KEYS : couleurs nommées (`color: orange` doit
    rester orange quel que soit le thème).
"""

from __future__ import annotations

import colorsys
import math
import re

# Bande « chaude » (teinte HSL, en degrés) considérée comme couleur de marque.
WARM_HUE = (0.0, 46.0)
# En dessous, la couleur est un gris neutre : rien à tourner.
MIN_SATURATION = 0.04
# Assombrissement OKLab maximal accepté pour rester dans le gamut sans désaturer.
MAX_DARKEN = 0.12

PROTECTED_VALUES = {
    "FFD166", "D97706", "B45309", "F59E0B", "FFE07A",  # ambres / jaunes (alerte, ampoules)
    "C47F00", "A16207",                                # ampoules / jaune (mode clair)
    "B98A6E", "8B5E45",                                # brown-color
}
PROTECTED_KEYS = {
    "glass-orange", "orange-color", "deep-orange-color", "brown-color",
    "amber-color", "yellow-color", "red-color", "warning-color",
    "mush-rgb-orange", "mush-rgb-deep-orange", "mush-rgb-brown",
    "mush-rgb-amber", "mush-rgb-yellow", "mush-rgb-red", "mush-rgb-warning",
    "mush-rgb-danger",
}

HEX_RE = re.compile(r"#([0-9A-Fa-f]{6})\b")
# rgb(…)/rgba(…) et triplets nus "r, g, b" (rgb-*, mush-rgb-*, blue-glass-*-rgb)
TRIPLE_RE = re.compile(r"(?<![\d.])(\d{1,3}), (\d{1,3}), (\d{1,3})(?![\d.])")
KEY_RE = re.compile(r"^\s*([A-Za-z0-9_-]+):")


# --- OKLab / OKLCH (Björn Ottosson) -------------------------------------------
def _to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _rgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    r, g, b = _to_linear(r), _to_linear(g), _to_linear(b)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def _oklab_to_linear(L: float, a: float, b: float) -> tuple[float, float, float]:
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def rotate(rgb: tuple[int, int, int], degrees: float) -> tuple[int, int, int]:
    """Tourne la teinte OKLCH.

    Hors gamut sRGB, on assombrit d'abord légèrement (jusqu'à MAX_DARKEN) pour
    garder la saturation — les pourpres saturés sont plus sombres que les
    oranges — puis, à défaut, on réduit la chroma à luminosité d'origine.
    """
    L, a, b = _rgb_to_oklab(*(c / 255 for c in rgb))
    C, h = math.hypot(a, b), math.atan2(b, a) + math.radians(degrees)

    def ok(lin: tuple[float, float, float]) -> bool:
        return all(-1e-6 <= c <= 1 + 1e-6 for c in lin)

    for step in range(int(MAX_DARKEN * 100) + 1):
        lin = _oklab_to_linear(L - step / 100, C * math.cos(h), C * math.sin(h))
        if ok(lin):
            return tuple(round(min(1.0, max(0.0, _to_srgb(max(0.0, c)))) * 255) for c in lin)  # type: ignore[return-value]

    lo, hi = 0.0, C
    for _ in range(24):
        lin = _oklab_to_linear(L, hi * math.cos(h), hi * math.sin(h))
        if all(-1e-6 <= c <= 1 + 1e-6 for c in lin):
            break
        mid = (lo + hi) / 2
        lin = _oklab_to_linear(L, mid * math.cos(h), mid * math.sin(h))
        if all(-1e-6 <= c <= 1 + 1e-6 for c in lin):
            lo = mid
        else:
            hi = mid
    else:
        lin = _oklab_to_linear(L, lo * math.cos(h), lo * math.sin(h))
    return tuple(round(min(1.0, max(0.0, _to_srgb(max(0.0, c)))) * 255) for c in lin)  # type: ignore[return-value]


def is_brand(rgb: tuple[int, int, int]) -> bool:
    if "%02X%02X%02X" % rgb in PROTECTED_VALUES:
        return False
    h, _, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return s >= MIN_SATURATION and WARM_HUE[0] <= h * 360 <= WARM_HUE[1]


def _shift(rgb: tuple[int, int, int], degrees: float) -> tuple[int, int, int]:
    return rotate(rgb, degrees) if is_brand(rgb) else rgb


def recolor_line(line: str, degrees: float) -> str:
    def hex_sub(m: re.Match) -> str:
        h = m.group(1)
        rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
        out = "#%02X%02X%02X" % _shift(rgb, degrees)  # type: ignore[arg-type]
        return out if h.isupper() else out.lower()

    def triple_sub(m: re.Match) -> str:
        rgb = tuple(int(g) for g in m.groups())
        if max(rgb) > 255:
            return m.group(0)
        return "%d, %d, %d" % _shift(rgb, degrees)  # type: ignore[arg-type]

    return TRIPLE_RE.sub(triple_sub, HEX_RE.sub(hex_sub, line))


def recolor_yaml(text: str, degrees: float) -> str:
    out = []
    for line in text.splitlines(keepends=True):
        key = KEY_RE.match(line)
        if line.lstrip().startswith("#") or (key and key.group(1) in PROTECTED_KEYS):
            out.append(line)
        else:
            out.append(recolor_line(line, degrees))
    return "".join(out)


def recolor_svg(text: str, degrees: float) -> str:
    return HEX_RE.sub(lambda m: "#%02X%02X%02X" % _shift(tuple(int(m.group(1)[i : i + 2], 16) for i in (0, 2, 4)), degrees), text)  # type: ignore[arg-type]
