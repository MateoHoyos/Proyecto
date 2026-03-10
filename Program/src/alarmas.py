"""
alarmas.py
──────────────────────────────────────────────────────────────────────────────
Módulo de alarmas para el sistema IDEO.

Dos capas de detección:
  1. Umbrales fijos  → reglas técnicas claras (sobrecarga, voltaje, temperatura)
  2. Isolation Forest → anomalías multivariables aprendidas del histórico 2025

Uso principal (desde panel_alarmas.py):
    from src.alarmas import evaluar_alarmas_completo
    resultado = evaluar_alarmas_completo(engine, lectura_actual)
──────────────────────────────────────────────────────────────────────────────
"""

import os
import pickle
import math
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DE UMBRALES FIJOS
#  Editar aquí si cambian los límites del nodo.
# ─────────────────────────────────────────────────────────────

UMBRALES = {
    # ── Corriente AC (TR) ────────────────────────────────────
    # Límite de los fusibles del nodo: 160 A
    # Alarma crítica a 90%, advertencia a 80%
    "tr_corriente_ac_l1":  {"warn": 128.0, "crit": 144.0, "unidad": "A",  "label": "Corriente AC L1 (TR)"},
    "tr_corriente_ac_l2":  {"warn": 128.0, "crit": 144.0, "unidad": "A",  "label": "Corriente AC L2 (TR)"},
    "tr_corriente_ac_l3":  {"warn": 128.0, "crit": 144.0, "unidad": "A",  "label": "Corriente AC L3 (TR)"},

    # ── Potencia aparente (TR) ───────────────────────────────
    # Transformador 75 kVA → límite operativo 90% = 67.5 kVA
    "tr_potencia_aparente_kva": {"warn": 60.0, "crit": 67.5, "unidad": "kVA", "label": "Potencia Aparente (TR)"},

    # ── Voltaje AC (TR) ──────────────────────────────────────
    # Nominal 220 V ±10% → rango válido [198 V, 242 V]
    "tr_voltaje_ac_l1_l2": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje L1-L2 (TR)"},
    "tr_voltaje_ac_l2_l3": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje L2-L3 (TR)"},
    "tr_voltaje_ac_l3_l1": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje L3-L1 (TR)"},

    # ── Voltaje AC (ML) ──────────────────────────────────────
    "ml_voltaje_ac_rs": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje AC R-S (ML)"},
    "ml_voltaje_ac_st": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje AC S-T (ML)"},
    "ml_voltaje_ac_tr": {"min": 198.0, "max": 242.0, "unidad": "V", "label": "Voltaje AC T-R (ML)"},

    # ── Corriente AC (ML) ────────────────────────────────────
    "ml_corriente_ac_r": {"warn": 128.0, "crit": 144.0, "unidad": "A", "label": "Corriente AC R (ML)"},
    "ml_corriente_ac_s": {"warn": 128.0, "crit": 144.0, "unidad": "A", "label": "Corriente AC S (ML)"},
    "ml_corriente_ac_t": {"warn": 128.0, "crit": 144.0, "unidad": "A", "label": "Corriente AC T (ML)"},

    # ── Temperatura sala ─────────────────────────────────────
    # Estándar ASHRAE A2: máximo 27 °C de entrada
    "ml_temp_sala_s01": {"warn": 25.0, "crit": 27.0, "unidad": "°C", "label": "Temperatura Sala S01"},
    "ml_temp_sala_s02": {"warn": 25.0, "crit": 27.0, "unidad": "°C", "label": "Temperatura Sala S02"},

    # ── Rectificadores (aplica a R1 y R2) ───────────────────
    # Porcentaje de carga: advertencia 80%, crítico 90%
    "rect_porcentaje_carga": {"warn": 80.0, "crit": 90.0, "unidad": "%", "label": "% Carga Rectificador"},

    # Voltaje DC de salida: nominal 54 V, ±5%
    "rect_voltaje_dc_salida": {"min": 51.3, "max": 56.7, "unidad": "V", "label": "Voltaje DC Salida (RECT)"},
}


# ─────────────────────────────────────────────────────────────
#  RUTA DEL MODELO ISOLATION FOREST
# ─────────────────────────────────────────────────────────────

_DIR_SRC    = os.path.dirname(os.path.abspath(__file__))   # src/
_DIR_BASE   = os.path.dirname(_DIR_SRC)                    # Program/
RUTA_MODELO = os.path.join(_DIR_BASE, "Model", "modelo_if.pkl")
RUTA_META   = os.path.join(_DIR_BASE, "Model", "meta_if.pkl")


# ─────────────────────────────────────────────────────────────
#  CAPA 1 — UMBRALES FIJOS
# ─────────────────────────────────────────────────────────────

def _evaluar_umbral(clave, valor, config):
    """
    Evalúa una variable contra su umbral.
    Retorna None si está OK, o un dict de alarma si hay problema.

    Tipos de umbral soportados:
      - warn/crit : solo límite superior  (corriente, potencia, temperatura)
      - min/max   : rango bilateral       (voltaje)
    """
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None

    label  = config.get("label", clave)
    unidad = config.get("unidad", "")

    # Rango bilateral (voltaje)
    if "min" in config and "max" in config:
        if valor < config["min"]:
            return {
                "variable": label,
                "valor": valor,
                "umbral": config["min"],
                "unidad": unidad,
                "tipo": "BAJO",
                "severidad": "CRITICO",
                "mensaje": f"{label}: {valor:.1f}{unidad} por debajo del mínimo ({config['min']}{unidad})"
            }
        if valor > config["max"]:
            return {
                "variable": label,
                "valor": valor,
                "umbral": config["max"],
                "unidad": unidad,
                "tipo": "ALTO",
                "severidad": "CRITICO",
                "mensaje": f"{label}: {valor:.1f}{unidad} por encima del máximo ({config['max']}{unidad})"
            }
        return None

    # Solo límite superior (corriente, potencia, temperatura)
    if "crit" in config and valor >= config["crit"]:
        return {
            "variable": label,
            "valor": valor,
            "umbral": config["crit"],
            "unidad": unidad,
            "tipo": "SOBRECARGA",
            "severidad": "CRITICO",
            "mensaje": f"{label}: {valor:.1f}{unidad} ≥ límite crítico ({config['crit']}{unidad})"
        }
    if "warn" in config and valor >= config["warn"]:
        return {
            "variable": label,
            "valor": valor,
            "umbral": config["warn"],
            "unidad": unidad,
            "tipo": "ADVERTENCIA",
            "severidad": "ADVERTENCIA",
            "mensaje": f"{label}: {valor:.1f}{unidad} ≥ umbral de advertencia ({config['warn']}{unidad})"
        }
    return None


def evaluar_umbrales_fijos(lectura: dict) -> list:
    """
    Recibe un diccionario plano con TODAS las lecturas actuales.
    Claves esperadas: prefijadas por equipo, ej:
        tr_corriente_ac_l1, ml_temp_sala_s01,
        r1_porcentaje_carga, r2_voltaje_dc_salida, etc.

    Retorna lista de alarmas (puede estar vacía).
    """
    alarmas = []

    for clave_cfg, config in UMBRALES.items():
        # Variables de rectificador: evaluar R1 y R2 por separado
        if clave_cfg.startswith("rect_"):
            sufijo = clave_cfg[5:]  # ej: "porcentaje_carga"
            for rid in [1, 2]:
                clave_real = f"r{rid}_{sufijo}"
                valor = lectura.get(clave_real)
                if valor is not None:
                    alarma = _evaluar_umbral(clave_real, float(valor), config)
                    if alarma:
                        alarma["variable"] = f"{config['label']} (Rect {rid})"
                        alarmas.append(alarma)
        else:
            valor = lectura.get(clave_cfg)
            if valor is not None:
                alarma = _evaluar_umbral(clave_cfg, float(valor), config)
                if alarma:
                    alarmas.append(alarma)

    return alarmas


# ─────────────────────────────────────────────────────────────
#  CAPA 2 — ISOLATION FOREST
# ─────────────────────────────────────────────────────────────

# Columnas que se usan como features para el modelo.
# Deben coincidir EXACTAMENTE con las usadas en entrenar_if.py
FEATURES_IF = [
    # TR
    "tr_corriente_ac_l1", "tr_corriente_ac_l2", "tr_corriente_ac_l3",
    "tr_potencia_activa_kw", "tr_potencia_reactiva_kvar", "tr_potencia_aparente_kva",
    "tr_factor_potencia",
    "tr_voltaje_ac_l1_l2", "tr_voltaje_ac_l2_l3", "tr_voltaje_ac_l3_l1",
    # ML
    "ml_corriente_ac_r", "ml_corriente_ac_s", "ml_corriente_ac_t",
    "ml_voltaje_ac_rs", "ml_voltaje_ac_st", "ml_voltaje_ac_tr",
    "ml_temp_sala_s01", "ml_temp_sala_s02",
    # Rectificadores — solo columnas disponibles en rect1/2_historico
    "rect_avg_corriente_dc", "rect_avg_voltaje_dc", "rect_avg_corriente_carga",
]


def _preparar_vector_if(lectura: dict) -> np.ndarray:
    """
    Construye el vector de features para el modelo IF a partir de la lectura
    en tiempo real (obtenida de rect_dce vía obtener_ultima_lectura_db).

    Mapeo de columnas de rect_dce → features del modelo:
        r1/r2_corriente_dc_total → rect_avg_corriente_dc   (promedio R1+R2)
        r1/r2_voltaje_dc_salida  → rect_avg_voltaje_dc
        r1/r2_corriente_carga    → rect_avg_corriente_carga
    """
    lectura_ext = dict(lectura)

    def avg(campo_r1, campo_r2):
        v1 = lectura_ext.get(campo_r1) or 0
        v2 = lectura_ext.get(campo_r2) or 0
        return (v1 + v2) / 2

    lectura_ext["rect_avg_corriente_dc"]   = avg("r1_corriente_dc_total", "r2_corriente_dc_total")
    lectura_ext["rect_avg_voltaje_dc"]     = avg("r1_voltaje_dc_salida",  "r2_voltaje_dc_salida")
    lectura_ext["rect_avg_corriente_carga"]= avg("r1_corriente_carga",    "r2_corriente_carga")

    vector = []
    for feat in FEATURES_IF:
        val = lectura_ext.get(feat, 0)
        vector.append(float(val) if val is not None else 0.0)

    return np.array(vector).reshape(1, -1)


def evaluar_isolation_forest(lectura: dict) -> dict:
    """
    Carga el modelo entrenado y evalúa la lectura actual.

    Retorna dict con:
        - disponible (bool): si el modelo existe
        - es_anomalia (bool)
        - score (float): más negativo = más anómalo (-1 a 0 aprox)
        - score_pct (float): 0-100, donde 100 = más anómalo
        - features_influyentes (list): top 3 variables que más contribuyen
        - mensaje (str)
    """
    resultado = {
        "disponible": False,
        "es_anomalia": False,
        "score": None,
        "score_pct": None,
        "features_influyentes": [],
        "mensaje": "Modelo no entrenado. Ejecute 'Entrenar Modelo' primero."
    }

    if not os.path.exists(RUTA_MODELO):
        return resultado

    try:
        with open(RUTA_MODELO, "rb") as f:
            modelo = pickle.load(f)
        with open(RUTA_META, "rb") as f:
            meta = pickle.load(f)

        resultado["disponible"] = True

        vector = _preparar_vector_if(lectura)

        # score_samples: más negativo = más anómalo
        score_raw = modelo.score_samples(vector)[0]
        prediccion = modelo.predict(vector)[0]  # -1 anomalía, 1 normal

        # Normalizar score a 0-100 usando rango observado en entrenamiento
        score_min = meta.get("score_min", -0.5)
        score_max = meta.get("score_max", 0.0)
        score_norm = (score_raw - score_min) / (score_max - score_min + 1e-9)
        score_pct  = round((1 - np.clip(score_norm, 0, 1)) * 100, 1)

        resultado["score"]      = round(score_raw, 4)
        resultado["score_pct"]  = score_pct
        resultado["es_anomalia"] = (prediccion == -1)

        # Features más influyentes: cuáles se alejan más de la media de entrenamiento
        medias  = meta.get("feature_means", {})
        stds    = meta.get("feature_stds", {})
        desvios = []
        for i, feat in enumerate(FEATURES_IF):
            mu  = medias.get(feat, 0)
            sig = stds.get(feat, 1) or 1
            dev = abs((vector[0][i] - mu) / sig)
            desvios.append((feat, dev, vector[0][i]))

        desvios.sort(key=lambda x: x[1], reverse=True)

        # Top 3 para el mensaje rápido
        resultado["features_influyentes"] = [
            {"feature": f, "desviacion_sigma": round(d, 2), "valor_actual": round(v, 2)}
            for f, d, v in desvios[:3]
        ]

        # Todas las desviaciones — para la vista detallada en Streamlit
        resultado["todas_las_desviaciones"] = [
            {
                "feature":          f,
                "desviacion_sigma": round(d, 2),
                "valor_actual":     round(v, 2),
                "media_historica":  round(medias.get(f, 0), 2),
                "std_historica":    round(stds.get(f, 1) or 1, 2),
            }
            for f, d, v in desvios
        ]

        if resultado["es_anomalia"]:
            resultado["mensaje"] = (
                f"⚠️ ANOMALÍA DETECTADA — Score anómalo: {score_pct:.0f}/100. "
                f"Variables más desviadas: {', '.join(x['feature'] for x in resultado['features_influyentes'])}"
            )
        else:
            resultado["mensaje"] = f"✅ Operación normal — Score anómalo: {score_pct:.0f}/100"

    except Exception as e:
        resultado["mensaje"] = f"Error evaluando modelo IF: {e}"

    return resultado


# ─────────────────────────────────────────────────────────────
#  LECTOR DE ÚLTIMA LECTURA DESDE MySQL
# ─────────────────────────────────────────────────────────────

def obtener_ultima_lectura_db(engine) -> dict:
    """
    Lee la última fila de cada tabla _dce y construye el
    diccionario plano que usan las funciones de evaluación.
    """
    lectura = {}

    with engine.connect() as conn:

        # ── TR ────────────────────────────────────────────────
        try:
            row = conn.execute(text("""
                SELECT voltaje_ac_l1_l2, voltaje_ac_l2_l3, voltaje_ac_l3_l1,
                       corriente_ac_l1, corriente_ac_l2, corriente_ac_l3,
                       potencia_activa_kw, potencia_reactiva_kvar,
                       potencia_aparente_kva, factor_potencia, fecha
                FROM tr_dce ORDER BY fecha DESC LIMIT 1
            """)).mappings().fetchone()
            if row:
                lectura["tr_voltaje_ac_l1_l2"]      = row["voltaje_ac_l1_l2"]
                lectura["tr_voltaje_ac_l2_l3"]      = row["voltaje_ac_l2_l3"]
                lectura["tr_voltaje_ac_l3_l1"]      = row["voltaje_ac_l3_l1"]
                lectura["tr_corriente_ac_l1"]        = row["corriente_ac_l1"]
                lectura["tr_corriente_ac_l2"]        = row["corriente_ac_l2"]
                lectura["tr_corriente_ac_l3"]        = row["corriente_ac_l3"]
                lectura["tr_potencia_activa_kw"]     = row["potencia_activa_kw"]
                lectura["tr_potencia_reactiva_kvar"] = row["potencia_reactiva_kvar"]
                lectura["tr_potencia_aparente_kva"]  = row["potencia_aparente_kva"]
                lectura["tr_factor_potencia"]        = row["factor_potencia"]
                lectura["_fecha_tr"]                 = str(row["fecha"])
        except Exception as e:
            lectura["_error_tr"] = str(e)

        # ── ML ────────────────────────────────────────────────
        try:
            row = conn.execute(text("""
                SELECT corriente_ac_r, corriente_ac_s, corriente_ac_t,
                       voltaje_ac_rs, voltaje_ac_st, voltaje_ac_tr,
                       temp_sala_s01, temp_sala_s02, fecha
                FROM ml_dce ORDER BY fecha DESC LIMIT 1
            """)).mappings().fetchone()
            if row:
                lectura["ml_corriente_ac_r"] = row["corriente_ac_r"]
                lectura["ml_corriente_ac_s"] = row["corriente_ac_s"]
                lectura["ml_corriente_ac_t"] = row["corriente_ac_t"]
                lectura["ml_voltaje_ac_rs"]  = row["voltaje_ac_rs"]
                lectura["ml_voltaje_ac_st"]  = row["voltaje_ac_st"]
                lectura["ml_voltaje_ac_tr"]  = row["voltaje_ac_tr"]
                lectura["ml_temp_sala_s01"]  = row["temp_sala_s01"]
                lectura["ml_temp_sala_s02"]  = row["temp_sala_s02"]
                lectura["_fecha_ml"]         = str(row["fecha"])
        except Exception as e:
            lectura["_error_ml"] = str(e)

        # ── RECT 1 y 2 ───────────────────────────────────────
        for rid in [1, 2]:
            try:
                row = conn.execute(text(f"""
                    SELECT voltaje_dc_salida, corriente_dc_total,
                           porcentaje_carga, corriente_carga, fecha
                    FROM rect_dce
                    WHERE rectificador_id = {rid}
                    ORDER BY fecha DESC LIMIT 1
                """)).mappings().fetchone()
                if row:
                    lectura[f"r{rid}_voltaje_dc_salida"]  = row["voltaje_dc_salida"]
                    lectura[f"r{rid}_corriente_dc_total"] = row["corriente_dc_total"]
                    lectura[f"r{rid}_porcentaje_carga"]   = row["porcentaje_carga"]
                    lectura[f"r{rid}_corriente_carga"]    = row["corriente_carga"]
                    lectura[f"_fecha_r{rid}"]             = str(row["fecha"])
            except Exception as e:
                lectura[f"_error_r{rid}"] = str(e)

    return lectura


# ─────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL — EVALUACIÓN COMPLETA
# ─────────────────────────────────────────────────────────────

def evaluar_alarmas_completo(engine, lectura: dict = None) -> dict:
    """
    Punto de entrada principal del módulo.

    Si lectura es None, la obtiene de la BD.
    Retorna:
        {
          "timestamp": "...",
          "lectura": {...},
          "alarmas_umbrales": [...],   # Capa 1
          "resultado_if": {...},       # Capa 2
          "hay_alarmas": bool,
          "nivel_maximo": "OK" | "ADVERTENCIA" | "CRITICO",
          "resumen": "..."
        }
    """
    if lectura is None:
        lectura = obtener_ultima_lectura_db(engine)

    # Capa 1
    alarmas_u = evaluar_umbrales_fijos(lectura)

    # Capa 2
    resultado_if = evaluar_isolation_forest(lectura)

    # Nivel máximo de severidad
    niveles = [a["severidad"] for a in alarmas_u]
    if resultado_if.get("es_anomalia"):
        niveles.append("ADVERTENCIA")

    if "CRITICO" in niveles:
        nivel = "CRITICO"
    elif "ADVERTENCIA" in niveles:
        nivel = "ADVERTENCIA"
    else:
        nivel = "OK"

    hay_alarmas = len(alarmas_u) > 0 or resultado_if.get("es_anomalia", False)

    if nivel == "CRITICO":
        resumen = f"🔴 {len([a for a in alarmas_u if a['severidad']=='CRITICO'])} alarma(s) CRÍTICA(S) detectada(s)."
    elif nivel == "ADVERTENCIA":
        resumen = f"🟡 {len(alarmas_u)} advertencia(s). Revisar condiciones del nodo."
    else:
        resumen = "🟢 Nodo operando dentro de parámetros normales."

    return {
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lectura":          lectura,
        "alarmas_umbrales": alarmas_u,
        "resultado_if":     resultado_if,
        "hay_alarmas":      hay_alarmas,
        "nivel_maximo":     nivel,
        "resumen":          resumen,
    }


# ─────────────────────────────────────────────────────────────
#  EMAIL (preparado, sin configurar)
# ─────────────────────────────────────────────────────────────

def enviar_email_alarma(resultado: dict, destinatarios: list) -> tuple:
    """
    Envía un email con el resumen de alarmas.

    CONFIGURACIÓN PENDIENTE:
        Reemplazar SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
        con las credenciales corporativas antes de usar.

    Retorna (exito: bool, mensaje: str)
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # ── CONFIGURAR AQUÍ ──────────────────────────────────────
    SMTP_HOST = "smtp.office365.com"   # Outlook corporativo
    SMTP_PORT = 587
    SMTP_USER = "tu_usuario@tigo.com"  # ← reemplazar
    SMTP_PASS = "tu_contraseña"        # ← reemplazar (usar variable de entorno)
    REMITENTE = "alertas-ideo@tigo.com"
    # ─────────────────────────────────────────────────────────

    nivel   = resultado["nivel_maximo"]
    alarmas = resultado["alarmas_umbrales"]
    res_if  = resultado["resultado_if"]
    ts      = resultado["timestamp"]

    color_banner = {"CRITICO": "#C0392B", "ADVERTENCIA": "#E67E22", "OK": "#1E8449"}.get(nivel, "#888")
    icono        = {"CRITICO": "🔴", "ADVERTENCIA": "🟡", "OK": "🟢"}.get(nivel, "⚪")

    # Construir filas HTML de alarmas
    filas_html = ""
    for a in alarmas:
        color_fila = "#FADBD8" if a["severidad"] == "CRITICO" else "#FEF9E7"
        filas_html += f"""
        <tr style="background:{color_fila}">
            <td style="padding:6px 10px">{a['variable']}</td>
            <td style="padding:6px 10px;text-align:center"><b>{a['valor']:.1f} {a['unidad']}</b></td>
            <td style="padding:6px 10px;text-align:center">{a['umbral']} {a['unidad']}</td>
            <td style="padding:6px 10px;text-align:center"><b>{a['severidad']}</b></td>
        </tr>"""

    if_html = ""
    if res_if.get("disponible"):
        color_if = "#FADBD8" if res_if["es_anomalia"] else "#D5F5E3"
        if_html = f"""
        <h3 style="color:#1A5276">Análisis Isolation Forest</h3>
        <div style="background:{color_if};padding:10px;border-radius:6px">
            {res_if['mensaje']}<br>
            Score anómalo: <b>{res_if['score_pct']}/100</b>
        </div>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#2C3E50">
    <div style="background:{color_banner};color:white;padding:16px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">{icono} Alerta IDEO — Nodo IDEO CALI | {nivel}</h2>
        <p style="margin:4px 0 0 0;font-size:13px">Generado: {ts}</p>
    </div>
    <div style="padding:16px;border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px">
        <p>{resultado['resumen']}</p>
        {"<table border='0' cellspacing='0' width='100%' style='border-collapse:collapse'><tr style='background:#1A5276;color:white'><th style='padding:7px 10px;text-align:left'>Variable</th><th style='padding:7px 10px'>Valor Actual</th><th style='padding:7px 10px'>Límite</th><th style='padding:7px 10px'>Severidad</th></tr>" + filas_html + "</table>" if alarmas else "<p>✅ Sin violaciones de umbrales.</p>"}
        {if_html}
        <hr style="margin:20px 0">
        <p style="font-size:11px;color:#888">Este es un mensaje automático del Sistema IDEO — Gerencia Infraestructura.</p>
    </div>
    </body></html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[IDEO] Alerta {nivel} — Nodo IDEO CALI — {ts}"
        msg["From"]    = REMITENTE
        msg["To"]      = ", ".join(destinatarios)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as servidor:
            servidor.starttls()
            servidor.login(SMTP_USER, SMTP_PASS)
            servidor.sendmail(REMITENTE, destinatarios, msg.as_string())

        return True, f"Email enviado a: {', '.join(destinatarios)}"

    except Exception as e:
        return False, f"Error enviando email: {e}"