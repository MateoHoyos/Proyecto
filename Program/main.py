import sys
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
# Agregamos la carpeta 'src' para poder importar tus módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# --- IMPORTACIONES ---
from src.db import inicializar_base_datos_completa, get_engine
from src.etl import ejecutar_etl_maestro
from src.recomendador import evaluar_solicitud  # Tu nueva lógica de PDBs y Energía
from src.logica_racks import buscar_espacio_en_racks, mostrar_foto_rack # Tu lógica de Racks

def obtener_datos_usuario():
    """
    Formulario para pedir los datos técnicos del equipo nuevo.
    """
    print("\n📝 --- FORMULARIO DE INGRESO DE PROYECTO ---")
    datos = {}
    
    datos["Equipment"] = input("1. Nombre del Equipo (ej. Router Huawei NE40): ")
    
    # Validación de números
    while True:
        try:
            datos["Quantity Equipment DC"] = int(input("2. Cantidad de equipos: "))
            break
        except ValueError: print("❌ Ingresa un número entero.")

    while True:
        try:
            # Pedimos la potencia máxima para calcular el peor escenario
            datos["Máx. Power DC (W)"] = float(input("3. Potencia Máxima DC por equipo (Watts): "))
            break
        except ValueError: print("❌ Ingresa un número (ej. 2500).")

    datos["Voltage(AC or DC)"] = input("4. Voltaje (ej. DC -48V): ")
    
    while True:
        try:
            # CAMBIO AQUÍ: Permitimos hasta 10 fuentes (para cubrir casos de 4+4, etc.)
            input_fuentes = int(input("5. Número TOTAL de fuentes de poder (ej. 2, 4, 6...): "))
            
            if 1 <= input_fuentes <= 10: 
                datos["Power sources"] = input_fuentes
                break
            else: 
                print("❌ Por favor ingrese un número entre 1 y 10.")
        except ValueError: 
            print("❌ Error de número.")

    while True:
        try:
            datos["U_Requeridas"] = int(input("6. Unidades de Rack (U) requeridas (Altura): "))
            break
        except ValueError: print("❌ Ingresa un número entero.")

    # Datos adicionales requeridos por la lógica
    datos["Technical Site"] = "IDEO CALI"
    datos["Potencia a liberar"] = 0 
    
    return datos

def ejecutar_evaluacion_completa():
    """
    Orquestador: Une la validación de Racks con la Eléctrica.
    """
    # 1. Obtener datos y conexión
    solicitud = obtener_datos_usuario()
    engine = get_engine() 
    
    print("\n" + "█"*60)
    print("🚀 INICIANDO ANÁLISIS DE PRE-FACTIBILIDAD")
    print("█"*60)
    time.sleep(1)

    # =========================================================
    # PASO 1: ESPACIO FÍSICO (RACKS)
    # =========================================================
    print("\n🔍 1. VERIFICANDO ESPACIO EN RACKS...")
    u_req = solicitud["U_Requeridas"]
    racks_viables = buscar_espacio_en_racks(u_req)
    
    espacio_aprobado = False
    
    if racks_viables:
        print(f"   ✅ ¡ESPACIO ENCONTRADO! Opciones disponibles:")
        # Mostrar resumen simple
        for i, r in enumerate(racks_viables):
            # Formatear bloques para que se vea limpio "U24-U28"
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
        print("   ❌ FALLO: No hay racks con espacio contiguo suficiente.")
        print("   ⚠️ El proceso se detiene. No es posible instalar.")
        return # Salimos, no vale la pena calcular energía si no cabe

    # =========================================================
    # PASO 2: CAPACIDAD ELÉCTRICA (PDB + CABLES + TR)
    # =========================================================
    print("\n⚡ 2. VERIFICANDO CAPACIDAD ELÉCTRICA (PDB, Cables, TR)...")
    
    # Aquí llamamos a tu nuevo recomendador
    # Él internamente decide si cabe en PDB1 o PDB2 y valida la corriente manual
    resultado_energia = evaluar_solicitud(engine, solicitud)
    
    energia_aprobada = (resultado_energia["PRE-Factibilidad Infraestructura (Si / No)"] == "SI")
    
    # =========================================================
    # REPORTE FINAL
    # =========================================================
    print("\n" + "="*60)
    print("📋  INFORME FINAL DE VIABILIDAD TÉCNICA")
    print("="*60)
    
    if espacio_aprobado and energia_aprobada:
        print(f"✅ ESTADO: APROBADO")
        print("\n--- 📍 UBICACIÓN FÍSICA SUGERIDA ---")
        print(f"Rack Recomendado: {racks_viables[0]['rack']}")
        
        print("\n--- 🔌 CONEXIÓN ELÉCTRICA ---")
        print(resultado_energia['Recomendacion_Instalacion']) 
        # Esto imprimirá: "Espacio asignado en PDB1..."
        
        print("\n--- ✅ VALIDACIONES EXITOSAS ---")
        for check in resultado_energia['Checks']:
            if "✅" in check: print(f"   {check}")
            
    else:
        print(f"❌ ESTADO: RECHAZADO")
        print("\n--- ⚠️ MOTIVOS DEL RECHAZO ---")
        
        # Imprimimos todas las alertas y errores eléctricos
        for check in resultado_energia['Checks']:
            if "❌" in check or "⚠️" in check or "SOBRECARGA" in check:
                print(f"   • {check}")

def menu_principal():
    while True:
        print("\n" + "-"*40)
        print("      SISTEMA GESTIÓN NODO IDEO")
        print("-" * 40)
        print("1. 🔄 Actualizar Base de Datos (ETL Manual)")
        print("2. 🏗️  Evaluar Nuevo Proyecto")
        print("3. 🚪 Salir")
        
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
    # Inicialización segura
    try:
        limpiar_consola()
        inicializar_base_datos_completa() # Asegura que las tablas existan
        menu_principal()
    except Exception as e:
        print(f"❌ Error crítico iniciando: {e}")