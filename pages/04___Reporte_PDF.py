"""
Página 4 — Reporte PDF
ADIC Platform · Procaps
"""

import streamlit as st
from modules.report_generator import generate_pdf_report
from modules.quality import score_label

st.markdown("## 📄 Generador de Reporte PDF")
st.markdown("Exporta un reporte ejecutivo profesional con identidad corporativa Procaps.")

if st.session_state.get("df") is None:
    st.warning("⚠️ Primero carga datos en la página **Carga de Datos**.")
    if st.button("← Ir a Carga de Datos"):
        st.switch_page("pages/01___Carga_de_Datos.py")
    st.stop()

df = st.session_state.df
source = st.session_state.get("source_name", "Dataset")
quality_score = st.session_state.get("quality_score", 0.0)
narration = st.session_state.get("narration")
report_type = st.session_state.get("report_type", "General (Libre)")

# ── Configuración ─────────────────────────────────────────────────────────────
st.markdown("### ⚙️ Configuración")

c1, c2 = st.columns(2)
with c1:
    report_title = st.text_input(
        "Título del reporte",
        value=f"Reporte {report_type} — {source[:30]}",
    )
with c2:
    include_ai = st.checkbox(
        "Incluir análisis del Asistente IA",
        value=bool(narration),
        disabled=not bool(narration),
        help="Genera el análisis IA primero desde la página 'Asistente IA'.",
    )

# ── Preview del contenido ─────────────────────────────────────────────────────
st.markdown("### 📋 Contenido del reporte")

cols_prev = st.columns(4)

with cols_prev[0]:
    num_cols = df.select_dtypes(include="number").columns
    st.markdown(f"""
    <div style='background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px;
                padding:16px; text-align:center;'>
        <div style='font-size:28px;'>📊</div>
        <div style='font-weight:700; color:#003087; margin-top:6px; font-size:0.85rem;'>Estadísticas</div>
        <div style='color:#64748B; font-size:0.72rem;'>{len(num_cols)} variables numéricas</div>
    </div>
    """, unsafe_allow_html=True)

with cols_prev[1]:
    label, color = score_label(quality_score)
    st.markdown(f"""
    <div style='background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px;
                padding:16px; text-align:center;'>
        <div style='font-size:28px;'>🔬</div>
        <div style='font-weight:700; color:#003087; margin-top:6px; font-size:0.85rem;'>Calidad datos</div>
        <div style='color:{color}; font-weight:800; font-size:1.1rem;'>{quality_score:.0f}/100</div>
    </div>
    """, unsafe_allow_html=True)

with cols_prev[2]:
    ai_ok = narration and include_ai
    ai_icon = "✅" if ai_ok else "❌"
    ai_text = "Incluido" if ai_ok else "No generado"
    st.markdown(f"""
    <div style='background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px;
                padding:16px; text-align:center;'>
        <div style='font-size:28px;'>🤖</div>
        <div style='font-weight:700; color:#003087; margin-top:6px; font-size:0.85rem;'>Análisis IA</div>
        <div style='color:#64748B; font-size:0.72rem;'>{ai_icon} {ai_text}</div>
    </div>
    """, unsafe_allow_html=True)

with cols_prev[3]:
    st.markdown(f"""
    <div style='background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px;
                padding:16px; text-align:center;'>
        <div style='font-size:28px;'>📋</div>
        <div style='font-weight:700; color:#003087; margin-top:6px; font-size:0.85rem;'>Vista previa</div>
        <div style='color:#64748B; font-size:0.72rem;'>Primeras 12 filas</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Generar PDF ───────────────────────────────────────────────────────────────
if st.button("⬇️ Generar y descargar reporte PDF", type="primary", use_container_width=True):
    with st.spinner("Generando reporte PDF con identidad Procaps..."):
        try:
            pdf_bytes = generate_pdf_report(
                df=df,
                source_name=source,
                quality_score=quality_score,
                narrative=narration if include_ai else None,
                title=report_title,
                report_type=report_type,
            )
            filename = f"Procaps_ADIC_{report_type.replace(' ', '_').replace('/', '')}_{source[:20].replace(' ', '_')}.pdf"
            st.download_button(
                label="📥 Descargar PDF — Listo para compartir",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
            st.success("✅ Reporte generado. El archivo incluye identidad corporativa Procaps.")

        except ImportError:
            st.error(
                "❌ ReportLab no está instalado. "
                "Ejecuta: `pip install reportlab` y reinicia la app."
            )
        except Exception as e:
            st.error(f"❌ Error al generar el PDF: {e}")
            st.exception(e)

# ── Tips ──────────────────────────────────────────────────────────────────────
if not narration:
    st.info(
        "💡 **Tip:** Para incluir el análisis ejecutivo del asistente IA en el PDF, "
        "ve primero a la página **Asistente IA** y genera el reporte, luego vuelve aquí."
    )

st.markdown("---")
st.markdown("#### 📌 Sobre el reporte PDF")
st.markdown("""
El reporte PDF incluye:
- **Encabezado corporativo** con identidad visual Procaps (azul institucional)
- **Resumen del dataset** (fuente, filas, columnas, tipo de reporte)
- **Score de calidad de datos** con calificación e interpretación
- **Análisis ejecutivo IA** (si está disponible) con hallazgos y recomendaciones
- **Estadísticas descriptivas** de todas las variables numéricas
- **Vista previa** de las primeras filas del dataset
- **Pie de página** con marca de confidencialidad y fecha de generación

> 🔒 El PDF es apto para distribución interna. Recuerda no incluir datos personales identificables en los datasets.
""")
