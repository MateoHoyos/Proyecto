import streamlit as st
import sys
import os

# Configuración de rutas
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Importar las vistas
from views.inicio import mostrar_vista_inicio
from views.panel_etl import mostrar_vista_etl
from views.visor_datos import mostrar_vista_datos
from views.evaluador import mostrar_vista_evaluador

# Configuración de página
st.set_page_config(page_title="Sistema IDEO", layout="wide", page_icon="⚡")

# Sidebar (Menú)
with st.sidebar:
    st.title("⚡ IDEO Manager")
    opcion = st.radio(
        "Navegación", 
        ["Inicio", "Datos de Entrada", "Gestión de Datos (ETL)", "Evaluador de Factibilidad"]
    )
    st.markdown("---")

# Router (Enrutador de Vistas)
if opcion == "Inicio":
    mostrar_vista_inicio()

elif opcion == "Datos de Entrada":
    mostrar_vista_datos()

elif opcion == "Gestión de Datos (ETL)":
    mostrar_vista_etl()

elif opcion == "Evaluador de Factibilidad":
    mostrar_vista_evaluador()