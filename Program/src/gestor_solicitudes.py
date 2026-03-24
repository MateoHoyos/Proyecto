"""
gestor_solicitudes.py — Lector de Solicitudes desde la Base de Datos
──────────────────────────────────────────────────────────────────────────────
Este módulo actúa como puerta de entrada del Módulo de Evaluación Técnica.
Lee las solicitudes de instalación de nuevos equipos desde MySQL y las
convierte al formato que espera el evaluador (analisis_potencia.py).

Las solicitudes fueron ingresadas por los técnicos a través del formulario
de SharePoint y llegaron a MySQL mediante el proceso ETL (etl.py).

Funciones:
    obtener_lista_solicitudes() → lista resumida para el selectbox de la UI
    obtener_detalle_solicitud() → datos completos listos para el evaluador
──────────────────────────────────────────────────────────────────────────────
"""

import pandas as pd
from sqlalchemy import text
from src.db import get_engine


def obtener_lista_solicitudes():
    """
    Retorna un DataFrame con el resumen de todas las solicitudes en la BD.

    Se usa para poblar el selectbox de la vista del evaluador, permitiendo
    al usuario ver y elegir qué solicitud desea evaluar.

    Retorna columnas: id_solicitud, Equipo, fecha_carga
    Ordenadas de más reciente a más antigua (ORDER BY id DESC).

    En caso de error de conexión, retorna un DataFrame vacío para que
    la interfaz pueda mostrar un mensaje apropiado sin lanzar excepciones.
    """
    engine = get_engine()
    try:
        query = ("SELECT id_solicitud, Equipo, fecha_carga "
                 "FROM historico_solicitudes ORDER BY id_solicitud DESC")
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"Error leyendo solicitudes: {e}")
        return pd.DataFrame()


def obtener_detalle_solicitud(id_solicitud):
    """
    Busca una solicitud por ID y la convierte al diccionario del evaluador.

    Lee el registro completo desde la tabla historico_solicitudes y mapea
    cada columna de la BD al nombre de clave que espera analisis_potencia.py.
    También realiza conversiones de tipo y cálculos derivados:

    Conversiones realizadas:
        - quantity = 0  → se corrige a 1 (mínimo un equipo)
        - additional_m2 = 'yes/si/y/...' → Requiere_Rack_Nuevo = True
        - btu = 0 → se calcula automáticamente desde la potencia DC
          usando el factor de conversión: 1 W = 3.41214 BTU/h

    El campo BTU es importante para evaluar la capacidad de climatización
    del nodo. Si el técnico no lo ingresó en el formulario, se calcula
    a partir de la potencia máxima del equipo.

    Retorna el diccionario de datos si existe la solicitud, o None si no.
    """
    engine = get_engine()
    try:
        query = text("SELECT * FROM historico_solicitudes WHERE id_solicitud = :id")
        with engine.connect() as conn:
            # mappings() permite acceder a los campos por nombre de columna
            res = conn.execute(query, {"id": id_solicitud}).mappings().fetchone()

        if not res:
            return None

        datos = {}

        # ── Identificación del equipo ─────────────────────────────────────
        datos["ID"]             = str(res["id_solicitud"])
        datos["Equipment"]      = res["Equipo"]
        datos["Technical Site"] = res["technical_site"]

        # ── Cantidad de equipos ───────────────────────────────────────────
        # Se garantiza un mínimo de 1 para evitar divisiones por cero
        datos["Quantity Equipment DC"] = int(res["quantity"])
        if datos["Quantity Equipment DC"] == 0:
            datos["Quantity Equipment DC"] = 1

        # ── Parámetros eléctricos ─────────────────────────────────────────
        datos["Máx. Power DC (W)"] = float(res["power_dc_w"])
        datos["Power sources"]     = int(res["power_sources"])
        datos["Voltage(AC or DC)"] = "DC -48V"   # Todos los equipos del nodo son DC 48V

        # ── Espacio físico requerido ──────────────────────────────────────
        # Si el técnico indicó que necesita m2 adicionales (rack nuevo en suelo),
        # se activa el modo de verificación de espacio en suelo (racks.py).
        # De lo contrario, se buscan unidades de rack (U) libres en racks existentes.
        add_m2 = str(res["additional_m2"]).strip().lower()
        if add_m2 in ['yes', 'si', 'y', 's', 'true', '1']:
            datos["Requiere_Rack_Nuevo"]  = True
            datos["Cantidad_Racks_Nuevos"] = int(res["num_racks_nuevos"])
            datos["U_Requeridas"]          = 0
        else:
            datos["Requiere_Rack_Nuevo"]  = False
            datos["Cantidad_Racks_Nuevos"] = 0
            datos["U_Requeridas"]          = int(res["u_requeridas"])

        # ── Disipación de calor (BTU/h) ───────────────────────────────────
        # Si el técnico ingresó el valor en el formulario, se usa directamente.
        # Si vino en 0, se calcula: Potencia total (W) × 3.41214 = BTU/h
        # Esta conversión es el factor estándar entre vatios y BTU/hora.
        if res["btu"] and float(res["btu"]) != 0:
            datos["BTU_Label"] = f"{res['btu']} (Ingresado)"
        else:
            total_watts = datos["Máx. Power DC (W)"] * datos["Quantity Equipment DC"]
            btu_calc    = round(total_watts * 3.41214, 2)
            datos["BTU_Label"] = f"{btu_calc} (Calculado)"

        # Campo requerido por el evaluador (potencia a liberar al reemplazar un equipo)
        datos["Potencia a liberar"] = 0

        return datos

    except Exception as e:
        print(f"Error obteniendo detalle: {e}")
        return None
