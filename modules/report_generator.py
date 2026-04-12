"""
Módulo de Reportes PDF — ADIC Platform Procaps
Genera reportes ejecutivos con identidad corporativa azul Procaps.
"""

from __future__ import annotations

import io
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Paleta corporativa Procaps ────────────────────────────────────────────────
C_BLUE_DARK  = colors.HexColor("#003087")   # Azul primario Procaps
C_BLUE_MED   = colors.HexColor("#0057D8")   # Azul secundario
C_BLUE_LIGHT = colors.HexColor("#00BFFF")   # Acento
C_WHITE      = colors.HexColor("#FFFFFF")
C_GRAY_BG    = colors.HexColor("#F4F6FA")
C_GRAY_LIGHT = colors.HexColor("#E2E8F0")
C_TEXT       = colors.HexColor("#1E293B")
C_MUTED      = colors.HexColor("#64748B")
C_SUCCESS    = colors.HexColor("#16A34A")
C_WARNING    = colors.HexColor("#D97706")
C_DANGER     = colors.HexColor("#DC2626")


def _quality_color(score: float) -> colors.HexColor:
    if score >= 90:
        return C_SUCCESS
    elif score >= 75:
        return C_BLUE_MED
    elif score >= 55:
        return C_WARNING
    return C_DANGER


def generate_pdf_report(
    df: pd.DataFrame,
    source_name: str,
    quality_score: float,
    narrative: str | None = None,
    title: str = "Reporte Ejecutivo",
    report_type: str = "General",
) -> bytes:
    """Genera reporte PDF con identidad Procaps."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2.2*cm, leftMargin=2.2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # Estilos
    s_title = ParagraphStyle("T", fontSize=20, textColor=C_WHITE,
                              fontName="Helvetica-Bold", spaceAfter=2, alignment=TA_LEFT)
    s_h2 = ParagraphStyle("H2", fontSize=12, textColor=C_BLUE_DARK,
                           fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=6)
    s_body = ParagraphStyle("B", fontSize=9, textColor=C_TEXT,
                             fontName="Helvetica", leading=14)
    s_muted = ParagraphStyle("M", fontSize=8, textColor=C_MUTED, fontName="Helvetica")
    s_center = ParagraphStyle("C", parent=s_body, alignment=TA_CENTER)

    # ── Header con logo visual ────────────────────────────────────────────────
    header_data = [[
        Paragraph("<b>💊 ADIC Platform · Procaps</b>", s_title),
        Paragraph(
            f"<font color='#94A3B8'>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>"
            f"Tipo: {report_type}</font>",
            s_muted,
        ),
    ]]
    header_table = Table(header_data, colWidths=["65%", "35%"])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_BLUE_DARK),
        ("ROWPADDING", (0, 0), (-1, -1), 16),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    # Título del reporte
    story.append(Paragraph(title, ParagraphStyle(
        "RT", fontSize=15, textColor=C_BLUE_DARK,
        fontName="Helvetica-Bold", spaceAfter=4,
    )))
    story.append(Paragraph(
        f"Fuente: <b>{source_name}</b> &nbsp;|&nbsp; "
        f"Registros: <b>{len(df):,}</b> &nbsp;|&nbsp; "
        f"Columnas: <b>{len(df.columns)}</b> &nbsp;|&nbsp; "
        f"Tipo: <b>{report_type}</b>",
        s_muted,
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=C_BLUE_DARK))
    story.append(Spacer(1, 0.4*cm))

    # ── Data Quality Score ────────────────────────────────────────────────────
    story.append(Paragraph("Calidad de Datos", s_h2))
    qc = _quality_color(quality_score)
    qs_label = ("Excelente" if quality_score >= 90 else
                "Bueno" if quality_score >= 75 else
                "Aceptable" if quality_score >= 55 else "Crítico")

    qs_data = [[
        Paragraph(f"<b>{quality_score:.0f}/100</b>", ParagraphStyle(
            "QS", fontSize=26, textColor=qc, alignment=TA_CENTER, fontName="Helvetica-Bold",
        )),
        Paragraph(
            f"<b>{qs_label}</b> — Score de calidad basado en completitud ({quality_score:.0f}%), "
            f"unicidad y consistencia de los datos cargados. "
            f"{'Los datos son confiables para análisis.' if quality_score >= 75 else 'Se recomienda revisar la calidad antes de tomar decisiones.'}",
            s_body,
        ),
    ]]
    qs_table = Table(qs_data, colWidths=["22%", "78%"])
    qs_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_GRAY_BG),
        ("ROWPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, -1), 1, C_GRAY_LIGHT),
    ]))
    story.append(qs_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Narrativa IA ─────────────────────────────────────────────────────────
    if narrative:
        story.append(Paragraph("Análisis Ejecutivo (Asistente IA)", s_h2))
        # Limpiar markdown para ReportLab
        clean = (narrative
                 .replace("## 📊 ¿Qué muestran los datos?", "<b>¿Qué muestran los datos?</b><br/>")
                 .replace("## 🔍 Hallazgos principales", "<br/><b>Hallazgos principales</b><br/>")
                 .replace("## ⚠️ Puntos de atención", "<br/><b>Puntos de atención</b><br/>")
                 .replace("## ✅ Recomendación ejecutiva", "<br/><b>Recomendación ejecutiva</b><br/>")
                 .replace("**", "")
                 .replace("---", "")
                 .replace("• ", "· ")
                 .replace("\n\n", "<br/><br/>")
                 .replace("\n", "<br/>"))
        story.append(Paragraph(clean, s_body))
        story.append(Spacer(1, 0.4*cm))

    # ── Estadísticas descriptivas ─────────────────────────────────────────────
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        story.append(Paragraph("Estadísticas Descriptivas", s_h2))
        cols_show = num_cols[:7]
        stats = df[cols_show].describe().round(1)
        labels = {"count": "N", "mean": "Promedio", "std": "Desv. Est.",
                  "min": "Mínimo", "25%": "Q1 (25%)", "50%": "Mediana",
                  "75%": "Q3 (75%)", "max": "Máximo"}
        header_row = [""] + [c[:16] for c in cols_show]
        rows = [header_row]
        for idx in stats.index:
            row = [labels.get(idx, idx)]
            for col in cols_show:
                val = stats.loc[idx, col]
                row.append(f"{val:,.1f}" if not pd.isna(val) else "—")
            rows.append(row)

        n_cols = len(cols_show) + 1
        col_w = [2.8*cm] + [((17 - 2.8) / len(cols_show))*cm] * len(cols_show)
        t = Table(rows, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_BLUE_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BACKGROUND", (0, 1), (0, -1), C_GRAY_BG),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 1), (-1, -1), C_TEXT),
            ("ROWBACKGROUNDS", (1, 1), (-1, -1), [C_WHITE, C_GRAY_BG]),
            ("GRID", (0, 0), (-1, -1), 0.4, C_GRAY_LIGHT),
            ("ROWPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

    # ── Vista previa de datos ─────────────────────────────────────────────────
    story.append(Paragraph("Vista Previa de Datos (primeras 12 filas)", s_h2))
    preview = df.head(12).fillna("—")
    cols_show_data = preview.columns.tolist()[:7]
    preview = preview[cols_show_data]

    data_rows = [[str(c)[:18] for c in cols_show_data]] + [
        [str(cell)[:20] for cell in row]
        for row in preview.values.tolist()
    ]
    col_w_data = [(17 / len(cols_show_data))*cm] * len(cols_show_data)

    dt = Table(data_rows, colWidths=col_w_data, repeatRows=1)
    dt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_BLUE_MED),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_GRAY_BG]),
        ("TEXTCOLOR", (0, 1), (-1, -1), C_TEXT),
        ("GRID", (0, 0), (-1, -1), 0.4, C_GRAY_LIGHT),
        ("ROWPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(dt)
    story.append(Spacer(1, 0.8*cm))

    # ── Pie de página ─────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE_DARK))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"ADIC Platform · Procaps · Barranquilla, Colombia · "
        f"Generado el {datetime.now().strftime('%d de %B de %Y')} · "
        f"Documento de uso interno — Confidencial",
        ParagraphStyle("Footer", fontSize=7, textColor=C_MUTED, alignment=TA_CENTER),
    ))

    doc.build(story)
    return buffer.getvalue()
