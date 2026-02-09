import pandas as pd
from sqlalchemy import text
import sys
import os
from db import get_engine, inicializar_base_datos_completa

# Rutas
DIR_DATOS = os.path.join(os.path.dirname(__file__), '..', 'Datos')
ARCHIVO_MANUAL = os.path.join(DIR_DATOS, 'datos_manuales.xlsx')
#DIR_HISTORICO = os.path.join(DIR_DATOS, 'Historico')

def cargar_tabla_manual(engine, nombre_hoja, nombre_tabla_sql):
    """Función genérica para cargar una hoja de Excel a una tabla"""
    try:
        # Limpieza (Truncate)
        with engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {nombre_tabla_sql}"))
            conn.commit()
            
        # Carga
        df = pd.read_excel(ARCHIVO_MANUAL, sheet_name=nombre_hoja).fillna("")
        df.to_sql(nombre_tabla_sql, con=engine, if_exists='append', index=False)
        print(f"Carga manual: '{nombre_tabla_sql}' actualizada ({len(df)} regs).")
    except Exception as e:
        print(f"Error en {nombre_tabla_sql}: {e}")


def ejecutar_etl_maestro():
    print("INICIANDO ETL MAESTRO...")
    
    # 1. Asegurar estructura (Llama al db.py)
    engine = inicializar_base_datos_completa()
    
    # 2. Cargar Datos Maestros (Configuración)
    print("\n Cargando Inventarios y Configuración...")
    cargar_tabla_manual(engine, "info_nodo", "info_nodo")
    cargar_tabla_manual(engine, "protecciones", "protecciones")
    cargar_tabla_manual(engine, "inventario_pdb", "inventario_dc_pdb")
    cargar_tabla_manual(engine, "inventario_racks", "inventario_racks")

    print("\nETL FINALIZADO CORRECTAMENTE.")