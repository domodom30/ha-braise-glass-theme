"""Validation du thème Braise Glass.

Usage : python validate_theme.py [chemin/vers/braise_glass.yaml]

Vérifie :
  1. Syntaxe YAML (ancres, alias et merge keys `<<:` compris)
  2. Schéma attendu par Home Assistant (frontend.themes) :
       { nom_theme: { variable: "str", modes: { light|dark: { variable: "str" } } } }
  3. Noms de variables CSS valides
  4. card-mod-theme == nom du thème
  5. Couleurs hex valides
  6. Toutes les références var(--glass-*) pointent vers un token défini
  7. Accolades CSS équilibrées dans les blocs card-mod
  8. Contrastes WCAG des textes principaux sur les fonds principaux
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

DEFAULT = Path(__file__).resolve().parent.parent / "themes" / "braise_glass.yaml"
KEY_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
VAR_RE = re.compile(r"var\(--([a-zA-Z0-9_-]+)")
MODES = {"light", "dark"}
STATE_COLORS = (
    "success-color", "warning-color", "error-color", "info-color",
    "state-active-color", "state-light-active-color", "state-climate-heat-color",
    "state-climate-cool-color", "state-sun-above_horizon-color",
    "blue-color", "light-blue-color", "cyan-color", "teal-color", "green-color",
    "light-green-color", "lime-color", "yellow-color", "amber-color", "orange-color",
    "deep-orange-color", "red-color", "pink-color", "purple-color", "deep-purple-color",
    "indigo-color", "brown-color", "grey-color", "blue-grey-color",
    *(f"graph-color-{i}" for i in range(1, 13)),
)

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    h = value.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def luminance(value: str) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(c) for c in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def check_vars(theme: str, scope: str, variables: dict) -> None:
    for key, value in variables.items():
        if not isinstance(key, str) or not KEY_RE.match(key):
            err(f"[{theme}/{scope}] nom de variable invalide : {key!r}")
        if not isinstance(value, str):
            err(f"[{theme}/{scope}] {key} doit être une chaîne (reçu {type(value).__name__})")
            continue
        if value.startswith("#") and not HEX_RE.match(value):
            err(f"[{theme}/{scope}] {key} : couleur hex invalide {value!r}")
        if value.count("(") != value.count(")"):
            err(f"[{theme}/{scope}] {key} : parenthèses déséquilibrées")
        if key.startswith("card-mod-") and value.count("{") != value.count("}"):
            err(f"[{theme}/{scope}] {key} : accolades CSS déséquilibrées")


def main(path: Path) -> int:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        err("Le fichier doit contenir un dictionnaire de thèmes")
        return report()

    for theme, conf in data.items():
        if not isinstance(conf, dict):
            err(f"[{theme}] la définition doit être un dictionnaire")
            continue
        modes = conf.get("modes", {})
        base = {k: v for k, v in conf.items() if k != "modes"}
        check_vars(theme, "base", base)

        if not isinstance(modes, dict) or set(modes) - MODES:
            err(f"[{theme}] 'modes' ne peut contenir que light/dark")
            modes = {}
        for mode, mvars in modes.items():
            if not isinstance(mvars, dict):
                err(f"[{theme}/{mode}] doit être un dictionnaire")
                continue
            check_vars(theme, mode, mvars)

        cm = base.get("card-mod-theme")
        if cm is not None and cm != theme:
            err(f"[{theme}] card-mod-theme={cm!r} doit être égal au nom du thème")

        # Références var(--glass-*) résolues pour chaque mode
        for mode in modes or {"(none)": {}}:
            effective = {**base, **modes.get(mode, {})}
            for key, value in effective.items():
                if not isinstance(value, str):
                    continue
                for ref in VAR_RE.findall(value):
                    if ref.startswith("glass-") and ref not in effective:
                        err(f"[{theme}/{mode}] {key} référence --{ref} non défini")

            # Contrastes
            text = effective.get("primary-text-color")
            text2 = effective.get("secondary-text-color")
            bg = effective.get("primary-background-color")
            primary = effective.get("primary-color")
            pairs = [
                ("primary-text / primary-bg", text, bg, 7.0),
                ("secondary-text / primary-bg", text2, bg, 4.5),
                ("primary-color / primary-bg", primary, bg, 3.0),
            ]
            # Couleurs d'état / nommées : icônes et textes d'état (WCAG 1.4.11, 3:1)
            for key in STATE_COLORS:
                pairs.append((key, effective.get(key), bg, 3.0))
            for label, fg, bgc, minimum in pairs:
                if fg and bgc and HEX_RE.match(fg) and HEX_RE.match(bgc):
                    ratio = contrast(fg, bgc)
                    status = "OK " if ratio >= minimum else "BAS"
                    print(f"  [{theme}/{mode}] contraste {label:30s} {ratio:5.2f}:1 (min {minimum}) {status}")
                    if ratio < minimum:
                        warnings.append(f"[{theme}/{mode}] contraste {label} = {ratio:.2f}")

        n_base = len(base)
        n_modes = {m: len(v) for m, v in modes.items() if isinstance(v, dict)}
        print(f"✔ {theme}: {n_base} variables communes, modes {n_modes}")

    return report()


def report() -> int:
    for w in warnings:
        print(f"⚠ {w}")
    for e in errors:
        print(f"✘ {e}")
    if errors:
        print(f"\n{len(errors)} erreur(s).")
        return 1
    print("\nValidation réussie : aucune erreur.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT))
