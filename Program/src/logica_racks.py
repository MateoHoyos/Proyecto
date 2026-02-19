import pandas as pd
import sys
import os
from itertools import groupby
from operator import itemgetter
from sqlalchemy import text

# ver fotos en windows 
import platform
import subprocess


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db import get_engine

def buscar_espacio_en_racks(u_requeridas):
    """
    Busca GRANDES BLOQUES de espacio libre en los racks.
    Retorna los rangos disponibles (ej: U24 a U40) donde cabe el equipo.
    """
    engine = get_engine()
    
    try:
        df = pd.read_sql("SELECT * FROM inventario_racks", engine)
    except Exception as e:
        print(f" Error consultando la BD: {e}")
        return []
    
    resumen_racks = []
    
    for index, row in df.iterrows():
        if not row['u_libres_listado'] or pd.isna(row['u_libres_listado']):
            continue
            
        # 1. Limpieza y Conversión de datos
        try:
            texto_libres = str(row['u_libres_listado']).replace('.', ',')
            # Convertimos a lista de enteros y ordenamos
            lista_libres = sorted([int(float(x)) for x in texto_libres.split(',') if x.strip().isdigit()])
        except ValueError:
            continue 

        if not lista_libres:
            continue

        # 2. ALGORITMO DE AGRUPACIÓN (La magia)
        # Esto convierte [24, 25, 26, 30, 31] en bloques: [[24, 25, 26], [30, 31]]
        bloques = []
        for k, g in groupby(enumerate(lista_libres), lambda ix: ix[0] - ix[1]):
            bloques.append(list(map(itemgetter(1), g)))

        # 3. Filtrar bloques donde quepa el equipo
        bloques_validos = []
        for bloque in bloques:
            tamano_bloque = len(bloque)
            if tamano_bloque >= u_requeridas:
                bloques_validos.append({
                    "inicio": bloque[0],
                    "fin": bloque[-1],
                    "total_u": tamano_bloque
                })

        # 4. Si el rack tiene al menos un bloque válido, lo guardamos
        if bloques_validos:
            resumen_racks.append({
                "rack": row['nombre_rack'],
                "foto": row.get('nombre_foto', 'No disponible'),
                "bloques": bloques_validos
            })
    
    return resumen_racks



def verificar_espacio_suelo(engine, racks_adicionales):
    """
    Valida si hay espacio físico en la sala (m2) para instalar racks nuevos.
    """
    try:
        # Consultar capacidad de la sala
        sql = "SELECT Racks, maximo_racks FROM info_nodo LIMIT 1"
        with engine.connect() as conn:
            fila = conn.execute(text(sql)).fetchone()
            
        if not fila:
            return False, " No hay información de capacidad de racks en la BD (info_nodo)."
            
        actuales = fila[0]
        maximos = fila[1]
        
        futuro = actuales + racks_adicionales
        
        if futuro <= maximos:
            disponibles = maximos - futuro
            return True, f"Espacio en Suelo OK: Se instalarán {racks_adicionales} racks nuevos. Total ocupado: {futuro}/{maximos}. Quedan {disponibles} espacios."
        else:
            return False, f"RECHAZADO POR SUELO: Se requieren {racks_adicionales} racks nuevos. Total proyectado ({futuro}) supera la capacidad máxima de la sala ({maximos})."
            
    except Exception as e:
        return False, f" Error validando suelo: {e}"




def mostrar_foto_rack(nombre_archivo):
    """
    Busca la imagen en la carpeta Datos/fotos_racks y la abre
    con el visor predeterminado del sistema.
    """
    # 1. Construir la ruta absoluta para evitar errores de "archivo no encontrado"
    # Asumimos que la carpeta 'Datos' está en la raíz del proyecto
    ruta_base_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_imagen = os.path.join(ruta_base_proyecto, "Datos", "fotos_racks", nombre_archivo)
    
    # 2. Validar que el archivo exista
    if not os.path.exists(ruta_imagen):
        print(f"\n    ERROR DE FOTO: El archivo '{nombre_archivo}' no existe en la carpeta 'Datos/fotos_racks'.")
        print(f"      Ruta buscada: {ruta_imagen}")
        return

    print(f"    Abriendo imagen: {nombre_archivo}...")


    try:
        sistema = platform.system()
        
        if sistema == "Windows":
            os.startfile(ruta_imagen) 
            
    except Exception as e:
        print(f"    No se pudo abrir el visor de imágenes: {e}")