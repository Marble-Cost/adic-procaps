"""
Módulo de Detección de Irregularidades — ADIC Platform
Motor de análisis forense para transacciones de terceros.
Detecta patrones de riesgo mediante indicadores cuantitativos y cualitativos.
"""

from __future__ import annotations

import unicodedata
import pandas as pd
import numpy as np
from typing import Optional

# ── Diccionario de riesgo (patrones con comodines del sistema forense) ────────
# Formato: cada entrada es un patrón que puede tener múltiples raíces separadas
# por espacio (todas deben aparecer en el texto para que haya coincidencia).
RISK_DICTIONARY_RAW: list[str] = [
    "*comis*",
    "*comis0*",
    "*sobor*",
    "*coima*",
    "*grati*",
    "*cortes*",
    "*atenci*",
    "*regalo*",
    "*ddiva*",
    "*favor*",
    "*promoci*",
    "*incentiv*",
    "*bonific*",
    "*bono*",
    "*descuent* especi*",
    "*confl* inter*",
    "*intermed*",
    "*agente extern*",
    "*representant* exclu*",
    "*aport* polit*",
    "*donaci*",
    "*filantr*",
    "*patroci*",
    "*ajust*",
    "*agust*",
    "*ajuzt*",
    "*ajusce*",
    "*nota debit*",
    "*nota credit*",
    "*reversi*",
    "*reclasif*",
    "*descuadr*",
    "*diferenci*",
    "*redond*",
    "*balance* ajust*",
    "*provision*",
    "*amortiz*",
    "*depreci*",
    "*inflaci* costo*",
    "*sobreval*",
    "*subfactur*",
    "*sobrefactur*",
    "*dobl* pag*",
    "*anticip* sin contrat*",
    "*desfas*",
    "*urgent*",
    "*priorit*",
    "*emergenci*",
    "*inmedi*",
    "*excepci*",
    "*sin licitar*",
    "*contrataci* direct*",
    "*sin cotiz*",
    "*por instruccion* de gerenci*",
    "*verbal*",
    "*retroactiv*",
    "*antedatad*",
    "*aprobad* verbal*",
    "*fuera de sistem*",
    "*sin orden de compra*",
    "*sin soporte*",
    "*por favor confirm*",
    "*liberar pag*",
    "*saltar aprob*",
    "*varios*",
    "*miscelane*",
    "*gestion*",
    "*servici* profes*",
    "*servici* admin*",
    "*apoyo logist*",
    "*apoyo comerci*",
    "*support*",
    "*asesor*",
    "*consult* especializ*",
    "*estudio de mercad*",
    "*analisis estrateg*",
    "*reunion ejecutiv*",
    "*evento corporativ*",
    "*capacitaci* especial*",
    "*viatico*",
    "*represent*",
    "*relaciones instituc*",
    "*otros gastos*",
    "*caja menor*",
    "*reembolso*",
    "*saldo a favor*",
]

# ── Pesos del sistema de puntaje ──────────────────────────────────────────────
ALERT_SCORES: dict[str, int] = {
    "precio":    50,
    "palabra":   40,
    "identidad":  5,
    "fecha":      3,
    "desfase":    2,
}

# ── Umbrales de clasificación de riesgo ──────────────────────────────────────
RISK_THRESHOLDS = {
    "RIESGO ALTO":  41,   # 41 – 100 pts
    "RIESGO MEDIO": 11,   # 11 – 40 pts
    "RIESGO BAJO":   1,   #  1 – 10 pts
    "SIN ALERTA":    0,
}

RISK_COLORS = {
    "RIESGO ALTO":  "#DC2626",
    "RIESGO MEDIO": "#D97706",
    "RIESGO BAJO":  "#0057D8",
    "SIN ALERTA":   "#16A34A",
}


# ── Funciones de utilidad ──────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normaliza texto: minúsculas y sin tildes/diacríticos."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _parse_pattern(raw: str) -> list[str]:
    """
    Convierte un patrón crudo como '*descuent* especi*'
    en una lista de raíces normalizadas ['descuent', 'especi'].
    """
    cleaned = raw.replace("*", " ")
    parts = cleaned.split()
    return [_normalize(p) for p in parts if p]


def _build_parsed_dictionary() -> list[list[str]]:
    """Pre-procesa el diccionario para búsqueda eficiente."""
    return [_parse_pattern(p) for p in RISK_DICTIONARY_RAW]


# Diccionario pre-procesado (singleton)
_PARSED_DICT: list[list[str]] = _build_parsed_dictionary()


def detect_keyword_in_text(text_combined: str) -> tuple[bool, str]:
    """
    Busca coincidencias del diccionario de riesgo en el texto combinado.
    Retorna (encontrado, primera_palabra_detectada).
    """
    normalized = _normalize(str(text_combined))
    if not normalized.strip():
        return False, ""

    for i, parts in enumerate(_PARSED_DICT):
        if all(part in normalized for part in parts):
            return True, RISK_DICTIONARY_RAW[i].replace("*", "").strip()

    return False, ""


def classify_risk(score: float) -> str:
    """Clasifica el nivel de riesgo según el puntaje de la transacción."""
    if score >= RISK_THRESHOLDS["RIESGO ALTO"]:
        return "RIESGO ALTO"
    elif score >= RISK_THRESHOLDS["RIESGO MEDIO"]:
        return "RIESGO MEDIO"
    elif score >= RISK_THRESHOLDS["RIESGO BAJO"]:
        return "RIESGO BAJO"
    return "SIN ALERTA"


def classify_risk_tercero(max_score: float, freq_pct: float) -> str:
    """
    Clasifica el riesgo del tercero usando su peor transacción
    y la frecuencia con que ha generado alertas.
    """
    base = classify_risk(max_score)
    # Si tiene frecuencia muy alta de alertas (>50%), sube un nivel
    if freq_pct > 50 and base == "RIESGO MEDIO":
        return "RIESGO ALTO"
    if freq_pct > 50 and base == "RIESGO BAJO":
        return "RIESGO MEDIO"
    return base


# ── Motor principal de análisis ───────────────────────────────────────────────

def run_risk_analysis(
    df: pd.DataFrame,
    col_tercero: str,
    col_importe: str,
    col_fecha_doc: Optional[str] = None,
    col_fecha_contab: Optional[str] = None,
    col_num_documento: Optional[str] = None,
    col_texto1: Optional[str] = None,
    col_texto2: Optional[str] = None,
    col_texto3: Optional[str] = None,
) -> pd.DataFrame:
    """
    Ejecuta el análisis completo de detección de irregularidades.

    Parámetros
    ----------
    df              : DataFrame original con los datos de transacciones.
    col_tercero     : Columna con el nombre o código del tercero.
    col_importe     : Columna con el valor monetario de la transacción.
    col_fecha_doc   : (Opcional) Fecha del documento/transacción.
    col_fecha_contab: (Opcional) Fecha de contabilización en el sistema.
    col_num_documento: (Opcional) Número de documento del tercero.
    col_texto1/2/3  : (Opcional) Columnas de descripción textual.

    Retorna
    -------
    DataFrame con todas las columnas originales más las columnas de alerta,
    puntaje y nivel de riesgo calculados por transacción.
    """
    result = df.copy()

    # ── 1. Promedio histórico por tercero ─────────────────────────────────────
    hist_avg = (
        df.groupby(col_tercero)[col_importe]
        .mean()
        .to_dict()
    )
    result["_Promedio_Historico"] = result[col_tercero].map(hist_avg).fillna(0)

    # ── 2. Alerta de precio (>130% del promedio histórico del tercero) ────────
    result["Alerta_Precio"] = (
        result[col_importe] > result["_Promedio_Historico"] * 1.3
    ).map({True: "SÍ", False: "NO"})

    # Guardar desviación porcentual del promedio para contexto
    result["_Desviacion_Vs_Promedio_Pct"] = (
        ((result[col_importe] - result["_Promedio_Historico"]) /
         result["_Promedio_Historico"].replace(0, np.nan)) * 100
    ).round(1)

    # ── 3. Alerta de palabra y filtro de evasión ──────────────────────────────
    text_cols_present = [c for c in [col_texto1, col_texto2, col_texto3] if c]

    if text_cols_present:
        def _build_combined(row: pd.Series) -> str:
            parts = []
            for c in text_cols_present:
                val = row.get(c, "")
                parts.append(str(val) if pd.notna(val) else "")
            return " ".join(parts)

        combined_texts = result.apply(_build_combined, axis=1)

        keyword_results = combined_texts.apply(detect_keyword_in_text)
        result["Alerta_Palabra"] = keyword_results.apply(
            lambda r: "SÍ" if r[0] else "NO"
        )
        result["_Palabra_Detectada"] = keyword_results.apply(lambda r: r[1])

        # Filtro de evasión: longitud total de descripciones < 20 caracteres
        combined_lengths = combined_texts.apply(lambda t: len(t.strip()))
        result["Filtro_Evasion"] = combined_lengths.apply(
            lambda n: "SÍ" if n < 20 else "NO"
        )
        result["_Longitud_Descripcion"] = combined_lengths

    else:
        result["Alerta_Palabra"] = "NO"
        result["_Palabra_Detectada"] = ""
        result["Filtro_Evasion"] = "NO"
        result["_Longitud_Descripcion"] = 0

    # ── 4. Alerta de fecha (fin de semana: sábado o domingo) ──────────────────
    if col_fecha_doc:
        try:
            fechas_doc = pd.to_datetime(result[col_fecha_doc], errors="coerce")
            result["Alerta_Fecha"] = fechas_doc.dt.dayofweek.apply(
                lambda d: "SÍ" if pd.notna(d) and d >= 5 else "NO"
            )
            result["_Dia_Semana"] = fechas_doc.dt.day_name()
        except Exception:
            result["Alerta_Fecha"] = "NO"
            result["_Dia_Semana"] = ""
    else:
        result["Alerta_Fecha"] = "NO"
        result["_Dia_Semana"] = ""

    # ── 5. Alerta de desfase (>60 días entre fecha doc y contabilización) ─────
    if col_fecha_doc and col_fecha_contab:
        try:
            f_doc   = pd.to_datetime(result[col_fecha_doc],    errors="coerce")
            f_cont  = pd.to_datetime(result[col_fecha_contab], errors="coerce")
            delay_days = (f_cont - f_doc).dt.days
            result["Alerta_Desfase"]  = delay_days.apply(
                lambda d: "SÍ" if pd.notna(d) and d > 60 else "NO"
            )
            result["_Dias_Desfase"] = delay_days
        except Exception:
            result["Alerta_Desfase"] = "NO"
            result["_Dias_Desfase"]  = np.nan
    else:
        result["Alerta_Desfase"] = "NO"
        result["_Dias_Desfase"]  = np.nan

    # ── 6. Alerta de identidad (tercero o número de documento vacíos) ─────────
    def _check_identity(row: pd.Series) -> str:
        tercero_vacio = (
            pd.isna(row[col_tercero]) or
            str(row[col_tercero]).strip() == ""
        )
        doc_vacio = False
        if col_num_documento:
            doc_vacio = (
                pd.isna(row.get(col_num_documento)) or
                str(row.get(col_num_documento, "")).strip() == ""
            )
        return "SÍ" if (tercero_vacio or doc_vacio) else "NO"

    result["Alerta_Identidad"] = result.apply(_check_identity, axis=1)

    # ── 7. Puntaje acumulado por transacción ──────────────────────────────────
    result["Puntaje"] = (
        result["Alerta_Precio"].eq("SÍ").astype(int)    * ALERT_SCORES["precio"]   +
        result["Alerta_Palabra"].eq("SÍ").astype(int)   * ALERT_SCORES["palabra"]  +
        result["Alerta_Identidad"].eq("SÍ").astype(int) * ALERT_SCORES["identidad"] +
        result["Alerta_Fecha"].eq("SÍ").astype(int)     * ALERT_SCORES["fecha"]    +
        result["Alerta_Desfase"].eq("SÍ").astype(int)   * ALERT_SCORES["desfase"]
    )

    # ── 8. Nivel de riesgo por transacción ────────────────────────────────────
    result["Nivel_Riesgo"] = result["Puntaje"].apply(classify_risk)

    # ── 9. Nombre de monitoreo (maneja terceros no identificados) ─────────────
    result["Nombre_Monitoreo"] = result[col_tercero].apply(
        lambda x: "TERCERO NO IDENTIFICADO"
        if (pd.isna(x) or str(x).strip() == "")
        else str(x).strip()
    )

    # ── Limpiar columnas auxiliares internas ──────────────────────────────────
    result = result.drop(columns=["_Promedio_Historico"])

    return result


def get_tercero_summary(
    result_df: pd.DataFrame,
    col_importe: str,
) -> pd.DataFrame:
    """
    Genera un resumen consolidado por tercero con métricas de riesgo.
    Usa el puntaje MÁXIMO de sus transacciones para la clasificación,
    combinado con la frecuencia de alertas para capturar patrones recurrentes.
    """
    grp = result_df.groupby("Nombre_Monitoreo")

    summary = pd.DataFrame({
        "Total_Transacciones":      grp.size(),
        "Importe_Total":            grp[col_importe].sum(),
        "Importe_Promedio":         grp[col_importe].mean(),
        "Importe_Maximo":           grp[col_importe].max(),
        "Puntaje_Maximo":           grp["Puntaje"].max(),
        "Puntaje_Promedio":         grp["Puntaje"].mean().round(1),
        "Transacciones_Con_Alerta": grp["Puntaje"].apply(lambda x: (x > 0).sum()),
        "Alertas_Precio":           grp["Alerta_Precio"].apply(lambda x: (x == "SÍ").sum()),
        "Alertas_Palabra":          grp["Alerta_Palabra"].apply(lambda x: (x == "SÍ").sum()),
        "Alertas_Identidad":        grp["Alerta_Identidad"].apply(lambda x: (x == "SÍ").sum()),
        "Alertas_Fecha":            grp["Alerta_Fecha"].apply(lambda x: (x == "SÍ").sum()),
        "Alertas_Desfase":          grp["Alerta_Desfase"].apply(lambda x: (x == "SÍ").sum()),
        "Evasion_Detectada":        grp["Filtro_Evasion"].apply(lambda x: (x == "SÍ").sum()),
    }).reset_index()

    # Frecuencia de riesgo (% de transacciones con alguna alerta)
    summary["Frecuencia_Riesgo_Pct"] = (
        summary["Transacciones_Con_Alerta"] / summary["Total_Transacciones"] * 100
    ).round(1)

    # Clasificación de riesgo del tercero (combina max score + frecuencia)
    summary["Nivel_Riesgo"] = summary.apply(
        lambda row: classify_risk_tercero(
            row["Puntaje_Maximo"],
            row["Frecuencia_Riesgo_Pct"],
        ),
        axis=1,
    )

    # Indicadores de activación (cuáles alertas tiene el tercero)
    def _flags(row: pd.Series) -> str:
        flags = []
        if row["Alertas_Precio"]    > 0: flags.append("💰 Precio")
        if row["Alertas_Palabra"]   > 0: flags.append("🔤 Palabra")
        if row["Alertas_Identidad"] > 0: flags.append("🆔 Identidad")
        if row["Alertas_Fecha"]     > 0: flags.append("📅 Fecha")
        if row["Alertas_Desfase"]   > 0: flags.append("⏳ Desfase")
        if row["Evasion_Detectada"] > 0: flags.append("🚫 Evasión")
        return " | ".join(flags) if flags else "—"

    summary["Alertas_Activas"] = summary.apply(_flags, axis=1)

    # Ordenar por nivel de riesgo y puntaje
    _order_map = {"RIESGO ALTO": 0, "RIESGO MEDIO": 1, "RIESGO BAJO": 2, "SIN ALERTA": 3}
    summary["_orden"] = summary["Nivel_Riesgo"].map(_order_map)
    summary = (
        summary
        .sort_values(["_orden", "Puntaje_Maximo", "Frecuencia_Riesgo_Pct"],
                     ascending=[True, False, False])
        .drop(columns=["_orden"])
        .reset_index(drop=True)
    )

    return summary


def get_analysis_stats(result_df: pd.DataFrame, col_importe: str) -> dict:
    """Calcula estadísticas globales del análisis para los KPIs del dashboard."""
    total = len(result_df)
    alertados = (result_df["Puntaje"] > 0).sum()
    alto  = (result_df["Nivel_Riesgo"] == "RIESGO ALTO").sum()
    medio = (result_df["Nivel_Riesgo"] == "RIESGO MEDIO").sum()
    bajo  = (result_df["Nivel_Riesgo"] == "RIESGO BAJO").sum()

    terceros = result_df["Nombre_Monitoreo"].nunique()
    terceros_alertados = (
        result_df[result_df["Puntaje"] > 0]["Nombre_Monitoreo"].nunique()
    )

    importe_total   = result_df[col_importe].sum()
    importe_en_riesgo = result_df[result_df["Nivel_Riesgo"] == "RIESGO ALTO"][col_importe].sum()

    return {
        "total_transacciones":     total,
        "transacciones_alertadas": int(alertados),
        "pct_alertadas":           round(alertados / total * 100, 1) if total > 0 else 0,
        "riesgo_alto":             int(alto),
        "riesgo_medio":            int(medio),
        "riesgo_bajo":             int(bajo),
        "total_terceros":          int(terceros),
        "terceros_alertados":      int(terceros_alertados),
        "importe_total":           float(importe_total),
        "importe_en_riesgo_alto":  float(importe_en_riesgo),
        "pct_importe_en_riesgo":   round(importe_en_riesgo / importe_total * 100, 1)
                                   if importe_total > 0 else 0,
    }