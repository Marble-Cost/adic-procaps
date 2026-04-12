"""
Página 1 — Carga de Datos
ADIC Platform · Procaps
"""

import streamlit as st
import pandas as pd
from modules import load_from_upload, load_sample, compute_quality_score, score_label
from config.settings import REPORT_TEMPLATES

st.markdown("## 📂 Carga de Datos")
st.markdown("Sube tu archivo **Excel o CSV**, o selecciona un dataset de muestra para explorar la plataforma.")

# ── Aviso de privacidad compacto ──────────────────────────────────────────────
st.info(
    "🔒 **Privacidad:** Para datos de nómina o RRHH, usa archivos con columnas anonimizadas "
    "(códigos en lugar de cédulas o nombres completos) conforme a la Ley 1581 de 2012.",
    icon=None,
)

# ── Selección de tipo de reporte ──────────────────────────────────────────────
st.markdown("#### Tipo de reporte")
template_names = list(REPORT_TEMPLATES.keys())
template_icons = [REPORT_TEMPLATES[t]["icon"] for t in template_names]

cols_tmpl = st.columns(len(template_names))
for col, name in zip(cols_tmpl, template_names):
    tmpl = REPORT_TEMPLATES[name]
    selected = st.session_state.get("report_type") == name
    with col:
        border_color = "#003087" if selected else "#E2E8F0"
        bg = "#EFF6FF" if selected else "#fff"
        st.markdown(f"""
        <div style='background:{bg}; border:2px solid {border_color}; border-radius:10px;
                    padding:12px 8px; text-align:center; cursor:pointer; height:90px;'>
            <div style='font-size:22px;'>{tmpl["icon"]}</div>
            <div style='font-size:0.72rem; font-weight:600; color:#003087; margin-top:4px;'>{name}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Seleccionar", key=f"tmpl_{name}", use_container_width=True):
            st.session_state.report_type = name
            st.rerun()

if "report_type" not in st.session_state:
    st.session_state.report_type = "General (Libre)"

selected_type = st.session_state.get("report_type", "General (Libre)")
tmpl_info = REPORT_TEMPLATES.get(selected_type, {})
st.caption(f"Tipo activo: **{selected_type}** — {tmpl_info.get('desc', '')}")

st.markdown("---")

# ── Tabs de carga ─────────────────────────────────────────────────────────────
tab_upload, tab_sample = st.tabs(["⬆️ Subir archivo", "🗂️ Dataset de muestra"])

with tab_upload:
    st.markdown("""
    <div style='background:#F8FAFC; border:2px dashed #CBD5E1; border-radius:12px;
                padding:8px 16px; margin-bottom:12px; font-size:0.82rem; color:#64748B;'>
        📋 Formatos soportados: <b>.xlsx, .xls, .csv</b> (separador coma o punto y coma, hasta 200MB)
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Selecciona tu archivo",
        type=["xlsx", "xls", "csv"],
        label_visibility="collapsed",
    )

    if uploaded:
        with st.spinner("Cargando y analizando datos..."):
            try:
                df, name = load_from_upload(uploaded)
                st.session_state.df = df
                st.session_state.source_name = name
                report = compute_quality_score(df)
                st.session_state.quality_score = report.score
                st.session_state.quality_report = report
                st.success(f"✅ **{name}** cargado — {len(df):,} filas × {len(df.columns)} columnas")
            except Exception as e:
                st.error(f"❌ Error al leer el archivo: {e}")

with tab_sample:
    st.markdown("Selecciona un dataset de muestra anonimizado para explorar la plataforma:")
    sample_options = {
        "Nómina Mensual": "👥",
        "Ventas Comercial": "📈",
        "Producción / Operaciones": "🏭",
        "Finanzas y Costos": "💰",
    }
    cols_s = st.columns(4)
    for col, (name, icon) in zip(cols_s, sample_options.items()):
        with col:
            if st.button(f"{icon} {name}", use_container_width=True):
                with st.spinner(f"Generando dataset '{name}'..."):
                    df, src = load_sample(name)
                    st.session_state.df = df
                    st.session_state.source_name = src
                    st.session_state.report_type = name
                    report = compute_quality_score(df)
                    st.session_state.quality_score = report.score
                    st.session_state.quality_report = report
                st.success(f"✅ Dataset '{name}' — {len(df):,} filas")
                st.rerun()

# ── Panel de calidad ──────────────────────────────────────────────────────────
if st.session_state.get("df") is not None:
    df = st.session_state.df
    report = st.session_state.get("quality_report")

    st.markdown("---")
    st.markdown("### 🔬 Análisis de Calidad de Datos")

    if report:
        label, color = score_label(report.score)

        # Score visual
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score Global", f"{report.score}/100", label)
        c2.metric("Completitud", f"{report.completeness}%")
        c3.metric("Unicidad (sin dups.)", f"{report.uniqueness}%")
        c4.metric("Consistencia", f"{report.consistency}%")

        # Barra de progreso visual
        score_color = color
        st.markdown(f"""
        <div style='background:#F1F5F9; border-radius:8px; height:10px; margin:8px 0 16px; overflow:hidden;'>
            <div style='background:{score_color}; width:{report.score}%; height:100%; border-radius:8px;
                        transition:width 0.5s;'></div>
        </div>
        """, unsafe_allow_html=True)

        col_issues, col_recs = st.columns(2)
        with col_issues:
            if report.issues:
                with st.expander(f"⚠️ {len(report.issues)} problema(s) detectado(s)"):
                    for issue in report.issues:
                        st.markdown(f"- {issue}")
            else:
                st.success("✅ Sin problemas de calidad detectados.")

        with col_recs:
            if report.recommendations:
                with st.expander("💡 Recomendaciones"):
                    for rec in report.recommendations:
                        st.markdown(f"- {rec}")

        # Detalle por columna
        st.markdown("#### Detalle por columna")
        detail_df = pd.DataFrame(report.column_detail).T.reset_index()
        detail_df.columns = ["Columna", "% Nulos", "Tipo de dato", "Valores únicos"]
        st.dataframe(detail_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 👁️ Vista previa del dataset")
    st.dataframe(df.head(100), use_container_width=True)

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.caption(f"**{len(df):,}** filas · **{len(df.columns)}** columnas")
    with col_info2:
        st.caption(f"Fuente: `{st.session_state.source_name}`")
    with col_info3:
        st.caption(f"Tipo: **{st.session_state.get('report_type', 'General')}**")

    # Botón para ir al dashboard
    st.markdown("")
    if st.button("📊 Ir al Dashboard →", type="primary", use_container_width=True):
        st.switch_page("pages/02___Dashboard.py")

else:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center; padding:60px 20px; background:#F8FAFC;
                border-radius:16px; border:2px dashed #CBD5E1;'>
        <div style='font-size:48px; margin-bottom:16px;'>📂</div>
        <h3 style='color:#003087; margin:0 0 8px;'>Comienza cargando tus datos</h3>
        <p style='color:#64748B; margin:0;'>
            Sube un archivo Excel o CSV, o selecciona un dataset de muestra arriba.
        </p>
    </div>
    """, unsafe_allow_html=True)
