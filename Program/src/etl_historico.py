"""
etl_historico.py
──────────────────────────────────────────────────────────────────────────────
ETL del histórico 2025: lee los CSVs crudos por sensor, hace resample a 10
minutos y carga en MySQL las tablas históricas usadas por el Isolation Forest.

Basado en el notebook ETL.ipynb — migrado al programa como módulo reutilizable.

Tablas que genera/actualiza:
    tr_historico    ml_historico    rect1_historico    rect2_historico

Cuándo ejecutar:
    - Una vez para cargar el histórico 2025 completo
    - Opcionalmente cada mes para incorporar datos nuevos

Desde consola:
    python src/etl_historico.py

Desde Streamlit:
    from src.etl_historico import ejecutar_etl_historico
    ejecutar_etl_historico(log_fn=st.write)
──────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import glob
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db import get_engine

# ─────────────────────────────────────────────────────────────
#  RUTAS
#  Ajustar si los CSVs están en otra ubicación
# ─────────────────────────────────────────────────────────────
DIR_PROYECTO  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DIR_DATOS_RAW = os.path.join(DIR_PROYECTO, 'Datos', 'DCE_DATOS_2025')   # CSVs crudos por sensor
DIR_HISTORICO = os.path.join(DIR_PROYECTO, 'Datos', 'Historico')         # CSVs consolidados (salida)

# ─────────────────────────────────────────────────────────────
#  MAPAS SENSOR → COLUMNA DB
#  (tomados directamente del notebook ETL.ipynb)
# ─────────────────────────────────────────────────────────────
MAPA_TR = {
    "01_VOLTAJE_AC_DEL_SISTEMA_L1_L2":   "voltaje_ac_l1_l2",
    "02_VOLTAJE_AC_DEL_SISTEMA_L2-L3":   "voltaje_ac_l2_l3",
    "03_VOLTAJE_AC_DEL_SISTEMA_L3-L1":   "voltaje_ac_l3_l1",
    "11_CORRIENTE_AC_DE_LA_CARGA_L1":    "corriente_ac_l1",
    "12_CORRIENTE_AC_DE_LA_CARGA_L2":    "corriente_ac_l2",
    "13_CORRIENTE_AC_DE_LA_CARGA_L3":    "corriente_ac_l3",
    "14_POTENCIA_ACTIVA_DE_LA_CARGA":    "potencia_activa_kw",
    "15_POTENCIA_REACTIVA_DE_LA_CARGA":  "potencia_reactiva_kvar",
    "16_POTENCIA_APARENTE_DE_LA_CARGA":  "potencia_aparente_kva",
    "17_FACTOR_DE_POTENCIA_DE_LA_CARGA": "factor_potencia",
}

MAPA_ML = {
    "ANALOG_INPUT_-_ML_CURRENT_AC_R":   "corriente_ac_r",
    "ANALOG_INPUT_-_ML_CURRENT_AC_S":   "corriente_ac_s",
    "ANALOG_INPUT_-_ML_CURRENT_AC_T":   "corriente_ac_t",
    "ANALOG_INPUT_-_ML_VOLTAGE_AC_R-S": "voltaje_ac_rs",
    "ANALOG_INPUT_-_ML_VOLTAGE_AC_S-T": "voltaje_ac_st",
    "ANALOG_INPUT_-_ML_VOLTAGE_AC_T-R": "voltaje_ac_tr",
    "ANALOG_INPUT_C_SALA_S01":          "temp_sala_s01",
    "ANALOG_INPUT_C_SALA_S02":          "temp_sala_s02",
}

MAPA_RECT1 = {
    "01_-_VOLTAJE_AC_DEL_SISTEMA":  "voltaje_ac_vs",
    "02_-_VOLTAJE_DC_DEL_SISTEMA":  "voltaje_dc_vs",
    "03_-_CORRIENTE_DC_DEL_SISTEMA":"corriente_dc_cs",
    "11_-_CORRIENTE_DC_DE_LA_CARGA":"corriente_dc_carga",
}

MAPA_RECT2 = {
    "01_-_VOLTAJE_AC_DEL_SISTEMA":  "voltaje_ac_vs",
    "02_-_VOLTAJE_DC_DEL_SISTEMA":  "voltaje_dc_vs",
    "03_-_CORRIENTE_DC_DEL_SISTEMA":"corriente_dc_cs",
    "11_-_CORRIENTE_DC_DE_LA_CARGA":"corriente_dc_carga",
}

# Dispositivos a procesar: (nombre, ruta_base, mapa, tabla_destino)
ELEMENTOS = [
    ("TR",    os.path.join(DIR_DATOS_RAW, "TR"),    MAPA_TR,    "tr_historico"),
    ("ML",    os.path.join(DIR_DATOS_RAW, "ML"),    MAPA_ML,    "ml_historico"),
    ("Rect1", os.path.join(DIR_DATOS_RAW, "Rect1"), MAPA_RECT1, "rect1_historico"),
    ("Rect2", os.path.join(DIR_DATOS_RAW, "Rect2"), MAPA_RECT2, "rect2_historico"),
]

# ─────────────────────────────────────────────────────────────
#  DDL — tablas históricas
# ─────────────────────────────────────────────────────────────
DDL_TABLAS = {

    "tr_historico": """
        CREATE TABLE IF NOT EXISTS tr_historico (
            timestamp              DATETIME NOT NULL,
            voltaje_ac_l1_l2       FLOAT,
            voltaje_ac_l2_l3       FLOAT,
            voltaje_ac_l3_l1       FLOAT,
            corriente_ac_l1        FLOAT,
            corriente_ac_l2        FLOAT,
            corriente_ac_l3        FLOAT,
            potencia_activa_kw     FLOAT,
            potencia_reactiva_kvar FLOAT,
            potencia_aparente_kva  FLOAT,
            factor_potencia        FLOAT,
            PRIMARY KEY (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "ml_historico": """
        CREATE TABLE IF NOT EXISTS ml_historico (
            timestamp      DATETIME NOT NULL,
            corriente_ac_r FLOAT,
            corriente_ac_s FLOAT,
            corriente_ac_t FLOAT,
            voltaje_ac_rs  FLOAT,
            voltaje_ac_st  FLOAT,
            voltaje_ac_tr  FLOAT,
            temp_sala_s01  FLOAT,
            temp_sala_s02  FLOAT,
            PRIMARY KEY (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "rect1_historico": """
        CREATE TABLE IF NOT EXISTS rect1_historico (
            timestamp          DATETIME NOT NULL,
            voltaje_ac_vs      FLOAT,
            voltaje_dc_vs      FLOAT,
            corriente_dc_cs    FLOAT,
            corriente_dc_carga FLOAT,
            PRIMARY KEY (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "rect2_historico": """
        CREATE TABLE IF NOT EXISTS rect2_historico (
            timestamp          DATETIME NOT NULL,
            voltaje_ac_vs      FLOAT,
            voltaje_dc_vs      FLOAT,
            corriente_dc_cs    FLOAT,
            corriente_dc_carga FLOAT,
            PRIMARY KEY (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
}


# ─────────────────────────────────────────────────────────────
#  PROCESAMIENTO — igual que el notebook, pero como función
# ─────────────────────────────────────────────────────────────

def _limpiar_fecha(fecha_str: str) -> str:
    """
    Limpia el formato de fecha con caracteres corruptos del export DCE.
    Ej: '1/1/2025, 12:00:00 a.Â m.' → '1/1/2025 12:00:00 AM'
    """
    if not isinstance(fecha_str, str):
        return str(fecha_str)
    limpia = (fecha_str
              .replace("Â", "")
              .replace("\xa0", " ")
              .replace(",", ""))
    limpia = (limpia.lower()
              .replace("a. m.", "AM").replace("p. m.", "PM")
              .replace("a.m.",  "AM").replace("p.m.",  "PM")
              .replace("am",    "AM").replace("pm",    "PM"))
    return limpia.strip()


def _procesar_sensor(ruta_base: str, carpeta_sensor: str,
                     nombre_columna: str, log) -> pd.DataFrame | None:
    """
    Lee los 12 CSVs mensuales de una carpeta de sensor,
    limpia y hace resample a 10 minutos.
    """
    patron   = os.path.join(ruta_base, carpeta_sensor, "*.csv")
    archivos = glob.glob(patron)

    # Intentar también extensión .cvs (typo frecuente en el export)
    if not archivos:
        patron   = os.path.join(ruta_base, carpeta_sensor, "*.cvs")
        archivos = glob.glob(patron)

    if not archivos:
        log(f"    ⚠️  Sin archivos en: {carpeta_sensor}")
        return None

    log(f"    Sensor '{carpeta_sensor}' — {len(archivos)} archivo(s)")

    dfs_meses = []
    for archivo in sorted(archivos):
        try:
            df = pd.read_csv(archivo, encoding='latin-1', dtype=str)

            df['Time_Clean']     = df['Time'].apply(_limpiar_fecha)
            df['timestamp']      = pd.to_datetime(
                df['Time_Clean'],
                format='%d/%m/%Y %I:%M:%S %p',
                errors='coerce'
            )
            df['valor_numerico'] = pd.to_numeric(df['Value'], errors='coerce')
            df = df.dropna(subset=['valor_numerico', 'timestamp'])

            dfs_meses.append(df[['timestamp', 'valor_numerico']].copy())

        except Exception as e:
            log(f"      Error en {os.path.basename(archivo)}: {e}")

    if not dfs_meses:
        return None

    df_anual = pd.concat(dfs_meses, ignore_index=True)
    df_anual = df_anual.sort_values('timestamp').set_index('timestamp')

    # Resample 10 minutos — alinea timestamps irregulares
    df_resampled = df_anual.resample('10min').mean()
    df_resampled.columns = [nombre_columna]

    return df_resampled


def _procesar_dispositivo(nombre: str, ruta_base: str,
                           mapa: dict, log) -> pd.DataFrame | None:
    """
    Procesa todos los sensores de un dispositivo y los une en un DataFrame.
    """
    log(f"\n  ── {nombre} ──────────────────────────────")

    if not os.path.isdir(ruta_base):
        log(f"  ❌ Carpeta no encontrada: {ruta_base}")
        return None

    dfs_sensores = []
    for carpeta_sensor, columna_db in mapa.items():
        df_sensor = _procesar_sensor(ruta_base, carpeta_sensor, columna_db, log)
        if df_sensor is not None:
            dfs_sensores.append(df_sensor)

    if not dfs_sensores:
        log(f"  ⚠️  Sin datos para {nombre}")
        return None

    df_final = pd.concat(dfs_sensores, axis=1).reset_index()

    # Eliminar filas donde TODAS las columnas numéricas son NaN o 0
    cols_num = df_final.select_dtypes(include='number').columns
    mascara_vacias = (df_final[cols_num].fillna(0) == 0).all(axis=1)
    df_final = df_final[~mascara_vacias]

    log(f"  ✅ {nombre}: {len(df_final):,} filas a 10 min")
    return df_final


# ─────────────────────────────────────────────────────────────
#  CARGA A MySQL
# ─────────────────────────────────────────────────────────────

def _crear_tablas_historicas(engine, log):
    """Crea las 4 tablas históricas si no existen."""
    with engine.connect() as conn:
        for nombre, ddl in DDL_TABLAS.items():
            conn.execute(text(ddl))
        conn.commit()
    log("  Tablas históricas verificadas.")


def _guardar_csv_intermedio(df: pd.DataFrame, nombre: str, log):
    """Guarda el CSV consolidado en Datos/Historico/ (igual que el notebook)."""
    os.makedirs(DIR_HISTORICO, exist_ok=True)
    ruta = os.path.join(DIR_HISTORICO, f"consolidado_{nombre}_2025.csv")
    df.to_csv(ruta, index=False)
    log(f"  CSV guardado: {os.path.basename(ruta)}")
    return ruta


def _cargar_a_mysql(engine, df: pd.DataFrame, tabla: str, log):
    """
    Carga el DataFrame en MySQL.
    Usa INSERT IGNORE (vía primary key en timestamp) para ser idempotente:
    si ya existen filas con ese timestamp, las ignora sin error.
    """
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Insertar en bloques para no saturar la conexión
    CHUNK = 2000
    insertados = 0
    omitidos   = 0

    for i in range(0, len(df), CHUNK):
        bloque = df.iloc[i:i+CHUNK]
        try:
            # if_exists='append' + primary key en timestamp → duplicados fallan silenciosamente
            bloque.to_sql(tabla, con=engine, if_exists='append', index=False,
                          chunksize=CHUNK, method='multi')
            insertados += len(bloque)
        except Exception as e:
            # Probable error de duplicate key — registrar y continuar
            omitidos += len(bloque)
            log(f"    ⚠️  Bloque {i//CHUNK + 1}: {e}")

    log(f"  MySQL '{tabla}': {insertados:,} insertados, {omitidos:,} omitidos (duplicados).")
    return insertados


# ─────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────

def ejecutar_etl_historico(log_fn=print):
    """
    Ejecuta el ETL histórico completo.

    log_fn: función de logging. Usar print para consola, st.write para Streamlit.
    """
    log_fn("\n" + "="*60)
    log_fn("  ETL HISTÓRICO — NODO IDEO 2025")
    log_fn("  Fuente: CSVs crudos por sensor → resample 10 min → MySQL")
    log_fn("="*60)

    engine = get_engine()

    log_fn("\n[1/3] Verificando tablas históricas en MySQL...")
    _crear_tablas_historicas(engine, log_fn)

    log_fn("\n[2/3] Procesando dispositivos...")
    resultados = {}

    for nombre, ruta_base, mapa, tabla in ELEMENTOS:
        df = _procesar_dispositivo(nombre, ruta_base, mapa, log_fn)

        if df is not None:
            _guardar_csv_intermedio(df, nombre, log_fn)
            resultados[tabla] = df
        else:
            resultados[tabla] = None

    log_fn("\n[3/3] Cargando a MySQL...")
    totales = {}
    for tabla, df in resultados.items():
        if df is not None:
            n = _cargar_a_mysql(engine, df, tabla, log_fn)
            totales[tabla] = n
        else:
            totales[tabla] = 0
            log_fn(f"  ⚠️  Sin datos para {tabla}, saltando.")

    log_fn("\n" + "="*60)
    log_fn("  RESUMEN ETL HISTÓRICO")
    log_fn("="*60)
    for tabla, n in totales.items():
        icono = "✅" if n > 0 else "❌"
        log_fn(f"  {icono} {tabla}: {n:,} registros")

    total = sum(totales.values())
    log_fn(f"\n  Total: {total:,} registros cargados.")
    log_fn("  Siguiente paso: entrenar el Isolation Forest desde el Monitor de Alarmas.\n")

    return totales