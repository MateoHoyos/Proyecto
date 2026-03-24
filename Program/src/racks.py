"""
racks.py — Módulo de Verificación de Espacio Físico
──────────────────────────────────────────────────────────────────────────────
Este módulo verifica si hay espacio físico disponible en los racks del nodo
para instalar un nuevo equipo.

Maneja dos escenarios distintos:

    1. El equipo cabe en un rack existente:
       Se buscan bloques contiguos de unidades de rack (U) libres suficientes
       para alojar el equipo. Por ejemplo, un equipo de 2U necesita dos
       posiciones consecutivas libres dentro de un mismo rack.

    2. El equipo requiere un rack nuevo (suelo):
       Se verifica si hay espacio en el piso de la sala para instalar
       uno o más racks adicionales, respetando la capacidad máxima
       de cada fila definida en la información del nodo.
──────────────────────────────────────────────────────────────────────────────
"""

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
    Busca bloques contiguos de unidades de rack (U) libres para el nuevo equipo.

    Un equipo de telecomunicaciones ocupa una cantidad fija de unidades de rack
    (por ejemplo, 1U, 2U o 4U) y estas unidades deben ser CONTIGUAS dentro
    del mismo rack para que el equipo pueda montarse correctamente.

    El algoritmo:
        1. Lee el inventario de racks desde MySQL.
        2. Para cada rack, lee la lista de unidades libres (ej: "24,25,26,30,31").
        3. Agrupa las unidades libres en bloques contiguos usando el algoritmo
           de groupby: [24,25,26,30,31] → [[24,25,26], [30,31]]
        4. Filtra los bloques cuyo tamaño sea >= u_requeridas.
        5. Retorna todos los racks que tienen al menos un bloque válido.

    Retorna una lista de dicts con la información de cada rack disponible:
        [{"rack": "Rack-01", "foto": "rack01.jpg",
          "bloques": [{"inicio": 24, "fin": 26, "total_u": 3}]}]
    """
    engine = get_engine()

    try:
        # Cargar todo el inventario de racks desde la BD
        df = pd.read_sql("SELECT * FROM inventario_racks", engine)
    except Exception as e:
        print(f" Error consultando la BD: {e}")
        return []

    resumen_racks = []

    for index, row in df.iterrows():
        # Omitir racks sin información de unidades libres
        if not row['u_libres_listado'] or pd.isna(row['u_libres_listado']):
            continue

        # PASO 1: Limpiar y convertir la lista de unidades libres a enteros
        # El campo viene como string "24,25,26,30,31" o "24.0,25.0,26.0"
        try:
            texto_libres = str(row['u_libres_listado']).replace('.', ',')
            lista_libres = sorted([int(float(x)) for x in texto_libres.split(',')
                                   if x.strip().isdigit()])
        except ValueError:
            continue

        if not lista_libres:
            continue

        # PASO 2: ALGORITMO DE AGRUPACIÓN DE BLOQUES CONTIGUOS
        # Convierte una lista plana de números en grupos de números consecutivos.
        # Ejemplo: [24, 25, 26, 30, 31] → [[24, 25, 26], [30, 31]]
        #
        # El truco del algoritmo: si restamos el índice de posición al valor,
        # los números consecutivos producen el mismo resultado:
        #   índice 0 → valor 24 → 24-0 = 24
        #   índice 1 → valor 25 → 25-1 = 24  ← mismo grupo
        #   índice 2 → valor 26 → 26-2 = 24  ← mismo grupo
        #   índice 3 → valor 30 → 30-3 = 27  ← nuevo grupo
        #   índice 4 → valor 31 → 31-4 = 27  ← mismo grupo
        bloques = []
        for k, g in groupby(enumerate(lista_libres), lambda ix: ix[0] - ix[1]):
            bloques.append(list(map(itemgetter(1), g)))

        # PASO 3: Filtrar bloques donde quepa el equipo (tamaño >= u_requeridas)
        bloques_validos = []
        for bloque in bloques:
            tamano_bloque = len(bloque)
            if tamano_bloque >= u_requeridas:
                bloques_validos.append({
                    "inicio":   bloque[0],   # Primera U disponible del bloque
                    "fin":      bloque[-1],  # Última U disponible del bloque
                    "total_u":  tamano_bloque
                })

        # PASO 4: Si el rack tiene bloques válidos, incluirlo en el resultado
        if bloques_validos:
            resumen_racks.append({
                "rack":   row['nombre_rack'],
                "foto":   row.get('nombre_foto', 'No disponible'),
                "bloques": bloques_validos
            })

    return resumen_racks


def verificar_espacio_suelo(engine, racks_adicionales):
    """
    Verifica si hay espacio en el piso de la sala para instalar racks nuevos.

    Algunos equipos son demasiado grandes para montarse en un rack existente
    y requieren uno o más racks nuevos instalados en el suelo de la sala.
    Esta función verifica si la sala tiene capacidad para alojarlos.

    El nodo IDEO Cali tiene dos filas de racks:
        - Fila 1: capacidad máxima definida en la tabla info_nodo
        - Fila 2: capacidad máxima definida en la tabla info_nodo

    Los racks nuevos se asignan primero a la fila 1 (si tiene espacio)
    y luego a la fila 2, y se les asigna un ID secuencial.

    Retorna:
        (ok: bool, mensaje: str, info_racks: dict)

        info_racks contiene la distribución actual y propuesta de racks
        por fila, usada para visualizar el plano de la sala en el PDF.
    """
    try:
        # Consultar la capacidad y distribución actual de racks en la sala
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

        actuales = int(fila[0] or 0)   # Total de racks instalados actualmente
        maximos  = int(fila[1] or 0)   # Capacidad máxima total de la sala

        # Leer distribución por fila desde la BD
        # Si las columnas no existen, se usan valores fijos del nodo IDEO Cali
        try:
            n_f1   = int(fila[2] or 0)   # Racks instalados en fila 1
            max_f1 = int(fila[3] or 0)   # Máximo de racks en fila 1
            n_f2   = int(fila[4] or 0)   # Racks instalados en fila 2
            max_f2 = int(fila[5] or 0)   # Máximo de racks en fila 2
        except Exception:
            # Valores de respaldo específicos del nodo IDEO Cali
            n_f1   = 4;  max_f1 = 6
            n_f2   = actuales - n_f1
            max_f2 = maximos - max_f1

        # Construir los IDs de racks instalados en cada fila
        # Formato: "01-R1", "01-R2" para fila 1 / "02-R1", "02-R2" para fila 2
        racks_f1 = [f"01-R{i+1}" for i in range(n_f1)]
        racks_f2 = [f"02-R{i+1}" for i in range(n_f2)]

        # Asignar IDs a los racks nuevos propuestos
        # Se llena primero la fila 1 hasta su máximo, luego la fila 2
        racks_nuevos  = []
        proximo_f1    = n_f1 + 1
        proximo_f2    = n_f2 + 1

        for _ in range(racks_adicionales):
            if proximo_f1 <= max_f1:
                racks_nuevos.append(f"01-R{proximo_f1}")
                proximo_f1 += 1
            elif proximo_f2 <= max_f2:
                racks_nuevos.append(f"02-R{proximo_f2}")
                proximo_f2 += 1

        # Empaquetar la información de distribución para el PDF
        info_racks = {
            "racks_f1":     racks_f1,
            "racks_f2":     racks_f2,
            "max_f1":       max_f1,
            "max_f2":       max_f2,
            "racks_nuevos": racks_nuevos,
        }

        # Verificar si cabe la cantidad de racks solicitada
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
