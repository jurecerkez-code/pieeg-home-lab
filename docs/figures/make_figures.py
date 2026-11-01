"""
Builds every figure in docs/images from documented sources, so each one can be checked and rebuilt.

    python make_figures.py              # all figures
    python make_figures.py placement    # only some: hero system kit assembly placement wiring header

Style: the PiEEG Home Lab design system, Lab theme. Ground #0b0d33, corner brackets, FIG. 0N labels,
Inter Display, Inter and DejaVu Sans Mono, gold for hardware, one fixed color per electrode lead,
no gradients. Every figure is 1000 px wide in SVG and exported at 2x to PNG.

Needs numpy, scipy and Pillow, plus rsvg-convert (librsvg) or the cairosvg package for the PNGs.
Sources, extracted once by extract_reference_data.py into data/:
  electrodes_1020.json    electrode positions, MNE-Python standard 10-20 montage (colin27 head)
  raspberry_pi_3b.json    Raspberry Pi 3 Model B outline, parts and 40 pin header, official DXF drawing
  hero_trace.json         6 s of a real PiEEG recording, from PiEEG's published example data
  assets/athena_generated.jpg   the hero bust, an AI generated illustration (Gamma), recolored here
The PiEEG-8 has no published mechanical drawing. Its outline and parts are measured from the top view
photo in PiEEG's documentation (pieeg8_led.png, board printed PiEEG V2.1), about 1 mm accurate.
Pin order, Pi pinout and register values follow PiEEG's documentation and PiEEG Server 0.49.0.
"""

import base64
import io
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA, ASSETS, OUT = HERE / "data", HERE / "assets", HERE.parent / "images"
W = 1000

# ---------------------------------------------------------------- design system tokens (Lab theme)
GROUND, SURFACE, SURFACE_TAB, SURFACE_CODE = "#0b0d33", "#11144a", "#161a52", "#161a78"
LINE, INK, MUTED, FAINT = "#2b3170", "#ecebf7", "#9a9ccc", "#5d6199"
ACCENT, ON_ACCENT = "#3d3dff", "#ecebf7"
E1C, E2C, REFC, BIASC, ALPHA = "#4b4bff", "#8f96ff", "#22d3ff", "#c792ff", "#5c5cff"
GOLD, GOLD_DEEP, GOLD_LIGHT = "#d8b55a", "#bf9b45", "#e3c46f"
MARBLE1, MARBLE2 = "#e7e2d6", "#cfc8b9"
DISPLAY = "Inter Display, Inter, Helvetica Neue, Arial, sans-serif"
SANS = "Inter, Helvetica Neue, Arial, sans-serif"
MONO = "DejaVu Sans Mono, Menlo, Consolas, monospace"

STYLES = {  # family, size, weight, letter spacing, uppercase, color
    "fig_label": (MONO, 12, 400, 2.0, True, MUTED),
    "title": (DISPLAY, 32, 200, 0, False, INK),
    "caption": (SANS, 14, 400, 0, False, MUTED),
    "card_title": (SANS, 15, 500, 0, False, INK),
    "detail": (SANS, 13, 400, 0, False, MUTED),
    "body": (SANS, 13, 400, 0, False, INK),
    "pin": (MONO, 12, 400, 1.0, True, INK),
    "index": (MONO, 12, 400, 1.5, True, E2C),
    "spec": (MONO, 10, 400, 0.8, True, MUTED),
    "note": (MONO, 10, 400, 1.5, True, MUTED),
    "chip": (MONO, 9, 400, 0.5, True, MUTED),
}


def blend(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


SKIN = blend(GROUND, MARBLE1, 0.07)      # skin as drawn: marble at 7 % on ground, opaque where a part hides lines


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def upper(s):
    """Uppercase for mono labels, keeping the micro sign and hex prefixes (0x20) as they are."""
    s = "".join(c if c == "µ" else c.upper() for c in s)
    return re.sub(r"\b0X([0-9A-F]+)\b", r"0x\1", s)


def text_width(s, style):
    fam, size, _, ls, up, _ = STYLES[style]
    s = upper(s) if up else s
    return len(s) * ((0.602 if fam == MONO else 0.56) * size + ls)


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.items, self.defs = w, h, [], {}

    def add(self, *items):
        self.items.extend(items)

    def line(self, x1, y1, x2, y2, stroke=INK, w=1.0, dash=None, op=1, cap="round"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{w}" stroke-linecap="{cap}" opacity="{op}"{d}/>')

    def path(self, d, stroke=INK, w=1.0, fill="none", dash=None, op=1, cap="round"):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" stroke="{stroke}" stroke-width="{w}" fill="{fill}" opacity="{op}" '
                 f'stroke-linejoin="round" stroke-linecap="{cap}"{ds}/>')

    def poly(self, pts, stroke=INK, w=1.0, fill="none", closed=False, dash=None, op=1):
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + (" Z" if closed else "")
        self.path(d, stroke, w, fill, dash, op)

    def rect(self, x, y, w, h, stroke=INK, sw=1.0, fill="none", r=0, dash=None, op=1):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" stroke="{stroke}" '
                 f'stroke-width="{sw}" fill="{fill}" opacity="{op}"{ds}/>')

    def circle(self, cx, cy, r, stroke=INK, sw=1.0, fill="none", dash=None, op=1):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.2f}" stroke="{stroke}" stroke-width="{sw}" '
                 f'fill="{fill}" opacity="{op}"{ds}/>')

    def ellipse(self, cx, cy, rx, ry, stroke=INK, sw=1.0, fill="none", dash=None, op=1, rot=0):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.2f}" ry="{ry:.2f}" stroke="{stroke}" '
                 f'stroke-width="{sw}" fill="{fill}" opacity="{op}" transform="rotate({rot} {cx:.1f} {cy:.1f})"{ds}/>')

    def text(self, x, y, s, style="detail", fill=None, anchor="start", size=None, weight=None, halo=False,
             op=1, caps=None, bg=False):
        fam, sz, wt, ls, up, col = STYLES[style]
        s = upper(s) if (up if caps is None else caps) else s
        if bg:                                   # ground colored box behind the label, for dimension lines
            w = len(s) * ((0.602 if fam == MONO else 0.56) * (size or sz) + ls)
            x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
            self.rect(x0 - 4, y - (size or sz) * 0.85, w + 6, (size or sz) * 1.2, "none", 0, fill=GROUND)
        a = (f'x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size or sz}" font-weight="{weight or wt}" '
             f'letter-spacing="{ls}" fill="{fill or col}" text-anchor="{anchor}" opacity="{op}"')
        if halo:
            a += f' stroke="{GROUND}" stroke-width="5" stroke-linejoin="round" paint-order="stroke"'
        self.add(f'<text {a} xml:space="preserve">{esc(s)}</text>')

    def image(self, x, y, w, h, png_bytes):
        b64 = base64.b64encode(png_bytes).decode()
        self.add(f'<image x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                 f'href="data:image/png;base64,{b64}"/>')

    def svg(self):
        defs = "<defs>" + "".join(self.defs.values()) + "</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}">{defs}' + "\n".join(self.items) + "</svg>")


def brackets(s):
    i = 18
    for x, y, dx, dy in [(i, i, 1, 1), (W - i, i, -1, 1), (i, s.h - i, 1, -1), (W - i, s.h - i, -1, -1)]:
        s.add(f'<path class="bracket" d="M{x} {y + dy * i} L{x} {y} L{x + dx * i} {y}" stroke="{LINE}" stroke-width="2" fill="none"/>')


def sheet(h, num, name, title, caption=None):
    """Figure frame: ground, four corner brackets, FIG label, title and caption."""
    s = Svg(W, h)
    s.add(f'<rect width="{W}" height="{h}" fill="{GROUND}"/>')
    brackets(s)
    s.text(44, 49, f"FIG. {num:02d}  ·  {name}", "fig_label")
    s.text(44, 87, title, "title")
    if caption:
        s.text(44, 113, caption, "caption")
    return s


def resize(s, h):
    """Change a sheet's height after drawing: new ground and corner brackets."""
    s.h = h
    s.items = [it for it in s.items if 'class="bracket"' not in it]
    s.items[0] = f'<rect width="{W}" height="{h}" fill="{GROUND}"/>'
    brackets(s)


def footer(s, text):
    s.text(44, s.h - 32, text, "note")


def export(s, name):
    OUT.mkdir(exist_ok=True)
    src, png = OUT / f"{name}.svg", OUT / f"{name}.png"
    src.write_text(s.svg())
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-z", "2", str(src), "-o", str(png)], check=True)
    else:
        import cairosvg
        cairosvg.svg2png(url=str(src), write_to=str(png), scale=2)
    print("wrote", png.relative_to(HERE.parent.parent))


# ---------------------------------------------------------------- drawing helpers
def catmull(points, closed=False, tension=0.5):
    """Smooth SVG path through points (Catmull-Rom as cubic Beziers)."""
    p = list(points)
    p = ([p[-1]] + p + [p[0], p[1]]) if closed else ([p[0]] + p + [p[-1]])
    d = f"M{p[1][0]:.1f} {p[1][1]:.1f}"
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d + (" Z" if closed else "")


def arrowhead(s, x, y, ang, color=MUTED, size=6.0):
    """Filled arrowhead with its tip at (x, y), pointing along ang (degrees, screen coordinates)."""
    a = math.radians(ang)
    bx, by = x - size * math.cos(a), y - size * math.sin(a)
    px, py = -math.sin(a) * size * 0.42, math.cos(a) * size * 0.42
    s.path(f"M{x:.1f} {y:.1f} L{bx + px:.1f} {by + py:.1f} L{bx - px:.1f} {by - py:.1f} Z", "none", 0, fill=color)


def dim_h(s, x1, x2, y, label, ext_from=None, color=MUTED):
    """Horizontal dimension line, extension lines from ext_from, label centered on the line."""
    if ext_from is not None:
        sgn = 1 if y > ext_from else -1
        for x in (x1, x2):
            s.line(x, ext_from + 3 * sgn, x, y + 5 * sgn, color, 0.8)
    s.line(x1, y, x2, y, color, 0.9)
    arrowhead(s, x1, y, 180, color, 5)
    arrowhead(s, x2, y, 0, color, 5)
    s.text((x1 + x2) / 2, y + 3.5, label, "note", color, "middle", bg=True)


def dim_v(s, x, y1, y2, label, ext_from=None, color=MUTED):
    """Vertical dimension line, label set horizontally beside it."""
    if ext_from is not None:
        sgn = 1 if x > ext_from else -1
        for y in (y1, y2):
            s.line(ext_from + 3 * sgn, y, x + 5 * sgn, y, color, 0.8)
    s.line(x, y1, x, y2, color, 0.9)
    arrowhead(s, x, y1, -90, color, 5)
    arrowhead(s, x, y2, 90, color, 5)
    s.text(x + 8, (y1 + y2) / 2 + 3.5, label, "note", color)


def leader(s, pts, color=MUTED, dot=True, w=1.0):
    s.poly(pts, color, w)
    if dot:
        s.circle(pts[0][0], pts[0][1], 2.2, "none", 0, fill=color)


def scale_bar(s, x, y, mm, k, label=None, color=MUTED):
    L = mm * k
    s.line(x, y, x + L, y, color, 1.2)
    for t in (0, 0.5, 1):
        s.line(x + L * t, y - (5 if t != 0.5 else 3), x + L * t, y + (5 if t != 0.5 else 3), color, 1)
    s.text(x + L + 8, y + 3.5, label or f"{mm} MM", "note", color)


def tag(s, x, y, txt, color=MUTED, anchor="start"):
    """Register or value tag: chip label in a hairline box. y is the text baseline."""
    w = text_width(txt, "chip") + 10
    x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
    s.rect(x0, y - 10, w, 15, LINE, 1, fill=GROUND)
    s.text(x0 + 5, y + 0.5, txt, "chip", color)
    return x0, x0 + w


def hair_paint(s):
    """Hair as a see-through gold hatch (pattern, not a gradient)."""
    s.defs["hair"] = (f'<pattern id="hair" width="4.5" height="4.5" patternUnits="userSpaceOnUse" '
                      f'patternTransform="rotate(38)"><line x1="0" y1="0" x2="0" y2="4.5" stroke="{GOLD_LIGHT}" '
                      f'stroke-width="0.9" opacity="0.42"/></pattern>')
    return "url(#hair)"


FOAM = blend(GROUND, MARBLE1, 0.24)      # the white foam disc, as drawn on the dark technical head


def sticker(s, cx, cy, rx, ry, color, rot=0, style="solid", sw=1.5, foam=FOAM):
    """Electrode sticker at true size: foam disc with a colored rim and the metal snap stud
    (about 5 mm) in the middle. style: solid, optional (dashed 8 6, the optional E2 lead)
    or hidden (short dashes, behind the head)."""
    if style != "solid":
        s.ellipse(cx, cy, rx, ry, color, sw, dash="8 6" if style == "optional" else "3 3", rot=rot)
        return
    s.ellipse(cx, cy, rx, ry, color, sw, fill=foam, rot=rot)
    f = 2.6 / STICKER_R
    s.ellipse(cx, cy, max(rx * f, 1.3), max(ry * f, 1.3), GROUND, 0.7, fill=MARBLE2, rot=rot)


def wire(s, pts, color, dash=None, w=2.5):
    s.path(catmull(pts), color, w, dash=dash)


def catenary(p1, p2, slack=1.2, n=48):
    """A cable hanging freely between two supports (screen coordinates, y down): a catenary whose
    length is slack times the straight distance."""
    from scipy.optimize import brentq
    (x1, y1), (x2, y2) = p1, p2
    if x2 < x1:
        return catenary(p2, p1, slack, n)[::-1]
    h, v = x2 - x1, y1 - y2                        # v measured upward
    L = slack * math.hypot(h, v)
    target = math.sqrt(L * L - v * v)
    a = brentq(lambda a: 2 * a * math.sinh(h / (2 * a)) - target, h / 1000, 1e7)
    x0 = (x1 + x2) / 2 - a * math.atanh(v / L)
    c = -y1 - a * math.cosh((x1 - x0) / a)
    return [(x, -(a * math.cosh((x - x0) / a) + c)) for x in np.linspace(x1, x2, n)]


# ---------------------------------------------------------------- head geometry (mm, MNE head coordinates)
EL = json.loads((DATA / "electrodes_1020.json").read_text())
CH = {k: np.array(v, float) for k, v in EL["channels"].items()}
FID = {k: np.array(v, float) for k, v in EL["fiducials"].items()}
STICKER_R = 13.0                     # Somnomedics SEN010C, 26 mm foam disc

# Midline face profile (y forward, z up), anchored on the template's nasion; the rest follows adult
# proportions (nasion to chin about 107 mm). The neck is cut 165 mm below the template origin.
NZ_Y, NZ_Z = FID["nasion"][1], FID["nasion"][2]
NECK_Z = -165
FACE = [(NZ_Y + 5.5, NZ_Z + 15), (NZ_Y, NZ_Z), (NZ_Y + 9, NZ_Z - 22), (NZ_Y + 20, NZ_Z - 38),
        (NZ_Y + 24, NZ_Z - 43), (NZ_Y + 15, NZ_Z - 49), (NZ_Y + 8, NZ_Z - 50), (NZ_Y + 11.5, NZ_Z - 62),
        (NZ_Y + 13, NZ_Z - 65.5), (NZ_Y + 9.5, NZ_Z - 69), (NZ_Y + 11, NZ_Z - 75), (NZ_Y + 4, NZ_Z - 83),
        (NZ_Y + 7.5, NZ_Z - 95), (NZ_Y + 2, NZ_Z - 104), (NZ_Y - 10, NZ_Z - 109), (NZ_Y - 30, NZ_Z - 112),
        (NZ_Y - 42, NZ_Z - 116), (NZ_Y - 45.5, NZ_Z - 128), (NZ_Y - 45, NECK_Z)]
NAPE = [(CH["Iz"][1] + 4, CH["Iz"][2] - 22), (CH["Iz"][1] + 14, CH["Iz"][2] - 52),
        (CH["Iz"][1] + 26, CH["Iz"][2] - 85), (CH["Iz"][1] + 28.5, NECK_Z)]
# Hairline seen from the left: forehead, temple, in front of and over the ear, behind it, into the knot.
HAIRLINE = [(55, 24), (20, 13), (-6, -6), (-20, -22), (-24, -36), (-28, -22), (-37, -12), (-50, -10),
            (-60, -22), (-64, -44), (-74, -60), (-92, -64), (-112, -56)]


def side_head_outline():
    scalp = [(CH[c][1], CH[c][2]) for c in ["Fpz", "AFz", "Fz", "FCz", "Cz", "CPz", "Pz", "POz", "Oz", "Iz"]]
    return list(reversed(FACE)) + scalp + NAPE


def side_hair():
    """Hair pulled back into a low knot, as you would wear it for mastoid electrodes."""
    over = [(80, 26)] + [(CH[c][1] + d, CH[c][2] + e) for c, d, e in
                         [("AFz", 1, 2.5), ("Fz", 2, 4), ("FCz", 1, 5), ("Cz", 0, 5), ("CPz", -2, 5),
                          ("Pz", -4, 4), ("POz", -5, 3), ("Oz", -6, 1)]]
    knot = [(-127, 4), (-141, 2), (-151, -8), (-153, -22), (-146, -35), (-133, -41), (-123, -40), (-117, -50)]
    return over + knot + HAIRLINE[::-1]


def ear_points(rot_deg=12):
    """Left ear, side view template (u = mm toward the back, v = mm up, origin at the ear canal)."""
    helix = [(-3, -2), (-2.5, 4), (-1, 10), (3, 20), (10, 27), (17, 27.5), (22.5, 21), (24.5, 10), (23.5, -1),
             (19.5, -12), (12.5, -20), (6.5, -26), (1.5, -24), (-0.5, -14), (-2, -7)]
    anti = [(6.5, 19), (14, 22.5), (19, 15), (19.5, 4), (17, -6), (12.5, -13)]
    rim = [(1, 11), (6, 21.5), (12, 24.5), (18, 23.5), (21.2, 17)]
    concha = [(1.5, 3.5), (6.5, 6), (10.5, 1), (8.5, -6.5), (3, -7.5)]
    a = math.radians(rot_deg)

    def r(pts):
        return [(u * math.cos(a) + v * math.sin(a), -u * math.sin(a) + v * math.cos(a)) for u, v in pts]
    return r(helix), r(anti), r(rim), r(concha)


def draw_side_head(s, X0, Y0, k, lw=1.5, features=True):
    """Left side view, nose to the left. Returns P(y, z) and Pp(point) mapping to screen."""
    def P(y, z):
        return X0 - y * k, Y0 - z * k

    def Pp(p):
        return P(p[1], p[2])
    out = [P(y, z) for y, z in side_head_outline()]
    s.path(catmull(out) + " Z", "none", 0, fill=SKIN)
    hair = [P(y, z) for y, z in side_hair()]
    s.path(catmull(hair, closed=True), "none", 0, fill=hair_paint(s))
    s.path(catmull(hair, closed=True), GOLD_DEEP, lw * 0.6)
    for strand in ([(-128, -2), (-140, -10), (-147, -22)], [(-131, -12), (-139, -24), (-139, -34)]):
        s.path(catmull([P(y, z) for y, z in strand]), GOLD_DEEP, lw * 0.5)
    s.path(catmull(out), INK, lw)
    if features:
        ny, nz = NZ_Y, NZ_Z
        s.path(catmull([P(ny - 1, nz + 11), P(ny - 10, nz + 15), P(ny - 22, nz + 15.5), P(ny - 32, nz + 12.5)]), INK, lw * 1.2, op=0.9)
        s.path(catmull([P(ny - 8, nz - 3), P(ny - 14, nz + 1.5), P(ny - 22, nz + 0.5), P(ny - 27, nz - 4.5)]), INK, lw * 0.8)
        s.path(catmull([P(ny - 27, nz - 4.5), P(ny - 19, nz - 7.5), P(ny - 11, nz - 6.5), P(ny - 8, nz - 3)]), INK, lw * 0.65, op=0.85)
        s.path(catmull([P(ny + 5, nz - 48), P(ny + 3, nz - 43), P(ny + 8.5, nz - 39.5), P(ny + 14, nz - 43.5)]), INK, lw * 0.7, op=0.85)
        s.path(catmull([P(ny + 9.5, nz - 69), P(ny + 4, nz - 69.8), P(ny - 1, nz - 70.5)]), INK, lw * 0.7, op=0.85)
    return P, Pp


def draw_side_ear(s, P, lw=1.5):
    """Left ear, drawn over anything behind it. Ear canal level with the template's preauricular point."""
    eac = (FID["lpa"][1], FID["lpa"][2])
    helix, anti, rim, concha = ear_points(12)
    E = lambda pts: [P(eac[0] - u, eac[1] + v) for u, v in pts]
    s.path(catmull(E(helix), closed=True), INK, lw * 0.9, fill=SKIN)
    s.path(catmull(E(rim)), INK, lw * 0.6, op=0.7)
    s.path(catmull(E(anti)), INK, lw * 0.6, op=0.7)
    s.path(catmull(E(concha), closed=True), INK, lw * 0.55, op=0.6)


def draw_front_head(s, X0, Y0, k, lw=1.5):
    """Front view. Her left side (x < 0) appears on the viewer's right."""
    def P(x, z):
        return X0 - x * k, Y0 - z * k
    right = [(0, CH["Cz"][2]), (36, 91), (CH["C4"][0], CH["C4"][2]), (80, 30), (CH["T8"][0], CH["T8"][2]),
             (80, -32), (69, -52), (62, -75), (54, -98), (47, -113), (31, -129), (14, -140.5), (0, -143)]
    left = [(-x, z) for x, z in reversed(right[1:-1])]
    head = [P(x, z) for x, z in right + left]
    s.path(catmull(head, closed=True), "none", 0, fill=SKIN)
    hair_r = [(0, 108), (40, 98), (73, 70), (89, 32), (92, 0), (90, -20), (84, -33), (74, -38),
              (72, -25), (64, -6), (48, 12), (25, 22)]
    hair = [P(x, z) for x, z in hair_r] + [P(0, 24)] + [P(-x, z) for x, z in reversed(hair_r[1:])]
    s.path(catmull(hair, closed=True), "none", 0, fill=hair_paint(s))
    s.path(catmull(hair, closed=True), GOLD_DEEP, lw * 0.6)
    for sgn in (1, -1):                                  # neck, emerging below the jaw
        s.path(catmull([P(sgn * 43, -117), P(sgn * 41.5, -140), P(sgn * 43, NECK_Z + 2)]), INK, lw)
    s.path(catmull(head, closed=True), INK, lw)
    for sgn in (1, -1):
        ear = [(79, -13), (88, -14), (94, -23), (95.5, -38), (93, -53), (88, -66), (81, -71)]
        s.path(catmull([P(sgn * x, z) for x, z in ear]) + f" L{P(sgn * 79, -13)[0]:.1f} {P(sgn * 79, -13)[1]:.1f}",
               INK, lw * 0.9, fill=SKIN)
        s.path(catmull([P(sgn * x, z) for x, z in [(84, -20), (89, -30), (89.5, -46), (85, -60)]]), INK, lw * 0.6, op=0.6)
        s.path(catmull([P(sgn * x, z) for x, z in [(13, -24.5), (22, -21), (33, -19.5), (43, -20.5), (50, -24)]]), INK, lw * 1.25, op=0.9)
        s.path(catmull([P(sgn * x, z) for x, z in [(17, -38.5), (24, -34.5), (33, -33.5), (41, -35.5), (46, -38.5)]]), INK, lw * 0.85)
        s.path(catmull([P(sgn * x, z) for x, z in [(46, -38.5), (38, -42), (28, -42.5), (21, -41), (17, -38.5)]]), INK, lw * 0.65, op=0.85)
        cx, cy = P(sgn * 31, -38.2)
        s.circle(cx, cy, 4.6 * k / 2, INK, lw * 0.6, op=0.85)
        s.circle(cx, cy, 1.6 * k / 2, "none", 0, fill=INK, op=0.85)
        s.path(catmull([P(sgn * 6.5, -37), P(sgn * 6, -55), P(sgn * 8, -72)]), INK, lw * 0.6, op=0.35)
    s.path(catmull([P(x, z) for x, z in [(-15, -77), (-17.5, -82.5), (-12, -87.5), (-5, -86), (0, -88),
                                           (5, -86), (12, -87.5), (17.5, -82.5), (15, -77)]]), INK, lw * 0.8)
    s.path(catmull([P(x, z) for x, z in [(-23, -101.5), (-9, -98.5), (0, -100.2), (9, -98.5), (23, -101.5)]]), INK, lw * 0.8, op=0.85)
    s.path(catmull([P(x, z) for x, z in [(-23, -101.5), (-8, -102.2), (0, -101.4), (8, -102.2), (23, -101.5)]]), INK, lw * 0.9)
    s.path(catmull([P(x, z) for x, z in [(-14, -107), (0, -109.5), (14, -107)]]), INK, lw * 0.65, op=0.55)
    return P


def top_projection():
    """Azimuthal equidistant projection from the vertex, as in MNE's topographic maps, with the head
    tilted so Fpz and Oz lie on the circle. Left to right it is scaled so T7 and T8 lie on it too:
    the circle is the 10 % circumference, as in the classic 10-20 diagram."""
    fpz, oz = CH["Fpz"], CH["Oz"]
    ang = math.atan2(oz[2] - fpz[2], fpz[1] - oz[1])
    c, s_ = math.cos(ang), math.sin(ang)
    rot = np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])
    f2, o2 = rot @ fpz, rot @ oz
    origin = np.array([0.0, (f2[1] + o2[1]) / 2, (f2[2] + o2[2]) / 2])

    def raw(p):
        v = rot @ np.asarray(p, float) - origin
        theta = math.acos(max(-1, min(1, v[2] / np.linalg.norm(v))))
        phi = math.atan2(v[1], v[0])
        r = theta / (math.pi / 2)
        return r * math.cos(phi), -r * math.sin(phi)
    su = 2 / (abs(raw(CH["T7"])[0]) + abs(raw(CH["T8"])[0]))
    rho = float(np.mean([np.linalg.norm(rot @ CH[k] - origin) for k in ("Fpz", "Oz", "T7", "T8", "Cz")]))
    return (lambda p: (raw(p)[0] * su, raw(p)[1])), rho


# ---------------------------------------------------------------- boards
PI = json.loads((DATA / "raspberry_pi_3b.json").read_text())
PI_MAJOR = {  # bounding boxes in board mm, from the official DXF
    "ethernet": (65.65, 2.5, 87.0, 18.0), "usb_top": (69.3, 39.65, 87.0, 53.57),
    "usb_bottom": (69.3, 21.65, 87.0, 35.57), "soc": (19.98, 24.52, 33.98, 38.52),
    "hdmi": (24.75, -1.5, 39.25, 10.65), "csi": (43.55, 0.3, 47.5, 22.7), "dsi": (1.5, 16.8, 5.45, 39.2),
    "audio": (50.0, 0.0, 57.0, 12.5), "lan": (55.4, 29.2, 64.4, 38.2), "micro_usb": (6.85, -0.6, 14.35, 4.71)}
MICROSD_CARD = PI["parts_bottom_boxes"][1]     # the card itself, on the underside, sticking out at the left
# PiEEG-8, measured on the top view photo in PiEEG's docs (pieeg8_led.png), board mm, origin bottom left.
# The 40 pin socket mates with the Pi's header, so it shares the Pi's coordinates (HAT layout).
PIEEG = {"w": 65.0, "h": 56.0, "r": 3.0, "holes": [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)],
         "header_x": 10.2, "header_top": 38.0, "ads1299": (28.2, 18.0), "led": (42.0, 18.7),
         "jumpers": [(56.6, 42.5), (56.6, 37.6), (56.6, 32.7)], "cap": (37.0, 7.0, 4.6, 7.6)}
HEADER = ["Ref", "Biasout", "E8", "E7", "E6", "E5", "E4", "E3", "E2", "E1"]     # printed top to bottom


def board_map(x0, y0, k, h=56.0):
    return lambda bx, by: (x0 + bx * k, y0 + (h - by) * k)


def box(s, M, b, stroke=INK, sw=1.0, fill="none", dash=None, op=1, r=0):
    x1, y1 = M(b[0], b[3])
    x2, y2 = M(b[2], b[1])
    s.rect(x1, y1, x2 - x1, y2 - y1, stroke, sw, fill=fill, dash=dash, op=op, r=r)
    return (x1 + x2) / 2, (y1 + y2) / 2


def draw_pi(s, x0, y0, k, detail=True, microsd=True):
    """Raspberry Pi 3 Model B, top view, from the official DXF drawing."""
    M = board_map(x0, y0, k)
    if microsd:
        box(s, M, MICROSD_CARD, MUTED, 1, dash="3 3")
    s.poly([M(x, y) for x, y in PI["outline"]], INK, 1.5, fill=SURFACE, closed=True)
    if detail:
        for part in PI["parts_top"]:
            s.poly([M(x, y) for x, y in part], MUTED, 0.5, op=0.35)
    for name, b in PI_MAJOR.items():
        box(s, M, b, INK, 1.0, fill=SURFACE if name in ("ethernet", "usb_top", "usb_bottom") else "none", op=0.9)
    d = PI["mounting_holes"]["diameter"]
    for cx, cy in PI["mounting_holes"]["centers"]:
        s.circle(*M(cx, cy), d / 2 * k, INK, 1)
    box(s, M, (7.1, 50.0, 57.9, 55.0), GOLD, 1)
    for cx, cy in PI["gpio_pins"]:
        X, Y = M(cx, cy)
        s.rect(X - 0.32 * k, Y - 0.32 * k, 0.64 * k, 0.64 * k, "none", 0, fill=GOLD)
    return M


def header_pins():
    return [(PIEEG["header_x"], PIEEG["header_top"] - i * 2.54) for i in range(10)]


def draw_pieeg(s, x0, y0, k, fill=SURFACE, chip_label=True):
    """PiEEG-8, top view, after PiEEG's photo (about 1 mm accurate)."""
    M = board_map(x0, y0, k)
    s.rect(x0, y0, PIEEG["w"] * k, PIEEG["h"] * k, GOLD, 1.5, fill=fill, r=PIEEG["r"] * k)
    for cx, cy in PIEEG["holes"]:
        s.circle(*M(cx, cy), 1.375 * k, GOLD, 1)
    for cx, cy in PI["gpio_pins"]:                     # through hole pads of the 40 pin socket
        s.circle(*M(cx, cy), 0.78 * k, GOLD, 0.9, op=0.9)
    X, Y = M(*PI["gpio_pin1"])
    s.rect(X - 0.85 * k, Y - 0.85 * k, 1.7 * k, 1.7 * k, GOLD, 1.2, fill=fill)
    ax, ay = PIEEG["ads1299"]
    box(s, M, (ax - 6, ay - 6, ax + 6, ay + 6), GOLD, 0.6, op=0.55)
    box(s, M, (ax - 5, ay - 5, ax + 5, ay + 5), GOLD, 1.2, fill=GROUND)
    if chip_label and k >= 3:
        s.text(*M(ax, ay - 0.6), "ADS1299", "chip", GOLD, "middle")
    lx, ly = PIEEG["led"]
    box(s, M, (lx - 0.8, ly - 0.4, lx + 0.8, ly + 0.4), "none", 0, fill=GOLD)
    for jx, jy in PIEEG["jumpers"]:
        box(s, M, (jx - 2.54, jy - 1.27, jx + 2.54, jy + 1.27), GOLD, 0.9, fill=GROUND, op=0.85)
    cx, cy, cw, chh = PIEEG["cap"]
    box(s, M, (cx - cw / 2, cy - chh / 2, cx + cw / 2, cy + chh / 2), GOLD, 0.8, op=0.6)
    hx, top = PIEEG["header_x"], PIEEG["header_top"]
    box(s, M, (hx - 1.27, top - 9 * 2.54 - 1.27, hx + 1.27, top + 1.27), GOLD, 1, fill=GROUND)
    for px, py in header_pins():
        X, Y = M(px, py)
        s.rect(X - 0.32 * k, Y - 0.32 * k, 0.64 * k, 0.64 * k, "none", 0, fill=GOLD)
    return M


def trace(seconds=None, skip=0.1):
    t = json.loads((DATA / "hero_trace.json").read_text())
    v = np.array(t["microvolts"], float)
    fs = t["sample_rate_hz"]
    v = v[int(skip * fs):]
    if seconds:
        v = v[: int(seconds * fs)]
    return v, t


# ---------------------------------------------------------------- FIG. 01 system
def laptop(s, x, y, w, h):
    """Laptop outline: screen and base. Returns the screen's inner rectangle."""
    s.rect(x, y, w, h, INK, 1.5, fill=SURFACE, r=6)
    s.rect(x + 9, y + 9, w - 18, h - 18, LINE, 1, r=2)
    s.poly([(x - 16, y + h + 2), (x + w + 16, y + h + 2), (x + w + 4, y + h + 14), (x - 4, y + h + 14)],
           INK, 1.5, closed=True)
    return x + 9, y + 9, w - 18, h - 18


def fig_system():
    s = sheet(560, 1, "SYSTEM", "How the pieces talk",
              "From the skin to the browser. Everything wired to the person runs on battery.")
    s.rect(40, 146, 572, 338, LINE, 1.2, r=10, dash="6 5")
    s.text(56, 166, "BATTERY ONLY  ·  NO CABLE TO THE MAINS", "note")
    # head, left side view
    k, X0, Y0 = 0.80, 206, 296
    P, Pp = draw_side_head(s, X0, Y0, k, lw=1.3)
    fx, fy = Pp(CH["Fp1"])
    mx, my = Pp(CH["M1"])
    sticker(s, mx, my, STICKER_R * k * 0.85, STICKER_R * k, REFC)
    # E1 lead lies on the skin from the forehead to the top of the ear, goes behind the ear
    wire(s, [(fx + 1, fy), P(64, -3), P(36, -2), P(8, -6), P(-16, -11), P(-33, -12)], E1C)
    draw_side_ear(s, P, lw=1.3)
    sticker(s, fx + 1.5, fy, STICKER_R * k * 0.35, STICKER_R * k, E1C)
    # boards
    kb, bx0, by0 = 2.0, 418, 220
    Mpi = draw_pi(s, bx0, by0, kb, detail=False, microsd=False)
    M = draw_pieeg(s, bx0, by0, kb, chip_label=False)
    hx = M(PIEEG["header_x"], 0)[0]
    pin_y = {n: M(PIEEG["header_x"], PIEEG["header_top"] - i * 2.54)[1] for i, n in enumerate(HEADER)}
    # free hanging parts: catenaries from behind the ear and the nape to the header pins
    for start, pin, col, slack in [(P(-97, -100), "Biasout", BIASC, 1.22), ((mx + 2, my + 2), "Ref", REFC, 1.18),
                                   (P(-38, -76), "E1", E1C, 1.16)]:
        s.poly(catenary(start, (hx, pin_y[pin]), slack), col, 2.5)
    s.text(350, 420, "20 CM CABLES", "note", MUTED, "middle")
    leader(s, [(fx - 3, fy - 10), (fx - 14, fy - 46), (fx - 22, fy - 46)], E1C)
    s.text(fx - 26, fy - 42, "E1 · FP1", "pin", E1C, "end", halo=True)
    s.text(bx0, by0 - 26, "PIEEG-8  ·  ADS1299", "pin", GOLD)
    s.text(bx0, by0 - 11, "ON RASPBERRY PI 3 MODEL B", "spec")
    # legend for the leads
    lx = 56
    for lab, col in [("E1 · FP1", E1C), ("REF · M1", REFC), ("BIAS · M2, BEHIND THE RIGHT EAR", BIASC)]:
        s.line(lx, 461, lx + 18, 461, col, 2.5)
        s.text(lx + 26, 465, lab, "note", col)
        lx += 26 + text_width(lab, "note") + 22
    # power
    ux, uy = Mpi(10.6, -0.6)
    px0, py0 = 418, 384
    s.rect(px0, py0, 168, 50, INK, 1.5, fill=SURFACE, r=10)
    s.text(px0 + 84, py0 + 22, "POWERBANK  ·  5 V", "pin", INK, "middle")
    s.text(px0 + 84, py0 + 38, "CHARGED, NOT CHARGING", "spec", MUTED, "middle")
    s.line(ux, uy + 1, ux, py0, INK, 1.5)
    s.text(ux + 10, uy + 34, "MICRO USB → PWR IN", "note")
    # wifi and laptop
    lx, ly, lw_, lh = 752, 226, 188, 118
    s.line(626, 284, lx - 28, 284, MUTED, 1.5, dash="6 6")
    arrowhead(s, lx - 20, 284, 0, MUTED, 7)
    arrowhead(s, 620, 284, 180, MUTED, 7)
    s.text(684, 272, "WIFI 2.4 GHZ", "pin", MUTED, "middle")
    s.text(684, 304, "PIEEG SERVER", "note", MUTED, "middle")
    s.text(684, 320, "DATA :1616", "note", MUTED, "middle")
    s.text(684, 336, "DASHBOARD :1617", "note", MUTED, "middle")
    sx, sy, sw, sh = laptop(s, lx, ly, lw_, lh)
    v, _ = trace(seconds=2.5)
    xs = np.linspace(sx + 10, sx + sw - 10, len(v))
    s.poly(list(zip(xs, sy + sh / 2 - v / np.percentile(np.abs(v), 99) * sh * 0.3)), ALPHA, 1.1)
    s.text(lx + lw_ / 2, ly + lh + 42, "MACBOOK", "pin", INK, "middle")
    s.text(lx + lw_ / 2, ly + lh + 58, "ON BATTERY, CHARGER UNPLUGGED", "spec", MUTED, "middle")
    s.text(lx + lw_ / 2, ly + lh + 74, "BROWSER DASHBOARD  ·  PYTHON", "spec", MUTED, "middle")
    footer(s, "SKIN  →  ADS1299, 24 BIT, 250 SAMPLES/S  →  SPI  →  PIEEG SERVER  →  WIFI  →  BROWSER, PYTHON")
    return s


# ---------------------------------------------------------------- FIG. 02 what's in the box
def alligator(s, x, y, k, color=INK):
    """Small alligator clip, side view, jaws closed (about 28 mm long)."""
    L = 28 * k
    s.path(f"M{x:.1f} {y - 2.6 * k:.1f} L{x + 0.42 * L:.1f} {y - 4.0 * k:.1f} L{x + L:.1f} {y - 0.7 * k:.1f} "
           f"L{x + L:.1f} {y + 0.7 * k:.1f} L{x + 0.42 * L:.1f} {y + 4.0 * k:.1f} L{x:.1f} {y + 2.6 * k:.1f} Z",
           color, 1.2, fill=GROUND)
    zz = f"M{x + 0.55 * L:.1f} {y:.1f}"
    n = 6
    for i in range(1, n + 1):
        zz += f" L{x + 0.55 * L + i * 0.45 * L / n:.1f} {y + (0.9 if i % 2 else -0.9) * k:.1f}"
    s.path(zz, color, 0.8)
    s.circle(x + 0.38 * L, y, 1.3 * k, color, 1)
    return x + L


def dupont_cable(s, x, y, w_total, color, k):
    """Female Dupont housing (2.54 mm square, 14 mm long), wire with a break, alligator clip."""
    hw, hl = 2.6 * k, 14 * k
    s.rect(x, y - hw / 2, hl, hw, INK, 1.2, fill=GROUND)
    clip = 28 * k
    wire_len = w_total - hl - clip
    a = x + hl
    s.line(a, y, a + wire_len * 0.5 - 8, y, color, 2.5)
    s.line(a + wire_len * 0.5 - 5, y - 6, a + wire_len * 0.5 - 1, y + 6, MUTED, 1)
    s.line(a + wire_len * 0.5 + 1, y - 6, a + wire_len * 0.5 + 5, y + 6, MUTED, 1)
    s.line(a + wire_len * 0.5 + 8, y, a + wire_len, y, color, 2.5)
    alligator(s, a + wire_len, y, k)


def fig_kit():
    s = sheet(700, 2, "WHAT'S IN THE BOX", "Six parts, no soldering",
              "Parts 01 to 04 are drawn to the same scale. 05 and 06 are not to scale.")
    cw, chh, gap, x0, y0 = 296, 236, 12, 44, 140
    k = 2.1
    cards = [
        ("Raspberry Pi 3 Model B", ["BCM2837 · 1 GB · WIFI 2.4 GHZ", "16 GB MICROSD, PIEEG SERVER INSTALLED"]),
        ("PiEEG-8", ["ADS1299 · 24 BIT · 250 HZ", "10 MALE PINS: REF, BIASOUT, E8 … E1"]),
        ("Ag/AgCl electrode stickers", ["Ø 26 MM FOAM · SNAP · SINGLE USE", "60 · SOMNOMEDICS SEN010C"]),
        ("Dupont to alligator cables", ["FEMALE 2.54 MM → CLIP · 20 CM", "10 · BERRYBASE DUPAC20"]),
        ("Powerbank and Micro USB cable", ["5 V · 3 A, AS PIEEG RECOMMENDS", "OFFICIAL CABLE RPI-MUSB-1"]),
        ("Alcohol wipes and MacBook", ["CLEAN, DRY SKIN UNDER EACH STICKER", "MACBOOK ON BATTERY, WIFI ONLY"]),
    ]
    for i, (title, spec) in enumerate(cards):
        cx = x0 + (i % 3) * (cw + gap)
        cy = y0 + (i // 3) * (chh + gap)
        s.rect(cx, cy, cw, chh, LINE, 1)
        s.text(cx + 14, cy + 24, f"{i + 1:02d}", "index")
        s.text(cx + 14, cy + chh - 52, title, "card_title")
        for j, line in enumerate(spec):
            s.text(cx + 14, cy + chh - 32 + j * 15, line, "spec")
        ax, ay, aw, ah = cx + 14, cy + 32, cw - 28, chh - 104      # drawing area
        if i == 0:
            draw_pi(s, ax + (aw - 87 * k) / 2 + 2, ay + (ah - 56 * k) / 2, k, detail=True)
        elif i == 1:
            draw_pieeg(s, ax + (aw - 65 * k) / 2, ay + (ah - 56 * k) / 2, k, chip_label=False)
        elif i == 2:
            r = STICKER_R * k
            yc = ay + ah / 2 - 12
            sx = ax + 6 + r                                    # top view, true size
            s.circle(sx, yc, r, INK, 1.5)
            s.circle(sx, yc, 2.6 * k, GROUND, 0.7, fill=MARBLE2)
            dim_h(s, sx - r, sx + r, yc + r + 16, "Ø 26 MM", ext_from=yc)
            k2 = 2 * k                                         # side view at 2:1, schematic
            vw, vt = 26 * k2, 1.6 * k2                         # foam disc width and thickness
            vx, vy = ax + aw - vw - 2, yc + 14
            s.rect(vx, vy - vt, vw, vt, INK, 1.2, fill=GROUND)
            cxs = vx + vw / 2
            s.rect(cxs - 2.6 * k2, vy - vt - 2.6 * k2, 5.2 * k2, 2.6 * k2, INK, 1, fill=MARBLE2, r=2)
            leader(s, [(cxs, vy - vt - 2.6 * k2), (cxs, vy - 44), (cxs - 10, vy - 44)], MUTED)
            s.text(cxs - 14, vy - 47, "SNAP STUD:", "chip", MUTED, "end")
            s.text(cxs - 14, vy - 37, "THE CLIP BITES HERE", "chip", MUTED, "end")
            leader(s, [(vx + vw - 6, vy), (vx + vw - 6, vy + 16), (vx + vw - 16, vy + 16)], MUTED)
            s.text(vx + vw - 20, vy + 19, "STICKY SIDE ON SKIN", "chip", MUTED, "end")
            s.text(vx, yc + r + 19, "SIDE VIEW, 2:1", "chip", MUTED)
        elif i == 3:
            for j, col in enumerate((E1C, REFC, BIASC)):
                dupont_cable(s, ax + 6, ay + 22 + j * 28, aw - 14, col, k)
            s.text(ax + 6, ay + 110, "WIRE SHORTENED IN THE DRAWING", "note")
        elif i == 4:
            s.rect(ax + 16, ay + 22, 120, 64, INK, 1.5, fill=SURFACE, r=12)
            s.text(ax + 76, ay + 59, "5 V", "pin", INK, "middle")
            s.path(f"M{ax + 136} {ay + 54} C{ax + 180} {ay + 54} {ax + 190} {ay + 24} {ax + 232} {ay + 24}", INK, 1.5)
            s.rect(ax + 232, ay + 18, 16, 12, INK, 1.2, fill=GROUND, r=2)
            s.text(ax + 240, ay + 48, "MICRO USB", "chip", MUTED, "middle")
        else:
            s.rect(ax + 10, ay + 24, 92, 62, INK, 1.5, r=4)
            s.line(ax + 10, ay + 38, ax + 102, ay + 38, LINE, 1)
            s.text(ax + 56, ay + 66, "WIPES", "pin", MUTED, "middle")
            s.rect(ax + 136, ay + 14, 104, 66, INK, 1.5, r=4)
            s.poly([(ax + 126, ay + 82), (ax + 250, ay + 82), (ax + 244, ay + 90), (ax + 132, ay + 90)], INK, 1.5, closed=True)
    scale_bar(s, 44, 666, 20, k, "20 MM, PARTS 01 TO 04")
    s.text(W - 44, 669, "SOURCES  ·  PI: OFFICIAL DRAWING  ·  PIEEG-8: PIEEG PHOTO, ABOUT 1 MM", "note", MUTED, "end")
    return s


# ---------------------------------------------------------------- FIG. 03 mounting
def side_stack(s, x0, y0, k, tilt=0.0):
    """Schematic side view from the HDMI edge: Pi, its 40 pin header, the PiEEG-8 on its socket.
    Heights are schematic. tilt lifts the socket at the USB end (mm)."""
    def S(x, z):
        return x0 + x * k, y0 - z * k
    s.rect(*S(0, 1.4), 85 * k, 1.4 * k, INK, 1.2, fill=SURFACE, r=1)
    for a, b, hgt in [(65.6, 87, 13.5), (69.3, 87, 15.5)]:
        x1, y1 = S(a, 1.4 + hgt)
        x2, y2 = S(b, 1.4)
        s.rect(x1, y1, x2 - x1, y2 - y1, INK, 1, fill=SURFACE)
    s.rect(*S(7.1, 3.9), 50.8 * k, 2.5 * k, GOLD, 1, fill=GROUND)        # header base on the Pi

    def Z(x):
        return 3.9 + tilt * (x / 65.0)
    for i in range(20):                                                    # pins, visible where not covered
        x = 8.37 + i * 2.54
        if Z(x) > 4.4:
            s.line(*S(x, 3.9), *S(x, Z(x)), GOLD, 1.4)
    s.poly([S(7.1, Z(7.1)), S(57.9, Z(57.9)), S(57.9, Z(57.9) + 8.5), S(7.1, Z(7.1) + 8.5)], GOLD, 1.1, fill=GROUND, closed=True)
    s.poly([S(0, Z(0) + 8.5), S(65, Z(65) + 8.5), S(65, Z(65) + 10.1), S(0, Z(0) + 10.1)], GOLD, 1.4, fill=SURFACE, closed=True)
    hx = PIEEG["header_x"]
    s.poly([S(hx - 1.27, Z(hx) + 10.1), S(hx + 1.27, Z(hx) + 10.1), S(hx + 1.27, Z(hx) + 12.6), S(hx - 1.27, Z(hx) + 12.6)],
           GOLD, 1, fill=GROUND, closed=True)
    s.line(*S(hx, Z(hx) + 12.6), *S(hx, Z(hx) + 18.6), GOLD, 1.6)
    return S


def fig_mounting():
    s = sheet(740, 3, "MOUNTING", "Pin 1 on pin 1, then press straight down",
              "The Raspberry Pi from its official drawing, the PiEEG-8 measured from PiEEG's photo (about 1 mm).")
    k, x0, y0 = 3.4, 154, 222
    s.text(44, 150, "A  ·  TOP VIEW, PIEEG-8 IN PLACE", "note")
    Mpi = draw_pi(s, x0, y0, k, detail=True)
    M = draw_pieeg(s, x0, y0, k, chip_label=False)
    dim_h(s, x0, x0 + 85 * k, y0 - 38, "85 MM", ext_from=y0 + 2)
    dim_h(s, x0, x0 + 65 * k, y0 - 16, "65 MM", ext_from=y0)
    dim_v(s, x0 + 87 * k + 22, y0, y0 + 56 * k, "56 MM", ext_from=x0 + 87 * k)
    p1 = M(*PI["gpio_pin1"])
    leader(s, [p1, (x0 - 14, p1[1])], GOLD)
    s.text(44, p1[1] - 2, "PIN 1", "pin", GOLD)
    s.text(44, p1[1] + 12, "BOTH BOARDS", "note")
    hx, hy = M(PIEEG["header_x"], PIEEG["header_top"] - 4.5 * 2.54)
    leader(s, [(hx, hy), (x0 - 14, hy)], GOLD)
    s.text(44, hy - 2, "ELECTRODE", "pin", GOLD)
    s.text(44, hy + 12, "PINS, UP", "note")
    sx, sy = Mpi(-1.6, 28)
    leader(s, [(sx, sy + 6), (sx - 12, sy + 64), (x0 - 70, sy + 64)], MUTED)
    s.text(44, sy + 60, "MICROSD", "pin", MUTED)
    s.text(44, sy + 74, "UNDERSIDE", "note")
    mx, my = Mpi(10.6, -0.6)
    leader(s, [(mx, my), (mx, my + 36), (mx + 14, my + 36)], INK)
    s.text(mx + 18, my + 40, "MICRO USB · PWR IN", "pin", INK)
    ux, uy = Mpi(78, 2.4)
    leader(s, [(ux, uy), (ux, uy + 46), (ux + 10, uy + 46)], INK)
    s.text(ux + 14, uy + 50, "USB, ETHERNET FREE", "note", INK)
    # B: seated or not
    s.text(44, 516, "B  ·  SIDE VIEW FROM THE HDMI EDGE, SCHEMATIC HEIGHTS", "note")
    side_stack(s, 60, 618, 2.0)
    s.text(60, 648, "SEATED", "pin", INK)
    s.text(60, 663, "NO PIN VISIBLE, BOARDS PARALLEL", "note")
    side_stack(s, 330, 618, 2.0, tilt=4.5)
    s.text(330, 648, "NOT SEATED", "pin", MUTED)
    s.text(330, 663, "PINS SHOW AT ONE END", "note")
    # C: steps
    cx, cy = 600, 150
    s.text(cx, cy, "C  ·  STEPS", "note")
    steps = [("Unplug the power.", ["Never mount or remove the board while", "the Pi has power."]),
             ("Find pin 1 on both boards.", ["Pi: inner row, at the microSD end.", "PiEEG-8: the socket end printed 1."]),
             ("Line up all 40 pins.", ["Edges flush on the microSD side.", "USB and Ethernet stay free."]),
             ("Press straight down, evenly.", ["Push near both ends of the socket,", "not in the middle of the board."]),
             ("Check.", ["No pin visible at either end,", "the two boards parallel (B)."])]
    for i, (a, b) in enumerate(steps):
        y = cy + 40 + i * 98
        s.text(cx, y, f"{i + 1:02d}", "index")
        s.text(cx + 34, y, a, "card_title")
        for j, line in enumerate(b):
            s.text(cx + 34, y + 22 + j * 18, line, "detail")
    footer(s, "SOURCES  ·  RASPBERRY PI 3 B MECHANICAL DRAWING RPI-3B-V1_2  ·  PIEEG-8 TOP VIEW PHOTO, PIEEG DOCS")
    return s


# ---------------------------------------------------------------- the rendered head (FIG. 01, 04)
import render3d as R3                                   # noqa: E402

HEAD = {}
LEADS = {"E1": ("Fp1", E1C), "E2": ("Fp2", E2C), "REF": ("M1", REFC), "BIAS": ("M2", BIASC)}
for _lead, (_ch, _col) in LEADS.items():
    R3.material("rim_" + _lead, _col, 0.6, 0.0, 8, 0.7, emit=0.55)
NECK_CUT = ((0, 0, 1), 606.0)          # the bust is cut flat 606 mm above the mesh's origin


def head():
    """MakeHuman's CC0 head with the 10-20 montage fitted to it (data/head_*, extract_reference_data)."""
    if not HEAD:
        V, F = R3.load_head()
        HEAD.update(V=V, F=F, skin=R3.Skin(V, F), E=R3.load_electrodes())
    return HEAD


def hpos(ch):
    return np.array(head()["E"]["channels"][ch]["pos"], float)


def hmark(name):
    E = head()["E"]
    return np.array(E["landmarks"].get(name) or E["midline_arc"]["marks"][name], float)


def head_scene(leads=("E1", "REF", "BIAS")):
    h = head()
    sc = R3.Scene().add(h["V"], h["F"], "skin", smooth=True)
    for lead in leads:
        v, f, m, c, n = R3.sticker_mesh(h["skin"], hpos(LEADS[lead][0]), "rim_" + lead)
        sc.add(v, f, m)
    return sc


def place(s, r):
    x, y, w, h = r.image_box()
    s.image(x, y, w, h, r.png())


def on_skin(P, lift=0.0):
    q, n = head()["skin"].project(P)
    return q + n * lift, n


def runs(mask):
    """Index runs where mask is true, on a closed loop."""
    n = len(mask)
    if mask.all():
        return [list(range(n)) + [0]]
    start = int(np.argmin(mask))
    out, cur = [], []
    for i in range(start, start + n + 1):
        j = i % n
        if mask[j]:
            cur.append(j)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [r for r in out if len(r) > 1]


def sticker_outline(s, r, ch, col, style):
    """The rim of a sticker on the skin, as a vector line. hidden: short dashes where the head hides
    it. optional: long dashes (8 6) where it can be seen, for the optional E2 lead."""
    c, n = on_skin(hpos(ch))
    ring, _ = on_skin(R3.disc_points(c[0], n[0], R3.STICKER_R, 120), R3.FOAM_T)
    xy = r.to_svg(ring)
    vis = r.visible(ring, tol=1.0)
    want = ~vis if style == "hidden" else vis
    for run in runs(want):
        s.poly([tuple(xy[j]) for j in run], col, 1.4 if style == "hidden" else 1.6,
               dash="3 3" if style == "hidden" else "8 6")


def silhouette_x(r, y_svg, side):
    """Leftmost (side=-1) or rightmost (side=1) point of a render's silhouette on an SVG row."""
    x0, y0, w, h = r.image_box()
    row = int((y_svg - y0) * r.ss)
    cols = np.nonzero(r.mask[row])[0]
    edge = cols.max() if side > 0 else cols.min()
    return x0 + edge / r.ss


def chip_dot(s, x, y, label=None, dx=0, dy=-6, anchor="middle", color=MUTED):
    s.circle(x, y, 2.3, GROUND, 1.1, fill=MARBLE1)
    if label:
        s.text(x + dx, y + dy, label, "chip", color, anchor, caps=False, halo=True)


def skin_label(s, x, y, text, anchor="middle"):
    """A label printed on the light skin: dark ink, no halo."""
    s.text(x, y, text, "chip", GROUND, anchor, caps=False, weight=600)


def skin_dot(s, x, y):
    s.circle(x, y, 2.4, GROUND, 1.2, fill=MARBLE1)


# ---------------------------------------------------------------- FIG. 04 electrode placement
def fig_placement():
    s = sheet(1010, 4, "ELECTRODE PLACEMENT", "Three stickers, placed by landmarks",
              "One adult head at true scale, seen from the front, the left and above. Stickers at true size, Ø 26 mm.")
    k, ztop = 1.5, 848.0
    oy = 168 + ztop * k
    sc = head_scene()
    # ---- A front view (her left on the viewer's right) and B left side view, same scale, same rows
    XF, XS = 262, 790
    rf = R3.Render(sc, R3.FRONT, k, XF, oy, cut=NECK_CUT)
    rs = R3.Render(sc, R3.LEFT, k, XS, oy, cut=NECK_CUT)
    place(s, rf)
    place(s, rs)
    # level lines between the views: the same height in both, one label serving both
    for lab, ch, col in [("E1 · FP1", "Fp1", E1C), ("REF · M1", "M1", REFC)]:
        y = rf.to_svg(hpos(ch))[0, 1]
        xa, xb = silhouette_x(rf, y, 1) + 8, silhouette_x(rs, y, -1) - 8
        s.line(xa, y, xb, y, col, 0.9, dash="2 4")
        s.text((xa + xb) / 2, y + 4, lab, "pin", col, "middle", bg=True)
    # A: optional E2, the hidden mastoid stickers, the pupil line
    sticker_outline(s, rf, "Fp2", E2C, "optional")
    sticker_outline(s, rf, "M1", REFC, "hidden")
    sticker_outline(s, rf, "M2", BIASC, "hidden")
    px, py = rf.to_svg(hmark("pupil_l")[None])[0]
    fy = rf.to_svg((hpos("Fp1") - [0, 0, R3.STICKER_R])[None])[0, 1]
    s.line(px, py - 7, px, fy + 2, E1C, 1, dash="2 2")
    x2, y2 = rf.to_svg(hpos("Fp2")[None])[0]
    lw2 = text_width("E2 · FP2", "pin")
    leader(s, [(x2 - 12, y2 - 10), (x2 - 40, y2 - 52), (44 + lw2 + 8, y2 - 52)], E2C)
    s.text(44, y2 - 48, "E2 · FP2", "pin", E2C)
    s.text(44, y2 - 34, "OPTIONAL", "note", MUTED)
    xb, yb = rf.to_svg(hpos("M2")[None])[0]
    lwb = text_width("BIAS · M2", "pin")
    leader(s, [(xb - 3, yb + 13), (xb - 14, yb + 64), (44 + lwb + 8, yb + 64)], BIASC)
    s.text(44, yb + 68, "BIAS · M2", "pin", BIASC)
    s.text(44, yb + 82, "BEHIND THE", "note", MUTED)
    s.text(44, yb + 96, "RIGHT EAR", "note", MUTED)
    # B: the midline arc with its 10 and 20 % steps, landmarks, the mastoid
    arc = np.array(head()["E"]["midline_arc"]["points"], float)

    def out(P, d):
        q, n = on_skin(np.atleast_2d(P))
        return q + n * d
    s.path(catmull([tuple(p) for p in rs.to_svg(out(arc, 15))]), FAINT, 1)
    marks = [hmark("nasion"), hmark("Fpz"), hmark("Fz"), hmark("Cz"), hmark("Pz"), hmark("Oz"), hmark("inion")]
    for p in marks:
        a, b = rs.to_svg(out(p, 10.5))[0], rs.to_svg(out(p, 19.5))[0]
        s.line(*a, *b, FAINT, 1)
    for (p, q), lab in zip(zip(marks, marks[1:]), ["10%", "20%", "20%", "20%", "20%", "10%"]):
        mid = arc[np.argmin(np.linalg.norm(arc - (p + q) / 2, axis=1))]
        x, y = rs.to_svg(out(mid, 28))[0]
        s.text(x, y + 3.5, lab, "chip", MUTED, "middle")
    for name in ("Fz", "Cz", "Pz", "Oz"):
        x, y = rs.to_svg(out(hmark(name), 0))[0]
        xi, yi = rs.to_svg(out(hmark(name), -12))[0]
        skin_dot(s, x - 0.6, y)
        skin_label(s, xi, yi + 3.5, name)
    for name, dy in (("F7", 15), ("T7", -7), ("P7", 15)):
        x, y = rs.to_svg(hpos(name)[None])[0]
        skin_dot(s, x, y)
        skin_label(s, x, y + dy, name)
    nx, ny = rs.to_svg(hmark("nasion")[None])[0]
    leader(s, [(nx - 3, ny), (nx - 30, ny + 4)], MUTED)
    s.text(nx - 34, ny + 8, "NASION", "note", MUTED, "end")
    ix, iy = rs.to_svg(hmark("inion")[None])[0]
    leader(s, [(ix + 2, iy + 2), (ix + 26, iy + 34), (ix + 36, iy + 34)], MUTED)
    s.text(ix + 40, iy + 38, "INION", "note", MUTED)
    mx, my = rs.to_svg(hpos("M1")[None])[0]
    leader(s, [(mx + 10, my + 12), (mx + 40, my + 72), (mx + 54, my + 72)], REFC)
    s.text(mx + 58, my + 76, "MASTOID BONE", "note")
    s.text(mx + 58, my + 90, "ON SKIN, NOT HAIR", "note")
    ybot = oy - NECK_CUT[1] * k
    s.text(XF, ybot + 30, "A  ·  FRONT", "note", MUTED, "middle")
    s.text(rs.to_svg(np.array([[0, 64.0, 700]]))[0, 0], ybot + 30, "B  ·  LEFT SIDE", "note", MUTED, "middle")
    scale_bar(s, 470, ybot + 26, 50, k)
    # ---- C from above: the 10-20 sites on the same head
    s.line(44, ybot + 58, W - 44, ybot + 58, LINE, 1)
    kt = 1.25
    yc0 = ybot + 100
    XT = 226
    rt = R3.Render(sc, R3.TOP, kt, XT, yc0 + 172.0 * kt, cut=NECK_CUT)
    place(s, rt)
    ring = ["Fpz", "Fp2", "F8", "T8", "P8", "O2", "Oz", "O1", "P7", "T7", "F7", "Fp1"]
    pts = [tuple(p) for p in rt.to_svg(np.array([hpos(c) for c in ring]))]
    s.path(catmull(pts, closed=True), GROUND, 0.9, dash="2 4", op=0.55)
    cx0, cy0 = rt.to_svg(hpos("Cz")[None])[0]
    for c in ["F3", "Fz", "F4", "C3", "Cz", "C4", "P3", "Pz", "P4", "F7", "F8", "T7", "T8", "P7", "P8", "O1", "O2"]:
        x, y = rt.to_svg(hpos(c)[None])[0]
        skin_dot(s, x, y)
        if c in ("F7", "F8", "O1", "O2", "P7", "P8"):          # on the rim: label toward the middle
            v = np.array([cx0 - x, cy0 - y])
            v /= np.linalg.norm(v)
            skin_label(s, x + v[0] * 14, y + v[1] * 14 + 3.5, c)
        elif c in ("T7", "T8"):
            skin_label(s, x + (9 if c == "T7" else -9), y + 3.5, c, "start" if c == "T7" else "end")
        elif c in ("C3", "C4"):
            skin_label(s, x, y + 15, c)
        else:
            skin_label(s, x, y - 6, c)
    sticker_outline(s, rt, "Fp2", E2C, "optional")
    xl, xr = rt.image_box()[0] - 8, rt.image_box()[0] + rt.image_box()[2] + 8
    for lead, side, dy in [("E1", -1, -18), ("E2", 1, -18)]:
        ch, col = LEADS[lead]
        x, y = rt.to_svg(hpos(ch)[None])[0]
        xe = xl if side < 0 else xr
        leader(s, [(x, y), (x + side * 10, y + dy), (xe, y + dy)], col)
        s.text(xe - 4 if side < 0 else xe + 4, y + dy + 4, lead, "pin", col, "end" if side < 0 else "start")
    nose = rt.to_svg(np.array([[0, 168.0, 700]]))[0]
    s.text(nose[0], nose[1] - 12, "NOSE", "note", MUTED, "middle")
    s.text(44, yc0 - 18, "C  ·  FROM ABOVE", "note")
    s.text(XT, rt.image_box()[1] + rt.image_box()[3] + 16, "DOTTED: THE 10 % CIRCUMFERENCE", "chip", MUTED, "middle")
    s.text(XT, rt.image_box()[1] + rt.image_box()[3] + 30, "REF AND BIAS SIT LOWER, BEHIND THE EARS (B)", "chip", MUTED, "middle")
    # ---- D how to find each spot
    dx0 = 452
    s.text(dx0, yc0 - 18, "D  ·  HOW TO FIND EACH SPOT", "note")
    rows = [("E1  →  LEFT FOREHEAD  ·  FP1", E1C, ["Lower edge just above the left eyebrow,", "in line with the pupil."]),
            ("REF  →  BEHIND THE LEFT EAR  ·  M1", REFC, ["The bony bump right behind the lower half", "of the ear, on skin. Tie long hair back."]),
            ("BIASOUT  →  BEHIND THE RIGHT EAR  ·  M2", BIASC, ["The same spot on the right side."]),
            ("E2  →  RIGHT FOREHEAD  ·  FP2, OPTIONAL", E2C, ["Mirror image of Fp1."])]
    y = yc0 + 16
    for head_, col, lines in rows:
        s.text(dx0, y, head_, "pin", col)
        for j, line in enumerate(lines):
            s.text(dx0, y + 20 + j * 18, line, "detail")
        y += 34 + 18 * len(lines)
    s.text(dx0, y + 4, "Short dashes: hidden behind the head. Long dashes: optional.", "detail")
    footer(s, "SOURCES  ·  HEAD: MAKEHUMAN BASE MESH, CC0  ·  POSITIONS: MNE-PYTHON STANDARD 10-20, FITTED TO 5 LANDMARKS")
    return s


# ---------------------------------------------------------------- the rendered boards (FIG. 01, 05)
import parts3d as P3                                    # noqa: E402

LEAD_PIN = {"E1": "E1", "E2": "E2", "REF": "Ref", "BIAS": "Biasout"}
for _lead, (_ch, _col) in LEADS.items():
    R3.material("wire_" + _lead, _col, 0.75, 0.25, 30, 0.6, emit=0.25)


def board_scene(leads=("REF", "BIAS", "E1"), stub=None, toward=(-110.0, 0.0, 150.0), length=230.0):
    """Pi 3 B with the PiEEG-8, a jumper housing on each used pin and its wire. The wire's shape is
    the elastic rod at rest on its way to the head (up and to the left); stub keeps its first mm."""
    sc = R3.Scene()
    P3.raspberry_pi(sc)
    P3.pieeg(sc, used=[LEAD_PIN[l] for l in leads])
    obst = [(0, 0, -2, 87, 56, P3.PE_TOP)]
    for l in leads:
        x, y = P3.pin_xy(LEAD_PIN[l])
        obst.append((x - 1.27, y - 1.27, P3.EL_BASE, x + 1.27, y + 1.27, P3.EL_BASE + P3.HOUSING_L))
    wires = {}
    for i, l in enumerate(leads):
        p0 = P3.housing_top(LEAD_PIN[l])
        far = p0 + np.array(toward) + np.array([0, 0, 12.0 * i])
        P = P3.hang(p0, (0, 0, 1), far, length + 10 * i, floors=[((0, 0, 1), -2.0)], boxes=obst)
        if stub:
            P = P3.cut_path(P, stub)
        P3.add_cable(sc, P, "wire_" + l)
        wires[l] = P
    return sc, wires


def cable_break(s, r, P, col):
    """Technical drawing break at the end of a cable that continues: two short slanted strokes."""
    a, b = r.to_svg(np.asarray(P[-2:], float))
    d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
    nrm = np.array([-d[1], d[0]])
    for off in (3.0, 7.0):
        c = b + d * off
        p, q = c + nrm * 6 + d * 2.5, c - nrm * 6 - d * 2.5
        s.line(*p, *q, col, 1.2)
    return b + d * 12


# ---------------------------------------------------------------- FIG. 05 wiring
def fig_wiring():
    s = sheet(1080, 5, "WIRING", "Which pin goes where",
              "The PiEEG-8 on the Raspberry Pi. Each lead starts with a jumper, its female end pushed onto a pin.")
    # ---- A: the whole stack, three jumpers in place
    sc, wires = board_scene(stub=30.0)
    ca = R3.Camera.orbit(-35, 30)
    ra = R3.Render(sc, ca, 4.1, 0, 0, catcher=-2.0).move_to(30, 170)
    place(s, ra)
    s.text(44, 150, "A  ·  ON THE PI, SEEN FROM THE MICROSD END", "note")
    for l in ("REF", "BIAS", "E1"):
        cable_break(s, ra, wires[l], LEADS[l][1])
    abot = ra.image_box()[1] + ra.image_box()[3] + 8
    targets = [("ELECTRODE HEADER", "ENLARGED IN B", np.array([P3.PIEEG["header_x"] - 1.3, 16.0, P3.PE_TOP + 1.0]), 44, INK),
               ("ADS1299", "THE EEG CHIP", np.array([*P3.PIEEG["ads1299"], P3.PE_TOP + 1.0]), 236, GOLD),
               ("LED", "ON WITH POWER", np.array([*P3.PIEEG["led"], P3.PE_TOP + 0.6]), 384, GOLD)]
    for title, sub, P, tx, col in targets:
        x, y = ra.to_svg(P[None])[0]
        leader(s, [(x, y), (x, abot), (tx, abot)] if abs(x - tx) > 2 else [(x, y), (x, abot)], col)
        s.text(tx, abot + 18, title, "pin", col)
        s.text(tx, abot + 33, sub, "note", MUTED)
    # ---- B: the electrode header, a detail cut out of the board
    cb = R3.Camera.orbit(-16, 16)
    scb, wb = board_scene(stub=12.0)
    cut = [((-1, 0, 0), -15.0), ((0, 1, 0), 11.0), ((0, -1, 0), -42.0), ((0, 0, 1), P3.PE_Z0 - 0.05)]
    corners = np.array([[x, y, z] for x in (0, 15) for y in (11, 42) for z in (P3.PE_Z0, P3.EL_BASE + P3.HOUSING_L + 12)])
    pc = cb.project(corners)
    kb = 344 / (np.ptp(pc[:, 0]) + 8)
    rb = R3.Render(scb, cb, kb, 0, 0, cut=cut, pad=4, bounds=(pc[:, 0].min(), pc[:, 1].min(), pc[:, 0].max(), pc[:, 1].max())).move_to(604, 180)
    place(s, rb)
    s.text(604, 150, "B  ·  ELECTRODE HEADER, 2.54 MM PITCH", "note")
    for l in ("REF", "BIAS", "E1"):
        cable_break(s, rb, wb[l], LEADS[l][1])
    x2, y2 = P3.pin_xy("E2")                      # where the optional fourth jumper goes
    w2 = P3.HOUSING_W / 2
    sq = [(x2 - w2, y2 - w2), (x2 - w2, y2 + w2), (x2 + w2, y2 + w2), (x2 + w2, y2 - w2)]
    z0, z1 = P3.EL_BASE, P3.EL_BASE + P3.HOUSING_L
    for a in range(4):
        for p, q in [((*sq[a], z0), (*sq[(a + 1) % 4], z0)), ((*sq[a], z1), (*sq[(a + 1) % 4], z1)),
                     ((*sq[a], z0), (*sq[a], z1))]:
            pp, qq = rb.to_svg(np.array([p, q]))
            if rb.visible(np.array([p, q]), tol=0.6).all():
                s.line(*pp, *qq, E2C, 1, dash="3 3")
    yb0 = rb.image_box()[1] + rb.image_box()[3] + 4
    colors = {"Ref": REFC, "Biasout": BIASC, "E1": E1C, "E2": E2C}
    for i, name in enumerate(P3.HEADER):
        x, y = P3.pin_xy(name)
        px_ = rb.to_svg(np.array([[x - 1.3, y, P3.EL_BASE]]))[0, 0]       # straight below the pin,
        ix0, iy0, _, _ = rb.image_box()                                     # from the board's lower edge
        rows = np.nonzero(rb.mask[:, int((px_ - ix0) * rb.ss)])[0]
        py_ = iy0 + (rows.max() + 1) / rb.ss + 3
        ty = yb0 + 18 + (i % 2) * 18
        col = colors.get(name, FAINT)
        s.line(px_, py_, px_, ty - 11, col if name in colors else LINE, 0.9)
        s.text(px_, ty, name, "chip", col, "middle", caps=True, size=10)
    b_end = yb0 + 40
    ty = abot + 96
    s.text(44, ty - 24, "EACH LEAD GOES TO", "note")
    for l, where in [("REF", "M1, BEHIND THE LEFT EAR"), ("BIAS", "M2, BEHIND THE RIGHT EAR"),
                     ("E1", "FP1, LEFT FOREHEAD"), ("E2", "FP2, RIGHT FOREHEAD, OPTIONAL")]:
        col = LEADS[l][1]
        s.line(44, ty - 4, 60, ty - 4, col, 2.5, dash="5 4" if l == "E2" else None)
        s.text(68, ty, f"{'BIASOUT' if l == 'BIAS' else l}  →  {where}", "chip", col, size=11)
        ty += 19
    s.text(44, ty + 4, "E3 TO E8 STAY EMPTY", "note", FAINT)
    c_top = max(b_end, ty + 10) + 34
    # C: inside the ADS1299
    cy0 = c_top + 26
    s.line(44, cy0 - 26, W - 44, cy0 - 26, LINE, 1)
    s.text(44, cy0, "C  ·  INSIDE THE ADS1299, WITH THE REGISTER VALUES PIEEG SERVER WRITES", "note")
    bx0, bx1, cb0, cb1 = 196, 716, cy0 + 22, cy0 + 254
    s.rect(bx0, cb0, bx1 - bx0, cb1 - cb0, GOLD, 1.5, r=6)
    s.text(bx0 + 12, cb0 + 18, "ADS1299", "chip", GOLD)
    yE1, yREF, yB = cy0 + 74, cy0 + 140, cy0 + 214
    for y, col, lab, frm in [(yE1, E1C, "E1", "FROM FP1"), (yREF, REFC, "REF", "FROM M1"), (yB, BIASC, "BIASOUT", "TO M2")]:
        s.circle(bx0, y, 5, col, 2, fill=GROUND)
        s.text(bx0 - 14, y + 4, lab, "pin", col, "end")
        s.text(bx0 - 14, y + 19, frm, "note", MUTED, "end")
    # channel 1: PGA (channels 2 to 8 stacked behind), ADC, SPI out
    ga, gb = 390, 456
    gt, gbm = cy0 + 54, cy0 + 114
    gm = (gt + gbm) / 2
    for off, op in [(10, 0.3), (5, 0.55)]:
        s.path(f"M{ga + off} {gt - off} L{gb + off} {gm - off} L{ga + off} {gbm - off} Z", INK, 1, fill=GROUND, op=op)
    s.path(f"M{ga} {gt} L{gb} {gm} L{ga} {gbm} Z", INK, 1.5, fill=GROUND)
    s.text(ga + 7, yE1 + 4, "+", "body", INK, weight=600)
    s.text(ga + 7, gbm - 9, "−", "body", INK, weight=600)
    s.line(bx0 + 5, yE1, ga, yE1, E1C, 2.5)
    s.text(bx0 + 20, yE1 - 8, "IN1P", "chip", E1C)
    s.line(bx0 + 5, yREF, 350, yREF, REFC, 2.5)
    s.line(350, yREF, 350, gbm - 14, REFC, 2.5)
    s.line(350, gbm - 14, ga, gbm - 14, REFC, 2.5)
    s.text(bx0 + 20, yREF - 8, "SRB1", "chip", REFC)
    s.text(357, gbm - 21, "IN1N", "chip", REFC)
    tag(s, bx0 + 20, yREF + 26, "MISC1 = 0x20  ·  SRB1 TO ALL 8 − INPUTS", REFC)
    tag(s, ga - 8, gt - 16, "CH1SET = 0x00  ·  GAIN 1", MUTED)
    s.text(ga + 20, gbm + 28, "CHANNELS 2 TO 8: THE SAME, INPUTS OPEN", "chip", MUTED)
    s.line(gb, gm, 500, gm, INK, 1.5)
    s.rect(500, gm - 24, 112, 48, INK, 1.5, fill=GROUND)
    s.text(556, gm - 3, "ΔΣ ADC", "body", INK, "middle")
    s.text(556, gm + 13, "24 BIT", "chip", MUTED, "middle")
    tag(s, 556, gm + 42, "CONFIG1 = 0x96  ·  250 SAMPLES/S", MUTED, "middle")
    s.line(612, gm, 744, gm, INK, 1.5)
    arrowhead(s, 750, gm, 0, INK, 7)
    s.text(758, gm - 6, "SPI → PI", "pin", INK)
    s.text(758, gm + 10, "27 BYTES PER SAMPLE", "note")
    s.text(758, gm + 24, "SEE FIG. 06", "note")
    # bias
    t0, t1 = 380, 444
    s.path(f"M{t1} {yB - 22} L{t0} {yB} L{t1} {yB + 22} Z", INK, 1.5, fill=GROUND)
    s.text(t0 + 2, yB - 28, "BIAS AMP", "chip", MUTED)
    s.line(bx0 + 5, yB, t0, yB, BIASC, 2.5)
    arrowhead(s, bx0 + 8, yB, 180, BIASC, 8)
    s.line(t1, yB - 9, 516, yB - 9, INK, 1.2)
    s.rect(516, yB - 25, 150, 30, INK, 1.2, fill=GROUND)
    s.text(591, yB - 6, "(AVDD + AVSS) / 2", "body", INK, "middle")
    tag(s, 500, yB - 34, "CONFIG3 = 0xFF  ·  BIASREF INSIDE", MUTED)
    s.line(t1, yB + 9, 490, yB + 9, FAINT, 1, dash="3 3")
    tag(s, 452, yB + 26, "BIAS_SENSP/N = 0x00  ·  NONE FED BACK", MUTED)
    # result
    rx = 758
    s.text(rx, yB - 34, "RESULT", "note", FAINT)
    s.text(rx, yB - 14, "CH1 = V(FP1) − V(M1)", "pin", E1C)
    s.text(rx, yB + 6, "Forehead minus left mastoid.", "detail")
    s.text(rx, yB + 23, "Bias holds the body at", "detail")
    s.text(rx, yB + 40, "the chip's mid supply.", "detail")
    resize(s, cy0 + 254 + 96)
    footer(s, "SOURCES  ·  PIEEG DOCS: ELECTRODES & PINOUT  ·  PIEEG SERVER 0.49.0 HARDWARE.PY  ·  TI ADS1299 DATASHEET")
    return s


# ---------------------------------------------------------------- FIG. 06 Pi header
PI_HEADER = {1: "3V3", 2: "5V", 3: "GPIO2", 4: "5V", 5: "GPIO3", 6: "GND", 7: "GPIO4", 8: "GPIO14", 9: "GND",
             10: "GPIO15", 11: "GPIO17", 12: "GPIO18", 13: "GPIO27", 14: "GND", 15: "GPIO22", 16: "GPIO23",
             17: "3V3", 18: "GPIO24", 19: "GPIO10", 20: "GND", 21: "GPIO9", 22: "GPIO25", 23: "GPIO11",
             24: "GPIO8", 25: "GND", 26: "GPIO7", 27: "GPIO0", 28: "GPIO1", 29: "GPIO5", 30: "GND", 31: "GPIO6",
             32: "GPIO12", 33: "GPIO13", 34: "GND", 35: "GPIO19", 36: "GPIO16", 37: "GPIO26", 38: "GPIO20",
             39: "GND", 40: "GPIO21"}
PIEEG_PINS = [  # PiEEG docs, Electrodes & Pinout; SPI clock from PiEEG Server's Pi profile
    (19, "GPIO 10", "MOSI", "PI → ADS1299", ["Commands and register", "values for the chip"]),
    (21, "GPIO 9", "MISO", "ADS1299 → PI", ["Every sample,", "27 bytes"]),
    (23, "GPIO 11", "SCLK", "PI → ADS1299", ["Clock for each bit,", "4 MHz"]),
    (24, "GPIO 8", "CE0", "PI → ADS1299", ["Chip select, low", "during each transfer"]),
    (37, "GPIO 26", "DRDY", "ADS1299 → PI", ["Low when a new sample", "is ready, 250 a second"]),
]


def fig_header():
    s = sheet(900, 6, "PI HEADER", "Five pins carry the data",
              "The Pi's 40 pin header as it sits on the board: pin 1 at the left, the board edge at the top.")
    p, x0, yt, yb = 40, 122, 232, 272          # pitch, first column, outer (even) row, inner (odd) row
    used = {pin for pin, *_ in PIEEG_PINS}
    s.text(44, 150, "A  ·  RASPBERRY PI 3 MODEL B, 40 PIN HEADER, TOP VIEW", "note")
    s.line(x0 - 50, yt - 58, x0 + 19 * p + 50, yt - 58, INK, 1.5)
    s.text(x0 + 19 * p + 50, yt - 66, "BOARD EDGE", "note", MUTED, "end")
    s.rect(x0 - 18, yt - 18, 19 * p + 36, (yb - yt) + 36, GOLD, 1.2, r=3)
    for n in range(1, 41):
        col = (n - 1) // 2
        x = x0 + col * p
        y = yb if n % 2 else yt
        on = n in used
        fn = PI_HEADER[n]
        power = fn in ("3V3", "5V", "GND")
        if n == 1:
            s.rect(x - 8, y - 8, 16, 16, GOLD, 1.3, fill=GOLD if on else "none")
        else:
            s.circle(x, y, 8, GOLD, 1.3, fill=GOLD if on else "none")
        ny = y + 34 if n % 2 else y - 26
        s.text(x, ny, str(n), "chip", INK if on else (MUTED if power else FAINT), "middle")
        if power:
            s.text(x, ny + (12 if n % 2 else -11), fn, "chip", MUTED, "middle")
    x35 = x0 + 17 * p
    s.text(x35 + 8, yb + 30, "*", "chip", MUTED)
    cw, gap, cy = 172, 12, 400
    card_x = [44 + i * (cw + gap) for i in range(5)]
    elbow = {19: 336, 21: 348, 23: 360, 24: 348, 37: 336}
    for i, (pin, gpio, sig, direction, what) in enumerate(PIEEG_PINS):
        col = (pin - 1) // 2
        px = x0 + col * p
        tx = card_x[i] + cw / 2
        if pin == 24:                     # leave the top row through the gap next to the pin
            pts = [(px + 8, yt), (px + p / 2, yt), (px + p / 2, elbow[pin]), (tx, elbow[pin]), (tx, cy)]
        else:
            pts = [(px, yb + 40), (px, elbow[pin]), (tx, elbow[pin]), (tx, cy)]
        leader(s, pts, GOLD, dot=False)
        cx = card_x[i]
        s.rect(cx, cy, cw, 124, LINE, 1)
        s.text(cx + 12, cy + 22, f"PIN {pin}", "pin", GOLD)
        s.text(cx + 12, cy + 46, sig, "pin", INK, size=16)
        s.text(cx + 12, cy + 64, f"{gpio} · {direction}", "spec")
        for j, line in enumerate(what):
            s.text(cx + 12, cy + 86 + j * 17, line, "detail")
    s.text(44, cy + 152, "Power and ground also come from the header. PiEEG's docs don't say which pins, so none are marked.",
           "detail")
    s.text(44, cy + 170, "* Pin 35, GPIO 19: PiEEG Server holds it high. It selects the second chip on the PiEEG-16, "
           "the PiEEG-8 doesn't use it.", "detail")
    # B: one sample on the wire
    ty0 = 626
    s.line(44, ty0 - 26, W - 44, ty0 - 26, LINE, 1)
    s.text(44, ty0, "B  ·  ONE SAMPLE ON THE WIRE, TIME NOT TO SCALE", "note")
    lx0, t_drdy, t_read, seg = 150, 206, 254, 72
    t_end = t_read + 9 * seg
    rows = [("DRDY", ty0 + 34), ("CE0", ty0 + 64), ("SCLK", ty0 + 94), ("MISO", ty0 + 126)]
    for name, y in rows:
        s.text(lx0 - 16, y + 4, name, "pin", INK, "end")
    hi, lo = -8, 8
    y = rows[0][1]
    s.poly([(lx0, y + hi), (t_drdy, y + hi), (t_drdy, y + lo), (t_read + 4, y + lo), (t_read + 4, y + hi), (W - 60, y + hi)], GOLD, 1.5)
    s.text(t_drdy + 2, y + hi - 6, "NEW SAMPLE READY", "chip", MUTED)
    y = rows[1][1]
    s.poly([(lx0, y + hi), (t_read - 10, y + hi), (t_read - 10, y + lo), (t_end + 10, y + lo), (t_end + 10, y + hi), (W - 60, y + hi)], GOLD, 1.5)
    y = rows[2][1]
    s.line(lx0, y + lo, t_read, y + lo, GOLD, 1.5)
    xx = t_read
    d = f"M{xx} {y + lo}"
    while xx < t_end - 4:
        d += f" L{xx} {y + hi} L{xx + 4} {y + hi} L{xx + 4} {y + lo} L{xx + 8} {y + lo}"
        xx += 8
    s.path(d, GOLD, 1)
    s.line(t_end, y + lo, W - 60, y + lo, GOLD, 1.5)
    y = rows[3][1]
    names = ["STATUS"] + [f"CH{i}" for i in range(1, 9)]
    for i, nm in enumerate(names):
        a = t_read + i * seg
        s.path(f"M{a} {y} L{a + 5} {y + hi} L{a + seg - 5} {y + hi} L{a + seg} {y} L{a + seg - 5} {y + lo} L{a + 5} {y + lo} Z",
               GOLD, 1.2, fill=SURFACE)
        s.text(a + seg / 2, y + 3.5, nm, "chip", INK if i else MUTED, "middle")
    s.line(lx0, y, t_read, y, GOLD, 1)
    s.line(t_end, y, W - 60, y, GOLD, 1)
    dim_h(s, t_read, t_end, y + 30, "216 CLOCKS  =  27 BYTES  ·  ABOUT 54 MICROSECONDS AT 4 MHZ")
    s.text(lx0 - 16, y + 60, "Each channel: 24 bit two's complement, most significant bit first. Status: 1100, lead off bits, GPIO.",
           "detail")
    s.text(lx0 - 16, y + 78, "The next sample follows 4 ms later (250 per second). PiEEG Server turns each value into µV.",
           "detail")
    footer(s, "SOURCES  ·  PIEEG DOCS: PIEEG-8 ELECTRODES & PINOUT  ·  PIEEG SERVER 0.49.0  ·  TI ADS1299 DATASHEET")
    return s


# ---------------------------------------------------------------- hero
BUST_CROP = (420, 30, 1620, 2030)        # region of assets/athena_generated.jpg used in the hero


def athena_png(height=960):
    """The AI generated Athena bust with two decorative neck lines painted out, its colors mapped
    exactly onto ground and marble-100 (background noise becomes flat ground)."""
    from PIL import Image, ImageDraw
    im = Image.open(ASSETS / "athena_generated.jpg").convert("RGB")
    marble = (232, 225, 210)
    d = ImageDraw.Draw(im)
    d.rectangle([772, 1794, 814, 1888], fill=marble)                       # far neck contour below the shoulder
    d.polygon([(979, 1804), (1000, 1811), (921, 1953), (899, 1946)], fill=marble)   # stroke on the chest
    a = np.asarray(im).astype(float) @ np.array([0.299, 0.587, 0.114])
    t = np.clip((a - 42.0) / (212.0 - 42.0), 0, 1)[..., None]
    g = np.array([int(GROUND[i:i + 2], 16) for i in (1, 3, 5)], float)
    m = np.array([int(MARBLE1[i:i + 2], 16) for i in (1, 3, 5)], float)
    out = Image.fromarray(np.uint8(np.round(g + t * (m - g)))).crop(BUST_CROP)
    out = out.resize((round(out.width * height / out.height), height), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def clip_glyph(s, x, y, ang, L, boot):
    """Alligator clip seen from above, jaws on the snap at (x, y), lying along ang (degrees).
    Drawn like the bust: marble fill, ground outline. The rubber boot carries the lead color."""
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)

    def T(u, v):
        return x + u * ca - v * sa, y + u * sa + v * ca
    w = L * 0.13
    s.poly([T(0, -0.3 * w), T(0.42 * L, -w), T(0.66 * L, -0.9 * w), T(0.66 * L, 0.9 * w), T(0.42 * L, w), T(0, 0.3 * w)],
           GROUND, 0.9, fill=MARBLE1, closed=True)
    s.line(*T(0.05 * L, 0), *T(0.38 * L, 0), GROUND, 0.6)
    s.circle(*T(0.47 * L, 0), 0.34 * w, GROUND, 0.6)
    s.poly([T(0.62 * L, -1.15 * w), T(L, -1.0 * w), T(L + 0.5 * w, 0), T(L, 1.0 * w), T(0.62 * L, 1.15 * w)],
           GROUND, 0.8, fill=boot, closed=True)
    return T(L + 0.5 * w, 0)


def fig_hero():
    from scipy import signal
    H = 460
    s = Svg(W, H)
    s.add(f'<rect width="{W}" height="{H}" fill="{GROUND}"/>')
    brackets(s)
    s.text(44, 62, "OPEN SOURCE EEG  ·  STARTER KIT", "fig_label")
    s.text(40, 156, "PiEEG", "title", INK, size=88)
    s.text(40, 240, "Home Lab", "title", INK, size=88)
    s.text(44, 282, "8 CHANNEL EEG  ·  RASPBERRY PI 3  ·  ADS1299  ·  24 BIT  ·  250 HZ", "spec", MUTED, size=11)
    for j, (lab, on) in enumerate([("DASHBOARD", False), ("PYTHON", True), ("SELF TEST", False)]):
        tx = 44 + j * 98
        s.rect(tx, 298, 96, 22, "none", 0, fill=ACCENT if on else SURFACE_TAB)
        s.text(tx + 48, 313, lab, "chip", ON_ACCENT if on else INK, "middle", size=10)
    s.rect(44, 322, 292, 30, "none", 0, fill=SURFACE_CODE)
    s.text(58, 342, "$ python live_view.py", "pin", INK, caps=False, size=12.5)
    # real EEG: PiEEG example recording, alpha bursts in trace-alpha
    v, t = trace()
    fs = t["sample_rate_hz"]
    env = np.abs(signal.hilbert(signal.sosfiltfilt(signal.butter(4, [8, 13], btype="band", fs=fs, output="sos"), v)))
    burst = np.convolve(env, np.ones(25) / 25, mode="same") > np.percentile(env, 50)
    x0, x1 = 44, 560
    xs = np.linspace(x0, x1, len(v))
    ys = 400 - v / np.percentile(np.abs(v), 99) * 22
    start = 0
    for j in range(1, len(v) + 1):
        if j == len(v) or burst[j] != burst[start]:
            seg = list(zip(xs[start:j + 1], ys[start:j + 1]))
            if len(seg) > 1:
                s.poly(seg, ALPHA if burst[start] else MUTED, 1.2)
            start = j
    s.text(x0, 442, f"REAL EEG  ·  PIEEG EXAMPLE DATA, CH {t['channel']}", "note")
    s.text(x1, 442, f"ALPHA BURSTS  ·  PEAK {t['alpha_peak_hz']:.1f} HZ", "note", ALPHA, "end")
    px_per_s = (x1 - x0) / len(v) * fs
    scale_bar(s, x1 - px_per_s - 64, 366, 1, px_per_s, "1 SECOND")
    # Athena, wearing the kit's electrodes where they really go
    sc = 440 / (BUST_CROP[3] - BUST_CROP[1])
    bx, by = 668, 10
    s.image(bx, by, (BUST_CROP[2] - BUST_CROP[0]) * sc, (BUST_CROP[3] - BUST_CROP[1]) * sc, athena_png())

    def B(ox, oy):
        return bx + (ox - BUST_CROP[0]) * sc, by + (oy - BUST_CROP[1]) * sc
    mm = 5.1 * sc                                   # the bust's scale: about 5.1 image px per mm
    # Fp1: 26 mm foam disc, lower edge just above the left eyebrow, centered over the pupil
    fx, fy = B(850, 960)
    s.ellipse(fx, fy, 11.8 * mm, 13 * mm, GROUND, 0.9, fill=MARBLE1)
    s.ellipse(fx, fy, 2.4 * mm, 2.6 * mm, GROUND, 0.6, fill=MARBLE2)
    # the leads: Fp1 clipped on the snap, cable over the temple and behind the ear (strain relief),
    # REF from under the hair behind the ear, BIAS from behind the neck; all drape over the shoulder
    e1_hang = [B(1236, 1384), B(1236, 1460), B(1244, 1560), B(1264, 1648), B(1318, 1696), B(1392, 1742),
               B(1440, 1782), B(1472, 1880), B(1490, 2090)]
    ref_hang = [B(1284, 1462), B(1280, 1540), B(1280, 1610), B(1292, 1664), B(1340, 1706), B(1405, 1750),
                B(1452, 1794), B(1488, 1890), B(1512, 2090)]
    bias_hang = [B(1298, 1626), B(1314, 1672), B(1362, 1712), B(1420, 1755), B(1466, 1802), B(1505, 1895), B(1536, 2090)]
    wire(s, bias_hang, BIASC, w=2.2)
    wire(s, ref_hang, REFC, w=2.2)
    wire(s, e1_hang, E1C, w=2.2)
    end = clip_glyph(s, fx, fy, 11, 28 * mm, E1C)
    wire(s, [end, B(1052, 1002), B(1112, 1040), B(1160, 1102), B(1188, 1166)], E1C, w=2.2)
    return s


FIGURES = {"hero": fig_hero, "system": fig_system, "kit": fig_kit, "assembly": fig_mounting,
           "placement": fig_placement, "wiring": fig_wiring, "header": fig_header}

if __name__ == "__main__":
    for n in sys.argv[1:] or list(FIGURES):
        export(FIGURES[n](), n)
