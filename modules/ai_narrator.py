"""
Módulo de Narración con IA — ADIC Platform
Usa la API de Claude para generar análisis ejecutivos en lenguaje natural.
"""

from __future__ import annotations

import os
import time
import pandas as pd
import anthropic

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
MAX_REINTENTOS = 3
ESPERA_BASE_SEG = 4


def _llamar_claude(client: anthropic.Anthropic, system_prompt: str,
                   user_prompt: str, max_tokens: int = 1200) -> str:
    """
    Llama a Claude con reintentos automáticos si el servidor está saturado (error 529).
    Espera 4 s → 8 s → 16 s antes de rendirse.
    """
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            message = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text

        except anthropic.APIStatusError as e:
            if e.status_code == 529 and intento < MAX_REINTENTOS:
                espera = ESPERA_BASE_SEG * (2 ** (intento - 1))   # 4 s, 8 s, 16 s
                time.sleep(espera)
                continue
            elif e.status_code == 529:
                return (
                    "⏳ Los servidores de Anthropic están temporalmente saturados. "
                    "Espera 1–2 minutos e intenta de nuevo."
                )
            raise

    return "⏳ No fue posible obtener respuesta tras varios intentos. Intenta de nuevo en un momento."


def _build_data_summary(df: pd.DataFrame) -> str:
    """Construye un resumen estadístico del DataFrame para enviar a Claude."""
    lines = [f"Total de registros: {len(df):,} | Total de columnas: {len(df.columns)}"]

    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        lines.append("\nVariables numéricas:")
        for col in num_cols[:8]:
            s = df[col].dropna()
            if len(s) == 0:
                continue
            lines.append(
                f"  • {col}: total = {s.sum():,.2f} | "
                f"promedio = {s.mean():,.2f} | "
                f"mínimo = {s.min():,.2f} | "
                f"máximo = {s.max():,.2f}"
            )

    cat_cols = df.select_dtypes(include="object").columns.tolist()
    if cat_cols:
        lines.append("\nVariables categóricas (top 3 valores más frecuentes):")
        for col in cat_cols[:5]:
            top = df[col].value_counts().head(3)
            items = ", ".join(f"{k} ({v} registros)" for k, v in top.items())
            lines.append(f"  • {col}: {items}")

    return "\n".join(lines)


def generate_narrative(
    df: pd.DataFrame,
    source_name: str,
    quality_score: float,
    extra_context: str = "",
) -> str:
    """
    Llama a la API de Claude y retorna una narración ejecutiva en español.
    Requiere ANTHROPIC_API_KEY en variables de entorno o secrets de Streamlit.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or _get_streamlit_secret()

    if not api_key:
        return (
            "⚠️ **API Key no configurada.** Para activar la narración con IA, "
            "añade `ANTHROPIC_API_KEY` en los Secrets de tu app en Streamlit Cloud "
            "(Settings → Secrets).\n\n"
            "```toml\nANTHROPIC_API_KEY = 'sk-ant-...'\n```"
        )

    summary = _build_data_summary(df)

    system_prompt = """Eres el analista ejecutivo de ADIC Platform, una plataforma de inteligencia \
de negocios para empresas latinoamericanas. Tu función es generar informes ejecutivos \
impecables en español, con redacción profesional, ortografía perfecta y presentación clara.

REGLAS DE REDACCIÓN OBLIGATORIAS:
- Escribe siempre con tildes correctas: análisis, período, métricas, número, según, también, así, más, sección, información, etc.
- Usa signos de puntuación correctos: comas, puntos, signos de apertura ¿¡ cuando corresponda.
- Nunca uses mayúsculas innecesarias ni abreviaciones informales.
- Redacta en tercera persona o en voz impersonal, como un informe corporativo formal.
- Los números mayores a mil se escriben con separador de miles (ejemplo: 1.250.000).
- Usa el símbolo $ seguido del valor cuando hables de dinero, y aclara la moneda si aplica.

ESTRUCTURA OBLIGATORIA DE TU RESPUESTA (usa exactamente estos encabezados):

## Resumen General
Describe en 2 o 3 oraciones el estado general del conjunto de datos analizado. \
Menciona el volumen de información y la calidad de los datos.

## Hallazgos Principales
Lista entre 3 y 4 hallazgos concretos y relevantes, con cifras específicas extraídas \
de los datos. Cada hallazgo debe comenzar con un guion y ocupar máximo 2 líneas.

## Puntos de Atención
Identifica entre 1 y 2 situaciones que requieren seguimiento o presentan riesgo. \
Sé específico y objetivo, sin alarmar innecesariamente.

## Recomendación Ejecutiva
Una sola recomendación concreta, accionable y priorizada, redactada como si fuera \
para el gerente general de la empresa. Máximo 3 oraciones.

---
IMPORTANTE: No inventes datos que no estén en el resumen estadístico. \
Si algo no es calculable con los datos disponibles, omítelo."""

    user_prompt = f"""Genera el informe ejecutivo con base en la siguiente información.

Fuente de datos: {source_name}
Puntaje de calidad de datos: {quality_score}/100

Estadísticas del conjunto de datos:
{summary}

Contexto adicional proporcionado por el usuario: {extra_context if extra_context else 'No se proporcionó contexto adicional.'}

Genera el informe ahora, siguiendo estrictamente la estructura y las reglas de redacción indicadas."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        return _llamar_claude(client, system_prompt, user_prompt, max_tokens=1200)

    except anthropic.AuthenticationError:
        return "❌ La API Key es inválida. Verifica que **ANTHROPIC_API_KEY** esté correctamente configurada en los Secrets de Streamlit Cloud."
    except anthropic.RateLimitError:
        return "⏳ Se alcanzó el límite de solicitudes a la API. Espera unos minutos e intenta de nuevo."
    except Exception as e:
        return f"❌ Error al conectar con la API de Claude: {str(e)}"


def answer_natural_query(
    df: pd.DataFrame,
    question: str,
    api_key: str | None = None,
) -> str:
    """
    Responde preguntas en lenguaje natural sobre el DataFrame.
    """
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY") or _get_streamlit_secret()
    if not api_key:
        return "⚠️ Se requiere la API Key para usar las consultas en lenguaje natural."

    col_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        sample = df[col].dropna().head(3).tolist()
        col_info.append(f"  - {col} (tipo: {dtype}) | ejemplos: {sample}")

    schema = "\n".join(col_info)

    system_prompt = """Eres un analista de datos experto con dominio del español formal colombiano. \
Recibirás una pregunta sobre un conjunto de datos y debes responderla de forma clara, \
profesional y bien redactada. Usa tildes, signos de puntuación correctos y un lenguaje \
ejecutivo. Si no puedes calcular el resultado exacto con los datos disponibles, \
explica qué información adicional se necesitaría. Nunca inventes cifras."""

    user_prompt = f"""El conjunto de datos tiene {len(df):,} registros con las siguientes columnas:

{schema}

Pregunta del usuario: {question}

Responde de forma directa, profesional y bien redactada."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        return _llamar_claude(client, system_prompt, user_prompt, max_tokens=600)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def _get_streamlit_secret() -> str | None:
    """Intenta leer la API key desde Streamlit secrets."""
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None
