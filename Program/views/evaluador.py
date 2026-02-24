import streamlit as st
from src.db import get_engine
from src.lector_excel import leer_ultima_solicitud
from src.racks import buscar_espacio_en_racks, verificar_espacio_suelo
from src.analisis_potencia import evaluar_solicitud
from src.reporte_pdf import generar_pdf_factibilidad
import pandas as pd

def mostrar_vista_evaluador():
    st.header("Evaluación de Factibilidad Técnica")
    
    # --- BOTÓN DE CÁLCULO ---
    if st.button("Ejecutar Análisis"):
        solicitud = leer_ultima_solicitud()
        
        if not solicitud:
            st.error("No se pueden cargar los datos de entrada.")
        else:
            engine = get_engine()
            with st.spinner("Calculando..."):
                # 1. Racks
                racks_viables_res = []
                if solicitud['Requiere_Rack_Nuevo']:
                    suelo_ok, msg_suelo = verificar_espacio_suelo(engine, solicitud['Cantidad_Racks_Nuevos'])
                    solicitud['Recomendacion_Instalacion_Fisica'] = msg_suelo
                    st.session_state['espacio_aprobado'] = suelo_ok
                else:
                    racks_viables_res = buscar_espacio_en_racks(solicitud["U_Requeridas"])
                    if racks_viables_res:
                        solicitud['Recomendacion_Instalacion_Fisica'] = f"Rack Sugerido: {racks_viables_res[0]['rack']}"
                        st.session_state['espacio_aprobado'] = True
                    else:
                        st.session_state['espacio_aprobado'] = False

                # 2. Energía
                resultado_energia_res = evaluar_solicitud(engine, solicitud)
                
                # Guardar en sesión
                st.session_state['solicitud_actual'] = solicitud
                st.session_state['resultado_energia'] = resultado_energia_res
                st.session_state['racks_viables'] = racks_viables_res
                st.session_state['calculo_realizado'] = True

    st.write("---")

    # --- MOSTRAR RESULTADOS ---
    if st.session_state.get('calculo_realizado'):
        solicitud = st.session_state['solicitud_actual']
        resultado = st.session_state['resultado_energia']
        racks = st.session_state['racks_viables']
        espacio_aprobado = st.session_state['espacio_aprobado']
        energia_aprobada = (resultado["PRE-Factibilidad Infraestructura (Si / No)"] == "SI")

        # 1. Racks
        st.subheader("1. Análisis de Espacio Físico")
        if espacio_aprobado:
            st.success(solicitud['Recomendacion_Instalacion_Fisica'])
            if racks:
                data_racks = [{"Rack": r['rack'], "Espacios": [f"U{b['inicio']}-{b['fin']}" for b in r['bloques']]} for r in racks]
                st.dataframe(pd.DataFrame(data_racks), hide_index=True)
        else:
            st.error(solicitud.get('Recomendacion_Instalacion_Fisica', "Sin espacio disponible."))

        # 2. Energía
        st.subheader("2. Análisis de Energía")
        for check in resultado['Checks']:
            if "[FALLO]" in check or "❌" in check: st.error(check)
            elif "[ADVERTENCIA]" in check or "⚠️" in check: st.warning(check)
            elif "[OK]" in check or "✅" in check: st.success(check)
            else: st.info(check)

        # 3. Final
        st.write("---")
        if espacio_aprobado and energia_aprobada:
            st.success("✅ VIABILIDAD TÉCNICA: APROBADO")
            if st.button("📄 Generar Reporte PDF", key="btn_pdf"):
                exito, ruta = generar_pdf_factibilidad(resultado, racks, solicitud)
                if exito: st.success(f"Reporte generado: {ruta}")
                else: st.error(f"Error: {ruta}")
        else:
            st.error("❌ VIABILIDAD TÉCNICA: RECHAZADO")
            if st.button("📄 Generar Reporte de Rechazo", key="btn_pdf_fail"):
                exito, ruta = generar_pdf_factibilidad(resultado, racks, solicitud)
                if exito: st.info(f"Reporte de rechazo generado: {ruta}")