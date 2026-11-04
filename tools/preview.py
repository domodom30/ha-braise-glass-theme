"""Génère les aperçus du README (assets/preview_dark.png, assets/preview_light.png).

Usage : python tools/preview.py [chemin/vers/chrome]

Construit une page de démonstration (cartes façon Home Assistant) stylée
uniquement par les variables du thème distribué, puis la capture avec
Chrome en mode headless.
"""

from __future__ import annotations

import html
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

TILES = [
    ("mdi-lightbulb", "Salon", "Allumée · 80 %", "light"),
    ("mdi-thermometer", "Chambre", "21,4 °C", ""),
    ("mdi-lock", "Entrée", "Verrouillée", "lock"),
    ("mdi-fan", "Ventilateur", "Allumé", "on"),
    ("mdi-television", "Téléviseur", "Éteint", ""),
    ("mdi-water-boiler", "Chauffe-eau", "Heures creuses", "on"),
]

PAGE = """<!doctype html><html style="{vars}"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/css/materialdesignicons.min.css">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; min-height: 100vh; background: var(--lovelace-background); color: var(--primary-text-color);
  font-family: var(--ha-font-family-body); }}
header {{ height: 56px; display: flex; align-items: center; gap: 24px; padding: 0 20px; font-size: 20px;
  background: var(--app-header-background-color); backdrop-filter: var(--app-header-backdrop-filter);
  border-bottom: var(--app-header-border-bottom); }}
header .tabs {{ display: flex; gap: 22px; height: 100%; font-size: 14px; color: var(--secondary-text-color); }}
header .tabs > * {{ display: flex; align-items: center; border-bottom: 2px solid transparent; }}
header .tabs b {{ color: var(--ha-tab-active-text-color); border-bottom-color: var(--ha-tab-indicator-color); }}
main {{ padding: 24px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; max-width: 1180px; margin: 0 auto; }}
.card {{ background: var(--ha-card-background); border: 1px solid var(--ha-card-border-color); border-radius: var(--ha-card-border-radius);
  box-shadow: var(--ha-card-box-shadow); backdrop-filter: var(--ha-card-backdrop-filter); padding: 14px 16px; }}
.tile {{ display: flex; align-items: center; gap: 12px; }}
.ico {{ width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; font-size: 22px;
  background: color-mix(in srgb, var(--c, var(--disabled-color)) 18%, transparent); color: var(--c, var(--secondary-text-color)); }}
.name {{ font-weight: 600; font-size: 14px; }}
.state {{ font-size: 12px; color: var(--secondary-text-color); }}
.wide {{ grid-column: span 3; display: flex; gap: 18px; align-items: center; }}
.hero {{ background: var(--glass-accent-surface); color: var(--glass-on-accent); border-color: var(--glass-accent-border); }}
.big {{ font-size: 34px; font-weight: 600; }}
.bar {{ flex: 1; height: 8px; border-radius: 4px; background: var(--ha-bar-background-color); overflow: hidden; }}
.bar i {{ display: block; height: 100%; width: 64%; background: var(--ha-bar-primary-color); }}
.btn {{ padding: 8px 16px; border-radius: 999px; background: var(--primary-color); color: var(--text-primary-color); font-weight: 600; font-size: 14px; }}
.sw {{ width: 36px; height: 20px; border-radius: 10px; background: var(--switch-checked-track-color); position: relative; }}
.sw::after {{ content: ""; position: absolute; right: 2px; top: 2px; width: 16px; height: 16px; border-radius: 50%; background: var(--switch-checked-button-color); }}
</style></head><body>
<header><span class="mdi mdi-menu"></span><span>Maison</span><div class="tabs"><b>Appartement</b><span>Énergie</span><span>Télévision</span></div></header>
<main>
<div class="card wide hero"><span class="mdi mdi-weather-night" style="font-size:40px"></span>
<div><div class="big">18,6 °C</div><div>Nuit claire · Lyon</div></div><div style="flex:1"></div><div>Humidité 62 %</div></div>
{tiles}
<div class="card wide"><span class="mdi mdi-lightning-bolt" style="font-size:26px;color:var(--energy-grid-consumption-color)"></span>
<div style="min-width:180px"><div class="name">Consommation du mois</div><div class="state">212 kWh · 43,80 €</div></div>
<div class="bar"><i></i></div><div class="sw"></div><div class="btn">Détails</div></div>
</main></body></html>"""


def theme_vars(mode: str) -> str:
    themes = yaml.safe_load((ROOT / "themes" / "braise_glass.yaml").read_text(encoding="utf-8"))
    t = themes["Braise Glass"]
    v = {k: x for k, x in t.items() if k != "modes" and isinstance(x, str) and not k.startswith("card-mod")}
    v.update(t["modes"][mode])
    return html.escape(";".join(f"--{k}:{x}" for k, x in v.items()))


def tiles() -> str:
    color = {"light": "var(--state-light-active-color)", "lock": "var(--state-lock-locked-color)", "on": "var(--state-active-color)"}
    out = []
    for icon, name, state, kind in TILES:
        style = f' style="--c:{color[kind]}"' if kind else ""
        out.append(f'<div class="card tile"><div class="ico"{style}><span class="mdi {icon}"></span></div>'
                   f'<div><div class="name">{name}</div><div class="state">{state}</div></div></div>')
    return "\n".join(out)


def main(chrome: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for mode in ("dark", "light"):
            page = Path(tmp) / f"{mode}.html"
            page.write_text(PAGE.format(vars=theme_vars(mode), tiles=tiles()), encoding="utf-8")
            out = ROOT / "assets" / f"preview_{mode}.png"
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1280,640",
                            "--virtual-time-budget=4000", f"--screenshot={out}", page.as_uri()],
                           check=True, capture_output=True)
            print(out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else CHROME)
