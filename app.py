"""
ADIC Platform — Procaps
Automated Data Intelligence & Custom Reporting
Herramienta interna de Business Intelligence
"""

import streamlit as st

st.set_page_config(
    page_title="ADIC · Procaps",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "ADIC Platform — Herramienta interna Procaps. Uso exclusivo del equipo.",
    },
)

# ── Estilos globales ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700;9..40,800&family=DM+Mono:wght@400;500&display=swap');

/* Reset & base */
.stApp { background: #F4F6FA !important; font-family: 'DM Sans', sans-serif !important; }
* { font-family: 'DM Sans', sans-serif !important; }
code, pre { font-family: 'DM Mono', monospace !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #1A1A2E !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] a { color: #00BFFF !important; }

/* Métricas */
[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
[data-testid="stMetricValue"] {
    color: #003087 !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}
[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

/* Botones primarios */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #003087 0%, #0057D8 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,48,135,0.3) !important;
}
.stButton > button:not([kind="primary"]) {
    background: #FFFFFF !important;
    color: #003087 !important;
    border: 1.5px solid #003087 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}

/* DataFrames */
[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    overflow: hidden;
    background: #fff !important;
}

/* Tabs */
[data-testid="stTabs"] button {
    font-weight: 600 !important;
    color: #64748B !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #003087 !important;
    border-bottom-color: #003087 !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput input {
    background: #FFFFFF !important;
    border: 1.5px solid #E2E8F0 !important;
    border-radius: 8px !important;
    color: #1E293B !important;
}

/* HR */
hr { border-color: #E2E8F0 !important; margin: 20px 0 !important; }

/* Alerts */
[data-testid="stAlert"] { border-radius: 8px !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #F1F5F9; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }

/* Remove default top padding */
.block-container { padding-top: 2rem !important; }

h1, h2, h3, h4 { color: #1E293B !important; font-family: 'DM Sans', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

# ── Estado de sesión inicial ──────────────────────────────────────────────────
defaults = {
    "df": None,
    "quality_score": None,
    "quality_report": None,
    "source_name": None,
    "alerts": [],
    "narration": None,
    "authenticated": False,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Autenticación simple por contraseña ──────────────────────────────────────
def check_password():
    """Devuelve True si el usuario ingresó la contraseña correcta."""
    def verify():
        try:
            correct = st.secrets.get("APP_PASSWORD", "procaps2025")
        except Exception:
            correct = "procaps2025"
        if st.session_state.get("password_input") == correct:
            st.session_state.authenticated = True
        else:
            st.session_state.auth_error = True

    if st.session_state.get("authenticated"):
        return True

    # Pantalla de login
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("""
        <div style='text-align:center; padding: 60px 0 30px;'>
            <div style='font-size:56px; margin-bottom:12px;'>💊</div>
            <h1 style='font-size:2rem; font-weight:800; color:#003087; margin:0;'>ADIC Platform</h1>
            <p style='color:#64748B; margin:8px 0 32px; font-size:0.95rem;'>
                Herramienta de Business Intelligence · Procaps
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='background:#fff; border:1px solid #E2E8F0; border-radius:16px;
                    padding:32px; box-shadow:0 4px 24px rgba(0,48,135,0.08);'>
        """, unsafe_allow_html=True)

        st.text_input(
            "Contraseña de acceso",
            type="password",
            key="password_input",
            placeholder="Ingresa la contraseña del equipo...",
        )
        st.button("Acceder →", type="primary", on_click=verify, use_container_width=True)

        if st.session_state.get("auth_error"):
            st.error("Contraseña incorrecta. Contacta al administrador.")
            st.session_state.auth_error = False

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <p style='text-align:center; color:#94A3B8; font-size:0.78rem; margin-top:24px;'>
            🔒 Acceso restringido — Solo equipo autorizado Procaps<br>
            Los datos analizados permanecen en tu sesión local y no se almacenan en ningún servidor externo.
        </p>
        """, unsafe_allow_html=True)
    return False

if not check_password():
    st.stop()

# ── Sidebar de navegación ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:16px 0 24px;'>
        <div style='display:flex; align-items:center; gap:10px;'>
            <span style='font-size:32px;'>💊</span>
            <div>
                <div style='font-weight:800; font-size:1.1rem; color:#fff;'>ADIC Platform</div>
                <div style='font-size:0.72rem; color:#94A3B8;'>Procaps · Uso Interno</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div style='font-size:0.7rem; color:#64748B; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;'>Módulos</div>", unsafe_allow_html=True)

    # Estado de sesión en sidebar
    if st.session_state.df is not None:
        df = st.session_state.df
        st.markdown(f"""
        <div style='background:rgba(0,191,255,0.08); border:1px solid rgba(0,191,255,0.2);
                    border-radius:8px; padding:12px; margin-bottom:16px;'>
            <div style='font-size:0.7rem; color:#00BFFF; font-weight:600; margin-bottom:6px;'>DATASET ACTIVO</div>
            <div style='font-size:0.82rem; color:#E2E8F0; font-weight:500;'>{st.session_state.source_name}</div>
            <div style='font-size:0.72rem; color:#94A3B8; margin-top:4px;'>{len(df):,} filas · {len(df.columns)} columnas</div>
            <div style='font-size:0.72rem; color:#94A3B8;'>Quality: {st.session_state.quality_score:.0f}/100</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:rgba(255,200,0,0.08); border:1px solid rgba(255,200,0,0.2);
                    border-radius:8px; padding:12px; margin-bottom:16px; font-size:0.78rem; color:#FFB800;'>
            ⚠️ Sin datos cargados
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.72rem; color:#64748B; margin-top:8px; line-height:1.6;'>
        🔒 <b style='color:#94A3B8;'>Privacidad de datos</b><br>
        Los datos no salen de tu navegador ni se almacenan en servidores externos.
        La IA procesa solo estadísticas agregadas, nunca registros individuales.
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Cerrar sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Header principal ──────────────────────────────────────────────────────────
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("""
    <h1 style='font-size:2.2rem; font-weight:800; color:#003087; margin:0 0 4px;'>
        ADIC Platform
        <span style='font-size:1rem; font-weight:500; color:#64748B; margin-left:10px;'>Procaps</span>
    </h1>
    <p style='color:#64748B; margin:0; font-size:0.95rem;'>
        Automated Data Intelligence & Custom Reporting — Herramienta interna del equipo
    </p>
    """, unsafe_allow_html=True)

with col_status:
    st.markdown("""
    <div style='text-align:right; padding-top:8px;'>
        <span style='background:#DCFCE7; color:#16A34A; font-size:0.72rem; font-weight:600;
                     padding:4px 12px; border-radius:20px;'>● Sistema operativo</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── Cards de módulos ──────────────────────────────────────────────────────────
st.markdown("#### Módulos disponibles")

cards = [
    ("📂", "Carga de Datos", "Sube Excel o CSV. Análisis de calidad automático.", "#003087", "FASE 1"),
    ("📊", "Dashboard", "Gráficos interactivos y KPIs con filtros cruzados.", "#003087", "FASE 1"),
    ("🤖", "Asistente IA", "El asistente analiza tu dataset y genera reportes en lenguaje natural.", "#0057D8", "FASE 2"),
    ("📄", "Reporte PDF", "Exporta reportes ejecutivos con identidad Procaps.", "#0057D8", "FASE 2"),
    ("🔔", "Alertas", "Configura umbrales y detecta registros fuera de rango.", "#0057D8", "FASE 2"),
]

cols = st.columns(len(cards))
for col, (icon, title, desc, color, badge) in zip(cols, cards):
    with col:
        st.markdown(f"""
        <div style='background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px;
                    padding:20px 16px; height:170px; position:relative;
                    box-shadow:0 2px 8px rgba(0,48,135,0.06); transition:all 0.2s;'>
            <span style='position:absolute; top:12px; right:12px;
                         background:{color}15; color:{color};
                         font-size:0.6rem; font-weight:700; letter-spacing:0.8px;
                         padding:2px 8px; border-radius:20px; border:1px solid {color}30;'>
                {badge}
            </span>
            <div style='font-size:26px; margin-bottom:10px;'>{icon}</div>
            <div style='font-weight:700; font-size:0.92rem; color:#1E293B; margin-bottom:6px;'>{title}</div>
            <div style='font-size:0.76rem; color:#64748B; line-height:1.45;'>{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── KPIs de sesión ─────────────────────────────────────────────────────────────
st.markdown("#### Estado de la sesión")
m1, m2, m3, m4 = st.columns(4)

df_state = st.session_state.df
with m1:
    st.metric("Filas cargadas", f"{len(df_state):,}" if df_state is not None else "—")
with m2:
    st.metric("Columnas", len(df_state.columns) if df_state is not None else "—")
with m3:
    st.metric("Data Quality Score",
              f"{st.session_state.quality_score:.0f}/100" if st.session_state.quality_score else "—")
with m4:
    st.metric("Fuente activa", st.session_state.source_name or "—")

st.markdown("---")

# ── Aviso de privacidad ───────────────────────────────────────────────────────
with st.expander("🔒 Aviso de privacidad y habeas data — Leer antes de usar"):
    st.markdown("""
    **Esta herramienta fue diseñada con privacidad desde su arquitectura:**

    1. **Los datos NO salen de tu sesión.** Todo el procesamiento ocurre en el servidor de Streamlit asignado a tu sesión, no en servidores de terceros.
    2. **La IA solo recibe estadísticas agregadas**, nunca registros individuales con datos personales. El módulo de narración envía únicamente resúmenes numéricos (sumas, promedios, máximos) a la API de Claude.
    3. **No hay persistencia.** Al cerrar sesión o el navegador, todos los datos se eliminan automáticamente.
    4. **Para datos de nómina o datos sensibles:** usa datasets anonimizados (sin cédulas, nombres completos ni información que identifique personas naturales). Esto cumple con la Ley 1581 de 2012 (Habeas Data Colombia).
    5. **Sin base de datos externa.** ADIC no guarda ningún archivo subido por el usuario.

    > ⚠️ **Recomendación:** Antes de subir cualquier base de datos de RRHH o nómina, reemplaza columnas de identificación personal por códigos internos (ej: `EMP-001` en lugar de número de cédula).
    """)

st.markdown(
    "<p style='text-align:center; color:#94A3B8; font-size:0.78rem; margin-top:8px;'>"
    "ADIC Platform · Procaps · Barranquilla, Colombia · Herramienta de uso interno exclusivo"
    "</p>",
    unsafe_allow_html=True,
)
