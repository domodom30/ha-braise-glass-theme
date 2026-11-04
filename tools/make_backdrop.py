"""Génère les décors SVG de Braise Glass (sombre et clair).

Usage : python make_backdrop.py [dossier_de_sortie]
        (par défaut : ../assets)

Reprend le décor « Ember » de Domo TV (Glass.java, ember()) :
fond noir fumé, grande lueur orange en bas, deux lueurs secondaires,
sol de lignes en perspective, anneau lumineux de la scène, braises qui montent.
Tout est dessiné en unités 1920×1080 ; l'image est ancrée en bas
(preserveAspectRatio xMidYMax slice) pour garder le sol visible en portrait.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

DARK = {
    "base": ("#0C0A0B", "#070607", "#0B0706"),
    "blobs": [  # x, y, rayon, couleur, alpha
        (960, 1260, 1150, "#FF4D12", 0.60),
        (1720, 120, 620, "#FF7A1A", 0.19),
        (140, 560, 520, "#FF3B30", 0.15),
    ],
    "line": "#FF8A3D",
    "line_alpha": 1.0,
    "ring": "#FF6A1F",
    "ring_alpha": (0.47, 0.86),
    "embers": 140,
    "ember_colors": ("#FF9A3D", "#FFC27A"),
    "ember_alpha": 1.0,
}

LIGHT = {
    "base": ("#FCF7F2", "#F8EEE5", "#F4E6DA"),
    "blobs": [
        (960, 1260, 1150, "#FF7A2E", 0.34),
        (1720, 120, 640, "#FFC27A", 0.34),
        (140, 560, 540, "#FF8A80", 0.16),
    ],
    "line": "#E0560F",
    "line_alpha": 0.75,
    "ring": "#FF6A1F",
    "ring_alpha": (0.30, 0.65),
    "embers": 90,
    "ember_colors": ("#FF8A3D", "#F5A524"),
    "ember_alpha": 0.7,
}


def f(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".")


def build(p: dict) -> str:
    r = random.Random(7)
    out: list[str] = []
    a = out.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" '
      'preserveAspectRatio="xMidYMax slice">')
    a("<defs>")
    b0, b1, b2 = p["base"]
    a('<linearGradient id="base" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="400" y2="1080">'
      f'<stop offset="0" stop-color="{b0}"/><stop offset="0.5" stop-color="{b1}"/>'
      f'<stop offset="1" stop-color="{b2}"/></linearGradient>')
    for i, (_, _, _, color, alpha) in enumerate(p["blobs"]):
        a(f'<radialGradient id="blob{i}">'
          f'<stop offset="0" stop-color="{color}" stop-opacity="{f(alpha)}"/>'
          f'<stop offset="0.45" stop-color="{color}" stop-opacity="{f(alpha * 0.45)}"/>'
          f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    for i, color in enumerate(p["ember_colors"]):
        a(f'<radialGradient id="halo{i}"><stop offset="0" stop-color="{color}" stop-opacity="0.55"/>'
          f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    a('<filter id="glow" x="-20%" y="-60%" width="140%" height="220%">'
      '<feGaussianBlur stdDeviation="15"/></filter>')
    a('<clipPath id="floor"><rect x="0" y="700" width="1920" height="380"/></clipPath>')
    a("</defs>")

    a('<rect width="1920" height="1080" fill="url(#base)"/>')
    for i, (x, y, rad, _, _) in enumerate(p["blobs"]):
        a(f'<circle cx="{x}" cy="{y}" r="{rad}" fill="url(#blob{i})"/>')

    # Sol de lignes en perspective, sous les cartes.
    la = p["line_alpha"]
    a(f'<g clip-path="url(#floor)" stroke="{p["line"]}" stroke-width="1.4">')
    for i in range(-14, 15):
        op = (0.16 - abs(i) * 0.006) * la
        a(f'<line x1="960" y1="420" x2="{960 + i * 220}" y2="1080" stroke-opacity="{f(op)}"/>')
    for i in range(9):
        y = 700 + i * i * 5.2
        op = (0.05 + i * 0.015) * la
        a(f'<line x1="0" y1="{f(y)}" x2="1920" y2="{f(y)}" stroke-opacity="{f(op)}"/>')
    a("</g>")

    # Anneau lumineux de la scène : la lueur floue, puis le fil net.
    ga, la2 = p["ring_alpha"]
    ring = 'cx="960" cy="960" rx="520" ry="100" fill="none"'
    a(f'<ellipse {ring} stroke="{p["ring"]}" stroke-width="18" stroke-opacity="{f(ga)}" filter="url(#glow)"/>')
    a(f'<ellipse {ring} stroke="{p["ring"]}" stroke-width="3" stroke-opacity="{f(la2)}"/>')

    # Braises qui montent.
    ea = p["ember_alpha"]
    halos, dots = [], []
    for _ in range(p["embers"]):
        x = r.random() * 1920
        y = 1080 - r.random() * r.random() * 900
        size = 0.8 + r.random() * 2.2
        k = 0 if r.random() < 0.5 else 1
        color = p["ember_colors"][k]
        halos.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(size * 3.5)}" fill="url(#halo{k})"/>')
        op = (140 + r.randrange(115)) / 255 * ea
        dots.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(size)}" fill="{color}" fill-opacity="{f(op)}"/>')
    a("<g>" + "".join(halos) + "</g>")
    a("<g>" + "".join(dots) + "</g>")
    a("</svg>")
    return "\n".join(out) + "\n"


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, palette in (("braise_glass_dark.svg", DARK), ("braise_glass_light.svg", LIGHT)):
        path = out / name
        path.write_text(build(palette), encoding="utf-8", newline="\n")
        print(f"{path} ({path.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
