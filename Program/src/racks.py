import pandas as pd
import sys
import os
from itertools import groupby
from operator import itemgetter
from sqlalchemy import text

from src.db import get_engine

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


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
    Valida si hay espacio físico en la sala para instalar racks nuevos.

    Retorna:
        (ok: bool, mensaje: str, info_racks: dict)

        info_racks contiene:
            racks_f1        : list de IDs instalados en fila 1  ej: ['01-R1','01-R2',...]
            racks_f2        : list de IDs instalados en fila 2
            max_f1          : capacidad máxima fila 1
            max_f2          : capacidad máxima fila 2
            racks_nuevos    : list de IDs propuestos para los racks nuevos (en fila 1 primero)
    """
    try:
        # Consultar capacidad y distribución de la sala
        sql = """
            SELECT Racks, maximo_racks,
                   racks_fila1, maximo_fila1,
                   racks_fila2, maximo_fila2
            FROM info_nodo LIMIT 1
        """
        with engine.connect() as conn:
            fila = conn.execute(text(sql)).fetchone()

        if not fila:
            return False, "No hay información de capacidad de racks en la BD (info_nodo).", {}

        actuales  = int(fila[0] or 0)
        maximos   = int(fila[1] or 0)

        # Distribución por fila — usa columnas dedicadas si existen,
        # si no, reparte proporcionalmente con los valores totales conocidos.
        # Ajusta los nombres de columna si tu tabla los tiene diferente.
        try:
            n_f1   = int(fila[2] or 0)   # racks instalados fila 1
            max_f1 = int(fila[3] or 0)   # máximo fila 1
            n_f2   = int(fila[4] or 0)   # racks instalados fila 2
            max_f2 = int(fila[5] or 0)   # máximo fila 2
        except Exception:
            # Fallback: valores fijos del nodo IDEO Cali
            n_f1   = 4;  max_f1 = 6
            n_f2   = actuales - n_f1
            max_f2 = maximos - max_f1

        # Construir IDs instalados
        racks_f1 = [f"01-R{i+1}" for i in range(n_f1)]
        racks_f2 = [f"02-R{i+1}" for i in range(n_f2)]

        # Asignar IDs a los racks nuevos (fila 1 primero, luego fila 2)
        racks_nuevos = []
        proximo_f1 = n_f1 + 1
        proximo_f2 = n_f2 + 1
        for _ in range(racks_adicionales):
            if proximo_f1 <= max_f1:
                racks_nuevos.append(f"01-R{proximo_f1}")
                proximo_f1 += 1
            elif proximo_f2 <= max_f2:
                racks_nuevos.append(f"02-R{proximo_f2}")
                proximo_f2 += 1

        info_racks = {
            "racks_f1":     racks_f1,
            "racks_f2":     racks_f2,
            "max_f1":       max_f1,
            "max_f2":       max_f2,
            "racks_nuevos": racks_nuevos,
        }

        futuro = actuales + racks_adicionales
        if futuro <= maximos:
            disponibles = maximos - futuro
            msg = (f"Espacio en Suelo OK: Se instalarán {racks_adicionales} racks nuevos. "
                   f"Total ocupado: {futuro}/{maximos}. Quedan {disponibles} espacios.")
            return True, msg, info_racks
        else:
            msg = (f"RECHAZADO POR SUELO: Se requieren {racks_adicionales} racks nuevos. "
                   f"Total proyectado ({futuro}) supera la capacidad máxima ({maximos}).")
            return False, msg, info_racks

    except Exception as e:
        return False, f"Error validando suelo: {e}", {}


 