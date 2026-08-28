"""NEURAL GOLD v3.2 visual identity renderer."""
from __future__ import annotations

from pathlib import Path
import hashlib
import html

BASE = Path(__file__).resolve().parent
ASSET_DIR = BASE / "assets"
LOGO_SVG = ASSET_DIR / "neural_gold_logo_v3_2.svg"
CACHE_DIR = Path("/tmp/neural_gold_visuals")

THEMES = {
    "home": ("NEURAL GOLD", "PREMIUM XAU/USD MARKET INTELLIGENCE", "HOME"),
    "price": ("LIVE GOLD FEED", "XAU/USD REAL-TIME MARKET", "GOLD"),
    "matrix": ("ALPHA-SENTI MATRIX", "MARKET INTELLIGENCE", "MATRIX"),
    "signal": ("NEURAL-SIGNAL", "XAU/USD MARKET SIGNAL", "SIGNAL"),
    "account": ("ACCOUNT STATUS", "PREMIUM ACCESS CONTROL", "ACCOUNT"),
    "token": ("ACTIVATE TOKEN", "SECURE ACCESS ACTIVATION", "TOKEN"),
    "access": ("PREMIUM ACCESS", "7 / 14 / 30 DAYS", "ACCESS"),
    "checkout": ("CHECKOUT", "SECURE PAYMENT ROUTE", "CHECKOUT"),
    "success": ("PAYMENT CONFIRMED", "ACCESS FULFILLMENT", "SUCCESS"),
}


def _esc(v: str) -> str:
    return html.escape(v)


def _svg_for(key: str) -> str:
    title, subtitle, badge = THEMES.get(key, THEMES["home"])
    logo = LOGO_SVG.read_text(encoding="utf-8")
    logo_body = logo.split("<svg", 1)[1].split(">", 1)[1].rsplit("</svg>", 1)[0]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
<defs>
  <radialGradient id="bg"><stop stop-color="#17130a"/><stop offset="1" stop-color="#020203"/></radialGradient>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff0a0"/><stop offset=".35" stop-color="#d69a19"/><stop offset=".65" stop-color="#fff1a1"/><stop offset="1" stop-color="#8c5707"/></linearGradient>
</defs>
<rect width="1200" height="675" fill="url(#bg)"/>
<path d="M0 570 C180 470 310 610 470 505 S760 420 1200 525" fill="none" stroke="#5f430f" stroke-width="2" opacity=".7"/>
<path d="M0 610 C220 510 360 650 540 535 S820 460 1200 570" fill="none" stroke="#a87517" stroke-width="1" opacity=".55"/>
<g stroke="#8f6718" stroke-width="1" opacity=".5">
  <path d="M700 110h370v60H820v55h250"/><path d="M760 275h290v55H910v55h160"/>
  <path d="M610 500h190v-70h150v-65h150"/>
</g>
<g fill="#e2ad3a" opacity=".8">
  <circle cx="700" cy="110" r="3"/><circle cx="820" cy="170" r="3"/><circle cx="1070" cy="170" r="3"/>
  <circle cx="760" cy="275" r="3"/><circle cx="910" cy="330" r="3"/><circle cx="1070" cy="330" r="3"/>
  <circle cx="800" cy="500" r="3"/><circle cx="950" cy="430" r="3"/><circle cx="1100" cy="365" r="3"/>
</g>
<g transform="translate(55 55) scale(.42)">{logo_body}</g>
<text x="315" y="125" fill="url(#gold)" font-family="Arial,sans-serif" font-size="52" font-weight="800" letter-spacing="2">NEURAL GOLD <tspan font-size="30">v3.2</tspan></text>
<text x="318" y="170" fill="#eee5c9" font-family="Arial,sans-serif" font-size="25" letter-spacing="2">{_esc(title)}</text>
<text x="318" y="208" fill="#cfa83f" font-family="Arial,sans-serif" font-size="17" letter-spacing="3">{_esc(subtitle)}</text>
<rect x="318" y="235" width="280" height="48" rx="24" fill="#080807" stroke="url(#gold)" stroke-width="2"/>
<text x="458" y="266" text-anchor="middle" fill="#f3d778" font-family="Arial,sans-serif" font-size="16" font-weight="700" letter-spacing="3">{_esc(badge)}</text>
<text x="318" y="620" fill="#a9893f" font-family="Arial,sans-serif" font-size="15" letter-spacing="4">SPEED  •  PRECISION  •  ACCURACY</text>
<text x="1180" y="620" text-anchor="end" fill="#6f5a29" font-family="Arial,sans-serif" font-size="13" letter-spacing="2">XAU/USD  //  MARKET INTELLIGENCE</text>
</svg>'''


def visual_path(key: str) -> str | None:
    if key not in THEMES or not LOGO_SVG.exists():
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((LOGO_SVG.read_text(encoding="utf-8") + key).encode()).hexdigest()[:12]
    target = CACHE_DIR / f"{key}_{digest}.png"
    if target.exists():
        return str(target)
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=_svg_for(key).encode("utf-8"), write_to=str(target), output_width=900, output_height=506)
        return str(target)
    except Exception:
        return None
