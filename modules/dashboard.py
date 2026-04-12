"""
Módulo de Dashboard — ADIC Platform Procaps
Gráficos Plotly con paleta corporativa azul Procaps.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

# Paleta corporativa Procaps
COLORS = ["#003087", "#0057D8", "#00BFFF", "#1E40AF", "#3B82F6",
          "#60A5FA", "#93C5FD", "#0EA5E9", "#0284C7", "#0369A1"]

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
    font=dict(color="#1E293B", family="'DM Sans', sans-serif", size=12),
    margin=dict(t=50, b=40, l=40, r=20),
    legend=dict(bgcolor="rgba(255,255,255,0.8)", font=dict(color="#475569")),
    xaxis=dict(gridcolor="#F1F5F9", zerolinecolor="#E2E8F0"),
    yaxis=dict(gridcolor="#F1F5F9", zerolinecolor="#E2E8F0"),
)


def detect_column_types(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    date_cols = [
        c for c in df.columns
        if pd.api.types.is_datetime64_any_dtype(df[c])
        or (df[c].dtype == object and _is_parseable_date(df[c]))
    ]
    categorical_cols = [
        c for c in df.select_dtypes(include="object").columns
        if c not in date_cols and df[c].nunique() <= 40
    ]
    return {
        "numeric": numeric_cols,
        "date": date_cols,
        "categorical": categorical_cols,
        "all": df.columns.tolist(),
    }


def _is_parseable_date(series: pd.Series, sample_n: int = 20) -> bool:
    try:
        pd.to_datetime(series.dropna().head(sample_n))
        return True
    except Exception:
        return False


def bar_chart(df: pd.DataFrame, x: str, y: str, color: Optional[str] = None,
              title: str = "") -> go.Figure:
    fig = px.bar(df, x=x, y=y, color=color,
                 color_discrete_sequence=COLORS, title=title, barmode="group")
    fig.update_layout(**LAYOUT_BASE)
    fig.update_traces(marker_line_width=0)
    return fig


def line_chart(df: pd.DataFrame, x: str, y: str | list[str],
               color: Optional[str] = None, title: str = "") -> go.Figure:
    if isinstance(y, list):
        fig = go.Figure()
        for i, col in enumerate(y):
            fig.add_trace(go.Scatter(
                x=df[x], y=df[col], name=col, mode="lines+markers",
                line=dict(color=COLORS[i % len(COLORS)], width=2.5),
                marker=dict(size=5),
            ))
        fig.update_layout(title=title, **LAYOUT_BASE)
    else:
        fig = px.line(df, x=x, y=y, color=color,
                      color_discrete_sequence=COLORS, title=title)
        fig.update_traces(mode="lines+markers", line_width=2.5, marker_size=5)
        fig.update_layout(**LAYOUT_BASE)
    return fig


def pie_chart(df: pd.DataFrame, names: str, values: str, title: str = "") -> go.Figure:
    grouped = df.groupby(names)[values].sum().reset_index()
    fig = px.pie(grouped, names=names, values=values,
                 color_discrete_sequence=COLORS, title=title, hole=0.45)
    fig.update_layout(**LAYOUT_BASE)
    fig.update_traces(textfont_color="#1E293B", pull=[0.02] * len(grouped))
    return fig


def scatter_chart(df: pd.DataFrame, x: str, y: str, size: Optional[str] = None,
                  color: Optional[str] = None, title: str = "") -> go.Figure:
    fig = px.scatter(df, x=x, y=y, size=size, color=color,
                     color_discrete_sequence=COLORS, title=title, opacity=0.7)
    fig.update_layout(**LAYOUT_BASE)
    return fig


def heatmap_correlation(df: pd.DataFrame, numeric_cols: list[str],
                        title: str = "Correlaciones") -> go.Figure:
    if len(numeric_cols) < 2:
        return None
    corr = df[numeric_cols].corr()
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
        colorscale=[[0, "#DC2626"], [0.5, "#F1F5F9"], [1, "#003087"]],
        zmin=-1, zmax=1,
        text=corr.round(2).values, texttemplate="%{text}",
    ))
    fig.update_layout(title=title, **LAYOUT_BASE)
    return fig


def histogram_chart(df: pd.DataFrame, col: str, title: str = "") -> go.Figure:
    fig = px.histogram(df, x=col, color_discrete_sequence=[COLORS[0]],
                       title=title or f"Distribución: {col}", nbins=30)
    fig.update_layout(**LAYOUT_BASE)
    fig.update_traces(marker_line_width=0, opacity=0.85)
    return fig


def boxplot_chart(df: pd.DataFrame, x: str, y: str, title: str = "") -> go.Figure:
    fig = px.box(df, x=x, y=y, color_discrete_sequence=COLORS,
                 title=title, color=x)
    fig.update_layout(**LAYOUT_BASE)
    return fig


def auto_dashboard(df: pd.DataFrame) -> list[go.Figure]:
    col_types = detect_column_types(df)
    figures = []
    num = col_types["numeric"]
    cat = col_types["categorical"]
    date = col_types["date"]

    for dc in date:
        try:
            df[dc] = pd.to_datetime(df[dc])
        except Exception:
            pass

    if date and num:
        ts_col = date[0]
        val_col = num[0]
        ts_df = df.groupby(ts_col)[val_col].sum().reset_index()
        figures.append(line_chart(ts_df, ts_col, val_col,
                                  title=f"📈 {val_col} en el tiempo"))

    if cat and num:
        g = df.groupby(cat[0])[num[0]].sum().reset_index().sort_values(num[0], ascending=False).head(15)
        figures.append(bar_chart(g, cat[0], num[0],
                                 title=f"📊 {num[0]} por {cat[0]}"))

    if len(cat) >= 2 and num:
        figures.append(pie_chart(df, cat[1 if len(cat) > 1 else 0], num[0],
                                 title=f"🥧 Distribución de {num[0]}"))

    if len(num) >= 2:
        sz = num[2] if len(num) > 2 else None
        cl = cat[0] if cat else None
        figures.append(scatter_chart(df, num[0], num[1], size=sz, color=cl,
                                     title=f"🔵 {num[0]} vs {num[1]}"))

    if cat and num and len(num) >= 1:
        figures.append(boxplot_chart(df, cat[0], num[0],
                                     title=f"📦 Distribución de {num[0]} por {cat[0]}"))

    if len(num) >= 3:
        hm = heatmap_correlation(df, num[:8])
        if hm:
            figures.append(hm)

    return figures
