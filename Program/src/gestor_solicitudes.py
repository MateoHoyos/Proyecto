import pandas as pd
from sqlalchemy import text

from src.db import get_engine

def obtener_lista_solicitudes():
    """
    Retorna un DataFrame con ID, Equipo y Fecha para llenar el Selectbox.
    """
    engine = get_engine()
    try:
        query = "SELECT id_solicitud, Equipo, fecha_carga FROM historico_solicitudes ORDER BY id_solicitud DESC"
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"Error leyendo solicitudes: {e}")
        return pd.DataFrame()

def obtener_detalle_solicitud(id_solicitud):
    """
    Busca una solicitud por ID y la convierte al diccionario que usa el evaluador.
    """
    engine = get_engine()
    try:
        query = text("SELECT * FROM historico_solicitudes WHERE id_solicitud = :id")
        with engine.connect() as conn:
            # Usamos mappings() para acceder por nombre de columna
            res = conn.execute(query, {"id": id_solicitud}).mappings().fetchone()
        
        if not res:
            return None

        # --- MAPEO DE SQL A DICCIONARIO DEL SISTEMA ---
        # Aquí convertimos los nombres de las columnas de la BD (snake_case)
        # a las llaves que espera tu lógica actual.
        
        datos = {}
        
        # Identificación
        datos["ID"] = str(res["id_solicitud"])
        datos["Equipment"] = res["Equipo"]
        datos["Technical Site"] = res["technical_site"]
        
        # Cantidad
        datos["Quantity Equipment DC"] = int(res["quantity"])
        if datos["Quantity Equipment DC"] == 0:
            datos["Quantity Equipment DC"] = 1

        # Potencia 
        datos["Máx. Power DC (W)"] = float(res["power_dc_w"])
        datos["Power sources"] = int(res["power_sources"])
        
        # Voltaje (Nota: No está en tu tabla SQL actual, asumimos DC -48V por defecto
        # o tendrías que agregar la columna a la tabla)
        datos["Voltage(AC or DC)"] = "DC -48V" 
        
        # Racks y Espacio
        add_m2 = str(res["additional_m2"]).strip().lower()
        if add_m2 in ['yes', 'si', 'y', 's', 'true', '1']:
            datos["Requiere_Rack_Nuevo"] = True
            datos["Cantidad_Racks_Nuevos"] = int(res["num_racks_nuevos"])
            datos["U_Requeridas"] = 0
        else:
            datos["Requiere_Rack_Nuevo"] = False
            datos["Cantidad_Racks_Nuevos"] = 0
            datos["U_Requeridas"] = int(res["u_requeridas"])

        # Aire
        if res["btu"] and float(res["btu"]) != 0:
            datos["BTU_Label"] = f"{res['btu']} (Ingresado)"
        else:
            # Calculamos si viene en 0
            total_watts = datos["Máx. Power DC (W)"] * datos["Quantity Equipment DC"]
            btu_calc = round(total_watts * 3.41214, 2)
            datos["BTU_Label"] = f"{btu_calc} (Calculado)"
        
        # Datos por defecto necesarios para el recomendador
        datos["Potencia a liberar"] = 0
        
        return datos

    except Exception as e:
        print(f"Error obteniendo detalle: {e}")
        return None