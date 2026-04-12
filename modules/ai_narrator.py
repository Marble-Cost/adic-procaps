"""
Módulo de Narración con IA — ADIC Platform Procaps
Privacidad: solo envía estadísticas agregadas a Claude API, nunca registros individuales.
"""

from __future__ import annotations

import os
import pandas as pd

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


def _build_data_summary(df: pd.DataFrame) -> str:
    """
    Construye resumen estadístico AGREGADO para enviar a Claude.
    NUNCA incluye registros individuales ni datos personales identificables.
    """
    lines = []
    lines.append(f"Total de registros: {len(df):,} | Columnas: {len(df.columns)}")
    lines.append(f"Columnas disponibles: {', '.join(df.columns.tolist()[:15])}")

    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        lines.append("\nResumen estadístico (variables numéricas):")
        for col in num_cols[:10]:
            s = df[col].dropna()
            if len(s) == 0:
                continue
            lines.append(
                f"  • {col}: total={s.sum():,.0f} | promedio={s.mean():,.1f} | "
                f"mín={s.min():,.1f} | máx={s.max():,.1f} | desv_est={s.std():,.1f}"
            )

    cat_cols = df.select_dtypes(include="object").columns.tolist()
    if cat_cols:
        lines.append("\nDistribución de categorías:")
        for col in cat_cols[:6]:
            top = df[col].value_counts().head(5)
            items = ", ".join(f"{k}: {v} registros" for k, v in top.items())
            lines.append(f"  • {col}: {items}")

    # Fechas si hay
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if date_cols:
        dc = date_cols[0]
        lines.append(f"\nRango temporal ({dc}): {df[dc].min().date()} → {df[dc].max().date()}")

    return "\n".join(lines)


def generate_narrative(
    df: pd.DataFrame,
    source_name: str,
    quality_score: float,
    report_type: str = "General",
    extra_context: str = "",
) -> str:
    """
    Genera narración ejecutiva usando Claude API.
    Solo envía estadísticas agregadas, nunca datos individuales.
    """
    api_key = _get_api_key()

    if not api_key:
        return (
            "⚠️ **API Key no configurada.**\n\n"
            "Para activar el asistente de IA:\n"
            "1. Obtén tu clave en [console.anthropic.com](https://console.anthropic.com)\n"
            "2. En Streamlit Cloud: ve a **Settings → Secrets** y añade:\n"
            "```toml\nANTHROPIC_API_KEY = 'sk-ant-tu-clave'\n```\n"
            "3. En local: crea el archivo `.streamlit/secrets.toml` con la misma línea.\n\n"
            "> 🔒 La clave nunca se comparte con otros usuarios ni se almacena en el código."
        )

    summary = _build_data_summary(df)

    system_prompt = f"""Eres el asistente analítico interno de Procaps, empresa farmacéutica colombiana líder.
Tu función es generar análisis ejecutivos claros, precisos y accionables en español colombiano.

CONTEXTO ORGANIZACIONAL: Procaps es una empresa farmacéutica con operaciones en producción, ventas, 
RRHH, finanzas y logística. Los reportes son para toma de decisiones internas.

PRIVACIDAD: Solo tienes acceso a estadísticas agregadas, nunca a datos individuales identificables.

Tu respuesta DEBE seguir EXACTAMENTE esta estructura en markdown:

## 📊 ¿Qué muestran los datos?
2-3 oraciones describiendo el panorama general con números concretos.

## 🔍 Hallazgos principales
3-4 hallazgos específicos con cifras. Cada uno en bullet point.

## ⚠️ Puntos de atención
1-2 situaciones que requieren seguimiento o acción. Sé directo.

## ✅ Recomendación ejecutiva
Una acción concreta y prioritaria que el equipo puede tomar esta semana.

---
Tipo de reporte: {report_type}
Calidad de datos: {quality_score}/100 {"(datos confiables)" if quality_score >= 75 else "(revisar calidad antes de decidir)"}
"""

    user_prompt = f"""Analiza este dataset de Procaps y genera el reporte ejecutivo.

Fuente: {source_name}
Tipo: {report_type}

DATOS (solo estadísticas agregadas — sin información personal):
{summary}

Contexto adicional del usuario: {extra_context or 'No especificado.'}

Genera el análisis ejecutivo ahora. Sé específico con los números. No uses frases genéricas."""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    except Exception as e:
        err = str(e)
        if "authentication" in err.lower() or "api_key" in err.lower():
            return "❌ API Key inválida. Verifica que sea correcta en los Secrets de Streamlit."
        elif "rate" in err.lower():
            return "⏳ Límite de solicitudes alcanzado. Espera un momento e intenta de nuevo."
        else:
            return f"❌ Error al conectar con el asistente IA: {err}"


def answer_natural_query(df: pd.DataFrame, question: str) -> str:
    """Responde preguntas en lenguaje natural sobre el dataset."""
    api_key = _get_api_key()
    if not api_key:
        return "⚠️ API Key requerida. Configúrala en los Secrets de Streamlit."

    col_info = []
    for col in df.columns[:20]:
        dtype = str(df[col].dtype)
        if pd.api.types.is_numeric_dtype(df[col]):
            sample_info = f"rango [{df[col].min():.1f} - {df[col].max():.1f}], promedio {df[col].mean():.1f}"
        else:
            unique_vals = df[col].dropna().unique()[:5].tolist()
            sample_info = f"valores ejemplo: {unique_vals}"
        col_info.append(f"  - {col} ({dtype}): {sample_info}")

    schema = "\n".join(col_info)

    system_prompt = """Eres un analista de datos de Procaps. Respondes preguntas sobre datasets 
de forma clara y directa en español. Cuando sea posible, da números concretos.
Si no puedes calcular algo exacto con la información disponible, indica cómo se haría."""

    user_prompt = f"""Dataset con {len(df):,} registros.

Columnas y descripción:
{schema}

Pregunta: {question}

Responde de forma concisa y útil. Si hay un número específico, dalo."""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=600,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except Exception as e:
        return f"❌ Error: {str(e)}"


def _get_api_key() -> str | None:
    """Lee la API key desde variables de entorno o Streamlit secrets."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None
