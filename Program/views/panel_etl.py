"""
panel_etl.py — Vista de Gestión de Datos (ETL)
──────────────────────────────────────────────────────────────────────────────
Este módulo presenta la interfaz para ejecutar los tres procesos de carga
de datos del sistema. Está organizado en tres pestañas independientes,
cada una correspondiente a un tipo de fuente de datos distinto.

Pestaña 1 — Carga Manual (Excel):
    Carga los archivos Excel de configuración estática del nodo y los datos
    operativos del DCE hacia MySQL. Se ejecuta cuando hay cambios en el
    inventario físico del nodo (racks, PDB, protecciones).

Pestaña 2 — Sincronización API (DCE):
    Consulta la API REST de Data Center Expert en tiempo real y actualiza
    las tablas operativas (tr_dce, ml_dce, rect_dce). Requiere VPN activa.

Pestaña 3 — ETL Histórico (IF):
    Procesa los archivos CSV del histórico 2025 exportados del DCE y los
    carga en las tablas históricas de MySQL. Estas tablas son la fuente
    de entrenamiento del modelo Isolation Forest.
──────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st

from src.db import inicializar_base_datos_completa
from src.etl import ejecutar_etl_maestro
from src.etl_dce import ejecutar_actualizacion_excel_dce
from src.etl_historico import ejecutar_etl_historico


def mostrar_vista_etl():
    """
    Renderiza la vista de Gestión de Datos con sus tres pestañas.

    Cada pestaña es independiente: el usuario puede ejecutar cualquiera
    de los tres procesos ETL sin afectar a los demás.
    """
    st.header("Gestión de Datos y Sincronización")

    # Crear las tres pestañas de la vista
    tab1, tab2, tab3 = st.tabs([
        "Carga Manual (Excel)",
        "Sincronización API (DCE)",
        "ETL Histórico (IF)"
    ])

    # ─────────────────────────────────────────────────────────
    # PESTAÑA 1 — Carga Manual desde Excel
    # Actualiza las tablas de configuración estática (inventario,
    # protecciones, datos del nodo) y los últimos datos del DCE
    # a partir de los archivos Excel de la carpeta Datos/
    # ─────────────────────────────────────────────────────────
    with tab1:
        st.subheader("Actualizar Base de Datos desde Excel")
        st.write(
            "Carga los archivos `datos_manuales.xlsx` y `datos_DCE.xlsx` "
            "desde la carpeta `Datos/DB` hacia MySQL."
        )

        # Mostrar las tablas que se actualizarán para informar al usuario
        st.caption(
            "Tablas actualizadas: `info_nodo`, `protecciones`, `inventario_dc_pdb`, "
            "`inventario_racks`, `tr_dce`, `ml_dce`, `rect_dce`, `historico_solicitudes`."
        )

        if st.button("▶ Ejecutar ETL Manual", type="primary"):

            # Contenedor dinámico para mostrar el progreso en tiempo real
            log_container = st.empty()
            logs = []

            def log_etl(msg):
                """Agrega un mensaje al log y actualiza el contenedor en pantalla."""
                logs.append(str(msg))
                log_container.code("\n".join(logs), language="text")

            with st.spinner("Procesando Excel..."):
                try:
                    # Asegurar que las tablas existen antes de cargar
                    inicializar_base_datos_completa()
                    # Ejecutar el ETL maestro (etl.py)
                    ejecutar_etl_maestro()
                    log_etl("✅ Base de datos actualizada correctamente.")
                except Exception as e:
                    log_etl(f"❌ Error: {e}")

    # ─────────────────────────────────────────────────────────
    # PESTAÑA 2 — Sincronización en Tiempo Real con la API del DCE
    # Consulta directamente la API REST de Data Center Expert
    # y guarda la lectura actual de cada equipo en el Excel datos_DCE.xlsx,
    # que luego se carga a MySQL con la Pestaña 1.
    # IMPORTANTE: Requiere conexión VPN activa para alcanzar el servidor DCE.
    # ─────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Sincronización en Tiempo Real con Data Center Expert")

        # Aviso de VPN destacado visualmente para recordárselo al usuario
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

        # Campos de credenciales para autenticarse en el servidor DCE
        col1, col2  = st.columns([1, 2])
        usuario     = col1.text_input("Usuario", value="mhoyosme")
        password    = col1.text_input("Contraseña", type="password")

        if st.button("🔄 Iniciar Sincronización API", type="primary"):
            if not password:
                st.warning("Ingrese la contraseña.")
            else:
                with st.spinner("Conectando con DCE..."):
                    try:
                        # Llama a etl_dce.py para consultar la API y guardar en Excel
                        ejecutar_actualizacion_excel_dce(usuario, password)
                        st.success("✅ Datos sincronizados con la API.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    # ─────────────────────────────────────────────────────────
    # PESTAÑA 3 — ETL Histórico para el Modelo Isolation Forest
    # Procesa los CSVs crudos del histórico 2025 (uno por sensor),
    # hace resample a 10 minutos y los carga en las tablas históricas.
    # Este proceso solo se necesita ejecutar una vez (primera configuración)
    # o al incorporar datos de un mes nuevo.
    # ─────────────────────────────────────────────────────────
    with tab3:
        st.subheader("ETL Histórico 2025 — Para Isolation Forest")

        st.info(
            "Este proceso lee los **CSVs crudos por sensor** exportados del DCE "
            "(carpeta `Datos/DCE_DATOS_2025/`), hace resample a **10 minutos** "
            "y los carga en las tablas históricas de MySQL."
        )

        # Mostrar información sobre las tablas generadas y cuándo ejecutar
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

        # Sección expandible para ver el estado actual de las tablas históricas
        # antes de ejecutar el ETL, útil para saber si ya están cargadas
        with st.expander("📊 Ver estado actual de tablas históricas", expanded=False):
            try:
                from src.db import get_engine
                import pandas as pd
                engine = get_engine()
                tablas = ["tr_historico", "ml_historico",
                          "rect1_historico", "rect2_historico"]
                filas_estado = []

                for tabla in tablas:
                    try:
                        # Contar registros y obtener el rango de fechas de cada tabla
                        n     = pd.read_sql(f"SELECT COUNT(*) as n FROM {tabla}",
                                            engine).iloc[0]["n"]
                        rango = pd.read_sql(
                            f"SELECT MIN(timestamp) as desde, MAX(timestamp) as hasta FROM {tabla}",
                            engine
                        )
                        filas_estado.append({
                            "Tabla":     tabla,
                            "Registros": f"{n:,}",
                            "Desde":     str(rango.iloc[0]["desde"])[:10] if n > 0 else "—",
                            "Hasta":     str(rango.iloc[0]["hasta"])[:10] if n > 0 else "—",
                        })
                    except Exception:
                        filas_estado.append({
                            "Tabla": tabla, "Registros": "No existe",
                            "Desde": "—", "Hasta": "—"
                        })

                st.dataframe(pd.DataFrame(filas_estado),
                             use_container_width=True, hide_index=True)
            except Exception as e:
                st.warning(f"No se pudo consultar el estado: {e}")

        st.markdown("---")

        if st.button("▶ Ejecutar ETL Histórico", type="primary"):

            # Contenedor dinámico para mostrar el progreso sensor por sensor
            log_container = st.empty()
            logs = []

            def log_historico(msg):
                """Agrega un mensaje al log y actualiza el contenedor en pantalla."""
                logs.append(str(msg))
                log_container.code("\n".join(logs), language="text")

            # Este proceso puede tardar 1-2 minutos dependiendo del volumen de CSVs
            with st.spinner("Procesando CSVs históricos... (puede tardar 1-2 minutos)"):
                try:
                    totales = ejecutar_etl_historico(log_fn=log_historico)
                    total   = sum(totales.values())

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
