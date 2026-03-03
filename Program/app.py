import streamlit as st
import streamlit.components.v1 as components
import sys
import os

# Configuración de rutas
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Importar las vistas
from views.inicio import mostrar_vista_inicio
from views.panel_etl import mostrar_vista_etl
from views.evaluador import mostrar_vista_evaluador

# Configuración de página
st.set_page_config(page_title="Sistema IDEO", layout="wide", page_icon="🧊") #🗄️🏢


# Sidebar (Menú)
with st.sidebar:
    st.image("C:/Users/mhoyosme/Desktop/Proyecto/Archivos/img/Designer.png", width=250) 
    st.title("Sistema IDEO")
    
    # MENÚ SIMPLIFICADO
    opcion = st.radio(
        "Navegación", 
        [
            "Inicio", 
            "Gestión de Datos (ETL)", 
            "Evaluador de Factibilidad" # Esta opción ahora hace todo
        ]
    )
    st.markdown("---")
    st.caption("v1.0")

# Router
if opcion == "Inicio":
    mostrar_vista_inicio()

elif opcion == "Gestión de Datos (ETL)":
    mostrar_vista_etl()

elif opcion == "Evaluador de Factibilidad":
    mostrar_vista_evaluador() 


