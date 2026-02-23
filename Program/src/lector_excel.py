import pandas as pd
import os

archivo = "C:/Users/mhoyosme/OneDrive - MIC/Modelado de infraestructura de los nodos - Formulario/Datos del Equipo Nuevo.xlsx"

def obtener_int_seguro(valor, default=0):
    """
    Convierte un valor de Excel a entero de forma segura.
    Si es NaN, vacío o texto basura, devuelve el default.
    """
    try:
        # Si es nulo o vacío
        if pd.isna(valor) or str(valor).strip() == "":
            return default
        # Convertimos primero a float por si viene como "2.0" y luego a int
        return int(float(valor))
    except Exception:
        return default

def obtener_float_seguro(valor, default=0.0):
    """
    Convierte a decimal de forma segura.
    """
    try:
        if pd.isna(valor) or str(valor).strip() == "":
            return default
        return float(valor)
    except Exception:
        return default





def leer_ultima_solicitud():
    """
    Lee el archivo 'Datos del Equipo Nuevo.xlsx' y extrae la última fila.
    """
    # Ajusta la ruta según tu estructura
    ruta_archivo = archivo
    
    if not os.path.exists(ruta_archivo):
        print(f"❌ Error: No se encuentra el archivo: {ruta_archivo}")
        return None
    try:
        df = pd.read_excel(ruta_archivo)
        if df.empty: return None
        ultima_fila = df.iloc[-1]
        datos = {}

        # DATOS BÁSICOS
        datos["Equipment"] = str(ultima_fila.get('Equipment', 'Desconocido'))
        datos["Technical Site"] = str(ultima_fila.get('Technical Site', 'IDEO CALI'))
        
        # Limpieza de Voltaje: Si es nan, ponemos el default
        voltaje_raw = str(ultima_fila.get('Voltage', ''))
        if voltaje_raw.lower() == 'nan' or voltaje_raw.strip() == '':
            datos["Voltage(AC or DC)"] = "DC -48V" # Default
        else:
            datos["Voltage(AC or DC)"] = voltaje_raw

        # POTENCIA
        datos["Máx. Power DC (W)"] = obtener_float_seguro(ultima_fila.get('Máx. Power DC (W)'), 0.0)
        col_qty = 'Quantity Equipment' if 'Quantity Equipment' in df.columns else 'Quantity Equipmen' 
        datos["Quantity Equipment DC"] = obtener_int_seguro(ultima_fila.get(col_qty), 1)
        datos["Power sources"] = obtener_int_seguro(ultima_fila.get('Power sources'), 2)
        
        # RACKS (Lógica M2 vs Unidades)
        datos["U_Requeridas"] = obtener_int_seguro(ultima_fila.get('Unidades de Rack (U)'), 0)
        
        add_m2 = str(ultima_fila.get('Additional m2?', 'No')).strip().lower()
        if add_m2 in ['yes', 'si']:
            datos["Requiere_Rack_Nuevo"] = True
            datos["Cantidad_Racks_Nuevos"] = obtener_int_seguro(ultima_fila.get('Racks?'), 1)
            # Si pide rack nuevo, las U requeridas pasan a segundo plano o son 0
        else:
            datos["Requiere_Rack_Nuevo"] = False
            datos["Cantidad_Racks_Nuevos"] = 0

        # AIRE (Presentación limpia)
        btu_input = ultima_fila.get('Air Dissipation BTU')
        if pd.isna(btu_input) or btu_input == 0 or str(btu_input).strip() == "":
            total_watts = datos["Máx. Power DC (W)"] * datos["Quantity Equipment DC"]
            datos["BTU"] = round(total_watts * 3.41214, 2)
            datos["BTU_Label"] = f"{datos['BTU']} (Calculado)"
        else:
            datos["BTU"] = obtener_float_seguro(btu_input)
            datos["BTU_Label"] = f"{datos['BTU']} (Manual)"

        datos["Potencia a liberar"] = obtener_float_seguro(ultima_fila.get('Potencia a liberar'), 0.0)
        
        return datos

    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return None