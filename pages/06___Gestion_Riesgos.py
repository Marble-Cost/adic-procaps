"""
Página 6 — Gestión de Riesgos
ADIC Platform · Detección de Irregularidades en Transacciones de Terceros
"""

from __future__ import annotations

import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.risk_detector import (
    ALERT_SCORES,
    RISK_COLORS,
    RISK_DICTIONARY_RAW,
    run_risk_analysis,
    get_tercero_summary,
    get_analysis_stats,
)

# ── Paleta y constantes visuales ──────────────────────────────────────────────
_RISK_ORDER  = ["RIESGO ALTO", "RIESGO MEDIO", "RIESGO BAJO", "SIN ALERTA"]
_RISK_EMOJIS = {
    "RIESGO ALTO":  "🔴",
    "RIESGO MEDIO": "🟡",
    "RIESGO BAJO":  "🔵",
    "SIN ALERTA":   "🟢",
}

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
    font=dict(color="#1E293B", family="'DM Sans', sans-serif", size=12),
    margin=dict(t=50, b=40, l=40, r=20),
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🔍 Gestión de Riesgos")
st.markdown(
    "Detección forense de irregularidades en transacciones de terceros. "
    "El motor evalúa **precio, palabras clave, identidad, fecha y desfase temporal** "
    "para puntuar cada transacción y clasificar el nivel de riesgo del tercero."
)

# ── Guardia: requiere datos cargados ─────────────────────────────────────────
if st.session_state.get("df") is None:
    st.warning("⚠️ Primero carga datos en la página **Carga de Datos**.")
    if st.button("← Ir a Carga de Datos"):
        st.switch_page("pages/01___Carga_de_Datos.py")
    st.stop()

df_raw = st.session_state.df
source  = st.session_state.get("source_name", "Dataset")
st.caption(f"Dataset activo: **{source}** · {len(df_raw):,} filas · {len(df_raw.columns)} columnas")

all_cols   = df_raw.columns.tolist()
num_cols   = df_raw.select_dtypes(include="number").columns.tolist()
text_cols  = df_raw.select_dtypes(include="object").columns.tolist()
_NONE      = "— (no disponible) —"


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — MAPEO DE COLUMNAS
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("⚙️ **Paso 1 — Mapeo de columnas** (obligatorio antes de analizar)", expanded=True):
    st.markdown(
        "Indica a qué columna de tu dataset corresponde cada campo del motor forense. "
        "Los campos marcados con **\\*** son obligatorios."
    )
    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("##### 🔑 Campos obligatorios")

        col_tercero = st.selectbox(
            "* Tercero (nombre o código del proveedor/cliente)",
            options=all_cols,
            index=0,
            help="Columna que identifica al tercero que realizó la transacción.",
            key="rsk_col_tercero",
        )
        col_importe = st.selectbox(
            "* Importe / Valor de la transacción",
            options=num_cols if num_cols else all_cols,
            index=0,
            help="Columna con el valor monetario de cada movimiento.",
            key="rsk_col_importe",
        )

    with col_b:
        st.markdown("##### 📋 Campos opcionales (amplían la detección)")

        col_fecha_doc = st.selectbox(
            "Fecha del documento",
            options=[_NONE] + all_cols,
            index=0,
            help="Activa la Alerta de Fecha (fin de semana) y la Alerta de Desfase.",
            key="rsk_col_fecha_doc",
        )
        col_fecha_contab = st.selectbox(
            "Fecha de contabilización",
            options=[_NONE] + all_cols,
            index=0,
            help="Necesaria para calcular el desfase temporal (>60 días).",
            key="rsk_col_fecha_contab",
        )

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("##### 📝 Columnas de descripción (para Alerta de Palabra)")
        col_texto1 = st.selectbox(
            "Descripción / texto 1",
            options=[_NONE] + text_cols,
            index=0,
            key="rsk_col_texto1",
        )
        col_texto2 = st.selectbox(
            "Descripción / texto 2",
            options=[_NONE] + text_cols,
            index=0,
            key="rsk_col_texto2",
        )
        col_texto3 = st.selectbox(
            "Descripción / texto 3",
            options=[_NONE] + text_cols,
            index=0,
            key="rsk_col_texto3",
        )

    with col_d:
        st.markdown("##### 🆔 Identificación")
        col_num_documento = st.selectbox(
            "Número de documento del tercero",
            options=[_NONE] + all_cols,
            index=0,
            help="Columna con el NIT, cédula u otro identificador del tercero.",
            key="rsk_col_numdoc",
        )

        st.markdown("##### 📊 Sistema de puntaje")
        st.markdown(f"""
        <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px; font-size:0.82rem;'>
            <b>Alerta de precio:</b> {ALERT_SCORES['precio']} pts &nbsp;|&nbsp;
            <b>Alerta de palabra:</b> {ALERT_SCORES['palabra']} pts<br/>
            <b>Alerta de identidad:</b> {ALERT_SCORES['identidad']} pts &nbsp;|&nbsp;
            <b>Alerta de fecha:</b> {ALERT_SCORES['fecha']} pts &nbsp;|&nbsp;
            <b>Desfase:</b> {ALERT_SCORES['desfase']} pts<br/><br/>
            🔴 <b>RIESGO ALTO:</b> 41–100 pts &nbsp;|&nbsp;
            🟡 <b>RIESGO MEDIO:</b> 11–40 pts &nbsp;|&nbsp;
            🔵 <b>RIESGO BAJO:</b> 1–10 pts
        </div>
        """, unsafe_allow_html=True)

    # Vista previa de qué diccionario se usará
    with st.expander(f"📖 Ver diccionario de riesgo ({len(RISK_DICTIONARY_RAW)} patrones)"):
        st.caption(
            "Estos patrones se buscan en las columnas de descripción. "
            "Cada asterisco (*) actúa como comodín."
        )
        cols_dict = st.columns(3)
        for i, kw in enumerate(RISK_DICTIONARY_RAW):
            cols_dict[i % 3].markdown(f"- `{kw}`")

    st.markdown("---")

    # Resolver valores opcionales
    _f_doc   = None if col_fecha_doc   == _NONE else col_fecha_doc
    _f_cont  = None if col_fecha_contab== _NONE else col_fecha_contab
    _txt1    = None if col_texto1      == _NONE else col_texto1
    _txt2    = None if col_texto2      == _NONE else col_texto2
    _txt3    = None if col_texto3      == _NONE else col_texto3
    _num_doc = None if col_num_documento== _NONE else col_num_documento

    run_btn = st.button(
        "🚀 Ejecutar análisis forense",
        type="primary",
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR DE ANÁLISIS
# ══════════════════════════════════════════════════════════════════════════════
if run_btn:
    with st.spinner("Analizando transacciones y calculando indicadores de riesgo..."):
        try:
            result_df = run_risk_analysis(
                df=df_raw,
                col_tercero=col_tercero,
                col_importe=col_importe,
                col_fecha_doc=_f_doc,
                col_fecha_contab=_f_cont,
                col_num_documento=_num_doc,
                col_texto1=_txt1,
                col_texto2=_txt2,
                col_texto3=_txt3,
            )
            tercero_df = get_tercero_summary(result_df, col_importe)
            stats      = get_analysis_stats(result_df, col_importe)

            st.session_state["risk_result_df"]  = result_df
            st.session_state["risk_tercero_df"] = tercero_df
            st.session_state["risk_stats"]      = stats
            st.session_state["risk_col_importe"]= col_importe
            st.session_state["risk_col_tercero"]= col_tercero

            st.success(
                f"✅ Análisis completado · {stats['total_transacciones']:,} transacciones · "
                f"{stats['transacciones_alertadas']:,} con alguna alerta "
                f"({stats['pct_alertadas']}%)"
            )
        except Exception as e:
            st.error(f"❌ Error durante el análisis: {e}")
            st.exception(e)
            st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# RESULTADOS (solo si ya se ejecutó el análisis)
# ══════════════════════════════════════════════════════════════════════════════
if "risk_result_df" not in st.session_state:
    st.info("👆 Completa el mapeo de columnas y ejecuta el análisis para ver los resultados.")
    st.stop()

result_df   = st.session_state["risk_result_df"]
tercero_df  = st.session_state["risk_tercero_df"]
stats       = st.session_state["risk_stats"]
col_importe = st.session_state["risk_col_importe"]
col_tercero = st.session_state["risk_col_tercero"]

st.markdown("---")

# ── KPIs globales ─────────────────────────────────────────────────────────────
st.markdown("### 📊 Resumen ejecutivo del análisis")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total transacciones",    f"{stats['total_transacciones']:,}")
k2.metric("Con alguna alerta",      f"{stats['transacciones_alertadas']:,}",
          f"{stats['pct_alertadas']}%")
k3.metric("🔴 Riesgo alto",         f"{stats['riesgo_alto']:,}")
k4.metric("🟡 Riesgo medio",        f"{stats['riesgo_medio']:,}")
k5.metric("Terceros analizados",    f"{stats['total_terceros']:,}")
k6.metric("Terceros con alerta",    f"{stats['terceros_alertados']:,}")

# ── Importe en riesgo ─────────────────────────────────────────────────────────
ia1, ia2 = st.columns(2)
with ia1:
    st.markdown(f"""
    <div style='background:#FEF2F2; border:1px solid #FECACA; border-radius:10px; padding:16px;'>
        <div style='font-size:0.72rem; color:#DC2626; font-weight:700; text-transform:uppercase;
                    letter-spacing:0.6px;'>Importe expuesto — RIESGO ALTO</div>
        <div style='font-size:1.6rem; font-weight:800; color:#DC2626; margin:4px 0;'>
            ${stats['importe_en_riesgo_alto']:,.0f}
        </div>
        <div style='font-size:0.78rem; color:#64748B;'>
            {stats['pct_importe_en_riesgo']}% del importe total analizado
        </div>
    </div>
    """, unsafe_allow_html=True)

with ia2:
    st.markdown(f"""
    <div style='background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px; padding:16px;'>
        <div style='font-size:0.72rem; color:#003087; font-weight:700; text-transform:uppercase;
                    letter-spacing:0.6px;'>Importe total analizado</div>
        <div style='font-size:1.6rem; font-weight:800; color:#003087; margin:4px 0;'>
            ${stats['importe_total']:,.0f}
        </div>
        <div style='font-size:0.78rem; color:#64748B;'>
            {stats['total_terceros']} terceros · {stats['total_transacciones']:,} transacciones
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── Tabs de resultados ────────────────────────────────────────────────────────
tab_vis, tab_terceros, tab_transacciones, tab_exportar = st.tabs([
    "📈 Visualizaciones",
    "👤 Por tercero",
    "📋 Por transacción",
    "⬇️ Exportar",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VISUALIZACIONES
# ══════════════════════════════════════════════════════════════════════════════
with tab_vis:

    vc1, vc2 = st.columns(2)

    # Gráfico 1: Distribución de niveles de riesgo (transacciones)
    with vc1:
        risk_counts = (
            result_df["Nivel_Riesgo"]
            .value_counts()
            .reindex(_RISK_ORDER, fill_value=0)
            .reset_index()
        )
        risk_counts.columns = ["Nivel", "Transacciones"]
        risk_counts["Color"] = risk_counts["Nivel"].map(RISK_COLORS)

        fig_dist = go.Figure(go.Bar(
            x=risk_counts["Nivel"],
            y=risk_counts["Transacciones"],
            marker_color=risk_counts["Color"],
            text=risk_counts["Transacciones"],
            textposition="outside",
        ))
        fig_dist.update_layout(
            title="Distribución de riesgo por transacción",
            xaxis_title="", yaxis_title="N° de transacciones",
            **LAYOUT_BASE,
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    # Gráfico 2: Distribución de riesgo por tercero (dona)
    with vc2:
        t_risk_counts = (
            tercero_df["Nivel_Riesgo"]
            .value_counts()
            .reindex(_RISK_ORDER, fill_value=0)
            .reset_index()
        )
        t_risk_counts.columns = ["Nivel", "Terceros"]
        t_risk_counts["Color"] = t_risk_counts["Nivel"].map(RISK_COLORS)

        fig_dona = go.Figure(go.Pie(
            labels=t_risk_counts["Nivel"],
            values=t_risk_counts["Terceros"],
            marker_colors=t_risk_counts["Color"],
            hole=0.5,
            textinfo="label+percent",
        ))
        fig_dona.update_layout(
            title="Distribución de riesgo por tercero",
            **LAYOUT_BASE,
        )
        st.plotly_chart(fig_dona, use_container_width=True)

    # Gráfico 3: Frecuencia de cada tipo de alerta
    alert_freq = {
        "💰 Precio":    result_df["Alerta_Precio"].eq("SÍ").sum(),
        "🔤 Palabra":   result_df["Alerta_Palabra"].eq("SÍ").sum(),
        "🆔 Identidad": result_df["Alerta_Identidad"].eq("SÍ").sum(),
        "📅 Fecha":     result_df["Alerta_Fecha"].eq("SÍ").sum(),
        "⏳ Desfase":   result_df["Alerta_Desfase"].eq("SÍ").sum(),
        "🚫 Evasión":   result_df["Filtro_Evasion"].eq("SÍ").sum(),
    }
    alert_df = pd.DataFrame(
        list(alert_freq.items()), columns=["Alerta", "Activaciones"]
    ).sort_values("Activaciones", ascending=True)

    fig_alerts = go.Figure(go.Bar(
        x=alert_df["Activaciones"],
        y=alert_df["Alerta"],
        orientation="h",
        marker_color="#0057D8",
        text=alert_df["Activaciones"],
        textposition="outside",
    ))
    fig_alerts.update_layout(
        title="Frecuencia de activación por tipo de alerta",
        xaxis_title="N° de transacciones alertadas",
        **LAYOUT_BASE,
    )
    st.plotly_chart(fig_alerts, use_container_width=True)

    # Gráfico 4: Top 15 terceros con mayor puntaje máximo
    top_terceros = tercero_df[tercero_df["Nivel_Riesgo"] != "SIN ALERTA"].head(15)
    if not top_terceros.empty:
        top_terceros = top_terceros.sort_values("Puntaje_Maximo", ascending=True)
        colors_bar = top_terceros["Nivel_Riesgo"].map(RISK_COLORS).tolist()

        fig_top = go.Figure(go.Bar(
            x=top_terceros["Puntaje_Maximo"],
            y=top_terceros["Nombre_Monitoreo"].str[:40],
            orientation="h",
            marker_color=colors_bar,
            text=top_terceros["Puntaje_Maximo"].astype(str) + " pts",
            textposition="outside",
        ))
        fig_top.update_layout(
            title="Top terceros por puntaje máximo de riesgo",
            xaxis_title="Puntaje máximo (peor transacción)",
            height=max(350, len(top_terceros) * 28 + 80),
            **LAYOUT_BASE,
        )
        st.plotly_chart(fig_top, use_container_width=True)

    # Gráfico 5: Dispersión importe vs puntaje (burbuja por frecuencia)
    scatter_data = tercero_df[tercero_df["Nivel_Riesgo"] != "SIN ALERTA"].copy()
    if not scatter_data.empty:
        scatter_data["Color"] = scatter_data["Nivel_Riesgo"].map(RISK_COLORS)
        fig_scatter = px.scatter(
            scatter_data,
            x="Importe_Total",
            y="Puntaje_Maximo",
            size="Frecuencia_Riesgo_Pct",
            color="Nivel_Riesgo",
            color_discrete_map=RISK_COLORS,
            hover_name="Nombre_Monitoreo",
            hover_data={
                "Total_Transacciones": True,
                "Frecuencia_Riesgo_Pct": ":.1f",
                "Importe_Total": ":,.0f",
                "Puntaje_Maximo": True,
            },
            title="Importe total vs Puntaje de riesgo (tamaño = frecuencia de alertas %)",
            labels={
                "Importe_Total": "Importe total ($)",
                "Puntaje_Maximo": "Puntaje máximo",
                "Frecuencia_Riesgo_Pct": "Frecuencia %",
            },
        )
        fig_scatter.update_layout(**LAYOUT_BASE)
        st.plotly_chart(fig_scatter, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — POR TERCERO
# ══════════════════════════════════════════════════════════════════════════════
with tab_terceros:
    st.markdown("### 👤 Perfil de riesgo por tercero")
    st.caption(
        "La clasificación del tercero usa el **puntaje máximo** entre todas sus transacciones. "
        "Si más del 50% de sus movimientos genera alguna alerta, el nivel puede subir un escalón."
    )

    # Filtros
    tf1, tf2 = st.columns(2)
    with tf1:
        filtro_nivel = st.multiselect(
            "Filtrar por nivel de riesgo",
            options=_RISK_ORDER,
            default=["RIESGO ALTO", "RIESGO MEDIO"],
        )
    with tf2:
        min_transacciones = st.number_input(
            "Mínimo de transacciones por tercero", min_value=1, value=1, step=1
        )

    filtered_t = tercero_df.copy()
    if filtro_nivel:
        filtered_t = filtered_t[filtered_t["Nivel_Riesgo"].isin(filtro_nivel)]
    filtered_t = filtered_t[filtered_t["Total_Transacciones"] >= min_transacciones]

    st.markdown(f"**{len(filtered_t):,} terceros** con los filtros aplicados")

    # Tabla de terceros con colores de riesgo
    for _, row in filtered_t.iterrows():
        nivel   = row["Nivel_Riesgo"]
        emoji   = _RISK_EMOJIS.get(nivel, "")
        color   = RISK_COLORS.get(nivel, "#64748B")
        bg      = {"RIESGO ALTO": "#FEF2F2", "RIESGO MEDIO": "#FFFBEB",
                   "RIESGO BAJO": "#EFF6FF", "SIN ALERTA": "#F0FDF4"}.get(nivel, "#F8FAFC")
        border  = {"RIESGO ALTO": "#FECACA", "RIESGO MEDIO": "#FDE68A",
                   "RIESGO BAJO": "#BFDBFE", "SIN ALERTA": "#BBF7D0"}.get(nivel, "#E2E8F0")

        with st.expander(
            f"{emoji} **{row['Nombre_Monitoreo'][:60]}** — {nivel} "
            f"| Puntaje máx: {row['Puntaje_Maximo']} pts "
            f"| {row['Total_Transacciones']} transacciones "
            f"| {row['Frecuencia_Riesgo_Pct']}% alertadas"
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Importe total",    f"${row['Importe_Total']:,.0f}")
            c2.metric("Importe promedio", f"${row['Importe_Promedio']:,.0f}")
            c3.metric("Puntaje máximo",   f"{row['Puntaje_Maximo']} pts")
            c4.metric("Frecuencia alerta",f"{row['Frecuencia_Riesgo_Pct']}%")

            st.markdown(f"""
            <div style='background:{bg}; border:1px solid {border};
                         border-radius:8px; padding:10px 14px; font-size:0.82rem;'>
                <b>Alertas activas:</b> {row['Alertas_Activas']}<br/>
                <span style='color:#64748B;'>
                    Alertas precio: {row['Alertas_Precio']} &nbsp;|&nbsp;
                    Palabras: {row['Alertas_Palabra']} &nbsp;|&nbsp;
                    Identidad: {row['Alertas_Identidad']} &nbsp;|&nbsp;
                    Fecha: {row['Alertas_Fecha']} &nbsp;|&nbsp;
                    Desfase: {row['Alertas_Desfase']} &nbsp;|&nbsp;
                    Evasión: {row['Evasion_Detectada']}
                </span>
            </div>
            """, unsafe_allow_html=True)

            # Transacciones de este tercero
            txns = result_df[result_df["Nombre_Monitoreo"] == row["Nombre_Monitoreo"]]
            cols_show = [
                col_importe, "Puntaje", "Nivel_Riesgo",
                "Alerta_Precio", "Alerta_Palabra", "Alerta_Identidad",
                "Alerta_Fecha", "Alerta_Desfase", "Filtro_Evasion",
            ]
            if "_Palabra_Detectada" in txns.columns:
                cols_show.insert(4, "_Palabra_Detectada")
            if "_Desviacion_Vs_Promedio_Pct" in txns.columns:
                cols_show.insert(2, "_Desviacion_Vs_Prom