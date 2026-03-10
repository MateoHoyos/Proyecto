import streamlit as st
from src.db import get_engine

def mostrar_vista_inicio():
    st.info("Bienvenido al Sistema de Prefactibilidad.")
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            st.success("Estado del Sistema: ONLINE (Base de Datos Conectada)")
    except Exception as e:
        st.error(f"Estado del Sistema: ERROR DE CONEXIÓN ({e})")

    # Título principal
    st.header("Estado Actual del Sitio")
    st.markdown("---")
    
    # 1. INTEGRACIÓN POWER BI
    url_pbi = "https://app.powerbi.com/view?r=eyJrIjoiMDcyN2U4OTAtNTI1Mi00ZTc2LTk1ZDYtZmQ3NmQ4ZjM0N2QyIiwidCI6IjY1MDAzOWZkLTcxMmEtNGZlMS1iODYzLTg2MTAzYzQyNWMxNyIsImMiOjh9&embedImagePlaceholder=true&pageName=6e420c6053b596a1eaad"
    # Código HTML del iframe (Ajustado a width=100% y height=600px para mejor visualización)
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
    # Renderizar el iframe
    st.markdown(iframe_html, unsafe_allow_html=True)
