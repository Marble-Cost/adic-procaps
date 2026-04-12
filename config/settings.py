"""
Configuración global — ADIC Platform Procaps
"""

APP_CONFIG = {
    "name": "ADIC Platform",
    "version": "1.0.0",
    "company": "Procaps",
    "city": "Barranquilla, Colombia",
}

# Paleta corporativa Procaps (azul institucional)
THEME = {
    "primary": "#003087",
    "secondary": "#0057D8",
    "accent": "#00BFFF",
    "bg_light": "#F4F6FA",
    "bg_white": "#FFFFFF",
    "border": "#E2E8F0",
    "text_primary": "#1E293B",
    "text_muted": "#64748B",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
}

QUALITY_WEIGHTS = {
    "completeness": 0.40,
    "uniqueness": 0.30,
    "consistency": 0.30,
}

# Tipos de reporte predefinidos para Procaps
REPORT_TEMPLATES = {
    "Nómina Mensual": {
        "icon": "👥",
        "desc": "Análisis de nómina, deducciones y distribución salarial",
        "cols_hint": ["cargo", "salario", "area", "ciudad"],
    },
    "Ventas Comercial": {
        "icon": "📈",
        "desc": "KPIs de ventas, productos, regiones y representantes",
        "cols_hint": ["producto", "valor", "region", "fecha"],
    },
    "Producción / Operaciones": {
        "icon": "🏭",
        "desc": "Lotes, rendimientos, tiempos de ciclo y calidad",
        "cols_hint": ["lote", "cantidad", "fecha", "linea"],
    },
    "Finanzas y Costos": {
        "icon": "💰",
        "desc": "Presupuesto vs ejecución, centros de costo, variaciones",
        "cols_hint": ["centro_costo", "presupuesto", "ejecucion", "variacion"],
    },
    "General (Libre)": {
        "icon": "📋",
        "desc": "Análisis libre de cualquier dataset",
        "cols_hint": [],
    },
}

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
