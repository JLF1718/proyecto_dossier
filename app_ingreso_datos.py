#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
App de Ingreso de Datos para CSV Normalizados
=============================================

Permite agregar filas a los CSV que alimentan los dashboards:
- BAYSA: data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv
- JAMAR: data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv

Campos mínimos que afectan gráficas/tablas:
- BLOQUE (texto)
- ETAPA (texto)
- ESTATUS (PLANEADO, OBSERVADO, EN_REVISIÓN, LIBERADO)
- PESO (kg)
- ENTREGA (solo BAYSA, código semana p.ej. S186)
- No. REVISIÓN (opcional, para Gantt)

Ejecutar:
    streamlit run app_ingreso_datos.py
"""

import re
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

BASE = Path(__file__).parent
CSV_PATHS = {
    "BAYSA": BASE / "data/contratistas/BAYSA/ctrl_dosieres_BAYSA_normalizado.csv",
    "JAMAR": BASE / "data/contratistas/JAMAR/ctrl_dosieres_JAMAR_normalizado.csv",
}

# CSV fuente originales
CSV_FUENTE_PATHS = {
    "BAYSA": BASE / "data/contratistas/BAYSA/ctrl_dosieres.csv",
    "JAMAR": BASE / "data/ctrl_dosieres_JAMAR.csv",
}

ESTATUS_OPCIONES = ["PLANEADO", "OBSERVADO", "EN_REVISIÓN", "LIBERADO"]

# Algunas etapas comunes; editable libremente
ETAPAS_SUGERIDAS = [
    "INGENIERIA", "DISEÑO", "FABRICACION", "MONTAJE", "PRUEBAS", "ENTREGA"
]

st.set_page_config(page_title="Ingreso de Datos - Dossieres", page_icon="📝", layout="centered")
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {font-weight:600;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("📝 Ingreso de Datos a CSV (Normalizado)")
st.caption("Agrega registros mínimos que impactan las tablas y gráficos del proyecto.")

contratista = st.selectbox("Contratista", ["BAYSA", "JAMAR"], index=0)
origen = st.radio("Origen de datos para visualizar", ["Normalizado", "Fuente"], horizontal=True, index=0)

# Nota: si eliges "Fuente", el editor mostrará los datos del CSV de origen convertidos a esquema normalizado,
# pero los cambios se guardarán en el CSV normalizado. Esto evita recalcular manualmente.

def convertir_fuente_a_normalizado_preview(contr: str, df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if contr == "JAMAR":
        rename_map = {
            "Dossier_Estatus": "ESTATUS",
            "Peso_Plano": "PESO",
            "Bastidor": "BLOQUE",
            "Etapa": "ETAPA",
        }
        df = df.rename(columns=rename_map)
    # Selección robusta de columnas
    def pick(col, alternativas):
        for a in [col] + alternativas:
            if a in df.columns:
                return a
        return None
    cols = {}
    for col, alts in {
        "BLOQUE": ["DOSIER", "SUBESTACION", "Plano", "Bloque"],
        "ETAPA": ["Etapa", "ETAPAS"],
        "ESTATUS": ["Estatus", "STATUS"],
        "PESO": ["Peso", "PESO_KG", "Peso_Plano"],
        "No. REVISIÓN": ["No. REVISIÓN", "No_REVISION"],
        "ENTREGA": ["ENTREGA", "Semana", "Semana_entrega"],
    }.items():
        src = pick(col, alts)
        if src:
            cols[col] = df[src]
        else:
            cols[col] = pd.NA
    out = pd.DataFrame(cols)
    # Tipos
    out["PESO"] = pd.to_numeric(out["PESO"], errors="coerce").fillna(0.0)
    return out


def normalizar_estatus(df: pd.DataFrame) -> pd.DataFrame:
    """Mapea estatus al canónico que usan dashboards."""
    status_map = {
        "NO_INICIADO": "PLANEADO",
        "POR_ASIGNAR": "PLANEADO",
        "PLANEADO": "PLANEADO",
        "OBSERVADO": "OBSERVADO",
        "EN_REVISION": "EN_REVISIÓN",
        "EN_REVISION": "EN_REVISIÓN",
        "EN_REVISIÓN": "EN_REVISIÓN",
        "INPROS_REVISANDO": "EN_REVISIÓN",
        "LIBERADO": "LIBERADO",
        "BAYSA_ATENDIENDO_COMENTARIOS": "OBSERVADO",
    }
    if "ESTATUS" in df.columns:
        df["ESTATUS"] = df["ESTATUS"].astype(str).str.strip().str.upper()
        df["ESTATUS"] = df["ESTATUS"].map(status_map).fillna(df["ESTATUS"])
    return df

# Cargar CSV (normalizado o fuente) para sugerencias y resumen
def leer_csv_robusto(ruta: Path) -> pd.DataFrame:
    """Lee CSV con fallback automático de encodings."""
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
        try:
            return pd.read_csv(ruta, encoding=enc)
        except (UnicodeDecodeError, Exception):
            continue
    return pd.DataFrame()

df_existente = pd.DataFrame()
try:
    if origen == "Normalizado" and CSV_PATHS[contratista].exists():
        df_existente = leer_csv_robusto(CSV_PATHS[contratista])
    elif origen == "Fuente" and CSV_FUENTE_PATHS[contratista].exists():
        df_src = leer_csv_robusto(CSV_FUENTE_PATHS[contratista])
        df_existente = convertir_fuente_a_normalizado_preview(contratista, df_src)
    df_existente = normalizar_estatus(df_existente)
except Exception:
    df_existente = pd.DataFrame()

col1, col2 = st.columns(2)
with col1:
    bloque = st.text_input("BLOQUE", placeholder="Ej: BLOQUE-123")
    etapa = st.selectbox("ETAPA", options=sorted(set(ETAPAS_SUGERIDAS + list(df_existente.get("ETAPA", [])))), index=0 if ETAPAS_SUGERIDAS else None)
with col2:
    estatus = st.selectbox("ESTATUS", ESTATUS_OPCIONES, index=0)
    peso_kg = st.number_input("PESO (kg)", min_value=0.0, step=1.0, format="%f")

entrega = None
no_revision = None

if contratista == "BAYSA":
    entrega = st.text_input("ENTREGA (semana)", placeholder="Ej: S186")
    no_revision = st.number_input("No. REVISIÓN (opcional)", min_value=0, step=1)
else:
    no_revision = st.number_input("No. REVISIÓN (opcional)", min_value=0, step=1)

st.divider()

def validar_entrada() -> list:
    errores = []
    if not bloque.strip():
        errores.append("BLOQUE es obligatorio")
    if not etapa or not str(etapa).strip():
        errores.append("ETAPA es obligatoria")
    if estatus not in ESTATUS_OPCIONES:
        errores.append("ESTATUS inválido")
    if peso_kg is None or float(peso_kg) <= 0:
        errores.append("PESO debe ser mayor a 0")
    if contratista == "BAYSA":
        if not entrega or not re.fullmatch(r"S\d{3}", entrega.strip()):
            errores.append("ENTREGA debe tener formato S###, p.ej. S186")
    return errores

def asegurar_esquema(df: pd.DataFrame, contratista: str) -> pd.DataFrame:
    # Columnas mínimas
    cols = ["BLOQUE", "ETAPA", "ESTATUS", "PESO"]
    if contratista == "BAYSA":
        cols += ["ENTREGA"]
    # Opcionales
    cols += ["No. REVISIÓN"]
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df[cols]

def agregar_fila():
    errores = validar_entrada()
    if errores:
        st.error("\n".join([f"• {e}" for e in errores]))
        return

    ruta = CSV_PATHS[contratista]
    ruta.parent.mkdir(parents=True, exist_ok=True)

    # Construir DataFrame de la nueva fila
    nueva = {
        "BLOQUE": bloque.strip(),
        "ETAPA": str(etapa).strip(),
        "ESTATUS": estatus,
        "PESO": float(peso_kg),  # en kg
        "No. REVISIÓN": int(no_revision) if no_revision is not None else pd.NA,
    }
    if contratista == "BAYSA":
        nueva["ENTREGA"] = entrega.strip()

    df_new = pd.DataFrame([nueva])

    # Cargar existente y asegurar esquema
    if ruta.exists():
        df_old = leer_csv_robusto(ruta)
    else:
        df_old = pd.DataFrame()

    df_old = asegurar_esquema(df_old, contratista)
    df_new = asegurar_esquema(df_new, contratista)

    # Evitar duplicado simple por BLOQUE + ETAPA + CONTRATISTA (+ENTREGA en BAYSA)
    clave_cols = ["BLOQUE", "ETAPA"] + (["ENTREGA"] if contratista == "BAYSA" else [])
    if not df_old.empty:
        existe = ((df_old[clave_cols].astype(str) == df_new.iloc[0][clave_cols].astype(str)).all(axis=1)).any()
        if existe:
            st.warning("Registro similar ya existe (misma clave). Se agregará de todos modos.")

    df_final = pd.concat([df_old, df_new], ignore_index=True)

    # Guardar
    df_final.to_csv(ruta, index=False, encoding="utf-8-sig")

    st.success(f"✅ Registro agregado a {ruta.relative_to(BASE)}")
    st.dataframe(df_new, use_container_width=True)

    # Resumen rápido
    try:
        total = len(df_final)
        liberados = (df_final["ESTATUS"] == "LIBERADO").sum()
        peso_total_ton = df_final["PESO"].sum() / 1000.0
        st.info(f"Total registros: {total} | Liberados: {liberados} | Peso total: {peso_total_ton:,.0f} ton")
    except Exception:
        pass

if st.button("➕ Agregar Registro"):
    agregar_fila()

st.divider()
st.caption("Tip: El peso se guarda en kg (las tablas convierten a toneladas). Para BAYSA, ENTREGA usa formato S### (semana de proyecto).")

# =====================
# Editar / Actualizar Registros
# =====================
st.divider()
st.subheader("✏️ Editar / Actualizar Registros")

def cargar_df_con_esquema(contr: str) -> pd.DataFrame:
    ruta = CSV_PATHS[contr]
    if ruta.exists():
        try:
            # Intentar diferentes encodings
            for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                try:
                    df = pd.read_csv(ruta, encoding=enc)
                    return asegurar_esquema(df, contr)
                except UnicodeDecodeError:
                    continue
            df = pd.DataFrame()
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()
    return asegurar_esquema(df, contr)

if not df_existente.empty:
    df_edit = asegurar_esquema(df_existente.copy(), contratista)
else:
    df_edit = cargar_df_con_esquema(contratista)

if df_edit.empty:
    st.info("No hay registros aún para editar.")
else:
    # Filtros simples
    if "filtros" not in st.session_state:
        st.session_state["filtros"] = {
            "bloque": "",
            "etapa": "",
            "estatus": "",
            "entrega": ""
        }
    if st.button("Limpiar filtros"):
        st.session_state["filtros"] = {
            "bloque": "",
            "etapa": "",
            "estatus": "",
            "entrega": ""
        }
        # Resetear estado de widgets para que el panel refleje el limpiado
        st.session_state["filtro_bloque"] = ""
        st.session_state["filtro_etapa"] = ""
        st.session_state["filtro_estatus"] = ""
        if "filtro_entrega" in st.session_state:
            st.session_state["filtro_entrega"] = ""
        st.rerun()
    fcol1, fcol2, fcol3, fcol4 = st.columns([1, 1, 1, 1])
    with fcol1:
        filtro_bloque = st.text_input("Buscar BLOQUE (contiene)", value=st.session_state["filtros"]["bloque"], key="filtro_bloque")
        st.session_state["filtros"]["bloque"] = filtro_bloque
    with fcol2:
        opciones_etapa = [""] + sorted([e for e in df_edit["ETAPA"].dropna().astype(str).unique().tolist() if e])
        filtro_etapa = st.selectbox("Filtrar por ETAPA", opciones_etapa, index=opciones_etapa.index(st.session_state["filtros"]["etapa"]) if st.session_state["filtros"]["etapa"] in opciones_etapa else 0, key="filtro_etapa")
        st.session_state["filtros"]["etapa"] = filtro_etapa
    with fcol3:
        opciones_estatus = [""] + ESTATUS_OPCIONES
        filtro_estatus = st.selectbox("Filtrar por ESTATUS", opciones_estatus, index=opciones_estatus.index(st.session_state["filtros"]["estatus"]) if st.session_state["filtros"]["estatus"] in opciones_estatus else 0, key="filtro_estatus")
        st.session_state["filtros"]["estatus"] = filtro_estatus
    with fcol4:
        if contratista == "BAYSA":
            opciones_entrega = [""] + sorted([s for s in df_edit.get("ENTREGA", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if s])
            filtro_entrega = st.selectbox("Filtrar por ENTREGA (semana)", opciones_entrega, index=opciones_entrega.index(st.session_state["filtros"]["entrega"]) if st.session_state["filtros"]["entrega"] in opciones_entrega else 0, key="filtro_entrega")
            st.session_state["filtros"]["entrega"] = filtro_entrega
        else:
            filtro_entrega = None
            st.write("")  # Espacio vacío para mantener alineación

    df_filtrado = df_edit.copy()
    if filtro_bloque:
        df_filtrado = df_filtrado[df_filtrado["BLOQUE"].astype(str).str.contains(filtro_bloque, case=False, na=False)]
    if filtro_etapa:
        df_filtrado = df_filtrado[df_filtrado["ETAPA"].astype(str) == filtro_etapa]
    if filtro_estatus:
        df_filtrado = df_filtrado[df_filtrado["ESTATUS"].astype(str) == filtro_estatus]
    if contratista == "BAYSA" and filtro_entrega:
        df_filtrado = df_filtrado[df_filtrado["ENTREGA"].astype(str) == filtro_entrega]

    # Agregar índice original para aplicar cambios
    df_filtrado = df_filtrado.reset_index().rename(columns={"index": "__idx"})

    # Editor de datos (solo columnas relevantes para gráficas/tablas)
    cols_editables = ["BLOQUE", "ETAPA", "ESTATUS", "PESO", "No. REVISIÓN"]

    column_config = {
        "BLOQUE": st.column_config.TextColumn("BLOQUE"),
        "ETAPA": st.column_config.TextColumn("ETAPA"),
        "ESTATUS": st.column_config.SelectboxColumn("ESTATUS", options=ESTATUS_OPCIONES),
        "PESO": st.column_config.NumberColumn("PESO (kg)", min_value=0.0, step=1.0),
        "No. REVISIÓN": st.column_config.NumberColumn("No. REVISIÓN", min_value=0, step=1),
    }

    # Reindex explícito para mostrar solo columnas necesarias en orden fijo
    df_view = df_filtrado[["__idx"] + cols_editables].set_index("__idx")

    st.caption("Edita directamente en la tabla. Luego pulsa 'Guardar Cambios'.")
    edited = st.data_editor(
        df_view,
        column_config=column_config,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        key=f"editor_{contratista}"
    )

    def validar_fila_editada(row: pd.Series) -> list:
        errores = []
        if not str(row.get("BLOQUE", "")).strip():
            errores.append("BLOQUE vacío")
        if not str(row.get("ETAPA", "")).strip():
            errores.append("ETAPA vacía")
        if row.get("ESTATUS") not in ESTATUS_OPCIONES:
            errores.append("ESTATUS inválido")
        try:
            peso = float(row.get("PESO", 0))
            if peso < 0:
                errores.append("PESO negativo")
        except Exception:
            errores.append("PESO inválido")
        if contratista == "BAYSA":
            ent = str(row.get("ENTREGA", "")).strip()
            if ent and not re.fullmatch(r"S\d{3}", ent):
                errores.append("ENTREGA debe ser S### (p.ej. S186)")
        return errores

    def guardar_cambios():
        # Siempre guardamos en el normalizado
        ruta = CSV_PATHS[contratista]

        # Leer el DataFrame completo actual
        df_actual = leer_csv_robusto(ruta)

        # Aplicar cambios solo a las filas editadas (por índice original)
        df_editado = df_actual.copy()
        for idx, r in edited.iterrows():
            # idx es el índice original (__idx)
            for col in r.index:
                if col != "__idx" and col in df_editado.columns:
                    df_editado.at[idx, col] = r[col]
        # Validar todas las filas editadas
        for idx, r in edited.iterrows():
            errs = validar_fila_editada(r)
            if errs:
                st.error("Fila {}: \n".format(idx) + "\n".join([f"• {e}" for e in errs]))
                return

        # Crear backup del archivo ACTUAL antes de sobrescribir
        try:
            from utils_backup import crear_backup_automatico
            crear_backup_automatico(ruta, mantener_ultimos=10)
        except Exception as e:
            st.warning(f"No se pudo crear backup automático: {e}")

        # Guardar definitivo
        df_editado.to_csv(ruta, index=False, encoding="utf-8-sig")
        st.success("✅ Cambios guardados en el CSV normalizado (todas las filas conservadas)")
        st.rerun()

    if st.button("💾 Guardar Cambios"):
        guardar_cambios()
# Resumen Ejecutivo
# =====================
st.divider()
st.subheader("📈 Resumen Ejecutivo")
if not df_existente.empty:
    try:
        total = len(df_existente)
        liberados = (df_existente.get("ESTATUS", pd.Series(dtype=str)) == "LIBERADO").sum()
        observados = (df_existente.get("ESTATUS", pd.Series(dtype=str)) == "OBSERVADO").sum()
        enrev = (df_existente.get("ESTATUS", pd.Series(dtype=str)) == "EN_REVISIÓN").sum()
        planeados = (df_existente.get("ESTATUS", pd.Series(dtype=str)) == "PLANEADO").sum()
        peso_total_ton = df_existente.get("PESO", pd.Series(dtype=float)).fillna(0).sum() / 1000.0

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total", f"{total}")
        c2.metric("Liberados", f"{liberados}")
        c3.metric("Observados", f"{observados}")
        c4.metric("En Revisión", f"{enrev}")
        c5.metric("Planeados", f"{planeados}")
        c6.metric("Peso Total (ton)", f"{peso_total_ton:,.0f}")

        if contratista == "BAYSA" and "ENTREGA" in df_existente.columns:
            entregas = (
                df_existente[df_existente["ENTREGA"].notna()]
                .groupby("ENTREGA")
                .agg(Planeados=("BLOQUE", "count"), Peso=("PESO", lambda x: x.sum()/1000))
                .sort_index()
            )
            # Agregar fila de totales
            total_planeados = entregas["Planeados"].sum()
            total_peso = entregas["Peso"].sum()
            entregas = pd.concat([
                entregas,
                pd.DataFrame({
                    "Planeados": [total_planeados],
                    "Peso": [total_peso]
                }, index=["TOTAL"])
            ])
            st.caption("Próximas entregas (BAYSA):")
            st.dataframe(entregas.reset_index(), use_container_width=True)
    except Exception:
        pass
else:
    # Sugerir normalización si hay fuente pero no normalizado
    if origen == "Normalizado" and CSV_FUENTE_PATHS[contratista].exists() and not CSV_PATHS[contratista].exists():
        st.warning("No se encontró el CSV normalizado, pero existe el CSV fuente. Puedes normalizarlo aquí.")
        def normalizar_desde_fuente():
            try:
                import subprocess, sys
                script = "scripts/normalizar_baysa.py" if contratista == "BAYSA" else "scripts/normalizar_jamar.py"
                r = subprocess.run([sys.executable, "-X", "utf8", script], capture_output=True, text=True, encoding="utf-8", errors="replace")
                ok = r.returncode == 0
                st.success("✅ Normalización completada" if ok else "❌ Error normalizando datos")
                with st.expander("Ver salida de normalización"):
                    st.text(r.stdout or "(sin salida)")
                    if r.stderr:
                        st.text("\n[stderr]\n" + r.stderr)
            except Exception as e:
                st.error(f"Error: {e}")
        if st.button("🛠️ Normalizar datos fuente"):
            normalizar_desde_fuente()

# =====================
# Botón para generar dashboards
# =====================
st.divider()
st.subheader("🚀 Generar Dashboards y Tablas")
semana_corte = st.text_input("Semana de corte (formato S###)", value="S186")

def validar_semana(s: str) -> bool:
    return bool(re.fullmatch(r"S\d{1,4}", s.strip().upper()))

def generar_dashboards(semana: str):
    """Genera dashboards individuales para la semana especificada."""
    if not validar_semana(semana):
        st.error("Semana inválida. Usa formato S###, por ejemplo S186.")
        return
    with st.spinner(f"⏳ Generando dashboards para {semana.upper()}..."):
        try:
            import subprocess, sys, os
            from pathlib import Path
            working_dir = str(Path(__file__).parent)
            semana_upper = semana.strip().upper()
            # Ejecutar dashboard.py para JAMAR y BAYSA
            for contratista in ["JAMAR", "BAYSA"]:
                script = "dashboard.py"
                env = os.environ.copy()
                env["PYTHONUTF8"] = "1"
                env["PYTHONIOENCODING"] = "utf-8"
                env["SEMANA_CORTE"] = semana_upper
                env["CONTRATISTA"] = contratista
                r = subprocess.run([
                    sys.executable, "-X", "utf8", script, "--no-cache"
                ], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=working_dir, env=env)
                if r.returncode != 0:
                    st.error(f"❌ Error generando dashboard para {contratista}")
                    with st.expander(f"Ver salida de {contratista}"):
                        st.text(r.stdout or "(sin salida)")
                        if r.stderr:
                            st.text("\n[stderr]\n" + r.stderr)
                    return
            st.success("✅ Dashboards generados correctamente")
            # Mostrar archivos recientes
            out_dash = BASE / "output" / "dashboards"
            archivos_dash = []
            if out_dash.exists():
                archivos_dash = sorted(out_dash.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)[:6]
            if archivos_dash:
                st.caption("📁 Dashboards recientes generados:")
                for p in archivos_dash:
                    st.write(f"• {p.name}")
        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")
            import traceback
            st.text(traceback.format_exc())

def generar_tablas(semana: str):
    """Genera tablas consolidadas para la semana especificada."""
    if not validar_semana(semana):
        st.error("Semana inválida. Usa formato S###, por ejemplo S186.")
        return
    with st.spinner(f"⏳ Generando tablas para {semana.upper()}..."):
        try:
            import subprocess, sys, os
            from pathlib import Path
            import streamlit.components.v1 as components
            working_dir = str(Path(__file__).parent)
            semana_upper = semana.strip().upper()
            script = "dashboard_consolidado.py"
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["SEMANA_CORTE"] = semana_upper
            st.info(f"Ejecutando: {sys.executable} -X utf8 {script}\nCWD: {working_dir}\nSEMANA_CORTE: {semana_upper}")
            try:
                r = subprocess.run([
                    sys.executable, "-X", "utf8", script
                ], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=working_dir, env=env, timeout=30)
            except subprocess.TimeoutExpired as e:
                st.error("⏱️ Timeout: El proceso tardó más de 30 segundos y fue cancelado.")
                with st.expander("Ver salida parcial del proceso"):
                    if hasattr(e, 'output') and e.output:
                        st.text(e.output)
                    if hasattr(e, 'stderr') and e.stderr:
                        st.text("\n[stderr]\n" + e.stderr)
                return
            st.info(f"[stdout]:\n{r.stdout}\n[stderr]:\n{r.stderr}")
            if r.returncode != 0:
                st.error(f"❌ Error generando tablas")
                with st.expander("Ver salida del proceso"):
                    st.text(r.stdout or "(sin salida)")
                    if r.stderr:
                        st.text("\n[stderr]\n" + r.stderr)
                return
            # Ejecutar exportar_bloques_liberados_json_html.py
            script2 = str(Path(working_dir) / "scripts" / "exportar_bloques_liberados_json_html.py")
            st.info(f"Ejecutando: {sys.executable} -X utf8 {script2}\nCWD: {working_dir}")
            r2 = subprocess.run([
                sys.executable, "-X", "utf8", script2
            ], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=working_dir, env=env)
            st.info(f"[stdout]:\n{r2.stdout}\n[stderr]:\n{r2.stderr}")
            if r2.returncode != 0:
                st.warning("Tablas generadas, pero error al generar bloques_liberados.html")
                with st.expander("Ver salida del proceso de bloques liberados"):
                    st.text(r2.stdout or "(sin salida)")
                    if r2.stderr:
                        st.text("\n[stderr]\n" + r2.stderr)
            else:
                st.success("✅ Tablas y bloques liberados generados correctamente")
                # Mostrar tabla bloques_liberados.html
                html_path = Path(working_dir) / "bloques_liberados.html"
                if html_path.exists():
                    with open(html_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    st.caption("Vista previa de bloques liberados:")
                    components.html(html_content, height=600, scrolling=True)
            # Mostrar archivos recientes
            out_tablas = BASE / "output" / "tablas"
            archivos_tablas = []
            if out_tablas.exists():
                archivos_tablas = sorted(out_tablas.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)[:6]
            if archivos_tablas:
                st.caption("📁 Tablas recientes generadas:")
                for p in archivos_tablas:
                    st.write(f"• {p.name}")
        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")
            import traceback
            st.text(traceback.format_exc())

if st.button("📄 Generar Dashboards (solo dashboards)"):
    generar_dashboards(semana_corte)
if st.button("📊 Generar Tablas (solo tablas)"):
    generar_tablas(semana_corte)
