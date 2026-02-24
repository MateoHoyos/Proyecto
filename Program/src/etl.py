import pandas as pd
from sqlalchemy import text
import sys
import os
from src.db import get_engine, inicializar_base_datos_completa

# Rutas
DIR_DATOS = os.path.join(os.path.dirname(__file__), '..', 'Datos\DB')
ARCHIVO_MANUAL = os.path.join(DIR_DATOS, 'datos_manuales.xlsx')
ARCHIVO_DCE = os.path.join(DIR_DATOS, 'datos_DCE.xlsx') 

def cargar_excel_generico(engine, ruta_archivo, hoja_excel, tabla_destino):
    """
    Función Universal: Lee una hoja de Excel y la vuelca en una tabla SQL.
    REQUISITO: Los nombres de columnas en Excel deben ser IGUALES a la BD.
    """
    print(f"   Procesando hoja '{hoja_excel}' -> tabla '{tabla_destino}'...")
    
    if not os.path.exists(ruta_archivo):
        print(f"  Archivo no encontrado: {ruta_archivo}")
        return

    try:
        # 1. Limpiar Tabla Antigua
        with engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {tabla_destino}"))
            conn.commit()

        df = pd.read_excel(ruta_archivo, sheet_name=hoja_excel)
        
        # 3. Pequeña limpieza automática (Fechas y NaNs)
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Rellenar celdas vacías con None (NULL en SQL) o 0
        df = df.where(pd.notnull(df), None)

        # 4. Cargar a MySQL
        # if_exists='append' porque ya hicimos el TRUNCATE arriba
        df.to_sql(tabla_destino, con=engine, if_exists='append', index=False)
        
        print(f"\nCarga exitosa: {len(df)} registros.\n")

    except ValueError as ve:
        print(f" \n   Error de columnas: Verifica que los nombres en Excel coincidan con SQL.\nDetalle: {ve} \n")
    except Exception as e:
        print(f"   \n Error general en {tabla_destino}: {e} \n")

def ejecutar_etl_maestro():
    print(" INICIANDO ETL (MODO EXCEL DIRECTO)...")
    
    # 1. Asegurar tablas
    engine = inicializar_base_datos_completa()
    
    # 2. Cargar Datos Manuales (Configuración)
    print("\n 1. Cargando Inventarios Estáticos...")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "info_nodo", "info_nodo")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "protecciones", "protecciones")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "inventario_pdb", "inventario_dc_pdb")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "inventario_racks", "inventario_racks")
    
    # 3. Cargar Datos DCE (Monitoreo) - AQUÍ ESTÁ LO NUEVO
    print("\n 2. Cargando Datos DCE ")
    cargar_excel_generico(engine, ARCHIVO_DCE, "TR", "tr_dce")
    cargar_excel_generico(engine, ARCHIVO_DCE, "ML", "ml_dce")
    cargar_excel_generico(engine, ARCHIVO_DCE, "RECT", "rect_dce")

    print("\n PROCESO COMPLETADO.")