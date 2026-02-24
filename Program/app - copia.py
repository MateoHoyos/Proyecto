import streamlit as st
import pandas as pd
import sys
import os
import time

#streamlit run app.py

# --- CONFIGURACIÓN DE RUTAS ---
# Permitir importar módulos de la carpeta src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# --- IMPORTACIONES DEL BACKEND ---
from src.db import inicializar_base_datos_completa, get_engine
from src.etl import ejecutar_etl_maestro
from src.etl_dce import ejecutar_actualizacion_excel_dce
from src.analisis_potencia import evaluar_solicitud
from src.racks import buscar_espacio_en_racks, verificar_espacio_suelo
from src.lector_excel import leer_ultima_solicitud
from src.reporte_pdf import generar_pdf_factibilidad

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Sistema IDEO",

    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS (Opcional, para que se vea más limpio) ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TÍTULO PRINCIPAL ---
st.title("⚡ Sistema de Gestión Automática - Nodo IDEO")
st.markdown("---")

# ==========================================
# BARRA LATERAL (MENÚ)
# ==========================================
with st.sidebar:
    st.image("C:/Users/mhoyosme/Desktop/Proyecto/Archivos/img/logo_tigo.png", width=100) 
    st.header("Menú Principal")
    
    opcion = st.radio(
        "Seleccione una acción:",
        options=[
            "🏠 Inicio",
            "🔄 Actualizar Base de Datos (Manual)",
            "📡 Sincronizar DCE (API Real)",
            "📋 Ver Datos de Entrada (Excel)",
            "🚀 Procesar Solicitud (Evaluador)"
        ]
    )
    
    st.markdown("---")
    st.caption("v1.0 - Modelado de infraestructura de los nodos")

# ==========================================
# LÓGICA DE LAS PÁGINAS
# ==========================================

# 1. INICIO
if opcion == "🏠 Inicio":
    st.info("Bienvenido al Sistema de Gestión de Capacidad.")
    st.markdown("""
    Este sistema permite:
    *   **Digitalizar** el inventario de energía y espacio.
    *   **Monitorear** en tiempo real vía API DCE.
    *   **Evaluar** factibilidad técnica de nuevos equipos automáticamente.
    """)
    
    # Check rápido de conexión
    try:
        engine = get_engine()
        with engine.connect() as conn:
            st.success("✅ Conexión a Base de Datos: ACTIVA")
    except Exception as e:
        st.error(f"❌ Error de conexión a BD: {e}")

# 2. ACTUALIZAR BD (ETL MANUAL)
elif opcion == "🔄 Actualizar Base de Datos (Manual)":
    st.header("Actualización de Datos Maestros")
    st.write("Esta opción recarga la información desde el archivo Excel `Datos/datos_manuales.xlsx`.")
    
    if st.button("Ejecutar ETL Manual"):
        with st.spinner("Actualizando tablas..."):
            try:
                # Redirigimos prints para verlos en log o simplemente confiamos en el spinner
                inicializar_base_datos_completa()
                ejecutar_etl_maestro()
                st.success("✅ Base de datos actualizada correctamente desde Excel manual.")
            except Exception as e:
                st.error(f"❌ Error durante el proceso: {e}")

# 3. SINCRONIZAR DCE (API)
elif opcion == "📡 Sincronizar DCE (API Real)":
    st.header("Sincronización con Data Center Expert")
    st.write("Conexión en tiempo real para actualizar voltajes y corrientes.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        usuario = st.text_input("Usuario DCE", value="mhoyosme")
        password = st.text_input("Contraseña", type="password")
    
    if st.button("Iniciar Sincronización"):
        if not password:
            st.warning("⚠️ Ingrese la contraseña.")
        else:
            proceso_contenedor = st.empty()
            with st.spinner("Conectando a API DCE... (Esto puede tardar unos segundos)"):
                try:
                    # Nota: Ejecutar sincronización imprime en consola. 
                    # En Streamlit solo veremos el resultado final o errores.
                    ejecutar_actualizacion_excel_dce(usuario, password)
                    st.success("✅ Datos sincronizados y guardados en MySQL.")
                except Exception as e:
                    st.error(f"❌ Error de conexión: {e}")

# 4. VER DATOS DE ENTRADA
elif opcion == "📋 Ver Datos de Entrada (Excel)":
    st.header("Datos de la Última Solicitud")
    st.write("Lectura del archivo `Datos del Equipo Nuevo.xlsx`")
    
    solicitud = leer_ultima_solicitud()
    
    if solicitud:
        # Mostramos los datos en tarjetas (métricas)
        c1, c2, c3 = st.columns(3)
        c1.metric("Equipo", solicitud['Equipment'])
        c2.metric("Potencia Total", f"{solicitud['Máx. Power DC (W)'] * solicitud['Quantity Equipment DC']} W")
        c3.metric("Voltaje", solicitud['Voltage(AC or DC)'])
        
        c4, c5, c6 = st.columns(3)
        c4.metric("Fuentes", solicitud['Power sources'])
        c5.metric("Sitio", solicitud['Technical Site'])
        
        # Lógica visual para Racks
        if solicitud['Requiere_Rack_Nuevo']:
            c6.metric("Espacio", f"{solicitud['Cantidad_Racks_Nuevos']} Racks Nuevos (Suelo)")
        else:
            c6.metric("Espacio", f"{solicitud['U_Requeridas']} U (Rack Existente)")
            
        st.info(f"Disipación Térmica: {solicitud.get('BTU_Label', 'N/A')}")
        
        # Mostrar diccionario completo crudo (para debug)
        with st.expander("Ver datos crudos (JSON)"):
            st.json(solicitud)
    else:
        st.error("❌ No se pudo leer el archivo Excel o está vacío.")

# 5. PROCESAR SOLICITUD (EL EVALUADOR)
elif opcion == "🚀 Procesar Solicitud (Evaluador)":
    st.header("Evaluación de Factibilidad Técnica")
    
    if st.button("Ejecutar Análisis"):
        solicitud = leer_ultima_solicitud()
        
        if not solicitud:
            st.error("No se pueden cargar los datos de entrada.")
            st.stop()
            
        engine = get_engine()
        st.write("---")
        
        # --- PASO 1: ESPACIO FÍSICO ---
        st.subheader("1. Análisis de Espacio Físico")
        espacio_aprobado = False
        racks_viables = []
        
        if solicitud['Requiere_Rack_Nuevo']:
            suelo_ok, msg_suelo = verificar_espacio_suelo(engine, solicitud['Cantidad_Racks_Nuevos'])
            if suelo_ok:
                st.success(msg_suelo)
                solicitud['Recomendacion_Instalacion_Fisica'] = msg_suelo
                espacio_aprobado = True
            else:
                st.error(msg_suelo)
                solicitud['Recomendacion_Instalacion_Fisica'] = msg_suelo
        else:
            racks_viables = buscar_espacio_en_racks(solicitud["U_Requeridas"])
            if racks_viables:
                st.success(f"Espacio encontrado en {len(racks_viables)} Racks.")
                
                # Crear DataFrame para mostrar tabla bonita
                data_racks = []
                for r in racks_viables:
                    bloques = ", ".join([f"U{b['inicio']}-{b['fin']}" for b in r['bloques']])
                    data_racks.append({"Rack": r['rack'], "Bloques Disponibles": bloques, "Foto": r.get('foto', '')})
                
                st.dataframe(pd.DataFrame(data_racks), hide_index=True, use_container_width=True)
                
                solicitud['Recomendacion_Instalacion_Fisica'] = f"Rack Sugerido: {racks_viables[0]['rack']}"
                espacio_aprobado = True
            else:
                st.error("No se encontró espacio contiguo en ningún rack.")

        # --- PASO 2: ENERGÍA ---
        st.subheader("2. Análisis de Energía y Protecciones")
        
        # Spinner mientras calcula
        with st.spinner("Calculando cargas, validando PDBs y Rectificadores..."):
            resultado_energia = evaluar_solicitud(engine, solicitud)
        
        energia_aprobada = (resultado_energia["PRE-Factibilidad Infraestructura (Si / No)"] == "SI")
        
        # Mostrar Checks con colores
        for check in resultado_energia['Checks']:
            if "[FALLO]" in check or "❌" in check:
                st.error(check)
            elif "[ADVERTENCIA]" in check or "⚠️" in check:
                st.warning(check)
            elif "[OK]" in check or "✅" in check:
                st.success(check)
            else:
                st.info(check)

        # --- RESULTADO FINAL ---
        st.write("---")
        st.subheader("Dictamen Final")
        
        if espacio_aprobado and energia_aprobada:
            # st.balloons()
            st.success("✅ VIABILIDAD TÉCNICA: APROBADO")
            
            st.markdown(f"**Instrucción:** {resultado_energia['Recomendacion_Instalacion']}")
            
            # Botón para generar PDF
            if st.button("📄 Generar Reporte PDF"):
                # Si racks_viables está vacío (caso suelo), pasamos lista vacía
                racks_pdf = racks_viables if racks_viables else []
                generar_pdf_factibilidad(resultado_energia, racks_pdf, solicitud)
                st.success("Reporte generado en la carpeta /Reportes")
                
        else:
            st.error("❌ VIABILIDAD TÉCNICA: RECHAZADO")
            st.write("Revise los puntos marcados en rojo arriba.")
            
            # También permitimos generar reporte de rechazo
            if st.button("📄 Generar Reporte de Rechazo"):
                racks_pdf = racks_viables if racks_viables else []
                generar_pdf_factibilidad(resultado_energia, racks_pdf, solicitud)
                st.info("Reporte de rechazo generado.")