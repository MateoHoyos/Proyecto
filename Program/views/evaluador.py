import streamlit as st
import pandas as pd
from src.db import get_engine
from src.lector_excel import leer_ultima_solicitud
from src.racks import buscar_espacio_en_racks, verificar_espacio_suelo
from src.analisis_potencia import evaluar_solicitud
from src.reporte_pdf import generar_pdf_factibilidad

def mostrar_vista_evaluador():
    st.header("Evaluación de Proyecto Nuevo")

    # Cargar datos
    solicitud = leer_ultima_solicitud()

    if not solicitud:
        st.error("❌ No se pudo leer el archivo 'Datos del Equipo Nuevo.xlsx'. Verifique que exista en la carpeta Datos.")
        return

    # ─────────────────────────────────────────────
    # ESTADO: aún no se ha ejecutado el análisis
    # ─────────────────────────────────────────────
    if not st.session_state.get('calculo_realizado'):

        st.markdown("Revise los datos cargados desde el archivo Excel y ejecute el análisis.")
        st.subheader("Datos de Entrada")
        st.markdown("---")

        # Información general

        st.metric("Equipo", solicitud['Equipment'])

        c1, c2 = st.columns(2)
        c1.metric("Sitio", solicitud['Technical Site'])
        c2.metric("Cantidad de Equipos", solicitud['Quantity Equipment DC'])

        c2, c3 = st.columns(2)
        c2.metric("Potencia Total", f"{solicitud['Máx. Power DC (W)'] * solicitud['Quantity Equipment DC']} W")
        c3.metric("Fuentes de Alimentación", solicitud['Power sources'])

        c4, c5 = st.columns(2)
        c4.metric("Voltaje", solicitud['Voltage(AC or DC)'])
        c5.metric("Disipación: ", f"{solicitud.get('BTU_Label', 'N/A')} BTU")
        


        if solicitud['Requiere_Rack_Nuevo']:
            st.info(f"Espacio Requerido: {solicitud['Cantidad_Racks_Nuevos']} Racks (Suelo)")
        else:
            st.info(f"Espacio Requerido: {solicitud['U_Requeridas']} U (Rack)")


        st.markdown("---")

        # Detalle completo opcional
        with st.expander("Ver detalle completo de datos (JSON)"):
            st.json(solicitud)

        st.markdown("---")

        # Botón de ejecución
        if st.button("▶ EJECUTAR ANÁLISIS", type="primary"):
            engine = get_engine()
            with st.spinner("Analizando disponibilidad física y eléctrica..."):

                # A. Espacio en racks / suelo
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

                # B. Energía
                resultado_energia_res = evaluar_solicitud(engine, solicitud)

            # Guardar en sesión y recargar
            st.session_state['solicitud_actual'] = solicitud
            st.session_state['resultado_energia'] = resultado_energia_res
            st.session_state['racks_viables'] = racks_viables_res
            st.session_state['calculo_realizado'] = True
            st.rerun()

    # ─────────────────────────────────────────────
    # ESTADO: análisis ya ejecutado → mostrar resultados
    # ─────────────────────────────────────────────
    else:
        res_energia = st.session_state['resultado_energia']
        res_racks   = st.session_state['racks_viables']
        espacio_ok  = st.session_state['espacio_aprobado']
        solicitud   = st.session_state['solicitud_actual']
        energia_ok  = (res_energia["PRE-Factibilidad Infraestructura (Si / No)"] == "SI")

        st.markdown("Resultados del análisis de factibilidad técnica.")
        st.markdown("---")

        # ── SECCIÓN 1: ESPACIO FÍSICO ──────────────────
        st.subheader("1. Espacio Físico")

        if espacio_ok:
            st.success(solicitud['Recomendacion_Instalacion_Fisica'])
            if res_racks:
                data_racks = [
                    {
                        "Rack": r['rack'],
                        "Bloques Disponibles": ", ".join(
                            [f"U{b['inicio']}-{b['fin']}" for b in r['bloques']]
                        )
                    }
                    for r in res_racks
                ]
                st.dataframe(pd.DataFrame(data_racks), use_container_width=True, hide_index=True)
        else:
            st.error(solicitud.get('Recomendacion_Instalacion_Fisica', "No hay espacio suficiente."))

        st.markdown("---")

        # ── SECCIÓN 2: ENERGÍA Y PROTECCIONES ─────────
        st.subheader("2. Energía y Protecciones")

        for check in res_energia['Checks']:
            if "[FALLO]" in check or "❌" in check:
                st.error(check)
            elif "[ADVERTENCIA]" in check or "⚠️" in check:
                st.warning(check)
            elif "[OK]" in check or "✅" in check:
                st.success(check)
            else:
                st.info(check)

        st.markdown("---")

        # ── SECCIÓN 3: DICTAMEN FINAL ──────────────────
        st.subheader("3. Dictamen Final")

        if espacio_ok and energia_ok:
            st.success("✅ VIABILIDAD TÉCNICA: APROBADO")
            st.markdown("**Instrucción de Instalación:**")
            st.write(res_energia['Recomendacion_Instalacion'])

            if st.button("📄 Descargar Informe PDF",type="primary"):
                racks_pdf = res_racks if res_racks else []
                exito, ruta = generar_pdf_factibilidad(res_energia, racks_pdf, solicitud)
                if exito:
                    st.success("Informe generado correctamente.")
                    st.code(ruta)
                else:
                    st.error(f"Error generando PDF: {ruta}")
        else:
            st.error("❌ VIABILIDAD TÉCNICA: RECHAZADO")
            st.write("El proyecto no cumple con los criterios técnicos. Revise los resultados anteriores.")

            if st.button("📄 Generar Reporte de Rechazo"):
                racks_pdf = res_racks if res_racks else []
                exito, ruta = generar_pdf_factibilidad(res_energia, racks_pdf, solicitud)
                if exito:
                    st.code(ruta)

        st.markdown("---")

        # Botón para reiniciar y volver a los datos de entrada
        if st.button("🔄 Nueva Evaluación"):
            for key in ['calculo_realizado', 'solicitud_actual', 'resultado_energia',
                        'racks_viables', 'espacio_aprobado']:
                st.session_state.pop(key, None)
            st.rerun()