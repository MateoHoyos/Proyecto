import streamlit as st
import pandas as pd
from src.db import get_engine
from src.gestor_solicitudes import obtener_lista_solicitudes, obtener_detalle_solicitud
from src.racks import buscar_espacio_en_racks, verificar_espacio_suelo
from src.analisis_potencia import evaluar_solicitud
from src.reporte_pdf import generar_pdf_factibilidad


def mostrar_vista_evaluador():
    st.header("Evaluación de Proyecto Nuevo")

    # 1. CARGAR LISTA DESDE BD
    df_solicitudes = obtener_lista_solicitudes()

    if df_solicitudes.empty:
        st.warning("No hay solicitudes en la base de datos.")
        return

    # Crear lista para el selectbox
    opciones = df_solicitudes.apply(
        lambda x: f"{x['id_solicitud']} | {x['Equipo']} | {x['fecha_carga']}", axis=1
    )
    
    # Selectbox
    seleccion = st.selectbox("Seleccione la solicitud a evaluar:", opciones)
    
    # Extraer ID
    id_seleccionado = int(seleccion.split("|")[0].strip())

    # --- LÓGICA DE REINICIO (EL ARREGLO) ---
    # Si el usuario cambió de opción en la lista, borramos el cálculo anterior
    # para que se actualicen las métricas y aparezca el botón de ejecutar de nuevo.
    if 'id_anterior' not in st.session_state:
        st.session_state['id_anterior'] = id_seleccionado

    if st.session_state['id_anterior'] != id_seleccionado:
        st.session_state['calculo_realizado'] = False
        st.session_state['id_anterior'] = id_seleccionado
        # No usamos st.rerun() aquí para dejar que fluya y cargue los datos nuevos abajo

    # 2. OBTENER DETALLES FRESCOS DE LA BD
    solicitud = obtener_detalle_solicitud(id_seleccionado)

    #print("\n",solicitud,"\n")

    if not solicitud:
        st.error("❌ Error cargando los detalles.")
        return

    # ─────────────────────────────────────────────
    # VISTA PREVIA (MÉTRICAS) - SIEMPRE VISIBLE ANTES DE CALCULAR
    # ─────────────────────────────────────────────
    if not st.session_state.get('calculo_realizado'):
        st.info(f"Datos cargados: {solicitud['Equipment']} (ID: {solicitud['ID']})")
        st.markdown("---")
        st.subheader("Datos de Entrada")
        
        st.metric("Equipo", solicitud['Equipment'])

        c1, c2 = st.columns(2)
        c1.metric("Sitio", solicitud['Technical Site'])
        c2.metric("Cantidad de Equipos", solicitud['Quantity Equipment DC'])

        c2, c3 = st.columns(2)
        c2.metric("Potencia Total", f"{solicitud['Máx. Power DC (W)']} W")
        c3.metric("Fuentes de Alimentación", solicitud['Power sources'])

        c4, c5 = st.columns(2)
        c4.metric("Voltaje", solicitud['Voltage(AC or DC)'])
        c5.metric("Disipación: ", f"{solicitud.get('BTU_Label', 'N/A')} BTU")
        


        if solicitud['Requiere_Rack_Nuevo']:
            st.info(f"Espacio Requerido: {solicitud['Cantidad_Racks_Nuevos']} Racks (Suelo)")
        else:
            st.info(f"Espacio Requerido: {solicitud['U_Requeridas']} U (Rack)")
        
        st.markdown("---")

        with st.expander("Ver JSON crudo"):
            st.json(solicitud)

        st.markdown("---")

        # BOTÓN DE EJECUCIÓN
        if st.button("▶ EJECUTAR ANÁLISIS", type="primary"):
            engine = get_engine()
            with st.spinner("Analizando..."):
                # A. Espacio
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

            # Guardar en sesión
            st.session_state['solicitud_procesada'] = solicitud # Guardamos copia exacta de lo procesado
            st.session_state['resultado_energia'] = resultado_energia_res
            st.session_state['racks_viables'] = racks_viables_res
            st.session_state['calculo_realizado'] = True
            st.rerun()

    # ─────────────────────────────────────────────
    # VISTA RESULTADOS (DESPUÉS DE CALCULAR)
    # ─────────────────────────────────────────────
    else:
        # Recuperar variables
        res_energia = st.session_state['resultado_energia']
        res_racks = st.session_state['racks_viables']
        espacio_ok = st.session_state['espacio_aprobado']
        sol_procesada = st.session_state['solicitud_procesada']
        energia_ok = (res_energia["PRE-Factibilidad Infraestructura (Si / No)"] == "SI")

        st.success(f"Resultados del análisis para: {sol_procesada['Equipment']}")
        
        st.subheader("1. Espacio Físico")
        if espacio_ok:
            st.success(sol_procesada['Recomendacion_Instalacion_Fisica'])
            if res_racks:
                data_racks = [{"Rack": r['rack'], "Bloques": ", ".join([f"U{b['inicio']}-{b['fin']}" for b in r['bloques']])} for r in res_racks]
                st.dataframe(pd.DataFrame(data_racks), use_container_width=True, hide_index=True)
        else:
            st.error(sol_procesada.get('Recomendacion_Instalacion_Fisica', "Sin espacio."))

        st.subheader("2. Energía y Protecciones")
        for check in res_energia['Checks']:
            if "[FALLO]" in check or "❌" in check: st.error(check)
            elif "[ADVERTENCIA]" in check or "⚠️" in check: st.warning(check)
            elif "[OK]" in check or "✅" in check: st.success(check)
            else: st.info(check)

        st.write("---")
        
        # Dictamen
        if espacio_ok and energia_ok:
            st.success("✅ VIABILIDAD TÉCNICA: APROBADO")
            st.write(f"**Instrucción:** {res_energia['Recomendacion_Instalacion']}")
            
            if st.button("📄 Descargar Informe PDF", type="primary"):
                racks_pdf = res_racks if res_racks else []
                exito, ruta = generar_pdf_factibilidad(res_energia, racks_pdf, sol_procesada)
                if exito:
                    st.success(f"Generado en: {ruta}")
                    
                else:
                    st.error(f"Error: {ruta}")
        else:
            st.error("❌ RECHAZADO")
            if st.button("📄 Reporte de Rechazo"):
                racks_pdf = res_racks if res_racks else []
                exito, ruta = generar_pdf_factibilidad(res_energia, racks_pdf, sol_procesada)
                if exito:
                    st.success(f"Generado en: {ruta}")
                    

        st.markdown("---")
        if st.button("🔄 Evaluar otra solicitud"):
            st.session_state['calculo_realizado'] = False
            st.rerun()