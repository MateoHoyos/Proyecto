import streamlit as st
from src.lector_excel import leer_ultima_solicitud

def mostrar_vista_datos():
    st.header("Datos de la Última Solicitud")
    solicitud = leer_ultima_solicitud()
    
    if solicitud:
        c1, c2, c3 = st.columns(3)
        c1.metric("Equipo", solicitud['Equipment'])
        c2.metric("Potencia Total", f"{solicitud['Máx. Power DC (W)'] * solicitud['Quantity Equipment DC']} W")
        c3.metric("Voltaje", solicitud['Voltage(AC or DC)'])
        st.info(f"Disipación: {solicitud.get('BTU_Label')}")
        with st.expander("Ver JSON completo"):
            st.json(solicitud)
    else:
        st.error("No se pudo leer el archivo Excel.")