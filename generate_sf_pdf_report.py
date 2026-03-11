#!/usr/bin/env python3
"""
Salesforce Org Audit — PDF Report Generator
Clean, professional PDF with per-domain chart pages.
Usage: python3 generate_sf_pdf_report.py [input.json] [output.pdf]
Demo:  python3 generate_sf_pdf_report.py
"""

import sys, json, math
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing, Circle, Rect, String, Line, Group
    from reportlab.graphics.charts.barcharts import HorizontalBarChart
except ImportError:
    print("ERROR: reportlab is required. Install with: pip3 install reportlab")
    sys.exit(1)


# ─── Page geometry ─────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4                   # 210mm × 297mm
L_MARGIN  = 16 * mm
R_MARGIN  = 12 * mm
T_MARGIN  = 18 * mm
B_MARGIN  = 14 * mm
SIDEBAR_W =  5 * mm                   # left sidebar strip (drawn on canvas)
CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN  # 182mm — all tables/charts must fit

# ─── Colors ────────────────────────────────────────────────────────────────────
C_WHITE      = HexColor("#FFFFFF")
C_PAGE_BG    = HexColor("#F7F9FB")
C_PANEL      = HexColor("#EBF4F8")

C_TEAL       = HexColor("#1E7FA4")
C_TEAL_DARK  = HexColor("#155A76")
C_TEAL_LIGHT = HexColor("#A8D4E6")
C_GOLD       = HexColor("#F5A623")
C_GOLD_DARK  = HexColor("#C8861A")

C_INK        = HexColor("#1A2533")
C_SLATE      = HexColor("#3D5166")
C_MID        = HexColor("#6B8599")
C_FAINT      = HexColor("#A0B4C0")
C_BORDER     = HexColor("#C8DCE6")
C_BORDER_LT  = HexColor("#E2EEF4")

C_A_BG = HexColor("#D6F0DC"); C_A_FG = HexColor("#1A6B35")
C_B_BG = HexColor("#D0E8F5"); C_B_FG = HexColor("#1A5C80")
C_C_BG = HexColor("#FEF3C7"); C_C_FG = HexColor("#7A5000")
C_D_BG = HexColor("#FDE8E8"); C_D_FG = HexColor("#8B2020")

C_CRIT_BG = HexColor("#FDE8E8"); C_CRIT_FG = HexColor("#8B2020")
C_HIGH_BG = HexColor("#FEF0E0"); C_HIGH_FG = HexColor("#8B4000")
C_MED_BG  = HexColor("#FEF3C7"); C_MED_FG  = HexColor("#7A5000")
C_LOW_BG  = HexColor("#D6F0DC"); C_LOW_FG  = HexColor("#1A6B35")

# One accent color per domain (9 total)
DOMAIN_COLORS = [
    HexColor("#1E7FA4"),  # Security
    HexColor("#2E9E8A"),  # Data Quality
    HexColor("#E09B20"),  # Automation
    HexColor("#5B6EAE"),  # Architecture
    HexColor("#3EB0A8"),  # Test Coverage
    HexColor("#C8861A"),  # Naming
    HexColor("#7B5EA7"),  # Orphaned
    HexColor("#2A8FA0"),  # Descriptions
    HexColor("#D4622E"),  # Field Sprawl
]


# ─── Helpers ───────────────────────────────────────────────────────────────────
def score_grade(s):
    if s >= 90: return "A+", C_A_BG, C_A_FG
    if s >= 80: return "A",  C_A_BG, C_A_FG
    if s >= 70: return "B",  C_B_BG, C_B_FG
    if s >= 60: return "C",  C_C_BG, C_C_FG
    if s >= 50: return "D",  C_D_BG, C_D_FG
    return "F", C_D_BG, C_D_FG

def grade_label(g):
    return {"A+":"Excellent","A":"Strong","B":"Good","C":"Fair","D":"Poor","F":"Critical"}.get(g,"")

def sev_colors(sev):
    s = sev.lower()
    if "crit" in s: return C_CRIT_BG, C_CRIT_FG
    if "high" in s: return C_HIGH_BG, C_HIGH_FG
    if "med"  in s: return C_MED_BG,  C_MED_FG
    return C_LOW_BG, C_LOW_FG


# ─── Score badge (replaces circular gauge — clean & reliable) ─────────────────
def score_badge(score, accent, w_mm=44, h_mm=52):
    """Rectangle badge: large score number + grade + label."""
    W, H = w_mm * mm, h_mm * mm
    g, bg, fg = score_grade(score)
    d = Drawing(W, H)

    # Background rounded rect (approximated as rect)
    d.add(Rect(0, 0, W, H, rx=6, ry=6,
               fillColor=bg, strokeColor=accent, strokeWidth=1.5))

    # Score number
    d.add(String(W / 2, H * 0.52, str(score),
                 fontSize=28, fontName="Helvetica-Bold",
                 fillColor=accent, textAnchor="middle"))
    # /100
    d.add(String(W / 2, H * 0.36, "/100",
                 fontSize=8.5, fontName="Helvetica",
                 fillColor=C_MID, textAnchor="middle"))
    # Grade
    d.add(String(W / 2, H * 0.22, g,
                 fontSize=14, fontName="Helvetica-Bold",
                 fillColor=fg, textAnchor="middle"))
    # Label
    d.add(String(W / 2, H * 0.08, grade_label(g),
                 fontSize=7, fontName="Helvetica",
                 fillColor=C_MID, textAnchor="middle"))
    return d


# ─── Horizontal bar chart (dimension scores 0–10) ─────────────────────────────
def dim_chart(dimensions, bar_color, avail_w_mm):
    """
    Horizontal bar chart fitting within avail_w_mm.
    avail_w_mm = CONTENT_W/mm minus any badge/padding beside it.
    """
    if not dimensions:
        return Drawing(avail_w_mm * mm, 10 * mm)

    n = len(dimensions)
    row_h   = 13              # mm per bar row
    chart_h = n * row_h + 10  # mm total height
    label_w = 46 * mm         # left labels column
    chart_w = avail_w_mm * mm - label_w - 4 * mm  # remaining for bars

    total_w = avail_w_mm * mm
    total_h = chart_h * mm

    d = Drawing(total_w, total_h)
    chart = HorizontalBarChart()
    chart.x           = label_w
    chart.y           = 5 * mm
    chart.width       = chart_w
    chart.height      = total_h - 10 * mm
    chart.data        = [[v if isinstance(v,(int,float)) else 0
                          for v in dimensions.values()]]
    chart.reversePlotOrder = 1

    chart.bars[0].fillColor   = bar_color
    chart.bars[0].strokeColor = None

    chart.valueAxis.valueMin       = 0
    chart.valueAxis.valueMax       = 10
    chart.valueAxis.valueStep      = 2
    chart.valueAxis.labels.fontName  = "Helvetica"
    chart.valueAxis.labels.fontSize  = 7
    chart.valueAxis.labels.fillColor = C_MID
    chart.valueAxis.gridStrokeColor  = C_BORDER_LT
    chart.valueAxis.gridStrokeWidth  = 0.4
    chart.valueAxis.strokeColor      = C_BORDER_LT

    labels = list(dimensions.keys())
    # Truncate long labels so they fit in label_w
    chart.categoryAxis.categoryNames    = labels
    chart.categoryAxis.labels.fontName  = "Helvetica"
    chart.categoryAxis.labels.fontSize  = 8
    chart.categoryAxis.labels.fillColor = C_SLATE
    chart.categoryAxis.labels.dx        = -4
    chart.categoryAxis.labels.textAnchor= "end"
    chart.categoryAxis.gridStrokeColor  = None
    chart.categoryAxis.strokeColor      = None

    chart.barLabelFormat          = "%g"
    chart.barLabels.fontName      = "Helvetica-Bold"
    chart.barLabels.fontSize      = 7.5
    chart.barLabels.fillColor     = C_INK
    chart.barLabels.nudge         = 5

    d.add(chart)
    return d


# ─── All-domain overview bar chart ────────────────────────────────────────────
def overview_chart(domains, avail_w_mm):
    n      = len(domains)
    row_h  = 14
    h_mm   = n * row_h + 12
    lw     = 48 * mm
    cw     = avail_w_mm * mm - lw - 4 * mm
    total_w = avail_w_mm * mm
    total_h = h_mm * mm

    d = Drawing(total_w, total_h)
    chart = HorizontalBarChart()
    chart.x      = lw
    chart.y      = 5 * mm
    chart.width  = cw
    chart.height = total_h - 10 * mm
    chart.data   = [[int(v.get("score",0)) for v in domains.values()]]
    chart.reversePlotOrder = 1

    for i in range(len(domains)):
        idx = (len(domains) - 1 - i) % len(DOMAIN_COLORS)
        chart.bars[(0, i)].fillColor   = DOMAIN_COLORS[idx]
        chart.bars[(0, i)].strokeColor = None

    chart.valueAxis.valueMin       = 0
    chart.valueAxis.valueMax       = 100
    chart.valueAxis.valueStep      = 20
    chart.valueAxis.labels.fontName  = "Helvetica"
    chart.valueAxis.labels.fontSize  = 7
    chart.valueAxis.labels.fillColor = C_MID
    chart.valueAxis.gridStrokeColor  = C_BORDER_LT
    chart.valueAxis.gridStrokeWidth  = 0.4
    chart.valueAxis.strokeColor      = C_BORDER_LT

    chart.categoryAxis.categoryNames    = list(domains.keys())
    chart.categoryAxis.labels.fontName  = "Helvetica"
    chart.categoryAxis.labels.fontSize  = 8
    chart.categoryAxis.labels.fillColor = C_SLATE
    chart.categoryAxis.labels.dx        = -4
    chart.categoryAxis.labels.textAnchor= "end"
    chart.categoryAxis.gridStrokeColor  = None
    chart.categoryAxis.strokeColor      = None

    chart.barLabelFormat     = "%d"
    chart.barLabels.fontName = "Helvetica-Bold"
    chart.barLabels.fontSize = 7.5
    chart.barLabels.fillColor= C_INK
    chart.barLabels.nudge    = 6

    d.add(chart)
    return d


# ─── Styles ────────────────────────────────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

def build_styles():
    return {
        "cover_title": S("cover_title", fontName="Helvetica-Bold",
                         fontSize=26, textColor=C_TEAL_DARK,
                         leading=32, spaceAfter=3),
        "cover_org":   S("cover_org",   fontName="Helvetica-Bold",
                         fontSize=15, textColor=C_TEAL, spaceAfter=2),
        "cover_sub":   S("cover_sub",   fontName="Helvetica",
                         fontSize=10, textColor=C_SLATE, spaceAfter=2),
        "h1":          S("h1",          fontName="Helvetica-Bold",
                         fontSize=13, textColor=C_TEAL_DARK,
                         spaceBefore=8, spaceAfter=4, leading=17),
        "h2":          S("h2",          fontName="Helvetica-Bold",
                         fontSize=10, textColor=C_TEAL_DARK,
                         spaceBefore=5, spaceAfter=3),
        "body":        S("body",        fontName="Helvetica", fontSize=9,
                         textColor=C_SLATE, leading=14, spaceAfter=3),
        "small":       S("small",       fontName="Helvetica", fontSize=8,
                         textColor=C_MID, leading=12),
        "exec":        S("exec",        fontName="Helvetica", fontSize=9.5,
                         textColor=C_SLATE, leading=15,
                         leftIndent=10, rightIndent=10, spaceAfter=4),
        "th":          S("th",          fontName="Helvetica-Bold",
                         fontSize=8, textColor=C_TEAL_DARK),
        "td":          S("td",          fontName="Helvetica",
                         fontSize=8, textColor=C_SLATE, leading=11),
        "action":      S("action",      fontName="Helvetica",
                         fontSize=8.5, textColor=C_SLATE,
                         leading=13, leftIndent=4),
        "footer":      S("footer",      fontName="Helvetica",
                         fontSize=7, textColor=C_FAINT, alignment=TA_CENTER),
        "domain_hdr":  S("domain_hdr",  fontName="Helvetica-Bold",
                         fontSize=12, textColor=C_WHITE, leading=15),
        "domain_sub":  S("domain_sub",  fontName="Helvetica",
                         fontSize=8.5, textColor=C_WHITE,
                         alignment=TA_RIGHT),
    }


# ─── Canvas decorations ────────────────────────────────────────────────────────
def decorate_page(canvas, doc, org_name, audit_date, is_cover):
    canvas.saveState()
    W, H = PAGE_W, PAGE_H

    # Left sidebar
    canvas.setFillColor(C_TEAL_DARK)
    canvas.rect(0, 0, SIDEBAR_W, H, stroke=0, fill=1)

    # Top strip
    canvas.setFillColor(C_TEAL)
    canvas.rect(0, H - 5 * mm, W, 5 * mm, stroke=0, fill=1)

    # Bottom gold accent
    canvas.setFillColor(C_GOLD)
    canvas.rect(SIDEBAR_W, 0, W - SIDEBAR_W, 2.5 * mm, stroke=0, fill=1)

    if not is_cover:
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(C_FAINT)
        canvas.drawString(L_MARGIN, H - 10 * mm,
                          f"Salesforce Org Audit  ·  {org_name}")
        canvas.drawRightString(W - R_MARGIN, H - 10 * mm, audit_date)
        canvas.setFillColor(C_FAINT)
        canvas.drawCentredString(W / 2, 5.5 * mm, f"Page {doc.page}")
        canvas.drawString(L_MARGIN, 5.5 * mm, "SF Audit Report")
        canvas.drawRightString(W - R_MARGIN, 5.5 * mm, "Powered by Claude Code")

    canvas.restoreState()


# ─── Reusable table helper ─────────────────────────────────────────────────────
def make_table(rows, col_w, row_styles=None, header=True):
    """Build a standard audit table. col_w list must sum to CONTENT_W."""
    base = [
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0),  8),
        ("BACKGROUND",    (0,0), (-1,0),  C_PANEL),
        ("TEXTCOLOR",     (0,0), (-1,0),  C_TEAL_DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("FONTSIZE",      (0,1), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_PAGE_BG]),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, C_BORDER_LT),
    ]
    style = TableStyle(base + (row_styles or []))
    t = Table(rows, colWidths=col_w, repeatRows=1 if header else 0)
    t.setStyle(style)
    return t


# ─── HR helper ────────────────────────────────────────────────────────────────
def hr(color=C_BORDER_LT, thickness=0.5, before=2, after=4):
    return HRFlowable(width="100%", thickness=thickness,
                      color=color, spaceBefore=before*mm, spaceAfter=after*mm)


# ─── PAGE 1 — Cover ────────────────────────────────────────────────────────────
def page_cover(data, st):
    els = []
    org   = data.get("org_name","Salesforce Org")
    user  = data.get("org_username","")
    ed    = data.get("org_edition","")
    date  = data.get("audit_date", datetime.now().strftime("%B %d, %Y"))
    score = int(data.get("overall_score",0))
    grade, bg, fg = score_grade(score)
    summary = data.get("executive_summary","")
    domains = data.get("domains",{})

    els.append(Spacer(1, 18*mm))
    els.append(Paragraph("Salesforce Org Health Audit", st["cover_title"]))
    els.append(Paragraph(org, st["cover_org"]))
    if user: els.append(Paragraph(user, st["cover_sub"]))
    if ed:   els.append(Paragraph(f"{ed}  ·  {date}", st["cover_sub"]))
    els.append(Spacer(1, 4*mm))
    els.append(hr(C_GOLD, thickness=2, before=0, after=5))

    # Score badge + grade box side by side
    badge = score_badge(score, DOMAIN_COLORS[0], w_mm=46, h_mm=56)

    grade_rows = [
        [Paragraph(f'<font size="34"><b>{grade}</b></font>',
                   ParagraphStyle("gv", fontName="Helvetica-Bold",
                                  fontSize=34, textColor=C_TEAL_DARK,
                                  alignment=TA_CENTER))],
        [Paragraph(grade_label(grade),
                   ParagraphStyle("gl", fontName="Helvetica", fontSize=11,
                                  textColor=C_TEAL, alignment=TA_CENTER))],
        [Spacer(1,2)],
        [Paragraph("Org Health Score",
                   ParagraphStyle("gll", fontName="Helvetica", fontSize=7.5,
                                  textColor=C_FAINT, alignment=TA_CENTER))],
    ]
    grade_tbl = Table(grade_rows, colWidths=[62*mm])
    grade_tbl.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BACKGROUND",    (0,0),(-1,-1), bg),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("BOX",           (0,0),(-1,-1), 1.2, C_TEAL_LIGHT),
        ("ROUNDEDCORNERS", [6]),
    ]))

    hero = Table([[badge, grade_tbl]], colWidths=[52*mm, 66*mm])
    hero.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN", (0,0),(-1,-1),"CENTER"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))
    els.append(hero)
    els.append(Spacer(1, 5*mm))
    els.append(hr(C_BORDER, before=0, after=4))

    # Executive summary
    if summary:
        els.append(Paragraph("Executive Summary", st["h1"]))
        panel = Table([[Paragraph(summary, st["exec"])]], colWidths=[CONTENT_W])
        panel.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C_PANEL),
            ("BOX",           (0,0),(-1,-1), 0.8, C_TEAL_LIGHT),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ]))
        els.append(panel)
        els.append(Spacer(1, 4*mm))

    # Quick domain score strip (all domains, 2 columns)
    if domains:
        els.append(Paragraph("Domain Scores at a Glance", st["h2"]))
        items = list(domains.items())
        half  = math.ceil(len(items)/2)
        rows_data = []
        for i in range(half):
            row = []
            for j in [i, i + half]:
                if j < len(items):
                    name, info = items[j]
                    sc = int(info.get("score",0))
                    _, ibg, ifg = score_grade(sc)
                    row.append(Table([
                        [Paragraph(f"<b>{sc}</b>",
                                   ParagraphStyle("qs", fontName="Helvetica-Bold",
                                                  fontSize=15, textColor=ifg,
                                                  alignment=TA_CENTER)),
                         Paragraph(name,
                                   ParagraphStyle("qn", fontName="Helvetica",
                                                  fontSize=7.5, textColor=C_SLATE,
                                                  leading=10))],
                    ], colWidths=[14*mm, 73*mm]))
                    row[-1].setStyle(TableStyle([
                        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                        ("BACKGROUND",    (0,0),(0,0),   ibg),
                        ("TOPPADDING",    (0,0),(-1,-1), 3),
                        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
                        ("LEFTPADDING",   (0,0),(-1,-1), 5),
                        ("BOX",           (0,0),(-1,-1), 0.3, C_BORDER_LT),
                    ]))
                else:
                    row.append(Spacer(1,1))
            rows_data.append(row)

        strip = Table(rows_data, colWidths=[CONTENT_W/2, CONTENT_W/2])
        strip.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1),"TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 2),
            ("BOTTOMPADDING", (0,0),(-1,-1), 2),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ]))
        els.append(strip)

    els.append(PageBreak())
    return els


# ─── PAGE 2 — Domain Overview ─────────────────────────────────────────────────
def page_overview(data, st):
    els = []
    domains = data.get("domains",{})
    els.append(Spacer(1, 6*mm))
    els.append(Paragraph("Domain Score Overview", st["h1"]))
    els.append(hr(C_GOLD, thickness=1.5, before=0, after=4))

    if not domains:
        els.append(Paragraph("No domain data available.", st["body"]))
        els.append(PageBreak())
        return els

    # Bar chart — fits exactly within CONTENT_W
    ch = overview_chart(domains, CONTENT_W/mm)
    els.append(ch)
    els.append(Spacer(1, 3*mm))

    # Score table — col widths sum = CONTENT_W
    cw = [80*mm, 18*mm, 28*mm, 20*mm, 36*mm]  # 182mm total
    hdr = [Paragraph(h, st["th"]) for h in
           ["Domain","Weight","Score","Grade","Status"]]
    rows = [hdr]
    rstyles = []

    for i,(name,info) in enumerate(domains.items()):
        sc = int(info.get("score",0))
        wt = info.get("weight","—")
        g, bg, fg = score_grade(sc)
        status = "PASS ✓" if sc>=70 else ("WARN ⚠" if sc>=50 else "FAIL ✗")
        s_bg   = C_A_BG if sc>=70 else (C_C_BG if sc>=50 else C_D_BG)
        col    = DOMAIN_COLORS[i % len(DOMAIN_COLORS)]

        rows.append([
            Paragraph(f'<font color="#{col.hexval()[2:]}">▐ </font>{name}', st["td"]),
            Paragraph(wt,              st["td"]),
            Paragraph(f"<b>{sc}/100</b>", st["td"]),
            Paragraph(f"<b>{g}</b>",   st["td"]),
            Paragraph(status,          st["td"]),
        ])
        ri = i+1
        rstyles += [
            ("BACKGROUND",(2,ri),(3,ri), bg),
            ("TEXTCOLOR", (2,ri),(3,ri), fg),
            ("BACKGROUND",(4,ri),(4,ri), s_bg),
            ("TEXTCOLOR", (4,ri),(4,ri), fg),
            ("ALIGN",     (1,ri),(4,ri), "CENTER"),
        ]

    tbl = make_table(rows, cw, rstyles)
    els.append(tbl)
    els.append(PageBreak())
    return els


# ─── PAGES 3–11 — Per-domain pages ────────────────────────────────────────────
def page_domain(domain_name, info, idx, all_findings, st):
    els = []
    score     = int(info.get("score",0))
    weight    = info.get("weight","—")
    grade, bg, fg = score_grade(score)
    accent    = DOMAIN_COLORS[idx % len(DOMAIN_COLORS)]
    dims      = info.get("dimension_scores",{})
    top_finds = info.get("top_findings",[])

    # Domain header strip
    hdr_tbl = Table([[
        Paragraph(domain_name, st["domain_hdr"]),
        Paragraph(f"Score: {score}/100  ·  Grade: {grade}  ·  Weight: {weight}",
                  st["domain_sub"]),
    ]], colWidths=[CONTENT_W*0.6, CONTENT_W*0.4])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), accent),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
    ]))
    els.append(hdr_tbl)
    els.append(Spacer(1, 4*mm))

    # Badge (left) + Chart (right) — widths: 50mm + 132mm = 182mm
    BADGE_W = 50 * mm
    CHART_W = (CONTENT_W - BADGE_W - 4*mm) / mm  # mm for the chart helper

    badge = score_badge(score, accent, w_mm=44, h_mm=54)

    if dims:
        ch = dim_chart(dims, accent, avail_w_mm=CHART_W)
        body_row = Table([[badge, ch]],
                         colWidths=[BADGE_W, CONTENT_W - BADGE_W])
        body_row.setStyle(TableStyle([
            ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
            ("TOPPADDING",   (0,0),(-1,-1), 0),
            ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ]))
        els.append(body_row)
    else:
        els.append(badge)

    els.append(Spacer(1, 4*mm))

    # Dimension breakdown table
    if dims:
        els.append(hr(C_BORDER_LT, before=0, after=2))
        els.append(Paragraph("Dimension Breakdown", st["h2"]))

        # col widths: 110 + 28 + 44 = 182mm
        cw = [110*mm, 28*mm, 44*mm]
        hdr = [Paragraph(h, st["th"])
               for h in ["Dimension", "Score", "Status"]]
        rows = [hdr]
        rstyles = []
        for j,(dim_name,dim_sc) in enumerate(dims.items()):
            sc_raw = dim_sc if isinstance(dim_sc,(int,float)) else 0
            pct    = int(sc_raw * 10)
            g2, dbg, dfg = score_grade(pct)
            status = "PASS" if sc_raw>=7 else ("WARN" if sc_raw>=5 else "FAIL")
            s_bg   = C_A_BG if sc_raw>=7 else (C_C_BG if sc_raw>=5 else C_D_BG)
            rows.append([
                Paragraph(dim_name,            st["td"]),
                Paragraph(f"<b>{sc_raw}/10</b>", st["td"]),
                Paragraph(status,              st["td"]),
            ])
            ri = j+1
            rstyles += [
                ("BACKGROUND",(1,ri),(1,ri), dbg),
                ("TEXTCOLOR", (1,ri),(1,ri), dfg),
                ("BACKGROUND",(2,ri),(2,ri), s_bg),
                ("TEXTCOLOR", (2,ri),(2,ri), dfg),
                ("ALIGN",     (1,ri),(2,ri), "CENTER"),
            ]
        els.append(make_table(rows, cw, rstyles))
        els.append(Spacer(1, 3*mm))

    # Key findings for this domain
    domain_finds = [f for f in all_findings
                    if domain_name.lower() in f.get("domain","").lower()]
    if not domain_finds and top_finds:
        domain_finds = [{"severity":"High","domain":domain_name,"finding":t}
                        for t in top_finds[:3]]

    if domain_finds:
        els.append(hr(C_BORDER_LT, before=0, after=2))
        els.append(Paragraph("Key Findings", st["h2"]))
        # col widths: 24 + 158 = 182mm
        cw = [24*mm, 158*mm]
        hdr = [Paragraph(h, st["th"]) for h in ["Severity","Finding"]]
        rows = [hdr]
        rstyles = []
        for k, f in enumerate(domain_finds[:5]):
            sev = f.get("severity","Medium")
            fbg, ffg = sev_colors(sev)
            rows.append([
                Paragraph(f"<b>{sev}</b>",
                          ParagraphStyle("fs", fontName="Helvetica-Bold",
                                         fontSize=7.5, textColor=ffg,
                                         alignment=TA_CENTER)),
                Paragraph(f.get("finding",""), st["td"]),
            ])
            ri = k+1
            rstyles.append(("BACKGROUND",(0,ri),(0,ri), fbg))
        els.append(make_table(rows, cw, rstyles))

    els.append(PageBreak())
    return els


# ─── Findings page ────────────────────────────────────────────────────────────
def page_findings(data, st):
    els = []
    els.append(Spacer(1, 6*mm))
    els.append(Paragraph("All Key Findings", st["h1"]))
    els.append(hr(C_GOLD, thickness=1.5, before=0, after=4))

    findings = sorted(data.get("findings",[]),
                      key=lambda f: {"critical":0,"high":1,"medium":2,"low":3}
                                    .get(f.get("severity","").lower(), 4))
    if not findings:
        els.append(Paragraph("No findings recorded.", st["body"]))
        els.append(PageBreak())
        return els

    # col widths: 24 + 36 + 122 = 182mm
    cw = [24*mm, 36*mm, 122*mm]
    hdr = [Paragraph(h, st["th"]) for h in ["Severity","Domain","Finding"]]
    rows = [hdr]
    rstyles = []
    for i, f in enumerate(findings):
        sev = f.get("severity","Medium")
        fbg, ffg = sev_colors(sev)
        rows.append([
            Paragraph(f"<b>{sev}</b>",
                      ParagraphStyle("fs2", fontName="Helvetica-Bold",
                                     fontSize=7.5, textColor=ffg,
                                     alignment=TA_CENTER)),
            Paragraph(f.get("domain","—"), st["td"]),
            Paragraph(f.get("finding",""), st["td"]),
        ])
        rstyles.append(("BACKGROUND",(0,i+1),(0,i+1), fbg))

    tbl = make_table(rows, cw, rstyles)
    els.append(tbl)
    els.append(PageBreak())
    return els


# ─── Action plan page ─────────────────────────────────────────────────────────
def page_actions(data, st):
    els = []
    els.append(Spacer(1, 6*mm))
    els.append(Paragraph("Priority Action Plan", st["h1"]))
    els.append(hr(C_GOLD, thickness=1.5, before=0, after=4))

    for key, title, bg, fg in [
        ("critical_actions",  "Critical — Act Within 1 Week",    C_CRIT_BG, C_CRIT_FG),
        ("important_actions", "Important — Act Within 1 Month",   C_HIGH_BG, C_HIGH_FG),
        ("strategic_actions", "Strategic — Plan for This Quarter",C_PANEL,   C_TEAL_DARK),
    ]:
        items = data.get(key,[])
        if not items: continue

        # Section header
        hdr_row = Table([[Paragraph(f"<b>{title}</b>",
                                    ParagraphStyle("ah", fontName="Helvetica-Bold",
                                                   fontSize=9.5, textColor=fg))]],
                        colWidths=[CONTENT_W])
        hdr_row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("BOX",           (0,0),(-1,-1), 0.4, C_BORDER_LT),
        ]))
        els.append(hdr_row)

        # Items — col widths: 10 + 172 = 182mm
        cw = [10*mm, CONTENT_W - 10*mm]
        for n, item in enumerate(items, 1):
            item_row = Table([[
                Paragraph(f"<b>{n}.</b>",
                          ParagraphStyle("num", fontName="Helvetica-Bold",
                                         fontSize=8.5, textColor=fg)),
                Paragraph(item, st["action"]),
            ]], colWidths=cw)
            item_row.setStyle(TableStyle([
                ("VALIGN",        (0,0),(-1,-1), "TOP"),
                ("TOPPADDING",    (0,0),(-1,-1), 4),
                ("BOTTOMPADDING", (0,0),(-1,-1), 3),
                ("LEFTPADDING",   (0,0),(-1,-1), 8),
                ("BACKGROUND",    (0,0),(-1,-1), C_WHITE if n%2 else C_PAGE_BG),
                ("BOX",           (0,0),(-1,-1), 0.3, C_BORDER_LT),
            ]))
            els.append(item_row)
        els.append(Spacer(1, 4*mm))

    els.append(PageBreak())
    return els


# ─── Methodology page ─────────────────────────────────────────────────────────
def page_methodology(data, st):
    els = []
    els.append(Spacer(1, 6*mm))
    els.append(Paragraph("Methodology & Audit Metadata", st["h1"]))
    els.append(hr(C_GOLD, thickness=1.5, before=0, after=4))

    # Weights table — 50 + 16 + 116 = 182mm
    cw_w = [50*mm, 16*mm, 116*mm]
    domain_desc = {
        "Security & Access":       "Profiles, permission sets, sharing model, MFA, login activity",
        "Data Quality":            "Contact/Account/Lead completeness, duplicates, stale records",
        "Automation Health":       "Flows, Process Builder, Workflow Rules, Apex triggers",
        "Org Architecture":        "Governor limits, custom objects, Apex API versions, packages",
        "Test Coverage":           "Apex test coverage %, classes below 75%, test failures",
        "Naming Conventions":      "Apex class/trigger naming, field/flow/validation rule standards",
        "Orphaned Metadata":       "Inactive flows, dead validation/workflow rules, stale fields",
        "Description Completeness":"Missing help text on fields, flows, objects, validation rules",
        "Custom Field Sprawl":     "Objects with 100+ fields, stale fields, duplicate-purpose fields",
    }
    hdr = [Paragraph(h, st["th"]) for h in ["Domain","Weight","What It Measures"]]
    rows = [hdr]
    for name, info in data.get("domains",{}).items():
        rows.append([Paragraph(name, st["td"]),
                     Paragraph(info.get("weight","—"), st["td"]),
                     Paragraph(domain_desc.get(name,"—"), st["td"])])
    els.append(Paragraph("Scoring Weights", st["h2"]))
    tbl = make_table(rows, cw_w)
    tbl.setStyle(TableStyle([("ALIGN",(1,0),(1,-1),"CENTER")]))
    els.append(tbl)
    els.append(Spacer(1, 4*mm))

    # Grade scale — 28 + 18 + 28 + 108 = 182mm
    cw_g = [28*mm, 18*mm, 28*mm, 108*mm]
    els.append(Paragraph("Grade Scale", st["h2"]))
    ghdr = [Paragraph(h, st["th"]) for h in ["Score","Grade","Label","Interpretation"]]
    grows = [ghdr,
             ["90–100","A+","Excellent","Production-grade org, minimal risk"],
             ["80–89", "A", "Strong",   "Minor improvements recommended"],
             ["70–79", "B", "Good",     "Some areas need attention"],
             ["60–69", "C", "Fair",     "Multiple risk areas identified"],
             ["50–59", "D", "Poor",     "Significant remediation required"],
             ["< 50",  "F", "Critical", "Immediate action required"]]
    gstyles = []
    for i,sc in enumerate([95,85,75,65,55,45],1):
        _,bg,fg = score_grade(sc)
        gstyles += [("BACKGROUND",(1,i),(1,i),bg),("TEXTCOLOR",(1,i),(1,i),fg)]
        grows[i] = [Paragraph(str(x), st["td"]) for x in grows[i]]
    els.append(make_table(grows, cw_g, gstyles))
    els.append(Spacer(1, 4*mm))

    # Metadata — 60 + 122 = 182mm
    meta = data.get("audit_metadata",{})
    if meta:
        els.append(Paragraph("Audit Metadata", st["h2"]))
        mrows = [[Paragraph("Item",st["th"]), Paragraph("Value",st["th"])]]
        for k,v in meta.items():
            mrows.append([Paragraph(str(k),st["td"]),Paragraph(str(v),st["td"])])
        els.append(make_table(mrows, [60*mm, 122*mm]))

    els.append(Spacer(1, 6*mm))
    els.append(hr(C_GOLD, before=0, after=3))
    els.append(Paragraph(
        "Generated by sf-audit  ·  Powered by Claude Code  ·  anthropic.com",
        st["footer"]))
    return els


# ─── Build & save PDF ─────────────────────────────────────────────────────────
def generate_pdf(data, output_path):
    org_name   = data.get("org_name","Salesforce Org")
    audit_date = data.get("audit_date", datetime.now().strftime("%B %d, %Y"))

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=L_MARGIN, rightMargin=R_MARGIN,
        topMargin=T_MARGIN,  bottomMargin=B_MARGIN,
        title=f"Salesforce Org Audit — {org_name}",
        author="sf-audit (Claude Code)",
        subject="Salesforce Org Health Report",
    )

    st  = build_styles()
    els = []
    els += page_cover(data, st)
    els += page_overview(data, st)

    domains  = data.get("domains",{})
    findings = data.get("findings",[])
    for idx,(name,info) in enumerate(domains.items()):
        els += page_domain(name, info, idx, findings, st)

    els += page_findings(data, st)
    els += page_actions(data, st)
    els += page_methodology(data, st)

    page_num = [0]
    def on_page(canvas, doc):
        page_num[0] += 1
        decorate_page(canvas, doc, org_name, audit_date,
                      is_cover=(page_num[0]==1))

    doc.build(els, onFirstPage=on_page, onLaterPages=on_page)
    total = 2 + len(domains) + 3
    print(f"✓ PDF generated: {output_path}  ({total} pages)")


# ─── Demo data ────────────────────────────────────────────────────────────────
def demo_data():
    return {
        "org_name": "codeSTREETS B.V.",
        "org_username": "admin@codestreets.com",
        "org_edition": "Enterprise Edition",
        "audit_date": datetime.now().strftime("%B %d, %Y"),
        "overall_score": 71,
        "grade": "B",
        "executive_summary": (
            "codeSTREETS B.V.'s Salesforce org scores 71/100 — a solid foundation with targeted "
            "improvement areas. The primary risk is security: two non-admin profiles carry "
            "Modify All Data permissions. Naming conventions and description completeness are "
            "the weakest metadata quality dimensions, with 38% of active flows missing descriptions. "
            "Immediate action: remove elevated profile permissions and add descriptions to all active flows."
        ),
        "domains": {
            "Security & Access":       {"score": 63, "weight": "20%",
                "dimension_scores": {"Profile Hygiene":5,"Permission Set Sprawl":7,"Sharing Model":8,"MFA Enforcement":6,"IP/Session Restrictions":4,"Field-Level Security":7},
                "top_findings":["2 non-admin profiles have Modify All Data","14 users inactive 90+ days"]},
            "Data Quality":            {"score": 78, "weight": "15%",
                "dimension_scores":{"Contact Completeness":8,"Account Completeness":7,"Lead Hygiene":6,"Duplicate Rule Coverage":9,"Opportunity Hygiene":7},
                "top_findings":["Contact Email null rate 18%"]},
            "Automation Health":       {"score": 69, "weight": "15%",
                "dimension_scores":{"Flow Health":7,"Process Builder Debt":5,"Workflow Rules":4,"Trigger Hygiene":8,"Validation Quality":8},
                "top_findings":["6 active Workflow Rules","3 Process Builder processes"]},
            "Org Architecture":        {"score": 84, "weight": "12%",
                "dimension_scores":{"Object/Field Sprawl":8,"Governor Limits":9,"Apex API Version Debt":7,"Package Health":9,"Custom Settings vs CMDT":6},
                "top_findings":["8 classes on API v45"]},
            "Test Coverage":           {"score": 73, "weight": "8%",
                "dimension_scores":{"Org-Wide Coverage %":8,"Classes Below 75%":6,"Test Class Quality":7,"Trigger Coverage":8},
                "top_findings":["4 classes below 75% coverage"]},
            "Naming Conventions":      {"score": 61, "weight": "8%",
                "dimension_scores":{"Apex Class Naming":5,"Apex Trigger Naming":7,"Custom Field Naming":6,"Flow Naming":5,"Validation Rule Naming":7},
                "top_findings":["32% of classes missing type suffix","14 flows non-descriptive"]},
            "Orphaned Metadata":       {"score": 72, "weight": "8%",
                "dimension_scores":{"Inactive Flows":8,"Dead Validation Rules":7,"Deactivated Workflow Rules":6,"Stale Custom Fields":7},
                "top_findings":["12 inactive flows","5 deactivated validation rules"]},
            "Description Completeness":{"score": 54, "weight": "7%",
                "dimension_scores":{"Custom Field Help Text":4,"Flow Descriptions":5,"Validation Rule Descriptions":6,"Object Descriptions":5,"Apex Class Doc Comments":6},
                "top_findings":["62% of fields missing help text","38% of flows undocumented"]},
            "Custom Field Sprawl":     {"score": 80, "weight": "7%",
                "dimension_scores":{"Objects >=100 Fields":8,"Objects 50-99 Fields":7,"Stale Fields >730d":8,"Duplicate-Purpose Fields":8},
                "top_findings":["Account object at 127 custom fields"]},
        },
        "findings": [
            {"severity":"Critical","domain":"Security & Access","finding":"2 non-admin profiles have PermissionsModifyAllData = true."},
            {"severity":"Critical","domain":"Automation Health","finding":"6 active Workflow Rules — retired technology with no Salesforce bug fixes after Winter '23."},
            {"severity":"High",    "domain":"Security & Access","finding":"14 active users have not logged in for 90+ days — deactivate to reduce attack surface."},
            {"severity":"High",    "domain":"Description Completeness","finding":"62% of custom fields are missing InlineHelpText — users cannot understand field purpose."},
            {"severity":"High",    "domain":"Naming Conventions","finding":"32% of Apex classes are missing a type suffix (_CTRL, _SERVICE, _TEST, _HANDLER)."},
            {"severity":"Medium",  "domain":"Data Quality","finding":"Contact Email null rate is 18% (3,210 of 17,830 contacts unreachable by email)."},
            {"severity":"Medium",  "domain":"Automation Health","finding":"3 Process Builder processes still active — migrate to Flow."},
            {"severity":"Medium",  "domain":"Test Coverage","finding":"4 Apex classes below 75%: OrderSync (48%), PricingHelper (52%), LeadRouter (61%), InvoiceService (64%)."},
            {"severity":"Low",     "domain":"Org Architecture","finding":"8 Apex classes on API v45 — review for deprecated method usage."},
        ],
        "critical_actions": [
            "Remove PermissionsModifyAllData from both non-admin profiles. Use Permission Sets for elevated-access requirements.",
            "Migrate all 6 Workflow Rules to Record-Triggered Flows immediately.",
        ],
        "important_actions": [
            "Deactivate 14 users with no login in 90+ days.",
            "Add InlineHelpText to all custom fields missing descriptions.",
            "Add type suffixes (_CTRL, _SERVICE, _HANDLER, _TEST) to Apex classes missing them.",
            "Add descriptions to all 38% of active flows currently undocumented.",
        ],
        "strategic_actions": [
            "Migrate 3 Process Builder processes to Flow as part of Q3 automation modernization.",
            "Run a quarterly naming convention cleanup sprint.",
            "Establish a definition-of-done checklist requiring help text and description on all new metadata.",
        ],
        "audit_metadata": {
            "Queries Executed": "78",
            "API Version": "v66.0",
            "Execution Mode": "Parallel (9 agents)",
            "Generated": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
            "Tool": "sf-audit (Claude Code)",
        },
    }


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        with open(sys.argv[1]) as f:
            data = json.load(f)
        output = sys.argv[2] if len(sys.argv) >= 3 else "SF-AUDIT-REPORT.pdf"
    else:
        print("No input file — generating demo report.")
        data   = demo_data()
        output = "SF-AUDIT-REPORT-DEMO.pdf"
    generate_pdf(data, output)
