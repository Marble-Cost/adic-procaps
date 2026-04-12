"""
Módulo de Calidad de Datos — ADIC Platform Procaps
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field


@dataclass
class QualityReport:
    score: float
    completeness: float
    uniqueness: float
    consistency: float
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    column_detail: dict = field(default_factory=dict)


def compute_quality_score(df: pd.DataFrame) -> QualityReport:
    issues = []
    recommendations = []
    column_detail = {}

    # Completitud
    total_cells = df.shape[0] * df.shape[1]
    null_cells = df.isnull().sum().sum()
    completeness = 1.0 - (null_cells / total_cells) if total_cells > 0 else 1.0

    null_by_col = df.isnull().mean()
    for col in df.columns:
        nulos_pct = null_by_col[col] * 100
        column_detail[col] = {
            "nulls_pct": round(nulos_pct, 1),
            "dtype": str(df[col].dtype),
            "unique_values": int(df[col].nunique()),
        }
        if nulos_pct > 30:
            issues.append(f"'{col}' tiene {nulos_pct:.0f}% de valores nulos.")
            recommendations.append(f"Revisar origen de '{col}' o aplicar imputación.")
        elif nulos_pct > 10:
            issues.append(f"'{col}' tiene {nulos_pct:.0f}% de valores nulos (moderado).")

    # Unicidad
    total_rows = len(df)
    duplicate_rows = df.duplicated().sum()
    uniqueness = 1.0 - (duplicate_rows / total_rows) if total_rows > 0 else 1.0

    if duplicate_rows > 0:
        issues.append(f"{duplicate_rows} filas duplicadas detectadas.")
        recommendations.append("Eliminar duplicados antes de analizar.")

    # Consistencia
    mixed_cols = 0
    for col in df.select_dtypes(include="object").columns:
        try:
            numeric_count = pd.to_numeric(df[col].dropna(), errors="coerce").notna().sum()
            non_null = df[col].notna().sum()
            if non_null > 0 and 0 < numeric_count < non_null:
                mixed_pct = numeric_count / non_null
                if 0.1 < mixed_pct < 0.9:
                    mixed_cols += 1
                    issues.append(f"'{col}' mezcla texto y números.")
                    recommendations.append(f"Revisar tipo de dato en '{col}'.")
        except Exception:
            pass

    total_obj = len(df.select_dtypes(include="object").columns)
    consistency = 1.0 - (mixed_cols / total_obj) if total_obj > 0 else 1.0

    score = (completeness * 0.40 + uniqueness * 0.30 + consistency * 0.30) * 100

    if total_rows < 20:
        issues.append("Dataset muy pequeño (< 20 filas).")
    if not issues:
        recommendations.append("¡Excelente calidad de datos! Puedes proceder con confianza.")

    return QualityReport(
        score=round(score, 1),
        completeness=round(completeness * 100, 1),
        uniqueness=round(uniqueness * 100, 1),
        consistency=round(consistency * 100, 1),
        issues=issues,
        recommendations=recommendations,
        column_detail=column_detail,
    )


def score_label(score: float) -> tuple[str, str]:
    if score >= 90:
        return "Excelente", "#16A34A"
    elif score >= 75:
        return "Bueno", "#003087"
    elif score >= 55:
        return "Aceptable", "#D97706"
    else:
        return "Crítico", "#DC2626"
