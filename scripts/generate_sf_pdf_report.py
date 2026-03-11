#!/usr/bin/env python3
"""
Salesforce Org Audit — PDF Report Generator
Generates a professional, client-ready PDF from SF audit JSON data.
Inspired by codeSTREETS design: teal/gold palette, clean white layout,
per-domain chart pages.

Usage: python3 generate_sf_pdf_report.py [input.json] [output.pdf]
Demo:  python3 generate_sf_pdf_report.py
"""

import sys
import json
import math
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import (
        Drawing, Circle, Rect, String, Line, Polygon, ArcPath
    )
    from reportlab.graphics import renderPDF
    from reportlab.graphics.charts.barcharts import HorizontalBarChart
except ImportError:
    print("ERROR: reportlab is required. Install with: pip3 install reportlab")
    sys.exit(1)


# ─── Color Palette (codeSTREETS-inspired: teal + gold + clean white) ──────────
C_WHITE        = HexColor("#FFFFFF")
C_PAGE_BG      = HexColor("#F5F7FA")   # near-white page bg
C_PANEL        = HexColor("#EBF4F8")   # light teal panel
C_PANEL_GOLD   = HexColor("#FEF9EC")   # light gold panel

C_TEAL         = HexColor("#1E7FA4")   # primary teal
C_TEAL_DARK    = HexColor("#155A76")   # darker teal — headings
C_TEAL_LIGHT   = HexColor("#7DC4DC")   # light teal — accents
C_GOLD         = HexColor("#F5A623")   # gold accent
C_GOLD_DARK    = HexColor("#D4891A")   # darker gold

C_NAVY         = HexColor("#1A2533")   # near-black body text
C_SLATE        = HexColor("#3D5166")   # mid-dark secondary text
C_MID          = HexColor("#5A7A8A")   # muted labels
C_LIGHT        = HexColor("#8BA8B5")   # faint captions/watermarks
C_BORDER       = HexColor("#C4DAE4")   # teal-tinted border
C_BORDER_LIGHT = HexColor("#E0EDF2")   # very light border

# Grade / score colors
C_A_BG  = HexColor("#D4EDDA"); C_A_FG  = HexColor("#1A6632")
C_B_BG  = HexColor("#D0EAF5"); C_B_FG  = HexColor("#1E5F80")
C_C_BG  = HexColor("#FEF9C3"); C_C_FG  = HexColor("#7A5A00")
C_D_BG  = HexColor("#FDECEA"); C_D_FG  = HexColor("#8B2222")

C_CRIT_BG = HexColor("#FDECEA"); C_CRIT_FG = HexColor("#8B2222")
C_HIGH_BG = HexColor("#FEF0E4"); C_HIGH_FG = HexColor("#8B4500")
C_MED_BG  = HexColor("#FEF9C3"); C_MED_FG  = HexColor("#7A5A00")
C_LOW_BG  = HexColor("#D4EDDA"); C_LOW_FG  = HexColor("#1A6632")

# Per-domain accent colors (one per domain for chart bars)
DOMAIN_COLORS = [
    HexColor("#1E7FA4"),  # Security        — primary teal
    HexColor("#2E9E8A"),  # Data Quality     — green-teal
    HexColor("#F5A623"),  # Automation       — gold
    HexColor("#5B6EAE"),  # Architecture     — slate-blue
    HexColor("#3EB0A8"),  # Test Coverage    — aqua
    HexColor("#D4891A"),  # Naming           — dark gold
    HexColor("#7B5EA7"),  # Orphaned         — purple
    HexColor("#2A8FA0"),  # Descriptions     — mid-teal
    HexColor("#E0703C"),  # Field Sprawl     — terracotta
]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def score_colors(score):
    if score >= 80: return C_A_BG, C_A_FG
    if score >= 70: return C_B_BG, C_B_FG
    if score >= 60: return C_C_BG, C_C_FG
    return C_D_BG, C_D_FG


def grade_from_score(score):
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"


def grade_label(grade):
    return {
        "A+": "Excellent", "A": "Strong", "B": "Good",
        "C": "Fair", "D": "Poor", "F": "Critical",
    }.get(grade, "")


def severity_colors(severity):
    s = severity.lower()
    if "critical" in s: return C_CRIT_BG, C_CRIT_FG
    if "high"     in s: return C_HIGH_BG, C_HIGH_FG
    if "medium"   in s: return C_MED_BG,  C_MED_FG
    return C_LOW_BG, C_LOW_FG


# ─── Score Gauge ──────────────────────────────────────────────────────────────
def build_score_gauge(score, size=110, accent_color=None):
    d = Drawing(size, size)
    cx, cy = size / 2, size / 2
    r = size * 0.40

    # Track (full circle using ArcPath)
    track = ArcPath()
    track.addArc(cx - r, cy - r, cx + r, cy + r, 0, 360)
    track.strokeColor = C_BORDER_LIGHT
    track.strokeWidth = size * 0.08
    track.fillColor = None
    d.add(track)

    # Score arc
    pct = max(0, min(score, 100)) / 100
    if pct > 0:
        _, fg = score_colors(score)
        color = accent_color if accent_color else fg
        arc = ArcPath()
        arc.addArc(cx - r, cy - r, cx + r, cy + r, 90, -(pct * 360))
        arc.strokeColor = color
        arc.strokeWidth = size * 0.08
        arc.fillColor = None
        d.add(arc)

    # Inner white fill
    inner = Circle(cx, cy, r * 0.60)
    inner.fillColor = C_WHITE
    inner.strokeColor = C_BORDER_LIGHT
    inner.strokeWidth = 0.5
    d.add(inner)

    # Score text
    _, fg = score_colors(score)
    color = accent_color if accent_color else fg
    d.add(String(cx, cy + size * 0.03, str(score),
                 fontSize=size * 0.20, fontName="Helvetica-Bold",
                 fillColor=color, textAnchor="middle"))
    d.add(String(cx, cy - size * 0.12, "/100",
                 fontSize=size * 0.09, fontName="Helvetica",
                 fillColor=C_LIGHT, textAnchor="middle"))
    return d


# ─── Dimension Bar Chart ──────────────────────────────────────────────────────
def build_dimension_chart(dimensions, bar_color, chart_width_mm=120, chart_height_mm=None):
    """Horizontal bar chart of dimension scores (0–10 scale)."""
    n = len(dimensions)
    if n == 0:
        return Drawing(chart_width_mm * mm, 10 * mm)

    h = chart_height_mm * mm if chart_height_mm else (n * 12 + 14) * mm
    cw = chart_width_mm * mm
    label_w = 52 * mm

    d = Drawing(cw + label_w, h)
    chart = HorizontalBarChart()
    chart.x = label_w
    chart.y = 6 * mm
    chart.width = cw - 8 * mm
    chart.height = h - 12 * mm

    scores = [v if isinstance(v, (int, float)) else 0 for v in dimensions.values()]
    chart.data = [scores]
    chart.reversePlotOrder = 1

    chart.bars[0].fillColor = bar_color
    chart.bars[0].strokeColor = None

    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 10
    chart.valueAxis.valueStep = 2
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 6.5
    chart.valueAxis.labels.fillColor = C_MID
    chart.valueAxis.gridStrokeColor = C_BORDER_LIGHT
    chart.valueAxis.gridStrokeWidth = 0.3
    chart.valueAxis.strokeColor = C_BORDER_LIGHT

    chart.categoryAxis.categoryNames = list(dimensions.keys())
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.fillColor = C_SLATE
    chart.categoryAxis.labels.dx = -4
    chart.categoryAxis.labels.textAnchor = 'end'
    chart.categoryAxis.gridStrokeColor = None
    chart.categoryAxis.strokeColor = None

    chart.barLabelFormat = '%g'
    chart.barLabels.fontName = "Helvetica-Bold"
    chart.barLabels.fontSize = 7
    chart.barLabels.fillColor = C_NAVY
    chart.barLabels.nudge = 5

    d.add(chart)
    return d


# ─── All-Domain Overview Bar Chart ───────────────────────────────────────────
def build_overview_chart(domains):
    """Horizontal bar chart for all domains (0–100 scale), colored by domain."""
    names = list(domains.keys())
    scores = [int(v.get("score", 0)) for v in domains.values()]
    n = len(names)

    h = (n * 14 + 16) * mm
    cw = 130 * mm
    lw = 50 * mm
    d = Drawing(cw + lw, h)

    chart = HorizontalBarChart()
    chart.x = lw
    chart.y = 6 * mm
    chart.width = cw - 8 * mm
    chart.height = h - 12 * mm
    chart.data = [scores]
    chart.reversePlotOrder = 1

    # Color each bar by its domain color
    for i, sc in enumerate(scores):
        idx = (n - 1 - i) % len(DOMAIN_COLORS)
        chart.bars[(0, i)].fillColor = DOMAIN_COLORS[idx]
        chart.bars[(0, i)].strokeColor = None

    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 20
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = C_MID
    chart.valueAxis.gridStrokeColor = C_BORDER_LIGHT
    chart.valueAxis.gridStrokeWidth = 0.3
    chart.valueAxis.strokeColor = C_BORDER_LIGHT

    chart.categoryAxis.categoryNames = names
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = C_SLATE
    chart.categoryAxis.labels.dx = -4
    chart.categoryAxis.labels.textAnchor = 'end'
    chart.categoryAxis.gridStrokeColor = None
    chart.categoryAxis.strokeColor = None

    chart.barLabelFormat = '%d'
    chart.barLabels.fontName = "Helvetica-Bold"
    chart.barLabels.fontSize = 7.5
    chart.barLabels.fillColor = C_NAVY
    chart.barLabels.nudge = 6

    d.add(chart)
    return d


# ─── Styles ───────────────────────────────────────────────────────────────────
def build_styles():
    return {
        "cover_title": ParagraphStyle(
            "cover_title", fontName="Helvetica-Bold", fontSize=28,
            textColor=C_TEAL_DARK, spaceAfter=4, leading=34),
        "cover_org": ParagraphStyle(
            "cover_org", fontName="Helvetica-Bold", fontSize=16,
            textColor=C_TEAL, spaceAfter=2),
        "cover_sub": ParagraphStyle(
            "cover_sub", fontName="Helvetica", fontSize=11,
            textColor=C_SLATE, spaceAfter=2),
        "section_heading": ParagraphStyle(
            "section_heading", fontName="Helvetica-Bold", fontSize=14,
            textColor=C_TEAL_DARK, spaceBefore=10, spaceAfter=5, leading=18),
        "domain_heading": ParagraphStyle(
            "domain_heading", fontName="Helvetica-Bold", fontSize=13,
            textColor=C_WHITE, spaceAfter=3, leading=16),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=9,
            textColor=C_SLATE, leading=14, spaceAfter=4),
        "body_small": ParagraphStyle(
            "body_small", fontName="Helvetica", fontSize=8,
            textColor=C_MID, leading=12),
        "label": ParagraphStyle(
            "label", fontName="Helvetica-Bold", fontSize=8,
            textColor=C_MID, leading=11),
        "executive": ParagraphStyle(
            "executive", fontName="Helvetica", fontSize=10,
            textColor=C_SLATE, leading=16, spaceAfter=5,
            leftIndent=10, rightIndent=10),
        "table_header": ParagraphStyle(
            "table_header", fontName="Helvetica-Bold", fontSize=8,
            textColor=C_TEAL_DARK),
        "table_cell": ParagraphStyle(
            "table_cell", fontName="Helvetica", fontSize=8,
            textColor=C_SLATE, leading=12),
        "action_item": ParagraphStyle(
            "action_item", fontName="Helvetica", fontSize=9,
            textColor=C_SLATE, leading=13, leftIndent=6, spaceAfter=3),
        "finding_item": ParagraphStyle(
            "finding_item", fontName="Helvetica", fontSize=8.5,
            textColor=C_SLATE, leading=13, spaceAfter=2),
        "footer": ParagraphStyle(
            "footer", fontName="Helvetica", fontSize=7,
            textColor=C_LIGHT, alignment=TA_CENTER),
    }


# ─── Page header/footer callbacks ─────────────────────────────────────────────
def on_page(canvas, doc, org_name="", audit_date="", is_cover=False):
    W, H = A4
    canvas.saveState()

    if is_cover:
        # Left teal sidebar strip
        canvas.setFillColor(C_TEAL_DARK)
        canvas.rect(0, 0, 8 * mm, H, stroke=0, fill=1)
        # Top strip
        canvas.setFillColor(C_TEAL)
        canvas.rect(0, H - 6 * mm, W, 6 * mm, stroke=0, fill=1)
        # Bottom gold accent line
        canvas.setFillColor(C_GOLD)
        canvas.rect(8 * mm, 0, W - 8 * mm, 3 * mm, stroke=0, fill=1)
    else:
        # Left teal sidebar
        canvas.setFillColor(C_TEAL_DARK)
        canvas.rect(0, 0, 5 * mm, H, stroke=0, fill=1)
        # Top strip
        canvas.setFillColor(C_TEAL)
        canvas.rect(0, H - 5 * mm, W, 5 * mm, stroke=0, fill=1)
        # Gold bottom accent
        canvas.setFillColor(C_GOLD)
        canvas.rect(5 * mm, 0, W - 5 * mm, 2 * mm, stroke=0, fill=1)

        # Header text
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(C_LIGHT)
        canvas.drawString(12 * mm, H - 10 * mm,
                          f"Salesforce Org Audit  ·  {org_name}")
        canvas.drawRightString(W - 8 * mm, H - 10 * mm, audit_date)

        # Footer text
        canvas.drawCentredString(W / 2, 6 * mm, f"Page {doc.page}")
        canvas.drawString(12 * mm, 6 * mm, "SF Audit Report")
        canvas.drawRightString(W - 8 * mm, 6 * mm, "Powered by Claude Code")

    canvas.restoreState()


# ─── Page 1: Cover ────────────────────────────────────────────────────────────
def build_cover(data, styles):
    elements = []
    org   = data.get("org_name", "Salesforce Org")
    user  = data.get("org_username", "")
    ed    = data.get("org_edition", "")
    date  = data.get("audit_date", datetime.now().strftime("%B %d, %Y"))
    score = int(data.get("overall_score", 0))
    grade = data.get("grade") or grade_from_score(score)
    summary = data.get("executive_summary", "")

    elements.append(Spacer(1, 20 * mm))
    elements.append(Paragraph("Salesforce Org Health Audit", styles["cover_title"]))
    elements.append(Paragraph(org, styles["cover_org"]))
    if user:
        elements.append(Paragraph(user, styles["cover_sub"]))
    if ed:
        elements.append(Paragraph(f"{ed}  ·  Audit Date: {date}", styles["cover_sub"]))
    elements.append(Spacer(1, 6 * mm))

    # Gold accent rule
    elements.append(HRFlowable(width="100%", thickness=2,
                               color=C_GOLD, spaceAfter=8 * mm))

    # Score gauge + grade
    gauge = build_score_gauge(score, size=120, accent_color=C_TEAL)
    bg_c, fg_c = score_colors(score)

    grade_content = [
        [Paragraph(f'<font size="40"><b>{grade}</b></font>',
                   ParagraphStyle("gv", fontName="Helvetica-Bold",
                                  fontSize=40, textColor=C_TEAL_DARK,
                                  alignment=TA_CENTER))],
        [Paragraph(grade_label(grade), ParagraphStyle(
            "gl", fontName="Helvetica", fontSize=12,
            textColor=C_TEAL, alignment=TA_CENTER))],
        [Spacer(1, 4)],
        [Paragraph("Overall Org Health", ParagraphStyle(
            "gll", fontName="Helvetica", fontSize=8,
            textColor=C_LIGHT, alignment=TA_CENTER))],
    ]
    grade_tbl = Table(grade_content, colWidths=[65 * mm])
    grade_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, -1), C_PANEL),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("BOX", (0, 0), (-1, -1), 1, C_TEAL_LIGHT),
    ]))

    score_row = Table([[gauge, grade_tbl]], colWidths=[75 * mm, 75 * mm])
    score_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(score_row)
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=C_BORDER, spaceAfter=6 * mm))

    # Executive summary
    if summary:
        elements.append(Paragraph("Executive Summary", styles["section_heading"]))
        panel = Table([[Paragraph(summary, styles["executive"])]],
                      colWidths=[168 * mm])
        panel.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_PANEL),
            ("ROUNDEDCORNERS", [6]),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
            ("BOX", (0, 0), (-1, -1), 1, C_TEAL_LIGHT),
        ]))
        elements.append(panel)

    elements.append(Spacer(1, 6 * mm))
    # Quick domain summary at bottom of cover
    domains = data.get("domains", {})
    if domains:
        elements.append(Paragraph("Domain Scores at a Glance",
                                  ParagraphStyle("dg", fontName="Helvetica-Bold",
                                                 fontSize=9, textColor=C_TEAL_DARK,
                                                 spaceAfter=4)))
        cols = min(len(domains), 5)
        dom_items = list(domains.items())[:cols]
        cell_w = 168 / cols * mm
        quick_row = []
        for name, info in dom_items:
            sc = int(info.get("score", 0))
            bg, fg = score_colors(sc)
            cell = Table([
                [Paragraph(f"<b>{sc}</b>", ParagraphStyle(
                    "qs", fontName="Helvetica-Bold", fontSize=13,
                    textColor=fg, alignment=TA_CENTER))],
                [Paragraph(name, ParagraphStyle(
                    "qn", fontName="Helvetica", fontSize=6.5,
                    textColor=C_MID, alignment=TA_CENTER, leading=9))],
            ], colWidths=[cell_w - 4 * mm])
            cell.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("ROUNDEDCORNERS", [4]),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            quick_row.append(cell)

        quick_tbl = Table([quick_row],
                          colWidths=[cell_w] * len(dom_items))
        quick_tbl.setStyle(TableStyle([
            ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(quick_tbl)

    elements.append(PageBreak())
    return elements


# ─── Page 2: Domain Overview ──────────────────────────────────────────────────
def build_domain_overview(data, styles):
    elements = []
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Domain Score Overview", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=C_GOLD, spaceAfter=6 * mm))

    domains = data.get("domains", {})
    if not domains:
        elements.append(Paragraph("No domain data available.", styles["body"]))
        elements.append(PageBreak())
        return elements

    # Chart
    chart_d = build_overview_chart(domains)
    elements.append(chart_d)
    elements.append(Spacer(1, 4 * mm))

    # Score table
    header = [
        Paragraph("Domain", styles["table_header"]),
        Paragraph("Weight", styles["table_header"]),
        Paragraph("Score", styles["table_header"]),
        Paragraph("Grade", styles["table_header"]),
        Paragraph("Status", styles["table_header"]),
    ]
    rows = [header]
    row_styles = []

    for i, (domain, info) in enumerate(domains.items()):
        sc = int(info.get("score", 0))
        wt = info.get("weight", "—")
        gr = grade_from_score(sc)
        bg_c, fg_c = score_colors(sc)
        status = "PASS" if sc >= 70 else ("WARN" if sc >= 50 else "FAIL")
        status_bg = C_A_BG if sc >= 70 else (C_C_BG if sc >= 50 else C_D_BG)
        dot_color = DOMAIN_COLORS[i % len(DOMAIN_COLORS)]

        rows.append([
            Paragraph(f'<font color="#{dot_color.hexval()[2:]}">■</font>  {domain}',
                      styles["table_cell"]),
            Paragraph(wt, styles["table_cell"]),
            Paragraph(f"<b>{sc}/100</b>", styles["table_cell"]),
            Paragraph(f"<b>{gr}</b>", styles["table_cell"]),
            Paragraph(status, styles["table_cell"]),
        ])
        ri = i + 1
        row_styles += [
            ("BACKGROUND", (2, ri), (3, ri), bg_c),
            ("TEXTCOLOR",  (2, ri), (3, ri), fg_c),
            ("BACKGROUND", (4, ri), (4, ri), status_bg),
        ]

    tbl = Table(rows, colWidths=[72 * mm, 16 * mm, 26 * mm, 18 * mm, 22 * mm],
                repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_TEAL_DARK),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (0, 0), (0, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
    ] + row_styles))
    elements.append(tbl)
    elements.append(PageBreak())
    return elements


# ─── Pages 3–11: Per-Domain Detail Pages ──────────────────────────────────────
def build_domain_page(domain_name, info, idx, findings, styles):
    """One page per domain: header strip, gauge, dimension chart, top findings."""
    elements = []
    score = int(info.get("score", 0))
    weight = info.get("weight", "—")
    grade = grade_from_score(score)
    bar_color = DOMAIN_COLORS[idx % len(DOMAIN_COLORS)]
    bg_c, fg_c = score_colors(score)
    dimensions = info.get("dimension_scores", {})
    top_findings = info.get("top_findings", [])

    elements.append(Spacer(1, 4 * mm))

    # Domain header banner
    header_content = [[
        Paragraph(domain_name, styles["domain_heading"]),
        Paragraph(f"Score: {score}/100  ·  Grade: {grade}  ·  Weight: {weight}",
                  ParagraphStyle("ds", fontName="Helvetica", fontSize=9,
                                 textColor=C_WHITE, alignment=TA_RIGHT)),
    ]]
    header_tbl = Table(header_content, colWidths=[100 * mm, 68 * mm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bar_color),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [4]),
    ]))
    elements.append(header_tbl)
    elements.append(Spacer(1, 5 * mm))

    # Gauge + Dimension chart side by side
    gauge = build_score_gauge(score, size=100, accent_color=bar_color)

    if dimensions:
        chart_d = build_dimension_chart(dimensions, bar_color,
                                        chart_width_mm=115,
                                        chart_height_mm=max(len(dimensions) * 11 + 12, 50))
        layout = Table([[gauge, chart_d]],
                       colWidths=[50 * mm, 120 * mm])
        layout.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(layout)
    else:
        elements.append(gauge)

    elements.append(Spacer(1, 4 * mm))

    # Dimension scores table (if available)
    if dimensions:
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                   color=C_BORDER_LIGHT, spaceAfter=3 * mm))
        elements.append(Paragraph("Dimension Breakdown",
                                  ParagraphStyle("dh", fontName="Helvetica-Bold",
                                                 fontSize=9, textColor=C_TEAL_DARK,
                                                 spaceAfter=3)))
        dim_header = [
            Paragraph("Dimension", styles["table_header"]),
            Paragraph("Score (/10)", styles["table_header"]),
            Paragraph("Status", styles["table_header"]),
        ]
        dim_rows = [dim_header]
        dim_styles = []
        for j, (dim_name, dim_score) in enumerate(dimensions.items()):
            sc = dim_score if isinstance(dim_score, (int, float)) else 0
            pct_score = int(sc * 10)
            bg, fg = score_colors(pct_score)
            status = "PASS" if sc >= 7 else ("WARN" if sc >= 5 else "FAIL")
            s_bg = C_A_BG if sc >= 7 else (C_C_BG if sc >= 5 else C_D_BG)
            dim_rows.append([
                Paragraph(dim_name, styles["table_cell"]),
                Paragraph(f"<b>{sc}/10</b>", styles["table_cell"]),
                Paragraph(status, styles["table_cell"]),
            ])
            ri = j + 1
            dim_styles += [
                ("BACKGROUND", (1, ri), (1, ri), bg),
                ("TEXTCOLOR",  (1, ri), (1, ri), fg),
                ("BACKGROUND", (2, ri), (2, ri), s_bg),
            ]

        dim_tbl = Table(dim_rows, colWidths=[100 * mm, 30 * mm, 24 * mm])
        dim_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_TEAL_DARK),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
            ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
        ] + dim_styles))
        elements.append(dim_tbl)
        elements.append(Spacer(1, 4 * mm))

    # Top findings for this domain
    domain_findings = [f for f in findings
                       if domain_name.lower() in f.get("domain", "").lower()]
    if not domain_findings and top_findings:
        domain_findings = [{"severity": "High", "domain": domain_name,
                            "finding": t} for t in top_findings[:3]]

    if domain_findings:
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                   color=C_BORDER_LIGHT, spaceAfter=3 * mm))
        elements.append(Paragraph("Key Findings",
                                  ParagraphStyle("fh", fontName="Helvetica-Bold",
                                                 fontSize=9, textColor=C_TEAL_DARK,
                                                 spaceAfter=3)))
        for f in domain_findings[:4]:
            sev = f.get("severity", "Medium")
            txt = f.get("finding", "")
            bg_c, fg_c = severity_colors(sev)
            row = [[
                Paragraph(f"<b>{sev}</b>", ParagraphStyle(
                    "fs", fontName="Helvetica-Bold", fontSize=7.5,
                    textColor=fg_c, alignment=TA_CENTER)),
                Paragraph(txt, styles["finding_item"]),
            ]]
            row_tbl = Table(row, colWidths=[20 * mm, 148 * mm])
            row_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (0, 0), bg_c),
                ("BACKGROUND",    (1, 0), (1, 0), C_WHITE),
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("BOX",           (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
                ("LINEBELOW",     (0, 0), (-1, 0), 0.3, C_BORDER_LIGHT),
            ]))
            elements.append(row_tbl)

    elements.append(PageBreak())
    return elements


# ─── Findings Page ────────────────────────────────────────────────────────────
def build_findings(data, styles):
    elements = []
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("All Key Findings", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=C_GOLD, spaceAfter=6 * mm))

    findings = data.get("findings", [])
    if not findings:
        elements.append(Paragraph("No findings recorded.", styles["body"]))
        elements.append(PageBreak())
        return elements

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings = sorted(findings,
                      key=lambda f: sev_order.get(f.get("severity", "").lower(), 4))

    header = [
        Paragraph("Severity", styles["table_header"]),
        Paragraph("Domain", styles["table_header"]),
        Paragraph("Finding", styles["table_header"]),
    ]
    rows = [header]
    row_styles = []

    for i, f in enumerate(findings):
        sev = f.get("severity", "Medium")
        bg_c, fg_c = severity_colors(sev)
        rows.append([
            Paragraph(f"<b>{sev}</b>", ParagraphStyle(
                "sev", fontName="Helvetica-Bold", fontSize=8,
                textColor=fg_c, alignment=TA_CENTER)),
            Paragraph(f.get("domain", "—"), styles["table_cell"]),
            Paragraph(f.get("finding", ""), styles["table_cell"]),
        ])
        row_styles.append(("BACKGROUND", (0, i + 1), (0, i + 1), bg_c))

    tbl = Table(rows, colWidths=[24 * mm, 30 * mm, 114 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_TEAL_DARK),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (0, 0), (0, -1), "CENTER"),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
    ] + row_styles))
    elements.append(tbl)
    elements.append(PageBreak())
    return elements


# ─── Action Plan Page ─────────────────────────────────────────────────────────
def build_action_plan(data, styles):
    elements = []
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Priority Action Plan", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=C_GOLD, spaceAfter=6 * mm))

    sections = [
        ("critical_actions",  "Critical — Act Within 1 Week",    C_CRIT_BG, C_CRIT_FG),
        ("important_actions", "Important — Act Within 1 Month",   C_HIGH_BG, C_HIGH_FG),
        ("strategic_actions", "Strategic — Plan for This Quarter",C_PANEL,   C_TEAL_DARK),
    ]

    for key, title, bg, fg in sections:
        items = data.get(key, [])
        if not items:
            continue

        header_tbl = Table([[Paragraph(f"<b>{title}</b>", ParagraphStyle(
            "ah", fontName="Helvetica-Bold", fontSize=10, textColor=fg))]],
            colWidths=[168 * mm])
        header_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER_LIGHT),
        ]))
        elements.append(header_tbl)

        for n, item in enumerate(items, 1):
            row_tbl = Table([[
                Paragraph(f"<b>{n}.</b>", ParagraphStyle(
                    "num", fontName="Helvetica-Bold", fontSize=9, textColor=fg)),
                Paragraph(item, styles["action_item"]),
            ]], colWidths=[8 * mm, 160 * mm])
            row_tbl.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("BACKGROUND",    (0, 0), (-1, -1), C_WHITE if n % 2 == 1 else C_PAGE_BG),
                ("BOX",           (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
            ]))
            elements.append(row_tbl)
        elements.append(Spacer(1, 5 * mm))

    elements.append(PageBreak())
    return elements


# ─── Methodology Page ─────────────────────────────────────────────────────────
def build_methodology(data, styles):
    elements = []
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Methodology & Audit Metadata", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=C_GOLD, spaceAfter=6 * mm))

    # Weights table
    elements.append(Paragraph("Scoring Weights", ParagraphStyle(
        "sh2", fontName="Helvetica-Bold", fontSize=10,
        textColor=C_TEAL_DARK, spaceAfter=4)))

    domains = data.get("domains", {})
    weight_rows = [[Paragraph(h, styles["table_header"])
                    for h in ["Domain", "Weight", "What It Measures"]]]

    domain_descriptions = {
        "Security & Access":       "Profiles, permission sets, sharing model, MFA, login activity",
        "Data Quality":            "Contact/Account/Lead completeness, duplicates, stale records",
        "Automation Health":       "Flows, Process Builder, Workflow Rules, Apex triggers",
        "Org Architecture":        "Governor limits, custom objects, Apex API versions, packages",
        "Test Coverage":           "Apex test coverage %, classes below 75%, test failures",
        "Naming Conventions":      "Apex class/trigger naming, field/flow/VR naming standards",
        "Orphaned Metadata":       "Inactive flows, dead validation/workflow rules, stale fields",
        "Description Completeness":"Missing help text on fields, flows, objects, validation rules",
        "Custom Field Sprawl":     "Objects with 100+ fields, stale fields, duplicate-purpose fields",
    }

    for name, info in domains.items():
        weight_rows.append([
            Paragraph(name, styles["table_cell"]),
            Paragraph(info.get("weight", "—"), styles["table_cell"]),
            Paragraph(domain_descriptions.get(name, "—"), styles["table_cell"]),
        ])

    w_tbl = Table(weight_rows, colWidths=[50 * mm, 16 * mm, 102 * mm])
    w_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("ALIGN",         (1, 0), (1, -1), "CENTER"),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
    ]))
    elements.append(w_tbl)
    elements.append(Spacer(1, 5 * mm))

    # Grade scale
    elements.append(Paragraph("Grade Scale", ParagraphStyle(
        "sh2", fontName="Helvetica-Bold", fontSize=10,
        textColor=C_TEAL_DARK, spaceAfter=4)))

    grade_rows = [
        [Paragraph(h, styles["table_header"]) for h in
         ["Score", "Grade", "Label", "Interpretation"]],
        ["90–100", "A+", "Excellent", "Production-grade org, minimal risk"],
        ["80–89",  "A",  "Strong",    "Minor improvements recommended"],
        ["70–79",  "B",  "Good",      "Some areas need attention"],
        ["60–69",  "C",  "Fair",      "Multiple risk areas identified"],
        ["50–59",  "D",  "Poor",      "Significant remediation required"],
        ["< 50",   "F",  "Critical",  "Immediate action required"],
    ]
    grade_row_styles = []
    for i, sc in enumerate([95, 85, 75, 65, 55, 45], 1):
        bg_c, fg_c = score_colors(sc)
        grade_row_styles += [("BACKGROUND", (1, i), (1, i), bg_c),
                             ("TEXTCOLOR",  (1, i), (1, i), fg_c)]
        for j in range(len(grade_rows[i])):
            grade_rows[i][j] = Paragraph(str(grade_rows[i][j]), styles["table_cell"])

    g_tbl = Table(grade_rows, colWidths=[24 * mm, 16 * mm, 24 * mm, 104 * mm])
    g_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("ALIGN",         (0, 0), (1, -1), "CENTER"),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
    ] + grade_row_styles))
    elements.append(g_tbl)
    elements.append(Spacer(1, 5 * mm))

    # Metadata
    meta = data.get("audit_metadata", {})
    if meta:
        elements.append(Paragraph("Audit Metadata", ParagraphStyle(
            "sh2", fontName="Helvetica-Bold", fontSize=10,
            textColor=C_TEAL_DARK, spaceAfter=4)))
        meta_rows = [[Paragraph("Item", styles["table_header"]),
                      Paragraph("Value", styles["table_header"])]]
        for k, v in meta.items():
            meta_rows.append([Paragraph(str(k), styles["table_cell"]),
                              Paragraph(str(v), styles["table_cell"])])
        m_tbl = Table(meta_rows, colWidths=[60 * mm, 108 * mm])
        m_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
        ]))
        elements.append(m_tbl)

    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_GOLD))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "Generated by sf-audit  ·  Powered by Claude Code  ·  anthropic.com",
        styles["footer"]))
    return elements


# ─── Main ─────────────────────────────────────────────────────────────────────
def generate_pdf(data, output_path):
    org_name   = data.get("org_name", "Salesforce Org")
    audit_date = data.get("audit_date", datetime.now().strftime("%B %d, %Y"))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=10 * mm,
        topMargin=16 * mm,
        bottomMargin=12 * mm,
        title=f"Salesforce Org Audit — {org_name}",
        author="sf-audit (Claude Code)",
        subject="Salesforce Org Health Report",
    )

    styles = build_styles()
    elements = []

    # Page 1: Cover
    elements += build_cover(data, styles)

    # Page 2: Domain Overview
    elements += build_domain_overview(data, styles)

    # Pages 3–N: One per domain
    domains = data.get("domains", {})
    findings = data.get("findings", [])
    for idx, (domain_name, info) in enumerate(domains.items()):
        elements += build_domain_page(domain_name, info, idx, findings, styles)

    # Findings, Action Plan, Methodology
    elements += build_findings(data, styles)
    elements += build_action_plan(data, styles)
    elements += build_methodology(data, styles)

    page_num = [0]
    def on_each_page(canvas, doc):
        page_num[0] += 1
        on_page(canvas, doc, org_name=org_name, audit_date=audit_date,
                is_cover=(page_num[0] == 1))

    doc.build(elements, onFirstPage=on_each_page, onLaterPages=on_each_page)
    total_pages = 2 + len(domains) + 3
    print(f"✓ PDF generated: {output_path}  ({total_pages} pages)")


# ─── Demo Data ────────────────────────────────────────────────────────────────
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
            "Security & Access": {
                "score": 63, "weight": "20%",
                "dimension_scores": {
                    "Profile Hygiene": 5, "Permission Set Sprawl": 7,
                    "Sharing Model": 8, "MFA Enforcement": 6,
                    "IP/Session Restrictions": 4, "Field-Level Security": 7,
                },
                "top_findings": [
                    "2 non-admin profiles have Modify All Data enabled",
                    "14 users inactive for 90+ days — deactivate to reduce attack surface",
                ]
            },
            "Data Quality": {
                "score": 78, "weight": "15%",
                "dimension_scores": {
                    "Contact Completeness": 8, "Account Completeness": 7,
                    "Lead Hygiene": 6, "Duplicate Rule Coverage": 9,
                    "Opportunity Hygiene": 7,
                },
                "top_findings": [
                    "Contact Email null rate is 18% (3,210 contacts unreachable)",
                ]
            },
            "Automation Health": {
                "score": 69, "weight": "15%",
                "dimension_scores": {
                    "Flow Health": 7, "Process Builder Debt": 5,
                    "Workflow Rules": 4, "Trigger Hygiene": 8,
                    "Validation Quality": 8,
                },
                "top_findings": [
                    "6 active Workflow Rules — retire immediately",
                    "3 active Process Builder processes — migrate to Flow",
                ]
            },
            "Org Architecture": {
                "score": 84, "weight": "12%",
                "dimension_scores": {
                    "Object/Field Sprawl": 8, "Governor Limits": 9,
                    "Apex API Version Debt": 7, "Package Health": 9,
                    "Custom Settings vs CMDT": 6,
                },
                "top_findings": [
                    "8 Apex classes still on API v45 — update to v62",
                ]
            },
            "Test Coverage": {
                "score": 73, "weight": "8%",
                "dimension_scores": {
                    "Org-Wide Coverage %": 8, "Classes Below 75%": 6,
                    "Test Class Quality": 7, "Trigger Coverage": 8,
                },
                "top_findings": [
                    "4 Apex classes below 75% coverage threshold",
                ]
            },
            "Naming Conventions": {
                "score": 61, "weight": "8%",
                "dimension_scores": {
                    "Apex Class Naming": 5, "Apex Trigger Naming": 7,
                    "Custom Field Naming": 6, "Flow Naming": 5,
                    "Validation Rule Naming": 7,
                },
                "top_findings": [
                    "32% of Apex classes missing type suffix (_CTRL, _SERVICE, _TEST)",
                    "14 flows have single-word or non-descriptive names",
                ]
            },
            "Orphaned Metadata": {
                "score": 72, "weight": "8%",
                "dimension_scores": {
                    "Inactive Flows": 8, "Dead Validation Rules": 7,
                    "Deactivated Workflow Rules": 6, "Stale Custom Fields": 7,
                },
                "top_findings": [
                    "12 inactive flows still present in org",
                    "5 deactivated workflow rules should be deleted",
                ]
            },
            "Description Completeness": {
                "score": 54, "weight": "7%",
                "dimension_scores": {
                    "Custom Field Help Text": 4, "Flow Descriptions": 5,
                    "Validation Rule Descriptions": 6, "Object Descriptions": 5,
                    "Apex Class Doc Comments": 6,
                },
                "top_findings": [
                    "62% of custom fields missing InlineHelpText",
                    "38% of active flows have no description",
                ]
            },
            "Custom Field Sprawl": {
                "score": 80, "weight": "7%",
                "dimension_scores": {
                    "Objects ≥100 Fields": 8, "Objects 50–99 Fields": 7,
                    "Stale Fields (>730 days)": 8, "Duplicate-Purpose Fields": 8,
                },
                "top_findings": [
                    "1 object (Account) at 127 custom fields — review for cleanup",
                ]
            },
        },
        "findings": [
            {"severity": "Critical", "domain": "Security & Access",
             "finding": "2 non-System Administrator profiles have PermissionsModifyAllData = true."},
            {"severity": "Critical", "domain": "Automation Health",
             "finding": "6 active Workflow Rules detected — retired technology, no Salesforce bug fixes after Winter '23."},
            {"severity": "High", "domain": "Security & Access",
             "finding": "14 active users have not logged in for 90+ days — deactivate to reduce attack surface."},
            {"severity": "High", "domain": "Description Completeness",
             "finding": "62% of custom fields are missing InlineHelpText — users cannot understand field purpose."},
            {"severity": "High", "domain": "Naming Conventions",
             "finding": "32% of Apex classes are missing type suffix (_CTRL, _SERVICE, _TEST, _HANDLER)."},
            {"severity": "Medium", "domain": "Data Quality",
             "finding": "Contact Email null rate is 18% (3,210 of 17,830 contacts unreachable by email)."},
            {"severity": "Medium", "domain": "Automation Health",
             "finding": "3 active Process Builder processes — migrate to Flow as part of automation modernization."},
            {"severity": "Medium", "domain": "Test Coverage",
             "finding": "4 Apex classes below 75% coverage: OrderSync (48%), PricingHelper (52%), LeadRouter (61%), InvoiceService (64%)."},
            {"severity": "Low", "domain": "Org Architecture",
             "finding": "8 Apex classes on API v45 or below — review for deprecated method usage."},
        ],
        "critical_actions": [
            "Remove PermissionsModifyAllData from both non-admin profiles. Use Permission Sets for any legitimate elevated-access requirements.",
            "Migrate all 6 Workflow Rules to Record-Triggered Flows. Workflow Rules are retired — no bug fixes or future investment from Salesforce.",
        ],
        "important_actions": [
            "Deactivate 14 users with no login in 90+ days — reduces attack surface and frees licenses.",
            "Add InlineHelpText to all custom fields missing descriptions — start with the highest-traffic objects.",
            "Add type suffixes to the 32% of Apex classes that are missing them (_CTRL, _SERVICE, _HANDLER, _TEST).",
            "Add descriptions to all 38% of active flows currently undocumented.",
        ],
        "strategic_actions": [
            "Migrate 3 Process Builder processes to Flow as part of the Q3 automation modernization initiative.",
            "Run a quarterly naming convention cleanup sprint targeting the worst-offending metadata types.",
            "Establish a definition-of-done checklist requiring InlineHelpText and a Description on all new metadata.",
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
        with open(sys.argv[1], "r") as f:
            data = json.load(f)
        output_file = sys.argv[2] if len(sys.argv) >= 3 else "SF-AUDIT-REPORT.pdf"
    else:
        print("No input file provided — generating demo report.")
        data = demo_data()
        output_file = "SF-AUDIT-REPORT-DEMO.pdf"

    generate_pdf(data, output_file)
