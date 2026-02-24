import streamlit as st
# Nota el 'src.' antes de db
from src.db import get_engine, inicializar_base_datos_completa


def mostrar_vista_inicio():
    st.info("Bienvenido al Sistema de Gestión de Capacidad.")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            st.success("✅ Estado del Sistema: ONLINE (Base de Datos Conectada)")
    except Exception as e:
        st.error(f"❌ Estado del Sistema: ERROR DE CONEXIÓN ({e})")