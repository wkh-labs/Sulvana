"""WKH Labs logo, based on the Gemini layout the team liked, with Khmer-correct towers.
Run: python3 make_logo.py   (writes the SVGs; render PNGs with rsvg-convert)

Palette: Deep Indigo #1B1947 (temple, type), Lotus Pink #FF5E97→#FF94B9 (sun, accents),
iridescent #FF5E97→#B56BFF→#00D2FF (pond reflection).
"""
import math

INDIGO, PINK, PINK_LIGHT = "#1B1947", "#FF5E97", "#FF94B9"
HORIZON = 175

def prasat(x, base, top, w, notches=2):
    """Khmer corn-cob tower: straight-sided body, then a smooth tapering bud to a rounded point,
    with shallow tier notches (no onion necks)."""
    h = base - top
    body = h * 0.34
    pts = [(x - w / 2, base), (x - w / 2, base - body)]
    steps = 20
    notch_at = {round(steps * (k + 1) / (notches + 1)) for k in range(notches)}
    for i in range(1, steps + 1):
        t = i / steps
        y = base - body - t * (h - body)
        half = w / 2 * math.cos(t * math.pi / 2) ** 0.75   # full at the body, rounded taper to the tip
        if i in notch_at:
            pts.append((x - half * 0.86, y + 1.2))
        pts.append((x - max(half, 0.4), y))
    pts.append((x, top))
    right = [(2 * x - px, py) for px, py in reversed(pts[:-1])]
    return "M" + " L".join(f"{px:.2f} {py:.2f}" for px, py in pts + right) + "Z"

def temple():
    """Gemini's silhouette: terrace, galleries, sloped gallery roofs, five towers in the same places."""
    return "".join([
        '<rect x="62" y="166" width="216" height="9.5" rx="1.5"/>',
        '<rect x="74" y="156" width="192" height="12" rx="1"/>',
        '<rect x="98" y="146" width="144" height="12" rx="1"/>',
        '<polygon points="80,156 96,142 156,142 156,156"/>',
        '<polygon points="260,156 244,142 184,142 184,156"/>',
        f'<path d="{prasat(96, 156, 110, 17)}"/>',
        f'<path d="{prasat(131, 150, 88, 23)}"/>',
        f'<path d="{prasat(170, 148, 60, 33, 3)}"/>',
        f'<path d="{prasat(209, 150, 88, 23)}"/>',
        f'<path d="{prasat(244, 156, 110, 17)}"/>',
    ])

def mark(uid, ink=INDIGO):
    shapes = temple()
    # Ripples: Gemini's dashed bands, now cut from the temple's real mirror image.
    bands = "".join(f'<rect x="40" y="{y:.1f}" width="260" height="3.4" rx="1.7"/>'
                    for y in [HORIZON + 4 + 7.4 * k for k in range(9)])
    return f'''
  <defs>
    <linearGradient id="sun{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{PINK_LIGHT}"/></linearGradient>
    <linearGradient id="iri{uid}" gradientUnits="userSpaceOnUse" x1="62" y1="0" x2="278" y2="0">
      <stop offset="0" stop-color="#FF5E97"/><stop offset=".5" stop-color="#B56BFF"/><stop offset="1" stop-color="#00D2FF"/></linearGradient>
    <linearGradient id="fade{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity=".12"/></linearGradient>
    <mask id="ripples{uid}"><g fill="url(#fade{uid})">{bands}</g></mask>
    <clipPath id="sky{uid}"><rect width="360" height="{HORIZON}"/></clipPath>
  </defs>
  <circle cx="170" cy="140" r="70" fill="url(#sun{uid})" clip-path="url(#sky{uid})"/>
  <g fill="{ink}">{shapes}</g>
  <g mask="url(#ripples{uid})"><g transform="translate(0 {HORIZON + 3 + HORIZON * 0.58:.1f}) scale(1 -.58)" fill="url(#iri{uid})">{shapes}</g></g>'''

FONT = "Inter, Montserrat, 'Helvetica Neue', 'Adwaita Sans', 'Noto Sans', sans-serif"

def wordmark(theme):
    bg, ink, labs, sub, divider = (("#FFFFFF", INDIGO, "#2A2760", "#4A4775", INDIGO) if theme == "light"
                                   else (INDIGO, "#F5F3FF", "#DDD9FF", "#B9B6E0", "#F5F3FF"))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 300" width="820" height="300">
  <rect width="820" height="300" fill="{bg}"/>
  <g transform="translate(15 0)">{mark(theme, INDIGO if theme == "light" else "#F5F3FF")}</g>
  <line x1="335" y1="92" x2="335" y2="208" stroke="{divider}" stroke-width="1.5" opacity=".22"/>
  <g transform="translate(370 0)">
    <text x="0" y="162" font-family="{FONT}" font-size="76" fill="{ink}"><tspan font-weight="800" letter-spacing="-1.5">WKH</tspan><tspan dx="18" font-weight="300" letter-spacing="-0.5" fill="{labs}">Labs</tspan></text>
    <text x="3" y="198" font-family="{FONT}" font-size="14" font-weight="600" fill="{sub}" letter-spacing="3.5"><tspan>WISDOM</tspan><tspan dx="9" fill="{PINK}">·</tspan><tspan dx="9">KHMER</tspan><tspan dx="9" fill="{PINK}">·</tspan><tspan dx="9">HERITAGE</tspan></text>
  </g>
</svg>
'''

open("wkh-labs-logo.svg", "w").write(wordmark("light"))
open("wkh-labs-wordmark-light.svg", "w").write(wordmark("light"))
open("wkh-labs-wordmark-dark.svg", "w").write(wordmark("dark"))
square = lambda body, extra="": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">{extra}<g transform="translate(-14 -6) scale(1.55)">{body}</g>\n</svg>\n'
open("wkh-labs-icon.svg", "w").write(square(mark("i")))
open("wkh-labs-app-icon.svg", "w").write(square(mark("a"), '<rect x="24" y="24" width="464" height="464" rx="108" fill="#F7F5FF"/>'))
