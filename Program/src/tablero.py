import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from src.config import DB_CONFIG

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Monitor IDEO CALI", layout="wide", page_icon="⚡")

# --- CONEXIÓN BASE DE DATOS ---
@st.cache_resource # Cache para no reconectar a cada clic
def get_db_connection():
    conn_str = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
    return create_engine(conn_str)

engine = get_db_connection()

# --- TÍTULO ---
st.title("⚡ Tablero de Control - Nodo IDEO CALI")
st.markdown("Visión unificada de Transformador, ML y Rectificadores")

# --- SECCIÓN 1: ÚLTIMO ESTADO (KPIs) ---
st.header("1. Estado Actual del Sitio")

# Consultas para obtener el último dato disponible
with engine.connect() as conn:
    # TR
    sql_tr = "SELECT * FROM bitacora_tr_excel ORDER BY fecha DESC LIMIT 1"
    df_tr = pd.read_sql(sql_tr, conn)
    
    # ML
    sql_ml = "SELECT * FROM bitacora_ml_excel ORDER BY fecha DESC LIMIT 1"
    df_ml = pd.read_sql(sql_ml, conn)
    
    # Rectificadores
    sql_rect = "SELECT * FROM bitacora_rectificadores_excel ORDER BY fecha DESC LIMIT 2"
    df_rect = pd.read_sql(sql_rect, conn)

# Métricas Principales (Fila 1)
col1, col2, col3, col4 = st.columns(4)

if not df_tr.empty:
    potencia_tr = df_tr.iloc[0]['potencia_aparente_kva']
    voltaje_tr = df_tr.iloc[0]['voltaje_ac_l1_l2']
    col1.metric("Carga Transformador", f"{potencia_tr} kVA", help="Capacidad Max: 75 kVA")
    col2.metric("Voltaje Red (L1-L2)", f"{voltaje_tr} V")

if not df_ml.empty:
    temp_sala = df_ml.iloc[0]['temp_sala_s01']
    corriente_ml = df_ml.iloc[0]['corriente_ac_r']
    col3.metric("Temperatura Sala", f"{temp_sala} °C", delta_color="inverse")
    col4.metric("Corriente Fase R (ML)", f"{corriente_ml} A")

st.markdown("---")

# --- SECCIÓN 2: DETALLE RECTIFICADORES ---
st.header("2. Estado de Rectificadores y Baterías")

col_r1, col_r2 = st.columns(2)

# Separar datos por rectificador
r1 = df_rect[df_rect['rectificador_id'] == 1].iloc[0] if not df_rect.empty else None
r2 = df_rect[df_rect['rectificador_id'] == 2].iloc[0] if len(df_rect) > 1 else None

with col_r1:
    st.subheader("Rectificador 1")
    if r1 is not None:
        st.write(f"**Estado:** {r1['estado_sistema']}")
        st.write(f"**Modo:** {r1['modo_sistema']}")
        # Barra de progreso de carga
        st.progress(int(r1['porcentaje_carga']))
        st.caption(f"Carga: {r1['porcentaje_carga']}% ({r1['corriente_dc_total']} A)")
        
        st.metric("Temp. Baterías", f"{r1['temp_baterias']} °C")
        st.metric("Módulos Activos", f"{int(r1['modulos_instalados'])}")
    else:
        st.warning("Sin datos")

with col_r2:
    st.subheader("Rectificador 2")
    if r2 is not None:
        st.write(f"**Estado:** {r2['estado_sistema']}")
        st.write(f"**Modo:** {r2['modo_sistema']}")
        st.progress(int(r2['porcentaje_carga']))
        st.caption(f"Carga: {r2['porcentaje_carga']}% ({r2['corriente_dc_total']} A)")
        
        st.metric("Temp. Baterías", f"{r2['temp_baterias']} °C")
        st.metric("Módulos Activos", f"{int(r2['modulos_instalados'])}")
    else:
        st.warning("Sin datos")

st.markdown("---")

# --- SECCIÓN 3: ANÁLISIS HISTÓRICO (Tus datos masivos) ---
st.header("3. Tendencias Históricas")

tab1, tab2 = st.tabs(["Voltaje AC (Red)", "Consumo DC (Rectificadores)"])

with tab1:
    st.subheader("Estabilidad de Voltaje AC")
    # Traemos datos históricos reales (remuestreados)
    df_hist_tr = pd.read_sql("SELECT timestamp, voltaje_ac_l1_l2, voltaje_ac_l2_l3, voltaje_ac_l3_l1 FROM tr_historico ORDER BY timestamp DESC LIMIT 5000", engine)
    
    if not df_hist_tr.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_hist_tr['timestamp'], y=df_hist_tr['voltaje_ac_l1_l2'], name="L1-L2", line=dict(color='red', width=1)))
        fig.add_trace(go.Scatter(x=df_hist_tr['timestamp'], y=df_hist_tr['voltaje_ac_l2_l3'], name="L2-L3", line=dict(color='blue', width=1)))
        fig.add_trace(go.Scatter(x=df_hist_tr['timestamp'], y=df_hist_tr['voltaje_ac_l3_l1'], name="L3-L1", line=dict(color='green', width=1)))
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Carga Total DC")
    df_hist_r1 = pd.read_sql("SELECT timestamp, corriente_total_dc FROM rect1_historico ORDER BY timestamp DESC LIMIT 5000", engine)
    df_hist_r2 = pd.read_sql("SELECT timestamp, corriente_total_dc FROM rect2_historico ORDER BY timestamp DESC LIMIT 5000", engine)
    
    if not df_hist_r1.empty:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_hist_r1['timestamp'], y=df_hist_r1['corriente_total_dc'], name="Rectificador 1", fill='tozeroy'))
        fig2.add_trace(go.Scatter(x=df_hist_r2['timestamp'], y=df_hist_r2['corriente_total_dc'], name="Rectificador 2", fill='tozeroy'))
        fig2.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig2, use_container_width=True)

# --- PIE DE PÁGINA ---
st.sidebar.markdown("---")
st.sidebar.info("Sistema desarrollado para Tesis UdeA")
if st.sidebar.button("🔄 Refrescar Datos"):
    st.cache_resource.clear()