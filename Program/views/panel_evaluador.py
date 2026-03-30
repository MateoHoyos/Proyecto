"""
panel_evaluador.py — Vista del Evaluador de Pre-Factibilidad
──────────────────────────────────────────────────────────────────────────────
Este módulo es la vista principal del sistema. Permite al usuario seleccionar
una solicitud de instalación de equipo y ejecutar el análisis completo de
pre-factibilidad técnica.

El flujo de la vista tiene dos estados:

    Estado 1 — Vista previa (antes de calcular):
        Muestra los datos del equipo seleccionado (potencia, fuentes, U)
        y el botón para ejecutar el análisis.

    Estado 2 — Vista de resultados (después de calcular):
        Muestra los resultados del análisis físico (espacio en racks)
        y eléctrico (checks de protecciones), el veredicto final
        (APROBADO / RECHAZADO) y el botón para descargar el informe PDF.

Se usa st.session_state para mantener los resultados entre reruns de Streamlit
y detectar cuándo el usuario cambia de solicitud para limpiar el estado anterior.
──────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd

from src.db import get_engine
from src.gestor_solicitudes import obtener_lista_solicitudes, obtener_detalle_solicitud
from src.racks import buscar_espacio_en_racks, verificar_espacio_suelo
from src.analisis_potencia import evaluar_solicitud
from src.reporte_pdf import generar_pdf_factibilidad


def mostrar_vista_evaluador():
    """
    Renderiza la vista del evaluador de pre-factibilidad.

    Gestiona dos estados de la interfaz usando st.session_state:
        'calculo_realizado' : bool que indica si ya se ejecutó el análisis
        'id_anterior'       : ID de la última solicitud procesada
        'resultado_energia' : dict con los checks del análisis eléctrico
        'racks_viables'     : list con los racks disponibles para el equipo
        'espacio_aprobado'  : bool resultado del análisis físico
        'solicitud_procesada': dict completo de la solicitud evaluada
    """
    st.header("Evaluación de Proyecto Nuevo")

    # ── CARGAR LISTA DE SOLICITUDES DESDE LA BD ───────────────────────────
    df_solicitudes = obtener_lista_solicitudes()

    if df_solicitudes.empty:
        st.warning("No hay solicitudes en la base de datos.")
        return

    # Construir las opciones del selectbox con formato: "ID | Equipo | Fecha"
    opciones = df_solicitudes.apply(
        lambda x: f"{x['id_solicitud']} | {x['Equipo']} | {x['fecha_carga']}", axis=1
    )

    # Selectbox para que el usuario elija qué solicitud evaluar
    seleccion = st.selectbox("Seleccione la solicitud a evaluar:", opciones)

    # Extraer el ID numérico de la opción seleccionada
    id_seleccionado = int(seleccion.split("|")[0].strip())

    # ── DETECCIÓN DE CAMBIO DE SOLICITUD ─────────────────────────────────
    # Si el usuario selecciona una solicitud diferente a la anterior,
    # se limpia el resultado del cálculo previo para mostrar los datos
    # frescos del nuevo equipo y el botón de ejecutar nuevamente.
    if 'id_anterior' not in st.session_state:
        st.session_state['id_anterior'] = id_seleccionado

    if st.session_state['id_anterior'] != id_seleccionado:
        st.session_state['calculo_realizado'] = False
        st.session_state['id_anterior']       = id_seleccionado

    # Obtener los detalles completos de la solicitud seleccionada
    solicitud = obtener_detalle_solicitud(id_seleccionado)

    if not solicitud:
        st.error("❌ Error cargando los detalles.")
        return

    # ═════════════════════════════════════════════════════════════════════
    # ESTADO 1 — VISTA PREVIA (antes de ejecutar el análisis)
    # Muestra los datos del equipo para que el usuario los revise
    # antes de lanzar el cálculo.
    # ═════════════════════════════════════════════════════════════════════
    if not st.session_state.get('calculo_realizado'):

        st.info(f"Datos cargados: {solicitud['Equipment']} (ID: {solicitud['ID']})")
        st.markdown("---")
        st.subheader("Datos de Entrada")

        # Mostrar métricas del equipo en columnas para mejor lectura
        st.metric("Equipo", solicitud['Equipment'])

        c1, c2 = st.columns(2)
        c1.metric("Sitio",              solicitud['Technical Site'])
        c2.metric("Cantidad de Equipos", solicitud['Quantity Equipment DC'])

        c2, c3 = st.columns(2)
        c2.metric("Potencia Total",          f"{solicitud['Máx. Power DC (W)']} W")
        c3.metric("Fuentes de Alimentación", solicitud['Power sources'])

        c4, c5 = st.columns(2)
        c4.metric("Voltaje",     solicitud['Voltage(AC or DC)'])
        c5.metric("Disipación:", f"{solicitud.get('BTU_Label', 'N/A')} BTU")

        # Mostrar el tipo de espacio requerido según la solicitud
        if solicitud['Requiere_Rack_Nuevo']:
            st.info(f"Espacio Requerido: {solicitud['Cantidad_Racks_Nuevos']} Racks (Suelo)")
        else:
            st.info(f"Espacio Requerido: {solicitud['U_Requeridas']} U (Rack)")

        st.markdown("---")

        # Expansor opcional para ver todos los datos de la solicitud en JSON
        with st.expander("Ver JSON crudo"):
            st.json(solicitud)

        st.markdown("---")

        # ── BOTÓN DE EJECUCIÓN DEL ANÁLISIS ──────────────────────────────
        if st.button("▶ EJECUTAR ANÁLISIS", type="primary"):
            engine = get_engine()

            with st.spinner("Analizando..."):

                racks_viables_res = []

                # A. ANÁLISIS DE ESPACIO FÍSICO
                # Dos caminos según si el equipo necesita rack nuevo o no:
                if solicitud['Requiere_Rack_Nuevo']:
                    # Caso 1: el equipo necesita rack(s) nuevos en el suelo de la sala
                    suelo_ok, msg_suelo, info_racks = verificar_espacio_suelo(
                        engine, solicitud['Cantidad_Racks_Nuevos'])

                    # Guardar información de distribución de racks para el PDF
                    solicitud['Recomendacion_Instalacion_Fisica']  = msg_suelo
                    solicitud['Racks_Instalados_F1']               = info_racks.get('racks_f1', [])
                    solicitud['Racks_Instalados_F2']               = info_racks.get('racks_f2', [])
                    solicitud['Max_Racks_F1']                      = info_racks.get('max_f1', 6)
                    solicitud['Max_Racks_F2']                      = info_racks.get('max_f2', 10)
                    solicitud['Racks_Nuevos_Propuestos']           = info_racks.get('racks_nuevos', [])
                    st.session_state['espacio_aprobado']           = suelo_ok
                else:
                    # Caso 2: el equipo va en un rack existente, buscar U libres contiguas
                    racks_viables_res = buscar_espacio_en_racks(solicitud["U_Requeridas"])

                    if racks_viables_res:
                        solicitud['Recomendacion_Instalacion_Fisica'] = (
                            f"Rack Sugerido: {racks_viables_res[0]['rack']}")
                        st.session_state['espacio_aprobado'] = True
                    else:
                        st.session_state['espacio_aprobado'] = False

                # B. ANÁLISIS ELÉCTRICO Y DE PROTECCIONES
                # Ejecuta la cadena de validaciones en analisis_potencia.py
                resultado_energia_res = evaluar_solicitud(engine, solicitud)

            # Guardar todos los resultados en session_state para mostrarlos
            # después del rerun de Streamlit sin perder los datos
            st.session_state['solicitud_procesada'] = solicitud
            st.session_state['resultado_energia']   = resultado_energia_res
            st.session_state['racks_viables']       = racks_viables_res
            st.session_state['calculo_realizado']   = True
            st.rerun()  # Recargar la vista para mostrar los resultados

    # ═════════════════════════════════════════════════════════════════════
    # ESTADO 2 — VISTA DE RESULTADOS (después de ejecutar el análisis)
    # Muestra los checks de espacio y energía, el veredicto final
    # y el botón para descargar el informe PDF.
    # ═════════════════════════════════════════════════════════════════════
    else:
        # Recuperar los resultados guardados en session_state
        res_energia   = st.session_state['resultado_energia']
        res_racks     = st.session_state['racks_viables']
        espacio_ok    = st.session_state['espacio_aprobado']
        sol_procesada = st.session_state['solicitud_procesada']
        energia_ok    = (res_energia["PRE-Factibilidad Infraestructura (Si / No)"] == "SI")

        st.success(f"Resultados del análisis para: {sol_procesada['Equipment']}")

        # ── SECCIÓN 1: ESPACIO FÍSICO ─────────────────────────────────────
        st.subheader("1. Espacio Físico")
        if espacio_ok:
            st.success(sol_procesada['Recomendacion_Instalacion_Fisica'])
            # Si hay racks viables, mostrar tabla con los bloques disponibles
            if res_racks:
                data_racks = [{
                    "Rack": r['rack'],
                    "Bloques": ", ".join([f"U{b['inicio']}-{b['fin']}"
                                         for b in r['bloques']])
                } for r in res_racks]
                st.dataframe(pd.DataFrame(data_racks),
                             width=True, hide_index=True)
        else:
            st.error(sol_procesada.get('Recomendacion_Instalacion_Fisica', "Sin espacio."))

        # ── SECCIÓN 2: ENERGÍA Y PROTECCIONES ────────────────────────────
        st.subheader("2. Energía y Protecciones")

        # Mostrar cada check con el color correspondiente a su resultado:
        # FALLO → rojo (error), ADVERTENCIA → amarillo (warning),
        # OK    → verde (success), resto → azul (info)
        for check in res_energia['Checks']:
            if   "[FALLO]"      in check or "❌" in check: st.error(check)
            elif "[ADVERTENCIA]" in check or "⚠️" in check: st.warning(check)
            elif "[OK]"          in check or "✅" in check: st.success(check)
            else:                                            st.info(check)

        st.write("---")

        # ── VEREDICTO FINAL Y DESCARGA DE PDF ────────────────────────────
        if espacio_ok and energia_ok:
            # APROBADO: mostrar instrucción de conexión y botón de PDF
            st.success("✅ VIABILIDAD TÉCNICA: APROBADO")
            st.write(f"**Instrucción:** {res_energia['Recomendacion_Instalacion']}")

            if st.button("📄 Descargar Informe PDF", type="primary"):
                racks_pdf    = res_racks if res_racks else []
                exito, ruta  = generar_pdf_factibilidad(res_energia, racks_pdf, sol_procesada)
                if exito:
                    st.success(f"Generado en: {ruta}")
                else:
                    st.error(f"Error: {ruta}")
        else:
            # RECHAZADO: mostrar botón de reporte de rechazo
            st.error("❌ RECHAZADO")
            if st.button("📄 Reporte de Rechazo"):
                racks_pdf   = res_racks if res_racks else []
                exito, ruta = generar_pdf_factibilidad(res_energia, racks_pdf, sol_procesada)
                if exito:
                    st.success(f"Generado en: {ruta}")

        st.markdown("---")

        # Botón para reiniciar y evaluar una solicitud diferente
        # Limpia el estado del cálculo para volver al Estado 1
        if st.button("🔄 Evaluar otra solicitud"):
            st.session_state['calculo_realizado'] = False
            st.rerun()
