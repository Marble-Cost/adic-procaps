"""
Página 5 — Alertas
ADIC Platform · Procaps
"""

import streamlit as st
import pandas as pd

st.markdown("## 🔔 Sistema de Alertas")
st.markdown(
    "Define umbrales sobre variables numéricas. "
    "El sistema detecta automáticamente qué registros están fuera de rango."
)

if st.session_state.get("df") is None:
    st.warning("⚠️ Primero carga datos en la página **Carga de Datos**.")
    if st.button("← Ir a Carga de Datos"):
        st.switch_page("pages/01___Carga_de_Datos.py")
    st.stop()

df = st.session_state.df
num_cols = df.select_dtypes(include="number").columns.tolist()
source = st.session_state.get("source_name", "Dataset")
report_type = st.session_state.get("report_type", "General")

if not num_cols:
    st.info("No se detectaron columnas numéricas en el dataset actual.")
    st.stop()

st.caption(f"Dataset: **{source}** · Tipo: **{report_type}** · {len(df):,} registros")

# ── Alertas predefinidas por tipo de reporte ──────────────────────────────────
PRESET_ALERTS = {
    "Nómina Mensual": [
        {"nombre": "Salario muy alto", "columna": "Salario_Base_COP", "condicion": "Mayor que (>)", "umbral": 10_000_000},
        {"nombre": "Sin neto a pagar", "columna": "Neto_Pagar", "condicion": "Menor que (<)", "umbral": 1_000_000},
    ],
    "Ventas Comercial": [
        {"nombre": "Margen negativo", "columna": "Margen_COP", "condicion": "Menor que (<)", "umbral": 0},
        {"nombre": "Meta no cumplida (<80%)", "columna": "Cumplimiento_Pct", "condicion": "Menor que (<)", "umbral": 80},
    ],
    "Producción / Operaciones": [
        {"nombre": "Eficiencia crítica (<85%)", "columna": "Eficiencia_Pct", "condicion": "Menor que (<)", "umbral": 85},
        {"nombre": "Tasa rechazo alta (>2%)", "columna": "Tasa_Rechazo_Pct", "condicion": "Mayor que (>)", "umbral": 2},
    ],
    "Finanzas y Costos": [
        {"nombre": "Sobrepresupuesto >10%", "columna": "Variacion_Pct", "condicion": "Mayor que (>)", "umbral": 10},
        {"nombre": "Subejecución >20%", "columna": "Variacion_Pct", "condicion": "Menor que (<)", "umbral": -20},
    ],
}

# Sugerir alertas predefinidas
presets = PRESET_ALERTS.get(report_type, [])
available_presets = [p for p in presets if p["columna"] in num_cols]

if available_presets:
    st.markdown("#### 💡 Alertas sugeridas para este tipo de reporte")
    cols_preset = st.columns(len(available_presets))
    for col, preset in zip(cols_preset, available_presets):
        with col:
            if st.button(f"+ {preset['nombre']}", use_container_width=True):
                if "alerts" not in st.session_state:
                    st.session_state.alerts = []
                # Evitar duplicados
                if not any(a["nombre"] == preset["nombre"] for a in st.session_state.alerts):
                    st.session_state.alerts.append(preset)
                    st.rerun()

st.markdown("---")

# ── Crear nueva alerta ────────────────────────────────────────────────────────
st.markdown("### ➕ Nueva alerta personalizada")

with st.form("nueva_alerta"):
    c1, c2, c3 = st.columns(3)
    with c1:
        col_alerta = st.selectbox("Variable a monitorear", num_cols)
    with c2:
        condicion = st.selectbox(
            "Condición",
            ["Mayor que (>)", "Menor que (<)", "Mayor o igual (≥)", "Menor o igual (≤)"],
        )
    with c3:
        default_val = float(df[col_alerta].mean()) if col_alerta else 0.0
        umbral = st.number_input("Umbral", value=default_val)

    nombre_alerta = st.text_input(
        "Nombre de la alerta",
        value=f"Alerta: {col_alerta} {condicion.split('(')[1][:-1]} {umbral:.0f}" if col_alerta else "",
    )
    submitted = st.form_submit_button("✅ Crear alerta", type="primary")

    if submitted and col_alerta:
        alert = {
            "nombre": nombre_alerta or f"{col_alerta} {condicion}",
            "columna": col_alerta,
            "condicion": condicion,
            "umbral": umbral,
        }
        if "alerts" not in st.session_state:
            st.session_state.alerts = []
        st.session_state.alerts.append(alert)
        st.success(f"✅ Alerta '{nombre_alerta}' creada.")

# ── Alertas activas ───────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔍 Alertas activas")

alerts = st.session_state.get("alerts", [])

if not alerts:
    st.markdown("""
    <div style='background:#F8FAFC; border:2px dashed #CBD5E1; border-radius:12px;
                padding:40px; text-align:center;'>
        <div style='font-size:36px; margin-bottom:12px;'>🔔</div>
        <div style='color:#64748B; font-size:0.9rem;'>No hay alertas configuradas.<br>Crea una arriba o usa las sugeridas.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    for i, alert in enumerate(alerts):
        col = alert["columna"]
        if col not in df.columns:
            continue

        cond = alert["condicion"]
        thresh = alert["umbral"]

        # Aplicar condición
        if "Mayor que" in cond and "o igual" not in cond:
            mask = df[col] > thresh
        elif "Menor que" in cond and "o igual" not in cond:
            mask = df[col] < thresh
        elif "Mayor o igual" in cond:
            mask = df[col] >= thresh
        else:
            mask = df[col] <= thresh

        triggered = df[mask]
        count = len(triggered)
        total = len(df)
        pct = count / total * 100 if total > 0 else 0

        status_icon = "🔴" if count > 0 else "🟢"
        border_color = "#FCA5A5" if count > 0 else "#BBF7D0"
        bg_color = "#FFF5F5" if count > 0 else "#F0FDF4"

        st.markdown(f"""
        <div style='background:{bg_color}; border:1px solid {border_color}; border-radius:10px;
                    padding:2px 16px; margin-bottom:4px;'>
            <div style='font-weight:700; color:#1E293B; margin:8px 0 4px;'>
                {status_icon} {alert['nombre']}
                <span style='font-weight:400; color:#64748B; font-size:0.8rem; margin-left:8px;'>
                    {count:,} registros afectados ({pct:.1f}%)
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Ver detalles — {alert['nombre']}"):
            st.markdown(
                f"**Variable:** `{col}` · **Condición:** {cond} · **Umbral:** `{thresh:,.2f}`"
            )

            if count > 0:
                # KPIs rápidos
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Registros disparados", f"{count:,}")
                m2.metric("% del total", f"{pct:.1f}%")
                m3.metric(f"Máx. {col[:15]}", f"{triggered[col].max():,.1f}")
                m4.metric(f"Prom. {col[:15]}", f"{triggered[col].mean():,.1f}")

                # Tabla
                extra_cols = [c for c in df.columns if c != col][:4]
                st.dataframe(
                    triggered[[col] + extra_cols].head(50),
                    use_container_width=True,
                )

                # Exportar
                csv = triggered.to_csv(index=False).encode("utf-8")
                st.download_button(
                    f"⬇️ Exportar registros disparados",
                    data=csv,
                    file_name=f"Alerta_{alert['nombre'].replace(' ', '_')[:20]}.csv",
                    mime="text/csv",
                    key=f"exp_{i}",
                )
            else:
                st.success("✅ Ningún registro supera el umbral actualmente. Todo en orden.")

            if st.button(f"🗑️ Eliminar alerta", key=f"del_{i}"):
                st.session_state.alerts.pop(i)
                st.rerun()

# ── Resumen global ────────────────────────────────────────────────────────────
if alerts:
    st.markdown("---")
    st.markdown("### 📊 Resumen global de alertas")

    summary_data = []
    for alert in alerts:
        col = alert["columna"]
        if col not in df.columns:
            continue
        thresh = alert["umbral"]
        cond = alert["condicion"]
        if "Mayor que" in cond and "o igual" not in cond:
            mask = df[col] > thresh
        elif "Menor que" in cond and "o igual" not in cond:
            mask = df[col] < thresh
        elif "Mayor o igual" in cond:
            mask = df[col] >= thresh
        else:
            mask = df[col] <= thresh

        count = mask.sum()
        summary_data.append({
            "Alerta": alert["nombre"],
            "Variable": col,
            "Condición": cond,
            "Umbral": f"{thresh:,.2f}",
            "Disparadas": count,
            "% del total": f"{count/len(df)*100:.1f}%",
            "Estado": "🔴 Requiere atención" if count > 0 else "🟢 Normal",
        })

    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        # Exportar resumen
        csv_summary = summary_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Exportar resumen de alertas",
            data=csv_summary,
            file_name=f"Procaps_Alertas_Resumen.csv",
            mime="text/csv",
        )
