#!/usr/bin/env python3
"""
Build the free 8-page GAA guide that newsletter subscribers get:
assets/downloads/gaa-legal-streaming-guide.pdf

The original generator was lost, so this script rebuilds the guide to match
the earlier PDF (A4, DejaVu Sans, navy header band, same figures and tables).
All the wording lives in this file: for a fact check, edit the text here and
re-run the script. Never edit the PDF by hand.

Every claim must agree with the "GAA" and "Streaming devices and Irish apps"
entries in _data/site_facts.yml. The 2026 figures and prices below were
checked for the September 2026 edition; refresh them all together for 2027.

Every printed onairireland.ie address is a clickable link to the full
https://onairireland.ie/... URL, and every other printed web address links to
its source. Before writing the PDF the script checks each on-site link against
the site's real addresses (posts, using the permalink /:categories/:title/,
and _pages permalinks) and stops if one doesn't exist.

    python scripts/make_gaa_guide.py

then review the PDF before committing it.

Needs: pip install reportlab pyyaml
"""
import math
import os
import re
import sys

import yaml
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "downloads", "gaa-legal-streaming-guide.pdf")
SITE = "https://onairireland.ie"

# Change these at each fact check
UPDATED = "September 2026"
EDITION = "2026 EDITION"
DOC_TITLE = "Watching GAA Legally in Ireland"

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


def white_line(x1, y1, x2, y2, sw):
    return Line(x1, y1, x2, y2, strokeColor=white, strokeWidth=sw)


def cover_illustration():
    """A TV showing a GAA pitch, with a stick in its side, a sofa and a remote."""
    d = Drawing(430, 340)
    d.add(Circle(215, 170, 150, fillColor=HexColor("#1e3a5f"), strokeColor=None))
    d.add(rrect(91, 106, 248, 148, 4, "#0b1220"))            # TV
    d.add(rect(95, 110, 240, 140, "#15803d"))                # pitch
    d.add(rect(212, 92, 6, 14, "#334155"))                   # stand
    d.add(rrect(185, 90, 60, 4, 2, "#334155"))
    for x in range(95, 335, 40):                             # mown stripes
        d.add(rect(x, 110, 20, 140, "#16a34a"))
    d.add(white_line(215, 110, 215, 250, 1.2))               # halfway line
    d.add(Circle(215, 180, 18, fillColor=None, strokeColor=white, strokeWidth=1.2))
    for x in (103, 307):                                     # goalposts
        d.add(white_line(x, 158, x, 220, 2))
        d.add(white_line(x + 20, 158, x + 20, 220, 2))
        d.add(white_line(x, 178, x + 20, 178, 2))
    d.add(dot(243.8, 196.8, 5, "#ffffff", "#d1d5db", 1))     # ball
    d.add(rrect(103, 230, 38, 13, 3, "#dc2626"))
    d.add(text(122, 233.5, "LIVE", 8, "#ffffff", BOLD, "middle"))
    d.add(rrect(225, 230, 102, 13, 3, "#0f172a"))
    d.add(text(276, 233.5, "1-14   v   0-16", 7.5, "#ffffff", BOLD, "middle"))
    d.add(rrect(341, 140, 23.8, 8.4, 2.1, "#111827"))        # stick in the TV's side
    d.add(rect(364.8, 142.1, 5.6, 4.2, "#9ca3af"))
    d.add(rrect(120, 12, 190, 26, 6, "#475569"))             # sofa
    d.add(rrect(128, 34, 174, 26, 8, "#64748b"))
    d.add(rrect(114, 12, 14, 36, 6, "#475569"))
    d.add(rrect(302, 12, 14, 36, 6, "#475569"))
    d.add(rrect(340, 18, 11.2, 40, 4.8, "#1f2937"))          # remote
    d.add(dot(345.6, 48.4, 3.6, "#6b7280"))
    for y in (37.2, 31.6, 26):
        d.add(dot(345.6, y, 1.44, "#9ca3af"))
    return d


def stat_tiles(stats):
    """Row of big numbers on a pale blue panel (page 2)."""
    s_num = style("statn", fontName=BOLD, fontSize=22, leading=26, textColor=ACCENT, alignment=TA_CENTER)
    s_lab = style("statl", fontSize=8.5, leading=11, textColor=SLATE, alignment=TA_CENTER)
    row = [[Paragraph(n, s_num), Paragraph(lab, s_lab)] for n, lab in stats]
    t = Table([row], colWidths=[TEXT_W / len(stats)] * len(stats))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_PANEL),
        ("BOX", (0, 0), (-1, -1), 1, white),
        ("INNERGRID", (0, 0), (-1, -1), 1, white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
SEASON = [  # (stage, who shows it, start and end in months from 1 January, colour)
    ("Allianz Leagues", "TG4 · BBC (Ulster)", 0.75, 3.15, "#7c3aed"),
    ("Provincial championships", "RTÉ · GAA+ · BBC (Ulster)", 3.35, 6.0, "#0284c7"),
    ("All-Ireland series", "RTÉ · GAA+", 4.8, 6.9, "#fb923c"),
    ("Finals", "RTÉ", 6.55, 7.35, "#dc2626"),
]
SEASON_NOTE = "2026 dates for reference. Hurling final 19 Jul · Football final 26 Jul · Camogie final 9 Aug."


def season_chart():
    """Figure 1: the inter-county season as a month-by-month timeline."""
    d = Drawing(TEXT_W, 150)
    x0 = 118
    month = (TEXT_W - 8 - x0) / len(MONTHS)
    for i, m in enumerate(MONTHS):
        d.add(text(x0 + (i + 0.5) * month, 136, m, 8, "#475569", BOLD, "middle"))
        d.add(Line(x0 + i * month, 20, x0 + i * month, 130, strokeColor=RULE, strokeWidth=0.6))
    for i, (stage, who, start, end, colour) in enumerate(SEASON):
        y = 108 - i * 24
        d.add(text(4, y + 5, stage, 7.8, "#0f172a", BOLD))
        d.add(rrect(x0 + start * month, y, (end - start) * month, 16, 4, colour))
        d.add(text(x0 + start * month + 5, y + 5, who, 7.2, "#ffffff"))
    d.add(text(4, 6, SEASON_NOTE, 7.2, "#64748b", ITALIC))
    return d


LIVE_GAMES = [  # (broadcaster, games, label, what they are, colour). 2026 figures
    ("TG4", 45, "45+", "Allianz League games live (Jan–Apr)", "#7c3aed"),
    ("GAA+", 40, "40", "Exclusive championship games (paid)", "#fb923c"),
    ("RTÉ", 35, "35", "Championship games live, free (Apr–Aug)", "#0284c7"),
]


def games_chart():
    """Figure 2: horizontal bars, live games by broadcaster."""
    d = Drawing(TEXT_W, 130)
    scale = 218.9055 / max(v for _, v, _, _, _ in LIVE_GAMES)
    for i, (who, games, label, what, colour) in enumerate(LIVE_GAMES):
        y = 92 - i * 36
        w = games * scale
        d.add(text(52, y + 7, who, 10, "#0f172a", BOLD, "end"))
        d.add(rrect(60, y, w, 22, 4, colour))
        d.add(text(60 + w - 6, y + 7, label, 10, "#ffffff", BOLD, "end"))
        d.add(text(60 + w + 8, y + 7, what, 8, "#475569"))
    return d


WAYS = [  # Figure 3: (title, two lines of detail)
    ("Smart TV app", "RTÉ Player, TG4 Player, GAA+", "built into the TV"),
    ("Streaming stick or box", "Fire TV, Google TV, Roku,", "Apple TV in the HDMI port"),
    ("Cast from your phone", "Chromecast / AirPlay", "from the mobile apps"),
    ("Laptop + HDMI cable", "Browser on a laptop,", "plugged into the TV"),
]


def ways_diagram():
    """Figure 3: four boxes with arrows into a TV."""
    d = Drawing(TEXT_W, 175)
    tx = TEXT_W - 16 - 138
    d.add(rrect(tx, 51, 138, 86, 4, "#0b1220"))
    d.add(rect(tx + 4, 55, 130, 78, "#15803d"))
    d.add(rect(tx + 66, 37, 6, 14, "#334155"))
    d.add(rrect(tx + 39, 35, 60, 4, 2, "#334155"))
    d.add(Line(tx + 69, 55, tx + 69, 133, strokeColor=white, strokeWidth=1))
    d.add(text(tx + 69, 12, "Your TV", 9, "#0f172a", BOLD, "middle"))
    for i, (title, *lines) in enumerate(WAYS):
        y = 135 - i * 40
        d.add(rrect(0, y, 200, 34, 6, "#ffffff", "#0284c7", 1.2))
        for j, s in enumerate([title] + lines):
            d.add(text(100, y + 25.7 - j * 10.2, s, 7.6, "#0f172a", BOLD if j == 0 else BODY, "middle"))
        d.add(arrow(204, y + 17, tx - 6, 106 - i * 8))
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
    c.drawString(MARGIN, 170.79, "Watching GAA")
    c.drawString(MARGIN, 135.35, "Legally in Ireland")
    c.setFillColor(HexColor("#cbd5e1"))
    c.setFont(BODY, 12)
    c.drawString(MARGIN, 105.59, "Who shows what, what it costs, and how to get it on your TV")
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

# Must agree with "Streaming devices and Irish apps" in _data/site_facts.yml
VEGA_MODELS = ("Fire TV Stick 4K (3rd gen, 2026), Fire TV Stick HD (2026) and "
               "Fire TV Stick 4K Select (2025)")


def story():
    s = [NextPageTemplate("page"), PageBreak()]

    # Page 2
    s += [
        h1("The short version"),
        lead("Most GAA on Irish television is free. RTÉ and TG4 show well over 100 live games a season between "
             "them. A block of championship matches is only on GAA+, the GAA's own paid streaming service. Every "
             "option in this guide is official and licensed."),
        Spacer(1, 16.5),
        stat_tiles([
            ("35", "live championship games<br/>free on RTÉ in 2026"),
            ("45+", "live Allianz League games<br/>free on TG4 in 2026"),
            ("40", "exclusive championship<br/>games on GAA+"),
            ("€95", "GAA+ 2026 Season Pass<br/>(Ireland)"),
        ]),
        Spacer(1, 10),
        h2("Where each game is shown"),
        body("Coverage is decided competition by competition and round by round, not by county. Use this as your "
             "map, then check the weekly TV listings (see the match-day checklist on page 7) to confirm a specific "
             "match."),
        table([
            ["Competition", "Free-to-air", "Paid / streaming", "Notes"],
            ["Allianz Football &amp; Hurling Leagues", "TG4 (45+ live games in 2026), TG4 Player", "—",
             "BBC Northern Ireland streams up to 10 league games involving Ulster teams"],
            ["Provincial championships", "RTÉ (RTÉ2 / RTÉ Player)",
             "GAA+ (19 exclusive games in 2026, including Munster and Leinster hurling)",
             "Ulster football also on BBC Northern Ireland"],
            ["All-Ireland football series", "RTÉ", "GAA+ (14 exclusive games in 2026)",
             "Quarter-finals onwards mostly on RTÉ"],
            ["All-Ireland hurling series", "RTÉ", "—", ""],
            ["Tailteann Cup", "RTÉ (semi-finals and final)", "GAA+ (7 games in 2026)", ""],
            ["All-Ireland semi-finals and finals", "RTÉ", "—", "BBC simulcasts the semi-finals and finals"],
            ["Minor and U20 championships", "TG4", "—", "Plus third-level and schools competitions"],
            ["Camogie", "RTÉ (at least 9 live games, incl. the final)", "—", "TG4 Monday-night highlights"],
            ["Ladies football", "TG4", "—", "Including the All-Ireland finals"],
        ], [0.25, 0.26, 0.24, 0.25]),
        Spacer(1, 6),
        note("Sources: GAA broadcast statement 2023–2027; RTÉ and TG4 2026 coverage announcements; GAA+ 2026 "
             "Season Pass. The current broadcast deal runs to the end of the 2027 season."),
        PageBreak(),
    ]

    # Page 3
    s += [
        h1("The GAA season at a glance"),
        body("The inter-county year runs in two halves: the Allianz Leagues from late January to early April, then "
             "the championships from April to the finals in July. Here's where to look at each stage."),
        season_chart(),
        caption("Figure 1. Where to watch through the inter-county season (2026 dates)."),
        h2("How many games are live"),
        games_chart(),
        caption("Figure 2. Live games by broadcaster in 2026. The TG4 figure covers the leagues; RTÉ and GAA+ cover "
                "the championships."),
        callout("Irish-language and radio coverage",
                "From May to August, RTÉ offers Irish-language commentary on All-Ireland championship games. On "
                "radio, RTÉ Radio 1 carries live commentary, and <b>Raidió na Gaeltachta</b> covers games in Irish. "
                "BBC Radio Ulster and around two dozen local radio stations also have live commentary rights — "
                "handy in the car or when your broadband is struggling."),
        PageBreak(),
    ]

    # Page 4
    s += [
        h1("The free options: RTÉ and TG4"),
        h2("RTÉ"),
        body("RTÉ is the home of the championships. In 2026 it showed <b>35 live championship games</b> between "
             "12 April and 9 August, across football, hurling and camogie, including every provincial final, the "
             "All-Ireland semi-finals and all the All-Ireland finals."),
        bullet("<b>The Sunday Game Live</b> — live games on Sundays on RTÉ2 and RTÉ Player."),
        bullet("<b>The Saturday Game</b> and <b>The Sunday Game</b> — highlights and analysis on Saturday and "
               "Sunday nights at 9.30pm."),
        bullet("<b>RTÉ Player</b> — every live game streamed free, plus on-demand replays. You need a free RTÉ "
               "account."),
        bullet("Highlights also go up on " + link("https://www.rte.ie/", "RTÉ.ie") +
               ", the RTÉ News app and YouTube."),
        h2("TG4"),
        body("TG4 owns the spring. In 2026 it broadcast <b>more than 45 live Allianz League games</b> across every "
             "football division and hurling Divisions 1A, 1B and 2, plus the league finals and multi-screen "
             "“Super Saturday” and “Super Sunday” final rounds."),
        bullet("Minor and U20 championships, third-level and schools competitions, and the <b>Ladies Football</b> "
               "championships."),
        bullet("<b>GAA 2026</b> highlights on Monday nights at 8pm during the leagues."),
        bullet("<b>TG4 Player</b> — live and catch-up, free. Some games stream on TG4 Player with a deferred TV "
               "broadcast."),
        callout("Do I need a TV licence?",
                "If you watch on a TV set that can receive broadcast channels, yes — the licence is €160 a year. If "
                "you only stream on devices that can't receive a TV signal (a laptop, phone or tablet), Citizens "
                "Information says you don't need one. See our "
                + link(site("/streaming-services/tv-licence-streaming-ireland/"),
                       "TV licence guide on onairireland.ie") + " for the details.",
                panel=AMBER_PANEL, edge=AMBER),
        PageBreak(),
    ]

    # Page 5. Fire TV caveat must agree with "Streaming devices and Irish apps" in _data/site_facts.yml
    s += [
        h1("GAA+ explained"),
        lead("GAA+ is the GAA's own streaming service (it replaced GAAGO in 2025). It carries championship games "
             "that aren't on free-to-air TV, streams live in Ireland and in more than 180 territories worldwide, "
             "and keeps games on demand afterwards."),
        table([
            ["GAA+ option (2026)", "Price", "Best for"],
            ["Season Pass", "€95", "Following your county through the whole championship"],
            ["Season Pass for GAA members", "10% off, via Foireann", "Registered club members"],
            ["Single match", "€15", "One or two big games"],
            ["3-for-2 bundle", "€30", "A short run of games"],
            ["Club Pass", "€150", "Showing games in a clubhouse"],
            ["Commercial premises pass", "€300", "Pubs, hotels and other businesses"],
        ], [0.34, 0.26, 0.40]),
        Spacer(1, 6),
        note("The 2026 Season Pass covered 40 exclusive games: 19 provincial championship games, 7 Tailteann Cup "
             "games and 14 games from the All-Ireland football series. Care homes get free access through a "
             "partnership with the HSE and Nursing Homes Ireland."),
        h2("Which devices GAA+ works on"),
        table([
            ["Type", "Supported"],
            ["TV apps", "Amazon Fire TV, Google TV, Apple TV, Roku, LG TVs, Samsung TVs (2021 models and newer)"
             "<br/><b>Fire TV:</b> Amazon's newest sticks, the " + VEGA_MODELS + ", run Vega OS, which has fewer "
             "apps. Check GAA+ is listed for your exact model before you buy. Fire OS models such as the Fire TV "
             "Stick 4K Max are the safe pick."],
            ["Phones and tablets", "iOS and Android apps (current OS version or the one before)"],
            ["Casting", "Chromecast and Apple AirPlay from the mobile apps"],
            ["Computers", "Any modern browser at " + link("https://gaaplus.ie/", "gaaplus.ie")
             + "; or connect a laptop to the TV with an HDMI cable"],
            ["Not supported", "Web browsers built into smart TVs and games consoles"],
        ], [0.25, 0.75]),
        Spacer(1, 10),
        callout("Tip: buy the pass before throw-in",
                "Sign up and log in on your TV app the day before a big game. Payment problems and forgotten "
                "passwords at 3.25pm on a Sunday are the most common reason people miss the start."),
        PageBreak(),
    ]

    # Page 6
    s += [
        h1("Getting GAA on your TV"),
        body("There are four ways to get RTÉ Player, TG4 Player and GAA+ onto the big screen. Most homes use the "
             "first two."),
        ways_diagram(),
        caption("Figure 3. Four ways to get GAA streams onto your television."),
        Paragraph("Setting up on a streaming stick (Fire TV, Google TV or Roku)", S_H3),
    ]
    s += numbered([
        "Plug the stick into a free HDMI port and its power adapter into the wall (not the TV's USB port, which "
        "can underpower it).",
        "Switch the TV to that HDMI input and follow the on-screen setup to join your Wi-Fi.",
        "Open the app store (Fire TV: <b>Find → Search</b>; Google TV: <b>Apps</b>; Roku: <b>Streaming Store</b>) "
        "and install <b>RTÉ Player</b>, <b>TG4 Player</b> and <b>GAA+</b>.",
        "Open each app and sign in. RTÉ Player and GAA+ usually show a short code — enter it on your phone to log "
        "in quickly.",
        "Play something before match day to make sure everything works.",
    ])
    s += [
        Spacer(1, 4),
        callout("Buying a Fire TV stick?",
                "Amazon's newest sticks, the " + VEGA_MODELS + ", run Vega OS, which has fewer apps. Before you "
                "buy, check that GAA+, RTÉ Player and TG4 Player are listed for your exact model. Fire OS models "
                "such as the Fire TV Stick 4K Max are the safe pick.",
                panel=AMBER_PANEL, edge=AMBER),
        Paragraph("Casting from your phone", S_H3),
    ]
    s += numbered([
        "Connect your phone and your TV (or Chromecast / Apple TV) to the same Wi-Fi network.",
        "Start the game in the GAA+ or RTÉ Player app on your phone.",
        "Tap the cast (Chromecast) or AirPlay icon and choose your TV.",
    ])
    s += [
        note("Menu names can change slightly between app and software updates."),
        PageBreak(),
    ]

    # Page 7
    s += [
        h1("Match-day checklist"),
        table([
            ["Check", "Why it matters"],
            ["Confirm the channel on Monday or Tuesday",
             "RTÉ and GAA+ announce their picks round by round, and big games get moved"],
            ["Test your stream the day before",
             "Catches expired passes, logged-out apps and app updates that need installing"],
            ["Aim for at least 5 Mbps for HD",
             "Netflix, for example, recommends 5 Mbps for HD and 15 Mbps for 4K; live sport needs a steady "
             "connection"],
            ["Use a wired connection if you can",
             "An Ethernet cable to your stick, box or TV removes most Wi-Fi buffering"],
            ["Pause big downloads", "Game consoles and phone backups can swallow bandwidth at throw-in"],
            ["Restart the stick and router if it buffers", "Unplug for 30 seconds — it fixes most mid-game freezes"],
            ["Keep the radio as a backup",
             "RTÉ Radio 1, Raidió na Gaeltachta and local radio all carry live commentary"],
        ], [0.38, 0.62]),
        h2("Watching from abroad"),
        body("<b>GAA+</b> streams live in more than 180 territories, so it's the simplest option for Irish people "
             "abroad. In Northern Ireland and Britain, BBC Northern Ireland covers Ulster championship games and "
             "simulcasts the All-Ireland semi-finals and finals, and BBC iPlayer carries them in the UK. RTÉ "
             "Player's live sport is usually limited to viewers in Ireland because of rights agreements."),
        callout("Every option in this guide is official",
                "RTÉ, TG4 and GAA+ show inter-county GAA in Ireland, and BBC Northern Ireland covers games in "
                "Northern Ireland and Britain, so every option in this guide is licensed and official. The money "
                "from GAA+ passes and TV rights goes back into the games.",
                panel=AMBER_PANEL, edge=AMBER),
        PageBreak(),
    ]

    # Page 8
    guides = [
        ("Where to watch GAA legally in Ireland", "/streaming-services/where-to-watch-gaa-legally-ireland/"),
        ("GAA+ not working? Try these fixes", "/troubleshooting/gaa-not-working-try-these-fixes/"),
        ("How to set up GAA+ on an Apple TV", "/installation-guides/how-to-set-up-gaa-on-an-apple-tv/"),
        ("Every legal streaming service in Ireland, with prices",
         "/streaming-services/legal-streaming-services-ireland-2026/"),
        ("Why is my streaming app buffering?",
         "/troubleshooting/why-is-my-streaming-app-buffering-common-fixes/"),
    ]
    # Primary sources only: (who, title, printed address and its link, extra detail)
    sources = [
        ("GAA", "GAA Broadcast Statement 2023–2027",
         ("gaa.ie", "https://www.gaa.ie/news/gaa-broadcast-statement-2023-2027"), ""),
        ("GAA", "GAA+ launches 2026 Season Pass",
         ("gaa.ie", "https://www.gaa.ie/article/gaa-launches-2026-season-pass"), ", 24 March 2026"),
        ("RTÉ", "The GAA Championships on RTÉ",
         ("about.rte.ie", "https://about.rte.ie/2026/04/07/the-gaa-championships-on-rte"), ", 7 April 2026"),
        ("TG4", "TG4 Unveils Extensive Allianz Leagues Coverage",
         ("tg4.ie", "https://www.tg4.ie/en/information/press/press-releases/2026-2/"
                    "tg4-unveils-extensive-allianz-leagues-coverage/"), ", 2026"),
        ("GAA+ Support", "On what devices can I watch GAA+?", ("help.gaaplus.ie", "https://help.gaaplus.ie/"), ""),
        ("Citizens Information", "TV licences", None, ""),
        ("Netflix Help Centre", "Internet connection speed recommendations", None, ""),
    ]

    def cite(who, title, where, extra):
        t = f"{who}, “{title}”"
        if where:
            t += " (" + link(where[1], where[0]) + extra + ")"
        return t

    s += [
        h1("More free guides from On Air Ireland"),
        lead("Everything on our site covers licensed, legal services only. Good places to start:"),
    ]
    for title, path in guides:
        s.append(bullet(f"<b>{title}</b> —<br/>" + link(site(path), "onairireland.ie" + path)))
    s += [
        Spacer(1, 10),
        Paragraph("Sources", S_H3),
        note("; ".join(cite(*x) for x in sources) + "."),
        Spacer(1, 10),
        note(f"This guide reflects information available in {UPDATED}. Broadcast picks, GAA+ prices and app "
             "features change between seasons — always confirm current details with RTÉ, TG4 and GAA+. On Air "
             "Ireland is independent and not affiliated with the GAA, RTÉ, TG4 or the BBC."),
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
                          title=DOC_TITLE + ": a free guide",
                          author="John Paul, On Air Ireland",
                          subject="Who shows GAA in Ireland, what GAA+ costs and how to get RTÉ Player, TG4 Player "
                                  "and GAA+ on your TV: licensed, legal services only",
                          creator="On Air Ireland (scripts/make_gaa_guide.py)")
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
