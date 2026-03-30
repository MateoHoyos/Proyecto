import streamlit as st
import sys
import os
import base64

# Configuración de rutas
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Importar las vistas
from views.panel_inicio import mostrar_vista_inicio
from views.panel_etl import mostrar_vista_etl
from views.panel_evaluador import mostrar_vista_evaluador
from views.panel_alarmas import mostrar_vista_alarmas

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
img_Designer = BASE_DIR.parent / "docs" / "img" / "Designer.png"

# Configuración de página
st.set_page_config(page_title="Sistema IDEO", layout="wide", page_icon="🧊") #🗄️🏢

def img_a_base64(ruta):
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Menú
with st.sidebar:
    st.image(img_Designer, width=250) 
    #st.title("Sistema IDEO")
    
    # MENÚ SIMPLIFICADO
    opcion = st.radio(
        "Navegación", 
        [
            "Inicio", 
            "Gestión de Datos (ETL)", 
            "Evaluador de Pre-Factibilidad",
            "Monitor de Alarmas"  
        ]
    )
    st.markdown("---")

    url_sharepoint = "https://millicom.sharepoint.com/sites/Modeladodeinfraestructuradelosnodos"
    #st.link_button("📂 Ver Sitio de SharePoint", url_sharepoint)

    logo_b64 = img_a_base64("src/assets/SharePoint_logo.png")

    st.markdown(f"""
        <div style="text-align:center; margin-top:8px;">
            <a href="{url_sharepoint}" target="_blank" style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background-color: #e8ebed;
                color: black;
                padding: 8px 16px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 0.875rem;
                font-weight: 500;
            ">
                <img src="data:image/png;base64,{logo_b64}" width="20" height="20"
                    style="vertical-align:middle;">
                Ver Sitio de SharePoint
            </a>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    with open("src/assets/logo.png", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    
    st.markdown(f"""
        <div style="display:flex; justify-content:center; margin-bottom:16px;">
            <img src="data:image/png;base64,{logo_b64}" width="80">
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="text-align:center; font-size:12px; color: #9aa0a6;">
        <b>Versión 1.0</b><br>
        Gerencia Infraestructura
        </div>
    """, unsafe_allow_html=True)

if opcion == "Inicio":
    mostrar_vista_inicio()

elif opcion == "Gestión de Datos (ETL)":
    mostrar_vista_etl()

elif opcion == "Evaluador de Pre-Factibilidad":
    mostrar_vista_evaluador()

elif opcion == "Monitor de Alarmas":
        mostrar_vista_alarmas()