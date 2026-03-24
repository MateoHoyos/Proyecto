"""
etl_historico.py — ETL del Histórico 2025 para el Modelo de IA
──────────────────────────────────────────────────────────────────────────────
Este módulo procesa el histórico de datos del año 2025 exportados desde
Data Center Expert en formato CSV (un archivo por sensor por mes).

Su propósito es preparar los datos históricos que usa el modelo de Isolation
Forest para aprender el comportamiento normal del nodo y detectar anomalías.

El proceso transforma 158.376 lecturas crudas en 4 tablas históricas limpias
y alineadas temporalmente en MySQL:

    tr_historico      → histórico del Transformador
    ml_historico      → histórico del Tablero Principal
    rect1_historico   → histórico del Rectificador 1
    rect2_historico   → histórico del Rectificador 2

Cuándo ejecutar:
    - Una vez para cargar el histórico 2025 completo (primera configuración)
    - Opcionalmente cada mes para incorporar datos nuevos
    - Siempre antes de reentrenar el modelo Isolation Forest
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
#  DIR_DATOS_RAW: carpeta con los CSVs crudos exportados del DCE,
#                 organizados en subcarpetas por equipo y sensor.
#  DIR_HISTORICO: carpeta donde se guardan los CSVs consolidados
#                 (uno por equipo) como respaldo intermedio.
# ─────────────────────────────────────────────────────────────
DIR_PROYECTO  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DIR_DATOS_RAW = os.path.join(DIR_PROYECTO, 'Datos', 'DCE_DATOS_2025')
DIR_HISTORICO = os.path.join(DIR_PROYECTO, 'Datos', 'Historico')

# ─────────────────────────────────────────────────────────────
#  MAPAS SENSOR → COLUMNA DB
#  Cada mapa relaciona el nombre de carpeta del sensor en DCE
#  con el nombre de columna que tendrá en MySQL.
#  El nombre de carpeta corresponde al label del sensor en la API.
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

# Los mapas de Rect1 y Rect2 son idénticos porque ambos rectificadores
# tienen los mismos sensores; se diferencian por la carpeta de origen
MAPA_RECT1 = {
    "01_-_VOLTAJE_AC_DEL_SISTEMA":   "voltaje_ac_vs",
    "02_-_VOLTAJE_DC_DEL_SISTEMA":   "voltaje_dc_vs",
    "03_-_CORRIENTE_DC_DEL_SISTEMA": "corriente_dc_cs",
    "11_-_CORRIENTE_DC_DE_LA_CARGA": "corriente_dc_carga",
}

MAPA_RECT2 = {
    "01_-_VOLTAJE_AC_DEL_SISTEMA":   "voltaje_ac_vs",
    "02_-_VOLTAJE_DC_DEL_SISTEMA":   "voltaje_dc_vs",
    "03_-_CORRIENTE_DC_DEL_SISTEMA": "corriente_dc_cs",
    "11_-_CORRIENTE_DC_DE_LA_CARGA": "corriente_dc_carga",
}

# Lista de dispositivos a procesar: (nombre, ruta_base, mapa, tabla_destino)
ELEMENTOS = [
    ("TR",    os.path.join(DIR_DATOS_RAW, "TR"),    MAPA_TR,    "tr_historico"),
    ("ML",    os.path.join(DIR_DATOS_RAW, "ML"),    MAPA_ML,    "ml_historico"),
    ("Rect1", os.path.join(DIR_DATOS_RAW, "Rect1"), MAPA_RECT1, "rect1_historico"),
    ("Rect2", os.path.join(DIR_DATOS_RAW, "Rect2"), MAPA_RECT2, "rect2_historico"),
]

# ─────────────────────────────────────────────────────────────
#  DDL — Definición de tablas históricas en MySQL
#  Se usan PRIMARY KEY en timestamp para que las inserciones sean
#  idempotentes: si ya existe un timestamp, la fila se ignora.
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


def _limpiar_fecha(fecha_str: str) -> str:
    """
    Limpia el formato de fecha con caracteres corruptos del export de DCE.

    Los archivos CSV exportados desde Data Center Expert contienen caracteres
    especiales en los campos de fecha por problemas de codificación (UTF-8 / Latin).
    Esta función los elimina y estandariza el formato AM/PM para que
    pandas pueda convertirlos correctamente.

    Ejemplo:
        '1/1/2025, 12:00:00 a.Â m.'  →  '1/1/2025 12:00:00 AM'
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
    Lee los archivos CSV mensuales de un sensor y los consolida en un DataFrame.

    Cada sensor tiene una carpeta propia con hasta 12 CSVs (uno por mes).
    Esta función los lee todos, limpia las fechas, convierte los valores a
    numérico y hace un resample a intervalos de 10 minutos.

    El resample a 10 minutos es necesario porque:
    - Las lecturas del DCE no son exactamente periódicas (pueden variar en segundos)
    - Al alinear todos los sensores al mismo intervalo de 10 min, se pueden
      hacer joins por timestamp para construir el DataFrame del modelo de IA
    """
    # Buscar todos los CSVs en la carpeta del sensor
    patron   = os.path.join(ruta_base, carpeta_sensor, "*.csv")
    archivos = glob.glob(patron)

    # Intentar también extensión .cvs (error tipográfico frecuente en el export)
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
            # Leer CSV con codificación latin-1 para manejar caracteres especiales
            df = pd.read_csv(archivo, encoding='latin-1', dtype=str)

            # Limpiar y convertir la columna de fecha
            df['Time_Clean']     = df['Time'].apply(_limpiar_fecha)
            df['timestamp']      = pd.to_datetime(
                df['Time_Clean'],
                format='%d/%m/%Y %I:%M:%S %p',
                errors='coerce'    # Las fechas inválidas se convierten a NaT
            )
            # Convertir el valor del sensor a numérico
            df['valor_numerico'] = pd.to_numeric(df['Value'], errors='coerce')

            # Eliminar filas con fecha o valor inválido
            df = df.dropna(subset=['valor_numerico', 'timestamp'])
            dfs_meses.append(df[['timestamp', 'valor_numerico']].copy())

        except Exception as e:
            log(f"      Error en {os.path.basename(archivo)}: {e}")

    if not dfs_meses:
        return None

    # Unir todos los meses en un solo DataFrame anual
    df_anual = pd.concat(dfs_meses, ignore_index=True)
    df_anual = df_anual.sort_values('timestamp').set_index('timestamp')

    # Resample a 10 minutos: agrupa lecturas por ventana de 10 min y promedia
    # Esto alinea los timestamps irregulares de la API a intervalos uniformes
    df_resampled         = df_anual.resample('10min').mean()
    df_resampled.columns = [nombre_columna]

    return df_resampled


def _procesar_dispositivo(nombre: str, ruta_base: str,
                           mapa: dict, log) -> pd.DataFrame | None:
    """
    Procesa todos los sensores de un dispositivo y los une en un solo DataFrame.

    Para cada sensor en el mapa, llama a _procesar_sensor() y une los resultados
    en un DataFrame con todos los sensores del dispositivo como columnas,
    alineados por el mismo índice de timestamp a 10 minutos.

    Al final elimina las filas donde todos los valores numéricos son 0 o NaN,
    que corresponden a períodos sin datos válidos.
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

    # Unir todos los sensores por timestamp (join horizontal)
    df_final = pd.concat(dfs_sensores, axis=1).reset_index()

    # Eliminar filas donde TODAS las columnas numéricas son NaN o 0
    # (períodos sin medición real del equipo)
    cols_num       = df_final.select_dtypes(include='number').columns
    mascara_vacias = (df_final[cols_num].fillna(0) == 0).all(axis=1)
    df_final       = df_final[~mascara_vacias]

    log(f"  ✅ {nombre}: {len(df_final):,} filas a 10 min")
    return df_final


def _crear_tablas_historicas(engine, log):
    """Crea las 4 tablas históricas en MySQL si aún no existen."""
    with engine.connect() as conn:
        for nombre, ddl in DDL_TABLAS.items():
            conn.execute(text(ddl))
        conn.commit()
    log("  Tablas históricas verificadas.")


def _guardar_csv_intermedio(df: pd.DataFrame, nombre: str, log):
    """
    Guarda el DataFrame consolidado como CSV en la carpeta Datos/Historico/.

    Este archivo sirve como respaldo intermedio y replica el comportamiento
    del notebook ETL.ipynb original, donde se guardaban los CSVs consolidados
    antes de cargarlos a la base de datos.
    """
    os.makedirs(DIR_HISTORICO, exist_ok=True)
    ruta = os.path.join(DIR_HISTORICO, f"consolidado_{nombre}_2025.csv")
    df.to_csv(ruta, index=False)
    log(f"  CSV guardado: {os.path.basename(ruta)}")
    return ruta


def _cargar_a_mysql(engine, df: pd.DataFrame, tabla: str, log):
    """
    Carga el DataFrame en la tabla MySQL correspondiente.

    La carga es idempotente gracias al PRIMARY KEY en timestamp:
    si una fila con ese timestamp ya existe en la tabla, la inserción
    falla silenciosamente (duplicate key) y se omite sin error.

    Para no saturar la conexión, los datos se insertan en bloques
    de 2000 filas. Esto es importante dado el volumen de datos
    (hasta ~50.000 filas por dispositivo).
    """
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    CHUNK      = 2000   # Tamaño del bloque de inserción
    insertados = 0
    omitidos   = 0

    for i in range(0, len(df), CHUNK):
        bloque = df.iloc[i:i+CHUNK]
        try:
            # if_exists='append' + PRIMARY KEY en timestamp:
            # los duplicados generan error de clave duplicada que se captura abajo
            bloque.to_sql(tabla, con=engine, if_exists='append', index=False,
                          chunksize=CHUNK, method='multi')
            insertados += len(bloque)
        except Exception as e:
            # Error esperado: duplicate key (timestamp ya existe en la tabla)
            omitidos += len(bloque)
            log(f"    ⚠️  Bloque {i//CHUNK + 1}: {e}")

    log(f"  MySQL '{tabla}': {insertados:,} insertados, {omitidos:,} omitidos (duplicados).")
    return insertados


def ejecutar_etl_historico(log_fn=print):
    """
    Función principal: ejecuta el ETL histórico completo en 3 etapas.

    Etapa 1 — Verificar tablas:
        Crea las tablas históricas en MySQL si no existen.

    Etapa 2 — Procesar dispositivos:
        Para cada equipo (TR, ML, Rect1, Rect2):
        - Lee los CSVs crudos por sensor desde la carpeta DCE_DATOS_2025/
        - Limpia las fechas y los valores numéricos
        - Hace resample a 10 minutos para alinear timestamps
        - Une todos los sensores en un DataFrame por dispositivo
        - Guarda el CSV consolidado como respaldo en Datos/Historico/

    Etapa 3 — Cargar a MySQL:
        Inserta los DataFrames en las tablas históricas.
        Las filas duplicadas (mismo timestamp) se omiten automáticamente.

    Parámetro log_fn: función de registro de mensajes.
        - Usar print para ejecución desde consola.
        - Usar st.write para mostrar el progreso en la interfaz de Streamlit.

    Retorna un diccionario con el conteo de registros cargados por tabla.
    """
    log_fn("\n" + "="*60)
    log_fn("  ETL HISTÓRICO — NODO IDEO 2025")
    log_fn("  Fuente: CSVs crudos por sensor → resample 10 min → MySQL")
    log_fn("="*60)

    engine = get_engine()

    # ETAPA 1: Verificar/crear tablas históricas
    log_fn("\n[1/3] Verificando tablas históricas en MySQL...")
    _crear_tablas_historicas(engine, log_fn)

    # ETAPA 2: Procesar cada dispositivo
    log_fn("\n[2/3] Procesando dispositivos...")
    resultados = {}

    for nombre, ruta_base, mapa, tabla in ELEMENTOS:
        df = _procesar_dispositivo(nombre, ruta_base, mapa, log_fn)

        if df is not None:
            _guardar_csv_intermedio(df, nombre, log_fn)
            resultados[tabla] = df
        else:
            resultados[tabla] = None

    # ETAPA 3: Cargar a MySQL
    log_fn("\n[3/3] Cargando a MySQL...")
    totales = {}
    for tabla, df in resultados.items():
        if df is not None:
            n = _cargar_a_mysql(engine, df, tabla, log_fn)
            totales[tabla] = n
        else:
            totales[tabla] = 0
            log_fn(f"  ⚠️  Sin datos para {tabla}, saltando.")

    # Resumen final
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