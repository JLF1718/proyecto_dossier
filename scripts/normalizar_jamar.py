#!/usr/bin/env python3
"""Normalización rápida para CSV JAMAR -> formato esperado por dashboard.

Ejecutar desde la raíz del repo:
    python scripts/normalizar_jamar.py

Genera `data/ctrl_dosieres_JAMAR_normalizado.csv`.
"""
from pathlib import Path
import pandas as pd


IN_PATH = Path("data/ctrl_dosieres_JAMAR.csv")
OUT_PATH = Path("data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv")

def main():
    if not IN_PATH.exists():
        raise SystemExit(f"Archivo no encontrado: {IN_PATH}\nCopia el CSV en la carpeta data/ primero.")

    # Leer todo como texto para evitar inferencia incorrecta
    df = pd.read_csv(IN_PATH, dtype=str)

    # Renombrar columnas base al esquema que usa dashboard
    rename_map = {
        "Dossier_Estatus": "ESTATUS",
        "Peso_Plano": "PESO",
        "Bastidor": "BLOQUE",
        "Etapa": "ETAPA",
        # columnas de fecha originales
        # "Fecha_entrega", "Fecha_respuesta_contratista", etc.
    }
    df = df.rename(columns=rename_map)

    # Normalizar ETAPA
    if "ETAPA" in df.columns:
        df["ETAPA"] = df["ETAPA"].astype(str).str.strip().str.replace(" ", "_").str.upper()

    # Mapeo de estatus JAMAR -> canónico del dashboard
    status_map = {
        "NO_INICIADO": "PLANEADO",
        "OBSERVADO": "OBSERVADO",  # A corrección (contratista atendiendo comentarios)
        "LIBERADO": "LIBERADO",
        "POR_ASIGNAR": "PLANEADO",
        # valores que indiquen que el documento está en revisión por tu parte
        "EN_REVISION": "EN_REVISIÓN",
        "REVISANDO": "EN_REVISIÓN",
    }

    if "ESTATUS" in df.columns:
        df["ESTATUS_RAW"] = df["ESTATUS"].astype(str).str.strip()
        df["ESTATUS"] = df["ESTATUS_RAW"].map(status_map).fillna(df["ESTATUS_RAW"]).astype(str)

    # Mapear fechas a las columnas R1 que espera el dashboard
    # Usamos dayfirst=True para formatos dd/mm/yyyy
    df["BAYSA ENTREGA FECHA R1"] = pd.to_datetime(df.get("Fecha_entrega"), dayfirst=True, errors="coerce")
    df["INPROS RESPUESTA FECHA R1"] = pd.to_datetime(df.get("Fecha_respuesta_contratista"), dayfirst=True, errors="coerce")
    df["BAYSA ENTREGA FECHA R1"] = df["BAYSA ENTREGA FECHA R1"]
    df["INPROS RESPUESTA FECHA R1"] = df["INPROS RESPUESTA FECHA R1"]

    # Crear columnas vacías para R2..R7 si no existen
    for side in ["BAYSA ENTREGA FECHA", "INPROS RESPUESTA FECHA"]:
        for r in range(2, 8):
            col = f"{side} R{r}"
            if col not in df.columns:
                df[col] = pd.NaT

    # PESO numeric
    if "PESO" in df.columns:
        df["PESO"] = pd.to_numeric(df["PESO"].str.replace(",", ".", regex=False), errors="coerce").fillna(0)
    else:
        df["PESO"] = 0

    # PESO_LIBERADO: por defecto NaN; copiar PESO si ESTATUS == LIBERADO
    df["PESO_LIBERADO"] = pd.NA
    if "ESTATUS" in df.columns:
        df.loc[df["ESTATUS"] == "LIBERADO", "PESO_LIBERADO"] = df.loc[df["ESTATUS"] == "LIBERADO", "PESO"]

    # Asegurar columna identificadora: si no hay BLOQUE, usar Plano
    if "BLOQUE" not in df.columns and "Plano" in df.columns:
        df = df.rename(columns={"Plano": "BLOQUE"})

    # Guardar CSV normalizado
    df.to_csv(OUT_PATH, index=False)

    # Resumen rápido
    print("Normalización completada:", OUT_PATH)
    print(df["ESTATUS"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
