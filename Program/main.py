import sys
import os
import getpass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.db import inicializar_base_datos_completa, get_engine
from src.etl import ejecutar_etl_maestro
from src.analisis_potencia import evaluar_solicitud
from src.racks import buscar_espacio_en_racks, verificar_espacio_suelo, mostrar_foto_rack
from src.lector_excel import leer_ultima_solicitud 
from src.reporte_pdf import generar_pdf_factibilidad
from src.etl_dce import ejecutar_actualizacion_excel_dce 


def ejecutar_evaluacion_automatica():
    engine = get_engine()
    
    print("\n" + "█"*60)
    print("LEYENDO ÚLTIMA SOLICITUD DEL FORMULARIO...")
    print("█"*60)
    
    # 1. Leer Excel
    solicitud = leer_ultima_solicitud()
    
    if not solicitud:
        print("No se pudo procesar la solicitud. Revise el archivo Excel.")
        return

    print(f"\n Solicitud encontrada:")
    print(f"   • Equipo: {solicitud['Equipment']}")
    print(f"   • Potencia: {solicitud['Máx. Power DC (W)']} W")
    print(f"   • Espacio U: {solicitud['U_Requeridas']} U")
    if solicitud['Requiere_Rack_Nuevo']:
        print(f"   •  REQUIERE {solicitud['Cantidad_Racks_Nuevos']} RACKS NUEVOS (Suelo)")
    
    print(f"   • Aire (BTU): {solicitud['BTU']} {'(Calculado)' if solicitud.get('BTU_Calculado') else '(Manual)'}")

    # =========================================================
    # PASO 1: EVALUACIÓN DE ESPACIO (RACKS O SUELO)
    # =========================================================
    print("\n 1. VERIFICANDO ESPACIO FÍSICO...")
    espacio_aprobado = False
    racks_viables = [] # Para el PDF
    

    # CASO A: Piden Rack Nuevo (Validar Suelo)
    if solicitud['Requiere_Rack_Nuevo']:
        print("   -> Analizando capacidad de suelo para nuevos racks...")
        suelo_ok, msg_suelo = verificar_espacio_suelo(engine, solicitud['Cantidad_Racks_Nuevos'])
        
        if suelo_ok:
            print(f"   {msg_suelo}")
            espacio_aprobado = True
            
            # --- CAMBIO AQUÍ ---
            # Antes guardábamos un texto genérico. Ahora guardamos el mensaje DETALLADO (msg_suelo)
            # para que salga tal cual en el PDF.
            solicitud['Recomendacion_Instalacion_Fisica'] = msg_suelo 
            
        else:
            print(f"   {msg_suelo}")
            # También guardamos el mensaje de error para el PDF de rechazo
            solicitud['Recomendacion_Instalacion_Fisica'] = msg_suelo
            return # Fin del proceso




    # CASO B: Piden espacio en Rack Existente (Validar U)
    else:
        print("   -> Buscando huecos en racks existentes...")
        racks_viables = buscar_espacio_en_racks(solicitud["U_Requeridas"])
        
        if racks_viables:
            print(f"  ¡ESPACIO ENCONTRADO! {len(racks_viables)} opciones.")
            # Tomamos el primero como recomendación principal
            solicitud['Recomendacion_Instalacion_Fisica'] = f"Rack Recomendado: {racks_viables[0]['rack']}"
            espacio_aprobado = True
        else:
            print("  FALLO: No hay racks con espacio contiguo suficiente.")
            return

    # =========================================================
    # PASO 2: EVALUACIÓN ELÉCTRICA
    # =========================================================
    print("\n 2. VERIFICANDO CAPACIDAD ELÉCTRICA...")
    resultado_energia = evaluar_solicitud(engine, solicitud)
    
    # =========================================================
    # REPORTE Y PDF
    # =========================================================
    energia_aprobada = (resultado_energia["PRE-Factibilidad Infraestructura (Si / No)"] == "SI")
    
    print("\n" + "="*60)
    print("  RESULTADO DE LA EVALUACIÓN")
    print("="*60)
    
    if espacio_aprobado and energia_aprobada:
        print(f"APROBADO")
        # Generar PDF
        print("\nGenerando PDF...")
        generar_pdf_factibilidad(resultado_energia, racks_viables, solicitud)
    else:
        print(f"RECHAZADO")

        generar_pdf_factibilidad(resultado_energia, racks_viables, solicitud)

def menu_principal():

    while True:
        print("\n--- SISTEMA AUTOMÁTICO IDEO ---")
        print("1. Actualizar base de datos")
        print("2. Ver datos de ingreso")
        print("3. Sincronizar con DCE (Tiempo Real API)")
        print("4. Procesar Solicitud desde Excel")
        print("0. Salir")
        
        op = input("Opción: ")
        if op == '1': ejecutar_etl_maestro()

        elif op == '2':
            solicitud = leer_ultima_solicitud() 
            print(solicitud)
        
        elif op == '3':
            # Pedir credenciales una vez (o usar keyring si lo implementaste)
            #user = "mhoyosme"
            #print(f"Usuario: {user}")
            user = getpass.getpass("Ingrese Usuario DCE: ")
            pw = getpass.getpass("Ingrese contraseña DCE: ")
            ejecutar_actualizacion_excel_dce(user, pw)
            input("\n[Enter] para continuar...")

        elif op == '4': ejecutar_evaluacion_automatica()

        elif op == '0': break

def limpiar_consola():
    os.system('cls' if os.name == 'nt' else 'clear') 

if __name__ == "__main__":
    try:
        limpiar_consola()
        inicializar_base_datos_completa()
        menu_principal()
    except Exception as e:
        print(f"Error: {e}")