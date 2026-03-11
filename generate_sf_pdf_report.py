#!/usr/bin/env python3
"""
Salesforce Org Audit — PDF Report Generator
Generates a clean, professional PDF from SF audit JSON data.
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
    from reportlab.graphics.shapes import Drawing, Circle, Arc, Rect, String, Line
    from reportlab.graphics import renderPDF
    from reportlab.graphics.charts.barcharts import HorizontalBarChart
    from reportlab.graphics.shapes import Drawing
except ImportError:
    print("ERROR: reportlab is required. Install with: pip3 install reportlab")
    sys.exit(1)


# ─── Color Palette (light & clean) ────────────────────────────────────────────
C_WHITE        = HexColor("#FFFFFF")
C_PAGE_BG      = HexColor("#F8FAFC")   # near-white page background
C_PANEL        = HexColor("#EFF6FF")   # light blue panel backgrounds
C_PANEL_ALT    = HexColor("#F0FDF4")   # light green panel (for passing scores)
C_BORDER       = HexColor("#DBEAFE")   # soft blue border
C_BORDER_LIGHT = HexColor("#E2E8F0")   # very light gray border

C_PRIMARY      = HexColor("#2563EB")   # blue — headers, accents
C_PRIMARY_DARK = HexColor("#1E40AF")   # darker blue — cover title
C_SECONDARY    = HexColor("#0EA5E9")   # sky blue — section accents

C_TEXT_DARK    = HexColor("#0F172A")   # near-black — main body text
C_TEXT_MID     = HexColor("#334155")   # slate — secondary text
C_TEXT_LIGHT   = HexColor("#64748B")   # muted — labels, captions
C_TEXT_FAINT   = HexColor("#94A3B8")   # very light — watermarks, footers

# Score/severity colors — light fills with matching text
C_SCORE_A_BG   = HexColor("#DCFCE7")   # light green bg (A grade)
C_SCORE_A_FG   = HexColor("#15803D")   # green text
C_SCORE_B_BG   = HexColor("#DBEAFE")   # light blue bg (B grade)
C_SCORE_B_FG   = HexColor("#1D4ED8")   # blue text
C_SCORE_C_BG   = HexColor("#FEF9C3")   # light yellow bg (C grade)
C_SCORE_C_FG   = HexColor("#A16207")   # amber text
C_SCORE_D_BG   = HexColor("#FEE2E2")   # light red bg (D/F grade)
C_SCORE_D_FG   = HexColor("#B91C1C")   # red text

C_CRITICAL_BG  = HexColor("#FEE2E2")
C_CRITICAL_FG  = HexColor("#B91C1C")
C_HIGH_BG      = HexColor("#FFEDD5")
C_HIGH_FG      = HexColor("#C2410C")
C_MEDIUM_BG    = HexColor("#FEF9C3")
C_MEDIUM_FG    = HexColor("#A16207")
C_LOW_BG       = HexColor("#DCFCE7")
C_LOW_FG       = HexColor("#15803D")

C_COVER_BG     = HexColor("#EFF6FF")   # cover page light blue
C_COVER_STRIP  = HexColor("#2563EB")   # top strip
C_FOOTER_LINE  = HexColor("#BFDBFE")   # footer rule


# ─── Helpers ──────────────────────────────────────────────────────────────────
def score_colors(score):
    """Return (bg, fg) color pair for a given 0–100 score."""
    if score >= 90:   return C_SCORE_A_BG, C_SCORE_A_FG
    if score >= 80:   return C_SCORE_A_BG, C_SCORE_A_FG
    if score >= 70:   return C_SCORE_B_BG, C_SCORE_B_FG
    if score >= 60:   return C_SCORE_C_BG, C_SCORE_C_FG
    if score >= 50:   return C_SCORE_D_BG, C_SCORE_D_FG
    return C_SCORE_D_BG, C_SCORE_D_FG


def grade_from_score(score):
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"


def grade_label(grade):
    labels = {
        "A+": "Excellent",
        "A":  "Strong",
        "B":  "Good",
        "C":  "Fair",
        "D":  "Poor",
        "F":  "Critical",
    }
    return labels.get(grade, "")


def severity_colors(severity):
    s = severity.lower()
    if "critical" in s: return C_CRITICAL_BG, C_CRITICAL_FG
    if "high"     in s: return C_HIGH_BG,     C_HIGH_FG
    if "medium"   in s: return C_MEDIUM_BG,   C_MEDIUM_FG
    return C_LOW_BG, C_LOW_FG


# ─── Score Gauge (circular arc) ───────────────────────────────────────────────
def build_score_gauge(score, size=110):
    """Draw a clean circular score gauge with light styling."""
    d = Drawing(size, size)
    cx, cy, r = size / 2, size / 2, size * 0.42

    # Background ring (light gray track)
    track = Arc(cx - r, cy - r, cx + r, cy + r, startAngle=0, extent=360)
    track.strokeColor = C_BORDER_LIGHT
    track.strokeWidth = size * 0.07
    track.fillColor = None
    d.add(track)

    # Score arc — sweeps from 90° (top) clockwise
    pct = max(0, min(score, 100)) / 100
    extent = pct * 360
    if extent > 0:
        bg_color, fg_color = score_colors(score)
        arc = Arc(cx - r, cy - r, cx + r, cy + r,
                  startAngle=90, extent=-extent)
        arc.strokeColor = fg_color
        arc.strokeWidth = size * 0.07
        arc.fillColor = None
        d.add(arc)

    # Center circle (white fill)
    inner_r = r * 0.62
    center_bg = Circle(cx, cy, inner_r)
    center_bg.fillColor = C_WHITE
    center_bg.strokeColor = C_BORDER_LIGHT
    center_bg.strokeWidth = 0.5
    d.add(center_bg)

    # Score number
    _, fg = score_colors(score)
    score_text = String(cx, cy + size * 0.04, str(score),
                        fontSize=size * 0.20, fontName="Helvetica-Bold",
                        fillColor=fg, textAnchor="middle")
    d.add(score_text)

    # "/100" label
    label = String(cx, cy - size * 0.10, "/100",
                   fontSize=size * 0.09, fontName="Helvetica",
                   fillColor=C_TEXT_LIGHT, textAnchor="middle")
    d.add(label)

    return d


# ─── Styles ───────────────────────────────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=C_PRIMARY_DARK,
            spaceAfter=4,
            leading=32,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            fontName="Helvetica",
            fontSize=12,
            textColor=C_TEXT_MID,
            spaceAfter=2,
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=C_PRIMARY_DARK,
            spaceBefore=14,
            spaceAfter=6,
            leading=18,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=C_TEXT_MID,
            leading=14,
            spaceAfter=4,
        ),
        "body_small": ParagraphStyle(
            "body_small",
            fontName="Helvetica",
            fontSize=8,
            textColor=C_TEXT_LIGHT,
            leading=12,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=C_TEXT_LIGHT,
            leading=11,
        ),
        "executive": ParagraphStyle(
            "executive",
            fontName="Helvetica",
            fontSize=10,
            textColor=C_TEXT_MID,
            leading=16,
            spaceAfter=6,
            leftIndent=10,
            rightIndent=10,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=C_PRIMARY_DARK,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName="Helvetica",
            fontSize=8,
            textColor=C_TEXT_MID,
            leading=12,
        ),
        "action_item": ParagraphStyle(
            "action_item",
            fontName="Helvetica",
            fontSize=9,
            textColor=C_TEXT_MID,
            leading=13,
            leftIndent=10,
            bulletIndent=2,
            spaceAfter=3,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7,
            textColor=C_TEXT_FAINT,
            alignment=TA_CENTER,
        ),
    }
    return styles


# ─── Page template callbacks ───────────────────────────────────────────────────
def on_page(canvas, doc, org_name="", audit_date="", is_cover=False):
    W, H = A4
    canvas.saveState()

    if is_cover:
        # Top color strip
        canvas.setFillColor(C_COVER_STRIP)
        canvas.rect(0, H - 8 * mm, W, 8 * mm, stroke=0, fill=1)
        # Bottom strip
        canvas.setFillColor(C_COVER_STRIP)
        canvas.rect(0, 0, W, 4 * mm, stroke=0, fill=1)
    else:
        # Header line
        canvas.setStrokeColor(C_FOOTER_LINE)
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, H - 14 * mm, W - 15 * mm, H - 14 * mm)

        # Header text
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(C_TEXT_FAINT)
        canvas.drawString(15 * mm, H - 11 * mm, f"Salesforce Org Audit  |  {org_name}")
        canvas.drawRightString(W - 15 * mm, H - 11 * mm, audit_date)

        # Footer line
        canvas.line(15 * mm, 14 * mm, W - 15 * mm, 14 * mm)

        # Page number
        canvas.drawCentredString(W / 2, 9 * mm, f"Page {doc.page}")
        canvas.drawString(15 * mm, 9 * mm, "SF Audit Report")
        canvas.drawRightString(W - 15 * mm, 9 * mm, "Powered by Claude Code")

    canvas.restoreState()


# ─── Page builders ────────────────────────────────────────────────────────────

def build_cover(data, styles):
    """Page 1: Cover with gauge, grade, org info, executive summary."""
    elements = []
    W, H = A4
    org   = data.get("org_name", "Salesforce Org")
    user  = data.get("org_username", "")
    ed    = data.get("org_edition", "")
    date  = data.get("audit_date", datetime.now().strftime("%B %d, %Y"))
    score = int(data.get("overall_score", 0))
    grade = data.get("grade") or grade_from_score(score)
    summary = data.get("executive_summary", "")

    elements.append(Spacer(1, 22 * mm))

    # Org title
    elements.append(Paragraph("Salesforce Org Health Audit", styles["cover_title"]))
    elements.append(Paragraph(f"{org}", ParagraphStyle(
        "org_name", fontName="Helvetica-Bold", fontSize=16,
        textColor=C_PRIMARY, spaceAfter=2)))
    if user:
        elements.append(Paragraph(user, styles["cover_subtitle"]))
    if ed:
        elements.append(Paragraph(f"{ed}  ·  {date}", styles["cover_subtitle"]))

    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=C_FOOTER_LINE, spaceAfter=8 * mm))

    # Score gauge + grade side by side
    gauge = build_score_gauge(score, size=120)
    bg_c, fg_c = score_colors(score)

    grade_block = [
        [Paragraph(f'<font color="#{fg_c.hexval()[2:].upper()}" size="36"><b>{grade}</b></font>', ParagraphStyle(
            "g", fontName="Helvetica-Bold", fontSize=36,
            textColor=fg_c, alignment=TA_CENTER))],
        [Paragraph(grade_label(grade), ParagraphStyle(
            "gl", fontName="Helvetica", fontSize=11,
            textColor=fg_c, alignment=TA_CENTER))],
        [Spacer(1, 4)],
        [Paragraph("Org Health Score", ParagraphStyle(
            "gll", fontName="Helvetica", fontSize=8,
            textColor=C_TEXT_LIGHT, alignment=TA_CENTER))],
    ]

    grade_tbl = Table(grade_block, colWidths=[60 * mm])
    grade_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, -1), bg_c),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    score_row = Table([[gauge, grade_tbl]], colWidths=[70 * mm, 70 * mm])
    score_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(score_row)
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=C_FOOTER_LINE, spaceAfter=6 * mm))

    # Executive summary panel
    if summary:
        elements.append(Paragraph("Executive Summary", styles["section_heading"]))
        panel_data = [[Paragraph(summary, styles["executive"])]]
        panel = Table(panel_data, colWidths=[170 * mm])
        panel.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_PANEL),
            ("ROUNDEDCORNERS", [6]),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
            ("BOX", (0, 0), (-1, -1), 0.5, C_BORDER),
        ]))
        elements.append(panel)

    elements.append(PageBreak())
    return elements


def build_domain_scores(data, styles):
    """Page 2: Domain score breakdown — bar chart + table."""
    elements = []
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Domain Score Breakdown", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_FOOTER_LINE, spaceAfter=6 * mm))

    domains = data.get("domains", {})
    if not domains:
        elements.append(Paragraph("No domain data available.", styles["body"]))
        elements.append(PageBreak())
        return elements

    # Bar chart
    d = Drawing(170 * mm, len(domains) * 14 * mm + 10 * mm)
    chart = HorizontalBarChart()
    chart.x = 48 * mm
    chart.y = 4 * mm
    chart.width = 115 * mm
    chart.height = len(domains) * 13 * mm

    scores = [int(v.get("score", 0)) for v in domains.values()]
    chart.data = [scores]
    chart.reversePlotOrder = 1

    chart.bars[0].fillColor = C_PRIMARY
    chart.bars[0].strokeColor = None

    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 20
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = C_TEXT_LIGHT
    chart.valueAxis.gridStrokeColor = C_BORDER_LIGHT
    chart.valueAxis.gridStrokeWidth = 0.3

    chart.categoryAxis.categoryNames = list(domains.keys())
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = C_TEXT_MID
    chart.categoryAxis.labels.dx = -4
    chart.categoryAxis.gridStrokeColor = None
    chart.categoryAxis.strokeColor = C_BORDER_LIGHT

    chart.barLabelFormat = '%d'
    chart.barLabels.fontName = "Helvetica-Bold"
    chart.barLabels.fontSize = 7.5
    chart.barLabels.fillColor = C_TEXT_DARK
    chart.barLabels.nudge = 6

    d.add(chart)
    elements.append(d)
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
        status_bg = C_SCORE_A_BG if sc >= 70 else (C_SCORE_C_BG if sc >= 50 else C_SCORE_D_BG)

        row = [
            Paragraph(domain, styles["table_cell"]),
            Paragraph(wt, styles["table_cell"]),
            Paragraph(f"<b>{sc}/100</b>", styles["table_cell"]),
            Paragraph(f"<b>{gr}</b>", styles["table_cell"]),
            Paragraph(status, styles["table_cell"]),
        ]
        rows.append(row)

        ri = i + 1
        row_styles += [
            ("BACKGROUND", (2, ri), (3, ri), bg_c),
            ("TEXTCOLOR",  (2, ri), (3, ri), fg_c),
            ("BACKGROUND", (4, ri), (4, ri), status_bg),
        ]

    col_w = [72 * mm, 18 * mm, 28 * mm, 20 * mm, 24 * mm]
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    base_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_PRIMARY_DARK),
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
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER_LIGHT),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
    ]
    tbl.setStyle(TableStyle(base_style + row_styles))
    elements.append(tbl)
    elements.append(PageBreak())
    return elements


def build_findings(data, styles):
    """Page 3: Key findings table, severity-coded."""
    elements = []
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Key Findings", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_FOOTER_LINE, spaceAfter=6 * mm))

    findings = data.get("findings", [])
    if not findings:
        elements.append(Paragraph("No findings recorded.", styles["body"]))
        elements.append(PageBreak())
        return elements

    # Sort: Critical → High → Medium → Low
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
        dom = f.get("domain", "—")
        txt = f.get("finding", "")
        bg_c, fg_c = severity_colors(sev)

        row = [
            Paragraph(f"<b>{sev}</b>", ParagraphStyle(
                "sev", fontName="Helvetica-Bold", fontSize=8,
                textColor=fg_c, alignment=TA_CENTER)),
            Paragraph(dom, styles["table_cell"]),
            Paragraph(txt, styles["table_cell"]),
        ]
        rows.append(row)
        ri = i + 1
        row_styles.append(("BACKGROUND", (0, ri), (0, ri), bg_c))

    col_w = [24 * mm, 30 * mm, 114 * mm]
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_PRIMARY_DARK),
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
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER_LIGHT),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
    ] + row_styles))
    elements.append(tbl)
    elements.append(PageBreak())
    return elements


def build_action_plan(data, styles):
    """Page 4: Priority action plan — Critical / Important / Strategic."""
    elements = []
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Priority Action Plan", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_FOOTER_LINE, spaceAfter=6 * mm))

    sections = [
        ("critical_actions",  "Critical — Act Within 1 Week",
         C_CRITICAL_BG, C_CRITICAL_FG),
        ("important_actions", "Important — Act Within 1 Month",
         C_HIGH_BG,     C_HIGH_FG),
        ("strategic_actions", "Strategic — Plan for This Quarter",
         C_PANEL,       C_PRIMARY_DARK),
    ]

    for key, title, bg, fg in sections:
        items = data.get(key, [])
        if not items:
            continue

        # Section header panel
        header_data = [[Paragraph(f"<b>{title}</b>", ParagraphStyle(
            "ah", fontName="Helvetica-Bold", fontSize=10,
            textColor=fg))]]
        header_tbl = Table(header_data, colWidths=[170 * mm])
        header_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER_LIGHT),
        ]))
        elements.append(header_tbl)

        # Items
        for n, item in enumerate(items, 1):
            row = [[
                Paragraph(f"<b>{n}.</b>", ParagraphStyle(
                    "num", fontName="Helvetica-Bold", fontSize=9,
                    textColor=fg)),
                Paragraph(item, styles["action_item"]),
            ]]
            item_tbl = Table(row, colWidths=[8 * mm, 162 * mm])
            item_tbl.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("BACKGROUND",    (0, 0), (-1, -1), C_WHITE if n % 2 == 1 else C_PAGE_BG),
                ("BOX",           (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
            ]))
            elements.append(item_tbl)

        elements.append(Spacer(1, 5 * mm))

    elements.append(PageBreak())
    return elements


def build_methodology(data, styles):
    """Page 5: Scoring methodology, grade scale, audit metadata."""
    elements = []
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Methodology & Audit Metadata", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_FOOTER_LINE, spaceAfter=6 * mm))

    # Scoring weights table
    elements.append(Paragraph("Scoring Weights", ParagraphStyle(
        "sh2", fontName="Helvetica-Bold", fontSize=10,
        textColor=C_TEXT_DARK, spaceAfter=4)))

    weight_rows = [
        [Paragraph("Domain", styles["table_header"]),
         Paragraph("Weight", styles["table_header"]),
         Paragraph("What It Measures", styles["table_header"])],
        ["Security & Access",   "30%", "Profiles, permission sets, sharing model, MFA, login activity"],
        ["Data Quality",        "20%", "Contact/Account/Lead completeness, duplicates, stale records"],
        ["Automation Health",   "20%", "Flows, Process Builder, Workflow Rules, Apex triggers"],
        ["Org Architecture",    "15%", "Governor limits, custom objects, Apex API versions, packages"],
        ["Test Coverage",       "15%", "Apex test coverage %, classes below 75%, test failures"],
    ]

    for i in range(1, len(weight_rows)):
        for j in range(len(weight_rows[i])):
            weight_rows[i][j] = Paragraph(str(weight_rows[i][j]), styles["table_cell"])

    w_tbl = Table(weight_rows, colWidths=[50 * mm, 18 * mm, 102 * mm])
    w_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("ALIGN",         (1, 0), (1, -1), "CENTER"),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER_LIGHT),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
    ]))
    elements.append(w_tbl)
    elements.append(Spacer(1, 5 * mm))

    # Grade scale table
    elements.append(Paragraph("Grade Scale", ParagraphStyle(
        "sh2", fontName="Helvetica-Bold", fontSize=10,
        textColor=C_TEXT_DARK, spaceAfter=4)))

    grade_rows = [
        [Paragraph(h, styles["table_header"]) for h in
         ["Score Range", "Grade", "Label", "Interpretation"]],
        ["90–100", "A+", "Excellent", "Production-grade org, minimal risk"],
        ["80–89",  "A",  "Strong",    "Minor improvements recommended"],
        ["70–79",  "B",  "Good",      "Some areas need attention"],
        ["60–69",  "C",  "Fair",      "Multiple risk areas identified"],
        ["50–59",  "D",  "Poor",      "Significant remediation required"],
        ["< 50",   "F",  "Critical",  "Immediate action required"],
    ]

    grade_row_styles = []
    grade_scores = [95, 85, 75, 65, 55, 45]
    for i, sc in enumerate(grade_scores, 1):
        bg_c, fg_c = score_colors(sc)
        grade_row_styles += [
            ("BACKGROUND", (1, i), (1, i), bg_c),
            ("TEXTCOLOR",  (1, i), (1, i), fg_c),
        ]
        for j in range(len(grade_rows[i])):
            grade_rows[i][j] = Paragraph(str(grade_rows[i][j]), styles["table_cell"])

    g_tbl = Table(grade_rows, colWidths=[28 * mm, 18 * mm, 26 * mm, 98 * mm])
    g_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("ALIGN",         (0, 0), (1, -1), "CENTER"),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER_LIGHT),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
    ] + grade_row_styles))
    elements.append(g_tbl)
    elements.append(Spacer(1, 5 * mm))

    # Audit metadata
    meta = data.get("audit_metadata", {})
    if meta:
        elements.append(Paragraph("Audit Metadata", ParagraphStyle(
            "sh2", fontName="Helvetica-Bold", fontSize=10,
            textColor=C_TEXT_DARK, spaceAfter=4)))

        meta_rows = [[Paragraph("Item", styles["table_header"]),
                      Paragraph("Value", styles["table_header"])]]
        for k, v in meta.items():
            meta_rows.append([
                Paragraph(str(k), styles["table_cell"]),
                Paragraph(str(v), styles["table_cell"]),
            ])

        m_tbl = Table(meta_rows, colWidths=[60 * mm, 110 * mm])
        m_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_PANEL),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_PAGE_BG]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER_LIGHT),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER_LIGHT),
        ]))
        elements.append(m_tbl)

    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_FOOTER_LINE))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "Generated by sf-audit · Powered by Claude Code · anthropic.com",
        styles["footer"]))
    return elements


# ─── Main ─────────────────────────────────────────────────────────────────────
def generate_pdf(data, output_path):
    W, H = A4
    org_name   = data.get("org_name", "Salesforce Org")
    audit_date = data.get("audit_date", datetime.now().strftime("%B %d, %Y"))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Salesforce Org Audit — {org_name}",
        author="sf-audit (Claude Code)",
        subject="Salesforce Org Health Report",
    )

    styles = build_styles()
    elements = []

    # Build all pages
    elements += build_cover(data, styles)
    elements += build_domain_scores(data, styles)
    elements += build_findings(data, styles)
    elements += build_action_plan(data, styles)
    elements += build_methodology(data, styles)

    page_num = [0]

    def on_each_page(canvas, doc):
        page_num[0] += 1
        on_page(canvas, doc,
                org_name=org_name,
                audit_date=audit_date,
                is_cover=(page_num[0] == 1))

    doc.build(elements, onFirstPage=on_each_page, onLaterPages=on_each_page)
    print(f"✓ PDF generated: {output_path}")


def demo_data():
    return {
        "org_name": "Acme Corporation",
        "org_username": "admin@acme.salesforce.com",
        "org_edition": "Enterprise Edition",
        "audit_date": datetime.now().strftime("%B %d, %Y"),
        "overall_score": 72,
        "grade": "B",
        "executive_summary": (
            "Acme's Salesforce org is in reasonably good health with a composite score of 72/100 (Grade B). "
            "The primary risk is in Security & Access — three non-administrator profiles have Modify All Data "
            "permissions enabled, creating unnecessary data exposure. On the positive side, org architecture "
            "is strong with governor limits well within thresholds. Immediate priorities are: remove elevated "
            "permissions from non-admin profiles, migrate 8 active Workflow Rules to Flows, and add test "
            "coverage to 5 Apex classes currently below the 75% deployment threshold."
        ),
        "domains": {
            "Security & Access":  {"score": 61, "weight": "30%"},
            "Data Quality":       {"score": 78, "weight": "20%"},
            "Automation Health":  {"score": 70, "weight": "20%"},
            "Org Architecture":   {"score": 85, "weight": "15%"},
            "Test Coverage":      {"score": 68, "weight": "15%"},
        },
        "findings": [
            {"severity": "Critical", "domain": "Security",    "finding": "3 non-System Administrator profiles have PermissionsModifyAllData = true: Sales Manager, Support Lead, Operations Admin."},
            {"severity": "Critical", "domain": "Automation",  "finding": "8 active Workflow Rules detected — this technology is retired. No Salesforce investment or bug fixes after Winter '23."},
            {"severity": "High",     "domain": "Security",    "finding": "14 active users have not logged in for 90+ days. These accounts should be deactivated to reduce attack surface."},
            {"severity": "High",     "domain": "Data Quality","finding": "Contact Email null rate is 23% (4,821 of 20,960 contacts). These contacts are unreachable via email campaigns."},
            {"severity": "High",     "domain": "Test Coverage","finding": "5 Apex classes are below the 75% coverage threshold: InvoiceService (61%), LeadRouter (58%), CaseEscalation (52%), PricingHelper (49%), OrderSync (44%)."},
            {"severity": "Medium",   "domain": "Automation",  "finding": "AccountTrigger and ContactTrigger have no corresponding handler class. This pattern risks execution order conflicts and is difficult to test."},
            {"severity": "Medium",   "domain": "Architecture","finding": "12 Apex classes are on API version v45 or below — these were last updated in 2017–2018 and should be reviewed for deprecated methods."},
            {"severity": "Low",      "domain": "Data Quality","finding": "3,210 open Opportunities have a CloseDate in the past. Pipeline reporting is inaccurate until these are updated or closed."},
        ],
        "critical_actions": [
            "Remove PermissionsModifyAllData from Sales Manager, Support Lead, and Operations Admin profiles. Use Permission Sets for any legitimate elevated access needs instead.",
            "Migrate all 8 active Workflow Rules to Record-Triggered Flows immediately. Workflow Rules receive no bug fixes and will eventually be retired from all orgs.",
        ],
        "important_actions": [
            "Deactivate 14 users with no login in 90+ days: [list available in SF-SECURITY.md]. This reduces your org's attack surface and frees user licenses.",
            "Add Apex tests for the 5 classes below 75% coverage. Start with OrderSync (44%) and PricingHelper (49%) as these are the furthest below threshold.",
            "Implement trigger handler pattern for AccountTrigger and ContactTrigger. Create AccountTriggerHandler and ContactTriggerHandler classes.",
        ],
        "strategic_actions": [
            "Update all 12 Apex classes on API v45 or below to the current API version (v62) as part of quarterly tech debt cleanup.",
            "Implement a data quality Flow or validation rule to make Contact Email required at point of entry.",
            "Evaluate the 5 active Process Builder processes for migration to Flow as part of the broader automation modernization project.",
        ],
        "audit_metadata": {
            "Queries Executed": "47",
            "API Version": "v62.0",
            "Execution Mode": "Parallel (5 agents)",
            "Generated": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
            "Tool": "sf-audit (Claude Code)",
        },
    }


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        input_file  = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) >= 3 else "SF-AUDIT-REPORT.pdf"
        with open(input_file, "r") as f:
            data = json.load(f)
    else:
        print("No input file provided — generating demo report.")
        data        = demo_data()
        output_file = "SF-AUDIT-REPORT-DEMO.pdf"

    generate_pdf(data, output_file)
