import sys
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from src.db import inicializar_base_datos_completa, get_engine
from src.etl import ejecutar_etl_maestro
from src.recomendador import evaluar_solicitud 
from src.logica_racks import buscar_espacio_en_racks, mostrar_foto_rack
from src.reporte_pdf import generar_pdf_factibilidad

def obtener_datos_usuario():
    print("\n --- FORMULARIO DE INGRESO DE PROYECTO ---")
    datos = {}

    datos["Equipment"] = input("1. Nombre del Equipo (ej. Router Huawei NE40): ")
    
    while True:

        try:
            datos["Quantity Equipment DC"] = int(input("2. Cantidad de equipos: "))
            break

        except ValueError: print("Ingresa un número entero.")



    while True:

        try:
            datos["Máx. Power DC (W)"] = float(input("3. Potencia Máxima DC por equipo (Watts): "))
            break

        except ValueError: print("Ingresa un número (ej. 2500).")

    datos["Voltage(AC or DC)"] = input("4. Voltaje (ej. DC -48V): ")

    while True:
        try:
            input_fuentes = int(input("5. Número TOTAL de fuentes de poder (ej. 2, 4, 6...): "))
            
            if 1 <= input_fuentes <= 10: 
                datos["Power sources"] = input_fuentes
                break
            else: 
                print("Por favor ingrese un número entre 1 y 10.")

        except ValueError: 
            print("Error de número.")


    while True:
        try:
            datos["U_Requeridas"] = int(input("6. Unidades de Rack (U) requeridas (Altura): "))
            break
        except ValueError: print("❌ Ingresa un número entero.")

    datos["Technical Site"] = "IDEO CALI"
    datos["Potencia a liberar"] = 0 

    return datos






def ejecutar_evaluacion_completa():
    solicitud = obtener_datos_usuario()
    engine = get_engine() 
    
    print("\n" + "█"*60)
    print("INICIANDO ANÁLISIS DE PRE-FACTIBILIDAD")
    print("█"*60)
    time.sleep(1)

    # =========================================================
    # PASO 1: ESPACIO FÍSICO (RACKS)
    # =========================================================

    print("\n 1. VERIFICANDO ESPACIO EN RACKS...")
    u_req = solicitud["U_Requeridas"]
    racks_viables = buscar_espacio_en_racks(u_req)
    espacio_aprobado = False
    
    if racks_viables:
        print(f"¡ESPACIO ENCONTRADO! Opciones disponibles:")


        for i, r in enumerate(racks_viables):
            bloques_str = ", ".join([f"U{b['inicio']}->U{b['fin']}" for b in r['bloques']])
            print(f"      {i+1}. {r['rack']:<15} | {bloques_str}")
        
        espacio_aprobado = True
        
        # Opcional: Ver foto
        ver_foto = input("\n   ¿Desea ver la foto de algún rack antes de seguir? (s/n): ")
        if ver_foto.lower() == 's':
            try:
                idx = int(input("   Ingrese el número de la lista: ")) - 1
                if 0 <= idx < len(racks_viables):
                    foto = racks_viables[idx].get('foto')
                    if foto: mostrar_foto_rack(foto)
            except: pass
    else:
        print("FALLO: No hay racks con espacio contiguo suficiente.")
        print("El proceso se detiene. No es posible instalar.")
        return

    # =========================================================
    # PASO 2: CAPACIDAD ELÉCTRICA (PDB + CABLES + TR)
    # =========================================================
    print("\n 2. VERIFICANDO CAPACIDAD ELÉCTRICA (PDB, Cables, TR)...")
    
    resultado_energia = evaluar_solicitud(engine, solicitud)
    energia_aprobada = (resultado_energia["PRE-Factibilidad Infraestructura (Si / No)"] == "SI")
    print("\nInforme PDF generado correctamente.")
    
    # =========================================================
    # REPORTE FINAL
    # =========================================================
    print("\n" + "="*60)
    print(" INFORME FINAL DE VIABILIDAD TÉCNICA")
    print("="*60)
    
    if espacio_aprobado and energia_aprobada:
        print(f"[OK] ESTADO: APROBADO")
        print("\n---  UBICACIÓN FÍSICA SUGERIDA ---")
        print(f"Rack Recomendado: {racks_viables[0]['rack']}")
        
        print("\n---  CONEXIÓN ELÉCTRICA ---")
        print(resultado_energia['Recomendacion_Instalacion']) 
        # Esto imprimirá: "Espacio asignado en PDB1..."
        
        print("\n--- [OK] VALIDACIONES EXITOSAS ---")
        for check in resultado_energia['Checks']:
            if "[OK]" in check: print(f"   {check}")
            
    else:
        print(f"ESTADO: RECHAZADO")
        print("\n--- [ALERTA] MOTIVOS DEL RECHAZO ---")
        
        # Imprimimos todas las alertas y errores eléctricos
        for check in resultado_energia['Checks']:
            if "[FALLO]" in check or "[ALERTA]" in check or "SOBRECARGA" in check:
                print(f"   • {check}")


    # GENERAR PDF AUTOMÁTICO
    print("\nGenerando documento PDF...")
    
    # Si racks_viables no existe, pasamos lista vacía
    racks_para_pdf = racks_viables if espacio_aprobado else []
    
    # NUEVO: Pasamos 'solicitud' como tercer argumento
    generar_pdf_factibilidad(resultado_energia, racks_para_pdf, solicitud)

def menu_principal():
    while True:
        print("\n" + "-"*40)
        print("      SISTEMA GESTIÓN NODO IDEO")
        print("-" * 40)
        print("1. Actualizar Base de Datos (ETL Manual)")
        print("2. Evaluar Nuevo Proyecto")
        print("3. Salir")
        
        opcion = input("\nSeleccione: ")
        
        if opcion == '1':
            ejecutar_etl_maestro()
            input("\n[Enter] para continuar...")
            
        elif opcion == '2':
            ejecutar_evaluacion_completa()
        
            input("\n[Enter] para volver al menú...")
            
        elif opcion == '3':
            print("Cerrando sistema...")
            break

def limpiar_consola():
    os.system('cls' if os.name == 'nt' else 'clear') 





if __name__ == "__main__":
    try:
        limpiar_consola()
        inicializar_base_datos_completa() # Asegura que las tablas existan
        menu_principal()
    except Exception as e:
        print(f"Error crítico iniciando: {e}")