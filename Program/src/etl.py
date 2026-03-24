"""
etl.py — ETL Maestro del Sistema IDEO
──────────────────────────────────────────────────────────────────────────────
Este módulo es el punto de entrada principal para cargar datos en la base de
datos MySQL. Integra tres fuentes distintas en un solo proceso orquestado:

    1. datos_manuales.xlsx  → Configuración estática del nodo
                              (inventario de racks, PDB, protecciones)
    2. datos_DCE.xlsx       → Lecturas operativas extraídas de Data Center Expert
                              (TR, ML, Rectificadores)
    3. Excel de OneDrive    → Historial de solicitudes sincronizado desde
                              el formulario de SharePoint

El proceso sigue el patrón ETL estándar:
    - Extracción:     lectura desde archivos Excel
    - Transformación: renombrado de columnas, limpieza de nulos, conversión de tipos
    - Carga:          volcado a MySQL con TRUNCATE previo para garantizar integridad
──────────────────────────────────────────────────────────────────────────────
"""

import os
import pandas as pd
from sqlalchemy import text

# Se importa la función que inicializa las tablas en MySQL si no existen
from src.db import inicializar_base_datos_completa

# ─────────────────────────────────────────────────────────────
#  RUTAS DE ARCHIVOS
#  DIR_DATOS apunta a la carpeta 'Datos/' en la raíz del proyecto.
#  ARCHIVO_SOLICITUDES apunta al Excel sincronizado desde OneDrive,
#  que contiene las solicitudes ingresadas por el formulario de SharePoint.
# ─────────────────────────────────────────────────────────────
DIR_DATOS           = os.path.join(os.path.dirname(__file__), '..', 'Datos/')
ARCHIVO_MANUAL      = os.path.join(DIR_DATOS, 'datos_manuales.xlsx')
ARCHIVO_DCE         = os.path.join(DIR_DATOS, 'datos_DCE.xlsx')
ARCHIVO_SOLICITUDES = "C:/Users/mhoyosme/OneDrive - MIC/Modelado de infraestructura de los nodos - Formulario/Datos del Equipo Nuevo.xlsx"

# ─────────────────────────────────────────────────────────────
#  MAPA DE COLUMNAS — SOLICITUDES
#  Relaciona los nombres de columna del formulario de SharePoint
#  con los nombres de columna que usa la base de datos MySQL.
#  Permite normalizar los datos sin modificar el formulario original.
# ─────────────────────────────────────────────────────────────
MAPA_SOLICITUDES = {
    "Id":                    "id_solicitud",
    "Hora de finalización":  "fecha_carga",
    "Equipment":             "Equipo",
    "Tipo":                  "tipo",
    "Technical Site":        "technical_site",
    "Additional m2?":        "additional_m2",
    "Racks?":                "num_racks_nuevos",
    "Unidades de Rack (U)":  "u_requeridas",
    "Air Dissipation BTU":   "btu",
    "Máx. Power DC (W)":     "power_dc_w",
    "Power sources":         "power_sources",
    "Quantity Equipment DC": "quantity"
}


def cargar_historico_solicitudes(engine):
    """
    Carga todo el historial de solicitudes desde el Excel de OneDrive hacia MySQL.

    El proceso realiza los siguientes pasos:
        1. Lee el archivo Excel sincronizado desde OneDrive.
        2. Renombra las columnas usando MAPA_SOLICITUDES para normalizar nombres.
        3. Filtra solo las columnas que existen en la tabla de la base de datos.
        4. Limpia valores numéricos nulos (los rellena con 0).
        5. Elimina filas sin ID de solicitud (registros incompletos del formulario).
        6. Hace TRUNCATE de la tabla y recarga todos los registros.
           Este enfoque garantiza que la BD siempre refleje el estado actual
           del formulario, incluyendo ediciones o eliminaciones posteriores.
    """
    print(f"\n 3 Cargando Histórico de Solicitudes...")

    # Verificar que el archivo exista antes de intentar leerlo
    if not os.path.exists(ARCHIVO_SOLICITUDES):
        print(f"   ⚠️ No se encontró el archivo: {ARCHIVO_SOLICITUDES}")
        return

    try:
        # PASO 1: Leer el Excel de solicitudes desde la carpeta de OneDrive
        df = pd.read_excel(ARCHIVO_SOLICITUDES)

        # PASO 2: Renombrar columnas según el mapa definido
        # Se hace de forma flexible para capturar nombres con espacios extra
        cols_nuevas = {}
        for col_excel in df.columns:
            col_limpia = col_excel.strip()
            if col_limpia in MAPA_SOLICITUDES:
                cols_nuevas[col_excel] = MAPA_SOLICITUDES[col_limpia]
        df = df.rename(columns=cols_nuevas)

        # PASO 3: Filtrar solo las columnas que existen en la BD
        cols_bd      = list(MAPA_SOLICITUDES.values())
        cols_finales = [c for c in df.columns if c in cols_bd]
        df           = df[cols_finales]

        # PASO 4: Limpieza de datos numéricos
        # Las columnas numéricas con celdas vacías se rellenan con 0
        # para evitar errores de tipo al insertar en MySQL
        cols_num = ['num_racks_nuevos', 'u_requeridas', 'btu',
                    'power_dc_w', 'quantity', 'power_sources']
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # PASO 5: Eliminar filas sin ID válido (registros del formulario incompletos)
        if 'id_solicitud' in df.columns:
            df = df.dropna(subset=['id_solicitud'])
            df['id_solicitud'] = df['id_solicitud'].astype(int)

        # PASO 6: TRUNCATE + recarga completa
        # Se borra la tabla antes de insertar para evitar duplicados y mantener
        # sincronía exacta con el estado actual del formulario de SharePoint
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE historico_solicitudes"))
            conn.commit()

        df.to_sql('historico_solicitudes', con=engine, if_exists='append', index=False)
        print(f"   ✅ Historial actualizado: {len(df)} registros cargados.")

    except Exception as e:
        print(f"   ❌ Error cargando solicitudes: {e}")


def cargar_excel_generico(engine, ruta_archivo, hoja_excel, tabla_destino):
    """
    Función universal para cargar cualquier hoja de Excel en una tabla MySQL.

    Se reutiliza para cargar todas las tablas de configuración del nodo
    (info_nodo, protecciones, inventario_pdb, inventario_racks) y las tablas
    de datos operativos del DCE (tr_dce, ml_dce, rect_dce).

    REQUISITO: Los nombres de columnas en el Excel deben coincidir exactamente
    con los nombres de columnas definidos en la tabla de MySQL.

    El proceso:
        1. Limpia (TRUNCATE) la tabla destino para eliminar datos anteriores.
        2. Lee la hoja especificada del archivo Excel.
        3. Aplica limpieza básica: convierte fechas y reemplaza NaN por NULL.
        4. Carga los datos limpios en MySQL.
    """
    print(f"   Procesando hoja '{hoja_excel}' -> tabla '{tabla_destino}'...")

    if not os.path.exists(ruta_archivo):
        print(f"  Archivo no encontrado: {ruta_archivo}")
        return

    try:
        # PASO 1: Limpiar la tabla destino antes de cargar datos nuevos
        # Esto garantiza que no queden registros obsoletos en la BD
        with engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {tabla_destino}"))
            conn.commit()

        # PASO 2: Leer la hoja específica del Excel
        df = pd.read_excel(ruta_archivo, sheet_name=hoja_excel)

        # PASO 3: Limpieza básica
        # Convertir columna 'fecha' al tipo datetime si existe
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])

        # Reemplazar celdas vacías (NaN de pandas) por None (NULL en SQL)
        df = df.where(pd.notnull(df), None)

        # PASO 4: Cargar a MySQL
        # Se usa if_exists='append' porque el TRUNCATE ya limpió la tabla
        df.to_sql(tabla_destino, con=engine, if_exists='append', index=False)
        print(f"\nCarga exitosa: {len(df)} registros.\n")

    except ValueError as ve:
        print(f"\n   Error de columnas: Verifica que los nombres en Excel coincidan con SQL.\nDetalle: {ve}\n")
    except Exception as e:
        print(f"\n Error general en {tabla_destino}: {e}\n")


def ejecutar_etl_maestro():
    """
    Función principal que orquesta todo el proceso ETL del sistema.

    Ejecuta la carga en tres etapas ordenadas:

    Etapa 1 — Inventarios estáticos (datos_manuales.xlsx):
        Configuración física y eléctrica del nodo que no cambia con frecuencia:
        información general del nodo, protecciones eléctricas, inventario del
        tablero de distribución (PDB) e inventario de racks.

    Etapa 2 — Datos operativos del DCE (datos_DCE.xlsx):
        Lecturas del Transformador (TR), Tablero Principal (ML) y Rectificadores
        (RECT) obtenidas de Data Center Expert. Este archivo es generado
        previamente por el módulo etl_dce.py.

    Etapa 3 — Historial de solicitudes (OneDrive):
        Solicitudes de instalación de nuevos equipos ingresadas por los técnicos
        a través del formulario de SharePoint y sincronizadas automáticamente
        mediante el cliente de OneDrive.
    """
    print(" INICIANDO ETL (MODO EXCEL DIRECTO)...")

    # Asegurar que todas las tablas existen en MySQL antes de cargar datos
    engine = inicializar_base_datos_completa()

    # ── ETAPA 1: Inventarios estáticos ────────────────────────
    # Datos de configuración del nodo que cambian solo cuando hay
    # modificaciones físicas en la infraestructura del sitio
    print("\n 1. Cargando Inventarios Estáticos...")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "info_nodo",        "info_nodo")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "protecciones",     "protecciones")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "inventario_pdb",   "inventario_dc_pdb")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "inventario_racks", "inventario_racks")

    # ── ETAPA 2: Datos operativos del DCE ─────────────────────
    # Lecturas eléctricas y de temperatura extraídas de la API de
    # Data Center Expert y guardadas en datos_DCE.xlsx por etl_dce.py
    print("\n 2. Cargando Datos DCE")
    cargar_excel_generico(engine, ARCHIVO_DCE, "TR",   "tr_dce")
    cargar_excel_generico(engine, ARCHIVO_DCE, "ML",   "ml_dce")
    cargar_excel_generico(engine, ARCHIVO_DCE, "RECT", "rect_dce")

    # ── ETAPA 3: Historial de solicitudes ─────────────────────
    # Solicitudes de instalación de nuevos equipos ingresadas a través
    # del formulario de SharePoint y sincronizadas por OneDrive
    print("\n 3. Cargar Histórico Solicitudes")
    cargar_historico_solicitudes(engine)

    print("\n PROCESO COMPLETADO.")
