"""
Módulo de Conectores — ADIC Platform Procaps
Carga datos desde Excel, CSV o datasets de muestra anonimizados.
"""

from __future__ import annotations

import io
import pandas as pd
import numpy as np
from pathlib import Path


def load_from_upload(uploaded_file) -> tuple[pd.DataFrame, str]:
    """
    Carga un DataFrame desde un archivo subido por Streamlit.
    Soporta .xlsx, .xls, .csv.
    """
    name = uploaded_file.name
    ext = Path(name).suffix.lower()

    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(uploaded_file)
    elif ext == ".csv":
        raw = uploaded_file.read()
        sample = raw[:4096].decode("utf-8", errors="replace")
        sep = ";" if sample.count(";") > sample.count(",") else ","
        df = pd.read_csv(io.BytesIO(raw), sep=sep)
    else:
        raise ValueError(f"Formato no soportado: {ext}. Use .xlsx, .xls o .csv")

    df = _clean_column_names(df)
    return df, name


def load_sample(name: str) -> tuple[pd.DataFrame, str]:
    """Carga un dataset de muestra anonimizado para demostración."""
    df = _generate_synthetic(name)
    return df, f"Muestra: {name}"


def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres de columnas."""
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _generate_synthetic(dataset_name: str) -> pd.DataFrame:
    """
    Genera datos sintéticos anonimizados según el tipo de reporte.
    TODOS los datos son ficticios y no corresponden a personas reales.
    """
    rng = np.random.default_rng(42)
    n = 300

    if "Nómina" in dataset_name:
        cargos = ["Analista Jr", "Analista Sr", "Coordinador", "Jefe de Área", "Director", "Auxiliar", "Técnico"]
        areas = ["Producción", "Comercial", "RRHH", "Finanzas", "Operaciones", "Calidad", "Logística"]
        ciudades = ["Barranquilla", "Bogotá", "Medellín", "Cali"]
        df = pd.DataFrame({
            "Codigo_Empleado": [f"EMP-{1000+i}" for i in range(n)],
            "Cargo": rng.choice(cargos, n),
            "Area": rng.choice(areas, n),
            "Ciudad": rng.choice(ciudades, n),
            "Salario_Base_COP": rng.integers(1_500_000, 12_000_000, n),
            "Antiguedad_Anos": rng.integers(0, 25, n),
            "Tipo_Contrato": rng.choice(["Indefinido", "Fijo", "Obra/Labor"], n, p=[0.65, 0.25, 0.10]),
            "Mes": rng.choice(["Ene", "Feb", "Mar", "Abr", "May", "Jun"], n),
            "Estado": rng.choice(["Activo", "Inactivo"], n, p=[0.92, 0.08]),
        })
        df["Auxilio_Transporte"] = np.where(df["Salario_Base_COP"] <= 2_600_000, 162_000, 0)
        df["Total_Devengado"] = df["Salario_Base_COP"] + df["Auxilio_Transporte"]
        df["Retencion_Fuente"] = (df["Salario_Base_COP"] * rng.uniform(0, 0.08, n)).astype(int)
        df["Neto_Pagar"] = df["Total_Devengado"] - df["Retencion_Fuente"]

    elif "Ventas" in dataset_name:
        productos = ["Vitamina C 500mg", "Suero Oral", "Antigripal", "Antiinflamatorio",
                     "Probiótico", "Calcio D3", "Multivitamínico", "Ibuprofeno 400mg"]
        regiones = ["Caribe", "Andina", "Pacífico", "Llanos", "Santanderes"]
        canales = ["Droguería", "Hospital", "Clínica", "Supermercado", "E-commerce"]
        fechas = pd.date_range("2024-01-01", periods=n, freq="D").tolist()
        df = pd.DataFrame({
            "Fecha": rng.choice(fechas, n),
            "Producto": rng.choice(productos, n),
            "Region": rng.choice(regiones, n),
            "Canal": rng.choice(canales, n),
            "Unidades_Vendidas": rng.integers(50, 2000, n),
            "Precio_Unitario_COP": rng.integers(3_000, 45_000, n),
            "Representante": [f"REP-{rng.integers(1,20)}" for _ in range(n)],
            "Meta_Mensual_COP": rng.integers(10_000_000, 80_000_000, n),
        })
        df["Ingreso_COP"] = df["Unidades_Vendidas"] * df["Precio_Unitario_COP"]
        df["Costo_COP"] = (df["Ingreso_COP"] * rng.uniform(0.45, 0.65, n)).astype(int)
        df["Margen_COP"] = df["Ingreso_COP"] - df["Costo_COP"]
        df["Cumplimiento_Pct"] = (df["Ingreso_COP"] / df["Meta_Mensual_COP"] * 100).round(1)
        df["Fecha"] = pd.to_datetime(df["Fecha"])

    elif "Producción" in dataset_name or "Operaciones" in dataset_name:
        lineas = ["Línea A - Sólidos", "Línea B - Líquidos", "Línea C - Inyectables", "Línea D - Tópicos"]
        productos = ["Tableta 500mg", "Jarabe 120ml", "Ampolla 5ml", "Crema 50g", "Cápsula 250mg"]
        df = pd.DataFrame({
            "Numero_Lote": [f"LOT-{2024000+i}" for i in range(n)],
            "Fecha_Produccion": pd.date_range("2024-01-01", periods=n, freq="12h"),
            "Linea_Produccion": rng.choice(lineas, n),
            "Producto": rng.choice(productos, n),
            "Unidades_Programadas": rng.integers(5_000, 50_000, n),
            "Unidades_Producidas": rng.integers(4_500, 50_000, n),
            "Unidades_Rechazadas": rng.integers(0, 500, n),
            "Tiempo_Ciclo_Min": rng.integers(120, 480, n),
            "Operario_Codigo": [f"OP-{rng.integers(1,30):02d}" for _ in range(n)],
            "Turno": rng.choice(["Mañana", "Tarde", "Noche"], n),
            "Estado_Lote": rng.choice(["Aprobado", "Cuarentena", "Rechazado"], n, p=[0.85, 0.10, 0.05]),
        })
        df["Eficiencia_Pct"] = (df["Unidades_Producidas"] / df["Unidades_Programadas"] * 100).round(1)
        df["Tasa_Rechazo_Pct"] = (df["Unidades_Rechazadas"] / df["Unidades_Producidas"] * 100).round(2)

    elif "Finanzas" in dataset_name:
        centros = ["Producción", "Comercial", "Administrativo", "I+D", "Logística", "RRHH"]
        conceptos = ["Salarios", "Materias Primas", "Servicios Públicos",
                     "Mantenimiento", "Marketing", "Capacitación", "Tecnología"]
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                 "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        df = pd.DataFrame({
            "Mes": rng.choice(meses, n),
            "Centro_Costo": rng.choice(centros, n),
            "Concepto": rng.choice(conceptos, n),
            "Presupuesto_COP": rng.integers(5_000_000, 200_000_000, n),
            "Ejecutado_COP": rng.integers(4_000_000, 210_000_000, n),
            "Ano": rng.choice([2024, 2025], n),
        })
        df["Variacion_COP"] = df["Ejecutado_COP"] - df["Presupuesto_COP"]
        df["Variacion_Pct"] = (df["Variacion_COP"] / df["Presupuesto_COP"] * 100).round(1)
        df["Estado"] = np.where(df["Variacion_Pct"] > 10, "Sobre presupuesto",
                       np.where(df["Variacion_Pct"] < -10, "Bajo presupuesto", "En rango"))

    else:  # General
        df = pd.DataFrame({
            "ID": range(1, n+1),
            "Fecha": pd.date_range("2024-01-01", periods=n, freq="D"),
            "Categoria": rng.choice(["A", "B", "C", "D"], n),
            "Subcategoria": rng.choice(["X1", "X2", "Y1", "Y2"], n),
            "Valor_Principal": rng.uniform(100, 10_000, n).round(2),
            "Valor_Secundario": rng.uniform(50, 5_000, n).round(2),
            "Cantidad": rng.integers(1, 500, n),
            "Region": rng.choice(["Norte", "Sur", "Centro", "Este", "Oeste"], n),
        })
        df["Total"] = df["Valor_Principal"] * df["Cantidad"]

    return df
