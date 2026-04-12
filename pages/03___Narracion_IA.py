"""
Página 3 — Asistente IA
ADIC Platform · Procaps
"""

import streamlit as st
import pandas as pd
from modules.ai_narrator import generate_narrative, answer_natural_query

st.markdown("## 🤖 Asistente de Análisis IA")
st.markdown(
    "El asistente analiza tus datos y genera reportes ejecutivos en lenguaje natural. "
    "**Solo procesa estadísticas agregadas** — nunca datos individuales ni información personal."
)

if st.session_state.get("df") is None:
    st.warning("⚠️ Primero carga datos en la página **Carga de Datos**.")
    if st.button("← Ir a Carga de Datos"):
        st.switch_page("pages/01___Carga_de_Datos.py")
    st.stop()

df = st.session_state.df
source = st.session_state.get("source_name", "Dataset")
quality_score = st.session_state.get("quality_score", 0)
report_type = st.session_state.get("report_type", "General (Libre)")

# ── Info de sesión ────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Dataset activo", source[:30])
c2.metric("Registros", f"{len(df):,}")
c3.metric("Quality Score", f"{quality_score:.0f}/100")

st.markdown("---")

tab_narrative, tab_query = st.tabs(["📝 Reporte ejecutivo", "💬 Consultas en lenguaje natural"])

# ── Tab 1: Reporte ejecutivo ──────────────────────────────────────────────────
with tab_narrative:
    st.markdown("### Configuración del reporte")

    col_a, col_b = st.columns(2)
    with col_a:
        report_type_sel = st.selectbox(
            "Tipo de reporte",
            ["Nómina Mensual", "Ventas Comercial", "Producción / Operaciones",
             "Finanzas y Costos", "General (Libre)"],
            index=["Nómina Mensual", "Ventas Comercial", "Producción / Operaciones",
                   "Finanzas y Costos", "General (Libre)"].index(report_type)
            if report_type in ["Nómina Mensual", "Ventas Comercial", "Producción / Operaciones",
                                "Finanzas y Costos", "General (Libre)"] else 4,
        )

    with col_b:
        context_extra = st.text_area(
            "Contexto adicional (opcional)",
            placeholder=(
                "Ej: 'Este es el reporte de nómina de marzo 2025. "
                "El incremento salarial este año fue del 9.28%.' "
                "O: 'La meta de ventas Q1 es $2.000M COP.'"
            ),
            height=100,
        )

    st.markdown("")

    # Privacidad explicada
    with st.expander("🔒 ¿Qué datos ve el asistente IA?"):
        st.markdown("""
        El asistente **solo recibe estadísticas resumidas**, nunca registros individuales:
        - ✅ Totales, promedios, mínimos y máximos por columna
        - ✅ Distribución de categorías (conteos)
        - ✅ Rango de fechas
        - ❌ NO recibe cédulas, nombres, salarios individuales, ni datos sensibles
        
        Esto cumple con el principio de minimización de datos de la Ley 1581 de 2012.
        """)

    if st.button("🚀 Generar reporte ejecutivo con IA", type="primary", use_container_width=True):
        with st.spinner("El asistente está analizando los datos..."):
            narrative = generate_narrative(
                df=df,
                source_name=source,
                quality_score=quality_score,
                report_type=report_type_sel,
                extra_context=context_extra,
            )
            st.session_state.narration = narrative
            st.session_state.report_type = report_type_sel

    if st.session_state.get("narration"):
        st.markdown("---")
        st.markdown("### 📋 Reporte ejecutivo generado")

        # Renderizar el reporte en un card visual
        st.markdown(f"""
        <div style='background:#EFF6FF; border-left:4px solid #003087; border-radius:8px;
                    padding:4px 16px; margin-bottom:8px; font-size:0.8rem; color:#003087;'>
            Generado por ADIC Asistente IA · Fuente: {source} · Tipo: {report_type_sel}
        </div>
        """, unsafe_allow_html=True)

        st.markdown(st.session_state.narration)

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            st.success("✅ Reporte listo. Ve a **Reporte PDF** para exportarlo.")
        with col_act2:
            if st.button("📄 Ir a Reporte PDF →", type="primary", use_container_width=True):
                st.switch_page("pages/04___Reporte_PDF.py")

        # Copiar texto
        if st.button("📋 Copiar texto del reporte"):
            st.code(st.session_state.narration, language=None)

# ── Tab 2: Consultas ──────────────────────────────────────────────────────────
with tab_query:
    st.markdown("Escribe una pregunta en español sobre tus datos y el asistente responderá.")

    # Sugerencias por tipo de reporte
    SUGGESTIONS = {
        "Nómina Mensual": [
            "¿Cuál área tiene la nómina más alta?",
            "¿Cuántos empleados hay por tipo de contrato?",
            "¿Cuál es el salario promedio por cargo?",
            "¿Cuántos empleados están activos?",
        ],
        "Ventas Comercial": [
            "¿Cuál fue el producto más vendido?",
            "¿Qué región genera más ingresos?",
            "¿Cuál es el margen promedio?",
            "¿Qué canal de venta es más eficiente?",
        ],
        "Producción / Operaciones": [
            "¿Cuál línea tiene mejor eficiencia?",
            "¿Cuántos lotes fueron rechazados?",
            "¿Cuál es el tiempo de ciclo promedio?",
            "¿Qué producto tiene más rechazos?",
        ],
        "Finanzas y Costos": [
            "¿Qué centro de costo tiene mayor sobrepresupuesto?",
            "¿Cuál es la variación total?",
            "¿Qué conceptos generan más ejecución?",
            "¿Cómo va el presupuesto vs ejecución?",
        ],
    }

    sugs = SUGGESTIONS.get(report_type, [
        "¿Cuál es el total de la columna principal?",
        "¿Qué categoría tiene el valor más alto?",
        "¿Cuál es el promedio general?",
        "¿Cuántos registros hay por categoría?",
    ])

    st.markdown("**Preguntas sugeridas:**")
    cols_sug = st.columns(len(sugs))
    for i, sug in enumerate(sugs):
        if cols_sug[i].button(sug, key=f"sug_{i}", use_container_width=True):
            st.session_state.nlp_question = sug

    question = st.text_input(
        "Tu pregunta",
        value=st.session_state.get("nlp_question", ""),
        placeholder="Ej: ¿Cuál es el total vendido en Barranquilla?",
    )

    if st.button("🔍 Preguntar al asistente", type="primary") and question:
        with st.spinner("Procesando..."):
            answer = answer_natural_query(df, question)
        st.markdown("---")
        st.markdown(f"""
        <div style='background:#F0F9FF; border:1px solid #BAE6FD; border-radius:8px; padding:12px;'>
            <div style='font-size:0.8rem; color:#0284C7; font-weight:600; margin-bottom:4px;'>PREGUNTA</div>
            <div style='color:#1E293B;'>{question}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:12px;'>
            <div style='font-size:0.8rem; color:#16A34A; font-weight:600; margin-bottom:4px;'>RESPUESTA DEL ASISTENTE</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(answer)

    st.markdown("---")
    st.markdown("#### Esquema de tus datos")
    schema_info = {
        "Columna": df.columns.tolist(),
        "Tipo": [str(df[c].dtype) for c in df.columns],
        "Valores únicos": [df[c].nunique() for c in df.columns],
        "% Nulos": [f"{df[c].isnull().mean()*100:.1f}%" for c in df.columns],
    }
    st.dataframe(pd.DataFrame(schema_info), use_container_width=True, hide_index=True)
