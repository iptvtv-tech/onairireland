#!/usr/bin/env python3
"""
Build the free 8-page device guide that newsletter subscribers get:
assets/downloads/legal-streaming-device-guide.pdf

The original generator was lost, so this script rebuilds the guide to match
the earlier PDF (A4, DejaVu Sans, navy header band, same figures and tables).
All the wording lives in this file: for a fact check, edit the text here and
re-run the script. Never edit the PDF by hand.

Every claim about devices and Irish apps must agree with the "Streaming
devices and Irish apps" entry in _data/site_facts.yml. No device prices: they
change too often, so the guide tells readers to check the current price.

Every printed onairireland.ie address is a clickable link to the full
https://onairireland.ie/... URL. Before writing the PDF the script checks each
on-site link against the site's real addresses (posts, using the permalink
/:categories/:title/, and _pages permalinks) and stops if one doesn't exist.

    python scripts/make_device_guide.py

then review the PDF before committing it.

Needs: pip install reportlab pyyaml
"""
import math
import os
import re
import sys

import yaml
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Ellipse, Group, Line, Path, Polygon, Rect, String
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "downloads", "legal-streaming-device-guide.pdf")
SITE = "https://onairireland.ie"

# Change these at each fact check
UPDATED = "November 2026"
EDITION = "2026 EDITION"
DOC_TITLE = "Choosing the Right Streaming Device"

# House colours (as in the other PDFs)
NAVY = HexColor("#0f172a")
INK = HexColor("#1e293b")
SLATE = HexColor("#475569")
MUTED = HexColor("#64748b")
ACCENT = HexColor("#0284c7")
SKY = HexColor("#38bdf8")
ORANGE = HexColor("#fb923c")
AMBER = HexColor("#b45309")
PANEL = HexColor("#f1f5f9")
BLUE_PANEL = HexColor("#eff6ff")
AMBER_PANEL = HexColor("#fef3c7")
RULE = HexColor("#e2e8f0")
COVER_TOP = HexColor("#0f172a")
COVER_BOTTOM = HexColor("#1e3a5f")

W, H = A4
MARGIN = 51.02362  # 18 mm
TEXT_W = W - 2 * MARGIN


# --------------------------------------------------------------------------
# Fonts

def register_fonts():
    """DejaVu Sans if it's installed (matches the other PDFs), else Helvetica."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/dejavu",
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
    ]
    for folder in candidates:
        files = {name: os.path.join(folder, f) for name, f in
                 (("Body", "DejaVuSans.ttf"), ("Body-Bold", "DejaVuSans-Bold.ttf"),
                  ("Body-Italic", "DejaVuSans-Oblique.ttf"))}
        if all(os.path.exists(p) for p in files.values()):
            for name, path in files.items():
                pdfmetrics.registerFont(TTFont(name, path))
            pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold",
                                          italic="Body-Italic", boldItalic="Body-Bold")
            return "Body", "Body-Bold", "Body-Italic"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


BODY, BOLD, ITALIC = register_fonts()


# --------------------------------------------------------------------------
# On-site links: build the site's real addresses and check every link

def front_matter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def site_paths():
    """Every public path on the site: posts (permalink /:categories/:title/) and _pages."""
    paths = {"/"}
    posts = os.path.join(ROOT, "_posts")
    for name in sorted(os.listdir(posts)):
        if not name.endswith((".md", ".markdown", ".html")):
            continue
        fm = front_matter(os.path.join(posts, name))
        if fm.get("published") is False:
            continue
        if fm.get("permalink"):
            paths.add(fm["permalink"])
            continue
        cats = fm.get("categories") or fm.get("category") or []
        if isinstance(cats, str):
            cats = cats.split()
        slug = fm.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.splitext(name)[0])
        prefix = "/".join(str(c).lower() for c in cats)
        paths.add(f"/{prefix}/{slug}/" if prefix else f"/{slug}/")
    pages = os.path.join(ROOT, "_pages")
    for name in sorted(os.listdir(pages)):
        fm = front_matter(os.path.join(pages, name))
        if fm.get("permalink") and fm.get("published") is not False:
            paths.add(fm["permalink"])
    return paths


LINKS_USED = []


def site(path):
    """Full URL for an on-site path; remembered so main() can check it exists."""
    LINKS_USED.append(path)
    return SITE + path


def link(url, text):
    return f'<a href="{url}">{text}</a>'


# --------------------------------------------------------------------------
# Paragraph styles

def style(name, **kw):
    base = dict(fontName=BODY, fontSize=10, leading=14.5, textColor=INK, spaceBefore=0, spaceAfter=0)
    base.update(kw)
    return ParagraphStyle(name, **base)


S_H1 = style("h1", fontName=BOLD, fontSize=20, leading=25, textColor=NAVY, spaceAfter=8)
S_H2 = style("h2", fontName=BOLD, fontSize=14, leading=18, textColor=NAVY, spaceBefore=12, spaceAfter=6)
S_H3 = style("h3", fontName=BOLD, fontSize=11.5, leading=15, textColor=ACCENT, spaceBefore=8, spaceAfter=3)
S_LEAD = style("lead", fontSize=11.5, leading=16.5, textColor=SLATE, spaceAfter=8)
S_BODY = style("body", spaceAfter=6)
S_BULLET = style("bullet", leading=14, leftIndent=14, bulletIndent=2, bulletFontName="Helvetica",
                 bulletFontSize=10, spaceAfter=3)
S_NOTE = style("note", fontSize=8, leading=11, textColor=MUTED)
S_CAPTION = style("caption", fontName=ITALIC, fontSize=8, leading=11, textColor=MUTED, alignment=TA_CENTER,
                  spaceBefore=3, spaceAfter=8)
S_TH = style("th", fontName=BOLD, fontSize=8.8, leading=11.8, textColor=white)
S_TD_KEY = style("tdk", fontName=BOLD, fontSize=8.8, leading=11.8, textColor=NAVY)
S_TD = style("td", fontSize=8.8, leading=11.8, textColor=INK)
S_BOX_TITLE = style("boxt", fontName=BOLD, fontSize=10.5, leading=14, textColor=NAVY, spaceAfter=3)
S_BOX_BODY = style("boxb", fontSize=9.4, leading=13.2, textColor=INK)


def h1(t): return Paragraph(t, S_H1)
def h2(t): return Paragraph(t, S_H2)
def lead(t): return Paragraph(t, S_LEAD)
def body(t): return Paragraph(t, S_BODY)
def note(t): return Paragraph(t, S_NOTE)
def caption(t): return Paragraph(t, S_CAPTION)
def bullet(t): return Paragraph(t, S_BULLET, bulletText="•")
def numbered(items): return [Paragraph(t, S_BULLET, bulletText=f"{i}.") for i, t in enumerate(items, 1)]


def table(rows, fractions):
    """Navy header row, then rows striped white / light grey. First column bold."""
    data = [[Paragraph(c, S_TH) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(c, S_TD_KEY if i == 0 else S_TD) for i, c in enumerate(r)])
    t = Table(data, colWidths=[TEXT_W * f for f in fractions], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, PANEL]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def callout(title, text, panel=BLUE_PANEL, edge=ACCENT):
    """Tinted box with a thick coloured line down the left."""
    t = Table([[[Paragraph(title, S_BOX_TITLE), Paragraph(text, S_BOX_BODY)]]], colWidths=[TEXT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), panel),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, edge, 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


# --------------------------------------------------------------------------
# Drawing helpers (all figures are vector, drawn here; no photos)

def rrect(x, y, w, h, r, fill, stroke=None, sw=1):
    return Rect(x, y, w, h, rx=r, ry=r, fillColor=HexColor(fill) if fill else None,
                strokeColor=HexColor(stroke) if stroke else None, strokeWidth=sw)


def rect(x, y, w, h, fill):
    return Rect(x, y, w, h, fillColor=HexColor(fill), strokeColor=None)


def dot(cx, cy, r, fill, stroke=None, sw=1):
    return Circle(cx, cy, r, fillColor=HexColor(fill), strokeColor=HexColor(stroke) if stroke else None,
                  strokeWidth=sw)


def text(x, y, s, size, color, font=None, anchor="start"):
    return String(x, y, s, fontName=font or BODY, fontSize=size, fillColor=HexColor(color), textAnchor=anchor)


def wifi(cx, cy, r):
    """Three stroked wedges and a dot: the Wi-Fi symbol."""
    g = Group()
    a0, a1 = math.radians(50), math.radians(130)
    k = 4 / 3 * math.tan((a1 - a0) / 4)
    for scale, sw in ((1, 2.2), (0.66, 1.9), (0.33, 1.6)):
        rr = r * scale
        x0, y0 = cx + rr * math.cos(a0), cy + rr * math.sin(a0)
        x3, y3 = cx + rr * math.cos(a1), cy + rr * math.sin(a1)
        p = Path(strokeColor=SKY, strokeWidth=sw, fillColor=None)
        p.moveTo(cx, cy)
        p.lineTo(x0, y0)
        p.curveTo(x0 - k * rr * math.sin(a0), y0 + k * rr * math.cos(a0),
                  x3 + k * rr * math.sin(a1), y3 - k * rr * math.cos(a1), x3, y3)
        p.closePath()
        g.add(p)
    g.add(dot(cx, cy + 1, 2, "#38bdf8"))
    return g


def arrow(x1, y1, x2, y2, color=ACCENT):
    """Line with a filled arrowhead at (x2, y2)."""
    g = Group()
    g.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.4))
    ang = math.atan2(y2 - y1, x2 - x1)
    size, spread = 6, math.radians(25.8)
    pts = [x2, y2]
    for s in (-1, 1):
        pts += [x2 - size * math.cos(ang + s * spread), y2 - size * math.sin(ang + s * spread)]
    g.add(Polygon(pts, fillColor=color, strokeColor=None))
    return g


def badge(cx, cy, n):
    """Orange numbered circle used in Figure 2."""
    g = Group()
    g.add(dot(cx, cy, 9, "#fb923c", "#ffffff", 1.5))
    g.add(text(cx, cy - 3.5, str(n), 10, "#ffffff", BOLD, "middle"))
    return g


APP_COLOURS = ["#0284c7", "#fb923c", "#16a34a", "#8b5cf6", "#e11d48",
               "#0ea5e9", "#f59e0b", "#14b8a6", "#0284c7", "#fb923c"]


def cover_illustration():
    """TV on a sideboard with a soundbar, remote, router, plant and a stick."""
    d = Drawing(430, 340)
    d.add(Circle(215, 170, 150, fillColor=HexColor("#1e3a5f"), strokeColor=None))
    d.add(rrect(91, 116, 248, 144, 4, "#0b1220"))
    d.add(rect(95, 120, 240, 136, "#0b1a33"))
    d.add(rrect(105, 198, 220, 48, 4, "#1d4ed8"))
    d.add(rrect(113, 226, 80, 8, 2, "#ffffff"))
    d.add(rrect(113, 212, 50, 6, 2, "#93c5fd"))
    for row, y in enumerate((132, 162)):
        for col in range(5):
            colour = APP_COLOURS[col if row == 0 else 5 + col]
            d.add(rrect(105 + col * 45.2, y, 39.2, 24, 4, colour))
    d.add(rrect(125, 94, 180, 12, 5, "#111827"))            # soundbar
    for i in range(12):
        d.add(dot(139 + i * 13.5, 100, 1.3, "#4b5563"))
    d.add(rrect(341, 160, 27.2, 9.6, 2.4, "#111827"))       # stick in the TV's side
    d.add(rect(368.2, 162.4, 6.4, 4.8, "#9ca3af"))
    d.add(rrect(60, 40, 310, 36, 4, "#78350f"))             # sideboard
    d.add(rect(60, 72, 310, 5, "#92400e"))
    d.add(rrect(300, 78, 44, 16, 3, "#e5e7eb"))             # router
    for x in (310, 318, 326):
        d.add(dot(x, 86, 1.6, "#16a34a"))
    d.add(wifi(322, 100, 12))
    d.add(rrect(80, 78, 22, 20, 3, "#f5f5f4"))              # plant pot and leaves
    for cx, cy in ((83, 110), (91, 120), (100, 112), (88, 116), (97, 124)):
        d.add(Ellipse(cx, cy, 6, 12, fillColor=HexColor("#22c55e"), strokeColor=None))
    d.add(rrect(200, 80, 7.7, 27.5, 3.3, "#1f2937"))        # remote
    d.add(dot(203.85, 100.9, 2.475, "#6b7280"))
    for y in (93.2, 89.35, 85.5):
        d.add(dot(203.85, y, 0.99, "#9ca3af"))
    return d


def flowchart():
    """Figure 1: do you need a streaming device?"""
    d = Drawing(TEXT_W, 250)

    def box(x, y, w, h, lines, fill, edge):
        d.add(rrect(x, y, w, h, 6, fill, edge, 1.2))
        cx = x + w / 2
        top = y + h / 2 + 5.4 * (len(lines) - 1) - 1.8
        for i, s in enumerate(lines):
            d.add(text(cx, top - i * 10.8, s, 8.2, "#0f172a", BOLD if i == 0 else BODY, "middle"))

    box(161.6142, 205, 170, 40, ["Is your TV a smart TV", "from roughly 2019 or later?"], "#eff6ff", "#0284c7")
    box(0, 130, 150, 44, ["No, or not sure", "You'll need a streaming", "stick or box"], "#fef3c7", "#b45309")
    box(161.6142, 130, 170, 44, ["Yes", "Are all your apps in its", "app store, and do they run well?"],
        "#eff6ff", "#0284c7")
    box(333.2283, 50, 150, 44, ["Yes to both", "You don't need a device.", "Just install the apps."],
        "#dcfce7", "#16a34a")
    box(161.6142, 50, 170, 44, ["Missing apps, or slow?", "Add a stick or box —", "it replaces the TV's apps"],
        "#fef3c7", "#b45309")
    box(0, 0, 150, 40, ["Then pick one", "using pages 3–5"], "#ffffff", "#0284c7")
    for a in ((201.6142, 205, 75, 174), (246.6142, 205, 246.6142, 174), (246.6142, 130, 246.6142, 94),
              (331.6142, 140, 408.2283, 94), (75, 130, 75, 40), (161.6142, 72, 150, 20)):
        d.add(arrow(*a))
    return d


def device_icons():
    """The five setup types, as simple icons in pale circles."""
    d = Drawing(TEXT_W, 110)
    step = TEXT_W / 5
    labels = [("Streaming stick", "Fire TV Stick"), ("Streaming box", "Google TV Streamer"),
              ("Premium box", "Apple TV 4K"), ("Smart TV apps", "Samsung, LG, Sony…"),
              ("Provider box", "Sky Stream, Virgin 360")]
    for i, (name, sub) in enumerate(labels):
        cx = step * (i + 0.5)
        d.add(dot(cx, 68, 34, "#eff6ff"))
        if i == 0:
            d.add(rrect(cx - 21, 62, 34, 12, 3, "#111827"))
            d.add(rect(cx + 13, 65, 8, 6, "#9ca3af"))
        elif i == 1:
            d.add(rrect(cx - 18, 56, 36, 22, 8, "#e7e5e4", "#a8a29e", 1))
            d.add(dot(cx, 60, 1.5, "#78716c"))
        elif i == 2:
            d.add(rrect(cx - 18, 58, 36, 18, 5, "#111827"))
        elif i == 3:
            d.add(rrect(cx - 28, 54, 56, 36, 4, "#0b1220"))
            d.add(rect(cx - 24, 58, 48, 28, "#0284c7"))
            for j, colour in enumerate(("#0284c7", "#fb923c", "#16a34a", "#8b5cf6", "#e11d48", "#0ea5e9")):
                d.add(rrect(cx - 18 + (j % 3) * 14, 64 + (j // 3) * 11, 8, 5, 4, colour))
        else:
            d.add(rrect(cx - 16, 56, 32, 24, 12, "#1f2937"))
            d.add(dot(cx, 68, 3, "#38bdf8"))
        d.add(text(cx, 22, name, 8.2, "#0f172a", BOLD, "middle"))
        d.add(text(cx, 10, sub, 7.4, "#475569", BODY, "middle"))
    return d


def setup_diagram():
    """Figure 2: stick into the TV, power from the wall, Wi-Fi from the router."""
    d = Drawing(TEXT_W, 190)
    # TV
    d.add(rrect(289.23, 66, 188, 112, 4, "#0b1220"))
    d.add(rect(293.23, 70, 180, 104, "#1e293b"))
    d.add(rect(380.23, 52, 6, 14, "#334155"))
    d.add(rrect(353.23, 50, 60, 4, 2, "#334155"))
    tiles = ["#0284c7", "#fb923c", "#16a34a", "#8b5cf6", "#e11d48", "#0ea5e9",
             "#f59e0b", "#14b8a6", "#0284c7", "#fb923c", "#16a34a", "#8b5cf6"]
    for j, colour in enumerate(tiles):
        d.add(rrect(299.23 + (j % 4) * 43.5, 76 + (j // 4) * 32.667, 37.5, 26.667, 4, colour))
    # HDMI port and stick
    d.add(rect(277.23, 110, 12, 10, "#9ca3af"))
    d.add(rrect(229.23, 109, 37.4, 13.2, 3.3, "#111827"))
    d.add(rect(266.63, 112.3, 8.8, 6.6, "#9ca3af"))
    d.add(badge(249.23, 88, 1))
    d.add(badge(383.23, 36, 4))
    d.add(text(397.23, 32, "TV input", 7.5, "#475569"))
    # Wall socket, plug and cable
    d.add(rrect(30, 14, 34, 40, 4, "#ffffff", "#475569", 1))
    d.add(rect(40, 30, 4, 10, "#475569"))
    d.add(rect(50, 30, 4, 10, "#475569"))
    d.add(rrect(74, 24, 26, 20, 3, "#111827"))
    for x1, y1, x2, y2 in ((100, 34, 223.23, 34), (223.23, 34, 223.23, 113), (223.23, 113, 229.23, 113)):
        d.add(Line(x1, y1, x2, y2, strokeColor=HexColor("#111827"), strokeWidth=2))
    d.add(badge(87, 62, 2))
    d.add(text(47, 2, "Wall socket", 7.5, "#475569", anchor="middle"))
    # Router
    d.add(rrect(20, 124, 80, 26, 4, "#e5e7eb", "#475569", 1))
    for x in (34, 46, 58, 70):
        d.add(dot(x, 137, 2.2, "#16a34a"))
    d.add(wifi(60, 156, 16))
    d.add(text(60, 112, "Router", 7.5, "#475569", anchor="middle"))
    d.add(arrow(106, 137, 231.23, 126))
    d.add(badge(150, 150, 3))
    d.add(text(164, 146, "Wi-Fi or Ethernet", 7.5, "#0284c7"))
    return d


SPEEDS = [  # (label, Mbps, colour). Per-stream figures: Netflix Help Centre
    ("SD (standard definition)", 3, "#0284c7"),
    ("HD (1080p)", 5, "#0284c7"),
    ("4K Ultra HD", 15, "#0284c7"),
    ("Family: 4K + two HD streams", 25, "#fb923c"),
]


def speed_chart():
    """Figure 3: horizontal bars, broadband speed per stream."""
    d = Drawing(TEXT_W, 150)
    scale = 215.19 / max(v for _, v, _ in SPEEDS)
    for i, (label, mbps, colour) in enumerate(SPEEDS):
        y = 118 - i * 32
        w = mbps * scale
        d.add(text(165, y + 6, label, 8.6, "#0f172a", BOLD, "end"))
        d.add(rrect(175, y, w, 20, 4, colour))
        d.add(text(175 + w + 6, y + 6, f"{mbps} Mbps", 9, "#0f172a", BOLD))
    d.add(text(0, 0, "Per-stream figures are Netflix's recommendations; the family figure adds them together.",
               7.2, "#64748b", ITALIC))
    return d


# --------------------------------------------------------------------------
# Page furniture

def draw_cover(c, doc):
    c.saveState()
    c.translate(0, 1)
    c.setFillColor(COVER_TOP)
    c.rect(-10, -10, W + 20, H + 20, stroke=0, fill=1)
    bands = 120
    step = H / bands
    for i in range(bands):
        t = i / bands
        c.setFillColorRGB(*(a + (b - a) * t for a, b in zip(COVER_TOP.rgb(), COVER_BOTTOM.rgb())))
        c.rect(-10, H - (i + 1) * step, W + 20, step + 1.5, stroke=0, fill=1)
    c.saveState()
    c.translate(50.3878, 277.8236)
    c.scale(1.15, 1.15)
    renderPDF.draw(cover_illustration(), c, 0, 0)
    c.restoreState()
    c.setFillColor(SKY)
    c.setFont(BOLD, 10)
    c.drawString(MARGIN, 779.53, "ON AIR IRELAND")
    c.setFillColor(HexColor("#cbd5e1"))
    c.setFont(BODY, 9)
    c.drawRightString(W - MARGIN, 779.53, "FREE GUIDE")
    c.setFillColor(ORANGE)
    c.setFont(BOLD, 10.5)
    c.drawString(MARGIN, 210.47, f"FREE GUIDE · {EDITION}")
    c.setFillColor(white)
    c.setFont(BOLD, 30)
    c.drawString(MARGIN, 170.79, "Choosing the Right")
    c.drawString(MARGIN, 135.35, "Streaming Device")
    c.setFillColor(HexColor("#cbd5e1"))
    c.setFont(BODY, 12)
    c.drawString(MARGIN, 105.59, "Fire TV, Google TV, Roku, Apple TV or your smart TV — for Irish homes")
    c.setFillColor(HexColor("#94a3b8"))
    c.setFont(BODY, 8.5)
    c.drawString(MARGIN, 39.69, f"onairireland.ie  ·  Updated {UPDATED}  ·  100% licensed, legal services only")
    w = pdfmetrics.stringWidth("onairireland.ie", BODY, 8.5)
    c.restoreState()
    c.linkURL(site("/"), (MARGIN, 38.69, MARGIN + w, 48.69), relative=0, thickness=0)


def draw_page(c, doc):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, H - 31.1811, W, 31.1811, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont(BOLD, 8.5)
    c.drawString(MARGIN, 822.0472, "ON AIR IRELAND")
    c.setFont(BODY, 8.5)
    c.drawRightString(W - MARGIN, 822.0472, DOC_TITLE)
    c.setFillColor(MUTED)
    c.setFont(BODY, 7.5)
    c.drawString(MARGIN, 25.51181, "onairireland.ie  ·  Independent guides to legal streaming in Ireland")
    c.drawRightString(W - MARGIN, 25.51181, f"Page {doc.page}")
    c.setStrokeColor(RULE)
    c.setLineWidth(1)
    c.line(MARGIN, 36.85039, W - MARGIN, 36.85039)
    w = pdfmetrics.stringWidth("onairireland.ie", BODY, 7.5)
    c.restoreState()
    c.linkURL(site("/"), (MARGIN, 23.5, MARGIN + w, 32.5), relative=0, thickness=0)


# --------------------------------------------------------------------------
# The guide. Edit the wording here.

def story():
    s = [NextPageTemplate("page"), PageBreak()]

    # Page 2
    s += [
        h1("Start here: do you even need one?"),
        lead("Every legal streaming service in Ireland — RTÉ Player, Virgin Media Play, TG4 Player, "
             "Netflix, Disney+, HBO Max, NOW, GAA+ and the rest — runs through an app. The only question "
             "is <i>where</i> that app runs: on the TV itself, or on a small device plugged into it."),
        flowchart(),
        caption("Figure 1. Deciding whether you need a streaming device."),
        callout("The quick test",
                "Open your TV's app store and search for <b>RTÉ Player</b>, <b>Virgin Media Play</b> and any "
                "paid service you use. If they're all there and the menus don't lag, you're done. If an app is "
                "missing, or your TV no longer gets software updates, a streaming stick is usually the cheapest "
                "fix — far cheaper than a new TV."),
        PageBreak(),
    ]

    # Page 3
    s += [
        h1("The five types of streaming setup"),
        device_icons(),
        Spacer(1, 6),
        table([
            ["Type", "What it is", "Good for", "Watch out for"],
            ["Streaming stick", "Plugs straight into an HDMI port; powered from the wall",
             "Cheapest way to modernise any TV with HDMI", "Wi-Fi only on most sticks unless you add an adapter"],
            ["Streaming box", "A small box beside or behind the TV",
             "Faster, more storage, often an Ethernet port", "Costs more than a stick"],
            ["Premium box", "Apple TV 4K",
             "iPhone households, polished interface, long software support", "Highest price"],
            ["Smart TV apps", "Apps built into the TV (Samsung, LG, Sony, Philips, TCL, Hisense…)",
             "No extra box or remote", "Older TVs stop getting app updates; some apps disappear"],
            ["Provider box", "Sky Stream, Virgin TV 360, Eir Vision box",
             "One remote for live channels, recordings and apps", "Tied to a monthly TV contract"],
        ], [0.17, 0.29, 0.28, 0.26]),
        Spacer(1, 8),
        callout("Stick to official app stores",
                "Every device in this guide is a mainstream product that runs licensed apps from an official app "
                "store. Install RTÉ Player, TG4 Player, Virgin Media Play and GAA+ from your device's Irish app "
                "store, as apps from a UK or US store account may not work.",
                panel=AMBER_PANEL, edge=AMBER),
        PageBreak(),
    ]

    # Page 4. Must agree with "Streaming devices and Irish apps" in _data/site_facts.yml
    s += [
        h1("The main devices, compared"),
        h2("Amazon Fire TV"),
        body("The most common choice in Irish homes: an Alexa voice remote, frequent sales and, on Fire OS "
             "models, wide app support. The range runs from the Fire TV Stick HD to the Fire TV Stick 4K, "
             "4K Plus and 4K Max and the hands-free Fire TV Cube."),
        bullet("<b>Best for:</b> most households, especially Amazon Prime members."),
        bullet("<b>Watch out:</b> the home screen promotes Prime Video content heavily."),
        bullet("<b>Fire OS or Vega OS?</b> The Fire TV Stick 4K (3rd gen, 2026), Fire TV Stick HD "
               "(2026) and Fire TV Stick 4K Select (2025) run Amazon's newer Vega OS, not Fire OS. Vega OS has "
               "fewer apps, and it isn't confirmed that RTÉ Player, Virgin Media Play or TG4 Player are "
               "available on Vega models. For Irish apps, the safe pick is the Fire TV Stick 4K Max (2nd gen, "
               "2023), which runs Fire OS (the Fire TV Stick 4K Plus also does, where it's sold). Before you buy, check that the "
               "listing says which OS the stick runs."),
        h2("Google TV Streamer"),
        body("Google's replacement for the Chromecast with Google TV, which was discontinued in 2024. It's a "
             "small box rather than a stick, with 4K HDR and Dolby Vision, 32GB of storage, built-in casting, an "
             "Ethernet port and a smart-home panel. It's sold in Ireland on the Google Store; check the current "
             "price there."),
        bullet("<b>Best for:</b> Android phone users, and anyone who casts a lot from their phone."),
        bullet("<b>Watch out:</b> pricier than basic sticks. If you already own a Chromecast with Google TV, it "
               "still works — there's no need to replace it."),
        bullet("<b>NOW:</b> NOW's Irish device list names the Chromecast with Google TV but not the Google TV "
               "Streamer yet, so check NOW's own list before you buy it mainly for NOW."),
        h2("Apple TV 4K"),
        body("The most polished interface and the longest software support, with tight iPhone integration "
             "(AirPlay, quick sign-in from your iPhone). RTÉ Player and GAA+ both have Apple TV apps."),
        bullet("<b>Best for:</b> iPhone households who want a premium, ad-light experience."),
        bullet("<b>Watch out:</b> the most expensive option here."),
        bullet("<b>New for 2026:</b> the 4th-generation Apple TV 4K was announced on 13 October 2026 and is in "
               "shops from 13 November 2026. Check the current price before you buy."),
        h2("Roku"),
        body("Simple, uncluttered menus and a straightforward remote, which suits less tech-confident viewers. "
             "Roku is sold in Ireland, including on Amazon.ie."),
        bullet("<b>Best for:</b> anyone who finds other menus confusing."),
        bullet("<b>Watch out:</b> check TG4 Player if you need it, as it isn't confirmed on Roku. Roku says "
               "RTÉ Player is officially available on Roku in Ireland, Virgin Media Play is in the Roku Channel "
               "Store, and GAA+ lists Roku as supported."),
        PageBreak(),
    ]

    # Page 5
    s += [
        h1("Smart TVs and provider boxes"),
        h2("Smart TV platforms"),
        table([
            ["Platform", "Found on", "Notes"],
            ["Tizen", "Samsung", "Strong app support on recent models. GAA+ supports Samsung TVs from 2021 onwards"],
            ["webOS", "LG", "Well supported by Irish apps, including RTÉ Player and GAA+"],
            ["Google TV / Android TV", "Sony, Philips, TCL, Hisense (some)",
             "Uses the Google Play store, so most apps are available"],
            ["Fire TV built in", "Xiaomi, Panasonic (some), Amazon-branded TVs", "Same app store as a Fire TV Stick"],
            ["VIDAA", "Hisense", "Smaller app store — check for Irish apps before buying"],
        ], [0.22, 0.30, 0.48]),
        note("Rule of thumb: TV makers only keep updating a model's apps for a number of years. After that, apps "
             "may slow down or be withdrawn, and a stick is the cheapest way to keep the TV useful."),
        h2("Provider boxes"),
        body("If you pay for Sky, Virgin Media or Eir TV, your box already runs many of the apps you need, "
             "including RTÉ Player on Sky and Virgin TV 360. Check what your box offers before buying another "
             "device — you may only need one for a service your provider doesn't carry."),
        h2("Which one should you buy?"),
        table([
            ["If you…", "Our suggestion"],
            ["Want the easiest all-rounder", "Amazon Fire TV Stick 4K Max (Fire OS)"],
            ["Have an older TV in a bedroom or kitchen", "Fire TV Stick 4K Max (Fire OS) — fine on HD TVs too"],
            ["Use an Android phone and cast a lot", "Google TV Streamer"],
            ["Live in the Apple world", "Apple TV 4K"],
            ["Want the simplest possible menus", "Roku (check TG4 Player if you need it)"],
            ["Have a recent Samsung or LG TV", "Probably nothing — try the built-in apps first"],
            ["Watch lots of live sport in 4K", "A box with an Ethernet port, wired to your router"],
        ], [0.5, 0.5]),
        note("Buying a Fire TV stick? Check that the listing says it runs Fire OS. Some newer models run Vega OS, "
             "which has fewer apps."),
        PageBreak(),
    ]

    # Page 6
    s += [
        h1("Setting up a streaming stick in 10 minutes"),
        setup_diagram(),
        caption("Figure 2. 1 stick into the HDMI port · 2 power from the wall · 3 Wi-Fi from your router · "
                "4 switch the TV to that input."),
    ]
    s += numbered([
        "<b>Plug in.</b> Put the stick in a free HDMI port. If it won't fit, use a short HDMI extender (Fire TV "
        "sticks include one) — it also improves Wi-Fi reception.",
        "<b>Power it from the wall.</b> Use the supplied adapter. TV USB ports often don't give enough power, "
        "which causes random restarts.",
        "<b>Pick the input.</b> Press Input or Source on your TV remote and choose the HDMI port you used.",
        "<b>Join Wi-Fi and sign in.</b> Follow the on-screen steps and sign in to your Amazon, Google, Apple or "
        "Roku account.",
        "<b>Install your apps.</b> Start with RTÉ Player, Virgin Media Play and TG4 Player (all free), then your "
        "paid services.",
        "<b>Sign in to each app.</b> Most show a short code on screen that you enter on your phone — quicker than "
        "typing passwords with a remote.",
        "<b>Tidy up.</b> Turn on HDMI-CEC (sometimes called Anynet+, SimpLink or Bravia Sync) so one remote "
        "controls the TV volume and power.",
    ])
    s.append(PageBreak())

    # Page 7
    s += [
        h1("Broadband and Wi-Fi: the real secret to smooth streaming"),
        body("Most buffering isn't the device's fault — it's the connection between your router and the TV. "
             "Here's how much speed you need, per stream:"),
        speed_chart(),
        caption("Figure 3. Recommended broadband speed per stream. Source: Netflix Help Centre."),
        h2("Five fixes that work"),
    ]
    s += numbered([
        "<b>Run a speed test on the TV itself</b> (most devices have one in Settings, or use the Netflix app's "
        "network check). Your broadband may be fast at the router but slow at the TV.",
        "<b>Use Ethernet where you can.</b> A cable, or a USB Ethernet adapter for a stick, beats Wi-Fi every "
        "time for live sport.",
        "<b>Move the router out of cupboards</b> and away from the TV's metal back panel. Thick stone walls are "
        "common in Irish houses and block Wi-Fi badly.",
        "<b>Add a mesh system</b> if the TV is two or more rooms from the router. It works better than a single "
        "plug-in extender.",
        "<b>Restart everything</b> — router, then device — if streams suddenly get worse. It fixes most sudden "
        "slowdowns.",
    ])
    s += [
        callout("Useful extras",
                "A certified <b>High-Speed or Ultra High-Speed HDMI cable</b> for 4K HDR boxes, a <b>long Ethernet "
                "cable</b> or <b>mesh Wi-Fi</b> for distant rooms, and a <b>soundbar</b> — the single biggest "
                "upgrade over TV speakers. See our "
                + link(site("/best-prices/"), "Best Prices page on onairireland.ie") + " for current options."),
        Spacer(1, 8),
        PageBreak(),
    ]

    # Page 8
    guides = [
        ("Best streaming devices for Irish homes", "/devices/best-streaming-devices-ireland/"),
        ("Roku streaming devices in Ireland", "/devices/roku-streaming-devices-are-they-worth-buying-in-ireland/"),
        ("Fire TV Stick 4K Max: worth the upgrade?", "/reviews/fire-tv-stick-4k-max-worth-the-upgrade/"),
        ("Google TV Streamer review", "/reviews/google-tv-streamer-review-should-you-switch-from-fire-tv/"),
        ("How to set up RTÉ Player on a Fire TV Stick", "/installation-guides/how-to-set-up-rte-player-fire-tv/"),
        ("Why is my streaming app buffering?",
         "/troubleshooting/why-is-my-streaming-app-buffering-common-fixes/"),
        ("Every legal streaming service in Ireland, with prices",
         "/streaming-services/legal-streaming-services-ireland-2026/"),
    ]
    # Primary sources only: the provider's own pages
    sources = [
        ("Google Store Ireland", "Google TV Streamer (4K)",
         "https://store.google.com/ie/product/google_tv_streamer_specs"),
        ("Amazon Developer", "Fire TV device specifications comparison table",
         "https://developer.amazon.com/docs/device-specs/device-specifications-comparison-table.html"),
        ("Roku", "RTÉ Player now available on the Roku platform in Ireland",
         "https://www.roku.com/blog/rte-player-now-available-on-the-roku-platform-in-ireland"),
        ("Roku Channel Store", "Virgin Media Play",
         "https://channelstore.roku.com/details/bf33320850b76363ffa4f36a0df887ef/virgin-media-play"),
        ("GAA+ Support", "On what devices can I watch GAA+?", None),
        ("Netflix Help Centre", "Internet connection speed recommendations", None),
    ]

    def cite(who, title, url):
        t = f"“{title}”"
        return f"{who}, " + (link(url, t) if url else t)

    s += [
        h1("More free guides from On Air Ireland"),
        lead("Everything on our site covers licensed, legal services only. Good places to go next:"),
    ]
    for title, path in guides:
        s.append(bullet(f"<b>{title}</b> —<br/>" + link(site(path), "onairireland.ie" + path)))
    s += [
        Spacer(1, 10),
        Paragraph("Sources", S_H3),
        note("; ".join(cite(*x) for x in sources) + "."),
        Spacer(1, 10),
        note(f"This guide reflects information available in {UPDATED}. App availability, device models and prices "
             "change often — check the app store listing and the retailer's page before you buy. Some links on "
             + link(site("/"), "onairireland.ie") + " are affiliate links; as an Amazon Associate we earn from "
             "qualifying purchases. On Air Ireland is independent and not affiliated with any device maker or "
             "broadcaster."),
    ]
    return s


def main():
    flow = story()
    # Check every on-site link before anything is written
    known = site_paths()
    missing = sorted({p for p in LINKS_USED + ["/"] if p not in known})
    if missing:
        sys.exit("These on-site links don't match a page on the site (check _posts and _pages):\n- "
                 + "\n- ".join(missing))
    out = sys.argv[1] if len(sys.argv) > 1 else OUT
    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=62.69, bottomMargin=48,
                          title=DOC_TITLE + ": a free guide for Irish homes",
                          author="John Paul, On Air Ireland",
                          subject="Fire TV, Google TV, Roku, Apple TV or your smart TV: choosing a streaming "
                                  "device for licensed, legal services in Ireland",
                          creator="On Air Ireland (scripts/make_device_guide.py)")
    frame = Frame(MARGIN, 48, TEXT_W, H - 62.69 - 48, leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0, id="body")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=draw_cover),
        PageTemplate(id="page", frames=[frame], onPage=draw_page),
    ])
    doc.build(flow)
    print(f"Wrote {os.path.relpath(out, ROOT) if out.startswith(ROOT) else out} "
          f"({doc.page} pages, {len(set(LINKS_USED))} on-site links checked)")


if __name__ == "__main__":
    main()
