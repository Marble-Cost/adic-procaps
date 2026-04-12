"""
Página 2 — Dashboard Analítico
ADIC Platform · Procaps
"""

import streamlit as st
import pandas as pd
from modules.dashboard import (
    auto_dashboard, detect_column_types,
    bar_chart, line_chart, pie_chart,
    scatter_chart, histogram_chart,
    heatmap_correlation, boxplot_chart,
)

st.markdown("## 📊 Dashboard Analítico")

if st.session_state.get("df") is None:
    st.warning("⚠️ Primero carga datos en la página **Carga de Datos**.")
    if st.button("← Ir a Carga de Datos"):
        st.switch_page("pages/01___Carga_de_Datos.py")
    st.stop()

df_original = st.session_state.df.copy()
source = st.session_state.get("source_name", "Dataset")
report_type = st.session_state.get("report_type", "General")

st.caption(f"Fuente: **{source}** · Tipo: **{report_type}** · {len(df_original):,} filas · {len(df_original.columns)} columnas")

col_types = detect_column_types(df_original)
num_cols  = col_types["numeric"]
cat_cols  = col_types["categorical"]
date_cols = col_types["date"]

# Parsear fechas
df_work = df_original.copy()
for dc in date_cols:
    try:
        df_work[dc] = pd.to_datetime(df_work[dc])
    except Exception:
        pass

# ── Sidebar — Filtros ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎛️ Filtros")

    if date_cols:
        date_col = st.selectbox("Columna de fecha", date_cols)
        min_d = df_work[date_col].min()
        max_d = df_work[date_col].max()
        try:
            date_range = st.date_input(
                "Rango de fechas",
                value=(min_d, max_d),
                min_value=min_d,
                max_value=max_d,
            )
            if len(date_range) == 2:
                df_work = df_work[
                    (df_work[date_col] >= pd.Timestamp(date_range[0]))
                    & (df_work[date_col] <= pd.Timestamp(date_range[1]))
                ]
        except Exception:
            pass

    for cat in cat_cols[:3]:
        unique_vals = df_work[cat].dropna().unique().tolist()
        if len(unique_vals) <= 30:
            sel = st.multiselect(f"{cat}", unique_vals, default=unique_vals)
            if sel:
                df_work = df_work[df_work[cat].isin(sel)]

    st.markdown(f"**Registros filtrados:** `{len(df_work):,}`")

    if st.button("🔄 Limpiar filtros", use_container_width=True):
        st.rerun()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
if num_cols:
    st.markdown("### 📌 KPIs principales")
    n_kpis = min(len(num_cols), 5)
    kpi_cols = st.columns(n_kpis)
    for i, col in enumerate(num_cols[:5]):
        series = df_work[col].dropna()
        total = series.sum()
        avg = series.mean()
        with kpi_cols[i]:
            if total > 10_000:
                display_val = f"{total:,.0f}"
                label = f"Total {col}"
            else:
                display_val = f"{avg:,.2f}"
                label = f"Prom. {col}"
            # Delta vs total original
            orig_val = df_original[col].dropna().sum() if total > 10_000 else df_original[col].dropna().mean()
            delta = None
            if orig_val != 0 and len(df_work) < len(df_original):
                delta_pct = (total - orig_val) / orig_val * 100 if total > 10_000 else (avg - orig_val) / orig_val * 100
                delta = f"{delta_pct:+.1f}% (filtrado)"
            st.metric(label[:20], display_val, delta)

st.markdown("---")

# ── Modo de visualización ─────────────────────────────────────────────────────
mode = st.radio(
    "Modo",
    ["🤖 Auto-generado", "🛠️ Configuración manual"],
    horizontal=True,
)

if mode == "🤖 Auto-generado":
    st.markdown("### Gráficos automáticos")
    with st.spinner("Generando visualizaciones..."):
        figs = auto_dashboard(df_work)

    if not figs:
        st.info("No se pudieron generar gráficos automáticamente. Prueba el modo manual.")
    else:
        for i in range(0, len(figs), 2):
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(figs[i], use_container_width=True)
            if i + 1 < len(figs):
                with c2:
                    st.plotly_chart(figs[i + 1], use_container_width=True)

else:
    st.markdown("### Configuración manual")
    all_cols = col_types["all"]

    chart_type = st.selectbox("Tipo de gráfico", [
        "📊 Barras agrupadas",
        "📈 Línea temporal",
        "🥧 Torta / Donut",
        "🔵 Dispersión",
        "📦 Boxplot por categoría",
        "📉 Histograma",
        "🔥 Mapa de calor (correlaciones)",
    ])

    c1, c2 = st.columns(2)

    if "Barras" in chart_type:
        with c1:
            x_col = st.selectbox("Eje X (categoría)", cat_cols + all_cols)
            agg_fn = st.selectbox("Agregar por", ["Suma", "Promedio", "Conteo"])
        with c2:
            y_col = st.selectbox("Eje Y (valor)", num_cols)
        if x_col and y_col:
            if agg_fn == "Suma":
                g = df_work.groupby(x_col)[y_col].sum().reset_index()
            elif agg_fn == "Promedio":
                g = df_work.groupby(x_col)[y_col].mean().reset_index()
            else:
                g = df_work.groupby(x_col)[y_col].count().reset_index()
            g = g.sort_values(y_col, ascending=False).head(20)
            fig = bar_chart(g, x_col, y_col, title=f"{agg_fn} de {y_col} por {x_col}")
            st.plotly_chart(fig, use_container_width=True)

    elif "Línea" in chart_type:
        with c1:
            x_col = st.selectbox("Eje X (fecha)", date_cols + all_cols)
        with c2:
            y_col = st.selectbox("Eje Y (valor)", num_cols)
        if x_col and y_col:
            ts = df_work.groupby(x_col)[y_col].sum().reset_index()
            fig = line_chart(ts, x_col, y_col, title=f"{y_col} en el tiempo")
            st.plotly_chart(fig, use_container_width=True)

    elif "Torta" in chart_type:
        with c1:
            names_col = st.selectbox("Categorías", cat_cols if cat_cols else all_cols)
        with c2:
            values_col = st.selectbox("Valores", num_cols)
        if names_col and values_col:
            fig = pie_chart(df_work, names_col, values_col,
                            title=f"Distribución de {values_col} por {names_col}")
            st.plotly_chart(fig, use_container_width=True)

    elif "Dispersión" in chart_type:
        with c1:
            x_col = st.selectbox("Eje X", num_cols)
            y_col = st.selectbox("Eje Y", num_cols[1:] if len(num_cols) > 1 else num_cols)
        with c2:
            size_col = st.selectbox("Tamaño (opc.)", ["—"] + num_cols)
            color_col = st.selectbox("Color (opc.)", ["—"] + cat_cols)
        size_col = None if size_col == "—" else size_col
        color_col = None if color_col == "—" else color_col
        if x_col and y_col:
            fig = scatter_chart(df_work, x_col, y_col, size=size_col, color=color_col,
                                title=f"{x_col} vs {y_col}")
            st.plotly_chart(fig, use_container_width=True)

    elif "Boxplot" in chart_type:
        with c1:
            x_col = st.selectbox("Categoría (X)", cat_cols if cat_cols else all_cols)
        with c2:
            y_col = st.selectbox("Variable numérica (Y)", num_cols)
        if x_col and y_col:
            fig = boxplot_chart(df_work, x_col, y_col,
                                title=f"Distribución de {y_col} por {x_col}")
            st.plotly_chart(fig, use_container_width=True)

    elif "Histograma" in chart_type:
        col_sel = st.selectbox("Variable numérica", num_cols)
        if col_sel:
            fig = histogram_chart(df_work, col_sel)
            st.plotly_chart(fig, use_container_width=True)

    elif "calor" in chart_type:
        sel_cols = st.multiselect("Columnas numéricas", num_cols, default=num_cols[:6])
        if len(sel_cols) >= 2:
            fig = heatmap_correlation(df_work, sel_cols)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selecciona al menos 2 columnas.")

# ── Tabla filtrada ────────────────────────────────────────────────────────────
with st.expander("📋 Ver tabla de datos filtrados"):
    st.dataframe(df_work, use_container_width=True)
    st.caption(f"{len(df_work):,} registros · {len(df_work.columns)} columnas")

    # Botón exportar CSV
    csv = df_work.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar datos filtrados (CSV)",
        data=csv,
        file_name=f"ADIC_{source[:20]}_filtrado.csv",
        mime="text/csv",
    )

# ── Ir al asistente IA ────────────────────────────────────────────────────────
st.markdown("---")
if st.button("🤖 Generar análisis con IA →", type="primary"):
    st.switch_page("pages/03___Narración_IA.py")
