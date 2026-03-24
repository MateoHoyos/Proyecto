"""
panel_inicio.py — Vista de Inicio del Sistema IDEO
──────────────────────────────────────────────────────────────────────────────
Este módulo muestra la pantalla principal de la aplicación.

Cumple dos funciones:
    1. Verificar y mostrar el estado de la conexión a la base de datos MySQL.
    2. Mostrar el tablero de Power BI embebido con el estado actual del nodo
       IDEO Cali (voltajes, corrientes, temperatura, ocupación de racks).

El tablero de Power BI se integra mediante un iframe HTML, lo que permite
visualizar los datos actualizados del nodo sin salir de la aplicación.
──────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
from src.db import get_engine


def mostrar_vista_inicio():
    """
    Renderiza la vista de inicio de la aplicación.

    Al cargar esta vista, intenta conectarse a MySQL para verificar
    que el sistema está operativo. Muestra un mensaje de ONLINE o ERROR
    según el resultado de la conexión.

    Luego muestra el tablero de Power BI embebido mediante un iframe,
    que presenta el estado eléctrico y operativo actual del nodo en tiempo real.
    """

    # ── VERIFICACIÓN DE CONEXIÓN A LA BASE DE DATOS ───────────────────────
    # Se intenta abrir una conexión a MySQL. Si tiene éxito, el sistema
    # está operativo. Si falla, se muestra el error para diagnóstico.
    try:
        engine = get_engine()
        with engine.connect() as conn:
            st.success("Estado del Sistema: ONLINE (Base de Datos Conectada)")
    except Exception as e:
        st.error(f"Estado del Sistema: ERROR DE CONEXIÓN ({e})")

    # Título y separador de la sección principal
    st.header("Estado Actual del Sitio")
    st.markdown("---")

    # ── TABLERO DE POWER BI EMBEBIDO ──────────────────────────────────────
    # Se integra el tablero de Power BI publicado en la nube mediante un iframe.
    # Este tablero muestra en tiempo real los datos del nodo IDEO Cali:
    #   - Voltajes y corrientes AC/DC
    #   - Temperatura de la sala
    #   - Ocupación de racks
    #   - Histórico de mediciones
    #
    # La URL corresponde al reporte publicado en el espacio de trabajo de
    # Power BI de la Gerencia de Infraestructura de Tigo.
    url_pbi = (
        "https://app.powerbi.com/view?r=eyJrIjoiMDcyN2U4OTAtNTI1Mi00ZTc2LTk1ZDYt"
        "ZmQ3NmQ4ZjM0N2QyIiwidCI6IjY1MDAzOWZkLTcxMmEtNGZlMS1iODYzLTg2MTAzYzQy"
        "NWMxNyIsImMiOjh9&embedImagePlaceholder=true&pageName=6e420c6053b596a1eaad"
    )

    # Se construye el HTML del iframe con ancho 100% para adaptarse
    # al contenedor de Streamlit y altura fija de 600px
    iframe_html = f"""
    <iframe
        title="Tablero_IDEO"
        width="100%"
        height="600"
        src="{url_pbi}"
        frameborder="0"
        allowFullScreen="true">
    </iframe>
    """

    # unsafe_allow_html=True es necesario para que Streamlit renderice el iframe
    st.markdown(iframe_html, unsafe_allow_html=True)
