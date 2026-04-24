"""
Página 6 — Gestión de Riesgos · Detección de Irregularidades
ADIC Platform · Analista de Cumplimiento Legal Corporativo
"""

from __future__ import annotations

import io
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from modules.risk_detector import (
    ALERT_SCORES, RISK_COLORS, RISK_DICTIONARY_RAW,
    INFRACTION_DEFINITIONS, SEVERITY_COLORS,
    run_risk_analysis, get_tercero_summary, get_analysis_stats,
)

# ── Constantes visuales ───────────────────────────────────────────────────────
_RISK_ORDER  = ["RIESGO ALTO", "RIESGO MEDIO", "RIESGO BAJO", "SIN ALERTA"]
_RISK_EMOJIS = {"RIESGO ALTO": "🔴", "RIESGO MEDIO": "🟡",
                "RIESGO BAJO": "🔵", "SIN ALERTA": "🟢"}
_RISK_BG     = {"RIESGO ALTO": ("#FEF2F2","#FECACA"),
                "RIESGO MEDIO":("#FFFBEB","#FDE68A"),
                "RIESGO BAJO": ("#EFF6FF","#BFDBFE"),
                "SIN ALERTA":  ("#F0FDF4","#BBF7D0")}

_L = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color="#1E293B", family="'DM Sans',sans-serif", size=12),
          margin=dict(t=52, b=36, l=36, r=16))

_NONE = "— (no disponible) —"

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🔍 Gestión de Riesgos — Detección de Irregularidades")
st.markdown(
    "Motor de análisis forense que actúa como **analista de cumplimiento legal corporativo**. "
    "Evalúa cada transacción con indicadores cuantitativos y cualitativos para identificar "
    "**terceros infractores**, **actos antiéticos** e **irregularidades documentales**."
)

if st.session_state.get("df") is None:
    st.warning("⚠️ Primero carga datos en la página **Carga de Datos**.")
    if st.button("← Ir a Carga de Datos"):
        st.switch_page("pages/01___Carga_de_Datos.py")
    st.stop()

df_raw = st.session_state.df
source = st.session_state.get("source_name", "Dataset")
st.caption(f"**{source}** · {len(df_raw):,} filas · {len(df_raw.columns)} columnas")

all_cols  = df_raw.columns.tolist()
num_cols  = df_raw.select_dtypes(include="number").columns.tolist()
text_cols = df_raw.select_dtypes(include="object").columns.tolist()

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — MAPEO DE COLUMNAS
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("⚙️ **Paso 1 — Mapeo de columnas** (configura y ejecuta el análisis)", expanded=True):

    ma, mb = st.columns(2)
    with ma:
        st.markdown("##### 🔑 Obligatorios")
        col_tercero = st.selectbox("* Tercero (nombre o código)", all_cols, key="rsk_t")
        col_importe = st.selectbox("* Importe / Valor de la transacción",
                                   num_cols if num_cols else all_cols, key="rsk_i")
    with mb:
        st.markdown("##### 📅 Fechas (activan alertas temporales)")
        col_fecha_doc   = st.selectbox("Fecha del documento",      [_NONE]+all_cols, key="rsk_fd")
        col_fecha_contab= st.selectbox("Fecha de contabilización", [_NONE]+all_cols, key="rsk_fc")

    mc, md = st.columns(2)
    with mc:
        st.markdown("##### 📝 Descripciones (activan Alerta de Palabra)")
        col_texto1 = st.selectbox("Descripción 1", [_NONE]+text_cols, key="rsk_tx1")
        col_texto2 = st.selectbox("Descripción 2", [_NONE]+text_cols, key="rsk_tx2")
        col_texto3 = st.selectbox("Descripción 3", [_NONE]+text_cols, key="rsk_tx3")
    with md:
        st.markdown("##### 🆔 Identificación")
        col_num_doc = st.selectbox("N° documento del tercero", [_NONE]+all_cols, key="rsk_nd")

        st.markdown("##### ⚖️ Pesos del sistema de puntaje")
        st.markdown(f"""
        <div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;
                    padding:12px;font-size:0.8rem;line-height:1.8;'>
          💰 <b>Precio:</b> {ALERT_SCORES['precio']} pts &nbsp;
          🔤 <b>Palabra:</b> {ALERT_SCORES['palabra']} pts &nbsp;
          🆔 <b>Identidad:</b> {ALERT_SCORES['identidad']} pts<br/>
          📅 <b>Fecha:</b> {ALERT_SCORES['fecha']} pts &nbsp;
          ⏳ <b>Desfase:</b> {ALERT_SCORES['desfase']} pts<br/><br/>
          🔴 <b>ALTO</b> ≥ 41 pts &nbsp;|&nbsp;
          🟡 <b>MEDIO</b> 11–40 pts &nbsp;|&nbsp;
          🔵 <b>BAJO</b> 1–10 pts
        </div>
        """, unsafe_allow_html=True)

    with st.expander(f"📖 Diccionario de riesgo ({len(RISK_DICTIONARY_RAW)} patrones)"):
        cols_dict = st.columns(3)
        for i, kw in enumerate(RISK_DICTIONARY_RAW):
            cols_dict[i % 3].markdown(f"- `{kw}`")

    st.markdown("---")
    _fd  = None if col_fecha_doc    == _NONE else col_fecha_doc
    _fc  = None if col_fecha_contab == _NONE else col_fecha_contab
    _t1  = None if col_texto1       == _NONE else col_texto1
    _t2  = None if col_texto2       == _NONE else col_texto2
    _t3  = None if col_texto3       == _NONE else col_texto3
    _nd  = None if col_num_doc      == _NONE else col_num_doc

    if st.button("🚀 Ejecutar análisis forense de cumplimiento", type="primary",
                 use_container_width=True):
        with st.spinner("Analizando transacciones, clasificando infracciones y detectando anomalías..."):
            try:
                res = run_risk_analysis(df_raw, col_tercero, col_importe,
                                        _fd, _fc, _nd, _t1, _t2, _t3)
                t_df   = get_tercero_summary(res, col_importe)
                stats  = get_analysis_stats(res, col_importe)
                st.session_state.update({
                    "rsk_res": res, "rsk_tdf": t_df, "rsk_stats": stats,
                    "rsk_imp": col_importe, "rsk_ter": col_tercero,
                })
                n_crit = (t_df["Nivel_Riesgo"] == "RIESGO ALTO").sum()
                st.success(
                    f"✅ Análisis completado · {stats['total_transacciones']:,} transacciones · "
                    f"{stats['transacciones_alertadas']:,} con alerta "
                    f"({stats['pct_alertadas']}%) · **{n_crit} terceros en RIESGO ALTO**"
                )
            except Exception as e:
                st.error(f"❌ Error durante el análisis: {e}")
                st.exception(e)
                st.stop()

if "rsk_res" not in st.session_state:
    st.info("👆 Configura el mapeo de columnas y ejecuta el análisis.")
    st.stop()

res         = st.session_state["rsk_res"]
t_df        = st.session_state["rsk_tdf"]
stats       = st.session_state["rsk_stats"]
col_importe = st.session_state["rsk_imp"]
col_tercero = st.session_state["rsk_ter"]

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# KPIs EJECUTIVOS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📊 Panel ejecutivo de cumplimiento")

k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.metric("Transacciones",      f"{stats['total_transacciones']:,}")
k2.metric("Con alguna alerta",  f"{stats['transacciones_alertadas']:,}",
          f"{stats['pct_alertadas']}%")
k3.metric("🔴 Riesgo Alto",     f"{stats['riesgo_alto']:,}")
k4.metric("🟡 Riesgo Medio",    f"{stats['riesgo_medio']:,}")
k5.metric("Terceros analizados",f"{stats['total_terceros']:,}")
k6.metric("⛔ Terceros críticos",f"{stats['terceros_criticos']:,}")

# Tarjetas de exposición financiera
fi1, fi2, fi3 = st.columns(3)
with fi1:
    st.markdown(f"""
    <div style='background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;padding:16px;'>
      <div style='font-size:0.7rem;color:#DC2626;font-weight:700;text-transform:uppercase;
                  letter-spacing:.6px;'>⚠️ Importe expuesto — Riesgo Alto</div>
      <div style='font-size:1.55rem;font-weight:800;color:#DC2626;margin:4px 0;'>
        ${stats['importe_riesgo_alto']:,.0f}
      </div>
      <div style='font-size:0.78rem;color:#64748B;'>
        {stats['pct_importe_riesgo']}% del importe total analizado
      </div>
    </div>""", unsafe_allow_html=True)

with fi2:
    n_infracciones = sum(stats["infraction_counts"].values())
    st.markdown(f"""
    <div style='background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;padding:16px;'>
      <div style='font-size:0.7rem;color:#D97706;font-weight:700;text-transform:uppercase;
                  letter-spacing:.6px;'>🚨 Total de infracciones detectadas</div>
      <div style='font-size:1.55rem;font-weight:800;color:#D97706;margin:4px 0;'>
        {n_infracciones:,}
      </div>
      <div style='font-size:0.78rem;color:#64748B;'>
        En {stats['transacciones_alertadas']:,} transacciones irregulares
      </div>
    </div>""", unsafe_allow_html=True)

with fi3:
    n_anomalias = sum(stats["anomaly_counts"].values())
    st.markdown(f"""
    <div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;padding:16px;'>
      <div style='font-size:0.7rem;color:#003087;font-weight:700;text-transform:uppercase;
                  letter-spacing:.6px;'>🔬 Anomalías estadísticas adicionales</div>
      <div style='font-size:1.55rem;font-weight:800;color:#003087;margin:4px 0;'>
        {n_anomalias:,}
      </div>
      <div style='font-size:0.78rem;color:#64748B;'>
        Montos redondos, duplicados, outliers, fraccionamiento
      </div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_dash, tab_terceros, tab_infracc, tab_anomalias, tab_txns, tab_export = st.tabs([
    "📈 Dashboards de Riesgo",
    "👤 Terceros Infractores",
    "🚨 Infracciones",
    "🔬 Anomalías Estadísticas",
    "📋 Transacciones",
    "⬇️ Exportar Reporte",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARDS DE RIESGO
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown("### 📈 Dashboards forenses de cumplimiento")

    # ── Fila 1: distribución de riesgo y mapa de calor de alertas ────────────
    r1a, r1b = st.columns([1, 1])

    with r1a:
        # Pirámide de riesgo — transacciones
        counts_txn = (res["Nivel_Riesgo"].value_counts()
                      .reindex(_RISK_ORDER, fill_value=0).reset_index())
        counts_txn.columns = ["Nivel", "N"]
        counts_txn["Pct"] = (counts_txn["N"] / counts_txn["N"].sum() * 100).round(1)
        counts_txn["Color"] = counts_txn["Nivel"].map(RISK_COLORS)

        fig_pir = go.Figure(go.Bar(
            y=counts_txn["Nivel"], x=counts_txn["N"],
            orientation="h",
            marker_color=counts_txn["Color"],
            text=counts_txn.apply(lambda r: f"{r['N']:,}  ({r['Pct']}%)", axis=1),
            textposition="outside",
        ))
        fig_pir.update_layout(title="Pirámide de riesgo — transacciones",
                              xaxis_title="N° transacciones", **_L)
        st.plotly_chart(fig_pir, use_container_width=True)

    with r1b:
        # Mapa de calor: tipo de alerta × nivel de riesgo
        alertas_cols = {
            "💰 Precio":    "Alerta_Precio",
            "🔤 Palabra":   "Alerta_Palabra",
            "🆔 Identidad": "Alerta_Identidad",
            "📅 Fecha":     "Alerta_Fecha",
            "⏳ Desfase":   "Alerta_Desfase",
            "🚫 Evasión":   "Filtro_Evasion",
        }
        hm_data = []
        for nivel in ["RIESGO ALTO", "RIESGO MEDIO", "RIESGO BAJO"]:
            sub = res[res["Nivel_Riesgo"] == nivel]
            row_vals = []
            for label, col in alertas_cols.items():
                if col in sub.columns:
                    row_vals.append(int(sub[col].eq("SÍ").sum()))
                else:
                    row_vals.append(0)
            hm_data.append(row_vals)

        fig_hm = go.Figure(go.Heatmap(
            z=hm_data,
            x=list(alertas_cols.keys()),
            y=["🔴 Riesgo Alto", "🟡 Riesgo Medio", "🔵 Riesgo Bajo"],
            colorscale=[[0,"#F0FDF4"],[0.5,"#FEF9C3"],[1,"#7C0000"]],
            text=[[str(v) for v in row] for row in hm_data],
            texttemplate="%{text}",
            showscale=True,
        ))
        fig_hm.update_layout(title="Mapa de calor: alertas por nivel de riesgo", **_L)
        st.plotly_chart(fig_hm, use_container_width=True)

    # ── Fila 2: top terceros infractores y distribución de infracciones ───────
    r2a, r2b = st.columns([1.2, 0.8])

    with r2a:
        # Top 12 terceros por puntaje máximo (barra horizontal con colores)
        top12 = (t_df[t_df["Nivel_Riesgo"] != "SIN ALERTA"]
                 .head(12).sort_values("Puntaje_Maximo"))
        if not top12.empty:
            colors_t = top12["Nivel_Riesgo"].map(RISK_COLORS).tolist()
            fig_top = go.Figure(go.Bar(
                x=top12["Puntaje_Maximo"],
                y=top12["Nombre_Monitoreo"].str[:35],
                orientation="h",
                marker_color=colors_t,
                text=top12.apply(
                    lambda r: f"{r['Puntaje_Maximo']} pts · {r['Txns_Con_Alerta']} alertas", axis=1
                ),
                textposition="outside",
            ))
            fig_top.update_layout(
                title="Top terceros por puntaje de riesgo",
                xaxis_title="Puntaje máximo alcanzado",
                height=max(360, len(top12)*30+80), **_L,
            )
            st.plotly_chart(fig_top, use_container_width=True)

    with r2b:
        # Tipos de infracción detectadas (dona)
        inf_counts = stats["infraction_counts"]
        inf_df = (pd.DataFrame(list(inf_counts.items()), columns=["Tipo","N"])
                  .sort_values("N", ascending=False))
        inf_df = inf_df[inf_df["N"] > 0]
        if not inf_df.empty:
            fig_inf = go.Figure(go.Pie(
                labels=inf_df["Tipo"],
                values=inf_df["N"],
                hole=0.48,
                marker_colors=["#7C0000","#DC2626","#D97706","#0057D8","#94A3B8","#16A34A"],
                textinfo="label+percent",
                textfont_size=10,
            ))
            fig_inf.update_layout(title="Distribución por tipo de infracción",
                                  showlegend=False, **_L)
            st.plotly_chart(fig_inf, use_container_width=True)

    # ── Fila 3: exposición financiera por nivel y frecuencia de riesgo ────────
    r3a, r3b = st.columns(2)

    with r3a:
        # Importe en riesgo por nivel (waterfall visual con barras)
        imp_nivel = (res.groupby("Nivel_Riesgo")[col_importe]
                     .sum().reindex(_RISK_ORDER, fill_value=0).reset_index())
        imp_nivel.columns = ["Nivel","Importe"]
        imp_nivel["Color"] = imp_nivel["Nivel"].map(RISK_COLORS)
        imp_nivel["Pct"] = (imp_nivel["Importe"] / imp_nivel["Importe"].sum() * 100).round(1)

        fig_imp = go.Figure(go.Bar(
            x=imp_nivel["Nivel"],
            y=imp_nivel["Importe"],
            marker_color=imp_nivel["Color"],
            text=imp_nivel.apply(lambda r: f"${r['Importe']:,.0f}<br>{r['Pct']}%", axis=1),
            textposition="outside",
        ))
        fig_imp.update_layout(title="Exposición financiera por nivel de riesgo",
                              yaxis_title="Importe ($)", **_L)
        st.plotly_chart(fig_imp, use_container_width=True)

    with r3b:
        # Scatter: frecuencia de riesgo % vs importe promedio (terceros alertados)
        sc_df = t_df[t_df["Nivel_Riesgo"] != "SIN ALERTA"].copy()
        if not sc_df.empty:
            fig_sc = px.scatter(
                sc_df,
                x="Frecuencia_Riesgo_Pct",
                y="Importe_Promedio",
                color="Nivel_Riesgo",
                color_discrete_map=RISK_COLORS,
                size="Total_Transacciones",
                hover_name="Nombre_Monitoreo",
                hover_data={"Puntaje_Maximo": True,
                            "Txns_Con_Alerta": True,
                            "Tipos_Infraccion": True},
                labels={
                    "Frecuencia_Riesgo_Pct": "% transacciones con alerta",
                    "Importe_Promedio": "Importe promedio ($)",
                },
                title="Frecuencia de alerta vs Importe promedio por tercero",
            )
            fig_sc.update_layout(**_L)
            # Cuadrante crítico
            med_freq = sc_df["Frecuencia_Riesgo_Pct"].median()
            med_imp  = sc_df["Importe_Promedio"].median()
            fig_sc.add_hline(y=med_imp,  line_dash="dot", line_color="#94A3B8", opacity=0.5)
            fig_sc.add_vline(x=med_freq, line_dash="dot", line_color="#94A3B8", opacity=0.5)
            st.plotly_chart(fig_sc, use_container_width=True)

    # ── Fila 4: línea temporal de alertas (si hay fecha) ─────────────────────
    if "Dia_Semana" in res.columns and res["Alerta_Fecha"].eq("SÍ").any():
        r4a, r4b = st.columns(2)

        with r4a:
            # Alertas por día de la semana
            dias_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            dias_es    = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
                          "Thursday":"Jueves","Friday":"Viernes",
                          "Saturday":"Sábado","Sunday":"Domingo"}
            if "Dia_Semana" in res.columns:
                dia_counts = (res["Dia_Semana"].value_counts()
                              .reindex(dias_order, fill_value=0).reset_index())
                dia_counts.columns = ["Dia_EN","N"]
                dia_counts["Dia"] = dia_counts["Dia_EN"].map(dias_es)
                dia_counts["Color"] = dia_counts["Dia_EN"].apply(
                    lambda d: "#DC2626" if d in ["Saturday","Sunday"] else "#003087"
                )
                fig_dias = go.Figure(go.Bar(
                    x=dia_counts["Dia"], y=dia_counts["N"],
                    marker_color=dia_counts["Color"],
                    text=dia_counts["N"], textposition="outside",
                ))
                fig_dias.update_layout(title="Transacciones por día de la semana<br><sub>Rojo = fin de semana (alerta)</sub>",
                                       yaxis_title="N° transacciones", **_L)
                st.plotly_chart(fig_dias, use_container_width=True)

        with r4b:
            # Desfase de contabilización
            if "Dias_Desfase" in res.columns and res["Dias_Desfase"].notna().any():
                desfase_valid = res[res["Dias_Desfase"].notna()]["Dias_Desfase"]
                fig_def = px.histogram(
                    desfase_valid, nbins=30,
                    color_discrete_sequence=["#0057D8"],
                    title="Distribución del desfase de contabilización",
                    labels={"value":"Días entre documento y contabilización",
                            "count":"N° transacciones"},
                )
                fig_def.add_vline(x=60, line_dash="dash", line_color="#DC2626",
                                  annotation_text="Límite 60 días", annotation_font_color="#DC2626")
                fig_def.update_layout(**_L)
                st.plotly_chart(fig_def, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TERCEROS INFRACTORES
# ══════════════════════════════════════════════════════════════════════════════
with tab_terceros:
    st.markdown("### 👤 Terceros infractores — Perfil de cumplimiento")
    st.caption(
        "Clasificación basada en el **puntaje máximo** de sus transacciones. "
        "Si >50% de sus movimientos generan alguna alerta, el nivel sube automáticamente un escalón."
    )

    tf1, tf2, tf3 = st.columns(3)
    with tf1:
        filtro_nivel = st.multiselect("Nivel de riesgo",
                                      _RISK_ORDER, default=["RIESGO ALTO","RIESGO MEDIO"],
                                      key="tab2_nivel")
    with tf2:
        min_txns = st.number_input("Mínimo de transacciones", min_value=1, value=1, step=1)
    with tf3:
        buscar = st.text_input("Buscar tercero", placeholder="Nombre parcial...")

    ft = t_df.copy()
    if filtro_nivel:
        ft = ft[ft["Nivel_Riesgo"].isin(filtro_nivel)]
    ft = ft[ft["Total_Transacciones"] >= min_txns]
    if buscar:
        ft = ft[ft["Nombre_Monitoreo"].str.contains(buscar, case=False, na=False)]

    st.markdown(f"**{len(ft):,} terceros** con los filtros aplicados")
    st.markdown("---")

    for _, row in ft.iterrows():
        nivel = row["Nivel_Riesgo"]
        emoji = _RISK_EMOJIS.get(nivel, "")
        bg, border = _RISK_BG.get(nivel, ("#F8FAFC","#E2E8F0"))
        veredicto  = row.get("Veredicto_Compliance","—")
        sev        = row.get("Severidad_Maxima","—")

        with st.expander(
            f"{emoji} **{row['Nombre_Monitoreo'][:55]}** — {veredicto}  "
            f"| Puntaje: {row['Puntaje_Maximo']} pts "
            f"| {row['Total_Transacciones']} transacciones "
            f"| {row['Frecuencia_Riesgo_Pct']}% alertadas"
        ):
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Importe total",     f"${row['Importe_Total']:,.0f}")
            c2.metric("Importe promedio",  f"${row['Importe_Promedio']:,.0f}")
            c3.metric("Puntaje máximo",    f"{row['Puntaje_Maximo']} pts")
            c4.metric("% alertadas",       f"{row['Frecuencia_Riesgo_Pct']}%")
            c5.metric("Severidad",         sev)

            st.markdown(f"""
            <div style='background:{bg};border:1px solid {border};
                        border-radius:8px;padding:12px 16px;font-size:0.82rem;margin:8px 0;'>
              <b>Infracciones detectadas:</b> {row.get('Tipos_Infraccion','—')}<br/>
              <span style='color:#64748B;'>
                Alertas precio: <b>{row['Alertas_Precio']}</b> &nbsp;|&nbsp;
                Palabras: <b>{row['Alertas_Palabra']}</b> &nbsp;|&nbsp;
                Identidad: <b>{row['Alertas_Identidad']}</b> &nbsp;|&nbsp;
                Fecha: <b>{row['Alertas_Fecha']}</b> &nbsp;|&nbsp;
                Desfase: <b>{row['Alertas_Desfase']}</b> &nbsp;|&nbsp;
                Evasión: <b>{row['Evasion']}</b><br/>
                Montos redondos: <b>{row.get('Montos_Redondos',0)}</b> &nbsp;|&nbsp;
                Duplicados: <b>{row.get('Montos_Duplicados',0)}</b> &nbsp;|&nbsp;
                Outliers: <b>{row.get('Outliers_Estadisticos',0)}</b> &nbsp;|&nbsp;
                Fraccionamiento: <b>{row.get('Fraccionamiento',0)}</b>
              </span>
            </div>
            """, unsafe_allow_html=True)

            txns_t = res[res["Nombre_Monitoreo"] == row["Nombre_Monitoreo"]]
            cols_show = [c for c in [
                col_importe, "Desviacion_Vs_Promedio_Pct", "Puntaje", "Nivel_Riesgo",
                "Infracciones_Detectadas", "Severidad_Maxima",
                "Alerta_Precio", "Alerta_Palabra", "Palabra_Detectada",
                "Filtro_Evasion", "Alerta_Fecha", "Dia_Semana",
                "Alerta_Desfase", "Dias_Desfase", "Alerta_Identidad",
                "Monto_Redondo", "Monto_Duplicado", "Outlier_Estadistico",
                "Posible_Fraccionamiento",
            ] if c in txns_t.columns]
            st.dataframe(txns_t[cols_show].reset_index(drop=True), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — INFRACCIONES
# ══════════════════════════════════════════════════════════════════════════════
with tab_infracc:
    st.markdown("### 🚨 Catálogo de infracciones detectadas")
    st.markdown(
        "El motor clasifica cada transacción irregular en una o más **categorías de infracción** "
        "según la combinación de alertas activadas. Esta vista te permite identificar qué tipo de "
        "actos antiéticos predominan en la base de datos."
    )

    for defn in INFRACTION_DEFINITIONS:
        count = int(res.apply(defn["check"], axis=1).sum())
        if count == 0:
            continue

        sev   = defn["severidad"]
        color = SEVERITY_COLORS.get(sev, "#64748B")
        bg    = {"CRÍTICA":"#FEF2F2","ALTA":"#FFF5F5","MEDIA":"#FFFBEB","BAJA":"#EFF6FF"}.get(sev,"#F8FAFC")
        bd    = {"CRÍTICA":"#FECACA","ALTA":"#FECACA","MEDIA":"#FDE68A","BAJA":"#BFDBFE"}.get(sev,"#E2E8F0")

        with st.expander(
            f"{defn['icono']} **{defn['nombre']}** — Severidad: {sev} — {count:,} transacciones"
        ):
            st.markdown(f"""
            <div style='background:{bg};border-left:4px solid {color};
                        border-radius:6px;padding:10px 14px;font-size:0.84rem;margin-bottom:10px;'>
              <b>Definición:</b> {defn['descripcion']}<br/>
              <b>Severidad:</b> <span style='color:{color};font-weight:700;'>{sev}</span> &nbsp;|&nbsp;
              <b>Transacciones afectadas:</b> {count:,} &nbsp;|&nbsp;
              <b>% del total:</b> {count/len(res)*100:.1f}%
            </div>
            """, unsafe_allow_html=True)

            # Terceros involucrados en esta infracción
            mask = res.apply(defn["check"], axis=1)
            infr_txns = res[mask].copy()

            ia, ib = st.columns(2)
            with ia:
                terceros_involucrados = (infr_txns["Nombre_Monitoreo"]
                                         .value_counts().head(10).reset_index())
                terceros_involucrados.columns = ["Tercero","N° transacciones"]
                fig_ti = px.bar(terceros_involucrados, x="N° transacciones", y="Tercero",
                                orientation="h", color_discrete_sequence=[color],
                                title=f"Top 10 terceros — {defn['nombre']}")
                fig_ti.update_layout(**_L, height=300)
                st.plotly_chart(fig_ti, use_container_width=True)

            with ib:
                imp_infr = infr_txns[col_importe].describe()
                st.markdown(f"""
                <div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;
                            padding:14px;font-size:0.82rem;line-height:2;'>
                  <b>Importe total comprometido:</b><br/>
                  <span style='font-size:1.2rem;font-weight:800;color:{color};'>
                    ${infr_txns[col_importe].sum():,.0f}
                  </span><br/>
                  Promedio: ${imp_infr['mean']:,.0f}<br/>
                  Máximo:   ${imp_infr['max']:,.0f}<br/>
                  Mínimo:   ${imp_infr['min']:,.0f}<br/>
                  Terceros únicos: {infr_txns['Nombre_Monitoreo'].nunique()}
                </div>
                """, unsafe_allow_html=True)

            st.dataframe(
                infr_txns[[col_tercero, col_importe, "Puntaje", "Nivel_Riesgo",
                            "Infracciones_Detectadas"]
                           ].head(50).reset_index(drop=True),
                use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ANOMALÍAS ESTADÍSTICAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_anomalias:
    st.markdown("### 🔬 Anomalías estadísticas en la base de datos")
    st.markdown(
        "Irregularidades detectadas mediante técnicas cuantitativas, independientes "
        "del diccionario de palabras. Indicios de **fraude estructurado**, "
        "**pagos duplicados**, **montos artificiales** y **valores atípicos**."
    )

    anomaly_defs = [
        {
            "col": "Monto_Redondo",
            "nombre": "Montos redondos sospechosos",
            "icono": "🔢",
            "desc": "Importes exactamente múltiplos de $100k, $500k, $1M o $5M. "
                    "Los pagos legítimos raramente son cifras perfectamente redondas; "
                    "esto puede indicar montos pactados o inventados.",
        },
        {
            "col": "Monto_Duplicado",
            "nombre": "Montos duplicados por tercero",
            "icono": "🔁",
            "desc": "El mismo tercero registra el mismo importe más de una vez. "
                    "Puede ser un doble pago, una factura duplicada o una contabilización errónea.",
        },
        {
            "col": "Outlier_Estadistico",
            "nombre": "Outliers estadísticos (z-score > 2.5)",
            "icono": "📊",
            "desc": "Transacciones cuyo importe se aleja más de 2.5 desviaciones estándar "
                    "del promedio global. Valores anómalos que merecen revisión.",
        },
        {
            "col": "Posible_Fraccionamiento",
            "nombre": "Posible fraccionamiento de pagos",
            "icono": "✂️",
            "desc": "Tercero con 3 o más transacciones de importe casi idéntico (±5%). "
                    "Patrón clásico para evadir umbrales de aprobación o control.",
        },
    ]

    for defn in anomaly_defs:
        col_a = defn["col"]
        if col_a not in res.columns:
            continue
        sub = res[res[col_a] == "SÍ"]
        n   = len(sub)
        if n == 0:
            continue

        with st.expander(f"{defn['icono']} **{defn['nombre']}** — {n:,} transacciones"):
            st.markdown(f"""
            <div style='background:#FFF7ED;border-left:4px solid #D97706;
                        border-radius:6px;padding:10px 14px;font-size:0.84rem;margin-bottom:10px;'>
              {defn['desc']}<br/>
              <b>Importe total en este grupo:</b>
              <span style='color:#D97706;font-weight:700;'> ${sub[col_importe].sum():,.0f}</span> &nbsp;|&nbsp;
              <b>Terceros únicos:</b> {sub['Nombre_Monitoreo'].nunique()}
            </div>
            """, unsafe_allow_html=True)

            aa, ab = st.columns(2)
            with aa:
                t_breakdown = sub["Nombre_Monitoreo"].value_counts().head(10).reset_index()
                t_breakdown.columns = ["Tercero","N"]
                fig_ab = px.bar(t_breakdown, x="N", y="Tercero", orientation="h",
                                color_discrete_sequence=["#D97706"],
                                title="Terceros más frecuentes en esta anomalía")
                fig_ab.update_layout(**_L, height=300)
                st.plotly_chart(fig_ab, use_container_width=True)

            with ab:
                fig_imp_a = px.histogram(
                    sub, x=col_importe, nbins=20,
                    color_discrete_sequence=["#D97706"],
                    title="Distribución de importes en esta anomalía",
                    labels={col_importe: "Importe ($)"},
                )
                fig_imp_a.update_layout(**_L, height=300)
                st.plotly_chart(fig_imp_a, use_container_width=True)

            show_a = [c for c in ["Nombre_Monitoreo", col_importe, "Nivel_Riesgo",
                                  "Infracciones_Detectadas", "Puntaje"] if c in sub.columns]
            st.dataframe(sub[show_a].head(50).reset_index(drop=True), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — POR TRANSACCIÓN
# ══════════════════════════════════════════════════════════════════════════════
with tab_txns:
    st.markdown("### 📋 Detalle por transacción")

    rf1, rf2, rf3 = st.columns(3)
    with rf1:
        f_nivel = st.multiselect("Nivel de riesgo", _RISK_ORDER,
                                 default=["RIESGO ALTO","RIESGO MEDIO"], key="t5_n")
    with rf2:
        solo_alertas = st.checkbox("Solo transacciones con alerta", value=True)
    with rf3:
        buscar_t = st.text_input("Buscar tercero", placeholder="Nombre parcial...", key="t5_b")

    txn_d = res.copy()
    if f_nivel:
        txn_d = txn_d[txn_d["Nivel_Riesgo"].isin(f_nivel)]
    if solo_alertas:
        txn_d = txn_d[txn_d["Puntaje"] > 0]
    if buscar_t:
        txn_d = txn_d[txn_d["Nombre_Monitoreo"].str.contains(buscar_t, case=False, na=False)]

    st.markdown(f"**{len(txn_d):,} transacciones** con los filtros aplicados")

    motor_cols = [c for c in [
        "Nombre_Monitoreo", col_importe, "Desviacion_Vs_Promedio_Pct",
        "Puntaje", "Nivel_Riesgo", "Severidad_Maxima", "Infracciones_Detectadas",
        "Alerta_Precio", "Alerta_Palabra", "Palabra_Detectada",
        "Filtro_Evasion", "Alerta_Fecha", "Dia_Semana",
        "Alerta_Desfase", "Dias_Desfase", "Alerta_Identidad",
        "Monto_Redondo", "Monto_Duplicado", "Outlier_Estadistico", "Posible_Fraccionamiento",
    ] if c in txn_d.columns]

    st.dataframe(txn_d[motor_cols].reset_index(drop=True),
                 use_container_width=True, height=420)

    if not txn_d.empty and txn_d["Puntaje"].max() > 0:
        fig_dist_p = px.histogram(
            txn_d[txn_d["Puntaje"] > 0], x="Puntaje",
            color="Nivel_Riesgo", color_discrete_map=RISK_COLORS,
            nbins=20, title="Distribución de puntajes — transacciones alertadas",
            labels={"Puntaje":"Puntaje de riesgo","count":"N° transacciones"},
        )
        fig_dist_p.update_layout(**_L)
        st.plotly_chart(fig_dist_p, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — EXPORTAR REPORTE
# ══════════════════════════════════════════════════════════════════════════════
with tab_export:
    st.markdown("### ⬇️ Exportar reporte de cumplimiento")
    st.markdown(
        "El reporte Excel incluye **5 hojas**: Resumen ejecutivo por tercero, "
        "Detalle de transacciones, Solo riesgo alto, Anomalías estadísticas y Glosario."
    )

    motor_exp = [c for c in [
        "Nombre_Monitoreo", col_importe, "Desviacion_Vs_Promedio_Pct",
        "Puntaje", "Nivel_Riesgo", "Severidad_Maxima", "Infracciones_Detectadas",
        "Alerta_Precio", "Alerta_Palabra", "Palabra_Detectada",
        "Filtro_Evasion", "Long_Descripcion", "Alerta_Fecha", "Dia_Semana",
        "Alerta_Desfase", "Dias_Desfase", "Alerta_Identidad",
        "Monto_Redondo", "Monto_Duplicado", "Outlier_Estadistico", "Posible_Fraccionamiento",
    ] if c in res.columns]

    ea, eb = st.columns(2)

    with ea:
        st.markdown("#### 📊 Reporte completo (Excel 5 hojas)")
        if st.button("📥 Generar Excel de cumplimiento", type="primary",
                     use_container_width=True):
            output = io.BytesIO()

            glosario_data = {
                "Campo": [
                    "Puntaje","Nivel_Riesgo","Severidad_Maxima","Infracciones_Detectadas",
                    "Alerta_Precio","Alerta_Palabra","Filtro_Evasion","Alerta_Fecha",
                    "Alerta_Desfase","Alerta_Identidad",
                    "Monto_Redondo","Monto_Duplicado","Outlier_Estadistico","Posible_Fraccionamiento",
                    "Desviacion_Vs_Promedio_Pct","Frecuencia_Riesgo_Pct","Veredicto_Compliance",
                ],
                "Descripción": [
                    "Puntos acumulados en la transacción (máx 100)",
                    "RIESGO ALTO ≥41 pts | MEDIO 11-40 | BAJO 1-10 | SIN ALERTA",
                    "Peor nivel de infracción según combinación de alertas",
                    "Categorías de infracción detectadas en la transacción",
                    "Importe >130% del promedio histórico del tercero (50 pts)",
                    "Se encontró término del diccionario de riesgo en la descripción (40 pts)",
                    "Descripción combinada con menos de 20 caracteres",
                    "Transacción registrada en sábado o domingo (3 pts)",
                    "Más de 60 días entre fecha documento y contabilización (2 pts)",
                    "Tercero o número de documento vacíos (5 pts)",
                    "Importe exactamente múltiplo de $100k, $500k, $1M o $5M",
                    "Mismo tercero con el mismo importe más de una vez",
                    "Importe a más de 2.5 desviaciones estándar del promedio global",
                    "Tercero con ≥3 transacciones de importe casi idéntico (±5%)",
                    "% de diferencia entre el importe y el promedio histórico del tercero",
                    "% de transacciones del tercero que generaron alguna alerta",
                    "⛔ MONITOREO URGENTE | ⚠️ INVESTIGAR | 🔵 OBSERVAR | ✅ CONFORME",
                ],
            }

            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # Hoja 1: Resumen por tercero
                t_exp = t_df.rename(columns={"Nombre_Monitoreo":"Tercero"})
                t_exp.to_excel(writer, sheet_name="1_Resumen_Terceros", index=False)

                # Hoja 2: Detalle transacciones
                res[motor_exp].to_excel(writer, sheet_name="2_Detalle_Transacciones", index=False)

                # Hoja 3: Solo riesgo alto
                solo_alto = res[res["Nivel_Riesgo"] == "RIESGO ALTO"][motor_exp]
                solo_alto.to_excel(writer, sheet_name="3_Solo_Riesgo_Alto", index=False)

                # Hoja 4: Anomalías estadísticas
                anomaly_cols = [c for c in ["Nombre_Monitoreo", col_importe,
                                            "Monto_Redondo","Monto_Duplicado",
                                            "Outlier_Estadistico","Posible_Fraccionamiento",
                                            "Nivel_Riesgo"] if c in res.columns]
                res[anomaly_cols].to_excel(writer, sheet_name="4_Anomalias", index=False)

                # Hoja 5: Glosario
                pd.DataFrame(glosario_data).to_excel(writer, sheet_name="5_Glosario", index=False)

            fname = f"ADIC_Cumplimiento_{source[:20].replace(' ','_')}.xlsx"
            st.download_button(
                "💾 Descargar reporte Excel de cumplimiento",
                data=output.getvalue(),
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, type="primary",
            )

    with eb:
        st.markdown("#### 🔴 Terceros para monitoreo urgente (CSV)")
        criticos = t_df[t_df["Nivel_Riesgo"] == "RIESGO ALTO"]
        st.metric("Terceros en RIESGO ALTO", len(criticos))
        if not criticos.empty:
            csv_crit = criticos.rename(columns={"Nombre_Monitoreo":"Tercero"}).to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Descargar CSV — Terceros críticos",
                data=csv_crit,
                file_name=f"ADIC_Terceros_Criticos_{source[:15].replace(' ','_')}.csv",
                mime="text/csv", use_container_width=True,
            )

        st.markdown("---")
        st.markdown("#### ⚠️ Infracciones por categoría (CSV)")
        inf_rows = []
        for defn in INFRACTION_DEFINITIONS:
            mask = res.apply(defn["check"], axis=1)
            sub  = res[mask]
            if len(sub) > 0:
                inf_rows.append({
                    "Tipo_Infraccion": defn["nombre"],
                    "Severidad":       defn["severidad"],
                    "N_Transacciones": len(sub),
                    "Importe_Total":   sub[col_importe].sum(),
                    "Terceros_Unicos": sub["Nombre_Monitoreo"].nunique(),
                    "Pct_Del_Total":   f"{len(sub)/len(res)*100:.1f}%",
                })
        if inf_rows:
            inf_summary = pd.DataFrame(inf_rows)
            st.download_button(
                "📥 Descargar CSV — Resumen de infracciones",
                data=inf_summary.to_csv(index=False).encode("utf-8"),
                file_name=f"ADIC_Infracciones_{source[:15].replace(' ','_')}.csv",
                mime="text/csv", use_container_width=True,
            )

    st.markdown("---")
    st.markdown("""
    #### 📌 Glosario rápido de campos
    | Campo | Significado |
    |---|---|
    | **Puntaje** | Puntos acumulados por transacción (máx 100) |
    | **Nivel_Riesgo** | ALTO ≥41 · MEDIO 11-40 · BAJO 1-10 pts |
    | **Infracciones_Detectadas** | Categoría de acto antiético según combinación de alertas |
    | **Severidad_Maxima** | CRÍTICA / ALTA / MEDIA según la peor infracción |
    | **Veredicto_Compliance** | ⛔ Monitoreo urgente · ⚠️ Investigar · 🔵 Observar · ✅ Conforme |
    | **Monto_Redondo** | Múltiplo exacto de $100k, $500k, $1M o $5M |
    | **Posible_Fraccionamiento** | Tercero con ≥3 pagos casi idénticos (evasión de controles) |
    | **Outlier_Estadistico** | Importe a >2.5 desviaciones del promedio global |
    | **Frecuencia_Riesgo_Pct** | % de transacciones del tercero que generaron alguna alerta |
    """)
