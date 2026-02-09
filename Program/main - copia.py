import sys
import os
import time
from itertools import groupby
from operator import itemgetter
import pandas as pd

# --- IMPORTACIÓN DE TUS MÓDULOS ---
# Agregamos la carpeta src al sistema para poder importar
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from src.db import inicializar_base_datos_completa, get_engine
from src.etl import ejecutar_etl_maestro
from src.logica_racks import buscar_espacio_en_racks, mostrar_foto_rack 
#from recomendador import evaluar_solicitud  # Tu lógica eléctrica (PDB, TR, Rectificadores)
#from logica_racks import buscar_espacio_en_racks # Tu lógica de espacio físico


#******************************************************************************************************

def obtener_datos_usuario():
    """
    Pide los datos básicos por consola con validación de errores.
    """
    print("\n --- INGRESO DE DATOS DEL NUEVO PROYECTO ---")
    datos = {}
    
    # 1. Nombre
    datos["Equipment"] = input("1. Nombre del Equipo (ej. Router Huawei NE40): ")
    
    # 2. Unidades de Rack (Fundamental para el paso 1)
    while True:
        try:
            u_input = input("2. ¿Cuántas Unidades de Rack (U) ocupa de altura? (ej. 2): ")
            datos["U_Requeridas"] = int(u_input)

            if datos["U_Requeridas"] > 0: break
            else: print("Debe ser mayor a 0.")
        except ValueError: print("Ingresa un número entero válido.")

    # 3. Datos eléctricos (Los pedimos de una vez para guardarlos, aunque no se usen en el paso 1)
    while True:
        try:
            datos["Quantity"] = int(input("3. Cantidad de equipos: "))
            break
        except ValueError: print("Error: Ingresa un número.")

    while True:
        try:
            datos["Power_W"] = float(input("4. Potencia Máxima DC por equipo (Watts): "))
            break
        except ValueError: print("Error: Ingresa un número (ej. 2500).")

    datos["Voltage"] = input("5. Voltaje (ej. DC -48V): ")
    
    return datos


#******************************************************************************************************

def evaluar_espacio_racks(datos_solicitud):
    """
    Muestra disponibilidad agrupada por Rack y permite ver fotos.
    """
    print("\n" + "█"*60)
    print(" PASO 1: VERIFICANDO ESPACIO FÍSICO (RACK2S)")
    print("█"*60)
    time.sleep(1)
    
    u_necesarias = int(datos_solicitud["U_Requeridas"])
    print(f"   Analizando inventario para equipo de {u_necesarias}U...")
    
    # Llamamos a la nueva lógica
    racks_encontrados = buscar_espacio_en_racks(u_necesarias)
    
    if racks_encontrados:
        print(f"\n   ¡ÉXITO! Se encontró espacio en {len(racks_encontrados)} Racks:\n")
        
        # Imprimir Tabla Resumen
        print(f"   {'RACK':<20} | {'ESPACIO DISPONIBLE (Bloques)'}")
        print("   " + "-"*60)
        
        for i, item in enumerate(racks_encontrados):
            # Formatear los bloques en un string (ej: "U24-U40, U42-U44")
            textos_bloques = [f"U{b['inicio']}->U{b['fin']}" for b in item['bloques']]
            detalle = ", ".join(textos_bloques)
            print(f"   {i+1}. {item['rack']:<17} | {detalle}")

        # Preguntar si quiere ver foto
        print("\n" + "-"*60)
        

        while True:
            opcion = input("   ¿Desea ver la foto de algún rack? (Escriba el número de la lista o 'n' para continuar): ")
            
            if opcion.lower() == 'n':
                return True # Continuamos al siguiente paso
            
            try:
                # Convertimos opción a índice (ej: Usuario escribe "1", el índice es 0)
                idx = int(opcion) - 1
                
                if 0 <= idx < len(racks_encontrados):
                    rack_elegido = racks_encontrados[idx]
                    nombre_foto = rack_elegido.get('foto')
                    
                    # Validar si en la BD dice "No disponible" o viene vacío
                    if nombre_foto and nombre_foto != "No disponible":
                        mostrar_foto_rack(nombre_foto)
                    else:
                        print(f"    El Rack {rack_elegido['rack']} no tiene foto registrada en la Base de Datos.")
                else:
                    print("   Número fuera de rango. Intente con los números de la lista (1, 2...).")
            
            except ValueError:
                print("   Entrada no válida. Escriba un número o 'n'.")

        return True
    else:
        print(f"\n    FALLO CRÍTICO: No hay {u_necesarias} unidades consecutivas en ningún rack.")
        return False



#******************************************************************************************************

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')


def ejecutar_evaluacion_completa():
    # 1. Pedir datos
    engine = get_engine() # Conexión para las consultas
    
    print("\n" + "█"*60)
    print(" INICIANDO ANÁLISIS DE PRE-FACTIBILIDAD")
    print("█"*60)
    time.sleep(1)


def menu_principal():
    while True:
        print("\n" + "-"*40)
        print("      SISTEMA GESTIÓN NODO IDEO")
        print("-" * 40)
        print("1.Actualizar Base de Datos (Ejecutar ETL)")
        print("2.Evaluar Nuevo Proyecto (Paso a Paso)")
        print("3.Salir")
        
        opcion = input("\nSeleccione una opción: ")

        
        if opcion == '1':
            ejecutar_etl_maestro()
            input("\nPresione Enter para continuar...")

        elif opcion == '2':
            # A. Pedir datos
            solicitud = obtener_datos_usuario()
            
            # B. Evaluar Racks (Paso 1)
            if evaluar_espacio_racks(solicitud):
                print("\n✨ PASO 1 APROBADO. (Aquí seguiría la evaluación eléctrica...)")
            else:
                print("\n⛔ PROYECTO RECHAZADO POR FALTA DE ESPACIO.")
            
            input("\nPresione Enter para volver al menú...")


        elif opcion == '3':
            print("Saliendo del sistema...")
            break    
        else:
            print("Opción no válida.")





#******************************************************************************************************

if __name__ == "__main__":
    # Aseguramos que la BD exista al arrancar el programa
    try:
        inicializar_base_datos_completa()
        menu_principal()
    except Exception as e:
        print(f"Error crítico iniciando el sistema: {e}")