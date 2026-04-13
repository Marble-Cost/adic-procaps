"""
Página 2 — Dashboard Analítico
ADIC Platform · Fase 1
"""

import streamlit as st
import pandas as pd
from modules.dashboard import auto_dashboard, detect_column_types, bar_chart, line_chart, pie_chart, scatter_chart, histogram_chart, heatmap_correlation

st.set_page_config(page_title="Dashboard · ADIC", layout="wide")

st.markdown("## 📊 Dashboard Analítico")

if st.session_state.get("df") is None:
    st.warning("⚠️ Primero carga datos en la página **Carga de Datos**.")
    st.stop()

df = st.session_state.df
source = st.session_state.get("source_name", "Dataset")

st.caption(f"Fuente activa: **{source}** · {len(df):,} filas · {len(df.columns)} columnas")

col_types = detect_column_types(df)
num_cols  = col_types["numeric"]
cat_cols  = col_types["categorical"]
date_cols = col_types["date"]
all_cols  = col_types["all"]

# Parsear fechas detectadas
for dc in date_cols:
    try:
        df[dc] = pd.to_datetime(df[dc])
    except Exception:
        pass

# ── Sidebar — Filtros globales ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎛️ Filtros globales")

    if date_cols:
        date_col = st.selectbox("Columna de fecha", date_cols)
        min_d = df[date_col].min()
        max_d = df[date_col].max()
        date_range = st.date_input(
            "Rango de fechas",
            value=(min_d, max_d),
            min_value=min_d,
            max_value=max_d,
        )
        if len(date_range) == 2:
            df = df[
                (df[date_col] >= pd.Timestamp(date_range[0]))
                & (df[date_col] <= pd.Timestamp(date_range[1]))
            ]

    if cat_cols:
        for cat in cat_cols[:2]:
            unique_vals = df[cat].dropna().unique().tolist()
            sel = st.multiselect(f"Filtrar por {cat}", unique_vals, default=unique_vals)
            if sel:
                df = df[df[cat].isin(sel)]

    st.markdown(f"**Registros filtrados:** {len(df):,}")

# ── KPI Cards ─────────────────────────────────────────────────────────────────
if num_cols:
    st.markdown("### 📌 KPIs")
    kpi_cols = st.columns(min(len(num_cols), 4))
    for i, col in enumerate(num_cols[:4]):
        series = df[col].dropna()
        total = series.sum()
        avg = series.mean()
        with kpi_cols[i]:
            display_val = f"{total:,.0f}" if total > 10_000 else f"{avg:,.2f}"
            label = "Total" if total > 10_000 else "Promedio"
            st.metric(f"{col}", display_val, f"{label}")

st.markdown("---")

# ── Modo: Auto vs Manual ──────────────────────────────────────────────────────
mode = st.radio("Modo de visualización", ["🤖 Auto-generado", "🛠️ Configuración manual"],
                horizontal=True)

if mode == "🤖 Auto-generado":
    st.markdown("### Gráficos generados automáticamente")
    with st.spinner("Generando dashboard..."):
        figs = auto_dashboard(df)

    if not figs:
        st.info("No se pudieron generar gráficos. Intenta con el modo manual.")
    else:
        # Disposición en grilla 2 columnas
        for i in range(0, len(figs), 2):
            cols = st.columns(2)
            cols[0].plotly_chart(figs[i], use_container_width=True)
            if i + 1 < len(figs):
                cols[1].plotly_chart(figs[i + 1], use_container_width=True)

else:
    st.markdown("### Configuración manual de gráficos")

    chart_type = st.selectbox("Tipo de gráfico", [
        "Barras", "Línea temporal", "Torta / Donut",
        "Dispersión / Burbujas", "Histograma", "Mapa de calor (correlaciones)"
    ])

    c1, c2 = st.columns(2)

    if chart_type == "Barras":
        with c1:
            x_col = st.selectbox("Eje X (categoría)", cat_cols + all_cols)
        with c2:
            y_col = st.selectbox("Eje Y (valor)", num_cols)
        color_col = st.selectbox("Color por (opcional)", ["Ninguno"] + cat_cols)
        color_col = None if color_col == "Ninguno" else color_col
        if x_col and y_col:
            g = df.groupby(x_col)[y_col].sum().reset_index()
            fig = bar_chart(g, x_col, y_col, color=None,
                            title=f"{y_col} por {x_col}")
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Línea temporal":
        with c1:
            x_col = st.selectbox("Eje X (fecha)", date_cols + all_cols)
        with c2:
            y_col = st.selectbox("Eje Y (valor)", num_cols)
        if x_col and y_col:
            ts = df.groupby(x_col)[y_col].sum().reset_index()
            fig = line_chart(ts, x_col, y_col, title=f"{y_col} en el tiempo")
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Torta / Donut":
        with c1:
            names_col = st.selectbox("Categorías", cat_cols)
        with c2:
            values_col = st.selectbox("Valores", num_cols)
        if names_col and values_col:
            fig = pie_chart(df, names_col, values_col,
                            title=f"Distribución de {values_col} por {names_col}")
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Dispersión / Burbujas":
        with c1:
            x_col = st.selectbox("Eje X", num_cols)
            y_col = st.selectbox("Eje Y", num_cols[1:] if len(num_cols) > 1 else num_cols)
        with c2:
            size_col = st.selectbox("Tamaño (opcional)", ["Ninguno"] + num_cols)
            color_col = st.selectbox("Color (opcional)", ["Ninguno"] + cat_cols)
        size_col = None if size_col == "Ninguno" else size_col
        color_col = None if color_col == "Ninguno" else color_col
        if x_col and y_col:
            fig = scatter_chart(df, x_col, y_col, size=size_col, color=color_col,
                                title=f"{x_col} vs {y_col}")
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Histograma":
        col_sel = st.selectbox("Variable", num_cols)
        if col_sel:
            fig = histogram_chart(df, col_sel)
            st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Mapa de calor (correlaciones)":
        sel_cols = st.multiselect("Columnas numéricas", num_cols, default=num_cols[:6])
        if len(sel_cols) >= 2:
            fig = heatmap_correlation(df, sel_cols)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selecciona al menos 2 columnas numéricas.")

# ── Tabla de datos filtrados ──────────────────────────────────────────────────
with st.expander("📋 Ver tabla de datos filtrados"):
    st.dataframe(df, use_container_width=True)
    st.caption(f"{len(df):,} registros · {len(df.columns)} columnas")