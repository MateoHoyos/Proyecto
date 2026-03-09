import streamlit as st
from src.db import inicializar_base_datos_completa
from src.etl import ejecutar_etl_maestro
from src.etl_dce import ejecutar_actualizacion_excel_dce

def mostrar_vista_etl():
    st.header("Gestión de Datos y Sincronización")
    
    tab1, tab2 = st.tabs(["Carga Manual (Excel)", "Sincronización API (DCE)"])
    
    with tab1:
        st.write("Actualiza la base de datos con los archivos Excel de la carpeta `Datos/DB`.")
        if st.button("Ejecutar ETL Manual"):
            with st.spinner("Procesando..."):
                try:
                    inicializar_base_datos_completa()
                    ejecutar_etl_maestro()
                    st.success("✅ Base de datos actualizada.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab2:
        st.write("Conexión en tiempo real con Data Center Expert.")

        #st.info(f"Recuerde conectar la VPN")
        st.markdown("""
            <div style="
            background-color:#fff3cd;
            color:#856404;
            padding:10px;
            border-radius:6px;
            border-left:5px solid #ffc107;
            font-size:14px;">
            ⚠️ Recuerde conectar la VPN
            </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        col1, col2 = st.columns([1, 2])
        usuario = col1.text_input("Usuario", value="mhoyosme")
        password = col1.text_input("Contraseña", type="password")
        
        if st.button("Iniciar Sincronización API"):
            if not password:
                st.warning("Ingrese contraseña.")
            else:
                with st.spinner("Conectando..."):
                    try:
                        ejecutar_actualizacion_excel_dce(usuario, password)
                        st.success("✅ Datos sincronizados con la API.")
                    except Exception as e:
                        st.error(f"Error: {e}")