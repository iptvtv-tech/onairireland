#!/usr/bin/env python3
"""
Build the one-page GAA sheet for county boards and clubs:
assets/downloads/gaa-county-sheet.pdf

Every sentence about who shows what comes from the GAA entry in
_data/site_facts.yml, word for word, so the sheet can't say more than we've
checked. The four big numbers are read out of those sentences; if a fact is
reworded and a number can't be found, the script stops and says which, so
nobody prints a sheet with an old figure.

When the GAA entry changes (new season, new deal, quarterly fact check):
    python scripts/make_gaa_sheet.py
then review the PDF before committing it.

Needs: pip install reportlab pyyaml
"""
import datetime
import os
import re
import sys

import yaml
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = os.path.join(ROOT, "_data", "site_facts.yml")
OUT = os.path.join(ROOT, "assets", "downloads", "gaa-county-sheet.pdf")
# Every printed "onairireland.ie/gaa" (and the QR code) links here
GUIDE_URL = "https://onairireland.ie/gaa/"

NAVY = HexColor("#0f172a")
INK = HexColor("#1e293b")
MUTED = HexColor("#475569")
ACCENT = HexColor("#0369a1")
PANEL = HexColor("#f1f5f9")
LINE = HexColor("#cbd5e1")
WARM = HexColor("#c2410c")


def register_fonts():
    """DejaVu Sans if it's installed (matches the other PDFs), else Helvetica."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/dejavu",
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
    ]
    for folder in candidates:
        regular = os.path.join(folder, "DejaVuSans.ttf")
        bold = os.path.join(folder, "DejaVuSans-Bold.ttf")
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("Body", regular))
            pdfmetrics.registerFont(TTFont("Body-Bold", bold))
            return "Body", "Body-Bold"
    return "Helvetica", "Helvetica-Bold"


def gaa_entry():
    with open(FACTS, encoding="utf-8") as f:
        entries = yaml.safe_load(f)
    for e in entries:
        if e.get("topic") == "GAA":
            return e
    sys.exit("No GAA entry in _data/site_facts.yml")


def find(pattern, text, what):
    m = re.search(pattern, text)
    if not m:
        sys.exit(f"Couldn't find {what} in the GAA facts. Check the wording in "
                 f"_data/site_facts.yml and update this script's pattern.")
    return m.group(1)


def main():
    entry = gaa_entry()
    facts = entry["facts"]
    checked = entry["checked"]
    if isinstance(checked, str):
        checked = datetime.date.fromisoformat(checked)
    everything = " ".join(facts)

    overview = [f for f in facts if f.startswith("GAA games in Ireland")]
    # Who holds the TV rights, and for how long: shown with the overview
    rights = [f for f in facts if f.startswith("The GAA's current TV deals")]
    rte = [f for f in facts if f.startswith("In ") and "RTÉ showed" in f]
    tg4 = [f for f in facts if f.startswith("TG4")]
    gaaplus = [f for f in facts if f.startswith("GAA+") or f.startswith("In Ireland, GAA+")]
    later = [f for f in facts if "weren't announced" in f or "not announced" in f]
    used = set(overview + rights + tg4 + rte + gaaplus + later)
    unused = [f for f in facts if f not in used]
    if unused:
        sys.exit("These GAA facts don't fit a section on the sheet yet:\n- " + "\n- ".join(unused))

    season = find(r"In (\d{4}) RTÉ showed", everything, "the season year")
    stats = [
        (find(r"RTÉ showed (\d+) live championship games", everything, "RTÉ's game count"),
         f"live championship games free on RTÉ in {season}"),
        (find(r"TG4 showed over (\d+) live Allianz League", everything, "TG4's league count") + "+",
         f"live Allianz League games free on TG4 in {season}"),
        (find(r"GAA\+ had (\d+) exclusive games", everything, "GAA+'s exclusive games"),
         f"exclusive games on GAA+ in {season}"),
        ("€" + find(r"season pass was €(\d+)", everything, "the season pass price"),
         f"GAA+ {season} season pass (or €" + find(r"or €(\d+) a game", everything, "the per-game price") + " a game)"),
    ]

    body_font, bold_font = register_fonts()
    W, H = A4
    margin = 40
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle(f"Watching GAA in Ireland: who shows what ({season} season)")
    c.setAuthor("John Paul, On Air Ireland")
    c.setSubject("One-page guide for county boards, clubs and supporters")
    c.setCreator("On Air Ireland")

    # Header band
    c.setFillColor(NAVY)
    c.rect(0, H - 34, W, 34, stroke=0, fill=1)
    c.setFillColor(HexColor("#38bdf8"))
    c.setFont(bold_font, 9)
    c.drawString(margin, H - 22, "ON AIR IRELAND")
    c.setFillColor(HexColor("#cbd5e1"))
    c.setFont(body_font, 9)
    c.drawRightString(W - margin, H - 22, "Free to print and share")

    # Title
    y = H - 78
    c.setFillColor(INK)
    title = "Watching GAA in Ireland: who shows what"
    size = 24
    while pdfmetrics.stringWidth(title, bold_font, size) > W - 2 * margin and size > 14:
        size -= 0.5
    c.setFont(bold_font, size)
    c.drawString(margin, y, title)
    y -= 20
    c.setFillColor(MUTED)
    c.setFont(body_font, 10.5)
    c.drawString(margin, y, f"A one-page guide for clubs and supporters. {season} season, "
                            f"checked {checked.day} {checked:%B %Y}.")

    def para(text, size=10.5, color=INK, font=None, leading=None, width=None, bullet=False):
        style = ParagraphStyle("p", fontName=font or body_font, fontSize=size,
                               leading=leading or size * 1.4, textColor=color,
                               leftIndent=12 if bullet else 0, bulletIndent=0,
                               bulletFontName=font or body_font, bulletFontSize=size)
        p = Paragraph(text, style, bulletText="•" if bullet else None)
        _, h = p.wrap(width or (W - 2 * margin), 1000)
        return p, h

    # Overview line
    y -= 26
    for f in overview + rights:
        p, h = para(f, size=10.5)
        p.drawOn(c, margin, y - h + 11)
        y -= h + 4

    # Stat boxes
    y -= 8
    gap = 8
    box_w = (W - 2 * margin - 3 * gap) / 4
    box_h = 64
    for i, (num, label) in enumerate(stats):
        x = margin + i * (box_w + gap)
        c.setFillColor(PANEL)
        c.setStrokeColor(LINE)
        c.roundRect(x, y - box_h, box_w, box_h, 6, stroke=1, fill=1)
        c.setFillColor(ACCENT)
        c.setFont(bold_font, 20)
        c.drawCentredString(x + box_w / 2, y - 26, num)
        p, h = para(label, size=8, color=MUTED, width=box_w - 14)
        p.drawOn(c, x + 7, y - 34 - h)
    y -= box_h + 18

    def section(title, items, label_color=ACCENT):
        nonlocal y
        y -= 2
        c.setFillColor(label_color)
        c.setFont(bold_font, 13)
        c.drawString(margin, y, title)
        y -= 7
        c.setStrokeColor(LINE)
        c.line(margin, y, W - margin, y)
        y -= 16
        for name, lines in items:
            c.setFillColor(INK)
            c.setFont(bold_font, 11.5)
            c.drawString(margin, y, name)
            y -= 5
            for line in lines:
                p, h = para(line, size=10, width=W - 2 * margin - 4, bullet=True)
                p.drawOn(c, margin + 4, y - h)
                y -= h + 2
            y -= 8

    section("Free to watch", [("RTÉ", rte), ("TG4", tg4)])
    section("Paid", [("GAA+, the GAA's own streaming service", gaaplus)], label_color=WARM)
    section("Next season", [("Not announced yet", later +
             ["We update this sheet when they're announced. The latest is always at "
              f'<a href="{GUIDE_URL}">onairireland.ie/gaa/</a>'])],
            label_color=MUTED)

    # QR code panel: points to the always-current GAA guide
    qr_size = 84
    panel_h = qr_size + 20
    panel_y = 100
    c.setFillColor(PANEL)
    c.setStrokeColor(LINE)
    c.roundRect(margin, panel_y, W - 2 * margin, panel_h, 8, stroke=1, fill=1)
    widget = QrCodeWidget(GUIDE_URL)
    x0, y0, x1, y1 = widget.getBounds()
    d = Drawing(qr_size, qr_size, transform=[qr_size / (x1 - x0), 0, 0, qr_size / (y1 - y0), 0, 0])
    d.add(widget)
    qr_x, qr_y = W - margin - qr_size - 10, panel_y + 10
    renderPDF.draw(d, c, qr_x, qr_y)
    # The QR code is clickable too, for people reading the PDF on screen
    c.linkURL(GUIDE_URL, (qr_x, qr_y, qr_x + qr_size, qr_y + qr_size), relative=0, thickness=0)
    c.setFillColor(INK)
    c.setFont(bold_font, 14)
    c.drawString(margin + 16, panel_y + panel_h - 34, "The latest GAA TV guide")
    p, h = para(f'Scan the code or visit <a href="{GUIDE_URL}"><b>onairireland.ie/gaa</b></a> for who shows GAA this season, '
                "GAA+ prices once they're announced, and help with RTÉ, TG4 and GAA+.",
                size=10.5, color=MUTED, width=W - 2 * margin - qr_size - 50)
    p.drawOn(c, margin + 16, panel_y + panel_h - 44 - h)
    if y < panel_y + panel_h + 10:
        sys.exit(f"The facts no longer fit on one page (text ends at {y:.0f}pt, panel top {panel_y + panel_h}pt). "
                 "Shorten them or lay out the sheet again.")

    # Footer
    c.setStrokeColor(LINE)
    c.line(margin, 92, W - margin, 92)
    # Each printed source domain links to that site's home page (first source URL wins)
    domains = {}
    for s in entry.get("source", []):
        m = re.match(r"^(https?://(?:www\.)?([^/]+))/", s)
        if m:
            domains.setdefault(m.group(2), m.group(1) + "/")
    sources = ", ".join(f'<a href="{home}">{name}</a>' for name, home in domains.items())
    foot = (f'<a href="{GUIDE_URL}"><b>onairireland.ie/gaa</b></a> · Independent guides to legal streaming in Ireland, by John Paul, On Air Ireland. '
            f"Not connected to the GAA, RTÉ or TG4. Checked against {sources} on "
            f"{checked.day} {checked:%B %Y}. Fixtures and channels can change, so check the "
            f"broadcaster's own listings on the day.")
    p, h = para(foot, size=8.5, color=MUTED, font=body_font)
    p.drawOn(c, margin, 84 - h)

    c.showPage()
    c.save()
    print(f"Wrote {os.path.relpath(OUT, ROOT)} ({season} season, facts checked {checked})")


if __name__ == "__main__":
    main()
