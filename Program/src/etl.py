import pandas as pd
from sqlalchemy import text
import sys
import os
from src.db import inicializar_base_datos_completa

# Rutas
DIR_DATOS = os.path.join(os.path.dirname(__file__), '..', 'Datos/')
ARCHIVO_MANUAL = os.path.join(DIR_DATOS, 'datos_manuales.xlsx')
ARCHIVO_DCE = os.path.join(DIR_DATOS, 'datos_DCE.xlsx') 
ARCHIVO_SOLICITUDES = "C:/Users/mhoyosme/OneDrive - MIC/Modelado de infraestructura de los nodos - Formulario/Datos del Equipo Nuevo.xlsx"


MAPA_SOLICITUDES = {
    "Id": "id_solicitud",
    "Hora de finalización": "fecha_carga",
    "Equipment": "Equipo",
    "Tipo": "tipo",
    "Technical Site": "technical_site",
    "Additional m2?": "additional_m2",
    "Racks?": "num_racks_nuevos",
    "Unidades de Rack (U)": "u_requeridas", 
    "Air Dissipation BTU": "btu",
    "Máx. Power DC (W)": "power_dc_w",
    "Power sources": "power_sources",
    "Quantity Equipment DC": "quantity"
}

def cargar_historico_solicitudes(engine):
    """
    Carga todo el historial de solicitudes desde el Excel a la BD.
    """
    print(f"\n 3 Cargando Histórico de Solicitudes...")
    
    if not os.path.exists(ARCHIVO_SOLICITUDES):
        print(f"   ⚠️ No se encontró el archivo: {ARCHIVO_SOLICITUDES}")
        return

    try:
        # 1. Leer Excel
        df = pd.read_excel(ARCHIVO_SOLICITUDES)

        
        
        # 2. Renombrar columnas (Normalización)
        # Hacemos un mapeo flexible para atrapar nombres parecidos
        cols_nuevas = {}

        for col_excel in df.columns:
            col_limpia = col_excel.strip()
            
            if col_limpia in MAPA_SOLICITUDES:
                cols_nuevas[col_excel] = MAPA_SOLICITUDES[col_limpia]
        
        df = df.rename(columns=cols_nuevas)
        
        # 3. Filtrar solo las columnas que existen en nuestra BD
        cols_bd = list(MAPA_SOLICITUDES.values())
        cols_finales = [c for c in df.columns if c in cols_bd]
        df = df[cols_finales]

        # 4. Limpieza de datos
        # Llenar vacíos numéricos con 0
        cols_num = ['num_racks_nuevos', 'u_requeridas', 'btu', 'power_dc_w', 'quantity', 'power_sources']
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # Asegurar que el ID no sea nulo
        if 'id_solicitud' in df.columns:
            df = df.dropna(subset=['id_solicitud']) # Borrar filas sin ID
            df['id_solicitud'] = df['id_solicitud'].astype(int)

        # 5. Cargar a MySQL
        with engine.connect() as conn:
            # Opción A: Borrar y recargar todo (Recomendado para integridad con el Excel)
            conn.execute(text("TRUNCATE TABLE historico_solicitudes"))
            conn.commit()
        
        #print(df.columns)

        df.to_sql('historico_solicitudes', con=engine, if_exists='append', index=False)
        print(f"   ✅ Historial actualizado: {len(df)} registros cargados.")

    except Exception as e:
        print(f"   ❌ Error cargando solicitudes: {e}")




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
        
        print(f"/nCarga exitosa: {len(df)} registros./n")

    except ValueError as ve:
        print(f" /n   Error de columnas: Verifica que los nombres en Excel coincidan con SQL./nDetalle: {ve} /n")
    except Exception as e:
        print(f"   /n Error general en {tabla_destino}: {e} /n")

def ejecutar_etl_maestro():
    print(" INICIANDO ETL (MODO EXCEL DIRECTO)...")
    
    # 1. Asegurar tablas
    engine = inicializar_base_datos_completa()
    
    # 2. Cargar Datos Manuales (Configuración)
    print("/n 1. Cargando Inventarios Estáticos...")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "info_nodo", "info_nodo")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "protecciones", "protecciones")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "inventario_pdb", "inventario_dc_pdb")
    cargar_excel_generico(engine, ARCHIVO_MANUAL, "inventario_racks", "inventario_racks")
    
    # 3. Cargar Datos DCE (Monitoreo) - AQUÍ ESTÁ LO NUEVO
    print("/n 2. Cargando Datos DCE ")
    cargar_excel_generico(engine, ARCHIVO_DCE, "TR", "tr_dce")
    cargar_excel_generico(engine, ARCHIVO_DCE, "ML", "ml_dce")
    cargar_excel_generico(engine, ARCHIVO_DCE, "RECT", "rect_dce")

    print("/n 3. Cargar Histórico Solicitudes ")
    cargar_historico_solicitudes(engine)

    print("/n PROCESO COMPLETADO.")