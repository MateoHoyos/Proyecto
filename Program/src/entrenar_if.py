"""
panel_alarmas.py — Vista Streamlit del Monitor de Alarmas IDEO
──────────────────────────────────────────────────────────────────────────────
Este módulo implementa la interfaz gráfica del sistema de alarmas del nodo
IDEO CALI. Muestra en tiempo real el estado eléctrico y térmico del nodo,
detecta anomalías mediante dos capas complementarias de análisis y permite
enviar notificaciones por email cuando se detectan condiciones fuera de rango.

CAPA 1 — Validación de Umbrales Técnicos:
    Compara cada variable medida contra límites fijos definidos por el equipo
    de ingeniería (voltajes, corrientes, temperaturas, factores de potencia).
    Clasifica las violaciones en ADVERTENCIA o CRÍTICO según la gravedad.

CAPA 2 — Detección de Anomalías con Isolation Forest:
    Evalúa la lectura actual contra el modelo entrenado con el histórico 2025
    (ver entrenar_if.py). Detecta combinaciones inusuales de variables que
    no violarían umbrales individuales pero que en conjunto son anómalas.
    Genera un score 0–100 e identifica las variables más desviadas.

Integración con app.py:
    from views.panel_alarmas import mostrar_vista_alarmas

    # En el sidebar — agregar opción al radio de navegación:
    opcion = st.radio("Navegación", [
        "Inicio",
        "Gestión de Datos (ETL)",
        "Evaluador de Factibilidad",
        "Monitor de Alarmas"          ← agregar esta línea
    ])

    # En el router de vistas:
    elif opcion == "Monitor de Alarmas":
        mostrar_vista_alarmas()

Dependencias internas:
    src.db         → get_engine()              conexión MySQL
    src.alarmas    → evaluar_alarmas_completo() lógica de evaluación
                   → enviar_email_alarma()      notificación SMTP

Flujo de ejecución (botón "Verificar Alarmas Ahora"):
    MySQL (última lectura) → evaluar_alarmas_completo()
    → Capa 1: umbrales técnicos
    → Capa 2: Isolation Forest (si modelo disponible)
    → Renderizado en Streamlit + opción de envío de email
──────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import os, sys
import pickle

from src.db import get_engine
from src.alarmas import evaluar_alarmas_completo, enviar_email_alarma


# ─────────────────────────────────────────────────────────────
#  HELPERS DE UI
#  Funciones auxiliares para renderizar componentes visuales
#  reutilizables a lo largo del panel.
# ─────────────────────────────────────────────────────────────

def _badge_nivel(nivel: str) -> str:
    """
    Genera un badge HTML coloreado que representa el nivel de alerta global.

    Parámetros:
        nivel (str): "CRITICO", "ADVERTENCIA" u "OK"

    Retorna:
        str: HTML inline del badge con icono, color de fondo y borde.
             Listo para usar con st.markdown(..., unsafe_allow_html=True).
    """
    config = {
        "CRITICO":     ("🔴", "#C0392B", "#FADBD8"),
        "ADVERTENCIA": ("🟡", "#D35400", "#FDEBD0"),
        "OK":          ("🟢", "#1E8449", "#D5F5E3"),
    }
    icono, color_texto, color_bg = config.get(nivel, ("⚪", "#888", "#eee"))
    return (
        f"<div style='display:inline-block;background:{color_bg};color:{color_texto};"
        f"padding:6px 18px;border-radius:20px;font-weight:bold;font-size:16px;"
        f"border:2px solid {color_texto}'>{icono} {nivel}</div>"
    )


def _tarjeta_lectura(label: str, valor, unidad: str = "", color: str = "#2C3E50"):
    """
    Renderiza una tarjeta de métrica individual con borde de color temático.

    Cada tarjeta muestra una variable eléctrica o térmica con su etiqueta
    y unidad. El color del borde izquierdo indica el subsistema al que
    pertenece (azul=voltaje, azul oscuro=corriente, naranja=temperatura, etc.).

    Parámetros:
        label (str):  Nombre descriptivo de la variable (ej. "Voltaje L1-L2").
        valor:        Valor numérico o string a mostrar.
        unidad (str): Unidad de medida (ej. "V", "A", "°C", "kVA").
        color (str):  Color hex para el borde izquierdo y el texto del valor.
    """
    val_str = f"{valor:.2f} {unidad}" if isinstance(valor, (int, float)) else str(valor)
    st.markdown(
        f"""<div style='background:#F2F4F7;border-left:4px solid {color};
        padding:10px 14px;border-radius:6px;margin-bottom:4px'>
        <div style='font-size:11px;color:#7F8C8D'>{label}</div>
        <div style='font-size:18px;font-weight:bold;color:{color}'>{val_str}</div>
        </div>""",
        unsafe_allow_html=True
    )


def _seccion_header(titulo: str):
    """
    Renderiza un encabezado de sección con fondo azul oscuro corporativo.

    Parámetros:
        titulo (str): Texto del encabezado de sección.
    """
    st.markdown(
        f"<div style='background:#1A5276;color:white;padding:8px 14px;"
        f"border-radius:6px;font-weight:bold;margin:12px 0 8px 0'>{titulo}</div>",
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────
#  SECCIÓN: LECTURA ACTUAL
#  Muestra todas las variables de la última lectura disponible
#  en MySQL, organizadas por subsistema en cuatro columnas.
# ─────────────────────────────────────────────────────────────

def _mostrar_lectura_actual(lectura: dict):
    """
    Despliega la última lectura del nodo organizada por subsistema.

    Columnas mostradas:
        Col 1 — Transferencia (TR): voltajes trifásicos, corrientes y potencia.
        Col 2 — Tablero ML:         voltajes, corrientes y temperaturas de sala.
        Col 3 — Rectificador 1:     voltaje DC, corriente y porcentaje de carga.
        Col 4 — Rectificador 2:     ídem Rectificador 1.

    Al final muestra los timestamps de cada subsistema si están presentes
    en el dict de lectura (claves con prefijo "_fecha").

    Parámetros:
        lectura (dict): Diccionario con todos los campos de la última lectura,
                        retornado por evaluar_alarmas_completo().
    """
    _seccion_header("Última Lectura del Nodo")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**Transferencia (TR)**")
        _tarjeta_lectura("Voltaje L1-L2", lectura.get("tr_voltaje_ac_l1_l2"), "V", "#2E86C1")
        _tarjeta_lectura("Voltaje L2-L3", lectura.get("tr_voltaje_ac_l2_l3"), "V", "#2E86C1")
        _tarjeta_lectura("Voltaje L3-L1", lectura.get("tr_voltaje_ac_l3_l1"), "V", "#2E86C1")
        _tarjeta_lectura("Corriente L1",  lectura.get("tr_corriente_ac_l1"),  "A", "#1A5276")
        _tarjeta_lectura("Corriente L2",  lectura.get("tr_corriente_ac_l2"),  "A", "#1A5276")
        _tarjeta_lectura("Corriente L3",  lectura.get("tr_corriente_ac_l3"),  "A", "#1A5276")
        _tarjeta_lectura("Potencia Aparente", lectura.get("tr_potencia_aparente_kva"), "kVA", "#0D2B45")
        _tarjeta_lectura("Factor de Potencia", lectura.get("tr_factor_potencia"), "", "#0D2B45")

    with col2:
        st.markdown("**Tablero ML**")
        _tarjeta_lectura("Voltaje R-S", lectura.get("ml_voltaje_ac_rs"), "V", "#2E86C1")
        _tarjeta_lectura("Voltaje S-T", lectura.get("ml_voltaje_ac_st"), "V", "#2E86C1")
        _tarjeta_lectura("Voltaje T-R", lectura.get("ml_voltaje_ac_tr"), "V", "#2E86C1")
        _tarjeta_lectura("Corriente R", lectura.get("ml_corriente_ac_r"), "A", "#1A5276")
        _tarjeta_lectura("Corriente S", lectura.get("ml_corriente_ac_s"), "A", "#1A5276")
        _tarjeta_lectura("Corriente T", lectura.get("ml_corriente_ac_t"), "A", "#1A5276")
        _tarjeta_lectura("Temp Sala S01", lectura.get("ml_temp_sala_s01"), "°C", "#E67E22")
        _tarjeta_lectura("Temp Sala S02", lectura.get("ml_temp_sala_s02"), "°C", "#E67E22")

    with col3:
        st.markdown("**Rectificador 1**")
        _tarjeta_lectura("Voltaje DC",     lectura.get("r1_voltaje_dc_salida"),  "V",  "#1E8449")
        _tarjeta_lectura("Corriente DC",   lectura.get("r1_corriente_dc_total"), "A",  "#1A5276")
        _tarjeta_lectura("% Carga",        lectura.get("r1_porcentaje_carga"),   "%",  "#D35400")
        _tarjeta_lectura("Corriente Carga",lectura.get("r1_corriente_carga"),    "A",  "#1A5276")

    with col4:
        st.markdown("**Rectificador 2**")
        _tarjeta_lectura("Voltaje DC",     lectura.get("r2_voltaje_dc_salida"),  "V",  "#1E8449")
        _tarjeta_lectura("Corriente DC",   lectura.get("r2_corriente_dc_total"), "A",  "#1A5276")
        _tarjeta_lectura("% Carga",        lectura.get("r2_porcentaje_carga"),   "%",  "#D35400")
        _tarjeta_lectura("Corriente Carga",lectura.get("r2_corriente_carga"),    "A",  "#1A5276")

    # Muestra los timestamps de cada subsistema (claves con prefijo "_fecha_")
    fechas = {k: v for k, v in lectura.items() if k.startswith("_fecha")}
    if fechas:
        st.caption(
            "  ·  ".join(
                f"{k.replace('_fecha_','').upper()}: {v}"
                for k, v in fechas.items()
            )
        )


# ─────────────────────────────────────────────────────────────
#  SECCIÓN: ALARMAS DE UMBRALES (CAPA 1)
#  Valida cada variable contra límites técnicos fijos.
#  Las violaciones se clasifican en CRÍTICO o ADVERTENCIA.
# ─────────────────────────────────────────────────────────────

def _mostrar_alarmas_umbrales(alarmas: list):
    """
    Renderiza los resultados de la validación de umbrales técnicos.

    Si no hay alarmas activas, muestra un mensaje de estado OK.
    Si hay alarmas, las separa en dos tablas: críticas y advertencias.
    Cada fila incluye la variable, el valor actual, el límite configurado
    y el tipo de violación (mínimo/máximo).

    Parámetros:
        alarmas (list): Lista de dicts retornada por evaluar_alarmas_completo().
                        Cada dict contiene: variable, severidad, valor, unidad,
                        umbral y tipo.
    """
    _seccion_header("Capa 1 — Validación de Umbrales Técnicos")

    if not alarmas:
        st.success("✅ Todas las variables dentro de rangos normales.")
        return

    # Separar por severidad para mostrar críticas primero
    criticas    = [a for a in alarmas if a["severidad"] == "CRITICO"]
    advertencias = [a for a in alarmas if a["severidad"] == "ADVERTENCIA"]

    if criticas:
        st.error(f"🔴 {len(criticas)} ALARMA(S) CRÍTICA(S)")
        df_crit = pd.DataFrame([{
            "Variable":      a["variable"],
            "Valor Actual":  f"{a['valor']:.1f} {a['unidad']}",
            "Límite":        f"{a['umbral']} {a['unidad']}",
            "Tipo":          a["tipo"],
        } for a in criticas])
        st.dataframe(df_crit, width='stretch', hide_index=True)

    if advertencias:
        st.warning(f"🟡 {len(advertencias)} ADVERTENCIA(S)")
        df_warn = pd.DataFrame([{
            "Variable":      a["variable"],
            "Valor Actual":  f"{a['valor']:.1f} {a['unidad']}",
            "Umbral Warn":   f"{a['umbral']} {a['unidad']}",
        } for a in advertencias])
        st.dataframe(df_warn, width='stretch', hide_index=True)


# ─────────────────────────────────────────────────────────────
#  SECCIÓN: ISOLATION FOREST (CAPA 2)
#  Visualiza el score de anomalía multivariable y las variables
#  que más contribuyen a la desviación respecto al histórico.
# ─────────────────────────────────────────────────────────────

def _gauge_svg(score_pct: float, es_anomalia: bool) -> str:
    """
    Genera un gauge semicircular en SVG puro para visualizar el score IF.

    El gauge divide el arco en tres zonas de color:
        Verde  (0–40):   Comportamiento normal
        Naranja (40–70): Revisar — comportamiento inusual
        Rojo   (70–100): Crítico — anomalía significativa

    La aguja apunta al score actual y el centro muestra el valor numérico.
    No requiere dependencias externas: todo es SVG con geometría calculada
    en Python (math.cos / math.sin).

    Parámetros:
        score_pct (float): Score normalizado 0–100 (0=normal, 100=muy anómalo).
        es_anomalia (bool): Si True, muestra etiqueta "⚠ ANOMALÍA"; si False, "✓ NORMAL".

    Retorna:
        str: Código SVG completo listo para st.markdown(..., unsafe_allow_html=True).
    """
    # Color de aguja y etiqueta según zona del score
    if score_pct >= 70:
        color_aguja = "#C0392B"   # rojo crítico
        color_arco  = "#FADBD8"
        label_color = "#C0392B"
    elif score_pct >= 40:
        color_aguja = "#E67E22"   # naranja advertencia
        color_arco  = "#FDEBD0"
        label_color = "#E67E22"
    else:
        color_aguja = "#1E8449"   # verde normal
        color_arco  = "#D5F5E3"
        label_color = "#1E8449"

    # Geometría del semicírculo: centro (cx, cy) y radio r
    cx, cy, r = 150, 130, 100
    # El ángulo de la aguja va de 180° (izquierda=0) a 0° (derecha=100)
    angulo_aguja  = 180 - (score_pct / 100) * 180

    def punto(ang_deg, radio=r):
        """Convierte ángulo en grados a coordenadas (x, y) sobre el arco."""
        rad = math.radians(ang_deg)
        return cx + radio * math.cos(rad), cy - radio * math.sin(rad)

    x0, y0 = punto(180)   # extremo izquierdo del arco
    x1, y1 = punto(0)     # extremo derecho del arco

    # Punta de la aguja
    largo_aguja = 85
    ax = cx + largo_aguja * math.cos(math.radians(angulo_aguja))
    ay = cy - largo_aguja * math.sin(math.radians(angulo_aguja))

    # Límites de cada zona de color sobre el arco
    x_v0, y_v0 = punto(180)   # inicio zona verde
    x_v1, y_v1 = punto(108)   # fin zona verde  (0–40%)
    x_n0, y_n0 = punto(108)   # inicio zona naranja
    x_n1, y_n1 = punto(54)    # fin zona naranja (40–70%)
    x_r0, y_r0 = punto(54)    # inicio zona roja
    x_r1, y_r1 = punto(0)     # fin zona roja   (70–100%)

    svg = f"""
    <svg width="300" height="170" xmlns="http://www.w3.org/2000/svg">
      <!-- Zonas de color: verde / naranja / rojo -->
      <path d="M {x_v0:.1f} {y_v0:.1f} A {r} {r} 0 0 1 {x_v1:.1f} {y_v1:.1f}"
            stroke="#1E8449" stroke-width="14" fill="none" stroke-linecap="round"/>
      <path d="M {x_n0:.1f} {y_n0:.1f} A {r} {r} 0 0 1 {x_n1:.1f} {y_n1:.1f}"
            stroke="#E67E22" stroke-width="14" fill="none" stroke-linecap="round"/>
      <path d="M {x_r0:.1f} {y_r0:.1f} A {r} {r} 0 0 1 {x_r1:.1f} {y_r1:.1f}"
            stroke="#C0392B" stroke-width="14" fill="none" stroke-linecap="round"/>
      <!-- Arco interior gris como referencia visual -->
      <path d="M {x0:.1f} {y0:.1f} A {r-18} {r-18} 0 0 1 {x1:.1f} {y1:.1f}"
            stroke="#E5E8EA" stroke-width="2" fill="none"/>
      <!-- Aguja y pivote central -->
      <line x1="{cx}" y1="{cy}" x2="{ax:.1f}" y2="{ay:.1f}"
            stroke="{color_aguja}" stroke-width="3" stroke-linecap="round"/>
      <circle cx="{cx}" cy="{cy}" r="7" fill="{color_aguja}"/>
      <!-- Score numérico en el centro del gauge -->
      <text x="{cx}" y="{cy + 28}" text-anchor="middle"
            font-size="26" font-weight="bold" fill="{label_color}">{score_pct:.0f}</text>
      <text x="{cx}" y="{cy + 44}" text-anchor="middle"
            font-size="11" fill="#7F8C8D">/ 100</text>
      <!-- Etiquetas de extremos del arco -->
      <text x="30"  y="{cy + 12}" font-size="10" fill="#7F8C8D">Normal</text>
      <text x="230" y="{cy + 12}" font-size="10" fill="#7F8C8D">Anómalo</text>
      <!-- Estado: ANOMALÍA o NORMAL -->
      <text x="{cx}" y="165" text-anchor="middle" font-size="13"
            font-weight="bold" fill="{label_color}">
        {"⚠ ANOMALÍA" if es_anomalia else "✓ NORMAL"}
      </text>
    </svg>
    """
    return svg


def _mostrar_isolation_forest(resultado_if: dict):
    """
    Renderiza la sección completa de resultados del modelo Isolation Forest.

    Estructura visual:
        1. Gauge SVG con el score normalizado 0–100.
        2. Interpretación textual según la zona del score (normal/revisar/crítico).
        3. Score raw del modelo para usuarios técnicos.
        4. Gráfico de barras horizontales con la desviación estándar (σ) de
           cada variable respecto a su media histórica, coloreado por nivel.
        5. Tabla expandible con el detalle completo de todas las variables.

    Si el modelo no está disponible (modelo_if.pkl no encontrado), muestra
    un mensaje informativo y una guía para ejecutar el entrenamiento.

    Parámetros:
        resultado_if (dict): Sub-dict retornado por evaluar_alarmas_completo().
            Campos relevantes:
                disponible (bool)          → si el modelo está cargado
                score_pct (float)          → score normalizado 0–100
                es_anomalia (bool)         → True si supera el umbral IF
                score (float)              → score raw del IsolationForest
                features_influyentes (list)→ top 3 variables más desviadas
                todas_las_desviaciones (list) → lista completa con σ por feature
    """
    _seccion_header("🤖 Capa 2 — Anomalías Multivariables (Isolation Forest)")

    if not resultado_if.get("disponible"):
        st.info(resultado_if.get("mensaje", "Modelo no disponible."))
        st.markdown(
            "Para activar esta capa ejecute el entrenamiento desde "
            "⚙️ Configuración del Modelo arriba."
        )
        return

    score_pct   = resultado_if.get("score_pct") or 0.0
    es_anomalia = resultado_if.get("es_anomalia", False)
    todas       = resultado_if.get("todas_las_desviaciones", [])
    top3        = resultado_if.get("features_influyentes", [])

    # ── Fila superior: gauge a la izquierda, interpretación a la derecha ──
    col_gauge, col_interp = st.columns([1, 2])

    with col_gauge:
        st.markdown(_gauge_svg(score_pct, es_anomalia), unsafe_allow_html=True)

    with col_interp:
        st.markdown("**¿Qué significa este score?**")

        # Barra explicativa de zonas de color como referencia rápida
        st.markdown("""
        <div style="display:flex;height:18px;border-radius:9px;overflow:hidden;margin:6px 0 10px 0">
            <div style="flex:40;background:#1E8449"></div>
            <div style="flex:30;background:#E67E22"></div>
            <div style="flex:30;background:#C0392B"></div>
        </div>
        <div style="display:flex;font-size:11px;color:#7F8C8D;margin-bottom:12px">
            <div style="flex:40">0–40: Normal</div>
            <div style="flex:30">40–70: Revisar</div>
            <div style="flex:30">70–100: Crítico</div>
        </div>
        """, unsafe_allow_html=True)

        # Mensaje adaptado según la zona del score
        if score_pct < 40:
            st.success(
                "El nodo opera dentro de los patrones aprendidos del histórico 2025. "
                "No se detectan combinaciones inusuales de variables."
            )
        elif score_pct < 70:
            vars_desc = ", ".join(f"**{x['feature'].replace('_',' ')}**" for x in top3[:2])
            st.warning(
                f"Comportamiento ligeramente inusual. "
                f"Variables con mayor desviación: {vars_desc}. "
                "Monitorear en las próximas lecturas."
            )
        else:
            vars_desc = ", ".join(f"**{x['feature'].replace('_',' ')}**" for x in top3[:3])
            st.error(
                f"Combinación de variables significativamente fuera del patrón histórico. "
                f"Revisar: {vars_desc}."
            )

        # Score raw para análisis técnico (más negativo = más anómalo en IF)
        st.caption(
            f"Score raw IF: `{resultado_if.get('score', 'N/A')}` — "
            "Valores más negativos indican mayor anomalía según el modelo."
        )

    st.markdown("---")

    # ── Gráfico de barras: desviación estándar por variable ──
    if todas:
        st.markdown("**Desviación de cada variable respecto a su media histórica (σ)**")
        st.caption(
            "Una desviación de 1σ significa que el valor actual está 1 desviación estándar "
            "por encima o por debajo de lo normal. Valores >2σ merecen atención."
        )

        try:
            labels  = [d["feature"].replace("_", " ") for d in todas]
            desvios = [d["desviacion_sigma"] for d in todas]
            valores = [d["valor_actual"] for d in todas]
            medias  = [d["media_historica"] for d in todas]

            # Colorear cada barra según su nivel de desviación
            colores = []
            for dev in desvios:
                if dev >= 3:   colores.append("#C0392B")   # crítico
                elif dev >= 2: colores.append("#E67E22")   # advertencia
                elif dev >= 1: colores.append("#F4D03F")   # leve
                else:          colores.append("#1E8449")   # normal

            # Tooltip con contexto completo al pasar el cursor
            hover = [
                f"<b>{labels[i]}</b><br>"
                f"Valor actual: {valores[i]:.2f}<br>"
                f"Media histórica: {medias[i]:.2f}<br>"
                f"Desviación: {desvios[i]:.2f}σ"
                for i in range(len(labels))
            ]

            fig = go.Figure(go.Bar(
                x=desvios,
                y=labels,
                orientation="h",
                marker_color=colores,
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover,
                text=[f"{d:.1f}σ" for d in desvios],
                textposition="outside",
            ))

            # Líneas verticales de referencia en 1σ, 2σ y 3σ
            fig.add_vline(x=1, line_dash="dot", line_color="#F4D03F",
                          annotation_text="1σ", annotation_position="top")
            fig.add_vline(x=2, line_dash="dot", line_color="#E67E22",
                          annotation_text="2σ", annotation_position="top")
            fig.add_vline(x=3, line_dash="dot", line_color="#C0392B",
                          annotation_text="3σ", annotation_position="top")

            fig.update_layout(
                height=max(350, len(labels) * 22),
                margin=dict(l=0, r=60, t=20, b=20),
                xaxis_title="Desviación estándar (σ)",
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="#000000",
                paper_bgcolor="black",
                font=dict(size=11),
                showlegend=False,
            )
            st.plotly_chart(fig, width='stretch')

        except ImportError:
            # Fallback si plotly no está instalado: tabla con los mismos datos
            st.info("Instale plotly para ver el gráfico: `pip install plotly`")
            df_dev = pd.DataFrame([{
                "Variable":           d["feature"],
                "Desviación (σ)":     d["desviacion_sigma"],
                "Valor Actual":       d["valor_actual"],
                "Media Histórica":    d["media_historica"],
            } for d in todas])
            st.dataframe(df_dev, width='stretch', hide_index=True)

    # ── Tabla detallada de todas las variables (expandible) ──
    with st.expander("📋 Ver tabla completa de variables", expanded=False):
        if todas:
            df_tabla = pd.DataFrame([{
                "Variable":        d["feature"].replace("_", " "),
                "Valor Actual":    d["valor_actual"],
                "Media Histórica": d["media_historica"],
                "Std Histórica":   d["std_historica"],
                "Desviación (σ)":  d["desviacion_sigma"],
                # Semáforo de estado basado en la desviación estándar
                "Estado":          "🔴 Crítico" if d["desviacion_sigma"] >= 3
                                   else "🟡 Revisar" if d["desviacion_sigma"] >= 2
                                   else "🟢 Normal",
            } for d in todas])
            st.dataframe(df_tabla, width='stretch', hide_index=True)


# ─────────────────────────────────────────────────────────────
#  SECCIÓN: NOTIFICACIÓN POR EMAIL
#  Permite enviar un resumen de las alarmas activas a uno o
#  más destinatarios mediante SMTP (configurado en alarmas.py).
# ─────────────────────────────────────────────────────────────

def _mostrar_panel_email(resultado: dict):
    """
    Muestra el panel de notificación por email cuando hay alarmas activas.

    Si no hay alarmas, informa que no es necesario enviar correo.
    Si hay alarmas, permite ingresar destinatarios y dispara el envío
    llamando a enviar_email_alarma() de src.alarmas.

    Las credenciales SMTP deben configurarse en src/alarmas.py antes
    de usar esta funcionalidad.

    Parámetros:
        resultado (dict): Dict completo de evaluar_alarmas_completo(),
                          que incluye hay_alarmas, nivel_maximo y alarmas_umbrales.
    """
    _seccion_header("📧 Notificación por Email")

    hay_alarmas = resultado.get("hay_alarmas", False)

    if not hay_alarmas:
        st.info("No hay alarmas activas. No es necesario enviar notificación.")
        return

    # Campo de entrada para uno o más destinatarios separados por coma
    destinatarios_raw = st.text_input(
        "Destinatarios (separados por coma)",
        value="infraestructura@tigo.com",
        help="Ingrese uno o más correos separados por coma"
    )

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("📤 Enviar Email de Alerta", type="primary"):
            destinatarios = [d.strip() for d in destinatarios_raw.split(",") if d.strip()]
            if not destinatarios:
                st.warning("Ingrese al menos un destinatario.")
            else:
                with st.spinner("Enviando..."):
                    exito, msg = enviar_email_alarma(resultado, destinatarios)
                if exito:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
                    st.info(
                        "Configure las credenciales SMTP en `src/alarmas.py` → "
                        "función `enviar_email_alarma` antes de usar esta función."
                    )

    with col2:
        st.caption(
            f"Se enviará un resumen de las {len(resultado.get('alarmas_umbrales',[]))} "
            f"alarma(s) activa(s) con nivel **{resultado.get('nivel_maximo','—')}**."
        )


# ─────────────────────────────────────────────────────────────
#  SECCIÓN: ENTRENAMIENTO DEL MODELO
#  Panel expandible para consultar el estado del modelo IF
#  y lanzar un reentrenamiento desde la interfaz.
# ─────────────────────────────────────────────────────────────

def _mostrar_panel_entrenamiento():
    """
    Renderiza el panel de configuración y entrenamiento del modelo Isolation Forest.

    El panel aparece colapsado por defecto para no interrumpir el flujo
    principal. Dentro muestra:
        - Cuándo es recomendable reentrenar el modelo.
        - Qué hace el proceso de entrenamiento (fuente de datos, output).
        - Estado actual del modelo (fecha y muestras de entrenamiento).
        - Botón para lanzar el reentrenamiento desde la UI.

    Estado del modelo:
        Se verifica la existencia de Model/meta_if.pkl relativo a la raíz
        del proyecto. Si existe, se muestran los metadatos; si no, se
        advierte al usuario que debe entrenar.

    Entrenamiento desde UI:
        Importa y ejecuta src.entrenar_if.main(). Equivalente a ejecutar
        `python src/modelo_if/entrenar_if.py` desde la terminal.
        Llama st.rerun() al terminar para refrescar el estado del modelo.
    """
    with st.expander("⚙️ Configuración del Modelo Isolation Forest", expanded=False):
        st.markdown("""
        **¿Cuándo entrenar?**
        - La primera vez que uses el módulo de alarmas
        - Cuando se acumule histórico de al menos 3 meses adicionales
        - Si cambia significativamente la carga del nodo (nuevo equipo instalado)

        **¿Qué hace el entrenamiento?**
        Lee todo el histórico 2025 de MySQL (TR, ML, RECT), lo limpia,
        une las tablas por timestamp y entrena un modelo que aprende
        los patrones normales de operación del nodo. Luego, lecturas
        que se alejan de ese patrón reciben un score anómalo alto.
        """)

        # Ruta al archivo de metadatos: Model/meta_if.pkl en la raíz del proyecto
        ruta_meta = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Model", "meta_if.pkl"
        )

        if os.path.exists(ruta_meta):
            # Mostrar fecha de entrenamiento y tamaño del dataset usado
            with open(ruta_meta, "rb") as f:
                meta = pickle.load(f)
            st.success(
                f"✅ Modelo disponible — Entrenado el "
                f"{meta.get('fecha_entrenamiento','?')[:10]} "
                f"con {meta.get('n_muestras_entrenamiento',0):,} muestras."
            )
        else:
            st.warning("⚠️ Modelo no encontrado. Ejecute el entrenamiento.")

        if st.button("🔁 Entrenar / Reentrenar Modelo IF", type="secondary"):
            with st.spinner("Entrenando... (puede tomar 1-2 minutos con el histórico completo)"):
                try:
                    sys.path.append(
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
                    )
                    from src.entrenar_if import main as entrenar
                    entrenar()
                    st.success("✅ Modelo entrenado y guardado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error durante el entrenamiento: {e}")
                    st.info("También puede ejecutar manualmente: `python src/modelo_if/entrenar_if.py`")


# ─────────────────────────────────────────────────────────────
#  VISTA PRINCIPAL
#  Punto de entrada del módulo. Orquesta todas las secciones
#  en orden y gestiona el estado de sesión de Streamlit.
# ─────────────────────────────────────────────────────────────

def mostrar_vista_alarmas():
    """
    Función principal del panel de alarmas. Punto de entrada desde app.py.

    Orquesta la ejecución completa del monitor en el siguiente orden:
        1. Panel de entrenamiento (colapsado, siempre visible).
        2. Botón "Verificar Alarmas Ahora" que dispara la evaluación.
        3. Banner de estado global (OK / ADVERTENCIA / CRÍTICO).
        4. Lectura actual del nodo organizada por subsistema.
        5. Capa 1: resultados de validación de umbrales técnicos.
        6. Capa 2: resultados del modelo Isolation Forest.
        7. Panel de notificación por email.
        8. Botón para limpiar resultados y reiniciar la vista.

    Estado de sesión (st.session_state):
        "alarmas_resultado": almacena el dict de evaluar_alarmas_completo()
        entre reruns de Streamlit para no repetir la consulta a MySQL
        innecesariamente. Se limpia con el botón "Limpiar resultados".

    Parámetros:
        Ninguno. Utiliza get_engine() para conectar a MySQL.
    """
    st.header("Monitor de Alarmas — Nodo IDEO CALI")

    engine = get_engine()

    # ── Panel de entrenamiento (siempre visible, colapsado por defecto) ──
    _mostrar_panel_entrenamiento()

    st.markdown("---")

    # ── Botón principal de evaluación ───────────────────────────────────
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        ejecutar = st.button("🔍 Verificar Alarmas Ahora", type="primary", width='stretch')
    with col_info:
        st.caption(
            "Lee la última lectura disponible en MySQL y evalúa:\n"
            "① umbrales técnicos fijos  ②  modelo Isolation Forest"
        )

    # ── Ejecución: nueva consulta o resultado en caché de sesión ─────────
    if ejecutar or st.session_state.get("alarmas_resultado"):

        if ejecutar:
            with st.spinner("Consultando base de datos y evaluando..."):
                resultado = evaluar_alarmas_completo(engine)
            st.session_state["alarmas_resultado"] = resultado
        else:
            # Reutilizar resultado previo sin volver a consultar MySQL
            resultado = st.session_state["alarmas_resultado"]

        # ── Banner de estado global ──────────────────────────────────────
        st.markdown("---")
        st.markdown(
            f"<div style='text-align:center;padding:12px 0'>"
            f"{_badge_nivel(resultado['nivel_maximo'])}"
            f"<p style='margin-top:8px;color:#555'>{resultado['resumen']}</p>"
            f"<p style='font-size:11px;color:#999'>Evaluado: {resultado['timestamp']}</p>"
            f"</div>",
            unsafe_allow_html=True
        )
        st.markdown("---")

        # ── Secciones del panel en orden lógico ─────────────────────────
        _mostrar_lectura_actual(resultado["lectura"])
        st.markdown("---")

        _mostrar_alarmas_umbrales(resultado["alarmas_umbrales"])
        st.markdown("---")

        _mostrar_isolation_forest(resultado["resultado_if"])
        st.markdown("---")

        _mostrar_panel_email(resultado)

        # ── Limpiar resultados de sesión y reiniciar vista ───────────────
        st.markdown("---")
        if st.button("🔄 Limpiar resultados"):
            del st.session_state["alarmas_resultado"]
            st.rerun()