"""
Módulo de Detección de Irregularidades — ADIC Platform
Motor de análisis forense · Analista de Cumplimiento Legal Corporativo
"""
from __future__ import annotations
import unicodedata
import pandas as pd
import numpy as np
from typing import Optional

RISK_DICTIONARY_RAW: list[str] = [
    # ── Pagos ilícitos ────────────────────────────────────────────────────────
    "*comis*","*sobor*","*coima*","*grati*","*cortes*",
    "*atenci*","*regalo*","*dadiva*","*ddiva*","*favor*","*promoci*","*incentiv*",
    "*bonific*","*bono*","*descuent* especi*","*confl* inter*",
    "*intermed*","*agente extern*","*representant* exclu*",
    "*aport* polit*","*donaci*","*filantr*","*patroci*",
    # ── Ajustes contables ─────────────────────────────────────────────────────
    # CAMBIO 3: eliminados "*agust*" (typo de *ajust*), "*ajuzt*" y "*ajusce*" (redundantes)
    "*ajust*",
    "*nota debit*","*nota credit*","*reversi*","*reclasif*",
    "*descuadr*","*diferenci*","*redond*","*balance* ajust*",
    "*provision*","*amortiz*","*depreci*","*inflaci* costo*",
    "*sobreval*","*subfactur*","*sobrefactur*",
    "*dobl* pag*","*anticip* sin contrat*","*desfas*",
    # ── Urgencias / evasión de control ───────────────────────────────────────
    "*urgent*","*priorit*","*emergenci*","*inmedi*","*excepci*",
    "*sin licitar*","*contrataci* direct*","*sin cotiz*",
    "*por instruccion* de gerenci*","*verbal*","*retroactiv*",
    "*antedatad*","*aprobad* verbal*","*fuera de sistem*",
    "*sin orden de compra*","*sin soporte*",
    "*por favor confirm*","*liberar pag*","*saltar aprob*",
    # ── Servicios genéricos / descripciones vagas ─────────────────────────────
    "*varios*","*miscelane*","*gestion*",
    "*servici* profes*","*servici* admin*",
    "*apoyo logist*","*apoyo comerci*","*support*",
    "*asesor*","*consult* especializ*","*estudio de mercad*",
    "*analisis estrateg*","*reunion ejecutiv*","*evento corporativ*",
    "*capacitaci* especial*","*viatico*","*represent*",
    "*relaciones instituc*","*otros gastos*","*caja menor*",
    "*reembolso*","*saldo a favor*",
    # ── Variantes adicionales — sector farmacéutico / servicios externos ──────
    "*soporte extern*","*servicio tecnico extern*","*expertise*",
    "*honorario*","*fee*","*retainer*","*management fee*",
]

ALERT_SCORES: dict[str, int] = {
    "precio": 50, "palabra": 40, "identidad": 5, "fecha": 3, "desfase": 2,
}

RISK_COLORS = {
    "RIESGO ALTO":  "#DC2626",
    "RIESGO MEDIO": "#D97706",
    "RIESGO BAJO":  "#0057D8",
    "SIN ALERTA":   "#16A34A",
}

SEVERITY_COLORS = {
    "CRÍTICA": "#7C0000", "ALTA": "#DC2626", "MEDIA": "#D97706", "BAJA": "#0057D8",
}

INFRACTION_DEFINITIONS = [
    {
        "id": "SOBORNO_CRITICO",
        "nombre": "Posible Soborno / Cohecho",
        "icono": "🤝", "severidad": "CRÍTICA",
        "descripcion": "Precio anómalo (+30% promedio) Y lenguaje asociado a pagos ilícitos en la descripción.",
        "check": lambda r: r.get("Alerta_Precio") == "SÍ" and r.get("Alerta_Palabra") == "SÍ",
    },
    {
        "id": "LENGUAJE_SOSPECHOSO",
        "nombre": "Lenguaje Sospechoso en Descripción",
        "icono": "🔤", "severidad": "ALTA",
        "descripcion": "La descripción contiene términos del diccionario de riesgo (sobornos, ajustes, urgencias, etc.).",
        "check": lambda r: r.get("Alerta_Palabra") == "SÍ" and r.get("Alerta_Precio") != "SÍ",
    },
    {
        "id": "SOBREPRECIO",
        "nombre": "Sobreprecio / Inflación de Costos",
        "icono": "💰", "severidad": "ALTA",
        "descripcion": "El importe supera en >30% el promedio histórico del tercero, sin lenguaje sospechoso.",
        "check": lambda r: r.get("Alerta_Precio") == "SÍ" and r.get("Alerta_Palabra") != "SÍ",
    },
    {
        "id": "TERCERO_FANTASMA",
        "nombre": "Tercero No Identificado",
        "icono": "👻", "severidad": "ALTA",
        "descripcion": "Transacción sin nombre de tercero o sin número de documento registrado.",
        "check": lambda r: r.get("Alerta_Identidad") == "SÍ",
    },
    {
        "id": "EVASION_DOCUMENTAL",
        "nombre": "Evasión Documental",
        "icono": "📄", "severidad": "MEDIA",
        "descripcion": "Descripción combinada menor a 20 caracteres — impide identificar el propósito.",
        "check": lambda r: r.get("Filtro_Evasion") == "SÍ" and r.get("Alerta_Identidad") != "SÍ",
    },
    {
        "id": "IRREGULARIDAD_TEMPORAL",
        "nombre": "Irregularidad Temporal",
        "icono": "⏰", "severidad": "MEDIA",
        "descripcion": "Transacción registrada en fin de semana y/o con desfase de contabilización mayor a 60 días.",
        "check": lambda r: r.get("Alerta_Fecha") == "SÍ" or r.get("Alerta_Desfase") == "SÍ",
    },
]

# ── Utilidades ─────────────────────────────────────────────────────────────────
def _normalize(text: str) -> str:
    t = str(text).lower()
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")

import re as _re

# CAMBIO 3: Compilar el diccionario como expresiones regulares reales.
# El formato original "*asesor*" usaba split() y buscaba tokens individuales,
# lo que fallaba con patrones compuestos y no detectaba substrings correctamente.
# Ahora cada "*" se traduce a ".*" en la regex, y toda la expresión se compila
# con re.IGNORECASE para robustez.
def _compile_pattern(raw: str) -> _re.Pattern:
    # Normalizar el patrón de la misma forma que el texto
    norm = _normalize(raw)
    # Convertir wildcards: "*" → ".*", escapar el resto
    parts = norm.split("*")
    regex = ".*".join(_re.escape(p) for p in parts)
    return _re.compile(regex, _re.IGNORECASE)

_COMPILED_PATTERNS: list[tuple[_re.Pattern, str]] = [
    (_compile_pattern(raw), raw)
    for raw in RISK_DICTIONARY_RAW
]

def detect_keyword_in_text(text: str) -> tuple[bool, str]:
    norm = _normalize(text)
    if not norm.strip():
        return False, ""
    # CAMBIO 3: usa las regex compiladas en lugar del check de tokens
    for pattern, raw in _COMPILED_PATTERNS:
        if pattern.search(norm):
            return True, raw.replace("*", "").strip()
    return False, ""

def classify_risk(score: float) -> str:
    if score >= 41: return "RIESGO ALTO"
    if score >= 11: return "RIESGO MEDIO"
    if score >= 1:  return "RIESGO BAJO"
    return "SIN ALERTA"

def _classify_tercero(max_score: float, freq_pct: float, total_txns: int = 0) -> str:
    """
    Clasifica el nivel de riesgo de un tercero.

    CAMBIO 2: Se añade el parámetro total_txns para aplicar la regla de escalada
    por frecuencia solo cuando hay suficientes observaciones (>= MIN_TXNS_FOR_ESCALATION).
    Con menos registros, el 50% de alertas es estadísticamente insignificante y
    puede producir escaladas falsas que no son defendibles en un comité de cumplimiento.
    """
    MIN_TXNS_FOR_ESCALATION = 5  # Configurable — mínimo para aplicar la regla del 50%

    base = classify_risk(max_score)

    # Solo escalar por frecuencia si hay suficiente muestra
    if total_txns >= MIN_TXNS_FOR_ESCALATION and freq_pct > 50:
        if base == "RIESGO MEDIO":
            return "RIESGO ALTO"
        if base == "RIESGO BAJO":
            return "RIESGO MEDIO"

    return base

def _infraction_label(row: pd.Series) -> str:
    hits = [d for d in INFRACTION_DEFINITIONS if d["check"](row)]
    return " | ".join(f"{d['icono']} {d['nombre']}" for d in hits) if hits else "Sin infracción"

def _worst_severity(row: pd.Series) -> str:
    order = {"CRÍTICA": 0, "ALTA": 1, "MEDIA": 2, "BAJA": 3}
    hits = [d for d in INFRACTION_DEFINITIONS if d["check"](row)]
    if not hits: return "—"
    return min(hits, key=lambda d: order.get(d["severidad"], 9))["severidad"]

# ── Anomalías estadísticas ──────────────────────────────────────────────────────
def _detect_anomalies(df: pd.DataFrame, col_tercero: str, col_importe: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    # 1. Monto redondo sospechoso
    def _is_round(v):
        try:
            v = float(v)
            for t in [5_000_000, 1_000_000, 500_000, 100_000]:
                if v >= t and v % t == 0:
                    return "SÍ"
        except Exception:
            pass
        return "NO"
    out["Monto_Redondo"] = df[col_importe].apply(_is_round)

    # 2. Monto duplicado por tercero
    dup = df.duplicated(subset=[col_tercero, col_importe], keep=False)
    out["Monto_Duplicado"] = dup.map({True: "SÍ", False: "NO"})

    # 3. Outlier estadístico global (z-score > 2.5)
    vals = df[col_importe].dropna()
    mu, sigma = vals.mean(), vals.std()
    if sigma and sigma > 0:
        z = (df[col_importe] - mu) / sigma
        out["Outlier_Estadistico"] = z.abs().apply(lambda x: "SÍ" if x > 2.5 else "NO")
    else:
        out["Outlier_Estadistico"] = "NO"

    # 4. Posible fraccionamiento (≥3 montos casi idénticos ±5% por tercero)
    # Vectorizado — compatible con pandas 3.x (sin groupby+apply)
    _imp = df[col_importe].fillna(0)
    _ter = df[col_tercero].fillna("__NA__").astype(str)
    _mu  = _imp.groupby(_ter).transform("mean")
    _cerca = _imp.between(_mu * 0.95, _mu * 1.05).astype(int)
    _cnt = _cerca.groupby(_ter).transform("sum")
    _tam = _ter.groupby(_ter).transform("count")
    out["Posible_Fraccionamiento"] = ((_cnt >= 3) & (_tam >= 3)).map({True: "SÍ", False: "NO"}).values

    return out

# ── Motor principal ─────────────────────────────────────────────────────────────
def run_risk_analysis(
    df: pd.DataFrame,
    col_tercero: str,
    col_importe: str,
    col_fecha_doc: Optional[str]    = None,
    col_fecha_contab: Optional[str] = None,
    col_num_documento: Optional[str]= None,
    col_texto1: Optional[str]       = None,
    col_texto2: Optional[str]       = None,
    col_texto3: Optional[str]       = None,
) -> pd.DataFrame:
    r = df.copy()

    # ── CAMBIO 1: Mediana + P90 por tercero (resistente a inflación sostenida) ──
    # Antes: se usaba .mean(), que se desplaza cuando un tercero infla precios
    # de forma constante, haciendo que ninguna transacción individual parezca anómala.
    # Ahora: se usa .median() (resistente a outliers) como referencia base,
    # y adicionalmente se marca alerta si el importe supera el P90 del tercero.
    mediana_tercero = df.groupby(col_tercero)[col_importe].median().to_dict()
    p90_tercero     = df.groupby(col_tercero)[col_importe].quantile(0.90).to_dict()

    r["_mediana"] = r[col_tercero].map(mediana_tercero).fillna(0)
    r["_p90"]     = r[col_tercero].map(p90_tercero).fillna(0)

    # Alerta de precio: supera 30% sobre la mediana O supera el P90 del tercero
    alerta_mediana = r[col_importe] > r["_mediana"] * 1.3
    alerta_p90     = r[col_importe] > r["_p90"]
    r["Alerta_Precio"] = (alerta_mediana | alerta_p90).map({True: "SÍ", False: "NO"})

    # Desviación porcentual respecto a la mediana (más interpretable)
    r["Desviacion_Vs_Mediana_Pct"] = (
        ((r[col_importe] - r["_mediana"]) / r["_mediana"].replace(0, np.nan)) * 100
    ).round(1)
    # Mantener columna legacy con nombre actualizado para compatibilidad de UI
    r["Desviacion_Vs_Promedio_Pct"] = r["Desviacion_Vs_Mediana_Pct"]

    r.drop(columns=["_mediana", "_p90"], inplace=True)

    # Alerta de palabra + filtro de evasión
    text_cols = [c for c in [col_texto1, col_texto2, col_texto3] if c]
    if text_cols:
        combined = r.apply(
            lambda row: " ".join(str(row.get(c) or "") for c in text_cols), axis=1
        )
        kw = combined.apply(detect_keyword_in_text)
        r["Alerta_Palabra"]    = kw.apply(lambda x: "SÍ" if x[0] else "NO")
        r["Palabra_Detectada"] = kw.apply(lambda x: x[1])
        lens = combined.str.strip().str.len()
        r["Filtro_Evasion"]    = lens.apply(lambda n: "SÍ" if n < 20 else "NO")
        r["Long_Descripcion"]  = lens
    else:
        r["Alerta_Palabra"]    = "NO"
        r["Palabra_Detectada"] = ""
        r["Filtro_Evasion"]    = "NO"
        r["Long_Descripcion"]  = 0

    # Alerta de fecha (fin de semana)
    if col_fecha_doc:
        try:
            fd = pd.to_datetime(r[col_fecha_doc], errors="coerce")
            r["Alerta_Fecha"] = fd.dt.dayofweek.apply(lambda d: "SÍ" if pd.notna(d) and d >= 5 else "NO")
            r["Dia_Semana"]   = fd.dt.day_name()
        except Exception:
            r["Alerta_Fecha"] = "NO"; r["Dia_Semana"] = ""
    else:
        r["Alerta_Fecha"] = "NO"; r["Dia_Semana"] = ""

    # Alerta de desfase (>60 días)
    if col_fecha_doc and col_fecha_contab:
        try:
            f1 = pd.to_datetime(r[col_fecha_doc],    errors="coerce")
            f2 = pd.to_datetime(r[col_fecha_contab], errors="coerce")
            d  = (f2 - f1).dt.days
            r["Alerta_Desfase"] = d.apply(lambda x: "SÍ" if pd.notna(x) and x > 60 else "NO")
            r["Dias_Desfase"]   = d
        except Exception:
            r["Alerta_Desfase"] = "NO"; r["Dias_Desfase"] = np.nan
    else:
        r["Alerta_Desfase"] = "NO"; r["Dias_Desfase"] = np.nan

    # Alerta de identidad
    def _ident(row):
        vt = pd.isna(row[col_tercero]) or str(row[col_tercero]).strip() == ""
        vd = False
        if col_num_documento:
            v = row.get(col_num_documento)
            vd = pd.isna(v) or str(v).strip() == ""
        return "SÍ" if (vt or vd) else "NO"
    r["Alerta_Identidad"] = r.apply(_ident, axis=1)

    # Puntaje
    r["Puntaje"] = (
        r["Alerta_Precio"].eq("SÍ").astype(int)    * ALERT_SCORES["precio"]    +
        r["Alerta_Palabra"].eq("SÍ").astype(int)   * ALERT_SCORES["palabra"]   +
        r["Alerta_Identidad"].eq("SÍ").astype(int) * ALERT_SCORES["identidad"] +
        r["Alerta_Fecha"].eq("SÍ").astype(int)     * ALERT_SCORES["fecha"]     +
        r["Alerta_Desfase"].eq("SÍ").astype(int)   * ALERT_SCORES["desfase"]
    )

    # Nivel de riesgo
    r["Nivel_Riesgo"] = r["Puntaje"].apply(classify_risk)

    # Categorías de infracción
    r["Infracciones_Detectadas"] = r.apply(_infraction_label, axis=1)
    r["Severidad_Maxima"]        = r.apply(_worst_severity, axis=1)

    # Anomalías estadísticas
    anom = _detect_anomalies(df, col_tercero, col_importe)
    for col in anom.columns:
        r[col] = anom[col].values

    # Nombre de monitoreo
    r["Nombre_Monitoreo"] = r[col_tercero].apply(
        lambda x: "TERCERO NO IDENTIFICADO" if (pd.isna(x) or str(x).strip() == "") else str(x).strip()
    )
    return r


# ── Resumen por tercero ─────────────────────────────────────────────────────────
def get_tercero_summary(result_df: pd.DataFrame, col_importe: str) -> pd.DataFrame:
    g = result_df.groupby("Nombre_Monitoreo")
    s = pd.DataFrame({
        "Total_Transacciones":    g.size(),
        "Importe_Total":          g[col_importe].sum(),
        "Importe_Promedio":       g[col_importe].mean(),
        "Importe_Maximo":         g[col_importe].max(),
        "Puntaje_Maximo":         g["Puntaje"].max(),
        "Puntaje_Promedio":       g["Puntaje"].mean().round(1),
        "Txns_Con_Alerta":        g["Puntaje"].apply(lambda x: (x > 0).sum()),
        "Alertas_Precio":         g["Alerta_Precio"].apply(lambda x: (x == "SÍ").sum()),
        "Alertas_Palabra":        g["Alerta_Palabra"].apply(lambda x: (x == "SÍ").sum()),
        "Alertas_Identidad":      g["Alerta_Identidad"].apply(lambda x: (x == "SÍ").sum()),
        "Alertas_Fecha":          g["Alerta_Fecha"].apply(lambda x: (x == "SÍ").sum()),
        "Alertas_Desfase":        g["Alerta_Desfase"].apply(lambda x: (x == "SÍ").sum()),
        "Evasion":                g["Filtro_Evasion"].apply(lambda x: (x == "SÍ").sum()),
        "Montos_Redondos":        g["Monto_Redondo"].apply(lambda x: (x == "SÍ").sum()),
        "Montos_Duplicados":      g["Monto_Duplicado"].apply(lambda x: (x == "SÍ").sum()),
        "Outliers_Estadisticos":  g["Outlier_Estadistico"].apply(lambda x: (x == "SÍ").sum()),
        "Fraccionamiento":        g["Posible_Fraccionamiento"].apply(lambda x: (x == "SÍ").sum()),
    }).reset_index()

    s["Frecuencia_Riesgo_Pct"] = (s["Txns_Con_Alerta"] / s["Total_Transacciones"] * 100).round(1)
    # CAMBIO 2b: pasar Total_Transacciones para activar el mínimo estadístico
    s["Nivel_Riesgo"] = s.apply(
        lambda r: _classify_tercero(r["Puntaje_Maximo"], r["Frecuencia_Riesgo_Pct"], r["Total_Transacciones"]),
        axis=1,
    )
    # Flag de muestra insuficiente — visible en el reporte para el equipo legal
    s["Muestra_Insuficiente"] = s["Total_Transacciones"].apply(lambda n: "⚠️ Sí (< 5 txns)" if n < 5 else "No")

    # Tipos de infracción únicos del tercero
    def _unique_inf(name):
        txns = result_df[result_df["Nombre_Monitoreo"] == name]["Infracciones_Detectadas"]
        seen, out = set(), []
        for raw in txns:
            for part in raw.split(" | "):
                p = part.strip()
                if p and p != "Sin infracción" and p not in seen:
                    seen.add(p); out.append(p)
        return " | ".join(out) if out else "—"

    s["Tipos_Infraccion"] = s["Nombre_Monitoreo"].apply(_unique_inf)

    # Severidad máxima del tercero
    _ord = {"CRÍTICA": 0, "ALTA": 1, "MEDIA": 2, "—": 9}
    def _worst_sev(name):
        sevs = result_df[result_df["Nombre_Monitoreo"] == name]["Severidad_Maxima"]
        cands = [x for x in sevs if x != "—"]
        return min(cands, key=lambda x: _ord.get(x, 9)) if cands else "—"
    s["Severidad_Maxima"] = s["Nombre_Monitoreo"].apply(_worst_sev)

    # Veredicto de compliance
    def _veredicto(row):
        if row["Nivel_Riesgo"] == "RIESGO ALTO":  return "⛔ MONITOREO URGENTE"
        if row["Nivel_Riesgo"] == "RIESGO MEDIO": return "⚠️ INVESTIGAR"
        if row["Nivel_Riesgo"] == "RIESGO BAJO":  return "🔵 OBSERVAR"
        return "✅ CONFORME"
    s["Veredicto_Compliance"] = s.apply(_veredicto, axis=1)

    _o = {"RIESGO ALTO": 0, "RIESGO MEDIO": 1, "RIESGO BAJO": 2, "SIN ALERTA": 3}
    s["_o"] = s["Nivel_Riesgo"].map(_o)
    return s.sort_values(["_o", "Puntaje_Maximo"], ascending=[True, False]).drop(columns=["_o"]).reset_index(drop=True)


# ── Estadísticas globales ───────────────────────────────────────────────────────
def get_analysis_stats(result_df: pd.DataFrame, col_importe: str) -> dict:
    total     = len(result_df)
    alertados = int((result_df["Puntaje"] > 0).sum())
    alto      = int((result_df["Nivel_Riesgo"] == "RIESGO ALTO").sum())
    medio     = int((result_df["Nivel_Riesgo"] == "RIESGO MEDIO").sum())
    bajo      = int((result_df["Nivel_Riesgo"] == "RIESGO BAJO").sum())
    terceros           = int(result_df["Nombre_Monitoreo"].nunique())
    terceros_alertados = int(result_df[result_df["Puntaje"] > 0]["Nombre_Monitoreo"].nunique())
    terceros_criticos  = int(result_df[result_df["Nivel_Riesgo"] == "RIESGO ALTO"]["Nombre_Monitoreo"].nunique())
    importe_total      = float(result_df[col_importe].sum())
    importe_riesgo     = float(result_df[result_df["Nivel_Riesgo"] == "RIESGO ALTO"][col_importe].sum())

    infraction_counts = {
        d["nombre"]: int(result_df.apply(d["check"], axis=1).sum())
        for d in INFRACTION_DEFINITIONS
    }
    anomaly_counts = {
        "Montos redondos sospechosos": int(result_df.get("Monto_Redondo",     pd.Series(dtype=str)).eq("SÍ").sum()),
        "Montos duplicados":           int(result_df.get("Monto_Duplicado",   pd.Series(dtype=str)).eq("SÍ").sum()),
        "Outliers estadísticos":       int(result_df.get("Outlier_Estadistico",pd.Series(dtype=str)).eq("SÍ").sum()),
        "Posible fraccionamiento":     int(result_df.get("Posible_Fraccionamiento",pd.Series(dtype=str)).eq("SÍ").sum()),
    }

    return {
        "total_transacciones":     total,
        "transacciones_alertadas": alertados,
        "pct_alertadas":           round(alertados / total * 100, 1) if total > 0 else 0,
        "riesgo_alto":             alto,
        "riesgo_medio":            medio,
        "riesgo_bajo":             bajo,
        "total_terceros":          terceros,
        "terceros_alertados":      terceros_alertados,
        "terceros_criticos":       terceros_criticos,
        "importe_total":           importe_total,
        "importe_riesgo_alto":     importe_riesgo,
        "pct_importe_riesgo":      round(importe_riesgo / importe_total * 100, 1) if importe_total > 0 else 0,
        "infraction_counts":       infraction_counts,
        "anomaly_counts":          anomaly_counts,
    }
