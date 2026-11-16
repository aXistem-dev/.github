"""Build the aXistem profile images: logo, banner, project cards and avatar.

Every image is a self-contained SVG. Text is converted to outlines, so the images look the
same on every machine and no web font is needed.

    uv run --no-project --with fonttools --with uharfbuzz python scripts/build.py

The avatar PNG is rendered separately with scripts/render.sh.
"""

from __future__ import annotations

import base64
import html
from dataclasses import dataclass, field
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets"

# ---------------------------------------------------------------- palette

THEMES = {
    "dark": {
        "page": "#0d1117",
        "card": "#161b22",
        "card2": "#11161d",
        "border": "#30363d",
        "text": "#e6edf3",
        "muted": "#9198a1",
        "chip": "#21262d",
        "chiptext": "#c9d1d9",
        "faint": "#1f2630",
        "cyan": "#38d6ff",
        "lime": "#a3ff3f",
    },
    "light": {
        "page": "#ffffff",
        "card": "#f6f8fa",
        "card2": "#ffffff",
        "border": "#d1d9e0",
        "text": "#1f2328",
        "muted": "#59636e",
        "chip": "#eaeef2",
        "chiptext": "#31373d",
        "faint": "#e6ebf0",
        "cyan": "#0b93bf",
        "lime": "#4f9a0c",
    },
}

ACCENT = ('<linearGradient id="{id}" x1="0" y1="0" x2="1" y2="1">'
          '<stop offset="0" stop-color="#38d6ff"/><stop offset="1" stop-color="#a3ff3f"/>'
          "</linearGradient>")

LANG_COLOURS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "C": "#555555",
    "C++": "#f34b7d",
    "Swift": "#F05138",
    "Docker": "#2496ED",
}

# ---------------------------------------------------------------- text to outlines


class Face:
    def __init__(self, file: str, weight: int, opsz: float | None = None):
        path = FONTS / file
        self.tt = TTFont(path)
        loc = {"wght": weight}
        if opsz is not None:
            loc["opsz"] = opsz
        self.glyphs = self.tt.getGlyphSet(location=loc)
        self.upem = self.tt["head"].unitsPerEm
        blob = hb.Blob.from_file_path(str(path))
        self.hbfont = hb.Font(hb.Face(blob))
        self.hbfont.set_variations(loc)
        self.order = self.tt.getGlyphOrder()

    def shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf, {"kern": True, "liga": True})
        return buf.glyph_infos, buf.glyph_positions

    def width(self, text: str, size: float, tracking: float = 0) -> float:
        _, pos = self.shape(text)
        return sum(p.x_advance for p in pos) * size / self.upem + tracking * max(len(pos) - 1, 0)

    def path(self, text: str, x: float, y: float, size: float, tracking: float = 0) -> str:
        """SVG path data for text with its baseline at y."""
        infos, pos = self.shape(text)
        scale = size / self.upem
        pen = SVGPathPen(self.glyphs)
        cx = 0.0
        for info, p in zip(infos, pos):
            name = self.order[info.codepoint]
            gx = x + (cx + p.x_offset) * scale
            gy = y - p.y_offset * scale
            tpen = TransformPen(pen, (scale, 0, 0, -scale, gx, gy))
            self.glyphs[name].draw(tpen)
            cx += p.x_advance + tracking / scale
        return pen.getCommands()


DISPLAY = Face("Exo2.ttf", 650)
DISPLAY_BOLD = Face("Exo2.ttf", 700)
BODY = Face("Inter.ttf", 400, 14)
BODY_MED = Face("Inter.ttf", 550, 14)


def text(face: Face, s: str, x: float, y: float, size: float, fill: str, tracking: float = 0,
         anchor: str = "start") -> str:
    if anchor == "middle":
        x -= face.width(s, size, tracking) / 2
    elif anchor == "end":
        x -= face.width(s, size, tracking)
    d = face.path(s, x, y, size, tracking)
    return f'<path d="{d}" fill="{fill}"/>'


def wrap(face: Face, s: str, size: float, max_w: float) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and face.width(trial, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- the mark

A_PATH = "M256,128 L376,392 L304,392 L288,354 L224,354 L208,392 L136,392 Z M256,228 L237,300 L275,300 Z"
FRONT = "36,36 170,36 476,476 342,476"
BACK = "342,36 476,36 170,476 36,476"


def mark(prefix: str) -> tuple[str, str]:
    """(defs, body) for the aXistem mark in a 512x512 box. Works on light and dark."""
    p = prefix
    defs = f"""
<linearGradient id="{p}bandA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#525b69"/><stop offset="1" stop-color="#2b313a"/></linearGradient>
<linearGradient id="{p}bandB" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a6372"/><stop offset="1" stop-color="#2e343d"/></linearGradient>
{ACCENT.format(id=p + "accent")}
<path id="{p}A" d="{A_PATH}"/>
<polygon id="{p}front" points="{FRONT}"/>
<mask id="{p}cutBack" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
  <rect width="512" height="512" fill="#fff"/>
  <use href="#{p}front" fill="#000" stroke="#000" stroke-width="20" stroke-linejoin="round"/>
  <use href="#{p}A" fill="#000" stroke="#000" stroke-width="28" stroke-linejoin="round"/>
</mask>
<mask id="{p}cutFront" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
  <rect width="512" height="512" fill="#fff"/>
  <use href="#{p}A" fill="#000" stroke="#000" stroke-width="28" stroke-linejoin="round"/>
</mask>"""
    body = f"""
<g mask="url(#{p}cutBack)">
  <polygon points="{BACK}" fill="url(#{p}bandB)"/>
  <g fill="none" stroke="#a3ff3f" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
    <path d="M400,70 L362,124 L362,150"/><rect x="389" y="47" width="22" height="22" rx="4"/>
    <path d="M440,70 L392,138"/><circle cx="446" cy="61" r="7" fill="#a3ff3f" stroke="none"/>
    <path d="M112,442 L150,388 L150,362"/><circle cx="106" cy="452" r="11"/>
    <path d="M72,442 L120,374"/><circle cx="66" cy="451" r="7" fill="#a3ff3f" stroke="none"/>
  </g>
</g>
<g mask="url(#{p}cutFront)">
  <use href="#{p}front" fill="url(#{p}bandA)"/>
  <g fill="none" stroke="#38d6ff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
    <path d="M112,70 L150,124 L150,150"/><rect x="101" y="47" width="22" height="22" rx="4"/>
    <path d="M72,70 L120,138"/><circle cx="66" cy="61" r="7" fill="#38d6ff" stroke="none"/>
    <path d="M400,442 L362,388 L362,362"/><circle cx="406" cy="452" r="11"/>
    <path d="M440,442 L392,374"/><circle cx="446" cy="451" r="7" fill="#38d6ff" stroke="none"/>
  </g>
</g>
<use href="#{p}A" fill="url(#{p}accent)" fill-rule="evenodd"/>"""
    return defs, body


def svg(w: int, h: int, defs: str, body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{html.escape(title)}">'
            f"<title>{html.escape(title)}</title><defs>{defs}</defs>{body}</svg>\n")


def build_logo() -> None:
    defs, body = mark("m")
    (OUT / "logo.svg").write_text(svg(512, 512, defs, body, "aXistem"))
    # Avatar: the mark on the dark page colour, with room for GitHub's rounded crop.
    defs, body = mark("v")
    av = f'<rect width="512" height="512" fill="#0d1117"/><g transform="translate(56 56) scale(0.78125)">{body}</g>'
    (OUT / "avatar.svg").write_text(svg(512, 512, defs, av, "aXistem"))


# ---------------------------------------------------------------- circuit decoration


def circuit(t: dict, w: int, h: int, side: str) -> str:
    """Faint circuit traces running in from one edge of a banner."""
    c = t["faint"]
    out = []
    if side == "right":
        traces = [
            (w, 46, w - 150, 46, w - 190, 86, w - 300, 86),
            (w, 120, w - 90, 120, w - 130, 160, w - 250, 160),
            (w, 236, w - 180, 236, w - 214, 202, w - 340, 202),
            (w, 270, w - 120, 270),
        ]
    else:
        traces = [
            (0, 60, 40, 60, 70, 30, 150, 30),
            (0, 250, 60, 250, 90, 280, 210, 280),
        ]
    for tr in traces:
        pts = " ".join(f"{tr[i]},{tr[i + 1]}" for i in range(0, len(tr), 2))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="3" stroke-linejoin="round"/>')
        out.append(f'<circle cx="{tr[-2]}" cy="{tr[-1]}" r="6" fill="none" stroke="{c}" stroke-width="3"/>')
    return "".join(out)


# ---------------------------------------------------------------- banner


def build_banner(theme: str) -> None:
    t = THEMES[theme]
    w, h = 1280, 300
    mdefs, mbody = mark("b")
    defs = mdefs + ACCENT.format(id="wordaccent") + (
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="20"/></clipPath>')
    body = [f'<g clip-path="url(#clip)"><rect width="{w}" height="{h}" fill="{t["card"]}"/>',
            circuit(t, w, h, "right"), circuit(t, w, h, "left"), "</g>",
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="19" fill="none" stroke="{t["border"]}" stroke-width="2"/>',
            f'<g transform="translate(70 40) scale(0.43)">{mbody}</g>']
    x, base = 330, 160
    size = 112
    a_w = DISPLAY_BOLD.width("a", size)
    x_w = DISPLAY_BOLD.width("X", size)
    body.append(text(DISPLAY_BOLD, "a", x, base, size, t["text"]))
    body.append(f'<path d="{DISPLAY_BOLD.path("X", x + a_w, base, size)}" fill="url(#wordaccent)"/>')
    body.append(text(DISPLAY_BOLD, "istem", x + a_w + x_w, base, size, t["text"]))
    body.append(text(BODY, "Open-source tools for MeshCore mesh radios and Home Assistant",
                     x + 4, 214, 27, t["muted"]))
    # A small accent rule under the tagline.
    body.append(f'<rect x="{x + 4}" y="238" width="96" height="5" rx="2.5" fill="url(#wordaccent)"/>')
    (OUT / f"banner-{theme}.svg").write_text(svg(w, h, defs, "".join(body), "aXistem"))


# ---------------------------------------------------------------- icons (48x48, stroke)

ICONS = {
    # chat bubble holding three linked mesh nodes
    "chat-mesh": """
<path d="M8 10h32a4 4 0 0 1 4 4v18a4 4 0 0 1-4 4H22l-9 7v-7H8a4 4 0 0 1-4-4V14a4 4 0 0 1 4-4z"/>
<circle cx="15" cy="25" r="3"/><circle cx="24" cy="18" r="3"/><circle cx="33" cy="25" r="3"/>
<path d="M17.5 23.2l4-3.4M26.5 19.8l4 3.4M18 25h12"/>""",
    # electric car seen from the side with a charge bolt
    "ev": """
<path d="M6 30v-5l4-8a4 4 0 0 1 3.6-2.2h20.8A4 4 0 0 1 38 17l4 8v5a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2z"/>
<path d="M8 25h32"/><circle cx="14" cy="32" r="4"/><circle cx="34" cy="32" r="4"/>
<path d="M25 4l-5 7h6l-4 6"/>""",
    # terminal window with prompt and stacked sessions
    "terminal": """
<rect x="4" y="9" width="36" height="28" rx="4"/><path d="M4 16h36"/>
<path d="M11 23l5 4-5 4M20 31h9"/><path d="M44 14v26a3 3 0 0 1-3 3H11"/>""",
    # browser window with a radio wave
    "browser-radio": """
<rect x="4" y="7" width="40" height="34" rx="4"/><path d="M4 15h40"/>
<circle cx="9" cy="11" r=".8"/><circle cx="13" cy="11" r=".8"/>
<circle cx="24" cy="30" r="2.5"/><path d="M18.5 24.5a8 8 0 0 0 0 11M29.5 24.5a8 8 0 0 1 0 11"/>
<path d="M15 21a13 13 0 0 0 0 18M33 21a13 13 0 0 1 0 18"/>""",
    # map pin over linked nodes
    "map-pin": """
<path d="M24 42s-12-11-12-21a12 12 0 0 1 24 0c0 10-12 21-12 21z"/><circle cx="24" cy="21" r="4.5"/>
<path d="M6 40l8-4M42 40l-8-4"/><circle cx="5" cy="41" r="1.6"/><circle cx="43" cy="41" r="1.6"/>""",
}


def icon_tile(name: str | None, image: str | None, x: float, y: float, s: float, t: dict, gid: str) -> str:
    out = [f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{s * 0.24}" fill="{t["card2"]}" '
           f'stroke="{t["border"]}" stroke-width="1.5"/>']
    if image:
        pad = s * 0.08
        out.append(f'<image x="{x + pad}" y="{y + pad}" width="{s - 2 * pad}" height="{s - 2 * pad}" href="{image}"/>')
    else:
        k = s * 0.7 / 48
        off = s * 0.15
        out.append(f'<g transform="translate({x + off} {y + off}) scale({k})" fill="none" stroke="url(#{gid})" '
                   f'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')
    return "".join(out)


# ---------------------------------------------------------------- project cards


@dataclass
class Card:
    slug: str
    name: str
    desc: str
    language: str
    tags: list[str] = field(default_factory=list)
    icon: str | None = None
    image: Path | None = None


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def build_card(c: Card, theme: str) -> None:
    t = THEMES[theme]
    w, h = 600, 224
    gid = "ic"
    defs = (f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["cyan"]}"/>'
            f'<stop offset="1" stop-color="{t["lime"]}"/></linearGradient>') + ACCENT.format(id="edge")
    body = [f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16" fill="{t["card"]}" '
            f'stroke="{t["border"]}" stroke-width="2"/>',
            f'<rect x="1" y="22" width="4" height="56" rx="2" fill="url(#edge)"/>']
    body.append(icon_tile(c.icon, data_uri(c.image) if c.image else None, 28, 28, 64, t, gid))
    tx = 112
    body.append(text(DISPLAY, c.name, tx, 58, 27, t["text"]))
    body.append(text(BODY, f"aXistem-dev/{c.slug}", tx, 84, 15, t["muted"]))
    lines = wrap(BODY, c.desc, 17.5, w - 28 - 28)
    if len(lines) > 3:
        raise SystemExit(f"{c.slug}: description is {len(lines)} lines, keep it to 3")
    for i, line in enumerate(lines):
        body.append(text(BODY, line, 28, 122 + i * 24, 17.5, t["text"]))
    # footer: language + tags
    fy = h - 22
    lc = LANG_COLOURS.get(c.language, t["muted"])
    body.append(f'<circle cx="34" cy="{fy - 5.5}" r="6" fill="{lc}"/>')
    body.append(text(BODY_MED, c.language, 47, fy, 14.5, t["muted"]))
    cx = 47 + BODY_MED.width(c.language, 14.5) + 18
    for tag in c.tags:
        tw = BODY_MED.width(tag, 13)
        body.append(f'<rect x="{cx}" y="{fy - 17}" width="{tw + 18}" height="23" rx="11.5" fill="{t["chip"]}"/>')
        body.append(text(BODY_MED, tag, cx + 9, fy - 1, 13, t["chiptext"]))
        cx += tw + 26
    if cx > w - 20:
        raise SystemExit(f"{c.slug}: tags overflow the card")
    # Projects with three description lines push the footer; keep them apart.
    if 122 + (len(lines) - 1) * 24 > fy - 30:
        raise SystemExit(f"{c.slug}: description runs into the footer")
    (OUT / "cards").mkdir(exist_ok=True)
    (OUT / "cards" / f"{c.slug}-{theme}.svg").write_text(svg(w, h, defs, "".join(body), c.name))


CARDS = [
    Card("MicroPyMesh", "MicroPyMesh",
         "MeshCore messenger for MicroPythonOS: channels, direct messages, repeater admin "
         "and an offline map on 480×480 touch screens.",
         "Python", ["MeshCore", "ESP32"], icon="chat-mesh"),
    Card("ha-myskoda-public-api", "MyŠkoda for Home Assistant",
         "Unofficial Home Assistant integration for Škoda cars on the official MyŠkoda "
         "Public API. Signs in with an API key, no account password.",
         "Python", ["Home Assistant", "EV"], icon="ev"),
    Card("axism", "aXism",
         "Agent Interactive Session Manager: one TUI and CLI for the sessions of "
         "Claude Code, Cursor, Hermes and OpenCode.",
         "Python", ["TUI", "PyPI"], image=ROOT / "scripts" / "img" / "axism-icon.png"),
    Card("meshcore-web", "meshcore-web",
         "The MeshCore companion web app as a Docker image, so you can host it yourself "
         "and talk to your radio over Bluetooth or USB.",
         "Docker", ["MeshCore", "Self-hosted"], icon="browser-radio"),
    Card("MC-NL-Map", "MC-NL-Map",
         "Interactive map of MeshCore nodes in the Netherlands, with filters, search and "
         "activity stats. Derived from the official map.",
         "JavaScript", ["MeshCore", "Map"], icon="map-pin"),
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    build_logo()
    for theme in THEMES:
        build_banner(theme)
        for c in CARDS:
            build_card(c, theme)
    print("built", sorted(str(p.relative_to(ROOT)) for p in OUT.rglob("*.svg")))


if __name__ == "__main__":
    main()
