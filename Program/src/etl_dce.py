import pandas as pd
import sys
import os
import time
from datetime import datetime
from openpyxl import load_workbook

# Importar módulos propios
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.api_client import GestorDCE 
from src.config_dce import DCE_IDS, MAPA_TR, MAPA_ML, MAPA_RECT

# Ruta del Excel
DIR_DATOS = os.path.join(os.path.dirname(__file__), '..', 'Datos\DB')
ARCHIVO_EXCEL_DCE = os.path.join(DIR_DATOS, 'datos_DCE.xlsx')

def limpiar_valor_dce(valor_str):
    """
    Intenta convertir a número (float). 
    Si es texto de estado (ej: 'Online'), lo devuelve tal cual.
    Ej: "215.5 V" -> 215.5
    Ej: "Normal" -> "Normal"
    """
    # Si ya es número, devolverlo
    if isinstance(valor_str, (int, float)):
        return valor_str
    
    texto = str(valor_str).strip()
    
    # Intento 1: ¿Es un número directo o con unidades (ej "220 V")?
    try:
        # Tomamos la primera parte antes del espacio
        parte_numerica = texto.split(' ')[0]
        return float(parte_numerica)
    except ValueError:
        # Intento 2: Si falló, es porque es un texto puro (ej: "Online", "Float")
        # Devolvemos el texto original limpio
        return texto

def guardar_en_excel(df_nuevo, nombre_hoja):
    """
    Agrega datos a una hoja de Excel existente sin borrar lo anterior.
    """
    # 1. Si el archivo no existe, lo creamos
    if not os.path.exists(ARCHIVO_EXCEL_DCE):
        print(f"       Creando archivo nuevo: {ARCHIVO_EXCEL_DCE}")
        with pd.ExcelWriter(ARCHIVO_EXCEL_DCE, engine='openpyxl') as writer:
            df_nuevo.to_excel(writer, sheet_name=nombre_hoja, index=False)
        return

    # 2. Si el archivo existe, intentamos adjuntar (append)
    try:
        # Cargamos el libro existente
        book = load_workbook(ARCHIVO_EXCEL_DCE)
        
        # Verificamos si la hoja existe
        if nombre_hoja in book.sheetnames:
            # Opción A: Leer todo, concatenar y guardar (Más seguro para mantener formato)
            df_existente = pd.read_excel(ARCHIVO_EXCEL_DCE, sheet_name=nombre_hoja)
            df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
            
            # Usamos ExcelWriter con modo 'a' (append) y replace de la hoja
            with pd.ExcelWriter(ARCHIVO_EXCEL_DCE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_final.to_excel(writer, sheet_name=nombre_hoja, index=False)
        else:
            # Si la hoja no existe, la creamos nueva en el mismo archivo
            with pd.ExcelWriter(ARCHIVO_EXCEL_DCE, engine='openpyxl', mode='a') as writer:
                df_nuevo.to_excel(writer, sheet_name=nombre_hoja, index=False)
                
    except Exception as e:
        print(f"       Error escribiendo Excel: {e}")

def sincronizar_dispositivo_a_excel(dce, device_id, mapa_columnas, nombre_hoja, extra_data=None):
    """
    Consulta API -> Mapea Columnas -> Guarda en Excel
    """
    print(f"    Consultando ID: {device_id} para hoja '{nombre_hoja}'...")
    
    # 1. API
    datos_raw = dce.consultar_equipo(device_id)
    if not datos_raw:
        print("       Sin respuesta del dispositivo.")
        return

    # 2. Construir Fila
    fila = {'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if extra_data:
        fila.update(extra_data)

    encontrados = 0
    for sensor in datos_raw:
        label_api = sensor.get('label', '')
        valor_api = sensor.get('value', 0)
        
        for key_map, col_excel in mapa_columnas.items():
            if key_map in label_api:
                fila[col_excel] = limpiar_valor_dce(valor_api)
                encontrados += 1
                break
    
    # 3. Guardar
    if encontrados > 0:
        df = pd.DataFrame([fila])
        guardar_en_excel(df, nombre_hoja)
        print(f"       Fila agregada a hoja '{nombre_hoja}' ({encontrados} datos).")
    else:
        print("       No se encontraron sensores coincidentes.")

def ejecutar_actualizacion_excel_dce(usuario, password):

    IP_DCE = "10.159.125.33"
    dce = GestorDCE(IP_DCE, usuario, password)

    print("\n" + "="*60)
    print(" ACTUALIZANDO EXCEL 'datos_DCE.xlsx' DESDE API \n")
    print(f" IP DCE: {IP_DCE} \n")
    print("="*60)
    
    
    
    # 1. TR (Hoja 'TR')
    sincronizar_dispositivo_a_excel(dce, DCE_IDS["TR"], MAPA_TR, "TR")
    
    # 2. ML (Hoja 'ML')
    time.sleep(1)
    sincronizar_dispositivo_a_excel(dce, DCE_IDS["ML"], MAPA_ML, "ML")
    
    # 3. Rectificadores (Hoja Unificada 'RECT')
    # Nota: Aquí usamos la misma hoja 'RECT' para ambos, agregando el ID
    time.sleep(1)
    sincronizar_dispositivo_a_excel(dce, DCE_IDS["RECT1"], MAPA_RECT, "RECT", extra_data={"rectificador_id": 1})
    
    time.sleep(1)
    sincronizar_dispositivo_a_excel(dce, DCE_IDS["RECT2"], MAPA_RECT, "RECT", extra_data={"rectificador_id": 2})

    print("\n Excel actualizado correctamente.")
    print(f" Archivo ubicado en: {ARCHIVO_EXCEL_DCE}")
