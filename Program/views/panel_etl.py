import streamlit as st

from src.db import inicializar_base_datos_completa
from src.etl import ejecutar_etl_maestro
from src.etl_dce import ejecutar_actualizacion_excel_dce
from src.etl_historico import ejecutar_etl_historico

"""
panel_etl.py — Vista Streamlit de Gestión de Datos
Tres pestañas:
  1. Carga Manual (Excel)         → datos manuales + DCE operativos
  2. Sincronización API (DCE)     → tiempo real vía API
  3. ETL Histórico (Isolation Forest) → CSVs crudos → tablas históricas
"""

''' def mostrar_vista_etl():
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
'''

def mostrar_vista_etl():
    st.header("Gestión de Datos y Sincronización")

    tab1, tab2, tab3 = st.tabs([
        "Carga Manual (Excel)",
        "Sincronización API (DCE)",
        "ETL Histórico (IF)"
    ])

    # ─────────────────────────────────────────────────────────
    # TAB 1 — Carga Manual
    # ─────────────────────────────────────────────────────────
    with tab1:
        st.subheader("Actualizar Base de Datos desde Excel")
        st.write(
            "Carga los archivos `datos_manuales.xlsx` y `datos_DCE.xlsx` "
            "desde la carpeta `Datos/DB` hacia MySQL."
        )
        st.caption(
            "Tablas actualizadas: `info_nodo`, `protecciones`, `inventario_dc_pdb`, "
            "`inventario_racks`, `tr_dce`, `ml_dce`, `rect_dce`, `historico_solicitudes`."
        )

        if st.button("▶ Ejecutar ETL Manual", type="primary"):
            log_container = st.empty()
            logs = []

            def log_etl(msg):
                logs.append(str(msg))
                log_container.code("\n".join(logs), language="text")

            with st.spinner("Procesando Excel..."):
                try:
                    inicializar_base_datos_completa()
                    ejecutar_etl_maestro()
                    log_etl("✅ Base de datos actualizada correctamente.")
                except Exception as e:
                    log_etl(f"❌ Error: {e}")

    # ─────────────────────────────────────────────────────────
    # TAB 2 — Sincronización API
    # ─────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Sincronización en Tiempo Real con Data Center Expert")

        st.markdown("""
            <div style="background:#fff3cd;color:#856404;padding:10px;
            border-radius:6px;border-left:5px solid #ffc107;font-size:14px;">
            ⚠️ Recuerde conectar la VPN antes de sincronizar.
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.write(
            "Consulta la API de DCE y guarda la **última lectura** de TR, ML, "
            "Rect1 y Rect2 en las tablas operativas (`tr_dce`, `ml_dce`, `rect_dce`)."
        )

        col1, col2 = st.columns([1, 2])
        usuario  = col1.text_input("Usuario", value="mhoyosme")
        password = col1.text_input("Contraseña", type="password")

        if st.button("🔄 Iniciar Sincronización API", type="primary"):
            if not password:
                st.warning("Ingrese la contraseña.")
            else:
                with st.spinner("Conectando con DCE..."):
                    try:
                        ejecutar_actualizacion_excel_dce(usuario, password)
                        st.success("✅ Datos sincronizados con la API.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    # ─────────────────────────────────────────────────────────
    # TAB 3 — ETL Histórico
    # ─────────────────────────────────────────────────────────
    with tab3:
        st.subheader("ETL Histórico 2025 — Para Isolation Forest")

        st.info(
            "Este proceso lee los **CSVs crudos por sensor** exportados del DCE "
            "(carpeta `Datos/DCE_DATOS_2025/`), hace resample a **10 minutos** "
            "y los carga en las tablas históricas de MySQL."
        )

        col_a, col_b = st.columns(2)
        col_a.markdown("""
        **Tablas que genera:**
        - `tr_historico`
        - `ml_historico`
        - `rect1_historico`
        - `rect2_historico`
        """)
        col_b.markdown("""
        **Cuándo ejecutar:**
        - Primera vez que se configura el sistema
        - Al incorporar datos de un mes nuevo
        - Antes de reentrenar el Isolation Forest
        """)

        st.markdown("---")

        # Estado actual de las tablas históricas
        with st.expander("📊 Ver estado actual de tablas históricas", expanded=False):
            try:
                from src.db import get_engine
                import pandas as pd
                engine = get_engine()
                tablas = ["tr_historico", "ml_historico", "rect1_historico", "rect2_historico"]
                filas_estado = []
                for tabla in tablas:
                    try:
                        n = pd.read_sql(f"SELECT COUNT(*) as n FROM {tabla}", engine).iloc[0]["n"]
                        rango = pd.read_sql(
                            f"SELECT MIN(timestamp) as desde, MAX(timestamp) as hasta FROM {tabla}", engine
                        )
                        filas_estado.append({
                            "Tabla":     tabla,
                            "Registros": f"{n:,}",
                            "Desde":     str(rango.iloc[0]["desde"])[:10] if n > 0 else "—",
                            "Hasta":     str(rango.iloc[0]["hasta"])[:10] if n > 0 else "—",
                        })
                    except Exception:
                        filas_estado.append({"Tabla": tabla, "Registros": "No existe", "Desde": "—", "Hasta": "—"})

                st.dataframe(pd.DataFrame(filas_estado), use_container_width=True, hide_index=True)
            except Exception as e:
                st.warning(f"No se pudo consultar el estado: {e}")

        st.markdown("---")

        if st.button("▶ Ejecutar ETL Histórico", type="primary"):
            log_container = st.empty()
            logs = []

            def log_historico(msg):
                logs.append(str(msg))
                log_container.code("\n".join(logs), language="text")

            with st.spinner("Procesando CSVs históricos... (puede tardar 1-2 minutos)"):
                try:
                    totales = ejecutar_etl_historico(log_fn=log_historico)
                    total = sum(totales.values())
                    if total > 0:
                        st.success(
                            f"✅ ETL histórico completado: {total:,} registros cargados. "
                            f"Ya puede entrenar el Isolation Forest desde el Monitor de Alarmas."
                        )
                    else:
                        st.warning(
                            "⚠️ No se cargaron registros. "
                            "Verifique que la carpeta `Datos/DCE_DATOS_2025/` exista "
                            "y contenga los CSVs por sensor."
                        )
                except Exception as e:
                    st.error(f"❌ Error durante el ETL histórico: {e}")
                    st.info("Revise que la ruta `Datos/DCE_DATOS_2025/` sea correcta en `etl_historico.py`.")